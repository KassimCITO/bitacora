# -*- coding: utf-8 -*-
"""
Rutas de gestión de tareas: CRUD, avances, adjuntos.
Filtrado multi-tenant por empresa_id.
"""
import os
from datetime import datetime, timedelta, timezone
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, send_file, abort, session
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.task import Task
from ..models.task_log import TaskLog
from ..models.attachment import Attachment
from ..models.user import User
from ..models.group import Group
from ..services.image_service import image_url, optimize_image_upload
from ..utils.decorators import role_required
from ..utils.helpers import allowed_file, save_upload
from ..utils.sanitizer import sanitize_html

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


def _task_time(task):
    """Fecha operativa para ordenar/separar tareas en la vista."""
    return task.ultima_actualizacion or task.fecha_creacion or task.fecha_hora_inicio


def _format_elapsed(delta):
    """Convierte un timedelta en texto breve para separadores de tareas."""
    total_seconds = int(abs(delta.total_seconds()))
    if total_seconds < 60:
        return 'menos de 1 min'

    minutes = total_seconds // 60
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)

    parts = []
    if days:
        parts.append(f"{days} dia{'s' if days != 1 else ''}")
    if hours and len(parts) < 2:
        parts.append(f"{hours} h")
    if minutes and len(parts) < 2:
        parts.append(f"{minutes} min")
    return ' '.join(parts)


def _build_task_timeline(tasks):
    """Prepara tareas con separadores de tiempo entre una y otra."""
    rows = []
    previous_task = None
    previous_time = None

    for task in tasks:
        current_time = _task_time(task)
        separator = None

        if previous_task and previous_time and current_time:
            separator = {
                'label': _format_elapsed(previous_time - current_time),
                'detail': f"Entre #{previous_task.id} y #{task.id}",
            }

        rows.append({
            'task': task,
            'separator': separator,
        })
        previous_task = task
        previous_time = current_time

    return rows


@tasks_bp.route('/')
@login_required
def list_tasks():
    """Lista de tareas con filtros y paginación."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', '')
    prioridad = request.args.get('prioridad', '')
    usuario_id = request.args.get('usuario', '', type=str)
    grupo_id = request.args.get('grupo', '', type=str)
    search = request.args.get('search', '').strip()

    # Query base según rol + empresa
    if current_user.has_role('administrador', 'manager', 'visor') or current_user.is_superuser:
        query = Task.query.filter_by(empresa_id=empresa_id)
    else:
        query = Task.query.filter_by(empresa_id=empresa_id, usuario_asignado_id=current_user.id)

    # Aplicar filtros
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

    now = datetime.now()
    due_soon_limit = now + timedelta(hours=48)
    open_states = ('pendiente', 'en_progreso', 'pausada')
    pulse = {
        'overdue': query.filter(
            Task.estado.in_(open_states),
            Task.fecha_hora_fin_estimada.isnot(None),
            Task.fecha_hora_fin_estimada < now,
        ).count(),
        'due_soon': query.filter(
            Task.estado.in_(open_states),
            Task.fecha_hora_fin_estimada.isnot(None),
            Task.fecha_hora_fin_estimada >= now,
            Task.fecha_hora_fin_estimada <= due_soon_limit,
        ).count(),
        'high_priority': query.filter(
            Task.estado.in_(open_states),
            Task.prioridad == 'alta',
        ).count(),
    }

    # Ordenar y paginar
    query = query.order_by(Task.ultima_actualizacion.desc())
    pagination = query.paginate(
        page=page,
        per_page=current_app.config.get('TASKS_PER_PAGE', 15),
        error_out=False,
    )
    task_rows = _build_task_timeline(pagination.items)
    pulse['without_progress'] = sum(1 for task in pagination.items if task.ultimo_avance == 0)

    # Usuarios y grupos para filtro
    users = User.query.filter_by(empresa_id=empresa_id, activo=True).order_by(User.nombre_completo).all()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Group.nombre).all()

    return render_template(
        'tasks/list.html',
        tasks=pagination.items,
        task_rows=task_rows,
        pulse=pulse,
        pagination=pagination,
        users=users,
        groups=groups,
        estados=Task.ESTADOS,
        prioridades=Task.PRIORIDADES,
        filter_estado=estado,
        filter_prioridad=prioridad,
        filter_usuario=usuario_id,
        filter_grupo=grupo_id,
        filter_search=search,
    )


@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'manager')
def create():
    """Crear una nueva tarea."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    if request.method == 'POST':
        try:
            task = Task(
                nombre=request.form['nombre'].strip(),
                descripcion=sanitize_html(request.form.get('descripcion', '')),
                fecha_hora_inicio=datetime.fromisoformat(request.form['fecha_hora_inicio']),
                fecha_hora_fin_estimada=(
                    datetime.fromisoformat(request.form['fecha_hora_fin_estimada'])
                    if request.form.get('fecha_hora_fin_estimada') else None
                ),
                estado=request.form.get('estado', 'pendiente'),
                prioridad=request.form.get('prioridad', 'media'),
                usuario_asignado_id=int(request.form['usuario_asignado_id']),
                creado_por_id=current_user.id,
                empresa_id=empresa_id,
                grupo_id=int(request.form['grupo_id']) if request.form.get('grupo_id') else None,
            )
            db.session.add(task)
            db.session.commit()

            # Crear log inicial
            log = TaskLog(
                task_id=task.id,
                usuario_id=current_user.id,
                comentario='Tarea creada.',
                porcentaje_avance=0,
            )
            db.session.add(log)
            db.session.commit()

            flash('Tarea creada exitosamente.', 'success')
            return redirect(url_for('tasks.detail', task_id=task.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la tarea: {str(e)}', 'danger')

    users = User.query.filter_by(empresa_id=empresa_id, activo=True).order_by(User.nombre_completo).all()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Group.nombre).all()
    return render_template(
        'tasks/create.html',
        users=users,
        groups=groups,
        estados=Task.ESTADOS,
        prioridades=Task.PRIORIDADES,
    )


@tasks_bp.route('/editor-image', methods=['POST'])
@login_required
@role_required('administrador', 'manager')
def editor_image_upload():
    """Sube una imagen para incrustarla en el editor de tareas."""
    file = request.files.get('image')
    try:
        _, ruta, _, _ = optimize_image_upload(
            file,
            current_app.config['UPLOAD_FOLDER'],
            prefix='task-editor',
            max_size=(1800, 1800),
            quality=84,
        )
    except Exception as exc:
        return {'error': str(exc)}, 400

    return {'url': image_url(ruta)}


@tasks_bp.route('/<int:task_id>')
@login_required
def detail(task_id):
    """Detalle de una tarea con historial de avances."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()

    # Control de acceso multi-tenant
    if task.empresa_id != empresa_id:
        abort(403)

    # Control de acceso: usuario normal solo ve sus tareas
    if current_user.has_role('usuario') and task.usuario_asignado_id != current_user.id:
        abort(403)

    # Historial ordenado cronológicamente
    logs = task.logs.order_by(None).order_by(TaskLog.fecha_hora.asc()).all()
    attachments = task.attachments.order_by(Attachment.fecha_subida.desc()).all()

    return render_template(
        'tasks/detail.html',
        task=task,
        logs=logs,
        attachments=attachments,
    )


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'manager')
def edit(task_id):
    """Editar una tarea existente."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()

    if task.empresa_id != empresa_id:
        abort(403)

    if request.method == 'POST':
        try:
            task.nombre = request.form['nombre'].strip()
            task.descripcion = sanitize_html(request.form.get('descripcion', ''))
            task.fecha_hora_inicio = datetime.fromisoformat(request.form['fecha_hora_inicio'])
            task.fecha_hora_fin_estimada = (
                datetime.fromisoformat(request.form['fecha_hora_fin_estimada'])
                if request.form.get('fecha_hora_fin_estimada') else None
            )
            task.fecha_hora_fin_real = (
                datetime.fromisoformat(request.form['fecha_hora_fin_real'])
                if request.form.get('fecha_hora_fin_real') else None
            )
            task.estado = request.form.get('estado', task.estado)
            task.prioridad = request.form.get('prioridad', task.prioridad)
            task.usuario_asignado_id = int(request.form['usuario_asignado_id'])
            task.grupo_id = int(request.form['grupo_id']) if request.form.get('grupo_id') else None

            db.session.commit()
            flash('Tarea actualizada exitosamente.', 'success')
            return redirect(url_for('tasks.detail', task_id=task.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    users = User.query.filter_by(empresa_id=empresa_id, activo=True).order_by(User.nombre_completo).all()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Group.nombre).all()
    return render_template(
        'tasks/edit.html',
        task=task,
        users=users,
        groups=groups,
        estados=Task.ESTADOS,
        prioridades=Task.PRIORIDADES,
    )


@tasks_bp.route('/<int:task_id>/log', methods=['POST'])
@login_required
@role_required('administrador', 'manager', 'usuario')
def add_log(task_id):
    """Agregar un avance a la bitácora de la tarea."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()

    if task.empresa_id != empresa_id:
        abort(403)

    # Usuario normal solo puede agregar avances a sus tareas
    if current_user.has_role('usuario') and task.usuario_asignado_id != current_user.id:
        abort(403)

    comentario = sanitize_html(request.form.get('comentario', '').strip())
    porcentaje = request.form.get('porcentaje_avance', 0, type=int)

    if not comentario:
        flash('El comentario es obligatorio.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task_id))

    # Validar porcentaje
    porcentaje = max(0, min(100, porcentaje))

    log = TaskLog(
        task_id=task.id,
        usuario_id=current_user.id,
        comentario=comentario,
        porcentaje_avance=porcentaje,
    )
    db.session.add(log)

    # Actualizar estado de la tarea si se permite
    nuevo_estado = request.form.get('nuevo_estado', '')
    if nuevo_estado and nuevo_estado in dict(Task.ESTADOS):
        task.estado = nuevo_estado
        if nuevo_estado == 'terminada' and not task.fecha_hora_fin_real:
            task.fecha_hora_fin_real = datetime.now(timezone.utc)

    db.session.commit()
    flash('Avance registrado correctamente.', 'success')
    return redirect(url_for('tasks.detail', task_id=task_id))


@tasks_bp.route('/<int:task_id>/upload', methods=['POST'])
@login_required
@role_required('administrador', 'manager', 'usuario')
def upload_file(task_id):
    """Subir un archivo adjunto a la tarea."""
    task = Task.query.get_or_404(task_id)
    empresa_id = _get_empresa_id()

    if task.empresa_id != empresa_id:
        abort(403)

    if current_user.has_role('usuario') and task.usuario_asignado_id != current_user.id:
        abort(403)

    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task_id))

    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task_id))

    if not allowed_file(file.filename):
        flash('Tipo de archivo no permitido.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task_id))

    try:
        nombre, ruta, mime, tamano = save_upload(
            file, current_app.config['UPLOAD_FOLDER']
        )
        attachment = Attachment(
            task_id=task.id,
            usuario_id=current_user.id,
            nombre_archivo=nombre,
            ruta_archivo=ruta,
            tipo_mime=mime,
            tamano=tamano,
        )
        db.session.add(attachment)
        db.session.commit()
        flash('Archivo subido correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir archivo: {str(e)}', 'danger')

    return redirect(url_for('tasks.detail', task_id=task_id))


@tasks_bp.route('/<int:task_id>/download/<int:att_id>')
@login_required
def download_file(task_id, att_id):
    """Descargar un archivo adjunto."""
    attachment = Attachment.query.get_or_404(att_id)
    if attachment.task_id != task_id:
        abort(404)

    if not os.path.exists(attachment.ruta_archivo):
        flash('Archivo no encontrado.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task_id))

    return send_file(
        attachment.ruta_archivo,
        download_name=attachment.nombre_archivo,
        as_attachment=True,
    )
