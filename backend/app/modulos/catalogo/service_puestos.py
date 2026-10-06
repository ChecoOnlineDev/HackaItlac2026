"""Puestos y dotación recomendada (FEAT-003, D-01 a D-04). Dueño de `puesto` y `dotacion`.

Los métodos de lectura para otros módulos (`obtener_puesto`, `puesto_por_nombre`,
`renglones_de_puesto`) no hacen commit. Los que atienden un endpoint hacen el suyo y dejan su
registro de cambios (CF-15) en la misma transacción.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_UNICO, violacion
from app.core.excepciones import AppError, DatosInvalidos
from app.core.paginacion import Pagina, Paginacion
from app.modulos.acceso.models import Usuario
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.exceptions import PuestoNoEncontrado, PuestoRepetido
from app.modulos.catalogo.models import Articulo, Dotacion, Puesto
from app.modulos.catalogo.repository import ArticuloRepository, PuestoRepository
from app.modulos.catalogo.schemas import (
    ArticuloDotacionOut,
    DotacionIn,
    DotacionOut,
    LimiteOut,
    PuestoCreate,
    PuestoFilters,
    PuestoOut,
    PuestoRefOut,
    PuestoUpdate,
    RenglonDotacionOut,
)


def _limite_de(articulo: Articulo) -> LimiteOut | None:
    if articulo.limite_cantidad is None:
        return None
    return LimiteOut(cantidad=articulo.limite_cantidad, periodo_dias=articulo.limite_periodo_dias)


def _texto_limite(articulo: Articulo) -> str:
    periodo = articulo.limite_periodo_dias
    return (
        f"{articulo.limite_cantidad} en {periodo} días"
        if periodo
        else (f"{articulo.limite_cantidad} en posesión")
    )


class PuestoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.puestos = PuestoRepository(session)
        self.articulos = ArticuloRepository(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------- transacción

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            traducido = self._traducir(exc)
            if traducido is None:
                raise
            raise traducido from exc
        except Exception:
            self.session.rollback()
            raise

    @staticmethod
    def _traducir(exc: DBAPIError) -> AppError | None:
        v = violacion(exc)
        if v.errno == ERRNO_UNICO and v.restriccion == "uq_puesto_nombre":
            return PuestoRepetido(detalles={"campo": "nombre"})
        return None

    # ------------------------------------------------ lecturas para otros módulos

    def obtener_puesto(self, puesto_id: uuid.UUID) -> Puesto:
        """El puesto, o `PuestoNoEncontrado` (404)."""
        puesto = self.puestos.get(puesto_id)
        if puesto is None:
            raise PuestoNoEncontrado()
        return puesto

    def puesto_por_nombre(self, nombre: str | None) -> Puesto | None:
        """El puesto con ese nombre (sin importar mayúsculas ni acentos), o `None`."""
        if not nombre or not nombre.strip():
            return None
        return self.puestos.get_by_nombre(nombre)

    def renglones_de_puesto(self, puesto_id: uuid.UUID) -> list[tuple[Dotacion, Articulo]]:
        """La dotación recomendada del puesto (D-01) con sus artículos. Solo lectura."""
        return self.puestos.renglones(puesto_id)

    # ----------------------------------------------------------------- puestos

    def _out(self, puesto: Puesto, total_articulos: int) -> PuestoOut:
        return PuestoOut(
            id=puesto.id,
            nombre=puesto.nombre,
            activo=puesto.activo,
            total_articulos=total_articulos,
        )

    def listar(self, filtros: PuestoFilters, pagina: Paginacion) -> Pagina[PuestoOut]:
        filas, total = self.puestos.listar(
            activo=filtros.activo, offset=pagina.offset, limit=pagina.limit
        )
        return Pagina[PuestoOut](elementos=[self._out(p, n) for p, n in filas], total=total)

    def crear(self, datos: PuestoCreate, usuario: Usuario) -> PuestoOut:
        """Nombre único sin importar mayúsculas ni acentos (409)."""
        with self._transaccion():
            if self.puestos.get_by_nombre(datos.nombre) is not None:
                raise PuestoRepetido(detalles={"campo": "nombre"})
            puesto = self.puestos.add(Puesto(nombre=datos.nombre))
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="puesto.crear",
                entidad="puesto",
                entidad_id=puesto.id,
                despues={"nombre": puesto.nombre, "activo": puesto.activo},
            )
        return self._out(puesto, 0)

    def actualizar(self, puesto_id: uuid.UUID, datos: PuestoUpdate, usuario: Usuario) -> PuestoOut:
        puesto = self.obtener_puesto(puesto_id)
        cambios = datos.model_dump(exclude_unset=True)
        diferencias = {k: v for k, v in cambios.items() if getattr(puesto, k) != v}
        if not diferencias:
            return self._out(puesto, self.puestos.total_articulos(puesto.id))
        with self._transaccion():
            if "nombre" in diferencias:
                otro = self.puestos.get_by_nombre(diferencias["nombre"])
                if otro is not None and otro.id != puesto.id:
                    raise PuestoRepetido(detalles={"campo": "nombre"})
            antes = {k: getattr(puesto, k) for k in diferencias}
            for campo, valor in diferencias.items():
                setattr(puesto, campo, valor)
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="puesto.editar",
                entidad="puesto",
                entidad_id=puesto.id,
                antes=antes,
                despues=diferencias,
            )
        return self._out(puesto, self.puestos.total_articulos(puesto.id))

    # ---------------------------------------------------------------- dotación

    def _dotacion_out(self, puesto: Puesto) -> DotacionOut:
        return DotacionOut(
            puesto=PuestoRefOut(id=puesto.id, nombre=puesto.nombre),
            renglones=[
                RenglonDotacionOut(
                    articulo=ArticuloDotacionOut(
                        id=a.id,
                        codigo=a.codigo,
                        nombre=a.nombre,
                        unidad=a.unidad,
                        control=a.control,
                    ),
                    cantidad=d.cantidad,
                    limite=_limite_de(a),
                )
                for d, a in self.puestos.renglones(puesto.id)
            ],
        )

    def dotacion(self, puesto_id: uuid.UUID) -> DotacionOut:
        return self._dotacion_out(self.obtener_puesto(puesto_id))

    def reemplazar_dotacion(
        self, puesto_id: uuid.UUID, datos: DotacionIn, usuario: Usuario
    ) -> DotacionOut:
        """Reemplaza la dotación (D-01). Cada artículo existe y está activo, no se repite, y su
        cantidad no pasa del límite del artículo (D-04): 422 con el renglón que falló."""
        puesto = self.obtener_puesto(puesto_id)
        errores = self._validar_renglones(datos)
        if errores:
            raise DatosInvalidos(errores[0]["mensaje"], errores)
        nuevos = {r.articulo_id: r.cantidad for r in datos.renglones}
        with self._transaccion():
            antes = {str(d.articulo_id): d.cantidad for d, _ in self.puestos.renglones(puesto.id)}
            self.puestos.reemplazar_renglones(puesto.id, nuevos)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="puesto.dotacion",
                entidad="puesto",
                entidad_id=puesto.id,
                antes={"renglones": antes},
                despues={"renglones": {str(k): v for k, v in nuevos.items()}},
            )
        return self._dotacion_out(puesto)

    def _validar_renglones(self, datos: DotacionIn) -> list[dict[str, str]]:
        errores: list[dict[str, str]] = []
        articulos = self.articulos.get_varios([r.articulo_id for r in datos.renglones])
        vistos: set[uuid.UUID] = set()
        for i, renglon in enumerate(datos.renglones):
            campo = f"renglones.{i}.articulo_id"
            articulo = articulos.get(renglon.articulo_id)
            if renglon.articulo_id in vistos:
                errores.append(
                    {
                        "campo": campo,
                        "mensaje": "Ese artículo ya está en la dotación.",
                        "regla": "D-01",
                    }
                )
                continue
            vistos.add(renglon.articulo_id)
            if articulo is None:
                errores.append(
                    {"campo": campo, "mensaje": "No existe ese artículo.", "regla": "D-01"}
                )
            elif not articulo.activo:
                errores.append(
                    {
                        "campo": campo,
                        "mensaje": f"{articulo.nombre} está inactivo: no puede ir en una dotación.",
                        "regla": "D-01",
                    }
                )
            elif (
                articulo.limite_cantidad is not None and renglon.cantidad > articulo.limite_cantidad
            ):
                errores.append(
                    {
                        "campo": f"renglones.{i}.cantidad",
                        "mensaje": (
                            f"La cantidad recomendada de {articulo.nombre} no puede pasar de su "
                            f"límite ({_texto_limite(articulo)})."
                        ),
                        "regla": "D-04",
                    }
                )
        return errores
