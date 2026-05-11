import time
import threading
import requests
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QTimer, Qt

class ChatAppHelpersMixin:

    def update_typing_label(self, users):
        if not users:
            self.typing_lbl.setText('')
            return
        if len(users) == 1:
            text = f'{users[0]} печатает...'
        elif len(users) == 2:
            text = f'{users[0]} и {users[1]} печатают...'
        else:
            text = 'Несколько человек печатают...'
        self.typing_lbl.setText(text)

    def on_input_changed(self):
        now = time.time()
        if not hasattr(self, '_last_typing_sent') or now - self._last_typing_sent > 2:
            self._last_typing_sent = now
            threading.Thread(target=requests.post, args=(f'{self.active_server}/typing',), kwargs={'params': {'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': self.settings['name']}}, daemon=True).start()

    def add_system_message(self, text, color='#888'):
        lbl = QLabel(text)
        lbl.setStyleSheet(f'color: {color}; font-style: italic; font-size: 12px;')
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setCursor(Qt.IBeamCursor)
        self.chat_layout.addWidget(lbl)
        self.scroll_chat_to_bottom()

    def add_chat_message(self, user_name, text, sender_uuid):
        lbl = QLabel(f"<b style='color:#E2D189'>{user_name}:</b> {text}")
        lbl.setStyleSheet('color: white; font-size: 13px;')
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setCursor(Qt.IBeamCursor)
        self.chat_layout.addWidget(lbl)
        self.scroll_chat_to_bottom()