// filename="script.js"
// Глобальные переменные для управления состоянием
let currentPaths = { 'photo_cache': '', 'ready_photos': '' };
let positionCount = 1;
let selectedFiles = {};
let isProcessing = false;

// Функция для получения логов
async function fetchLogs() {
    const response = await fetch('/api/logs');
    const data = await response.json();
    document.getElementById('logs').textContent = data.logs.join('\n');
}

// Функция добавления новой позиции
function addPosition() {
    if (isProcessing) return;
    isProcessing = true;
    try {
        positionCount++;
        const row = document.getElementById('position-row');
        const newTile = document.createElement('div');
        newTile.classList.add('position-tile');
        newTile.dataset.position = positionCount;
        newTile.innerHTML = `
            <button class="clear-photos" onclick="clearPhotos(${positionCount})" title="Очистить фотографии">🧹</button>
            <button class="delete-position" onclick="deletePosition(${positionCount})" title="Удалить позицию">🗑️</button>
            <div class="tile-header">
                <div class="position-number">${positionCount}</div>
                <div class="position-label">Фото для ${positionCount}-й позиции</div>
            </div>
            <div class="thumbnail-container" id="thumbnails-${positionCount}"></div>
            <button class="upload-button" onclick="openFileInput(${positionCount})">Загрузить изображения</button>
            <input type="file" multiple class="file-input" accept="image/*" style="display: none;">
        `;
        const thumbnailContainer = newTile.querySelector('.thumbnail-container');
        thumbnailContainer.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        newTile.querySelector('.file-input').addEventListener('change', function(e) {
            handleFileSelection(e, newTile.dataset.position);
        });
        row.appendChild(newTile);
        selectedFiles[positionCount] = [];
    } finally {
        isProcessing = false;
    }
}

// Функция удаления позиции
function deletePosition(positionNumber) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        if (positionCount === 1) {
            alert('Нельзя удалить единственную позицию. Добавьте новую, а потом удалите эту.');
            return;
        }
        if (confirm(`Удалить позицию ${positionNumber}?`)) {
            const tile = document.querySelector(`[data-position="${positionNumber}"]`);
            if (tile) {
                tile.remove();
                const remainingTiles = document.querySelectorAll('.position-tile');
                const oldSelectedFiles = {...selectedFiles};
                selectedFiles = {};
                remainingTiles.forEach((tile, index) => {
                    const oldPosition = tile.dataset.position;
                    const newPosition = index + 1;
                    tile.dataset.position = newPosition;
                    tile.querySelector('.position-number').textContent = newPosition;
                    tile.querySelector('.position-label').textContent = `Фото для ${newPosition}-й позиции`;
                    selectedFiles[newPosition] = oldSelectedFiles[oldPosition] || [];
                    const container = tile.querySelector('.thumbnail-container');
                    container.id = `thumbnails-${newPosition}`;
                    const uploadBtn = tile.querySelector('.upload-button');
                    uploadBtn.onclick = () => openFileInput(newPosition);
                    const fileInput = tile.querySelector('.file-input');
                    fileInput.addEventListener('change', function(e) {
                        handleFileSelection(e, newPosition);
                    });
                    const deleteBtn = tile.querySelector('.delete-position');
                    deleteBtn.onclick = () => deletePosition(newPosition);
                    const clearBtn = tile.querySelector('.clear-photos');
                    clearBtn.onclick = () => clearPhotos(newPosition);
                });
                positionCount = remainingTiles.length;
            }
        }
    } finally {
        isProcessing = false;
    }
}

// Функция очистки фото в позиции
function clearPhotos(positionNumber) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        if (confirm(`Очистить все фотографии с позиции ${positionNumber}?`)) {
            selectedFiles[positionNumber] = [];
            const container = document.getElementById(`thumbnails-${positionNumber}`);
            container.innerHTML = '';
            const tile = document.querySelector(`[data-position="${positionNumber}"]`);
            const input = tile.querySelector('.file-input');
            const newInput = document.createElement('input');
            newInput.type = 'file';
            newInput.multiple = true;
            newInput.classList.add('file-input');
            newInput.accept = 'image/*';
            newInput.style.display = 'none';
            newInput.addEventListener('change', function(e) {
                handleFileSelection(e, positionNumber);
            });
            input.replaceWith(newInput);
            updateFileCount(positionNumber);
        }
    } finally {
        isProcessing = false;
    }
}

// Обработка выбора файлов
function handleFileSelection(event, position) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const files = Array.from(event.target.files);
        if (files.length === 0) {
            return; // Ничего не делать при отмене
        }
        selectedFiles[position] = files;
        const container = document.getElementById(`thumbnails-${position}`);
        container.innerHTML = '';
        files.forEach((file, index) => {
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
                                selectedFiles[position] = selectedFiles[position].filter(f => f !== file);
                                img.remove();
                                updateFileCount(position);
                            }
                        };
                        container.appendChild(img);
                    };
                    image.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
        updateFileCount(position);
    } finally {
        isProcessing = false;
    }
}

// Обновление счётчика файлов
function updateFileCount(position) {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const tile = document.querySelector(`[data-position="${position}"]`);
        const existingBadge = tile.querySelector('.count-badge');
        if (existingBadge) existingBadge.remove();
        const files = selectedFiles[position] || [];
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
function openFileInput(position) {
    const tile = document.querySelector(`[data-position="${position}"]`);
    const fileInput = tile.querySelector('.file-input');
    fileInput.click();
}

// Показ модального окна подтверждения
function showConfirmModal() {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const categoryName = document.getElementById('category-name').value.trim();
        if (!categoryName) {
            alert('Пожалуйста, введите название папки категории');
            return;
        }
        const positions = Array.from(document.querySelectorAll('.position-tile')).map(tile => tile.dataset.position);
        const totalFiles = positions.reduce((sum, pos) => sum + (selectedFiles[pos] ? selectedFiles[pos].length : 0), 0);
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <p><strong>Категория:</strong> <span class="highlight">${categoryName}</span></p>
            <p><strong>Позиции:</strong> ${positions.map(p => `<span class="highlight">${p}</span>`).join(', ')}</p>
            <p><strong>Всего файлов:</strong> <span class="highlight">${totalFiles}</span></p>
            <p style="color: #007bff; font-weight: 500; margin-top: 15px;">Подтвердите создание структуры папок. Выбранные файлы будут автоматически загружены в соответствующие подпапки.</p>
        `;
        document.getElementById('confirm-modal').style.display = 'block';
        document.getElementById('progress-container').style.display = 'none';
        document.getElementById('create-button').disabled = false;
    } finally {
        isProcessing = false;
    }
}

// Закрытие модального окна
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

// Создание структуры папок и загрузка файлов
async function createFolderStructure() {
    if (isProcessing) return;
    isProcessing = true;
    const categoryName = document.getElementById('category-name').value.trim();
    const positions = Array.from(document.querySelectorAll('.position-tile')).map(tile => tile.dataset.position);
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
            body: JSON.stringify({category: categoryName, positions: positions})
        });
        const folderData = await folderResponse.json();
        if (!folderData.success) {
            throw new Error(`Ошибка создания структуры: ${folderData.error}`);
        }
        currentProgress += 100 / totalSteps;
        progressFill.style.width = `${currentProgress}%`;
        let uploadSuccess = true;
        let completedUploads = 0;
        for (let pos of positions) {
            progressText.textContent = `Загрузка файлов для позиции ${pos}...`;
            const files = selectedFiles[pos] || [];
            if (files.length > 0) {
                const formData = new FormData();
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
                        console.error(`Ошибка загрузки файлов для позиции ${pos}: ${uploadData.error}`);
                        uploadSuccess = false;
                    }
                } catch (error) {
                    console.error(`Ошибка при загрузке файлов для позиции ${pos}:`, error);
                    uploadSuccess = false;
                }
            }
            completedUploads++;
            currentProgress += 100 / totalSteps;
            progressFill.style.width = `${Math.min(currentProgress, 100)}%`;
        }
        progressText.textContent = 'Завершение...';
        await new Promise(resolve => setTimeout(resolve, 500));
        progressFill.style.width = '100%';
        closeModal();
        if (uploadSuccess) {
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
                Структура создана и ${Object.values(selectedFiles).reduce((sum, files) => sum + files.length, 0)} файлов загружено
            `;
            document.body.appendChild(successDiv);
            setTimeout(() => {
                successDiv.remove();
            }, 5000);
            document.getElementById('category-name').value = '';
            document.querySelectorAll('.thumbnail-container').forEach(container => container.innerHTML = '');
            document.querySelectorAll('.position-tile').forEach(tile => {
                const badge = tile.querySelector('.count-badge');
                if (badge) badge.remove();
            });
            selectedFiles = {};
            positionCount = 1;
            document.getElementById('position-row').innerHTML = `
                <div class="position-tile active" data-position="1">
                    <button class="clear-photos" onclick="clearPhotos(1)" title="Очистить фотографии">🧹</button>
                    <button class="delete-position" onclick="deletePosition(1)" title="Удалить позицию">🗑️</button>
                    <div class="tile-header">
                        <div class="position-number">1</div>
                        <div class="position-label">Фото для 1-й позиции</div>
                    </div>
                    <div class="thumbnail-container" id="thumbnails-1"></div>
                    <button class="upload-button" onclick="openFileInput(1)">Загрузить изображения</button>
                    <input type="file" multiple class="file-input" accept="image/*" style="display: none;">
                </div>
            `;
            initFirstPosition();
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
                Структура создана, но возникли проблемы с загрузкой файлов. Проверьте логи.
            `;
            document.body.appendChild(warningDiv);
            setTimeout(() => {
                warningDiv.remove();
            }, 5000);
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

// Инициализация первой позиции
function initFirstPosition() {
    if (isProcessing) return;
    isProcessing = true;
    try {
        const firstTile = document.querySelector('.position-tile');
        const thumbnailContainer = firstTile.querySelector('.thumbnail-container');
        thumbnailContainer.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        firstTile.querySelector('.file-input').addEventListener('change', function(e) {
            handleFileSelection(e, this.parentElement.dataset.position);
        });
        selectedFiles[1] = [];
    } finally {
        isProcessing = false;
    }
}

// Обработчик клика вне модального окна
window.onclick = function(event) {
    const modal = document.getElementById('confirm-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Обработчик вкладок
document.querySelectorAll('.tab-link').forEach(tab => {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        document.getElementById(this.dataset.tab).classList.add('active');
    });
});

// Инициализация при загрузке страницы
window.onload = () => {
    initFirstPosition();
    fetchLogs();
    setInterval(fetchLogs, 2000);
};