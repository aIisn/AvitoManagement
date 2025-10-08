// filename="auth-manager.js"
// Главный менеджер авторизации - точка входа
// Main authentication manager - entry point

import { 
    login, 
    register, 
    verifyEmail, 
    logout, 
    checkAuth, 
    clearAuthData, 
    redirectToAuth, 
    resendCode,
    getCurrentUser,
    isAuthenticated,
    startAuthCheck
} from './auth-core.js';

import { initSecurityMonitoring } from './auth-security.js';
import { switchForm, showError, showSuccess, setLoading, showFieldError, clearFieldError } from './auth-ui.js';

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ АВТОРИЗАЦИИ / AUTHENTICATION INITIALIZATION
// ============================================================================

/**
 * Инициализация системы авторизации
 */
export async function initAuth() {
    try {
        // Инициализируем мониторинг безопасности
        initSecurityMonitoring();
        
        // Проверяем авторизацию при загрузке
        const isAuth = await checkAuth();
        
        if (isAuth) {
            // Запускаем периодическую проверку
            startAuthCheck();
            // Обновляем UI
            updateUserInterface();
        }
        
        // Инициализируем обработчики событий
        initEventHandlers();
        
    } catch (error) {
        console.error('Ошибка инициализации авторизации:', error);
    }
}

// ============================================================================
// ОБРАБОТЧИКИ СОБЫТИЙ / EVENT HANDLERS
// ============================================================================

/**
 * Инициализация обработчиков событий
 */
function initEventHandlers() {
    // Обработчик формы входа
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    // Обработчик формы регистрации
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegisterSubmit);
    }
    
    // Обработчик формы верификации
    const verificationForm = document.getElementById('verificationForm');
    if (verificationForm) {
        verificationForm.addEventListener('submit', handleVerificationSubmit);
    }
    
    // Обработчики переключения форм
    initFormSwitchers();
    
    // Обработчики переключателей паролей
    initPasswordToggles();
    
    // Обработчики валидации в реальном времени
    initRealTimeValidation();
    
    // Обработчик кнопки повторной отправки кода
    const resendCodeBtn = document.getElementById('resendCodeBtn');
    if (resendCodeBtn) {
        resendCodeBtn.addEventListener('click', handleResendCode);
    }
    
    // Обработчик кнопки возврата к регистрации
    const backToRegisterBtn = document.getElementById('backToRegisterBtn');
    if (backToRegisterBtn) {
        backToRegisterBtn.addEventListener('click', handleBackToRegister);
    }
}

/**
 * Обработчик отправки формы входа
 */
async function handleLoginSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const username = formData.get('username');
    const password = formData.get('password');
    const rememberMe = formData.get('rememberMe');
    
    await login(username, password, !!rememberMe);
}

/**
 * Обработчик отправки формы регистрации
 */
async function handleRegisterSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const username = formData.get('username');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const agreeTerms = formData.get('agreeTerms');
    
    await register(username, email, password, confirmPassword, !!agreeTerms);
}

/**
 * Обработчик отправки формы верификации
 */
async function handleVerificationSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const code = formData.get('code');
    
    await verifyEmail(email, code);
}

/**
 * Обработчик повторной отправки кода
 */
async function handleResendCode() {
    const emailInput = document.getElementById('verificationEmail');
    if (emailInput && emailInput.value) {
        await resendCode(emailInput.value);
    } else {
        showError('Введите email адрес');
    }
}

/**
 * Обработчик возврата к регистрации
 */
function handleBackToRegister() {
    // Показываем переключатель форм
    const formSwitcher = document.querySelector('.form-switcher');
    if (formSwitcher) {
        formSwitcher.style.display = 'flex';
    }
    
    // Переключаемся на форму регистрации
    switchForm('register');
}

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ UI КОМПОНЕНТОВ / UI COMPONENTS INITIALIZATION
// ============================================================================

/**
 * Инициализация переключателей форм
 */
function initFormSwitchers() {
    const switchButtons = document.querySelectorAll('.switch-btn');
    
    switchButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (setLoading.isLoading) return;
            
            const targetForm = this.dataset.form;
            switchForm(targetForm);
        });
    });
}

/**
 * Инициализация переключателей видимости паролей
 */
function initPasswordToggles() {
    const passwordToggles = document.querySelectorAll('.password-toggle');
    
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const passwordInput = document.getElementById(targetId);
            
            if (passwordInput) {
                togglePasswordVisibility(passwordInput, this);
            }
        });
    });
}

/**
 * Инициализация валидации в реальном времени
 */
function initRealTimeValidation() {
    const inputs = document.querySelectorAll('.form-input');
    
    inputs.forEach(input => {
        input.addEventListener('blur', async function() {
            await validateFieldRealTime(this);
        });
        
        input.addEventListener('input', function() {
            clearFieldError(this);
        });
    });
    
    // Специальная валидация для подтверждения пароля
    const confirmPasswordInput = document.getElementById('confirmPassword');
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validatePasswordConfirmationRealTime();
        });
    }
}

// ============================================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ / HELPER FUNCTIONS
// ============================================================================

/**
 * Переключение видимости пароля
 */
function togglePasswordVisibility(input, toggleButton) {
    const icon = toggleButton.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
        toggleButton.title = 'Скрыть пароль';
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
        toggleButton.title = 'Показать пароль';
    }
}

/**
 * Валидация поля в реальном времени
 */
async function validateFieldRealTime(field) {
    const { validateForm } = await import('./auth-validation.js');
    const form = field.closest('form');
    if (form) {
        const formData = new FormData(form);
        const formType = form.id.replace('Form', '');
        const validation = validateForm(Object.fromEntries(formData), formType);
        
        if (!validation.isValid) {
            const fieldError = validation.errors.find(error => error.field === field.name);
            if (fieldError) {
                showFieldError(field, fieldError.message);
            }
        }
    }
}

/**
 * Валидация подтверждения пароля в реальном времени
 */
function validatePasswordConfirmationRealTime() {
    const password = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    
    if (password && confirmPassword && password.value && confirmPassword.value) {
        if (password.value !== confirmPassword.value) {
            showFieldError(confirmPassword, 'Пароли не совпадают');
        } else {
            clearFieldError(confirmPassword);
        }
    }
}

/**
 * Обновление интерфейса пользователя
 */
function updateUserInterface() {
    const user = getCurrentUser();
    if (!user) return;
    
    // Обновляем аватар пользователя
    const userAvatar = document.querySelector('.user-avatar');
    if (userAvatar) {
        userAvatar.innerHTML = `<i class="fas fa-user"></i>`;
        userAvatar.title = `Пользователь: ${user.username}`;
    }
    
    // Обновляем информацию в настройках
    const settingsContent = document.getElementById('settings');
    if (settingsContent) {
        settingsContent.innerHTML = `
            <div class="section">
                <h2>Настройки</h2>
                <div class="user-info">
                    <h3>Информация о пользователе</h3>
                    <p><strong>Имя пользователя:</strong> ${user.username}</p>
                    <p><strong>Email:</strong> ${user.email}</p>
                    <p><strong>ID:</strong> ${user.id}</p>
                    <p><strong>Последняя активность:</strong> ${formatDate(user.last_activity)}</p>
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

/**
 * Форматирование даты
 */
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU');
    } catch (error) {
        return 'Неизвестно';
    }
}

// ============================================================================
// ЭКСПОРТ ФУНКЦИЙ ДЛЯ ГЛОБАЛЬНОГО ДОСТУПА / EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================================

// Делаем функции доступными глобально
window.AuthManager = {
    initAuth,
    login,
    register,
    verifyEmail,
    logout,
    checkAuth,
    clearAuthData,
    redirectToAuth,
    resendCode,
    getCurrentUser,
    isAuthenticated
};

// Глобальные функции для использования в HTML
window.logout = logout;
window.initAuth = initAuth;
