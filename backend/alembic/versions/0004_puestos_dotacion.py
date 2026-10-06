"""puestos_dotacion

FEAT-003: catálogo de puestos (`puesto`), dotación recomendada por puesto (`dotacion`) y la
referencia `periodo_contrato.puesto_id`. El texto `periodo_contrato.puesto` se conserva. Los
periodos que ya existían se relacionan con el catálogo por nombre; como el catálogo nace vacío,
quedan con `puesto_id` nulo (sin dotación) hasta que se capture el puesto.

Revision ID: 0004_puestos_dotacion
Revises: 0003_huella_cuerpo
Create Date: 2026-10-05 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0004_puestos_dotacion'
down_revision: str | None = '0003_huella_cuerpo'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('puesto',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_puesto')),
    sa.UniqueConstraint('nombre', name=op.f('uq_puesto_nombre'))
    )
    op.create_table('dotacion',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('puesto_id', sa.Uuid(), nullable=False),
    sa.Column('articulo_id', sa.Uuid(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.CheckConstraint('cantidad >= 1', name=op.f('ck_dotacion_cantidad_positiva')),
    sa.ForeignKeyConstraint(['articulo_id'], ['articulo.id'], name=op.f('fk_dotacion_articulo_id_articulo')),
    sa.ForeignKeyConstraint(['puesto_id'], ['puesto.id'], name=op.f('fk_dotacion_puesto_id_puesto')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dotacion')),
    sa.UniqueConstraint('puesto_id', 'articulo_id', name=op.f('uq_dotacion_puesto_id_articulo_id'))
    )
    op.create_index('ix_dotacion_articulo_id', 'dotacion', ['articulo_id'], unique=False)

    op.add_column('periodo_contrato', sa.Column('puesto_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_periodo_contrato_puesto_id_puesto'), 'periodo_contrato', 'puesto', ['puesto_id'], ['id'])
    op.create_index('ix_periodo_contrato_puesto_id', 'periodo_contrato', ['puesto_id'], unique=False)
    # Relaciona los periodos viejos con el catálogo por nombre (la colación ignora mayúsculas y
    # acentos). Con el catálogo recién creado no hay coincidencias; queda por si la migración se
    # corre después de cargar puestos a mano.
    op.execute(
        "UPDATE periodo_contrato pc JOIN puesto p ON p.nombre = pc.puesto "
        "SET pc.puesto_id = p.id WHERE pc.puesto_id IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_periodo_contrato_puesto_id_puesto'), 'periodo_contrato', type_='foreignkey')
    op.drop_index('ix_periodo_contrato_puesto_id', table_name='periodo_contrato')
    op.drop_column('periodo_contrato', 'puesto_id')
    op.drop_table('dotacion')
    op.drop_table('puesto')
