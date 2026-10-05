"""Cargador de contexto: reúne de la base los hechos que el evaluador necesita.

Lee con los servicios de los demás módulos (catalogo, trabajadores, almacenes) y con el repository
de `movimientos`. Guarda en memoria lo ya leído durante la evaluación (identificación de códigos,
ficha del trabajador). No escribe nada.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Ubicacion, UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.exceptions import ArticuloNoEncontrado, PiezaNoEncontrada
from app.modulos.catalogo.models import Articulo, Pieza, TipoCodigo
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.evaluador import (
    HechosArticulo,
    HechosCuenta,
    HechosPieza,
    HechosRenglonEntrega,
    HechosTrabajador,
    Titular,
)
from app.modulos.movimientos.repository import MovimientoRepository
from app.modulos.trabajadores.models import Trabajador
from app.modulos.trabajadores.schemas import FichaBreveOut
from app.modulos.trabajadores.service import TrabajadorService

_TEXTO_VIRTUAL = {
    UbicacionVirtual.EN_TRANSITO: "está en tránsito entre almacenes",
    UbicacionVirtual.CONSUMIDO: "ya se consumió",
    UbicacionVirtual.BAJA: "está de baja",
    UbicacionVirtual.PROVEEDOR: "todavía no ha entrado a ningún almacén",
}


@dataclass(frozen=True)
class Identificacion:
    """Qué es un código escaneado. `tipo`: ARTICULO, PIEZA, OTRO (trabajador o vale) o None
    (el código no existe)."""

    tipo: str | None
    articulo: Articulo | None = None
    pieza: Pieza | None = None


def hechos_de_articulo(articulo: Articulo) -> HechosArticulo:
    return HechosArticulo(
        id=articulo.id,
        codigo=articulo.codigo,
        nombre=articulo.nombre,
        marca=articulo.marca,
        modelo=articulo.modelo,
        talla=articulo.talla,
        unidad=articulo.unidad,
        control=articulo.control,
        retornable=articulo.retornable,
        activo=articulo.activo,
        motivo_inactivacion=articulo.motivo_inactivacion,
        requiere_inspeccion=articulo.requiere_inspeccion,
        vigencia_inspeccion_dias=articulo.vigencia_inspeccion_dias,
        requiere_autorizacion=articulo.requiere_autorizacion,
        motivo_uso_especial=articulo.motivo_uso_especial,
        limite_cantidad=articulo.limite_cantidad,
        limite_periodo_dias=articulo.limite_periodo_dias,
        cantidad_aviso=articulo.cantidad_aviso,
    )


def hechos_de_pieza(pieza: Pieza) -> HechosPieza:
    return HechosPieza(
        id=pieza.id,
        codigo=pieza.codigo,
        numero_serie=pieza.numero_serie,
        estado=pieza.estado,
        inspeccion_vigente_hasta=pieza.inspeccion_vigente_hasta,
        ubicacion_id=pieza.ubicacion_id,
    )


class Cargador:
    def __init__(
        self,
        repository: MovimientoRepository,
        catalogo: CatalogoService,
        trabajadores: TrabajadorService,
        almacenes: AlmacenService,
        usuario: Usuario,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo
        self.trabajadores = trabajadores
        self.almacenes = almacenes
        self.usuario = usuario
        self._identificaciones: dict[str, Identificacion] = {}
        self._fichas: dict[uuid.UUID, FichaBreveOut] = {}

    def olvidar_lecturas(self) -> None:
        """Descarta lo leído antes de bloquear las filas: al confirmar se vuelve a leer todo."""
        self._fichas.clear()

    # ------------------------------------------------------------------ códigos

    def identificar(self, codigo: str) -> Identificacion:
        """Resuelve un código escaneado con el registro único de códigos (RG-10)."""
        clave = codigo.strip().casefold()
        if clave in self._identificaciones:
            return self._identificaciones[clave]
        fila = self.catalogo.identificar_codigo(codigo)
        if fila is None:
            resultado = Identificacion(None)
        elif fila.tipo == TipoCodigo.ARTICULO:
            try:
                resultado = Identificacion("ARTICULO", self.catalogo.obtener_articulo(fila.ref_id))
            except ArticuloNoEncontrado:
                resultado = Identificacion(None)
        elif fila.tipo == TipoCodigo.PIEZA:
            try:
                pieza = self.catalogo.obtener_pieza(fila.ref_id)
                articulo = self.catalogo.obtener_articulo(pieza.articulo_id)
                resultado = Identificacion("PIEZA", articulo, pieza)
            except PiezaNoEncontrada, ArticuloNoEncontrado:
                resultado = Identificacion(None)
        else:
            resultado = Identificacion("OTRO")
        self._identificaciones[clave] = resultado
        return resultado

    def descripcion_de_codigo(self, codigo: str) -> str | None:
        """A qué cosa ya identifica un código, para decirlo al usuario (I-02), o `None`."""
        fila = self.catalogo.identificar_codigo(codigo)
        if fila is None:
            return None
        return {
            TipoCodigo.ARTICULO: "un artículo",
            TipoCodigo.PIEZA: "una pieza",
            TipoCodigo.TRABAJADOR: "la credencial de un trabajador",
            TipoCodigo.VALE: "un vale",
        }.get(fila.tipo, "otra cosa")

    # --------------------------------------------------------------- trabajador

    def trabajador(self, trabajador_id: uuid.UUID) -> Trabajador:
        return self.trabajadores.obtener(trabajador_id)

    def ficha(self, trabajador: Trabajador) -> FichaBreveOut:
        if trabajador.id not in self._fichas:
            self._fichas[trabajador.id] = self.trabajadores.ficha_breve(trabajador, self.usuario)
        return self._fichas[trabajador.id]

    def hechos_trabajador(self, trabajador: Trabajador) -> HechosTrabajador:
        ficha = self.ficha(trabajador)
        return HechosTrabajador(
            vigente=ficha.vigencia.vigente,
            motivo_no_vigente=ficha.vigencia.motivo,
            pendientes_periodo_anterior=ficha.pendientes.de_periodos_anteriores,
        )

    # ---------------------------------------------------------------- ubicaciones

    def ubicacion_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        return self.almacenes.ubicacion_de_trabajador(trabajador_id)

    def ubicacion_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        return self.almacenes.ubicacion_virtual(virtual)

    def titular_de(self, pieza: Pieza) -> Titular | None:
        """Dónde está la pieza según el sistema (E-03)."""
        if pieza.ubicacion_id is None:
            return Titular(None, None, "", "no está registrada en ningún almacén")
        datos = self.repository.ubicaciones([pieza.ubicacion_id]).get(pieza.ubicacion_id)
        if datos is None:
            return None
        ubicacion, nombre, clave = datos
        if ubicacion.tipo == "TRABAJADOR":
            return Titular(
                "TRABAJADOR",
                ubicacion.trabajador_id,
                nombre,
                f"la tiene {nombre} ({clave})",
                numero_empleado=clave,
            )
        if ubicacion.tipo == "ALMACEN":
            return Titular(
                "ALMACEN",
                ubicacion.almacen_id,
                nombre,
                f"está en el almacén {clave} ({nombre})",
            )
        texto = _TEXTO_VIRTUAL.get(
            UbicacionVirtual(ubicacion.virtual), "está fuera de los almacenes"
        )
        return Titular("VIRTUAL", None, nombre, texto)

    # ---------------------------------------------------------------- existencias

    def existencia(self, ubicacion_id: uuid.UUID, articulo_id: uuid.UUID) -> int:
        return self.repository.existencia(ubicacion_id, articulo_id)

    def disponible(self, ubicacion_id: uuid.UUID, articulo: Articulo) -> int:
        """Lo que se puede entregar: en piezas, solo las Aptas (I-05)."""
        if articulo.control == "PIEZA":
            return self.repository.piezas_aptas_en(ubicacion_id, articulo.id)
        return self.repository.existencia(ubicacion_id, articulo.id)

    # --------------------------------------------------------------------- límites

    def cuenta(self, trabajador: Trabajador, articulo: Articulo, ahora: datetime) -> HechosCuenta:
        """Lo que el trabajador tiene ahora y lo que consumió en el periodo del límite."""
        if articulo.limite_cantidad is None:
            return HechosCuenta(0, 0)
        en_posesion = 0
        consumido = 0
        if articulo.retornable:
            ubicacion = self.ubicacion_de_trabajador(trabajador.id)
            en_posesion = self.repository.existencia(ubicacion.id, articulo.id)
        elif articulo.limite_periodo_dias is not None:
            desde = ahora - timedelta(days=articulo.limite_periodo_dias)
            consumido = self.repository.consumido_desde(
                trabajador.id,
                articulo.id,
                self.ubicacion_virtual(UbicacionVirtual.CONSUMIDO).id,
                desde,
            )
        return HechosCuenta(en_posesion, consumido)

    # ------------------------------------------------------------------ renglones

    def hechos_renglon_entrega(
        self,
        *,
        codigo: str,
        cantidad: int,
        identificacion: Identificacion,
        ubicacion_almacen_id: uuid.UUID,
        trabajador: Trabajador,
        ahora: datetime,
        pedido_previo: int,
    ) -> HechosRenglonEntrega:
        articulo = identificacion.articulo
        pieza = identificacion.pieza
        if articulo is None:
            return HechosRenglonEntrega(
                codigo=codigo,
                cantidad=cantidad,
                articulo=None,
                pieza=None,
                titular=None,
                ubicacion_almacen_id=ubicacion_almacen_id,
                existencia_almacen=0,
                disponible=0,
                cuenta=HechosCuenta(0, 0),
            )
        titular = None
        if pieza is not None and pieza.ubicacion_id != ubicacion_almacen_id:
            titular = self.titular_de(pieza)
        return HechosRenglonEntrega(
            codigo=codigo,
            cantidad=cantidad,
            articulo=hechos_de_articulo(articulo),
            pieza=hechos_de_pieza(pieza) if pieza else None,
            titular=titular,
            ubicacion_almacen_id=ubicacion_almacen_id,
            existencia_almacen=self.existencia(ubicacion_almacen_id, articulo.id),
            disponible=self.disponible(ubicacion_almacen_id, articulo),
            cuenta=self.cuenta(trabajador, articulo, ahora),
            pedido_previo=pedido_previo,
        )
