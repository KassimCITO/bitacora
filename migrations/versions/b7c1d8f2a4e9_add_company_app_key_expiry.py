"""add company app key expiry

Revision ID: b7c1d8f2a4e9
Revises: 9f2b6d4a7c31
Create Date: 2026-05-07 00:00:00.000000

"""
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c1d8f2a4e9'
down_revision = '9f2b6d4a7c31'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'companies' not in inspector.get_table_names():
        return

    columns = [column['name'] for column in inspector.get_columns('companies')]
    indexes = [index['name'] for index in inspector.get_indexes('companies')]

    with op.batch_alter_table('companies', schema=None) as batch_op:
        if 'app_key_valid_days' not in columns:
            batch_op.add_column(sa.Column('app_key_valid_days', sa.Integer(), nullable=False, server_default='365'))
        if 'app_key_issued_at' not in columns:
            batch_op.add_column(sa.Column('app_key_issued_at', sa.DateTime(), nullable=True))
        if 'app_key_expires_at' not in columns:
            batch_op.add_column(sa.Column('app_key_expires_at', sa.DateTime(), nullable=True))
        if 'ix_companies_app_key_expires_at' not in indexes:
            batch_op.create_index(batch_op.f('ix_companies_app_key_expires_at'), ['app_key_expires_at'], unique=False)

    issued_at = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).replace(tzinfo=None)
    companies = sa.table(
        'companies',
        sa.column('app_key', sa.String(length=27)),
        sa.column('app_key_valid_days', sa.Integer()),
        sa.column('app_key_issued_at', sa.DateTime()),
        sa.column('app_key_expires_at', sa.DateTime()),
    )
    bind.execute(
        companies.update()
        .where(companies.c.app_key.isnot(None))
        .where(companies.c.app_key_issued_at.is_(None))
        .values(
            app_key_valid_days=365,
            app_key_issued_at=issued_at,
            app_key_expires_at=expires_at,
        )
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'companies' not in inspector.get_table_names():
        return

    columns = [column['name'] for column in inspector.get_columns('companies')]
    indexes = [index['name'] for index in inspector.get_indexes('companies')]

    with op.batch_alter_table('companies', schema=None) as batch_op:
        if 'ix_companies_app_key_expires_at' in indexes:
            batch_op.drop_index(batch_op.f('ix_companies_app_key_expires_at'))
        if 'app_key_expires_at' in columns:
            batch_op.drop_column('app_key_expires_at')
        if 'app_key_issued_at' in columns:
            batch_op.drop_column('app_key_issued_at')
        if 'app_key_valid_days' in columns:
            batch_op.drop_column('app_key_valid_days')
