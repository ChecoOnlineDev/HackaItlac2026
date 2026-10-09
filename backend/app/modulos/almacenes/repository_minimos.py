import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models_minimos import Minimo


class MinimosRepository:
    def __init__(self, session: Session):
        self.session = session

    def cantidad(self, almacen_id: uuid.UUID, articulo_id: uuid.UUID) -> int | None:
        return self.session.scalar(
            select(Minimo.cantidad).where(
                Minimo.almacen_id == almacen_id, Minimo.articulo_id == articulo_id
            )
        )

    def listar(self, almacen_id: uuid.UUID) -> list[Minimo]:
        return list(
            self.session.scalars(
                select(Minimo).where(Minimo.almacen_id == almacen_id).order_by(Minimo.articulo_id)
            )
        )

    def de_ubicacion(self, ubicacion_id: uuid.UUID, articulo_id: uuid.UUID) -> int | None:
        return self.session.scalar(
            select(Minimo.cantidad)
            .join(Ubicacion, Ubicacion.almacen_id == Minimo.almacen_id)
            .where(Ubicacion.id == ubicacion_id, Minimo.articulo_id == articulo_id)
        )

    def poner(self, almacen_id: uuid.UUID, articulo_id: uuid.UUID, cantidad: int | None):
        minimo = self.session.get(Minimo, (almacen_id, articulo_id))
        if cantidad is None:
            if minimo is not None:
                self.session.delete(minimo)
        elif minimo is None:
            self.session.add(
                Minimo(almacen_id=almacen_id, articulo_id=articulo_id, cantidad=cantidad)
            )
        else:
            minimo.cantidad = cantidad
        self.session.flush()
