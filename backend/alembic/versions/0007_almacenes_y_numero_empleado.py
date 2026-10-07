"""almacenes y numero de empleado

FEAT-008: restricciones de `almacen` (nombre unico y un solo central), contador
`serie_empleado` y la marca `trabajador.numero_externo` (T-10).

Revision ID: 0007_almacenes_empleado
Revises: 0006_solicitudes_compra
Create Date: 2026-10-06 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007_almacenes_empleado'
down_revision: str | None = '0006_solicitudes_compra'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conexion = op.get_bind()

    # Si la base ya trae datos que rompen las restricciones nuevas, se avisa en claro.
    repetidos = conexion.execute(
        sa.text("SELECT nombre FROM almacen GROUP BY nombre HAVING COUNT(*) > 1")
    ).scalars().all()
    if repetidos:
        raise RuntimeError(
            "Hay almacenes con el mismo nombre (" + ", ".join(repetidos) + "). "
            "Cambia el nombre de uno antes de migrar."
        )
    centrales = conexion.execute(
        sa.text("SELECT COUNT(*) FROM almacen WHERE tipo = 'CENTRAL'")
    ).scalar_one()
    if centrales > 1:
        raise RuntimeError(
            "Hay mas de un almacen central. Deja solo uno antes de migrar."
        )

    op.create_unique_constraint('uq_almacen_nombre', 'almacen', ['nombre'])
    op.add_column('almacen', sa.Column(
        'central_unico', sa.Integer(),
        sa.Computed("CASE WHEN tipo = 'CENTRAL' THEN 1 ELSE NULL END", persisted=False),
        nullable=True,
    ))
    op.create_unique_constraint('uq_almacen_un_central', 'almacen', ['central_unico'])

    op.add_column('trabajador', sa.Column(
        'numero_externo', sa.Boolean(), server_default=sa.text('0'), nullable=False
    ))
    # Los que ya existian conservan su numero y quedan como externos (T-10).
    op.execute("UPDATE trabajador SET numero_externo = 1")

    op.create_table('serie_empleado',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('ultimo', sa.Integer(), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_serie_empleado_una_sola_fila')),
    sa.CheckConstraint('ultimo >= 0', name=op.f('ck_serie_empleado_ultimo_no_negativo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_serie_empleado'))
    )
    # El contador arranca en el mayor consecutivo con forma E-NNNNNN que ya exista.
    mayor = conexion.execute(sa.text(
        "SELECT COALESCE(MAX(CAST(SUBSTRING(numero_empleado, 3) AS UNSIGNED)), 0) "
        "FROM trabajador WHERE numero_empleado REGEXP '^E-[0-9]{6}$'"
    )).scalar_one()
    conexion.execute(
        sa.text("INSERT INTO serie_empleado (id, ultimo) VALUES (1, :ultimo)"),
        {"ultimo": int(mayor)},
    )


def downgrade() -> None:
    op.drop_table('serie_empleado')
    op.drop_column('trabajador', 'numero_externo')
    op.drop_constraint('uq_almacen_un_central', 'almacen', type_='unique')
    op.drop_column('almacen', 'central_unico')
    op.drop_constraint('uq_almacen_nombre', 'almacen', type_='unique')
