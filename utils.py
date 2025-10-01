import pytz
from datetime import datetime
import time
import os

# ===== БЕЗОПАСНОСТЬ =====
ALLOWED_USER_AGENTS = ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']
BLOCKED_IPS = set()
IP_REQUEST_COUNTS = {}
IP_BLOCK_TIMES = {}
RATE_LIMIT = 1000  # Лимит запросов до временной блокировки
REQUEST_TIMEOUT = 300  # Время блокировки в секундах
# ======================

def get_timestamp():
    # Получает текущую временную метку в московском времени
    tz = pytz.timezone('Europe/Moscow')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def log_message(message):
    # Логирует сообщение с временной меткой в консоль и файл
    timestamp = get_timestamp()
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    with open("main.txt", "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def is_suspicious_request():
    # Проверяет запрос на подозрительность
    from flask import request  # Импорт внутри функции, чтобы избежать циклических импортов
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    method = request.method
    
    if request.path == '/api/logs':
        return False
    
    if not any(ua in user_agent for ua in ALLOWED_USER_AGENTS):
        log_message(f"🚫 Подозрительный User-Agent от {client_ip}: {user_agent[:100]}")
        return True
    
    if method not in ['GET', 'POST', 'HEAD', 'OPTIONS']:
        log_message(f"🚫 Неизвестный метод {method} от {client_ip}")
        return True
    
    IP_REQUEST_COUNTS[client_ip] = IP_REQUEST_COUNTS.get(client_ip, 0) + 1
    
    if IP_REQUEST_COUNTS[client_ip] > RATE_LIMIT:
        BLOCKED_IPS.add(client_ip)
        IP_BLOCK_TIMES[client_ip] = time.time()
        log_message(f"🚫 IP {client_ip} заблокирован временно (слишком много запросов)")
        return True
    
    if client_ip in BLOCKED_IPS:
        return True
    
    return False

def clean_blocked_ips():
    # Очищает заблокированные IP по таймауту
    current_time = time.time()
    expired_ips = []
    for ip in BLOCKED_IPS:
        if current_time - IP_BLOCK_TIMES.get(ip, 0) > REQUEST_TIMEOUT:
            expired_ips.append(ip)
    
    for ip in expired_ips:
        BLOCKED_IPS.discard(ip)
        if ip in IP_BLOCK_TIMES:
            del IP_BLOCK_TIMES[ip]
        if ip in IP_REQUEST_COUNTS:
            IP_REQUEST_COUNTS[ip] = 0  # Сброс счетчика запросов после разблокировки

def allowed_file(filename):
    # Проверяет допустимое расширение файла
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ("jpg", "jpeg", "png")