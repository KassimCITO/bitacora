# -*- coding: utf-8 -*-
"""
Modelo de Grupo de usuarios.
Permite agrupar usuarios por tarea específica (ej: Gerencia, Programación, etc.)
"""
from datetime import datetime, timezone
from ..extensions import db

# Tabla asociativa many-to-many User <-> Group
user_groups = db.Table(
    'user_groups',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True),
)


class Group(db.Model):
    """Grupo de usuarios dentro de una empresa."""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default='#00d4aa')  # Hex color para calendario
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)

    # Metadata
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    members = db.relationship(
        'User', secondary=user_groups,
        backref=db.backref('groups', lazy='dynamic'),
        lazy='dynamic',
    )
    tasks = db.relationship('Task', backref='grupo', lazy='dynamic')

    @property
    def member_count(self):
        """Número de miembros activos."""
        return self.members.filter_by(activo=True).count()

    def __repr__(self):
        return f'<Group {self.nombre}>'
