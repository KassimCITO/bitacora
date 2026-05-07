# -*- coding: utf-8 -*-
"""
Rutas de gestión de empresas (superuser y administradores).
CRUD completo con tabs: General, Email, IA.
"""
import os

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, session
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.company import Company
from ..services.app_key_service import (
    generate_app_key,
    is_valid_app_key_format,
    normalize_app_key,
    validate_app_key,
)
from ..services.fiscal_pdf_service import extract_constancia_fiscal_data
from ..services.image_service import generate_logo_variants, image_url, optimize_image_upload
from ..utils.decorators import superuser_required, role_required
from ..utils.helpers import allowed_file, save_upload

companies_bp = Blueprint('companies', __name__, url_prefix='/companies')


def _expected_app_key(company):
    return generate_app_key(company.razon_social, current_app.config.get('SECRET_KEY'))


def _set_expected_app_key(company):
    app_key = _expected_app_key(company)
    if app_key:
        company.app_key = app_key
    return app_key


def _apply_constancia_data(company, path):
    """Actualiza la empresa con datos detectados en la constancia fiscal."""
    fiscal_data = extract_constancia_fiscal_data(path)
    if fiscal_data.get('__error__'):
        return [], fiscal_data['__error__'], fiscal_data

    field_labels = {
        'rfc': 'RFC',
        'razon_social': 'razón social',
        'direccion': 'dirección',
        'regimen_fiscal': 'régimen fiscal',
    }

    applied = []
    for field, label in field_labels.items():
        value = fiscal_data.get(field)
        if value:
            setattr(company, field, value.strip())
            applied.append(label)

    if fiscal_data.get('razon_social') and not company.nombre:
        company.nombre = fiscal_data['razon_social'].strip()

    return applied, None, fiscal_data


def _fiscal_snapshot(company):
    return {
        'nombre': company.nombre,
        'rfc': company.rfc,
        'razon_social': company.razon_social,
        'direccion': company.direccion,
        'regimen_fiscal': company.regimen_fiscal,
        'constancia_fiscal_path': company.constancia_fiscal_path,
        'app_key': company.app_key,
    }


def _restore_fiscal_snapshot(company, snapshot):
    for field, value in snapshot.items():
        setattr(company, field, value)


def _validate_csf_file(file):
    if not file or not file.filename:
        return 'Selecciona la CSF en PDF antes de guardar.'
    if not allowed_file(file.filename) or file.filename.rsplit('.', 1)[1].lower() != 'pdf':
        return 'La CSF debe ser un archivo PDF válido.'
    return None


def _process_constancia_upload(company, file, should_generate_app_key):
    error = _validate_csf_file(file)
    if error:
        return False, [], error

    snapshot = _fiscal_snapshot(company)
    _, ruta, _, _ = save_upload(file, current_app.config['UPLOAD_FOLDER'])
    applied, error, fiscal_data = _apply_constancia_data(company, ruta)

    missing_required = []
    if not fiscal_data.get('rfc'):
        missing_required.append('RFC')
    if not fiscal_data.get('razon_social'):
        missing_required.append('razón social fiscal')

    if error or missing_required:
        try:
            os.remove(ruta)
        except OSError:
            pass
        _restore_fiscal_snapshot(company, snapshot)
        if missing_required:
            error = 'No se detectó ' + ' ni '.join(missing_required) + ' en la CSF.'
        return False, [], error

    company.constancia_fiscal_path = ruta
    if should_generate_app_key:
        _set_expected_app_key(company)

    return True, applied, None


def _process_company_logo(company, file):
    """Optimiza logo a WebP y genera favicon ICO."""
    _, ruta, _, _ = optimize_image_upload(
        file,
        current_app.config['UPLOAD_FOLDER'],
        prefix='company-logo',
        max_size=(1200, 1200),
        quality=88,
    )
    generate_logo_variants(ruta)
    company.logo_path = ruta
    return ruta


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
            validation_failed = False
            company = Company(
                # General
                nombre=request.form.get('nombre', '').strip(),
                representante_legal=request.form.get('representante_legal', '').strip(),
                telefono=request.form.get('telefono', '').strip(),
                email_contacto=request.form.get('email_contacto', '').strip(),
                sitio_web=request.form.get('sitio_web', '').strip(),
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
                _process_company_logo(company, request.files['logo'])

            csf_uploaded = False
            # Constancia fiscal PDF upload
            if 'constancia_fiscal' in request.files and request.files['constancia_fiscal'].filename:
                csf_uploaded, applied, error = _process_constancia_upload(
                    company,
                    request.files['constancia_fiscal'],
                    should_generate_app_key=True,
                )
                if error:
                    validation_failed = True
                    flash('No se pudo procesar la CSF: ' + error, 'danger')
                elif applied:
                    flash('Datos fiscales actualizados desde la CSF: ' + ', '.join(applied) + '. APP-Key generada.', 'info')
                else:
                    flash('CSF cargada y APP-Key generada.', 'info')

            if validation_failed:
                db.session.rollback()
                return render_template(
                    'companies/form.html',
                    company=company,
                    ai_providers=Company.AI_PROVIDERS,
                    image_url=image_url,
                ), 400

            db.session.add(company)
            db.session.commit()
            flash(f'Empresa "{company.nombre}" creada exitosamente.', 'success')
            if csf_uploaded:
                return redirect(url_for('companies.edit', company_id=company.id))
            return redirect(url_for('companies.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear empresa: {str(e)}', 'danger')

    return render_template(
        'companies/form.html',
        company=None,
        ai_providers=Company.AI_PROVIDERS,
        image_url=image_url,
    )


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
            validation_failed = False
            # General
            company.nombre = request.form.get('nombre', company.nombre).strip()
            company.representante_legal = request.form.get('representante_legal', '').strip()
            company.telefono = request.form.get('telefono', '').strip()
            company.email_contacto = request.form.get('email_contacto', '').strip()
            company.sitio_web = request.form.get('sitio_web', '').strip()

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
                _process_company_logo(company, logo_file)

            csf_uploaded = False
            # Constancia fiscal PDF upload
            if 'constancia_fiscal' in request.files and request.files['constancia_fiscal'].filename:
                csf_uploaded, applied, error = _process_constancia_upload(
                    company,
                    request.files['constancia_fiscal'],
                    should_generate_app_key=current_user.is_superuser,
                )
                app_key_msg = ' APP-Key generada desde la razón social fiscal.' if current_user.is_superuser else ''
                if error:
                    validation_failed = True
                    flash('No se pudo procesar la CSF: ' + error, 'danger')
                elif applied:
                    flash('Datos fiscales actualizados desde la CSF: ' + ', '.join(applied) + '.' + app_key_msg, 'info')
                else:
                    flash('CSF cargada.' + app_key_msg, 'info')

            if not current_user.is_superuser:
                submitted_app_key = request.form.get('app_key', '').strip()
                if submitted_app_key:
                    normalized_app_key = normalize_app_key(submitted_app_key)
                    if validate_app_key(company.razon_social, normalized_app_key, current_app.config.get('SECRET_KEY')):
                        company.app_key = normalized_app_key
                        flash('APP-Key validada correctamente.', 'success')
                    elif not company.razon_social:
                        validation_failed = True
                        flash('Primero sube una CSF válida para registrar la razón social fiscal.', 'danger')
                    elif not is_valid_app_key_format(submitted_app_key):
                        validation_failed = True
                        flash('La APP-Key debe tener el formato KMR-XXXXX-XXXXX-XXXXX-XXXXX.', 'danger')
                    else:
                        validation_failed = True
                        flash('APP-Key incorrecta para la razón social fiscal registrada.', 'danger')
                elif company.razon_social and not validate_app_key(
                    company.razon_social,
                    company.app_key,
                    current_app.config.get('SECRET_KEY'),
                ):
                    flash('Captura una APP-Key válida para la razón social fiscal registrada.', 'danger')

            if validation_failed:
                db.session.rollback()
                return render_template(
                    'companies/form.html',
                    company=company,
                    ai_providers=Company.AI_PROVIDERS,
                    image_url=image_url,
                ), 400

            db.session.commit()
            flash('Empresa actualizada correctamente.', 'success')
            if csf_uploaded:
                return redirect(url_for('companies.edit', company_id=company_id))
            return redirect(url_for('companies.list_companies') if current_user.is_superuser
                            else url_for('companies.edit', company_id=company_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    return render_template(
        'companies/form.html',
        company=company,
        ai_providers=Company.AI_PROVIDERS,
        image_url=image_url,
    )


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
