"""support chat and marketing automation

Revision ID: e4f1c2d3b5a6
Revises: c9d2e7a5b6f1
Create Date: 2026-05-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4f1c2d3b5a6'
down_revision = 'c9d2e7a5b6f1'
branch_labels = None
depends_on = None


def _columns(inspector, table):
    if table not in inspector.get_table_names():
        return []
    return [column['name'] for column in inspector.get_columns(table)]


def _indexes(inspector, table):
    if table not in inspector.get_table_names():
        return []
    return [index['name'] for index in inspector.get_indexes(table)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'companies' in tables:
        company_columns = _columns(inspector, 'companies')
        with op.batch_alter_table('companies', schema=None) as batch_op:
            if 'support_whatsapp_phone' not in company_columns:
                batch_op.add_column(sa.Column('support_whatsapp_phone', sa.String(length=32), nullable=True))

    if 'marketing_campaigns' in tables:
        campaign_columns = _columns(inspector, 'marketing_campaigns')
        with op.batch_alter_table('marketing_campaigns', schema=None) as batch_op:
            if 'url_destino' not in campaign_columns:
                batch_op.add_column(sa.Column('url_destino', sa.String(length=500), nullable=True))
            if 'copy_rrss' not in campaign_columns:
                batch_op.add_column(sa.Column('copy_rrss', sa.Text(), nullable=True))
            if 'hashtags' not in campaign_columns:
                batch_op.add_column(sa.Column('hashtags', sa.String(length=300), nullable=True))
            if 'plataformas' not in campaign_columns:
                batch_op.add_column(sa.Column('plataformas', sa.String(length=200), nullable=True))
            if 'ad_objective' not in campaign_columns:
                batch_op.add_column(sa.Column('ad_objective', sa.String(length=80), nullable=True))
            if 'ai_assets' not in campaign_columns:
                batch_op.add_column(sa.Column('ai_assets', sa.JSON(), nullable=True))

    if 'support_threads' not in tables:
        op.create_table(
            'support_threads',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('subject', sa.String(length=180), nullable=False),
            sa.Column('status', sa.String(length=24), nullable=False),
            sa.Column('priority', sa.String(length=16), nullable=False),
            sa.Column('empresa_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('assigned_superuser_id', sa.Integer(), nullable=True),
            sa.Column('whatsapp_phone', sa.String(length=32), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['assigned_superuser_id'], ['users.id']),
            sa.ForeignKeyConstraint(['empresa_id'], ['companies.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_support_threads_created_at'), 'support_threads', ['created_at'], unique=False)
        op.create_index(op.f('ix_support_threads_empresa_id'), 'support_threads', ['empresa_id'], unique=False)
        op.create_index(op.f('ix_support_threads_priority'), 'support_threads', ['priority'], unique=False)
        op.create_index(op.f('ix_support_threads_status'), 'support_threads', ['status'], unique=False)
        op.create_index(op.f('ix_support_threads_updated_at'), 'support_threads', ['updated_at'], unique=False)
        op.create_index(op.f('ix_support_threads_user_id'), 'support_threads', ['user_id'], unique=False)

    if 'support_messages' not in tables:
        op.create_table(
            'support_messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('thread_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('is_staff', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['thread_id'], ['support_threads.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_support_messages_created_at'), 'support_messages', ['created_at'], unique=False)
        op.create_index(op.f('ix_support_messages_is_staff'), 'support_messages', ['is_staff'], unique=False)
        op.create_index(op.f('ix_support_messages_thread_id'), 'support_messages', ['thread_id'], unique=False)

    if 'support_attachments' not in tables:
        op.create_table(
            'support_attachments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('nombre_archivo', sa.String(length=255), nullable=False),
            sa.Column('ruta_archivo', sa.String(length=500), nullable=False),
            sa.Column('tipo_mime', sa.String(length=100), nullable=True),
            sa.Column('tamano', sa.Integer(), nullable=True),
            sa.Column('fecha_subida', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['message_id'], ['support_messages.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_support_attachments_fecha_subida'), 'support_attachments', ['fecha_subida'], unique=False)
        op.create_index(op.f('ix_support_attachments_message_id'), 'support_attachments', ['message_id'], unique=False)

    if 'marketing_audience_contacts' not in tables:
        op.create_table(
            'marketing_audience_contacts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('empresa_id', sa.Integer(), nullable=False),
            sa.Column('campaign_id', sa.Integer(), nullable=True),
            sa.Column('source', sa.String(length=40), nullable=False),
            sa.Column('external_user_id', sa.String(length=80), nullable=True),
            sa.Column('user_name', sa.String(length=180), nullable=False),
            sa.Column('profile_url', sa.String(length=500), nullable=True),
            sa.Column('profile_picture', sa.String(length=800), nullable=True),
            sa.Column('biography', sa.Text(), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=False),
            sa.Column('friendship_status', sa.String(length=80), nullable=True),
            sa.Column('join_status_text', sa.String(length=180), nullable=True),
            sa.Column('scraped_at', sa.DateTime(), nullable=True),
            sa.Column('consent_status', sa.String(length=24), nullable=False),
            sa.Column('raw_payload', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['campaign_id'], ['marketing_campaigns.id']),
            sa.ForeignKeyConstraint(['empresa_id'], ['companies.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_marketing_audience_contacts_campaign_id'), 'marketing_audience_contacts', ['campaign_id'], unique=False)
        op.create_index(op.f('ix_marketing_audience_contacts_consent_status'), 'marketing_audience_contacts', ['consent_status'], unique=False)
        op.create_index(op.f('ix_marketing_audience_contacts_created_at'), 'marketing_audience_contacts', ['created_at'], unique=False)
        op.create_index(op.f('ix_marketing_audience_contacts_empresa_id'), 'marketing_audience_contacts', ['empresa_id'], unique=False)
        op.create_index(op.f('ix_marketing_audience_contacts_external_user_id'), 'marketing_audience_contacts', ['external_user_id'], unique=False)
        op.create_index(op.f('ix_marketing_audience_contacts_source'), 'marketing_audience_contacts', ['source'], unique=False)

    if 'marketing_cron_jobs' not in tables:
        op.create_table(
            'marketing_cron_jobs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=180), nullable=False),
            sa.Column('empresa_id', sa.Integer(), nullable=False),
            sa.Column('campaign_id', sa.Integer(), nullable=True),
            sa.Column('creado_por_id', sa.Integer(), nullable=False),
            sa.Column('plataforma', sa.String(length=40), nullable=False),
            sa.Column('contenido', sa.Text(), nullable=False),
            sa.Column('url_destino', sa.String(length=500), nullable=True),
            sa.Column('interval_minutes', sa.Integer(), nullable=True),
            sa.Column('next_run_at', sa.DateTime(), nullable=False),
            sa.Column('last_run_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=24), nullable=False),
            sa.Column('last_result', sa.Text(), nullable=True),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['campaign_id'], ['marketing_campaigns.id']),
            sa.ForeignKeyConstraint(['creado_por_id'], ['users.id']),
            sa.ForeignKeyConstraint(['empresa_id'], ['companies.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_marketing_cron_jobs_campaign_id'), 'marketing_cron_jobs', ['campaign_id'], unique=False)
        op.create_index(op.f('ix_marketing_cron_jobs_created_at'), 'marketing_cron_jobs', ['created_at'], unique=False)
        op.create_index(op.f('ix_marketing_cron_jobs_empresa_id'), 'marketing_cron_jobs', ['empresa_id'], unique=False)
        op.create_index(op.f('ix_marketing_cron_jobs_next_run_at'), 'marketing_cron_jobs', ['next_run_at'], unique=False)
        op.create_index(op.f('ix_marketing_cron_jobs_plataforma'), 'marketing_cron_jobs', ['plataforma'], unique=False)
        op.create_index(op.f('ix_marketing_cron_jobs_status'), 'marketing_cron_jobs', ['status'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    for table, indexes in [
        ('marketing_cron_jobs', [
            'ix_marketing_cron_jobs_status',
            'ix_marketing_cron_jobs_plataforma',
            'ix_marketing_cron_jobs_next_run_at',
            'ix_marketing_cron_jobs_empresa_id',
            'ix_marketing_cron_jobs_created_at',
            'ix_marketing_cron_jobs_campaign_id',
        ]),
        ('marketing_audience_contacts', [
            'ix_marketing_audience_contacts_source',
            'ix_marketing_audience_contacts_external_user_id',
            'ix_marketing_audience_contacts_empresa_id',
            'ix_marketing_audience_contacts_created_at',
            'ix_marketing_audience_contacts_consent_status',
            'ix_marketing_audience_contacts_campaign_id',
        ]),
        ('support_attachments', [
            'ix_support_attachments_message_id',
            'ix_support_attachments_fecha_subida',
        ]),
        ('support_messages', [
            'ix_support_messages_thread_id',
            'ix_support_messages_is_staff',
            'ix_support_messages_created_at',
        ]),
        ('support_threads', [
            'ix_support_threads_user_id',
            'ix_support_threads_updated_at',
            'ix_support_threads_status',
            'ix_support_threads_priority',
            'ix_support_threads_empresa_id',
            'ix_support_threads_created_at',
        ]),
    ]:
        if table in tables:
            existing = _indexes(inspector, table)
            with op.batch_alter_table(table, schema=None) as batch_op:
                for index in indexes:
                    if index in existing:
                        batch_op.drop_index(op.f(index))
            op.drop_table(table)

    if 'marketing_campaigns' in tables:
        campaign_columns = _columns(inspector, 'marketing_campaigns')
        with op.batch_alter_table('marketing_campaigns', schema=None) as batch_op:
            for column in ['ai_assets', 'ad_objective', 'plataformas', 'hashtags', 'copy_rrss', 'url_destino']:
                if column in campaign_columns:
                    batch_op.drop_column(column)

    if 'companies' in tables and 'support_whatsapp_phone' in _columns(inspector, 'companies'):
        with op.batch_alter_table('companies', schema=None) as batch_op:
            batch_op.drop_column('support_whatsapp_phone')
