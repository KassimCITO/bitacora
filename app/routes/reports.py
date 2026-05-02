# -*- coding: utf-8 -*-
"""
Rutas de reportes PDF y compartición (email, WhatsApp).
Multi-tenant: usa config SMTP de la empresa.
"""
import os
import urllib.parse
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, make_response, session
)
from flask_login import login_required, current_user
from flask_mail import Message
from ..extensions import db, mail
from ..models.task import Task
from ..models.user import User
from ..models.company import Company
from ..services.pdf_service import generate_task_report, generate_range_report
from ..utils.decorators import role_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


def _get_company():
    """Obtiene la empresa activa."""
    empresa_id = _get_empresa_id()
    if empresa_id:
        return Company.query.get(empresa_id)
    return None


def _send_email_with_company_config(company, recipient, subject, body, pdf_bytes=None, pdf_filename='reporte.pdf'):
    """Envía email usando la configuración SMTP de la empresa."""
    if company and company.mail_server:
        # Configurar Flask-Mail dinámicamente
        current_app.config.update(company.get_mail_config())
        mail.init_app(current_app)

    try:
        sender = company.mail_default_sender if company and company.mail_default_sender else current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@bitacora.app')
        msg = Message(subject=subject, recipients=[recipient], body=body, sender=sender)
        if pdf_bytes:
            msg.attach(filename=pdf_filename, content_type='application/pdf', data=pdf_bytes)
        mail.send(msg)
        return True, 'Correo enviado exitosamente.'
    except Exception as e:
        current_app.logger.error(f'Error enviando correo: {str(e)}')
        return False, f'Error al enviar correo: {str(e)}'


@reports_bp.route('/')
@login_required
@role_required('administrador', 'manager', 'visor')
def index():
    """Vista principal de reportes."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    tasks = Task.query.filter_by(empresa_id=empresa_id).order_by(Task.nombre).all()
    return render_template('reports/generate.html', tasks=tasks)


@reports_bp.route('/task/<int:task_id>')
@login_required
@role_required('administrador', 'manager', 'visor')
def task_report(task_id):
    """Generar PDF de una tarea individual."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()
    if task.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    company = _get_company()
    company_name = company.nombre if company else current_app.config.get('COMPANY_NAME', 'Bitácora')
    logo_path = company.logo_path if company and company.logo_path else current_app.config.get('LOGO_PATH')

    pdf_bytes = generate_task_report(task, logo_path=logo_path, company_name=company_name)

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=tarea_{task.id}.pdf'
    return response


@reports_bp.route('/range', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'manager', 'visor')
def range_report():
    """Generar PDF por rango de fechas."""
    empresa_id = _get_empresa_id()

    if request.method == 'POST':
        try:
            start = datetime.fromisoformat(request.form['fecha_inicio'])
            end = datetime.fromisoformat(request.form['fecha_fin'])

            tasks = Task.query.filter(
                Task.empresa_id == empresa_id,
                Task.fecha_creacion >= start,
                Task.fecha_creacion <= end,
            ).order_by(Task.fecha_creacion.desc()).all()

            if not tasks:
                flash('No se encontraron tareas en el rango especificado.', 'warning')
                return redirect(url_for('reports.index'))

            company = _get_company()
            company_name = company.nombre if company else current_app.config.get('COMPANY_NAME', 'Bitácora')
            logo_path = company.logo_path if company and company.logo_path else current_app.config.get('LOGO_PATH')

            pdf_bytes = generate_range_report(
                tasks, start, end,
                logo_path=logo_path,
                company_name=company_name,
            )

            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            filename = f'reporte_{start.strftime("%Y%m%d")}_{end.strftime("%Y%m%d")}.pdf'
            response.headers['Content-Disposition'] = f'inline; filename={filename}'
            return response
        except Exception as e:
            flash(f'Error al generar reporte: {str(e)}', 'danger')
            return redirect(url_for('reports.index'))

    return redirect(url_for('reports.index'))


@reports_bp.route('/share/email/<int:task_id>', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def share_email(task_id):
    """Enviar reporte PDF por email."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()
    if task.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    recipient = request.form.get('email', '').strip()
    if not recipient:
        flash('Ingresa un email válido.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task_id))

    company = _get_company()
    company_name = company.nombre if company else current_app.config.get('COMPANY_NAME', 'Bitácora')
    logo_path = company.logo_path if company and company.logo_path else current_app.config.get('LOGO_PATH')

    pdf_bytes = generate_task_report(task, logo_path=logo_path, company_name=company_name)

    subject = f'Reporte de Tarea: {task.nombre}'
    body = (
        f'Adjunto encontrarás el reporte de la tarea "{task.nombre}".\n\n'
        f'Estado: {task.estado_label}\n'
        f'Avance: {task.ultimo_avance}%\n\n'
        f'— {company_name}'
    )

    success, message = _send_email_with_company_config(
        company, recipient, subject, body,
        pdf_bytes=pdf_bytes,
        pdf_filename=f'tarea_{task.id}.pdf',
    )

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tasks.detail', task_id=task_id))


@reports_bp.route('/share/whatsapp/<int:task_id>')
@login_required
@role_required('administrador', 'manager', 'usuario')
def share_whatsapp(task_id):
    """Generar enlace de WhatsApp para compartir tarea."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()
    if task.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    company = _get_company()
    company_name = company.nombre if company else 'Bitácora'

    message = (
        f'📋 *Tarea:* {task.nombre}\n'
        f'📊 *Estado:* {task.estado_label}\n'
        f'🔥 *Prioridad:* {task.prioridad_label}\n'
        f'👤 *Asignado a:* {task.usuario_asignado.nombre_completo}\n'
        f'📈 *Avance:* {task.ultimo_avance}%\n\n'
        f'📄 Descarga el reporte completo en {company_name}.'
    )

    whatsapp_url = f'https://wa.me/?text={urllib.parse.quote(message)}'
    return redirect(whatsapp_url)
