import time
import random
import os
import shutil
import concurrent.futures
from image_processing import load_logo, uniquify_image
from utils import log_message

# ===== НАСТРОЙКИ =====
PHOTOS_PER_AD = 10
MAX_ROWS = 5000
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png")
LOGO = "Logo.png"
BASE_SERVER_URL = "http://109.172.39.225/"
CACHE_DIR = "photo_cache"
LOCAL_READY_DIR = "ready_photos"

def process_ad(i, position_sources, logo, sheet_title, local_ready_base, use_rotation):
    # Обрабатывает одно объявление
    ad_dir_name = f"ready_ad_{i+1}_{int(time.time())}"
    ad_dir = os.path.join(local_ready_base, ad_dir_name)
    os.makedirs(ad_dir, exist_ok=True)
    
    used_files = set()
    selected_files = []
    for pos_idx, sources in enumerate(position_sources):
        available = [f for f in sources if f not in used_files]
        if not available:
            log_message(f"⚠️ [{sheet_title}] Нет доступных уникальных файлов для позиции {pos_idx+1} в объявлении {i+1}")
            return None
        file = random.choice(available)
        selected_files.append(file)
        used_files.add(file)
    
    if len(selected_files) != PHOTOS_PER_AD:
        log_message(f"⚠️ [{sheet_title}] Не удалось собрать полное объявление {i+1}")
        return None
    
    ad_links = []
    for j, orig_file in enumerate(selected_files):
        file_name = f"{j+1}.jpg"
        output_file = os.path.join(ad_dir, file_name)
        uniquify_image(orig_file, output_file, logo, use_rotation)
        rel_path = os.path.join(sheet_title, ad_dir_name, file_name)
        url = f"{BASE_SERVER_URL}ready_photos/{rel_path}"
        ad_links.append(url)
    
    if len(ad_links) == PHOTOS_PER_AD:
        return [i + 1, "\n".join(ad_links)]
    else:
        return None

def process_and_generate(sheet, folder_name, count, use_rotation):
    # Обрабатывает и генерирует объявления
    start_time = time.time()
    sheet_title = sheet.title
    try:
        local_folder = os.path.join(CACHE_DIR, folder_name)
        if not os.path.exists(local_folder):
            error_msg = f"❌ [{sheet_title}] Папка {local_folder} не существует. Загрузите фото через клиент."
            log_message(error_msg)
            return False
        log_message(f"📂 [{sheet_title}] использование локальных фото из {local_folder}")
        subfolders = sorted([d for d in os.listdir(local_folder) if os.path.isdir(os.path.join(local_folder, d))])
        num_subfolders = len(subfolders)
        root_files = [os.path.join(local_folder, f) for f in os.listdir(local_folder) if os.path.isfile(os.path.join(local_folder, f)) and f.lower().endswith(ALLOWED_EXTENSIONS)]
        folder_files = [root_files]
        for sub_idx in range(num_subfolders):
            subfolder_path = os.path.join(local_folder, subfolders[sub_idx])
            files = [os.path.join(subfolder_path, f) for f in os.listdir(subfolder_path) if os.path.isfile(os.path.join(subfolder_path, f)) and f.lower().endswith(ALLOWED_EXTENSIONS)]
            folder_files.append(files)
        position_sources = []
        for pos in range(PHOTOS_PER_AD):
            if pos == 0:
                position_sources.append(folder_files[0])
            else:
                idx = pos if pos <= num_subfolders else num_subfolders
                combined = folder_files[0] + folder_files[idx]
                position_sources.append(combined)
        if not position_sources[0] and num_subfolders > 0:
            position_sources[0] = folder_files[1]
        if any(not files for files in position_sources):
            error_msg = f"❌ [{sheet_title}] В некоторых позициях нет файлов"
            log_message(error_msg)
            return False
        logo = load_logo(LOGO)
        local_ready_base = os.path.join(LOCAL_READY_DIR, sheet_title)
        if os.path.exists(local_ready_base):
            log_message(f"🗑️ [{sheet_title}] удаление старой папки")
            shutil.rmtree(local_ready_base)
        os.makedirs(local_ready_base, exist_ok=True)
        log_message(f"Удаление/создание папки завершено")
        log_message(f"[{sheet_title}] начал уникализировать фотографии")
        results = [None] * count
        completed_count = 0
        batch_start = time.time()
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_ad, i, position_sources, logo, sheet_title, local_ready_base, use_rotation) for i in range(count)]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    idx = result[0] - 1
                    results[idx] = result
                completed_count += 1
                if completed_count % 10 == 0:
                    log_message(f"Обработка {completed_count} объявлений завершена (время на последние 10: {time.time() - batch_start:.2f} сек)")
                    batch_start = time.time()
                if completed_count % 100 == 0:
                    log_message(f"[{sheet_title}] {completed_count} объявлений создано")
        log_message(f"Уникализация завершена (общее время: {time.time() - start_time:.2f} сек)")
        results = [r for r in results if r]
        if len(results) < count:
            log_message(f"⚠️ [{sheet_title}] Создано только {len(results)} объявлений из {count}")
        while len(results) < MAX_ROWS - 1:
            results.append(["", ""])
        sheet.update(values=results, range_name=f"A2:B{MAX_ROWS}")
        log_message(f"✅ [{sheet_title}] Ссылки записаны в колонку B")
        return True
    except Exception as e:
        log_message(f"❌ [{sheet_title}] Ошибка: {str(e)}")
        return False