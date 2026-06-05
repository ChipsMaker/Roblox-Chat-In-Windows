import sys
import os
import PyQt5
from PyQt5.QtWidgets import QApplication
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'Qt5', 'plugins', 'platforms')
if os.path.exists(plugin_path):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
from src.chat_app import ChatApp

def main():
    app = QApplication(sys.argv)
    window = ChatApp()
    window.show()
    sys.exit(app.exec_())
if __name__ == '__main__':
    main()