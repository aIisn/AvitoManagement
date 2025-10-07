# server/main.py
# Main Flask Application Server / Основной сервер Flask-приложения
# Updated: removed global BLOCKED_IPS, IP_REQUEST_COUNTS, REQUEST_TIMEOUT, RATE_LIMIT, removed clean_blocked_ips call in security_middleware
# Обновлён: удалены глобальные BLOCKED_IPS, IP_REQUEST_COUNTS, REQUEST_TIMEOUT, RATE_LIMIT, удален вызов clean_blocked_ips в security_middleware

"""
Avito Management Server / Сервер управления Avito

Flask-based web server for managing advertisement photo processing and generation.
Веб-сервер на основе Flask для управления обработкой и генерацией фотографий объявлений.

Features / Функции:
- Manager management (create, rename, delete) / Управление менеджерами (создание, переименование, удаление)
- Photo upload and storage / Загрузка и хранение фотографий
- Image uniquification and watermarking / Уникализация изображений и добавление водяных знаков
- Ready advertisement link generation / Генерация ссылок на готовые объявления
- Security middleware / Промежуточное ПО для безопасности
"""

import time
import threading
from flask import Flask, request, jsonify, send_from_directory, abort, Response
import logging
from werkzeug.exceptions import BadRequest
import os
import shutil
from modules.utils import get_timestamp, log_message, is_suspicious_request, allowed_file
from modules.ad_processing import process_and_generate, PHOTOS_PER_AD

# ===== SETTINGS / НАСТРОЙКИ =====
CHECK_INTERVAL = 30  # Interval for periodic checks in seconds / Интервал периодических проверок в секундах
BASE_DIR = os.path.dirname(__file__)  # Base server directory / Базовая директория сервера
MANAGERS_DIR = os.path.join(BASE_DIR, 'data', 'managers')  # Managers data directory / Директория данных менеджеров
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'main.txt')  # Main log file path / Путь к основному лог-файлу
BASE_SERVER_URL = "http://109.172.39.225:5000/"  # Public server URL / Публичный URL сервера
CLIENT_DIR = os.path.join(BASE_DIR, '..', 'client')  # Client files directory / Директория файлов клиента

# ===== SECURITY / БЕЗОПАСНОСТЬ =====
ALLOWED_USER_AGENTS = ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']  # Allowed browser signatures / Разрешённые подписи браузеров
# ==================================

# Initialize Flask application / Инициализация Flask приложения
app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)

@app.before_request
def security_middleware():
    """
    Security middleware that runs before each request / Промежуточное ПО безопасности, выполняемое перед каждым запросом
    
    Performs / Выполняет:
    - Suspicious request detection / Обнаружение подозрительных запросов
    - CORS headers setup for API routes / Настройка CORS заголовков для API маршрутов
    - OPTIONS request handling / Обработка OPTIONS запросов
    """
    # Block suspicious requests / Блокировать подозрительные запросы
    if is_suspicious_request():
        abort(403)
    
    # Setup CORS for API routes / Настроить CORS для API маршрутов
    if request.path.startswith('/api/'):
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        if request.method == 'OPTIONS':
            return response

@app.route('/api/count_ready', methods=['GET'])
def count_ready():
    manager = request.args.get('manager')
    if not manager:
        return jsonify({'error': 'Manager required'}), 400
    try:
        ready_base = os.path.join(MANAGERS_DIR, manager, 'ready_photos')
        if not os.path.exists(ready_base):
            return jsonify({'counts': {}}), 200
        categories = [d for d in os.listdir(ready_base) if os.path.isdir(os.path.join(ready_base, d))]
        counts = {}
        for cat in categories:
            cat_path = os.path.join(ready_base, cat)
            counts[cat] = len([d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d))])
        return jsonify({'counts': counts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    """
    Error handler for malformed HTTP requests / Обработчик ошибок для некорректных HTTP-запросов
    
    Args:
        e: BadRequest exception / Исключение BadRequest
    
    Returns:
        tuple: Error message and 400 status code / Сообщение об ошибке и код статуса 400
    """
    client_ip = request.remote_addr
    log_message(f"🚫 Плохой HTTP-запрос от {client_ip} - игнорируем")
    return 'Bad Request', 400

@app.route('/api/get_links', methods=['GET'])
def get_links():
    manager = request.args.get('manager')
    category = request.args.get('category')
    if not manager or not category:
        return jsonify({'error': 'Manager and category required'}), 400
    try:
        ready_base = os.path.join(MANAGERS_DIR, manager, 'ready_photos', category)
        if not os.path.exists(ready_base):
            return jsonify({'error': 'Category not found'}), 404
        ad_dirs = sorted([d for d in os.listdir(ready_base) if os.path.isdir(os.path.join(ready_base, d))])
        results = []
        for idx, ad_dir in enumerate(ad_dirs, 1):
            ad_path = os.path.join(ready_base, ad_dir)
            files = sorted([f for f in os.listdir(ad_path) if f.lower().endswith('.jpg')])
            if len(files) == PHOTOS_PER_AD:
                links = []
                for file in files:
                    rel_path = os.path.join(category, ad_dir, file)
                    url = f"{BASE_SERVER_URL}{manager}/ready_photos/{rel_path}"
                    links.append(url)
                results.append([idx, "\n".join(links)])
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            last_20 = lines[-20:] if len(lines) > 20 else lines
            return jsonify({'logs': [line.strip() for line in last_20]})
        return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/managers', methods=['GET'])
def list_managers():
    try:
        managers = [d for d in os.listdir(MANAGERS_DIR) if os.path.isdir(os.path.join(MANAGERS_DIR, d))]
        return jsonify(managers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_logo', methods=['POST'])
def upload_logo():
    """
    Upload logo image for a manager / Загрузить изображение логотипа для менеджера
    
    Form data / Данные формы:
        manager: Manager name / Имя менеджера
        logo: Logo file (jpg, jpeg, png) / Файл логотипа (jpg, jpeg, png)
    
    Returns:
        JSON: Success status or error / Статус успеха или ошибка
    """
    manager = request.form.get('manager')
    if not manager:
        return jsonify({'error': 'Manager required'}), 400
    if 'logo' not in request.files:
        return jsonify({'error': 'No logo file'}), 400
    file = request.files['logo']
    if file and allowed_file(file.filename):
        img_dir = os.path.join(MANAGERS_DIR, manager, 'img')
        os.makedirs(img_dir, exist_ok=True)
        file_path = os.path.join(img_dir, 'Logo.png')
        file.save(file_path)
        log_message(f"📤 Логотип загружен для менеджера '{manager}'")
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/api/create-manager', methods=['POST'])
def create_manager():
    """
    Create a new manager with directory structure / Создать нового менеджера со структурой директорий
    
    JSON body:
        name: Manager name / Имя менеджера
    
    Creates directories / Создаёт директории:
    - photo_cache: For uploaded source photos / Для загруженных исходных фотографий
    - ready_photos: For processed photos / Для обработанных фотографий
    - img: For logo / Для логотипа
    
    Returns:
        JSON: Success status or error / Статус успеха или ошибка
    """
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        # Create manager directory structure / Создать структуру директорий менеджера
        manager_path = os.path.join(MANAGERS_DIR, name)
        os.makedirs(manager_path, exist_ok=True)
        os.makedirs(os.path.join(manager_path, 'photo_cache'), exist_ok=True)
        os.makedirs(os.path.join(manager_path, 'ready_photos'), exist_ok=True)
        os.makedirs(os.path.join(manager_path, 'img'), exist_ok=True)  # Logo directory / Директория для логотипа
        
        log_message(f"📁 Создана папка для менеджера '{name}'")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rename-manager', methods=['POST'])
def rename_manager():
    """
    Rename an existing manager / Переименовать существующего менеджера
    
    JSON body:
        old_name: Current manager name / Текущее имя менеджера
        new_name: New manager name / Новое имя менеджера
    
    Returns:
        JSON: Success status or error / Статус успеха или ошибка
    """
    try:
        old_name = request.json.get('old_name')
        new_name = request.json.get('new_name')
        if not old_name or not new_name:
            return jsonify({'error': 'Old and new names required'}), 400
        
        old_path = os.path.join(MANAGERS_DIR, old_name)
        new_path = os.path.join(MANAGERS_DIR, new_name)
        
        # Validate paths / Проверить пути
        if not os.path.exists(old_path):
            return jsonify({'error': 'Manager not found'}), 404
        if os.path.exists(new_path):
            return jsonify({'error': 'New name already exists'}), 400
        
        os.rename(old_path, new_path)
        log_message(f"🔄 Менеджер '{old_name}' переименован в '{new_name}'")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-manager', methods=['POST'])
def delete_manager():
    """
    Delete a manager and all associated data / Удалить менеджера и все связанные данные
    
    JSON body:
        name: Manager name to delete / Имя менеджера для удаления
    
    Returns:
        JSON: Success status or error / Статус успеха или ошибка
    """
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        path = os.path.join(MANAGERS_DIR, name)
        if not os.path.exists(path):
            return jsonify({'error': 'Manager not found'}), 404
        
        # Remove entire manager directory / Удалить всю директорию менеджера
        shutil.rmtree(path)
        log_message(f"🗑️ Менеджер '{name}' удален")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list', methods=['GET'])
def list_files():
    manager = request.args.get('manager')
    dir_type = request.args.get('dir')
    if not manager or dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Manager and valid directory required'}), 400
    base_dir = os.path.join(MANAGERS_DIR, manager, dir_type)
    path = request.args.get('path', '')
    full_path = os.path.normpath(os.path.join(base_dir, path))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path):
        return jsonify({'error': 'Invalid path'}), 400
    items = []
    for item in sorted(os.listdir(full_path)):
        item_path = os.path.join(full_path, item)
        rel_path = os.path.relpath(item_path, base_dir)
        item_type = 'dir' if os.path.isdir(item_path) else 'file'
        items.append({'name': item, 'type': item_type, 'path': rel_path})
    return jsonify({'children': items})

@app.route('/api/delete', methods=['POST'])
def delete_item():
    data = request.json
    manager = data.get('manager')
    dir_type = data.get('dir')
    if not manager or dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Manager and valid directory required'}), 400
    base_dir = os.path.join(MANAGERS_DIR, manager, dir_type)
    path = data.get('path')
    full_path = os.path.normpath(os.path.join(base_dir, path))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path) or full_path == base_dir:
        return jsonify({'error': 'Invalid path or cannot delete root'}), 400
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-folder-structure', methods=['POST'])
def create_folder_structure():
    """
    Create folder structure for photo positions / Создать структуру папок для позиций фотографий
    
    JSON body:
        manager: Manager name / Имя менеджера
        category: Category name / Имя категории
        positions: List of position folder names / Список имён папок позиций
    
    Returns:
        JSON: Success status with created folders or error / Статус успеха с созданными папками или ошибка
    """
    data = request.json
    manager = data.get('manager')
    category = data.get('category')
    positions = data.get('positions', [])
    
    if not manager or not category:
        return jsonify({'error': 'Manager and category required'}), 400
    
    try:
        # Create category directory / Создать директорию категории
        cache_dir = os.path.join(MANAGERS_DIR, manager, 'photo_cache')
        category_path = os.path.join(cache_dir, category)
        os.makedirs(category_path, exist_ok=True)
        
        # Create position folders / Создать папки позиций
        created_folders = []
        for pos in positions:
            pos_path = os.path.join(category_path, pos)
            os.makedirs(pos_path, exist_ok=True)
            created_folders.append(pos)
        log_message(f"📁 Создана структура папок для менеджера '{manager}', категории '{category}': {', '.join(created_folders)}")
        return jsonify({'success': True, 'created': created_folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """
    Upload multiple photo files to a specific position / Загрузить несколько фото-файлов в определённую позицию
    
    Form data / Данные формы:
        manager: Manager name / Имя менеджера
        category: Category name / Имя категории
        position: Position folder name / Имя папки позиции
        files: Multiple file uploads / Несколько загружаемых файлов
    
    Returns:
        JSON: Success status with uploaded filenames or error / Статус успеха с именами загруженных файлов или ошибка
    """
    manager = request.form.get('manager')
    category = request.form.get('category')
    position = request.form.get('position')
    
    if not manager or not category or not position:
        return jsonify({'error': 'Manager, category and position required'}), 400
    
    # Create target directory / Создать целевую директорию
    base_path = os.path.join(MANAGERS_DIR, manager, 'photo_cache', category, position)
    os.makedirs(base_path, exist_ok=True)
    
    # Upload files / Загрузить файлы
    uploaded = []
    for file in request.files.getlist('files'):
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(base_path, filename))
            uploaded.append(filename)
    log_message(f"📥 Загружено {len(uploaded)} файлов для менеджера '{manager}' в {category}/{position}: {', '.join(uploaded)}")
    return jsonify({'success': True, 'uploaded': uploaded})

@app.route('/api/uniquify', methods=['POST'])
def uniquify():
    data = request.json
    manager = data.get('manager')
    folder_name = data.get('folder_name')
    count = data.get('count')
    use_rotation = data.get('use_rotation', True)
    if not manager or not folder_name or not count:
        return jsonify({'error': 'Manager, folder_name and count required'}), 400
    try:
        results = process_and_generate(folder_name, count, use_rotation, manager)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<manager>/photo_cache/<path:path>')
def serve_photo_cache(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'photo_cache'), path)

@app.route('/<manager>/ready_photos/<path:path>')
def serve_ready_photos(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'ready_photos'), path)

@app.route('/')
def index():
    return send_from_directory(CLIENT_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename.endswith('.css') or filename.endswith('.js'):
        return send_from_directory(CLIENT_DIR, filename)
    abort(404)

if __name__ == "__main__":
    # Create managers directory if it doesn't exist / Создать директорию менеджеров если её не существует
    os.makedirs(MANAGERS_DIR, exist_ok=True)
    log_message("⏳ Сервер запущен")
    # Запустить Flask сервер
    app.run(host='0.0.0.0', port=5000, threaded=True)