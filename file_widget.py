import os, threading, requests, time, subprocess, traceback, re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .ASMI_checker import is_malware
from .Acerum import AcerumSmartDownloader

def sanitize_filename(name: str) -> str:
    name = re.sub('[^\\w\\-_ .]', '', name, flags=re.UNICODE)
    name = name.strip('. ')
    return name if name else 'file'

def human_readable_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f'{size:.2f} {unit}'
        size /= 1024
    return f'{size:.2f} PB'

class MaliciousFileDialog(QDialog):

    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle('⚠️ Предупреждение безопасности')
        self.setMinimumWidth(400)
        self.setStyleSheet('background-color: #1e1e1e; color: white; font-size: 12px;')
        layout = QVBoxLayout(self)
        msg = QLabel(f"<b style='color:#ff5c5c;'>ASMI обнаружил угрозу в файле:</b><br><br><span style='color:#ccc;'>{file_name}</span><br><br>Открытие этого файла может нанести вред вашему компьютеру.<br>Продолжайте только если вы абсолютно уверены в его безопасности.")
        msg.setWordWrap(True)
        layout.addWidget(msg)
        self.btn = QPushButton('Подождите...')
        self.btn.setEnabled(False)
        self.btn.setStyleSheet('\n            QPushButton { background: #ff5c5c; color: white; border: none; padding: 8px;\n                          border-radius: 5px; font-weight: bold; font-size: 14px; }\n            QPushButton:disabled { background: #666; color: #aaa; }\n        ')
        layout.addWidget(self.btn)
        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        self.seconds_left = 3
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_btn_text)
        self.timer.start(1000)
        self.update_btn_text()

    def update_btn_text(self):
        if self.seconds_left > 0:
            self.btn.setText(str(self.seconds_left))
            self.seconds_left -= 1
        else:
            self.btn.setText('Открыть файл')
            self.btn.setEnabled(True)
            self.btn.clicked.connect(self.accept)
            self.timer.stop()

class FileWidget(QFrame):
    scan_finished = pyqtSignal(bool)
    download_progress = pyqtSignal(int, int, float)
    download_complete = pyqtSignal(int)

    def __init__(self, username, file_name, file_id, text, crypto, active_server, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(320)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.username = username
        self.file_name = file_name
        self.file_id = file_id
        self.text = text
        self.crypto = crypto
        self.active_server = active_server
        self.downloader = None
        self.is_safe = None
        self.scanning = False
        self.setStyleSheet('\n            FileWidget {\n                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n                                            stop:0 #2c2c2c, stop:1 #1e1e1e);\n                border: 1px solid #E2D189;\n                border-radius: 10px;\n                padding: 8px;\n            }\n            QToolTip {\n                background-color: #333;\n                color: #E2D189;\n                border: 1px solid #E2D189;\n                padding: 4px;\n                border-radius: 4px;\n            }\n        ')
        self.scan_finished.connect(self.on_scan_finished)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet('\n            background: #3a3a3a;\n            border-radius: 10px;\n            font-size: 30px;\n        ')
        ext = self.file_name.split('.')[-1].lower()
        icon_map = {'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'bmp': '🖼️', 'mp4': '🎬', 'mkv': '🎬', 'avi': '🎬', 'mp3': '🎵', 'wav': '🎵', 'ogg': '🎵', 'pdf': '📑'}
        self.icon_lbl.setText(icon_map.get(ext, '🔗'))
        top_layout.addWidget(self.icon_lbl)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        self.file_name_lbl = QLabel(self.file_name)
        self.file_name_lbl.setStyleSheet('color: white; font-weight: bold; font-size: 13px; background: transparent; border: none;')
        self.file_name_lbl.setWordWrap(False)
        fm = QFontMetrics(self.file_name_lbl.font())
        elided = fm.elidedText(self.file_name, Qt.ElideRight, 190)
        self.file_name_lbl.setText(elided)
        info_layout.addWidget(self.file_name_lbl)
        self.status_lbl = QLabel('')
        self.status_lbl.setStyleSheet('color: #aaa; font-size: 11px; background: transparent; border: none;')
        info_layout.addWidget(self.status_lbl)
        sender_lbl = QLabel(f'📤 {self.username}')
        sender_lbl.setStyleSheet('color: #E2D189; font-size: 11px; background: transparent; border: none;')
        info_layout.addWidget(sender_lbl)
        if self.text:
            text_lbl = QLabel(self.text)
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet('color: #ccc; font-size: 11px; background: transparent; border: none; padding-top: 2px;')
            info_layout.addWidget(text_lbl)
        top_layout.addLayout(info_layout, 1)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        self.open_btn = QPushButton()
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setFixedSize(40, 40)
        self.open_btn.setToolTip('Открыть файл')
        self.open_btn.setStyleSheet('\n            QPushButton {\n                background: #E2D189;\n                color: black;\n                border-radius: 8px;\n                font-size: 22px;\n                border: none;\n            }\n            QPushButton:hover {\n                background: #f5e6a8;\n            }\n            QPushButton:disabled {\n                background: #666;\n                color: #aaa;\n            }\n        ')
        self.open_btn.clicked.connect(self.on_open_clicked)
        btn_layout.addWidget(self.open_btn)
        self.folder_btn = QPushButton('📂')
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.setFixedSize(40, 40)
        self.folder_btn.setToolTip('Показать файл в папке')
        self.folder_btn.setStyleSheet('\n            QPushButton {\n                background: #555;\n                color: white;\n                border-radius: 8px;\n                font-size: 22px;\n                border: none;\n            }\n            QPushButton:hover {\n                background: #777;\n            }\n            QPushButton:disabled {\n                background: #444;\n                color: #888;\n            }\n        ')
        self.folder_btn.clicked.connect(self.on_folder_clicked)
        btn_layout.addWidget(self.folder_btn)
        top_layout.addLayout(btn_layout)
        main_layout.addLayout(top_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('\n            QProgressBar {\n                background: rgba(255,255,255,10);\n                border-radius: 2px;\n                border: none;\n            }\n            QProgressBar::chunk {\n                background: #E2D189;\n                border-radius: 2px;\n            }\n        ')
        main_layout.addWidget(self.progress_bar)
        self.update_ui_state()
        self.check_local_file()
        self.download_progress.connect(self._on_download_progress)
        self.download_complete.connect(self._on_download_complete)

    def update_ui_state(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        file_exists = os.path.exists(local_path)
        if self.scanning:
            self.open_btn.setText('🔍')
            self.open_btn.setEnabled(False)
            self.open_btn.setToolTip('Идёт проверка безопасности...')
            self.folder_btn.setEnabled(False)
        elif not file_exists:
            self.open_btn.setText('⬇')
            self.open_btn.setEnabled(True)
            self.open_btn.setToolTip('Скачать файл')
            self.folder_btn.setEnabled(False)
        elif self.is_safe is None:
            self.open_btn.setText('⬇')
            self.open_btn.setEnabled(True)
            self.open_btn.setToolTip('Скачать файл')
            self.folder_btn.setEnabled(False)
        elif self.is_safe:
            self.open_btn.setText('▶')
            self.open_btn.setEnabled(True)
            self.open_btn.setToolTip('Открыть файл')
            self.folder_btn.setEnabled(True)
            self.status_lbl.setText('✅ Файл безопасен')
            self.status_lbl.setStyleSheet('color: #4CAF50; font-size: 11px; background: transparent; border: none;')
        else:
            self.open_btn.setText('⚠️')
            self.open_btn.setEnabled(True)
            self.open_btn.setToolTip('Файл может быть опасен. Открыть на свой риск')
            self.folder_btn.setEnabled(True)
            self.status_lbl.setText('⚠️ Обнаружена угроза!')
            self.status_lbl.setStyleSheet('color: #ff5c5c; font-size: 11px; background: transparent; border: none;')

    def get_download_dir(self):
        parent = self.window()
        if hasattr(parent, 'settings'):
            download_path = parent.settings.get('download_path')
            if download_path:
                return download_path
        return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

    def check_local_file(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if os.path.exists(local_path):
            self.status_lbl.setText(f'Уже загружен: {human_readable_size(os.path.getsize(local_path))}')
            self.start_scan()
        else:
            self.status_lbl.setText('Размер: неизвестен')
        self.update_ui_state()

    def open_file(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if not os.path.exists(local_path):
            QMessageBox.information(self, 'Файл не загружен', 'Сначала скачайте файл через Acerum.')
            return
        ext = self.file_name.split('.')[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                viewer = QLabel()
                viewer.setWindowFlags(Qt.Window)
                viewer.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                viewer.setWindowTitle(self.file_name)
                viewer.show()
                return
        try:
            os.startfile(local_path)
        except OSError as e:
            if e.winerror == 1223:
                pass
            else:
                QMessageBox.warning(self, 'Ошибка открытия', f'Не удалось открыть файл:\n{str(e)}')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка открытия', f'Не удалось открыть файл:\n{str(e)}')

    def start_download(self):
        download_dir = self.get_download_dir()
        filename = sanitize_filename(self.file_name)
        output_path = os.path.join(download_dir, filename)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.open_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)
        self.status_lbl.setText('Загрузка...')
        url = f'{self.active_server}/acerum/download/{self.file_id}'
        print(f'[Download] Начинаю загрузку: {url}')
        print(f'[Download] Output path: {output_path}')

        def run():
            import time, traceback
            try:
                start_time = time.time()
                print('[Download] Отправляю GET запрос...')
                if not re.match('^[a-f0-9\\-]{36}$', self.file_id):
                    raise Exception('Invalid file ID')
                response = requests.get(url, stream=True, timeout=720)
                response.raise_for_status()
                print(f'[Download] Ответ получен, статус: {response.status_code}')
                total_length = response.headers.get('Content-Length')
                total_size = int(total_length) if total_length else 0
                print(f'[Download] Размер файла: {total_size} байт (0 = неизвестен)')
                encrypted_data = b''
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        encrypted_data += chunk
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        self.download_progress.emit(downloaded, total_size, speed)
                print(f'[Download] Загружено {downloaded} байт, начинаю расшифровку...')
                nonce = encrypted_data[:12]
                ciphertext = encrypted_data[12:]
                print(f'[Download] Расшифровка...')
                decrypted = self.crypto.aes.decrypt(nonce, ciphertext, None)
                with open(output_path, 'wb') as f:
                    f.write(decrypted)
                print(f'[Download] Файл сохранён: {output_path}, размер {len(decrypted)} байт')
                self.download_complete.emit(len(decrypted))
            except Exception as e:
                print(f'[Download] Ошибка:')
                traceback.print_exc()
                QTimer.singleShot(0, lambda m=str(e): self._on_download_error(f'Ошибка загрузки: {m}'))
        threading.Thread(target=run, daemon=True).start()

    @pyqtSlot(int, int, float)
    def _on_download_progress(self, done, total, speed):
        self._update_download_progress(done, total, speed)

    def _update_download_progress(self, done, total, speed):
        if total > 0:
            percent = int(done / total * 100)
            self.progress_bar.setValue(percent)
            speed_str = human_readable_size(speed) + '/s' if speed else ''
            self.status_lbl.setText(f'{human_readable_size(done)} / {human_readable_size(total)}  {speed_str}')
        else:
            speed_str = human_readable_size(speed) + '/s' if speed else ''
            self.status_lbl.setText(f'Загружено: {human_readable_size(done)}  {speed_str}')

    def _on_download_complete(self, size):
        self.progress_bar.setVisible(False)
        self.status_lbl.setText(f'Загружен: {human_readable_size(size)}')
        self.start_scan()
        self.update_ui_state()

    def _on_download_error(self, error_msg):
        import traceback
        full_trace = traceback.format_exc()
        print(f'[UI] Ошибка загрузки: {error_msg}')
        print(full_trace)
        QMessageBox.critical(self, 'Ошибка загрузки', f'{error_msg}\n\nПодробности:\n{full_trace}')
        self.progress_bar.setVisible(False)
        self.status_lbl.setText(error_msg)
        self.open_btn.setEnabled(True)
        self.folder_btn.setEnabled(False)
        self.update_ui_state()

    def start_scan(self):
        if self.scanning:
            return
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if not os.path.exists(local_path):
            return
        self.scanning = True
        self.update_ui_state()
        self.open_btn.setEnabled(False)

        def scan_thread():
            try:
                with open(local_path, 'rb') as f:
                    data = f.read()
                infected = is_malware(data, self.file_name)
                result = not infected
            except Exception as e:
                print(f'Ошибка сканирования: {e}')
                result = False
            self.scanning = False
            self.is_safe = result
            self.scan_finished.emit(result)
        threading.Thread(target=scan_thread, daemon=True).start()

    @pyqtSlot(bool)
    def on_scan_finished(self, is_safe):
        self.update_ui_state()
        parent = self.window()
        if hasattr(parent, 'show_toast'):
            if is_safe:
                parent.show_toast(f'✅ {self.file_name} — безопасен')
            else:
                parent.show_toast(f'⚠️ {self.file_name} может быть вредоносным!')

    def on_open_clicked(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if not os.path.exists(local_path):
            self.start_download()
        elif self.is_safe:
            self.open_file()
        else:
            dlg = MaliciousFileDialog(self.file_name, self)
            if dlg.exec_() == QDialog.Accepted:
                self.open_file()

    def on_folder_clicked(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if not os.path.exists(local_path):
            QMessageBox.information(self, 'Файл не найден', 'Сначала загрузите файл.')
            return
        try:
            subprocess.Popen(['explorer', '/select,', os.path.normpath(local_path)])
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось открыть папку:\n{e}')