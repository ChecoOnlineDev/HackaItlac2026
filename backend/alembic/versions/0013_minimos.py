"""Mínimos por almacén y artículo (I-05)."""

import sqlalchemy as sa

from alembic import op

revision = "0013_minimos"
down_revision = "0012_alcance_proyectos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "minimo",
        sa.Column("almacen_id", sa.Uuid(), sa.ForeignKey("almacen.id"), primary_key=True),
        sa.Column("articulo_id", sa.Uuid(), sa.ForeignKey("articulo.id"), primary_key=True),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.CheckConstraint("cantidad >= 0", name="ck_minimo_cantidad_no_negativa"),
    )
    op.execute(
        "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
        "SELECT id, 'inventario.minimos' FROM rol WHERE nombre = 'Compras' OR protegido = 1"
    )


def downgrade():
    op.execute("DELETE FROM rol_permiso WHERE permiso = 'inventario.minimos'")
    op.drop_table("minimo")
