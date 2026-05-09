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
from ..utils.sanitizer import sanitize_html, strip_html


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

CAMPAIGN_AI_FIELDS = {
    'objetivo': 'Objetivo',
    'audiencia': 'Audiencia',
    'mensaje': 'Mensaje / Oferta',
}

CHANNEL_PLAYBOOKS = {
    'digital': {
        'expert': 'estrategia digital omnicanal',
        'angle': 'landing medible, remarketing y captura de leads',
        'docs': [
            ('Google Analytics', 'https://support.google.com/analytics/'),
            ('Meta Business', 'https://www.facebook.com/business/help'),
        ],
        'base_budget': 6000,
    },
    'redes': {
        'expert': 'redes sociales y community growth',
        'angle': 'contenido social, prueba visual y conversación directa',
        'docs': [
            ('Meta Business Help', 'https://www.facebook.com/business/help'),
            ('LinkedIn Marketing', 'https://business.linkedin.com/marketing-solutions'),
        ],
        'base_budget': 4500,
    },
    'email': {
        'expert': 'email marketing y automatizaciones',
        'angle': 'segmentación, secuencia de correos y medición de aperturas/clics',
        'docs': [
            ('Mailchimp Resources', 'https://mailchimp.com/resources/'),
            ('Google Analytics', 'https://support.google.com/analytics/'),
        ],
        'base_budget': 3000,
    },
    'marketplace': {
        'expert': 'marketplaces, fichas de producto y conversión ecommerce',
        'angle': 'optimización de ficha, precio/promoción, imágenes y reputación',
        'docs': [
            ('Amazon Seller University', 'https://sell.amazon.com/learn'),
            ('Mercado Libre Ayuda', 'https://www.mercadolibre.com.mx/ayuda/'),
        ],
        'base_budget': 7000,
    },
    'contenido': {
        'expert': 'marketing de contenidos y SEO',
        'angle': 'pieza útil, distribución y captación orgánica',
        'docs': [
            ('Google Search Central', 'https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=es'),
            ('HubSpot Resources', 'https://www.hubspot.com/resources'),
        ],
        'base_budget': 4000,
    },
    'branding': {
        'expert': 'branding, posicionamiento y percepción de marca',
        'angle': 'mensaje rector, consistencia visual y recordación',
        'docs': [
            ('Canva Learn Branding', 'https://www.canva.com/learn/brand-building/'),
            ('LinkedIn Marketing', 'https://business.linkedin.com/marketing-solutions'),
        ],
        'base_budget': 9000,
    },
    'ads': {
        'expert': 'performance marketing y pauta pagada',
        'angle': 'hipótesis de conversión, pruebas A/B, CPA y ROAS',
        'docs': [
            ('Google Ads Help', 'https://support.google.com/google-ads/'),
            ('Meta Business Help', 'https://www.facebook.com/business/help'),
        ],
        'base_budget': 10000,
    },
    'offline': {
        'expert': 'activaciones offline y generación local de demanda',
        'angle': 'punto físico, referidos, seguimiento por WhatsApp y medición manual',
        'docs': [
            ('Google Business Profile', 'https://support.google.com/business/'),
            ('WhatsApp Business', 'https://www.whatsapp.com/business/'),
        ],
        'base_budget': 12000,
    },
}

PRIORITY_MULTIPLIERS = {
    'baja': 0.65,
    'media': 1,
    'alta': 1.6,
}


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


def _option_label(options, value):
    return dict(options).get(value, value or '—')


def _channel_playbook(channel):
    return CHANNEL_PLAYBOOKS.get(channel) or CHANNEL_PLAYBOOKS['digital']


def _suggested_budget(channel, priority):
    playbook = _channel_playbook(channel)
    multiplier = PRIORITY_MULTIPLIERS.get(priority, 1)
    return int(round(playbook['base_budget'] * multiplier / 500) * 500)


def _link_list(channel):
    links = []
    for label, url in _channel_playbook(channel)['docs']:
        links.append(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')
    return ' y '.join(links)


def _fallback_campaign_field_suggestion(title, channel, priority, field):
    channel_label = _option_label(MarketingCampaign.CANALES, channel)
    priority_label = _option_label(MarketingCampaign.PRIORIDADES, priority)
    playbook = _channel_playbook(channel)
    budget = _suggested_budget(channel, priority)
    action_links = _link_list(channel)

    if field == 'objetivo':
        content = f"""
<p><strong>Objetivo comercial:</strong> convertir la campaña "{title}" en una iniciativa de {channel_label.lower()} con resultado medible en 30 días.</p>
<ul>
    <li>Definir KPI principal: leads, ventas, tráfico calificado o conversaciones iniciadas.</li>
    <li>Crear una oferta clara y una URL destino con UTM para medir el canal.</li>
    <li>Ejecutar una prueba inicial de 7 días, revisar CTR/CPL y duplicar la variante ganadora.</li>
    <li>Prioridad {priority_label.lower()}: presupuesto sugerido ${budget:,.0f} MXN para validar tracción sin sobredimensionar la inversión.</li>
</ul>
<p><strong>Guía de ejecución:</strong> revisar {action_links} antes de activar pauta, tracking o automatizaciones.</p>
"""
    elif field == 'audiencia':
        content = f"""
<p><strong>Audiencia recomendada:</strong> personas con intención comercial cercana al tema "{title}", segmentadas por problema, urgencia y capacidad de compra.</p>
<ul>
    <li>Segmento primario: clientes actuales o similares que ya entienden la categoría.</li>
    <li>Segmento de expansión: prospectos fríos con interés en {playbook['angle']}.</li>
    <li>Excluir usuarios sin intención clara y contactos sin consentimiento para evitar fricción comercial.</li>
    <li>Crear mensajes diferenciados para decisor, usuario final y comprador sensible a precio.</li>
</ul>
<p><strong>Acción concreta:</strong> preparar una lista de 3 perfiles, cargarla al canal y validar configuración con {action_links}.</p>
"""
    else:
        content = f"""
<p><strong>Mensaje / Oferta:</strong> presenta "{title}" como una solución directa, fácil de entender y con beneficio visible desde la primera línea.</p>
<ul>
    <li>Gancho: promesa específica ligada a ahorro, ventas, rapidez, confianza o conveniencia.</li>
    <li>Oferta: incentivo limitado, diagnóstico, demo, cotización rápida o paquete inicial según margen disponible.</li>
    <li>CTA: llevar a una landing, WhatsApp o formulario con una sola acción principal.</li>
    <li>Prueba: incluir testimonio, antes/después, número verificable o garantía razonable.</li>
</ul>
<p><strong>Siguiente paso:</strong> crear 2 variantes de copy y una pieza visual; usar {action_links} para configurar publicación, campaña o seguimiento.</p>
"""

    return {
        'field': field,
        'field_label': CAMPAIGN_AI_FIELDS[field],
        'content_html': sanitize_html(content),
        'suggested_budget': budget,
        'budget_rationale': (
            f'Base para {channel_label} con prioridad {priority_label}. '
            'Ajusta según margen, duración y tamaño de audiencia.'
        ),
        'actions': [
            'Configurar URL destino con UTM antes de publicar.',
            'Preparar al menos dos variantes creativas para prueba A/B.',
            'Revisar métricas a las 48-72 horas y pausar lo que no convierta.',
        ],
        'ai_used': False,
        'ai_provider': 'Recomendación local',
    }


def _build_campaign_field_prompt(title, channel, priority, field, current_values=None):
    current_values = current_values or {}
    channel_label = _option_label(MarketingCampaign.CANALES, channel)
    priority_label = _option_label(MarketingCampaign.PRIORIDADES, priority)
    playbook = _channel_playbook(channel)
    budget = _suggested_budget(channel, priority)

    return f"""
Actúa como experto senior en marketing especializado en {playbook['expert']}.
Evalúa una campaña en español y propone contenido accionable para el campo "{CAMPAIGN_AI_FIELDS[field]}".

Contexto:
- Título de campaña: {title}
- Canal: {channel_label}
- Prioridad: {priority_label}
- Objetivo actual: {strip_html(current_values.get('objetivo', ''))}
- Audiencia actual: {strip_html(current_values.get('audiencia', ''))}
- Mensaje/oferta actual: {strip_html(current_values.get('mensaje', ''))}
- Presupuesto base sugerido por heurística: {budget} MXN

Incluye acciones concretas y URLs explicativas cuando ayuden a ejecutar procesos del canal.
Usa HTML simple compatible con Quill: p, strong, ul, ol, li, a. No uses tablas.

Responde solo JSON válido con:
{{
  "content_html": "<p>...</p>",
  "suggested_budget": 0,
  "budget_rationale": "explicación breve",
  "actions": ["acción 1", "acción 2", "acción 3"]
}}
"""


def _parse_json_response(raw):
    cleaned = (raw or '').strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(cleaned)


def generate_campaign_field_suggestion(company, title, channel, priority, field, current_values=None):
    """Sugiere contenido para un campo de campaña nueva o existente."""
    title = (title or '').strip()
    channel = channel or 'digital'
    priority = priority or 'media'
    field = (field or '').strip()
    if field not in CAMPAIGN_AI_FIELDS:
        raise ValueError('Campo IA no soportado.')
    if len(title) <= 5:
        raise ValueError('El título de la campaña debe tener más de 5 caracteres.')

    fallback = _fallback_campaign_field_suggestion(title, channel, priority, field)

    if not company or not company.ai_provider or not company.ai_api_key:
        return fallback

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
        raw = call_fn(
            company.ai_api_key,
            company.ai_model,
            _build_campaign_field_prompt(title, channel, priority, field, current_values),
        )
        parsed = _parse_json_response(raw)
        content_html = sanitize_html(parsed.get('content_html') or fallback['content_html'])
        return {
            'field': field,
            'field_label': CAMPAIGN_AI_FIELDS[field],
            'content_html': content_html,
            'suggested_budget': parsed.get('suggested_budget') or fallback['suggested_budget'],
            'budget_rationale': parsed.get('budget_rationale') or fallback['budget_rationale'],
            'actions': parsed.get('actions') or fallback['actions'],
            'ai_used': True,
            'ai_provider': company.ai_provider_label,
        }
    except Exception as exc:
        current_app.logger.warning(f'Error sugiriendo campo de campaña con IA: {exc}')
        return fallback


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
    playbook = _channel_playbook(campaign.canal)

    if not company or not company.ai_provider or not company.ai_api_key:
        return fallback

    prompt = f"""
Actúa como experto senior en {playbook['expert']}.
Genera un kit de campaña de marketing en español para:
Nombre: {campaign.nombre}
Canal: {campaign.canal_label}
Prioridad: {campaign.prioridad_label}
Objetivo: {campaign.objetivo}
Audiencia: {campaign.audiencia}
Oferta/Mensaje: {campaign.mensaje}
URL destino: {campaign.url_destino}
Hashtags: {campaign.hashtags}
Objetivo Ads: {campaign.ad_objective_label}
Presupuesto: {campaign.presupuesto or 'pendiente'}
Contactos importados: {contacts_count}

Incluye acciones concretas y URLs explicativas si ayudan a ejecutar procesos del canal.
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
