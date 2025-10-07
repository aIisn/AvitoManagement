// filename="api.js"
// Модуль для всех операций с сервером (API)
// Module for all server operations (API)

// ============================================================================
// ИМПОРТЫ / IMPORTS
// ============================================================================

import { currentManager, currentUniquifyCategory, isProcessing, setIsProcessing, setCurrentPath } from './state.js';
import { renderCard, renderResultsTable } from './ui.js';

// ============================================================================
// ФУНКЦИИ ДЛЯ РАБОТЫ С ЛОГАМИ / LOG FUNCTIONS
// ============================================================================

// Функция для получения и отображения логов с сервера
// Function to fetch and display logs from server
export async function fetchLogs(manager = null) {
    const response = await fetch('/api/logs');
    const data = await response.json();
    // Находим элемент для отображения логов / Find element to display logs
    const logsElement = document.getElementById(`logs-${manager || 'global'}`);
    if (logsElement) {
        logsElement.textContent = data.logs.join('\n');
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛОВОЙ СИСТЕМОЙ / FILE SYSTEM FUNCTIONS
// ============================================================================

// Функция для загрузки и отображения сетки папок для менеджера
// Function to fetch and display folder grid for manager
export async function fetchManagerGrid(manager, gridId, path = '', dir_type = 'photo_cache') {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        setCurrentPath(manager, path);
        // Загружаем список файлов и папок / Fetch files and folders list
        const response = await fetch(`/api/list?manager=${manager}&dir=${dir_type}&path=${path}`);
        const data = await response.json();
        const grid = document.getElementById(gridId);
        
        // Специальная логика для корня photo_cache: парное отображение с ready_photos
        // Special logic for photo_cache root: paired display with ready_photos
        if (path === '' && dir_type === 'photo_cache') {
            // Фильтруем только директории / Filter directories only
            const photo_dirs = data.children.filter(node => node.type === 'dir');
            
            // Загружаем список готовых фото / Fetch ready photos list
            const ready_response = await fetch(`/api/list?manager=${manager}&dir=ready_photos&path=`);
            const ready_data = await ready_response.json();
            const ready_map = new Map(ready_data.children.filter(node => node.type === 'dir').map(node => [node.name, node]));
            
            // Единый fetch для всех counts / Single fetch for all counts
            const count_response = await fetch(`/api/count_ready?manager=${manager}`);
            const count_data = await count_response.json();
            const countMap = new Map(Object.entries(count_data.counts || {}));
            
            grid.innerHTML = '';
            
            // Отображаем каждую папку с фотографиями / Display each photo folder
            for (const photo_node of photo_dirs) {
                const row = document.createElement('div');
                row.classList.add('card-row');
                renderCard(photo_node, row, manager, path, 'photo_cache');
                
                // Если есть готовые фото, показываем связь / If ready photos exist, show link
                if (ready_map.has(photo_node.name)) {
                    row.classList.add('linked'); // Добавляем класс для обводки / Add class for border
                    const chain = document.createElement('span');
                    chain.classList.add('chain-icon');
                    chain.textContent = '🔗';
                    row.appendChild(chain);
                    
                    const category_path = photo_node.name;
                    const unique_node = {
                        name: photo_node.name,
                        type: 'dir-unique',
                        path: category_path,
                        count: countMap.get(category_path) || 0
                    };
                    renderCard(unique_node, row, manager, path, 'ready_photos');
                }
                grid.appendChild(row);
            }
        } else {
            // Обычная логика для поддиректорий или ready_photos
            // Standard logic for subdirectories or ready_photos
            grid.innerHTML = '';
            data.children.forEach(node => renderCard(node, grid, manager, path, dir_type));
        }
    } catch (error) {
        console.error(`Ошибка при загрузке сетки для ${manager}:`, error);
    } finally {
        setIsProcessing(false);
    }
    // Показываем секцию загрузки логотипа / Show logo upload section
    document.getElementById('logo-upload-section').style.display = 'block';
}

// ============================================================================
// ФУНКЦИИ ДЛЯ РАБОТЫ С ЛОГОТИПОМ / LOGO FUNCTIONS
// ============================================================================

// Функция загрузки логотипа для менеджера
// Function to upload logo for manager
export async function uploadLogo(manager) {
    const fileInput = document.getElementById('logo-input');
    const file = fileInput.files[0];
    
    // Проверка выбора файла / Check file selection
    if (!file) {
        alert('Выберите файл логотипа');
        return;
    }
    
    // Формируем данные для отправки / Prepare data for sending
    const formData = new FormData();
    formData.append('manager', manager);
    formData.append('logo', file);
    
    try {
        const response = await fetch('/api/upload_logo', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Логотип успешно загружен!');
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка загрузки логотипа:', error);
        alert('Ошибка загрузки');
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ УНИКАЛИЗАЦИИ / UNIQUIFICATION FUNCTIONS
// ============================================================================

// Функция запуска процесса уникализации фотографий
// Function to start photo uniquification process
export async function startUniquify() {
    // Получаем параметры уникализации / Get uniquification parameters
    const count = parseInt(document.getElementById('ad-count').value);
    const useRotation = document.getElementById('use-rotation').checked;
    
    // Валидация / Validation
    if (count < 1) {
        alert('Количество объявлений должно быть не менее 1');
        return;
    }
    
    // Закрываем модальное окно / Close modal window
    const { closeUniquifyModal } = await import('./ui.js');
    closeUniquifyModal();
    
    // Показываем индикатор прогресса / Show progress indicator
    const progressDiv = document.createElement('div');
    progressDiv.innerHTML = '<p>Уникализация в процессе...</p>';
    document.getElementById(`grid-${currentManager}`).after(progressDiv);
    
    try {
        // Отправляем запрос на сервер / Send request to server
        const response = await fetch('/api/uniquify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                manager: currentManager,
                folder_name: currentUniquifyCategory,
                count: count,
                use_rotation: useRotation
            })
        });
        const data = await response.json();
        
        if (data.success) {
            // Отображаем результаты / Display results
            renderResultsTable(data.results, currentManager);
            // Обновляем сетку папок / Refresh folder grid
            await fetchManagerGrid(currentManager, `grid-${currentManager}`);
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка уникализации:', error);
        alert(`Ошибка: ${error.message}`);
    } finally {
        // Удаляем индикатор прогресса / Remove progress indicator
        progressDiv.remove();
    }
}

// Функция получения ссылок для уникализированных объявлений
// Function to fetch links for uniquified ads
export async function fetchLinks(manager, category) {
    try {
        const response = await fetch(`/api/get_links?manager=${manager}&category=${category}`);
        const data = await response.json();
        
        if (data.success) {
            // Отображаем ссылки в таблице / Display links in table
            renderResultsTable(data.results, manager);
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка получения ссылок:', error);
        alert(`Ошибка: ${error.message}`);
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ МЕНЕДЖЕРАМИ / MANAGER MANAGEMENT FUNCTIONS
// ============================================================================

// Функция создания нового менеджера
// Function to create new manager
export async function createManager() {
    const name = document.getElementById('manager-name').value.trim();
    
    // Валидация имени / Validate name
    if (!name) {
        alert('Пожалуйста, введите имя менеджера');
        return;
    }
    
    try {
        const response = await fetch('/api/create-manager', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        const data = await response.json();
        
        if (data.success) {
            // Очищаем поле ввода / Clear input field
            document.getElementById('manager-name').value = '';
            // Обновляем список менеджеров / Refresh managers list
            await fetchManagers();
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка создания менеджера:', error);
    }
}

// Функция загрузки и отображения списка всех менеджеров
// Function to fetch and display list of all managers
export async function fetchManagers() {
    try {
        const response = await fetch('/api/managers');
        const managers = await response.json();
        const list = document.getElementById('manager-list');
        list.innerHTML = '';
        
        // Импортируем UI функции / Import UI functions
        const { loadManagerContent, showEditManagerModal } = await import('./ui.js');
        
        // Отображаем каждого менеджера / Display each manager
        managers.forEach(manager => {
            const item = document.createElement('li');
            item.classList.add('manager-item');
            
            // Имя менеджера (кликабельное) / Manager name (clickable)
            const nameSpan = document.createElement('span');
            nameSpan.textContent = manager;
            nameSpan.onclick = () => loadManagerContent(manager);
            item.appendChild(nameSpan);
            
            // Кнопка редактирования / Edit button
            const editBtn = document.createElement('button');
            editBtn.classList.add('edit-btn');
            editBtn.innerHTML = '✏️';
            editBtn.onclick = (e) => {
                e.stopPropagation();
                showEditManagerModal(manager);
            };
            item.appendChild(editBtn);
            list.appendChild(item);
        });
    } catch (error) {
        console.error('Ошибка загрузки менеджеров:', error);
    }
}

// Функция сохранения изменений при редактировании менеджера
// Function to save changes when editing manager
export async function saveManagerEdit() {
    const { currentEditManager, currentManager, setCurrentManager } = await import('./state.js');
    const { closeEditModal, loadManagerContent } = await import('./ui.js');
    const newName = document.getElementById('edit-manager-name').value.trim();
    
    // Если имя не изменилось, просто закрываем модал / If name unchanged, just close modal
    if (!newName || newName === currentEditManager) {
        closeEditModal();
        return;
    }
    
    // Подтверждение переименования / Confirm renaming
    if (confirm(`Переименовать менеджера '${currentEditManager}' в '${newName}'?`)) {
        try {
            const response = await fetch('/api/rename-manager', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({old_name: currentEditManager, new_name: newName})
            });
            const data = await response.json();
            
            if (data.success) {
                closeEditModal();
                // Обновляем список менеджеров / Refresh managers list
                await fetchManagers();
                
                // Если переименованный менеджер был активным, обновляем контент
                // If renamed manager was active, update content
                if (currentManager === currentEditManager) {
                    loadManagerContent(newName);
                    setCurrentManager(newName);
                }
            } else {
                alert(`Ошибка: ${data.error}`);
            }
        } catch (error) {
            console.error('Ошибка переименования менеджера:', error);
            alert(`Ошибка: ${error.message}`);
        }
    }
}

// Функция подтверждения и выполнения удаления менеджера
// Function to confirm and execute manager deletion
export async function deleteManagerConfirm() {
    const { currentEditManager, currentManager, setCurrentManager } = await import('./state.js');
    const { closeEditModal } = await import('./ui.js');
    
    // Подтверждение удаления (необратимое действие) / Confirm deletion (irreversible action)
    if (confirm(`Удалить менеджера '${currentEditManager}' и все его данные? Это действие нельзя отменить!`)) {
        try {
            const response = await fetch('/api/delete-manager', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: currentEditManager})
            });
            const data = await response.json();
            
            if (data.success) {
                closeEditModal();
                // Обновляем список менеджеров / Refresh managers list
                await fetchManagers();
                
                // Если удалённый менеджер был активным, очищаем контент
                // If deleted manager was active, clear content
                if (currentManager === currentEditManager) {
                    document.getElementById('manager-content').innerHTML = '';
                    setCurrentManager(null);
                }
            } else {
                alert(`Ошибка: ${data.error}`);
            }
        } catch (error) {
            console.error('Ошибка удаления менеджера:', error);
            alert(`Ошибка: ${error.message}`);
        }
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ ГЛАВНОЙ СТРАНИЦЫ / MAIN PAGE FUNCTIONS
// ============================================================================

// Функция загрузки менеджеров для главной страницы
// Function to fetch managers for main page
export async function fetchManagersForMain() {
    try {
        const response = await fetch('/api/managers');
        const managers = await response.json();
        
        // Импортируем UI функцию для рендеринга / Import UI function for rendering
        const { renderManagerCards } = await import('./ui.js');
        renderManagerCards(managers);
    } catch (error) {
        console.error('Ошибка загрузки менеджеров для главной страницы:', error);
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ СОЗДАНИЯ СТРУКТУРЫ ПАПОК / FOLDER STRUCTURE FUNCTIONS
// ============================================================================

// Функция создания структуры папок и загрузки файлов
// Function to create folder structure and upload files
export async function createFolderStructure(manager, categoryName) {
    const { isProcessing, setIsProcessing, selectedFiles } = await import('./state.js');
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    
    // Получаем все позиции из DOM / Get all positions from DOM
    const positions = Array.from(document.querySelectorAll(`#position-row-${manager} .position-tile`)).map(tile => tile.dataset.position);
    
    // Получаем элементы для прогресс-бара / Get progress bar elements
    const createButton = document.getElementById('create-button');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    // Настраиваем UI для отображения прогресса / Setup UI for progress display
    createButton.disabled = true;
    progressContainer.style.display = 'block';
    progressText.textContent = 'Создание структуры папок...';
    progressFill.style.width = '0%';
    
    // Инициализируем прогресс / Initialize progress
    let currentProgress = 0;
    const totalSteps = positions.length * 2 + 1; // Создание папок + загрузка файлов + финализация / Create folders + upload files + finalization
    try {
        // ШАГ 1: Создание структуры папок на сервере / STEP 1: Create folder structure on server
        progressText.textContent = 'Создание структуры папок...';
        const folderResponse = await fetch('/api/create-folder-structure', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({manager, category: categoryName, positions})
        });
        const folderData = await folderResponse.json();
        
        if (!folderData.success) {
            throw new Error(`Ошибка создания структуры: ${folderData.error}`);
        }
        
        // Обновляем прогресс / Update progress
        currentProgress += 100 / totalSteps;
        progressFill.style.width = `${currentProgress}%`;
        
        // ШАГ 2: Загрузка файлов для каждой позиции / STEP 2: Upload files for each position
        let uploadSuccess = true;
        for (let pos of positions) {
            progressText.textContent = `Загрузка файлов для позиции ${pos}...`;
            const files = selectedFiles[manager][pos] || [];
            
            if (files.length > 0) {
                // Формируем multipart/form-data для загрузки / Prepare multipart/form-data for upload
                const formData = new FormData();
                formData.append('manager', manager);
                formData.append('category', categoryName);
                formData.append('position', pos);
                
                for (let file of files) {
                    formData.append('files', file);
                }
                
                try {
                    const uploadResponse = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const uploadData = await uploadResponse.json();
                    
                    if (!uploadData.success) {
                        console.error(`Ошибка загрузки для позиции ${pos}: ${uploadData.error}`);
                        uploadSuccess = false;
                    }
                } catch (error) {
                    console.error(`Ошибка загрузки для позиции ${pos}:`, error);
                    uploadSuccess = false;
                }
            }
            
            // Обновляем прогресс после каждой позиции / Update progress after each position
            currentProgress += 100 / totalSteps;
            progressFill.style.width = `${Math.min(currentProgress, 100)}%`;
        }
        
        // ШАГ 3: Завершение процесса / STEP 3: Finalization
        progressText.textContent = 'Завершение...';
        await new Promise(resolve => setTimeout(resolve, 500));
        progressFill.style.width = '100%';
        
        const { closeModal, initPositionRow } = await import('./ui.js');
        const { resetManagerState } = await import('./state.js');
        closeModal();
        // Обработка успешного завершения / Handle successful completion
        if (uploadSuccess) {
            // Обновляем сетку папок / Refresh folder grid
            await fetchManagerGrid(manager, `grid-${manager}`);
            
            // Показываем уведомление об успехе / Show success notification
            const successDiv = document.createElement('div');
            successDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
                z-index: 1001;
                animation: slideInRight 0.5s ease;
                font-weight: 500;
            `;
            const totalFiles = positions.reduce((sum, pos) => sum + (selectedFiles[manager][pos] ? selectedFiles[manager][pos].length : 0), 0);
            successDiv.innerHTML = `
                ✅ <strong>Успешно!</strong><br>
                Структура создана и ${totalFiles} файлов загружено
            `;
            document.body.appendChild(successDiv);
            setTimeout(() => successDiv.remove(), 5000);
            
            // Очищаем форму / Clear form
            document.getElementById(`category-name-${manager}`).value = '';
            document.querySelectorAll(`#position-row-${manager} .thumbnail-container`).forEach(c => c.innerHTML = '');
            document.querySelectorAll(`#position-row-${manager} .position-tile`).forEach(t => {
                const badge = t.querySelector('.count-badge');
                if (badge) badge.remove();
            });
            
            // Сбрасываем состояние / Reset state
            resetManagerState(manager);
            
            // Создаём первую позицию заново / Recreate first position
            document.getElementById(`position-row-${manager}`).innerHTML = `
                <div class="position-tile active" data-position="1">
                    <button class="clear-photos" onclick="clearPhotos(1, '${manager}')" title="Очистить фотографии">🧹</button>
                    <button class="delete-position" onclick="deletePosition(1, '${manager}')" title="Удалить позицию">🗑️</button>
                    <div class="tile-header">
                        <div class="position-number">1</div>
                        <div class="position-label">Фото для 1-й позиции</div>
                    </div>
                    <div class="thumbnail-container" id="thumbnails-1-${manager}"></div>
                    <button class="upload-button" onclick="openFileInput(1, '${manager}')">Загрузить изображения</button>
                    <input type="file" multiple class="file-input" accept="image/*" style="display: none;">
                </div>
            `;
            initPositionRow(manager);
        } else {
            // Обработка частичного успеха (структура создана, но ошибки при загрузке)
            // Handle partial success (structure created but upload errors)
            const warningDiv = document.createElement('div');
            warningDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ffc107;
                color: #333;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
                z-index: 1001;
                animation: slideInRight 0.5s ease;
                font-weight: 500;
            `;
            warningDiv.innerHTML = `
                ⚠️ <strong>Предупреждение</strong><br>
                Структура создана, но проблемы с загрузкой файлов. Проверьте логи.
            `;
            document.body.appendChild(warningDiv);
            setTimeout(() => warningDiv.remove(), 5000);
        }
    } catch (error) {
        // Обработка критических ошибок / Handle critical errors
        console.error('Ошибка в createFolderStructure:', error);
        progressText.textContent = 'Ошибка!';
        progressFill.style.background = '#dc3545';
        
        const { closeModal } = await import('./ui.js');
        setTimeout(() => {
            closeModal();
            alert(`Ошибка: ${error.message}`);
        }, 1500);
    } finally {
        // Всегда снимаем блокировку / Always remove lock
        setIsProcessing(false);
    }
}

