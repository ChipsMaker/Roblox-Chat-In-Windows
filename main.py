import sys
import os
import PyQt5
from PyQt5.QtWidgets import QApplication, QMessageBox
from .critical_update import check_critical_update
from .download_window import DownloadWindow
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'Qt5', 'plugins', 'platforms')
if os.path.exists(plugin_path):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

def main():
    app = QApplication(sys.argv)
    critical, new_ver, download_url = check_critical_update()
    if critical:
        msg = QMessageBox()
        msg.setWindowTitle('Критическое обновление')
        msg.setText(f'Доступна обязательная новая версия: v{new_ver}\n\nЗапуск чата невозможен без обновления.\nПожалуйста, скачайте и установите последнюю версию.')
        msg.setIcon(QMessageBox.Warning)
        btn_update = msg.addButton('Скачать обновление', QMessageBox.AcceptRole)
        btn_exit = msg.addButton('Выход', QMessageBox.RejectRole)
        msg.exec_()
        if msg.clickedButton() == btn_update:
            updater = DownloadWindow(download_url, new_ver, sys.argv[0])
            app.exec_()
        sys.exit(0)
    from .chat_app import ChatApp
    window = ChatApp()
    window.show()
    sys.exit(app.exec_())
if __name__ == '__main__':
    main()