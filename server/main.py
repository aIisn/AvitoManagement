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
from modules.user_management import (
    register_user, verify_user_email, authenticate_user, authenticate_user_with_session,
    resend_verification_code, get_user_by_email, get_user_by_username
)
from modules.auth_middleware import (
    require_auth, get_current_user, is_authenticated, 
    api_logout, api_get_user_sessions, cleanup_expired_sessions
)
from modules.redis_manager import (
    initialize_redis, shutdown_redis, get_redis_info, 
    cache_set, cache_get, cache_delete, clear_all_cache
)

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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
def list_managers():
    try:
        managers = [d for d in os.listdir(MANAGERS_DIR) if os.path.isdir(os.path.join(MANAGERS_DIR, d))]
        return jsonify(managers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_logo', methods=['POST'])
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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

# ============================================================================
# API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ / USER MANAGEMENT API ENDPOINTS
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """
    Регистрация нового пользователя / Register new user
    
    JSON body:
        username: Имя пользователя / Username
        email: Email пользователя / User's email
        password: Пароль / Password
    
    Returns:
        JSON: Success status and message / Статус успеха и сообщение
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'Все поля обязательны для заполнения'}), 400
        
        success, message = register_user(username, email, password)
        
        if success:
            log_message(f"📝 Новый пользователь зарегистрирован: {username} ({email})")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_message(f"❌ Ошибка регистрации: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/verify', methods=['POST'])
def api_verify_email():
    """
    Верификация email пользователя / Verify user's email
    
    JSON body:
        email: Email пользователя / User's email
        code: Код верификации / Verification code
    
    Returns:
        JSON: Success status and message / Статус успеха и сообщение
    """
    try:
        data = request.json
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({'success': False, 'error': 'Email и код верификации обязательны'}), 400
        
        success, message = verify_user_email(email, code)
        
        if success:
            log_message(f"✅ Email верифицирован: {email}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_message(f"❌ Ошибка верификации: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Авторизация пользователя / User authentication
    
    JSON body:
        username: Имя пользователя или email / Username or email
        password: Пароль / Password
    
    Returns:
        JSON: Success status, message, user data and session token / Статус успеха, сообщение, данные пользователя и токен сессии
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Имя пользователя и пароль обязательны'}), 400
        
        success, message, user_data, session_token = authenticate_user_with_session(username, password)
        
        if success:
            log_message(f"🔐 Пользователь авторизован: {user_data['username']}")
            
            # Создаем ответ с токеном сессии / Create response with session token
            response = jsonify({
                'success': True, 
                'message': message,
                'user': user_data,
                'session_token': session_token
            })
            
            # Устанавливаем cookie с токеном сессии / Set cookie with session token
            response.set_cookie(
                'session_token', 
                session_token, 
                max_age=24*60*60,  # 24 часа / 24 hours
                httponly=True,     # Защита от XSS / XSS protection
                secure=False,      # В продакшене должно быть True / Should be True in production
                samesite='Lax'     # CSRF защита / CSRF protection
            )
            
            return response
        else:
            return jsonify({'success': False, 'error': message}), 401
            
    except Exception as e:
        log_message(f"❌ Ошибка авторизации: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/resend-code', methods=['POST'])
def api_resend_verification_code():
    """
    Повторная отправка кода верификации / Resend verification code
    
    JSON body:
        email: Email пользователя / User's email
    
    Returns:
        JSON: Success status and message / Статус успеха и сообщение
    """
    try:
        data = request.json
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'error': 'Email обязателен'}), 400
        
        success, message = resend_verification_code(email)
        
        if success:
            log_message(f"📧 Код верификации повторно отправлен: {email}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_message(f"❌ Ошибка повторной отправки кода: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/check-email', methods=['POST'])
def api_check_email():
    """
    Проверка существования email / Check if email exists
    
    JSON body:
        email: Email для проверки / Email to check
    
    Returns:
        JSON: Email status / Статус email
    """
    try:
        data = request.json
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'error': 'Email обязателен'}), 400
        
        user = get_user_by_email(email)
        
        if user:
            return jsonify({
                'success': True,
                'exists': True,
                'verified': user['verified'],
                'username': user['username']
            })
        else:
            return jsonify({
                'success': True,
                'exists': False
            })
            
    except Exception as e:
        log_message(f"❌ Ошибка проверки email: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def api_logout():
    """
    Выход из системы / Logout
    
    Returns:
        JSON: Success status and message / Статус успеха и сообщение
    """
    try:
        # Получаем токен сессии / Get session token
        auth_header = request.headers.get('Authorization')
        session_token = None
        
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        else:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({'success': False, 'error': 'Токен сессии не найден'}), 400
        
        # Выходим из системы / Logout
        success, message = api_logout(session_token)
        
        if success:
            log_message(f"🚪 Пользователь вышел из системы: {get_current_user()['username']}")
            
            # Создаем ответ и удаляем cookie / Create response and remove cookie
            response = jsonify({
                'success': True,
                'message': message
            })
            response.set_cookie('session_token', '', expires=0)
            
            return response
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_message(f"❌ Ошибка выхода: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def api_get_current_user():
    """
    Получение данных текущего пользователя / Get current user data
    
    Returns:
        JSON: Current user data / Данные текущего пользователя
    """
    try:
        current_user = get_current_user()
        
        if current_user:
            return jsonify({
                'success': True,
                'user': {
                    'id': current_user['user_id'],
                    'username': current_user['username'],
                    'email': current_user['email'],
                    'session_created': current_user['created_at'],
                    'last_activity': current_user['last_activity']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
            
    except Exception as e:
        log_message(f"❌ Ошибка получения данных пользователя: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ============================================================================
# REDIS MANAGEMENT API ENDPOINTS / API ЭНДПОИНТЫ УПРАВЛЕНИЯ REDIS
# ============================================================================

@app.route('/api/redis/info', methods=['GET'])
@require_auth
def api_redis_info():
    """
    Получение информации о Redis / Get Redis information
    
    Returns:
        JSON: Redis server information / Информация о сервере Redis
    """
    try:
        redis_info = get_redis_info()
        return jsonify({
            'success': True,
            'redis': redis_info
        })
    except Exception as e:
        log_message(f"❌ Ошибка получения информации о Redis: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/redis/cache/clear', methods=['POST'])
@require_auth
def api_clear_cache():
    """
    Очистка всего кэша Redis / Clear all Redis cache
    
    Returns:
        JSON: Success status / Статус успеха
    """
    try:
        success = clear_all_cache()
        if success:
            log_message("🧹 Кэш Redis очищен администратором")
            return jsonify({
                'success': True,
                'message': 'Кэш успешно очищен'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Не удалось очистить кэш'
            }), 500
    except Exception as e:
        log_message(f"❌ Ошибка очистки кэша: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/redis/cache/set', methods=['POST'])
@require_auth
def api_cache_set():
    """
    Установка значения в кэш Redis / Set value in Redis cache
    
    JSON body:
        key: Cache key / Ключ кэша
        value: Value to cache / Значение для кэширования
        ttl: Time to live in seconds (optional) / Время жизни в секундах (опционально)
        prefix: Key prefix (optional) / Префикс ключа (опционально)
    
    Returns:
        JSON: Success status / Статус успеха
    """
    try:
        data = request.json
        key = data.get('key')
        value = data.get('value')
        ttl = data.get('ttl')
        prefix = data.get('prefix', 'cache')
        
        if not key or value is None:
            return jsonify({'success': False, 'error': 'Ключ и значение обязательны'}), 400
        
        success = cache_set(key, value, ttl, prefix)
        if success:
            return jsonify({
                'success': True,
                'message': 'Значение успешно закэшировано'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Не удалось закэшировать значение'
            }), 500
    except Exception as e:
        log_message(f"❌ Ошибка установки кэша: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/redis/cache/get', methods=['GET'])
@require_auth
def api_cache_get():
    """
    Получение значения из кэша Redis / Get value from Redis cache
    
    Query parameters:
        key: Cache key / Ключ кэша
        prefix: Key prefix (optional) / Префикс ключа (опционально)
    
    Returns:
        JSON: Cached value or error / Закэшированное значение или ошибка
    """
    try:
        key = request.args.get('key')
        prefix = request.args.get('prefix', 'cache')
        
        if not key:
            return jsonify({'success': False, 'error': 'Ключ обязателен'}), 400
        
        value = cache_get(key, prefix)
        if value is not None:
            return jsonify({
                'success': True,
                'value': value
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Значение не найдено в кэше'
            }), 404
    except Exception as e:
        log_message(f"❌ Ошибка получения кэша: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/redis/cache/delete', methods=['DELETE'])
@require_auth
def api_cache_delete():
    """
    Удаление значения из кэша Redis / Delete value from Redis cache
    
    JSON body:
        key: Cache key / Ключ кэша
        prefix: Key prefix (optional) / Префикс ключа (опционально)
    
    Returns:
        JSON: Success status / Статус успеха
    """
    try:
        data = request.json
        key = data.get('key')
        prefix = data.get('prefix', 'cache')
        
        if not key:
            return jsonify({'success': False, 'error': 'Ключ обязателен'}), 400
        
        success = cache_delete(key, prefix)
        if success:
            return jsonify({
                'success': True,
                'message': 'Значение успешно удалено из кэша'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Не удалось удалить значение из кэша'
            }), 500
    except Exception as e:
        log_message(f"❌ Ошибка удаления кэша: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/<manager>/photo_cache/<path:path>')
def serve_photo_cache(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'photo_cache'), path)

@app.route('/<manager>/ready_photos/<path:path>')
def serve_ready_photos(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'ready_photos'), path)

@app.route('/')
def index():
    # Проверяем авторизацию для главной страницы / Check authorization for main page
    session_token = request.cookies.get('session_token')
    
    if not session_token:
        # Перенаправляем на страницу авторизации / Redirect to auth page
        return send_from_directory(CLIENT_DIR, 'auth.html')
    
    # Валидируем сессию / Validate session
    from modules.auth_middleware import validate_session_token
    is_valid, session_data = validate_session_token(session_token, update_activity=False)
    
    if not is_valid:
        # Перенаправляем на страницу авторизации / Redirect to auth page
        return send_from_directory(CLIENT_DIR, 'auth.html')
    
    # Пользователь авторизован, показываем главную страницу / User is authenticated, show main page
    return send_from_directory(CLIENT_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename.endswith('.css') or filename.endswith('.js') or filename.endswith('.html'):
        return send_from_directory(CLIENT_DIR, filename)
    abort(404)

def cleanup_sessions_periodically():
    """Периодическая очистка истекших сессий / Periodic cleanup of expired sessions"""
    while True:
        try:
            time.sleep(CHECK_INTERVAL * 60)  # Каждые 30 минут / Every 30 minutes
            removed_count = cleanup_expired_sessions()
            if removed_count > 0:
                log_message(f"🧹 Очищено {removed_count} истекших сессий")
        except Exception as e:
            log_message(f"❌ Ошибка очистки сессий: {e}")

if __name__ == "__main__":
    # Create managers directory if it doesn't exist / Создать директорию менеджеров если её не существует
    os.makedirs(MANAGERS_DIR, exist_ok=True)
    
    # Initialize Redis connection / Инициализируем подключение к Redis
    redis_initialized = initialize_redis()
    if redis_initialized:
        log_message("✅ Redis подключен и готов к работе")
    else:
        log_message("❌ Redis недоступен - сервер не может работать без Redis")
        log_message("🔧 Установите Redis: sudo apt install redis-server && sudo systemctl start redis-server")
        exit(1)
    
    # Запускаем фоновую задачу очистки сессий / Start background session cleanup task
    cleanup_thread = threading.Thread(target=cleanup_sessions_periodically, daemon=True)
    cleanup_thread.start()
    
    log_message("⏳ Сервер запущен с Redis-только сессиями и защитой авторизации")
    
    try:
        # Запустить Flask сервер / Start Flask server
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        log_message("🛑 Получен сигнал остановки сервера")
    finally:
        # Shutdown Redis connection / Завершаем подключение к Redis
        shutdown_redis()
        log_message("🔌 Redis подключение закрыто")