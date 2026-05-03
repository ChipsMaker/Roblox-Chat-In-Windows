import sys
import os
import uuid
import threading
import requests
from PyQt5.QtWidgets import QWidget, QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from .config import SERVERS_DATA, SERVER_URLS, VERSION, GITHUB_REPO
from .network_worker import NetworkWorker
from .download_window import DownloadWindow
import src.resources_rc
from .chat_app_ui_mixin import ChatAppUIMixin
from .chat_app_events_mixin import ChatAppEventsMixin
from .chat_app_server_mixin import ChatAppServerMixin
from .chat_app_room_mixin import ChatAppRoomMixin
from .chat_app_settings_mixin import ChatAppSettingsMixin
from .chat_app_helpers_mixin import ChatAppHelpersMixin

class ChatApp(QWidget, ChatAppRoomMixin, ChatAppUIMixin, ChatAppEventsMixin, ChatAppServerMixin, ChatAppSettingsMixin, ChatAppHelpersMixin):
    request_focus_signal = pyqtSignal()
    ping_updated_signal = pyqtSignal()
    VERSION = VERSION
    SERVER_URLS = SERVER_URLS
    GITHUB_REPO = GITHUB_REPO

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.attached_files = []
        self.http_session = requests.Session()
        self.server_pings = {url: '---' for url in SERVER_URLS}
        self.server_status = {url: False for url in SERVER_URLS}
        self.room_key = None
        self.room_code = None
        self.is_in_chat = False
        self.settings_path = os.path.join(os.getenv('APPDATA'), 'RBX_Chat_v2', 'settings.json')
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        self.load_settings()
        self._dialog_is_active = False
        manual = self.settings.get('manual_server')
        if manual in SERVER_URLS:
            self.active_server = manual
            self.auto_server_mode = False
        else:
            self.active_server = SERVER_URLS[0]
            self.auto_server_mode = True
        self.user_uuid = str(uuid.uuid4())
        self.last_sync = 0.0
        self.crypto = None
        self.pending_tasks = []
        self.current_dm_target = None
        self.pending_tasks = []
        self.attached_files = []
        self.init_ui()
        self.worker = NetworkWorker(self)
        self.worker.new_messages.connect(self.on_new_messages)
        self.worker.join_request.connect(self.on_join_request)
        self.worker.access_approved.connect(self.on_access_approved)
        self.worker.typing_updated.connect(self.update_typing_label)
        self.worker.start()
        self.ping_updated_signal.connect(self.actual_ui_ping_update)
        self.find_best_server()
        threading.Thread(target=self.server_monitor_loop, daemon=True).start()
        self.tray_icon = None
        self.create_tray_icon()
        QTimer.singleShot(800, self.check_updates)

    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        from PyQt5.QtGui import QIcon
        icon = QIcon(':/forBuild/new_icon.png')
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip('Red65 Chat')
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        menu = QMenu()
        show_action = menu.addAction('Показать')
        show_action.triggered.connect(self.restore_from_tray)
        quit_action = menu.addAction('Выход')
        quit_action.triggered.connect(self.quit_app)
        self.tray_icon.setContextMenu(menu)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.restore_from_tray()

    def minimize_to_tray(self):
        if self.tray_icon:
            self.tray_icon.show()
        self.hide()

    def restore_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(100, self.input_field.setFocus)

    def show_notification(self, title, message):
        try:
            from windows_toasts import Toast, WindowsToaster
            toaster = WindowsToaster('Red65 Chat')
            new_toast = Toast()
            new_toast.text_fields = [f'{title}: {message}']
            toaster.show_toast(new_toast)
        except Exception as e:
            print(f'Toast error: {e}')

    def on_join_request(self, uid, name):
        return ChatAppRoomMixin.on_join_request(self, uid, name)

    def on_access_approved(self):
        return ChatAppRoomMixin.on_access_approved(self)

    def on_new_messages(self, messages):
        return ChatAppEventsMixin.on_new_messages(self, messages)

    def update_typing_label(self, users):
        return ChatAppHelpersMixin.update_typing_label(self, users)

    def check_updates(self):
        if not getattr(self, 'settings', {}).get('auto_update', True):
            return
        try:
            res = requests.get(f'https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest', timeout=5).json()
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

    def show_admin_menu(self):
        return ChatAppUIMixin.show_admin_menu(self)

    def handle_nick_click(self, url):
        return ChatAppUIMixin.handle_nick_click(self, url)

    def toggle_emoji_menu(self):
        return ChatAppUIMixin.toggle_emoji_menu(self)

    def show_settings(self):
        self.open_settings()

    def quit_app(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
        if hasattr(self, 'worker'):
            self.worker.running = False
            self.worker.quit()
            self.worker.wait(2000)
        QApplication.quit()