import sys
import time
import threading
import requests
import re
from PyQt5.QtWidgets import QMessageBox, QInputDialog
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
        self.room_key = generate_room_key()
        self.room_code = room_code_from_key(self.room_key)
        self.crypto = Crypto(self.room_key)
        self.is_creator = True
        self._seen_join_requests.clear()
        self._pending_join_requests.clear()
        self._join_dialog_active = False
        try:
            requests.post(f'{self.active_server}/create_room', params={'room_code': self.room_code, 'creator_uuid': self.user_uuid}, timeout=5)
            self.is_in_chat = True
            self.add_system_message(f'Комната создана. Поделитесь кодом: {self.room_key}', color='#4CAF50')
        except Exception as e:
            self.add_system_message(f'Ошибка создания комнаты: {e}', color='#ff5c5c')

    def join_room_dialog(self):
        while True:
            code, ok = QInputDialog.getText(self, 'Вход в чат', 'Введите код комнаты (например, Kx9-2Qr-zP):')
            if not ok:
                self.main_menu()
                return
            raw_key = re.sub('[^A-Za-z0-9_-]', '', code)
            if len(raw_key) != 12 or not set(raw_key).issubset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-'):
                QMessageBox.warning(self, 'Ошибка', 'Неверный формат кода (должно быть 12 символов). Попробуйте снова.')
                continue
            break
        self.room_key = raw_key
        self.room_code = room_code_from_key(self.room_key)
        self.crypto = Crypto(self.room_key)
        self.is_creator = False
        try:
            requests.post(f'{self.active_server}/join_request', params={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': self.settings['name']}, timeout=5)
            self.add_system_message('Запрос на вступление отправлен.')
        except Exception as e:
            self.add_system_message(f'Ошибка: {e}', color='#ff5c5c')

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
                requests.post(f'{self.active_server}/approve_user', params={'room_code': self.room_code, 'user_uuid': uid}, timeout=3)
                QMessageBox.information(self, 'Готово', f'Пользователь {name} принят.')
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось одобрить: {e}')
        else:
            try:
                requests.post(f'{self.active_server}/reject_user', params={'room_code': self.room_code, 'user_uuid': uid}, timeout=3)
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