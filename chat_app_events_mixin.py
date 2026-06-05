import json, os, threading, requests, time, sip
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
                            file_url = m.get('file_server_url', self.active_server)
                            if file_url not in self.SERVER_URLS:
                                file_url = self.active_server
                            QMetaObject.invokeMethod(self, '_add_file_widget_slot', Qt.QueuedConnection, Q_ARG(str, user_name), Q_ARG(str, info.get('fn', 'file')), Q_ARG(str, file_id), Q_ARG(str, ''), Q_ARG(object, self.crypto), Q_ARG(str, file_url))
                        else:
                            self.add_system_message(f'🔗 {user_name} отправил файл без ID: {info.get('fn', 'file')}', '#E2D189')
                    else:
                        self.add_system_message(f'🔗 {user_name} отправил зашифрованный файл', '#E2D189')
                except Exception as e:
                    print(f'Ошибка при обработке файла: {e}')
            else:
                text = self.crypto.dec(m.get('data'))
                if text:
                    self.add_chat_message(user_name, text, m['sender_uuid'])
                    if m['sender_uuid'] != self.user_uuid and (not m.get('target_uuid')):
                        threading.Thread(target=self.send_delivery_ack, args=(m.get('time'),), daemon=True).start()
                    if not self.isVisible():
                        self.show_notification(user_name, text)
            self.last_sync = max(self.last_sync, m.get('time', 0))

    @pyqtSlot(str, str, str, str, object, str)
    def _add_file_widget_slot(self, user_name, filename, file_id, text, crypto, file_url):
        widget = FileWidget(user_name, filename, file_id, text, crypto, file_url)
        self.chat_layout.addWidget(widget)
        self.scroll_chat_to_bottom()

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
        target = self.current_dm_target if hasattr(self, 'current_dm_target') else None
        tasks_to_process = [t for t in self.pending_tasks if not t.cancelled and (not t.is_uploading)]
        self.pending_tasks.clear()

        def do_send_text():
            if not text:
                return
            self.add_chat_message(my_name, text, self.user_uuid)
            threading.Thread(target=self.network_send_text, args=(text, target), daemon=True).start()
            self.last_sync = 0.0
        if tasks_to_process:
            self.input_field.clear()
            total_files = len(tasks_to_process)
            state = {'done': 0, 'text_sent': False}

            def on_file_done():
                state['done'] += 1
                if state['done'] >= total_files:
                    if text and (not state['text_sent']):
                        state['text_sent'] = True
                        do_send_text()
                    QTimer.singleShot(100, self.restore_focus)
            for task in tasks_to_process:
                task.set_uploading()
                threading.Thread(target=self._upload_file, args=(task, on_file_done), daemon=True).start()
        elif text:
            do_send_text()
            self.input_field.clear()
            QTimer.singleShot(100, self.restore_focus)
        else:
            QTimer.singleShot(100, self.restore_focus)
        if target:
            self.reset_dm_mode()

    @pyqtSlot(object, object)
    def _handle_upload_success(self, task, result):
        if not sip.isdeleted(task):
            self._on_upload_success(task, result)

    @pyqtSlot(object, str)
    def _handle_upload_error(self, task, error_str):
        if not sip.isdeleted(task):
            self._on_upload_error(task, error_str)

    @pyqtSlot(object, int, float)
    def _handle_upload_progress(self, task, percent, speed):
        if not sip.isdeleted(task):
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
        if not sip.isdeleted(task):
            QTimer.singleShot(500, task.deleteLater)
        filename = os.path.basename(task.file_path)
        self.network_send_file(result, filename)
        self.last_sync = 0.0
        if isinstance(result, dict):
            file_id = result.get('file_id')
            server_url = result.get('server_url', self.active_server)
        else:
            file_id = result
            server_url = self.active_server
        widget = FileWidget(self.settings['name'], filename, file_id, '', self.crypto, server_url)
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

    def network_send_text(self, text, target_uuid=None):
        try:
            enc_text = self.crypto.enc(text)
            enc_name = self.crypto.enc(self.settings.get('name', 'User'))
            payload = {'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': enc_name, 'encrypted_payload': enc_text}
            if target_uuid:
                payload['target_uuid'] = target_uuid
            self.session.post(f'{self.active_server}/send', json=payload, timeout=6)
        except Exception as e:
            print(f'Ошибка отправки текста: {e}')

    def network_send_file(self, file_info, filename, comment=''):
        try:
            file_meta = json.dumps({'fn': filename})
            enc_meta = self.crypto.enc(file_meta)
            enc_name = self.crypto.enc(self.settings.get('name', 'User'))
            fid = file_info.get('file_id') if isinstance(file_info, dict) else file_info
            server_url = file_info.get('server_url', self.active_server)
            self.session.post(f'{self.active_server}/send', json={'room_code': self.room_code, 'user_uuid': self.user_uuid, 'username': enc_name, 'encrypted_payload': enc_meta, 'is_file': True, 'file_id': fid, 'file_server_url': server_url}, timeout=6)
        except Exception as e:
            print(f'Ошибка отправки файла в чат: {e}')