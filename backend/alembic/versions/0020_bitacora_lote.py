"""BT-02: vínculo de lote insertado con el vale, sin reconstrucción histórica."""

import sqlalchemy as sa

from alembic import op

revision = "0020_bitacora_lote"
down_revision = "0019_ajuste_cierre"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vale", sa.Column("lote_id", sa.Uuid(), nullable=True))
    op.create_index("ix_vale_lote_id", "vale", ["lote_id"])


def downgrade():
    op.drop_index("ix_vale_lote_id", table_name="vale")
    op.drop_column("vale", "lote_id")
