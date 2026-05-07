# -*- coding: utf-8 -*-
"""
API endpoints para operaciones AJAX y exportación CSV.
Multi-tenant: filtrado por empresa_id.
"""
from flask import Blueprint, request, make_response, jsonify, session
from flask_login import login_required, current_user
from ..models.task import Task
from ..services.export_service import export_tasks_csv
from ..utils.decorators import role_required

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


@api_bp.route('/tasks/export/csv')
@login_required
@role_required('administrador', 'manager', 'visor')
def export_csv():
    """Exportar tareas a CSV con filtros opcionales."""
    empresa_id = _get_empresa_id()
    estado = request.args.get('estado', '')
    prioridad = request.args.get('prioridad', '')
    usuario_id = request.args.get('usuario', '', type=str)
    grupo_id = request.args.get('grupo', '', type=str)
    search = request.args.get('search', '').strip()

    query = Task.query.filter_by(empresa_id=empresa_id)

    if estado:
        query = query.filter_by(estado=estado)
    if prioridad:
        query = query.filter_by(prioridad=prioridad)
    if usuario_id:
        query = query.filter_by(usuario_asignado_id=int(usuario_id))
    if grupo_id:
        query = query.filter_by(grupo_id=int(grupo_id))
    if search:
        query = query.filter(Task.nombre.ilike(f'%{search}%'))

    tasks = query.order_by(Task.fecha_creacion.desc()).all()
    csv_data = export_tasks_csv(tasks)

    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=tareas_exportadas.csv'
    return response
