"""Ayudas de las pruebas de `solicitudes_compra`: cuerpos válidos y llamadas por la API."""

import uuid

from fastapi.testclient import TestClient

RUTA = "/api/solicitudes-compra"


def cuerpo(**cambios) -> dict:
    """Un cuerpo válido de `POST /api/solicitudes-compra` (sin artículo de catálogo)."""
    base = {
        "id_cliente": str(uuid.uuid4()),
        "descripcion": "Llave métrica 24 mm",
        "cantidad": 2,
        "motivo": "Mantenimiento de un equipo europeo",
    }
    return {k: v for k, v in (base | cambios).items() if v is not ...}


def pedir(cliente: TestClient, *, esperado: int = 201, **cambios) -> dict:
    r = cliente.post(RUTA, json=cuerpo(**cambios))
    assert r.status_code == esperado, r.text
    return r.json()


def estado(cliente: TestClient, solicitud_id: str, nuevo: str, *, esperado: int = 200, **extra):
    r = cliente.post(f"{RUTA}/{solicitud_id}/estado", json={"estado": nuevo} | extra)
    assert r.status_code == esperado, r.text
    return r.json()
