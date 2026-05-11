import ctypes
AMSI_RESULT_CLEAN = 0
AMSI_RESULT_NOT_DETECTED = 1
AMSI_RESULT_DETECTED = 32768

def is_malware(data: bytes, filename: str='file') -> bool:
    print(f'\n[AMSI] Начинаю проверку: {filename}')
    try:
        amsi = ctypes.windll.amsi
        print('[AMSI] Библиотека amsi.dll загружена успешно.')
    except (AttributeError, FileNotFoundError):
        print('[AMSI] Ошибка: библиотека amsi.dll не найдена. AMSI недоступен.')
        return False
    amsi_context = ctypes.c_void_p()
    hr = amsi.AmsiInitialize(b'FileScanner', ctypes.byref(amsi_context))
    if hr != 0:
        print(f'[AMSI] Ошибка инициализации контекста (HRESULT: {hr:x})')
        return False
    print('[AMSI] Контекст инициализирован.')
    session = ctypes.c_void_p()
    hr = amsi.AmsiOpenSession(amsi_context, ctypes.byref(session))
    if hr != 0:
        print(f'[AMSI] Ошибка открытия сессии (HRESULT: {hr:x})')
        amsi.AmsiUninitialize(amsi_context)
        return False
    print('[AMSI] Сессия открыта.')
    result = ctypes.c_int()
    print(f'[AMSI] Передаю {len(data)} байт на сканирование...')
    hr = amsi.AmsiScanBuffer(amsi_context, ctypes.c_char_p(data), len(data), f'{filename}'.encode('utf-16-le'), session, ctypes.byref(result))
    if hr != 0:
        print(f'[AMSI] Ошибка сканирования (HRESULT: {hr:x})')
    else:
        print(f'[AMSI] Сканирование завершено. Код результата: {result.value}')
    amsi.AmsiCloseSession(amsi_context, session)
    amsi.AmsiUninitialize(amsi_context)
    print('[AMSI] Контекст и сессия освобождены.')
    if result.value >= AMSI_RESULT_DETECTED:
        print(f'[AMSI] Вредоносное ПО ОБНАРУЖЕНО.')
        return True
    else:
        if result.value == AMSI_RESULT_CLEAN:
            print('[AMSI] Результат: чисто.')
        elif result.value == AMSI_RESULT_NOT_DETECTED:
            print('[AMSI] Результат: угроз не найдено (Not Detected).')
        else:
            print(f'[AMSI] Неизвестный код результата: {result.value}')
        return False