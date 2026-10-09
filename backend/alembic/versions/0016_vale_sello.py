"""Sello encadenado de vales y firma en papel (F-02, F-06, F-07)."""

import sqlalchemy as sa

from alembic import op

revision = "0016_vale_sello"
down_revision = "0015_inspecciones_alertas"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vale", sa.Column("hash", sa.String(64), nullable=True))
    op.add_column("vale", sa.Column("hash_anterior", sa.String(64), nullable=True))
    op.add_column("vale", sa.Column("sello_anterior_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_vale_sello_anterior", "vale", "vale", ["sello_anterior_id"], ["id"])
    op.create_table(
        "cadena_sello",
        sa.Column("almacen_id", sa.Uuid(), sa.ForeignKey("almacen.id"), primary_key=True),
        sa.Column("ultimo_vale_id", sa.Uuid(), sa.ForeignKey("vale.id"), nullable=True),
        sa.Column("ultimo_hash", sa.String(64), nullable=True),
    )
    op.drop_constraint(op.f("ck_vale_firma_modo_valido"), "vale", type_="check")
    op.create_check_constraint(
        op.f("ck_vale_firma_modo_valido"),
        "vale",
        "firma_modo IS NULL OR firma_modo IN ('PANTALLA','SESION','PAPEL')",
    )
    op.drop_constraint(op.f("ck_adjunto_tipo"), "adjunto", type_="check")
    op.create_check_constraint(
        op.f("ck_adjunto_tipo"),
        "adjunto",
        "tipo IN ('FIRMA','FOTO_DANO','FOTO_TRABAJADOR','FOTO_INSPECCION','TICKET_FIRMADO')",
    )


def downgrade():
    # Una firma en papel forma parte de un vale inmutable; no se elimina para retroceder.
    conexion = op.get_bind()
    if conexion.scalar(sa.text("SELECT COUNT(*) FROM vale WHERE firma_modo='PAPEL'")):
        raise RuntimeError("Hay vales firmados en papel; conserva esta migración y sus pruebas.")
    op.drop_constraint(op.f("ck_adjunto_tipo"), "adjunto", type_="check")
    op.create_check_constraint(
        op.f("ck_adjunto_tipo"),
        "adjunto",
        "tipo IN ('FIRMA','FOTO_DANO','FOTO_TRABAJADOR','FOTO_INSPECCION')",
    )
    op.drop_constraint(op.f("ck_vale_firma_modo_valido"), "vale", type_="check")
    op.create_check_constraint(
        op.f("ck_vale_firma_modo_valido"),
        "vale",
        "firma_modo IS NULL OR firma_modo IN ('PANTALLA','SESION')",
    )
    op.drop_table("cadena_sello")
    op.drop_constraint("fk_vale_sello_anterior", "vale", type_="foreignkey")
    op.drop_column("vale", "sello_anterior_id")
    op.drop_column("vale", "hash_anterior")
    op.drop_column("vale", "hash")
