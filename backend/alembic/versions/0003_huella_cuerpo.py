"""huella_cuerpo

Idempotencia que no oculta cambios (H9): `vale.huella_cuerpo` guarda el SHA-256 del cuerpo con el
que se confirmó el vale. Un reintento con el mismo `id_cliente` y otro cuerpo responde 409.

Revision ID: 0003_huella_cuerpo
Revises: 0002_version_sesion
Create Date: 2026-10-05 12:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003_huella_cuerpo'
down_revision: str | None = '0002_version_sesion'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('vale', sa.Column('huella_cuerpo', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('vale', 'huella_cuerpo')
