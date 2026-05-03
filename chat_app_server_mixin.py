import time
import threading
import requests

class ChatAppServerMixin:

    def server_monitor_loop(self):
        while True:
            try:
                self.refresh_server_statuses()
                self.find_best_server()
            except:
                pass
            time.sleep(30)

    def find_best_server(self):
        best_url = self.active_server
        min_ping = 999.0

        def check(url):
            nonlocal min_ping, best_url
            try:
                start = time.time()
                res = requests.get(f'{url}/ping', timeout=5.0)
                if res.status_code == 200:
                    self.server_status[url] = True
                    latency = time.time() - start
                    if latency < min_ping:
                        min_ping = latency
                        best_url = url
                else:
                    self.server_status[url] = False
            except:
                self.server_status[url] = False
        threads = [threading.Thread(target=check, args=(url,)) for url in self.SERVER_URLS]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.1)
        if self.auto_server_mode:
            if not self.server_status.get(self.active_server) or self.active_server != best_url:
                print(f'🔄 Переключение на: {best_url}')
                self.active_server = best_url

    def refresh_server_statuses(self):
        threads = []
        results = {}

        def check_url(url):
            try:
                start_time = time.time()
                response = self.http_session.get(f'{url}/ping', timeout=1.2)
                if response.status_code == 200:
                    ms = int((time.time() - start_time) * 1000)
                    results[url] = (True, f'{ms}ms')
                else:
                    results[url] = (False, 'ERR')
            except:
                results[url] = (False, 'OFF')
        for url in self.SERVER_URLS:
            t = threading.Thread(target=check_url, args=(url,))
            t.daemon = True
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=1.3)
        for url, (stat, p_str) in results.items():
            self.server_status[url] = stat
            self.server_pings[url] = p_str
        if hasattr(self, 'ping_updated_signal'):
            self.ping_updated_signal.emit()

    def actual_ui_ping_update(self):
        if not hasattr(self, 'ui_ping_labels') or not self._dialog_is_active:
            return
        for url in self.SERVER_URLS:
            status = self.server_status.get(url, False)
            ping_text = self.server_pings.get(url, 'wait...')
            if url in self.ui_ping_labels:
                self.ui_ping_labels[url].setText(ping_text)
            if url in self.ui_status_circles:
                color = '#4CAF50' if status else '#ff5c5c'
                self.ui_status_circles[url].setStyleSheet(f'color: {color}; font-size: 16px;')