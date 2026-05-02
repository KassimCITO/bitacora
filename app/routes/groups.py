# -*- coding: utf-8 -*-
"""
Rutas de gestión de grupos de usuarios.
Agrupación funcional: Gerencia, Administración, Programación, etc.
"""
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, session
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models.group import Group
from ..models.user import User
from ..utils.decorators import role_required

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')


def _get_empresa_id():
    """Obtiene el empresa_id activo de la sesión o del usuario."""
    if current_user.is_superuser:
        return session.get('empresa_id')
    return current_user.empresa_id


@groups_bp.route('/')
@login_required
@role_required('administrador', 'manager')
def list_groups():
    """Lista de grupos de la empresa actual."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    groups = Group.query.filter_by(empresa_id=empresa_id).order_by(Group.nombre).all()
    return render_template('groups/list.html', groups=groups)


@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('administrador')
def create():
    """Crear un nuevo grupo."""
    empresa_id = _get_empresa_id()
    if not empresa_id:
        flash('Selecciona una empresa primero.', 'warning')
        return redirect(url_for('companies.list_companies'))

    if request.method == 'POST':
        try:
            group = Group(
                nombre=request.form.get('nombre', '').strip(),
                descripcion=request.form.get('descripcion', '').strip(),
                color=request.form.get('color', '#00d4aa').strip(),
                empresa_id=empresa_id,
            )
            db.session.add(group)
            db.session.flush()

            # Asignar miembros
            member_ids = request.form.getlist('members')
            if member_ids:
                members = User.query.filter(
                    User.id.in_([int(mid) for mid in member_ids]),
                    User.empresa_id == empresa_id,
                ).all()
                for member in members:
                    group.members.append(member)

            db.session.commit()
            flash(f'Grupo "{group.nombre}" creado exitosamente.', 'success')
            return redirect(url_for('groups.list_groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear grupo: {str(e)}', 'danger')

    users = User.query.filter_by(empresa_id=empresa_id, activo=True).order_by(User.nombre_completo).all()
    return render_template('groups/form.html', group=None, users=users)


@groups_bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('administrador')
def edit(group_id):
    """Editar un grupo existente."""
    empresa_id = _get_empresa_id()
    group = Group.query.get_or_404(group_id)

    if group.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    if request.method == 'POST':
        try:
            group.nombre = request.form.get('nombre', group.nombre).strip()
            group.descripcion = request.form.get('descripcion', '').strip()
            group.color = request.form.get('color', '#00d4aa').strip()

            # Actualizar miembros: limpiar y reasignar
            current_members = group.members.all()
            for m in current_members:
                group.members.remove(m)

            member_ids = request.form.getlist('members')
            if member_ids:
                members = User.query.filter(
                    User.id.in_([int(mid) for mid in member_ids]),
                    User.empresa_id == empresa_id,
                ).all()
                for member in members:
                    group.members.append(member)

            db.session.commit()
            flash('Grupo actualizado correctamente.', 'success')
            return redirect(url_for('groups.list_groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    users = User.query.filter_by(empresa_id=empresa_id, activo=True).order_by(User.nombre_completo).all()
    current_member_ids = [m.id for m in group.members.all()]
    return render_template('groups/form.html', group=group, users=users,
                           current_member_ids=current_member_ids)


@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
@role_required('administrador')
def delete(group_id):
    """Eliminar un grupo."""
    empresa_id = _get_empresa_id()
    group = Group.query.get_or_404(group_id)

    if group.empresa_id != empresa_id:
        from flask import abort
        abort(403)

    nombre = group.nombre
    db.session.delete(group)
    db.session.commit()
    flash(f'Grupo "{nombre}" eliminado.', 'info')
    return redirect(url_for('groups.list_groups'))
