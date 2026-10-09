"""F-02: reserva de folio para preparar y firmar el ticket en papel."""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "0018_vale_papel"
down_revision = "0017_alto_valor_deudores"
branch_labels = None
depends_on = None


def upgrade():
    fecha_hora = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
    op.create_table(
        "reserva_papel",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("id_cliente", sa.Uuid(), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), nullable=False),
        sa.Column("almacen_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=15), nullable=False),
        sa.Column("folio", sa.String(length=30), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("huella_cuerpo", sa.String(length=64), nullable=False),
        sa.Column("ticket", sa.JSON(), nullable=False),
        sa.Column("vale_id", sa.Uuid(), nullable=True),
        sa.Column("creado_en", fecha_hora, nullable=False),
        sa.Column("vence_en", fecha_hora, nullable=False),
        sa.ForeignKeyConstraint(["almacen_id"], ["almacen.id"]),
        sa.ForeignKeyConstraint(["responsable_id"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["vale_id"], ["vale.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio", name="uq_reserva_papel_folio"),
        sa.UniqueConstraint("id_cliente", name="uq_reserva_papel_id_cliente"),
        sa.UniqueConstraint("token", name="uq_reserva_papel_token"),
        sa.UniqueConstraint("vale_id"),
    )
    op.create_index("ix_reserva_papel_vence_en", "reserva_papel", ["vence_en"])


def downgrade():
    conexion = op.get_bind()
    if conexion.scalar(sa.text("SELECT COUNT(*) FROM reserva_papel WHERE vale_id IS NOT NULL")):
        raise RuntimeError(
            "Hay vales emitidos desde tickets en papel; no se puede borrar su vínculo."
        )
    op.drop_index("ix_reserva_papel_vence_en", table_name="reserva_papel")
    op.drop_table("reserva_papel")
