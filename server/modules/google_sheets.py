# server/modules/google_sheets.py
# Google Sheets Integration Module / Модуль интеграции с Google Sheets
# Updated: absolute path to config based on __file__ / Обновлён: абсолютный путь к конфигу на основе __file__

"""
Google Sheets Module / Модуль Google Sheets

This module handles Google Sheets API integration for managing advertisement generation tasks.
Данный модуль обрабатывает интеграцию с Google Sheets API для управления задачами генерации объявлений.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os
from modules.ad_processing import process_and_generate
from modules.utils import log_message

# Google Sheets authorization / Авторизация в Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'service_account.json')
creds = ServiceAccountCredentials.from_json_keyfile_name(config_path, scope)
client = gspread.authorize(creds)

# Open target spreadsheet / Открываем целевую таблицу
spreadsheet = client.open_by_key("1TpLi_ck_HCXmXTFRkJcrOFAee0RhG5O1WxCxOkHYck4")

def safe_get_worksheets(spreadsheet, retries=5, delay=3):
    """
    Safely get worksheets list with retries / Безопасно получить список листов с повторными попытками
    
    Args:
        spreadsheet: Google Sheets spreadsheet object / Объект таблицы Google Sheets
        retries: Number of retry attempts / Количество повторных попыток
        delay: Delay between retries in seconds / Задержка между попытками в секундах
    
    Returns:
        list: List of worksheet objects / Список объектов листов
    
    Raises:
        Exception: If unable to get worksheets after all retries / Если не удалось получить листы после всех попыток
    """
    for i in range(retries):
        try:
            sheets = spreadsheet.worksheets()
            return sheets
        except gspread.exceptions.APIError as e:
            log_message(f"Ошибка API: {e}, попытка {i+1} из {retries}")
            time.sleep(delay)
    error_msg = "❌ Не удалось получить список листов после нескольких попыток"
    log_message(error_msg)
    raise Exception(error_msg)

def run_program(sheet):
    """
    Run the advertisement generation program for a specific worksheet / Запустить программу генерации объявлений для конкретного листа
    
    Args:
        sheet: Google Sheets worksheet object / Объект листа Google Sheets
    
    The function reads configuration from cells C2, C4, C6, C8:
    - C2: Count of ads to generate / Количество объявлений для генерации
    - C4: "Да"/"Нет" flag to enable processing / Флаг "Да"/"Нет" для включения обработки
    - C6: Folder name with source photos / Имя папки с исходными фото
    - C8: Rotation flag (default "Да") / Флаг поворота (по умолчанию "Да")
    
    После обработки функция считывает конфигурацию из ячеек C2, C4, C6, C8:
    - C2: Количество объявлений для генерации
    - C4: Флаг "Да"/"Нет" для включения обработки
    - C6: Имя папки с исходными фото
    - C8: Флаг поворота (по умолчанию "Да")
    """
    start_time = time.time()
    try:
        # Read configuration cells / Читаем ячейки конфигурации
        values = sheet.batch_get(["C2", "C4", "C6", "C8"])
        count = int(values[0][0][0]) if values[0] and values[0][0] else None
        flag = values[1][0][0] if values[1] and values[1][0] else None
        folder_name = values[2][0][0] if values[2] and values[2][0] else None
        rotate_value = values[3][0][0] if values[3] and values[3][0] else "Да"
    except Exception as e:
        log_message(f"❌ [{sheet.title}] Ошибка при получении ячеек C2, C4, C6, C8: {e}")
        return
    
    # Validate required parameters / Проверяем обязательные параметры
    if not count:
        log_message(f"❌ [{sheet.title}] Не удалось получить число объявлений из C2")
        return
    if not folder_name:
        log_message(f"❌ [{sheet.title}] Нет названия папки в C6")
        return
    if not flag or flag.strip().lower() != "да":
        log_message(f"⏸ [{sheet.title}] Флаг 'Да' не установлен, пропуск.")
        return
    
    # Parse rotation flag / Разбираем флаг поворота
    use_rotation = rotate_value.strip().lower() == "да"
    folder_name = folder_name.strip('/')
    log_message(f"📂 [{sheet.title}] Используемый путь: {folder_name}")
    log_message(f"🔄 [{sheet.title}] Вращать картинки: {'Да' if use_rotation else 'Нет'}")
    # Process and generate ads / Обрабатываем и генерируем объявления
    if not process_and_generate(sheet, folder_name, count, use_rotation):
        return
    
    # Reset flag after successful processing / Сбрасываем флаг после успешной обработки
    sheet.update(values=[["Нет"]], range_name="C4")
    log_message(f"✅ [{sheet.title}] работа скрипта завершена")
    log_message(f"Общая обработка завершена (время: {time.time() - start_time:.2f} сек)")