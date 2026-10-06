"""sesion_dispositivo

Sesiones por dispositivo con token de acceso corto y token de renovación (AC-14 a AC-24):
tabla `sesion_dispositivo`, con la huella del token de renovación (nunca el token), la familia
del dispositivo, la ventana renovable, el tope absoluto y el motivo de revocación.

Revision ID: 0005_sesion_dispositivo
Revises: 0004_puestos_dotacion
Create Date: 2026-10-06 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0005_sesion_dispositivo'
down_revision: str | None = '0004_puestos_dotacion'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FECHA = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')


def upgrade() -> None:
    op.create_table('sesion_dispositivo',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('familia_id', sa.Uuid(), nullable=False),
    sa.Column('refresh_hash', sa.String(length=64), nullable=False),
    sa.Column('version_sesion', sa.Integer(), nullable=False),
    sa.Column('creado_en', FECHA, nullable=False),
    sa.Column('inicio', FECHA, nullable=False),
    sa.Column('ultimo_uso', FECHA, nullable=False),
    sa.Column('expira_en', FECHA, nullable=False),
    sa.Column('vence_absoluto', FECHA, nullable=False),
    sa.Column('revocada_en', FECHA, nullable=True),
    sa.Column('motivo_revocacion', sa.String(length=30), nullable=True),
    sa.Column('reemplazada_por', sa.Uuid(), nullable=True),
    sa.Column('agente', sa.String(length=120), nullable=True),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_sesion_dispositivo_usuario_id_usuario'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sesion_dispositivo')),
    sa.UniqueConstraint('refresh_hash', name=op.f('uq_sesion_dispositivo_refresh_hash'))
    )
    op.create_index(op.f('ix_sesion_dispositivo_usuario_id'), 'sesion_dispositivo', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_sesion_dispositivo_familia_id'), 'sesion_dispositivo', ['familia_id'], unique=False)
    op.create_index(op.f('ix_sesion_dispositivo_vence_absoluto'), 'sesion_dispositivo', ['vence_absoluto'], unique=False)


def downgrade() -> None:
    # Al borrar la tabla se van sus índices y la llave foránea (el índice de `usuario_id` no se
    # puede quitar solo: la llave foránea lo usa).
    op.drop_table('sesion_dispositivo')
