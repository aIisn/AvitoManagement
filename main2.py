import time
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import shutil
from PIL import Image, ImageEnhance
import numpy as np
import math
import concurrent.futures
import threading
from flask import Flask, request, jsonify, send_from_directory, abort, Response
import logging
from werkzeug.exceptions import BadRequest
import pytz
from datetime import datetime

# ===== НАСТРОЙКИ =====
GOOGLE_JSON = "service_account.json"
SPREADSHEET_ID = "1TpLi_ck_HCXmXTFRkJcrOFAee0RhG5O1WxCxOkHYck4"
CHECK_INTERVAL = 30
PHOTOS_PER_AD = 10
MAX_ROWS = 5000

ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png")

CACHE_DIR = "photo_cache"
LOCAL_READY_DIR = "ready_photos"
LOGO = "Logo.png"
LOG_FILE = "main.txt"

BASE_SERVER_URL = "http://109.172.39.225/"

# Параметры уникализации для изображения
MAX_ROT_DEG = 2
CROP_SCALE_RANGE = (0.95, 1.0)
ALTERNATIVE_CROP_SCALE_RANGE = (0.9, 1.0)
BRIGHTNESS_RANGE = (0.9, 1.1)
CONTRAST_RANGE = (0.9, 1.1)
SATURATION_RANGE = (0.9, 1.1)

# Параметры уникализации для логотипа
LOGO_BRIGHTNESS_RANGE = (0.97, 1.03)
LOGO_CONTRAST_RANGE = (0.97, 1.03)
LOGO_SATURATION_RANGE = (0.97, 1.03)
LOGO_ALPHA_RANGE = (0.8, 1.0)

JPEG_QUALITY = 80
JPEG_SUBSAMPLING = 2

# ===== БЕЗОПАСНОСТЬ =====
ALLOWED_USER_AGENTS = ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']
BLOCKED_IPS = set()
IP_REQUEST_COUNTS = {}
REQUEST_TIMEOUT = 300
RATE_LIMIT = 1000  # Увеличено для поддержки больших загрузок
# ======================

# Авторизация в Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key(SPREADSHEET_ID)

def safe_get_worksheets(spreadsheet, retries=5, delay=3):
    for i in range(retries):
        try:
            sheets = spreadsheet.worksheets()
            return sheets
        except gspread.exceptions.APIError as e:
            log_message(f"Ошибка API: {e}, попытка {i+1} из {retries}")
            time.sleep(delay)
    log_message("Не удалось получить список листов после нескольких попыток")
    raise Exception("Не удалось получить список листов после нескольких попыток")

def get_timestamp():
    tz = pytz.timezone('Europe/Moscow')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def log_message(message):
    timestamp = get_timestamp()
    log_entry = f"{timestamp} - {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def is_suspicious_request():
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    method = request.method
    
    if request.path == '/api/logs':
        return False
    
    if not any(ua in user_agent for ua in ALLOWED_USER_AGENTS):
        log_message(f"🚫 Подозрительный User-Agent от {client_ip}: {user_agent[:100]}")
        return True
    
    if method not in ['GET', 'POST', 'HEAD', 'OPTIONS']:
        log_message(f"🚫 Неизвестный метод {method} от {client_ip}")
        return True
    
    IP_REQUEST_COUNTS[client_ip] = IP_REQUEST_COUNTS.get(client_ip, 0) + 1
    
    if IP_REQUEST_COUNTS[client_ip] > RATE_LIMIT:
        BLOCKED_IPS.add(client_ip)
        log_message(f"🚫 IP {client_ip} заблокирован временно (слишком много запросов)")
        return True
    
    if client_ip in BLOCKED_IPS:
        return True
    
    return False

def clean_blocked_ips():
    current_time = time.time()
    expired_ips = []
    for ip in BLOCKED_IPS:
        if current_time - IP_REQUEST_COUNTS.get(ip, 0) > REQUEST_TIMEOUT:
            expired_ips.append(ip)
    
    for ip in expired_ips:
        BLOCKED_IPS.discard(ip)
        if ip in IP_REQUEST_COUNTS:
            del IP_REQUEST_COUNTS[ip]

def load_image(path):
    return Image.open(path).convert("RGB")

def load_logo(path):
    if not os.path.exists(path):
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        log_message(f"Ошибка загрузки логотипа: {e}")
        return None

def random_crop(im, scale_min, scale_max):
    w, h = im.size
    scale = random.uniform(scale_min, scale_max)
    new_w = int(w * scale)
    new_h = int(h * scale)
    if new_w == w and new_h == h:
        return im
    left = random.randint(0, w - new_w)
    top = random.randint(0, h - new_h)
    cropped = im.crop((left, top, left + new_w, top + new_h))
    return cropped.resize((w, h), Image.LANCZOS)

def random_rotate_no_borders(im, max_deg):
    w, h = im.size
    angle = random.uniform(-max_deg, max_deg)
    background = Image.new("RGBA", im.size, (255, 255, 255, 255))
    background.paste(im.convert("RGBA"), (0, 0), im.convert("RGBA"))
    rotated = background.rotate(angle, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated.size
    angle_rad = abs(angle) * math.pi / 180.0
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    new_w = int(w * cos_a - h * sin_a)
    new_h = int(h * cos_a - w * sin_a)
    scale_factor = 0.95
    new_w = int(new_w * scale_factor)
    new_h = int(new_h * scale_factor)
    left = (rw - new_w) // 2
    top = (rh - new_h) // 2
    cropped = rotated.crop((left, top, left + new_w, top + new_h)).convert("RGB")
    return cropped.resize((w, h), Image.LANCZOS)

def change_brightness_contrast_saturation(im, b_range, c_range, s_range):
    b = random.uniform(*b_range)
    c = random.uniform(*c_range)
    s = random.uniform(*s_range)
    im = ImageEnhance.Brightness(im).enhance(b)
    im = ImageEnhance.Contrast(im).enhance(c)
    arr = np.array(im).astype(np.float32) / 255.0
    gray = arr.mean(axis=2, keepdims=True)
    arr = np.clip(gray + (arr - gray) * s, 0, 1)
    arr = (arr * 255).astype(np.uint8)
    return Image.fromarray(arr)

def unique_logo(logo_rgba, b_range, c_range, s_range, alpha_range):
    if logo_rgba is None:
        return None
    rgb = Image.merge("RGB", logo_rgba.split()[0:3])
    alpha = logo_rgba.split()[3]
    rgb = change_brightness_contrast_saturation(rgb, b_range, c_range, s_range)
    alpha_factor = random.uniform(*alpha_range)
    alpha_arr = np.array(alpha).astype(np.float32) * alpha_factor
    alpha_arr = np.clip(alpha_arr, 0, 255).astype(np.uint8)
    alpha = Image.fromarray(alpha_arr)
    return Image.merge("RGBA", (*rgb.split(), alpha))

def apply_logo_to_image(im_rgb, logo_rgba):
    if logo_rgba is None:
        return im_rgb
    w, h = im_rgb.size
    lw, lh = logo_rgba.size
    pos_x = w - lw
    pos_y = h - lh
    if pos_x < 0:
        pos_x = 0
    if pos_y < 0:
        pos_y = 0
    base = im_rgb.convert("RGBA")
    base.paste(logo_rgba, (pos_x, pos_y), logo_rgba)
    return base.convert("RGB")

def uniquify_image(input_path, output_path, logo, use_rotation):
    im = load_image(input_path)
    im2 = random_crop(im, *CROP_SCALE_RANGE)
    if use_rotation:
        im2 = random_rotate_no_borders(im2, MAX_ROT_DEG)
    else:
        im2 = random_crop(im2, *ALTERNATIVE_CROP_SCALE_RANGE)
    im2 = change_brightness_contrast_saturation(im2, BRIGHTNESS_RANGE, CONTRAST_RANGE, SATURATION_RANGE)
    unique_logo_variant = unique_logo(logo, LOGO_BRIGHTNESS_RANGE, LOGO_CONTRAST_RANGE, LOGO_SATURATION_RANGE, LOGO_ALPHA_RANGE)
    variant_with_logo = apply_logo_to_image(im2, unique_logo_variant)
    variant_with_logo.save(output_path, "JPEG", quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING, optimize=True, progressive=True)

def process_ad(i, position_sources, logo, sheet_title, local_ready_base, use_rotation):
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

def run_program(sheet):
    start_time = time.time()
    try:
        values = sheet.batch_get(["C2", "C4", "C6", "C8"])
        count = int(values[0][0][0]) if values[0] and values[0][0] else None
        flag = values[1][0][0] if values[1] and values[1][0] else None
        folder_name = values[2][0][0] if values[2] and values[2][0] else None
        rotate_value = values[3][0][0] if values[3] and values[3][0] else "Да"
    except Exception as e:
        log_message(f"❌ [{sheet.title}] Ошибка при получении ячеек C2, C4, C6, C8: {e}")
        return
    if not count:
        log_message(f"❌ [{sheet.title}] Не удалось получить число объявлений из C2")
        return
    if not folder_name:
        log_message(f"❌ [{sheet.title}] Нет названия папки в C6")
        return
    if not flag or flag.strip().lower() != "да":
        log_message(f"⏸ [{sheet.title}] Флаг 'Да' не установлен, пропуск.")
        return
    use_rotation = rotate_value.strip().lower() == "да"
    folder_name = folder_name.strip('/')
    log_message(f"📂 [{sheet.title}] Используемый путь: {folder_name}")
    log_message(f"🔄 [{sheet.title}] Вращать картинки: {'Да' if use_rotation else 'Нет'}")
    if not process_and_generate(sheet, folder_name, count, use_rotation):
        return
    sheet.update(values=[["Нет"]], range_name="C4")
    log_message(f"✅ [{sheet.title}] работа скрипта завершена")
    log_message(f"Общая обработка завершена (время: {time.time() - start_time:.2f} сек)")

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def security_middleware():
    if is_suspicious_request():
        abort(403)
    if request.path.startswith('/api/'):
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        if request.method == 'OPTIONS':
            return response
    clean_blocked_ips()

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    client_ip = request.remote_addr
    log_message(f"🚫 Плохой HTTP-запрос от {client_ip} - игнорируем")
    return 'Bad Request', 400

@app.route('/api/sheets', methods=['GET'])
def get_sheets():
    try:
        sheets = [s.title for s in safe_get_worksheets(spreadsheet)]
        return jsonify(sheets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            last_20 = lines[-20:] if len(lines) > 20 else lines
            return jsonify({'logs': [line.strip() for line in last_20]})
        return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list', methods=['GET'])
def list_files():
    dir_type = request.args.get('dir')
    if dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Invalid directory'}), 400
    base_dir = CACHE_DIR if dir_type == 'photo_cache' else LOCAL_READY_DIR
    path = request.args.get('path', '')
    full_path = os.path.normpath(os.path.join(base_dir, path))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path):
        return jsonify({'error': 'Invalid path'}), 400
    items = []
    for item in sorted(os.listdir(full_path)):
        item_path = os.path.join(full_path, item)
        rel_path = os.path.relpath(item_path, base_dir)
        item_type = 'dir' if os.path.isdir(item_path) else 'file'
        items.append({'name': item, 'type': item_type, 'path': rel_path})
    return jsonify({'children': items})

@app.route('/api/delete', methods=['POST'])
def delete_item():
    dir_type = request.json.get('dir')
    if dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Invalid directory'}), 400
    base_dir = CACHE_DIR if dir_type == 'photo_cache' else LOCAL_READY_DIR
    path = request.json.get('path')
    full_path = os.path.normpath(os.path.join(base_dir, path))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path) or full_path == base_dir:
        return jsonify({'error': 'Invalid path or cannot delete root'}), 400
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-folder-structure', methods=['POST'])
def create_folder_structure():
    category = request.json.get('category')
    positions = request.json.get('positions', [])
    if not category:
        return jsonify({'error': 'Category required'}), 400
    try:
        category_path = os.path.join(CACHE_DIR, category)
        os.makedirs(category_path, exist_ok=True)
        created_folders = []
        for pos in positions:
            pos_path = os.path.join(category_path, pos)
            os.makedirs(pos_path, exist_ok=True)
            created_folders.append(pos)
        log_message(f"📁 Создана структура папок для категории '{category}': {', '.join(created_folders)}")
        return jsonify({'success': True, 'created': created_folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    category = request.form.get('category')
    position = request.form.get('position')
    if not category or not position:
        return jsonify({'error': 'Category and position required'}), 400
    base_path = os.path.join(CACHE_DIR, category, position)
    os.makedirs(base_path, exist_ok=True)
    uploaded = []
    for file in request.files.getlist('files'):
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(base_path, filename))
            uploaded.append(filename)
    log_message(f"📥 Загружено {len(uploaded)} файлов в {category}/{position}: {', '.join(uploaded)}")
    return jsonify({'success': True, 'uploaded': uploaded})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename.endswith('.css') or filename.endswith('.js'):
        return send_from_directory('.', filename)
    abort(404)

if __name__ == "__main__":
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(LOCAL_READY_DIR, exist_ok=True)
    log_message("⏳ Ожидание флага 'Да' в C4 на всех листах...")
    def main_loop():
        while True:
            try:
                sheets = safe_get_worksheets(spreadsheet)
                for sheet in sheets:
                    run_program(sheet)
            except Exception as e:
                log_message(f"⚠️ Не удалось обработать листы: {e}, повтор через {CHECK_INTERVAL} сек.")
            time.sleep(CHECK_INTERVAL)
    threading.Thread(target=main_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, threaded=True)