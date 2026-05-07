# -*- coding: utf-8 -*-
"""
Procesamiento mínimo de imágenes subidas.
Normaliza imágenes editoriales a WebP y genera favicon ICO para logos.
"""
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}


def is_image_file(filename):
    return '.' in (filename or '') and filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS


def _load_pillow():
    try:
        from PIL import Image, ImageOps
        return Image, ImageOps
    except Exception as exc:
        raise RuntimeError('Pillow no está instalado o no está disponible.') from exc


def _safe_basename(filename):
    original_name = secure_filename(filename or 'image')
    stem = Path(original_name).stem or 'image'
    return f"{stem[:36]}-{uuid.uuid4().hex[:12]}"


def image_url(path):
    """Devuelve la URL pública de un archivo en uploads."""
    if not path:
        return None
    from flask import url_for
    return url_for('uploaded_file', filename=os.path.basename(path))


def optimize_image_upload(file, upload_folder, prefix='image', max_size=(1600, 1600), quality=84):
    """
    Convierte una imagen subida a WebP optimizado.
    Retorna (nombre_original, ruta_webp, mime, tamaño).
    """
    if not file or not file.filename or not is_image_file(file.filename):
        raise ValueError('Selecciona una imagen válida.')

    Image, ImageOps = _load_pillow()
    os.makedirs(upload_folder, exist_ok=True)

    original_name = secure_filename(file.filename)
    base_name = f"{prefix}-{_safe_basename(original_name)}"
    output_path = os.path.join(upload_folder, f'{base_name}.webp')

    with Image.open(file.stream) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA' if 'A' in img.getbands() else 'RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        save_kwargs = {'format': 'WEBP', 'quality': quality, 'method': 6}
        if img.mode == 'RGBA':
            save_kwargs['lossless'] = False
        img.save(output_path, **save_kwargs)

    file_size = os.path.getsize(output_path)
    return original_name, output_path, 'image/webp', file_size


def generate_logo_variants(logo_path):
    """
    Genera variantes derivadas del logo ya convertido.
    Retorna diccionario con rutas disponibles.
    """
    if not logo_path or not os.path.exists(logo_path):
        return {}

    Image, ImageOps = _load_pillow()
    base = os.path.splitext(logo_path)[0]
    favicon_path = f'{base}.ico'

    with Image.open(logo_path) as img:
        img = ImageOps.exif_transpose(img).convert('RGBA')
        icon = img.copy()
        icon.thumbnail((256, 256), Image.Resampling.LANCZOS)
        icon.save(favicon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    return {'favicon_path': favicon_path}


def favicon_path_for_logo(logo_path):
    if not logo_path:
        return None
    candidate = os.path.splitext(logo_path)[0] + '.ico'
    return candidate if os.path.exists(candidate) else None
