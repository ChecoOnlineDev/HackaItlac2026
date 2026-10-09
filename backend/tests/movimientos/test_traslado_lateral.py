# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""FEAT-015: traslados entre almacenes de tercer nivel (X-16 a X-21, cambios a X-03 y A-05).

Una prueba por regla, con su ID en el nombre. Midrex (MID) y HYL son almacenes de tercer nivel que
cuelgan de Contratistas. El supervisor de un almacén es el de los datos de prueba (`sup_mid`...);
la "almacenista con permiso de enviar" es un rol nuevo con solo `traspasos.operar`.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.config import get_settings
from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import RolRepository
from app.modulos.almacenes.models import TipoAlmacen
from app.modulos.autorizaciones.models import Autorizacion, TipoAutorizacion
from app.modulos.movimientos.evaluador_traspasos import (
    ClaseRuta,
    HechosAlmacen,
    clasificar_ruta,
)
from tests.conftest import iniciar_sesion_en
from tests.movimientos.ayudas import abastecer_en, crear_articulo, existencia, total_vales
from tests.movimientos.ayudas_traspasos import (
    EVALUAR,
    POR_RECIBIR,
    VALES,
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    cuerpo_recepcion,
    cuerpo_traspaso,
    enviar,
    evaluar_recepcion,
    evaluar_traspaso,
    movimientos_del_vale,
    recibir,
    reglas,
    renglon,
    vale,
)

AUT = "/api/autorizaciones"


# ---------------------------------------------------------------------------- fixtures


@pytest.fixture
def cliente_con(app, crear_usuario) -> Iterator[Callable[..., tuple[TestClient, object]]]:
    """`cliente_con({permisos}, "MID")`: un cliente con sesión de un rol nuevo con exactamente
    esos permisos, y su usuario."""
    clientes: list[TestClient] = []

    def _cliente(permisos, almacen=None, pin=None):
        usuario = crear_usuario(set(permisos), almacen=almacen, pin=pin)
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente, usuario

    yield _cliente
    for c in clientes:
        c.close()


@pytest.fixture
def ana(cliente_con):
    """Ana: de Midrex, con `traspasos.operar` y sin `autorizaciones.resolver` (X-17)."""
    return cliente_con({P.TRASPASOS_OPERAR}, "MID")[0]


@pytest.fixture
def herramienta(session):
    articulo = crear_articulo(session, retornable=False)
    abastecer_en(session, articulo, 10, "MID")
    return articulo


def contar_autorizaciones(session) -> int:
    return session.scalar(select(func.count()).select_from(Autorizacion))


def pedir(cliente, session, renglones, destino="HYL", motivo="HYL arranca soldadura el lunes"):
    return cliente.post(
        AUT,
        json={
            "tipo": "TRASLADO",
            "destino_almacen_id": str(almacen_id(session, destino)),
            "renglones": renglones,
            "motivo": motivo,
        },
    )


def aprobada(ana, supervisor, session, renglones, destino="HYL") -> str:
    """Ana pide la autorización de un traslado y el supervisor del origen la aprueba."""
    r = pedir(ana, session, renglones, destino)
    assert r.status_code == 201, r.text
    autorizacion_id = r.json()["id"]
    r = supervisor.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200, r.text
    return autorizacion_id


def hechos(clave, tipo, padre=None, activo=True) -> HechosAlmacen:
    return HechosAlmacen(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, clave),
        clave=clave,
        nombre=clave,
        padre_id=uuid.uuid5(uuid.NAMESPACE_DNS, padre) if padre else None,
        activo=activo,
        tipo=tipo,
    )


# ------------------------------------------------------------------------------ X-18 y X-03


def test_x18_clasificar_ruta_es_pura_y_distingue_las_cuatro_clases():
    kepler = hechos("KEP", TipoAlmacen.CENTRAL)
    contratistas = hechos("CON", TipoAlmacen.SUBALMACEN, "KEP")
    midrex = hechos("MID", TipoAlmacen.PROYECTO, "CON")
    hyl = hechos("HYL", TipoAlmacen.PROYECTO, "CON")
    norte = hechos("NOR", TipoAlmacen.SUBALMACEN, "KEP")
    minas_norte = hechos("MNO", TipoAlmacen.PROYECTO, "NOR")
    assert clasificar_ruta(kepler, contratistas) == ClaseRuta.HABITUAL
    assert clasificar_ruta(midrex, contratistas) == ClaseRuta.HABITUAL
    assert clasificar_ruta(midrex, hyl) == ClaseRuta.LATERAL
    # CA-15-09: dos proyectos con padres distintos también son lateral.
    assert clasificar_ruta(midrex, minas_norte) == ClaseRuta.LATERAL
    assert clasificar_ruta(kepler, midrex) == ClaseRuta.NO_HABITUAL
    assert clasificar_ruta(midrex, kepler) == ClaseRuta.NO_HABITUAL
    # Un proyecto a un subalmacén que no es su padre no es lateral.
    assert clasificar_ruta(midrex, norte) == ClaseRuta.NO_HABITUAL
    assert clasificar_ruta(midrex, midrex) == ClaseRuta.MISMO


def test_x18_la_evaluacion_trae_la_ruta_lateral_y_x18_antes_que_x16(
    cliente_almacen, session, herramienta
):
    ev = evaluar_traspaso(cliente_almacen("MID"), session, "HYL", [renglon(herramienta.codigo)])
    assert ev["ruta"]["clase"] == "LATERAL"
    assert reglas(ev) == ["X-18", "X-16"]


def test_x18_ruta_habitual_trae_clase_habitual_y_nadie_autoriza(
    cliente_almacen, session, herramienta
):
    ev = evaluar_traspaso(cliente_almacen("MID"), session, "CON", [renglon(herramienta.codigo)])
    assert ev["ruta"] == {
        "clase": "HABITUAL",
        "autoriza": "NADIE",
        "autorizadores_disponibles": None,
    }
    assert reglas(ev) == ["X-03"]


def test_x03_kepler_a_midrex_sigue_igual_supervisor_rojo_y_administrador_amarillo(
    cliente_almacen, cliente_como, session
):
    articulo = crear_articulo(session, retornable=False)
    abastecer_en(session, articulo, 5, "KEP")
    cuerpo = cuerpo_traspaso(session, "MID", [renglon(articulo.codigo)])
    sup = cliente_almacen("KEP").post(EVALUAR, json=cuerpo).json()
    assert sup["nivel"] == "ROJO"
    assert sup["ruta"]["clase"] == "NO_HABITUAL" and sup["ruta"]["autoriza"] == "NADIE"
    r = cliente_almacen("KEP").post(VALES, json=cuerpo | {"observacion": "Urgente"})
    assert r.status_code == 403 and r.json()["codigo"] == "RUTA_SOLO_ADMINISTRADOR"

    admin = cliente_como("Administrador")
    cuerpo_admin = cuerpo | {"almacen_id": str(almacen_id(session, "KEP"))}
    ev = admin.post(EVALUAR, json=cuerpo_admin).json()
    assert ev["nivel"] == "AMARILLO" and reglas(ev) == ["X-03"]
    assert ev["ruta"]["clase"] == "NO_HABITUAL" and ev["ruta"]["autoriza"] == "ADMINISTRADOR"


def test_x03_midrex_a_kepler_no_es_lateral(cliente_almacen, session, herramienta):
    ev = evaluar_traspaso(cliente_almacen("MID"), session, "KEP", [renglon(herramienta.codigo)])
    assert ev["ruta"]["clase"] == "NO_HABITUAL" and ev["nivel"] == "ROJO"
    assert reglas(ev) == ["X-03"]


def test_x03_el_mismo_almacen_sigue_en_rojo(cliente_almacen, session, herramienta):
    ev = evaluar_traspaso(cliente_almacen("MID"), session, "MID", [renglon(herramienta.codigo)])
    assert ev["ruta"]["clase"] == "MISMO" and ev["nivel"] == "ROJO"
    assert reglas(ev) == ["X-03"]


def test_x18_rol_con_almacenes_todos_sin_resolver_va_por_x03(cliente_con, session, herramienta):
    cliente, _ = cliente_con({P.TRASPASOS_OPERAR, P.ALMACENES_TODOS})
    extra = {"almacen_id": str(almacen_id(session, "MID"))}
    ev = evaluar_traspaso(cliente, session, "HYL", [renglon(herramienta.codigo)], **extra)
    assert reglas(ev) == ["X-18", "X-03"]
    assert ev["nivel"] == "AMARILLO" and ev["pide_observacion"] is True
    assert ev["ruta"]["clase"] == "LATERAL" and ev["ruta"]["autoriza"] == "ADMINISTRADOR"
    cuerpo = cuerpo_traspaso(session, "HYL", [renglon(herramienta.codigo)], **extra)
    r = cliente.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "X-03"
    assert cliente.post(VALES, json=cuerpo | {"observacion": "Sobra en MID"}).status_code == 201


# ------------------------------------------------------------------------------------ X-16


def test_x16_el_supervisor_del_origen_envia_y_su_envio_es_la_autorizacion(
    cliente_almacen, session, herramienta
):
    mid = cliente_almacen("MID")
    renglones = [renglon(herramienta.codigo, 2)]
    ev = evaluar_traspaso(mid, session, "HYL", renglones)
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert ev["pide_observacion"] is True
    assert reglas(ev) == ["X-18", "X-16"]
    assert ev["ruta"] == {
        "clase": "LATERAL",
        "autoriza": "ENVIO_PROPIO",
        "autorizadores_disponibles": None,
    }
    assert "Tú lo autorizas" in ev["motivos"][1]["mensaje"]

    antes, autorizaciones = total_vales(session), contar_autorizaciones(session)
    cuerpo = cuerpo_traspaso(session, "HYL", renglones)
    r = mid.post(VALES, json=cuerpo)  # sin observación
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert r.json()["detalles"][0]["campo"] == "observacion"
    assert r.json()["detalles"][0]["regla"] == "X-16"
    assert mid.post(VALES, json=cuerpo | {"observacion": "   "}).status_code == 422
    assert total_vales(session) == antes

    traspaso = mid.post(VALES, json=cuerpo | {"observacion": "HYL arranca soldadura"})
    assert traspaso.status_code == 201, traspaso.text
    assert vale(session, traspaso.json()["id"]).estado == "EN_TRANSITO"
    for m in movimientos_del_vale(session, traspaso.json()["id"]):
        assert "X-16" in m.reglas and "X-18" in m.reglas  # CA-15-01
    # No se creó ninguna solicitud: nadie se autoriza a sí mismo una solicitud (A-05).
    assert contar_autorizaciones(session) == autorizaciones
    assert existencia(session, "MID", herramienta) == 8

    detalle = mid.get(f"{VALES}/{traspaso.json()['id']}").json()
    assert detalle["valido"]["medio"] == "ENVIO_PROPIO"
    assert detalle["valido"]["autorizo"]["nombre"] == "Supervisor Midrex"
    assert detalle["valido"]["autorizacion_id"] is None


def test_x16_el_administrador_tambien_envia_por_envio_propio(cliente_como, session, herramienta):
    admin = cliente_como("Administrador")
    extra = {"almacen_id": str(almacen_id(session, "MID"))}
    ev = evaluar_traspaso(admin, session, "HYL", [renglon(herramienta.codigo)], **extra)
    assert reglas(ev) == ["X-18", "X-16"] and ev["ruta"]["autoriza"] == "ENVIO_PROPIO"
    r = admin.post(
        VALES,
        json=cuerpo_traspaso(session, "HYL", [renglon(herramienta.codigo)], **extra)
        | {"observacion": "Reparto"},
    )
    assert r.status_code == 201, r.text


def test_x16_el_supervisor_de_hyl_no_es_supervisor_del_origen_midrex(
    cliente_almacen, session, herramienta
):
    # El permiso es por clave y por alcance: sup_hyl (Supervisor de HYL) opera HYL, no Midrex.
    sup_hyl = cliente_almacen("HYL")
    r = sup_hyl.post(
        EVALUAR,
        json=cuerpo_traspaso(session, "HYL", [renglon(herramienta.codigo)])
        | {"almacen_id": str(almacen_id(session, "MID"))},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"


# ------------------------------------------------------------------------------------ X-17


def test_x17_quien_no_es_supervisor_ve_naranja_y_no_confirma_sin_autorizacion(
    ana, session, herramienta
):
    renglones = [renglon(herramienta.codigo, 2)]
    ev = evaluar_traspaso(ana, session, "HYL", renglones)
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    assert reglas(ev) == ["X-18", "X-17"]
    assert ev["ruta"]["clase"] == "LATERAL" and ev["ruta"]["autoriza"] == "SUPERVISOR_ORIGEN"
    # Cuántos pueden autorizar, sin contarla a ella: el supervisor de Midrex y el Administrador.
    assert ev["ruta"]["autorizadores_disponibles"] >= 2
    x17 = ev["motivos"][1]
    assert x17["nivel"] == "NARANJA" and x17["autorizable"] is True and x17["autorizado"] is False
    assert "lo autoriza el supervisor de Midrex" in x17["mensaje"]

    antes = total_vales(session)
    r = ana.post(VALES, json=cuerpo_traspaso(session, "HYL", renglones))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"  # CA-15-02
    assert total_vales(session) == antes
    assert existencia(session, "MID", herramienta) == 10


def test_x17_flujo_completo_pedir_autorizar_enviar_y_la_autorizacion_queda_usada(
    ana, cliente_almacen, session, herramienta
):
    sup_mid = cliente_almacen("MID")
    renglones = [renglon(herramienta.codigo, 2)]
    pedida = pedir(ana, session, renglones)
    assert pedida.status_code == 201, pedida.text
    assert pedida.json()["estado"] == "PENDIENTE" and pedida.json()["tipo"] == "TRASLADO"
    autorizacion_id = pedida.json()["id"]
    fila = session.get(Autorizacion, uuid.UUID(autorizacion_id))
    assert fila.trabajador_id is None and fila.tipo == TipoAutorizacion.TRASLADO  # CA-15-03
    assert fila.almacen_id == almacen_id(session, "MID")
    assert fila.vence_en - fila.creado_en == timedelta(minutes=15)
    assert fila.detalle["destino_almacen_id"] == str(almacen_id(session, "HYL"))

    # El supervisor del origen la ve con tipo, origen y destino; trabajador va vacío.
    lista = sup_mid.get(AUT, params={"tipo": "TRASLADO"}).json()["elementos"]
    tarjeta = next(e for e in lista if e["id"] == autorizacion_id)
    assert tarjeta["tipo"] == "TRASLADO" and tarjeta["trabajador"] is None
    assert tarjeta["origen"]["clave"] == "MID" and tarjeta["destino"]["clave"] == "HYL"
    assert tarjeta["renglones"][0]["codigo"] == herramienta.codigo

    resuelta = sup_mid.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})
    assert resuelta.status_code == 200 and resuelta.json()["estado"] == "APROBADA"
    assert resuelta.json()["medio"] == "REMOTA"
    consulta = ana.get(f"{AUT}/{autorizacion_id}").json()
    assert consulta["tipo"] == "TRASLADO" and consulta["trabajador"] is None
    assert consulta["origen"]["clave"] == "MID" and consulta["destino"]["clave"] == "HYL"

    # Con la autorización el semáforo la marca cubierta.
    cuerpo = cuerpo_traspaso(session, "HYL", renglones, autorizacion_id=autorizacion_id)
    ev = ana.post(EVALUAR, json=cuerpo).json()
    assert ev["puede_confirmar"] is True and ev["autorizacion_error"] is None
    assert ev["motivos"][1]["regla"] == "X-17" and ev["motivos"][1]["autorizado"] is True

    r = ana.post(VALES, json=cuerpo)
    assert r.status_code == 201, r.text
    # Autorización y vale en la misma transacción: USADA y ligada al vale (A-03).
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"
    assert str(vale(session, r.json()["id"]).autorizacion_id) == autorizacion_id
    assert all("X-17" in m.reglas for m in movimientos_del_vale(session, r.json()["id"]))
    assert existencia(session, "MID", herramienta) == 8

    detalle = sup_mid.get(f"{VALES}/{r.json()['id']}").json()
    assert detalle["valido"]["medio"] == "REMOTA"
    assert detalle["valido"]["autorizo"]["nombre"] == "Supervisor Midrex"
    assert detalle["valido"]["solicito"]["nombre"].startswith("Usuario de prueba")

    # Una sola vez (A-03): el segundo vale con la misma autorización se rechaza.
    otra = ana.post(
        VALES, json=cuerpo_traspaso(session, "HYL", renglones, autorizacion_id=autorizacion_id)
    )
    assert otra.status_code == 409 and otra.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert existencia(session, "MID", herramienta) == 8


def test_x17_con_pin_del_supervisor_en_el_dispositivo_de_quien_envia(ana, session, herramienta):
    r = pedir(ana, session, [renglon(herramienta.codigo)])
    ajustes = get_settings()
    r = ana.post(
        f"{AUT}/{r.json()['id']}/resolucion",
        json={"decision": "APROBAR", "usuario": "sup_mid", "pin": ajustes.pin_datos_prueba},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APROBADA" and r.json()["medio"] == "PIN"


def test_x17_la_notificacion_no_existe_aun_pero_la_solicitud_se_ve_en_autorizaciones(
    ana, cliente_almacen, session, herramienta
):
    # Sin el módulo `notificaciones` (FEAT-014) la solicitud llega por la lista del supervisor.
    pedir(ana, session, [renglon(herramienta.codigo)])
    pendientes = cliente_almacen("MID").get(AUT).json()
    assert pendientes["total"] >= 1


def test_x17_rechazada_vencida_o_pendiente_no_confirma_y_no_guarda_nada(
    ana, cliente_almacen, session, herramienta
):
    sup_mid = cliente_almacen("MID")
    renglones = [renglon(herramienta.codigo)]
    antes = total_vales(session)

    # Rechazada.
    rechazada = pedir(ana, session, renglones).json()["id"]
    sup_mid.post(f"{AUT}/{rechazada}/resolucion", json={"decision": "RECHAZAR"})
    # Pendiente.
    pendiente = pedir(ana, session, renglones).json()["id"]
    # Aprobada y vencida antes de confirmar.
    vencida = aprobada(ana, sup_mid, session, renglones)
    fila = session.get(Autorizacion, uuid.UUID(vencida))
    fila.vence_en = ahora_utc() - timedelta(minutes=1)
    session.flush()

    for autorizacion_id, texto in (
        (rechazada, "no está aprobada"),
        (pendiente, "no está aprobada"),
        (vencida, "venció"),
    ):
        cuerpo = cuerpo_traspaso(session, "HYL", renglones, autorizacion_id=autorizacion_id)
        r = ana.post(VALES, json=cuerpo)
        assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA", r.text
        assert texto in r.json()["mensaje"]
        ev = ana.post(EVALUAR, json=cuerpo).json()
        assert ev["puede_confirmar"] is False and texto in ev["autorizacion_error"]
    assert total_vales(session) == antes
    assert existencia(session, "MID", herramienta) == 10


def test_x17_una_autorizacion_de_otro_origen_o_de_entrega_no_sirve(
    ana, cliente_almacen, session, herramienta
):
    renglones = [renglon(herramienta.codigo)]
    autorizacion_id = aprobada(ana, cliente_almacen("MID"), session, renglones)
    # Otro destino.
    r = ana.post(
        VALES,
        json=cuerpo_traspaso(session, "LAM", renglones, autorizacion_id=autorizacion_id),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert "otro destino" in r.json()["mensaje"]


def test_x17_aviso_cuando_nadie_mas_puede_autorizar_no_bloquea_la_solicitud(
    ana, session, herramienta
):
    session.execute(
        update(Usuario).where(Usuario.usuario.in_(["sup_mid", "admin"])).values(activo=False)
    )
    session.flush()
    ev = evaluar_traspaso(ana, session, "HYL", [renglon(herramienta.codigo)])
    assert ev["ruta"]["autorizadores_disponibles"] == 0
    assert "Nadie en Midrex puede autorizar ahora" in ev["motivos"][1]["mensaje"]
    assert pedir(ana, session, [renglon(herramienta.codigo)]).status_code == 201


# ------------------------------------------------------------------------------------ X-19


def test_x19_solo_se_pueden_quitar_renglones_de_lo_autorizado(
    ana, cliente_almacen, session, herramienta
):
    otra = crear_articulo(session, retornable=False)
    abastecer_en(session, otra, 10, "MID")
    tercera = crear_articulo(session, retornable=False)
    abastecer_en(session, tercera, 10, "MID")
    renglones = [renglon(herramienta.codigo, 2), renglon(otra.codigo, 3)]
    autorizacion_id = aprobada(ana, cliente_almacen("MID"), session, renglones)
    antes = total_vales(session)

    def enviar_con(destino, renglones_vale):
        return ana.post(
            VALES,
            json=cuerpo_traspaso(session, destino, renglones_vale, autorizacion_id=autorizacion_id),
        )

    # Agregar un renglón, subir una cantidad o cambiar el destino: no la cubre (CA-15-06).
    casos = (
        ("HYL", [*renglones, renglon(tercera.codigo)]),
        ("HYL", [renglon(herramienta.codigo, 3), renglon(otra.codigo, 3)]),
        ("LAM", renglones),
    )
    for destino, renglones_vale in casos:
        r = enviar_con(destino, renglones_vale)
        assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA", r.text
    assert total_vales(session) == antes
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"

    # Quitar un renglón sí se permite, y gasta la autorización.
    r = enviar_con("HYL", [renglon(herramienta.codigo, 2)])
    assert r.status_code == 201, r.text
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"


def test_x19_un_renglon_en_rojo_no_se_autoriza(ana, session, herramienta):
    antes = contar_autorizaciones(session)
    r = pedir(ana, session, [renglon(herramienta.codigo, 99)])  # solo hay 10 en Midrex
    assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert r.json()["detalles"]["regla"] == "X-02"
    r = pedir(ana, session, [renglon("NO-EXISTE-XYZ")])
    assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert contar_autorizaciones(session) == antes  # no se guardó nada


def test_x19_un_destino_que_no_existe_no_se_autoriza(ana, session, herramienta):
    r = ana.post(
        AUT,
        json={
            "tipo": "TRASLADO",
            "destino_almacen_id": str(uuid.uuid4()),
            "renglones": [renglon(herramienta.codigo)],
            "motivo": "Prueba",
        },
    )
    assert r.status_code == 404


def test_x19_quien_no_necesita_autorizacion_no_la_pide(cliente_almacen, session, herramienta):
    # El supervisor del origen (X-16) y una ruta habitual (X-03) no usan autorización.
    sup = pedir(cliente_almacen("MID"), session, [renglon(herramienta.codigo)])
    assert sup.status_code == 422 and sup.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert sup.json()["detalles"]["regla"] == "X-17"
    habitual = pedir(cliente_almacen("MID"), session, [renglon(herramienta.codigo)], destino="CON")
    assert habitual.status_code == 422


def test_x19_se_aprueba_o_se_rechaza_completa_sin_renglones(
    ana, cliente_almacen, session, herramienta
):
    autorizacion_id = pedir(ana, session, [renglon(herramienta.codigo)]).json()["id"]
    r = cliente_almacen("MID").post(
        f"{AUT}/{autorizacion_id}/resolucion",
        json={"decision": "APROBAR", "renglones": [{"renglon": 1, "decision": "APROBAR"}]},
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "X-19"
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "PENDIENTE"


def test_x19_solo_resuelve_el_supervisor_del_origen_o_el_administrador(
    ana, cliente_almacen, cliente_como, session, herramienta
):
    autorizacion_id = pedir(ana, session, [renglon(herramienta.codigo)]).json()["id"]
    resolver = f"{AUT}/{autorizacion_id}/resolucion"
    # El supervisor de HYL (el destino) y el de Laminador no son supervisores del origen: 404.
    for clave in ("HYL", "LAM"):
        r = cliente_almacen(clave).post(resolver, json={"decision": "APROBAR"})
        assert r.status_code == 404, (clave, r.text)
    # Quien la pidió no tiene `autorizaciones.resolver`: 403 sin permiso.
    assert ana.post(resolver, json={"decision": "APROBAR"}).status_code == 403
    # El Administrador sí (almacenes.todos).
    r = cliente_como("Administrador").post(resolver, json={"decision": "APROBAR"})
    assert r.status_code == 200 and r.json()["estado"] == "APROBADA"


def test_a05_quien_pidio_el_traslado_no_lo_autoriza_a_si_mismo(
    app, crear_usuario, session, herramienta
):
    usuario = crear_usuario({P.TRASPASOS_OPERAR}, almacen="MID")
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    autorizacion_id = pedir(cliente, session, [renglon(herramienta.codigo)]).json()["id"]
    # Le dan después `autorizaciones.resolver`: aun así no puede autorizar lo que él pidió.
    actual = RolRepository(session)
    fila = session.scalar(select(Usuario).where(Usuario.usuario == usuario.usuario))
    actual.reemplazar_permisos(fila.rol_id, {P.TRASPASOS_OPERAR, P.AUTORIZACIONES_RESOLVER})
    session.flush()
    r = cliente.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"
    cliente.close()


def test_a05_el_envio_propio_del_supervisor_no_crea_solicitud_que_el_mismo_resuelva(
    cliente_almacen, session, herramienta
):
    # Excepción de A-05 y AC-07 (X-16): su envío es la autorización; no hay solicitud.
    antes = contar_autorizaciones(session)
    enviar(
        cliente_almacen("MID"),
        session,
        "HYL",
        [renglon(herramienta.codigo)],
        observacion="Sobra en Midrex",
    )
    assert contar_autorizaciones(session) == antes


def test_x19_permisos_pedir_un_traslado_exige_traspasos_operar_en_el_servicio(
    cliente_con, cliente_almacen, session, herramienta
):
    renglones = [renglon(herramienta.codigo)]
    # Un almacenista (entregas.crear, sin traspasos.operar): 403.
    sin_permiso, _ = cliente_con({P.ENTREGAS_CREAR, P.TRASPASOS_RECIBIR}, "MID")
    r = pedir(sin_permiso, session, renglones)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    # Sin sesión: 401.
    assert TestClient(sin_permiso.app).post(AUT, json={}).status_code == 401
    # `traspasos.operar` basta para un traslado, pero no para un excedente (entregas.crear).
    con_permiso, _ = cliente_con({P.TRASPASOS_OPERAR}, "MID")
    assert pedir(con_permiso, session, renglones).status_code == 201
    excedente = con_permiso.post(
        AUT,
        json={
            "tipo": "EXCEDENTE",
            "trabajador_id": str(uuid.uuid4()),
            "renglones": renglones,
            "motivo": "x",
        },
    )
    assert excedente.status_code == 403 and excedente.json()["codigo"] == "SIN_PERMISO"
    # Un traslado no lleva trabajador y un excedente sí lo exige.
    mal = con_permiso.post(
        AUT,
        json={
            "tipo": "TRASLADO",
            "trabajador_id": str(uuid.uuid4()),
            "destino_almacen_id": str(almacen_id(session, "HYL")),
            "renglones": renglones,
            "motivo": "x",
        },
    )
    assert mal.status_code == 422


def test_x19_con_pin_la_sesion_de_quien_envia_debe_tener_traspasos_operar(
    cliente_con, ana, session, herramienta
):
    autorizacion_id = pedir(ana, session, [renglon(herramienta.codigo)]).json()["id"]
    # Una sesión con `entregas.crear` pero sin `traspasos.operar` no sirve de dispositivo.
    otro, _ = cliente_con({P.ENTREGAS_CREAR}, "MID")
    r = otro.post(
        f"{AUT}/{autorizacion_id}/resolucion",
        json={"decision": "APROBAR", "usuario": "sup_mid", "pin": get_settings().pin_datos_prueba},
    )
    assert r.status_code == 403


def test_x19_la_autorizacion_y_el_vale_se_escriben_en_una_sola_transaccion(
    ana, cliente_almacen, session, herramienta, monkeypatch
):
    """Si algo falla después de marcar la autorización USADA, todo se deshace: el vale no queda y
    la autorización sigue APROBADA."""
    renglones = [renglon(herramienta.codigo)]
    autorizacion_id = aprobada(ana, cliente_almacen("MID"), session, renglones)

    def falla(self, vale):
        raise RuntimeError("falla simulada después de marcar usada")

    monkeypatch.setattr(
        "app.modulos.movimientos.service.MovimientoService._registrar_codigos", falla
    )
    antes = total_vales(session)
    with pytest.raises(RuntimeError):
        ana.post(
            VALES, json=cuerpo_traspaso(session, "HYL", renglones, autorizacion_id=autorizacion_id)
        )
    session.expire_all()
    assert total_vales(session) == antes
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"
    assert existencia(session, "MID", herramienta) == 10


# ------------------------------------------------------------------------------------ X-20


def test_x20_el_traslado_aparece_en_por_recibir_con_ruta_lateral_y_quien_lo_valido(
    ana, cliente_almacen, session, herramienta
):
    sup_mid, sup_hyl = cliente_almacen("MID"), cliente_almacen("HYL")
    envio = enviar(sup_mid, session, "HYL", [renglon(herramienta.codigo, 3)], observacion="Reparto")
    elementos = sup_hyl.get(POR_RECIBIR).json()["elementos"]
    propio = next(e for e in elementos if e["id"] == envio["id"])
    assert propio["ruta"] == "LATERAL" and propio["origen"]["clave"] == "MID"
    assert propio["valido"]["medio"] == "ENVIO_PROPIO"
    assert propio["valido"]["autorizo"]["nombre"] == "Supervisor Midrex"

    autorizacion_id = aprobada(ana, sup_mid, session, [renglon(herramienta.codigo, 2)])
    con_autorizacion = ana.post(
        VALES,
        json=cuerpo_traspaso(
            session, "HYL", [renglon(herramienta.codigo, 2)], autorizacion_id=autorizacion_id
        ),
    ).json()
    elementos = sup_hyl.get(POR_RECIBIR).json()["elementos"]
    autorizado = next(e for e in elementos if e["id"] == con_autorizacion["id"])
    assert autorizado["ruta"] == "LATERAL" and autorizado["valido"]["medio"] == "REMOTA"
    assert sup_hyl.get(POR_RECIBIR, params={"solo_contar": True}).json()["total"] >= 2

    # Un traspaso habitual sigue siendo HABITUAL y sin "Validó".
    habitual = enviar(sup_mid, session, "CON", [renglon(herramienta.codigo)])
    elementos = cliente_almacen("CON").get(POR_RECIBIR).json()["elementos"]
    normal = next(e for e in elementos if e["id"] == habitual["id"])
    assert normal["ruta"] == "HABITUAL" and normal["valido"] is None


def test_x20_sin_nadie_que_reciba_en_el_destino_es_un_aviso_amarillo_que_no_bloquea(
    cliente_almacen, session, herramienta
):
    session.execute(
        update(Usuario).where(Usuario.almacen_id == almacen_id(session, "HYL")).values(activo=False)
    )
    session.flush()
    mid = cliente_almacen("MID")
    ev = evaluar_traspaso(mid, session, "HYL", [renglon(herramienta.codigo)])
    assert reglas(ev) == ["X-18", "X-16", "X-20"]
    aviso = ev["motivos"][2]
    assert aviso["nivel"] == "AMARILLO"
    assert aviso["mensaje"] == "Nadie en HYL puede recibir este traslado todavía."
    assert ev["puede_confirmar"] is True
    # No pide una observación extra: con la de X-16 se confirma.
    r = mid.post(
        VALES,
        json=cuerpo_traspaso(session, "HYL", [renglon(herramienta.codigo)])
        | {"observacion": "Para cuando abra HYL"},
    )
    assert r.status_code == 201, r.text
    assert all("X-20" in m.reglas for m in movimientos_del_vale(session, r.json()["id"]))


def test_x20_el_destino_recibe_el_traslado_con_diferencias_como_cualquier_traspaso(
    cliente_almacen, session, herramienta
):
    sup_mid, sup_hyl = cliente_almacen("MID"), cliente_almacen("HYL")
    envio = enviar(sup_mid, session, "HYL", [renglon(herramienta.codigo, 5)], observacion="Reparto")
    codigo = herramienta.codigo
    # Recibe 2 de 5 con la observación obligatoria (RG-14): Recibido con diferencias (X-13).
    recibir(sup_hyl, envio, [renglon(codigo, 2)])
    assert vale(session, envio["id"]).estado == "RECIBIDO_CON_DIFERENCIAS"
    assert existencia(session, "HYL", herramienta) == 2
    # El resto llega después: se recibe otra vez y el traspaso queda Recibido.
    recibir(sup_hyl, envio, [renglon(codigo, 3)], observacion=None)
    assert vale(session, envio["id"]).estado == "RECIBIDO"
    assert existencia(session, "HYL", herramienta) == 5


def test_x20_cancelar_un_traslado_lateral_regresa_la_existencia_y_la_autorizacion_sigue_usada(
    ana, cliente_almacen, session, herramienta
):
    sup_mid = cliente_almacen("MID")
    renglones = [renglon(herramienta.codigo, 4)]
    autorizacion_id = aprobada(ana, sup_mid, session, renglones)
    envio = ana.post(
        VALES, json=cuerpo_traspaso(session, "HYL", renglones, autorizacion_id=autorizacion_id)
    ).json()
    assert existencia(session, "MID", herramienta) == 6
    r = sup_mid.post(
        f"{VALES}/{envio['id']}/cancelacion",
        json={"motivo": "Se mandó a HYL por error", "id_cliente": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.text
    assert existencia(session, "MID", herramienta) == 10  # CA-15-14
    session.expire_all()
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"


# ------------------------------------------------------------------------------------ X-21


def test_x21_quien_envio_y_recibe_la_misma_persona_pide_observacion_y_queda_marcado(
    cliente_como, cliente_almacen, session
):
    articulo = crear_articulo(session, retornable=False)
    abastecer_en(session, articulo, 5, "KEP")
    admin = cliente_como("Administrador")
    envio = enviar(
        admin,
        session,
        "CON",
        [renglon(articulo.codigo, 2)],
        almacen_id=str(almacen_id(session, "KEP")),
    )
    destino = {"almacen_id": str(almacen_id(session, "CON"))}

    ev = evaluar_recepcion(admin, envio, [renglon(articulo.codigo, 2)], **destino)
    assert reglas(ev) == ["X-21"] and ev["nivel"] == "AMARILLO"
    assert ev["pide_observacion"] is True and ev["puede_confirmar"] is True
    assert "Tú enviaste este traspaso" in ev["motivos"][0]["mensaje"]

    cuerpo = cuerpo_recepcion(envio["id"], [renglon(articulo.codigo, 2)], **destino)
    sin_obs = admin.post(VALES, json=cuerpo | {"observacion": None})
    assert sin_obs.status_code == 422, sin_obs.text
    assert sin_obs.json()["detalles"][0]["regla"] == "X-21"
    assert vale(session, envio["id"]).estado == "EN_TRANSITO"

    con_obs = admin.post(VALES, json=cuerpo | {"observacion": "Yo mismo lo llevé a Contratistas"})
    assert con_obs.status_code == 201, con_obs.text
    assert "X-21" in con_obs.json()["renglones"][0]["reglas"]
    assert vale(session, envio["id"]).estado == "RECIBIDO"


def test_x21_otro_usuario_que_recibe_no_dispara_el_aviso(cliente_almacen, session, herramienta):
    envio = enviar(
        cliente_almacen("MID"), session, "CON", [renglon(herramienta.codigo)], observacion=None
    )
    ev = evaluar_recepcion(cliente_almacen("CON"), envio, [renglon(herramienta.codigo)])
    assert "X-21" not in reglas(ev) and ev["pide_observacion"] is False
