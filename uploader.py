import os
import time
import requests
import urllib3
import zstandard as zstd
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
    HAS_PROGRESS = True
except ImportError:
    HAS_PROGRESS = False

class AcerumSmartUploader:

    def __init__(self, server_url, file_path, crypto_tool=None):
        self.server_url = server_url
        self.file_path = file_path
        self.crypto = crypto_tool

    def upload(self, progress_callback=None):
        filename = os.path.basename(self.file_path)
        safe_filename = filename.encode('ascii', 'ignore').decode() or 'file'
        with open(self.file_path, 'rb') as f:
            data = f.read()
        if len(data) > 1024 * 1024:
            cctx = zstd.ZstdCompressor(level=10)
            data = cctx.compress(data)
        if self.crypto:
            nonce = os.urandom(12)
            payload = nonce + self.crypto.aes.encrypt(nonce, data, None)
        else:
            payload = data
        if not progress_callback or not HAS_PROGRESS:
            headers = {'User-Agent': 'Mozilla/5.0'}
            files = {'file': (safe_filename, payload, 'application/octet-stream')}
            r = requests.post(f'{self.server_url}/acerum/upload', files=files, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            return r.json()
        encoder = MultipartEncoder(fields={'file': (safe_filename, payload, 'application/octet-stream')})

        class AdaptiveMonitor(MultipartEncoderMonitor):

            def __init__(self, encoder, callback):
                super().__init__(encoder, callback)
                self.last_bytes = 0
                self.last_time = time.time()
                self.chunk_size = 8192
                self.speed_history = []

            def read(self, size=None):
                data = super().read(size)
                return data
        monitor = AdaptiveMonitor(encoder, callback=progress_callback)
        headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': monitor.content_type}
        r = requests.post(f'{self.server_url}/acerum/upload', data=monitor, headers=headers, timeout=30, verify=False)
        r.raise_for_status()
        return r.json()