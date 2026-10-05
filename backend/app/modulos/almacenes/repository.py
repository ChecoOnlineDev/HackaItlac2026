"""Persistencia del módulo `almacenes`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual


class AlmacenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    def get_by_clave(self, clave: str) -> Almacen | None:
        return self.session.scalar(select(Almacen).where(Almacen.clave == clave))

    def listar(self) -> list[Almacen]:
        return list(self.session.scalars(select(Almacen).order_by(Almacen.clave)))

    def add(self, almacen: Almacen) -> Almacen:
        self.session.add(almacen)
        self.session.flush()
        return almacen


class UbicacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, ubicacion_id: uuid.UUID) -> Ubicacion | None:
        return self.session.get(Ubicacion, ubicacion_id)

    def de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.almacen_id == almacen_id))

    def de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(
            select(Ubicacion).where(Ubicacion.trabajador_id == trabajador_id)
        )

    def virtual(self, virtual: UbicacionVirtual) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.virtual == virtual.value))

    def add(self, ubicacion: Ubicacion) -> Ubicacion:
        self.session.add(ubicacion)
        self.session.flush()
        return ubicacion

    def crear_de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.ALMACEN, almacen_id=almacen_id))

    def crear_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.TRABAJADOR, trabajador_id=trabajador_id))

    def crear_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.VIRTUAL, virtual=virtual.value))
