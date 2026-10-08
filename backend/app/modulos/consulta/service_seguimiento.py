"""Seguimiento de piezas (C-13): dónde está cada pieza y quién la tiene. SOLO LEE.

El alcance es el de la ficha de la pieza (C-02, AC-06): con `almacenes.todos` se ven todas; sin él,
solo las que `ConsultaRepository._pieza_visible` deja ver (su almacén, las que tiene un trabajador
y el tránsito desde o hacia su almacén). Nunca devuelve CURP, NSS ni costos (RG-12, RG-13).
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.paginacion import Paginacion
from app.core.tiempo import hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.consulta import exportacion
from app.modulos.consulta.repository_cantidad import CantidadRepository, FiltroCantidad
from app.modulos.consulta.repository_seguimiento import (
    CATEGORIAS_ALTO_VALOR,
    MAXIMO_PALABRAS,
    FiltroSeguimiento,
    SeguimientoRepository,
)
from app.modulos.consulta.schemas import (
    MENSAJE_BUSQUEDA_CORTA,
    MENSAJE_SIN_REGISTROS,
    TEXTO_ESTADO_PIEZA,
    TEXTO_VIRTUAL,
)
from app.modulos.consulta.schemas_seguimiento import (
    AlmacenSeguimientoOut,
    ArticuloSeguimientoOut,
    CantidadFilters,
    CantidadSeguimientoItem,
    DondeEstaOut,
    PaginaCantidad,
    PaginaSeguimiento,
    PiezaSeguimientoItem,
    ResumenCantidad,
    ResumenSeguimiento,
    SeguimientoFilters,
    TrabajadorSeguimientoOut,
    UbicacionSeguimiento,
    ValeSeguimientoOut,
)
from app.modulos.trabajadores.models import EstadoTrabajador
from app.modulos.trabajadores.service import TrabajadorService, calcular_vigencia

LONGITUD_MINIMA_BUSQUEDA = 2
TEXTO_SIN_UBICACION = "Sin ubicación"

_VACIO = ResumenSeguimiento(total=0, en_almacen=0, en_resguardo=0, en_transito=0, no_aptas=0)
_VACIO_CANTIDAD = ResumenCantidad(renglones=0, unidades=0, articulos=0, trabajadores=0)


def _donde_esta(f: Any) -> DondeEstaOut:
    """La ubicación de una fila del listado, en español llano."""
    if f.ub_tipo is None:
        return DondeEstaOut(tipo=UbicacionSeguimiento.NINGUNA, texto=TEXTO_SIN_UBICACION)
    if f.ub_tipo == "ALMACEN":
        return DondeEstaOut(
            tipo=UbicacionSeguimiento.ALMACEN,
            texto=f"En {f.ub_almacen}",
            almacen=AlmacenSeguimientoOut(
                id=f.ub_almacen_id, clave=f.ub_clave, nombre=f.ub_almacen
            ),
        )
    if f.ub_tipo == "TRABAJADOR":
        return DondeEstaOut(
            tipo=UbicacionSeguimiento.TRABAJADOR,
            texto=f"En resguardo de {f.ub_trabajador}",
            trabajador=TrabajadorSeguimientoOut(
                id=f.ub_trabajador_id, numero_empleado=f.ub_numero, nombre=f.ub_trabajador
            ),
        )
    if f.ub_virtual == "EN_TRANSITO":
        hacia = None
        if f.vale_destino_almacen_id is not None and f.trs_nombre is not None:
            hacia = AlmacenSeguimientoOut(
                id=f.vale_destino_almacen_id, clave=f.trs_clave, nombre=f.trs_nombre
            )
        return DondeEstaOut(
            tipo=UbicacionSeguimiento.TRANSITO,
            texto=f"En tránsito a {hacia.nombre}" if hacia else "En tránsito",
            almacen=hacia,
        )
    if f.ub_virtual == "BAJA":
        return DondeEstaOut(tipo=UbicacionSeguimiento.BAJA, texto="De baja")
    return DondeEstaOut(
        tipo=UbicacionSeguimiento.OTRA, texto=TEXTO_VIRTUAL.get(f.ub_virtual, f.ub_virtual or "")
    )


class SeguimientoService:
    def __init__(self, session: Session) -> None:
        self.repo = SeguimientoRepository(session)
        self.cantidad = CantidadRepository(session)
        self.acceso = AccesoService(session)
        self.trabajadores = TrabajadorService(session)

    def _filtro(self, filtros: SeguimientoFilters, usuario: Usuario) -> FiltroSeguimiento | None:
        """El filtro con el alcance del usuario (AC-06); `None` si no puede ver ninguna pieza."""
        palabras = tuple((filtros.q or "").split()[:MAXIMO_PALABRAS])
        common = {
            "palabras": palabras,
            "articulo_id": filtros.articulo_id,
            "estado": filtros.estado.value if filtros.estado else None,
            "ubicacion": filtros.ubicacion.value if filtros.ubicacion else None,
            "serie_pendiente": filtros.serie_pendiente,
            "alto_valor": filtros.alto_valor,
        }
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return FiltroSeguimiento(almacen_id=filtros.almacen_id, **common)
        if usuario.almacen_id is None:
            return None
        if filtros.almacen_id is not None and filtros.almacen_id != usuario.almacen_id:
            return None  # pedir otro almacén no devuelve nada (no es un error)
        ver_trabajadores = P.TRABAJADORES_VER in self.acceso.permisos_de(usuario)
        return FiltroSeguimiento(
            almacen_id=filtros.almacen_id,
            visibles=(usuario.almacen_id, ver_trabajadores),
            **common,
        )

    @staticmethod
    def _busqueda_corta(filtros: SeguimientoFilters | CantidadFilters) -> bool:
        texto = (filtros.q or "").strip()
        return 0 < len(texto) < LONGITUD_MINIMA_BUSQUEDA

    def _elementos(
        self, filtros: SeguimientoFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[PiezaSeguimientoItem], int, FiltroSeguimiento | None]:
        filtro = self._filtro(filtros, usuario)
        if filtro is None or self._busqueda_corta(filtros):
            return [], 0, None
        todos = self.acceso.puede_operar_todos_los_almacenes(usuario)
        filas, total = self.repo.piezas(
            filtro,
            pagina.offset if pagina else None,
            pagina.limit if pagina else None,
        )
        hoy = hoy_mx()
        avisos = self._avisos_de_trabajadores(
            {f.ub_trabajador_id for f in filas if self._es_alto_valor_en_resguardo(f)}, hoy
        )
        elementos = [self._item(f, usuario, todos, hoy, avisos) for f in filas]
        return elementos, total, filtro

    @staticmethod
    def _es_alto_valor_en_resguardo(f: Any) -> bool:
        return (
            f.categoria_nombre in CATEGORIAS_ALTO_VALOR
            and f.ub_tipo == "TRABAJADOR"
            and f.estado != "BAJA"
        )

    def _avisos_de_trabajadores(self, ids: set[uuid.UUID], hoy: date) -> dict[uuid.UUID, str]:
        """SG-06: por trabajador dado de baja o con el contrato vencido, el aviso para sus piezas
        de alto valor. Los vigentes (y quien aún no empieza) no traen aviso."""
        if not ids:
            return {}
        periodos = self.trabajadores.trabajadores.periodos_de(list(ids))
        avisos: dict[uuid.UUID, str] = {}
        for trabajador_id in ids:
            trabajador = self.trabajadores.trabajadores.get(trabajador_id)
            if trabajador is None:
                continue
            aviso = self._aviso_de(trabajador, periodos.get(trabajador_id, []), hoy)
            if aviso:
                avisos[trabajador_id] = aviso
        return avisos

    @staticmethod
    def _aviso_de(trabajador: Any, periodos: list, hoy: date) -> str | None:
        """SG-06: el texto si el trabajador está dado de baja o su contrato terminó."""
        if trabajador.estado == EstadoTrabajador.INACTIVO:
            return f"La tiene {trabajador.nombre}, que ya fue dado de baja. Hay que recuperarla."
        if trabajador.estado == EstadoTrabajador.BAJA_EN_PROCESO:
            return (
                f"La tiene {trabajador.nombre}, cuya baja está en proceso. "
                "Hay que recuperarla antes de cerrarla."
            )
        if calcular_vigencia(trabajador.estado, periodos, hoy).vigente:
            return None
        if not periodos or any(p.inicio > hoy for p in periodos):
            return None  # sin contrato todavía o por empezar: no es un contrato vencido
        fin = max(p.fin for p in periodos)
        return (
            f"La tiene {trabajador.nombre}, cuyo contrato terminó el {fin:%d/%m/%Y}. "
            "Hay que recuperarla o renovar su contrato."
        )

    def aviso_de_pieza(self, pieza: Any, categoria_nombre: str | None) -> str | None:
        """SG-06: el aviso de la ficha de una pieza de alto valor en resguardo de un trabajador
        dado de baja o con contrato vencido. `pieza` es la fila de `Pieza`."""
        if categoria_nombre not in CATEGORIAS_ALTO_VALOR or pieza.estado == "BAJA":
            return None
        trabajador_id = self.repo.trabajador_de_ubicacion(pieza.ubicacion_id)
        if trabajador_id is None:
            return None
        return self._avisos_de_trabajadores({trabajador_id}, hoy_mx()).get(trabajador_id)

    @staticmethod
    def _item(
        f: Any, usuario: Usuario, todos: bool, hoy: date, avisos: dict[uuid.UUID, str]
    ) -> PiezaSeguimientoItem:
        vale = None
        if f.vale_id is not None and (
            todos
            or (
                usuario.almacen_id is not None
                and usuario.almacen_id in (f.vale_almacen_id, f.vale_destino_almacen_id)
            )
        ):  # AC-06: el vale de otro almacén no se nombra
            vale = ValeSeguimientoOut(id=f.vale_id, folio=f.folio)
        hasta = f.inspeccion_vigente_hasta
        return PiezaSeguimientoItem(
            id=f.id,
            codigo=f.codigo,
            numero_serie=f.numero_serie,
            articulo=ArticuloSeguimientoOut(
                id=f.articulo_id,
                codigo=f.articulo_codigo,
                nombre=f.articulo_nombre,
                marca=f.articulo_marca,
            ),
            estado=f.estado,
            estado_texto=TEXTO_ESTADO_PIEZA.get(f.estado, f.estado),
            inspeccion_vigente=hasta is not None and hasta >= hoy,
            inspeccion_vigente_hasta=hasta,
            ubicacion=_donde_esta(f),
            desde=f.desde,
            vale=vale,
            alto_valor=f.categoria_nombre in CATEGORIAS_ALTO_VALOR,
            aviso=avisos.get(f.ub_trabajador_id) if f.ub_trabajador_id else None,
        )

    def seguimiento_piezas(
        self, filtros: SeguimientoFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaSeguimiento:
        """C-13: todas las piezas dentro del alcance, cada una con dónde está o quién la tiene,
        desde cuándo y con qué vale. El resumen cuenta lo del texto, el artículo y el almacén."""
        elementos, total, filtro = self._elementos(filtros, usuario, pagina)
        resumen = _VACIO
        if filtro:
            filtro_cantidad = self._filtro_cantidad(
                CantidadFilters(
                    q=filtros.q, articulo_id=filtros.articulo_id, almacen_id=filtros.almacen_id
                ),
                usuario,
            )
            por_cantidad = (
                self.cantidad.resumen(filtro_cantidad)["articulos"] if filtro_cantidad else 0
            )
            resumen = ResumenSeguimiento(
                **self.repo.resumen(filtro), articulos_por_cantidad=por_cantidad
            )
        sin = total == 0
        mensaje = None
        if self._busqueda_corta(filtros):
            mensaje = MENSAJE_BUSQUEDA_CORTA
        elif sin:
            mensaje = MENSAJE_SIN_REGISTROS
        return PaginaSeguimiento(
            elementos=elementos, total=total, sin_registros=sin, mensaje=mensaje, resumen=resumen
        )

    def csv_seguimiento_piezas(
        self, filtros: SeguimientoFilters, usuario: Usuario
    ) -> tuple[bytes, str]:
        elementos, _, _ = self._elementos(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Código de la pieza",
                "Número de serie",
                "Código del artículo",
                "Artículo",
                "Marca",
                "Estado",
                "Inspección vigente hasta",
                "Dónde está",
                "Número de empleado",
                "Trabajador",
                "Desde",
                "Folio del vale",
            ],
            [
                (
                    e.codigo,
                    e.numero_serie,
                    e.articulo.codigo,
                    e.articulo.nombre,
                    e.articulo.marca,
                    e.estado_texto,
                    e.inspeccion_vigente_hasta,
                    e.ubicacion.texto,
                    e.ubicacion.trabajador.numero_empleado if e.ubicacion.trabajador else None,
                    e.ubicacion.trabajador.nombre if e.ubicacion.trabajador else None,
                    e.desde,
                    e.vale.folio if e.vale else None,
                )
                for e in elementos
            ],
        )
        return contenido, f"seguimiento-piezas-{hoy_mx():%Y%m%d}.csv"

    # ===================================================================== por cantidad (SG-01)

    def _filtro_cantidad(self, filtros: CantidadFilters, usuario: Usuario) -> FiltroCantidad | None:
        """El filtro con el alcance del usuario (AC-06); `None` si no puede ver nada. Sin
        `almacenes.todos` solo ve lo que se entregó con un vale de su almacén, y solo si puede ver
        trabajadores."""
        palabras = tuple((filtros.q or "").split()[:MAXIMO_PALABRAS])
        comun = {"palabras": palabras, "articulo_id": filtros.articulo_id}
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return FiltroCantidad(almacen_id=filtros.almacen_id, **comun)
        if usuario.almacen_id is None:
            return None
        if P.TRABAJADORES_VER not in self.acceso.permisos_de(usuario):
            return None
        if filtros.almacen_id is not None and filtros.almacen_id != usuario.almacen_id:
            return None  # pedir otro almacén no devuelve nada (no es un error)
        return FiltroCantidad(solo_almacen_id=usuario.almacen_id, **comun)

    def _renglones_cantidad(
        self, filtros: CantidadFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[CantidadSeguimientoItem], int, FiltroCantidad | None]:
        filtro = self._filtro_cantidad(filtros, usuario)
        if filtro is None or self._busqueda_corta(filtros):
            return [], 0, None
        todos = self.acceso.puede_operar_todos_los_almacenes(usuario)
        filas, total = self.cantidad.renglones(
            filtro, pagina.offset if pagina else None, pagina.limit if pagina else None
        )
        elementos = []
        for f in filas:
            propio = todos or (
                usuario.almacen_id is not None and f.vale_almacen_id == usuario.almacen_id
            )
            elementos.append(
                CantidadSeguimientoItem(
                    trabajador=TrabajadorSeguimientoOut(
                        id=f.trabajador_id, numero_empleado=f.numero_empleado, nombre=f.trabajador
                    ),
                    articulo=ArticuloSeguimientoOut(
                        id=f.articulo_id,
                        codigo=f.articulo_codigo,
                        nombre=f.articulo_nombre,
                        marca=f.articulo_marca,
                    ),
                    unidad=f.articulo_unidad,
                    cantidad=f.cantidad,
                    desde=f.desde,
                    # AC-06: el folio de un vale de otro almacén no se muestra
                    vale=ValeSeguimientoOut(id=f.vale_id, folio=f.folio)
                    if f.vale_id is not None and propio
                    else None,
                    almacen=AlmacenSeguimientoOut(
                        id=f.vale_almacen_id, clave=f.almacen_clave, nombre=f.almacen_nombre
                    )
                    if f.vale_almacen_id is not None
                    else None,
                )
            )
        return elementos, total, filtro

    def seguimiento_cantidad(
        self, filtros: CantidadFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaCantidad:
        """SG-01: los artículos por cantidad en resguardo de trabajadores, con la cantidad, desde
        cuándo y el folio de la entrega más reciente."""
        elementos, total, filtro = self._renglones_cantidad(filtros, usuario, pagina)
        resumen = ResumenCantidad(**self.cantidad.resumen(filtro)) if filtro else _VACIO_CANTIDAD
        sin = total == 0
        mensaje = None
        if self._busqueda_corta(filtros):
            mensaje = MENSAJE_BUSQUEDA_CORTA
        elif sin:
            mensaje = MENSAJE_SIN_REGISTROS
        return PaginaCantidad(
            elementos=elementos, total=total, sin_registros=sin, mensaje=mensaje, resumen=resumen
        )

    def csv_seguimiento_cantidad(
        self, filtros: CantidadFilters, usuario: Usuario
    ) -> tuple[bytes, str]:
        elementos, _, _ = self._renglones_cantidad(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Número de empleado",
                "Trabajador",
                "Código del artículo",
                "Artículo",
                "Marca",
                "Cantidad",
                "Unidad",
                "Desde",
                "Folio del vale",
                "Almacén",
            ],
            [
                (
                    e.trabajador.numero_empleado,
                    e.trabajador.nombre,
                    e.articulo.codigo,
                    e.articulo.nombre,
                    e.articulo.marca,
                    e.cantidad,
                    e.unidad,
                    e.desde,
                    e.vale.folio if e.vale else None,
                    e.almacen.nombre if e.almacen else None,
                )
                for e in elementos
            ],
        )
        return contenido, f"seguimiento-por-cantidad-{hoy_mx():%Y%m%d}.csv"
