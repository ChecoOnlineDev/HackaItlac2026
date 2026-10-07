"""Seguimiento de piezas (C-13): dónde está cada pieza y quién la tiene. SOLO LEE.

El alcance es el de la ficha de la pieza (C-02, AC-06): con `almacenes.todos` se ven todas; sin él,
solo las que `ConsultaRepository._pieza_visible` deja ver (su almacén, las que tiene un trabajador
y el tránsito desde o hacia su almacén). Nunca devuelve CURP, NSS ni costos (RG-12, RG-13).
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.paginacion import Paginacion
from app.core.tiempo import hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.consulta import exportacion
from app.modulos.consulta.repository_seguimiento import (
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
    DondeEstaOut,
    PaginaSeguimiento,
    PiezaSeguimientoItem,
    ResumenSeguimiento,
    SeguimientoFilters,
    TrabajadorSeguimientoOut,
    UbicacionSeguimiento,
    ValeSeguimientoOut,
)

LONGITUD_MINIMA_BUSQUEDA = 2
TEXTO_SIN_UBICACION = "Sin ubicación"

_VACIO = ResumenSeguimiento(total=0, en_almacen=0, en_resguardo=0, en_transito=0, no_aptas=0)


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
        self.acceso = AccesoService(session)

    def _filtro(self, filtros: SeguimientoFilters, usuario: Usuario) -> FiltroSeguimiento | None:
        """El filtro con el alcance del usuario (AC-06); `None` si no puede ver ninguna pieza."""
        palabras = tuple((filtros.q or "").split()[:MAXIMO_PALABRAS])
        common = {
            "palabras": palabras,
            "articulo_id": filtros.articulo_id,
            "estado": filtros.estado.value if filtros.estado else None,
            "ubicacion": filtros.ubicacion.value if filtros.ubicacion else None,
            "serie_pendiente": filtros.serie_pendiente,
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
    def _busqueda_corta(filtros: SeguimientoFilters) -> bool:
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
        elementos = [self._item(f, usuario, todos, hoy) for f in filas]
        return elementos, total, filtro

    @staticmethod
    def _item(f: Any, usuario: Usuario, todos: bool, hoy: date) -> PiezaSeguimientoItem:
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
        )

    def seguimiento_piezas(
        self, filtros: SeguimientoFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaSeguimiento:
        """C-13: todas las piezas dentro del alcance, cada una con dónde está o quién la tiene,
        desde cuándo y con qué vale. El resumen cuenta lo del texto, el artículo y el almacén."""
        elementos, total, filtro = self._elementos(filtros, usuario, pagina)
        resumen = ResumenSeguimiento(**self.repo.resumen(filtro)) if filtro else _VACIO
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
