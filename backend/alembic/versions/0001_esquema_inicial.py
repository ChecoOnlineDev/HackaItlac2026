"""esquema_inicial

Revision ID: 0001_esquema_inicial
Revises: 
Create Date: 2026-10-05 00:26:22.703611
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0001_esquema_inicial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Revisada a mano.
    op.create_table('almacen',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('clave', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('padre_id', sa.Uuid(), nullable=True),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.Column('cerrado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=True),
    sa.CheckConstraint("estado IN ('ACTIVO', 'CERRADO')", name=op.f('ck_almacen_estado')),
    sa.CheckConstraint("tipo IN ('CENTRAL', 'SUBALMACEN', 'PROYECTO')", name=op.f('ck_almacen_tipo')),
    sa.ForeignKeyConstraint(['padre_id'], ['almacen.id'], name=op.f('fk_almacen_padre_id_almacen')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_almacen')),
    sa.UniqueConstraint('clave', name=op.f('uq_almacen_clave'))
    )
    op.create_table('categoria',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('control', sa.String(length=10), nullable=False),
    sa.Column('retornable', sa.Boolean(), nullable=False),
    sa.Column('requiere_inspeccion', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('vigencia_inspeccion_dias', sa.Integer(), nullable=True),
    sa.Column('requiere_autorizacion', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('motivo_uso_especial', sa.String(length=255), nullable=True),
    sa.Column('limite_cantidad', sa.Integer(), nullable=True),
    sa.Column('limite_periodo_dias', sa.Integer(), nullable=True),
    sa.Column('cantidad_aviso', sa.Integer(), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("control IN ('PIEZA', 'CANTIDAD')", name=op.f('ck_categoria_control')),
    sa.CheckConstraint("requiere_inspeccion = 0 OR control = 'PIEZA'", name=op.f('ck_categoria_inspeccion_solo_pieza')),
    sa.CheckConstraint("tipo IN ('EPP', 'HERRAMIENTA')", name=op.f('ck_categoria_tipo')),
    sa.CheckConstraint('cantidad_aviso IS NULL OR cantidad_aviso > 0', name=op.f('ck_categoria_aviso_positivo')),
    sa.CheckConstraint('limite_cantidad IS NULL OR limite_cantidad > 0', name=op.f('ck_categoria_limite_positivo')),
    sa.CheckConstraint('limite_periodo_dias IS NULL OR limite_periodo_dias > 0', name=op.f('ck_categoria_periodo_positivo')),
    sa.CheckConstraint('vigencia_inspeccion_dias IS NULL OR vigencia_inspeccion_dias > 0', name=op.f('ck_categoria_vigencia_positiva')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categoria')),
    sa.UniqueConstraint('nombre', name=op.f('uq_categoria_nombre'))
    )
    op.create_table('codigo',
    sa.Column('codigo', sa.String(length=64), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('ref_id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("tipo IN ('TRABAJADOR', 'ARTICULO', 'PIEZA', 'VALE')", name=op.f('ck_codigo_tipo')),
    sa.PrimaryKeyConstraint('codigo', name=op.f('pk_codigo'))
    )
    op.create_index('ix_codigo_tipo_ref_id', 'codigo', ['tipo', 'ref_id'], unique=False)
    op.create_table('rol',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('protegido', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rol')),
    sa.UniqueConstraint('nombre', name=op.f('uq_rol_nombre'))
    )
    op.create_table('trabajador',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('numero_empleado', sa.String(length=30), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('curp', sa.String(length=18), nullable=True),
    sa.Column('nss', sa.String(length=11), nullable=True),
    sa.Column('tallas', sa.JSON(), nullable=True),
    sa.Column('foto_adjunto_id', sa.Uuid(), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("estado IN ('ACTIVO', 'BAJA_EN_PROCESO', 'INACTIVO')", name=op.f('ck_trabajador_estado')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trabajador')),
    sa.UniqueConstraint('curp', name=op.f('uq_trabajador_curp')),
    sa.UniqueConstraint('numero_empleado', name=op.f('uq_trabajador_numero_empleado'))
    )
    op.create_table('articulo',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('codigo', sa.String(length=64), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('marca', sa.String(length=80), nullable=True),
    sa.Column('modelo', sa.String(length=80), nullable=True),
    sa.Column('categoria_id', sa.Uuid(), nullable=False),
    sa.Column('control', sa.String(length=10), nullable=False),
    sa.Column('retornable', sa.Boolean(), nullable=False),
    sa.Column('talla', sa.String(length=20), nullable=True),
    sa.Column('unidad', sa.String(length=20), nullable=False),
    sa.Column('costo_unitario', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('requiere_inspeccion', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('vigencia_inspeccion_dias', sa.Integer(), nullable=True),
    sa.Column('requiere_autorizacion', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('motivo_uso_especial', sa.String(length=255), nullable=True),
    sa.Column('limite_cantidad', sa.Integer(), nullable=True),
    sa.Column('limite_periodo_dias', sa.Integer(), nullable=True),
    sa.Column('cantidad_aviso', sa.Integer(), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('motivo_inactivacion', sa.String(length=255), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("control IN ('PIEZA', 'CANTIDAD')", name=op.f('ck_articulo_control')),
    sa.CheckConstraint("requiere_inspeccion = 0 OR control = 'PIEZA'", name=op.f('ck_articulo_inspeccion_solo_pieza')),
    sa.CheckConstraint('activo = 1 OR motivo_inactivacion IS NOT NULL', name=op.f('ck_articulo_inactivo_con_motivo')),
    sa.CheckConstraint('cantidad_aviso IS NULL OR cantidad_aviso > 0', name=op.f('ck_articulo_aviso_positivo')),
    sa.CheckConstraint('costo_unitario IS NULL OR costo_unitario >= 0', name=op.f('ck_articulo_costo_no_negativo')),
    sa.CheckConstraint('limite_cantidad IS NULL OR limite_cantidad > 0', name=op.f('ck_articulo_limite_positivo')),
    sa.CheckConstraint('limite_periodo_dias IS NULL OR limite_periodo_dias > 0', name=op.f('ck_articulo_periodo_positivo')),
    sa.CheckConstraint('vigencia_inspeccion_dias IS NULL OR vigencia_inspeccion_dias > 0', name=op.f('ck_articulo_vigencia_positiva')),
    sa.ForeignKeyConstraint(['categoria_id'], ['categoria.id'], name=op.f('fk_articulo_categoria_id_categoria')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_articulo')),
    sa.UniqueConstraint('codigo', name=op.f('uq_articulo_codigo'))
    )
    op.create_index('ix_articulo_categoria_id', 'articulo', ['categoria_id'], unique=False)
    op.create_table('rol_permiso',
    sa.Column('rol_id', sa.Uuid(), nullable=False),
    sa.Column('permiso', sa.String(length=80), nullable=False),
    sa.ForeignKeyConstraint(['rol_id'], ['rol.id'], name=op.f('fk_rol_permiso_rol_id_rol')),
    sa.PrimaryKeyConstraint('rol_id', 'permiso', name=op.f('pk_rol_permiso'))
    )
    op.create_table('serie_folio',
    sa.Column('almacen_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=15), nullable=False),
    sa.Column('ultimo', sa.Integer(), nullable=False),
    sa.CheckConstraint("tipo IN ('ENTRADA', 'ENTREGA', 'DEVOLUCION', 'TRASPASO', 'RECEPCION', 'NO_ADEUDO', 'CANCELACION')", name=op.f('ck_serie_folio_tipo')),
    sa.CheckConstraint('ultimo >= 0', name=op.f('ck_serie_folio_ultimo_no_negativo')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_serie_folio_almacen_id_almacen')),
    sa.PrimaryKeyConstraint('almacen_id', 'tipo', name=op.f('pk_serie_folio'))
    )
    op.create_table('ubicacion',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('almacen_id', sa.Uuid(), nullable=True),
    sa.Column('trabajador_id', sa.Uuid(), nullable=True),
    sa.Column('virtual', sa.String(length=12), nullable=True),
    sa.CheckConstraint("(tipo = 'ALMACEN' AND almacen_id IS NOT NULL AND trabajador_id IS NULL AND `virtual` IS NULL) OR (tipo = 'TRABAJADOR' AND trabajador_id IS NOT NULL AND almacen_id IS NULL AND `virtual` IS NULL) OR (tipo = 'VIRTUAL' AND `virtual` IS NOT NULL AND almacen_id IS NULL AND trabajador_id IS NULL)", name=op.f('ck_ubicacion_exactamente_uno')),
    sa.CheckConstraint("tipo IN ('ALMACEN', 'TRABAJADOR', 'VIRTUAL')", name=op.f('ck_ubicacion_tipo')),
    sa.CheckConstraint("`virtual` IS NULL OR `virtual` IN ('PROVEEDOR', 'EN_TRANSITO', 'CONSUMIDO', 'BAJA')", name=op.f('ck_ubicacion_virtual_valida')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_ubicacion_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['trabajador_id'], ['trabajador.id'], name=op.f('fk_ubicacion_trabajador_id_trabajador')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ubicacion')),
    sa.UniqueConstraint('almacen_id', name=op.f('uq_ubicacion_almacen_id')),
    sa.UniqueConstraint('trabajador_id', name=op.f('uq_ubicacion_trabajador_id')),
    sa.UniqueConstraint('virtual', name=op.f('uq_ubicacion_virtual'))
    )
    op.create_table('usuario',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('usuario', sa.String(length=60), nullable=False),
    sa.Column('contrasena_hash', sa.String(length=255), nullable=False),
    sa.Column('pin_hash', sa.String(length=255), nullable=True),
    sa.Column('rol_id', sa.Uuid(), nullable=False),
    sa.Column('almacen_id', sa.Uuid(), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.Column('intentos_fallidos', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bloqueado_hasta', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=True),
    sa.Column('pin_intentos_fallidos', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('pin_bloqueado_hasta', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=True),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_usuario_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['rol_id'], ['rol.id'], name=op.f('fk_usuario_rol_id_rol')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuario')),
    sa.UniqueConstraint('usuario', name=op.f('uq_usuario_usuario'))
    )
    op.create_index('ix_usuario_almacen_id', 'usuario', ['almacen_id'], unique=False)
    op.create_index('ix_usuario_rol_id', 'usuario', ['rol_id'], unique=False)
    op.create_table('auditoria',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=True),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('entidad', sa.String(length=60), nullable=False),
    sa.Column('entidad_id', sa.String(length=64), nullable=True),
    sa.Column('antes', sa.JSON(), nullable=True),
    sa.Column('despues', sa.JSON(), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_auditoria_usuario_id_usuario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auditoria'))
    )
    op.create_index('ix_auditoria_entidad_entidad_id_creado_en', 'auditoria', ['entidad', 'entidad_id', 'creado_en'], unique=False)
    op.create_index('ix_auditoria_usuario_id_creado_en', 'auditoria', ['usuario_id', 'creado_en'], unique=False)
    op.create_table('autorizacion',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('almacen_id', sa.Uuid(), nullable=False),
    sa.Column('trabajador_id', sa.Uuid(), nullable=False),
    sa.Column('solicitada_por', sa.Uuid(), nullable=False),
    sa.Column('motivo', sa.String(length=255), nullable=False),
    sa.Column('detalle', sa.JSON(), nullable=True),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('resuelta_por', sa.Uuid(), nullable=True),
    sa.Column('medio', sa.String(length=10), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.Column('resuelta_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=True),
    sa.Column('vence_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("estado IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'VENCIDA', 'USADA')", name=op.f('ck_autorizacion_estado')),
    sa.CheckConstraint("medio IS NULL OR medio IN ('PIN', 'REMOTA')", name=op.f('ck_autorizacion_medio_valido')),
    sa.CheckConstraint('resuelta_por IS NULL OR resuelta_por <> solicitada_por', name=op.f('ck_autorizacion_no_autorizarse')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_autorizacion_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['resuelta_por'], ['usuario.id'], name=op.f('fk_autorizacion_resuelta_por_usuario')),
    sa.ForeignKeyConstraint(['solicitada_por'], ['usuario.id'], name=op.f('fk_autorizacion_solicitada_por_usuario')),
    sa.ForeignKeyConstraint(['trabajador_id'], ['trabajador.id'], name=op.f('fk_autorizacion_trabajador_id_trabajador')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_autorizacion'))
    )
    op.create_index('ix_autorizacion_almacen_id_estado', 'autorizacion', ['almacen_id', 'estado'], unique=False)
    op.create_index('ix_autorizacion_solicitada_por', 'autorizacion', ['solicitada_por'], unique=False)
    op.create_table('existencia',
    sa.Column('ubicacion_id', sa.Uuid(), nullable=False),
    sa.Column('articulo_id', sa.Uuid(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.CheckConstraint('cantidad >= 0', name=op.f('ck_existencia_cantidad_no_negativa')),
    sa.ForeignKeyConstraint(['articulo_id'], ['articulo.id'], name=op.f('fk_existencia_articulo_id_articulo')),
    sa.ForeignKeyConstraint(['ubicacion_id'], ['ubicacion.id'], name=op.f('fk_existencia_ubicacion_id_ubicacion')),
    sa.PrimaryKeyConstraint('ubicacion_id', 'articulo_id', name=op.f('pk_existencia'))
    )
    op.create_table('periodo_contrato',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trabajador_id', sa.Uuid(), nullable=False),
    sa.Column('puesto', sa.String(length=100), nullable=True),
    sa.Column('area_obra', sa.String(length=100), nullable=True),
    sa.Column('referencia', sa.String(length=100), nullable=True),
    sa.Column('inicio', sa.Date(), nullable=False),
    sa.Column('fin', sa.Date(), nullable=False),
    sa.Column('creado_por', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint('fin >= inicio', name=op.f('ck_periodo_contrato_fin_posterior_a_inicio')),
    sa.ForeignKeyConstraint(['creado_por'], ['usuario.id'], name=op.f('fk_periodo_contrato_creado_por_usuario')),
    sa.ForeignKeyConstraint(['trabajador_id'], ['trabajador.id'], name=op.f('fk_periodo_contrato_trabajador_id_trabajador')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_periodo_contrato'))
    )
    op.create_index('ix_periodo_contrato_trabajador_id_fin', 'periodo_contrato', ['trabajador_id', 'fin'], unique=False)
    op.create_table('pieza',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('articulo_id', sa.Uuid(), nullable=False),
    sa.Column('codigo', sa.String(length=64), nullable=False),
    sa.Column('numero_serie', sa.String(length=80), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('inspeccion_vigente_hasta', sa.Date(), nullable=True),
    sa.Column('ubicacion_id', sa.Uuid(), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("estado IN ('APTO', 'NO_APTO', 'EN_MANTENIMIENTO', 'EN_CALIBRACION', 'BAJA')", name=op.f('ck_pieza_estado')),
    sa.ForeignKeyConstraint(['articulo_id'], ['articulo.id'], name=op.f('fk_pieza_articulo_id_articulo')),
    sa.ForeignKeyConstraint(['ubicacion_id'], ['ubicacion.id'], name=op.f('fk_pieza_ubicacion_id_ubicacion')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pieza')),
    sa.UniqueConstraint('articulo_id', 'numero_serie', name=op.f('uq_pieza_articulo_id_numero_serie')),
    sa.UniqueConstraint('codigo', name=op.f('uq_pieza_codigo'))
    )
    op.create_index('ix_pieza_articulo_id', 'pieza', ['articulo_id'], unique=False)
    op.create_index('ix_pieza_ubicacion_id_estado', 'pieza', ['ubicacion_id', 'estado'], unique=False)
    op.create_table('evento_pieza',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('pieza_id', sa.Uuid(), nullable=False),
    sa.Column('estado_anterior', sa.String(length=20), nullable=False),
    sa.Column('estado_nuevo', sa.String(length=20), nullable=False),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("estado_anterior IN ('APTO', 'NO_APTO', 'EN_MANTENIMIENTO', 'EN_CALIBRACION', 'BAJA')", name=op.f('ck_evento_pieza_estado_anterior_valido')),
    sa.CheckConstraint("estado_nuevo IN ('APTO', 'NO_APTO', 'EN_MANTENIMIENTO', 'EN_CALIBRACION', 'BAJA')", name=op.f('ck_evento_pieza_estado_nuevo_valido')),
    sa.ForeignKeyConstraint(['pieza_id'], ['pieza.id'], name=op.f('fk_evento_pieza_pieza_id_pieza')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_evento_pieza_usuario_id_usuario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evento_pieza'))
    )
    op.create_index('ix_evento_pieza_pieza_id_creado_en', 'evento_pieza', ['pieza_id', 'creado_en'], unique=False)
    op.create_table('inspeccion',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('pieza_id', sa.Uuid(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('resultado', sa.String(length=10), nullable=False),
    sa.Column('puntos', sa.JSON(), nullable=True),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("resultado IN ('APTO', 'NO_APTO')", name=op.f('ck_inspeccion_resultado')),
    sa.ForeignKeyConstraint(['pieza_id'], ['pieza.id'], name=op.f('fk_inspeccion_pieza_id_pieza')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_inspeccion_usuario_id_usuario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inspeccion'))
    )
    op.create_index('ix_inspeccion_pieza_id_fecha', 'inspeccion', ['pieza_id', 'fecha'], unique=False)
    op.create_table('vale',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_cliente', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=15), nullable=False),
    sa.Column('folio', sa.String(length=30), nullable=False),
    sa.Column('almacen_id', sa.Uuid(), nullable=False),
    sa.Column('trabajador_id', sa.Uuid(), nullable=True),
    sa.Column('periodo_contrato_id', sa.Uuid(), nullable=True),
    sa.Column('destino_almacen_id', sa.Uuid(), nullable=True),
    sa.Column('vale_origen_id', sa.Uuid(), nullable=True),
    sa.Column('estado', sa.String(length=30), nullable=False),
    sa.Column('responsable_id', sa.Uuid(), nullable=False),
    sa.Column('autorizacion_id', sa.Uuid(), nullable=True),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('firma_modo', sa.String(length=10), nullable=True),
    sa.Column('firma_adjunto_id', sa.Uuid(), nullable=True),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('dispositivo', sa.String(length=200), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("estado IN ('EMITIDO', 'EN_TRANSITO', 'RECIBIDO', 'RECIBIDO_CON_DIFERENCIAS', 'CANCELADO')", name=op.f('ck_vale_estado')),
    sa.CheckConstraint("firma_modo IS NULL OR firma_modo IN ('PANTALLA', 'SESION')", name=op.f('ck_vale_firma_modo_valido')),
    sa.CheckConstraint("tipo IN ('ENTRADA', 'ENTREGA', 'DEVOLUCION', 'TRASPASO', 'RECEPCION', 'NO_ADEUDO', 'CANCELACION')", name=op.f('ck_vale_tipo')),
    sa.ForeignKeyConstraint(['almacen_id'], ['almacen.id'], name=op.f('fk_vale_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['autorizacion_id'], ['autorizacion.id'], name=op.f('fk_vale_autorizacion_id_autorizacion')),
    sa.ForeignKeyConstraint(['destino_almacen_id'], ['almacen.id'], name=op.f('fk_vale_destino_almacen_id_almacen')),
    sa.ForeignKeyConstraint(['periodo_contrato_id'], ['periodo_contrato.id'], name=op.f('fk_vale_periodo_contrato_id_periodo_contrato')),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuario.id'], name=op.f('fk_vale_responsable_id_usuario')),
    sa.ForeignKeyConstraint(['trabajador_id'], ['trabajador.id'], name=op.f('fk_vale_trabajador_id_trabajador')),
    sa.ForeignKeyConstraint(['vale_origen_id'], ['vale.id'], name=op.f('fk_vale_vale_origen_id_vale')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vale')),
    sa.UniqueConstraint('folio', name=op.f('uq_vale_folio')),
    sa.UniqueConstraint('id_cliente', name=op.f('uq_vale_id_cliente')),
    sa.UniqueConstraint('token', name=op.f('uq_vale_token'))
    )
    op.create_index('ix_vale_responsable_id_creado_en', 'vale', ['responsable_id', 'creado_en'], unique=False)
    op.create_index('ix_vale_tipo_almacen_id_creado_en', 'vale', ['tipo', 'almacen_id', 'creado_en'], unique=False)
    op.create_index('ix_vale_trabajador_id', 'vale', ['trabajador_id'], unique=False)
    op.create_table('ajuste_vigencia',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('pieza_id', sa.Uuid(), nullable=False),
    sa.Column('inspeccion_id', sa.Uuid(), nullable=False),
    sa.Column('vigente_hasta_anterior', sa.Date(), nullable=True),
    sa.Column('vigente_hasta_nuevo', sa.Date(), nullable=False),
    sa.Column('motivo', sa.String(length=255), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.ForeignKeyConstraint(['inspeccion_id'], ['inspeccion.id'], name=op.f('fk_ajuste_vigencia_inspeccion_id_inspeccion')),
    sa.ForeignKeyConstraint(['pieza_id'], ['pieza.id'], name=op.f('fk_ajuste_vigencia_pieza_id_pieza')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_ajuste_vigencia_usuario_id_usuario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ajuste_vigencia'))
    )
    op.create_index('ix_ajuste_vigencia_pieza_id', 'ajuste_vigencia', ['pieza_id'], unique=False)
    op.create_table('movimiento',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('vale_id', sa.Uuid(), nullable=False),
    sa.Column('renglon', sa.Integer(), nullable=False),
    sa.Column('articulo_id', sa.Uuid(), nullable=False),
    sa.Column('pieza_id', sa.Uuid(), nullable=True),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('origen_id', sa.Uuid(), nullable=False),
    sa.Column('destino_id', sa.Uuid(), nullable=False),
    sa.Column('trabajador_id', sa.Uuid(), nullable=True),
    sa.Column('condicion', sa.String(length=10), nullable=True),
    sa.Column('motivo_baja', sa.String(length=255), nullable=True),
    sa.Column('nivel', sa.String(length=10), server_default=sa.text("'VERDE'"), nullable=False),
    sa.Column('reglas', sa.JSON(), nullable=True),
    sa.Column('observacion', sa.Text(), nullable=True),
    sa.Column('saldo_origen', sa.Integer(), nullable=True),
    sa.Column('saldo_destino', sa.Integer(), nullable=True),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("condicion IS NULL OR condicion IN ('BUENO', 'DESGASTE', 'DANADO')", name=op.f('ck_movimiento_condicion_valida')),
    sa.CheckConstraint("nivel IN ('VERDE', 'AMARILLO', 'NARANJA', 'ROJO')", name=op.f('ck_movimiento_nivel')),
    sa.CheckConstraint('cantidad > 0', name=op.f('ck_movimiento_cantidad_positiva')),
    sa.CheckConstraint('origen_id <> destino_id', name=op.f('ck_movimiento_origen_distinto_destino')),
    sa.CheckConstraint('pieza_id IS NULL OR cantidad = 1', name=op.f('ck_movimiento_pieza_cantidad_uno')),
    sa.CheckConstraint('renglon > 0', name=op.f('ck_movimiento_renglon_positivo')),
    sa.ForeignKeyConstraint(['articulo_id'], ['articulo.id'], name=op.f('fk_movimiento_articulo_id_articulo')),
    sa.ForeignKeyConstraint(['destino_id'], ['ubicacion.id'], name=op.f('fk_movimiento_destino_id_ubicacion')),
    sa.ForeignKeyConstraint(['origen_id'], ['ubicacion.id'], name=op.f('fk_movimiento_origen_id_ubicacion')),
    sa.ForeignKeyConstraint(['pieza_id'], ['pieza.id'], name=op.f('fk_movimiento_pieza_id_pieza')),
    sa.ForeignKeyConstraint(['trabajador_id'], ['trabajador.id'], name=op.f('fk_movimiento_trabajador_id_trabajador')),
    sa.ForeignKeyConstraint(['vale_id'], ['vale.id'], name=op.f('fk_movimiento_vale_id_vale')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_movimiento')),
    sa.UniqueConstraint('vale_id', 'renglon', name=op.f('uq_movimiento_vale_id_renglon'))
    )
    op.create_index('ix_movimiento_articulo_id_creado_en', 'movimiento', ['articulo_id', 'creado_en'], unique=False)
    op.create_index('ix_movimiento_destino_id_creado_en', 'movimiento', ['destino_id', 'creado_en'], unique=False)
    op.create_index('ix_movimiento_origen_id', 'movimiento', ['origen_id'], unique=False)
    op.create_index('ix_movimiento_pieza_id', 'movimiento', ['pieza_id'], unique=False)
    op.create_index('ix_movimiento_trabajador_id_articulo_id_creado_en', 'movimiento', ['trabajador_id', 'articulo_id', 'creado_en'], unique=False)
    op.create_table('adjunto',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('ruta', sa.String(length=255), nullable=False),
    sa.Column('mime', sa.String(length=100), nullable=False),
    sa.Column('tamano', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('vale_id', sa.Uuid(), nullable=True),
    sa.Column('movimiento_id', sa.Uuid(), nullable=True),
    sa.Column('subido_por', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False),
    sa.CheckConstraint("tipo IN ('FIRMA', 'FOTO_DANO', 'FOTO_TRABAJADOR')", name=op.f('ck_adjunto_tipo')),
    sa.CheckConstraint('tamano > 0', name=op.f('ck_adjunto_tamano_positivo')),
    sa.ForeignKeyConstraint(['movimiento_id'], ['movimiento.id'], name=op.f('fk_adjunto_movimiento_id_movimiento')),
    sa.ForeignKeyConstraint(['subido_por'], ['usuario.id'], name=op.f('fk_adjunto_subido_por_usuario')),
    sa.ForeignKeyConstraint(['vale_id'], ['vale.id'], name=op.f('fk_adjunto_vale_id_vale')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_adjunto')),
    sa.UniqueConstraint('ruta', name=op.f('uq_adjunto_ruta'))
    )
    op.create_index('ix_adjunto_movimiento_id', 'adjunto', ['movimiento_id'], unique=False)
    op.create_index('ix_adjunto_vale_id', 'adjunto', ['vale_id'], unique=False)
    # Llaves circulares (adjunto -> vale -> adjunto): se agregan al final.
    op.create_foreign_key(op.f('fk_trabajador_foto_adjunto_id_adjunto'), 'trabajador', 'adjunto', ['foto_adjunto_id'], ['id'])
    op.create_foreign_key(op.f('fk_vale_firma_adjunto_id_adjunto'), 'vale', 'adjunto', ['firma_adjunto_id'], ['id'])


def downgrade() -> None:
    # Al borrar cada tabla se borran sus índices; MySQL no deja borrar uno que sostiene una llave.
    op.drop_constraint('fk_vale_firma_adjunto_id_adjunto', 'vale', type_='foreignkey')
    op.drop_constraint('fk_trabajador_foto_adjunto_id_adjunto', 'trabajador', type_='foreignkey')
    # Revisada a mano.
    op.drop_table('adjunto')
    op.drop_table('movimiento')
    op.drop_table('ajuste_vigencia')
    op.drop_table('vale')
    op.drop_table('inspeccion')
    op.drop_table('evento_pieza')
    op.drop_table('pieza')
    op.drop_table('periodo_contrato')
    op.drop_table('existencia')
    op.drop_table('autorizacion')
    op.drop_table('auditoria')
    op.drop_table('usuario')
    op.drop_table('ubicacion')
    op.drop_table('serie_folio')
    op.drop_table('rol_permiso')
    op.drop_table('articulo')
    op.drop_table('trabajador')
    op.drop_table('rol')
    op.drop_table('codigo')
    op.drop_table('categoria')
    op.drop_table('almacen')
