# server/main.py (обновлен: удалены глобальные BLOCKED_IPS, IP_REQUEST_COUNTS, REQUEST_TIMEOUT, RATE_LIMIT, в security_middleware удален вызов clean_blocked_ips)

import time
import threading
from flask import Flask, request, jsonify, send_from_directory, abort, Response
import logging
from werkzeug.exceptions import BadRequest
import os
import shutil
from modules.utils import get_timestamp, log_message, is_suspicious_request, allowed_file
from modules.ad_processing import process_and_generate

# ===== НАСТРОЙКИ =====
CHECK_INTERVAL = 30
BASE_DIR = os.path.dirname(__file__)
MANAGERS_DIR = os.path.join(BASE_DIR, 'data', 'managers')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'main.txt')
BASE_SERVER_URL = "http://109.172.39.225/"
CLIENT_DIR = os.path.join(BASE_DIR, '..', 'client')

# ===== БЕЗОПАСНОСТЬ =====
ALLOWED_USER_AGENTS = ['Mozilla/5.0', 'Chrome/', 'Safari/', 'Firefox/', 'Edge/']
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

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    client_ip = request.remote_addr
    log_message(f"🚫 Плохой HTTP-запрос от {client_ip} - игнорируем")
    return 'Bad Request', 400

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

@app.route('/api/managers', methods=['GET'])
def list_managers():
    try:
        managers = [d for d in os.listdir(MANAGERS_DIR) if os.path.isdir(os.path.join(MANAGERS_DIR, d))]
        return jsonify(managers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-manager', methods=['POST'])
def create_manager():
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        manager_path = os.path.join(MANAGERS_DIR, name)
        os.makedirs(manager_path, exist_ok=True)
        os.makedirs(os.path.join(manager_path, 'photo_cache'), exist_ok=True)
        os.makedirs(os.path.join(manager_path, 'ready_photos'), exist_ok=True)
        log_message(f"📁 Создана папка для менеджера '{name}'")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rename-manager', methods=['POST'])
def rename_manager():
    try:
        old_name = request.json.get('old_name')
        new_name = request.json.get('new_name')
        if not old_name or not new_name:
            return jsonify({'error': 'Old and new names required'}), 400
        old_path = os.path.join(MANAGERS_DIR, old_name)
        new_path = os.path.join(MANAGERS_DIR, new_name)
        if not os.path.exists(old_path):
            return jsonify({'error': 'Manager not found'}), 404
        if os.path.exists(new_path):
            return jsonify({'error': 'New name already exists'}), 400
        os.rename(old_path, new_path)
        log_message(f"🔄 Менеджер '{old_name}' переименован в '{new_name}'")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-manager', methods=['POST'])
def delete_manager():
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        path = os.path.join(MANAGERS_DIR, name)
        if not os.path.exists(path):
            return jsonify({'error': 'Manager not found'}), 404
        shutil.rmtree(path)
        log_message(f"🗑️ Менеджер '{name}' удален")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list', methods=['GET'])
def list_files():
    manager = request.args.get('manager')
    dir_type = request.args.get('dir')
    if not manager or dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Manager and valid directory required'}), 400
    base_dir = os.path.join(MANAGERS_DIR, manager, dir_type)
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
    data = request.json
    manager = data.get('manager')
    dir_type = data.get('dir')
    if not manager or dir_type not in ['photo_cache', 'ready_photos']:
        return jsonify({'error': 'Manager and valid directory required'}), 400
    base_dir = os.path.join(MANAGERS_DIR, manager, dir_type)
    path = data.get('path')
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
    data = request.json
    manager = data.get('manager')
    category = data.get('category')
    positions = data.get('positions', [])
    if not manager or not category:
        return jsonify({'error': 'Manager and category required'}), 400
    try:
        cache_dir = os.path.join(MANAGERS_DIR, manager, 'photo_cache')
        category_path = os.path.join(cache_dir, category)
        os.makedirs(category_path, exist_ok=True)
        created_folders = []
        for pos in positions:
            pos_path = os.path.join(category_path, pos)
            os.makedirs(pos_path, exist_ok=True)
            created_folders.append(pos)
        log_message(f"📁 Создана структура папок для менеджера '{manager}', категории '{category}': {', '.join(created_folders)}")
        return jsonify({'success': True, 'created': created_folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    manager = request.form.get('manager')
    category = request.form.get('category')
    position = request.form.get('position')
    if not manager or not category or not position:
        return jsonify({'error': 'Manager, category and position required'}), 400
    base_path = os.path.join(MANAGERS_DIR, manager, 'photo_cache', category, position)
    os.makedirs(base_path, exist_ok=True)
    uploaded = []
    for file in request.files.getlist('files'):
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(base_path, filename))
            uploaded.append(filename)
    log_message(f"📥 Загружено {len(uploaded)} файлов для менеджера '{manager}' в {category}/{position}: {', '.join(uploaded)}")
    return jsonify({'success': True, 'uploaded': uploaded})

@app.route('/api/uniquify', methods=['POST'])
def uniquify():
    data = request.json
    manager = data.get('manager')
    folder_name = data.get('folder_name')
    count = data.get('count')
    use_rotation = data.get('use_rotation', True)
    if not manager or not folder_name or not count:
        return jsonify({'error': 'Manager, folder_name and count required'}), 400
    try:
        results = process_and_generate(folder_name, count, use_rotation, manager)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<manager>/photo_cache/<path:path>')
def serve_photo_cache(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'photo_cache'), path)

@app.route('/<manager>/ready_photos/<path:path>')
def serve_ready_photos(manager, path):
    return send_from_directory(os.path.join(MANAGERS_DIR, manager, 'ready_photos'), path)

@app.route('/')
def index():
    return send_from_directory(CLIENT_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename.endswith('.css') or filename.endswith('.js'):
        return send_from_directory(CLIENT_DIR, filename)
    abort(404)

if __name__ == "__main__":
    os.makedirs(MANAGERS_DIR, exist_ok=True)
    log_message("⏳ Сервер запущен")
    app.run(host='0.0.0.0', port=5000, threaded=True)