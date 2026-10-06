"""solicitudes_compra

Solicitud de compra urgente: `solicitud_compra`, su historial `solicitud_compra_evento` (solo se
inserta) y el contador de folios por almacén `serie_solicitud_compra`.

Revision ID: 0006_solicitudes_compra
Revises: 0005_sesion_dispositivo
Create Date: 2026-10-06 00:28:04.274690
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0006_solicitudes_compra'
down_revision: str | None = '0005_sesion_dispositivo'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('serie_solicitud_compra',
    sa.Column('almacen_id', sa.Uuid(), nullable=False),
    sa.Column('ultimo', sa.Integer(), nullable=False),
    sa.CheckConstraint('ultimo >= 0', name=op.f('ck_serie_solicitud_compra_ultimo_no_negativo')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_serie_solicitud_compra_almacen_id_almacen')),
    sa.PrimaryKeyConstraint('almacen_id', name=op.f('pk_serie_solicitud_compra'))
    )
    op.create_table('solicitud_compra',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_cliente', sa.Uuid(), nullable=False),
    sa.Column('huella_cuerpo', sa.String(length=64), nullable=False),
    sa.Column('folio', sa.String(length=30), nullable=False),
    sa.Column('almacen_id', sa.Uuid(), nullable=False),
    sa.Column('solicitante_id', sa.Uuid(), nullable=False),
    sa.Column('articulo_id', sa.Uuid(), nullable=True),
    sa.Column('descripcion', sa.String(length=255), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('motivo', sa.String(length=255), nullable=False),
    sa.Column('urgencia', sa.String(length=10), nullable=False),
    sa.Column('estado', sa.String(length=12), nullable=False),
    sa.Column('nota_compras', sa.String(length=500), nullable=True),
    sa.Column('vale_entrada_id', sa.Uuid(), nullable=True),
    sa.Column('creada_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.Column('actualizada_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("descripcion <> ''", name=op.f('ck_solicitud_compra_descripcion_con_texto')),
    sa.CheckConstraint("estado IN ('PENDIENTE', 'EN_COMPRA', 'COMPRADA', 'INGRESADA', 'RECHAZADA', 'CANCELADA')", name=op.f('ck_solicitud_compra_estado')),
    sa.CheckConstraint("urgencia IN ('URGENTE', 'NORMAL')", name=op.f('ck_solicitud_compra_urgencia')),
    sa.CheckConstraint("vale_entrada_id IS NULL OR estado = 'INGRESADA'", name=op.f('ck_solicitud_compra_vale_solo_ingresada')),
    sa.CheckConstraint('cantidad >= 1', name=op.f('ck_solicitud_compra_cantidad_positiva')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_solicitud_compra_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['articulo_id'], ['articulo.id'], name=op.f('fk_solicitud_compra_articulo_id_articulo')),
    sa.ForeignKeyConstraint(['solicitante_id'], ['usuario.id'], name=op.f('fk_solicitud_compra_solicitante_id_usuario')),
    sa.ForeignKeyConstraint(['vale_entrada_id'], ['vale.id'], name=op.f('fk_solicitud_compra_vale_entrada_id_vale')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_solicitud_compra')),
    sa.UniqueConstraint('folio', name=op.f('uq_solicitud_compra_folio')),
    sa.UniqueConstraint('id_cliente', name=op.f('uq_solicitud_compra_id_cliente'))
    )
    op.create_index('ix_solicitud_compra_almacen_id_estado', 'solicitud_compra', ['almacen_id', 'estado'], unique=False)
    op.create_index('ix_solicitud_compra_estado_urgencia_creada_en', 'solicitud_compra', ['estado', 'urgencia', 'creada_en'], unique=False)
    op.create_index('ix_solicitud_compra_solicitante_id', 'solicitud_compra', ['solicitante_id'], unique=False)
    op.create_table('solicitud_compra_evento',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('solicitud_id', sa.Uuid(), nullable=False),
    sa.Column('estado_anterior', sa.String(length=12), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=12), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('nota', sa.String(length=500), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.ForeignKeyConstraint(['solicitud_id'], ['solicitud_compra.id'], name=op.f('fk_solicitud_compra_evento_solicitud_id_solicitud_compra')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_solicitud_compra_evento_usuario_id_usuario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_solicitud_compra_evento'))
    )
    op.create_index('ix_solicitud_compra_evento_solicitud_id_creado_en', 'solicitud_compra_evento', ['solicitud_id', 'creado_en'], unique=False)


def downgrade() -> None:
    # Los índices se van con sus tablas (MySQL no deja quitar uno que respalda una llave foránea).
    op.drop_table('solicitud_compra_evento')
    op.drop_table('solicitud_compra')
    op.drop_table('serie_solicitud_compra')
