# filename="redis_manager.py"
# Redis Manager Module / Модуль управления Redis
# Module for Redis connection management, session storage, and caching

import redis
import json
import logging
from typing import Dict, Optional, Any, Union
from datetime import datetime, timedelta
import os

# ============================================================================
# КОНФИГУРАЦИЯ REDIS / REDIS CONFIGURATION
# ============================================================================

# Redis connection settings / Настройки подключения к Redis
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,  # Set password if Redis requires authentication
    'decode_responses': True,
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Redis key prefixes / Префиксы ключей Redis
REDIS_PREFIXES = {
    'session': 'avito:session:',
    'user_sessions': 'avito:user_sessions:',
    'cache': 'avito:cache:',
    'image_processing': 'avito:img:',
    'api_cache': 'avito:api:',
    'temp_data': 'avito:temp:'
}

# Cache TTL settings (in seconds) / Настройки TTL кэша (в секундах)
CACHE_TTL = {
    'session': 24 * 60 * 60,  # 24 hours
    'api_response': 5 * 60,   # 5 minutes
    'image_processing': 60 * 60,  # 1 hour
    'temp_data': 10 * 60,     # 10 minutes
    'user_data': 30 * 60      # 30 minutes
}

# ============================================================================
# REDIS CONNECTION MANAGER / МЕНЕДЖЕР ПОДКЛЮЧЕНИЯ К REDIS
# ============================================================================

class RedisManager:
    """Redis connection manager with fallback support / Менеджер подключения к Redis с поддержкой fallback"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        self.connection_errors = 0
        self.max_connection_errors = 5
        
    def connect(self) -> bool:
        """
        Establish Redis connection / Установить подключение к Redis
        
        Returns:
            bool: True if connected successfully / True если подключение успешно
        """
        try:
            self.redis_client = redis.Redis(**REDIS_CONFIG)
            # Test connection / Тестируем подключение
            self.redis_client.ping()
            self.is_connected = True
            self.connection_errors = 0
            logging.info("✅ Redis connection established successfully")
            return True
        except Exception as e:
            self.is_connected = False
            self.connection_errors += 1
            logging.warning(f"⚠️ Redis connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close Redis connection / Закрыть подключение к Redis"""
        if self.redis_client:
            try:
                self.redis_client.close()
                self.is_connected = False
                logging.info("🔌 Redis connection closed")
            except Exception as e:
                logging.error(f"❌ Error closing Redis connection: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Redis is available / Проверить доступность Redis
        
        Returns:
            bool: True if Redis is available / True если Redis доступен
        """
        if not self.is_connected or self.connection_errors >= self.max_connection_errors:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            self.connection_errors += 1
            return False
    
    def get_client(self) -> Optional[redis.Redis]:
        """
        Get Redis client / Получить клиент Redis
        
        Returns:
            Optional[redis.Redis]: Redis client or None / Клиент Redis или None
        """
        if self.is_available():
            return self.redis_client
        return None

# Global Redis manager instance / Глобальный экземпляр менеджера Redis
redis_manager = RedisManager()

# ============================================================================
# SESSION MANAGEMENT WITH REDIS / УПРАВЛЕНИЕ СЕССИЯМИ С REDIS
# ============================================================================

def store_session_redis(session_token: str, session_data: Dict, ttl: int = None) -> bool:
    """
    Store session data in Redis / Сохранить данные сессии в Redis
    
    Args:
        session_token: Session token / Токен сессии
        session_data: Session data / Данные сессии
        ttl: Time to live in seconds / Время жизни в секундах
    
    Returns:
        bool: True if stored successfully / True если сохранено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        key = f"{REDIS_PREFIXES['session']}{session_token}"
        ttl = ttl or CACHE_TTL['session']
        
        # Store session data / Сохраняем данные сессии
        client.setex(key, ttl, json.dumps(session_data, ensure_ascii=False))
        
        # Add to user sessions set / Добавляем в набор сессий пользователя
        user_id = session_data.get('user_id')
        if user_id:
            user_sessions_key = f"{REDIS_PREFIXES['user_sessions']}{user_id}"
            client.sadd(user_sessions_key, session_token)
            client.expire(user_sessions_key, ttl)
        
        return True
    except Exception as e:
        logging.error(f"❌ Error storing session in Redis: {e}")
        return False

def get_session_redis(session_token: str) -> Optional[Dict]:
    """
    Get session data from Redis / Получить данные сессии из Redis
    
    Args:
        session_token: Session token / Токен сессии
    
    Returns:
        Optional[Dict]: Session data or None / Данные сессии или None
    """
    if not redis_manager.is_available():
        return None
    
    try:
        client = redis_manager.get_client()
        if not client:
            return None
        
        key = f"{REDIS_PREFIXES['session']}{session_token}"
        data = client.get(key)
        
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logging.error(f"❌ Error getting session from Redis: {e}")
        return None

def delete_session_redis(session_token: str) -> bool:
    """
    Delete session from Redis / Удалить сессию из Redis
    
    Args:
        session_token: Session token / Токен сессии
    
    Returns:
        bool: True if deleted successfully / True если удалено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        key = f"{REDIS_PREFIXES['session']}{session_token}"
        
        # Get session data to find user_id / Получаем данные сессии для поиска user_id
        session_data = get_session_redis(session_token)
        
        # Delete session / Удаляем сессию
        client.delete(key)
        
        # Remove from user sessions set / Удаляем из набора сессий пользователя
        if session_data and 'user_id' in session_data:
            user_id = session_data['user_id']
            user_sessions_key = f"{REDIS_PREFIXES['user_sessions']}{user_id}"
            client.srem(user_sessions_key, session_token)
        
        return True
    except Exception as e:
        logging.error(f"❌ Error deleting session from Redis: {e}")
        return False

def delete_user_sessions_redis(user_id: str) -> bool:
    """
    Delete all sessions for a user from Redis / Удалить все сессии пользователя из Redis
    
    Args:
        user_id: User ID / ID пользователя
    
    Returns:
        bool: True if deleted successfully / True если удалено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        user_sessions_key = f"{REDIS_PREFIXES['user_sessions']}{user_id}"
        session_tokens = client.smembers(user_sessions_key)
        
        # Delete all session keys / Удаляем все ключи сессий
        for token in session_tokens:
            session_key = f"{REDIS_PREFIXES['session']}{token}"
            client.delete(session_key)
        
        # Delete user sessions set / Удаляем набор сессий пользователя
        client.delete(user_sessions_key)
        
        return True
    except Exception as e:
        logging.error(f"❌ Error deleting user sessions from Redis: {e}")
        return False

# ============================================================================
# CACHING FUNCTIONS / ФУНКЦИИ КЭШИРОВАНИЯ
# ============================================================================

def cache_set(key: str, value: Any, ttl: int = None, prefix: str = 'cache') -> bool:
    """
    Set cache value in Redis / Установить значение кэша в Redis
    
    Args:
        key: Cache key / Ключ кэша
        value: Value to cache / Значение для кэширования
        ttl: Time to live in seconds / Время жизни в секундах
        prefix: Key prefix / Префикс ключа
    
    Returns:
        bool: True if cached successfully / True если закэшировано успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        cache_key = f"{REDIS_PREFIXES[prefix]}{key}"
        ttl = ttl or CACHE_TTL.get(prefix, 300)  # Default 5 minutes
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        
        client.setex(cache_key, ttl, value)
        return True
    except Exception as e:
        logging.error(f"❌ Error setting cache in Redis: {e}")
        return False

def cache_get(key: str, prefix: str = 'cache') -> Optional[Any]:
    """
    Get cache value from Redis / Получить значение кэша из Redis
    
    Args:
        key: Cache key / Ключ кэша
        prefix: Key prefix / Префикс ключа
    
    Returns:
        Optional[Any]: Cached value or None / Закэшированное значение или None
    """
    if not redis_manager.is_available():
        return None
    
    try:
        client = redis_manager.get_client()
        if not client:
            return None
        
        cache_key = f"{REDIS_PREFIXES[prefix]}{key}"
        value = client.get(cache_key)
        
        if value is not None:
            # Try to parse as JSON / Пытаемся распарсить как JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        
        return None
    except Exception as e:
        logging.error(f"❌ Error getting cache from Redis: {e}")
        return None

def cache_delete(key: str, prefix: str = 'cache') -> bool:
    """
    Delete cache value from Redis / Удалить значение кэша из Redis
    
    Args:
        key: Cache key / Ключ кэша
        prefix: Key prefix / Префикс ключа
    
    Returns:
        bool: True if deleted successfully / True если удалено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        cache_key = f"{REDIS_PREFIXES[prefix]}{key}"
        client.delete(cache_key)
        return True
    except Exception as e:
        logging.error(f"❌ Error deleting cache from Redis: {e}")
        return False

# ============================================================================
# UTILITY FUNCTIONS / УТИЛИТАРНЫЕ ФУНКЦИИ
# ============================================================================

def get_redis_info() -> Dict[str, Any]:
    """
    Get Redis server information / Получить информацию о сервере Redis
    
    Returns:
        Dict[str, Any]: Redis server info / Информация о сервере Redis
    """
    if not redis_manager.is_available():
        return {'status': 'disconnected', 'error': 'Redis not available'}
    
    try:
        client = redis_manager.get_client()
        if not client:
            return {'status': 'disconnected', 'error': 'No client available'}
        
        info = client.info()
        return {
            'status': 'connected',
            'version': info.get('redis_version'),
            'uptime': info.get('uptime_in_seconds'),
            'connected_clients': info.get('connected_clients'),
            'used_memory': info.get('used_memory_human'),
            'keyspace': info.get('db0', {}).get('keys', 0)
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def clear_all_cache() -> bool:
    """
    Clear all application cache from Redis / Очистить весь кэш приложения из Redis
    
    Returns:
        bool: True if cleared successfully / True если очищено успешно
    """
    if not redis_manager.is_available():
        return False
    
    try:
        client = redis_manager.get_client()
        if not client:
            return False
        
        # Get all keys with our prefixes / Получаем все ключи с нашими префиксами
        keys_to_delete = []
        for prefix in REDIS_PREFIXES.values():
            pattern = f"{prefix}*"
            keys = client.keys(pattern)
            keys_to_delete.extend(keys)
        
        if keys_to_delete:
            client.delete(*keys_to_delete)
        
        return True
    except Exception as e:
        logging.error(f"❌ Error clearing cache from Redis: {e}")
        return False

# ============================================================================
# INITIALIZATION / ИНИЦИАЛИЗАЦИЯ
# ============================================================================

def initialize_redis() -> bool:
    """
    Initialize Redis connection / Инициализировать подключение к Redis
    
    Returns:
        bool: True if initialized successfully / True если инициализировано успешно
    """
    return redis_manager.connect()

def shutdown_redis():
    """Shutdown Redis connection / Завершить подключение к Redis"""
    redis_manager.disconnect()
