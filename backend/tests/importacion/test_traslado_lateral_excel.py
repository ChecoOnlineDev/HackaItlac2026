# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""FEAT-015, TR-05: el traspaso por lista de Excel con ruta lateral (X-16 y X-17).

La ruta se evalúa una vez para todo el archivo: el supervisor del origen lo autoriza al enviarlo
(X-16, pide la observación); quien no lo es pide una autorización de traslado con las filas que no
están en rojo (X-17) y la confirmación la usa (X-19).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.movimientos.models import Movimiento
from tests.conftest import iniciar_sesion_en
from tests.importacion.test_traspaso_lista import (
    RAIZ,
    art,
    cliente_almacen,  # noqa: F401  (fixture)
    confirmacion,
    vista,
)
from tests.movimientos.ayudas import abastecer_en, crear_articulo, existencia
from tests.movimientos.ayudas_traspasos import almacen_id, renglon

AUT = "/api/autorizaciones"


@pytest.fixture
def herramienta(session):
    articulo = crear_articulo(session, retornable=False)
    abastecer_en(session, articulo, 10, "MID")
    return articulo


@pytest.fixture
def ana(app, crear_usuario):
    """Ana: de Midrex, con `traspasos.operar` y sin `autorizaciones.resolver` (X-17)."""
    usuario = crear_usuario({P.TRASPASOS_OPERAR}, almacen="MID")
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    yield cliente
    cliente.close()


def pedir_autorizacion(cliente, session, renglones, destino="HYL"):
    return cliente.post(
        AUT,
        json={
            "tipo": "TRASLADO",
            "destino_almacen_id": str(almacen_id(session, destino)),
            "renglones": renglones,
            "motivo": "HYL arranca soldadura el lunes",
        },
    )


def test_tr_05_x16_el_supervisor_del_origen_ve_entre_proyectos_y_pide_la_observacion(
    cliente_almacen, session, herramienta
):
    mid = cliente_almacen("MID")
    filas = [art(herramienta.codigo, 3)]
    previa = vista(mid, session, filas, destino="HYL")
    ruta = previa["ruta"]
    assert ruta["clase"] == "LATERAL" and ruta["autoriza"] == "ENVIO_PROPIO"
    assert ruta["nivel"] == "AMARILLO" and ruta["pide_observacion"] is True
    assert ruta["habitual"] is False and "Tú lo autorizas" in ruta["mensaje"]
    assert previa["puede_confirmar"] is True and previa["motivos"] == []

    sin = mid.post(RAIZ, json=confirmacion(session, filas, "HYL"))
    assert sin.status_code == 422 and sin.json()["detalles"][0]["regla"] == "X-16"
    assert existencia(session, "MID", herramienta) == 10

    ok = mid.post(RAIZ, json=confirmacion(session, filas, "HYL", observacion="Sobra en Midrex"))
    assert ok.status_code == 201, ok.text
    assert existencia(session, "MID", herramienta) == 7
    vale_id = uuid.UUID(ok.json()["vale"]["id"])
    movimientos = session.scalars(select(Movimiento).where(Movimiento.vale_id == vale_id))
    reglas = {regla for m in movimientos for regla in m.reglas}
    assert {"X-16", "X-18"} <= reglas


def test_tr_05_x16_la_ruta_se_evalua_una_vez_para_todo_el_archivo(
    cliente_almacen, session, herramienta
):
    otra = crear_articulo(session, retornable=False)
    abastecer_en(session, otra, 5, "MID")
    previa = vista(
        cliente_almacen("MID"),
        session,
        [art(herramienta.codigo, 1), art(otra.codigo, 1)],
        destino="HYL",
    )
    assert previa["ruta"]["clase"] == "LATERAL"
    assert all("X-16" not in [m["regla"] for m in f["motivos"]] for f in previa["filas"])


def test_tr_05_x17_quien_no_es_supervisor_pide_autorizacion_con_las_filas_que_no_son_rojas(
    ana, cliente_almacen, session, herramienta
):
    sup_mid = cliente_almacen("MID")
    buena = art(herramienta.codigo, 3)
    mala = art("NO-EXISTE-EXCEL", 1)  # en rojo: se deja fuera
    filas = [buena, mala]

    previa = vista(ana, session, filas, destino="HYL")
    assert previa["ruta"]["clase"] == "LATERAL"
    assert previa["ruta"]["autoriza"] == "SUPERVISOR_ORIGEN"
    assert previa["ruta"]["nivel"] == "NARANJA" and previa["ruta"]["autorizada"] is False
    assert previa["ruta"]["autorizadores_disponibles"] >= 1
    assert previa["puede_confirmar"] is False

    # Sin autorización, la confirmación (dejando fuera la fila en rojo) no sale.
    sin = ana.post(RAIZ, json=confirmacion(session, filas, "HYL", dejar_fuera_errores=True))
    assert sin.status_code == 409 and sin.json()["codigo"] == "VALE_CAMBIO"
    assert existencia(session, "MID", herramienta) == 10

    # La solicitud lleva solo la fila que no está en rojo.
    pedida = pedir_autorizacion(ana, session, [renglon(herramienta.codigo, 3)])
    assert pedida.status_code == 201, pedida.text
    autorizacion_id = pedida.json()["id"]
    aprobada = sup_mid.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})
    assert aprobada.status_code == 200

    # La vista previa con la autorización dice que sirve: dejar fuera filas es quitar renglones.
    previa = vista(ana, session, filas, destino="HYL", autorizacion_id=autorizacion_id)
    assert previa["ruta"]["autorizada"] is True and previa["autorizacion_error"] is None
    assert previa["resumen"]["errores"] == 1

    ok = ana.post(
        RAIZ,
        json=confirmacion(
            session,
            filas,
            "HYL",
            dejar_fuera_errores=True,
            autorizacion_id=autorizacion_id,
        ),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["resumen"]["filas_importadas"] == 1
    assert existencia(session, "MID", herramienta) == 7
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"  # A-03


def test_tr_05_x19_una_autorizacion_que_no_cubre_el_archivo_no_sirve(
    ana, cliente_almacen, session, herramienta
):
    otra = crear_articulo(session, retornable=False)
    abastecer_en(session, otra, 5, "MID")
    pedida = pedir_autorizacion(ana, session, [renglon(herramienta.codigo, 3)])
    autorizacion_id = pedida.json()["id"]
    cliente_almacen("MID").post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})

    # El archivo agrega una fila que la autorización no cubre: no sirve (solo se pueden quitar).
    filas = [art(herramienta.codigo, 3), art(otra.codigo, 1)]
    previa = vista(ana, session, filas, destino="HYL", autorizacion_id=autorizacion_id)
    assert previa["ruta"]["autorizada"] is False
    assert "no cubre" in previa["autorizacion_error"] and previa["puede_confirmar"] is False
    r = ana.post(RAIZ, json=confirmacion(session, filas, "HYL", autorizacion_id=autorizacion_id))
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert existencia(session, "MID", herramienta) == 10
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"


def test_tr_05_la_ruta_habitual_sigue_verde_y_trae_su_clase(cliente_almacen, session, herramienta):
    previa = vista(cliente_almacen("MID"), session, [art(herramienta.codigo, 1)], destino="CON")
    assert previa["ruta"]["clase"] == "HABITUAL" and previa["ruta"]["habitual"] is True
    assert previa["ruta"]["autoriza"] == "NADIE" and previa["ruta"]["pide_observacion"] is False
