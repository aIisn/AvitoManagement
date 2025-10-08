// filename="auth-ui.js"
// Модуль управления UI для авторизации
// Authentication UI management module

// ============================================================================
// ФУНКЦИИ УПРАВЛЕНИЯ UI / UI MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Показать уведомление об ошибке
 * @param {string} message - Сообщение об ошибке
 * @param {string} type - Тип уведомления ('error', 'warning', 'info')
 */
export function showError(message, type = 'error') {
    showNotification(message, type);
}

/**
 * Показать уведомление об успехе
 * @param {string} message - Сообщение об успехе
 */
export function showSuccess(message) {
    showNotification(message, 'success');
}

/**
 * Показать уведомление
 * @param {string} message - Текст сообщения
 * @param {string} type - Тип уведомления
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) {
        console.warn('Контейнер уведомлений не найден');
        return;
    }
    
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
    
    // Стили для уведомления
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
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Управление состоянием загрузки
 * @param {boolean} state - Состояние загрузки (true - показать, false - скрыть)
 */
export function setLoading(state) {
    const buttons = document.querySelectorAll('.auth-button');
    const switchButtons = document.querySelectorAll('.switch-btn');
    
    buttons.forEach(button => {
        if (state) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    });
    
    // Блокируем переключатели форм
    switchButtons.forEach(button => {
        button.disabled = state;
    });
}

/**
 * Переключение между формами авторизации
 * @param {string} formType - Тип формы ('login', 'register', 'verification')
 */
export function switchForm(formType) {
    // Скрываем все формы
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        form.classList.remove('active');
    });
    
    // Показываем нужную форму
    const targetForm = document.querySelector(`[data-form="${formType}"]`);
    if (targetForm) {
        targetForm.classList.add('active');
    }
    
    // Обновляем активные кнопки переключения
    const switchButtons = document.querySelectorAll('.switch-btn');
    switchButtons.forEach(button => {
        button.classList.remove('active');
        if (button.dataset.form === formType) {
            button.classList.add('active');
        }
    });
    
    // Обновляем подзаголовок
    updateSubtitle(formType);
    
    // Очищаем формы при переключении
    clearForms();
}

/**
 * Показать ошибку поля
 * @param {HTMLElement} field - Поле для показа ошибки
 * @param {string} message - Сообщение об ошибке
 */
export function showFieldError(field, message) {
    if (!field) return;
    
    field.classList.add('error');
    
    // Удаляем старое сообщение об ошибке
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Добавляем новое сообщение об ошибке
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    errorElement.style.cssText = 'color: #dc3545; font-size: 12px; margin-top: 5px; font-weight: 500;';
    
    field.parentNode.appendChild(errorElement);
}

/**
 * Очистить ошибку поля
 * @param {HTMLElement} field - Поле для очистки ошибки
 */
export function clearFieldError(field) {
    if (!field) return;
    
    field.classList.remove('error');
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// ============================================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ / HELPER FUNCTIONS
// ============================================================================

/**
 * Получить иконку для типа уведомления
 * @param {string} type - Тип уведомления
 * @returns {string} - CSS класс иконки
 */
function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

/**
 * Получить цвет для типа уведомления
 * @param {string} type - Тип уведомления
 * @returns {string} - CSS градиент
 */
function getNotificationColor(type) {
    const colors = {
        success: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
        error: 'linear-gradient(135deg, #dc3545 0%, #fd7e14 100%)',
        warning: 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)',
        info: 'linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%)'
    };
    return colors[type] || colors.info;
}

/**
 * Обновить подзаголовок
 * @param {string} formType - Тип формы
 */
function updateSubtitle(formType) {
    const subtitle = document.querySelector('.auth-subtitle');
    if (!subtitle) return;
    
    const subtitles = {
        login: 'Войдите в систему для управления менеджерами',
        register: 'Создайте аккаунт для доступа к системе управления',
        verification: 'Подтвердите email для завершения регистрации'
    };
    
    subtitle.textContent = subtitles[formType] || subtitles.login;
}

/**
 * Очистить все формы
 */
function clearForms() {
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        form.reset();
        
        // Очищаем ошибки
        const inputs = form.querySelectorAll('.form-input');
        inputs.forEach(input => clearFieldError(input));
    });
}
