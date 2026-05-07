# -*- coding: utf-8 -*-
"""
Rutas de analítica e IA.
Dashboard de análisis con gráficos de pie por empresa, grupo y usuario.
"""
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, session, jsonify
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.task import Task
from ..models.user import User
from ..models.group import Group
from ..models.company import Company
from ..services.ai_service import (
    generate_ai_analysis, get_company_stats,
    get_group_stats, get_user_stats
)
from ..utils.decorators import role_required

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


@analytics_bp.route('/')
@login_required
@role_required('administrador', 'manager', 'visor')
def index():
    """Dashboard principal de analítica."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    company = Company.query.get_or_404(empresa_id)
    stats = get_company_stats(empresa_id)

    # Grupos con estadísticas
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).all()
    group_stats = []
    for g in groups:
        gs = get_group_stats(g.id)
        group_stats.append({
            'id': g.id,
            'nombre': g.nombre,
            'color': g.color,
            'stats': gs,
        })

    # Top usuarios
    users = User.query.filter_by(empresa_id=empresa_id, activo=True).all()
    user_stats = []
    for u in users:
        us = get_user_stats(u.id, empresa_id)
        user_stats.append({
            'id': u.id,
            'nombre': u.nombre_completo,
            'stats': us,
        })
    # Ordenar por avance descendente
    user_stats.sort(key=lambda x: x['stats']['avance_promedio'], reverse=True)

    return render_template(
        'analytics/index.html',
        company=company,
        stats=stats,
        group_stats=group_stats,
        user_stats=user_stats,
    )


@analytics_bp.route('/group/<int:group_id>')
@login_required
@role_required('administrador', 'manager', 'visor')
def group_detail(group_id):
    """Análisis detallado de un grupo."""
    empresa_id = _get_empresa_id()
    group = Group.query.get_or_404(group_id)

    if group.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    stats = get_group_stats(group_id)
    return render_template('analytics/group_detail.html', group=group, stats=stats)


@analytics_bp.route('/user/<int:user_id>')
@login_required
@role_required('administrador', 'manager', 'visor')
def user_detail(user_id):
    """Análisis detallado de un usuario."""
    empresa_id = _get_empresa_id()
    user = User.query.get_or_404(user_id)

    if user.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    stats = get_user_stats(user_id, empresa_id)
    return render_template('analytics/user_detail.html', user=user, stats=stats)


@analytics_bp.route('/api/ai-analyze', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def ai_analyze():
    """Endpoint AJAX para generar análisis de IA."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400

    payload = request.get_json(silent=True) or {}
    context_type = payload.get('context_type', 'empresa')
    context_id = payload.get('context_id')

    result = generate_ai_analysis(empresa_id, context_type, context_id)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)
