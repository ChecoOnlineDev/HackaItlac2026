import uuid

from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.repository import AlmacenRepository
from app.modulos.almacenes.repository_minimos import MinimosRepository
from app.modulos.almacenes.schemas_minimos import MinimoOut, MinimosIn
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.service import CatalogoService


class MinimosService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = MinimosRepository(session)

    def _alcance(self, almacen_id: uuid.UUID, usuario: Usuario, *, escritura=False):
        acceso = AccesoService(self.session)
        if not acceso.en_alcance(usuario, almacen_id):
            raise AlmacenNoEncontrado()
        if escritura and not acceso.puede_operar_todos_los_almacenes(usuario):
            acceso.exigir_mismo_almacen(usuario, almacen_id)
        return AlmacenService(self.session).obtener(almacen_id)

    def listar(self, almacen_id: uuid.UUID, usuario: Usuario) -> list[MinimoOut]:
        self._alcance(almacen_id, usuario)
        return [MinimoOut.model_validate(m) for m in self.repository.listar(almacen_id)]

    def cambiar(self, almacen_id: uuid.UUID, datos: MinimosIn, usuario: Usuario) -> list[MinimoOut]:
        self._alcance(almacen_id, usuario, escritura=True)
        try:
            AlmacenRepository(self.session).get_for_update(almacen_id)
            catalogo = CatalogoService(self.session)
            for minimo in datos.minimos:
                catalogo.obtener_articulo(minimo.articulo_id)
            antes = [m.model_dump(mode="json") for m in self.listar(almacen_id, usuario)]
            for minimo in datos.minimos:
                self.repository.poner(almacen_id, minimo.articulo_id, minimo.cantidad)
            despues = [m.model_dump(mode="json") for m in self.listar(almacen_id, usuario)]
            AuditoriaService(self.session).registrar(
                usuario_id=usuario.id,
                accion="almacen.minimos",
                entidad="almacen",
                entidad_id=almacen_id,
                antes={"minimos": antes},
                despues={"minimos": despues, "regla": "I-05"},
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.listar(almacen_id, usuario)
