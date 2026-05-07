"""add company app key

Revision ID: 9f2b6d4a7c31
Revises: 8554c8404497
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f2b6d4a7c31'
down_revision = '8554c8404497'
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
        if 'app_key' not in columns:
            batch_op.add_column(sa.Column('app_key', sa.String(length=27), nullable=True))
        if 'ix_companies_app_key' not in indexes:
            batch_op.create_index(batch_op.f('ix_companies_app_key'), ['app_key'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'companies' not in inspector.get_table_names():
        return

    columns = [column['name'] for column in inspector.get_columns('companies')]
    indexes = [index['name'] for index in inspector.get_indexes('companies')]
    with op.batch_alter_table('companies', schema=None) as batch_op:
        if 'ix_companies_app_key' in indexes:
            batch_op.drop_index(batch_op.f('ix_companies_app_key'))
        if 'app_key' in columns:
            batch_op.drop_column('app_key')
