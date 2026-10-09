"""CP-03: tipo AJUSTE y permisos de ajuste/reporte de cierre."""

import sqlalchemy as sa

from alembic import op

revision = "0019_ajuste_cierre"
down_revision = "0018_vale_papel"
branch_labels = None
depends_on = None

_ANTERIORES = "'ENTRADA','ENTREGA','DEVOLUCION','TRASPASO','RECEPCION','NO_ADEUDO','CANCELACION'"


def _tipos(valores):
    for tabla in ("vale", "serie_folio"):
        op.drop_constraint(op.f(f"ck_{tabla}_tipo"), tabla, type_="check")
        op.create_check_constraint(op.f(f"ck_{tabla}_tipo"), tabla, f"tipo IN ({valores})")


def upgrade():
    _tipos(f"{_ANTERIORES},'AJUSTE'")
    for permiso in ("inventario.ajustar", "reportes.cierre"):
        op.execute(
            sa.text(
                "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
                "SELECT id, :permiso FROM rol WHERE protegido=1 OR nombre='Supervisor'"
            ).bindparams(permiso=permiso)
        )
    # Las dependencias son necesarias también para roles iniciales ya persistidos.
    for permiso in ("inventario.ver", "catalogo.ver", "vales.ver", "trabajadores.ver"):
        op.execute(
            sa.text(
                "INSERT IGNORE INTO rol_permiso (rol_id, permiso) "
                "SELECT id, :permiso FROM rol WHERE protegido=1 OR nombre='Supervisor'"
            ).bindparams(permiso=permiso)
        )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM vale WHERE tipo='AJUSTE'")):
        raise RuntimeError("Hay vales AJUSTE; no se puede retirar su tipo sin perder historial.")
    op.execute("DELETE FROM serie_folio WHERE tipo='AJUSTE'")
    op.execute("DELETE FROM rol_permiso WHERE permiso IN ('inventario.ajustar','reportes.cierre')")
    _tipos(_ANTERIORES)
