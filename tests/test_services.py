# -*- coding: utf-8 -*-
"""
Tests adicionales para Bitácora SaaS by KzmCITO - Kassim Assad Mosri Rodríguez.
Cubre: Servicios, CRUD, Seguridad y Edge Cases.
Ejecutar con: python -m pytest tests/ -v --cov=app
"""
import pytest
import sys
import os
import re
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db as _db
from app.models.user import User, Role
from app.models.company import Company
from app.models.group import Group
from app.models.task import Task
from app.models.task_log import TaskLog
from app.models.attachment import Attachment
from app.models.marketing import MarketingAudienceContact, MarketingCampaign, MarketingCronJob
from app.models.support import SupportMessage, SupportThread


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


class TestFiscalPDFService:
    def test_extract_constancia_data_from_metadata_text(self, tmp_path):
        from app.services.fiscal_pdf_service import extract_constancia_fiscal_data

        constancia = tmp_path / 'constancia.pdf'
        constancia.write_text(
            """
            Constancia de Situación Fiscal
            RFC: ABC010203AB1
            Denominación/Razón Social: SERVICIOS INDUSTRIALES DEL CENTRO SA DE CV
            Régimen Fiscal: Régimen General de Ley Personas Morales
            Domicilio Fiscal: AV REFORMA 123, CENTRO, CUAUHTEMOC, CIUDAD DE MEXICO, 06000
            """,
            encoding='utf-8',
        )

        data = extract_constancia_fiscal_data(str(constancia))

        assert data['rfc'] == 'ABC010203AB1'
        assert data['razon_social'] == 'SERVICIOS INDUSTRIALES DEL CENTRO SA DE CV'
        assert 'REFORMA 123' in data['direccion']
        assert data['regimen_fiscal'] == 'Régimen General de Ley Personas Morales'

    def test_extract_persona_fisica_constancia_data(self, tmp_path):
        from app.services.fiscal_pdf_service import extract_constancia_fiscal_data

        constancia = tmp_path / 'persona_fisica.pdf'
        constancia.write_text(
            """
            CONSTANCIA DE SITUACIÓN FISCAL
            MORK680308PZ7
            Registro Federal de Contribuyentes
            KASSIM ASSAD MOSRI
            RODRIGUEZ
            Nombre, denominación o razón
            social
            Datos de Identificación del Contribuyente:
            RFC: MORK680308PZ7
            CURP: MORK680308HMNSDS06
            Nombre (s): KASSIM ASSAD
            Primer Apellido: MOSRI
            Segundo Apellido: RODRIGUEZ
            Datos del domicilio registrado
            Código Postal:60600 Tipo de Vialidad: CALLE
            Nombre de Vialidad: HERIBERTO JARA OTE Número Exterior: 121
            Número Interior: Nombre de la Colonia: APATZINGAN DE LA CONSTITUCION CENTRO
            Nombre de la Localidad: APATZINGAN DE LA CONSTITUCION Nombre del Municipio o Demarcación Territorial: APATZINGAN
            Nombre de la Entidad Federativa: MICHOACAN DE OCAMPO Entre Calle: LIC MANUEL DE ALDERETE Y SORIA
            Regímenes:
            Régimen Fecha Inicio Fecha Fin
            Régimen de las Personas Físicas con Actividades Empresariales y Profesionales 01/01/2014
            Obligaciones:
            """,
            encoding='utf-8',
        )

        data = extract_constancia_fiscal_data(str(constancia))

        assert data['rfc'] == 'MORK680308PZ7'
        assert data['razon_social'] == 'KASSIM ASSAD MOSRI RODRIGUEZ'
        assert '60600' in data['direccion']
        assert 'HERIBERTO JARA OTE' in data['direccion']
        assert data['regimen_fiscal'] == 'Régimen de las Personas Físicas con Actividades Empresariales y Profesionales'

    def test_image_only_constancia_returns_recovery_message(self, tmp_path, monkeypatch):
        from app.services import fiscal_pdf_service

        monkeypatch.setattr(fiscal_pdf_service.shutil, 'which', lambda _: None)
        constancia = tmp_path / 'escaneada.pdf'
        constancia.write_bytes(
            b'%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\nendobj\n%%EOF'
        )

        data = fiscal_pdf_service.extract_constancia_fiscal_data(str(constancia))

        assert data['__error_code__'] == 'unreadable_pdf'
        assert 'escaneada' in data['__error__'] or 'imagen' in data['__error__']
        assert 'PDF original del SAT' in data['__error__']


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

    def test_task_list_strips_rich_text_preview(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea nogroup').first()
            task.descripcion = '<p>Cliente <strong>VIP</strong></p>'
            _db.session.commit()

            response = client.get('/tasks/')
            body = response.data.decode('utf-8')

            assert response.status_code == 200
            assert 'Cliente VIP' in body
            assert '<strong>VIP</strong>' not in body

    def test_task_detail_shows_elapsed_between_logs(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A1 Editada').first() or Task.query.filter_by(nombre='Tarea A1').first()

            response = client.get(f'/tasks/{task.id}')
            body = response.data.decode('utf-8')

            assert response.status_code == 200
            assert 'para realizar avance' in body

    def test_task_image_attachment_preview_gallery(self, client, init_db, app, tmp_path):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A1 Editada').first() or Task.query.filter_by(nombre='Tarea A1').first()
            user = User.query.filter_by(username='admin_a').first()
            image_path = tmp_path / 'preview.png'
            image_path.write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04'
                b'\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            attachment = Attachment(
                task_id=task.id,
                usuario_id=user.id,
                nombre_archivo='preview.png',
                ruta_archivo=str(image_path),
                tipo_mime='image/png',
                tamano=image_path.stat().st_size,
            )
            _db.session.add(attachment)
            _db.session.commit()

            detail = client.get(f'/tasks/{task.id}')
            preview = client.get(f'/tasks/{task.id}/preview/{attachment.id}')

            assert detail.status_code == 200
            assert 'taskGalleryModal' in detail.data.decode('utf-8')
            assert 'task-image-thumb' in detail.data.decode('utf-8')
            assert preview.status_code == 200
            assert preview.content_type.startswith('image/png')

    def test_task_image_attachment_delete_button_removes_image(self, client, init_db, app, tmp_path):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A1 Editada').first() or Task.query.filter_by(nombre='Tarea A1').first()
            user = User.query.filter_by(username='admin_a').first()
            image_path = tmp_path / 'delete-me.png'
            image_path.write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04'
                b'\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            attachment = Attachment(
                task_id=task.id,
                usuario_id=user.id,
                nombre_archivo='delete-me.png',
                ruta_archivo=str(image_path),
                tipo_mime='image/png',
                tamano=image_path.stat().st_size,
            )
            _db.session.add(attachment)
            _db.session.commit()
            attachment_id = attachment.id

            detail = client.get(f'/tasks/{task.id}')
            response = client.post(
                f'/tasks/{task.id}/delete-image/{attachment_id}',
                follow_redirects=True,
            )

            assert 'bi-trash3' in detail.data.decode('utf-8')
            assert response.status_code == 200
            assert _db.session.get(Attachment, attachment_id) is None
            assert not image_path.exists()


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


class TestMarketingCRUD:
    def test_create_marketing_campaign_with_rich_text(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            user = User.query.filter_by(username='usr_a').first()

            response = client.post('/marketing/create', data={
                'nombre': 'Campaña Marketplace',
                'responsable_id': str(user.id),
                'estado': 'planeacion',
                'canal': 'marketplace',
                'prioridad': 'alta',
                'presupuesto': '1500',
                'fecha_inicio': '2026-05-01T10:00',
                'fecha_fin': '2026-05-20T18:00',
                'objetivo': '<p>Subir ventas <strong>20%</strong></p>',
                'audiencia': '<p>Clientes B2B</p>',
                'mensaje': '<p>Oferta principal</p>',
                'notas': '<p><a class="pdf-viewer-link" data-pdf-url="/uploads/test.pdf" href="/uploads/test.pdf"><span class="pdf-viewer-icon"></span><span class="pdf-viewer-copy"><span class="pdf-viewer-kicker">Documento PDF</span><span class="pdf-viewer-name">brief.pdf</span></span></a></p>',
            }, follow_redirects=True)

            campaign = MarketingCampaign.query.filter_by(nombre='Campaña Marketplace').first()
            assert response.status_code == 200
            assert campaign is not None
            assert campaign.canal == 'marketplace'
            assert '<strong>20%</strong>' in campaign.objetivo
            assert 'pdf-viewer-name' in campaign.notas

    def test_marketing_list_preview_strips_html(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            response = client.get('/marketing/')
            body = response.data.decode('utf-8')

            assert response.status_code == 200
            assert 'Subir ventas 20%' in body
            assert '<strong>20%</strong>' not in body

    def test_marketing_imports_facebook_csv_contacts(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            campaign = MarketingCampaign.query.filter_by(nombre='Campaña Marketplace').first()
            if campaign is None:
                user = User.query.filter_by(username='usr_a').first()
                campaign = MarketingCampaign(
                    nombre='Campaña Marketplace',
                    canal='marketplace',
                    estado='planeacion',
                    prioridad='alta',
                    responsable_id=user.id,
                    creado_por_id=user.id,
                    empresa_id=user.empresa_id,
                )
                _db.session.add(campaign)
                _db.session.commit()
            csv_data = (
                'User Id,User Name,Profile URL,Profile Picture,Biography,Is Verified,Friendship Status,Join Status Text,Scraped At\n'
                '100089577999353,Sandy Moreno,https://www.facebook.com/sandy.moreno.734193,https://example.com/p.jpg,Apatzingán de la Constitución,NO,CANNOT_REQUEST,Se unió el lunes,2025-04-30T18:45:30.617Z\n'
            )

            response = client.post(
                '/marketing/import',
                data={
                    'campaign_id': str(campaign.id),
                    'csv_file': (BytesIO(csv_data.encode('utf-8')), 'facebook.csv'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            contact = MarketingAudienceContact.query.filter_by(external_user_id='100089577999353').first()
            assert response.status_code == 200
            assert contact is not None
            assert contact.user_name == 'Sandy Moreno'
            assert contact.campaign_id == campaign.id

    def test_marketing_ai_suggest_returns_field_and_budget(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})

            response = client.post('/marketing/api/ai-suggest', json={
                'nombre': 'Lanzamiento ecommerce premium',
                'canal': 'ads',
                'prioridad': 'alta',
                'field': 'objetivo',
            })
            data = response.get_json()

            assert response.status_code == 200
            assert data['field'] == 'objetivo'
            assert data['suggested_budget'] == 16000
            assert 'Objetivo comercial' in data['content_html']
            assert data['ai_used'] is False

    def test_marketing_contacts_management_view_and_edit(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            campaign = MarketingCampaign.query.filter_by(nombre='Campaña Marketplace').first()
            creator = User.query.filter_by(username='admin_a').first()
            if campaign is None:
                campaign = MarketingCampaign(
                    nombre='Campaña Marketplace',
                    canal='marketplace',
                    estado='planeacion',
                    prioridad='alta',
                    responsable_id=creator.id,
                    creado_por_id=creator.id,
                    empresa_id=creator.empresa_id,
                )
                _db.session.add(campaign)
                _db.session.commit()

            contact = MarketingAudienceContact(
                empresa_id=creator.empresa_id,
                campaign_id=campaign.id,
                source='facebook_csv',
                external_user_id='contact-edit-test',
                user_name='Contacto Editable',
                biography='Lead con interes comercial',
            )
            _db.session.add(contact)
            _db.session.commit()

            list_response = client.get('/marketing/contacts')
            body = list_response.data.decode('utf-8')
            assert list_response.status_code == 200
            assert 'marketing-audience-stats' in body
            assert 'Contacto Editable' in body
            assert 'Consent. pendiente' in body

            edit_page = client.get(f'/marketing/contacts/{contact.id}/edit')
            assert edit_page.status_code == 200
            assert 'Editar contacto importado' in edit_page.data.decode('utf-8')

            edit_response = client.post(f'/marketing/contacts/{contact.id}/edit', data={
                'user_name': 'Contacto Calificado',
                'campaign_id': str(campaign.id),
                'consent_status': 'consentido',
                'profile_url': 'https://example.com/perfil',
                'profile_picture': '',
                'biography': 'Lead validado para campaña',
                'friendship_status': 'CAN_REQUEST',
                'join_status_text': 'Se unió recientemente',
                'is_verified': '1',
            }, follow_redirects=True)
            _db.session.refresh(contact)

            assert edit_response.status_code == 200
            assert contact.user_name == 'Contacto Calificado'
            assert contact.consent_status == 'consentido'
            assert contact.is_verified is True

    def test_marketing_cron_job_runner_completes_one_time_job(self, app, init_db):
        with app.app_context():
            from datetime import datetime, timedelta
            from app.services.marketing_service import run_due_marketing_jobs

            campaign = MarketingCampaign.query.filter_by(nombre='Campaña Marketplace').first()
            if campaign is None:
                creator = User.query.filter_by(username='admin_a').first()
                campaign = MarketingCampaign(
                    nombre='Campaña Marketplace',
                    canal='marketplace',
                    estado='planeacion',
                    prioridad='alta',
                    responsable_id=creator.id,
                    creado_por_id=creator.id,
                    empresa_id=creator.empresa_id,
                )
                _db.session.add(campaign)
                _db.session.commit()
            creator = User.query.filter_by(username='admin_a').first()
            job = MarketingCronJob(
                nombre='Publicación test',
                empresa_id=campaign.empresa_id,
                campaign_id=campaign.id,
                creado_por_id=creator.id,
                plataforma='whatsapp',
                contenido='Oferta programada',
                next_run_at=datetime.utcnow() - timedelta(minutes=1),
                status='activo',
            )
            _db.session.add(job)
            _db.session.commit()

            processed = run_due_marketing_jobs()
            _db.session.refresh(job)

            assert any(item['id'] == job.id for item in processed)
            assert job.status == 'completado'
            assert 'Contenido preparado' in job.last_result


class TestSupportChat:
    def test_user_opens_support_chat_and_uploads_file(self, client, init_db, app):
        with app.app_context():
            company = Company.query.filter_by(nombre='Empresa A').first()
            company.support_whatsapp_phone = '5215512345678'
            _db.session.commit()

            client.get('/logout')
            client.post('/login', data={'username': 'usr_a', 'password': 'test123'})
            response = client.post('/support/create', data={
                'subject': 'No puedo generar reporte',
                'priority': 'alta',
                'body': 'Necesito ayuda con un PDF.',
            }, follow_redirects=True)

            thread = SupportThread.query.filter_by(subject='No puedo generar reporte').first()
            assert response.status_code == 200
            assert thread is not None
            assert thread.whatsapp_phone == '5215512345678'

            upload = client.post(
                f'/support/{thread.id}/messages',
                data={
                    'body': 'Adjunto evidencia.',
                    'files': (BytesIO(b'evidencia'), 'evidencia.txt'),
                },
                content_type='multipart/form-data',
            )

            assert upload.status_code == 200
            assert SupportMessage.query.filter_by(thread_id=thread.id).count() == 2


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

    def test_superuser_create_company_with_csf_generates_app_key(self, client, init_db, app):
        with app.app_context():
            from app.services.app_key_service import generate_app_key

            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            fake_pdf = BytesIO(
                b"""
                Constancia de Situacion Fiscal
                RFC: NEW010203AB7
                Denominacion/Razon Social: NUEVA FISCAL SA DE CV
                Regimen Fiscal: Regimen General de Ley Personas Morales
                Domicilio Fiscal: AV NUEVA 10, CENTRO, CDMX, 06000
                """
            )

            response = client.post(
                '/companies/create',
                data={
                    'nombre': 'Nueva con CSF',
                    'mail_port': '587',
                    'constancia_fiscal': (fake_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=False,
            )

            assert response.status_code == 302
            c = Company.query.filter_by(nombre='Nueva con CSF').first()
            assert c is not None
            assert c.rfc == 'NEW010203AB7'
            assert c.razon_social == 'NUEVA FISCAL SA DE CV'
            assert c.app_key_expires_at is not None
            assert c.app_key == generate_app_key(c.razon_social, app.config['SECRET_KEY'], c.app_key_expires_at)
            assert f'/companies/{c.id}/edit' in response.headers['Location']

    def test_superuser_create_rejects_non_pdf_csf(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})

            response = client.post(
                '/companies/create',
                data={
                    'nombre': 'No Debe Crear',
                    'mail_port': '587',
                    'constancia_fiscal': (BytesIO(b'RFC: BAD010203AB1'), 'constancia.txt'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 400
            assert 'La CSF debe ser un archivo PDF válido' in response.data.decode('utf-8')
            assert Company.query.filter_by(nombre='No Debe Crear').first() is None

    def test_switch_company(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            response = client.post(f'/companies/{c.id}/switch', follow_redirects=True)
            assert response.status_code == 200

    def test_edit_company_uses_constancia_fiscal_data(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            fake_pdf = BytesIO(
                b"""
                Constancia de Situacion Fiscal
                RFC: FIS010203AB9
                Denominacion/Razon Social: FISCAL REAL SA DE CV
                Regimen Fiscal: Regimen General de Ley Personas Morales
                Domicilio Fiscal: CALLE SAT 45, CENTRO, MONTERREY, NUEVO LEON, 64000
                """
            )

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (fake_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert c.rfc == 'FIS010203AB9'
            assert c.razon_social == 'FISCAL REAL SA DE CV'
            assert 'CALLE SAT 45' in c.direccion
            assert c.regimen_fiscal == 'Regimen General de Ley Personas Morales'
            assert c.app_key is None
            c.rfc = 'EMPA010101AAA'
            c.razon_social = None
            c.direccion = None
            c.regimen_fiscal = None
            c.constancia_fiscal_path = None
            _db.session.commit()

    def test_invalid_csf_pdf_shows_error(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            bad_pdf = BytesIO(b'')

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (bad_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 400
            assert 'No se pudo procesar la CSF' in response.data.decode('utf-8')
            _db.session.refresh(c)
            assert c.constancia_fiscal_path is None

    def test_unreadable_csf_does_not_reuse_existing_fiscal_data(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa B').first()
            c.rfc = 'OLD010203AB1'
            c.razon_social = 'DATOS VIEJOS SA DE CV'
            c.constancia_fiscal_path = None
            _db.session.commit()

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (BytesIO(b'PDF sin datos SAT'), 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 400
            assert 'No se detectó RFC ni razón social fiscal' in response.data.decode('utf-8')
            _db.session.refresh(c)
            assert c.rfc == 'OLD010203AB1'
            assert c.razon_social == 'DATOS VIEJOS SA DE CV'
            assert c.constancia_fiscal_path is None

    def test_csf_without_fiscal_identity_is_rejected_and_preserves_data(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            c.rfc = 'KEEP010203AB1'
            c.razon_social = 'DATOS ORIGINALES SA DE CV'
            _db.session.commit()

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (BytesIO(b'PDF sin datos fiscales suficientes'), 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 400
            assert 'No se detectó RFC ni razón social fiscal' in response.data.decode('utf-8')
            _db.session.refresh(c)
            assert c.rfc == 'KEEP010203AB1'
            assert c.razon_social == 'DATOS ORIGINALES SA DE CV'

    def test_image_only_csf_shows_actionable_recovery_message(self, client, init_db, app, monkeypatch):
        with app.app_context():
            from app.services import fiscal_pdf_service

            monkeypatch.setattr(fiscal_pdf_service.shutil, 'which', lambda _: None)
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            image_pdf = BytesIO(
                b'%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\nendobj\n%%EOF'
            )

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (image_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            body = response.data.decode('utf-8')
            assert response.status_code == 400
            assert 'No se pudo procesar la CSF' in body
            assert 'escaneada' in body or 'imagen' in body
            assert 'PDF original del SAT' in body

    def test_superuser_csf_upload_redirects_back_to_edit(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa A').first()
            fake_pdf = BytesIO(
                b"""
                Constancia de Situacion Fiscal
                RFC: REDIRECT010203ABA
                Denominacion/Razon Social: REDIRECT PRUEBA SA DE CV
                Regimen Fiscal: Regimen General de Ley Personas Morales
                Domicilio Fiscal: CALLE REDIRECT 123, CENTRO, CIUDAD, 00000
                """
            )

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (fake_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert f'/companies/{c.id}/edit' in response.headers['Location']

    def test_superuser_csf_upload_generates_app_key(self, client, init_db, app):
        with app.app_context():
            from app.services.app_key_service import generate_app_key

            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})
            c = Company.query.filter_by(nombre='Empresa B').first()
            fake_pdf = BytesIO(
                b"""
                Constancia de Situacion Fiscal
                RFC: KEY010203AB8
                Denominacion/Razon Social: CLIENTE CON LICENCIA SA DE CV
                Regimen Fiscal: Regimen General de Ley Personas Morales
                Domicilio Fiscal: AV LICENCIA 100, GUADALAJARA, JALISCO, 44100
                """
            )

            response = client.post(
                f'/companies/{c.id}/edit',
                data={
                    'nombre': c.nombre,
                    'mail_port': '587',
                    'constancia_fiscal': (fake_pdf, 'constancia.pdf'),
                },
                content_type='multipart/form-data',
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert c.app_key is not None
            assert c.app_key_valid_days == 365
            assert c.app_key_issued_at is not None
            assert c.app_key_expires_at is not None
            assert re.fullmatch(r'KMR-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}', c.app_key)
            assert c.app_key == generate_app_key(c.razon_social, app.config['SECRET_KEY'], c.app_key_expires_at)

    def test_superuser_app_key_preview_uses_days(self, client, init_db, app):
        with app.app_context():
            client.get('/logout')
            client.post('/login', data={'username': 'su2', 'password': 'test123'})

            short = client.post('/companies/app-key/preview', json={
                'razon_social': 'CLIENTE PREVIEW SA DE CV',
                'app_key_valid_days': 30,
            })
            long = client.post('/companies/app-key/preview', json={
                'razon_social': 'CLIENTE PREVIEW SA DE CV',
                'app_key_valid_days': 365,
            })

            assert short.status_code == 200
            assert long.status_code == 200
            assert short.json['app_key'] != long.json['app_key']
            assert short.json['valid_days'] == 30
            assert long.json['valid_days'] == 365

    def test_invalid_app_key_blocks_app_until_correct_key(self, client, init_db, app):
        with app.app_context():
            from app.services.app_key_service import build_app_key_window, generate_app_key

            c = Company.query.filter_by(nombre='Empresa A').first()
            c.razon_social = 'EMPRESA A FISCAL SA DE CV'
            c.app_key = 'KMR-XXXXX-XXXXX-XXXXX-XXXXX'
            c.app_key_issued_at, c.app_key_expires_at, c.app_key_valid_days = build_app_key_window(365)
            _db.session.commit()

            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            blocked = client.get('/tasks/')
            assert blocked.status_code == 302
            assert f'/companies/{c.id}/edit' in blocked.headers['Location']

            c.razon_social = None
            c.app_key = None
            c.app_key_issued_at = None
            c.app_key_expires_at = None
            _db.session.commit()

            valid_key = generate_app_key(c.razon_social, app.config['SECRET_KEY'], c.app_key_expires_at)
            response = client.post(f'/companies/{c.id}/edit', data={
                'nombre': c.nombre,
                'representante_legal': '',
                'telefono': '',
                'email_contacto': '',
                'sitio_web': '',
                'mail_port': '587',
                'app_key': valid_key.lower(),
            }, follow_redirects=True)
            assert response.status_code == 200
            assert c.app_key == valid_key

            allowed = client.get('/tasks/')
            assert allowed.status_code == 200

    def test_expired_app_key_blocks_app(self, client, init_db, app):
        with app.app_context():
            from datetime import datetime, timezone, timedelta
            from app.services.app_key_service import generate_app_key

            c = Company.query.filter_by(nombre='Empresa A').first()
            c.razon_social = 'EMPRESA A FISCAL SA DE CV'
            c.app_key_issued_at = datetime.now(timezone.utc) - timedelta(days=10)
            c.app_key_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            c.app_key_valid_days = 9
            c.app_key = generate_app_key(c.razon_social, app.config['SECRET_KEY'], c.app_key_expires_at)
            _db.session.commit()

            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            blocked = client.get('/tasks/')

            assert blocked.status_code == 302
            assert f'/companies/{c.id}/edit' in blocked.headers['Location']

            c.razon_social = None
            c.app_key = None
            c.app_key_issued_at = None
            c.app_key_expires_at = None
            _db.session.commit()

    def test_invalid_submitted_app_key_does_not_save_changes(self, client, init_db, app):
        with app.app_context():
            c = Company.query.filter_by(nombre='Empresa A').first()
            c.razon_social = 'EMPRESA A FISCAL SA DE CV'
            c.app_key = None
            c.telefono = '111'
            _db.session.commit()

            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            response = client.post(f'/companies/{c.id}/edit', data={
                'nombre': c.nombre,
                'representante_legal': '',
                'telefono': '999',
                'email_contacto': '',
                'sitio_web': '',
                'mail_port': '587',
                'app_key': 'KMR-XXXXX-XXXXX-XXXXX-XXXXX',
            }, follow_redirects=True)

            assert response.status_code == 400
            assert 'APP-Key incorrecta' in response.data.decode('utf-8')
            _db.session.refresh(c)
            assert c.app_key is None
            assert c.telefono == '111'

            c.razon_social = None
            c.telefono = ''
            c.app_key = None
            c.app_key_issued_at = None
            c.app_key_expires_at = None
            _db.session.commit()


# ===== Tests de Seguridad =====

class TestSecurity:
    def test_login_missing_csrf_redirects_with_friendly_message(self, client, init_db, app):
        with app.app_context():
            previous = app.config.get('WTF_CSRF_ENABLED')
            app.config['WTF_CSRF_ENABLED'] = True
            try:
                response = client.post('/login', data={
                    'username': 'admin_a',
                    'password': 'test123',
                }, follow_redirects=True)
                body = response.data.decode('utf-8')
                assert response.status_code == 200
                assert 'La sesión de acceso expiró' in body
                assert 'CSRF session token is missing' not in body
            finally:
                app.config['WTF_CSRF_ENABLED'] = previous

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

    def test_whatsapp_share_uses_bitacora_brand_context(self, client, init_db, app):
        with app.app_context():
            import urllib.parse

            client.get('/logout')
            client.post('/login', data={'username': 'admin_a', 'password': 'test123'})
            task = Task.query.filter_by(nombre='Tarea A2').first()

            response = client.get(f'/reports/share/whatsapp/{task.id}', follow_redirects=False)
            location = response.headers['Location']
            decoded = urllib.parse.unquote(location)

            assert response.status_code == 302
            assert 'Bitácora SaaS - PC y Sistemas Mosri' in decoded
            assert '📎' in decoded


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
