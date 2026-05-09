# -*- coding: utf-8 -*-
"""Servicios para marketing: CSV, RRSS, IA y CronJobs."""
import csv
import io
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models.company import Company
from ..models.marketing import MarketingAudienceContact, MarketingCampaign, MarketingCronJob
from ..utils.sanitizer import strip_html


FACEBOOK_CSV_HEADERS = [
    'User Id',
    'User Name',
    'Profile URL',
    'Profile Picture',
    'Biography',
    'Is Verified',
    'Friendship Status',
    'Join Status Text',
    'Scraped At',
]


def _parse_bool(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'si', 'sí', 'verified'}


def _parse_datetime(value):
    raw = (value or '').strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None


def import_facebook_contacts(file_storage, empresa_id, campaign_id=None):
    """Importa contactos desde CSV con formato de scraping Facebook."""
    if not file_storage or not file_storage.filename:
        raise ValueError('Selecciona un archivo CSV válido.')
    if not file_storage.filename.lower().endswith('.csv'):
        raise ValueError('El archivo debe ser CSV.')

    stream = io.TextIOWrapper(file_storage.stream, encoding='utf-8-sig', newline='')
    reader = csv.DictReader(stream)
    headers = reader.fieldnames or []
    missing = [header for header in FACEBOOK_CSV_HEADERS if header not in headers]
    if missing:
        raise ValueError('CSV inválido. Faltan columnas: ' + ', '.join(missing))

    created = 0
    updated = 0
    skipped = 0

    for row in reader:
        external_id = (row.get('User Id') or '').strip()
        user_name = (row.get('User Name') or '').strip()
        if not external_id or not user_name:
            skipped += 1
            continue

        contact = MarketingAudienceContact.query.filter_by(
            empresa_id=empresa_id,
            source='facebook_csv',
            external_user_id=external_id,
        ).first()
        if contact:
            updated += 1
        else:
            contact = MarketingAudienceContact(
                empresa_id=empresa_id,
                source='facebook_csv',
                external_user_id=external_id,
            )
            db.session.add(contact)
            created += 1

        contact.campaign_id = campaign_id or contact.campaign_id
        contact.user_name = user_name
        contact.profile_url = (row.get('Profile URL') or '').strip() or None
        contact.profile_picture = (row.get('Profile Picture') or '').strip() or None
        contact.biography = (row.get('Biography') or '').strip() or None
        contact.is_verified = _parse_bool(row.get('Is Verified'))
        contact.friendship_status = (row.get('Friendship Status') or '').strip() or None
        contact.join_status_text = (row.get('Join Status Text') or '').strip() or None
        contact.scraped_at = _parse_datetime(row.get('Scraped At'))
        contact.raw_payload = {header: row.get(header) for header in FACEBOOK_CSV_HEADERS}

    db.session.commit()
    return {'created': created, 'updated': updated, 'skipped': skipped}


def build_social_share_links(campaign):
    """Construye links listos para compartir en RRSS."""
    text = campaign.copy_rrss or strip_html(campaign.mensaje) or strip_html(campaign.objetivo) or campaign.nombre
    text = text.replace('\n', ' ').strip()
    if campaign.hashtags:
        text = f'{text} {campaign.hashtags.strip()}'.strip()
    url = (campaign.url_destino or '').strip()
    encoded_text = urllib.parse.quote(text)
    encoded_url = urllib.parse.quote(url)

    links = {
        'facebook': f'https://www.facebook.com/sharer/sharer.php?u={encoded_url}&quote={encoded_text}' if url else None,
        'x': f'https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}' if url else f'https://twitter.com/intent/tweet?text={encoded_text}',
        'linkedin': f'https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}' if url else None,
        'whatsapp': f'https://wa.me/?text={urllib.parse.quote((text + " " + url).strip())}',
    }
    return {key: value for key, value in links.items() if value}


def _fallback_campaign_assets(campaign, contacts_count):
    url = campaign.url_destino or 'URL de landing pendiente'
    hashtags = campaign.hashtags or '#Bitacora #MarketingDigital'
    audience = campaign.audiencia or f'Audiencia importada y segmentos activos ({contacts_count} contacto(s)).'
    offer = campaign.mensaje or 'Oferta clara, medible y con llamada a la acción.'

    return {
        'summary': f'Kit de campaña para {campaign.nombre}: foco en {campaign.ad_objective_label}.',
        'hero_copy': f'{offer} Conoce más en {url}. {hashtags}',
        'social_posts': [
            {
                'platform': 'Facebook / Meta',
                'copy': f'{offer}\n\nDirigido a: {audience}\n{hashtags}',
                'cta': 'Enviar mensaje / Más información',
            },
            {
                'platform': 'X / Twitter',
                'copy': f'{campaign.nombre}: {offer} {url} {hashtags}',
                'cta': 'Compartir',
            },
            {
                'platform': 'LinkedIn',
                'copy': f'{campaign.nombre}\n\nProblema que resuelve: {campaign.objetivo or "crecimiento comercial"}.\nCTA: agenda una conversación o visita {url}.',
                'cta': 'Generar lead',
            },
        ],
        'ads': [
            {
                'platform': 'Meta Ads',
                'objective': campaign.ad_objective_label,
                'targeting': audience,
                'creative_angle': 'Beneficio directo + prueba visual + CTA de WhatsApp o landing.',
            },
            {
                'platform': 'Google Ads',
                'objective': 'Búsqueda/Performance Max',
                'keywords': ['solución comercial', campaign.nombre.lower(), 'servicio especializado'],
                'landing_url': url,
            },
            {
                'platform': 'LinkedIn Ads',
                'objective': 'Lead generation',
                'targeting': 'Cargo, industria, zona y tamaño de empresa según audiencia definida.',
                'lead_magnet': 'Demo, diagnóstico o cotización rápida.',
            },
        ],
        'viral_actions': [
            'Publicar pieza principal con CTA visible y enlace trackeable.',
            'Crear variante corta para WhatsApp y grupos con consentimiento.',
            'Reciclar el contenido en Facebook, LinkedIn y X con ángulos distintos.',
            'Usar contactos importados sólo como audiencia/segmento, evitando spam sin consentimiento.',
        ],
        'cron_suggestions': [
            'Publicación inicial al activar campaña.',
            'Recordatorio 48 horas después con prueba social.',
            'Cierre de oferta 24 horas antes de finalizar.',
        ],
    }


def generate_campaign_assets(company, campaign):
    """Genera assets de campaña con IA configurada o fallback local."""
    contacts_count = MarketingAudienceContact.query.filter_by(
        empresa_id=campaign.empresa_id,
        campaign_id=campaign.id,
    ).count()
    fallback = _fallback_campaign_assets(campaign, contacts_count)

    if not company or not company.ai_provider or not company.ai_api_key:
        return fallback

    prompt = f"""
Genera un kit de campaña de marketing en español para:
Nombre: {campaign.nombre}
Objetivo: {campaign.objetivo}
Audiencia: {campaign.audiencia}
Oferta/Mensaje: {campaign.mensaje}
URL destino: {campaign.url_destino}
Hashtags: {campaign.hashtags}
Objetivo Ads: {campaign.ad_objective_label}
Contactos importados: {contacts_count}

Responde solo JSON con: summary, hero_copy, social_posts, ads, viral_actions, cron_suggestions.
"""
    try:
        from . import ai_service

        providers = {
            'openai': ai_service._call_openai,
            'gemini': ai_service._call_gemini,
            'anthropic': ai_service._call_anthropic,
        }
        call_fn = providers.get(company.ai_provider)
        if not call_fn:
            return fallback
        raw = call_fn(company.ai_api_key, company.ai_model, prompt)
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0]
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else fallback
    except Exception as exc:
        current_app.logger.warning(f'Error generando campaña con IA: {exc}')
        return fallback


def _job_share_url(job):
    content = (job.contenido or '').strip()
    url = (job.url_destino or '').strip()
    payload = urllib.parse.quote((content + ' ' + url).strip())
    if job.plataforma == 'facebook' and url:
        return f'https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(url)}'
    if job.plataforma == 'linkedin' and url:
        return f'https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(url)}'
    if job.plataforma == 'x':
        return f'https://twitter.com/intent/tweet?text={payload}'
    if job.plataforma == 'whatsapp':
        return f'https://wa.me/?text={payload}'
    return url or None


def run_due_marketing_jobs(limit=25):
    """Procesa CronJobs vencidos. No publica sin credenciales externas; deja payload listo."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    jobs = MarketingCronJob.query.filter(
        MarketingCronJob.status == 'activo',
        MarketingCronJob.next_run_at <= now,
    ).order_by(MarketingCronJob.next_run_at.asc()).limit(limit).all()

    processed = []
    for job in jobs:
        try:
            share_url = _job_share_url(job)
            job.last_run_at = now
            job.last_result = (
                f'Contenido preparado para {job.plataforma}. '
                f'URL de publicación/asistencia: {share_url or "sin URL"}'
            )
            if job.interval_minutes and job.interval_minutes > 0:
                job.next_run_at = now + timedelta(minutes=job.interval_minutes)
            else:
                job.status = 'completado'
            processed.append({'id': job.id, 'status': job.status, 'share_url': share_url})
        except Exception as exc:
            job.status = 'error'
            job.last_result = str(exc)
            processed.append({'id': job.id, 'status': 'error', 'error': str(exc)})

    db.session.commit()
    return processed


def get_company_for_campaign(campaign):
    return db.session.get(Company, campaign.empresa_id)
