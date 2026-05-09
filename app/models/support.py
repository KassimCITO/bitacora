# -*- coding: utf-8 -*-
"""Modelos para chat de soporte técnico."""
from datetime import datetime, timezone

from ..extensions import db


class SupportThread(db.Model):
    """Conversación de ayuda por empresa."""
    __tablename__ = 'support_threads'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(180), nullable=False)
    status = db.Column(db.String(24), nullable=False, default='abierto', index=True)
    priority = db.Column(db.String(16), nullable=False, default='media', index=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    assigned_superuser_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    whatsapp_phone = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    empresa = db.relationship('Company', backref='support_threads')
    user = db.relationship('User', foreign_keys=[user_id], backref='support_threads')
    assigned_superuser = db.relationship('User', foreign_keys=[assigned_superuser_id])
    messages = db.relationship(
        'SupportMessage',
        backref='thread',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='SupportMessage.created_at.asc()',
    )

    STATUS = [
        ('abierto', 'Abierto'),
        ('en_revision', 'En revisión'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]

    PRIORITIES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    STATUS_BADGES = {
        'abierto': 'success',
        'en_revision': 'warning',
        'resuelto': 'primary',
        'cerrado': 'secondary',
    }

    @property
    def status_label(self):
        return dict(self.STATUS).get(self.status, self.status)

    @property
    def priority_label(self):
        return dict(self.PRIORITIES).get(self.priority, self.priority)

    @property
    def status_badge(self):
        return self.STATUS_BADGES.get(self.status, 'secondary')

    def __repr__(self):
        return f'<SupportThread {self.id}: {self.subject}>'


class SupportMessage(db.Model):
    """Mensaje dentro de una conversación de soporte."""
    __tablename__ = 'support_messages'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('support_threads.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_staff = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship('User', backref='support_messages')
    attachments = db.relationship(
        'SupportAttachment',
        backref='message',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='SupportAttachment.fecha_subida.asc()',
    )

    def __repr__(self):
        return f'<SupportMessage thread={self.thread_id} user={self.user_id}>'


class SupportAttachment(db.Model):
    """Archivo adjunto a un mensaje de soporte."""
    __tablename__ = 'support_attachments'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('support_messages.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(500), nullable=False)
    tipo_mime = db.Column(db.String(100), nullable=True)
    tamano = db.Column(db.Integer, nullable=True)
    fecha_subida = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship('User', backref='support_attachments')

    def __repr__(self):
        return f'<SupportAttachment {self.nombre_archivo}>'
