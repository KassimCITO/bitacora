# -*- coding: utf-8 -*-
"""
Rutas de autenticación: login / logout.
Soporta multi-tenant con sesión de empresa.
"""
from time import time
from urllib.parse import urlparse, urljoin
from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint('auth', __name__)
_FAILED_LOGINS = {}


def _client_key(username):
    forwarded_for = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    ip_addr = forwarded_for or request.remote_addr or 'unknown'
    return f"{ip_addr}:{(username or '').lower()}"


def _rate_limit_state(username):
    key = _client_key(username)
    now = time()
    state = _FAILED_LOGINS.get(key)
    if not state:
        return key, None
    if state.get('locked_until', 0) <= now and state.get('count', 0) <= 0:
        _FAILED_LOGINS.pop(key, None)
        return key, None
    return key, state


def _register_failed_login(username):
    key, state = _rate_limit_state(username)
    now = time()
    state = state or {'count': 0, 'first_failed_at': now, 'locked_until': 0}
    if now - state.get('first_failed_at', now) > current_app.config.get('LOGIN_LOCKOUT_SECONDS', 900):
        state = {'count': 0, 'first_failed_at': now, 'locked_until': 0}

    state['count'] = state.get('count', 0) + 1
    if state['count'] >= current_app.config.get('LOGIN_MAX_FAILED_ATTEMPTS', 5):
        state['locked_until'] = now + current_app.config.get('LOGIN_LOCKOUT_SECONDS', 900)
    _FAILED_LOGINS[key] = state


def _clear_failed_login(username):
    _FAILED_LOGINS.pop(_client_key(username), None)


def _is_safe_next(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Formulario de inicio de sesión."""
    if current_user.is_authenticated and request.method == 'GET':
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == '1'

        if not username or not password:
            flash('Ingresa usuario y contraseña.', 'warning')
            return render_template('auth/login.html')

        _, rate_state = _rate_limit_state(username)
        if rate_state and rate_state.get('locked_until', 0) > time():
            remaining = max(1, int((rate_state['locked_until'] - time()) // 60) + 1)
            flash(f'Demasiados intentos. Espera {remaining} min antes de intentar de nuevo.', 'danger')
            return render_template('auth/login.html'), 429

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.activo:
                _register_failed_login(username)
                flash('No fue posible iniciar sesión con esas credenciales.', 'danger')
                return render_template('auth/login.html')

            _clear_failed_login(username)
            session.clear()
            session.permanent = not remember
            login_user(user, remember=remember, fresh=True)

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
            return redirect(next_page if _is_safe_next(next_page) else url_for('dashboard.index'))
        else:
            _register_failed_login(username)
            flash('No fue posible iniciar sesión con esas credenciales.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario."""
    session.pop('empresa_id', None)
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))
