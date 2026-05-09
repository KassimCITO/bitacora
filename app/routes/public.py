# -*- coding: utf-8 -*-
"""
Public commercial entry points for Bitacora SaaS.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_mail import Message

from ..extensions import mail


public_bp = Blueprint('public', __name__)


PLANS = [
    {
        'key': 'starter',
        'name': 'Starter',
        'tagline': 'Para ordenar la operacion sin hojas sueltas.',
        'price': 'Desde $1,490 MXN/mes',
        'setup': 'Implementacion ligera',
        'highlight': False,
        'cta': 'Iniciar prueba',
        'best_for': 'Equipos de 5 a 15 usuarios',
        'features': [
            '1 empresa configurada',
            'Tareas, avances y evidencias',
            'Reportes PDF y exportacion CSV',
            'Usuarios por rol: admin, manager, usuario y visor',
            'Soporte de arranque por email',
        ],
    },
    {
        'key': 'pro',
        'name': 'Pro',
        'tagline': 'Para equipos que reportan a direccion o clientes.',
        'price': 'Desde $2,990 MXN/mes',
        'setup': 'Onboarding operativo incluido',
        'highlight': True,
        'cta': 'Solicitar demo',
        'best_for': 'Operaciones de 15 a 50 usuarios',
        'features': [
            'Grupos, filtros y pulso operativo',
            'Analitica con IA configurable',
            'Reportes por rango y envio por email',
            'Branding de empresa en app y documentos',
            'Configuracion SMTP propia',
        ],
    },
    {
        'key': 'business',
        'name': 'Business',
        'tagline': 'Para vender control multiempresa como servicio.',
        'price': 'A cotizar',
        'setup': 'Implementacion consultiva',
        'highlight': False,
        'cta': 'Hablar de rollout',
        'best_for': 'Multiempresa, franquicias o clientes externos',
        'features': [
            'Gestion multiempresa',
            'APP-Key y control comercial por cliente',
            'Plantillas y reportes personalizados',
            'Soporte prioritario',
            'Ruta de integraciones y automatizacion',
        ],
    },
]

PLAN_KEYS = {plan['key'] for plan in PLANS}


def _clean(value, limit=180):
    return (value or '').strip()[:limit]


def _lead_inbox_path():
    configured_path = current_app.config.get('LEAD_INBOX_PATH')
    if configured_path:
        return Path(configured_path)
    return Path(current_app.instance_path) / 'commercial_leads.jsonl'


def _store_lead(lead):
    inbox_path = _lead_inbox_path()
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    with inbox_path.open('a', encoding='utf-8') as lead_file:
        lead_file.write(json.dumps(lead, ensure_ascii=False, sort_keys=True) + '\n')


def _notify_sales(lead):
    recipient = current_app.config.get('SALES_LEADS_EMAIL')
    if not recipient:
        return False

    subject = f"Nuevo lead Bitacora: {lead['company']} ({lead['plan']})"
    body = "\n".join([
        'Nuevo contacto desde la pagina de precios de Bitacora.',
        '',
        f"Referencia: {lead['id']}",
        f"Plan: {lead['plan']}",
        f"Nombre: {lead['name']}",
        f"Empresa: {lead['company']}",
        f"Email: {lead['email']}",
        f"Telefono: {lead['phone'] or '-'}",
        f"Usuarios: {lead['team_size'] or '-'}",
        f"Mensaje: {lead['message'] or '-'}",
    ])

    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
        )
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.warning('No se pudo enviar lead comercial por email: %s', exc)
        return False


@public_bp.route('/pricing')
@public_bp.route('/planes')
def pricing():
    selected_plan = request.args.get('plan', 'pro')
    if selected_plan not in PLAN_KEYS:
        selected_plan = 'pro'
    return render_template('public/pricing.html', plans=PLANS, selected_plan=selected_plan)


@public_bp.route('/request-demo', methods=['POST'])
@public_bp.route('/solicitar-demo', methods=['POST'])
def request_demo():
    if _clean(request.form.get('website'), 120):
        flash('Solicitud recibida.', 'success')
        return redirect(url_for('public.pricing', sent='1'))

    plan = _clean(request.form.get('plan'), 40)
    name = _clean(request.form.get('name'), 120)
    company = _clean(request.form.get('company'), 160)
    email = _clean(request.form.get('email'), 180)
    phone = _clean(request.form.get('phone'), 60)
    team_size = _clean(request.form.get('team_size'), 40)
    message = _clean(request.form.get('message'), 900)

    if plan not in PLAN_KEYS:
        plan = 'pro'

    missing = []
    if not name:
        missing.append('nombre')
    if not company:
        missing.append('empresa')
    if not email or '@' not in email:
        missing.append('email valido')

    if missing:
        flash('Completa: ' + ', '.join(missing) + '.', 'warning')
        return redirect(url_for('public.pricing', plan=plan, contact='1') + '#contacto')

    lead = {
        'id': uuid4().hex[:10].upper(),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'plan': plan,
        'name': name,
        'company': company,
        'email': email,
        'phone': phone,
        'team_size': team_size,
        'message': message,
        'source': 'pricing_page',
        'remote_addr': request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip(),
        'user_agent': request.headers.get('User-Agent', '')[:240],
    }

    _store_lead(lead)
    _notify_sales(lead)

    flash(f'Solicitud recibida. Referencia {lead["id"]}. Te contactaremos para activar prueba o demo.', 'success')
    return redirect(url_for('public.pricing', plan=plan, sent='1') + '#contacto')
