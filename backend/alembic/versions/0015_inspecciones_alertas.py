"""Inspecciones con evidencia, idempotencia y aviso configurable (P-10 a P-17)."""

import sqlalchemy as sa

from alembic import op

revision = "0015_inspecciones_alertas"
down_revision = "0014_despacho_push"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for tabla in ("categoria", "articulo"):
        if "dias_aviso_inspeccion" not in {c["name"] for c in inspector.get_columns(tabla)}:
            op.add_column(tabla, sa.Column("dias_aviso_inspeccion", sa.Integer(), nullable=True))
            op.create_check_constraint(
                op.f(f"ck_{tabla}_dias_aviso_inspeccion_valido"),
                tabla,
                "dias_aviso_inspeccion IS NULL OR dias_aviso_inspeccion BETWEEN 1 AND 90",
            )
    existentes = {c["name"] for c in inspector.get_columns("inspeccion")}
    if "id_cliente" not in existentes:
        op.add_column("inspeccion", sa.Column("id_cliente", sa.Uuid(), nullable=True))
        op.add_column("inspeccion", sa.Column("huella", sa.String(64), nullable=True))
        op.create_unique_constraint(op.f("uq_inspeccion_id_cliente"), "inspeccion", ["id_cliente"])
    if "inspeccion_id" not in {c["name"] for c in inspector.get_columns("adjunto")}:
        op.add_column("adjunto", sa.Column("inspeccion_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            op.f("fk_adjunto_inspeccion_id_inspeccion"),
            "adjunto",
            "inspeccion",
            ["inspeccion_id"],
            ["id"],
        )
        op.create_index("ix_adjunto_inspeccion_id", "adjunto", ["inspeccion_id"])
    op.drop_constraint(op.f("ck_adjunto_tipo"), "adjunto", type_="check")
    op.create_check_constraint(
        op.f("ck_adjunto_tipo"),
        "adjunto",
        "tipo IN ('FIRMA', 'FOTO_DANO', 'FOTO_TRABAJADOR', 'FOTO_INSPECCION')",
    )
    op.execute(
        "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
        "SELECT id, 'inspecciones.ver' FROM rol "
        "WHERE nombre IN ('Almacenista', 'Supervisor') OR protegido = 1"
    )


def downgrade():
    op.execute("DELETE FROM rol_permiso WHERE permiso='inspecciones.ver'")
    op.drop_constraint(op.f("ck_adjunto_tipo"), "adjunto", type_="check")
    op.execute("DELETE FROM adjunto WHERE tipo='FOTO_INSPECCION'")
    op.create_check_constraint(
        op.f("ck_adjunto_tipo"), "adjunto", "tipo IN ('FIRMA', 'FOTO_DANO', 'FOTO_TRABAJADOR')"
    )
    op.drop_constraint(op.f("fk_adjunto_inspeccion_id_inspeccion"), "adjunto", type_="foreignkey")
    op.drop_index("ix_adjunto_inspeccion_id", table_name="adjunto")
    op.drop_column("adjunto", "inspeccion_id")
    op.drop_constraint(op.f("uq_inspeccion_id_cliente"), "inspeccion", type_="unique")
    op.drop_column("inspeccion", "huella")
    op.drop_column("inspeccion", "id_cliente")
    inspector = sa.inspect(op.get_bind())
    for tabla in ("articulo", "categoria"):
        nombre = next(
            c["name"]
            for c in inspector.get_check_constraints(tabla)
            if c["name"].endswith("dias_aviso_inspeccion_valido")
        )
        op.drop_constraint(op.f(nombre), tabla, type_="check")
        op.drop_column(tabla, "dias_aviso_inspeccion")
