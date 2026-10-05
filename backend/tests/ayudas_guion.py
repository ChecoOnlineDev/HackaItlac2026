"""Ayudas de las pruebas de punta a punta del guion del PDF (`test_guion_pdf.py`,
`test_guion_extremos.py`).

Todo lo que cambia el sistema se hace POR LA API HTTP con sesiones reales (cookie) de los usuarios
de prueba; la base solo se LEE para comprobar (existencias En tránsito y Consumido, folios,
invariantes). Las piezas de alturas y las herramientas por serie son las de los datos de prueba
(`app/datos_prueba_piezas.py`): ALT-001 a ALT-008 y HER-001 a HER-005.
"""

import json
import re
import uuid
from collections.abc import Callable
from datetime import timedelta
from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.movimientos.models import Existencia, SerieFolio
from tests.movimientos.ayudas import FIRMA

__all__ = [
    "FIRMA",
    "alta_trabajador",
    "buscar_trabajador_en_lista",
    "cantidad_en",
    "confirmar",
    "disponible_en",
    "entregar",
    "evaluar",
    "ids_de_almacen",
    "nuevo_cliente",
    "reglas_de",
    "sin_costos",
    "siguiente_folio",
    "ubicacion_de_pieza",
    "pieza_id",
    "en_ubicacion_virtual",
    "COSTOS_DE_PRUEBA",
]

_secuencia = count(1)


def nuevo_cliente() -> str:
    return str(uuid.uuid4())


def unico(prefijo: str) -> str:
    return f"{prefijo}{next(_secuencia):04d}{uuid.uuid4().hex[:4].upper()}"


# ------------------------------------------------------------------------- trabajadores


def alta_trabajador(
    rh: TestClient,
    *,
    nombre: str | None = None,
    numero: str | None = None,
    inicio_dias: int = -5,
    fin_dias: int = 200,
    credencial: str | None = None,
    **extra,
) -> dict:
    """RH da de alta a un trabajador por la API y le liga su credencial. Devuelve la ficha."""
    numero = numero or unico("EMP-G")
    hoy = hoy_mx()
    cuerpo = {
        "nombre": nombre or f"Trabajador {numero}",
        "numero_empleado": numero,
        "puesto": "Soldador",
        "area_obra": "Midrex",
        "inicio": str(hoy + timedelta(days=inicio_dias)),
        "fin": str(hoy + timedelta(days=fin_dias)),
    } | extra
    r = rh.post("/api/trabajadores", json=cuerpo)
    assert r.status_code == 201, r.text
    ficha = r.json()
    codigo = credencial or f"CRED-{numero}"
    c = rh.post(f"/api/trabajadores/{ficha['id']}/codigos", json={"codigo": codigo})
    assert c.status_code == 201, c.text
    ficha["credencial"] = codigo
    return ficha


def buscar_trabajador_en_lista(cliente: TestClient, trabajador_id: str, **filtros) -> dict | None:
    r = cliente.get("/api/trabajadores", params={"tamano": 100} | filtros)
    assert r.status_code == 200, r.text
    return next((t for t in r.json()["elementos"] if t["id"] == trabajador_id), None)


# --------------------------------------------------------------------------------- vales


def evaluar(cliente: TestClient, cuerpo: dict) -> dict:
    cuerpo = {k: v for k, v in cuerpo.items() if k not in ("id_cliente", "firma")}
    r = cliente.post("/api/vales/evaluar", json=cuerpo)
    assert r.status_code == 200, r.text
    return r.json()


def confirmar(cliente: TestClient, cuerpo: dict, *, esperado: int = 201) -> dict:
    cuerpo = {"id_cliente": nuevo_cliente()} | cuerpo
    r = cliente.post("/api/vales", json=cuerpo)
    assert r.status_code == esperado, r.text
    return r.json()


def entregar(
    cliente: TestClient,
    trabajador_id: str,
    renglones: list[dict],
    *,
    esperado: int = 201,
    **extra,
) -> dict:
    """ENTREGA firmada en pantalla. Cada renglón: `{"codigo": ..., "cantidad": ...}`."""
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": trabajador_id,
        "renglones": renglones,
        "firma": FIRMA,
    } | extra
    return confirmar(cliente, cuerpo, esperado=esperado)


def reglas_de(evaluacion: dict, renglon: int | None = None) -> list[str]:
    """IDs de regla del vale (`renglon=None`) o del renglón (1, 2...)."""
    if renglon is None:
        return [m["regla"] for m in evaluacion["motivos"]]
    return [m["regla"] for m in evaluacion["renglones"][renglon - 1]["motivos"]]


# ------------------------------------------------------------------- lugares y existencias


def ids_de_almacen(session: Session) -> dict[str, uuid.UUID]:
    return {a.clave: a.id for a in session.scalars(select(Almacen))}


def _fila_existencia(cliente: TestClient, almacen_id, codigo: str) -> dict | None:
    r = cliente.get(f"/api/almacenes/{almacen_id}/existencias", params={"q": codigo, "tamano": 100})
    assert r.status_code == 200, r.text
    return next(
        (
            f
            for f in r.json()["elementos"]
            if f.get("codigo") == codigo or f.get("articulo_codigo") == codigo
        ),
        None,
    )


def cantidad_en(cliente: TestClient, almacen_id, codigo_articulo: str) -> int:
    """Existencia de un artículo en un almacén, leída por la API (`GET .../existencias`)."""
    fila = _fila_existencia(cliente, almacen_id, codigo_articulo)
    return fila["cantidad"] if fila else 0


def disponible_en(cliente: TestClient, almacen_id, codigo_articulo: str) -> int:
    fila = _fila_existencia(cliente, almacen_id, codigo_articulo)
    return fila["disponible"] if fila else 0


def existencia_db(session: Session, ubicacion: Ubicacion, articulo_id) -> int:
    session.expire_all()
    return (
        session.scalar(
            select(Existencia.cantidad).where(
                Existencia.ubicacion_id == ubicacion.id, Existencia.articulo_id == articulo_id
            )
        )
        or 0
    )


def en_ubicacion_virtual(session: Session, virtual: str, codigo_articulo: str) -> int:
    """Existencia de un artículo en EN_TRANSITO, CONSUMIDO o BAJA (solo se ve en la base)."""
    from app.modulos.catalogo.models import Articulo

    session.expire_all()
    ubicacion = session.scalar(select(Ubicacion).where(Ubicacion.virtual == virtual))
    articulo = session.scalar(select(Articulo).where(Articulo.codigo == codigo_articulo))
    return existencia_db(session, ubicacion, articulo.id)


def pieza_id(cliente: TestClient, codigo: str) -> str:
    r = cliente.get(f"/api/escaneo/{codigo}")
    assert r.status_code == 200 and r.json()["tipo"] == "PIEZA", r.text
    return r.json()["id"]


def ubicacion_de_pieza(cliente: TestClient, codigo: str) -> str:
    """Dónde dice el sistema que está una pieza (el texto de su ubicación)."""
    r = cliente.get(f"/api/escaneo/{codigo}")
    assert r.status_code == 200, r.text
    return r.json()["resumen"]["ubicacion"]["texto"]


def siguiente_folio(session: Session, clave: str, prefijo: str) -> str:
    """El folio que le toca al próximo vale de esa serie (el último guardado más uno)."""
    from app.modulos.movimientos.models import PREFIJO_FOLIO, TipoVale

    tipo = next(t for t, p in PREFIJO_FOLIO.items() if p == prefijo)
    session.expire_all()
    almacen = session.scalar(select(Almacen).where(Almacen.clave == clave))
    ultimo = session.scalar(
        select(SerieFolio.ultimo).where(
            SerieFolio.almacen_id == almacen.id, SerieFolio.tipo == TipoVale(tipo).value
        )
    )
    return f"{clave}-{prefijo}-{(ultimo or 0) + 1:06d}"


# ------------------------------------------------------------------------------- costos

# Costos de los datos de prueba (catalogo): ninguno debe aparecer en un vale (RG-12, F-12).
COSTOS_DE_PRUEBA = (
    "800.00",
    "1250.00",
    "12.00",
    "6.02",
    "269.35",
    "172.93",
    "115.58",
    "178.00",
    "255.00",
    "28.00",
    "48.00",
    "695.00",
)


def sin_costos(cuerpo) -> None:
    """Ni una clave `costo*` ni un valor de costo de los datos de prueba, en ninguna parte."""
    texto = json.dumps(cuerpo, ensure_ascii=False)
    assert not re.search(r'"costo', texto, re.IGNORECASE), "el vale trae una clave de costo"
    for valor in COSTOS_DE_PRUEBA:
        assert f'"{valor}"' not in texto and f": {valor}," not in texto, f"aparece el costo {valor}"


Fabrica = Callable[[str], TestClient]
