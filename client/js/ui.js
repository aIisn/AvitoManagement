// filename="ui.js"
// Модуль для всех UI-операций (рендеринг, модальные окна, DOM манипуляции)
// Module for all UI operations (rendering, modal windows, DOM manipulation)

// ============================================================================
// ИМПОРТЫ / IMPORTS
// ============================================================================

import { 
    currentManager, 
    currentEditManager,
    selectedFiles, 
    positionCounts, 
    isProcessing, 
    setIsProcessing,
    setCurrentManager,
    setCurrentEditManager,
    setCurrentUniquifyCategory,
    initManagerState,
    copyToClipboard 
} from './state.js';
import { fetchManagerGrid, fetchLinks, fetchLogs } from './api.js';

// ============================================================================
// ФУНКЦИИ РЕНДЕРИНГА КАРТОЧЕК / CARD RENDERING FUNCTIONS
// ============================================================================

// Функция рендеринга карточки файла или папки
// Function to render file or folder card
export function renderCard(node, parentElement, manager, path, dir_type) {
    // Создаём основной элемент карточки / Create main card element
    const card = document.createElement('div');
    card.classList.add('card', node.type);
    if (node.type === 'dir-unique') {
        card.classList.add('unique');
    }
    
    // Добавляем имя / Add name
    const name = document.createElement('div');
    name.classList.add('name');
    name.textContent = node.name;
    card.appendChild(name);
    
    // Формируем полный путь / Build full path
    const fullPath = path ? `${path}/${node.name}` : node.name;
    
    // Добавляем обработчик клика для директорий / Add click handler for directories
    if (node.type.startsWith('dir')) {
        card.onclick = async (e) => {
            if (e.target.tagName === 'BUTTON') return; // Игнорируем клики по кнопкам / Ignore button clicks
            const target_dir = (node.type === 'dir-unique') ? 'ready_photos' : dir_type;
            await fetchManagerGrid(manager, `grid-${manager}`, fullPath, target_dir);
        };
    }
    
    let leftBtn = null;
    
    // Кнопка "Уникализировать" для исходных папок
    // "Uniquify" button for original folders
    if (path === '' && dir_type === 'photo_cache' && node.type === 'dir') {
        leftBtn = document.createElement('button');
        leftBtn.textContent = 'Уникализировать';
        leftBtn.classList.add('uniquify-btn', 'btn-common');
        leftBtn.onclick = (e) => {
            e.stopPropagation();
            showUniquifyModal(manager, node.name);
        };
    }
    
    // Кнопка "Показать ссылки" для готовых папок
    // "Show links" button for ready folders
    if (node.type === 'dir-unique') {
        leftBtn = document.createElement('button');
        leftBtn.textContent = 'Показать ссылки';
        leftBtn.classList.add('get-links-btn', 'btn-common');
        leftBtn.onclick = (e) => {
            e.stopPropagation();
            fetchLinks(manager, node.name);
        };
    }
    
    // Кнопка удаления / Delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = 'Удалить';
    deleteBtn.classList.add('delete', 'btn-common');
    deleteBtn.onclick = async (e) => {
        e.stopPropagation();
        if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
        setIsProcessing(true);
        try {
            // Подтверждение удаления / Confirm deletion
            if (confirm(`Вы уверены, что хотите удалить "${node.name}"? Это действие нельзя отменить.\nВсе файлы в папке будут удалены!`)) {
                const target_dir = (node.type === 'dir-unique') ? 'ready_photos' : dir_type;
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({manager, dir: target_dir, path: fullPath})
                });
                const data = await response.json();
                
                if (data.success) {
                    // Удаляем карточку из DOM / Remove card from DOM
                    parentElement.removeChild(card);
                    // Обновляем сетку / Refresh grid
                    await fetchManagerGrid(manager, `grid-${manager}`, path, dir_type);
                } else {
                    alert(`Ошибка: ${data.error}`);
                }
            }
        } catch (error) {
            console.error('Ошибка при удалении:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            setIsProcessing(false);
        }
    };
    
    // Общий контейнер для кнопок / Common container for buttons
    const buttonContainer = document.createElement('div');
    buttonContainer.classList.add('button-container');
    if (leftBtn) {
        buttonContainer.appendChild(leftBtn);
    }
    buttonContainer.appendChild(deleteBtn);
    card.appendChild(buttonContainer);
    
    // Добавляем бейдж с количеством для уникальных папок
    // Add count badge for unique folders
    if (node.count !== undefined) {
        const badge = document.createElement('div');
        badge.classList.add('count-badge');
        badge.textContent = `${node.count} адс`;
        card.appendChild(badge);
    }
    
    // Добавляем карточку в родительский элемент / Add card to parent element
    parentElement.appendChild(card);
}

// ============================================================================
// ФУНКЦИИ МОДАЛЬНЫХ ОКОН / MODAL WINDOW FUNCTIONS
// ============================================================================

// Функция показа модального окна для уникализации
// Function to show uniquification modal window
export function showUniquifyModal(manager, category) {
    setCurrentManager(manager);
    setCurrentUniquifyCategory(category);
    // Устанавливаем значения по умолчанию / Set default values
    document.getElementById('ad-count').value = 1;
    document.getElementById('use-rotation').checked = true;
    document.getElementById('uniquify-modal').style.display = 'block';
}

// Функция закрытия модального окна для уникализации
// Function to close uniquification modal window
export function closeUniquifyModal() {
    document.getElementById('uniquify-modal').style.display = 'none';
}

// ============================================================================
// ФУНКЦИИ РЕНДЕРИНГА РЕЗУЛЬТАТОВ / RESULTS RENDERING FUNCTIONS
// ============================================================================

// Функция рендеринга таблицы с результатами уникализации
// Function to render table with uniquification results
export function renderResultsTable(results, manager) {
    // Удаляем предыдущую таблицу результатов, если она существует
    // Remove previous results table if it exists
    const existingTable = document.getElementById(`results-table-${manager}`);
    if (existingTable) {
        existingTable.remove();
    }
    
    // Создаём секцию для таблицы / Create section for table
    const tableSection = document.createElement('div');
    tableSection.classList.add('section');
    tableSection.id = `results-table-${manager}`;
    tableSection.innerHTML = '<h2>Результаты уникализации</h2>';
    
    // Создаём таблицу / Create table
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    
    // Создаём заголовок таблицы / Create table header
    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    const th1 = document.createElement('th');
    th1.textContent = '№';
    const th2 = document.createElement('th');
    th2.textContent = 'Ссылки';
    
    // Добавляем кнопку "Скопировать ссылки" в заголовок второй колонки
    // Add "Copy links" button to second column header
    const copyButton = document.createElement('button');
    copyButton.textContent = 'Скопировать ссылки';
    copyButton.classList.add('copy-btn');
    copyButton.onclick = () => {
        // Извлекаем только ссылки из результатов / Extract only links from results
        const links = results.map(result => result[1]);
        // Форматируем для CSV (экранируем кавычки) / Format for CSV (escape quotes)
        const clipboardText = links.map(link => `"${link.replace(/"/g, '""')}"`).join('\n');
        copyToClipboard(clipboardText, copyButton);
    };
    th2.appendChild(copyButton);
    
    tr.appendChild(th1);
    tr.appendChild(th2);
    thead.appendChild(tr);
    table.appendChild(thead);
    
    // Создаём тело таблицы с данными / Create table body with data
    const tbody = document.createElement('tbody');
    results.forEach(result => {
        const tr = document.createElement('tr');
        // Заменяем переводы строк на <br> для отображения / Replace newlines with <br> for display
        tr.innerHTML = `<td>${result[0]}</td><td>${result[1].replace(/\n/g, '<br>')}</td>`;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableSection.appendChild(table);

    // Добавляем таблицу после сетки / Add table after grid
    document.getElementById(`grid-${manager}`).after(tableSection);
}

// Функция показа модального окна для редактирования менеджера
// Function to show modal window for editing manager
export function showEditManagerModal(manager) {
    setCurrentEditManager(manager);
    document.getElementById('edit-manager-name').value = manager;
    document.getElementById('edit-manager-modal').style.display = 'block';
}

// Функция закрытия модального окна редактирования
// Function to close edit modal window
export function closeEditModal() {
    document.getElementById('edit-manager-modal').style.display = 'none';
}

// ============================================================================
// ФУНКЦИИ ЗАГРУЗКИ КОНТЕНТА МЕНЕДЖЕРА / MANAGER CONTENT LOADING FUNCTIONS
// ============================================================================

// Функция загрузки контента для выбранного менеджера
// Function to load content for selected manager
export function loadManagerContent(manager) {
    setCurrentManager(manager);
    initManagerState(manager);
    
    // Генерируем HTML для интерфейса менеджера / Generate HTML for manager interface
    const content = document.getElementById('manager-content');
    content.innerHTML = `
        <div class="folder-setup" id="folder-setup-${manager}">
            <h2>Создание структуры папок для ${manager}</h2>
            <div class="input-group">
                <label for="category-name-${manager}">Название папки:</label>
                <input type="text" id="category-name-${manager}" placeholder="Введите название категории">
                <small>Укажите это название в Google таблице в ячейке "Название папки с подпапками" (C6)</small>
            </div>
            <div class="position-container">
                <div class="position-row" id="position-row-${manager}">
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
                </div>
            </div>
            <div class="button-group">
                <button class="btn-add-position" onclick="addPosition('${manager}')">+ Добавить позицию</button>
                <button class="btn-primary" onclick="showConfirmModal('${manager}')">Подтвердить</button>
            </div>
        </div>
        <div class="section">
            <h2>Логи (последние 20 строк)</h2>
            <pre id="logs-${manager}"></pre>
        </div>
        <div class="section">
            <h2>Созданные папки</h2>
            <div class="grid" id="grid-${manager}"></div>
        </div>
    `;
    // Инициализируем интерфейс и загружаем данные / Initialize interface and load data
    initPositionRow(manager);
    fetchLogs(manager);
    fetchManagerGrid(manager, `grid-${manager}`);
}

// ============================================================================
// ФУНКЦИИ УПРАВЛЕНИЯ ПОЗИЦИЯМИ / POSITION MANAGEMENT FUNCTIONS
// ============================================================================

// Функция инициализации первой позиции для менеджера
// Function to initialize first position for manager
export function initPositionRow(manager) {
    const firstTile = document.querySelector(`#position-row-${manager} .position-tile`);
    const thumbnailContainer = firstTile.querySelector('.thumbnail-container');
    
    // Предотвращаем всплытие событий клика на контейнере миниатюр
    // Prevent click event bubbling on thumbnail container
    thumbnailContainer.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // Добавляем обработчик изменения файлового инпута
    // Add file input change handler
    firstTile.querySelector('.file-input').addEventListener('change', function(e) {
        handleFileSelection(e, 1, manager);
    });
}

// Функция добавления новой позиции
// Function to add new position
export function addPosition(manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        // Увеличиваем счётчик позиций / Increment position count
        positionCounts[manager] = (positionCounts[manager] || 1) + 1;
        const positionCount = positionCounts[manager];
        const row = document.getElementById(`position-row-${manager}`);
        
        // Создаём новый тайл позиции / Create new position tile
        const newTile = document.createElement('div');
        newTile.classList.add('position-tile');
        newTile.dataset.position = positionCount;
        newTile.innerHTML = `
            <button class="clear-photos" onclick="clearPhotos(${positionCount}, '${manager}')" title="Очистить фотографии">🧹</button>
            <button class="delete-position" onclick="deletePosition(${positionCount}, '${manager}')" title="Удалить позицию">🗑️</button>
            <div class="tile-header">
                <div class="position-number">${positionCount}</div>
                <div class="position-label">Фото для ${positionCount}-й позиции</div>
            </div>
            <div class="thumbnail-container" id="thumbnails-${positionCount}-${manager}"></div>
            <button class="upload-button" onclick="openFileInput(${positionCount}, '${manager}')">Загрузить изображения</button>
            <input type="file" multiple class="file-input" accept="image/*" style="display: none;">
        `;
        
        // Настраиваем обработчики событий для нового тайла
        // Setup event handlers for new tile
        const thumbnailContainer = newTile.querySelector('.thumbnail-container');
        thumbnailContainer.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        newTile.querySelector('.file-input').addEventListener('change', function(e) {
            handleFileSelection(e, positionCount, manager);
        });
        
        // Добавляем в DOM и инициализируем массив файлов
        // Add to DOM and initialize files array
        row.appendChild(newTile);
        selectedFiles[manager][positionCount] = [];
    } finally {
        setIsProcessing(false);
    }
}

// Функция удаления позиции
// Function to delete position
export function deletePosition(positionNumber, manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        // Нельзя удалить последнюю позицию / Cannot delete the last position
        if (positionCounts[manager] === 1) {
            alert('Нельзя удалить единственную позицию. Добавьте новую, а потом удалите эту.');
            return;
        }
        
        // Подтверждение удаления / Confirm deletion
        if (confirm(`Удалить позицию ${positionNumber}?`)) {
            const tile = document.querySelector(`#position-row-${manager} [data-position="${positionNumber}"]`);
            if (tile) {
                tile.remove();
                
                // Перенумеруем оставшиеся позиции / Renumber remaining positions
                const remainingTiles = document.querySelectorAll(`#position-row-${manager} .position-tile`);
                const oldSelectedFiles = {...selectedFiles[manager]};
                selectedFiles[manager] = {};
                
                remainingTiles.forEach((tile, index) => {
                    const oldPosition = tile.dataset.position;
                    const newPosition = index + 1;
                    
                    // Обновляем номер позиции / Update position number
                    tile.dataset.position = newPosition;
                    tile.querySelector('.position-number').textContent = newPosition;
                    tile.querySelector('.position-label').textContent = `Фото для ${newPosition}-й позиции`;
                    
                    // Переносим выбранные файлы / Transfer selected files
                    selectedFiles[manager][newPosition] = oldSelectedFiles[oldPosition] || [];
                    
                    // Обновляем ID контейнера / Update container ID
                    const container = tile.querySelector('.thumbnail-container');
                    container.id = `thumbnails-${newPosition}-${manager}`;
                    
                    // Переназначаем обработчики / Reassign handlers
                    const uploadBtn = tile.querySelector('.upload-button');
                    uploadBtn.onclick = () => openFileInput(newPosition, manager);
                    
                    const fileInput = tile.querySelector('.file-input');
                    fileInput.addEventListener('change', function(e) {
                        handleFileSelection(e, newPosition, manager);
                    });
                    
                    const deleteBtn = tile.querySelector('.delete-position');
                    deleteBtn.onclick = () => deletePosition(newPosition, manager);
                    
                    const clearBtn = tile.querySelector('.clear-photos');
                    clearBtn.onclick = () => clearPhotos(newPosition, manager);
                });
                
                // Обновляем счётчик / Update counter
                positionCounts[manager] = remainingTiles.length;
            }
        }
    } finally {
        setIsProcessing(false);
    }
}

// Функция очистки всех фото в позиции
// Function to clear all photos in position
export function clearPhotos(positionNumber, manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        // Подтверждение очистки / Confirm clearing
        if (confirm(`Очистить все фотографии с позиции ${positionNumber}?`)) {
            // Очищаем массив файлов / Clear files array
            selectedFiles[manager][positionNumber] = [];
            
            // Очищаем контейнер миниатюр / Clear thumbnails container
            const container = document.getElementById(`thumbnails-${positionNumber}-${manager}`);
            container.innerHTML = '';
            
            // Пересоздаём input для сброса выбора / Recreate input to reset selection
            const tile = document.querySelector(`#position-row-${manager} [data-position="${positionNumber}"]`);
            const input = tile.querySelector('.file-input');
            const newInput = document.createElement('input');
            newInput.type = 'file';
            newInput.multiple = true;
            newInput.classList.add('file-input');
            newInput.accept = 'image/*';
            newInput.style.display = 'none';
            newInput.addEventListener('change', function(e) {
                handleFileSelection(e, positionNumber, manager);
            });
            input.replaceWith(newInput);
            
            // Обновляем счётчик файлов / Update file count
            updateFileCount(positionNumber, manager);
        }
    } finally {
        setIsProcessing(false);
    }
}

// ============================================================================
// ФУНКЦИИ ОБРАБОТКИ ФАЙЛОВ / FILE HANDLING FUNCTIONS
// ============================================================================

// Обработка выбора файлов пользователем
// Handle user file selection
export function handleFileSelection(event, position, manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        const files = Array.from(event.target.files);
        if (files.length === 0) return; // Если файлы не выбраны / If no files selected
        
        // Сохраняем файлы в состояние / Save files to state
        selectedFiles[manager][position] = files;
        const container = document.getElementById(`thumbnails-${position}-${manager}`);
        container.innerHTML = '';
        
        // Создаём миниатюры для каждого файла / Create thumbnails for each file
        files.forEach((file) => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.createElement('img');
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const image = new Image();
                    
                    image.onload = function() {
                        // Создаём миниатюру с сохранением пропорций
                        // Create thumbnail preserving aspect ratio
                        canvas.width = 120;
                        canvas.height = 90;
                        const scale = Math.min(canvas.width / image.width, canvas.height / image.height);
                        const scaledWidth = image.width * scale;
                        const scaledHeight = image.height * scale;
                        
                        // Центрируем изображение на canvas / Center image on canvas
                        ctx.drawImage(image, 
                            (canvas.width - scaledWidth) / 2, 
                            (canvas.height - scaledHeight) / 2, 
                            scaledWidth, 
                            scaledHeight
                        );
                        
                        // Конвертируем в JPEG с сжатием / Convert to JPEG with compression
                        img.src = canvas.toDataURL('image/jpeg', 0.5);
                        img.classList.add('thumbnail');
                        img.title = file.name;
                        
                        // Обработчик клика для удаления / Click handler for removal
                        img.onclick = function(evt) {
                            evt.stopPropagation();
                            if (confirm(`Удалить "${file.name}" из выбранных файлов?`)) {
                                selectedFiles[manager][position] = selectedFiles[manager][position].filter(f => f !== file);
                                img.remove();
                                updateFileCount(position, manager);
                            }
                        };
                        container.appendChild(img);
                    };
                    image.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
        
        // Обновляем счётчик файлов / Update file count
        updateFileCount(position, manager);
    } finally {
        setIsProcessing(false);
    }
}

// Обновление счётчика выбранных файлов
// Update selected files counter
export function updateFileCount(position, manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        const tile = document.querySelector(`#position-row-${manager} [data-position="${position}"]`);
        
        // Удаляем старый бейдж, если есть / Remove old badge if exists
        const existingBadge = tile.querySelector('.count-badge');
        if (existingBadge) existingBadge.remove();
        
        // Считаем количество изображений / Count images
        const files = selectedFiles[manager][position] || [];
        const count = files.filter(f => f.type.startsWith('image/')).length;
        
        // Если есть файлы, показываем счётчик / If files exist, show counter
        if (count > 0) {
            const countBadge = document.createElement('div');
            countBadge.classList.add('count-badge');
            countBadge.textContent = `Файлов: ${count}`;
            countBadge.style.cssText = 'position: absolute; top: 10px; left: 50px; background: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; z-index: 2;';
            tile.style.position = 'relative';
            tile.appendChild(countBadge);
        }
    } finally {
        setIsProcessing(false);
    }
}

// Открытие диалога выбора файлов
// Open file selection dialog
export function openFileInput(position, manager) {
    const tile = document.querySelector(`#position-row-${manager} [data-position="${position}"]`);
    const fileInput = tile.querySelector('.file-input');
    fileInput.click(); // Программно открываем диалог / Programmatically open dialog
}

// ============================================================================
// ФУНКЦИИ ДЛЯ ГЛАВНОЙ СТРАНИЦЫ / MAIN PAGE FUNCTIONS
// ============================================================================

// Функция рендеринга карточек менеджеров на главной странице
// Function to render manager cards on main page
export function renderManagerCards(managers) {
    const container = document.getElementById('managers-grid-main');
    if (!container) {
        console.error('Контейнер managers-grid-main не найден');
        return;
    }
    
    // Очищаем контейнер / Clear container
    container.innerHTML = '';
    
    // Если менеджеров нет, показываем сообщение / If no managers, show message
    if (!managers || managers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-users" style="font-size: 64px; color: #cbd5e0; margin-bottom: 20px;"></i>
                <h3 style="color: #718096;">Менеджеры не найдены</h3>
                <p style="color: #a0aec0;">Перейдите на вкладку "Уникализация фото" для создания менеджера</p>
            </div>
        `;
        return;
    }
    
    // Создаём карточку для каждого менеджера / Create card for each manager
    managers.forEach((manager, index) => {
        const card = document.createElement('div');
        card.classList.add('manager-card');
        card.style.animationDelay = `${index * 0.1}s`;
        
        // Генерируем случайный градиент для аватара / Generate random gradient for avatar
        const gradients = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
            'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
            'linear-gradient(135deg, #ff9a56 0%, #ff6a88 100%)'
        ];
        const gradient = gradients[index % gradients.length];
        
        card.innerHTML = `
            <div class="manager-card-avatar" style="background: ${gradient};">
                <i class="fas fa-user-tie"></i>
            </div>
            <div class="manager-card-content">
                <h3 class="manager-card-title">${manager}</h3>
                <div class="manager-card-balance">
                    <i class="fas fa-wallet"></i>
                    <span>Баланс Avito: <strong>Загрузка...</strong></span>
                </div>
            </div>
            <div class="manager-card-actions">
                <button class="manager-card-btn" title="Управление">
                    <i class="fas fa-cog"></i> Управление
                </button>
            </div>
        `;
        
        // Добавляем обработчик клика для перехода к управлению менеджером
        // Add click handler to navigate to manager management
        card.addEventListener('click', () => {
            // Переключаемся на вкладку уникализации / Switch to uniquification tab
            document.querySelector('.sidebar-item[data-tab="photo-uniquification"]').click();
            
            // Небольшая задержка для корректной загрузки / Small delay for proper loading
            setTimeout(() => {
                loadManagerContent(manager);
            }, 100);
        });
        
        container.appendChild(card);
    });
}

// ============================================================================
// ФУНКЦИИ ПОДТВЕРЖДЕНИЯ И ФИНАЛИЗАЦИИ / CONFIRMATION AND FINALIZATION FUNCTIONS
// ============================================================================

// Показ модального окна подтверждения создания структуры
// Show confirmation modal for structure creation
export function showConfirmModal(manager) {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        // Валидация названия категории / Validate category name
        const categoryName = document.getElementById(`category-name-${manager}`).value.trim();
        if (!categoryName) {
            alert('Пожалуйста, введите название папки категории');
            return;
        }
        
        // Собираем информацию о позициях и файлах / Collect info about positions and files
        const positions = Array.from(document.querySelectorAll(`#position-row-${manager} .position-tile`)).map(tile => tile.dataset.position);
        const totalFiles = positions.reduce((sum, pos) => sum + (selectedFiles[manager][pos] ? selectedFiles[manager][pos].length : 0), 0);
        
        // Формируем содержимое модального окна / Build modal content
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <p><strong>Категория:</strong> <span class="highlight">${categoryName}</span></p>
            <p><strong>Позиции:</strong> ${positions.map(p => `<span class="highlight">${p}</span>`).join(', ')}</p>
            <p><strong>Всего файлов:</strong> <span class="highlight">${totalFiles}</span></p>
            <p style="color: #007bff; font-weight: 500; margin-top: 15px;">Подтвердите создание структуры папок. Выбранные файлы будут автоматически загружены в соответствующие подпапки.</p>
        `;
        
        // Показываем модальное окно / Show modal window
        document.getElementById('confirm-modal').style.display = 'block';
        document.getElementById('progress-container').style.display = 'none';
        
        // Динамически импортируем createFolderStructure из api.js
        // Dynamically import createFolderStructure from api.js
        import('./api.js').then(module => {
            document.getElementById('create-button').onclick = () => module.createFolderStructure(manager, categoryName);
        });
        document.getElementById('create-button').disabled = false;
    } finally {
        setIsProcessing(false);
    }
}

// Закрытие модального окна подтверждения
// Close confirmation modal window
export function closeModal() {
    if (isProcessing) return; // Защита от повторного вызова / Prevent duplicate calls
    setIsProcessing(true);
    try {
        document.getElementById('confirm-modal').style.display = 'none';
        document.getElementById('progress-container').style.display = 'none';
        document.getElementById('create-button').disabled = false;
    } finally {
        setIsProcessing(false);
    }
}

