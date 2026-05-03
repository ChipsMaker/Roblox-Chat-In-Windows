import time
import requests
from PyQt5.QtCore import QThread, pyqtSignal

class NetworkWorker(QThread):
    new_messages = pyqtSignal(list)
    join_request = pyqtSignal(str, str)
    access_approved = pyqtSignal()
    typing_updated = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__()
        self.p = parent
        self.running = True

    def run(self):
        while self.running:
            if not self.p.room_code:
                time.sleep(1)
                continue
            try:
                res = requests.get(f'{self.p.active_server}/sync', params={'room_code': self.p.room_code, 'last_time': self.p.last_sync}, timeout=5).json()
                if res.get('messages'):
                    self.new_messages.emit(res['messages'])
                if not self.p.is_in_chat:
                    check = requests.get(f'{self.p.active_server}/check_access', params={'room_code': self.p.room_code, 'user_uuid': self.p.user_uuid}, timeout=3).json()
                    if check.get('status') == 'approved':
                        self.access_approved.emit()
                reqs = requests.get(f'{self.p.active_server}/get_requests', params={'room_code': self.p.room_code}, timeout=3).json()
                for uid, name in reqs.items():
                    self.join_request.emit(uid, name)
                t_res = requests.get(f'{self.p.active_server}/get_typing', params={'room_code': self.p.room_code, 'exclude_uuid': self.p.user_uuid}, timeout=2).json()
                self.typing_updated.emit(t_res.get('active', []))
            except:
                pass
            time.sleep(1.5)