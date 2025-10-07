// filename="auth.js"
// Модуль для управления формами авторизации и регистрации
// Module for managing authentication and registration forms

// ============================================================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ / GLOBAL VARIABLES
// ============================================================================

let currentForm = 'login'; // Текущая активная форма / Current active form
let isProcessing = false; // Флаг обработки для предотвращения повторных отправок / Processing flag to prevent duplicate submissions
let verificationTimer = null; // Таймер для кода верификации / Verification code timer
let verificationStartTime = null; // Время начала верификации / Verification start time
let pendingUserEmail = null; // Email пользователя ожидающего верификации / Pending verification user email

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ / INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 Модуль авторизации инициализирован');
    
    // Инициализация всех компонентов / Initialize all components
    initializeFormSwitcher();
    initializePasswordToggles();
    initializeFormValidation();
    initializeFormSubmissions();
    initializeVerificationForm();
    
    console.log('✅ Все компоненты авторизации готовы к работе');
});

// ============================================================================
// ПЕРЕКЛЮЧАТЕЛЬ ФОРМ / FORM SWITCHER
// ============================================================================

function initializeFormSwitcher() {
    const switchButtons = document.querySelectorAll('.switch-btn');
    const forms = document.querySelectorAll('.auth-form');
    
    switchButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (isProcessing) return; // Защита от переключения во время обработки / Prevent switching during processing
            
            const targetForm = this.dataset.form;
            
            if (targetForm === currentForm) return; // Уже активна / Already active
            
            // Переключение активной кнопки / Switch active button
            switchButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Переключение активной формы / Switch active form
            forms.forEach(form => {
                form.classList.remove('active');
                if (form.dataset.form === targetForm) {
                    form.classList.add('active');
                }
            });
            
            currentForm = targetForm;
            
            // Обновление подзаголовка / Update subtitle
            updateSubtitle(targetForm);
            
            // Очистка форм при переключении / Clear forms when switching
            clearForms();
            
            // Остановка таймера верификации при переключении / Stop verification timer when switching
            if (verificationTimer) {
                clearInterval(verificationTimer);
                verificationTimer = null;
            }
            
            console.log(`🔄 Переключено на форму: ${targetForm}`);
        });
    });
}

function updateSubtitle(formType) {
    const subtitle = document.querySelector('.auth-subtitle');
    if (subtitle) {
        if (formType === 'login') {
            subtitle.textContent = 'Войдите в систему для управления менеджерами';
        } else if (formType === 'register') {
            subtitle.textContent = 'Создайте аккаунт для доступа к системе управления';
        } else if (formType === 'verification') {
            subtitle.textContent = 'Подтвердите email для завершения регистрации';
        }
    }
}

// ============================================================================
// ПЕРЕКЛЮЧАТЕЛИ ПАРОЛЕЙ / PASSWORD TOGGLES
// ============================================================================

function initializePasswordToggles() {
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

// ============================================================================
// ВАЛИДАЦИЯ ФОРМ / FORM VALIDATION
// ============================================================================

function initializeFormValidation() {
    // Валидация в реальном времени / Real-time validation
    const inputs = document.querySelectorAll('.form-input');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            clearFieldError(this);
        });
    });
    
    // Специальная валидация для подтверждения пароля / Special validation for password confirmation
    const confirmPasswordInput = document.getElementById('confirmPassword');
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validatePasswordConfirmation();
        });
    }
}

function validateField(field) {
    const value = field.value.trim();
    const fieldType = field.type;
    const fieldName = field.name;
    
    clearFieldError(field);
    
    // Общие проверки / General checks
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'Это поле обязательно для заполнения');
        return false;
    }
    
    // Специфичные проверки / Specific checks
    switch (fieldType) {
        case 'email':
            if (value && !isValidEmail(value)) {
                showFieldError(field, 'Введите корректный email адрес');
                return false;
            }
            break;
        case 'password':
            if (value && !isValidPassword(value)) {
                showFieldError(field, 'Пароль должен содержать минимум 6 символов');
                return false;
            }
            break;
        case 'text':
            if (fieldName === 'username' && value && !isValidUsername(value)) {
                showFieldError(field, 'Имя пользователя должно содержать 3-20 символов (буквы, цифры, _)');
                return false;
            }
            break;
    }
    
    return true;
}

function validatePasswordConfirmation() {
    const password = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    
    if (password && confirmPassword && password.value && confirmPassword.value) {
        if (password.value !== confirmPassword.value) {
            showFieldError(confirmPassword, 'Пароли не совпадают');
            return false;
        } else {
            clearFieldError(confirmPassword);
        }
    }
    
    return true;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPassword(password) {
    return password.length >= 6;
}

function isValidUsername(username) {
    const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
    return usernameRegex.test(username);
}

function showFieldError(field, message) {
    field.classList.add('error');
    
    // Удаляем старое сообщение об ошибке / Remove old error message
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Добавляем новое сообщение об ошибке / Add new error message
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    errorElement.style.cssText = 'color: #dc3545; font-size: 12px; margin-top: 5px; font-weight: 500;';
    
    field.parentNode.appendChild(errorElement);
}

function clearFieldError(field) {
    field.classList.remove('error');
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// ============================================================================
// ОТПРАВКА ФОРМ / FORM SUBMISSIONS
// ============================================================================

function initializeFormSubmissions() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegisterSubmit);
    }
}

function handleLoginSubmit(e) {
    e.preventDefault();
    
    if (isProcessing) return;
    
    const formData = new FormData(e.target);
    const username = formData.get('username');
    const password = formData.get('password');
    const rememberMe = formData.get('rememberMe');
    
    // Валидация / Validation
    if (!validateLoginForm(username, password)) {
        return;
    }
    
    // Показываем индикатор загрузки / Show loading indicator
    setProcessingState(true);
    
    // Отправка запроса на сервер / Send request to server
    apiLogin(username, password)
        .then(response => {
            showNotification('Успешный вход в систему!', 'success');
            console.log('✅ Успешная авторизация:', response);
            
            // Сохраняем данные пользователя и токен сессии / Save user data and session token
            if (response.user) {
                localStorage.setItem('user', JSON.stringify(response.user));
            }
            
            if (response.session_token) {
                localStorage.setItem('session_token', response.session_token);
            }
            
            // Редирект на основное приложение / Redirect to main app
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        })
        .catch(error => {
            showNotification('Ошибка авторизации: ' + error.message, 'error');
            console.error('❌ Ошибка авторизации:', error);
        })
        .finally(() => {
            setProcessingState(false);
        });
}

function handleRegisterSubmit(e) {
    e.preventDefault();
    
    if (isProcessing) return;
    
    const formData = new FormData(e.target);
    const username = formData.get('username');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const agreeTerms = formData.get('agreeTerms');
    
    // Валидация / Validation
    if (!validateRegisterForm(username, email, password, confirmPassword, agreeTerms)) {
        return;
    }
    
    // Показываем индикатор загрузки / Show loading indicator
    setProcessingState(true);
    
    // Отправка запроса на сервер / Send request to server
    apiRegister(username, email, password)
        .then(response => {
            showNotification('Регистрация успешна! Проверьте email для подтверждения аккаунта.', 'success');
            console.log('✅ Успешная регистрация:', response);
            
            // Сохраняем email для верификации / Save email for verification
            pendingUserEmail = email;
            
            // Переключаемся на форму верификации / Switch to verification form
            switchToVerificationForm(email);
        })
        .catch(error => {
            showNotification('Ошибка регистрации: ' + error.message, 'error');
            console.error('❌ Ошибка регистрации:', error);
        })
        .finally(() => {
            setProcessingState(false);
        });
}

function validateLoginForm(username, password) {
    let isValid = true;
    
    if (!username || !username.trim()) {
        showFieldError(document.getElementById('loginUsername'), 'Введите имя пользователя');
        isValid = false;
    }
    
    if (!password || !password.trim()) {
        showFieldError(document.getElementById('loginPassword'), 'Введите пароль');
        isValid = false;
    }
    
    return isValid;
}

function validateRegisterForm(username, email, password, confirmPassword, agreeTerms) {
    let isValid = true;
    
    // Валидация имени пользователя / Username validation
    if (!username || !username.trim()) {
        showFieldError(document.getElementById('registerUsername'), 'Введите имя пользователя');
        isValid = false;
    } else if (!isValidUsername(username)) {
        showFieldError(document.getElementById('registerUsername'), 'Имя пользователя должно содержать 3-20 символов (буквы, цифры, _)');
        isValid = false;
    }
    
    // Валидация email / Email validation
    if (!email || !email.trim()) {
        showFieldError(document.getElementById('registerEmail'), 'Введите email');
        isValid = false;
    } else if (!isValidEmail(email)) {
        showFieldError(document.getElementById('registerEmail'), 'Введите корректный email адрес');
        isValid = false;
    }
    
    // Валидация пароля / Password validation
    if (!password || !password.trim()) {
        showFieldError(document.getElementById('registerPassword'), 'Введите пароль');
        isValid = false;
    } else if (!isValidPassword(password)) {
        showFieldError(document.getElementById('registerPassword'), 'Пароль должен содержать минимум 6 символов');
        isValid = false;
    }
    
    // Валидация подтверждения пароля / Password confirmation validation
    if (!confirmPassword || !confirmPassword.trim()) {
        showFieldError(document.getElementById('confirmPassword'), 'Подтвердите пароль');
        isValid = false;
    } else if (password !== confirmPassword) {
        showFieldError(document.getElementById('confirmPassword'), 'Пароли не совпадают');
        isValid = false;
    }
    
    // Валидация согласия с условиями / Terms agreement validation
    if (!agreeTerms) {
        showNotification('Необходимо согласиться с условиями использования', 'error');
        isValid = false;
    }
    
    return isValid;
}

// ============================================================================
// СИМУЛЯЦИЯ API / API SIMULATION
// ============================================================================

// ============================================================================
// API ФУНКЦИИ / API FUNCTIONS
// ============================================================================

async function apiLogin(username, password) {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'Ошибка авторизации');
    }
    
    return data;
}

async function apiRegister(username, email, password) {
    const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            email: email,
            password: password
        })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'Ошибка регистрации');
    }
    
    return data;
}

async function apiVerifyEmail(email, code) {
    const response = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            email: email,
            code: code
        })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'Ошибка верификации');
    }
    
    return data;
}

async function apiResendVerificationCode(email) {
    const response = await fetch('/api/auth/resend-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            email: email
        })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'Ошибка повторной отправки кода');
    }
    
    return data;
}

// ============================================================================
// ФОРМА ВЕРИФИКАЦИИ / VERIFICATION FORM
// ============================================================================

function initializeVerificationForm() {
    const verificationForm = document.getElementById('verificationForm');
    const resendCodeBtn = document.getElementById('resendCodeBtn');
    const backToRegisterBtn = document.getElementById('backToRegisterBtn');
    
    if (verificationForm) {
        verificationForm.addEventListener('submit', handleVerificationSubmit);
    }
    
    if (resendCodeBtn) {
        resendCodeBtn.addEventListener('click', handleResendCode);
    }
    
    if (backToRegisterBtn) {
        backToRegisterBtn.addEventListener('click', handleBackToRegister);
    }
    
    // Автоматический ввод кода / Auto code input
    const verificationCodeInput = document.getElementById('verificationCode');
    if (verificationCodeInput) {
        verificationCodeInput.addEventListener('input', function(e) {
            // Автоматическая отправка при вводе 6 символов / Auto submit on 6 characters
            if (e.target.value.length === 6) {
                setTimeout(() => {
                    verificationForm.dispatchEvent(new Event('submit'));
                }, 500);
            }
        });
    }
}

function switchToVerificationForm(email) {
    // Скрываем переключатель форм / Hide form switcher
    const formSwitcher = document.querySelector('.form-switcher');
    if (formSwitcher) {
        formSwitcher.style.display = 'none';
    }
    
    // Переключаемся на форму верификации / Switch to verification form
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        form.classList.remove('active');
        if (form.dataset.form === 'verification') {
            form.classList.add('active');
        }
    });
    
    // Заполняем email / Fill email
    const verificationEmailInput = document.getElementById('verificationEmail');
    if (verificationEmailInput) {
        verificationEmailInput.value = email;
    }
    
    // Обновляем подзаголовок / Update subtitle
    updateSubtitle('verification');
    
    // Запускаем таймер / Start timer
    startVerificationTimer();
    
    currentForm = 'verification';
    console.log('🔄 Переключено на форму верификации');
}

function handleVerificationSubmit(e) {
    e.preventDefault();
    
    if (isProcessing) return;
    
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const code = formData.get('code');
    
    // Валидация / Validation
    if (!email || !code) {
        showNotification('Заполните все поля', 'error');
        return;
    }
    
    if (code.length !== 6) {
        showNotification('Код должен содержать 6 символов', 'error');
        return;
    }
    
    // Показываем индикатор загрузки / Show loading indicator
    setProcessingState(true);
    
    // Отправка запроса на сервер / Send request to server
    apiVerifyEmail(email, code)
        .then(response => {
            showNotification('Email успешно подтвержден! Теперь вы можете войти в систему.', 'success');
            console.log('✅ Успешная верификация:', response);
            
            // Останавливаем таймер / Stop timer
            if (verificationTimer) {
                clearInterval(verificationTimer);
                verificationTimer = null;
            }
            
            // Переключаемся на форму входа / Switch to login form
            setTimeout(() => {
                switchToForm('login');
                // Очищаем email из формы входа / Clear email from login form
                const loginUsernameInput = document.getElementById('loginUsername');
                if (loginUsernameInput) {
                    loginUsernameInput.value = email;
                }
            }, 2000);
        })
        .catch(error => {
            showNotification('Ошибка верификации: ' + error.message, 'error');
            console.error('❌ Ошибка верификации:', error);
        })
        .finally(() => {
            setProcessingState(false);
        });
}

function handleResendCode() {
    if (isProcessing || !pendingUserEmail) return;
    
    setProcessingState(true);
    
    apiResendVerificationCode(pendingUserEmail)
        .then(response => {
            showNotification('Новый код отправлен на ваш email', 'success');
            console.log('✅ Код повторно отправлен:', response);
            
            // Перезапускаем таймер / Restart timer
            startVerificationTimer();
        })
        .catch(error => {
            showNotification('Ошибка отправки кода: ' + error.message, 'error');
            console.error('❌ Ошибка повторной отправки:', error);
        })
        .finally(() => {
            setProcessingState(false);
        });
}

function handleBackToRegister() {
    if (isProcessing) return;
    
    // Останавливаем таймер / Stop timer
    if (verificationTimer) {
        clearInterval(verificationTimer);
        verificationTimer = null;
    }
    
    // Показываем переключатель форм / Show form switcher
    const formSwitcher = document.querySelector('.form-switcher');
    if (formSwitcher) {
        formSwitcher.style.display = 'flex';
    }
    
    // Переключаемся на форму регистрации / Switch to register form
    switchToForm('register');
    
    // Очищаем email / Clear email
    pendingUserEmail = null;
}

function startVerificationTimer() {
    // Останавливаем предыдущий таймер / Stop previous timer
    if (verificationTimer) {
        clearInterval(verificationTimer);
    }
    
    // Устанавливаем время начала / Set start time
    verificationStartTime = Date.now();
    const expiryTime = 24 * 60 * 60 * 1000; // 24 часа в миллисекундах / 24 hours in milliseconds
    
    // Обновляем таймер каждую секунду / Update timer every second
    verificationTimer = setInterval(() => {
        const elapsed = Date.now() - verificationStartTime;
        const remaining = expiryTime - elapsed;
        
        if (remaining <= 0) {
            clearInterval(verificationTimer);
            verificationTimer = null;
            
            // Показываем сообщение об истечении / Show expiry message
            showNotification('Время действия кода истекло. Запросите новый код.', 'warning');
            
            // Отключаем кнопку подтверждения / Disable verification button
            const verifyButton = document.querySelector('#verificationForm .auth-button');
            if (verifyButton) {
                verifyButton.disabled = true;
            }
            
            return;
        }
        
        // Форматируем оставшееся время / Format remaining time
        const hours = Math.floor(remaining / (1000 * 60 * 60));
        const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((remaining % (1000 * 60)) / 1000);
        
        const timeString = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Обновляем отображение таймера / Update timer display
        const timerElement = document.getElementById('timer');
        if (timerElement) {
            timerElement.textContent = timeString;
            
            // Добавляем предупреждение при малом времени / Add warning for low time
            const timerContainer = timerElement.closest('.verification-timer');
            if (remaining < 5 * 60 * 1000) { // Меньше 5 минут / Less than 5 minutes
                timerContainer.classList.add('warning');
            } else {
                timerContainer.classList.remove('warning');
            }
        }
    }, 1000);
}

// ============================================================================
// УТИЛИТЫ / UTILITIES
// ============================================================================

function setProcessingState(processing) {
    isProcessing = processing;
    
    const buttons = document.querySelectorAll('.auth-button');
    buttons.forEach(button => {
        if (processing) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    });
    
    // Блокируем переключатели форм / Block form switchers
    const switchButtons = document.querySelectorAll('.switch-btn');
    switchButtons.forEach(button => {
        button.disabled = processing;
    });
}

function switchToForm(formType) {
    const switchButton = document.querySelector(`[data-form="${formType}"]`);
    if (switchButton) {
        switchButton.click();
    }
}

function clearForms() {
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        form.reset();
        
        // Очищаем ошибки / Clear errors
        const inputs = form.querySelectorAll('.form-input');
        inputs.forEach(input => clearFieldError(input));
    });
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Добавляем стили для уведомления / Add notification styles
    notification.style.cssText = `
        background: ${getNotificationColor(type)};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        animation: slideInRight 0.3s ease;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    `;
    
    container.appendChild(notification);
    
    // Автоматическое удаление через 5 секунд / Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

function getNotificationColor(type) {
    const colors = {
        success: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
        error: 'linear-gradient(135deg, #dc3545 0%, #fd7e14 100%)',
        warning: 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)',
        info: 'linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%)'
    };
    return colors[type] || colors.info;
}

// ============================================================================
// ЭКСПОРТ ФУНКЦИЙ ДЛЯ ГЛОБАЛЬНОГО ДОСТУПА / EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================================

// Делаем функции доступными глобально для отладки / Make functions globally available for debugging
window.AuthModule = {
    switchToForm,
    clearForms,
    showNotification,
    validateField,
    setProcessingState
};
