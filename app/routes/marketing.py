# -*- coding: utf-8 -*-
"""Rutas del módulo Marketing."""
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.company import Company
from ..models.marketing import MarketingAudienceContact, MarketingCampaign, MarketingCronJob
from ..models.user import User
from ..services.marketing_service import (
    build_social_share_links,
    generate_campaign_assets,
    import_facebook_contacts,
    run_due_marketing_jobs,
)
from ..utils.decorators import role_required, superuser_required
from ..utils.sanitizer import sanitize_html, strip_html

marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')


def _get_empresa_id():
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


def _get_company():
    empresa_id = _get_empresa_id()
    return db.session.get(Company, empresa_id) if empresa_id else None


def _parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


def _get_campaign(campaign_id):
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    empresa_id = _get_empresa_id()
    if campaign.empresa_id != empresa_id:
        abort(403)
    return campaign


def _campaign_from_form(campaign=None):
    campaign = campaign or MarketingCampaign()
    campaign.nombre = request.form.get('nombre', '').strip()
    campaign.objetivo = sanitize_html(request.form.get('objetivo', ''))
    campaign.audiencia = sanitize_html(request.form.get('audiencia', ''))
    campaign.mensaje = sanitize_html(request.form.get('mensaje', ''))
    campaign.notas = sanitize_html(request.form.get('notas', ''))
    campaign.url_destino = request.form.get('url_destino', '').strip() or None
    campaign.copy_rrss = strip_html(request.form.get('copy_rrss', '')).strip() or None
    campaign.hashtags = strip_html(request.form.get('hashtags', '')).strip() or None
    campaign.plataformas = ','.join(request.form.getlist('plataformas')) or None
    campaign.ad_objective = request.form.get('ad_objective', '').strip() or None
    campaign.canal = request.form.get('canal', 'digital')
    campaign.estado = request.form.get('estado', 'planeacion')
    campaign.prioridad = request.form.get('prioridad', 'media')
    campaign.presupuesto = request.form.get('presupuesto') or None
    campaign.fecha_inicio = _parse_datetime(request.form.get('fecha_inicio'))
    campaign.fecha_fin = _parse_datetime(request.form.get('fecha_fin'))
    campaign.responsable_id = int(request.form.get('responsable_id'))
    return campaign


def _users_for_empresa():
    return User.query.filter_by(
        empresa_id=_get_empresa_id(),
        activo=True,
    ).order_by(User.nombre_completo).all()


def _campaign_options():
    return MarketingCampaign.query.filter_by(
        empresa_id=_get_empresa_id(),
    ).order_by(MarketingCampaign.nombre).all()


@marketing_bp.route('/')
@login_required
@role_required('superuser', 'administrador', 'manager', 'visor')
def list_campaigns():
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', '')
    canal = request.args.get('canal', '')
    search = request.args.get('search', '').strip()

    query = MarketingCampaign.query.filter_by(empresa_id=empresa_id)
    if estado:
        query = query.filter_by(estado=estado)
    if canal:
        query = query.filter_by(canal=canal)
    if search:
        query = query.filter(MarketingCampaign.nombre.ilike(f'%{search}%'))

    pagination = query.order_by(MarketingCampaign.ultima_actualizacion.desc()).paginate(
        page=page,
        per_page=current_app.config.get('TASKS_PER_PAGE', 15),
        error_out=False,
    )

    contacts_count = MarketingAudienceContact.query.filter_by(empresa_id=empresa_id).count()
    active_jobs = MarketingCronJob.query.filter_by(empresa_id=empresa_id, status='activo').count()

    return render_template(
        'marketing/list.html',
        campaigns=pagination.items,
        pagination=pagination,
        estados=MarketingCampaign.ESTADOS,
        canales=MarketingCampaign.CANALES,
        filter_estado=estado,
        filter_canal=canal,
        filter_search=search,
        contacts_count=contacts_count,
        active_jobs=active_jobs,
        campaign_options=_campaign_options(),
    )


@marketing_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'manager')
def create():
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    if request.method == 'POST':
        try:
            campaign = _campaign_from_form()
            campaign.empresa_id = empresa_id
            campaign.creado_por_id = current_user.id
            db.session.add(campaign)
            db.session.commit()
            flash('Campaña de marketing creada correctamente.', 'success')
            return redirect(url_for('marketing.detail', campaign_id=campaign.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear campaña: {str(e)}', 'danger')

    return render_template(
        'marketing/form.html',
        campaign=None,
        users=_users_for_empresa(),
        estados=MarketingCampaign.ESTADOS,
        canales=MarketingCampaign.CANALES,
        prioridades=MarketingCampaign.PRIORIDADES,
        plataformas=MarketingCampaign.PLATAFORMAS,
        ad_objectives=MarketingCampaign.AD_OBJECTIVES,
    )


@marketing_bp.route('/import', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def import_contacts():
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    campaign_id = request.form.get('campaign_id', type=int)
    if campaign_id:
        _get_campaign(campaign_id)
    try:
        result = import_facebook_contacts(
            request.files.get('csv_file'),
            empresa_id=empresa_id,
            campaign_id=campaign_id,
        )
        flash(
            f'CSV importado: {result["created"]} nuevos, {result["updated"]} actualizados, {result["skipped"]} omitidos.',
            'success',
        )
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(request.referrer or url_for('marketing.list_campaigns'))


@marketing_bp.route('/contacts')
@login_required
@role_required('administrador', 'manager', 'visor')
def contacts():
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    page = request.args.get('page', 1, type=int)
    campaign_id = request.args.get('campaign_id', type=int)
    query = MarketingAudienceContact.query.filter_by(empresa_id=empresa_id)
    if campaign_id:
        query = query.filter_by(campaign_id=campaign_id)
    pagination = query.order_by(MarketingAudienceContact.updated_at.desc()).paginate(
        page=page,
        per_page=current_app.config.get('TASKS_PER_PAGE', 15),
        error_out=False,
    )
    return render_template(
        'marketing/contacts.html',
        contacts=pagination.items,
        pagination=pagination,
        campaign_options=_campaign_options(),
        filter_campaign_id=campaign_id,
    )


@marketing_bp.route('/cronjobs/run-due', methods=['POST'])
@login_required
@superuser_required
def run_due_jobs():
    processed = run_due_marketing_jobs()
    flash(f'CronJobs procesados: {len(processed)}.', 'success')
    return redirect(request.referrer or url_for('marketing.list_campaigns'))


@marketing_bp.route('/<int:campaign_id>')
@login_required
@role_required('superuser', 'administrador', 'manager', 'visor')
def detail(campaign_id):
    campaign = _get_campaign(campaign_id)
    contacts_count = MarketingAudienceContact.query.filter_by(
        empresa_id=campaign.empresa_id,
        campaign_id=campaign.id,
    ).count()
    cron_jobs = MarketingCronJob.query.filter_by(
        empresa_id=campaign.empresa_id,
        campaign_id=campaign.id,
    ).order_by(MarketingCronJob.next_run_at.asc()).all()
    return render_template(
        'marketing/detail.html',
        campaign=campaign,
        contacts_count=contacts_count,
        cron_jobs=cron_jobs,
        social_links=build_social_share_links(campaign),
        plataformas=MarketingCampaign.PLATAFORMAS,
    )


@marketing_bp.route('/<int:campaign_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'manager')
def edit(campaign_id):
    campaign = _get_campaign(campaign_id)

    if request.method == 'POST':
        try:
            _campaign_from_form(campaign)
            db.session.commit()
            flash('Campaña actualizada correctamente.', 'success')
            return redirect(url_for('marketing.detail', campaign_id=campaign.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar campaña: {str(e)}', 'danger')

    return render_template(
        'marketing/form.html',
        campaign=campaign,
        users=_users_for_empresa(),
        estados=MarketingCampaign.ESTADOS,
        canales=MarketingCampaign.CANALES,
        prioridades=MarketingCampaign.PRIORIDADES,
        plataformas=MarketingCampaign.PLATAFORMAS,
        ad_objectives=MarketingCampaign.AD_OBJECTIVES,
    )


@marketing_bp.route('/<int:campaign_id>/generate-ai', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def generate_ai(campaign_id):
    campaign = _get_campaign(campaign_id)
    try:
        assets = generate_campaign_assets(_get_company(), campaign)
        campaign.ai_assets = assets
        if assets.get('hero_copy') and not campaign.copy_rrss:
            campaign.copy_rrss = assets['hero_copy']
        db.session.commit()
        flash('Kit IA de campaña generado.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo generar el kit IA: {exc}', 'danger')
    return redirect(url_for('marketing.detail', campaign_id=campaign.id))


@marketing_bp.route('/<int:campaign_id>/cronjobs/create', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def create_cronjob(campaign_id):
    campaign = _get_campaign(campaign_id)
    try:
        job = MarketingCronJob(
            nombre=request.form.get('nombre', '').strip() or f'Publicación {campaign.nombre}',
            empresa_id=campaign.empresa_id,
            campaign_id=campaign.id,
            creado_por_id=current_user.id,
            plataforma=request.form.get('plataforma', 'web'),
            contenido=request.form.get('contenido', '').strip(),
            url_destino=request.form.get('url_destino', '').strip() or campaign.url_destino,
            interval_minutes=request.form.get('interval_minutes', type=int) or None,
            next_run_at=_parse_datetime(request.form.get('next_run_at')),
            payload={'campaign': campaign.nombre, 'ad_objective': campaign.ad_objective},
        )
        if not job.contenido:
            flash('El contenido del CronJob es obligatorio.', 'warning')
            return redirect(url_for('marketing.detail', campaign_id=campaign.id))
        if not job.next_run_at:
            flash('La fecha/hora de ejecución es obligatoria.', 'warning')
            return redirect(url_for('marketing.detail', campaign_id=campaign.id))
        db.session.add(job)
        db.session.commit()
        flash('CronJob de marketing creado.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo crear el CronJob: {exc}', 'danger')
    return redirect(url_for('marketing.detail', campaign_id=campaign.id))


@marketing_bp.route('/cronjobs/<int:job_id>/toggle', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def toggle_cronjob(job_id):
    empresa_id = _get_empresa_id()
    job = MarketingCronJob.query.get_or_404(job_id)
    if job.empresa_id != empresa_id:
        abort(403)
    if job.status == 'activo':
        job.status = 'pausado'
    elif job.status == 'pausado':
        job.status = 'activo'
    db.session.commit()
    flash('Estado del CronJob actualizado.', 'success')
    return redirect(url_for('marketing.detail', campaign_id=job.campaign_id))
