import os
import sys
import time
import argparse
import threading
import queue as queue_module
import requests
TEMP_DIR = '.acerum_parts'

def human_readable_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f'{size:.2f} {unit}'
        size /= 1024
    return f'{size:.2f} PB'

class AcerumSmartDownloader:

    def __init__(self, url: str, output: str=None, max_threads: int=32, progress_callback=None):
        self.url = url
        self.output = output or self._extract_filename(url)
        self.max_threads = max_threads
        self.block_size = 1024 * 1024
        self.min_speed_per_thread = 1024 * 1024
        self.lock = threading.Lock()
        self.downloaded_bytes = 0
        self.stop_event = threading.Event()
        self.progress_callback = progress_callback

    @staticmethod
    def _extract_filename(url: str) -> str:
        fname = url.rstrip('/').split('/')[-1]
        return fname if fname else 'downloaded_file'

    def _get_file_info(self):
        with requests.head(self.url, allow_redirects=True, timeout=15) as resp:
            resp.raise_for_status()
            accept_ranges = resp.headers.get('Accept-Ranges', '').lower()
            content_length = resp.headers.get('Content-Length')
            if content_length:
                size = int(content_length)
            else:
                size = None
                accept_ranges = 'none'
            return (size, accept_ranges == 'bytes')

    def _download_single(self):
        if self.progress_callback:
            self.progress_callback(0, 1, 0, 'starting')
        with requests.get(self.url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            start_time = time.time()
            with open(self.output, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.progress_callback:
                            speed = downloaded / (time.time() - start_time) if time.time() - start_time > 0 else 0
                            self.progress_callback(downloaded, total, speed)
        if self.progress_callback:
            self.progress_callback(downloaded, total, 0, 'complete')

    def _download_block(self, start: int, end: int, block_index: int):
        headers = {'Range': f'bytes={start}-{end}'}
        part_path = os.path.join(TEMP_DIR, f'part_{block_index:06d}')
        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(part_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            with self.lock:
                                self.downloaded_bytes += len(chunk)
        except Exception as e:
            print(f'\nBlock {block_index} error: {e}')
            self.stop_event.set()
            raise

    def _worker(self, block_queue: queue_module.Queue):
        while not self.stop_event.is_set():
            try:
                start, end, block_index = block_queue.get(timeout=1)
            except queue_module.Empty:
                continue
            self._download_block(start, end, block_index)
            block_queue.task_done()

    def _merge_blocks(self, total_blocks: int, output_path: str):
        with open(output_path, 'wb') as outfile:
            for i in range(total_blocks):
                part_path = os.path.join(TEMP_DIR, f'part_{i:06d}')
                with open(part_path, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(part_path)
        os.rmdir(TEMP_DIR)

    def download(self):
        size, supports_ranges = self._get_file_info()
        if not supports_ranges or size is None or size == 0:
            return self._download_single()
        os.makedirs(TEMP_DIR, exist_ok=True)
        total_blocks = (size + self.block_size - 1) // self.block_size
        block_queue = queue_module.Queue()
        for i in range(total_blocks):
            start = i * self.block_size
            end = min(start + self.block_size - 1, size - 1)
            block_queue.put((start, end, i))
        initial_threads = max(1, min(total_blocks, self.max_threads))
        threads = []
        for _ in range(initial_threads):
            t = threading.Thread(target=self._worker, args=(block_queue,))
            t.start()
            threads.append(t)
        start_time = time.time()
        last_callback_time = 0
        while not self.stop_event.is_set():
            time.sleep(0.5)
            with self.lock:
                current_downloaded = self.downloaded_bytes
            if self.progress_callback and (time.time() - last_callback_time > 0.5 or current_downloaded >= size):
                speed = current_downloaded / (time.time() - start_time) if time.time() - start_time > 0 else 0
                self.progress_callback(current_downloaded, size, speed)
                last_callback_time = time.time()
            if current_downloaded >= size:
                self.stop_event.set()
                break
            if len(threads) < self.max_threads:
                elapsed = time.time() - start_time
                if elapsed > 2:
                    speed_per_thread = current_downloaded / elapsed / len(threads)
                    if speed_per_thread < self.min_speed_per_thread:
                        t = threading.Thread(target=self._worker, args=(block_queue,))
                        t.start()
                        threads.append(t)
        for t in threads:
            t.join()
        self._merge_blocks(total_blocks, self.output)
        if self.progress_callback:
            self.progress_callback(size, size, 0, 'complete')
        print(f'\nDownload complete: {self.output}')