# filename="ad_processing.py"
# server/modules/ad_processing.py (обновлен: удалено глобальное определение LOGO, порт :5000 сохранен в BASE_SERVER_URL)

"""
Ad Processing Module / Модуль обработки объявлений

This module handles the processing and generation of unique advertisements with watermarked images.
Данный модуль обрабатывает и генерирует уникальные объявления с водяными знаками на изображениях.
"""

import time
import random
import os
import shutil
import concurrent.futures
from modules.image_processing import load_logo, uniquify_image
from modules.utils import log_message

# ===== SETTINGS / НАСТРОЙКИ =====
PHOTOS_PER_AD = 10  # Number of photos per advertisement / Количество фотографий на одно объявление
MAX_ROWS = 5000  # Maximum number of rows in output / Максимальное количество строк в выходном файле
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png")  # Allowed image formats / Разрешённые форматы изображений
BASE_SERVER_URL = "http://109.172.39.225:5000/"  # Base URL for serving images / Базовый URL для раздачи изображений
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Base directory of the project / Базовая директория проекта

def process_ad(i, position_sources, logo, folder_name, local_ready_base, use_rotation, manager):
    """
    Process a single advertisement / Обрабатывает одно объявление
    
    Args:
        i: Advertisement index / Индекс объявления
        position_sources: List of available files for each position / Список доступных файлов для каждой позиции
        logo: Logo image for watermarking / Логотип для водяного знака
        folder_name: Source folder name / Имя исходной папки
        local_ready_base: Base directory for ready ads / Базовая директория для готовых объявлений
        use_rotation: Whether to use rotation for uniquification / Использовать ли поворот для уникализации
        manager: Manager name / Имя менеджера
    
    Returns:
        List with ad number and URLs or None if failed / Список с номером объявления и URL или None при ошибке
    """
    # Create unique directory for this ad / Создаём уникальную директорию для данного объявления
    ad_dir_name = f"ready_ad_{i+1}_{int(time.time())}"
    ad_dir = os.path.join(local_ready_base, ad_dir_name)
    os.makedirs(ad_dir, exist_ok=True)
    
    # Track used files to ensure uniqueness within one ad / Отслеживаем использованные файлы для уникальности в одном объявлении
    used_files = set()
    selected_files = []
    
    # Select unique file for each position / Выбираем уникальный файл для каждой позиции
    for pos_idx, sources in enumerate(position_sources):
        # Filter out already used files / Фильтруем уже использованные файлы
        available = [f for f in sources if f not in used_files]
        if not available:
            log_message(f"⚠️ Нет доступных уникальных файлов для позиции {pos_idx+1} в объявлении {i+1}")
            return None
        # Randomly select a file from available ones / Случайно выбираем файл из доступных
        file = random.choice(available)
        selected_files.append(file)
        used_files.add(file)
    
    # Validate that we collected all required photos / Проверяем, что собрали все необходимые фотографии
    if len(selected_files) != PHOTOS_PER_AD:
        log_message(f"⚠️ Не удалось собрать полное объявление {i+1}")
        return None
    
    # Process each selected file and generate URLs / Обрабатываем каждый выбранный файл и генерируем URL
    ad_links = []
    for j, orig_file in enumerate(selected_files):
        file_name = f"{j+1}.jpg"
        output_file = os.path.join(ad_dir, file_name)
        # Apply watermark and uniquification / Применяем водяной знак и уникализацию
        uniquify_image(orig_file, output_file, logo, use_rotation)
        # Generate public URL for the image / Генерируем публичный URL для изображения
        rel_path = os.path.join(folder_name, ad_dir_name, file_name)
        url = f"{BASE_SERVER_URL}{manager}/ready_photos/{rel_path}"
        ad_links.append(url)
    
    # Return result if all links were generated / Возвращаем результат, если все ссылки сгенерированы
    if len(ad_links) == PHOTOS_PER_AD:
        return [i + 1, "\n".join(ad_links)]
    else:
        return None

def process_and_generate(folder_name, count, use_rotation, manager):
    """
    Process and generate advertisements with unique images / Обрабатывает и генерирует объявления с уникальными изображениями
    
    Args:
        folder_name: Name of the folder with source images / Имя папки с исходными изображениями
        count: Number of advertisements to generate / Количество объявлений для генерации
        use_rotation: Whether to use image rotation for uniquification / Использовать ли поворот изображений для уникализации
        manager: Manager name / Имя менеджера
    
    Returns:
        List of generated ads with their URLs / Список сгенерированных объявлений с их URL
    """
    start_time = time.time()
    try:
        # Build path to photo cache directory / Строим путь к директории кэша фотографий
        cache_dir = os.path.join(BASE_DIR, 'data', 'managers', manager, 'photo_cache')
        local_folder = os.path.join(cache_dir, folder_name)
        
        # Check if source folder exists / Проверяем существование исходной папки
        if not os.path.exists(local_folder):
            error_msg = f"❌ Папка {local_folder} не существует. Загрузите фото через клиент."
            log_message(error_msg)
            return []
        
        log_message(f"📂 использование локальных фото из {local_folder}")
        
        # Scan folder structure / Сканируем структуру папок
        # Get all subfolders in sorted order / Получаем все подпапки в отсортированном порядке
        subfolders = sorted([d for d in os.listdir(local_folder) if os.path.isdir(os.path.join(local_folder, d))])
        num_subfolders = len(subfolders)
        
        # Get files from root folder / Получаем файлы из корневой папки
        root_files = [os.path.join(local_folder, f) for f in os.listdir(local_folder) 
                      if os.path.isfile(os.path.join(local_folder, f)) and f.lower().endswith(ALLOWED_EXTENSIONS)]
        
        # Build list of files for each folder (root + subfolders) / Строим список файлов для каждой папки (корень + подпапки)
        folder_files = [root_files]
        for sub_idx in range(num_subfolders):
            subfolder_path = os.path.join(local_folder, subfolders[sub_idx])
            files = [os.path.join(subfolder_path, f) for f in os.listdir(subfolder_path) 
                    if os.path.isfile(os.path.join(subfolder_path, f)) and f.lower().endswith(ALLOWED_EXTENSIONS)]
            folder_files.append(files)
        # Assign source files to each photo position in the ad / Назначаем исходные файлы для каждой позиции фото в объявлении
        position_sources = []
        has_root = bool(root_files)
        
        for pos in range(PHOTOS_PER_AD):
            if has_root:
                # If root folder has files / Если в корневой папке есть файлы
                if pos == 0:
                    # First position uses only root files / Первая позиция использует только файлы из корня
                    position_sources.append(folder_files[0])
                else:
                    # Other positions combine root + corresponding subfolder / Остальные позиции объединяют корень + соответствующую подпапку
                    idx = min(pos, num_subfolders)
                    combined = folder_files[0] + folder_files[idx]
                    position_sources.append(combined)
            else:
                # If no root files, use only subfolders / Если нет файлов в корне, используем только подпапки
                if num_subfolders == 0:
                    position_sources.append([])
                else:
                    # Distribute positions cyclically across subfolders / Распределяем позиции циклически по подпапкам
                    idx = (pos % num_subfolders) + 1
                    position_sources.append(folder_files[idx])
        
        # Validate that all positions have files / Проверяем, что все позиции имеют файлы
        if any(not files for files in position_sources):
            error_msg = f"❌ В некоторых позициях нет файлов"
            log_message(error_msg)
            return []
        
        # Load logo for watermarking / Загружаем логотип для водяного знака
        logo_path = os.path.join(BASE_DIR, 'data', 'managers', manager, 'img', 'Logo.png')
        logo = load_logo(logo_path)
        
        # Prepare output directory / Подготавливаем выходную директорию
        local_ready_base = os.path.join(BASE_DIR, 'data', 'managers', manager, 'ready_photos', folder_name)
        if os.path.exists(local_ready_base):
            log_message(f"🗑️ удаление старой папки")
            shutil.rmtree(local_ready_base)
        os.makedirs(local_ready_base, exist_ok=True)
        log_message(f"Удаление/создание папки завершено")
        log_message(f"начал уникализировать фотографии")
        
        # Initialize results tracking / Инициализируем отслеживание результатов
        results = [None] * count
        completed_count = 0
        batch_start = time.time()
        
        # Process ads in parallel using multiprocessing / Обрабатываем объявления параллельно с помощью мультипроцессинга
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            # Submit all tasks to the executor / Отправляем все задачи в исполнитель
            futures = [executor.submit(process_ad, i, position_sources, logo, folder_name, local_ready_base, use_rotation, manager) 
                      for i in range(count)]
            
            # Process completed tasks as they finish / Обрабатываем завершённые задачи по мере их выполнения
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    # Store result at correct index / Сохраняем результат по правильному индексу
                    idx = result[0] - 1
                    results[idx] = result
                
                completed_count += 1
                
                # Log progress every 10 ads / Логируем прогресс каждые 10 объявлений
                if completed_count % 10 == 0:
                    log_message(f"Обработка {completed_count} объявлений завершена (время на последние 10: {time.time() - batch_start:.2f} сек)")
                    batch_start = time.time()
                
                # Log milestone every 100 ads / Логируем контрольную точку каждые 100 объявлений
                if completed_count % 100 == 0:
                    log_message(f"{completed_count} объявлений создано")
        
        # Final summary / Итоговая сводка
        log_message(f"Уникализация завершена (общее время: {time.time() - start_time:.2f} сек)")
        
        # Filter out failed ads / Фильтруем неудачные объявления
        results = [r for r in results if r]
        
        # Warn if some ads failed / Предупреждаем, если некоторые объявления не удались
        if len(results) < count:
            log_message(f"⚠️ Создано только {len(results)} объявлений из {count}")
        
        return results
    
    except Exception as e:
        # Handle any errors during processing / Обрабатываем любые ошибки во время обработки
        log_message(f"❌ Ошибка: {str(e)}")
        return []