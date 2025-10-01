from PIL import Image, ImageEnhance
import numpy as np
import math
import random
import os

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

def load_image(path):
    # Загружает изображение в RGB
    return Image.open(path).convert("RGB")

def load_logo(path):
    # Загружает логотип, если существует
    if not os.path.exists(path):
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        from utils import log_message
        log_message(f"Ошибка загрузки логотипа: {e}")
        return None

def random_crop(im, scale_min, scale_max):
    # Случайная обрезка изображения
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
    # Случайный поворот без границ
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
    # Изменяет яркость, контраст, насыщенность
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
    # Уникализирует логотип
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
    # Применяет логотип к изображению
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
    # Уникализирует изображение полностью
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