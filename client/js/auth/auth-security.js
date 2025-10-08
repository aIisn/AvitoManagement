// filename="auth-security.js"
// Модуль безопасности для авторизации
// Authentication security module

import { getStoredToken, removeToken, formatAuthError } from './auth-utils.js';
import { showError } from './auth-ui.js';

// ============================================================================
// ФУНКЦИИ БЕЗОПАСНОСТИ / SECURITY FUNCTIONS
// ============================================================================

/**
 * Валидация JWT токена
 * @param {string} token - Токен для проверки
 * @returns {Object} - Результат валидации
 */
export function validateToken(token) {
    if (!token || typeof token !== 'string') {
        return { isValid: false, error: 'Токен не предоставлен' };
    }
    
    try {
        // Проверяем формат JWT (должен содержать 3 части, разделенные точками)
        const parts = token.split('.');
        if (parts.length !== 3) {
            return { isValid: false, error: 'Неверный формат токена' };
        }
        
        // Декодируем payload (вторая часть)
        const payload = JSON.parse(atob(parts[1]));
        
        // Проверяем срок действия
        if (payload.exp && payload.exp < Date.now() / 1000) {
            return { isValid: false, error: 'Токен истек' };
        }
        
        // Проверяем время выдачи (не должен быть в будущем)
        if (payload.iat && payload.iat > Date.now() / 1000) {
            return { isValid: false, error: 'Токен выдан в будущем' };
        }
        
        return { 
            isValid: true, 
            payload: payload,
            expiresAt: payload.exp ? new Date(payload.exp * 1000) : null
        };
        
    } catch (error) {
        return { isValid: false, error: 'Ошибка при декодировании токена' };
    }
}

/**
 * Обновление токена
 * @returns {Promise<boolean>} - Успешность обновления
 */
export async function refreshToken() {
    const currentToken = getStoredToken();
    
    if (!currentToken) {
        return false;
    }
    
    // Проверяем, нужно ли обновлять токен
    const validation = validateToken(currentToken);
    if (!validation.isValid) {
        return false;
    }
    
    // Если токен истекает в течение 5 минут, обновляем его
    const fiveMinutesFromNow = Date.now() + (5 * 60 * 1000);
    if (validation.expiresAt && validation.expiresAt.getTime() < fiveMinutesFromNow) {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${currentToken}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.token) {
                    // Сохраняем новый токен
                    const { storeToken } = await import('./auth-utils.js');
                    storeToken(data.token);
                    return true;
                }
            }
        } catch (error) {
            console.error('Ошибка при обновлении токена:', error);
        }
    }
    
    return true; // Токен еще действителен
}

/**
 * Проверка истечения сессии
 * @returns {Promise<boolean>} - true если сессия действительна
 */
export async function checkSessionExpiry() {
    const currentToken = getStoredToken();
    
    if (!currentToken) {
        return false;
    }
    
    const validation = validateToken(currentToken);
    
    if (!validation.isValid) {
        // Токен недействителен, очищаем данные
        const { clearAuthData } = await import('./auth-core.js');
        clearAuthData();
        return false;
    }
    
    // Проверяем, истекает ли токен в течение 1 минуты
    const oneMinuteFromNow = Date.now() + (60 * 1000);
    if (validation.expiresAt && validation.expiresAt.getTime() < oneMinuteFromNow) {
        // Пытаемся обновить токен
        const refreshed = await refreshToken();
        if (!refreshed) {
            // Не удалось обновить, сессия истекает
            const { clearAuthData } = await import('./auth-core.js');
            clearAuthData();
            return false;
        }
    }
    
    return true;
}

/**
 * Обработка ошибок авторизации
 * @param {Object} error - Объект ошибки
 * @param {Response} response - HTTP ответ (опционально)
 */
export function handleAuthError(error, response = null) {
    console.error('Ошибка авторизации:', error);
    
    let errorMessage = formatAuthError(error);
    let shouldLogout = false;
    
    // Определяем, нужно ли разлогинивать пользователя
    if (response) {
        switch (response.status) {
            case 401:
                errorMessage = 'Сессия истекла, войдите заново';
                shouldLogout = true;
                break;
            case 403:
                errorMessage = 'Доступ запрещен';
                shouldLogout = true;
                break;
            case 429:
                errorMessage = 'Слишком много попыток, попробуйте позже';
                break;
            case 500:
                errorMessage = 'Ошибка сервера, попробуйте позже';
                break;
        }
    }
    
    // Показываем ошибку
    showError(errorMessage);
    
    // Если нужно разлогинить
    if (shouldLogout) {
        setTimeout(async () => {
            const { clearAuthData, redirectToAuth } = await import('./auth-core.js');
            clearAuthData();
            redirectToAuth();
        }, 2000);
    }
}

// ============================================================================
// ФУНКЦИИ МОНИТОРИНГА БЕЗОПАСНОСТИ / SECURITY MONITORING
// ============================================================================

/**
 * Инициализация мониторинга безопасности
 */
export function initSecurityMonitoring() {
    // Проверяем сессию каждые 5 минут
    setInterval(async () => {
        const isValid = await checkSessionExpiry();
        if (!isValid) {
            console.log('Сессия истекла, пользователь будет разлогинен');
        }
    }, 5 * 60 * 1000);
    
    // Перехватываем все fetch запросы для добавления авторизации
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Добавляем токен авторизации к API запросам
        if (url.startsWith('/api/') && !url.includes('/api/auth/')) {
            const token = getStoredToken();
            if (token) {
                options.headers = options.headers || {};
                options.headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        return originalFetch(url, options).then(response => {
            // Проверяем ответы на ошибки авторизации
            if (response.status === 401 && url.startsWith('/api/')) {
                console.log('Обнаружена ошибка авторизации, перенаправление');
                handleAuthError({ code: 'TOKEN_EXPIRED' }, response);
            }
            return response;
        });
    };
}

/**
 * Проверка безопасности запроса
 * @param {string} url - URL запроса
 * @param {Object} options - Опции запроса
 * @returns {boolean} - true если запрос безопасен
 */
export function isSecureRequest(url, options = {}) {
    // Проверяем, что запрос идет на наш API
    if (!url.startsWith('/api/')) {
        return false;
    }
    
    // Проверяем, что используется HTTPS в продакшене
    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
        console.warn('Небезопасное соединение в продакшене');
        return false;
    }
    
    // Проверяем наличие токена для защищенных эндпоинтов
    if (!url.includes('/api/auth/') && !options.headers?.Authorization) {
        const token = getStoredToken();
        if (!token) {
            return false;
        }
    }
    
    return true;
}
