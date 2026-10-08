"""X-03 (FEAT-008): una ruta que no es padre-hijo solo la hace quien tiene `almacenes.todos`, con
aviso amarillo y observación obligatoria; para los demás es rojo y el servidor responde 403."""

import pytest

from tests.movimientos.ayudas import abastecer_en, crear_articulo, total_vales
from tests.movimientos.ayudas_traspasos import (
    EVALUAR,
    VALES,
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    cuerpo_traspaso,
    renglon,
)


@pytest.fixture
def articulo(session, cliente_como):
    guantes = crear_articulo(session, retornable=False)
    abastecer_en(session, guantes, 5, "KEP")
    return guantes


def _cuerpo(session, articulo, destino="MID", **extra):
    return cuerpo_traspaso(session, destino, [renglon(articulo.codigo)], **extra)


def test_X_03_el_supervisor_no_puede_una_ruta_que_no_es_padre_hijo(
    cliente_almacen,  # noqa: F811
    session,
    articulo,
):
    supervisor = cliente_almacen("KEP")
    cuerpo = _cuerpo(session, articulo)
    ev = supervisor.post(EVALUAR, json={k: v for k, v in cuerpo.items() if k != "id_cliente"})
    assert ev.status_code == 200
    ev = ev.json()
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert [(m["regla"], m["nivel"]) for m in ev["motivos"]] == [("X-03", "ROJO")]
    vales = total_vales(session)
    r = supervisor.post(VALES, json=cuerpo | {"observacion": "Urgente"})
    assert r.status_code == 403 and r.json()["codigo"] == "RUTA_SOLO_ADMINISTRADOR"
    detalles = r.json()["detalles"]
    assert detalles["regla"] == "X-03"
    assert detalles["origen"]["clave"] == "KEP" and detalles["destino"]["clave"] == "MID"
    assert total_vales(session) == vales  # no se escribió nada


def test_X_03_el_administrador_si_puede_con_aviso_y_observacion(cliente_como, session, articulo):
    admin = cliente_como("Administrador")
    origen = {"almacen_id": str(almacen_id(session, "KEP"))}
    cuerpo = _cuerpo(session, articulo, **origen)
    ev = admin.post(EVALUAR, json={k: v for k, v in cuerpo.items() if k != "id_cliente"}).json()
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert ev["pide_observacion"] is True
    assert [(m["regla"], m["nivel"]) for m in ev["motivos"]] == [("X-03", "AMARILLO")]
    # Sin observación: 422 sobre ese campo, con la regla.
    r = admin.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert r.json()["detalles"][0]["campo"] == "observacion"
    assert r.json()["detalles"][0]["regla"] == "X-03"
    r = admin.post(VALES, json=cuerpo | {"observacion": "   "})
    assert r.status_code == 422
    # Con ella se confirma, y el movimiento guarda la regla.
    r = admin.post(VALES, json=cuerpo | {"observacion": "Contratistas no tiene stock"})
    assert r.status_code == 201, r.text
    assert "X-03" in r.json()["renglones"][0]["reglas"]


@pytest.mark.parametrize(("origen", "destino"), [("KEP", "CON"), ("CON", "MID")])
def test_X_03_la_ruta_padre_hijo_sigue_en_verde_sin_observacion(
    cliente_almacen,  # noqa: F811
    cliente_como,
    session,
    origen,
    destino,  # noqa: F811
):
    guantes = crear_articulo(session, retornable=False)
    abastecer_en(session, guantes, 3, origen)
    cuerpo = cuerpo_traspaso(session, destino, [renglon(guantes.codigo)])
    ev = cliente_almacen(origen).post(
        EVALUAR, json={k: v for k, v in cuerpo.items() if k != "id_cliente"}
    )
    assert ev.json()["nivel"] == "VERDE" and ev.json()["pide_observacion"] is False
    assert cliente_almacen(origen).post(VALES, json=cuerpo).status_code == 201
