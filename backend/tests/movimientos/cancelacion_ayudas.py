"""Ayudas de las pruebas de la CANCELACION.

DEVOLUCION y TRASPASO los implementan otros agentes en paralelo: aquí sus vales se insertan
directamente con los modelos, consistentes con las invariantes (existencias, saldos, ubicación de
las piezas y folio consecutivo), como lo haría el motor.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.models import (
    PREFIJO_FOLIO,
    Existencia,
    Movimiento,
    SerieFolio,
    TipoVale,
    Vale,
)
from app.modulos.movimientos.repository import MovimientoRepository
from app.modulos.trabajadores.models import Trabajador
from tests.movimientos.ayudas import cuerpo_entrega

VALES = "/api/vales"


def cancelacion(motivo: str = "Lo capturé mal", *, rehacer: bool = False, **extra) -> dict:
    return {"motivo": motivo, "id_cliente": str(uuid.uuid4()), "rehacer": rehacer} | extra


def url(vale_id) -> str:
    return f"/api/vales/{vale_id}/cancelacion"


def ub_almacen(session: Session, clave: str) -> Ubicacion:
    almacenes = AlmacenService(session)
    return almacenes.ubicacion_de_almacen(almacenes.obtener_por_clave(clave).id)


def ub_trabajador(session: Session, trabajador: Trabajador) -> Ubicacion:
    return AlmacenService(session).ubicacion_de_trabajador(trabajador.id)


def ub_virtual(session: Session, virtual: UbicacionVirtual) -> Ubicacion:
    return AlmacenService(session).ubicacion_virtual(virtual)


@dataclass
class Mov:
    """Un movimiento a insertar: de `origen` a `destino`."""

    articulo: Articulo
    cantidad: int
    origen: Ubicacion
    destino: Ubicacion
    pieza: Pieza | None = None
    trabajador: Trabajador | None = None
    condicion: str | None = None


def insertar_vale(
    session: Session,
    tipo: TipoVale,
    almacen_clave: str,
    movimientos: list[Mov],
    *,
    usuario: str = "almacenista",
    trabajador: Trabajador | None = None,
    estado: str = "EMITIDO",
    destino_almacen_clave: str | None = None,
    vale_origen: Vale | None = None,
    observacion: str | None = None,
) -> Vale:
    """Inserta un vale con sus movimientos y aplica sus efectos como el motor: existencias (sin
    dejarlas negativas), saldos, `pieza.ubicacion_id` y el folio consecutivo."""
    repo = MovimientoRepository(session)
    almacenes = AlmacenService(session)
    almacen = almacenes.obtener_por_clave(almacen_clave)
    destino_almacen = (
        almacenes.obtener_por_clave(destino_almacen_clave) if destino_almacen_clave else None
    )
    serie = repo.bloquear_serie(almacen.id, tipo)
    serie.ultimo += 1
    session.flush()
    responsable = UsuarioRepository(session).get_by_usuario(usuario)
    ahora = ahora_utc()
    vale = Vale(
        id=nuevo_id(),
        id_cliente=uuid.uuid4(),
        tipo=tipo,
        folio=f"{almacen.clave}-{PREFIJO_FOLIO[TipoVale(tipo)]}-{serie.ultimo:06d}",
        almacen_id=almacen.id,
        trabajador_id=trabajador.id if trabajador else None,
        destino_almacen_id=destino_almacen.id if destino_almacen else None,
        vale_origen_id=vale_origen.id if vale_origen else None,
        estado=estado,
        responsable_id=responsable.id,
        observacion=observacion,
        firma_modo="SESION",
        token=uuid.uuid4().hex,
        creado_en=ahora,
    )
    session.add(vale)
    session.flush()
    proveedor = ub_virtual(session, UbicacionVirtual.PROVEEDOR).id
    for numero, m in enumerate(movimientos, start=1):
        saldo_origen = saldo_destino = None
        if m.origen.id != proveedor:
            fila = _existencia(session, m.origen, m.articulo)
            assert fila.cantidad >= m.cantidad, "el vale insertado dejaría la existencia negativa"
            fila.cantidad -= m.cantidad
            saldo_origen = fila.cantidad
        if m.destino.id != proveedor:
            fila = _existencia(session, m.destino, m.articulo)
            fila.cantidad += m.cantidad
            saldo_destino = fila.cantidad
        if m.pieza is not None:
            m.pieza.ubicacion_id = m.destino.id
        session.flush()
        session.add(
            Movimiento(
                id=nuevo_id(),
                vale_id=vale.id,
                renglon=numero,
                articulo_id=m.articulo.id,
                pieza_id=m.pieza.id if m.pieza else None,
                cantidad=m.cantidad,
                origen_id=m.origen.id,
                destino_id=m.destino.id,
                trabajador_id=m.trabajador.id if m.trabajador else None,
                condicion=m.condicion,
                saldo_origen=saldo_origen,
                saldo_destino=saldo_destino,
                creado_en=ahora,
            )
        )
    session.flush()
    return vale


def _existencia(session: Session, ubicacion: Ubicacion, articulo: Articulo) -> Existencia:
    fila = session.get(Existencia, (ubicacion.id, articulo.id))
    if fila is None:
        fila = Existencia(ubicacion_id=ubicacion.id, articulo_id=articulo.id, cantidad=0)
        session.add(fila)
        session.flush()
    return fila


def cantidad_en(session: Session, ubicacion: Ubicacion, articulo: Articulo) -> int:
    session.expire_all()
    return (
        session.scalar(
            select(Existencia.cantidad).where(
                Existencia.ubicacion_id == ubicacion.id, Existencia.articulo_id == articulo.id
            )
        )
        or 0
    )


def ultimo_folio(session: Session, almacen_clave: str, tipo: str) -> int:
    almacen = session.scalar(select(Almacen).where(Almacen.clave == almacen_clave))
    session.expire_all()
    return (
        session.scalar(
            select(SerieFolio.ultimo).where(
                SerieFolio.almacen_id == almacen.id, SerieFolio.tipo == tipo
            )
        )
        or 0
    )


def entregar(cliente, trabajador, renglones: list[dict], **extra) -> dict:
    r = cliente.post(VALES, json=cuerpo_entrega(trabajador, renglones, **extra))
    assert r.status_code == 201, r.text
    return r.json()
