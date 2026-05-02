# -*- coding: utf-8 -*-
"""
Decoradores de control de acceso por roles.
Incluye soporte para superuser global.
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Decorador que restringe el acceso a usuarios con roles específicos.
    El superuser siempre tiene acceso.

    Uso:
        @role_required('administrador', 'manager')
        def mi_vista():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Inicia sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))
            # Superuser siempre tiene acceso
            if current_user.is_superuser:
                return f(*args, **kwargs)
            if not current_user.has_role(*roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Acceso solo para administradores (y superuser)."""
    return role_required('administrador')(f)


def manager_or_admin_required(f):
    """Acceso para administradores y managers (y superuser)."""
    return role_required('administrador', 'manager')(f)


def superuser_required(f):
    """Acceso exclusivo para superuser global."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Inicia sesión para acceder.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_superuser:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
