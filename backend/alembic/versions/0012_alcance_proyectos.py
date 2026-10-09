"""Alcance por conjunto y atribución de vales a proyectos (FEAT-013)."""

import sqlalchemy as sa

from alembic import op

revision = "0012_alcance_proyectos"
down_revision = "0011_proyectos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usuario_almacen",
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("almacen_id", sa.Uuid(), sa.ForeignKey("almacen.id"), primary_key=True),
    )
    op.execute(
        "INSERT INTO usuario_almacen (usuario_id, almacen_id) "
        "SELECT id, almacen_id FROM usuario WHERE almacen_id IS NOT NULL"
    )
    op.add_column("vale", sa.Column("proyecto_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_vale_proyecto_id_proyecto", "vale", "proyecto", ["proyecto_id"], ["id"]
    )
    op.create_index("ix_vale_proyecto_id", "vale", ["proyecto_id"])
    # Se asignan por capacidades actuales, nunca por nombre de rol.
    for permiso, origen in (
        ("proyectos.ver", "trabajadores.ver"),
        ("proyectos.administrar", "almacenes.todos"),
        ("proyectos.asignar", "trabajadores.administrar"),
    ):
        op.execute(
            sa.text(
                "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
                "SELECT rol_id, :destino FROM rol_permiso WHERE permiso = :origen"
            ).bindparams(destino=permiso, origen=origen)
        )


def downgrade():
    op.execute(
        "DELETE FROM rol_permiso WHERE permiso IN "
        "('proyectos.ver', 'proyectos.administrar', 'proyectos.asignar')"
    )
    op.drop_constraint("fk_vale_proyecto_id_proyecto", "vale", type_="foreignkey")
    op.drop_index("ix_vale_proyecto_id", table_name="vale")
    op.drop_column("vale", "proyecto_id")
    op.drop_table("usuario_almacen")
