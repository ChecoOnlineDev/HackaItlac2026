"""Ayudas de las pruebas de `movimientos`: crean artículos, trabajadores y existencias.

Todo se crea a través de los servicios o modelos de su módulo dueño (nunca saldos a mano): las
existencias nacen de entradas reales por la API.
"""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.models import Almacen
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import Articulo, Categoria, EstadoPieza, Pieza, TipoCodigo
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador

# 1x1 PNG válido: es lo que la interfaz mandaría como firma.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5E"
    "rkJggg=="
)
FIRMA = {"modo": "PANTALLA", "imagen": f"data:image/png;base64,{PNG_B64}", "trazo": []}


def unico(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"


def almacen(session: Session, clave: str = "KEP") -> Almacen:
    return AlmacenService(session).obtener_por_clave(clave)


def crear_articulo(
    session: Session,
    *,
    codigo: str | None = None,
    control: str = "CANTIDAD",
    retornable: bool = True,
    nombre: str | None = None,
    activo: bool = True,
    **reglas,
) -> Articulo:
    """Un artículo nuevo con su código registrado. `reglas`: límite_cantidad, requiere_..., etc."""
    categoria = session.scalar(select(Categoria).order_by(Categoria.nombre).limit(1))
    codigo = codigo or unico("ART")
    articulo = Articulo(
        id=uuid.uuid4(),
        codigo=codigo,
        nombre=nombre or f"Artículo {codigo}",
        marca=reglas.pop("marca", "Marca"),
        categoria_id=categoria.id,
        control=control,
        retornable=retornable,
        activo=activo,
        motivo_inactivacion=None if activo else "Prueba",
        **reglas,
    )
    session.add(articulo)
    session.flush()
    CodigoService(session).registrar(codigo, TipoCodigo.ARTICULO, articulo.id)
    return articulo


def crear_pieza(
    session: Session,
    articulo: Articulo,
    *,
    codigo: str | None = None,
    estado: EstadoPieza = EstadoPieza.APTO,
    vigente_hasta=None,
) -> Pieza:
    """Una pieza sin ubicación (como la deja `registrar_pieza`): entra con una ENTRADA."""
    return CatalogoService(session).registrar_pieza(
        articulo.id,
        codigo or unico("PZA"),
        unico("SER"),
        estado=estado,
        inspeccion_vigente_hasta=vigente_hasta,
    )


def crear_trabajador(
    session: Session, *, vigente: bool = True, estado: str = EstadoTrabajador.ACTIVO
) -> Trabajador:
    """Un trabajador con credencial, ubicación y periodo (vigente o vencido)."""
    admin = UsuarioRepository(session).get_by_usuario("admin")
    numero = unico("EMP")
    trabajador = Trabajador(
        id=uuid.uuid4(), numero_empleado=numero, nombre=f"Trabajador {numero}", estado=estado
    )
    session.add(trabajador)
    session.flush()
    hoy = hoy_mx()
    inicio, fin = (
        (hoy - timedelta(days=30), hoy + timedelta(days=300))
        if vigente
        else (hoy - timedelta(days=400), hoy - timedelta(days=5))
    )
    session.add(
        PeriodoContrato(
            trabajador_id=trabajador.id,
            puesto="Soldador",
            area_obra="Midrex",
            inicio=inicio,
            fin=fin,
            creado_por=admin.id,
        )
    )
    AlmacenService(session).asegurar_ubicacion_de_trabajador(trabajador.id)
    CodigoService(session).registrar(f"CRED-{numero}", TipoCodigo.TRABAJADOR, trabajador.id)
    session.flush()
    return trabajador


def existencia(session: Session, almacen_clave: str, articulo: Articulo) -> int:
    ubicacion = AlmacenService(session).ubicacion_de_almacen(almacen(session, almacen_clave).id)
    return session.scalar(
        select(Existencia.cantidad).where(
            Existencia.ubicacion_id == ubicacion.id, Existencia.articulo_id == articulo.id
        )
    ) or 0


def existencia_de_trabajador(session: Session, trabajador: Trabajador, articulo: Articulo) -> int:
    ubicacion = AlmacenService(session).ubicacion_de_trabajador(trabajador.id)
    return session.scalar(
        select(Existencia.cantidad).where(
            Existencia.ubicacion_id == ubicacion.id, Existencia.articulo_id == articulo.id
        )
    ) or 0


def cuerpo_entrada(renglones: list[dict], **extra) -> dict:
    return {
        "tipo": "ENTRADA",
        "id_cliente": str(uuid.uuid4()),
        "renglones": renglones,
    } | extra


def cuerpo_entrega(trabajador: Trabajador, renglones: list[dict], **extra) -> dict:
    return {
        "tipo": "ENTREGA",
        "trabajador_id": str(trabajador.id),
        "id_cliente": str(uuid.uuid4()),
        "renglones": renglones,
        "firma": FIRMA,
    } | extra


def abastecer(cliente_compras, articulo: Articulo, cantidad: int, **extra):
    """Una ENTRADA real por la API (Compras, Kepler por defecto)."""
    r = cliente_compras.post(
        "/api/vales",
        json=cuerpo_entrada([{"codigo": articulo.codigo, "cantidad": cantidad}], **extra),
    )
    assert r.status_code == 201, r.text
    return r.json()


def entrar_pieza(cliente_compras, articulo: Articulo, codigo: str | None = None, serie=None, **extra):
    """Una ENTRADA de una pieza nueva por la API. Devuelve `(respuesta, codigo_de_pieza)`."""
    codigo = codigo or unico("PZA")
    renglon = {
        "codigo": articulo.codigo,
        "cantidad": 1,
        "pieza": {"codigo": codigo, "numero_serie": serie or unico("SER")} | extra,
    }
    r = cliente_compras.post("/api/vales", json=cuerpo_entrada([renglon]))
    return r, codigo


def total_vales(session: Session) -> int:
    return len(session.scalars(select(Vale.id)).all())


def total_movimientos(session: Session) -> int:
    return len(session.scalars(select(Movimiento.id)).all())
