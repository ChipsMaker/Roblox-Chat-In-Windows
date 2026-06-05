import secrets
import base64
import hashlib
SERVERS_DATA = {...}
SERVER_URLS = list(SERVERS_DATA.keys())
VERSION = '1.0.0'
GITHUB_REPO = 'ChipsMaker/Roblox-Chat-In-Windows'

def generate_room_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(9)).decode().rstrip('=')

def room_code_from_key(room_key: str) -> str:
    return hashlib.sha256(room_key.encode()).hexdigest()[:32]