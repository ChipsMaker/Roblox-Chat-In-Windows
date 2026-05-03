import sys
import time
import threading
import requests
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
        try:
            requests.post(f'{self.active_server}/create_room', params={'room_code': self.room_code, 'creator_uuid': self.user_uuid}, timeout=5)
            self.is_in_chat = True
            formatted_key = '-'.join((self.room_key[i:i + 4] for i in range(0, 12, 4)))
            self.add_system_message(f'Комната создана. Поделитесь кодом: {formatted_key}', color='#4CAF50')
        except Exception as e:
            self.add_system_message(f'Ошибка создания комнаты: {e}', color='#ff5c5c')

    def join_room_dialog(self):
        code, ok = QInputDialog.getText(self, 'Вход в чат', 'Введите код комнаты (например, Kx9-2Qr-zP):')
        if ok and code:
            raw_key = code.replace('-', '').replace(' ', '').strip()
            if len(raw_key) != 12 or not set(raw_key).issubset('-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'):
                QMessageBox.warning(self, 'Ошибка', 'Неверный формат кода (должно быть 12 символов).')
                return
            self.room_key = raw_key
            self.room_code = room_code_from_key(self.room_key)
            self.crypto = Crypto(self.room_key)
            try:
                requests.post(f'{self.active_server}/join_request', params={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': self.settings['name']}, timeout=5)
                self.add_system_message('Запрос на вступление отправлен.')
            except Exception as e:
                self.add_system_message(f'Ошибка: {e}', color='#ff5c5c')

    def on_access_approved(self):
        if not self.is_in_chat:
            self.is_in_chat = True
            self.add_system_message('Доступ подтвержден!', color='#4CAF50')