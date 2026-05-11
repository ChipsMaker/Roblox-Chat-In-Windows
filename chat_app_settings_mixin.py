import os, json, time, threading, sys, requests, hmac, hashlib, winreg
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QStandardPaths
from .config import SERVERS_DATA, SERVER_URLS, VERSION
from pathlib import Path

class ChatAppSettingsMixin:

    def load_settings(self):
        default_settings = {'name': '', 'last_changed': 0, 'auto_update': True, 'slash_activation': True, 'manual_server': None, 'download_path': None}
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r') as f:
                try:
                    self.settings = json.load(f)
                except:
                    self.settings = default_settings
                    return
            signature = self.settings.pop('signature', None)
            expected_sig = self._compute_signature(self.settings)
            if not signature or not hmac.compare_digest(signature, expected_sig):
                self.settings['name'] = ''
                self.settings['last_changed'] = 0
                self.save_settings()
                return
            for k, v in default_settings.items():
                if k not in self.settings:
                    self.settings[k] = v
        else:
            self.settings = default_settings

    def save_settings(self):
        self.settings['signature'] = self._compute_signature(self.settings)
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def can_change_name(self):
        last_changed = self.settings.get('last_changed', 0)
        now = time.time()
        cooldown_period = 604800
        if now - last_changed > cooldown_period:
            return (True, 0)
        remaining_sec = cooldown_period - (now - last_changed)
        days_left = int(remaining_sec // 86400) + 1
        return (False, days_left)

    def change_save_path(self):
        path = QFileDialog.getExistingDirectory(self, 'Выберите папку для скачивания')
        if path:
            self.settings['download_path'] = path
            self.path_display.setText(path)

    def _get_or_create_signing_key(self):
        reg_path = 'Software\\Red65\\Chat'
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            signing_key = winreg.QueryValueEx(key, 'SigningKey')[0]
            winreg.CloseKey(key)
            return signing_key.encode() if isinstance(signing_key, str) else signing_key
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
            new_key = os.urandom(32)
            winreg.SetValueEx(key, 'SigningKey', 0, winreg.REG_BINARY, new_key)
            winreg.CloseKey(key)
            return new_key

    def _compute_signature(self, settings_dict):
        protected = {'name': settings_dict.get('name', ''), 'last_changed': settings_dict.get('last_changed', 0)}
        data = json.dumps(protected, sort_keys=True).encode()
        signing_key = self._get_or_create_signing_key()
        sig = hmac.new(signing_key, data, hashlib.sha256).hexdigest()
        return sig

    def show_settings_dialog(self):
        if hasattr(self, 'open_settings'):
            self.open_settings()
        else:
            QMessageBox.information(self, 'Settings', 'Ошибка открытия настроек.')

        def check_updates(self):
            if not self.settings.get('auto_update', True):
                return
            try:
                res = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest', timeout=5).json()
                latest_ver = res['tag_name'].replace('v', '')
                if latest_ver > self.VERSION:
                    m = QMessageBox(self)
                    m.setWindowTitle('Update Available')
                    m.setText(f'Доступна новая версия: v{latest_ver}\nХотите обновиться?')
                    b_down = m.addButton('Download', QMessageBox.AcceptRole)
                    b_skip = m.addButton('Skip', QMessageBox.RejectRole)
                    m.exec_()
                    if m.clickedButton() == b_down:
                        download_url = res['assets'][0]['browser_download_url']
                        self.updater = DownloadWindow(download_url, latest_ver, sys.argv[0])
            except Exception as e:
                print(f'Ошибка проверки обновлений: {e}')

    def open_settings(self):
        if not hasattr(self, '_dialog_is_active'):
            self._dialog_is_active = False
        if self._dialog_is_active:
            return
        self._dialog_is_active = True
        can_change, days_left = self.can_change_name()
        dialog = QDialog(self)
        dialog.setWindowTitle('Настройки Red65 Chat')
        dialog.setFixedWidth(380)
        dialog.setStyleSheet('background-color: #f0f0f0; color: black;')
        d_layout = QVBoxLayout(dialog)
        nick_info_label = QLabel(f'Ваш ник: {self.settings['name']}')
        nick_info_label.setStyleSheet('font-size: 13px; color: black; font-weight: bold;')
        d_layout.addWidget(nick_info_label)
        new_name_input = QLineEdit()
        new_name_input.setPlaceholderText('Введите новый ник...')
        new_name_input.setStyleSheet('background-color: white; color: black; border: 1px solid #ccc; padding: 4px;')
        if not can_change:
            new_name_input.setDisabled(True)
            time_lbl = QLabel(f'⏳ Смена ника доступна через: {days_left} дн.')
            time_lbl.setStyleSheet('color: gray; font-size: 11px;')
            d_layout.addWidget(new_name_input)
            d_layout.addWidget(time_lbl)
        else:
            d_layout.addWidget(new_name_input)
        d_layout.addSpacing(10)
        d_layout.addWidget(QLabel('<b>Сервер для подключения:</b>'))
        self.ui_ping_labels = {}
        self.ui_status_circles = {}
        self.server_group = QButtonGroup(dialog)
        auto_rb = QRadioButton('Автоматический выбор (лучший пинг)')
        self.server_group.addButton(auto_rb, 0)
        if self.settings.get('manual_server') is None:
            auto_rb.setChecked(True)
        d_layout.addWidget(auto_rb)
        for i, url in enumerate(SERVER_URLS):
            s_layout = QHBoxLayout()
            rb = QRadioButton(SERVERS_DATA.get(url, 'Server'))
            self.server_group.addButton(rb, i + 1)
            if self.settings.get('manual_server') == url:
                rb.setChecked(True)
            p_text = self.server_pings.get(url, '---')
            status = self.server_status.get(url, False)
            ping_lbl = QLabel(p_text)
            ping_lbl.setFixedWidth(55)
            ping_lbl.setStyleSheet('color: black; font-weight: bold; font-size: 11px;')
            status_circle = QLabel('●')
            color = '#4CAF50' if status else '#ff5c5c'
            status_circle.setStyleSheet(f'color: {color}; font-size: 16px;')
            s_layout.addWidget(rb)
            s_layout.addStretch()
            s_layout.addWidget(ping_lbl)
            s_layout.addWidget(status_circle)
            d_layout.addLayout(s_layout)
            self.ui_ping_labels[url] = ping_lbl
            self.ui_status_circles[url] = status_circle

        def background_worker():
            self.refresh_server_statuses()
            while dialog.isVisible():
                time.sleep(1.5)
                if not dialog.isVisible():
                    break
                self.refresh_server_statuses()
        threading.Thread(target=background_worker, daemon=True).start()
        d_layout.addSpacing(10)
        auto_upd_cb = QCheckBox('Включить автообновление')
        auto_upd_cb.setChecked(self.settings.get('auto_update', True))
        d_layout.addWidget(auto_upd_cb)
        slash_cb = QCheckBox('Активация через slash (/)')
        slash_cb.setChecked(self.settings.get('slash_activation', True))
        d_layout.addWidget(slash_cb)
        d_layout.addWidget(QLabel('<b>📁 Папка для скачивания:</b>'))
        path_box = QHBoxLayout()
        current_p = self.settings.get('download_path')
        if not current_p:
            current_p = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        self.path_display = QLabel(current_p)
        self.path_display.setStyleSheet('font-size: 10px; color: #555;')
        btn_sel = QPushButton('Изменить')
        btn_sel.setFixedWidth(70)
        btn_sel.clicked.connect(self.change_save_path)
        path_box.addWidget(self.path_display)
        path_box.addWidget(btn_sel)
        d_layout.addLayout(path_box)
        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet('height: 30px; background: #e2d189; color: black; font-weight: bold; border-radius: 5px;')
        d_layout.addWidget(save_btn)

        def handle_save():
            sid = self.server_group.checkedId()
            if sid == 0:
                self.auto_server_mode = True
                self.settings['manual_server'] = None
            else:
                self.auto_server_mode = False
                self.active_server = SERVER_URLS[sid - 1]
                self.settings['manual_server'] = self.active_server
            self.settings['auto_update'] = auto_upd_cb.isChecked()
            self.settings['slash_activation'] = slash_cb.isChecked()
            name = new_name_input.text().strip()
            if name and can_change:
                self.settings['name'] = name.replace('@', '')
                self.settings['last_changed'] = time.time()
            self.save_settings()
            dialog.accept()
        save_btn.clicked.connect(handle_save)
        dialog.finished.connect(lambda: setattr(self, '_dialog_is_active', False))
        dialog.exec_()