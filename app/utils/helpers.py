# -*- coding: utf-8 -*-
"""
Funciones auxiliares.
"""
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
    'xls', 'xlsx', 'csv', 'txt', 'zip', 'rar'
}


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, upload_folder):
    """
    Guarda un archivo subido con nombre único.
    Retorna (nombre_original, ruta_guardada, tipo_mime, tamaño).
    """
    original_name = secure_filename(file.filename)
    # Generar nombre único para evitar colisiones
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    filepath = os.path.join(upload_folder, unique_name)

    file.save(filepath)
    file_size = os.path.getsize(filepath)

    return original_name, filepath, file.content_type, file_size


def format_datetime(dt, fmt='%d/%m/%Y %H:%M'):
    """Formatea un datetime para visualización."""
    if dt is None:
        return '—'
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime(fmt)


def format_date(dt, fmt='%d/%m/%Y'):
    """Formatea solo la fecha."""
    if dt is None:
        return '—'
    return dt.strftime(fmt)
