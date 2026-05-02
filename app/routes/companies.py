# -*- coding: utf-8 -*-
"""
Rutas de gestión de empresas (superuser y administradores).
CRUD completo con tabs: General, Fiscal, Email, IA.
"""
import os
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, session
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.company import Company
from ..utils.decorators import superuser_required, role_required
from ..utils.helpers import save_upload

companies_bp = Blueprint('companies', __name__, url_prefix='/companies')


@companies_bp.route('/')
@login_required
@superuser_required
def list_companies():
    """Lista de todas las empresas."""
    companies = Company.query.order_by(Company.nombre).all()
    return render_template('companies/list.html', companies=companies)


@companies_bp.route('/create', methods=['GET', 'POST'])
@login_required
@superuser_required
def create():
    """Crear una nueva empresa."""
    if request.method == 'POST':
        try:
            company = Company(
                # General
                nombre=request.form.get('nombre', '').strip(),
                representante_legal=request.form.get('representante_legal', '').strip(),
                direccion=request.form.get('direccion', '').strip(),
                telefono=request.form.get('telefono', '').strip(),
                email_contacto=request.form.get('email_contacto', '').strip(),
                sitio_web=request.form.get('sitio_web', '').strip(),
                # Fiscal
                rfc=request.form.get('rfc', '').strip(),
                razon_social=request.form.get('razon_social', '').strip(),
                regimen_fiscal=request.form.get('regimen_fiscal', '').strip(),
                # Email
                mail_server=request.form.get('mail_server', '').strip(),
                mail_port=int(request.form.get('mail_port', 587)),
                mail_use_tls=request.form.get('mail_use_tls') == 'on',
                mail_use_ssl=request.form.get('mail_use_ssl') == 'on',
                mail_username=request.form.get('mail_username', '').strip(),
                mail_default_sender=request.form.get('mail_default_sender', '').strip(),
                # IA
                ai_provider=request.form.get('ai_provider', '').strip() or None,
                ai_model=request.form.get('ai_model', '').strip(),
            )

            # Campos cifrados
            mail_pass = request.form.get('mail_password', '').strip()
            if mail_pass:
                company.mail_password = mail_pass

            ai_key = request.form.get('ai_api_key', '').strip()
            if ai_key:
                company.ai_api_key = ai_key

            # Logo upload
            if 'logo' in request.files and request.files['logo'].filename:
                logo_file = request.files['logo']
                nombre, ruta, _, _ = save_upload(logo_file, current_app.config['UPLOAD_FOLDER'])
                company.logo_path = ruta

            # Constancia fiscal PDF upload
            if 'constancia_fiscal' in request.files and request.files['constancia_fiscal'].filename:
                cf_file = request.files['constancia_fiscal']
                nombre, ruta, _, _ = save_upload(cf_file, current_app.config['UPLOAD_FOLDER'])
                company.constancia_fiscal_path = ruta

            db.session.add(company)
            db.session.commit()
            flash(f'Empresa "{company.nombre}" creada exitosamente.', 'success')
            return redirect(url_for('companies.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear empresa: {str(e)}', 'danger')

    return render_template('companies/form.html', company=None, ai_providers=Company.AI_PROVIDERS)


@companies_bp.route('/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('superuser', 'administrador')
def edit(company_id):
    """Editar una empresa existente."""
    company = Company.query.get_or_404(company_id)

    # Admin solo puede editar su propia empresa
    if not current_user.is_superuser and current_user.empresa_id != company_id:
        from flask import abort
        abort(403)

    if request.method == 'POST':
        try:
            # General
            company.nombre = request.form.get('nombre', company.nombre).strip()
            company.representante_legal = request.form.get('representante_legal', '').strip()
            company.direccion = request.form.get('direccion', '').strip()
            company.telefono = request.form.get('telefono', '').strip()
            company.email_contacto = request.form.get('email_contacto', '').strip()
            company.sitio_web = request.form.get('sitio_web', '').strip()

            # Fiscal
            company.rfc = request.form.get('rfc', '').strip()
            company.razon_social = request.form.get('razon_social', '').strip()
            company.regimen_fiscal = request.form.get('regimen_fiscal', '').strip()

            # Email
            company.mail_server = request.form.get('mail_server', '').strip()
            company.mail_port = int(request.form.get('mail_port', 587))
            company.mail_use_tls = request.form.get('mail_use_tls') == 'on'
            company.mail_use_ssl = request.form.get('mail_use_ssl') == 'on'
            company.mail_username = request.form.get('mail_username', '').strip()
            company.mail_default_sender = request.form.get('mail_default_sender', '').strip()

            # Contraseña SMTP solo si se proporciona
            mail_pass = request.form.get('mail_password', '').strip()
            if mail_pass:
                company.mail_password = mail_pass

            # IA
            company.ai_provider = request.form.get('ai_provider', '').strip() or None
            company.ai_model = request.form.get('ai_model', '').strip()

            ai_key = request.form.get('ai_api_key', '').strip()
            if ai_key:
                company.ai_api_key = ai_key

            # Logo upload
            if 'logo' in request.files and request.files['logo'].filename:
                logo_file = request.files['logo']
                nombre, ruta, _, _ = save_upload(logo_file, current_app.config['UPLOAD_FOLDER'])
                company.logo_path = ruta

            # Constancia fiscal PDF upload
            if 'constancia_fiscal' in request.files and request.files['constancia_fiscal'].filename:
                cf_file = request.files['constancia_fiscal']
                nombre, ruta, _, _ = save_upload(cf_file, current_app.config['UPLOAD_FOLDER'])
                company.constancia_fiscal_path = ruta

            db.session.commit()
            flash('Empresa actualizada correctamente.', 'success')
            return redirect(url_for('companies.list_companies') if current_user.is_superuser
                            else url_for('companies.edit', company_id=company_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    return render_template('companies/form.html', company=company, ai_providers=Company.AI_PROVIDERS)


@companies_bp.route('/<int:company_id>/toggle', methods=['POST'])
@login_required
@superuser_required
def toggle_active(company_id):
    """Activar o desactivar una empresa."""
    company = Company.query.get_or_404(company_id)
    company.activa = not company.activa
    db.session.commit()
    estado = 'activada' if company.activa else 'desactivada'
    flash(f'Empresa "{company.nombre}" {estado}.', 'info')
    return redirect(url_for('companies.list_companies'))


@companies_bp.route('/<int:company_id>/switch', methods=['POST'])
@login_required
@superuser_required
def switch_company(company_id):
    """Cambiar la empresa activa en la sesión (solo superuser)."""
    company = Company.query.get_or_404(company_id)
    if not company.activa:
        flash('No puedes cambiar a una empresa desactivada.', 'warning')
        return redirect(url_for('companies.list_companies'))

    session['empresa_id'] = company.id
    flash(f'Ahora estás trabajando en: {company.nombre}', 'success')
    return redirect(url_for('dashboard.index'))
