// filename="auth-utils.js"
// Модуль утилит для авторизации
// Authentication utilities module

// ============================================================================
// ФУНКЦИИ РАБОТЫ С ТОКЕНАМИ / TOKEN MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Получить сохраненный токен
 * @returns {string|null} - Токен или null
 */
export function getStoredToken() {
    // Сначала пробуем localStorage
    let token = localStorage.getItem('session_token');
    
    // Если нет в localStorage, пробуем cookies
    if (!token) {
        token = getCookie('session_token');
    }
    
    return token;
}

/**
 * Сохранить токен
 * @param {string} token - Токен для сохранения
 * @param {boolean} remember - Запомнить пользователя
 */
export function storeToken(token, remember = false) {
    if (!token) return;
    
    // Сохраняем в localStorage
    localStorage.setItem('session_token', token);
    
    // Если нужно запомнить, сохраняем в cookies
    if (remember) {
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + 30); // 30 дней
        document.cookie = `session_token=${token}; expires=${expiryDate.toUTCString()}; path=/; secure; samesite=strict`;
    }
}

/**
 * Удалить токен
 */
export function removeToken() {
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
    
    // Удаляем cookie
    document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

// ============================================================================
// ФУНКЦИИ ОБРАБОТКИ ОШИБОК / ERROR HANDLING FUNCTIONS
// ============================================================================

/**
 * Форматирование ошибки авторизации
 * @param {Object} error - Объект ошибки
 * @returns {string} - Пользовательское сообщение об ошибке
 */
export function formatAuthError(error) {
    if (!error) return 'Произошла неизвестная ошибка';
    
    // Если это строка, возвращаем как есть
    if (typeof error === 'string') {
        return error;
    }
    
    // Если это объект с сообщением
    if (error.message) {
        return error.message;
    }
    
    // Если это объект с кодом ошибки
    if (error.code) {
        const errorMessages = {
            'INVALID_CREDENTIALS': 'Неверное имя пользователя или пароль',
            'USER_NOT_FOUND': 'Пользователь не найден',
            'EMAIL_NOT_VERIFIED': 'Email не подтвержден',
            'TOKEN_EXPIRED': 'Сессия истекла, войдите заново',
            'TOKEN_INVALID': 'Недействительная сессия',
            'USER_ALREADY_EXISTS': 'Пользователь с таким именем уже существует',
            'EMAIL_ALREADY_EXISTS': 'Пользователь с таким email уже существует',
            'VERIFICATION_CODE_INVALID': 'Неверный код подтверждения',
            'VERIFICATION_CODE_EXPIRED': 'Код подтверждения истек',
            'RATE_LIMIT_EXCEEDED': 'Слишком много попыток, попробуйте позже',
            'NETWORK_ERROR': 'Ошибка сети, проверьте подключение к интернету'
        };
        
        return errorMessages[error.code] || 'Произошла ошибка при авторизации';
    }
    
    return 'Произошла неизвестная ошибка';
}

// ============================================================================
// ФУНКЦИИ РАБОТЫ С COOKIES / COOKIE FUNCTIONS
// ============================================================================

/**
 * Получить значение cookie
 * @param {string} name - Имя cookie
 * @returns {string|null} - Значение cookie или null
 */
export function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}

/**
 * Установить cookie
 * @param {string} name - Имя cookie
 * @param {string} value - Значение cookie
 * @param {number} days - Количество дней до истечения
 */
export function setCookie(name, value, days = 7) {
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + days);
    document.cookie = `${name}=${value}; expires=${expiryDate.toUTCString()}; path=/; secure; samesite=strict`;
}

// ============================================================================
// ФУНКЦИИ РАБОТЫ С ДАТАМИ / DATE FUNCTIONS
// ============================================================================

/**
 * Форматирование даты
 * @param {string|Date} dateString - Дата для форматирования
 * @returns {string} - Отформатированная дата
 */
export function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return 'Неизвестно';
    }
}

/**
 * Проверить, истекла ли дата
 * @param {string|Date} dateString - Дата для проверки
 * @returns {boolean} - true если дата истекла
 */
export function isDateExpired(dateString) {
    try {
        const date = new Date(dateString);
        return date < new Date();
    } catch (error) {
        return true;
    }
}

// ============================================================================
// ФУНКЦИИ РАБОТЫ С URL / URL FUNCTIONS
// ============================================================================

/**
 * Получить параметры URL
 * @returns {Object} - Объект с параметрами URL
 */
export function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    
    for (const [key, value] of params) {
        result[key] = value;
    }
    
    return result;
}

/**
 * Перенаправить на URL
 * @param {string} url - URL для перенаправления
 * @param {boolean} replace - Заменить текущую запись в истории
 */
export function redirectTo(url, replace = false) {
    if (replace) {
        window.location.replace(url);
    } else {
        window.location.href = url;
    }
}

// ============================================================================
// ФУНКЦИИ РАБОТЫ С ДАННЫМИ / DATA FUNCTIONS
// ============================================================================

/**
 * Сохранить данные пользователя
 * @param {Object} userData - Данные пользователя
 */
export function storeUserData(userData) {
    if (userData) {
        localStorage.setItem('user', JSON.stringify(userData));
    }
}

/**
 * Получить данные пользователя
 * @returns {Object|null} - Данные пользователя или null
 */
export function getUserData() {
    try {
        const userData = localStorage.getItem('user');
        return userData ? JSON.parse(userData) : null;
    } catch (error) {
        console.error('Ошибка при получении данных пользователя:', error);
        return null;
    }
}

/**
 * Очистить данные пользователя
 */
export function clearUserData() {
    localStorage.removeItem('user');
}
