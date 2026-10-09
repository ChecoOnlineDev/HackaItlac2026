"""Pruebas del módulo `autorizaciones` (US-AUT-001): A-01 a A-06, AC-07 y permisos."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.excepciones import SinPermiso
from app.core.tiempo import ahora_utc
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.autorizaciones import service as modulo_service
from app.modulos.autorizaciones.exceptions import (
    AutorizacionInvalida,
    AutorizacionPropia,
    RenglonNoAutorizable,
)
from app.modulos.autorizaciones.models import Autorizacion, EstadoAutorizacion, MedioAutorizacion
from app.modulos.autorizaciones.schemas import RenglonSolicitud, RenglonSolicitudIn, SolicitudCreate
from app.modulos.autorizaciones.service import (
    TRANSICIONES,
    AutorizacionService,
    RenglonVale,
)
from app.modulos.trabajadores.models import Trabajador
from tests.conftest import iniciar_sesion_en

E = EstadoAutorizacion
RUTA = "/api/autorizaciones"


@pytest.fixture
def trabajador(session) -> Trabajador:
    t = Trabajador(numero_empleado=f"E-{uuid.uuid4().hex[:8]}", nombre="Juan Pérez")
    session.add(t)
    session.flush()
    return t


def renglon(codigo="ALT-024", cantidad=3, **extra) -> dict:
    base = {
        "codigo": codigo,
        "articulo": "Guante de carnaza",
        "cantidad": cantidad,
        "limite": 2,
        "tiene": 0,
        "excedente": cantidad - 2,
        "regla": "L-01",
    }
    return base | extra


def cuerpo(trabajador, renglones=None, motivo="Trabajo especial") -> dict:
    return {
        "trabajador_id": str(trabajador.id),
        "renglones": renglones if renglones is not None else [renglon()],
        "motivo": motivo,
    }


@pytest.fixture
def pedir(cliente_como, trabajador):
    """El almacenista (KEP) crea una solicitud y devuelve su id."""
    alm = cliente_como("Almacenista")

    def _pedir(**kw) -> str:
        r = alm.post(RUTA, json=cuerpo(trabajador, **kw))
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _pedir


def cliente_de(app, usuario) -> TestClient:
    c = TestClient(app)
    assert iniciar_sesion_en(c, usuario).status_code == 200
    return c


def tiempo_en(monkeypatch, delta: timedelta) -> None:
    ahora = ahora_utc()
    monkeypatch.setattr(modulo_service, "ahora_utc", lambda: ahora + delta)


# --------------------------------------------------------------- solicitar


def test_US_AUT_001_solicitar_responde_id_estado_y_vence_en_15_minutos(
    cliente_como, trabajador, session
):
    r = cliente_como("Almacenista").post(RUTA, json=cuerpo(trabajador))
    assert r.status_code == 201
    datos = r.json()
    assert datos["estado"] == "PENDIENTE" and datos["vence_en"].endswith("Z")
    fila = session.get(Autorizacion, uuid.UUID(datos["id"]))
    assert fila.vence_en - fila.creado_en == timedelta(minutes=15)
    assert fila.detalle["renglones"][0]["regla"] == "L-01"
    # El almacén sale de la sesión del almacenista (KEP).
    assert fila.almacen_id is not None


def test_A_02_el_motivo_es_obligatorio(cliente_como, trabajador):
    alm = cliente_como("Almacenista")
    assert alm.post(RUTA, json=cuerpo(trabajador, motivo="   ")).status_code == 422
    sin_motivo = cuerpo(trabajador)
    del sin_motivo["motivo"]
    assert alm.post(RUTA, json=sin_motivo).status_code == 422


def test_AC_04_solicitar_exige_entregas_crear(client, crear_usuario, iniciar_sesion, trabajador):
    sin = crear_usuario({P.VALES_VER}, almacen="KEP")
    iniciar_sesion(client, sin)
    r = client.post(RUTA, json=cuerpo(trabajador))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert TestClient(client.app).post(RUTA, json=cuerpo(trabajador)).status_code == 401


def test_solicitar_con_trabajador_inexistente_da_404(cliente_como):
    r = cliente_como("Almacenista").post(
        RUTA, json={"trabajador_id": str(uuid.uuid4()), "renglones": [renglon()], "motivo": "x"}
    )
    assert r.status_code == 404


def test_A_06_un_renglon_rojo_no_se_envia_a_autorizacion(cliente_como, trabajador):
    # El verificador falso (conftest) trata `ROJO*` como un rojo de la evaluación del servidor.
    r = cliente_como("Almacenista").post(RUTA, json=cuerpo(trabajador, [renglon("ROJO-1")]))
    assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"


def test_A_06_punto_de_extension_con_verificador_falso(session, crear_usuario, trabajador):
    crear_usuario({P.ENTREGAS_CREAR}, almacen="KEP")
    almacenista = UsuarioRepository(session).get_by_usuario("almacenista")
    datos = SolicitudCreate(
        trabajador_id=trabajador.id,
        renglones=[RenglonSolicitudIn(codigo="ALT-024", cantidad=3)],
        motivo="m",
    )
    llamadas = []

    def rojo(almacen_id, trabajador_id, renglones):
        llamadas.append((almacen_id, trabajador_id, [r.codigo for r in renglones]))
        raise RenglonNoAutorizable()

    def evaluado(almacen_id, trabajador_id, renglones):
        return [RenglonSolicitud(**renglon(r.codigo, r.cantidad)) for r in renglones]

    servicio = AutorizacionService(session)
    with pytest.raises(RenglonNoAutorizable):
        servicio.solicitar(almacenista, datos, verificador_renglones=rojo)
    assert llamadas and llamadas[0][2] == ["ALT-024"]
    assert servicio.solicitar(almacenista, datos, verificador_renglones=evaluado).id


# ------------------------------------------------------------ ver y listar


def test_A_01_ver_estado_solo_solicitante_o_quien_resuelve(app, cliente_como, pedir, crear_usuario):
    id_ = pedir()
    assert cliente_como("Almacenista").get(f"{RUTA}/{id_}").json()["estado"] == "PENDIENTE"
    assert cliente_como("Supervisor").get(f"{RUTA}/{id_}").status_code == 200
    otro = crear_usuario({P.ENTREGAS_CREAR}, almacen="KEP")
    assert cliente_de(app, otro).get(f"{RUTA}/{id_}").status_code == 404
    assert TestClient(app).get(f"{RUTA}/{id_}").status_code == 401
    assert cliente_como("Supervisor").get(f"{RUTA}/{uuid.uuid4()}").status_code == 404


def test_US_AUT_001_lista_del_supervisor_con_tarjetas(cliente_como, pedir):
    id_ = pedir()
    r = cliente_como("Supervisor").get(f"{RUTA}?estado=PENDIENTE")
    assert r.status_code == 200
    tarjeta = next(e for e in r.json()["elementos"] if e["id"] == id_)
    assert tarjeta["trabajador"]["nombre"] == "Juan Pérez"
    assert tarjeta["solicitada_por"]["nombre"]
    assert tarjeta["excedente_total"] == 1 and tarjeta["motivo"] == "Trabajo especial"
    assert tarjeta["renglones"][0]["articulo"] == "Guante de carnaza"


def test_AC_04_listar_exige_autorizaciones_resolver(cliente_como):
    assert cliente_como("Almacenista").get(RUTA).status_code == 403


def test_AC_06_alcance_por_almacen(app, cliente_como, pedir, crear_usuario):
    id_ = pedir()  # almacén KEP
    de_con = crear_usuario({P.AUTORIZACIONES_RESOLVER}, almacen="CON", pin="4321")
    de_kep = crear_usuario({P.AUTORIZACIONES_RESOLVER}, almacen="KEP", pin="4321")
    c_con, c_kep = cliente_de(app, de_con), cliente_de(app, de_kep)
    assert id_ not in [e["id"] for e in c_con.get(RUTA).json()["elementos"]]
    assert id_ in [e["id"] for e in c_kep.get(RUTA).json()["elementos"]]
    assert id_ in [e["id"] for e in cliente_como("Supervisor").get(RUTA).json()["elementos"]]
    assert c_con.get(f"{RUTA}/{id_}").status_code == 404
    r = c_con.post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 404


# --------------------------------------------------------------- resolución


def test_A_01_resolver_remota_aprueba_y_registra_a_04(cliente_como, pedir, session):
    id_ = pedir()
    r = cliente_como("Supervisor").post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["estado"] == "APROBADA" and datos["medio"] == "REMOTA"
    assert datos["resuelta_por"]["nombre"] and datos["resuelta_en"]
    # El solicitante ve el resultado al consultar.
    assert cliente_como("Almacenista").get(f"{RUTA}/{id_}").json()["estado"] == "APROBADA"
    fila = session.get(Autorizacion, uuid.UUID(id_))
    valido = AutorizacionService(session).datos_valido(fila)
    assert valido.medio == MedioAutorizacion.REMOTA and valido.motivo == "Trabajo especial"


def test_A_01_resolver_remota_rechaza(cliente_como, pedir):
    id_ = pedir()
    r = cliente_como("Supervisor").post(
        f"{RUTA}/{id_}/resolucion", json={"decision": "RECHAZAR", "motivo": "No corresponde"}
    )
    assert r.json()["estado"] == "RECHAZADA"


def test_AC_04_resolver_remota_exige_el_permiso(cliente_como, pedir):
    id_ = pedir()
    r = cliente_como("Almacenista").post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_A_01_resolver_con_pin_desde_el_dispositivo_del_almacenista(
    cliente_como, pedir, usuario_por_rol, session
):
    id_ = pedir()
    pin = usuario_por_rol("Supervisor").pin
    r = cliente_como("Almacenista").post(
        f"{RUTA}/{id_}/resolucion",
        json={"decision": "APROBAR", "usuario": "supervisor", "pin": pin},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APROBADA" and r.json()["medio"] == "PIN"
    assert r.json()["resuelta_por"]["nombre"] == "Supervisor Kepler"


def test_A_01_pin_incorrecto_da_403_y_no_resuelve(cliente_como, pedir, session):
    id_ = pedir()
    alm = cliente_como("Almacenista")
    r = alm.post(
        f"{RUTA}/{id_}/resolucion",
        json={"decision": "APROBAR", "usuario": "supervisor", "pin": "0000"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "PIN_INCORRECTO"
    assert alm.get(f"{RUTA}/{id_}").json()["estado"] == "PENDIENTE"
    r = alm.post(
        f"{RUTA}/{id_}/resolucion",
        json={"decision": "APROBAR", "usuario": "no_existe", "pin": "0000"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "PIN_INCORRECTO"


def test_A_01_cinco_pin_incorrectos_bloquean_cinco_minutos(cliente_como, pedir, usuario_por_rol):
    id_ = pedir()
    alm = cliente_como("Almacenista")
    mal = {"decision": "APROBAR", "usuario": "supervisor", "pin": "0000"}
    for _ in range(4):
        assert alm.post(f"{RUTA}/{id_}/resolucion", json=mal).status_code == 403
    quinto = alm.post(f"{RUTA}/{id_}/resolucion", json=mal)
    assert quinto.status_code == 429
    assert quinto.json()["detalles"]["segundos_espera"] == get_settings().bloqueo_segundos
    bien = mal | {"pin": usuario_por_rol("Supervisor").pin}
    bloqueado = alm.post(f"{RUTA}/{id_}/resolucion", json=bien)
    assert bloqueado.status_code == 429  # ni con el PIN correcto mientras dura el bloqueo


def test_A_01_el_pin_es_de_un_usuario_con_el_permiso_de_autorizar(
    cliente_como, pedir, crear_usuario, app
):
    id_ = pedir()
    sin_permiso = crear_usuario({P.ENTREGAS_CREAR}, almacen="KEP", pin="4321")
    r = cliente_como("Almacenista").post(
        f"{RUTA}/{id_}/resolucion",
        json={"decision": "APROBAR", "usuario": sin_permiso.usuario, "pin": "4321"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_A_05_quien_pide_no_se_autoriza_a_si_mismo_remota(app, crear_usuario, trabajador):
    ambos = crear_usuario({P.ENTREGAS_CREAR, P.AUTORIZACIONES_RESOLVER}, almacen="KEP")
    c = cliente_de(app, ambos)
    id_ = c.post(RUTA, json=cuerpo(trabajador)).json()["id"]
    r = c.post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"
    assert c.get(f"{RUTA}/{id_}").json()["estado"] == "PENDIENTE"


def test_A_05_quien_pide_no_se_autoriza_a_si_mismo_con_su_pin(app, crear_usuario, trabajador):
    ambos = crear_usuario({P.ENTREGAS_CREAR, P.AUTORIZACIONES_RESOLVER}, almacen="KEP", pin="4321")
    c = cliente_de(app, ambos)
    id_ = c.post(RUTA, json=cuerpo(trabajador)).json()["id"]
    r = c.post(
        f"{RUTA}/{id_}/resolucion",
        json={"decision": "APROBAR", "usuario": ambos.usuario, "pin": "4321"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"


def test_AC_07_la_base_impide_autorizarse_a_si_mismo(session, pedir):
    from sqlalchemy.exc import DBAPIError

    from app.core import errores_bd

    id_ = pedir()
    fila = session.get(Autorizacion, uuid.UUID(id_))
    fila.resuelta_por = fila.solicitada_por
    with pytest.raises(DBAPIError) as e:
        session.flush()
    assert errores_bd.es_restriccion(e.value, "ck_autorizacion_no_autorizarse")
    session.rollback()


def test_A_03_una_solicitud_resuelta_no_se_resuelve_de_nuevo(cliente_como, pedir):
    id_ = pedir()
    sup = cliente_como("Supervisor")
    assert (
        sup.post(
            f"{RUTA}/{id_}/resolucion", json={"decision": "RECHAZAR", "motivo": "No corresponde"}
        ).status_code
        == 200
    )
    r = sup.post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_RESUELTA"
    assert sup.get(f"{RUTA}/{id_}").json()["estado"] == "RECHAZADA"


def test_A_03_resolver_ya_resuelta_con_pin_no_gasta_intentos(cliente_como, pedir):
    id_ = pedir()
    cliente_como("Supervisor").post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    alm = cliente_como("Almacenista")
    mal = {"decision": "APROBAR", "usuario": "supervisor", "pin": "0000"}
    for _ in range(6):
        assert alm.post(f"{RUTA}/{id_}/resolucion", json=mal).status_code == 409


def test_A_03_la_solicitud_vence_a_los_15_minutos(cliente_como, pedir, monkeypatch):
    id_ = pedir()
    alm, sup = cliente_como("Almacenista"), cliente_como("Supervisor")
    tiempo_en(monkeypatch, timedelta(minutes=14))
    assert alm.get(f"{RUTA}/{id_}").json()["estado"] == "PENDIENTE"
    tiempo_en(monkeypatch, timedelta(minutes=15, seconds=1))
    assert alm.get(f"{RUTA}/{id_}").json()["estado"] == "VENCIDA"
    r = sup.post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_RESUELTA"
    assert id_ not in [e["id"] for e in sup.get(RUTA).json()["elementos"]]


def test_A_03_vencida_se_persiste_al_resolver_y_en_la_lista(
    cliente_como, pedir, monkeypatch, session
):
    id_ = pedir()
    sup = cliente_como("Supervisor")
    tiempo_en(monkeypatch, timedelta(minutes=16))
    assert id_ not in [e["id"] for e in sup.get(RUTA).json()["elementos"]]
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(id_)).estado == E.VENCIDA
    vencidas = sup.get(f"{RUTA}?estado=VENCIDA").json()["elementos"]
    assert id_ in [e["id"] for e in vencidas]


def test_A_03_maquina_de_estados():
    assert TRANSICIONES[E.PENDIENTE] == {E.APROBADA, E.RECHAZADA, E.VENCIDA}
    assert TRANSICIONES[E.APROBADA] == {E.USADA}
    for terminal in (E.RECHAZADA, E.VENCIDA, E.USADA):
        assert TRANSICIONES[terminal] == frozenset()


# ----------------------------------------- servicios para otros módulos (A-03)


@pytest.fixture
def aprobada(cliente_como, pedir, session):
    id_ = uuid.UUID(pedir(renglones=[renglon("ALT-024", 3), renglon("GU-001", 5)]))
    r = cliente_como("Supervisor").post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200
    fila = session.get(Autorizacion, id_)
    return fila


def _vale(session, fila, usuario=None, renglones=None, **cambios):
    almacenista = usuario or UsuarioRepository(session).get_by_usuario("almacenista")
    return AutorizacionService(session).validar_para_vale(
        fila.id,
        cambios.get("almacen_id", fila.almacen_id),
        cambios.get("trabajador_id", fila.trabajador_id),
        renglones or [RenglonVale("ALT-024", 3)],
        almacenista,
    )


def test_A_03_validar_para_vale_acepta_la_autorizacion_aprobada(session, aprobada):
    assert _vale(session, aprobada).id == aprobada.id
    assert _vale(session, aprobada, renglones=[RenglonVale("ALT-024", 3), RenglonVale("GU-001", 5)])


def test_A_03_no_cubre_otro_renglon_ni_otra_cantidad(session, aprobada):
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada, renglones=[RenglonVale("ALT-024", 4)])
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada, renglones=[RenglonVale("OTRO-1", 1)])


def test_A_03_debe_ser_del_mismo_almacen_y_trabajador(session, aprobada):
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada, trabajador_id=uuid.uuid4())
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada, almacen_id=uuid.uuid4())


def test_A_03_pendiente_o_rechazada_no_sirven(session, cliente_como, pedir):
    id_ = pedir()
    fila = session.get(Autorizacion, uuid.UUID(id_))
    with pytest.raises(AutorizacionInvalida):
        _vale(session, fila)
    cliente_como("Supervisor").post(
        f"{RUTA}/{id_}/resolucion", json={"decision": "RECHAZAR", "motivo": "No corresponde"}
    )
    session.expire_all()
    with pytest.raises(AutorizacionInvalida):
        _vale(session, fila)


def test_A_03_aprobada_vencida_no_sirve(session, aprobada, monkeypatch):
    tiempo_en(monkeypatch, timedelta(minutes=16))
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada)


def test_A_03_se_usa_una_sola_vez(session, aprobada):
    servicio = AutorizacionService(session)
    servicio.marcar_usada(aprobada.id)
    assert aprobada.estado == E.USADA
    with pytest.raises(AutorizacionInvalida):
        _vale(session, aprobada)
    with pytest.raises(AutorizacionInvalida):
        servicio.marcar_usada(aprobada.id)
    # Y "Validó" sigue disponible después de usarla (A-04).
    assert servicio.datos_valido(aprobada).nombre


def test_A_05_el_autorizador_no_confirma_el_vale(session, aprobada):
    supervisor = UsuarioRepository(session).get_by_usuario("supervisor")
    with pytest.raises(AutorizacionPropia):
        _vale(session, aprobada, usuario=supervisor)


def test_A_04_la_auditoria_registra_solicitud_y_resolucion(cliente_como, pedir, session):
    from sqlalchemy import select

    from app.modulos.auditoria.models import Auditoria

    id_ = pedir()
    cliente_como("Supervisor").post(f"{RUTA}/{id_}/resolucion", json={"decision": "APROBAR"})
    acciones = set(
        session.scalars(select(Auditoria.accion).where(Auditoria.entidad_id == id_)).all()
    )
    assert {"autorizacion.solicitar", "autorizacion.aprobar"} <= acciones


def test_A_05_sin_permiso_error_de_dominio_es_sin_http():
    assert issubclass(AutorizacionPropia, SinPermiso)


def test_AC_06_quien_opera_todos_los_almacenes_indica_el_almacen_al_solicitar(
    cliente_como, trabajador, session
):
    """Quien tiene `almacenes.todos` (solo el Administrador) que captura una entrega pide la
    autorización indicando el almacén en el que opera; sin indicarlo se le pide."""
    from sqlalchemy import select

    from app.modulos.almacenes.models import Almacen

    supervisor = cliente_como("Administrador")
    kep = session.scalar(select(Almacen.id).where(Almacen.clave == "KEP"))

    sin_almacen = supervisor.post(RUTA, json=cuerpo(trabajador))
    assert sin_almacen.status_code == 422
    assert sin_almacen.json()["detalles"][0]["campo"] == "almacen_id"

    con_almacen = supervisor.post(RUTA, json={**cuerpo(trabajador), "almacen_id": str(kep)})
    assert con_almacen.status_code == 201, con_almacen.text
    guardada = session.get(Autorizacion, uuid.UUID(con_almacen.json()["id"]))
    assert guardada.almacen_id == kep
