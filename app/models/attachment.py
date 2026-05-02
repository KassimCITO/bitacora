# -*- coding: utf-8 -*-
"""
Modelo de Archivos Adjuntos.
"""
from datetime import datetime, timezone
from ..extensions import db


class Attachment(db.Model):
    """Archivo adjunto asociado a una tarea."""
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(500), nullable=False)
    tipo_mime = db.Column(db.String(100))
    tamano = db.Column(db.Integer)  # Bytes
    fecha_subida = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relación con usuario
    usuario = db.relationship('User', backref='attachments')

    def __repr__(self):
        return f'<Attachment {self.nombre_archivo}>'
