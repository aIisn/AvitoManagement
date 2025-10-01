# server/modules/google_sheets.py (обновлен: абсолютный путь к конфигу на основе __file__)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os
from modules.ad_processing import process_and_generate
from modules.utils import log_message

# Авторизация в Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'service_account.json')
creds = ServiceAccountCredentials.from_json_keyfile_name(config_path, scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key("1TpLi_ck_HCXmXTFRkJcrOFAee0RhG5O1WxCxOkHYck4")

def safe_get_worksheets(spreadsheet, retries=5, delay=3):
    # Безопасно получает список листов с ретраями
    for i in range(retries):
        try:
            sheets = spreadsheet.worksheets()
            return sheets
        except gspread.exceptions.APIError as e:
            log_message(f"Ошибка API: {e}, попытка {i+1} из {retries}")
            time.sleep(delay)
    log_message("Не удалось получить список листов после нескольких попыток")
    raise Exception("Не удалось получить список листов после нескольких попыток")

def run_program(sheet):
    # Запускает программу для листа
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