# -*- coding: utf-8 -*-
"""Uploads seguros para editores de texto enriquecido."""
import os

from flask import Blueprint, current_app, url_for, request
from flask_login import login_required

from ..services.image_service import image_url, optimize_image_upload
from ..utils.decorators import role_required
from ..utils.helpers import save_upload

editor_bp = Blueprint('editor', __name__, url_prefix='/editor')


def _is_pdf_upload(file):
    filename = (file.filename or '').lower()
    mimetype = (file.content_type or '').lower()
    return filename.endswith('.pdf') and mimetype in {
        'application/pdf',
        'application/x-pdf',
        'binary/octet-stream',
        'application/octet-stream',
        '',
    }


@editor_bp.route('/upload', methods=['POST'])
@login_required
@role_required('administrador', 'manager', 'usuario')
def upload():
    """Sube imágenes o PDFs para incrustarlos como contenido enriquecido."""
    file = request.files.get('file')
    upload_type = (request.form.get('type') or '').lower()

    if not file or not file.filename:
        return {'error': 'Selecciona un archivo válido.'}, 400

    if upload_type == 'image':
        try:
            original_name, ruta, mime, size = optimize_image_upload(
                file,
                current_app.config['UPLOAD_FOLDER'],
                prefix='editor-image',
                max_size=(1800, 1800),
                quality=84,
            )
        except Exception as exc:
            return {'error': str(exc)}, 400

        return {
            'type': 'image',
            'name': original_name,
            'url': image_url(ruta),
            'mime': mime,
            'size': size,
        }

    if upload_type == 'pdf':
        if not _is_pdf_upload(file):
            return {'error': 'El archivo debe ser un PDF válido.'}, 400

        original_name, ruta, mime, size = save_upload(file, current_app.config['UPLOAD_FOLDER'])
        if not ruta.lower().endswith('.pdf') or not os.path.exists(ruta):
            return {'error': 'No se pudo guardar el PDF.'}, 400

        return {
            'type': 'pdf',
            'name': original_name,
            'url': url_for('uploaded_file', filename=os.path.basename(ruta)),
            'mime': mime or 'application/pdf',
            'size': size,
        }

    return {'error': 'Tipo de carga no permitido.'}, 400
