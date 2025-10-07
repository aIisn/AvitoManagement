# server/modules/utils.py
# Utility functions for the AvitoManagement server / Вспомогательные функции для сервера AvitoManagement
# Updated: removed global variables BLOCKED_IPS and IP_REQUEST_COUNTS, removed blocking logic by request count in is_suspicious_request, removed clean_blocked_ips function
# Обновлён: удалены глобальные переменные BLOCKED_IPS и IP_REQUEST_COUNTS, удалена логика блокировки по количеству запросов в is_suspicious_request, удалена функция clean_blocked_ips

"""
Utilities Module / Модуль утилит

This module provides helper functions for logging, timestamp generation, request validation, and file validation.
Данный модуль предоставляет вспомогательные функции для логирования, генерации временных меток, валидации запросов и валидации файлов.
"""

import pytz
from datetime import datetime
import os

def get_timestamp():
    """
    Get current timestamp in Moscow timezone / Получить текущую временную метку в московском часовом поясе
    
    Returns:
        str: Formatted timestamp string in "YYYY-MM-DD HH:MM:SS" format / Форматированная строка временной метки в формате "YYYY-MM-DD HH:MM:SS"
    """
    tz = pytz.timezone('Europe/Moscow')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def log_message(message):
    """
    Log message with timestamp to console and file / Логировать сообщение с временной меткой в консоль и файл
    
    Args:
        message (str): Message to log / Сообщение для логирования
    
    The function:
    - Adds timestamp to the message / Добавляет временную метку к сообщению
    - Prints to console / Выводит в консоль
    - Appends to log file 'logs/main.txt' / Добавляет в лог-файл 'logs/main.txt'
    """
    timestamp = get_timestamp()
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    
    # Create logs directory if it doesn't exist / Создать директорию logs, если её не существует
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Append log entry to main.txt / Добавить запись в main.txt
    log_path = os.path.join(log_dir, 'main.txt')
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def is_suspicious_request():
    """
    Check if current request is suspicious / Проверить, является ли текущий запрос подозрительным
    
    Returns:
        bool: True if request is suspicious, False otherwise / True если запрос подозрительный, False в противном случае
    
    Checks performed / Выполняемые проверки:
    - User-Agent validation (must contain browser signatures) / Валидация User-Agent (должен содержать подписи браузеров)
    - HTTP method validation (only GET, POST, HEAD, OPTIONS allowed) / Валидация HTTP-метода (разрешены только GET, POST, HEAD, OPTIONS)
    - Skips validation for /api/logs endpoint / Пропускает валидацию для эндпоинта /api/logs
    """
    # Import inside function to avoid circular imports / Импорт внутри функции, чтобы избежать циклических импортов
    from flask import request
    
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    method = request.method
    
    # Skip validation for logs API / Пропустить валидацию для API логов
    if request.path == '/api/logs':
        return False
    
    # Check if User-Agent contains known browser signatures / Проверить, содержит ли User-Agent известные подписи браузеров
    if not any(ua in user_agent for ua in ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']):
        log_message(f"🚫 Подозрительный User-Agent от {client_ip}: {user_agent[:100]}")
        return True
    
    # Check if HTTP method is allowed / Проверить, разрешён ли HTTP-метод
    if method not in ['GET', 'POST', 'HEAD', 'OPTIONS']:
        log_message(f"🚫 Неизвестный метод {method} от {client_ip}")
        return True
    
    return False

def allowed_file(filename):
    """
    Check if file has allowed extension / Проверить, имеет ли файл допустимое расширение
    
    Args:
        filename (str): Name of the file to check / Имя файла для проверки
    
    Returns:
        bool: True if file extension is allowed (jpg, jpeg, png), False otherwise / True если расширение файла допустимо (jpg, jpeg, png), False в противном случае
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ("jpg", "jpeg", "png")