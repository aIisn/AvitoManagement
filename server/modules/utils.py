# server/modules/utils.py (обновлен: удалены глобальные переменные BLOCKED_IPS и IP_REQUEST_COUNTS, удалена логика блокировки по количеству запросов в is_suspicious_request, удалена функция clean_blocked_ips)

import pytz
from datetime import datetime
import os

def get_timestamp():
    # Получает текущую временную метку в московском времени
    tz = pytz.timezone('Europe/Moscow')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def log_message(message):
    # Логирует сообщение с временной меткой в консоль и файл
    timestamp = get_timestamp()
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'main.txt')
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def is_suspicious_request():
    # Проверяет запрос на подозрительность
    from flask import request  # Импорт внутри функции, чтобы избежать циклических импортов
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    method = request.method
    
    if request.path == '/api/logs':
        return False
    
    if not any(ua in user_agent for ua in ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']):
        log_message(f"🚫 Подозрительный User-Agent от {client_ip}: {user_agent[:100]}")
        return True
    
    if method not in ['GET', 'POST', 'HEAD', 'OPTIONS']:
        log_message(f"🚫 Неизвестный метод {method} от {client_ip}")
        return True
    
    return False

def allowed_file(filename):
    # Проверяет допустимое расширение файла
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ("jpg", "jpeg", "png")