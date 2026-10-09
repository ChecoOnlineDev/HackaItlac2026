"""Marca de alto valor y permiso de deudores (AV-04/DU-01)."""

import sqlalchemy as sa

from alembic import op

revision = "0017_alto_valor_deudores"
down_revision = "0016_vale_sello"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "categoria",
        sa.Column("alto_valor", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.execute("UPDATE categoria SET alto_valor = 1 WHERE nombre = 'Equipo de alto valor'")
    op.execute(
        "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
        "SELECT DISTINCT r.id, 'deudores.ver' FROM rol r "
        "LEFT JOIN rol_permiso p ON p.rol_id=r.id WHERE r.protegido=1 "
        "OR r.nombre IN ('Supervisor','Recursos Humanos') OR p.permiso='reportes.adeudos'"
    )


def downgrade():
    op.execute("DELETE FROM rol_permiso WHERE permiso='deudores.ver'")
    op.drop_column("categoria", "alto_valor")
