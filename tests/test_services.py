# -*- coding: utf-8 -*-
"""
Tests adicionales para Bitácora SaaS.
Cubre: Servicios, CRUD, Seguridad y Edge Cases.
Ejecutar con: python -m pytest tests/ -v --cov=app
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db as _db
from app.models.user import User, Role
from app.models.company import Company
from app.models.group import Group
from app.models.task import Task
from app.models.task_log import TaskLog
from app.models.attachment import Attachment


@pytest.fixture(scope='module')
def app():
    app = create_app('testing')
    return app


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


@pytest.fixture(scope='module')
def init_db(app):
    with app.app_context():
        _db.create_all()

        # Roles
        roles = {}
        for name in ['superuser', 'administrador', 'manager', 'usuario', 'visor']:
            role = Role(name=name, description=f'Rol {name}')
            _db.session.add(role)
            roles[name] = role
        _db.session.commit()

        # Companies
        company_a = Company(nombre='Empresa A', rfc='EMPA010101AAA')
        company_b = Company(nombre='Empresa B', rfc='EMPB010101BBB')
        _db.session.add_all([company_a, company_b])
        _db.session.commit()

        # Superuser
        su = User(username='su2', email='su2@test.com', nombre_completo='Super 2',
                  role_id=roles['superuser'].id)
        su.set_password('test123')
        _db.session.add(su)

        # Users empresa A
        admin_a = User(username='admin_a', email='admin_a@test.com', nombre_completo='Admin A',
                       role_id=roles['administrador'].id, empresa_id=company_a.id)
        admin_a.set_password('test123')

        mgr_a = User(username='mgr_a', email='mgr_a@test.com', nombre_completo='Manager A',
                     role_id=roles['manager'].id, empresa_id=company_a.id)
        mgr_a.set_password('test123')

        usr_a = User(username='usr_a', email='usr_a@test.com', nombre_completo='User A',
                     role_id=roles['usuario'].id, empresa_id=company_a.id)
        usr_a.set_password('test123')

        visor_a = User(username='visor_a', email='visor_a@test.com', nombre_completo='Visor A',
                       role_id=roles['visor'].id, empresa_id=company_a.id)
        visor_a.set_password('test123')

        # User empresa B
        usr_b = User(username='usr_b', email='usr_b@test.com', nombre_completo='User B',
                     role_id=roles['usuario'].id, empresa_id=company_b.id)
        usr_b.set_password('test123')

        # Inactive user
        inactive = User(username='inactive_u', email='inactive@test.com',
                        nombre_completo='Inactive', role_id=roles['usuario'].id,
                        empresa_id=company_a.id, activo=False)
        inactive.set_password('test123')

        _db.session.add_all([admin_a, mgr_a, usr_a, visor_a, usr_b, inactive])
        _db.session.commit()

        # Group
        group_a = Group(nombre='Dev A', descripcion='Devs', color='#00d4aa',
                        empresa_id=company_a.id)
        _db.session.add(group_a)
        _db.session.commit()
        group_a.members.append(usr_a)
        _db.session.commit()

        # Tasks
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        task1 = Task(nombre='Tarea A1', descripcion='<p>Desc A1</p>', estado='en_progreso',
                     prioridad='alta', usuario_asignado_id=usr_a.id, creado_por_id=mgr_a.id,
                     empresa_id=company_a.id, grupo_id=group_a.id,
                     fecha_hora_inicio=now - timedelta(days=3),
                     fecha_hora_fin_estimada=now + timedelta(days=7))
        task2 = Task(nombre='Tarea A2', descripcion='<p>Desc A2</p>', estado='terminada',
                     prioridad='media', usuario_asignado_id=usr_a.id, creado_por_id=admin_a.id,
                     empresa_id=company_a.id, fecha_hora_inicio=now - timedelta(days=10),
                     fecha_hora_fin_estimada=now - timedelta(days=2),
                     fecha_hora_fin_real=now - timedelta(days=1))
        task3 = Task(nombre='Tarea nogroup', descripcion='Sin grupo', estado='pendiente',
                     prioridad='baja', usuario_asignado_id=usr_a.id, creado_por_id=mgr_a.id,
                     empresa_id=company_a.id, fecha_hora_inicio=now)

        _db.session.add_all([task1, task2, task3])
        _db.session.commit()

        log1 = TaskLog(task_id=task1.id, usuario_id=usr_a.id, comentario='Inicio',
                       porcentaje_avance=30)
        log2 = TaskLog(task_id=task2.id, usuario_id=usr_a.id, comentario='Completada',
                       porcentaje_avance=100)
        _db.session.add_all([log1, log2])
        _db.session.commit()

        yield _db
        _db.drop_all()


# ===== Tests de Servicios =====

class TestPDFService:
    def test_generate_task_pdf(self, app, init_db):
        with app.app_context():
            from app.services.pdf_service import generate_task_report
            task = Task.query.filter_by(nombre='Tarea A1').first()
            pdf = generate_task_report(task, company_name='Test Corp')
            assert isinstance(pdf, bytes)
            assert pdf[:5] == b'%PDF-'
            assert len(pdf) > 500

    def test_generate_range_pdf(self, app, init_db):
        with app.app_context():
            from app.services.pdf_service import generate_range_report
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            tasks = Task.query.filter_by(empresa_id=1).all()
            pdf = generate_range_report(tasks, now - timedelta(days=30), now,
                                        company_name='Test Corp')
            assert isinstance(pdf, bytes)
            assert pdf[:5] == b'%PDF-'


class TestExportService:
    def test_csv_export(self, app, init_db):
        with app.app_context():
            from app.services.export_service import export_tasks_csv
            tasks = Task.query.filter_by(empresa_id=1).all()
            csv_data = export_tasks_csv(tasks)
            assert 'ID' in csv_data
            assert 'Nombre' in csv_data
            assert 'Tarea A1' in csv_data

    def test_csv_empty(self, app, init_db):
        with app.app_context():
            from app.services.export_service import export_tasks_csv
            csv_data = export_tasks_csv([])
            lines = csv_data.strip().split('\n')
            assert len(lines) == 1  # Solo header


class TestAIFallback:
    def test_fallback_analysis(self, app, init_db):
        with app.app_context():
            from app.services.ai_service import generate_ai_analysis
            result = generate_ai_analysis(1, 'empresa')
            assert 'analysis' in result
            assert 'stats' in result
            assert result['ai_used'] is False
            assert 'resumen' in result['analysis']
            assert 'puntuacion' in result['analysis']

    def test_company_stats(self, app, init_db):
        with app.app_context():
            from app.services.ai_service import get_company_stats
            stats = get_company_stats(1)
            assert stats['total'] >= 3
            assert 'usuarios_activos' in stats

    def test_group_stats(self, app, init_db):
        with app.app_context():
            from app.services.ai_service import get_group_stats
            group = Group.query.first()
            stats = get_group_stats(group.id)
            assert 'nombre_grupo' in stats
            assert stats['total'] >= 1

    def test_user_stats(self, app, init_db):
        with app.app_context():
            from app.services.ai_service import get_user_stats
            user = User.query.filter_by(username='usr_a').first()
            stats = get_user_stats(user.id, 1)
            assert stats['total'] >= 2
            assert 'nombre_usuario' in stats

    def test_invalid_empresa(self, app, init_db):
        with app.app_context():
            from app.services.ai_service import generate_ai_analysis
            result = generate_ai_analysis(9999, 'empresa')
            assert 'error' in result


class TestHelpers:
    def test_allowed_file(self):
        from app.utils.helpers import allowed_file
        assert allowed_file('doc.pdf') is True
        assert allowed_file('img.png') is True
        assert allowed_file('script.exe') is False
        assert allowed_file('noext') is False

    def test_format_datetime(self):
        from app.utils.helpers import format_datetime
        assert format_datetime(None) == '—'
        from datetime import datetime
        dt = datetime(2026, 5, 1, 10, 30)
        assert format_datetime(dt) == '01/05/2026 10:30'

    def test_format_date(self):
        from app.utils.helpers import format_date
        assert format_date(None) == '—'


# ===== Tests CRUD =====

class TestTaskCRUD:
    def test_create_task_post(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'mgr_a', 'password': 'test123'})
            usr = User.query.filter_by(username='usr_a').first()
            response = client.post('/tasks/create', data={
                'nombre': 'Nueva Tarea CRUD',
                'descripcion': '<p>Descripción</p>',
                'fecha_hora_inicio': '2026-05-01T10:00',
                'fecha_hora_fin_estimada': '2026-05-10T18:00',
                'estado': 'pendiente',
                'prioridad': 'media',
                'usuario_asignado_id': str(usr.id),
                'grupo_id': '',
            }, follow_redirects=True)
            assert response.status_code == 200
            task = Task.query.filter_by(nombre='Nueva Tarea CRUD').first()
            assert task is not None

    def test_add_log_post(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'usr_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A1').first()
            response = client.post(f'/tasks/{task.id}/log', data={
                'comentario': 'Avance test',
                'porcentaje_avance': '50',
                'nuevo_estado': '',
            }, follow_redirects=True)
            assert response.status_code == 200

    def test_edit_task(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'mgr_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A1').first()
            usr = User.query.filter_by(username='usr_a').first()
            response = client.post(f'/tasks/{task.id}/edit', data={
                'nombre': 'Tarea A1 Editada',
                'descripcion': '<p>Editada</p>',
                'fecha_hora_inicio': '2026-05-01T10:00',
                'estado': 'en_progreso',
                'prioridad': 'alta',
                'usuario_asignado_id': str(usr.id),
                'grupo_id': '',
            }, follow_redirects=True)
            assert response.status_code == 200


class TestGroupCRUD:
    def test_create_group(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            response = client.post('/groups/create', data={
                'nombre': 'Nuevo Grupo',
                'descripcion': 'Test',
                'color': '#ff5500',
            }, follow_redirects=True)
            assert response.status_code == 200
            g = Group.query.filter_by(nombre='Nuevo Grupo').first()
            assert g is not None

    def test_delete_group(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            g = Group.query.filter_by(nombre='Nuevo Grupo').first()
            response = client.post(f'/groups/{g.id}/delete', follow_redirects=True)
            assert response.status_code == 200


class TestCompanyCRUD:
    def test_superuser_create_company(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            response = client.post('/companies/create', data={
                'nombre': 'Empresa Test CRUD',
                'rfc': 'ETCR010101CCC',
                'mail_port': '587',
            }, follow_redirects=True)
            assert response.status_code == 200

    def test_switch_company(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            response = client.post(f'/companies/{c.id}/switch', follow_redirects=True)
            assert response.status_code == 200


# ===== Tests de Seguridad =====

class TestSecurity:
    def test_visor_cannot_create_task(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'visor_a', 'password': 'test123'})
        response = client.get('/tasks/create')
        assert response.status_code == 403

    def test_user_cannot_access_reports(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'usr_a', 'password': 'test123'})
        response = client.get('/reports/')
        assert response.status_code == 403

    def test_user_cannot_manage_users(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'usr_a', 'password': 'test123'})
        response = client.get('/users/')
        assert response.status_code == 403

    def test_admin_cannot_access_companies(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
        response = client.get('/companies/')
        assert response.status_code == 403

    def test_cross_tenant_task_forbidden(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'usr_b', 'password': 'test123'})
            task_a = Task.query.filter_by(nombre='Tarea A2').first()
            response = client.get(f'/tasks/{task_a.id}')
            assert response.status_code == 403


# ===== Tests Edge Cases =====

class TestEdgeCases:
    def test_login_inactive_user(self, client, init_db):
        client.get('/logout')
        response = client.post('/login', data={
            'username': 'inactive_u', 'password': 'test123'
        }, follow_redirects=True)
        html = response.data.decode('utf-8')
        assert 'desactivada' in html or 'danger' in html

    def test_task_without_group(self, app, init_db):
        with app.app_context():
            task = Task.query.filter_by(nombre='Tarea nogroup').first()
            assert task is not None
            assert task.grupo_id is None

    def test_avance_100_completed(self, app, init_db):
        with app.app_context():
            task = Task.query.filter_by(nombre='Tarea A2').first()
            assert task.ultimo_avance == 100
            assert task.estado == 'terminada'

    def test_calendar_invalid_date(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
        response = client.get('/api/calendar-data?view=monthly&date=invalid')
        assert response.status_code == 200

    def test_calendar_empty_date(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
        response = client.get('/api/calendar-data?view=weekly&date=')
        assert response.status_code == 200

    def test_empty_log_rejected(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'usr_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea nogroup').first()
            response = client.post(f'/tasks/{task.id}/log', data={
                'comentario': '',
                'porcentaje_avance': '10',
            }, follow_redirects=True)
            assert response.status_code == 200

    def test_task_properties(self, app, init_db):
        with app.app_context():
            task = Task.query.filter_by(nombre='Tarea nogroup').first()
            assert task.estado_label == 'Pendiente'
            assert task.prioridad_label == 'Baja'
            assert task.estado_badge == 'warning'
            assert task.prioridad_badge == 'success'

    def test_sanitizer_xss_attributes(self):
        from app.utils.sanitizer import sanitize_html
        result = sanitize_html('<p onclick="alert(1)">Hi</p>')
        assert 'onclick' not in result
        assert '<p>' in result
