import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class Crypto:

    def __init__(self, room_key: str):
        self.key = hashlib.sha256(room_key.encode()).digest()
        self.aes = AESGCM(self.key)

    def enc(self, text: str) -> str:
        nonce = os.urandom(12)
        return base64.b64encode(nonce + self.aes.encrypt(nonce, text.encode(), None)).decode()

    def dec(self, data: str) -> str | None:
        try:
            raw = base64.b64decode(data)
            return self.aes.decrypt(raw[:12], raw[12:], None).decode()
        except Exception:
            return None