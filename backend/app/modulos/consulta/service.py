"""Consulta: escaneo, búsqueda, ficha de pieza y reportes. SOLO LEE; nunca hace `commit`.

Las reglas que aplica (C-01 a C-08, C-11) se ven en el nombre de cada método. Los permisos de
información se verifican aquí con `AccesoService`, por clave y no por nombre de rol.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.paginacion import Pagina, Paginacion
from app.core.tiempo import ZONA_MX, hoy_mx
from app.modulos.acceso.alcance_almacenes import dentro_del_alcance
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.catalogo.alto_valor import calcular_alto_valor
from app.modulos.catalogo.codigos import CodigoService, normalizar
from app.modulos.catalogo.exceptions import PiezaNoEncontrada
from app.modulos.catalogo.models import Articulo, Categoria, Pieza, TipoCodigo
from app.modulos.catalogo.service import CatalogoService
from app.modulos.consulta import exportacion
from app.modulos.consulta.exceptions import RangoFechasInvalido
from app.modulos.consulta.repository import ConsultaRepository, Pendiente
from app.modulos.consulta.schemas import (
    MENSAJE_BUSQUEDA_CORTA,
    MENSAJE_SIN_REGISTROS,
    MENSAJE_SIN_RESULTADOS,
    TEXTO_ESTADO_PIEZA,
    TEXTO_ESTADO_TRABAJADOR,
    TEXTO_TIPO_VALE,
    TEXTO_VIRTUAL,
    AdeudoReporteItem,
    AdeudosFilters,
    ArticuloPiezaOut,
    BusquedaArticuloItem,
    BusquedaOut,
    BusquedaPiezaItem,
    BusquedaTrabajadorItem,
    ConsumoFilters,
    ConsumoReporteItem,
    ConsumoTrabajadorItem,
    EscaneoOut,
    ExistenciaReporteItem,
    ExistenciasFilters,
    HistorialItem,
    InspeccionOut,
    MovimientoReporteItem,
    MovimientosFilters,
    PaginaReporte,
    PiezaFichaOut,
    ResumenArticulo,
    ResumenDesconocido,
    ResumenPieza,
    ResumenTrabajador,
    ResumenVale,
    TipoEscaneo,
    TipoHistorial,
    UbicacionOut,
    UsuarioOpcionOut,
    UsuariosOpcionesOut,
)
from app.modulos.consulta.service_seguimiento import SeguimientoService
from app.modulos.inspecciones.service import InspeccionService
from app.modulos.trabajadores.models import Trabajador
from app.modulos.trabajadores.repository import TrabajadorRepository
from app.modulos.trabajadores.service import TrabajadorService, calcular_vigencia, elegir_periodo

LONGITUD_MINIMA_BUSQUEDA = 2
TEXTO_OTRO_ALMACEN = "Otro almacén"
TEXTO_RESULTADO_INSPECCION = {"APTO": "Apta", "NO_APTO": "No apta"}


# ------------------------------------------------------------------------------ utilidades


def rango_utc(desde: date | None, hasta: date | None) -> tuple[datetime | None, datetime | None]:
    """Un rango de fechas locales de México como `[inicio, fin)` en UTC sin zona.

    El día `hasta` entra completo: termina a las 23:59:59.999999 hora de México, que es la
    medianoche siguiente menos un instante. Un rango invertido se rechaza.
    """
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoFechasInvalido(
            detalles=[{"campo": "desde", "mensaje": "La fecha inicial es posterior a la final."}]
        )

    def _utc(dia: date) -> datetime:
        return datetime.combine(dia, time.min, tzinfo=ZONA_MX).astimezone(UTC).replace(tzinfo=None)

    inicio = _utc(desde) if desde is not None else None
    fin = _utc(hasta + timedelta(days=1)) if hasta is not None else None
    return inicio, fin


def _fecha(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def _ubicacion(fila: Any, prefijo: str) -> UbicacionOut | None:
    """La ubicación que describen las columnas de un `Lugar` (`None` si no hay ubicación)."""
    tipo = getattr(fila, f"{prefijo}_tipo")
    if tipo is None:
        return None
    clave = getattr(fila, f"{prefijo}_clave")
    almacen = getattr(fila, f"{prefijo}_almacen")
    numero = getattr(fila, f"{prefijo}_numero")
    nombre_trabajador = getattr(fila, f"{prefijo}_trabajador")
    virtual = getattr(fila, f"{prefijo}_virtual")
    if tipo == "ALMACEN":
        texto = f"{almacen} ({clave})"
    elif tipo == "TRABAJADOR":
        texto = f"{nombre_trabajador} ({numero})"
    else:
        texto = TEXTO_VIRTUAL.get(virtual, virtual or "")
    return UbicacionOut(
        tipo=tipo,
        texto=texto,
        almacen_id=getattr(fila, f"{prefijo}_almacen_id"),
        almacen_clave=clave,
        trabajador_id=getattr(fila, f"{prefijo}_trabajador_id"),
        numero_empleado=numero,
        virtual=virtual,
    )


def _texto_ubicacion(fila: Any, prefijo: str) -> str:
    ubicacion = _ubicacion(fila, prefijo)
    return ubicacion.texto if ubicacion else ""


TEXTO_DIRECCION = {"ENTRADA": "Entrada", "SALIDA": "Salida", "EN_CAMINO": "En camino"}


def direccion_para(fila: Any, almacen_id: uuid.UUID | None) -> str | None:
    """SG-05: qué fue el movimiento para el almacén que se ve. ENTRADA si llega a sus
    ubicaciones desde fuera, SALIDA si sale de ellas, EN_CAMINO si es un traspaso hacia él que
    aún no llega, y `None` si no se filtró por almacén o no lo toca directamente."""
    if almacen_id is None:
        return None
    desde_aqui = dentro_del_alcance(fila.origen_almacen_id, almacen_id)
    hacia_aqui = dentro_del_alcance(fila.destino_almacen_id, almacen_id)
    if hacia_aqui and not desde_aqui:
        return "ENTRADA"
    if desde_aqui and not hacia_aqui:
        return "SALIDA"
    if (
        not desde_aqui
        and not hacia_aqui
        and dentro_del_alcance(fila.vale_destino_almacen_id, almacen_id)
    ):
        return "EN_CAMINO"
    return None


@dataclass(frozen=True)
class Alcance:
    """Qué almacén puede ver el usuario (AC-06, C-11). `vacio` = no puede ver ninguno."""

    almacen_id: uuid.UUID | frozenset[uuid.UUID] | None
    vacio: bool = False


class ConsultaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.consultas = ConsultaRepository(session)
        self.acceso = AccesoService(session)
        self.codigos = CodigoService(session)
        self.trabajadores = TrabajadorService(session)

    # =================================================================== alcance (AC-06)

    def _alcance(self, usuario: Usuario, almacen_id: uuid.UUID | None) -> Alcance:
        """Con `almacenes.todos`, todos los almacenes (o el del filtro). Sin él, solo el
        asignado: si el filtro pide otro almacén, no ve nada (no es un error). Sin almacén
        asignado ni `almacenes.todos`, no ve nada."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return Alcance(almacen_id)
        asignados = self.acceso.almacenes_del_usuario(usuario.id)
        if not asignados:
            return Alcance(None, vacio=True)
        if almacen_id is not None and almacen_id not in asignados:
            return Alcance(None, vacio=True)
        return Alcance(almacen_id if almacen_id is not None else frozenset(asignados))

    @staticmethod
    def _pagina[T](elementos: list[T], total: int) -> PaginaReporte[T]:
        sin = total == 0
        return PaginaReporte[Any](
            elementos=elementos,
            total=total,
            sin_registros=sin,
            mensaje=MENSAJE_SIN_REGISTROS if sin else None,
        )

    # ============================================================== opciones de filtros

    def opciones_usuarios(self, usuario: Usuario) -> UsuariosOpcionesOut:
        """Quién hizo vales, para el filtro de la bitácora (C-11): con `almacenes.todos` de todos
        los almacenes; sin él, solo de su almacén (AC-06)."""
        alcance = self._alcance(usuario, None)
        if alcance.vacio:
            return UsuariosOpcionesOut(elementos=[])
        filas = self.consultas.usuarios_que_hicieron_vales(alcance.almacen_id)
        return UsuariosOpcionesOut(
            elementos=[UsuarioOpcionOut(id=u.id, nombre=u.nombre, usuario=u.usuario) for u in filas]
        )

    # ========================================================================== escaneo

    def escanear(
        self, codigo: str, usuario: Usuario, almacen_id: uuid.UUID | None = None
    ) -> EscaneoOut:
        """C-01, C-02, C-03, C-04: qué es el código y un resumen. Lo que el usuario no puede ver
        llega como DESCONOCIDO. Acepta el código de una credencial, un artículo o una pieza, el
        QR (token) o el folio de un vale y el número de empleado tecleado.

        TR-11: con `almacen_id` (el origen de un traspaso) el artículo y la pieza traen
        `disponible`: lo que hay en ese almacén (0 si no hay; el servidor rechaza con X-02)."""
        permisos = self.acceso.permisos_de(usuario)
        codigo = normalizar(codigo)
        fila = self.codigos.identificar(codigo)
        if fila is not None:
            return self._escaneo_por_codigo(fila.tipo, fila.ref_id, permisos, usuario, almacen_id)
        if P.TRABAJADORES_VER in permisos:
            trabajador = self.consultas.trabajador_por_numero(codigo)
            if trabajador is not None:
                return self._escaneo_trabajador(trabajador)
        if P.VALES_VER in permisos:
            vale_id = self.consultas.vale_id_por_token_o_folio(codigo)
            if vale_id is not None:
                return self._escaneo_vale(vale_id, usuario)
        return self._desconocido()

    @staticmethod
    def _desconocido() -> EscaneoOut:
        return EscaneoOut(tipo=TipoEscaneo.DESCONOCIDO, id=None, resumen=ResumenDesconocido())

    def _escaneo_por_codigo(
        self,
        tipo: str,
        ref_id: uuid.UUID,
        permisos: frozenset[str],
        usuario: Usuario,
        almacen_id: uuid.UUID | None = None,
    ) -> EscaneoOut:
        if tipo == TipoCodigo.TRABAJADOR and P.TRABAJADORES_VER in permisos:
            trabajador = self.consultas.trabajador(ref_id)
            return self._escaneo_trabajador(trabajador) if trabajador else self._desconocido()
        if tipo == TipoCodigo.ARTICULO and P.CATALOGO_VER in permisos:
            return self._escaneo_articulo(ref_id, usuario, almacen_id)
        if tipo == TipoCodigo.PIEZA and P.CATALOGO_VER in permisos:
            return self._escaneo_pieza(ref_id, usuario, permisos, almacen_id)
        if tipo == TipoCodigo.VALE and P.VALES_VER in permisos:
            return self._escaneo_vale(ref_id, usuario)
        return self._desconocido()

    def _escaneo_trabajador(self, trabajador: Trabajador) -> EscaneoOut:
        """C-01: el trabajador, su vigencia y lo que tiene en resguardo. Sin CURP ni NSS."""
        vigencia = self.trabajadores.evaluar_vigencia(trabajador)
        periodo = self.trabajadores.periodo_vigente(trabajador)
        pendientes = self.trabajadores.pendientes_de(trabajador.id)
        resumen = ResumenTrabajador(
            numero_empleado=trabajador.numero_empleado,
            nombre=trabajador.nombre,
            estado=trabajador.estado,
            estado_texto=TEXTO_ESTADO_TRABAJADOR.get(trabajador.estado, trabajador.estado),
            vigente=vigencia.vigente,
            motivo_no_vigente=vigencia.motivo,
            puesto=periodo.puesto if periodo else None,
            area_obra=periodo.area_obra if periodo else None,
            vigente_hasta=periodo.fin if periodo else None,
            pendientes=sum(p.cantidad for p in pendientes),
        )
        return EscaneoOut(tipo=TipoEscaneo.TRABAJADOR, id=trabajador.id, resumen=resumen)

    def _escaneo_articulo(
        self, articulo_id: uuid.UUID, usuario: Usuario, almacen_id: uuid.UUID | None = None
    ) -> EscaneoOut:
        """C-03: el artículo y cuánto hay en los almacenes (sin costo, RG-12). AC-06: sin
        `almacenes.todos`, `existencia_total` es lo que hay en SU almacén."""
        encontrado = self.consultas.articulo(articulo_id)
        if encontrado is None:
            return self._desconocido()
        articulo, categoria = encontrado
        resumen = ResumenArticulo(
            codigo=articulo.codigo,
            nombre=articulo.nombre,
            marca=articulo.marca,
            categoria=categoria,
            control=articulo.control,
            retornable=articulo.retornable,
            unidad=articulo.unidad,
            activo=articulo.activo,
            existencia_total=self._existencia_visible(articulo.id, usuario),
            disponible=self._disponible_articulo(articulo.id, usuario, almacen_id),
        )
        return EscaneoOut(tipo=TipoEscaneo.ARTICULO, id=articulo.id, resumen=resumen)

    def _disponible_articulo(
        self, articulo_id: uuid.UUID, usuario: Usuario, almacen_id: uuid.UUID | None
    ) -> int | None:
        """TR-11: lo que hay del artículo en `almacen_id` (dentro del alcance, AC-06); `None` si
        no se pidió almacén."""
        if almacen_id is None:
            return None
        alcance = self._alcance(usuario, almacen_id)
        if alcance.vacio or alcance.almacen_id is None:
            return 0
        return self.consultas.existencia_total_en_almacenes(articulo_id, alcance.almacen_id)

    def _existencia_visible(self, articulo_id: uuid.UUID, usuario: Usuario) -> int:
        """AC-06: lo que hay del artículo en todos los almacenes con `almacenes.todos`; sin él,
        solo lo que hay en el almacén del usuario (0 si no tiene almacén)."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return self.consultas.existencia_total_en_almacenes(articulo_id)
        if usuario.almacen_id is None:
            return 0
        return self.consultas.existencia_total_en_almacenes(articulo_id, usuario.almacen_id)

    def _pieza_en_alcance(
        self, pieza_id: uuid.UUID, usuario: Usuario, permisos: frozenset[str] | None = None
    ) -> bool:
        """AC-06, C-02: con `almacenes.todos` se ve cualquier pieza. Sin él, solo la que está en
        el almacén del usuario, la que tiene un trabajador (su resguardo, con `trabajadores.ver`)
        o la que va en tránsito o ya salió por un vale de su almacén."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return True
        permisos = permisos if permisos is not None else self.acceso.permisos_de(usuario)
        return self.consultas.pieza_visible(
            pieza_id,
            frozenset(self.acceso.almacenes_del_usuario(usuario.id)),
            P.TRABAJADORES_VER in permisos,
        )

    def _escaneo_pieza(
        self,
        pieza_id: uuid.UUID,
        usuario: Usuario,
        permisos: frozenset[str],
        almacen_id: uuid.UUID | None = None,
    ) -> EscaneoOut:
        """C-02: estado, inspección y quién la tiene (el historial va en la ficha). AC-06: una
        pieza fuera del alcance del usuario llega como DESCONOCIDO."""
        encontrada = self.consultas.pieza(pieza_id)
        if encontrada is None or not self._pieza_en_alcance(pieza_id, usuario, permisos):
            return self._desconocido()
        pieza, articulo = encontrada
        ubicacion = self._ubicacion_de(pieza)
        disponible = None
        if almacen_id is not None:  # TR-11
            alcance = self._alcance(usuario, almacen_id)
            en_el_almacen = (
                not alcance.vacio
                and ubicacion is not None
                and ubicacion.tipo == "ALMACEN"
                and dentro_del_alcance(ubicacion.almacen_id, alcance.almacen_id)
            )
            disponible = 1 if en_el_almacen else 0
        resumen = ResumenPieza(
            codigo=pieza.codigo,
            numero_serie=pieza.numero_serie,
            articulo_id=articulo.id,
            articulo=articulo.nombre,
            estado=pieza.estado,
            estado_texto=TEXTO_ESTADO_PIEZA.get(pieza.estado, pieza.estado),
            inspeccion_vigente_hasta=pieza.inspeccion_vigente_hasta,
            inspeccion_vigente=self._inspeccion_vigente(pieza),
            ubicacion=ubicacion,
            disponible=disponible,
        )
        return EscaneoOut(tipo=TipoEscaneo.PIEZA, id=pieza.id, resumen=resumen)

    def _escaneo_vale(self, vale_id: uuid.UUID, usuario: Usuario) -> EscaneoOut:
        """C-04: el vale (su integridad es de FEAT-001). AC-06: igual que `GET /api/vales/{id}`,
        un vale fuera del alcance del usuario (ni su almacén es el de origen ni el de destino de
        un traspaso, y sin `almacenes.todos`) llega como DESCONOCIDO."""
        fila = self.consultas.vale_resumen(vale_id)
        if fila is None:
            return self._desconocido()
        vale, clave_almacen, trabajador, responsable = fila
        if not self.acceso.en_alcance(usuario, vale.almacen_id, vale.destino_almacen_id):
            return self._desconocido()
        resumen = ResumenVale(
            folio=vale.folio,
            tipo=vale.tipo,
            tipo_texto=TEXTO_TIPO_VALE.get(vale.tipo, vale.tipo),
            estado=vale.estado,
            fecha=vale.creado_en,
            almacen_clave=clave_almacen,
            trabajador=trabajador,
            responsable=responsable,
        )
        return EscaneoOut(tipo=TipoEscaneo.VALE, id=vale.id, resumen=resumen)

    @staticmethod
    def _inspeccion_vigente(pieza: Pieza) -> bool:
        hasta = pieza.inspeccion_vigente_hasta
        return hasta is not None and hasta >= hoy_mx()

    def _ubicacion_de(self, pieza: Pieza) -> UbicacionOut | None:
        if pieza.ubicacion_id is None:
            return None
        fila = self.consultas.ubicacion(pieza.ubicacion_id)
        return _ubicacion(fila, "ub") if fila else None

    # ======================================================================== búsqueda

    def buscar(
        self,
        q: str,
        usuario: Usuario,
        pagina: Paginacion,
        almacen_id: uuid.UUID | None = None,
    ) -> BusquedaOut:
        """C-06: artículos (nombre o código), piezas (serie, código o nombre del artículo) y
        trabajadores (nombre o número). Cada grupo se llena solo si el usuario puede verlo.
        Menos de dos caracteres no busca.

        TR-11: con `almacen_id` (el origen de un traspaso) solo se ofrecen artículos y piezas que
        están en ese almacén, cada uno con `disponible`. Escanear un código que no hay allí no
        pasa por aquí: sigue dando el artículo con `disponible` 0 y el servidor rechaza con X-02."""
        texto = (q or "").strip()
        vacio_art: Pagina[BusquedaArticuloItem] = Pagina(elementos=[], total=0)
        vacio_pza: Pagina[BusquedaPiezaItem] = Pagina(elementos=[], total=0)
        vacio_trab: Pagina[BusquedaTrabajadorItem] = Pagina(elementos=[], total=0)
        if len(texto) < LONGITUD_MINIMA_BUSQUEDA:
            return BusquedaOut(
                q=texto,
                articulos=vacio_art,
                piezas=vacio_pza,
                trabajadores=vacio_trab,
                sin_resultados=True,
                mensaje=MENSAJE_BUSQUEDA_CORTA,
            )

        permisos = self.acceso.permisos_de(usuario)
        articulos, piezas, trabajadores = vacio_art, vacio_pza, vacio_trab
        en_almacen: uuid.UUID | None = None
        sin_alcance = False
        if almacen_id is not None:
            alcance = self._alcance(usuario, almacen_id)
            sin_alcance, en_almacen = alcance.vacio, alcance.almacen_id
        if P.CATALOGO_VER in permisos and not sin_alcance:
            filas, total = self.consultas.buscar_articulos(
                texto, pagina.offset, pagina.limit, en_almacen_id=en_almacen
            )
            alcance_cantidades = self._alcance(usuario, almacen_id)
            cantidades = (
                self.consultas.cantidades_busqueda(
                    [f.id for f in filas], alcance_cantidades.almacen_id
                )
                if not alcance_cantidades.vacio
                else {}
            )
            articulos = Pagina(
                elementos=[
                    BusquedaArticuloItem.model_validate(
                        {
                            **dict(f._mapping),
                            "en_almacen": cantidades.get(f.id, (0, 0))[0],
                            "con_trabajadores": cantidades.get(f.id, (0, 0))[1]
                            if f.retornable
                            else None,
                        }
                    )
                    for f in filas
                ],
                total=total,
            )
            filas, total = self.consultas.buscar_piezas(
                texto,
                pagina.offset,
                pagina.limit,
                todos=self.acceso.puede_operar_todos_los_almacenes(usuario),  # AC-06
                almacen_id=frozenset(self.acceso.almacenes_del_usuario(usuario.id)),
                ver_trabajadores=P.TRABAJADORES_VER in permisos,
                en_almacen_id=en_almacen,
            )
            piezas = Pagina(
                elementos=[
                    BusquedaPiezaItem(
                        id=f.id,
                        codigo=f.codigo,
                        numero_serie=f.numero_serie,
                        articulo_id=f.articulo_id,
                        articulo=f.articulo,
                        estado=f.estado,
                        estado_texto=TEXTO_ESTADO_PIEZA.get(f.estado, f.estado),
                        ubicacion=_texto_ubicacion(f, "ub") or None,
                        ubicacion_texto=(
                            f"En tránsito a {f.destino_transito}"
                            if f.ub_tipo == "VIRTUAL"
                            and f.ub_virtual == "EN_TRANSITO"
                            and f.destino_transito
                            else f"En resguardo de {_texto_ubicacion(f, 'ub')}"
                            if f.ub_tipo == "TRABAJADOR"
                            else f"En {f.ub_almacen}"
                            if f.ub_tipo == "ALMACEN"
                            else _texto_ubicacion(f, "ub")
                        )
                        or None,
                        disponible=1 if en_almacen is not None else None,
                    )
                    for f in filas
                ],
                total=total,
            )
        if P.TRABAJADORES_VER in permisos:
            filas, total = self.consultas.buscar_trabajadores(texto, pagina.offset, pagina.limit)
            periodos_busqueda = TrabajadorRepository(self.session).periodos_de(
                [f.id for f in filas]
            )
            trabajadores = Pagina(
                elementos=[
                    BusquedaTrabajadorItem(
                        id=f.id,
                        numero_empleado=f.numero_empleado,
                        nombre=f.nombre,
                        estado=f.estado,
                        estado_texto=TEXTO_ESTADO_TRABAJADOR.get(f.estado, f.estado),
                        puesto=(
                            periodo.puesto
                            if (
                                periodo := elegir_periodo(periodos_busqueda.get(f.id, []), hoy_mx())
                            )
                            else None
                        ),
                        vigencia={
                            "vigente": (
                                vigencia := calcular_vigencia(
                                    f.estado, periodos_busqueda.get(f.id, []), hoy_mx()
                                )
                            ).vigente,
                            "texto": "Vigente"
                            if vigencia.vigente
                            else vigencia.motivo or "No vigente",
                        },
                        credencial=f.credencial,
                    )
                    for f in filas
                ],
                total=total,
            )
        sin = articulos.total + piezas.total + trabajadores.total == 0
        return BusquedaOut(
            q=texto,
            articulos=articulos,
            piezas=piezas,
            trabajadores=trabajadores,
            sin_resultados=sin,
            mensaje=MENSAJE_SIN_RESULTADOS if sin else None,
        )

    # =================================================================== ficha de pieza

    def ficha_pieza(self, pieza_id: uuid.UUID, usuario: Usuario) -> PiezaFichaOut:
        """C-02: estado, inspección, quién la tiene e historial. AC-06: una pieza fuera del
        alcance del usuario responde igual que una que no existe."""
        encontrada = self.consultas.pieza(pieza_id)
        if encontrada is None or not self._pieza_en_alcance(pieza_id, usuario):
            raise PiezaNoEncontrada()
        pieza, articulo = encontrada
        ultima = self.consultas.ultima_inspeccion(pieza.id)
        dias_aviso, origen_aviso = CatalogoService(self.session).aviso_inspeccion(articulo)
        lugar = self._ubicacion_de(pieza)
        impedimento = None
        if pieza.estado == "BAJA":
            impedimento = ("La pieza está dada de baja.", "P-17")
        elif pieza.estado in ("EN_MANTENIMIENTO", "EN_CALIBRACION"):
            impedimento = ("Primero retira la pieza de mantenimiento o calibración.", "P-17")
        elif lugar and lugar.tipo == "EN_TRANSITO":
            impedimento = ("Recibe la pieza antes de inspeccionarla.", "P-17")
        elif not self.acceso.tiene_permiso(usuario, P.PIEZAS_INSPECCIONAR):
            impedimento = ("No tienes permiso para inspeccionar.", "AC-06")
        return PiezaFichaOut(
            vigencia_inspeccion_dias=articulo.vigencia_inspeccion_dias,
            dias_aviso_inspeccion=dias_aviso,
            origen_aviso_inspeccion=origen_aviso,
            dias_restantes=(pieza.inspeccion_vigente_hasta - hoy_mx()).days
            if pieza.inspeccion_vigente_hasta
            else None,
            vigencia_si_apta_hoy=hoy_mx() + timedelta(days=articulo.vigencia_inspeccion_dias)
            if articulo.vigencia_inspeccion_dias
            else None,
            inspeccion_posible={
                "puede": impedimento is None,
                "motivo": impedimento[0] if impedimento else None,
                "regla": impedimento[1] if impedimento else None,
            },
            id=pieza.id,
            codigo=pieza.codigo,
            numero_serie=pieza.numero_serie,
            estado=pieza.estado,
            estado_texto=TEXTO_ESTADO_PIEZA.get(pieza.estado, pieza.estado),
            articulo=self._articulo_de_pieza(articulo),
            inspeccion_vigente_hasta=pieza.inspeccion_vigente_hasta,
            inspeccion_vigente=self._inspeccion_vigente(pieza),
            ultima_inspeccion=self._inspeccion_out(*ultima) if ultima else None,
            ubicacion=self._ubicacion_de(pieza),
            historial=self._historial(pieza.id, usuario),
            aviso=self._aviso_de_resguardo(pieza, articulo),
        )

    def _aviso_de_resguardo(self, pieza: Pieza, articulo: Articulo) -> str | None:
        """SG-06: pieza de alto valor en resguardo de un trabajador de baja o sin contrato."""
        categoria = self.session.get(Categoria, articulo.categoria_id)
        return SeguimientoService(self.session).aviso_de_pieza(
            pieza, categoria.nombre if categoria else None
        )

    @staticmethod
    def _lugar_visible(fila: Any, prefijo: str, usuario: Usuario) -> str:
        """El texto de una ubicación del historial; un almacén que no es el del usuario se
        muestra como "otro almacén" (AC-06)."""
        if getattr(fila, f"{prefijo}_tipo") == "ALMACEN" and (
            getattr(fila, f"{prefijo}_almacen_id") != usuario.almacen_id
        ):
            return TEXTO_OTRO_ALMACEN
        return _texto_ubicacion(fila, prefijo)

    def _articulo_de_pieza(self, articulo: Articulo) -> ArticuloPiezaOut:
        catalogo = CatalogoService(self.session)
        alto, _ = calcular_alto_valor(articulo, catalogo.obtener_categoria(articulo.categoria_id))
        return ArticuloPiezaOut(
            alto_valor=alto,
            id=articulo.id,
            codigo=articulo.codigo,
            nombre=articulo.nombre,
            marca=articulo.marca,
            modelo=articulo.modelo,
            talla=articulo.talla,
            unidad=articulo.unidad,
            requiere_inspeccion=articulo.requiere_inspeccion,
            vigencia_inspeccion_dias=articulo.vigencia_inspeccion_dias,
        )

    def _inspeccion_out(self, inspeccion, usuario: str) -> InspeccionOut:
        return InspeccionOut(
            id=inspeccion.id,
            puntos=inspeccion.puntos,
            foto=InspeccionService(self.session).foto_referencia(inspeccion.id),
            fecha=inspeccion.fecha,
            resultado=inspeccion.resultado,
            resultado_texto=TEXTO_RESULTADO_INSPECCION.get(
                inspeccion.resultado, inspeccion.resultado
            ),
            vigente_hasta=inspeccion.vigente_hasta,
            observacion=inspeccion.observacion,
            usuario=usuario,
        )

    def _historial(self, pieza_id: uuid.UUID, usuario: Usuario) -> list[HistorialItem]:
        """Movimientos, inspecciones, cambios de estado y ajustes de vigencia, del más reciente
        al más antiguo.

        AC-06: sin `almacenes.todos`, de los movimientos solo se ven los de un vale de su almacén
        (sale de él o va hacia él, con sus lugares completos) y los que pasan por un trabajador (el
        resguardo de la pieza), donde el almacén ajeno se muestra como "otro almacén"."""
        items: list[HistorialItem] = []
        todos = self.acceso.puede_operar_todos_los_almacenes(usuario)
        for f in self.consultas.historial_movimientos(pieza_id):
            propio = True  # el vale es de este almacén, o el usuario ve todos
            if not todos:
                propio = usuario.almacen_id is not None and usuario.almacen_id in (
                    f.vale_almacen_id,
                    f.vale_destino_almacen_id,
                )
                if not propio and "TRABAJADOR" not in (f.origen_tipo, f.destino_tipo):
                    continue
            # SG-03: quién recibe la pieza (o quién la devuelve), con su nombre sin el número
            trabajador = f.destino_trabajador or f.origen_trabajador
            trabajador_id = f.destino_trabajador_id or f.origen_trabajador_id
            if propio:
                origen, destino = _texto_ubicacion(f, "origen"), _texto_ubicacion(f, "destino")
                detalle = f"De {origen} a {destino}. Vale {f.folio}."
                vale_id, folio, responsable = f.vale_id, f.folio, f.responsable
            else:
                # Un vale de otro almacén: sin folio, sin enlace, sin responsable ni almacén.
                origen = self._lugar_visible(f, "origen", usuario)
                destino = self._lugar_visible(f, "destino", usuario)
                detalle = f"De {origen} a {destino}."
                vale_id, folio, responsable = None, None, TEXTO_OTRO_ALMACEN
            items.append(
                HistorialItem(
                    tipo=TipoHistorial.MOVIMIENTO,
                    fecha=f.creado_en,
                    titulo=TEXTO_TIPO_VALE.get(f.tipo, f.tipo),
                    detalle=detalle,
                    usuario=responsable,
                    vale_id=vale_id,
                    folio=folio,
                    tipo_vale=f.tipo,
                    origen=origen,
                    destino=destino,
                    responsable=responsable,
                    condicion=f.condicion,
                    almacen=f.vale_almacen if propio else None,
                    trabajador=trabajador,
                    trabajador_id=trabajador_id,
                )
            )
        for inspeccion, usuario in self.consultas.historial_inspecciones(pieza_id):
            texto = TEXTO_RESULTADO_INSPECCION.get(inspeccion.resultado, inspeccion.resultado)
            partes = [f"Inspección del {_fecha(inspeccion.fecha)}."]
            if inspeccion.vigente_hasta:
                partes.append(f"Vigente hasta el {_fecha(inspeccion.vigente_hasta)}.")
            if inspeccion.observacion:
                partes.append(inspeccion.observacion)
            items.append(
                HistorialItem(
                    tipo=TipoHistorial.INSPECCION,
                    id=inspeccion.id,
                    puntos=inspeccion.puntos,
                    foto=InspeccionService(self.session).foto_referencia(inspeccion.id),
                    fecha=inspeccion.creado_en,
                    titulo=f"Inspección: {texto}",
                    detalle=" ".join(partes),
                    usuario=usuario,
                    resultado=inspeccion.resultado,
                    vigente_hasta=inspeccion.vigente_hasta,
                    observacion=inspeccion.observacion,
                )
            )
        for evento, usuario in self.consultas.historial_cambios_estado(pieza_id):
            antes = TEXTO_ESTADO_PIEZA.get(evento.estado_anterior, evento.estado_anterior)
            ahora = TEXTO_ESTADO_PIEZA.get(evento.estado_nuevo, evento.estado_nuevo)
            items.append(
                HistorialItem(
                    tipo=TipoHistorial.CAMBIO_ESTADO,
                    fecha=evento.creado_en,
                    titulo=f"Cambió de estado: de {antes} a {ahora}",
                    detalle=evento.observacion,
                    usuario=usuario,
                    estado_anterior=evento.estado_anterior,
                    estado_nuevo=evento.estado_nuevo,
                    observacion=evento.observacion,
                )
            )
        for ajuste, usuario in self.consultas.historial_ajustes_vigencia(pieza_id):
            antes = _fecha(ajuste.vigente_hasta_anterior) or "sin fecha"
            items.append(
                HistorialItem(
                    tipo=TipoHistorial.AJUSTE_VIGENCIA,
                    fecha=ajuste.creado_en,
                    titulo="Se ajustó la vigencia de la inspección",
                    detalle=(
                        f"De {antes} a {_fecha(ajuste.vigente_hasta_nuevo)}. "
                        f"Motivo: {ajuste.motivo}"
                    ),
                    usuario=usuario,
                    vigente_hasta=ajuste.vigente_hasta_nuevo,
                    vigente_hasta_anterior=ajuste.vigente_hasta_anterior,
                    observacion=ajuste.motivo,
                )
            )
        items.sort(key=lambda i: i.fecha, reverse=True)
        return items

    # ====================================================================== existencias

    def _existencias(
        self, filtros: ExistenciasFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[ExistenciaReporteItem], int]:
        alcance = self._alcance(usuario, filtros.almacen_id)
        if alcance.vacio:
            return [], 0
        filas, total = self.consultas.reporte_existencias(
            almacen_id=alcance.almacen_id,
            categoria_id=filtros.categoria_id,
            offset=pagina.offset if pagina else None,
            limit=pagina.limit if pagina else None,
        )
        return [ExistenciaReporteItem.model_validate(dict(f._mapping)) for f in filas], total

    def reporte_existencias(
        self, filtros: ExistenciasFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaReporte[ExistenciaReporteItem]:
        """C-05: existencias por almacén y artículo, dentro del alcance del usuario."""
        elementos, total = self._existencias(filtros, usuario, pagina)
        return self._pagina(elementos, total)

    def csv_existencias(self, filtros: ExistenciasFilters, usuario: Usuario) -> tuple[bytes, str]:
        elementos, _ = self._existencias(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Clave del almacén",
                "Almacén",
                "Código",
                "Artículo",
                "Categoría",
                "Unidad",
                "Cantidad",
                "Disponible",
            ],
            [
                (
                    e.almacen_clave,
                    e.almacen,
                    e.codigo,
                    e.articulo,
                    e.categoria,
                    e.unidad,
                    e.cantidad,
                    e.disponible,
                )
                for e in elementos
            ],
        )
        return contenido, f"existencias-{hoy_mx():%Y%m%d}.csv"

    # ====================================================================== movimientos

    def _movimientos(
        self, filtros: MovimientosFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[MovimientoReporteItem], int]:
        inicio, fin = rango_utc(filtros.desde, filtros.hasta)
        alcance = self._alcance(usuario, filtros.almacen_id)
        if alcance.vacio:
            return [], 0
        usuario_id = filtros.usuario_id
        if filtros.solo_mios:  # SG-05: «Solo los míos»
            if usuario_id is not None and usuario_id != usuario.id:
                return [], 0
            usuario_id = usuario.id
        filas, total = self.consultas.reporte_movimientos(
            desde=inicio,
            hasta_excluyente=fin,
            almacen_id=alcance.almacen_id,
            tipo=filtros.tipo.value if filtros.tipo else None,
            trabajador_id=filtros.trabajador_id,
            articulo_id=filtros.articulo_id,
            usuario_id=usuario_id,
            pieza_texto=(filtros.pieza or "").strip() or None,
            offset=pagina.offset if pagina else None,
            limit=pagina.limit if pagina else None,
        )
        elementos = [
            MovimientoReporteItem(
                id=f.id,
                fecha=f.creado_en,
                vale_id=f.vale_id,
                folio=f.folio,
                tipo=f.tipo,
                tipo_texto=TEXTO_TIPO_VALE.get(f.tipo, f.tipo),
                articulo_id=f.articulo_id,
                codigo_articulo=f.codigo_articulo,
                articulo=f.articulo,
                pieza=f.pieza,
                numero_serie=f.numero_serie,
                cantidad=f.cantidad,
                origen=_texto_ubicacion(f, "origen"),
                destino=_texto_ubicacion(f, "destino"),
                direccion=direccion,
                direccion_texto=TEXTO_DIRECCION.get(direccion) if direccion else None,
                responsable=f.responsable,
                trabajador_id=f.trabajador_id,
                trabajador=f"{f.trabajador} ({f.numero_empleado})" if f.trabajador else None,
                autorizado_por=f.autorizado_por,
                motivo=f.motivo,
                saldo_origen=f.saldo_origen,
                saldo_destino=f.saldo_destino,
                observacion=f.observacion,
            )
            for f in filas
            for direccion in [direccion_para(f, alcance.almacen_id)]
        ]
        return elementos, total

    def reporte_movimientos(
        self, filtros: MovimientosFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaReporte[MovimientoReporteItem]:
        """C-05 y C-11: la bitácora con filtros; el usuario filtra siempre dentro de su alcance."""
        elementos, total = self._movimientos(filtros, usuario, pagina)
        return self._pagina(elementos, total)

    def csv_movimientos(self, filtros: MovimientosFilters, usuario: Usuario) -> tuple[bytes, str]:
        elementos, _ = self._movimientos(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Fecha",
                "Folio",
                "Tipo",
                "Código del artículo",
                "Artículo",
                "Pieza",
                "Cantidad",
                "Origen",
                "Destino",
                "Entrada o salida",
                "Responsable",
                "Trabajador",
                "Autorizado por",
                "Motivo",
                "Saldo origen",
                "Saldo destino",
            ],
            [
                (
                    e.fecha,
                    e.folio,
                    e.tipo_texto,
                    e.codigo_articulo,
                    e.articulo,
                    e.pieza,
                    e.cantidad,
                    e.origen,
                    e.destino,
                    e.direccion_texto,
                    e.responsable,
                    e.trabajador,
                    e.autorizado_por,
                    e.motivo,
                    e.saldo_origen,
                    e.saldo_destino,
                )
                for e in elementos
            ],
        )
        return contenido, f"movimientos-{hoy_mx():%Y%m%d}.csv"

    # ========================================================================== adeudos

    def _adeudos(
        self, filtros: AdeudosFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[AdeudoReporteItem], int]:
        """El adeudo es de la persona, no de un almacén: se decide por PERMISO. Con
        `almacenes.todos` (AC-06) o con `trabajadores.administrar` (RH, que administra a las
        personas y no tiene almacén) se ven los de todos los almacenes. Sin ellos, solo lo
        entregado por el almacén asignado; sin almacén asignado, nada."""
        permisos = self.acceso.permisos_de(usuario)
        if P.ALMACENES_TODOS in permisos or P.TRABAJADORES_ADMINISTRAR in permisos:
            almacen_id = filtros.almacen_id
        else:
            asignados = self.acceso.almacenes_del_usuario(usuario.id)
            if not asignados:
                return [], 0
            if filtros.almacen_id is not None and filtros.almacen_id not in asignados:
                return [], 0
            almacen_id = filtros.almacen_id or frozenset(asignados)

        pendientes = self.consultas.pendientes()
        if almacen_id is not None:
            pendientes = [p for p in pendientes if dentro_del_alcance(p.almacen_id, almacen_id)]

        vigencias = self._vigencias({p.trabajador for p in pendientes})
        if filtros.solo_no_vigentes:
            pendientes = [p for p in pendientes if not vigencias[p.trabajador.id].vigente]
        pendientes.sort(
            key=lambda p: (
                p.trabajador.nombre.casefold(),
                p.trabajador.numero_empleado,
                p.desde is None,
                p.desde or datetime.min,
                p.articulo.nombre.casefold(),
                p.pieza.codigo if p.pieza else p.articulo.codigo,
            )
        )
        total = len(pendientes)
        if pagina is not None:
            pendientes = pendientes[pagina.offset : pagina.offset + pagina.limit]
        return [self._adeudo_out(p, vigencias[p.trabajador.id]) for p in pendientes], total

    def _vigencias(self, trabajadores: set[Trabajador]) -> dict:
        periodos = TrabajadorRepository(self.session).periodos_de([t.id for t in trabajadores])
        hoy = hoy_mx()
        return {
            t.id: calcular_vigencia(t.estado, periodos.get(t.id, []), hoy) for t in trabajadores
        }

    @staticmethod
    def _adeudo_out(p: Pendiente, vigencia) -> AdeudoReporteItem:
        return AdeudoReporteItem(
            trabajador_id=p.trabajador.id,
            numero_empleado=p.trabajador.numero_empleado,
            trabajador=p.trabajador.nombre,
            estado=p.trabajador.estado,
            estado_texto=TEXTO_ESTADO_TRABAJADOR.get(p.trabajador.estado, p.trabajador.estado),
            vigente=vigencia.vigente,
            motivo_no_vigente=vigencia.motivo,
            articulo_id=p.articulo.id,
            codigo=p.pieza.codigo if p.pieza else p.articulo.codigo,
            articulo=p.articulo.nombre,
            numero_serie=p.pieza.numero_serie if p.pieza else None,
            cantidad=p.cantidad,
            desde=p.desde,
            folio=p.folio,
            almacen_clave=p.almacen_clave,
            almacen=p.almacen,
        )

    def reporte_adeudos(
        self, filtros: AdeudosFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaReporte[AdeudoReporteItem]:
        """C-05: lo que cada trabajador tiene pendiente, desde cuándo y de qué almacén."""
        elementos, total = self._adeudos(filtros, usuario, pagina)
        return self._pagina(elementos, total)

    def csv_adeudos(self, filtros: AdeudosFilters, usuario: Usuario) -> tuple[bytes, str]:
        elementos, _ = self._adeudos(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Número de empleado",
                "Trabajador",
                "Situación",
                "Motivo",
                "Artículo",
                "Código",
                "Número de serie",
                "Cantidad",
                "Desde",
                "Folio del vale",
                "Almacén",
            ],
            [
                (
                    e.numero_empleado,
                    e.trabajador,
                    "Vigente" if e.vigente else "No vigente",
                    e.motivo_no_vigente,
                    e.articulo,
                    e.codigo,
                    e.numero_serie,
                    e.cantidad,
                    e.desde,
                    e.folio,
                    e.almacen,
                )
                for e in elementos
            ],
        )
        return contenido, f"adeudos-{hoy_mx():%Y%m%d}.csv"

    # ========================================================================== consumo

    def _consumo(
        self, filtros: ConsumoFilters, usuario: Usuario, pagina: Paginacion | None
    ) -> tuple[list[ConsumoReporteItem], int]:
        inicio, fin = rango_utc(filtros.desde, filtros.hasta)
        alcance = self._alcance(usuario, filtros.almacen_id)
        if alcance.vacio:
            return [], 0
        filas = self.consultas.consumo(
            desde=inicio,
            hasta_excluyente=fin,
            almacen_id=alcance.almacen_id,
            categoria_id=filtros.categoria_id,
            articulo_id=filtros.articulo_id,
            trabajador_id=filtros.trabajador_id,
            proyecto_id=filtros.proyecto_id,
        )
        trabajadores = self.consultas.trabajadores_por_id(
            {f.trabajador_id for f in filas if f.trabajador_id is not None}
        )
        por_articulo: dict[uuid.UUID, ConsumoReporteItem] = {}
        for f in filas:
            item = por_articulo.get(f.articulo_id)
            if item is None:
                item = ConsumoReporteItem(
                    articulo_id=f.articulo_id,
                    codigo=f.codigo,
                    articulo=f.articulo,
                    categoria=f.categoria,
                    unidad=f.unidad,
                    total=0,
                    trabajadores=[],
                )
                por_articulo[f.articulo_id] = item
            trabajador = trabajadores.get(f.trabajador_id) if f.trabajador_id else None
            cantidad = int(f.cantidad)
            item.total += cantidad
            item.trabajadores.append(
                ConsumoTrabajadorItem(
                    trabajador_id=f.trabajador_id,
                    numero_empleado=trabajador.numero_empleado if trabajador else None,
                    trabajador=trabajador.nombre if trabajador else "Sin trabajador",
                    cantidad=cantidad,
                )
            )
        elementos = sorted(por_articulo.values(), key=lambda i: (-i.total, i.articulo.casefold()))
        for item in elementos:
            item.trabajadores.sort(key=lambda t: (-t.cantidad, t.trabajador.casefold()))
        total = len(elementos)
        if pagina is not None:
            elementos = elementos[pagina.offset : pagina.offset + pagina.limit]
        return elementos, total

    def reporte_consumo(
        self, filtros: ConsumoFilters, usuario: Usuario, pagina: Paginacion
    ) -> PaginaReporte[ConsumoReporteItem]:
        """C-08: consumo neto por artículo consumible, con el desglose por trabajador."""
        elementos, total = self._consumo(filtros, usuario, pagina)
        return self._pagina(elementos, total)

    def csv_consumo(self, filtros: ConsumoFilters, usuario: Usuario) -> tuple[bytes, str]:
        elementos, _ = self._consumo(filtros, usuario, None)
        contenido = exportacion.construir_csv(
            [
                "Código",
                "Artículo",
                "Categoría",
                "Unidad",
                "Total del artículo",
                "Número de empleado",
                "Trabajador",
                "Cantidad del trabajador",
            ],
            [
                (
                    e.codigo,
                    e.articulo,
                    e.categoria,
                    e.unidad,
                    e.total,
                    t.numero_empleado,
                    t.trabajador,
                    t.cantidad,
                )
                for e in elementos
                for t in e.trabajadores
            ],
        )
        return contenido, f"consumo-{hoy_mx():%Y%m%d}.csv"
