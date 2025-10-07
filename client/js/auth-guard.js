// filename="auth-guard.js"
// Модуль для защиты клиентской части от неавторизованного доступа
// Module for protecting client-side from unauthorized access

// ============================================================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ / GLOBAL VARIABLES
// ============================================================================

let currentUser = null;
let sessionToken = null;
let authCheckInterval = null;

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ / INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🛡️ Модуль защиты авторизации инициализирован');
    
    // Проверяем авторизацию при загрузке страницы / Check authorization on page load
    checkAuthentication();
    
    // Запускаем периодическую проверку авторизации / Start periodic auth check
    startAuthCheck();
    
    console.log('✅ Защита авторизации активна');
});

// ============================================================================
// ПРОВЕРКА АВТОРИЗАЦИИ / AUTHENTICATION CHECK
// ============================================================================

async function checkAuthentication() {
    try {
        // Получаем токен из localStorage или cookies / Get token from localStorage or cookies
        sessionToken = localStorage.getItem('session_token') || getCookie('session_token');
        
        if (!sessionToken) {
            console.log('🔒 Токен сессии не найден, перенаправление на авторизацию');
            redirectToAuth();
            return false;
        }
        
        // Проверяем валидность токена на сервере / Check token validity on server
        const response = await fetch('/api/auth/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.log('🔒 Сессия истекла, перенаправление на авторизацию');
                clearAuthData();
                redirectToAuth();
                return false;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.user) {
            currentUser = data.user;
            console.log('✅ Пользователь авторизован:', currentUser.username);
            
            // Обновляем UI с данными пользователя / Update UI with user data
            updateUserInterface();
            
            return true;
        } else {
            throw new Error('Неверный ответ сервера');
        }
        
    } catch (error) {
        console.error('❌ Ошибка проверки авторизации:', error);
        clearAuthData();
        redirectToAuth();
        return false;
    }
}

function startAuthCheck() {
    // Проверяем авторизацию каждые 5 минут / Check auth every 5 minutes
    authCheckInterval = setInterval(async () => {
        const isAuthenticated = await checkAuthentication();
        if (!isAuthenticated) {
            clearInterval(authCheckInterval);
        }
    }, 5 * 60 * 1000);
}

// ============================================================================
// УПРАВЛЕНИЕ АВТОРИЗАЦИЕЙ / AUTHENTICATION MANAGEMENT
// ============================================================================

function clearAuthData() {
    currentUser = null;
    sessionToken = null;
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
    // Удаляем cookie / Remove cookie
    document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

function redirectToAuth() {
    // Проверяем, не находимся ли мы уже на странице авторизации / Check if we're not already on auth page
    if (!window.location.pathname.includes('auth.html')) {
        window.location.href = '/auth.html';
    }
}

function updateUserInterface() {
    if (!currentUser) return;
    
    // Обновляем аватар пользователя / Update user avatar
    const userAvatar = document.querySelector('.user-avatar');
    if (userAvatar) {
        userAvatar.innerHTML = `<i class="fas fa-user"></i>`;
        userAvatar.title = `Пользователь: ${currentUser.username}`;
    }
    
    // Добавляем информацию о пользователе в настройки / Add user info to settings
    const settingsTab = document.querySelector('[data-tab="settings"]');
    if (settingsTab) {
        const settingsContent = document.getElementById('settings');
        if (settingsContent) {
            settingsContent.innerHTML = `
                <div class="section">
                    <h2>Настройки</h2>
                    <div class="user-info">
                        <h3>Информация о пользователе</h3>
                        <p><strong>Имя пользователя:</strong> ${currentUser.username}</p>
                        <p><strong>Email:</strong> ${currentUser.email}</p>
                        <p><strong>ID:</strong> ${currentUser.id}</p>
                        <p><strong>Последняя активность:</strong> ${formatDate(currentUser.last_activity)}</p>
                    </div>
                    <div class="auth-actions">
                        <button class="btn-danger" onclick="logout()">
                            <i class="fas fa-sign-out-alt"></i>
                            Выйти из системы
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// ============================================================================
// API ФУНКЦИИ / API FUNCTIONS
// ============================================================================

async function logout() {
    try {
        if (!sessionToken) {
            clearAuthData();
            redirectToAuth();
            return;
        }
        
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                console.log('✅ Успешный выход из системы');
            }
        }
        
    } catch (error) {
        console.error('❌ Ошибка выхода:', error);
    } finally {
        // Очищаем данные и перенаправляем независимо от результата / Clear data and redirect regardless of result
        clearAuthData();
        redirectToAuth();
    }
}

// ============================================================================
// УТИЛИТЫ / UTILITIES
// ============================================================================

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU');
    } catch (error) {
        return 'Неизвестно';
    }
}

// ============================================================================
// ОБРАБОТКА ОШИБОК API / API ERROR HANDLING
// ============================================================================

// Перехватываем все fetch запросы для добавления авторизации / Intercept all fetch requests to add authorization
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    // Добавляем токен авторизации к API запросам / Add auth token to API requests
    if (url.startsWith('/api/') && !url.includes('/api/auth/')) {
        if (sessionToken) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${sessionToken}`;
        }
    }
    
    return originalFetch(url, options).then(response => {
        // Проверяем ответы на ошибки авторизации / Check responses for auth errors
        if (response.status === 401 && url.startsWith('/api/')) {
            console.log('🔒 Обнаружена ошибка авторизации, перенаправление');
            clearAuthData();
            redirectToAuth();
        }
        return response;
    });
};

// ============================================================================
// ЭКСПОРТ ФУНКЦИЙ ДЛЯ ГЛОБАЛЬНОГО ДОСТУПА / EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================================

// Делаем функции доступными глобально / Make functions globally available
window.AuthGuard = {
    checkAuthentication,
    logout,
    getCurrentUser: () => currentUser,
    getSessionToken: () => sessionToken,
    clearAuthData
};

// Глобальная функция выхода / Global logout function
window.logout = logout;
