"""permisos nuevos de FEAT-011 (AC-30, AC-31)

Los permisos son claves en `rol_permiso`; no hay tabla de catalogo. Esta migracion solo agrega
filas y no quita acceso a nadie:

- `acceso.usuarios` y `acceso.roles` a todo rol con `acceso.administrar`.
- `catalogo.limites` a todo rol con `catalogo.administrar`, salvo el Supervisor (AC-31).
- `inventario.importar` a quien ya tiene `inventario.entradas`; `piezas.marcar_estado` a quien ya
  tiene `piezas.inspeccionar`.
- Roles iniciales (por nombre, como el script de datos de prueba): AC-31.
- Los roles protegidos (Administrador) reciben todos los nuevos.

Revision ID: 0008_permisos_feat011
Revises: 0007_almacenes_empleado
Create Date: 2026-10-07 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0008_permisos_feat011'
down_revision: str | None = '0007_almacenes_empleado'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NUEVOS = (
    'bitacora.ver', 'resguardo.ver', 'inventario.importar', 'catalogo.limites',
    'piezas.marcar_estado', 'acceso.usuarios', 'acceso.roles', 'auditoria.ver',
)

# (rol, permiso) de AC-31 para los roles iniciales.
POR_NOMBRE = (
    ('Supervisor', 'bitacora.ver'), ('Supervisor', 'resguardo.ver'),
    ('Supervisor', 'traspasos.recibir'),
    ('Almacenista', 'bitacora.ver'), ('Almacenista', 'resguardo.ver'),
    ('Almacenista', 'traspasos.recibir'),
    ('Compras', 'bitacora.ver'),
    ('Recursos Humanos', 'vales.ver'),
)


def _dar(destino: str, de_quien_tiene: str, salvo: str | None = None) -> None:
    filtro = f" AND r.nombre <> '{salvo}'" if salvo else ''
    op.execute(
        f"INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
        f"SELECT rp.rol_id, '{destino}' FROM rol_permiso rp "
        f"JOIN rol r ON r.id = rp.rol_id "
        f"WHERE rp.permiso = '{de_quien_tiene}'{filtro}"
    )


def upgrade() -> None:
    _dar('acceso.usuarios', 'acceso.administrar')
    _dar('acceso.roles', 'acceso.administrar')
    _dar('catalogo.limites', 'catalogo.administrar', salvo='Supervisor')
    _dar('inventario.importar', 'inventario.entradas')
    _dar('piezas.marcar_estado', 'piezas.inspeccionar')
    for rol, permiso in POR_NOMBRE:
        op.execute(
            f"INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
            f"SELECT id, '{permiso}' FROM rol WHERE nombre = '{rol}'"
        )
    for permiso in NUEVOS:
        op.execute(
            f"INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
            f"SELECT id, '{permiso}' FROM rol WHERE protegido = 1"
        )
    # El Supervisor no cambia limites (AC-31): si un rol con ese nombre ya lo tenia, no hay nada
    # que quitar porque el permiso no existia antes de esta migracion.


def downgrade() -> None:
    lista = ", ".join(f"'{p}'" for p in NUEVOS)
    op.execute(f"DELETE FROM rol_permiso WHERE permiso IN ({lista})")
    # `traspasos.recibir` y `vales.ver` ya existian como permisos; lo que AC-31 dio a los roles
    # iniciales se conserva (no se puede distinguir de lo que alguien activo a mano).
