# -*- coding: utf-8 -*-
"""
Configuración de la aplicación.
Separada en clases para facilitar el cambio entre entornos.
Soporta SQLite (desarrollo) y PostgreSQL (producción).
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(os.path.dirname(basedir), 'instance')


class Config:
    """Configuración base."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bitacora-secret-key-change-in-production')

    # Base de datos — PostgreSQL en producción, SQLite en desarrollo
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(instance_dir, "bitacora.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

    # Flask-Mail defaults (se sobrescriben con config de empresa)
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = 'noreply@bitacora.app'


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
