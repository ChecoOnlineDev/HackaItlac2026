"""Persistencia del último sello; sin commit (F-06)."""

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from app.modulos.movimientos.models import CadenaSello, Movimiento, Vale


class SelloRepository:
    def __init__(self, session):
        self.session = session

    def bloquear_cadena(self, almacen_id):
        tabla = CadenaSello.__table__
        alta = insert(tabla).values(almacen_id=almacen_id)
        self.session.execute(alta.on_duplicate_key_update(almacen_id=alta.inserted.almacen_id))
        return self.session.scalar(
            select(CadenaSello)
            .where(CadenaSello.almacen_id == almacen_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def movimientos(self, vale_id):
        return list(
            self.session.scalars(
                select(Movimiento).where(Movimiento.vale_id == vale_id).order_by(Movimiento.renglon)
            )
        )

    def vales(self, almacen_id):
        return list(self.session.scalars(select(Vale).where(Vale.almacen_id == almacen_id)))

    def cadena(self, almacen_id):
        return self.session.get(CadenaSello, almacen_id)
