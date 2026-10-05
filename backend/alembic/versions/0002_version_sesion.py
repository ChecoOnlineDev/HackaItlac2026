"""version_sesion

Cerrar sesión revoca el token (H5): `usuario.version_sesion` va dentro del token (`ver`) y se
incrementa al cerrar sesión, al restablecer la contraseña o el PIN y al inactivar al usuario.

Revision ID: 0002_version_sesion
Revises: 0001_esquema_inicial
Create Date: 2026-10-05 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002_version_sesion'
down_revision: str | None = '0001_esquema_inicial'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'usuario',
        sa.Column('version_sesion', sa.Integer(), server_default=sa.text('0'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('usuario', 'version_sesion')
