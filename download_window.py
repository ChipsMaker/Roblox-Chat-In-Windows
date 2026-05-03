import os
import time
import threading
import subprocess
import requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class DownloadWindow(QWidget):

    def __init__(self, download_url, new_version, current_exe):
        super().__init__()
        self.download_url = download_url
        self.new_version = new_version
        self.current_exe = current_exe
        self.new_exe = self.current_exe + '.new'
        self.is_paused = False
        self.is_stopped = False
        self.oldPos = QPoint()
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 130)
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, 350, 130)
        self.frame.setStyleSheet('background: rgba(12, 12, 12, 240); border-radius: 12px; border: 1px solid rgba(226, 209, 137, 60);')
        layout = QVBoxLayout(self.frame)
        header = QHBoxLayout()
        self.title_lbl = QLabel(f'Обновление до v{self.new_version}')
        self.title_lbl.setStyleSheet("color: white; font-weight: bold; font-family: 'Segoe UI';")
        self.pause_btn = QPushButton('❚❚')
        self.pause_btn.setFixedSize(24, 24)
        self.pause_btn.setStyleSheet('color: #E2D189; background: transparent; border: none; font-size: 14px;')
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.close_btn = QPushButton('✕')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet('color: #ff5c5c; background: transparent; border: none; font-size: 16px;')
        self.close_btn.clicked.connect(self.stop_download)
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.pause_btn)
        header.addWidget(self.close_btn)
        layout.addLayout(header)
        self.lbl = QLabel('Подключение...')
        self.lbl.setStyleSheet("color: rgba(255,255,255,180); font-family: 'Segoe UI'; font-size: 11px;")
        layout.addWidget(self.lbl)
        self.pbar = QProgressBar()
        self.pbar.setStyleSheet('\n            QProgressBar { background: rgba(255,255,255,10); border-radius: 5px; text-align: center; color: transparent; height: 12px; }\n            QProgressBar::chunk { background: #E2D189; border-radius: 5px; }\n        ')
        layout.addWidget(self.pbar)
        self.show()
        threading.Thread(target=self.start_download, daemon=True).start()

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f'{bytes_per_sec:.1f} B/s'
        if bytes_per_sec < 1024 ** 2:
            return f'{bytes_per_sec / 1024:.1f} KB/s'
        if bytes_per_sec < 1024 ** 3:
            return f'{bytes_per_sec / 1024 ** 2:.1f} MB/s'
        return f'{bytes_per_sec / 1024 ** 3:.1f} GB/s'

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_btn.setText('▶' if self.is_paused else '❚❚')
        if self.is_paused:
            self.lbl.setText('Загрузка приостановлена')

    def stop_download(self):
        self.is_stopped = True
        self.close()
        if os.path.exists(self.new_exe):
            try:
                os.remove(self.new_exe)
            except:
                pass

    def start_download(self):
        try:
            r = requests.get(self.download_url, stream=True, timeout=10)
            total = int(r.headers.get('content-length', 0))
            with open(self.new_exe, 'wb') as f:
                done = 0
                start_time = time.time()
                last_done = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if self.is_stopped:
                        return
                    while self.is_paused:
                        if self.is_stopped:
                            return
                        time.sleep(0.5)
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        now = time.time()
                        if now - start_time >= 1.0:
                            speed = (done - last_done) / (now - start_time)
                            self.lbl.setText(f'Скорость: {self.format_speed(speed)} | Осталось: {(total - done) // 1024} KB')
                            last_done = done
                            start_time = now
                        self.pbar.setValue(int(done / total * 100))
            if not self.is_stopped:
                self.finalize_update(self.new_exe)
        except Exception as e:
            if not self.is_stopped:
                self.lbl.setText(f'Ошибка: {str(e)[:30]}')

    def finalize_update(self, new_exe):
        bat_path = 'updater.bat'
        current_pid = os.getpid()
        with open(bat_path, 'w', encoding='cp866') as f:
            f.write(f'@echo off\n')
            f.write(f'taskkill /f /pid {current_pid} >nul 2>&1\n')
            f.write(f':loop\n')
            f.write(f'timeout /t 1 /nobreak > nul\n')
            f.write(f'del /f /q "{self.current_exe}"\n')
            f.write(f'if exist "{self.current_exe}" goto loop\n')
            f.write(f'move /y "{new_exe}" "{self.current_exe}"\n')
            f.write(f'start "" "{self.current_exe}"\n')
            f.write(f'del "%~f0"\n')
        subprocess.Popen([bat_path], shell=True)
        os._exit(0)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()