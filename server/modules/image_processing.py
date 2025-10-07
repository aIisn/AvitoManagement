# server/modules/image_processing.py
# Image Processing Module / Модуль обработки изображений
# Updated: removed incorrect self-import at top level / Обновлён: удален некорректный самоимпорт на верхнем уровне

"""
Image Processing Module / Модуль обработки изображений

This module provides functions for image manipulation, watermarking, and uniquification.
Данный модуль предоставляет функции для манипуляции изображениями, добавления водяных знаков и уникализации.
"""

from PIL import Image, ImageEnhance
import numpy as np
import math
import random
import os

# ===== IMAGE UNIQUIFICATION PARAMETERS / ПАРАМЕТРЫ УНИКАЛИЗАЦИИ ИЗОБРАЖЕНИЯ =====
MAX_ROT_DEG = 2  # Maximum rotation angle in degrees / Максимальный угол поворота в градусах
CROP_SCALE_RANGE = (0.95, 1.0)  # Primary crop scale range / Основной диапазон масштаба обрезки
ALTERNATIVE_CROP_SCALE_RANGE = (0.9, 1.0)  # Alternative crop scale when rotation disabled / Альтернативный диапазон обрезки когда поворот отключён
BRIGHTNESS_RANGE = (0.9, 1.1)  # Image brightness variation range / Диапазон изменения яркости изображения
CONTRAST_RANGE = (0.9, 1.1)  # Image contrast variation range / Диапазон изменения контраста изображения
SATURATION_RANGE = (0.9, 1.1)  # Image saturation variation range / Диапазон изменения насыщенности изображения

# ===== LOGO UNIQUIFICATION PARAMETERS / ПАРАМЕТРЫ УНИКАЛИЗАЦИИ ЛОГОТИПА =====
LOGO_BRIGHTNESS_RANGE = (0.97, 1.03)  # Logo brightness variation range / Диапазон изменения яркости логотипа
LOGO_CONTRAST_RANGE = (0.97, 1.03)  # Logo contrast variation range / Диапазон изменения контраста логотипа
LOGO_SATURATION_RANGE = (0.97, 1.03)  # Logo saturation variation range / Диапазон изменения насыщенности логотипа
LOGO_ALPHA_RANGE = (0.8, 1.0)  # Logo transparency variation range / Диапазон изменения прозрачности логотипа

# ===== OUTPUT QUALITY SETTINGS / НАСТРОЙКИ КАЧЕСТВА ВЫВОДА =====
JPEG_QUALITY = 80  # JPEG compression quality (0-100) / Качество JPEG сжатия (0-100)
JPEG_SUBSAMPLING = 2  # JPEG chroma subsampling / Субдискретизация цветности JPEG

def load_image(path):
    """
    Load image and convert to RGB / Загрузить изображение и конвертировать в RGB
    
    Args:
        path (str): Path to image file / Путь к файлу изображения
    
    Returns:
        Image: PIL Image object in RGB mode / Объект изображения PIL в режиме RGB
    """
    return Image.open(path).convert("RGB")

def load_logo(path):
    """
    Load logo if it exists / Загрузить логотип, если он существует
    
    Args:
        path (str): Path to logo file / Путь к файлу логотипа
    
    Returns:
        Image or None: PIL Image object in RGBA mode or None if file doesn't exist / Объект изображения PIL в режиме RGBA или None если файл не существует
    """
    if not os.path.exists(path):
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        from modules.utils import log_message
        log_message(f"Ошибка загрузки логотипа: {e}")
        return None

def random_crop(im, scale_min, scale_max):
    """
    Randomly crop image and resize back to original size / Случайно обрезать изображение и изменить размер до исходного
    
    Args:
        im (Image): Input image / Входное изображение
        scale_min (float): Minimum scale factor / Минимальный масштабный коэффициент
        scale_max (float): Maximum scale factor / Максимальный масштабный коэффициент
    
    Returns:
        Image: Cropped and resized image / Обрезанное изображение с измененным размером
    """
    w, h = im.size
    scale = random.uniform(scale_min, scale_max)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # If no change in size, return original / Если размер не изменился, вернуть оригинал
    if new_w == w and new_h == h:
        return im
    
    # Random crop position / Случайная позиция обрезки
    left = random.randint(0, w - new_w)
    top = random.randint(0, h - new_h)
    cropped = im.crop((left, top, left + new_w, top + new_h))
    
    # Resize back to original dimensions / Изменить размер обратно до исходных размеров
    return cropped.resize((w, h), Image.LANCZOS)

def random_rotate_no_borders(im, max_deg):
    """
    Randomly rotate image without visible borders / Случайно повернуть изображение без видимых границ
    
    Args:
        im (Image): Input image / Входное изображение
        max_deg (float): Maximum rotation angle in degrees / Максимальный угол поворота в градусах
    
    Returns:
        Image: Rotated and cropped image / Повернутое и обрезанное изображение
    
    The function rotates the image and crops it to remove any borders that would appear.
    Функция поворачивает изображение и обрезает его, чтобы удалить границы.
    """
    w, h = im.size
    angle = random.uniform(-max_deg, max_deg)
    
    # Create white background and paste image / Создать белый фон и вставить изображение
    background = Image.new("RGBA", im.size, (255, 255, 255, 255))
    background.paste(im.convert("RGBA"), (0, 0), im.convert("RGBA"))
    
    # Rotate with expansion / Повернуть с расширением
    rotated = background.rotate(angle, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated.size
    
    # Calculate crop dimensions to remove borders / Вычислить размеры обрезки для удаления границ
    angle_rad = abs(angle) * math.pi / 180.0
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    new_w = int(w * cos_a - h * sin_a)
    new_h = int(h * cos_a - w * sin_a)
    
    # Apply safety scale factor / Применить коэффициент безопасности
    scale_factor = 0.95
    new_w = int(new_w * scale_factor)
    new_h = int(new_h * scale_factor)
    
    # Crop from center / Обрезать из центра
    left = (rw - new_w) // 2
    top = (rh - new_h) // 2
    cropped = rotated.crop((left, top, left + new_w, top + new_h)).convert("RGB")
    
    # Resize back to original size / Изменить размер обратно до исходного
    return cropped.resize((w, h), Image.LANCZOS)

def change_brightness_contrast_saturation(im, b_range, c_range, s_range):
    """
    Randomly adjust brightness, contrast, and saturation / Случайно настроить яркость, контраст и насыщенность
    
    Args:
        im (Image): Input image / Входное изображение
        b_range (tuple): Brightness range (min, max) / Диапазон яркости (мин, макс)
        c_range (tuple): Contrast range (min, max) / Диапазон контраста (мин, макс)
        s_range (tuple): Saturation range (min, max) / Диапазон насыщенности (мин, макс)
    
    Returns:
        Image: Modified image / Модифицированное изображение
    """
    # Generate random factors within ranges / Генерировать случайные коэффициенты в диапазонах
    b = random.uniform(*b_range)
    c = random.uniform(*c_range)
    s = random.uniform(*s_range)
    
    # Apply brightness and contrast / Применить яркость и контраст
    im = ImageEnhance.Brightness(im).enhance(b)
    im = ImageEnhance.Contrast(im).enhance(c)
    
    # Apply saturation using numpy for better control / Применить насыщенность используя numpy для лучшего контроля
    arr = np.array(im).astype(np.float32) / 255.0
    gray = arr.mean(axis=2, keepdims=True)
    arr = np.clip(gray + (arr - gray) * s, 0, 1)
    arr = (arr * 255).astype(np.uint8)
    
    return Image.fromarray(arr)

def unique_logo(logo_rgba, b_range, c_range, s_range, alpha_range):
    """
    Create a unique variant of the logo / Создать уникальный вариант логотипа
    
    Args:
        logo_rgba (Image): Logo image in RGBA mode / Изображение логотипа в режиме RGBA
        b_range (tuple): Brightness range / Диапазон яркости
        c_range (tuple): Contrast range / Диапазон контраста
        s_range (tuple): Saturation range / Диапазон насыщенности
        alpha_range (tuple): Alpha transparency range / Диапазон прозрачности альфа-канала
    
    Returns:
        Image or None: Uniquified logo or None if input is None / Уникализированный логотип или None если вход None
    """
    if logo_rgba is None:
        return None
    
    # Split RGB and alpha channels / Разделить RGB и альфа-каналы
    rgb = Image.merge("RGB", logo_rgba.split()[0:3])
    alpha = logo_rgba.split()[3]
    
    # Apply color modifications to RGB / Применить цветовые модификации к RGB
    rgb = change_brightness_contrast_saturation(rgb, b_range, c_range, s_range)
    
    # Apply random transparency / Применить случайную прозрачность
    alpha_factor = random.uniform(*alpha_range)
    alpha_arr = np.array(alpha).astype(np.float32) * alpha_factor
    alpha_arr = np.clip(alpha_arr, 0, 255).astype(np.uint8)
    alpha = Image.fromarray(alpha_arr)
    
    # Merge back to RGBA / Объединить обратно в RGBA
    return Image.merge("RGBA", (*rgb.split(), alpha))

def apply_logo_to_image(im_rgb, logo_rgba):
    """
    Apply logo watermark to image (bottom-right corner) / Применить водяной знак логотипа к изображению (правый нижний угол)
    
    Args:
        im_rgb (Image): Base image in RGB mode / Базовое изображение в режиме RGB
        logo_rgba (Image): Logo in RGBA mode / Логотип в режиме RGBA
    
    Returns:
        Image: Image with logo applied / Изображение с примененным логотипом
    """
    if logo_rgba is None:
        return im_rgb
    
    # Calculate logo position (bottom-right) / Вычислить позицию логотипа (правый нижний угол)
    w, h = im_rgb.size
    lw, lh = logo_rgba.size
    pos_x = w - lw
    pos_y = h - lh
    
    # Ensure position is not negative / Убедиться что позиция не отрицательная
    if pos_x < 0:
        pos_x = 0
    if pos_y < 0:
        pos_y = 0
    
    # Paste logo with alpha transparency / Вставить логотип с альфа-прозрачностью
    base = im_rgb.convert("RGBA")
    base.paste(logo_rgba, (pos_x, pos_y), logo_rgba)
    
    return base.convert("RGB")

def uniquify_image(input_path, output_path, logo, use_rotation):
    """
    Apply complete uniquification pipeline to an image / Применить полный пайплайн уникализации к изображению
    
    Args:
        input_path (str): Path to input image / Путь к входному изображению
        output_path (str): Path to save output image / Путь для сохранения выходного изображения
        logo (Image): Logo to apply as watermark / Логотип для применения в качестве водяного знака
        use_rotation (bool): Whether to use rotation (if False, uses alternative crop) / Использовать ли поворот (если False, использует альтернативную обрезку)
    
    The uniquification process includes / Процесс уникализации включает:
    1. Random crop / Случайная обрезка
    2. Rotation (if enabled) or additional crop / Поворот (если включён) или дополнительная обрезка
    3. Brightness/contrast/saturation adjustments / Настройка яркости/контраста/насыщенности
    4. Logo watermark with variations / Водяной знак логотипа с вариациями
    5. JPEG compression with quality settings / JPEG сжатие с настройками качества
    """
    # Load original image / Загрузить исходное изображение
    im = load_image(input_path)
    
    # Apply first crop / Применить первую обрезку
    im2 = random_crop(im, *CROP_SCALE_RANGE)
    
    # Apply rotation or additional crop / Применить поворот или дополнительную обрезку
    if use_rotation:
        im2 = random_rotate_no_borders(im2, MAX_ROT_DEG)
    else:
        im2 = random_crop(im2, *ALTERNATIVE_CROP_SCALE_RANGE)
    
    # Apply color adjustments / Применить цветовые настройки
    im2 = change_brightness_contrast_saturation(im2, BRIGHTNESS_RANGE, CONTRAST_RANGE, SATURATION_RANGE)
    
    # Create unique logo variant / Создать уникальный вариант логотипа
    unique_logo_variant = unique_logo(logo, LOGO_BRIGHTNESS_RANGE, LOGO_CONTRAST_RANGE, LOGO_SATURATION_RANGE, LOGO_ALPHA_RANGE)
    
    # Apply logo watermark / Применить водяной знак логотипа
    variant_with_logo = apply_logo_to_image(im2, unique_logo_variant)
    
    # Save with JPEG compression / Сохранить с JPEG сжатием
    variant_with_logo.save(output_path, "JPEG", quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING, optimize=True, progressive=True)