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

# Redis-only session storage - no file storage needed

# ============================================================================
# УТИЛИТЫ / UTILITIES
# ============================================================================

# File-based session storage functions removed - using Redis only

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
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            logging.error("Redis недоступен - невозможно создать сессию")
            return None, None
        
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
        
        # Clean old sessions for user in Redis / Очищаем старые сессии пользователя в Redis
        cleanup_user_sessions_redis(user_id)
        
        # Store in Redis / Сохраняем в Redis
        if store_session_redis(session_token, session_data):
            logging.info(f"Создана сессия в Redis для пользователя {username} ({user_id})")
            return session_token, session_data
        else:
            logging.error(f"Не удалось сохранить сессию в Redis для пользователя {username}")
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

def validate_session_token(session_token: str, update_activity: bool = True) -> Tuple[bool, Optional[Dict]]:
    """
    Валидирует токен сессии / Validates session token
    
    Args:
        session_token: Токен сессии / Session token
        update_activity: Обновлять ли время последней активности / Whether to update last activity time
    
    Returns:
        Tuple[bool, Optional[Dict]]: (валидность, данные сессии) / (validity, session data)
    """
    try:
        if not session_token:
            return False, None
        
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            logging.error("Redis недоступен - невозможно валидировать сессию")
            return False, None
        
        # Get session from Redis / Получаем сессию из Redis
        session_data = get_session_redis(session_token)
        if session_data:
            # Проверяем срок действия / Check expiry
            if is_session_expired(session_data['created_at']):
                # Удаляем истекшую сессию / Remove expired session
                delete_session_redis(session_token)
                return False, None
            
            # Обновляем время последней активности только если требуется / Update last activity only if required
            if update_activity:
                session_data['last_activity'] = datetime.now().isoformat()
                store_session_redis(session_token, session_data)
            
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
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            logging.error("Redis недоступен - невозможно уничтожить сессию")
            return False
        
        # Delete from Redis / Удаляем из Redis
        if delete_session_redis(session_token):
            logging.info(f"Сессия {session_token} уничтожена в Redis")
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
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            logging.error("Redis недоступен - невозможно уничтожить сессии пользователя")
            return False
        
        # Delete all user sessions from Redis / Удаляем все сессии пользователя из Redis
        if delete_user_sessions_redis(user_id):
            logging.info(f"Все сессии пользователя {user_id} уничтожены в Redis")
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
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            logging.warning("Redis недоступен - пропуск очистки сессий")
            return 0
        
        # Redis automatically handles TTL expiration, but we can manually clean up
        # Redis автоматически обрабатывает истечение TTL, но мы можем очистить вручную
        from modules.redis_manager import redis_manager
        client = redis_manager.get_client()
        if not client:
            return 0
        
        removed_count = 0
        
        # Get all session keys / Получаем все ключи сессий
        session_keys = client.keys("avito:session:*")
        
        for key in session_keys:
            try:
                session_data = client.get(key)
                if session_data:
                    data = json.loads(session_data)
                    if is_session_expired(data['created_at']):
                        client.delete(key)
                        removed_count += 1
            except (json.JSONDecodeError, KeyError):
                # Invalid session data, remove it / Неверные данные сессии, удаляем
                client.delete(key)
                removed_count += 1
        
        if removed_count > 0:
            logging.info(f"Очищено {removed_count} истекших сессий из Redis")
        
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
        # Check if Redis is available / Проверяем доступность Redis
        if not redis_manager.is_available():
            return False, "Redis недоступен - невозможно получить сессии", []
        
        from modules.redis_manager import redis_manager
        client = redis_manager.get_client()
        if not client:
            return False, "Redis клиент недоступен", []
        
        user_sessions_key = f"avito:user_sessions:{user_id}"
        session_tokens = client.smembers(user_sessions_key)
        
        if not session_tokens:
            return True, "Активных сессий не найдено", []
        
        user_sessions = []
        for token in session_tokens:
            session_key = f"avito:session:{token}"
            session_data = client.get(session_key)
            
            if session_data:
                try:
                    data = json.loads(session_data)
                    if not is_session_expired(data['created_at']):
                        # Скрываем чувствительные данные / Hide sensitive data
                        safe_session = {
                            'session_id': token[:8] + '...',  # Показываем только часть токена / Show only part of token
                            'created_at': data['created_at'],
                            'last_activity': data['last_activity'],
                            'ip_address': data['ip_address'],
                            'user_agent': data['user_agent'][:50] + '...' if len(data['user_agent']) > 50 else data['user_agent']
                        }
                        user_sessions.append(safe_session)
                except (json.JSONDecodeError, KeyError):
                    # Invalid session data, skip / Неверные данные сессии, пропускаем
                    continue
        
        return True, f"Найдено {len(user_sessions)} активных сессий", user_sessions
        
    except Exception as e:
        error_msg = f"Ошибка получения сессий: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, []
