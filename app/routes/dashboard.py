# -*- coding: utf-8 -*-
"""
Dashboard principal con resumen de tareas y datos de calendario.
Filtrado por empresa (multi-tenant).
"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, jsonify, request, session
from flask_login import login_required, current_user
from sqlalchemy import func, cast, Date
from ..extensions import db
from ..models.task import Task
from ..models.group import Group

dashboard_bp = Blueprint('dashboard', __name__)


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


def _base_query():
    """Query base filtrada por empresa y rol."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        return Task.query.filter(False)  # Query vacía

    query = Task.query.filter_by(empresa_id=empresa_id)

    if not current_user.has_role('administrador', 'manager', 'visor') and not current_user.is_superuser:
        query = query.filter_by(usuario_asignado_id=current_user.id)

    return query


@dashboard_bp.route('/')
@login_required
def index():
    """Vista principal del dashboard."""
    base_query = _base_query()

    # Conteo por estado
    estado_counts = dict(
        db.session.query(Task.estado, func.count(Task.id))
        .filter(Task.id.in_(base_query.with_entities(Task.id)))
        .group_by(Task.estado)
        .all()
    )

    # Total de tareas
    total = sum(estado_counts.values())

    # Tareas recientes (últimas 10)
    recent_tasks = base_query.order_by(Task.ultima_actualizacion.desc()).limit(10).all()

    # Tareas de alta prioridad pendientes
    urgent = base_query.filter(
        Task.prioridad == 'alta',
        Task.estado.in_(['pendiente', 'en_progreso'])
    ).count()

    # Grupos de la empresa
    empresa_id = _get_empresa_id()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).all() if empresa_id else []

    return render_template(
        'dashboard/index.html',
        estado_counts=estado_counts,
        total=total,
        recent_tasks=recent_tasks,
        urgent=urgent,
        groups=groups,
    )


@dashboard_bp.route('/api/calendar-data')
@login_required
def calendar_data():
    """
    Endpoint AJAX para datos del calendario.
    Params:
        view: daily | weekly | monthly | yearly
        date: YYYY-MM-DD (fecha de referencia)
    Returns:
        JSON con conteo de tareas por día/período.
    """
    view = request.args.get('view', 'monthly')
    date_str = request.args.get('date', '')

    try:
        ref_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now(timezone.utc).date()
    except ValueError:
        ref_date = datetime.now(timezone.utc).date()

    base_query = _base_query()

    # Determinar rango de fechas según vista
    if view == 'daily':
        start = ref_date
        end = ref_date
    elif view == 'weekly':
        start = ref_date - timedelta(days=ref_date.weekday())  # Lunes
        end = start + timedelta(days=6)  # Domingo
    elif view == 'yearly':
        start = ref_date.replace(month=1, day=1)
        end = ref_date.replace(month=12, day=31)
    else:  # monthly
        start = ref_date.replace(day=1)
        next_month = start.replace(day=28) + timedelta(days=4)
        end = next_month - timedelta(days=next_month.day)

    # Obtener tareas en el rango
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    tasks_in_range = base_query.filter(
        Task.fecha_hora_inicio <= end_dt,
        db.or_(
            Task.fecha_hora_fin_estimada >= start_dt,
            Task.fecha_hora_fin_estimada.is_(None),
        ),
    ).all()

    # Construir datos por día
    calendar_items = {}
    current = start
    while current <= end:
        day_key = current.isoformat()
        day_start = datetime.combine(current, datetime.min.time())
        day_end = datetime.combine(current, datetime.max.time())

        # Contar tareas activas en este día
        day_tasks = [t for t in tasks_in_range
                     if t.fecha_hora_inicio <= day_end and
                     (t.fecha_hora_fin_estimada is None or t.fecha_hora_fin_estimada >= day_start)]

        pendientes = sum(1 for t in day_tasks if t.estado in ('pendiente', 'en_progreso'))
        total_day = len(day_tasks)

        calendar_items[day_key] = {
            'total': total_day,
            'pendientes': pendientes,
            'terminadas': sum(1 for t in day_tasks if t.estado == 'terminada'),
        }

        current += timedelta(days=1)

    # Info de navegación
    prev_date = start - timedelta(days=1)
    next_date = end + timedelta(days=1)

    return jsonify({
        'view': view,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'ref_date': ref_date.isoformat(),
        'prev_date': prev_date.isoformat(),
        'next_date': next_date.isoformat(),
        'items': calendar_items,
    })
