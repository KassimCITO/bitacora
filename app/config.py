# -*- coding: utf-8 -*-
"""
Configuración de la aplicación.
Separada en clases para facilitar el cambio entre entornos.
Soporta SQLite (desarrollo) y PostgreSQL (producción).
"""
import os
from pathlib import Path
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = Path(os.path.dirname(basedir)).resolve() / 'instance'


class Config:
    """Configuración base."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bitacora-secret-key-change-in-production')

    # Base de datos — PostgreSQL en producción, SQLite en desarrollo
    default_sqlite_uri = f'sqlite:///{instance_dir.as_posix()}/bitacora.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        default_sqlite_uri
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(basedir), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Clave de cifrado para credenciales sensibles en BD
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'change-me-generate-a-real-fernet-key')

    # Reportes PDF (default, se sobrescribe con datos de empresa)
    COMPANY_NAME = 'Bitácora'
    LOGO_PATH = os.path.join(basedir, 'static', 'img', 'logo.png')

    # Paginación
    TASKS_PER_PAGE = 15
    LOGIN_MAX_FAILED_ATTEMPTS = int(os.environ.get('LOGIN_MAX_FAILED_ATTEMPTS', 5))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get('LOGIN_LOCKOUT_SECONDS', 900))

    # Flask-Mail defaults (se sobrescriben con config de empresa)
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = 'noreply@bitacora.app'

    # Entrada comercial publica
    SALES_LEADS_EMAIL = os.environ.get('SALES_LEADS_EMAIL')
    LEAD_INBOX_PATH = os.environ.get('LEAD_INBOX_PATH')


class DevelopmentConfig(Config):
    """Configuración de desarrollo."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración de producción."""
    DEBUG = False


class TestingConfig(Config):
    """Configuración de testing."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Mapeo de configuraciones
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
