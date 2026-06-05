from PyQt5.QtWidgets import QMenu, QAction

class ChatAppDMMixin:

    def handle_nick_click(self, user_name):
        if user_name.lower() == 'host':
            self.add_system_message('🔒 Нельзя отправить личное сообщение создателю комнаты (Host).', '#ff5c5c')
            return
        users, _ = self.cached_room_users
        target_uuid = None
        for u in users:
            if u['name'] == user_name:
                target_uuid = u['uuid']
                break
        if target_uuid and target_uuid != self.user_uuid:
            self.current_dm_target = target_uuid
            self.input_field.setPlaceholderText(f'Личное сообщение для {user_name}...')
            self.add_system_message(f'💬 Вы пишете личное сообщение для {user_name}', '#E2D189')
        else:
            self.add_system_message('Не удалось определить пользователя', '#ff5c5c')

    def reset_dm_mode(self):
        self.current_dm_target = None
        self.input_field.setPlaceholderText('Нажмите для ввода...')