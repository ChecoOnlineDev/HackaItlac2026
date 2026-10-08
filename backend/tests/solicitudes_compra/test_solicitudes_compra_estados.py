"""El seguimiento de Compras: SC-04, SC-05, SC-06, SC-07, SC-08 y SC-11."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.core.errores_bd import es_restriccion
from app.main import create_app
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen
from app.modulos.movimientos.models import Existencia, Vale
from app.modulos.solicitudes_compra.models import SolicitudCompra, SolicitudCompraEvento
from app.modulos.solicitudes_compra.service import TRANSICIONES_DE_COMPRAS
from tests.ayudas_guion import alta_trabajador, entregar
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    total_movimientos,
    total_vales,
)
from tests.solicitudes_compra.ayudas import RUTA, estado, pedir

ESTADOS = ["PENDIENTE", "EN_COMPRA", "COMPRADA", "INGRESADA", "RECHAZADA", "CANCELADA"]


def _llevar_a(compras, solicitante, objetivo: str) -> dict:
    """Una solicitud nueva de Kepler llevada por el camino válido hasta `objetivo`."""
    s = pedir(solicitante)
    camino = {
        "PENDIENTE": [],
        "EN_COMPRA": [("EN_COMPRA", {})],
        "COMPRADA": [("EN_COMPRA", {}), ("COMPRADA", {})],
        "INGRESADA": [("EN_COMPRA", {}), ("COMPRADA", {}), ("INGRESADA", {})],
        "RECHAZADA": [("RECHAZADA", {"nota": "No procede"})],
        "CANCELADA": [],
    }[objetivo]
    for nuevo, extra in camino:
        s = estado(compras, s["id"], nuevo, **extra)
    if objetivo == "CANCELADA":
        r = solicitante.post(f"{RUTA}/{s['id']}/cancelacion")
        assert r.status_code == 200, r.text
        s = r.json()
    return s


# ------------------------------------------------------------------------------- SC-04


def test_SC_04_el_camino_completo_pendiente_en_compra_comprada_ingresada(como):
    compras, almacenista = como("compras"), como("almacenista")
    s = pedir(almacenista)
    antes = s["actualizada_en"]
    s = estado(compras, s["id"], "EN_COMPRA", nota="Cotizando")
    assert s["estado"] == "EN_COMPRA" and s["nota_compras"] == "Cotizando"
    assert s["actualizada_en"] >= antes and s["creada_en"] == antes
    s = estado(compras, s["id"], "COMPRADA", nota="Orden 4471, llega el viernes")
    assert s["estado"] == "COMPRADA" and s["nota_compras"] == "Orden 4471, llega el viernes"
    s = estado(compras, s["id"], "INGRESADA")
    assert s["estado"] == "INGRESADA" and s["acciones"] == []
    assert [(e["estado_anterior"], e["estado_nuevo"]) for e in s["eventos"]] == [
        (None, "PENDIENTE"),
        ("PENDIENTE", "EN_COMPRA"),
        ("EN_COMPRA", "COMPRADA"),
        ("COMPRADA", "INGRESADA"),
    ]
    assert [e["usuario"]["nombre"] for e in s["eventos"]] == [
        "Almacenista Kepler",
        "Compras de prueba",
        "Compras de prueba",
        "Compras de prueba",
    ]
    # Lo que el almacenista ve al abrirla es lo mismo, con sus propias acciones.
    assert almacenista.get(f"{RUTA}/{s['id']}").json()["estado"] == "INGRESADA"


@pytest.mark.parametrize(
    "origen,destino,extra",
    [
        ("PENDIENTE", "EN_COMPRA", {}),
        ("PENDIENTE", "RECHAZADA", {"nota": "Ya hay en otro almacén"}),
        ("EN_COMPRA", "COMPRADA", {}),
        ("EN_COMPRA", "RECHAZADA", {"nota": "El proveedor ya no lo fabrica"}),
        ("COMPRADA", "INGRESADA", {}),
    ],
)
def test_SC_04_cada_transicion_valida_agrega_su_evento(como, origen, destino, extra):
    compras, almacenista = como("compras"), como("almacenista")
    s = _llevar_a(compras, almacenista, origen)
    n = len(s["eventos"])
    s = estado(compras, s["id"], destino, **extra)
    assert s["estado"] == destino and len(s["eventos"]) == n + 1
    ultimo = s["eventos"][-1]
    assert (ultimo["estado_anterior"], ultimo["estado_nuevo"]) == (origen, destino)
    assert ultimo["nota"] == extra.get("nota")


@pytest.mark.parametrize(
    "origen,destino",
    [(o, d) for o in ESTADOS for d in ESTADOS if d not in TRANSICIONES_DE_COMPRAS.get(o, ())],
)
def test_SC_04_cualquier_otra_transicion_es_409_y_no_cambia_nada(como, origen, destino):
    compras, almacenista = como("compras"), como("almacenista")
    s = _llevar_a(compras, almacenista, origen)
    r = compras.post(f"{RUTA}/{s['id']}/estado", json={"estado": destino, "nota": "una nota"})
    assert r.status_code == 409, f"{origen} -> {destino}: {r.text}"
    assert r.json()["codigo"] == "TRANSICION_INVALIDA"
    detalles = r.json()["detalles"]
    assert detalles["regla"] == "SC-04" and detalles["estado_actual"] == origen
    assert detalles["estado_pedido"] == destino
    despues = compras.get(f"{RUTA}/{s['id']}").json()
    assert despues["estado"] == origen and len(despues["eventos"]) == len(s["eventos"])


def test_SC_04_una_solicitud_inexistente_es_404(como):
    r = como("compras").post(f"{RUTA}/{uuid.uuid4()}/estado", json={"estado": "EN_COMPRA"})
    assert r.status_code == 404


def test_SC_04_el_servidor_calcula_las_acciones_segun_el_permiso_y_el_estado(como):
    compras, almacenista, supervisor, admin = (
        como("compras"),
        como("almacenista"),
        como("supervisor"),
        como("admin"),
    )
    s = pedir(almacenista)

    def acciones(cliente) -> list[str]:
        return cliente.get(f"{RUTA}/{s['id']}").json()["acciones"]

    assert acciones(compras) == ["tomar", "rechazar"]
    assert acciones(almacenista) == ["cancelar"]  # quien la pidió
    assert acciones(supervisor) == ["cancelar"]  # supervisor de su almacén
    assert acciones(admin) == ["tomar", "rechazar", "cancelar"]  # tiene ambos permisos
    estado(compras, s["id"], "EN_COMPRA")
    assert acciones(compras) == ["rechazar", "comprar"]
    assert acciones(almacenista) == acciones(supervisor) == []
    assert acciones(admin) == ["rechazar", "comprar"]
    estado(compras, s["id"], "COMPRADA")
    assert acciones(compras) == ["ingresar"] == acciones(admin)
    estado(compras, s["id"], "INGRESADA")
    assert acciones(compras) == acciones(admin) == []
    # La lista trae las mismas acciones en cada elemento.
    en_lista = {x["id"]: x["acciones"] for x in compras.get(RUTA).json()["elementos"]}
    assert en_lista[s["id"]] == []


def test_SC_04_las_acciones_de_quien_solo_pide_nunca_incluyen_las_de_compras(con_permisos, como):
    solo_pide = con_permisos({P.COMPRAS_SOLICITAR}, almacen="KEP")
    s = pedir(solo_pide)
    assert s["acciones"] == ["cancelar"]
    r = solo_pide.post(f"{RUTA}/{s['id']}/estado", json={"estado": "EN_COMPRA"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


# ------------------------------------------------------------------------------- SC-05


@pytest.mark.parametrize("origen", ["PENDIENTE", "EN_COMPRA"])
@pytest.mark.parametrize("nota", [..., None, "", "   "])
def test_SC_05_rechazar_exige_una_nota(como, origen, nota):
    compras, almacenista = como("compras"), como("almacenista")
    s = _llevar_a(compras, almacenista, origen)
    extra = {} if nota is ... else {"nota": nota}
    r = compras.post(f"{RUTA}/{s['id']}/estado", json={"estado": "RECHAZADA"} | extra)
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert r.json()["detalles"][0]["regla"] == "SC-05"
    assert compras.get(f"{RUTA}/{s['id']}").json()["estado"] == origen


def test_SC_05_el_rechazo_deja_la_nota_a_la_vista_de_quien_pidio(como):
    compras, almacenista = como("compras"), como("almacenista")
    s = pedir(almacenista)
    estado(compras, s["id"], "RECHAZADA", nota="Ya hay dos en Contratistas: pide un traspaso")
    visto = almacenista.get(f"{RUTA}/{s['id']}").json()
    assert visto["estado"] == "RECHAZADA"
    assert visto["nota_compras"] == "Ya hay dos en Contratistas: pide un traspaso"
    assert visto["eventos"][-1]["nota"] == visto["nota_compras"]


# ------------------------------------------------------------------------------- SC-06


def _entrada(compras, session) -> dict:
    return abastecer(compras, crear_articulo(session), 5)


def test_SC_06_ingresar_sin_vale_es_valido(como):
    compras = como("compras")
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    s = estado(compras, s["id"], "INGRESADA")
    assert s["vale_entrada"] is None


def test_SC_06_ingresar_liga_un_vale_de_entrada_real(como, session):
    compras = como("compras")
    vale = _entrada(compras, session)
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    s = estado(compras, s["id"], "INGRESADA", vale_entrada_id=vale["id"], nota="Ya en estante")
    assert s["vale_entrada"] == {"id": vale["id"], "folio": vale["folio"]}
    assert vale["folio"].startswith("KEP-ING-")
    # Quien la pidió ve el vale ligado en el detalle y en la lista.
    visto = como("almacenista").get(f"{RUTA}/{s['id']}").json()
    assert visto["vale_entrada"] == s["vale_entrada"]
    en_lista = {x["id"]: x for x in como("almacenista").get(RUTA).json()["elementos"]}
    assert en_lista[s["id"]]["vale_entrada"] == s["vale_entrada"]


def test_SC_06_un_vale_que_no_es_de_entrada_se_rechaza(como, session):
    compras = como("compras")
    trabajador = alta_trabajador(como("rh"))
    entrega = entregar(como("almacenista"), trabajador["id"], [{"codigo": "LENTE-CL"}])
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    r = compras.post(
        f"{RUTA}/{s['id']}/estado",
        json={"estado": "INGRESADA", "vale_entrada_id": entrega["id"]},
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "SC-06"
    assert compras.get(f"{RUTA}/{s['id']}").json()["estado"] == "COMPRADA"


def test_SC_06_un_vale_de_entrada_cancelado_se_rechaza(como, session):
    compras = como("compras")
    vale = _entrada(compras, session)
    r = compras.post(
        f"/api/vales/{vale['id']}/cancelacion",
        json={"motivo": "Se capturó mal", "id_cliente": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.text
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    r = compras.post(
        f"{RUTA}/{s['id']}/estado",
        json={"estado": "INGRESADA", "vale_entrada_id": vale["id"]},
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "SC-06"


def test_EK_05_SC_06_un_vale_inexistente_o_que_no_es_de_kepler_se_rechaza(como, session):
    compras, admin = como("compras"), como("admin")
    # Una entrada vieja a Contratistas (de antes de EK-01): se simula moviendo el vale de sitio.
    entrada = _entrada(compras, session)
    contratistas = session.scalar(select(Almacen.id).where(Almacen.clave == "CON"))
    session.get(Vale, uuid.UUID(entrada["id"])).almacen_id = contratistas
    session.flush()
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    for vale_id in (str(uuid.uuid4()), entrada["id"]):
        for cliente in (compras, admin):
            r = cliente.post(
                f"{RUTA}/{s['id']}/estado",
                json={"estado": "INGRESADA", "vale_entrada_id": vale_id},
            )
            assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "SC-06", vale_id


def test_EK_05_el_vale_de_entrada_de_kepler_se_liga_y_el_almacen_pide_recibir_por_traspaso(
    como, session
):
    compras = como("compras")
    vale = _entrada(compras, session)
    assert vale["folio"].startswith("KEP-ING-")
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    s = estado(compras, s["id"], "INGRESADA", vale_entrada_id=vale["id"])
    assert s["vale_entrada"]["folio"] == vale["folio"]


@pytest.mark.parametrize("destino", ["EN_COMPRA", "COMPRADA", "RECHAZADA"])
def test_SC_06_el_vale_solo_se_indica_al_ingresar(como, session, destino):
    compras = como("compras")
    vale = _entrada(compras, session)
    origen = "EN_COMPRA" if destino == "COMPRADA" else "PENDIENTE"
    s = _llevar_a(compras, como("almacenista"), origen)
    r = compras.post(
        f"{RUTA}/{s['id']}/estado",
        json={"estado": destino, "nota": "x", "vale_entrada_id": vale["id"]},
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "SC-06"


def test_SC_06_la_base_solo_deja_ligar_un_vale_a_una_solicitud_ingresada(como, session):
    compras = como("compras")
    vale = _entrada(compras, session)
    s = _llevar_a(compras, como("almacenista"), "COMPRADA")
    solicitud = session.get(SolicitudCompra, uuid.UUID(s["id"]))
    solicitud.vale_entrada_id = uuid.UUID(vale["id"])
    with pytest.raises(DBAPIError) as error:
        session.flush()
    assert es_restriccion(error.value, "ck_solicitud_compra_vale_solo_ingresada")
    session.rollback()


# ------------------------------------------------------------------------------- SC-07


def test_SC_07_quien_la_pidio_la_cancela_mientras_esta_pendiente(como):
    almacenista = como("almacenista")
    s = pedir(almacenista)
    r = almacenista.post(f"{RUTA}/{s['id']}/cancelacion", json={"nota": "Ya apareció"})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["estado"] == "CANCELADA" and s["acciones"] == []
    assert s["eventos"][-1]["estado_anterior"] == "PENDIENTE"
    assert s["eventos"][-1]["nota"] == "Ya apareció"
    assert s["eventos"][-1]["usuario"]["nombre"] == "Almacenista Kepler"


def test_SC_07_la_nota_de_la_cancelacion_es_opcional_y_el_cuerpo_tambien(como):
    almacenista = como("almacenista")
    sin_cuerpo = pedir(almacenista)
    assert almacenista.post(f"{RUTA}/{sin_cuerpo['id']}/cancelacion").status_code == 200
    sin_nota = pedir(almacenista)
    r = almacenista.post(f"{RUTA}/{sin_nota['id']}/cancelacion", json={})
    assert r.status_code == 200 and r.json()["eventos"][-1]["nota"] is None


def test_SC_07_un_supervisor_del_mismo_almacen_y_el_administrador_tambien_la_cancelan(como):
    s1, s2 = pedir(como("almacenista")), pedir(como("almacenista"))
    assert como("supervisor").post(f"{RUTA}/{s1['id']}/cancelacion").status_code == 200
    assert como("admin").post(f"{RUTA}/{s2['id']}/cancelacion").status_code == 200


def test_SC_07_otro_almacenista_del_mismo_almacen_no_la_cancela(como, con_permisos):
    s = pedir(como("almacenista"))
    colega = con_permisos({P.COMPRAS_SOLICITAR, P.CATALOGO_VER}, almacen="KEP")
    assert colega.get(f"{RUTA}/{s['id']}").status_code == 200  # la ve (es de su almacén)
    r = colega.post(f"{RUTA}/{s['id']}/cancelacion")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert r.json()["detalles"]["regla"] == "SC-07"
    assert como("almacenista").get(f"{RUTA}/{s['id']}").json()["estado"] == "PENDIENTE"


def test_SC_07_un_supervisor_de_otro_almacen_no_la_ve_ni_la_cancela(como):
    s = pedir(como("almacenista"))
    r = como("sup_mid").post(f"{RUTA}/{s['id']}/cancelacion")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_SC_07_compras_no_cancela_solicitudes_ajenas(como):
    s = pedir(como("almacenista"))
    r = como("compras").post(f"{RUTA}/{s['id']}/cancelacion")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


@pytest.mark.parametrize("origen", ["EN_COMPRA", "COMPRADA", "INGRESADA", "RECHAZADA", "CANCELADA"])
def test_SC_07_solo_se_cancela_mientras_esta_pendiente(como, origen):
    compras, almacenista = como("compras"), como("almacenista")
    s = _llevar_a(compras, almacenista, origen)
    r = almacenista.post(f"{RUTA}/{s['id']}/cancelacion")
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"
    assert r.json()["detalles"] == {"regla": "SC-07", "estado_actual": origen}
    assert almacenista.get(f"{RUTA}/{s['id']}").json()["estado"] == origen


def test_SC_07_una_cancelada_no_vuelve_a_moverse(como):
    compras, almacenista = como("compras"), como("almacenista")
    s = _llevar_a(compras, almacenista, "CANCELADA")
    for nuevo in ("EN_COMPRA", "RECHAZADA"):
        r = compras.post(f"{RUTA}/{s['id']}/estado", json={"estado": nuevo, "nota": "x"})
        assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"


# ------------------------------------------------------------------------------- SC-08


def test_SC_08_no_hay_endpoint_que_edite_o_borre_una_solicitud_ni_sus_eventos():
    rutas = {
        camino: set(operaciones)
        for camino, operaciones in create_app().openapi()["paths"].items()
        if "solicitudes-compra" in camino
    }
    assert set(rutas) == {
        "/api/solicitudes-compra",
        "/api/solicitudes-compra/{solicitud_id}",
        "/api/solicitudes-compra/{solicitud_id}/estado",
        "/api/solicitudes-compra/{solicitud_id}/cancelacion",
    }
    usados = set().union(*rutas.values())
    assert usados == {"get", "post"}, f"hay métodos que editan o borran: {rutas}"
    # Los eventos no tienen ruta propia: solo se leen dentro del detalle.
    assert not any("evento" in camino for camino in rutas)


def test_SC_08_los_eventos_de_antes_nunca_cambian(como, session):
    compras, almacenista = como("compras"), como("almacenista")
    s = pedir(almacenista)
    primeros = como("almacenista").get(f"{RUTA}/{s['id']}").json()["eventos"]
    estado(compras, s["id"], "EN_COMPRA", nota="Uno")
    estado(compras, s["id"], "RECHAZADA", nota="Dos")
    ahora = compras.get(f"{RUTA}/{s['id']}").json()["eventos"]
    assert ahora[: len(primeros)] == primeros
    assert [e["nota"] for e in ahora] == [None, "Uno", "Dos"]
    assert (
        session.scalar(
            select(func.count())
            .select_from(SolicitudCompraEvento)
            .where(SolicitudCompraEvento.solicitud_id == uuid.UUID(s["id"]))
        )
        == 3
    )


def test_SC_08_un_cambio_que_falla_no_deja_evento_ni_cambia_la_solicitud(como, session):
    compras, almacenista = como("compras"), como("almacenista")
    s = pedir(almacenista)
    antes = session.scalar(select(func.count()).select_from(SolicitudCompraEvento))
    assert compras.post(f"{RUTA}/{s['id']}/estado", json={"estado": "RECHAZADA"}).status_code == 422
    assert compras.post(f"{RUTA}/{s['id']}/estado", json={"estado": "INGRESADA"}).status_code == 409
    assert session.scalar(select(func.count()).select_from(SolicitudCompraEvento)) == antes
    assert compras.get(f"{RUTA}/{s['id']}").json()["actualizada_en"] == s["actualizada_en"]


# ------------------------------------------------------------------------------- SC-11


def test_SC_11_el_modulo_no_escribe_vales_movimientos_ni_existencias(como, session):
    compras, almacenista = como("compras"), como("almacenista")
    vale = _entrada(compras, session)
    antes = (
        total_vales(session),
        total_movimientos(session),
        session.scalar(select(func.coalesce(func.sum(Existencia.cantidad), 0))),
    )
    s = _llevar_a(compras, almacenista, "COMPRADA")
    estado(compras, s["id"], "INGRESADA", vale_entrada_id=vale["id"])
    otra = pedir(almacenista)
    almacenista.post(f"{RUTA}/{otra['id']}/cancelacion")
    despues = (
        total_vales(session),
        total_movimientos(session),
        session.scalar(select(func.coalesce(func.sum(Existencia.cantidad), 0))),
    )
    assert despues == antes
    # Ni el vale ligado cambió: sigue como lo dejó `movimientos`.
    assert session.scalar(select(Vale.estado).where(Vale.id == uuid.UUID(vale["id"]))) == "EMITIDO"
