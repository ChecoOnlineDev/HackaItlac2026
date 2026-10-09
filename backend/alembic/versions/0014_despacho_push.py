"""Despacho de EPP y suscripciones para Web Push (FEAT-014)."""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "0014_despacho_push"
down_revision = "0013_minimos"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "almacen",
        sa.Column(
            "despacho_epp_con_aprobacion", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "usuario",
        sa.Column("despacho_autonomo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("autorizacion", sa.Column("id_cliente", sa.Uuid(), nullable=True))
    op.add_column("autorizacion", sa.Column("huella_cuerpo", sa.String(64), nullable=True))
    op.add_column("autorizacion", sa.Column("renglones_resueltos", sa.JSON(), nullable=True))
    op.create_unique_constraint("uq_autorizacion_id_cliente", "autorizacion", ["id_cliente"])
    op.create_table(
        "suscripcion_push",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("familia_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(1000), nullable=False),
        sa.Column("huella_endpoint", sa.String(64), nullable=False),
        sa.Column("p256dh", sa.String(120), nullable=False),
        sa.Column("auth", sa.String(50), nullable=False),
        sa.Column("agente", sa.String(120)),
        sa.Column("creada_en", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("ultimo_envio", mysql.DATETIME(fsp=6)),
        sa.Column("ultima_etiqueta", sa.String(80)),
        sa.Column("ultima_prueba", mysql.DATETIME(fsp=6)),
        sa.Column("ultimo_error", sa.String(255)),
        sa.Column("revocada_en", mysql.DATETIME(fsp=6)),
        sa.Column(
            "endpoint_activo",
            sa.String(64),
            sa.Computed(
                "CASE WHEN revocada_en IS NULL THEN huella_endpoint ELSE NULL END", persisted=False
            ),
        ),
        sa.UniqueConstraint("endpoint_activo", name="uq_suscripcion_push_endpoint_activo"),
    )
    op.create_index(
        "ix_suscripcion_push_usuario_id_familia_id",
        "suscripcion_push",
        ["usuario_id", "familia_id"],
    )
    op.execute(
        "INSERT IGNORE INTO rol_permiso (rol_id,permiso) "
        "SELECT id,'despacho.autonomia' FROM rol WHERE protegido=1"
    )


def downgrade():
    op.execute("DELETE FROM rol_permiso WHERE permiso='despacho.autonomia'")
    op.drop_table("suscripcion_push")
    op.drop_constraint("uq_autorizacion_id_cliente", "autorizacion", type_="unique")
    for campo in ("renglones_resueltos", "huella_cuerpo", "id_cliente"):
        op.drop_column("autorizacion", campo)
    op.drop_column("usuario", "despacho_autonomo")
    op.drop_column("almacen", "despacho_epp_con_aprobacion")
