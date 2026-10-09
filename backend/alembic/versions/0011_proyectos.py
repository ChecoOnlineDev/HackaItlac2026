"""Proyectos e historial de asignaciones (FEAT-013)."""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "0011_proyectos"
down_revision = "0010_autorizacion_traslado"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "proyecto",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clave", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("almacen_id", sa.Uuid(), sa.ForeignKey("almacen.id"), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fin_estimado", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("cerrado_en", mysql.DATETIME(fsp=6)),
        sa.Column("motivo_cierre", sa.String(500)),
        sa.Column("creado_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creado_en", mysql.DATETIME(fsp=6), nullable=False),
        sa.UniqueConstraint("clave", name="uq_proyecto_clave"),
        sa.CheckConstraint(
            "fin_estimado >= inicio", name=op.f("ck_proyecto_fin_posterior_a_inicio")
        ),
        sa.CheckConstraint("estado IN ('ACTIVO', 'CERRADO')", name=op.f("ck_proyecto_estado")),
    )
    op.create_index("ix_proyecto_almacen_id_estado", "proyecto", ["almacen_id", "estado"])
    op.create_table(
        "asignacion_proyecto",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("trabajador_id", sa.Uuid(), sa.ForeignKey("trabajador.id"), nullable=False),
        sa.Column("proyecto_id", sa.Uuid(), sa.ForeignKey("proyecto.id"), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fin", sa.Date()),
        sa.Column("principal", sa.Boolean(), nullable=False),
        sa.Column("creado_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creado_en", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("terminada_en", mysql.DATETIME(fsp=6)),
        sa.Column("terminada_por", sa.Uuid(), sa.ForeignKey("usuario.id")),
        sa.Column(
            "activa",
            sa.Integer(),
            sa.Computed("CASE WHEN terminada_en IS NULL THEN 1 ELSE NULL END", persisted=False),
        ),
        sa.Column(
            "principal_activa",
            sa.Integer(),
            sa.Computed(
                "CASE WHEN terminada_en IS NULL AND principal = 1 THEN 1 ELSE NULL END",
                persisted=False,
            ),
        ),
        sa.UniqueConstraint(
            "trabajador_id", "proyecto_id", "activa", name="uq_asignacion_proyecto_activa"
        ),
        sa.UniqueConstraint(
            "trabajador_id", "principal_activa", name="uq_asignacion_proyecto_principal"
        ),
        sa.CheckConstraint(
            "fin IS NULL OR fin >= inicio OR terminada_en IS NOT NULL",
            name=op.f("ck_asignacion_proyecto_fin_posterior_a_inicio"),
        ),
    )
    for col in ("trabajador_id", "proyecto_id"):
        op.create_index(
            f"ix_asignacion_proyecto_{col}_terminada_en",
            "asignacion_proyecto",
            [col, "terminada_en"],
        )


def downgrade():
    op.drop_table("asignacion_proyecto")
    op.drop_table("proyecto")
