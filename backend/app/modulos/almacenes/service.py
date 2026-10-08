"""Servicio del módulo `almacenes`: red de almacenes, ubicaciones y lectura de existencias.

`existencia` es de `movimientos`: aquí solo se lee. Nada de este módulo escribe saldos.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import es_restriccion
from app.core.excepciones import Conflicto
from app.core.paginacion import Paginacion
from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.exceptions import (
    AlmacenCerrado,
    AlmacenConBloqueos,
    AlmacenNoEncontrado,
    ClaveConFolios,
    ClaveRepetida,
    NombreRepetido,
    PadreCerrado,
    PadreInvalido,
    UbicacionNoEncontrada,
    YaHayCentral,
)
from app.modulos.almacenes.models import (
    Almacen,
    EstadoAlmacen,
    TipoAlmacen,
    Ubicacion,
    UbicacionVirtual,
)
from app.modulos.almacenes.repository import (
    AlmacenRepository,
    FiltroExistencias,
    UbicacionRepository,
)
from app.modulos.almacenes.schemas import (
    AlmacenCreate,
    AlmacenFilters,
    AlmacenHijoOut,
    AlmacenOut,
    AlmacenResumenOut,
    AlmacenUpdate,
    BloqueoCierreOut,
    CambioEstadoIn,
    ExistenciaOut,
    ExistenciasOut,
    ExistenciasResumenOut,
    ResumenAlmacenOut,
)
from app.modulos.auditoria.service import AuditoriaService

# Cuántos renglones trae cada bloqueo de cierre en `detalles` (api-contracts.md).
LIMITE_DETALLE = 20


@dataclass
class _DatosResumen:
    """Conteos por almacén para el resumen y los bloqueos de cierre."""

    existencias: dict[uuid.UUID, tuple[int, int]] = field(default_factory=dict)
    usuarios: dict[uuid.UUID, int] = field(default_factory=dict)
    traspasos: dict[uuid.UUID, int] = field(default_factory=dict)
    solicitudes: dict[uuid.UUID, int] = field(default_factory=dict)
    piezas: dict[uuid.UUID, int] = field(default_factory=dict)
    con_folios: set[uuid.UUID] = field(default_factory=set)


class AlmacenService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.almacenes = AlmacenRepository(session)
        self.ubicaciones = UbicacionRepository(session)
        self.auditoria = AuditoriaService(session)

    def obtener(self, almacen_id: uuid.UUID) -> Almacen:
        almacen = self.almacenes.get(almacen_id)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    def obtener_central(self) -> Almacen:
        """EK-01: el almacén central (Kepler), resuelto por su tipo y no por su clave."""
        almacen = self.almacenes.get_central()
        if almacen is None:
            raise AlmacenNoEncontrado("No hay un almacén central. Créalo primero.")
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

    # ------------------------------------------------------------------ lectura

    def listar(self, *, resumen: bool = False) -> list[AlmacenOut]:
        """Todos los almacenes (también los cerrados) con su red: quién los surte y a quién
        surten. Con `resumen`, lo que necesita la administración (FEAT-008); quien lo pide debe
        tener `almacenes.administrar` (lo verifica el router)."""
        almacenes = self.almacenes.listar()
        datos = self._datos_de_resumen() if resumen else None
        return [self._ficha(a, almacenes, datos) for a in almacenes]

    # ------------------------------------------------------- administración (FEAT-008)

    def crear(self, datos: AlmacenCreate, actor: Usuario) -> AlmacenOut:
        """AL-01, AL-02: crea el almacén y su ubicación en una sola transacción."""
        if datos.tipo_enum() == TipoAlmacen.CENTRAL:
            if datos.padre_id is not None:
                raise PadreInvalido("El almacén central no depende de otro.")
        elif datos.padre_id is None:
            raise PadreInvalido("Elige de qué almacén depende.")
        self._rechazar_si_repetido(datos.clave, datos.nombre, datos.tipo_enum())
        if datos.padre_id is not None:
            padre = self._padre_valido(datos.padre_id)
            self._exigir_tipo_de_padre(datos.tipo_enum(), padre)
        try:
            almacen = self.almacenes.add(
                Almacen(
                    clave=datos.clave,
                    nombre=datos.nombre,
                    tipo=datos.tipo,
                    padre_id=datos.padre_id,
                    estado=EstadoAlmacen.ACTIVO,
                )
            )
            self.ubicaciones.crear_de_almacen(almacen.id)
            for virtual in UbicacionVirtual:  # una base nueva no las trae (idempotente)
                if self.ubicaciones.virtual(virtual) is None:
                    self.ubicaciones.crear_virtual(virtual)
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="almacen.crear",
                entidad="almacen",
                entidad_id=almacen.id,
                despues=self._instantanea(almacen),
            )
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            self._traducir_unico(exc)
            raise
        return self._ficha_de(almacen)

    def editar(self, almacen_id: uuid.UUID, datos: AlmacenUpdate, actor: Usuario) -> AlmacenOut:
        """AL-02, AL-05: nombre, de quién depende y, sin folios, la clave."""
        almacen = self._bloquear(almacen_id)
        if almacen.estado == EstadoAlmacen.CERRADO:
            raise AlmacenCerrado(almacen, "Ese almacén está cerrado. Reactívalo para editarlo.")
        enviados = datos.model_fields_set
        antes = self._instantanea(almacen)

        if "clave" in enviados and datos.clave is not None and datos.clave != almacen.clave:
            if almacen.id in self.almacenes.con_folios(almacen.id):
                raise ClaveConFolios()
            otro = self.almacenes.get_by_clave(datos.clave)
            if otro is not None and otro.id != almacen.id:
                raise ClaveRepetida()
            almacen.clave = datos.clave
        if "nombre" in enviados and datos.nombre is not None and datos.nombre != almacen.nombre:
            otro = self.almacenes.get_by_nombre(datos.nombre)
            if otro is not None and otro.id != almacen.id:
                raise NombreRepetido()
            almacen.nombre = datos.nombre
        if "padre_id" in enviados and datos.padre_id != almacen.padre_id:
            if almacen.tipo == TipoAlmacen.CENTRAL:
                raise PadreInvalido("El almacén central no depende de otro.")
            if datos.padre_id is None:
                raise PadreInvalido("Elige de qué almacén depende.")
            padre = self._padre_valido(datos.padre_id, hijo=almacen)
            self._exigir_tipo_de_padre(almacen.tipo, padre)
            almacen.padre_id = datos.padre_id

        despues = self._instantanea(almacen)
        if despues != antes:
            try:
                self.auditoria.registrar(
                    usuario_id=actor.id,
                    accion="almacen.editar",
                    entidad="almacen",
                    entidad_id=almacen.id,
                    antes=antes,
                    despues=despues,
                )
                self.session.commit()
            except DBAPIError as exc:
                self.session.rollback()
                self._traducir_unico(exc)
                raise
        else:
            self.session.rollback()  # sin cambios: suelta el bloqueo
        return self._ficha_de(self.obtener(almacen_id))

    def cerrar(
        self, almacen_id: uuid.UUID, datos: CambioEstadoIn | None, actor: Usuario
    ) -> AlmacenOut:
        """AL-03: inactiva el almacén si no queda nada vivo en él."""
        almacen = self._bloquear(almacen_id)
        if almacen.estado == EstadoAlmacen.CERRADO:
            raise Conflicto("Ese almacén ya está cerrado.")
        # Espera a los vales que están moviendo sus existencias y las lee ya confirmadas.
        self.almacenes.bloquear_existencias_de(almacen.id)
        bloqueos = self._bloqueos_de_cierre(almacen, con_detalle=True)
        if bloqueos:
            self.session.rollback()
            raise AlmacenConBloqueos(bloqueos[0]["mensaje"], bloqueos)
        antes = self._instantanea(almacen)
        almacen.estado = EstadoAlmacen.CERRADO
        almacen.cerrado_en = ahora_utc()
        despues = self._instantanea(almacen)
        if datos is not None and datos.motivo:
            despues["motivo"] = datos.motivo
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="almacen.inactivar",
            entidad="almacen",
            entidad_id=almacen.id,
            antes=antes,
            despues=despues,
        )
        self.session.commit()
        return self._ficha_de(self.obtener(almacen_id))

    def reabrir(
        self, almacen_id: uuid.UUID, datos: CambioEstadoIn | None, actor: Usuario
    ) -> AlmacenOut:
        """AL-03: reactiva el mismo almacén (misma clave e historial)."""
        almacen = self._bloquear(almacen_id)
        if almacen.estado == EstadoAlmacen.ACTIVO:
            raise Conflicto("Ese almacén ya está activo.")
        if almacen.padre_id is not None:
            padre = self.almacenes.get(almacen.padre_id)
            if padre is not None and padre.estado != EstadoAlmacen.ACTIVO:
                raise PadreCerrado(
                    f"{padre.nombre} está cerrado. Reactívalo primero para reactivar "
                    f"{almacen.nombre}."
                )
        antes = self._instantanea(almacen)
        almacen.estado = EstadoAlmacen.ACTIVO
        almacen.cerrado_en = None
        despues = self._instantanea(almacen)
        if datos is not None and datos.motivo:
            despues["motivo"] = datos.motivo
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="almacen.reactivar",
            entidad="almacen",
            entidad_id=almacen.id,
            antes=antes,
            despues=despues,
        )
        self.session.commit()
        return self._ficha_de(self.obtener(almacen_id))

    def exigir_abierto(self, almacen: Almacen) -> None:
        """AL-04: lo usan los módulos que reciben o envían algo con un almacén."""
        if almacen.estado == EstadoAlmacen.CERRADO:
            raise AlmacenCerrado(almacen)

    # ---------------------------------------------------------------- piezas internas

    def _bloquear(self, almacen_id: uuid.UUID) -> Almacen:
        almacen = self.almacenes.get_for_update(almacen_id)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    @staticmethod
    def _instantanea(almacen: Almacen) -> dict:
        # La auditoría oculta las llaves que se llamen `clave` (secretos): aquí va como `codigo`.
        return {
            "codigo": almacen.clave,
            "nombre": almacen.nombre,
            "tipo": almacen.tipo,
            "padre_id": almacen.padre_id,
            "estado": almacen.estado,
            "cerrado_en": almacen.cerrado_en,
        }

    def _rechazar_si_repetido(self, clave: str, nombre: str, tipo: TipoAlmacen) -> None:
        if self.almacenes.get_by_clave(clave) is not None:
            raise ClaveRepetida()
        if self.almacenes.get_by_nombre(nombre) is not None:
            raise NombreRepetido()
        if tipo == TipoAlmacen.CENTRAL and self.almacenes.hay_central():
            raise YaHayCentral()

    @staticmethod
    def _traducir_unico(exc: DBAPIError) -> None:
        """Dos altas a la vez: gana una y la otra recibe el 409 de la restricción de la base."""
        if es_restriccion(exc, "uq_almacen_clave"):
            raise ClaveRepetida() from exc
        if es_restriccion(exc, "uq_almacen_nombre"):
            raise NombreRepetido() from exc
        if es_restriccion(exc, "uq_almacen_un_central"):
            raise YaHayCentral() from exc

    def _padre_valido(self, padre_id: uuid.UUID, hijo: Almacen | None = None) -> Almacen:
        padre = self.almacenes.get(padre_id)
        if padre is None:
            raise PadreInvalido("El almacén del que depende no existe.")
        if padre.estado != EstadoAlmacen.ACTIVO:
            raise PadreInvalido(f"{padre.nombre} está cerrado: elige un almacén activo.")
        if hijo is not None:
            if padre.id == hijo.id:
                raise PadreInvalido("Un almacén no puede depender de sí mismo.")
            if padre.id in self._descendientes(hijo.id):
                raise PadreInvalido(
                    f"{padre.nombre} depende de {hijo.nombre}: así la red daría una vuelta."
                )
        return padre

    @staticmethod
    def _exigir_tipo_de_padre(tipo: TipoAlmacen, padre: Almacen) -> None:
        """EK-06: un proyecto depende de un subalmacén y un subalmacén del central, para que la
        ruta X-03 no se rompa por configuración."""
        if tipo == TipoAlmacen.PROYECTO and padre.tipo != TipoAlmacen.SUBALMACEN:
            raise PadreInvalido(
                "Un proyecto depende de un subalmacén (por ejemplo, Contratistas), "
                f"no de {padre.nombre}."
            )
        if tipo == TipoAlmacen.SUBALMACEN and padre.tipo != TipoAlmacen.CENTRAL:
            raise PadreInvalido(
                f"Un subalmacén depende del almacén central (Kepler), no de {padre.nombre}."
            )

    def _descendientes(self, almacen_id: uuid.UUID) -> set[uuid.UUID]:
        hijos: dict[uuid.UUID, list[uuid.UUID]] = {}
        for a in self.almacenes.listar():
            if a.padre_id is not None:
                hijos.setdefault(a.padre_id, []).append(a.id)
        salida: set[uuid.UUID] = set()
        pendientes = [almacen_id]
        while pendientes:
            for h in hijos.get(pendientes.pop(), []):
                if h not in salida:
                    salida.add(h)
                    pendientes.append(h)
        return salida

    # ------------------------------------------------------------- resumen y bloqueos

    def _datos_de_resumen(self, almacen_id: uuid.UUID | None = None) -> _DatosResumen:
        r = self.almacenes
        return _DatosResumen(
            existencias=r.existencias_por_almacen(almacen_id),
            usuarios=r.usuarios_activos_por_almacen(almacen_id),
            traspasos=r.traspasos_en_transito_por_almacen(almacen_id),
            solicitudes=r.solicitudes_abiertas_por_almacen(almacen_id),
            piezas=r.piezas_en_resguardo_por_almacen(almacen_id),
            con_folios=r.con_folios(almacen_id),
        )

    def _bloqueos_de_cierre(
        self, almacen: Almacen, datos: _DatosResumen | None = None, *, con_detalle: bool = False
    ) -> list[dict]:
        """Las condiciones de AL-03 que fallan, en el orden del contrato. Con `con_detalle`
        trae también lo que falta (artículos, traspasos, hijos, usuarios)."""
        datos = datos or self._datos_de_resumen(almacen.id)
        nombre = almacen.nombre
        padre = self.almacenes.get(almacen.padre_id) if almacen.padre_id else None
        regreso = f"a {padre.nombre}" if padre else "a otro almacén"
        bloqueos: list[dict] = []

        traspasos = datos.traspasos.get(almacen.id, 0)
        if traspasos:
            b = {
                "codigo": "CON_TRASPASOS_EN_TRANSITO",
                "mensaje": f"{nombre} tiene {traspasos} traspaso(s) en tránsito. Espera a que "
                "se reciban o cancélalos antes de cerrarlo.",
                "total": traspasos,
            }
            if con_detalle:
                b["traspasos"] = [
                    {
                        "id": str(v.id),
                        "folio": v.folio,
                        "estado": v.estado,
                        "origen": {"id": str(o.id), "clave": o.clave, "nombre": o.nombre},
                        "destino": {"id": str(d.id), "clave": d.clave, "nombre": d.nombre},
                    }
                    for v, o, d in self.almacenes.traspasos_en_transito(almacen.id, LIMITE_DETALLE)
                ]
            bloqueos.append(b)

        unidades, articulos = datos.existencias.get(almacen.id, (0, 0))
        if unidades:
            b = {
                "codigo": "CON_EXISTENCIAS",
                "mensaje": f"{nombre} todavía tiene {unidades} "
                f"{'unidad' if unidades == 1 else 'unidades'} de {articulos} "
                f"{'artículo' if articulos == 1 else 'artículos'}. Regrésalas por traspaso "
                f"{regreso} antes de cerrarlo.",
                "unidades": unidades,
                "total_articulos": articulos,
            }
            if con_detalle:
                b["articulos"] = [
                    {
                        "articulo_id": str(a.id),
                        "codigo": a.codigo,
                        "nombre": a.nombre,
                        "cantidad": c,
                    }
                    for a, c in self.almacenes.articulos_con_existencia(almacen.id, LIMITE_DETALLE)
                ]
            bloqueos.append(b)

        hijos = [h for h in self.almacenes.hijos(almacen.id) if h.estado == EstadoAlmacen.ACTIVO]
        if hijos:
            bloqueos.append(
                {
                    "codigo": "CON_HIJOS_ACTIVOS",
                    "mensaje": (
                        f"Del almacén {nombre} depende {hijos[0].nombre}, que sigue activo."
                        if len(hijos) == 1
                        else f"De {nombre} dependen {len(hijos)} almacenes activos: "
                        + ", ".join(h.nombre for h in hijos)
                        + "."
                    )
                    + " Ciérralos o cámbialos de almacén primero.",
                    "total": len(hijos),
                    "hijos": [
                        {"id": str(h.id), "clave": h.clave, "nombre": h.nombre} for h in hijos
                    ],
                }
            )

        usuarios = datos.usuarios.get(almacen.id, 0)
        if usuarios:
            b = {
                "codigo": "CON_USUARIOS",
                "mensaje": f"{nombre} tiene {usuarios} "
                f"{'usuario asignado' if usuarios == 1 else 'usuarios asignados'}. "
                "Cámbialos de almacén antes de cerrarlo.",
                "total": usuarios,
            }
            if con_detalle:
                b["usuarios"] = [
                    {"id": str(u.id), "nombre": u.nombre, "usuario": u.usuario}
                    for u in self.almacenes.usuarios_activos(almacen.id, LIMITE_DETALLE)
                ]
            bloqueos.append(b)
        return bloqueos

    def _ficha(
        self,
        a: Almacen,
        todos: list[Almacen],
        datos: _DatosResumen | None,
    ) -> AlmacenOut:
        por_id = {x.id: x for x in todos}
        padre = por_id.get(a.padre_id) if a.padre_id else None
        ficha = AlmacenOut(
            id=a.id,
            clave=a.clave,
            nombre=a.nombre,
            tipo=a.tipo,
            estado=a.estado,
            padre_id=a.padre_id,
            padre_clave=padre.clave if padre else None,
            cerrado_en=a.cerrado_en,
            hijos=[AlmacenHijoOut.model_validate(h) for h in todos if h.padre_id == a.id],
        )
        if datos is not None:
            ficha.resumen = self._resumen(a, padre, datos)
        return ficha

    def _resumen(
        self, a: Almacen, padre: Almacen | None, datos: _DatosResumen
    ) -> ResumenAlmacenOut:
        unidades, articulos = datos.existencias.get(a.id, (0, 0))
        bloqueos = self._bloqueos_de_cierre(a, datos) if a.estado == EstadoAlmacen.ACTIVO else []
        return ResumenAlmacenOut(
            existencias=ExistenciasResumenOut(unidades=unidades, articulos=articulos),
            piezas_en_resguardo=datos.piezas.get(a.id, 0),
            usuarios=datos.usuarios.get(a.id, 0),
            traspasos_en_transito=datos.traspasos.get(a.id, 0),
            solicitudes_compra_abiertas=datos.solicitudes.get(a.id, 0),
            tiene_folios=a.id in datos.con_folios,
            puede_cerrar=a.estado == EstadoAlmacen.ACTIVO and not bloqueos,
            puede_reabrir=a.estado == EstadoAlmacen.CERRADO
            and (padre is None or padre.estado == EstadoAlmacen.ACTIVO),
            bloqueos_cierre=[
                BloqueoCierreOut(codigo=b["codigo"], mensaje=b["mensaje"]) for b in bloqueos
            ],
        )

    def _ficha_de(self, almacen: Almacen) -> AlmacenOut:
        """La ficha de un almacén tras un cambio (sin el resumen)."""
        return self._ficha(almacen, self.almacenes.listar(), None)

    def existencias(
        self, almacen_id: uuid.UUID, filtros: AlmacenFilters, pagina: Paginacion
    ) -> ExistenciasOut:
        """Existencias y disponibles por artículo de un almacén (sin costos, RG-12)."""
        almacen = self.obtener(almacen_id)
        ubicacion = self.ubicacion_de_almacen(almacen.id)
        filas, total = self.almacenes.existencias_de_almacen(
            ubicacion.id,
            FiltroExistencias(
                q=filtros.q,
                categoria_id=filtros.categoria_id,
                activo=filtros.activo,
                offset=pagina.offset,
                limit=pagina.limit,
            ),
        )
        return ExistenciasOut(
            almacen=AlmacenResumenOut.model_validate(almacen),
            elementos=[
                ExistenciaOut(
                    articulo_id=art.id,
                    codigo=art.codigo,
                    nombre=art.nombre,
                    marca=art.marca,
                    talla=art.talla,
                    unidad=art.unidad,
                    control=art.control,
                    retornable=art.retornable,
                    categoria_id=art.categoria_id,
                    categoria_nombre=categoria,
                    activo=art.activo,
                    cantidad=cantidad,
                    disponible=int(disponible or 0),
                )
                for art, categoria, cantidad, disponible in filas
            ],
            total=total,
        )

    def existencias_de_articulo(self, articulo_id: uuid.UUID) -> list[tuple[Almacen, int, int]]:
        """Dónde hay de un artículo: `(almacen, cantidad, disponible)` por almacén."""
        return [
            (almacen, cantidad, int(disponible or 0))
            for almacen, cantidad, disponible in self.almacenes.existencias_de_articulo(articulo_id)
        ]

    def posesion_de_articulo(self, articulo_id: uuid.UUID, control: str) -> list:
        """Quién tiene un artículo y desde cuándo (SG-02), por cantidad o por pieza."""
        return self.almacenes.posesion_de_articulo(articulo_id, control)

    def poseedores_de_articulo(self, articulo_id: uuid.UUID) -> list[tuple]:
        """Quién lo tiene: `(trabajador, cantidad)` por trabajador con existencia."""
        return [(t, c) for t, c in self.almacenes.poseedores_de_articulo(articulo_id)]
