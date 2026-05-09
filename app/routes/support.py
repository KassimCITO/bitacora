# -*- coding: utf-8 -*-
"""Chat de ayuda y soporte técnico."""
import os

from flask import (
    Blueprint, abort, current_app, flash, jsonify, redirect, render_template,
    request, send_file, session, url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models.company import Company
from ..models.support import SupportAttachment, SupportMessage, SupportThread
from ..services.support_service import build_whatsapp_url
from ..utils.decorators import superuser_required
from ..utils.helpers import allowed_file, save_upload

support_bp = Blueprint('support', __name__, url_prefix='/support')


def _get_empresa_id():
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


def _get_company():
    empresa_id = _get_empresa_id()
    return db.session.get(Company, empresa_id) if empresa_id else None


def _thread_query():
    empresa_id = _get_empresa_id()
    if not empresa_id:
        return None
    query = SupportThread.query.filter_by(empresa_id=empresa_id)
    if not current_user.is_superuser:
        query = query.filter_by(user_id=current_user.id)
    return query


def _get_thread(thread_id):
    query = _thread_query()
    if query is None:
        abort(403)
    return query.filter_by(id=thread_id).first_or_404()


def _serialize_attachment(attachment, thread):
    return {
        'id': attachment.id,
        'name': attachment.nombre_archivo,
        'mime': attachment.tipo_mime,
        'size': attachment.tamano,
        'url': url_for('support.download_attachment', thread_id=thread.id, att_id=attachment.id),
    }


def _serialize_message(message):
    thread = message.thread
    return {
        'id': message.id,
        'body': message.body,
        'is_staff': message.is_staff,
        'author': message.user.nombre_completo,
        'created_at': message.created_at.strftime('%d/%m/%Y %H:%M'),
        'attachments': [
            _serialize_attachment(attachment, thread)
            for attachment in message.attachments.order_by(SupportAttachment.fecha_subida.asc()).all()
        ],
    }


def _whatsapp_message(thread):
    company = thread.empresa
    company_name = company.nombre if company else 'Bitácora'
    return (
        f'Hola, necesito ayuda con el ticket #{thread.id}: {thread.subject}\n'
        f'Empresa: {company_name}\n'
        f'Usuario: {thread.user.nombre_completo}'
    )


@support_bp.route('/')
@login_required
def index():
    company = _get_company()
    if not company:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = _thread_query()
    if status:
        query = query.filter_by(status=status)
    pagination = query.order_by(SupportThread.updated_at.desc()).paginate(
        page=page,
        per_page=current_app.config.get('TASKS_PER_PAGE', 15),
        error_out=False,
    )

    return render_template(
        'support/list.html',
        threads=pagination.items,
        pagination=pagination,
        statuses=SupportThread.STATUS,
        priorities=SupportThread.PRIORITIES,
        filter_status=status,
        company=company,
    )


@support_bp.route('/create', methods=['POST'])
@login_required
def create():
    company = _get_company()
    if not company:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    priority = request.form.get('priority', 'media')
    if not subject or not body:
        flash('Captura asunto y mensaje para abrir el chat.', 'warning')
        return redirect(url_for('support.index'))

    thread = SupportThread(
        subject=subject[:180],
        priority=priority if priority in dict(SupportThread.PRIORITIES) else 'media',
        empresa_id=company.id,
        user_id=current_user.id,
        whatsapp_phone=company.support_whatsapp_phone,
    )
    db.session.add(thread)
    db.session.flush()
    message = SupportMessage(
        thread_id=thread.id,
        user_id=current_user.id,
        body=body,
        is_staff=current_user.is_superuser,
    )
    db.session.add(message)
    db.session.commit()

    flash('Chat de soporte abierto correctamente.', 'success')
    return redirect(url_for('support.detail', thread_id=thread.id))


@support_bp.route('/<int:thread_id>')
@login_required
def detail(thread_id):
    thread = _get_thread(thread_id)
    company = thread.empresa
    messages = thread.messages.order_by(SupportMessage.created_at.asc()).all()
    whatsapp_url = build_whatsapp_url(thread.whatsapp_phone, _whatsapp_message(thread))

    return render_template(
        'support/detail.html',
        thread=thread,
        messages=messages,
        company=company,
        whatsapp_url=whatsapp_url,
        statuses=SupportThread.STATUS,
    )


@support_bp.route('/<int:thread_id>/messages', methods=['GET', 'POST'])
@login_required
def messages(thread_id):
    thread = _get_thread(thread_id)

    if request.method == 'GET':
        after = request.args.get('after', 0, type=int)
        query = thread.messages
        if after:
            query = query.filter(SupportMessage.id > after)
        items = query.order_by(SupportMessage.created_at.asc()).all()
        return jsonify({'messages': [_serialize_message(message) for message in items]})

    body = request.form.get('body', '').strip()
    files = request.files.getlist('files')
    valid_files = [file for file in files if file and file.filename]

    if not body and not valid_files:
        return jsonify({'error': 'Escribe un mensaje o adjunta un archivo.'}), 400

    for file in valid_files:
        if not allowed_file(file.filename):
            return jsonify({'error': f'Tipo de archivo no permitido: {file.filename}'}), 400

    try:
        message = SupportMessage(
            thread_id=thread.id,
            user_id=current_user.id,
            body=body or 'Archivo adjunto',
            is_staff=current_user.is_superuser,
        )
        if current_user.is_superuser:
            thread.assigned_superuser_id = current_user.id
            if thread.status == 'abierto':
                thread.status = 'en_revision'
        db.session.add(message)
        db.session.flush()

        for file in valid_files:
            nombre, ruta, mime, tamano = save_upload(file, current_app.config['UPLOAD_FOLDER'])
            db.session.add(SupportAttachment(
                message_id=message.id,
                user_id=current_user.id,
                nombre_archivo=nombre,
                ruta_archivo=ruta,
                tipo_mime=mime,
                tamano=tamano,
            ))

        db.session.commit()
        return jsonify({'message': _serialize_message(message)})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Error guardando mensaje de soporte')
        return jsonify({'error': str(exc)}), 500


@support_bp.route('/<int:thread_id>/attachment/<int:att_id>')
@login_required
def download_attachment(thread_id, att_id):
    thread = _get_thread(thread_id)
    attachment = SupportAttachment.query.get_or_404(att_id)
    if attachment.message.thread_id != thread.id:
        abort(404)
    if not os.path.exists(attachment.ruta_archivo):
        flash('Archivo no encontrado.', 'danger')
        return redirect(url_for('support.detail', thread_id=thread.id))

    return send_file(
        attachment.ruta_archivo,
        download_name=attachment.nombre_archivo,
        as_attachment=True,
    )


@support_bp.route('/<int:thread_id>/status', methods=['POST'])
@login_required
@superuser_required
def update_status(thread_id):
    thread = _get_thread(thread_id)
    status = request.form.get('status', '')
    if status not in dict(SupportThread.STATUS):
        flash('Estado de soporte inválido.', 'danger')
        return redirect(url_for('support.detail', thread_id=thread.id))
    thread.status = status
    db.session.commit()
    flash('Estado del chat actualizado.', 'success')
    return redirect(url_for('support.detail', thread_id=thread.id))
