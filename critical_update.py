import requests
import re
from .config import VERSION, GITHUB_REPO

def check_critical_update():
    try:
        resp = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest', timeout=5)
        resp.raise_for_status()
        release = resp.json()
        tag = release.get('tag_name', '')
        match = re.match('v?(\\d+\\.\\d+\\.\\d+)', tag)
        if not match:
            return (False, None, None)
        latest_ver = match.group(1)
        if latest_ver <= VERSION:
            return (False, None, None)
        is_critical = tag.endswith('_critical')
        if is_critical:
            assets = release.get('assets', [])
            if not assets:
                return (False, None, None)
            download_url = assets[0].get('browser_download_url')
            return (True, latest_ver, download_url)
        return (False, None, None)
    except Exception:
        return (False, None, None)