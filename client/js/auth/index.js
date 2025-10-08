// filename="index.js"
// Главный экспорт модулей авторизации
// Main export for authentication modules

// Экспорт всех функций из модулей
export * from './auth-core.js';
export * from './auth-security.js';
export * from './auth-validation.js';
export * from './auth-ui.js';
export * from './auth-utils.js';
export * from './auth-manager.js';

// Основные функции для быстрого доступа
export { 
    initAuth,
    login,
    register,
    verifyEmail,
    logout,
    checkAuth,
    clearAuthData,
    redirectToAuth,
    resendCode
} from './auth-manager.js';
