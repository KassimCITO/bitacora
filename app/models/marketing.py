# -*- coding: utf-8 -*-
"""Modelo de campañas de Marketing."""
from datetime import datetime, timezone
from ..extensions import db


class MarketingCampaign(db.Model):
    """Campaña o iniciativa de marketing por empresa."""
    __tablename__ = 'marketing_campaigns'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    objetivo = db.Column(db.Text, nullable=True)
    audiencia = db.Column(db.Text, nullable=True)
    mensaje = db.Column(db.Text, nullable=True)
    notas = db.Column(db.Text, nullable=True)
    url_destino = db.Column(db.String(500), nullable=True)
    copy_rrss = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.String(300), nullable=True)
    plataformas = db.Column(db.String(200), nullable=True)
    ad_objective = db.Column(db.String(80), nullable=True)
    ai_assets = db.Column(db.JSON, nullable=True)
    canal = db.Column(db.String(40), nullable=False, default='digital', index=True)
    estado = db.Column(db.String(24), nullable=False, default='planeacion', index=True)
    prioridad = db.Column(db.String(10), nullable=False, default='media', index=True)
    presupuesto = db.Column(db.Numeric(12, 2), nullable=True)
    fecha_inicio = db.Column(db.DateTime, nullable=True)
    fecha_fin = db.Column(db.DateTime, nullable=True)

    responsable_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)

    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ultima_actualizacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    responsable = db.relationship('User', foreign_keys=[responsable_id], backref='marketing_responsable')
    creador = db.relationship('User', foreign_keys=[creado_por_id], backref='marketing_creadas')
    empresa = db.relationship('Company', backref='marketing_campaigns')

    ESTADOS = [
        ('planeacion', 'Planeación'),
        ('activa', 'Activa'),
        ('pausada', 'Pausada'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    CANALES = [
        ('digital', 'Digital'),
        ('redes', 'Redes Sociales'),
        ('email', 'Email Marketing'),
        ('marketplace', 'Marketplace'),
        ('contenido', 'Contenido'),
        ('branding', 'Branding'),
        ('ads', 'Ads Performance'),
        ('offline', 'Offline'),
    ]

    PLATAFORMAS = [
        ('facebook', 'Facebook / Meta'),
        ('instagram', 'Instagram'),
        ('x', 'X / Twitter'),
        ('linkedin', 'LinkedIn'),
        ('google_ads', 'Google Ads'),
        ('whatsapp', 'WhatsApp'),
        ('web', 'Web / Landing'),
    ]

    AD_OBJECTIVES = [
        ('trafico', 'Tráfico web'),
        ('leads', 'Generación de leads'),
        ('conversiones', 'Conversiones'),
        ('alcance', 'Alcance'),
        ('engagement', 'Interacción'),
        ('ventas', 'Ventas'),
    ]

    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]

    ESTADO_BADGES = {
        'planeacion': 'info',
        'activa': 'success',
        'pausada': 'secondary',
        'finalizada': 'primary',
        'cancelada': 'danger',
    }

    PRIORIDAD_BADGES = {
        'baja': 'success',
        'media': 'warning',
        'alta': 'danger',
    }

    @property
    def estado_label(self):
        return dict(self.ESTADOS).get(self.estado, self.estado)

    @property
    def canal_label(self):
        return dict(self.CANALES).get(self.canal, self.canal)

    @property
    def prioridad_label(self):
        return dict(self.PRIORIDADES).get(self.prioridad, self.prioridad)

    @property
    def estado_badge(self):
        return self.ESTADO_BADGES.get(self.estado, 'secondary')

    @property
    def prioridad_badge(self):
        return self.PRIORIDAD_BADGES.get(self.prioridad, 'secondary')

    @property
    def platform_values(self):
        if not self.plataformas:
            return []
        return [item.strip() for item in self.plataformas.split(',') if item.strip()]

    @property
    def platform_labels(self):
        labels = dict(self.PLATAFORMAS)
        return [labels.get(value, value) for value in self.platform_values]

    @property
    def ad_objective_label(self):
        return dict(self.AD_OBJECTIVES).get(self.ad_objective, self.ad_objective or '—')

    def __repr__(self):
        return f'<MarketingCampaign {self.id}: {self.nombre}>'


class MarketingAudienceContact(db.Model):
    """Contacto/importación de audiencia para campañas."""
    __tablename__ = 'marketing_audience_contacts'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=True, index=True)
    source = db.Column(db.String(40), nullable=False, default='facebook_csv', index=True)
    external_user_id = db.Column(db.String(80), nullable=True, index=True)
    user_name = db.Column(db.String(180), nullable=False)
    profile_url = db.Column(db.String(500), nullable=True)
    profile_picture = db.Column(db.String(800), nullable=True)
    biography = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    friendship_status = db.Column(db.String(80), nullable=True)
    join_status_text = db.Column(db.String(180), nullable=True)
    scraped_at = db.Column(db.DateTime, nullable=True)
    consent_status = db.Column(db.String(24), nullable=False, default='pendiente', index=True)
    raw_payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    empresa = db.relationship('Company', backref='marketing_contacts')
    campaign = db.relationship('MarketingCampaign', backref='audience_contacts')

    CONSENT_STATUSES = [
        ('pendiente', 'Pendiente'),
        ('consentido', 'Consentido'),
        ('descartado', 'Descartado'),
    ]

    @property
    def consent_label(self):
        return dict(self.CONSENT_STATUSES).get(self.consent_status, self.consent_status)

    def __repr__(self):
        return f'<MarketingAudienceContact {self.user_name}>'


class MarketingCronJob(db.Model):
    """CronJob para programar contenido o automatizaciones de marketing."""
    __tablename__ = 'marketing_cron_jobs'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=True, index=True)
    creado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plataforma = db.Column(db.String(40), nullable=False, default='web', index=True)
    contenido = db.Column(db.Text, nullable=False)
    url_destino = db.Column(db.String(500), nullable=True)
    interval_minutes = db.Column(db.Integer, nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=False, index=True)
    last_run_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(24), nullable=False, default='activo', index=True)
    last_result = db.Column(db.Text, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    empresa = db.relationship('Company', backref='marketing_cron_jobs')
    campaign = db.relationship('MarketingCampaign', backref='cron_jobs')
    creador = db.relationship('User', backref='marketing_cron_jobs')

    STATUSES = [
        ('activo', 'Activo'),
        ('pausado', 'Pausado'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]

    @property
    def status_label(self):
        return dict(self.STATUSES).get(self.status, self.status)

    def __repr__(self):
        return f'<MarketingCronJob {self.id}: {self.nombre}>'
