import sys
import os
import ctypes
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .drag_overlay import DragOverlay

class ChatAppUIMixin:

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(400, 320)
        self.move(25, 65)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.main_frame = QFrame()
        self.main_frame.setObjectName('MainFrame')
        self.main_frame.setStyleSheet('\n            #MainFrame {\n                background-color: rgba(12, 12, 12, 180);\n                border-radius: 14px;\n                border: 1px solid rgba(255, 255, 255, 18);\n            }\n        ')
        flay = QVBoxLayout(self.main_frame)
        flay.setContentsMargins(12, 8, 12, 12)
        header = QHBoxLayout()
        self.info_lbl = QLabel(f'v{self.VERSION}')
        self.info_lbl.setStyleSheet('color: rgba(255,255,255,80); font-size: 10px;')
        self.admin_btn = QPushButton('🛡️')
        self.admin_btn.setFixedSize(22, 22)
        self.admin_btn.setStyleSheet('color: rgba(255,255,255,150); background: transparent; border: none; font-size: 14px;')
        self.admin_btn.clicked.connect(self.show_admin_menu)
        self.sett_btn = QPushButton('⚙')
        self.sett_btn.setFixedSize(22, 22)
        self.sett_btn.setStyleSheet('color: rgba(255,255,255,150); background: transparent; border: none; font-size: 14px;')
        self.sett_btn.clicked.connect(self.open_settings)
        self.minimize_btn = QPushButton('—')
        self.minimize_btn.setFixedSize(22, 22)
        self.minimize_btn.setStyleSheet('color: rgba(255,255,255,150); background: transparent; border: none; font-size: 16px; font-weight: bold;')
        self.minimize_btn.clicked.connect(self.minimize_to_tray)
        self.close_btn = QPushButton('✕')
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setStyleSheet('color: rgba(255,255,255,150); background: transparent; border: none; font-size: 16px; font-weight: bold;')
        self.close_btn.clicked.connect(self.quit_app)
        header.addWidget(self.info_lbl)
        header.addStretch()
        header.addWidget(self.admin_btn)
        header.addSpacing(5)
        header.addWidget(self.sett_btn)
        header.addSpacing(5)
        header.addWidget(self.minimize_btn)
        header.addSpacing(5)
        header.addWidget(self.close_btn)
        flay.addLayout(header)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet('background: transparent; border: none;')
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet('background: transparent;')
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(4)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(self.chat_widget)
        flay.addWidget(self.chat_scroll, 1)
        self.typing_lbl = QLabel('')
        self.typing_lbl.setStyleSheet('color: rgba(255,255,255,100); font-size: 10px; margin-left: 10px;')
        flay.addWidget(self.typing_lbl)
        self.input_container = QFrame()
        self.input_container.setFixedHeight(38)
        self.input_container.setStyleSheet('background-color: rgba(0, 0, 0, 190); border-radius: 9px;')
        input_lay = QHBoxLayout(self.input_container)
        input_lay.setContentsMargins(8, 0, 5, 0)
        self.attach_btn = QPushButton('🔗')
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setStyleSheet('color: #E2D189; background: transparent; border: none; font-size: 20px;')
        self.attach_btn.clicked.connect(self.select_file)
        input_lay.addWidget(self.attach_btn)
        self.emoji_btn = QPushButton('☺')
        self.emoji_btn.setFixedSize(32, 32)
        self.emoji_btn.setStyleSheet('color: #E2D189; background: transparent; border: none; font-size: 20px;')
        self.emoji_btn.clicked.connect(self.toggle_emoji_menu)
        input_lay.addWidget(self.emoji_btn)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Нажмите для ввода...')
        self.input_field.setStyleSheet('color: white; background: transparent; border: none; font-size: 13px;')
        self.input_field.returnPressed.connect(self.send_msg)
        self.input_field.textChanged.connect(self.on_input_changed)
        input_lay.addWidget(self.input_field)
        self.send_btn = QPushButton('➤')
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet('color: white; background: transparent; border: none; font-size: 28px; padding-bottom: 4px;')
        self.send_btn.clicked.connect(self.send_msg)
        input_lay.addWidget(self.send_btn)
        flay.addWidget(self.input_container)
        layout.addWidget(self.main_frame)
        self.drag_overlay = DragOverlay(self.main_frame)
        self.drag_overlay.setGeometry(self.main_frame.rect())
        self.current_dm_target = None
        self.pending_tasks = []
        self.request_focus_signal.connect(self.force_activate)

        def global_hotkey_handler():
            if self.settings.get('slash_activation', True):
                self.request_focus_signal.emit()
        for key in ['/', 'numpad /', 'divide', 181, 53]:
            try:
                import keyboard
                keyboard.add_hotkey(key, global_hotkey_handler, suppress=False)
            except:
                continue
        QTimer.singleShot(200, self.start_flow)
        QTimer.singleShot(1000, self.check_updates)

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        if hasattr(self, 'drag_overlay'):
            self.drag_overlay.setGeometry(self.main_frame.rect())

    def toggle_emoji_menu(self):
        menu = QMenu(self)
        menu.setFixedSize(300, 250)
        menu.setStyleSheet('QMenu { background: #111; border: 1px solid #E2D189; border-radius: 8px; }')
        scroll = QScrollArea(menu)
        scroll.setWidgetResizable(True)
        scroll.setFocusPolicy(Qt.NoFocus)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bar = scroll.verticalScrollBar()
        bar.setStyleSheet('QScrollBar:vertical { border:none; background:#111; width:8px; } QScrollBar::handle:vertical { background:#E2D189; min-height:20px; border-radius:4px; } QScrollBar::handle:vertical:hover { background:#f5e6a8; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:none; }')
        container = QWidget()
        container.setStyleSheet('background-color: #111; color: white;')
        grid = QGridLayout(container)
        grid.setSpacing(2)
        grid.setContentsMargins(5, 5, 5, 5)
        all_emojis = '😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙😚☺️🙂🤗🤩🤔🤨😐😑😶🙄😏😣😥😮🤐😯😪😫🥱😴😌😛😜😝🤤😒😓😔😕🙃🤑😲☹️🙁😖😞😟😤😢😭😦😧😨😩🤯😬😰😱🥵🥶😳🤪😵😡😠🤬😷🤒🤕🤢🤮🤧😇🥳🥺🤠🤡🤥🤫🤭🧐🤓😈👿👹👺💀👻👽🤖💩😺😸😹😻😼😽🙀😿😾🙈🙉🙊💥🔥💫⭐🌟✨⚡☄️☀️🌤️⛅🌥️🌦️☁️🌧️⛈️🌩️⚡❄️☃️⛄🌊💨🌬️🌫️🌪️🌡️🍇🍈🍉🍊🍋🍌🍍🥭🍎🍏🍑🍒🍓🥝🍅🥥🥑🥦🥬🥒🌶️🌽🥕🥔🍠🥐🍞🥖🥨🥯🥞🧀🍖🥩🍗🥓🍔🍟🍕🌭🥪🌮🌯🥙🍳🥘🍲🥣🥗🍿🧂🥫⚽🏀🏈⚾🥎🎾🏐🏉🎱🏓🏸🥅🏒🏑🏏🥍🏹🎣🤿🥊🥋⛸️🎿🛷🛹🚣🏊🏄🏌️🏇🚴🚵🏎️🏍️🤸🤼🤽🤾🧗🧘🕹️🎮🕹️🎰🎲🎯🎳🎮👾🎹🎸🎺🎻🥁📱💻🖥️⌨️🖱️🖨️💽💾💿📀🎥🎞️📽️🎬🎭🎫🎟️🏆🏅🥇🥈🥉📢📣🔔🔕🎼🎵🎶🎙️👂👀👁️❤️🧡💛💚💙💜🖤🤍🤎💔❣️💕💞💓💗💖💘💝💟☮️✝️☪️🕉️☸️✡️🔯🕎☯️☦️🛐⛎♈♉♊♋♌♍♎♏♐♑♒♓🆔⚛️🉑☢️☣️📴📳🈶🈚🈸🈺🈷️✴️🆚💮🉐㊙️㊗️🈴🈵🈹🈺🌓🌔🌕🌖🌗🌘🌙🌚🌛🌜🌡️☀️⭐🌟☁️⛅🌀🌈🌂☔⚡❄️🚀🛸🛰️🌑🪐🌠🌌⚓⚓🛸🛶🛸🚜🚑🚒🚜⚙️⚒️🛠️⛏️🔩🔧🔩⛓️🔫💣🧨🔪🗡️⚔️🛡️🚬⚰️⚱️🏺🔮📿🧿💈⚗️🔭🔬🕳️💊💉🩸🩹🏷️🔖🧹🧺🧼🪒🚿🛀🧼'
        columns = 7
        for i, char in enumerate(all_emojis):
            btn = QPushButton(char)
            btn.setFixedSize(35, 35)
            btn.setStyleSheet('QPushButton{ background:transparent; border:none; font-size:20px; color:white; border-radius:5px; } QPushButton:hover{ background:rgba(226,209,137,40); }')
            btn.clicked.connect(lambda _, c=char: [self.input_field.insert(c), menu.close()])
            grid.addWidget(btn, i // columns, i % columns)
        scroll.setWidget(container)
        menu_layout = QVBoxLayout(menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.addWidget(scroll)
        pos = self.emoji_btn.mapToGlobal(QPoint(-270, -255))
        menu.exec_(pos)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Выберите файл для отправки')
        if file_path:
            if os.path.getsize(file_path) > 400 * 1024 * 1024:
                QMessageBox.warning(self, 'Acerum', 'Файл слишком большой (макс. 400 МБ)')
                return
            self.add_pending_file_task(file_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drag_overlay.show()

    def dragLeaveEvent(self, event):
        self.drag_overlay.hide()

    def dropEvent(self, event):
        self.drag_overlay.hide()
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        for path in files:
            if os.path.isfile(path) and os.path.getsize(path) <= 400 * 1024 * 1024:
                self.add_pending_file_task(path)
            else:
                QMessageBox.warning(self, 'Acerum', 'Файл слишком большой (макс. 400 МБ)')

    def scroll_chat_to_bottom(self):
        QTimer.singleShot(0, lambda: self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum()))

    def show_admin_menu(self):
        if not self.room_code:
            QMessageBox.information(self, 'Инфо', 'Вы не в комнате')
            return
        menu = QMenu(self)
        menu.setStyleSheet('background: #111; color: white; border: 1px solid #E2D189;')
        menu.addAction(f'ID комнаты: {self.room_code[:10]}...').setEnabled(False)
        menu.addSeparator()
        if hasattr(self, 'current_dm_target') and self.current_dm_target:
            reset_dm = menu.addAction('❌ Выйти из режима ЛС')
            reset_dm.triggered.connect(self.reset_dm_mode)
        exit_act = menu.addAction('🚪 Покинуть чат')
        exit_act.triggered.connect(self.main_menu)
        menu.exec_(QCursor.pos())

    def reset_dm_mode(self):
        self.current_dm_target = None
        self.input_field.setPlaceholderText('Нажмите для ввода...')

    def force_activate(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self.previous_hwnd = user32.GetForegroundWindow()
            if self.previous_hwnd == int(self.winId()):
                self.previous_hwnd = None
            foreground_thread_id = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), 0)
            current_thread_id = kernel32.GetCurrentThreadId()
            if foreground_thread_id != current_thread_id:
                user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
                hwnd = int(self.winId())
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)
        except Exception as e:
            print(f'Ошибка привязки ввода: {e}')
        QTimer.singleShot(100, self.input_field.setFocus)

    def restore_focus(self):
        if hasattr(self, 'previous_hwnd') and self.previous_hwnd:
            try:
                user32 = ctypes.windll.user32
                if user32.IsWindow(self.previous_hwnd) and self.previous_hwnd != int(self.winId()):
                    user32.SetForegroundWindow(self.previous_hwnd)
            except:
                pass
            finally:
                self.previous_hwnd = None

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()