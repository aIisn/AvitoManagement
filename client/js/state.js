// filename="state.js"
// Модуль управления глобальным состоянием приложения
// Global application state management module

// ============================================================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ / GLOBAL VARIABLES
// ============================================================================

// Глобальные переменные для управления состоянием
// Global variables for state management
export let currentPaths = {}; // {manager: path} - Текущие пути для каждого менеджера / Current paths for each manager
export let currentManager = null; // Текущий выбранный менеджер / Currently selected manager
export let selectedFiles = {}; // {manager: {position: files[]}} - Выбранные файлы по позициям / Selected files by position
export let positionCounts = {}; // {manager: count} - Количество позиций для менеджера / Position count for each manager
export let isProcessing = false; // Флаг блокировки во время обработки / Processing lock flag
export let currentEditManager = null; // Менеджер, который редактируется / Manager being edited
export let currentUniquifyCategory = null; // Категория для уникализации / Category for uniquification

// ============================================================================
// ФУНКЦИИ ОБНОВЛЕНИЯ СОСТОЯНИЯ / STATE UPDATE FUNCTIONS
// ============================================================================

// Установить текущего менеджера / Set current manager
export function setCurrentManager(manager) {
    currentManager = manager;
}

// Установить менеджера для редактирования / Set manager for editing
export function setCurrentEditManager(manager) {
    currentEditManager = manager;
}

// Установить категорию для уникализации / Set category for uniquification
export function setCurrentUniquifyCategory(category) {
    currentUniquifyCategory = category;
}

// Установить флаг обработки / Set processing flag
export function setIsProcessing(value) {
    isProcessing = value;
}

// Установить текущий путь для менеджера / Set current path for manager
export function setCurrentPath(manager, path) {
    currentPaths[manager] = path;
}

// Инициализировать состояние менеджера / Initialize manager state
export function initManagerState(manager) {
    positionCounts[manager] = 1;
    selectedFiles[manager] = {1: []};
}

// Сбросить состояние менеджера / Reset manager state
export function resetManagerState(manager) {
    selectedFiles[manager] = {};
    positionCounts[manager] = 1;
}

// ============================================================================
// УТИЛИТЫ ДЛЯ РАБОТЫ С БУФЕРОМ ОБМЕНА / CLIPBOARD UTILITIES
// ============================================================================

// Копировать текст в буфер обмена с поддержкой fallback
// Copy text to clipboard with fallback support
export function copyToClipboard(text, button) {
    // Попытка использовать современный Clipboard API / Try to use modern Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            // Успешное копирование / Successful copy
            button.textContent = 'Скопировано!';
            setTimeout(() => { button.textContent = 'Скопировать ссылки'; }, 2000);
        }).catch(err => {
            console.error('Ошибка clipboard API:', err);
            // При ошибке используем fallback / On error use fallback
            fallbackCopy(text, button);
        });
    } else {
        // Если API недоступен, используем fallback / If API unavailable, use fallback
        fallbackCopy(text, button);
    }
}

// Резервный метод копирования (для старых браузеров)
// Fallback copy method (for older browsers)
export function fallbackCopy(text, button) {
    // Создаём временный textarea элемент / Create temporary textarea element
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        // Используем устаревшую команду execCommand / Use deprecated execCommand
        document.execCommand('copy');
        button.textContent = 'Скопировано!';
        setTimeout(() => { button.textContent = 'Скопировать ссылки'; }, 2000);
    } catch (err) {
        console.error('Ошибка fallback копирования:', err);
        alert('Ошибка при копировании в буфер обмена');
    }
    // Удаляем временный элемент / Remove temporary element
    document.body.removeChild(textArea);
}

