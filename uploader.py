import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        if self.crypto:
            nonce = os.urandom(12)
            payload = nonce + self.crypto.aes.encrypt(nonce, data, None)
        else:
            payload = data
        headers = {'User-Agent': 'Mozilla/5.0'}
        files = {'file': (safe_filename, payload, 'application/octet-stream')}
        r = requests.post(f'{self.server_url}/acerum/upload', files=files, headers=headers, timeout=30, verify=False)
        r.raise_for_status()
        return r.json()