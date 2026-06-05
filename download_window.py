import os
import time
import threading
import subprocess
import requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class DownloadWindow(QWidget):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, download_url, new_version, current_exe):
        super().__init__()
        self.download_url = download_url
        self.new_version = new_version
        self.current_exe = current_exe
        self.new_exe = self.current_exe + '.new'
        self.is_paused = False
        self.is_stopped = False
        self.oldPos = QPoint()
        self.progress_signal.connect(self._update_ui)
        self.finished_signal.connect(self._finalize)
        self.error_signal.connect(self._show_error)
        self.init_ui()
        self.show()
        threading.Thread(target=self._download_thread, daemon=True).start()

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

    def _download_thread(self):
        try:
            r = requests.get(self.download_url, stream=True, timeout=10)
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            done = 0
            last_done = 0
            start_time = time.time()
            with open(self.new_exe, 'wb') as f:
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
                        if now - start_time >= 0.5:
                            speed = (done - last_done) / (now - start_time)
                            percent = int(done / total * 100) if total > 0 else 0
                            status = f'Скорость: {self.format_speed(speed)} | Осталось: {(total - done) // 1024} KB' if total > 0 else f'Загружено: {done // 1024} KB'
                            self.progress_signal.emit(percent, status)
                            last_done = done
                            start_time = now
            if not self.is_stopped:
                self.finished_signal.emit(self.new_exe)
        except Exception as e:
            if not self.is_stopped:
                self.error_signal.emit(str(e))

    @pyqtSlot(int, str)
    def _update_ui(self, percent, status_text):
        self.pbar.setValue(percent)
        self.lbl.setText(status_text)

    @pyqtSlot(str)
    def _show_error(self, err):
        self.lbl.setText(f'Ошибка: {err[:40]}')
        self.pbar.setValue(0)

    @pyqtSlot(str)
    def _finalize(self, new_exe):
        import tempfile, shutil, traceback, glob
        log_file = os.path.join(tempfile.gettempdir(), 'updater_debug.log')

        def log(msg):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f'{time.time()} - {msg}\n')
        log('=== _finalize START ===')
        self.lbl.setText('Перезапуск приложения...')
        self.pause_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        QApplication.processEvents()
        current = os.path.abspath(self.current_exe)
        new = os.path.abspath(new_exe)
        old = current + '.old'
        log(f'current={current}, new={new}, old={old}')
        try:
            if os.path.exists(old):
                os.remove(old)
                log('Removed old')
            os.rename(current, old)
            log('rename current->old OK')
        except Exception as e:
            log(f'rename error: {e}')
            try:
                shutil.move(current, old)
                log('move current->old OK')
            except Exception as e2:
                log(f'move error: {e2}')
                self._show_error(f'Не удалось переименовать: {e}')
                return
        try:
            os.rename(new, current)
            log('rename new->current OK')
        except Exception as e:
            log(f'rename new error: {e}')
            try:
                shutil.move(new, current)
                log('move new->current OK')
            except Exception as e2:
                log(f'move new error: {e2}')
                try:
                    os.rename(old, current)
                    log('rollback OK')
                except Exception as rb:
                    log(f'rollback error: {rb}')
                self._show_error(f'Не удалось переместить файл: {e}')
                return
        log('Files renamed successfully')
        temp_dir = tempfile.gettempdir()
        log(f'Cleaning old _MEI* folders in {temp_dir}')
        for folder in glob.glob(os.path.join(temp_dir, '_MEI*')):
            try:
                shutil.rmtree(folder, ignore_errors=True)
                log(f'Removed old temp folder: {folder}')
            except Exception as e:
                log(f'Failed to remove {folder}: {e}')
        clean_env = {}
        allowed_keys = ['PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'COMSPEC', 'WINDIR', 'ProgramFiles', 'ProgramFiles(x86)', 'CommonProgramFiles', 'HOMEDRIVE', 'HOMEPATH', 'OS', 'PROCESSOR_ARCHITECTURE']
        for key in allowed_keys:
            if key in os.environ:
                clean_env[key] = os.environ[key]
        for key in list(clean_env.keys()):
            if key.startswith('_PYI_') or key.startswith('PYTHON'):
                del clean_env[key]
        log(f'Clean environment created with keys: {list(clean_env.keys())}')
        bat_path = os.path.join(temp_dir, 'run_update.bat')
        try:
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(f'@echo off\n        timeout /t 2 /nobreak > nul\n        start "" "{current}"\n        timeout /t 3 /nobreak > nul\n        del "{old}" 2> nul\n        del "%~f0"\n        ')
            log(f'Bat script written to {bat_path}')
        except Exception as e:
            log(f'Failed to write bat script: {e}')
            self._show_error(f'Не удалось создать bat-скрипт: {e}')
            return
        log('Launching bat script with clean environment')
        try:
            proc = subprocess.Popen(['cmd.exe', '/c', bat_path], env=clean_env, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
            log(f'Bat script launched, PID={proc.pid}')
            time.sleep(1.5)
        except Exception as e:
            log(f'Exception launching bat: {e}')
            log(traceback.format_exc())
            self._show_error(f'Не удалось запустить скрипт: {e}')
            return
        log('Exiting old app')
        QApplication.quit()
        os._exit(0)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()