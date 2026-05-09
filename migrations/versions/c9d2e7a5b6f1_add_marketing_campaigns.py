"""add marketing campaigns

Revision ID: c9d2e7a5b6f1
Revises: b7c1d8f2a4e9
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c9d2e7a5b6f1'
down_revision = 'b7c1d8f2a4e9'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'marketing_campaigns' in inspector.get_table_names():
        return

    op.create_table(
        'marketing_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('objetivo', sa.Text(), nullable=True),
        sa.Column('audiencia', sa.Text(), nullable=True),
        sa.Column('mensaje', sa.Text(), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('canal', sa.String(length=40), nullable=False),
        sa.Column('estado', sa.String(length=24), nullable=False),
        sa.Column('prioridad', sa.String(length=10), nullable=False),
        sa.Column('presupuesto', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('fecha_inicio', sa.DateTime(), nullable=True),
        sa.Column('fecha_fin', sa.DateTime(), nullable=True),
        sa.Column('responsable_id', sa.Integer(), nullable=False),
        sa.Column('creado_por_id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
        sa.Column('ultima_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['creado_por_id'], ['users.id']),
        sa.ForeignKeyConstraint(['empresa_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['responsable_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_marketing_campaigns_canal'), 'marketing_campaigns', ['canal'], unique=False)
    op.create_index(op.f('ix_marketing_campaigns_empresa_id'), 'marketing_campaigns', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_marketing_campaigns_estado'), 'marketing_campaigns', ['estado'], unique=False)
    op.create_index(op.f('ix_marketing_campaigns_prioridad'), 'marketing_campaigns', ['prioridad'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'marketing_campaigns' not in inspector.get_table_names():
        return

    op.drop_index(op.f('ix_marketing_campaigns_prioridad'), table_name='marketing_campaigns')
    op.drop_index(op.f('ix_marketing_campaigns_estado'), table_name='marketing_campaigns')
    op.drop_index(op.f('ix_marketing_campaigns_empresa_id'), table_name='marketing_campaigns')
    op.drop_index(op.f('ix_marketing_campaigns_canal'), table_name='marketing_campaigns')
    op.drop_table('marketing_campaigns')
