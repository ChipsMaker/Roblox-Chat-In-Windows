import sys, time, threading, requests, re, subprocess, os
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from PyQt5.QtCore import QTimer, QMetaObject, Qt, Q_ARG, pyqtSlot
from .config import generate_room_key, room_code_from_key
from .crypto import Crypto

class ChatAppRoomMixin:

    def start_flow(self):
        if not self.settings['name']:
            self.ask_name()
        self.main_menu()

    def ask_name(self):
        name, ok = QInputDialog.getText(self, 'Roblox Chat', 'Ваш ник Roblox (@):')
        if ok and name:
            self.settings['name'] = name.replace('@', '')
            self.settings['last_changed'] = time.time()
            self.save_settings()
        else:
            sys.exit()

    def main_menu(self):
        m = QMessageBox(self)
        m.setText(f'Аккаунт: {self.settings['name']}\nВыберите действие:')
        b_create = m.addButton('Создать чат', QMessageBox.AcceptRole)
        b_join = m.addButton('Войти в чат', QMessageBox.AcceptRole)
        m.exec_()
        if m.clickedButton() == b_create:
            self.create_room()
        else:
            self.join_room_dialog()

    def create_room(self):
        room_key = generate_room_key()
        room_code = room_code_from_key(room_key)
        self._seen_join_requests.clear()
        self._pending_join_requests.clear()
        self._join_dialog_active = False
        status_msg = self.add_system_message('🔄 Подключение к серверу и создание комнаты... Это может занять до 2 минут, пожалуйста, подождите.', '#E2D189')

        def _do_create(attempt=1):
            try:
                verify_ssl = True
                if attempt > 2:
                    verify_ssl = False
                print(f'[CREATE] Попытка {attempt}/3: отправка запроса к {self.active_server} (verify={verify_ssl})')
                resp = self.session.post(f'{self.active_server}/create_room', params={'room_code': room_code, 'creator_uuid': self.user_uuid}, timeout=120, verify=verify_ssl)
                resp.raise_for_status()
                print('[CREATE] Комната успешно создана')
                QMetaObject.invokeMethod(self, '_update_status_message', Qt.QueuedConnection, Q_ARG(object, status_msg), Q_ARG(str, f'✅ Комната создана. Поделитесь кодом: {room_key}'), Q_ARG(str, '#4CAF50'))
                self.room_key = room_key
                self.room_code = room_code
                self.crypto = Crypto(self.room_key)
                self.is_creator = True
                self.is_in_chat = True
            except requests.exceptions.SSLError as e:
                print(f'[CREATE] SSL ошибка (попытка {attempt}/3): {e}')
                if attempt < 3:
                    QMetaObject.invokeMethod(self, 'add_system_message', Qt.QueuedConnection, Q_ARG(str, f'⚠️ SSL ошибка. Повторная попытка {attempt + 1}/3...'), Q_ARG(str, '#ffaa00'))
                    threading.Timer(3.0, lambda: _do_create(attempt + 1)).start()
                else:
                    QMetaObject.invokeMethod(self, '_update_status_message', Qt.QueuedConnection, Q_ARG(object, status_msg), Q_ARG(str, '❌ Ошибка создания комнаты: Не удалось установить защищённое соединение.'), Q_ARG(str, '#ff5c5c'))
                    QMetaObject.invokeMethod(self, '_show_restart_dialog', Qt.QueuedConnection)
                    print('[CREATE] Все попытки исчерпаны, создание комнаты не удалось')
            except requests.exceptions.RequestException as e:
                print(f'[CREATE] Ошибка соединения (попытка {attempt}/3): {e}')
                if attempt < 3:
                    QMetaObject.invokeMethod(self, 'add_system_message', Qt.QueuedConnection, Q_ARG(str, f'⚠️ Ошибка соединения. Повторная попытка {attempt + 1}/3...'), Q_ARG(str, '#ffaa00'))
                    threading.Timer(3.0, lambda: _do_create(attempt + 1)).start()
                else:
                    error_msg = str(e)[:100]
                    QMetaObject.invokeMethod(self, '_update_status_message', Qt.QueuedConnection, Q_ARG(object, status_msg), Q_ARG(str, f'❌ Ошибка создания комнаты: {error_msg}'), Q_ARG(str, '#ff5c5c'))
                    QMetaObject.invokeMethod(self, '_show_restart_dialog', Qt.QueuedConnection)
                    print('[CREATE] Все попытки исчерпаны, создание комнаты не удалось')
            except Exception as e:
                print(f'[CREATE] Непредвиденная ошибка (попытка {attempt}/3): {e}')
                if attempt < 3:
                    QMetaObject.invokeMethod(self, 'add_system_message', Qt.QueuedConnection, Q_ARG(str, f'⚠️ Непредвиденная ошибка. Повторная попытка {attempt + 1}/3...'), Q_ARG(str, '#ffaa00'))
                    threading.Timer(3.0, lambda: _do_create(attempt + 1)).start()
                else:
                    QMetaObject.invokeMethod(self, '_update_status_message', Qt.QueuedConnection, Q_ARG(object, status_msg), Q_ARG(str, f'❌ Внутренняя ошибка: {str(e)[:80]}'), Q_ARG(str, '#ff5c5c'))
                    QMetaObject.invokeMethod(self, '_show_restart_dialog', Qt.QueuedConnection)
                    print('[CREATE] Все попытки исчерпаны, создание комнаты не удалось')
        threading.Thread(target=_do_create, daemon=True).start()

    @pyqtSlot(object, str, str)
    def _update_status_message(self, label, new_text, color):
        if label and (not label.isHidden()):
            label.setText(new_text)
            label.setStyleSheet(f'color: {color}; font-style: italic; font-size: 12px;')

    @pyqtSlot()
    def _show_restart_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle('Ошибка создания комнаты')
        msg.setText('Не удалось создать комнату после нескольких попыток.\n\nВозможно, проблема с сетевым подключением.')
        restart_btn = msg.addButton('Перезапустить приложение', QMessageBox.ActionRole)
        restart_btn.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #E2D189;\n                text-decoration: underline;\n                border: none;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                color: #f5e6a8;\n            }\n        ')
        restart_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn = msg.addButton('Отмена', QMessageBox.RejectRole)
        msg.exec_()
        if msg.clickedButton() == restart_btn:
            subprocess.Popen([sys.executable] + sys.argv)
            os._exit(0)

    def clear_chat(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def join_room_dialog(self):
        while True:
            code, ok = QInputDialog.getText(self, 'Вход в чат', 'Введите код комнаты:')
            if not ok:
                self.main_menu()
                return
            raw_key = re.sub('[^A-Za-z0-9_-]', '', code)
            if len(raw_key) != 12 or not set(raw_key).issubset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-'):
                QMessageBox.warning(self, 'Ошибка', 'Неверный формат кода (должно быть 12 символов). Попробуйте снова.')
                continue
            break
        room_code = room_code_from_key(raw_key)

        def _do_join():
            try:
                resp = self.session.post(f'{self.active_server}/join_request', params={'room_code': room_code, 'user_uuid': self.user_uuid, 'username': self.settings['name']}, timeout=60)
                if resp.status_code == 200:
                    self.room_key = raw_key
                    self.room_code = room_code
                    self.crypto = Crypto(self.room_key)
                    self.is_creator = False
                    self.add_system_message('✅ Запрос на вступление отправлен. Ожидайте одобрения создателя.')
                else:
                    self.add_system_message(f'❌ Вход отклонён (Код {resp.status_code})', color='#ff5c5c')
            except Exception as e:
                self.add_system_message(f'❌ Ошибка: {e}', color='#ff5c5c')
        threading.Thread(target=_do_join, daemon=True).start()

    def on_join_request(self, uid, name):
        if not self.is_creator:
            return
        if uid in self._seen_join_requests:
            return
        self._seen_join_requests.add(uid)
        if self._join_dialog_active:
            self._pending_join_requests.append((uid, name))
            return
        self._show_join_request_dialog(uid, name)

    def _show_join_request_dialog(self, uid, name):
        self._join_dialog_active = True
        msg = QMessageBox(self)
        msg.setWindowTitle('Запрос на вступление')
        msg.setText(f"Пользователь '{name}' хочет присоединиться к комнате.")
        accept_btn = msg.addButton('Принять', QMessageBox.AcceptRole)
        reject_btn = msg.addButton('Отклонить', QMessageBox.RejectRole)
        msg.exec_()
        if msg.clickedButton() == accept_btn:
            try:
                self.session.post(f'{self.active_server}/approve_user', params={'room_code': self.room_code, 'user_uuid': uid}, timeout=3)
                QMessageBox.information(self, 'Готово', f'Пользователь {name} принят.')
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось одобрить: {e}')
        else:
            try:
                self.session.post(f'{self.active_server}/reject_user', params={'room_code': self.room_code, 'user_uuid': uid}, timeout=3)
            except:
                pass
        self._join_dialog_active = False
        if self._pending_join_requests:
            next_uid, next_name = self._pending_join_requests.pop(0)
            self._show_join_request_dialog(next_uid, next_name)

    def on_access_approved(self):
        if not self.is_in_chat:
            self.is_in_chat = True
            self.add_system_message('Доступ подтвержден!', color='#4CAF50')
            threading.Thread(target=self.load_history, daemon=True).start()

    def load_history(self):
        try:
            resp = requests.get(f'{self.active_server}/history', params={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'after_time': 0.0}, timeout=10)
            if resp.status_code == 200:
                history = resp.json().get('messages', [])
                for m in history:
                    self.on_new_messages([m])
        except Exception as e:
            print(f'Ошибка загрузки истории: {e}')
            self.add_system_message('⚠️ Не удалось загрузить историю сообщений', '#ffaa00')