# -*- coding: utf-8 -*-
"""
Modelo de Empresa (Company).
Entidad raíz del sistema multi-tenant SaaS.
Cada empresa tiene su propia configuración de SMTP, IA, y datos fiscales.
"""
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from flask import current_app
from ..extensions import db


class Company(db.Model):
    """Empresa — unidad de negocio en el modelo SaaS multi-tenant."""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)

    # --- Información General ---
    nombre = db.Column(db.String(200), nullable=False)
    representante_legal = db.Column(db.String(200), nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    email_contacto = db.Column(db.String(150), nullable=True)
    sitio_web = db.Column(db.String(250), nullable=True)
    logo_path = db.Column(db.String(500), nullable=True)

    # --- Información Fiscal ---
    rfc = db.Column(db.String(20), nullable=True)
    razon_social = db.Column(db.String(300), nullable=True)
    regimen_fiscal = db.Column(db.String(200), nullable=True)
    constancia_fiscal_path = db.Column(db.String(500), nullable=True)  # PDF adjunto

    # --- Configuración SMTP (cifrado en BD) ---
    mail_server = db.Column(db.String(200), nullable=True)
    mail_port = db.Column(db.Integer, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_use_ssl = db.Column(db.Boolean, default=False)
    mail_username = db.Column(db.String(200), nullable=True)
    _mail_password = db.Column('mail_password', db.Text, nullable=True)
    mail_default_sender = db.Column(db.String(200), nullable=True)

    # --- Configuración IA (cifrado en BD) ---
    ai_provider = db.Column(db.String(50), nullable=True)  # openai | gemini | anthropic
    _ai_api_key = db.Column('ai_api_key', db.Text, nullable=True)
    ai_model = db.Column(db.String(100), nullable=True)

    # --- Metadata ---
    activa = db.Column(db.Boolean, default=True, nullable=False)
    plan_suscripcion = db.Column(db.String(50), default='free')
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ultima_actualizacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # --- Relaciones ---
    users = db.relationship('User', backref='empresa', lazy='dynamic')
    groups = db.relationship('Group', backref='empresa', lazy='dynamic',
                             cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='empresa', lazy='dynamic')

    # Proveedores IA soportados
    AI_PROVIDERS = [
        ('openai', 'OpenAI (GPT)'),
        ('gemini', 'Google Gemini'),
        ('anthropic', 'Anthropic (Claude)'),
    ]

    PLANES = [
        ('free', 'Gratuito'),
        ('basic', 'Básico'),
        ('pro', 'Profesional'),
        ('enterprise', 'Empresarial'),
    ]

    # --- Cifrado / Descifrado de credenciales ---

    @staticmethod
    def _get_fernet():
        """Obtiene la instancia de Fernet para cifrado/descifrado."""
        key = current_app.config.get('ENCRYPTION_KEY', '')
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            return None

    @staticmethod
    def _encrypt(value):
        """Cifra un valor sensible."""
        if not value:
            return None
        f = Company._get_fernet()
        if f:
            return f.encrypt(value.encode('utf-8')).decode('utf-8')
        return value

    @staticmethod
    def _decrypt(value):
        """Descifra un valor sensible."""
        if not value:
            return None
        f = Company._get_fernet()
        if f:
            try:
                return f.decrypt(value.encode('utf-8')).decode('utf-8')
            except Exception:
                return value
        return value

    @property
    def mail_password(self):
        """Descifra y retorna la contraseña SMTP."""
        return self._decrypt(self._mail_password)

    @mail_password.setter
    def mail_password(self, value):
        """Cifra y almacena la contraseña SMTP."""
        self._mail_password = self._encrypt(value)

    @property
    def ai_api_key(self):
        """Descifra y retorna la API key de IA."""
        return self._decrypt(self._ai_api_key)

    @ai_api_key.setter
    def ai_api_key(self, value):
        """Cifra y almacena la API key de IA."""
        self._ai_api_key = self._encrypt(value)

    @property
    def ai_provider_label(self):
        """Retorna el label legible del proveedor IA."""
        return dict(self.AI_PROVIDERS).get(self.ai_provider, self.ai_provider or '—')

    def get_mail_config(self):
        """Retorna la configuración SMTP como diccionario."""
        return {
            'MAIL_SERVER': self.mail_server or 'localhost',
            'MAIL_PORT': self.mail_port or 587,
            'MAIL_USE_TLS': self.mail_use_tls,
            'MAIL_USE_SSL': self.mail_use_ssl,
            'MAIL_USERNAME': self.mail_username or '',
            'MAIL_PASSWORD': self.mail_password or '',
            'MAIL_DEFAULT_SENDER': self.mail_default_sender or 'noreply@bitacora.app',
        }

    def __repr__(self):
        return f'<Company {self.nombre}>'
