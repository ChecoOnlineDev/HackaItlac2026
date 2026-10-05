"""Servicio del módulo `almacenes` (mínimo de la Fase 0: lo que `acceso` y los demás necesitan).

Falta por construir: endpoints de lista y existencias (`inventario.ver`). Ver el brief de la fase.
"""

import uuid

from sqlalchemy.orm import Session

from app.modulos.almacenes.exceptions import AlmacenNoEncontrado, UbicacionNoEncontrada
from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository


class AlmacenService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.almacenes = AlmacenRepository(session)
        self.ubicaciones = UbicacionRepository(session)

    def obtener(self, almacen_id: uuid.UUID) -> Almacen:
        almacen = self.almacenes.get(almacen_id)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    def obtener_por_clave(self, clave: str) -> Almacen:
        almacen = self.almacenes.get_by_clave(clave)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    def ubicacion_de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion:
        ubicacion = self.ubicaciones.de_almacen(almacen_id)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def ubicacion_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        ubicacion = self.ubicaciones.de_trabajador(trabajador_id)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def ubicacion_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        ubicacion = self.ubicaciones.virtual(virtual)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def asegurar_ubicacion_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        """Crea la ubicación de un trabajador si no existe (sin commit). Al dar de alta uno."""
        return self.ubicaciones.de_trabajador(
            trabajador_id
        ) or self.ubicaciones.crear_de_trabajador(trabajador_id)
