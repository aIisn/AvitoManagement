// filename="script.js"
// Глобальные переменные для управления состоянием
let currentPaths = {}; // {manager: path}
let currentManager = null;
let selectedFiles = {}; // {manager: {position: files[]}}
let positionCounts = {}; // {manager: count}
let isProcessing = false;
let currentEditManager = null;
let currentUniquifyCategory = null;

// Функция для получения логов
async function fetchLogs(manager = null) {
    const response = await fetch('/api/logs');
    const data = await response.json();
    const logsElement = document.getElementById(`logs-${manager || 'global'}`);
    if (logsElement) {
        logsElement.textContent = data.logs.join('\n');
    }
}

// Функция для загрузки сетки папок для менеджера
async function fetchManagerGrid(manager, gridId, path = '', dir_type = 'photo_cache') {
    if (isProcessing) return;
    isProcessing = true;
    try {
        currentPaths[manager] = path;
        const response = await fetch(`/api/list?manager=${manager}&dir=${dir_type}&path=${path}`);
        const data = await response.json();
        const grid = document.getElementById(gridId);
        if (path === '' && dir_type === 'photo_cache') {
            // Специальная логика для корня photo_cache: парное отображение с ready_photos
            const photo_dirs = data.children.filter(node => node.type === 'dir');
            const ready_response = await fetch(`/api/list?manager=${manager}&dir=ready_photos&path=`);
            const ready_data = await ready_response.json();
            const ready_map = new Map(ready_data.children.filter(node => node.type === 'dir').map(node => [node.name, node]));
            grid.innerHTML = '';
            for (const photo_node of photo_dirs) {
                const row = document.createElement('div');
                row.classList.add('card-row');
                renderCard(photo_node, row, manager, path, 'photo_cache');
                if (ready_map.has(photo_node.name)) {
                    const chain = document.createElement('span');
                    chain.classList.add('chain-icon');
                    chain.textContent = '🔗';
                    row.appendChild(chain);
                    const category_path = photo_node.name;
                    const count_response = await fetch(`/api/list?manager=${manager}&dir=ready_photos&path=${category_path}`);
                    const count_data = await count_response.json();
                    const count = count_data.children.length;
                    const unique_node = {
                        name: photo_node.name,
                        type: 'dir-unique',
                        path: category_path,
                        count: count
                    };
                    renderCard(unique_node, row, manager, path, 'ready_photos');
                }
                grid.appendChild(row);
            }
        } else {
            // Обычная логика для поддиректорий или ready_photos
            grid.innerHTML = '';
            data.children.forEach(node => renderCard(node, grid, manager, path, dir_type));
        }
    } catch (error) {
        console.error(`Ошибка при загрузке сетки для ${manager}:`, error);
    } finally {
        isProcessing = false;
    }
}

// Функция рендеринга карточки
// Функция рендеринга карточки с общим контейнером для кнопок и применением общих стилей
function renderCard(node, parentElement, manager, path, dir_type) {
    const card = document.createElement('div');
    card.classList.add('card', node.type);
    if (node.type === 'dir-unique') {
        card.classList.add('unique');
    }
    const name = document.createElement('div');
    name.classList.add('name');
    name.textContent = node.name;
    card.appendChild(name);
    const fullPath = path ? `${path}/${node.name}` : node.name;
    if (node.type.startsWith('dir')) {
        card.onclick = async (e) => {
            if (e.target.tagName === 'BUTTON') return;
            const target_dir = (node.type === 'dir-unique') ? 'ready_photos' : dir_type;
            await fetchManagerGrid(manager, `grid-${manager}`, fullPath, target_dir);
        };
    }
    let leftBtn = null;
    // Кнопка для исходных папок
    if (path === '' && dir_type === 'photo_cache' && node.type === 'dir') {
        leftBtn = document.createElement('button');
        leftBtn.textContent = 'Уникализировать';
        leftBtn.classList.add('uniquify-btn', 'btn-common');
        leftBtn.onclick = (e) => {
            e.stopPropagation();
            showUniquifyModal(manager, node.name);
        };
    }
    // Кнопка для готовых папок
    if (node.type === 'dir-unique') {
        leftBtn = document.createElement('button');
        leftBtn.textContent = 'Показать ссылки';
        leftBtn.classList.add('get-links-btn', 'btn-common');
        leftBtn.onclick = (e) => {
            e.stopPropagation();
            fetchLinks(manager, node.name);
        };
    }
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = 'Удалить';
    deleteBtn.classList.add('delete', 'btn-common');
    deleteBtn.onclick = async (e) => {
        e.stopPropagation();
        if (isProcessing) return;
        isProcessing = true;
        try {
            if (confirm(`Вы уверены, что хотите удалить "${node.name}"? Это действие нельзя отменить.\nВсе файлы в папке будут удалены!`)) {
                const target_dir = (node.type === 'dir-unique') ? 'ready_photos' : dir_type;
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({manager, dir: target_dir, path: fullPath})
                });
                const data = await response.json();
                if (data.success) {
                    parentElement.removeChild(card);
                    await fetchManagerGrid(manager, `grid-${manager}`, path, dir_type);
                } else {
                    alert(`Ошибка: ${data.error}`);
                }
            }
        } catch (error) {
            console.error('Ошибка при удалении:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            isProcessing = false;
        }
    };
    // Общий контейнер для кнопок
    const buttonContainer = document.createElement('div');
    buttonContainer.classList.add('button-container');
    if (leftBtn) {
        buttonContainer.appendChild(leftBtn);
    }
    buttonContainer.appendChild(deleteBtn);
    card.appendChild(buttonContainer);
    // Добавляем бейдж с количеством для уникальных папок
    if (node.count !== undefined) {
        const badge = document.createElement('div');
        badge.classList.add('count-badge');
        badge.textContent = `${node.count} адс`;
        card.appendChild(badge);
    }
    parentElement.appendChild(card);
}

// Функция показа модального для уникализации
function showUniquifyModal(manager, category) {
    currentManager = manager;
    currentUniquifyCategory = category;
    document.getElementById('ad-count').value = 1;
    document.getElementById('use-rotation').checked = true;
    document.getElementById('uniquify-modal').style.display = 'block';
}

// Функция закрытия модального для уникализации
function closeUniquifyModal() {
    document.getElementById('uniquify-modal').style.display = 'none';
}

// Функция запуска уникализации
async function startUniquify() {
    const count = parseInt(document.getElementById('ad-count').value);
    const useRotation = document.getElementById('use-rotation').checked;
    if (count < 1) {
        alert('Количество объявлений должно быть не менее 1');
        return;
    }
    closeUniquifyModal();
    // Показываем прогресс (используем существующий, но для простоты новый div)
    const progressDiv = document.createElement('div');
    progressDiv.innerHTML = '<p>Уникализация в процессе...</p>';
    document.getElementById(`grid-${currentManager}`).after(progressDiv);
    try {
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
            renderResultsTable(data.results, currentManager);
            await fetchManagerGrid(currentManager, `grid-${currentManager}`);
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка уникализации:', error);
        alert(`Ошибка: ${error.message}`);
    } finally {
        progressDiv.remove();
    }
}

async function fetchLinks(manager, category) {
    try {
        const response = await fetch(`/api/get_links?manager=${manager}&category=${category}`);
        const data = await response.json();
        if (data.success) {
            renderResultsTable(data.results, manager);
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка получения ссылок:', error);
        alert(`Ошибка: ${error.message}`);
    }
}   

// Функция рендеринга таблицы результатов
function renderResultsTable(results, manager) {
    const tableSection = document.createElement('div');
    tableSection.classList.add('section');
    tableSection.innerHTML = '<h2>Результаты уникализации</h2>';
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    const th1 = document.createElement('th');
    th1.textContent = '№';
    const th2 = document.createElement('th');
    th2.textContent = 'Ссылки';
    
    // Добавляем кнопку "Скопировать ссылки" в заголовок второй колонки
    const copyButton = document.createElement('button');
    copyButton.textContent = 'Скопировать ссылки';
    copyButton.classList.add('copy-btn');
    copyButton.onclick = () => {
        const links = results.map(result => result[1]);
        const clipboardText = links.map(link => `"${link.replace(/"/g, '""')}"`).join('\n');
        copyToClipboard(clipboardText, copyButton);
    };
    th2.appendChild(copyButton);
    
    tr.appendChild(th1);
    tr.appendChild(th2);
    thead.appendChild(tr);
    table.appendChild(thead);
    
    const tbody = document.createElement('tbody');
    results.forEach(result => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${result[0]}</td><td>${result[1].replace(/\n/g, '<br>')}</td>`;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableSection.appendChild(table);

    document.getElementById(`grid-${manager}`).after(tableSection);
}

// Функция копирования в буфер обмена с fallback
function copyToClipboard(text, button) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            button.textContent = 'Скопировано!';
            setTimeout(() => { button.textContent = 'Скопировать ссылки'; }, 2000);
        }).catch(err => {
            console.error('Ошибка clipboard API:', err);
            fallbackCopy(text, button);
        });
    } else {
        fallbackCopy(text, button);
    }
}

// Fallback метод копирования
function fallbackCopy(text, button) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        button.textContent = 'Скопировано!';
        setTimeout(() => { button.textContent = 'Скопировать ссылки'; }, 2000);
    } catch (err) {
        console.error('Ошибка fallback копирования:', err);
        alert('Ошибка при копировании в буфер обмена');
    }
    document.body.removeChild(textArea);
}

// Функция создания менеджера
async function createManager() {
    const name = document.getElementById('manager-name').value.trim();
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
            document.getElementById('manager-name').value = '';
            await fetchManagers();
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        console.error('Ошибка создания менеджера:', error);
    }
}

// Функция загрузки списка менеджеров
async function fetchManagers() {
    try {
        const response = await fetch('/api/managers');
        const managers = await response.json();
        const list = document.getElementById('manager-list');
        list.innerHTML = '';
        managers.forEach(manager => {
            const item = document.createElement('li');
            item.classList.add('manager-item');
            const nameSpan = document.createElement('span');
            nameSpan.textContent = manager;
            nameSpan.onclick = () => loadManagerContent(manager);
            item.appendChild(nameSpan);
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

// Функция показа модального для редактирования менеджера
function showEditManagerModal(manager) {
    currentEditManager = manager;
    document.getElementById('edit-manager-name').value = manager;
    document.getElementById('edit-manager-modal').style.display = 'block';
}

// Функция закрытия модального для редактирования
function closeEditModal() {
    document.getElementById('edit-manager-modal').style.display = 'none';
}

// Функция сохранения редактирования менеджера
async function saveManagerEdit() {
    const newName = document.getElementById('edit-manager-name').value.trim();
    if (!newName || newName === currentEditManager) {
        closeEditModal();
        return;
    }
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
                await fetchManagers();
                if (currentManager === currentEditManager) {
                    loadManagerContent(newName);
                    currentManager = newName;
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

// Функция подтверждения удаления менеджера
async function deleteManagerConfirm() {
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
                await fetchManagers();
                if (currentManager === currentEditManager) {
                    document.getElementById('manager-content').innerHTML = '';
                    currentManager = null;
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

// Функция загрузки контента для менеджера
function loadManagerContent(manager) {
    currentManager = manager;
    positionCounts[manager] = 1;
    selectedFiles[manager] = {1: []};
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
    initPositionRow(manager);
    fetchLogs(manager);
    fetchManagerGrid(manager, `grid-${manager}`);
}

// Функция инициализации первой позиции для менеджера
function initPositionRow(manager) {
    const firstTile = document.querySelector(`#position-row-${manager} .position-tile`);
    const thumbnailContainer = firstTile.querySelector('.thumbnail-container');
    thumbnailContainer.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    firstTile.querySelector('.file-input').addEventListener('change', function(e) {
        handleFileSelection(e, 1, manager);
    });
}

// Функция добавления позиции
function addPosition(manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        positionCounts[manager] = (positionCounts[manager] || 1) + 1;
        const positionCount = positionCounts[manager];
        const row = document.getElementById(`position-row-${manager}`);
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
        const thumbnailContainer = newTile.querySelector('.thumbnail-container');
        thumbnailContainer.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        newTile.querySelector('.file-input').addEventListener('change', function(e) {
            handleFileSelection(e, positionCount, manager);
        });
        row.appendChild(newTile);
        selectedFiles[manager][positionCount] = [];
    } finally {
        isProcessing = false;
    }
}

// Функция удаления позиции
function deletePosition(positionNumber, manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        if (positionCounts[manager] === 1) {
            alert('Нельзя удалить единственную позицию. Добавьте новую, а потом удалите эту.');
            return;
        }
        if (confirm(`Удалить позицию ${positionNumber}?`)) {
            const tile = document.querySelector(`#position-row-${manager} [data-position="${positionNumber}"]`);
            if (tile) {
                tile.remove();
                const remainingTiles = document.querySelectorAll(`#position-row-${manager} .position-tile`);
                const oldSelectedFiles = {...selectedFiles[manager]};
                selectedFiles[manager] = {};
                remainingTiles.forEach((tile, index) => {
                    const oldPosition = tile.dataset.position;
                    const newPosition = index + 1;
                    tile.dataset.position = newPosition;
                    tile.querySelector('.position-number').textContent = newPosition;
                    tile.querySelector('.position-label').textContent = `Фото для ${newPosition}-й позиции`;
                    selectedFiles[manager][newPosition] = oldSelectedFiles[oldPosition] || [];
                    const container = tile.querySelector('.thumbnail-container');
                    container.id = `thumbnails-${newPosition}-${manager}`;
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
                positionCounts[manager] = remainingTiles.length;
            }
        }
    } finally {
        isProcessing = false;
    }
}

// Функция очистки фото
function clearPhotos(positionNumber, manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        if (confirm(`Очистить все фотографии с позиции ${positionNumber}?`)) {
            selectedFiles[manager][positionNumber] = [];
            const container = document.getElementById(`thumbnails-${positionNumber}-${manager}`);
            container.innerHTML = '';
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
            updateFileCount(positionNumber, manager);
        }
    } finally {
        isProcessing = false;
    }
}

// Обработка выбора файлов
function handleFileSelection(event, position, manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;
        selectedFiles[manager][position] = files;
        const container = document.getElementById(`thumbnails-${position}-${manager}`);
        container.innerHTML = '';
        files.forEach((file) => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.createElement('img');
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const image = new Image();
                    image.onload = function() {
                        canvas.width = 120;
                        canvas.height = 90;
                        const scale = Math.min(canvas.width / image.width, canvas.height / image.height);
                        const scaledWidth = image.width * scale;
                        const scaledHeight = image.height * scale;
                        ctx.drawImage(image, (canvas.width - scaledWidth) / 2, (canvas.height - scaledHeight) / 2, scaledWidth, scaledHeight);
                        img.src = canvas.toDataURL('image/jpeg', 0.5);
                        img.classList.add('thumbnail');
                        img.title = file.name;
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
        updateFileCount(position, manager);
    } finally {
        isProcessing = false;
    }
}

// Обновление счётчика файлов
function updateFileCount(position, manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const tile = document.querySelector(`#position-row-${manager} [data-position="${position}"]`);
        const existingBadge = tile.querySelector('.count-badge');
        if (existingBadge) existingBadge.remove();
        const files = selectedFiles[manager][position] || [];
        const count = files.filter(f => f.type.startsWith('image/')).length;
        if (count > 0) {
            const countBadge = document.createElement('div');
            countBadge.classList.add('count-badge');
            countBadge.textContent = `Файлов: ${count}`;
            countBadge.style.cssText = 'position: absolute; top: 10px; left: 50px; background: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; z-index: 2;';
            tile.style.position = 'relative';
            tile.appendChild(countBadge);
        }
    } finally {
        isProcessing = false;
    }
}

// Открытие выбора файлов
function openFileInput(position, manager) {
    const tile = document.querySelector(`#position-row-${manager} [data-position="${position}"]`);
    const fileInput = tile.querySelector('.file-input');
    fileInput.click();
}

// Показ модального
function showConfirmModal(manager) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const categoryName = document.getElementById(`category-name-${manager}`).value.trim();
        if (!categoryName) {
            alert('Пожалуйста, введите название папки категории');
            return;
        }
        const positions = Array.from(document.querySelectorAll(`#position-row-${manager} .position-tile`)).map(tile => tile.dataset.position);
        const totalFiles = positions.reduce((sum, pos) => sum + (selectedFiles[manager][pos] ? selectedFiles[manager][pos].length : 0), 0);
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <p><strong>Категория:</strong> <span class="highlight">${categoryName}</span></p>
            <p><strong>Позиции:</strong> ${positions.map(p => `<span class="highlight">${p}</span>`).join(', ')}</p>
            <p><strong>Всего файлов:</strong> <span class="highlight">${totalFiles}</span></p>
            <p style="color: #007bff; font-weight: 500; margin-top: 15px;">Подтвердите создание структуры папок. Выбранные файлы будут автоматически загружены в соответствующие подпапки.</p>
        `;
        document.getElementById('confirm-modal').style.display = 'block';
        document.getElementById('progress-container').style.display = 'none';
        document.getElementById('create-button').onclick = () => createFolderStructure(manager, categoryName);
        document.getElementById('create-button').disabled = false;
    } finally {
        isProcessing = false;
    }
}

// Закрытие модального
function closeModal() {
    if (isProcessing) return;
    isProcessing = true;
    try {
        document.getElementById('confirm-modal').style.display = 'none';
        document.getElementById('progress-container').style.display = 'none';
        document.getElementById('create-button').disabled = false;
    } finally {
        isProcessing = false;
    }
}

// Создание структуры
async function createFolderStructure(manager, categoryName) {
    if (isProcessing) return;
    isProcessing = true;
    const positions = Array.from(document.querySelectorAll(`#position-row-${manager} .position-tile`)).map(tile => tile.dataset.position);
    const createButton = document.getElementById('create-button');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    createButton.disabled = true;
    progressContainer.style.display = 'block';
    progressText.textContent = 'Создание структуры папок...';
    progressFill.style.width = '0%';
    let currentProgress = 0;
    const totalSteps = positions.length * 2 + 1;
    try {
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
        currentProgress += 100 / totalSteps;
        progressFill.style.width = `${currentProgress}%`;
        let uploadSuccess = true;
        for (let pos of positions) {
            progressText.textContent = `Загрузка файлов для позиции ${pos}...`;
            const files = selectedFiles[manager][pos] || [];
            if (files.length > 0) {
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
            currentProgress += 100 / totalSteps;
            progressFill.style.width = `${Math.min(currentProgress, 100)}%`;
        }
        progressText.textContent = 'Завершение...';
        await new Promise(resolve => setTimeout(resolve, 500));
        progressFill.style.width = '100%';
        closeModal();
        if (uploadSuccess) {
            await fetchManagerGrid(manager, `grid-${manager}`);
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
            successDiv.innerHTML = `
                ✅ <strong>Успешно!</strong><br>
                Структура создана и ${positions.reduce((sum, pos) => sum + (selectedFiles[manager][pos] ? selectedFiles[manager][pos].length : 0), 0)} файлов загружено
            `;
            document.body.appendChild(successDiv);
            setTimeout(() => successDiv.remove(), 5000);
            document.getElementById(`category-name-${manager}`).value = '';
            document.querySelectorAll(`#position-row-${manager} .thumbnail-container`).forEach(c => c.innerHTML = '');
            document.querySelectorAll(`#position-row-${manager} .position-tile`).forEach(t => {
                const badge = t.querySelector('.count-badge');
                if (badge) badge.remove();
            });
            selectedFiles[manager] = {};
            positionCounts[manager] = 1;
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
        console.error('Ошибка в createFolderStructure:', error);
        progressText.textContent = 'Ошибка!';
        progressFill.style.background = '#dc3545';
        setTimeout(() => {
            closeModal();
            alert(`Ошибка: ${error.message}`);
        }, 1500);
    } finally {
        isProcessing = false;
    }
}

// Обработчик клика вне модального
window.onclick = function(event) {
    const confirmModal = document.getElementById('confirm-modal');
    const editModal = document.getElementById('edit-manager-modal');
    if (event.target === confirmModal) {
        closeModal();
    } else if (event.target === editModal) {
        closeEditModal();
    }
}

// Обработчик вкладок
document.querySelectorAll('.tab-link').forEach(tab => {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        document.getElementById(this.dataset.tab).classList.add('active');
        if (this.dataset.tab === 'photo-uniquification') {
            fetchManagers();
        }
    });
});

// Инициализация при загрузке страницы
window.onload = () => {
    setInterval(() => {
        if (currentManager) fetchLogs(currentManager);
    }, 2000);
};