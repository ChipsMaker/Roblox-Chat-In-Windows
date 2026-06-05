import sys
import os
import uuid
import threading
import requests
from PyQt5.QtWidgets import QWidget, QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal, Qt, pyqtSlot, QMetaObject, Q_ARG
from .config import SERVERS_DATA, SERVER_URLS, VERSION, GITHUB_REPO
from .network_worker import SyncPoller
from .download_window import DownloadWindow
import src.resources_rc
from .chat_app_ui_mixin import ChatAppUIMixin
from .chat_app_events_mixin import ChatAppEventsMixin
from .chat_app_server_mixin import ChatAppServerMixin
from .chat_app_room_mixin import ChatAppRoomMixin
from .chat_app_settings_mixin import ChatAppSettingsMixin
from .chat_app_helpers_mixin import ChatAppHelpersMixin
from .chat_app_dm_mixin import ChatAppDMMixin

class ChatApp(QWidget, ChatAppRoomMixin, ChatAppUIMixin, ChatAppEventsMixin, ChatAppServerMixin, ChatAppSettingsMixin, ChatAppHelpersMixin, ChatAppDMMixin):
    request_focus_signal = pyqtSignal()
    ping_updated_signal = pyqtSignal()
    VERSION = VERSION
    SERVER_URLS = SERVER_URLS
    GITHUB_REPO = GITHUB_REPO

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.setAcceptDrops(True)
        self.attached_files = []
        self.current_dm_target = None
        self.oldPos = None
        self.cached_room_users = None
        self.last_room_users_fetch = 0
        self.is_fetching_room_users = False
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
        self.init_ui()
        self.show()
        self.check_updates()
        self.server_search_complete = False
        self.server_search_in_progress = False
        self.poller = SyncPoller(self)
        self.poller.new_messages.connect(self.on_new_messages)
        self.poller.join_request.connect(self.on_join_request)
        self.poller.access_approved.connect(self.on_access_approved)
        self.poller.typing_updated.connect(self.update_typing_label)
        self.poller.start()
        self.is_creator = False
        self._seen_join_requests = set()
        self._pending_join_requests = []
        self._join_dialog_active = False
        self.server_search_in_progress = True
        threading.Thread(target=self._async_find_best_server, daemon=True).start()
        self.ping_updated_signal.connect(self.actual_ui_ping_update)
        threading.Thread(target=self.server_monitor_loop, daemon=True).start()
        self.tray_icon = None
        self.create_tray_icon()

    @pyqtSlot()
    def on_connection_lost(self):
        self.add_system_message('⚠️ Потеря соединения с сервером. Переподключение...', '#ffaa00')
        threading.Thread(target=self.rejoin_room, daemon=True).start()

    def rejoin_room(self):
        if not self.room_code:
            return
        for url in self.SERVER_URLS:
            try:
                resp = requests.get(f'{url}/check_access', params={'room_code': self.room_code, 'user_uuid': self.user_uuid}, timeout=3)
                if resp.json().get('status') == 'approved':
                    self.active_server = url
                    self.add_system_message(f'✅ Переподключено к серверу {url}', '#4CAF50')
                    return
            except:
                continue
        self.add_system_message('❌ Не удалось переподключиться. Попробуйте выйти и зайти заново.', '#ff5c5c')

    def reconnect_to_room_on_new_server(self, new_server_url):
        if not self.room_code or not self.room_key:
            return
        try:
            resp = requests.get(f'{new_server_url}/check_access', params={'room_code': self.room_code, 'user_uuid': self.user_uuid}, timeout=5)
            if resp.json().get('status') == 'approved':
                old_server = self.active_server
                self.active_server = new_server_url
                self.add_system_message(f'🔄 Сервер переключён с {old_server} на {new_server_url}', '#E2D189')
            else:
                print(f'Нет доступа к комнате на сервере {new_server_url}, переключение отменено')
        except Exception as e:
            print(f'Ошибка при переключении сервера: {e}')
    ' def _start_background_services(self):\n        # Запускает фоновые задачи без блокировки главного потока.\n        # Запускаем мониторинг серверов в отдельном потоке\n        threading.Thread(target=self.server_monitor_loop, daemon=True).start()\n        # Выбор лучшего сервера – тоже в потоке, без join\n        threading.Thread(target=self._async_find_best_server, daemon=True).start() '

    def send_delivery_ack(self, msg_time):
        try:
            requests.post(f'{self.active_server}/delivery_ack', params={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'message_time': msg_time}, timeout=5)
        except:
            pass

    def _async_find_best_server(self):
        try:
            self.find_best_server()
        except Exception as e:
            print(f'Ошибка поиска сервера: {e}')
        finally:
            self.server_search_complete = True
            self.server_search_in_progress = False

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
        if getattr(self, '_update_dialog_active', False):
            return
        self._update_dialog_active = True

        def async_check():
            try:
                res = self.session.get(f'https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest', timeout=5).json()
                tag = res.get('tag_name', '')
                import re
                match = re.match('v?(\\d+\\.\\d+\\.\\d+)', tag)
                if not match:
                    self._finish_update_check_and_start_flow()
                    return
                latest_ver = match.group(1)
                if latest_ver > self.VERSION:
                    is_critical = tag.endswith('_critical')
                    download_url = res['assets'][0]['browser_download_url'] if res.get('assets') else None
                    if download_url:
                        QMetaObject.invokeMethod(self, 'show_update_dialog', Qt.QueuedConnection, Q_ARG(str, latest_ver), Q_ARG(str, download_url), Q_ARG(bool, is_critical))
                        return
                    else:
                        self._finish_update_check_and_start_flow()
                else:
                    self._finish_update_check_and_start_flow()
            except Exception as e:
                print(f'Ошибка проверки обновлений: {e}')
                self._finish_update_check_and_start_flow()
        threading.Thread(target=async_check, daemon=True).start()

    def _finish_update_check_and_start_flow(self):
        self._update_dialog_active = False
        QMetaObject.invokeMethod(self, '_start_flow_safe', Qt.QueuedConnection)

    @pyqtSlot()
    def _start_flow_safe(self):
        self.start_flow()

    @pyqtSlot(str, str, bool)
    def show_update_dialog(self, latest_ver, download_url, is_critical=False):
        m = QMessageBox(self)
        if is_critical:
            m.setWindowTitle('⚠️ Критическое обновление')
            m.setText(f'Доступна новая версия: v{latest_ver}\n\nЭто обязательное обновление. Вы не сможете продолжать работу без него.\nНажмите «Download», чтобы скачать и установить, или «Exit», чтобы закрыть приложение.')
        else:
            m.setWindowTitle('Доступно обновление')
            m.setText(f'Доступна новая версия: v{latest_ver}\n\nРекомендуется обновиться.')
        btn_download = m.addButton('Download', QMessageBox.AcceptRole)
        if is_critical:
            btn_exit = m.addButton('Exit', QMessageBox.RejectRole)
        else:
            btn_skip = m.addButton('Skip', QMessageBox.RejectRole)
        m.exec_()
        clicked = m.clickedButton()
        if clicked == btn_download:
            if hasattr(self, 'updater') and self.updater:
                try:
                    self.updater.close()
                except:
                    pass
            self.updater = DownloadWindow(download_url, latest_ver, sys.argv[0])
            if is_critical:
                self.setEnabled(False)
                self.updater.finished_signal.connect(lambda: QApplication.quit())
        elif is_critical and clicked == btn_exit:
            QApplication.quit()
        else:
            self._start_flow_safe()
        self._update_dialog_active = False

    def show_admin_menu(self):
        return ChatAppUIMixin.show_admin_menu(self)

    def handle_nick_click(self, url):
        return ChatAppDMMixin.handle_nick_click(self, url)

    def toggle_emoji_menu(self):
        return ChatAppUIMixin.toggle_emoji_menu(self)

    def show_settings(self):
        self.open_settings()

    def quit_app(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
        if hasattr(self, 'poller'):
            self.poller.running = False
            self.poller.quit()
            self.poller.wait(2000)
        QApplication.quit()