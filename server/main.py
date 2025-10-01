# server/main.py (обновлен: абсолютные пути на основе __file__, добавлены роуты для фото, обслуживание client/ через '../client')

import time
import threading
from flask import Flask, request, jsonify, send_from_directory, abort, Response
import logging
from werkzeug.exceptions import BadRequest
import os
import shutil
from modules.utils import get_timestamp, log_message, is_suspicious_request, clean_blocked_ips, allowed_file
from modules.google_sheets import spreadsheet, safe_get_worksheets, run_program
from modules.ad_processing import process_and_generate

# ===== НАСТРОЙКИ =====
CHECK_INTERVAL = 30
BASE_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'photo_cache')
LOCAL_READY_DIR = os.path.join(BASE_DIR, 'data', 'ready_photos')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'main.txt')
BASE_SERVER_URL = "http://109.172.39.225/"
CLIENT_DIR = os.path.join(BASE_DIR, '..', 'client')

# ===== БЕЗОПАСНОСТЬ =====
ALLOWED_USER_AGENTS = ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']
BLOCKED_IPS = set()
IP_REQUEST_COUNTS = {}
REQUEST_TIMEOUT = 300
RATE_LIMIT = 1000  # Увеличено для поддержки больших загрузок
# ======================

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING)

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

@app.route('/photo_cache/<path:path>')
def serve_photo_cache(path):
    return send_from_directory(CACHE_DIR, path)

@app.route('/ready_photos/<path:path>')
def serve_ready_photos(path):
    return send_from_directory(LOCAL_READY_DIR, path)

@app.route('/')
def index():
    return send_from_directory(CLIENT_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename.endswith('.css') or filename.endswith('.js'):
        return send_from_directory(CLIENT_DIR, filename)
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