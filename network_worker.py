import time
import requests
from PyQt5.QtCore import QThread, pyqtSignal, QMetaObject, Qt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SyncPoller(QThread):
    new_messages = pyqtSignal(list)
    join_request = pyqtSignal(str, str)
    access_approved = pyqtSignal()
    typing_updated = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__()
        self.p = parent
        self.running = True
        self.session = requests.Session()
        retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504], allowed_methods=['GET', 'POST'], raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.poll_interval = 0.5

    def run(self):
        consecutive_errors = 0
        last_requests_check = 0
        last_typing_check = 0
        while self.running:
            if getattr(self.p, 'room_code', None) is None:
                time.sleep(0.5)
                continue
            now = time.time()
            try:
                res = self.session.get(f'{self.p.active_server}/sync', params={'room_code': self.p.room_code, 'last_time': self.p.last_sync, 'user_uuid': self.p.user_uuid}, headers={'Connection': 'close'}, timeout=5).json()
                if res.get('messages'):
                    self.new_messages.emit(res['messages'])
                if not self.p.is_in_chat:
                    check = self.session.get(f'{self.p.active_server}/check_access', params={'room_code': self.p.room_code, 'user_uuid': self.p.user_uuid}, headers={'Connection': 'close'}, timeout=5).json()
                    if check.get('status') == 'approved':
                        self.access_approved.emit()
                if self.p.is_creator and now - last_requests_check > 6.5:
                    last_requests_check = now
                    reqs = self.session.get(f'{self.p.active_server}/get_requests', params={'room_code': self.p.room_code}, headers={'Connection': 'close'}, timeout=5).json()
                    for uid, name in reqs.items():
                        self.join_request.emit(uid, name)
                if now - last_typing_check > 1.0:
                    last_typing_check = now
                    t_res = self.session.get(f'{self.p.active_server}/get_typing', params={'room_code': self.p.room_code, 'exclude_uuid': self.p.user_uuid}, headers={'Connection': 'close'}, timeout=5).json()
                    self.typing_updated.emit(t_res.get('active', []))
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    try:
                        QMetaObject.invokeMethod(self.p, 'on_connection_lost', Qt.QueuedConnection)
                    except Exception as invoke_err:
                        pass
                    time.sleep(5)
                    consecutive_errors = 0
                else:
                    time.sleep(1)
            time.sleep(self.poll_interval)