from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

class UploadTaskWidget(QFrame):

    def __init__(self, filename, file_path, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.file_path = file_path
        self.cancelled = False
        self.is_uploading = False
        self.cancel_callback = None
        self.setMaximumWidth(300)
        self.setStyleSheet('background: rgba(30,30,30,200); border-radius:8px; padding:8px;')
        self.init_ui()
        self.set_pending()
        self.progress_signal.connect(self._safe_set_progress)
        self.error_signal.connect(self._safe_set_error)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        header = QHBoxLayout()
        self.name_lbl = QLabel(self.filename)
        self.name_lbl.setStyleSheet('color:#E2D189; font-weight:bold; font-size:11px;')
        header.addWidget(self.name_lbl)
        header.addStretch()
        self.cancel_btn = QPushButton('✕')
        self.cancel_btn.setFixedSize(18, 18)
        self.cancel_btn.setStyleSheet('QPushButton{background:transparent; border:none; font-weight:bold; color:#ff5c5c; font-size:14px;} QPushButton:hover{color:#c0392b;}')
        self.cancel_btn.clicked.connect(self.handle_cancel)
        header.addWidget(self.cancel_btn)
        layout.addLayout(header)
        self.progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('QProgressBar{ background:rgba(255,255,255,10); border-radius:3px; } QProgressBar::chunk{ background:#E2D189; border-radius:3px; }')
        self.progress_layout.addWidget(self.progress_bar, 1)
        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet('color:#aaa; font-size:9px;')
        self.progress_layout.addWidget(self.status_lbl)
        layout.addLayout(self.progress_layout)

    def set_pending(self):
        self.is_uploading = False
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_lbl.setText('Нажмите Отправить')
        self.name_lbl.setStyleSheet('color:#E2D189; font-weight:bold; font-size:11px;')

    def set_uploading(self):
        self.is_uploading = True
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_lbl.setText('Загрузка...')
        self.name_lbl.setStyleSheet('color:#E2D189; font-weight:bold; font-size:11px;')
        self.set_progress(0, None)

    def set_finished(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_lbl.setText('Загружено')
        self.name_lbl.setStyleSheet('color:#4CAF50; font-weight:bold; font-size:11px;')
        self.progress_bar.update()
        self.status_lbl.update()
        self.name_lbl.update()

    def set_error(self, msg):
        self.error_signal.emit(msg)

    def _safe_set_error(self, msg):
        self.status_lbl.setText(msg)
        self.name_lbl.setStyleSheet('color:#ff5c5c; font-weight:bold; font-size:11px;')

    def set_progress(self, percent, speed=None):
        self.progress_signal.emit(percent, speed)

    def _safe_set_progress(self, percent, speed=None):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        if speed is not None:
            self.status_lbl.setText(f'Загрузка: {percent}% — {self._format_speed(speed)}')
        else:
            self.status_lbl.setText(f'Загрузка: {percent}%')

    @staticmethod
    def _format_speed(bytes_per_sec):
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if bytes_per_sec < 1024:
                return f'{bytes_per_sec:.1f} {unit}'
            bytes_per_sec /= 1024
        return f'{bytes_per_sec:.1f} TB/s'

    def handle_cancel(self):
        if self.is_uploading:
            self.cancelled = True
            self.cancel_btn.setEnabled(False)
            self.status_lbl.setText('Отменено')
            self.name_lbl.setStyleSheet('color:#ff5c5c; font-weight:bold; font-size:11px;')
            QTimer.singleShot(2000, self.deleteLater)
        else:
            if self.cancel_callback:
                self.cancel_callback(self)
            self.deleteLater()