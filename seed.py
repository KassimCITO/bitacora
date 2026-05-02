# -*- coding: utf-8 -*-
"""
Script de inicialización de datos.
Crea roles, superuser, empresa demo, grupos y datos de ejemplo.
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.user import Role, User
from app.models.company import Company
from app.models.group import Group
from app.models.task import Task
from app.models.task_log import TaskLog


def seed():
    """Poblar la base de datos con datos iniciales."""
    app = create_app()

    with app.app_context():
        print('🌱 Iniciando seed de la base de datos...')
        db.create_all()
        print('✅ Tablas creadas.')

        # --- Roles ---
        roles_data = [
            ('superuser', 'Administrador global del sistema SaaS'),
            ('administrador', 'Administrador de empresa'),
            ('manager', 'Crear y asignar tareas, generar reportes'),
            ('usuario', 'Ver y actualizar tareas asignadas'),
            ('visor', 'Solo lectura y exportación de reportes'),
        ]
        roles = {}
        for name, desc in roles_data:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.session.add(role)
                print(f'  ➕ Rol creado: {name}')
            roles[name] = role
        db.session.commit()

        # --- Superuser ---
        su = User.query.filter_by(username='superuser').first()
        if not su:
            su = User(
                username='superuser',
                email='super@bitacora.app',
                nombre_completo='Super Administrador',
                role_id=roles['superuser'].id,
                empresa_id=None,
            )
            su.set_password('super123')
            db.session.add(su)
            print('  ➕ Superuser creado: superuser')
        db.session.commit()

        # --- Empresa Demo ---
        company = Company.query.filter_by(nombre='Empresa Demo').first()
        if not company:
            company = Company(
                nombre='Empresa Demo',
                representante_legal='Juan Pérez González',
                direccion='Av. Reforma 123, Col. Centro, CDMX',
                telefono='+52 55 1234 5678',
                email_contacto='contacto@empresademo.com',
                rfc='EDM010101AAA',
                razon_social='Empresa Demo S.A. de C.V.',
                regimen_fiscal='General de Ley',
                mail_server='smtp.gmail.com',
                mail_port=587,
                mail_use_tls=True,
            )
            db.session.add(company)
            db.session.flush()
            print('  ➕ Empresa creada: Empresa Demo')
        db.session.commit()

        # --- Usuarios de empresa ---
        users_data = [
            ('admin', 'admin@bitacora.app', 'admin123', 'Administrador del Sistema', 'administrador'),
            ('manager1', 'manager@bitacora.app', 'manager123', 'Carlos Mendoza', 'manager'),
            ('user1', 'user1@bitacora.app', 'user123', 'Ana García López', 'usuario'),
            ('user2', 'user2@bitacora.app', 'user123', 'Roberto Hernández', 'usuario'),
            ('visor1', 'visor@bitacora.app', 'visor123', 'Laura Martínez', 'visor'),
        ]
        users = {}
        for username, email, password, nombre, role_name in users_data:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username, email=email,
                    nombre_completo=nombre,
                    role_id=roles[role_name].id,
                    empresa_id=company.id,
                )
                user.set_password(password)
                db.session.add(user)
                print(f'  ➕ Usuario creado: {username} ({role_name})')
            users[username] = user
        db.session.commit()

        # --- Grupos ---
        groups_data = [
            ('Gerencia', 'Equipo directivo y toma de decisiones', '#6610f2', ['admin', 'manager1']),
            ('Administración', 'Gestión administrativa y finanzas', '#0dcaf0', ['manager1', 'visor1']),
            ('Programación', 'Equipo de desarrollo de software', '#00d4aa', ['user1', 'user2']),
        ]
        groups = {}
        for g_name, g_desc, g_color, g_members in groups_data:
            group = Group.query.filter_by(nombre=g_name, empresa_id=company.id).first()
            if not group:
                group = Group(nombre=g_name, descripcion=g_desc, color=g_color, empresa_id=company.id)
                db.session.add(group)
                db.session.flush()
                for uname in g_members:
                    if uname in users:
                        group.members.append(users[uname])
                print(f'  ➕ Grupo creado: {g_name}')
            groups[g_name] = group
        db.session.commit()

        # --- Tareas de ejemplo ---
        if Task.query.filter_by(empresa_id=company.id).count() == 0:
            now = datetime.now(timezone.utc)
            tasks_data = [
                {'nombre': 'Revisión de inventario Q2', 'descripcion': 'Conteo físico de inventario del segundo trimestre.', 'estado': 'en_progreso', 'prioridad': 'alta', 'asignado': 'user1', 'creador': 'manager1', 'grupo': 'Administración', 'inicio': now - timedelta(days=5), 'fin_est': now + timedelta(days=10)},
                {'nombre': 'Capacitación nuevo sistema ERP', 'descripcion': 'Sesiones de capacitación para el equipo operativo.', 'estado': 'pendiente', 'prioridad': 'media', 'asignado': 'user2', 'creador': 'manager1', 'grupo': 'Programación', 'inicio': now + timedelta(days=2), 'fin_est': now + timedelta(days=15)},
                {'nombre': 'Auditoría de procesos logísticos', 'descripcion': 'Evaluar procesos actuales de logística interna.', 'estado': 'en_progreso', 'prioridad': 'alta', 'asignado': 'user1', 'creador': 'admin', 'grupo': 'Gerencia', 'inicio': now - timedelta(days=3), 'fin_est': now + timedelta(days=7)},
                {'nombre': 'Mantenimiento preventivo de equipos', 'descripcion': 'Mantenimiento trimestral de los equipos de producción.', 'estado': 'pausada', 'prioridad': 'baja', 'asignado': 'user2', 'creador': 'manager1', 'grupo': 'Administración', 'inicio': now - timedelta(days=10), 'fin_est': now + timedelta(days=5)},
                {'nombre': 'Reporte mensual de operaciones', 'descripcion': 'Compilar métricas operativas y generar reporte ejecutivo.', 'estado': 'terminada', 'prioridad': 'media', 'asignado': 'user1', 'creador': 'manager1', 'grupo': 'Gerencia', 'inicio': now - timedelta(days=15), 'fin_est': now - timedelta(days=2)},
            ]

            for td in tasks_data:
                task = Task(
                    nombre=td['nombre'], descripcion=td['descripcion'],
                    estado=td['estado'], prioridad=td['prioridad'],
                    usuario_asignado_id=users[td['asignado']].id,
                    creado_por_id=users[td['creador']].id,
                    empresa_id=company.id,
                    grupo_id=groups[td['grupo']].id if td.get('grupo') else None,
                    fecha_hora_inicio=td['inicio'],
                    fecha_hora_fin_estimada=td['fin_est'],
                    fecha_hora_fin_real=now - timedelta(days=1) if td['estado'] == 'terminada' else None,
                )
                db.session.add(task)
                db.session.flush()

                log1 = TaskLog(task_id=task.id, usuario_id=users[td['creador']].id, comentario='Tarea creada y asignada.', porcentaje_avance=0, fecha_hora=td['inicio'])
                db.session.add(log1)

                if td['estado'] in ('en_progreso', 'terminada'):
                    log2 = TaskLog(task_id=task.id, usuario_id=users[td['asignado']].id, comentario='Iniciando trabajo. Revisión de documentación previa.', porcentaje_avance=30, fecha_hora=td['inicio'] + timedelta(days=1))
                    db.session.add(log2)
                if td['estado'] == 'terminada':
                    log3 = TaskLog(task_id=task.id, usuario_id=users[td['asignado']].id, comentario='Tarea completada. Reporte entregado.', porcentaje_avance=100, fecha_hora=now - timedelta(days=1))
                    db.session.add(log3)

                print(f'  ➕ Tarea creada: {td["nombre"]}')
            db.session.commit()

        print('\n✅ Seed completado exitosamente!')
        print('\n📋 Credenciales de acceso:')
        print('  Superuser:     superuser / super123')
        print('  Admin:         admin / admin123')
        print('  Manager:       manager1 / manager123')
        print('  Usuario:       user1 / user123')
        print('  Visor:         visor1 / visor123')


if __name__ == '__main__':
    seed()
