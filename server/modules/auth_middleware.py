# filename="auth_middleware.py"
# Модуль для middleware авторизации и управления сессиями
# Module for authorization middleware and session management

import json
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from flask import request, jsonify, session
import logging
from modules.redis_manager import (
    store_session_redis, get_session_redis, delete_session_redis, 
    delete_user_sessions_redis, redis_manager
)

# ============================================================================
# КОНФИГУРАЦИЯ / CONFIGURATION
# ============================================================================

# Настройки сессий / Session settings
SESSION_CONFIG = {
    'secret_key': 'avito-management-secret-key-2024',  # В продакшене должен быть в переменных окружения / Should be in env vars in production
    'session_timeout_hours': 24,  # Время жизни сессии / Session lifetime
    'max_sessions_per_user': 3,   # Максимум сессий на пользователя / Max sessions per user
}

# Путь к файлу сессий / Sessions file path
SESSIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users', 'sessions.json')

# ============================================================================
# УТИЛИТЫ / UTILITIES
# ============================================================================

def ensure_sessions_file():
    """Создает файл сессий если он не существует / Creates sessions file if it doesn't exist"""
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_sessions() -> Dict:
    """Загружает сессии из файла / Loads sessions from file"""
    ensure_sessions_file()
    try:
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_sessions(sessions: Dict) -> bool:
    """Сохраняет сессии в файл / Saves sessions to file"""
    try:
        ensure_sessions_file()
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения сессий: {e}")
        return False

def generate_session_token() -> str:
    """Генерирует токен сессии / Generates session token"""
    return secrets.token_urlsafe(32)

def is_session_expired(created_at: str) -> bool:
    """Проверяет истекла ли сессия / Checks if session is expired"""
    try:
        created_time = datetime.fromisoformat(created_at)
        expiry_time = created_time + timedelta(hours=SESSION_CONFIG['session_timeout_hours'])
        return datetime.now() > expiry_time
    except ValueError:
        return True

# ============================================================================
# УПРАВЛЕНИЕ СЕССИЯМИ / SESSION MANAGEMENT
# ============================================================================

def create_user_session(user_id: str, username: str, email: str) -> Tuple[str, Dict]:
    """
    Создает новую сессию пользователя / Creates new user session
    
    Args:
        user_id: ID пользователя / User ID
        username: Имя пользователя / Username
        email: Email пользователя / User's email
    
    Returns:
        Tuple[str, Dict]: (токен сессии, данные сессии) / (session token, session data)
    """
    try:
        # Создаем новую сессию / Create new session
        session_token = generate_session_token()
        current_time = datetime.now().isoformat()
        
        session_data = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'created_at': current_time,
            'last_activity': current_time,
            'ip_address': request.remote_addr if request else 'unknown',
            'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
        }
        
        # Try Redis first, fallback to file storage / Пробуем Redis сначала, fallback на файловое хранилище
        if redis_manager.is_available():
            # Clean old sessions for user in Redis / Очищаем старые сессии пользователя в Redis
            cleanup_user_sessions_redis(user_id)
            
            # Store in Redis / Сохраняем в Redis
            if store_session_redis(session_token, session_data):
                logging.info(f"Создана сессия в Redis для пользователя {username} ({user_id})")
                return session_token, session_data
        
        # Fallback to file storage / Fallback на файловое хранилище
        sessions = load_sessions()
        
        # Очищаем старые сессии пользователя / Clean old user sessions
        if user_id in sessions:
            # Удаляем истекшие сессии / Remove expired sessions
            sessions[user_id] = {
                session_id: session_data for session_id, session_data in sessions[user_id].items()
                if not is_session_expired(session_data['created_at'])
            }
            
            # Ограничиваем количество сессий / Limit number of sessions
            if len(sessions[user_id]) >= SESSION_CONFIG['max_sessions_per_user']:
                # Удаляем самую старую сессию / Remove oldest session
                oldest_session = min(sessions[user_id].items(), key=lambda x: x[1]['created_at'])
                del sessions[user_id][oldest_session[0]]
        
        if user_id not in sessions:
            sessions[user_id] = {}
        
        sessions[user_id][session_token] = session_data
        
        if save_sessions(sessions):
            logging.info(f"Создана сессия в файле для пользователя {username} ({user_id})")
            return session_token, session_data
        else:
            return None, None
            
    except Exception as e:
        logging.error(f"Ошибка создания сессии: {e}")
        return None, None

def cleanup_user_sessions_redis(user_id: str) -> bool:
    """
    Clean up old sessions for a user in Redis / Очистить старые сессии пользователя в Redis
    
    Args:
        user_id: ID пользователя / User ID
    
    Returns:
        bool: True if cleaned successfully / True если очищено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        user_sessions_key = f"avito:user_sessions:{user_id}"
        session_tokens = client.smembers(user_sessions_key)
        
        # Check each session and remove expired ones / Проверяем каждую сессию и удаляем истекшие
        expired_tokens = []
        for token in session_tokens:
            session_key = f"avito:session:{token}"
            session_data = client.get(session_key)
            
            if session_data:
                try:
                    data = json.loads(session_data)
                    if is_session_expired(data['created_at']):
                        expired_tokens.append(token)
                except (json.JSONDecodeError, KeyError):
                    expired_tokens.append(token)
            else:
                expired_tokens.append(token)
        
        # Remove expired sessions / Удаляем истекшие сессии
        for token in expired_tokens:
            session_key = f"avito:session:{token}"
            client.delete(session_key)
            client.srem(user_sessions_key, token)
        
        return True
    except Exception as e:
        logging.error(f"Ошибка очистки сессий пользователя в Redis: {e}")
        return False

def validate_session_token(session_token: str) -> Tuple[bool, Optional[Dict]]:
    """
    Валидирует токен сессии / Validates session token
    
    Args:
        session_token: Токен сессии / Session token
    
    Returns:
        Tuple[bool, Optional[Dict]]: (валидность, данные сессии) / (validity, session data)
    """
    try:
        if not session_token:
            return False, None
        
        # Try Redis first / Пробуем Redis сначала
        if redis_manager.is_available():
            session_data = get_session_redis(session_token)
            if session_data:
                # Проверяем срок действия / Check expiry
                if is_session_expired(session_data['created_at']):
                    # Удаляем истекшую сессию / Remove expired session
                    delete_session_redis(session_token)
                    return False, None
                
                # Обновляем время последней активности / Update last activity
                session_data['last_activity'] = datetime.now().isoformat()
                store_session_redis(session_token, session_data)
                
                return True, session_data
        
        # Fallback to file storage / Fallback на файловое хранилище
        sessions = load_sessions()
        
        # Ищем сессию по токену / Find session by token
        for user_id, user_sessions in sessions.items():
            if session_token in user_sessions:
                session_data = user_sessions[session_token]
                
                # Проверяем срок действия / Check expiry
                if is_session_expired(session_data['created_at']):
                    # Удаляем истекшую сессию / Remove expired session
                    del user_sessions[session_token]
                    save_sessions(sessions)
                    return False, None
                
                # Обновляем время последней активности / Update last activity
                session_data['last_activity'] = datetime.now().isoformat()
                save_sessions(sessions)
                
                return True, session_data
        
        return False, None
        
    except Exception as e:
        logging.error(f"Ошибка валидации сессии: {e}")
        return False, None

def destroy_session(session_token: str) -> bool:
    """
    Уничтожает сессию / Destroys session
    
    Args:
        session_token: Токен сессии / Session token
    
    Returns:
        bool: Успех операции / Operation success
    """
    try:
        # Try Redis first / Пробуем Redis сначала
        if redis_manager.is_available():
            if delete_session_redis(session_token):
                logging.info(f"Сессия {session_token} уничтожена в Redis")
                return True
        
        # Fallback to file storage / Fallback на файловое хранилище
        sessions = load_sessions()
        
        for user_id, user_sessions in sessions.items():
            if session_token in user_sessions:
                del user_sessions[session_token]
                save_sessions(sessions)
                logging.info(f"Сессия {session_token} уничтожена в файле")
                return True
        
        return False
        
    except Exception as e:
        logging.error(f"Ошибка уничтожения сессии: {e}")
        return False

def destroy_all_user_sessions(user_id: str) -> bool:
    """
    Уничтожает все сессии пользователя / Destroys all user sessions
    
    Args:
        user_id: ID пользователя / User ID
    
    Returns:
        bool: Успех операции / Operation success
    """
    try:
        # Try Redis first / Пробуем Redis сначала
        if redis_manager.is_available():
            if delete_user_sessions_redis(user_id):
                logging.info(f"Все сессии пользователя {user_id} уничтожены в Redis")
                return True
        
        # Fallback to file storage / Fallback на файловое хранилище
        sessions = load_sessions()
        
        if user_id in sessions:
            del sessions[user_id]
            save_sessions(sessions)
            logging.info(f"Все сессии пользователя {user_id} уничтожены в файле")
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Ошибка уничтожения сессий пользователя: {e}")
        return False

def cleanup_expired_sessions() -> int:
    """
    Очищает истекшие сессии / Cleans up expired sessions
    
    Returns:
        int: Количество удаленных сессий / Number of removed sessions
    """
    try:
        sessions = load_sessions()
        removed_count = 0
        
        for user_id in list(sessions.keys()):
            user_sessions = sessions[user_id]
            expired_sessions = []
            
            for session_id, session_data in user_sessions.items():
                if is_session_expired(session_data['created_at']):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del user_sessions[session_id]
                removed_count += 1
            
            # Удаляем пользователя если у него нет активных сессий / Remove user if no active sessions
            if not user_sessions:
                del sessions[user_id]
        
        if removed_count > 0:
            save_sessions(sessions)
            logging.info(f"Очищено {removed_count} истекших сессий")
        
        return removed_count
        
    except Exception as e:
        logging.error(f"Ошибка очистки сессий: {e}")
        return 0

# ============================================================================
# MIDDLEWARE ФУНКЦИИ / MIDDLEWARE FUNCTIONS
# ============================================================================

def require_auth(f):
    """
    Декоратор для защиты маршрутов / Decorator for protecting routes
    
    Usage / Использование:
    @app.route('/api/protected')
    @require_auth
    def protected_route():
        # Доступно только авторизованным пользователям / Available only to authenticated users
        pass
    """
    def decorated_function(*args, **kwargs):
        # Получаем токен из заголовков / Get token from headers
        auth_header = request.headers.get('Authorization')
        session_token = None
        
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]  # Убираем "Bearer " / Remove "Bearer "
        else:
            # Пробуем получить из cookies / Try to get from cookies
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({
                'success': False,
                'error': 'Требуется авторизация',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Валидируем сессию / Validate session
        is_valid, session_data = validate_session_token(session_token)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Сессия истекла или недействительна',
                'code': 'SESSION_INVALID'
            }), 401
        
        # Добавляем данные пользователя в контекст запроса / Add user data to request context
        request.current_user = session_data
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_current_user() -> Optional[Dict]:
    """
    Получает данные текущего пользователя из контекста запроса / Gets current user data from request context
    
    Returns:
        Optional[Dict]: Данные пользователя или None / User data or None
    """
    return getattr(request, 'current_user', None)

def is_authenticated() -> bool:
    """
    Проверяет авторизован ли пользователь / Checks if user is authenticated
    
    Returns:
        bool: True если авторизован / True if authenticated
    """
    return get_current_user() is not None

# ============================================================================
# API ФУНКЦИИ / API FUNCTIONS
# ============================================================================

def api_logout(session_token: str) -> Tuple[bool, str]:
    """
    API функция для выхода из системы / API function for logout
    
    Args:
        session_token: Токен сессии / Session token
    
    Returns:
        Tuple[bool, str]: (успех, сообщение) / (success, message)
    """
    try:
        if not session_token:
            return False, "Токен сессии не предоставлен"
        
        success = destroy_session(session_token)
        
        if success:
            return True, "Успешный выход из системы"
        else:
            return False, "Сессия не найдена"
            
    except Exception as e:
        error_msg = f"Ошибка выхода: {str(e)}"
        logging.error(error_msg)
        return False, error_msg

def api_get_user_sessions(user_id: str) -> Tuple[bool, str, list]:
    """
    API функция для получения сессий пользователя / API function for getting user sessions
    
    Args:
        user_id: ID пользователя / User ID
    
    Returns:
        Tuple[bool, str, list]: (успех, сообщение, список сессий) / (success, message, sessions list)
    """
    try:
        sessions = load_sessions()
        
        if user_id not in sessions:
            return True, "Активных сессий не найдено", []
        
        user_sessions = []
        for session_id, session_data in sessions[user_id].items():
            if not is_session_expired(session_data['created_at']):
                # Скрываем чувствительные данные / Hide sensitive data
                safe_session = {
                    'session_id': session_id[:8] + '...',  # Показываем только часть токена / Show only part of token
                    'created_at': session_data['created_at'],
                    'last_activity': session_data['last_activity'],
                    'ip_address': session_data['ip_address'],
                    'user_agent': session_data['user_agent'][:50] + '...' if len(session_data['user_agent']) > 50 else session_data['user_agent']
                }
                user_sessions.append(safe_session)
        
        return True, f"Найдено {len(user_sessions)} активных сессий", user_sessions
        
    except Exception as e:
        error_msg = f"Ошибка получения сессий: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, []
