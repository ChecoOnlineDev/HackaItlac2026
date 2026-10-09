"""autorizacion.tipo y trabajador_id opcional (FEAT-015, X-17, X-19)

`tipo` distingue la autorización de un excedente (la de siempre), la de un despacho de EPP
(FEAT-014) y la de un traslado entre almacenes de tercer nivel (FEAT-015). Las existentes quedan
EXCEDENTE. Un traslado no tiene trabajador: `trabajador_id` acepta nulo, y un CHECK exige
trabajador salvo en el tipo TRASLADO.

Bajada: las autorizaciones de traslado no caben en el esquema anterior (sin trabajador), así que
se borran, y los vales que las citaban dejan de citarlas.

Revision ID: 0010_autorizacion_traslado
Revises: 0009_permiso_valor_inv
Create Date: 2026-10-08 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_autorizacion_traslado"
down_revision: str | None = "0009_permiso_valor_inv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "autorizacion",
        sa.Column("tipo", sa.String(length=10), server_default="EXCEDENTE", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_autorizacion_tipo"),
        "autorizacion",
        "tipo IN ('EXCEDENTE', 'DESPACHO', 'TRASLADO')",
    )
    op.alter_column("autorizacion", "trabajador_id", existing_type=sa.Uuid(), nullable=True)
    op.create_check_constraint(
        op.f("ck_autorizacion_trabajador_segun_tipo"),
        "autorizacion",
        "trabajador_id IS NOT NULL OR tipo = 'TRASLADO'",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE vale SET autorizacion_id = NULL WHERE autorizacion_id IN "
        "(SELECT id FROM autorizacion WHERE trabajador_id IS NULL)"
    )
    op.execute("DELETE FROM autorizacion WHERE trabajador_id IS NULL")
    op.drop_constraint(op.f("ck_autorizacion_trabajador_segun_tipo"), "autorizacion", type_="check")
    op.alter_column("autorizacion", "trabajador_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint(op.f("ck_autorizacion_tipo"), "autorizacion", type_="check")
    op.drop_column("autorizacion", "tipo")
