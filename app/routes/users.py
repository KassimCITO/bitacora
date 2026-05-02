# -*- coding: utf-8 -*-
"""
Rutas de gestión de usuarios (administrador + superuser).
Filtrado multi-tenant por empresa_id.
"""
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, session
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.user import User, Role
from ..models.group import Group
from ..utils.decorators import admin_required, role_required

users_bp = Blueprint('users', __name__, url_prefix='/users')


def _get_empresa_id():
    """Obtiene el empresa_id activo."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


@users_bp.route('/')
@login_required
@admin_required
def list_users():
    """Lista de todos los usuarios de la empresa."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    users = User.query.filter_by(empresa_id=empresa_id).order_by(User.nombre_completo).all()
    return render_template('users/list.html', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Crear un nuevo usuario."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        nombre = request.form.get('nombre_completo', '').strip()
        role_id = request.form.get('role_id', type=int)

        # Validaciones
        if not all([username, email, password, nombre, role_id]):
            flash('Todos los campos son obligatorios.', 'warning')
        elif User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('El email ya está registrado.', 'danger')
        else:
            user = User(
                username=username,
                email=email,
                nombre_completo=nombre,
                role_id=role_id,
                empresa_id=empresa_id,
            )
            user.set_password(password)

            # Asignar grupos
            group_ids = request.form.getlist('groups')
            if group_ids:
                groups = Group.query.filter(
                    Group.id.in_([int(gid) for gid in group_ids]),
                    Group.empresa_id == empresa_id,
                ).all()
                for g in groups:
                    g.members.append(user)

            db.session.add(user)
            db.session.commit()
            flash(f'Usuario "{username}" creado exitosamente.', 'success')
            return redirect(url_for('users.list_users'))

    # Excluir rol superuser de la lista
    roles = Role.query.filter(Role.name != 'superuser').order_by(Role.id).all()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Group.nombre).all()
    return render_template('users/create.html', roles=roles, groups=groups)


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(user_id):
    """Editar un usuario existente."""
    empresa_id = _get_empresa_id()
    user = User.query.get_or_404(user_id)

    if user.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    if request.method == 'POST':
        user.username = request.form.get('username', user.username).strip()
        user.email = request.form.get('email', user.email).strip()
        user.nombre_completo = request.form.get('nombre_completo', user.nombre_completo).strip()
        user.role_id = request.form.get('role_id', user.role_id, type=int)

        # Cambiar contraseña solo si se proporciona
        new_password = request.form.get('password', '').strip()
        if new_password:
            user.set_password(new_password)

        # Actualizar grupos
        current_groups = user.groups.all()
        for g in current_groups:
            g.members.remove(user)

        group_ids = request.form.getlist('groups')
        if group_ids:
            groups = Group.query.filter(
                Group.id.in_([int(gid) for gid in group_ids]),
                Group.empresa_id == empresa_id,
            ).all()
            for g in groups:
                g.members.append(user)

        try:
            db.session.commit()
            flash('Usuario actualizado correctamente.', 'success')
            return redirect(url_for('users.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    roles = Role.query.filter(Role.name != 'superuser').order_by(Role.id).all()
    groups = Group.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Group.nombre).all()
    current_group_ids = [g.id for g in user.groups.all()]
    return render_template('users/edit.html', user=user, roles=roles,
                           groups=groups, current_group_ids=current_group_ids)


@users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    """Activar o desactivar un usuario."""
    empresa_id = _get_empresa_id()
    user = User.query.get_or_404(user_id)

    if user.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    user.activo = not user.activo
    db.session.commit()

    estado = 'activado' if user.activo else 'desactivado'
    flash(f'Usuario "{user.username}" {estado}.', 'info')
    return redirect(url_for('users.list_users'))
