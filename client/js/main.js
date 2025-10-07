// filename="main.js"
// Главный файл приложения - инициализация и обработчики событий
// Main application file - initialization and event handlers

// ============================================================================
// ИМПОРТЫ / IMPORTS
// ============================================================================

// Импорт состояния / Import state
import { currentManager } from './state.js';

// Импорт API функций / Import API functions
import { 
    fetchManagers,      // Загрузка списка менеджеров / Fetch managers list
    fetchLogs,          // Загрузка логов / Fetch logs
    createManager,      // Создание менеджера / Create manager
    uploadLogo,         // Загрузка логотипа / Upload logo
    startUniquify,      // Запуск уникализации / Start uniquification
    saveManagerEdit,    // Сохранение редактирования / Save manager edit
    deleteManagerConfirm // Подтверждение удаления / Delete confirmation
} from './api.js';

// Импорт UI функций / Import UI functions
import { 
    closeUniquifyModal,  // Закрытие модала уникализации / Close uniquify modal
    closeEditModal,      // Закрытие модала редактирования / Close edit modal
    closeModal,          // Закрытие основного модала / Close main modal
    addPosition,         // Добавление позиции / Add position
    deletePosition,      // Удаление позиции / Delete position
    clearPhotos,         // Очистка фотографий / Clear photos
    openFileInput,       // Открытие выбора файлов / Open file input
    showConfirmModal     // Показ модала подтверждения / Show confirm modal
} from './ui.js';

// ============================================================================
// ЭКСПОРТ ФУНКЦИЙ В ГЛОБАЛЬНУЮ ОБЛАСТЬ / EXPORT FUNCTIONS TO GLOBAL SCOPE
// ============================================================================
// Необходимо для использования в onclick атрибутах HTML
// Required for use in HTML onclick attributes

window.createManager = createManager;
window.uploadLogo = uploadLogo;
window.startUniquify = startUniquify;
window.closeUniquifyModal = closeUniquifyModal;
window.saveManagerEdit = saveManagerEdit;
window.deleteManagerConfirm = deleteManagerConfirm;
window.closeEditModal = closeEditModal;
window.addPosition = addPosition;
window.deletePosition = deletePosition;
window.clearPhotos = clearPhotos;
window.openFileInput = openFileInput;
window.showConfirmModal = showConfirmModal;
window.closeModal = closeModal;

// ============================================================================
// ОБРАБОТЧИКИ СОБЫТИЙ / EVENT HANDLERS
// ============================================================================

// Обработчик клика вне модального окна для его закрытия
// Click handler outside modal window to close it
window.onclick = function(event) {
    const confirmModal = document.getElementById('confirm-modal');
    const editModal = document.getElementById('edit-manager-modal');
    
    // Закрываем модальное окно при клике на фон / Close modal when clicking on background
    if (event.target === confirmModal) {
        closeModal();
    } else if (event.target === editModal) {
        closeEditModal();
    }
}

// Обработчик вкладок / Tab handler
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.tab-link').forEach(tab => {
        tab.addEventListener('click', function() {
            // Убираем активный класс со всех вкладок и содержимого
            // Remove active class from all tabs and content
            document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Добавляем активный класс на выбранную вкладку
            // Add active class to selected tab
            this.classList.add('active');
            document.getElementById(this.dataset.tab).classList.add('active');
            
            // При переходе на вкладку уникализации загружаем менеджеров
            // When switching to uniquification tab, load managers
            if (this.dataset.tab === 'photo-uniquification') {
                fetchManagers();
            }
        });
    });
});

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ / INITIALIZATION
// ============================================================================

// Инициализация при загрузке страницы / Initialization on page load
window.onload = () => {
    // Автоматическое обновление логов каждые 2 секунды
    // Automatic log updates every 2 seconds
    setInterval(() => {
        if (currentManager) fetchLogs(currentManager);
    }, 2000);
};

