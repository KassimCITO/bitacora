# -*- coding: utf-8 -*-
"""
Tests completos para Bitácora SaaS.
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


@pytest.fixture(scope='module')
def app():
    """Crea la aplicación Flask para testing."""
    app = create_app('testing')
    return app


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


@pytest.fixture(scope='module')
def init_db(app):
    """Inicializa la BD con datos multi-tenant."""
    with app.app_context():
        _db.create_all()

        # Roles
        roles = {}
        for name in ['superuser', 'administrador', 'manager', 'usuario', 'visor']:
            role = Role(name=name, description=f'Rol {name}')
            _db.session.add(role)
            roles[name] = role
        _db.session.commit()

        # Company
        company = Company(nombre='Test Corp', rfc='TEST010101AAA')
        _db.session.add(company)
        _db.session.commit()

        # Superuser (no company)
        su = User(username='su_test', email='su@test.com', nombre_completo='Super Test', role_id=roles['superuser'].id)
        su.set_password('test123')
        _db.session.add(su)

        # Admin (with company)
        admin = User(username='admin_test', email='admin@test.com', nombre_completo='Admin Test', role_id=roles['administrador'].id, empresa_id=company.id)
        admin.set_password('test123')
        _db.session.add(admin)

        # User (with company)
        user = User(username='user_test', email='user@test.com', nombre_completo='User Test', role_id=roles['usuario'].id, empresa_id=company.id)
        user.set_password('test123')
        _db.session.add(user)
        _db.session.commit()

        # Group
        group = Group(nombre='Dev Team', descripcion='Developers', color='#00d4aa', empresa_id=company.id)
        _db.session.add(group)
        _db.session.commit()
        group.members.append(user)
        _db.session.commit()

        yield _db
        _db.drop_all()


# ===== Tests de Modelos =====

class TestUserModel:
    def test_password_hashing(self, app, init_db):
        with app.app_context():
            user = User.query.filter_by(username='admin_test').first()
            assert user is not None
            assert user.check_password('test123')
            assert not user.check_password('wrong')

    def test_has_role(self, app, init_db):
        with app.app_context():
            admin = User.query.filter_by(username='admin_test').first()
            assert admin.has_role('administrador')
            assert not admin.has_role('usuario')

    def test_is_superuser(self, app, init_db):
        with app.app_context():
            su = User.query.filter_by(username='su_test').first()
            assert su.is_superuser
            admin = User.query.filter_by(username='admin_test').first()
            assert not admin.is_superuser

    def test_user_empresa(self, app, init_db):
        with app.app_context():
            admin = User.query.filter_by(username='admin_test').first()
            assert admin.empresa_id is not None
            assert admin.empresa.nombre == 'Test Corp'

    def test_superuser_no_empresa(self, app, init_db):
        with app.app_context():
            su = User.query.filter_by(username='su_test').first()
            assert su.empresa_id is None


class TestCompanyModel:
    def test_company_exists(self, app, init_db):
        with app.app_context():
            c = Company.query.first()
            assert c is not None
            assert c.nombre == 'Test Corp'
            assert c.rfc == 'TEST010101AAA'

    def test_company_users(self, app, init_db):
        with app.app_context():
            c = Company.query.first()
            assert c.users.count() >= 2

    def test_ai_provider_label(self, app, init_db):
        with app.app_context():
            c = Company.query.first()
            assert c.ai_provider_label == '—'
            c.ai_provider = 'openai'
            assert c.ai_provider_label == 'OpenAI (GPT)'


class TestGroupModel:
    def test_group_exists(self, app, init_db):
        with app.app_context():
            g = Group.query.first()
            assert g is not None
            assert g.nombre == 'Dev Team'
            assert g.empresa_id is not None

    def test_group_members(self, app, init_db):
        with app.app_context():
            g = Group.query.first()
            assert g.member_count >= 1


class TestTaskModel:
    def test_create_task(self, app, init_db):
        with app.app_context():
            from datetime import datetime, timezone
            admin = User.query.filter_by(username='admin_test').first()
            user = User.query.filter_by(username='user_test').first()
            company = Company.query.first()
            group = Group.query.first()
            task = Task(
                nombre='Tarea test', descripcion='<p>Test</p>',
                estado='pendiente', prioridad='alta',
                usuario_asignado_id=user.id, creado_por_id=admin.id,
                empresa_id=company.id, grupo_id=group.id,
                fecha_hora_inicio=datetime.now(timezone.utc),
            )
            _db.session.add(task)
            _db.session.commit()
            assert task.id is not None
            assert task.empresa_id == company.id
            assert task.grupo_id == group.id
            assert task.estado_label == 'Pendiente'

    def test_task_progress(self, app, init_db):
        with app.app_context():
            task = Task.query.first()
            user = User.query.filter_by(username='user_test').first()
            log = TaskLog(task_id=task.id, usuario_id=user.id, comentario='Test', porcentaje_avance=50)
            _db.session.add(log)
            _db.session.commit()
            assert task.ultimo_avance == 50


# ===== Tests de Autenticación =====

class TestAuth:
    def test_login_page(self, client, init_db):
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_success(self, client, init_db):
        response = client.post('/login', data={'username': 'admin_test', 'password': 'test123'}, follow_redirects=True)
        assert response.status_code == 200

    def test_login_failure(self, client, init_db):
        response = client.post('/login', data={'username': 'admin_test', 'password': 'wrong'}, follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'incorrectos' in html or 'danger' in html

    def test_login_rejects_external_next(self, client, init_db):
        response = client.post(
            '/login?next=https://evil.example/phish',
            data={'username': 'admin_test', 'password': 'test123'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')

    def test_login_rate_limit_after_failed_attempts(self, client, init_db):
        for _ in range(5):
            response = client.post('/login', data={'username': 'locked_test', 'password': 'wrong'})
            assert response.status_code == 200
        response = client.post('/login', data={'username': 'locked_test', 'password': 'wrong'})
        assert response.status_code == 429

    def test_logout(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_superuser_login(self, client, init_db):
        response = client.post('/login', data={'username': 'su_test', 'password': 'test123'}, follow_redirects=True)
        assert response.status_code == 200


# ===== Tests de Sanitización =====

class TestSanitizer:
    def test_sanitize_safe_html(self):
        from app.utils.sanitizer import sanitize_html
        result = sanitize_html('<p>Hola <strong>mundo</strong></p>')
        assert '<p>' in result
        assert '<strong>' in result

    def test_sanitize_removes_script(self):
        from app.utils.sanitizer import sanitize_html
        result = sanitize_html('<p>Hola</p><script>alert("xss")</script>')
        assert '<script>' not in result

    def test_sanitize_empty(self):
        from app.utils.sanitizer import sanitize_html
        assert sanitize_html('') == ''
        assert sanitize_html(None) == ''

    def test_strip_html(self):
        from app.utils.sanitizer import strip_html
        assert strip_html('<p>Hola <strong>mundo</strong></p>') == 'Hola mundo'


# ===== Tests de Rutas =====

class TestRoutes:
    def test_dashboard_requires_login(self, client, init_db):
        client.get('/logout')
        response = client.get('/')
        assert response.status_code == 302

    def test_dashboard_accessible(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/')
        assert response.status_code == 200

    def test_tasks_list(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/tasks/')
        assert response.status_code == 200

    def test_reports_requires_role(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'user_test', 'password': 'test123'})
        response = client.get('/reports/')
        assert response.status_code == 403

    def test_calendar_data(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/api/calendar-data?view=monthly&date=2026-05-01')
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert data['view'] == 'monthly'

    def test_companies_requires_superuser(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/companies/')
        assert response.status_code == 403

    def test_companies_accessible_superuser(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'su_test', 'password': 'test123'})
        response = client.get('/companies/')
        assert response.status_code == 200

    def test_groups_accessible(self, client, init_db):
        client.get('/logout')
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/groups/')
        assert response.status_code == 200

    def test_analytics_accessible(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/analytics/')
        assert response.status_code == 200

    def test_ai_analyze_accepts_empty_json_body(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.post('/analytics/api/ai-analyze')
        assert response.status_code == 200
        data = response.get_json()
        assert data['context_type'] == 'empresa'
        assert 'analysis' in data

    def test_csv_export(self, client, init_db):
        client.post('/login', data={'username': 'admin_test', 'password': 'test123'})
        response = client.get('/api/tasks/export/csv')
        assert response.status_code == 200
        assert 'text/csv' in response.content_type


# ===== Tests Multi-Tenant =====

class TestMultiTenant:
    def test_user_belongs_to_company(self, app, init_db):
        with app.app_context():
            admin = User.query.filter_by(username='admin_test').first()
            company = Company.query.first()
            assert admin.empresa_id == company.id

    def test_task_belongs_to_company(self, app, init_db):
        with app.app_context():
            task = Task.query.first()
            company = Company.query.first()
            assert task.empresa_id == company.id

    def test_group_belongs_to_company(self, app, init_db):
        with app.app_context():
            group = Group.query.first()
            company = Company.query.first()
            assert group.empresa_id == company.id
