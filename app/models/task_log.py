# -*- coding: utf-8 -*-
"""
Modelo de Bitácora de Avances (TaskLog).
CORE del sistema — registro inmutable de avances por tarea.
"""
from datetime import datetime, timezone
from ..extensions import db


class TaskLog(db.Model):
    """
    Registro histórico de avances por tarea.
    IMPORTANTE: Solo INSERT, nunca UPDATE ni DELETE.
    Cada entrada es un snapshot del avance en un momento dado.
    """
    __tablename__ = 'task_logs'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comentario = db.Column(db.Text, nullable=False)
    porcentaje_avance = db.Column(db.Integer, nullable=False, default=0)
    fecha_hora = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __repr__(self):
        return f'<TaskLog task={self.task_id} avance={self.porcentaje_avance}%>'
