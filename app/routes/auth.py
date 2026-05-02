# -*- coding: utf-8 -*-
"""
Rutas de autenticación: login / logout.
Soporta multi-tenant con sesión de empresa.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Formulario de inicio de sesión."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Ingresa usuario y contraseña.', 'warning')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=request.form.get('remember'))

            # Establecer empresa en sesión
            if user.empresa_id:
                session['empresa_id'] = user.empresa_id
            elif user.is_superuser:
                # Superuser: seleccionar primera empresa activa o ninguna
                from ..models.company import Company
                first_company = Company.query.filter_by(activa=True).first()
                if first_company:
                    session['empresa_id'] = first_company.id

            flash(f'¡Bienvenido, {user.nombre_completo}!', 'success')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario."""
    session.pop('empresa_id', None)
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))
