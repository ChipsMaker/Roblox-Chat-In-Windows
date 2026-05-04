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
        self.setMaximumWidth(320)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.username = username
        self.file_name = file_name
        self.file_id = file_id
        self.text = text
        self.crypto = crypto
        self.active_server = active_server
        self.downloader = None
        self.setStyleSheet('\n            FileWidget {\n                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n                                            stop:0 #2c2c2c, stop:1 #1e1e1e);\n                border: 1px solid #E2D189;\n                border-radius: 10px;\n                padding: 8px;\n            }\n            QToolTip {\n                background-color: #333;\n                color: #E2D189;\n                border: 1px solid #E2D189;\n                padding: 4px;\n                border-radius: 4px;\n            }\n        ')
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet('\n            background: #3a3a3a;\n            border-radius: 10px;\n            font-size: 30px;\n        ')
        ext = self.file_name.split('.')[-1].lower()
        icon_map = {'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'bmp': '🖼️', 'mp4': '🎬', 'mkv': '🎬', 'avi': '🎬', 'mp3': '🎵', 'wav': '🎵', 'ogg': '🎵', 'pdf': '📑'}
        self.icon_lbl.setText(icon_map.get(ext, '📎'))
        top_layout.addWidget(self.icon_lbl)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        self.file_name_lbl = QLabel(self.file_name)
        self.file_name_lbl.setStyleSheet('color: white; font-weight: bold; font-size: 13px; background: transparent; border: none;')
        self.file_name_lbl.setWordWrap(False)
        fm = QFontMetrics(self.file_name_lbl.font())
        elided = fm.elidedText(self.file_name, Qt.ElideRight, 190)
        self.file_name_lbl.setText(elided)
        info_layout.addWidget(self.file_name_lbl)
        self.size_lbl = QLabel('Размер: неизвестен')
        self.size_lbl.setStyleSheet('color: #aaa; font-size: 11px; background: transparent; border: none;')
        info_layout.addWidget(self.size_lbl)
        sender_lbl = QLabel(f'📤 {self.username}')
        sender_lbl.setStyleSheet('color: #E2D189; font-size: 11px; background: transparent; border: none;')
        info_layout.addWidget(sender_lbl)
        if self.text:
            text_lbl = QLabel(self.text)
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet('color: #ccc; font-size: 11px; background: transparent; border: none; padding-top: 2px;')
            info_layout.addWidget(text_lbl)
        top_layout.addLayout(info_layout, 1)
        self.action_btn = QPushButton()
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setFixedSize(40, 40)
        self.action_btn.setStyleSheet('\n            QPushButton {\n                background: #E2D189;\n                color: black;\n                border-radius: 8px;\n                font-size: 22px;\n                border: none;\n            }\n            QPushButton:hover {\n                background: #f5e6a8;\n            }\n            QPushButton:disabled {\n                background: #666;\n                color: #aaa;\n            }\n        ')
        self.action_btn.clicked.connect(self.on_action_clicked)
        top_layout.addWidget(self.action_btn)
        main_layout.addLayout(top_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('\n            QProgressBar {\n                background: rgba(255,255,255,10);\n                border-radius: 2px;\n                border: none;\n            }\n            QProgressBar::chunk {\n                background: #E2D189;\n                border-radius: 2px;\n            }\n        ')
        main_layout.addWidget(self.progress_bar)
        self.update_action_button()
        self.check_local_file()

    def update_action_button(self, state=None):
        if state == 'downloading':
            self.action_btn.setText('⏳')
            self.action_btn.setEnabled(False)
            self.action_btn.setToolTip('Идёт загрузка...')
        elif state == 'ready':
            self.action_btn.setText('📂')
            self.action_btn.setEnabled(True)
            self.action_btn.setToolTip('Открыть файл')
        else:
            self.action_btn.setText('⬇')
            self.action_btn.setEnabled(True)
            self.action_btn.setToolTip('Скачать через Acerum')

    def on_action_clicked(self):
        download_dir = self.get_download_dir()
        local_path = os.path.join(download_dir, self.file_name)
        if os.path.exists(local_path):
            self.open_file()
        else:
            self.start_download()

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
            self.update_action_button('ready')
        else:
            self.size_lbl.setText('Размер: неизвестен')
            self.update_action_button(None)

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
                return
        try:
            os.startfile(local_path)
        except OSError as e:
            if e.winerror == 1223:
                pass
            else:
                QMessageBox.warning(self, 'Ошибка открытия', f'Не удалось открыть файл:\n{str(e)}')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка открытия', f'Не удалось открыть файл:\n{str(e)}')

    def start_download(self):
        download_dir = self.get_download_dir()
        output_path = os.path.join(download_dir, self.file_name)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.update_action_button('downloading')
        url = f'{self.active_server}/acerum/download/{self.file_id}'

        def callback(done, total, speed, status=''):

            def update_ui():
                if total > 0:
                    percent = int(done / total * 100)
                    self.progress_bar.setValue(percent)
                if status == 'complete':
                    self.progress_bar.setVisible(False)
                    self.size_lbl.setText(f'Загружен: {human_readable_size(total)}')
                    self.update_action_button('ready')
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