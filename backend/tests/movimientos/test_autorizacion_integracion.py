"""Integración con `autorizaciones` (US-AUT-001, US-ESP-001): A-01 a A-07, E-26, SM-03, SM-04.

Flujo completo: solicitar -> resolver -> confirmar el vale con la autorización -> USADA ->
no se reutiliza. La solicitud pasa por el verificador real de `movimientos` (A-06).
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.movimientos.service import MovimientoService
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    total_vales,
)
from tests.movimientos.test_entrega import evaluar, motivos, pieza_en_kep, renglon

VALES = "/api/vales"
AUT = "/api/autorizaciones"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def renglones_de_solicitud(evaluacion) -> list[dict]:
    """Lo que la interfaz manda a `POST /api/autorizaciones`: sale de la evaluación."""
    salida = []
    for r in evaluacion["renglones"]:
        if r["nivel"] != "NARANJA":
            continue
        salida.append(
            {
                "codigo": r["codigo"],
                "articulo_id": r["articulo"]["id"],
                "articulo": r["articulo"]["nombre"],
                "cantidad": r["cantidad"],
                "regla": r["motivos"][0]["regla"],
                "mensaje": r["motivos"][0]["mensaje"],
                "autorizable": r["autorizable"],
            }
        )
    return salida


def solicitar(almacenista, trabajador, evaluacion, motivo="Trabajo especial"):
    r = almacenista.post(
        AUT,
        json={
            "trabajador_id": str(trabajador.id),
            "renglones": renglones_de_solicitud(evaluacion),
            "motivo": motivo,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def aprobar(supervisor, autorizacion_id):
    r = supervisor.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def excedente(almacenista, compras, session, trabajador):
    """Un retornable con límite 1 que el trabajador ya tiene: pedir otro es naranja."""
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(arnes.codigo)]))
    assert r.status_code == 201
    return arnes


def test_A_03_flujo_completo_solicitar_resolver_confirmar_y_no_se_reutiliza(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)

    cuerpo = cuerpo_entrega(
        trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
    )
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 201, r.text
    assert r.json()["renglones"][0]["nivel"] == "NARANJA"
    assert r.json()["renglones"][0]["reglas"] == ["L-02"]
    vale = session.get(Vale, uuid.UUID(r.json()["id"]))
    assert str(vale.autorizacion_id) == autorizacion_id
    # La autorización quedó USADA (A-03).
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"
    assert almacenista.get(f"{AUT}/{autorizacion_id}").json()["estado"] == "USADA"
    assert existencia(session, "KEP", excedente) == 8

    # No se puede reutilizar: ni para otro vale ni repitiéndolo con otro id_cliente.
    de_nuevo = cuerpo_entrega(
        trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
    )
    r2 = almacenista.post(VALES, json=de_nuevo)
    assert r2.status_code == 409 and r2.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert "ya se usó" in r2.json()["mensaje"]
    assert existencia(session, "KEP", excedente) == 8


def test_A_04_el_vale_muestra_quien_pidio_quien_valido_cuando_y_por_que_medio(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev, motivo="Cubre a un compañero")
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
        ),
    )
    valido = almacenista.get(f"{VALES}/{r.json()['id']}").json()["valido"]
    assert valido["autorizo"]["nombre"] == "Supervisor Kepler"
    assert valido["solicito"]["nombre"] == "Almacenista Kepler"
    assert valido["medio"] == "REMOTA" and valido["motivo"] == "Cubre a un compañero"
    assert valido["resuelta_en"].endswith("Z") and valido["autorizacion_id"] == autorizacion_id


def test_A_01_tambien_se_autoriza_con_el_pin_en_el_dispositivo_del_almacenista(
    almacenista, usuario_por_rol, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    r = almacenista.post(
        f"{AUT}/{autorizacion_id}/resolucion",
        json={
            "decision": "APROBAR",
            "usuario": "supervisor",
            "pin": usuario_por_rol("Supervisor").pin,
        },
    )
    assert r.json()["medio"] == "PIN"
    ok = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
        ),
    )
    assert ok.status_code == 201
    valido = almacenista.get(f"{VALES}/{ok.json()['id']}").json()["valido"]
    assert valido["medio"] == "PIN"


def test_A_03_una_autorizacion_pendiente_rechazada_o_inexistente_no_sirve(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    pendiente = solicitar(almacenista, trabajador, ev)
    rechazada = solicitar(almacenista, trabajador, ev)
    supervisor.post(f"{AUT}/{rechazada}/resolucion", json={"decision": "RECHAZAR"})
    vales = total_vales(session)
    for id_ in (pendiente, rechazada):
        r = almacenista.post(
            VALES,
            json=cuerpo_entrega(trabajador, [renglon(excedente.codigo)], autorizacion_id=id_),
        )
        assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=str(uuid.uuid4())
        ),
    )
    assert r.status_code == 404
    assert total_vales(session) == vales


def test_A_03_una_autorizacion_vencida_no_sirve(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    fila = session.get(Autorizacion, uuid.UUID(autorizacion_id))
    fila.vence_en = fila.vence_en - timedelta(hours=1)
    session.flush()
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
        ),
    )
    assert r.status_code == 409 and "venció" in r.json()["mensaje"]


def test_A_03_la_autorizacion_es_de_ese_trabajador(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    otro = crear_trabajador(session)
    # `otro` también tiene un excedente del mismo artículo.
    almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(excedente.codigo)]))
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(otro, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id),
    )
    assert r.status_code == 409 and "otro trabajador" in r.json()["mensaje"]


def test_A_03_si_cambia_la_cantidad_la_autorizacion_ya_no_la_cubre(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo, 1)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo, 2)], autorizacion_id=autorizacion_id
        ),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert "no cubre" in r.json()["mensaje"]
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"


def test_A_03_solo_cubre_los_renglones_senalados(
    almacenista, supervisor, compras, session, trabajador, excedente
):
    otro = crear_articulo(session, retornable=True, limite_cantidad=1, requiere_autorizacion=True)
    abastecer(compras, otro, 5)
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)  # solo `excedente`
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador,
            [renglon(excedente.codigo), renglon(otro.codigo)],
            autorizacion_id=autorizacion_id,
        ),
    )
    assert r.status_code == 409 and otro.codigo in str(r.json()["detalles"])


def test_A_05_quien_autorizo_no_confirma_el_vale(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    kep = str(almacen(session, "KEP").id)
    r = supervisor.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id, almacen_id=kep
        ),
    )
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"


def test_A_03_la_autorizacion_usada_y_el_vale_van_en_la_misma_transaccion(
    almacenista, supervisor, session, trabajador, excedente, monkeypatch
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)

    def falla(self, vale):
        raise RuntimeError("falla simulada después de marcar usada")

    original = MovimientoService._registrar_codigos
    monkeypatch.setattr(MovimientoService, "_registrar_codigos", falla)
    cuerpo = cuerpo_entrega(
        trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
    )
    vales = total_vales(session)
    with pytest.raises(RuntimeError):
        almacenista.post(VALES, json=cuerpo)
    session.rollback()
    assert total_vales(session) == vales
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"
    monkeypatch.setattr(MovimientoService, "_registrar_codigos", original)
    assert almacenista.post(VALES, json=cuerpo).status_code == 201


def test_A_03_una_autorizacion_que_el_vale_no_necesita_no_se_gasta(
    almacenista, supervisor, compras, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    libre = crear_articulo(session)
    abastecer(compras, libre, 5)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(libre.codigo)], autorizacion_id=autorizacion_id),
    )
    assert (
        r.status_code == 201
        and session.get(Vale, uuid.UUID(r.json()["id"])).autorizacion_id is None
    )
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"


def test_US_ESP_001_E_07_E_26_una_sola_autorizacion_cubre_ambos_motivos(
    almacenista, supervisor, compras, session, trabajador
):
    arnes = crear_articulo(
        session,
        retornable=True,
        limite_cantidad=1,
        requiere_autorizacion=True,
        motivo_uso_especial="Equipo restringido",
    )
    abastecer(compras, arnes, 5)
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 2)])
    assert motivos(ev) == ["L-02", "E-26"]
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(arnes.codigo, 2)], autorizacion_id=autorizacion_id
        ),
    )
    assert r.status_code == 201, r.text
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == uuid.UUID(r.json()["id"])))
    assert mov.reglas == ["L-02", "E-26"] and mov.nivel == "NARANJA"
    assert mov.saldo_destino == 2


def test_US_ESP_001_autorizar_y_confirmar_un_articulo_de_uso_especial(
    almacenista, supervisor, compras, session, trabajador
):
    herramienta = crear_articulo(
        session, requiere_autorizacion=True, motivo_uso_especial="Restringido"
    )
    abastecer(compras, herramienta, 3)
    ev = evaluar(almacenista, trabajador, [renglon(herramienta.codigo)])
    assert motivos(ev) == ["E-26"]
    autorizacion_id = solicitar(almacenista, trabajador, ev, motivo="Trabajo en altura")
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(herramienta.codigo)], autorizacion_id=autorizacion_id
        ),
    )
    assert r.status_code == 201


def test_evaluar_con_autorizacion_marca_los_naranjas_cubiertos(
    almacenista, supervisor, session, trabajador, excedente
):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    sin_aprobar = evaluar(
        almacenista, trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
    )
    assert (
        sin_aprobar["puede_confirmar"] is False
        and "no está aprobada" in (sin_aprobar["autorizacion_error"])
    )
    aprobar(supervisor, autorizacion_id)
    con = evaluar(
        almacenista, trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
    )
    assert con["renglones"][0]["autorizado"] is True and con["puede_confirmar"] is True
    assert con["nivel"] == "NARANJA"  # el nivel no cambia: sigue siendo una excepción


# ------------------------------------------------------------------ A-06 y SM-04


@pytest.mark.parametrize(
    "estado", [EstadoPieza.NO_APTO, EstadoPieza.EN_MANTENIMIENTO, EstadoPieza.BAJA]
)
def test_A_06_SM_04_un_rojo_de_seguridad_no_se_envia_a_autorizacion(
    almacenista, compras, session, trabajador, estado
):
    _, pieza = pieza_en_kep(compras, session, estado=estado)
    r = almacenista.post(
        AUT,
        json={
            "trabajador_id": str(trabajador.id),
            "renglones": [
                # La interfaz (o un cliente tramposo) lo marca autorizable: el servidor decide.
                {"codigo": pieza.codigo, "cantidad": 1, "regla": "L-02", "autorizable": True}
            ],
            "motivo": "Urge",
        },
    )
    assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert (
        r.json()["detalles"]["codigo"] == pieza.codigo and r.json()["detalles"]["regla"] == "E-05"
    )


def test_A_06_una_inspeccion_vencida_no_se_envia_a_autorizacion(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigente_hasta=hoy_mx() - timedelta(days=1)
    )
    r = almacenista.post(
        AUT,
        json={
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": pieza.codigo, "cantidad": 1, "regla": "L-02"}],
            "motivo": "Urge",
        },
    )
    assert r.status_code == 422 and r.json()["detalles"]["regla"] == "E-06"


def test_A_06_un_codigo_desconocido_o_un_trabajador_no_vigente_tampoco(
    almacenista, compras, session, trabajador
):
    r = almacenista.post(
        AUT,
        json={
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": "NO-EXISTE-Z", "cantidad": 1, "regla": "L-02"}],
            "motivo": "x",
        },
    )
    assert r.status_code == 422 and r.json()["detalles"]["regla"] == "E-01"
    vencido = crear_trabajador(session, vigente=False)
    arnes = crear_articulo(session, limite_cantidad=1)
    abastecer(compras, arnes, 5)
    r = almacenista.post(
        AUT,
        json={
            "trabajador_id": str(vencido.id),
            "renglones": [{"codigo": arnes.codigo, "cantidad": 1, "regla": "L-02"}],
            "motivo": "x",
        },
    )
    assert r.status_code == 422 and r.json()["detalles"]["regla"] == "E-02"


def test_A_06_un_naranja_legitimo_si_se_envia(almacenista, session, trabajador, excedente):
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    assert solicitar(almacenista, trabajador, ev)


def test_SM_04_la_api_tampoco_confirma_un_rojo_con_una_autorizacion(
    almacenista, supervisor, compras, session, trabajador, excedente
):
    """Aunque exista una autorización aprobada, un renglón en rojo no se confirma."""
    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    _, pieza = pieza_en_kep(compras, session, estado=EstadoPieza.NO_APTO)
    vales = total_vales(session)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador,
            [renglon(excedente.codigo), renglon(pieza.codigo)],
            autorizacion_id=autorizacion_id,
        ),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert total_vales(session) == vales
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"
