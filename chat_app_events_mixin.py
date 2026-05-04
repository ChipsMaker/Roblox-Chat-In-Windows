import json, os, threading, requests, time
from PyQt5.QtCore import QTimer, pyqtSlot, Q_ARG, Qt, QMetaObject
from .uploader import AcerumSmartUploader
from .file_widget import FileWidget
from .task_widget import UploadTaskWidget

class ChatAppEventsMixin:

    def on_new_messages(self, messages):
        for m in messages:
            if m.get('sender_uuid') == self.user_uuid:
                self.last_sync = max(self.last_sync, m.get('time', 0))
                continue
            user_name = self.crypto.dec(m.get('user'))
            if not user_name:
                continue
            if m.get('is_file'):
                try:
                    file_data = self.crypto.dec(m.get('data'))
                    if file_data:
                        info = json.loads(file_data)
                        file_id = m.get('file_id')
                        if file_id:
                            widget = FileWidget(user_name, info.get('fn', 'file'), file_id, '', self.crypto, self.active_server)
                            self.chat_layout.addWidget(widget)
                            self.scroll_chat_to_bottom()
                        else:
                            self.add_system_message(f'📎 {user_name} отправил файл без ID: {info.get('fn', 'file')}', '#E2D189')
                    else:
                        self.add_system_message(f'📎 {user_name} отправил зашифрованный файл', '#E2D189')
                except:
                    pass
            else:
                text = self.crypto.dec(m.get('data'))
                if text:
                    self.add_chat_message(user_name, text, m['sender_uuid'])
                    if not self.isVisible():
                        self.show_notification(user_name, text)
            self.last_sync = max(self.last_sync, m.get('time', 0))

    def add_pending_file_task(self, path):
        filename = os.path.basename(path)
        task = UploadTaskWidget(filename, path)
        task.cancel_callback = lambda t: self.pending_tasks.remove(t) if t in self.pending_tasks else None
        self.pending_tasks.append(task)
        self.chat_layout.addWidget(task)
        self.scroll_chat_to_bottom()

    def send_msg(self):
        text = self.input_field.text().strip()
        my_name = self.settings.get('name', 'Я')
        tasks_to_process = [t for t in self.pending_tasks if not t.cancelled and (not t.is_uploading)]
        self.pending_tasks.clear()
        if not tasks_to_process and text:
            self.add_chat_message(my_name, text, self.user_uuid)
            threading.Thread(target=self.network_send_text, args=(text,), daemon=True).start()
            self.input_field.clear()
            QTimer.singleShot(100, self.restore_focus)
            return
        if tasks_to_process:
            self.input_field.clear()
            total_files = len(tasks_to_process)
            state = {'done': 0, 'text_sent': False}

            def on_file_done():
                state['done'] += 1
                if state['done'] >= total_files:
                    if text and (not state['text_sent']):
                        state['text_sent'] = True
                        self.add_chat_message(my_name, text, self.user_uuid)
                        threading.Thread(target=self.network_send_text, args=(text,), daemon=True).start()
                    QTimer.singleShot(100, self.restore_focus)
            for task in tasks_to_process:
                task.set_uploading()
                threading.Thread(target=self._upload_file, args=(task, on_file_done), daemon=True).start()
        else:
            QTimer.singleShot(100, self.restore_focus)

    @pyqtSlot(object, object)
    def _handle_upload_success(self, task, result):
        self._on_upload_success(task, result)

    @pyqtSlot(object, str)
    def _handle_upload_error(self, task, error_str):
        self._on_upload_error(task, error_str)

    @pyqtSlot(object, int, float)
    def _handle_upload_progress(self, task, percent, speed):
        task.set_progress(percent, speed)

    def _upload_file(self, task, on_complete=None):
        import time
        try:
            uploader = AcerumSmartUploader(self.active_server, task.file_path, self.crypto)
            start_time = time.time()

            def progress_callback(monitor):
                percent = int(monitor.bytes_read / monitor.len * 100)
                elapsed = time.time() - start_time
                speed = monitor.bytes_read / elapsed if elapsed > 0 else 0
                QMetaObject.invokeMethod(self, '_handle_upload_progress', Qt.QueuedConnection, Q_ARG(object, task), Q_ARG(int, percent), Q_ARG(float, speed))
            result = uploader.upload(progress_callback=progress_callback)
            QMetaObject.invokeMethod(self, '_handle_upload_success', Qt.QueuedConnection, Q_ARG(object, task), Q_ARG(object, result))
        except requests.exceptions.Timeout:
            QMetaObject.invokeMethod(self, '_handle_upload_error', Qt.QueuedConnection, Q_ARG(object, task), Q_ARG(str, 'Таймаут загрузки'))
        except requests.exceptions.ConnectionError:
            QMetaObject.invokeMethod(self, '_handle_upload_error', Qt.QueuedConnection, Q_ARG(object, task), Q_ARG(str, 'Ошибка соединения'))
        except Exception as e:
            QMetaObject.invokeMethod(self, '_handle_upload_error', Qt.QueuedConnection, Q_ARG(object, task), Q_ARG(str, str(e)))
        finally:
            if on_complete:
                QTimer.singleShot(0, on_complete)

    def _on_upload_success(self, task, result):
        task.set_finished()
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        QTimer.singleShot(500, task.deleteLater)
        self.network_send_file(result, '')
        filename = os.path.basename(task.file_path)
        file_id = result.get('file_id') if isinstance(result, dict) else result
        widget = FileWidget(self.settings['name'], filename, file_id, '', self.crypto, self.active_server)
        self.chat_layout.addWidget(widget)
        self.scroll_chat_to_bottom()

    def _on_upload_error(self, task, error_str):
        if '404' in error_str:
            msg = 'Сервер не поддерживает загрузку.'
        elif 'Connection' in error_str or 'SSL' in error_str:
            msg = 'Ошибка соединения с сервером.'
        else:
            msg = error_str
        task.set_error(msg)
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

    def network_send_text(self, text):
        try:
            enc_text = self.crypto.enc(text)
            enc_name = self.crypto.enc(self.settings.get('name', 'User'))
            requests.post(f'{self.active_server}/send', json={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': enc_name, 'encrypted_payload': enc_text}, timeout=6)
        except Exception as e:
            print(f'Ошибка отправки текста: {e}')

    def network_send_file(self, file_info, comment=''):
        try:
            enc_comment = self.crypto.enc(comment) if comment else ''
            enc_name = self.crypto.enc(self.settings.get('name', 'User'))
            fid = file_info.get('file_id') if isinstance(file_info, dict) else file_info
            requests.post(f'{self.active_server}/send', json={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': enc_name, 'encrypted_payload': enc_comment, 'is_file': True, 'file_id': fid}, timeout=6)
        except Exception as e:
            print(f'Ошибка отправки файла в чат: {e}')