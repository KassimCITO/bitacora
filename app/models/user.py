# -*- coding: utf-8 -*-
"""
Modelos de Usuario y Rol.
Soporta multi-tenant (empresa_id) y rol superuser global.
"""
from datetime import datetime, timezone
from flask_login import UserMixin
import bcrypt
from ..extensions import db


class Role(db.Model):
    """Roles del sistema: superuser, administrador, manager, usuario, visor."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    # Relación
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


class User(db.Model, UserMixin):
    """Modelo de usuario con autenticación, control de roles y multi-tenant."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Multi-tenant: empresa a la que pertenece (NULL para superuser global)
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)

    # Relaciones
    tareas_asignadas = db.relationship(
        'Task', foreign_keys='Task.usuario_asignado_id',
        backref='usuario_asignado', lazy='dynamic'
    )
    tareas_creadas = db.relationship(
        'Task', foreign_keys='Task.creado_por_id',
        backref='creador', lazy='dynamic'
    )
    logs = db.relationship('TaskLog', backref='usuario', lazy='dynamic')
    # 'groups' backref definido en Group model via user_groups

    def set_password(self, password):
        """Hash de contraseña con bcrypt."""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        """Verifica la contraseña contra el hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    @property
    def is_active(self):
        return self.activo

    @property
    def is_superuser(self):
        """Verifica si es superusuario global."""
        return self.role.name == 'superuser'

    def has_role(self, *roles):
        """Verifica si el usuario tiene alguno de los roles indicados."""
        return self.role.name in roles

    def __repr__(self):
        return f'<User {self.username}>'
