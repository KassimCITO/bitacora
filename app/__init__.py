# -*- coding: utf-8 -*-
"""
Bitácora SaaS by KzmCITO - Kassim Assad Mosri Rodríguez — Application Factory
Multi-tenant, multi-empresa.
"""
import os
from flask import Flask, flash, redirect, request, send_from_directory, session, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from .config import config_map
from .extensions import db, migrate, login_manager, csrf, mail


def create_app(config_name=None):
    """Crea y configura la aplicación Flask."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Asegurar que existan los directorios necesarios
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.endpoint == 'auth.login':
            flash('La sesión de acceso expiró. Vuelve a intentar iniciar sesión.', 'warning')
            return redirect(url_for('auth.login'))
        flash('La sesión del formulario expiró. Recarga la página e intenta nuevamente.', 'warning')
        return redirect(request.referrer or url_for('dashboard.index'))

    @app.template_filter('plain_text')
    def plain_text_filter(value):
        from .utils.sanitizer import strip_html
        return strip_html(value)

    # Registrar user_loader
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Registrar Blueprints
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.tasks import tasks_bp
    from .routes.users import users_bp
    from .routes.reports import reports_bp
    from .routes.api import api_bp
    from .routes.companies import companies_bp
    from .routes.groups import groups_bp
    from .routes.analytics import analytics_bp
    from .routes.editor import editor_bp
    from .routes.marketing import marketing_bp
    from .routes.public import public_bp
    from .routes.support import support_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(marketing_bp)
    app.register_blueprint(support_bp)

    from .cli import register_cli
    register_cli(app)

    # Exentar endpoints AJAX del CSRF cuando usan JSON
    csrf.exempt(analytics_bp)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """Sirve archivos subidos por nombre aleatorio desde el directorio controlado."""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.before_request
    def enforce_company_app_key():
        if not current_user.is_authenticated or current_user.is_superuser:
            return None

        allowed_endpoints = {
            'static',
            'auth.login',
            'auth.logout',
            'companies.edit',
            'uploaded_file',
        }
        if request.endpoint in allowed_endpoints or (request.endpoint or '').startswith('support.'):
            return None

        from .models.company import Company
        from .services.app_key_service import company_has_valid_app_key

        if not current_user.empresa_id:
            return None

        company = db.session.get(Company, current_user.empresa_id)
        if company_has_valid_app_key(company, app.config.get('SECRET_KEY')):
            return None

        flash('APP-Key inválida, vencida o pendiente. Las funciones quedan bloqueadas hasta capturar una clave correcta.', 'danger')
        return redirect(url_for('companies.edit', company_id=current_user.empresa_id))

    # Context processors — variables globales para templates
    @app.context_processor
    def inject_globals():
        from flask_login import current_user as cu
        from .models.company import Company
        from .services.image_service import favicon_path_for_logo, image_url

        empresa_actual = None
        empresa_nombre = app.config.get('COMPANY_NAME', 'Bitácora')
        empresa_logo_url = None
        empresa_favicon_url = url_for('static', filename='img/logo.png')

        if cu.is_authenticated:
            empresa_id = None
            if hasattr(cu, 'is_superuser') and cu.is_superuser:
                empresa_id = session.get('empresa_id')
            else:
                empresa_id = cu.empresa_id

            if empresa_id:
                empresa_actual = db.session.get(Company, empresa_id)
                if empresa_actual:
                    empresa_nombre = empresa_actual.nombre
                    if empresa_actual.logo_path:
                        empresa_logo_url = image_url(empresa_actual.logo_path)
                        favicon_path = favicon_path_for_logo(empresa_actual.logo_path)
                        if favicon_path:
                            empresa_favicon_url = image_url(favicon_path)

        return {
            'app_name': empresa_nombre,
            'empresa_actual': empresa_actual,
            'empresa_logo_url': empresa_logo_url,
            'empresa_favicon_url': empresa_favicon_url,
        }

    return app
