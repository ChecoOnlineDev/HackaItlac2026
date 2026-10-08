"""permiso reportes.valor_inventario (FEAT-012)

Los permisos son claves en `rol_permiso`; no hay tabla de catalogo ni cambios de tablas. Solo
agrega filas: el permiso a los roles protegidos (Administrador), Supervisor y Compras.

Revision ID: 0009_permiso_valor_inv
Revises: 0008_permisos_feat011
Create Date: 2026-10-08 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_permiso_valor_inv"
down_revision: str | None = "0008_permisos_feat011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISO = "reportes.valor_inventario"


def upgrade() -> None:
    for rol in ("Supervisor", "Compras"):
        op.execute(
            f"INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
            f"SELECT id, '{PERMISO}' FROM rol WHERE nombre = '{rol}'"
        )
    op.execute(
        f"INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
        f"SELECT id, '{PERMISO}' FROM rol WHERE protegido = 1"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM rol_permiso WHERE permiso = '{PERMISO}'")
