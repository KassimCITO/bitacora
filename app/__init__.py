# -*- coding: utf-8 -*-
"""
Bitácora SaaS — Application Factory
Multi-tenant, multi-empresa.
"""
import os
from flask import Flask, session
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(analytics_bp)

    # Exentar endpoints AJAX del CSRF cuando usan JSON
    csrf.exempt(analytics_bp)

    # Context processors — variables globales para templates
    @app.context_processor
    def inject_globals():
        from flask_login import current_user as cu
        from .models.company import Company

        empresa_actual = None
        empresa_nombre = app.config.get('COMPANY_NAME', 'Bitácora')

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

        return {
            'app_name': empresa_nombre,
            'empresa_actual': empresa_actual,
        }

    return app
