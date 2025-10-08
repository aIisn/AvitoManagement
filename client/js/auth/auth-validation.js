// filename="auth-validation.js"
// Модуль валидации для авторизации
// Authentication validation module

// ============================================================================
// ФУНКЦИИ ВАЛИДАЦИИ / VALIDATION FUNCTIONS
// ============================================================================

/**
 * Валидация email адреса
 * @param {string} email - Email для проверки
 * @returns {boolean} - Результат валидации
 */
export function validateEmail(email) {
    if (!email || typeof email !== 'string') {
        return false;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email.trim());
}

/**
 * Валидация пароля
 * @param {string} password - Пароль для проверки
 * @returns {boolean} - Результат валидации
 */
export function validatePassword(password) {
    if (!password || typeof password !== 'string') {
        return false;
    }
    
    // Минимальная длина 6 символов
    return password.length >= 6;
}

/**
 * Валидация имени пользователя
 * @param {string} username - Имя пользователя для проверки
 * @returns {boolean} - Результат валидации
 */
export function validateUsername(username) {
    if (!username || typeof username !== 'string') {
        return false;
    }
    
    const trimmedUsername = username.trim();
    // 3-20 символов, только буквы, цифры и подчеркивания
    const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
    return usernameRegex.test(trimmedUsername);
}

/**
 * Валидация кода верификации
 * @param {string} code - Код для проверки
 * @returns {boolean} - Результат валидации
 */
export function validateVerificationCode(code) {
    if (!code || typeof code !== 'string') {
        return false;
    }
    
    // Код должен содержать 6 символов
    return code.trim().length === 6;
}

/**
 * Валидация формы авторизации
 * @param {Object} formData - Данные формы
 * @param {string} formType - Тип формы ('login', 'register', 'verification')
 * @returns {Object} - Результат валидации с ошибками
 */
export function validateForm(formData, formType) {
    const errors = [];
    
    switch (formType) {
        case 'login':
            if (!formData.username || !formData.username.trim()) {
                errors.push({ field: 'username', message: 'Введите имя пользователя' });
            }
            if (!formData.password || !formData.password.trim()) {
                errors.push({ field: 'password', message: 'Введите пароль' });
            }
            break;
            
        case 'register':
            if (!formData.username || !formData.username.trim()) {
                errors.push({ field: 'username', message: 'Введите имя пользователя' });
            } else if (!validateUsername(formData.username)) {
                errors.push({ field: 'username', message: 'Имя пользователя должно содержать 3-20 символов (буквы, цифры, _)' });
            }
            
            if (!formData.email || !formData.email.trim()) {
                errors.push({ field: 'email', message: 'Введите email' });
            } else if (!validateEmail(formData.email)) {
                errors.push({ field: 'email', message: 'Введите корректный email адрес' });
            }
            
            if (!formData.password || !formData.password.trim()) {
                errors.push({ field: 'password', message: 'Введите пароль' });
            } else if (!validatePassword(formData.password)) {
                errors.push({ field: 'password', message: 'Пароль должен содержать минимум 6 символов' });
            }
            
            if (!formData.confirmPassword || !formData.confirmPassword.trim()) {
                errors.push({ field: 'confirmPassword', message: 'Подтвердите пароль' });
            } else if (formData.password !== formData.confirmPassword) {
                errors.push({ field: 'confirmPassword', message: 'Пароли не совпадают' });
            }
            
            if (!formData.agreeTerms) {
                errors.push({ field: 'agreeTerms', message: 'Необходимо согласиться с условиями использования' });
            }
            break;
            
        case 'verification':
            if (!formData.email || !formData.email.trim()) {
                errors.push({ field: 'email', message: 'Введите email' });
            } else if (!validateEmail(formData.email)) {
                errors.push({ field: 'email', message: 'Введите корректный email адрес' });
            }
            
            if (!formData.code || !formData.code.trim()) {
                errors.push({ field: 'code', message: 'Введите код подтверждения' });
            } else if (!validateVerificationCode(formData.code)) {
                errors.push({ field: 'code', message: 'Код должен содержать 6 символов' });
            }
            break;
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// ============================================================================
// УТИЛИТЫ ВАЛИДАЦИИ / VALIDATION UTILITIES
// ============================================================================

/**
 * Очистка и нормализация строки
 * @param {string} str - Строка для очистки
 * @returns {string} - Очищенная строка
 */
export function sanitizeString(str) {
    if (!str || typeof str !== 'string') {
        return '';
    }
    return str.trim();
}

/**
 * Проверка на пустую строку
 * @param {string} str - Строка для проверки
 * @returns {boolean} - true если строка пустая
 */
export function isEmpty(str) {
    return !str || sanitizeString(str).length === 0;
}
