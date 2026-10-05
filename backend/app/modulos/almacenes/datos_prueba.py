"""Datos de prueba de `almacenes`: los seis almacenes del PDF y las ubicaciones. Idempotente."""

from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, TipoAlmacen, UbicacionVirtual
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository

# (clave, nombre, tipo, clave del padre). Kepler surte a Contratistas; Contratistas, a las áreas.
ALMACENES = (
    ("KEP", "Kepler", TipoAlmacen.CENTRAL, None),
    ("CON", "Contratistas", TipoAlmacen.SUBALMACEN, "KEP"),
    ("MID", "Midrex", TipoAlmacen.PROYECTO, "CON"),
    ("HYL", "HYL", TipoAlmacen.PROYECTO, "CON"),
    ("LAM", "Laminador", TipoAlmacen.PROYECTO, "CON"),
    ("MIN", "Minas", TipoAlmacen.PROYECTO, "CON"),
)


def cargar(session: Session) -> None:
    almacenes = AlmacenRepository(session)
    ubicaciones = UbicacionRepository(session)

    for clave, nombre, tipo, clave_padre in ALMACENES:
        almacen = almacenes.get_by_clave(clave)
        padre = almacenes.get_by_clave(clave_padre) if clave_padre else None
        if almacen is None:
            almacen = almacenes.add(
                Almacen(clave=clave, nombre=nombre, tipo=tipo, padre_id=padre.id if padre else None)
            )
        else:
            almacen.nombre = nombre
            almacen.tipo = tipo
            almacen.padre_id = padre.id if padre else None
        if ubicaciones.de_almacen(almacen.id) is None:
            ubicaciones.crear_de_almacen(almacen.id)

    for virtual in UbicacionVirtual:
        if ubicaciones.virtual(virtual) is None:
            ubicaciones.crear_virtual(virtual)
    session.flush()
