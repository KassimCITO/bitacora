# -*- coding: utf-8 -*-
"""
Modelo de Tarea.
Soporta multi-tenant (empresa_id) y agrupación (grupo_id).
"""
from datetime import datetime, timezone
from ..extensions import db


class Task(db.Model):
    """Tarea operativa con seguimiento detallado."""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_hora_inicio = db.Column(db.DateTime, nullable=False)
    fecha_hora_fin_estimada = db.Column(db.DateTime, nullable=True)
    fecha_hora_fin_real = db.Column(db.DateTime, nullable=True)

    # Estado: pendiente, en_progreso, pausada, terminada, cancelada
    estado = db.Column(db.String(20), nullable=False, default='pendiente', index=True)

    # Prioridad: baja, media, alta
    prioridad = db.Column(db.String(10), nullable=False, default='media', index=True)

    # Relaciones con usuarios
    usuario_asignado_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Multi-tenant
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)

    # Agrupación (opcional)
    grupo_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True, index=True)

    # Timestamps
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ultima_actualizacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relaciones
    logs = db.relationship(
        'TaskLog', backref='task', lazy='dynamic',
        order_by='TaskLog.fecha_hora.desc()'
    )
    attachments = db.relationship('Attachment', backref='task', lazy='dynamic')

    # Constantes para estados y prioridades
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('pausada', 'Pausada'),
        ('terminada', 'Terminada'),
        ('cancelada', 'Cancelada'),
    ]

    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]

    ESTADO_BADGES = {
        'pendiente': 'warning',
        'en_progreso': 'info',
        'pausada': 'secondary',
        'terminada': 'success',
        'cancelada': 'danger',
    }

    PRIORIDAD_BADGES = {
        'baja': 'success',
        'media': 'warning',
        'alta': 'danger',
    }

    @property
    def estado_label(self):
        """Devuelve el label legible del estado."""
        return dict(self.ESTADOS).get(self.estado, self.estado)

    @property
    def prioridad_label(self):
        """Devuelve el label legible de la prioridad."""
        return dict(self.PRIORIDADES).get(self.prioridad, self.prioridad)

    @property
    def estado_badge(self):
        """Clase CSS del badge para el estado."""
        return self.ESTADO_BADGES.get(self.estado, 'secondary')

    @property
    def prioridad_badge(self):
        """Clase CSS del badge para la prioridad."""
        return self.PRIORIDAD_BADGES.get(self.prioridad, 'secondary')

    @property
    def ultimo_avance(self):
        """Porcentaje del último avance registrado."""
        last_log = self.logs.order_by(None).order_by(
            db.text('fecha_hora DESC')
        ).first()
        return last_log.porcentaje_avance if last_log else 0

    def __repr__(self):
        return f'<Task {self.id}: {self.nombre}>'
