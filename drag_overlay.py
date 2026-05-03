from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

class DragOverlay(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(12, 12, 12, 180))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
        pen = QPen(QColor(226, 209, 137), 2, Qt.DashLine)
        painter.setPen(pen)
        rect = self.rect().adjusted(15, 15, -15, -15)
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(QColor(226, 209, 137))
        painter.setFont(QFont('Segoe UI', 12, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, '🚀 Перетащите файлы сюда')