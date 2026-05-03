import os, threading, requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .Acerum import AcerumSmartDownloader

def human_readable_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f'{size:.2f} {unit}'
        size /= 1024
    return f'{size:.2f} PB'

class FileWidget(QFrame):

    def __init__(self, username, file_name, file_id, text, crypto, active_server, parent=None):
        super().__init__(parent)
        self.username = username
        self.file_name = file_name
        self.file_id = file_id
        self.text = text
        self.crypto = crypto
        self.active_server = active_server
        self.downloader = None
        self.setStyleSheet('background: #2a2a2a; border-radius: 12px; margin: 5px; padding: 8px;')
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        user_lbl = QLabel(f'<b>{self.username}</b>')
        user_lbl.setStyleSheet('color: #E2D189; font-size: 12px;')
        layout.addWidget(user_lbl)
        if self.text:
            text_lbl = QLabel(self.text)
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet('color: #ccc; font-size: 11px;')
            layout.addWidget(text_lbl)
        file_frame = QFrame()
        file_frame.setStyleSheet('background: #1e1e1e; border-radius: 8px;')
        file_layout = QHBoxLayout(file_frame)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet('background: #333; border-radius: 6px; font-size: 32px;')
        ext = self.file_name.split('.')[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            self.icon_lbl.setText('🖼️')
        elif ext in ['mp4', 'mkv', 'avi']:
            self.icon_lbl.setText('🎬')
        elif ext in ['mp3', 'wav', 'ogg']:
            self.icon_lbl.setText('🎵')
        elif ext in ['pdf']:
            self.icon_lbl.setText('📑')
        else:
            self.icon_lbl.setText('📎')
        file_layout.addWidget(self.icon_lbl)
        info_layout = QVBoxLayout()
        name_lbl = QLabel(self.file_name)
        name_lbl.setStyleSheet('font-weight: bold; color: white;')
        self.size_lbl = QLabel('Размер: неизвестен')
        self.size_lbl.setStyleSheet('font-size: 10px; color: #aaa;')
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('QProgressBar::chunk { background: #E2D189; }')
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(self.size_lbl)
        info_layout.addWidget(self.progress_bar)
        file_layout.addLayout(info_layout, 1)
        btn_layout = QVBoxLayout()
        self.open_btn = QPushButton('Открыть')
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setStyleSheet('background: #4a4a4a; border-radius: 5px; padding: 4px;')
        self.open_btn.clicked.connect(self.open_file)
        self.download_btn = QPushButton('Скачать (Acerum)')
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet('background: #E2D189; color: black; font-weight: bold; border-radius: 5px; padding: 4px;')
        self.download_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.download_btn)
        file_layout.addLayout(btn_layout)
        layout.addWidget(file_frame)
        self.check_local_file()

    def get_download_dir(self):
        parent = self.window()
        if hasattr(parent, 'settings'):
            download_path = parent.settings.get('download_path')
            if download_path:
                return download_path
        return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

    def check_local_file(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if os.path.exists(local_path):
            self.size_lbl.setText(f'Уже загружен: {human_readable_size(os.path.getsize(local_path))}')
            self.download_btn.setText('Загружен')
            self.download_btn.setEnabled(False)
            self.download_btn.setStyleSheet('background: #666; color: #aaa;')
        else:
            self.download_btn.setEnabled(True)

    def open_file(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if not os.path.exists(local_path):
            QMessageBox.information(self, 'Файл не загружен', 'Сначала скачайте файл через Acerum.')
            return
        ext = self.file_name.split('.')[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                viewer = QLabel()
                viewer.setWindowFlags(Qt.Window)
                viewer.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                viewer.setWindowTitle(self.file_name)
                viewer.show()
            else:
                os.startfile(local_path)
        else:
            os.startfile(local_path)

    def start_download(self):
        download_dir = self.get_download_dir()
        output_path = os.path.join(download_dir, self.file_name)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_btn.setEnabled(False)
        self.download_btn.setText('Загрузка...')
        url = f'{self.active_server}/acerum/download/{self.file_id}'

        def callback(done, total, speed, status=''):

            def update_ui():
                if total > 0:
                    percent = int(done / total * 100)
                    self.progress_bar.setValue(percent)
                if status == 'complete':
                    self.progress_bar.setVisible(False)
                    self.download_btn.setText('Загружен')
                    self.download_btn.setEnabled(False)
                    self.size_lbl.setText(f'Загружен: {human_readable_size(total)}')
                    parent = self.window()
                    if hasattr(parent, 'show_toast'):
                        parent.show_toast(f'Файл сохранён: {self.file_name}')
                else:
                    speed_str = human_readable_size(speed) + '/s'
                    self.size_lbl.setText(f'{human_readable_size(done)} / {human_readable_size(total)}  {speed_str}')
            QTimer.singleShot(0, update_ui)

        def run():
            response = requests.get(url, stream=True)
            response.raise_for_status()
            encrypted_data = response.content
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            decrypted = self.crypto.aes.decrypt(nonce, ciphertext, None)
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            if callback:
                callback(len(decrypted), len(decrypted), 0, 'complete')
        threading.Thread(target=run, daemon=True).start()