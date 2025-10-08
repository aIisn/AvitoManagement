// filename="auth-core.js"
// Ядро авторизации - основные функции
// Authentication core - main functions

import { validateForm } from './auth-validation.js';
import { showError, showSuccess, setLoading, switchForm } from './auth-ui.js';
import { storeToken, removeToken, storeUserData, clearUserData, formatAuthError, redirectTo } from './auth-utils.js';
import { handleAuthError } from './auth-security.js';

// ============================================================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ / GLOBAL VARIABLES
// ============================================================================

let currentUser = null;
let authCheckInterval = null;

// ============================================================================
// ОСНОВНЫЕ ФУНКЦИИ АВТОРИЗАЦИИ / MAIN AUTHENTICATION FUNCTIONS
// ============================================================================

/**
 * Вход в систему
 * @param {string} username - Имя пользователя
 * @param {string} password - Пароль
 * @param {boolean} remember - Запомнить пользователя
 * @returns {Promise<boolean>} - Успешность входа
 */
export async function login(username, password, remember = false) {
    try {
        setLoading(true);
        
        // Валидация данных
        const validation = validateForm({ username, password }, 'login');
        if (!validation.isValid) {
            validation.errors.forEach(error => {
                showError(error.message);
            });
            return false;
        }
        
        // Отправка запроса на сервер
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username.trim(),
                password: password
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка авторизации');
        }
        
        // Сохраняем данные пользователя и токен
        if (data.user) {
            currentUser = data.user;
            storeUserData(data.user);
        }
        
        if (data.session_token) {
            storeToken(data.session_token, remember);
        }
        
        showSuccess('Успешный вход в систему!');
        
        // Перенаправление на главную страницу
        setTimeout(() => {
            redirectTo('/');
        }, 500);
        
        return true;
        
    } catch (error) {
        handleAuthError(error);
        return false;
    } finally {
        setLoading(false);
    }
}

/**
 * Регистрация пользователя
 * @param {string} username - Имя пользователя
 * @param {string} email - Email
 * @param {string} password - Пароль
 * @param {string} confirmPassword - Подтверждение пароля
 * @param {boolean} agreeTerms - Согласие с условиями
 * @returns {Promise<boolean>} - Успешность регистрации
 */
export async function register(username, email, password, confirmPassword, agreeTerms) {
    try {
        setLoading(true);
        
        // Валидация данных
        const validation = validateForm({ 
            username, 
            email, 
            password, 
            confirmPassword, 
            agreeTerms 
        }, 'register');
        
        if (!validation.isValid) {
            validation.errors.forEach(error => {
                showError(error.message);
            });
            return false;
        }
        
        // Отправка запроса на сервер
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username.trim(),
                email: email.trim(),
                password: password
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка регистрации');
        }
        
        showSuccess('Регистрация успешна! Проверьте email для подтверждения аккаунта.');
        
        // Переключаемся на форму верификации
        switchForm('verification');
        
        // Сохраняем email для верификации
        const emailInput = document.getElementById('verificationEmail');
        if (emailInput) {
            emailInput.value = email;
        }
        
        return true;
        
    } catch (error) {
        handleAuthError(error);
        return false;
    } finally {
        setLoading(false);
    }
}

/**
 * Верификация email
 * @param {string} email - Email
 * @param {string} code - Код подтверждения
 * @returns {Promise<boolean>} - Успешность верификации
 */
export async function verifyEmail(email, code) {
    try {
        setLoading(true);
        
        // Валидация данных
        const validation = validateForm({ email, code }, 'verification');
        if (!validation.isValid) {
            validation.errors.forEach(error => {
                showError(error.message);
            });
            return false;
        }
        
        // Отправка запроса на сервер
        const response = await fetch('/api/auth/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email.trim(),
                code: code.trim()
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка верификации');
        }
        
        showSuccess('Email успешно подтвержден! Теперь вы можете войти в систему.');
        
        // Переключаемся на форму входа
        setTimeout(() => {
            switchForm('login');
            // Заполняем email в форме входа
            const loginUsernameInput = document.getElementById('loginUsername');
            if (loginUsernameInput) {
                loginUsernameInput.value = email;
            }
        }, 2000);
        
        return true;
        
    } catch (error) {
        handleAuthError(error);
        return false;
    } finally {
        setLoading(false);
    }
}

/**
 * Выход из системы
 * @returns {Promise<void>}
 */
export async function logout() {
    try {
        const token = getStoredToken();
        
        if (token) {
            // Отправляем запрос на сервер для завершения сессии
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
            } catch (error) {
                console.warn('Ошибка при завершении сессии на сервере:', error);
            }
        }
        
        // Очищаем локальные данные
        clearAuthData();
        
        showSuccess('Вы успешно вышли из системы');
        
        // Перенаправляем на страницу авторизации
        setTimeout(() => {
            redirectToAuth();
        }, 1000);
        
    } catch (error) {
        console.error('Ошибка при выходе:', error);
        // Даже если произошла ошибка, очищаем локальные данные
        clearAuthData();
        redirectToAuth();
    }
}

/**
 * Проверка авторизации
 * @returns {Promise<boolean>} - Статус авторизации
 */
export async function checkAuth() {
    try {
        const token = getStoredToken();
        
        if (!token) {
            return false;
        }
        
        // Проверяем валидность токена на сервере
        const response = await fetch('/api/auth/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                clearAuthData();
                return false;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.user) {
            currentUser = data.user;
            storeUserData(data.user);
            return true;
        }
        
        return false;
        
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        clearAuthData();
        return false;
    }
}

/**
 * Очистка данных авторизации
 */
export function clearAuthData() {
    currentUser = null;
    removeToken();
    clearUserData();
    
    // Останавливаем периодическую проверку
    if (authCheckInterval) {
        clearInterval(authCheckInterval);
        authCheckInterval = null;
    }
}

/**
 * Перенаправление на страницу авторизации
 */
export function redirectToAuth() {
    // Проверяем, не находимся ли мы уже на странице авторизации
    if (!window.location.pathname.includes('auth.html')) {
        redirectTo('/auth.html');
    }
}

/**
 * Повторная отправка кода верификации
 * @param {string} email - Email для отправки кода
 * @returns {Promise<boolean>} - Успешность отправки
 */
export async function resendCode(email) {
    try {
        setLoading(true);
        
        // Валидация email
        const { validateEmail } = await import('./auth-validation.js');
        if (!validateEmail(email)) {
            showError('Введите корректный email адрес');
            return false;
        }
        
        // Отправка запроса на сервер
        const response = await fetch('/api/auth/resend-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email.trim()
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка повторной отправки кода');
        }
        
        showSuccess('Новый код отправлен на ваш email');
        return true;
        
    } catch (error) {
        handleAuthError(error);
        return false;
    } finally {
        setLoading(false);
    }
}

// ============================================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ / HELPER FUNCTIONS
// ============================================================================

/**
 * Получить текущего пользователя
 * @returns {Object|null} - Данные пользователя
 */
export function getCurrentUser() {
    return currentUser;
}

/**
 * Проверить, авторизован ли пользователь
 * @returns {boolean} - Статус авторизации
 */
export function isAuthenticated() {
    return currentUser !== null && getStoredToken() !== null;
}

/**
 * Запустить периодическую проверку авторизации
 */
export function startAuthCheck() {
    // Проверяем авторизацию каждые 5 минут
    authCheckInterval = setInterval(async () => {
        const isAuthenticated = await checkAuth();
        if (!isAuthenticated) {
            clearInterval(authCheckInterval);
        }
    }, 5 * 60 * 1000);
}

// Импортируем getStoredToken для использования в этом файле
import { getStoredToken } from './auth-utils.js';
