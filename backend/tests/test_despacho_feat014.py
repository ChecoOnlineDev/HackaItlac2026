"""FEAT-014: API real, semáforo, aprobación parcial e inventario en una transacción."""

import base64
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
from sqlalchemy import select

from app.config import get_settings
from app.core.excepciones import DemasiadosIntentos, NoEncontrado
from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import SesionDispositivo
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import Categoria
from app.modulos.notificaciones.schemas import SuscripcionIn
from app.modulos.notificaciones.service import NotificacionService
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
)


@pytest.fixture
def datos(session, cliente_como, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    # La tarea posterior al commit se prueba aparte; una conexión ajena no ve savepoints.
    monkeypatch.setattr(
        "app.modulos.autorizaciones.router.enviar_aviso_autorizacion", lambda *a: None
    )
    monkeypatch.setattr("app.modulos.movimientos.router.enviar_aviso_autorizacion", lambda *a: None)
    a = cliente_como("Almacenista")
    sup = cliente_como("Supervisor")
    compras = cliente_como("Compras")
    t = crear_trabajador(session)
    cat = session.scalar(select(Categoria).where(Categoria.tipo == "EPP").limit(1))
    epp = crear_articulo(session, retornable=False)
    epp.categoria_id = cat.id
    herramienta = crear_articulo(session)
    session.flush()
    abastecer(compras, epp, 10)
    abastecer(compras, herramienta, 10)
    return SimpleNamespace(a=a, sup=sup, t=t, epp=epp, herramienta=herramienta)


def evaluar(d, rows, **kw):
    r = d.a.post(
        "/api/vales/evaluar",
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(d.t.id),
            "renglones": rows,
            "observacion": "Entrega de prueba sin proyecto",
            **kw,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def pedir(d, rows=None, **kw):
    body = {
        "tipo": "DESPACHO",
        "id_cliente": str(uuid.uuid4()),
        "trabajador_id": str(d.t.id),
        "renglones": rows or [{"codigo": d.epp.codigo, "cantidad": 2}],
        **kw,
    }
    r = d.a.post("/api/autorizaciones", json=body)
    assert r.status_code == 201, r.text
    return r.json(), body


def confirmar(d, rows, **kw):
    return d.a.post(
        "/api/vales",
        json=cuerpo_entrega(d.t, rows, observacion="Entrega de prueba sin proyecto", **kw),
    )


def test_DE_01_DE_02_etiqueta_no_cambia_semaforo_y_bloquea_sin_stock(datos, session):
    d = datos
    rows = [{"codigo": d.epp.codigo, "cantidad": 2}]
    e = evaluar(d, rows)
    assert e["despacho"]["modo"] == "CON_APROBACION"
    assert e["requiere_aprobacion_despacho"] and not e["puede_confirmar"]
    assert e["renglones"][0]["nivel"] == "VERDE"
    assert e["renglones"][0]["es_epp"] and e["renglones"][0]["requiere_aprobacion"]
    r = confirmar(d, rows)
    assert r.status_code == 409 and r.json()["codigo"] == "REQUIERE_APROBACION_DESPACHO"
    assert existencia(session, "KEP", d.epp) == 10


def test_DE_01_solo_herramienta_no_pide_despacho(datos):
    e = evaluar(datos, [{"codigo": datos.herramienta.codigo, "cantidad": 1}])
    assert not e["requiere_aprobacion_despacho"] and e["despacho"]["modo"] == "NO_APLICA"


def test_DE_04_DE_05_idempotencia_motivo_sistema_y_colision(datos, session):
    d = datos
    out, body = pedir(d)
    a = session.get(Autorizacion, uuid.UUID(out["id"]))
    assert a.motivo == "Despacho de EPP" and out["avisados"] == 0
    repetida = d.a.post("/api/autorizaciones", json=body)
    assert repetida.status_code == 200 and repetida.json()["id"] == out["id"]
    cambiado = body | {"nota": "Otro contenido"}
    assert d.a.post("/api/autorizaciones", json=cambiado).status_code == 409


def test_DE_06_DE_08_parcial_rechazo_disminucion_y_uso_unico(datos, session):
    d = datos
    otro = crear_articulo(session, retornable=False)
    otro.categoria_id = d.epp.categoria_id
    session.flush()
    from app.modulos.almacenes.service import AlmacenService
    from app.modulos.movimientos.models import Existencia

    ubicacion = AlmacenService(session).ubicacion_de_almacen(almacen(session).id)
    session.add(Existencia(ubicacion_id=ubicacion.id, articulo_id=otro.id, cantidad=10))
    session.commit()
    rows = [{"codigo": d.epp.codigo, "cantidad": 2}, {"codigo": otro.codigo, "cantidad": 1}]
    out, _ = pedir(d, rows)
    resolved = d.sup.post(
        f"/api/autorizaciones/{out['id']}/resolucion",
        json={
            "renglones": [
                {"renglon": 1, "decision": "APROBAR"},
                {"renglon": 2, "decision": "RECHAZAR", "motivo": "No corresponde"},
            ]
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["estado"] == "APROBADA"
    ev = evaluar(d, rows, autorizacion_id=out["id"])
    assert [r["aprobacion"] for r in ev["renglones"]] == ["APROBADO", "RECHAZADO"]
    bad = confirmar(d, rows, autorizacion_id=out["id"])
    assert bad.status_code == 409 and bad.json()["codigo"] == "APROBACION_INVALIDA"
    assert existencia(session, "KEP", d.epp) == 10
    good = confirmar(d, [{"codigo": d.epp.codigo, "cantidad": 1}], autorizacion_id=out["id"])
    assert good.status_code == 201, good.text
    assert "DE-01" in good.json()["renglones"][0]["reglas"]
    assert session.get(Autorizacion, uuid.UUID(out["id"])).estado == "USADA"
    assert existencia(session, "KEP", d.epp) == 9
    assert (
        confirmar(
            d, [{"codigo": d.epp.codigo, "cantidad": 1}], autorizacion_id=out["id"]
        ).status_code
        == 409
    )


def test_DE_06_rechazo_sin_motivo_y_contexto_no_resoluble(datos):
    out, _ = pedir(
        datos,
        [
            {"codigo": datos.epp.codigo, "cantidad": 1},
            {"codigo": datos.herramienta.codigo, "cantidad": 1},
        ],
    )
    url = f"/api/autorizaciones/{out['id']}/resolucion"
    assert datos.sup.post(url, json={"decision": "RECHAZAR"}).status_code == 422
    r = datos.sup.post(
        url,
        json={
            "renglones": [
                {"renglon": 1, "decision": "APROBAR"},
                {"renglon": 2, "decision": "APROBAR"},
            ]
        },
    )
    assert r.status_code == 422
    assert (
        datos.sup.post(url, json={"decision": "RECHAZAR", "motivo": "No corresponde"}).json()[
            "estado"
        ]
        == "RECHAZADA"
    )


def test_DE_07_supervisor_se_aprueba_despacho_y_valido(datos):
    d = datos
    rows = [{"codigo": d.epp.codigo, "cantidad": 1}]
    ev = d.sup.post(
        "/api/vales/evaluar",
        json={"tipo": "ENTREGA", "trabajador_id": str(d.t.id), "renglones": rows},
    ).json()
    assert ev["despacho"]["modo"] == "SUPERVISOR" and not ev["requiere_aprobacion_despacho"]
    r = d.sup.post("/api/vales", json=cuerpo_entrega(d.t, rows, observacion="Sin proyecto"))
    assert r.status_code == 201, r.text
    assert "DE-07" in r.json()["renglones"][0]["reglas"]
    detalle = d.sup.get(f"/api/vales/{r.json()['id']}").json()
    assert detalle["valido"]["medio"] == "DESPACHO_PROPIO"


def test_DE_09_DE_11_vigencia_nueva_y_primera_resolucion_gana(datos, session):
    out, _ = pedir(datos)
    a = session.get(Autorizacion, uuid.UUID(out["id"]))
    a.creado_en = ahora_utc() - timedelta(minutes=14)
    a.vence_en = ahora_utc() + timedelta(minutes=1)
    session.commit()
    url = f"/api/autorizaciones/{out['id']}/resolucion"
    r = datos.sup.post(url, json={"decision": "APROBAR"})
    assert r.status_code == 200, r.text
    assert a.vence_en - a.resuelta_en == timedelta(minutes=15)
    r = datos.sup.post(url, json={"decision": "APROBAR"})
    assert r.status_code == 409 and r.json()["detalles"]["resuelta_por"]["nombre"]


def test_DE_12_lote_procesa_cada_solicitud(datos):
    a, _ = pedir(datos)
    b, _ = pedir(datos)
    r = datos.sup.post(
        "/api/autorizaciones/resolucion-multiple",
        json={
            "resoluciones": [
                {"id": a["id"], "decision": "APROBAR"},
                {"id": b["id"], "decision": "RECHAZAR", "motivo": "No corresponde"},
                {"id": str(uuid.uuid4()), "decision": "APROBAR"},
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert [x["estado"] for x in r.json()["resultados"][:2]] == ["APROBADA", "RECHAZADA"]
    assert r.json()["resultados"][2]["error"]["codigo"] == "NO_ENCONTRADO"


def test_DE_14_autonomia_almacen_y_usuario_registran_regla(datos, session):
    d = datos
    a = almacen(session)
    a.despacho_epp_con_aprobacion = False
    session.commit()
    rows = [{"codigo": d.epp.codigo, "cantidad": 1}]
    assert evaluar(d, rows)["despacho"]["modo"] == "AUTONOMO_ALMACEN"
    r = confirmar(d, rows)
    assert r.status_code == 201 and "DE-14" in r.json()["renglones"][0]["reglas"]
    a.despacho_epp_con_aprobacion = True
    actor = UsuarioRepository(session).get_by_usuario("almacenista")
    actor.despacho_autonomo = True
    session.commit()
    assert evaluar(d, rows)["despacho"]["modo"] == "AUTONOMO_USUARIO"


def test_DE_14_endpoints_exigen_permiso_motivo_y_guardan_auditoria(datos, cliente_como, session):
    d = datos
    url = f"/api/almacenes/{almacen(session).id}/autonomia"
    body = {"despacho_epp_con_aprobacion": False, "motivo": "Autonomía aprobada"}
    assert d.a.patch(url, json=body).status_code == 403
    admin = cliente_como("Administrador")
    assert admin.patch(url, json=body | {"motivo": " "}).status_code == 422
    assert admin.patch(url, json=body).json()["despacho_epp_con_aprobacion"] is False
    u = UsuarioRepository(session).get_by_usuario("almacenista")
    userurl = f"/api/usuarios/{u.id}/autonomia"
    assert (
        admin.patch(
            userurl, json={"despacho_autonomo": True, "motivo": "Equipo habilitado"}
        ).json()["despacho_autonomo"]
        is True
    )
    from app.modulos.auditoria.models import Auditoria

    assert session.scalar(
        select(Auditoria.id).where(
            Auditoria.entidad_id == str(u.id), Auditoria.accion.like("%autonomia%")
        )
    )


def test_DE_13_aumentar_cantidad_no_cubierta_no_mueve_inventario(datos, session):
    out, _ = pedir(datos)
    assert (
        datos.sup.post(
            f"/api/autorizaciones/{out['id']}/resolucion", json={"decision": "APROBAR"}
        ).status_code
        == 200
    )
    rows = [{"codigo": datos.epp.codigo, "cantidad": 3}]
    ev = evaluar(datos, rows, autorizacion_id=out["id"])
    assert ev["renglones"][0]["aprobacion"] == "CANTIDAD_MAYOR" and not ev["puede_confirmar"]
    r = confirmar(datos, rows, autorizacion_id=out["id"])
    assert (
        r.status_code == 409 and r.json()["detalles"]["renglones"][0]["causa"] == "CANTIDAD_MAYOR"
    )
    assert existencia(session, "KEP", datos.epp) == 10


def test_NT_03_cifrado_real_vapid_timeout_y_sin_redirecciones(monkeypatch):
    from app.modulos.notificaciones.generar_claves import generar
    from app.modulos.notificaciones.service import TransportePush

    publica, privada = generar()
    monkeypatch.setattr(get_settings(), "vapid_clave_publica", publica)
    monkeypatch.setattr(get_settings(), "vapid_clave_privada", privada)
    llamadas = []

    def post(self, url, *args, **kw):
        llamadas.append((url, kw))
        return SimpleNamespace(status_code=201, text="", headers={})

    monkeypatch.setattr("requests.Session.post", post)
    dto = suscripcion()
    s = SimpleNamespace(endpoint=dto.endpoint, p256dh=dto.keys.p256dh, auth=dto.keys.auth)
    TransportePush().enviar(s, {"titulo": "Texto privado del aviso"}, 120)
    assert len(llamadas) == 1
    url, kw = llamadas[0]
    assert url == dto.endpoint and kw["allow_redirects"] is False and kw["timeout"] == 5
    assert b"Texto privado" not in kw["data"]
    headers = {k.lower(): v for k, v in kw["headers"].items()}
    assert headers["content-encoding"] == "aes128gcm"
    assert "vapid" in headers["authorization"].lower()


def test_NT_08_NT_09_endpoints_sesion_y_permisos(datos, monkeypatch):
    monkeypatch.setattr(get_settings(), "vapid_clave_publica", "")
    monkeypatch.setattr(get_settings(), "vapid_clave_privada", "")
    assert datos.sup.get("/api/notificaciones/clave-publica").status_code == 404
    dto = suscripcion().model_dump()
    assert datos.a.post("/api/notificaciones/suscripciones", json=dto).status_code == 403
    monkeypatch.setattr(get_settings(), "vapid_clave_publica", "publica")
    monkeypatch.setattr(get_settings(), "vapid_clave_privada", "privada")
    monkeypatch.setattr(
        "app.modulos.notificaciones.service.TransportePush.enviar",
        lambda *a: SimpleNamespace(status_code=201),
    )
    r = datos.sup.post("/api/notificaciones/suscripciones", json=dto)
    assert r.status_code == 201, r.text
    id = r.json()["id"]
    assert datos.sup.post("/api/notificaciones/suscripciones", json=dto).status_code == 200
    assert datos.a.delete(f"/api/notificaciones/suscripciones/{id}").status_code == 404
    assert datos.sup.post("/api/notificaciones/prueba").json()["enviadas"] == 1
    assert datos.sup.post("/api/notificaciones/prueba").status_code == 429
    assert datos.sup.delete(f"/api/notificaciones/suscripciones/{id}").status_code == 204


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/x",
        "https://127.0.0.1/x",
        "https://fcm.googleapis.com.evil.example/x",
        "https://u:p@fcm.googleapis.com/x",
    ],
)
def test_NT_03_endpoint_ajeno_no_recibe_claves(endpoint):
    from pydantic import ValidationError

    dto = suscripcion().model_dump()
    with pytest.raises(ValidationError):
        SuscripcionIn(**(dto | {"endpoint": endpoint}))


def test_NT_01_familia_cerrada_revoca_y_NT_05_agrupa_desde_base(datos, session, monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "vapid_clave_publica", "publica")
    monkeypatch.setattr(cfg, "vapid_clave_privada", "privada")
    usuario = UsuarioRepository(session).get_by_usuario("supervisor")
    familia = session.scalar(
        select(SesionDispositivo.familia_id).where(
            SesionDispositivo.usuario_id == usuario.id, SesionDispositivo.revocada_en.is_(None)
        )
    )
    enviadas = []

    class Transporte:
        def enviar(self, s, payload, ttl):
            enviadas.append(payload)
            return SimpleNamespace(status_code=201)

    service = NotificacionService(session, Transporte())
    s, _ = service.registrar(usuario, familia, suscripcion())
    a, _ = pedir(datos)
    b, _ = pedir(datos)
    service.avisar(uuid.UUID(a["id"]))
    # Nueva instancia: el cooldown y el conteo salen de MySQL, no de memoria.
    service = NotificacionService(session, Transporte())
    service.avisar(uuid.UUID(b["id"]))
    assert len(enviadas) == 2 and enviadas[0]["pendientes"] == 2
    assert enviadas[0]["url"] == "/autorizaciones"
    assert enviadas[0]["etiqueta"] == enviadas[1]["etiqueta"]
    assert not enviadas[0]["silencioso"] and enviadas[1]["silencioso"]
    # NT-02: suspensión por permiso conserva la suscripción y vuelve a enviar al recuperarlo.
    with monkeypatch.context() as parche:
        parche.setattr(service.acceso, "tiene_permiso", lambda *a: False)
        assert not service._enviar(s.id, {"titulo": "Suspendido"})
        assert session.get(type(s), s.id).revocada_en is None
    assert service._enviar(s.id, {"titulo": "Recuperado"})
    assert len(enviadas) == 3
    sesion = session.scalar(
        select(SesionDispositivo).where(
            SesionDispositivo.familia_id == familia, SesionDispositivo.revocada_en.is_(None)
        )
    )
    sesion.revocada_en = ahora_utc()
    session.commit()
    assert not service._enviar(s.id, {"titulo": "No debe llegar"})
    assert s.revocada_en is not None and len(enviadas) == 3


def test_DE_11_resolucion_concurrente_dos_conexiones_una_gana(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.core.excepciones import AppError
    from app.modulos.auditoria.models import Auditoria
    from app.modulos.autorizaciones.schemas import ResolucionIn
    from app.modulos.autorizaciones.service import AutorizacionService
    from app.modulos.trabajadores.models import Trabajador

    with Session(engine, expire_on_commit=False) as s:
        users = UsuarioRepository(s)
        actor = users.get_by_usuario("almacenista")
        t = s.scalar(select(Trabajador).limit(1))
        a = Autorizacion(
            almacen_id=actor.almacen_id,
            trabajador_id=t.id,
            tipo="DESPACHO",
            solicitada_por=actor.id,
            motivo="Despacho de EPP",
            vence_en=ahora_utc() + timedelta(minutes=15),
            detalle={
                "renglones": [
                    {
                        "codigo": "PRUEBA-COMPETENCIA",
                        "cantidad": 1,
                        "clase": "EPP",
                        "regla": "DE-01",
                        "renglon": 1,
                    }
                ]
            },
        )
        s.add(a)
        s.commit()
        id = a.id
    barrera = Barrier(2)

    def resolver(nombre):
        with Session(engine, expire_on_commit=False) as s:
            actor = UsuarioRepository(s).get_by_usuario(nombre)
            barrera.wait(timeout=10)
            try:
                out = AutorizacionService(s).resolver(id, actor, ResolucionIn(decision="APROBAR"))
                return out.estado
            except AppError as exc:
                return exc.codigo

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(resolver, ["supervisor", "admin"]))
        assert sorted(resultados) == ["APROBADA", "AUTORIZACION_RESUELTA"]
    finally:
        with Session(engine) as s:
            s.execute(delete(Auditoria).where(Auditoria.entidad_id == str(id)))
            s.execute(delete(Autorizacion).where(Autorizacion.id == id))
            s.commit()


def test_DE_04_doble_creacion_concurrente_id_cliente_una_solicitud(engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete, func
    from sqlalchemy.orm import Session

    from app.modulos.auditoria.models import Auditoria
    from app.modulos.autorizaciones.repository import AutorizacionRepository
    from app.modulos.autorizaciones.schemas import RenglonSolicitud, SolicitudCreate
    from app.modulos.autorizaciones.service import AutorizacionService
    from app.modulos.trabajadores.models import Trabajador

    # Se aísla la clasificación; la carrera prueba el índice único y el rollback reales.
    monkeypatch.setattr(
        "app.modulos.autorizaciones.verificador_despacho.evaluar_solicitud",
        lambda *args: (
            [
                RenglonSolicitud(
                    renglon=1, codigo="TEST-DUPLICADO", cantidad=1, clase="EPP", regla="DE-01"
                )
            ],
            None,
        ),
    )
    barrera = Barrier(2)
    agregar = AutorizacionRepository.add

    def add(self, a):
        barrera.wait(timeout=10)
        return agregar(self, a)

    monkeypatch.setattr(AutorizacionRepository, "add", add)
    id_cliente = uuid.uuid4()
    with Session(engine) as s:
        trabajador_id = s.scalar(select(Trabajador.id).limit(1))
    dto = SolicitudCreate(
        tipo="DESPACHO",
        id_cliente=id_cliente,
        trabajador_id=trabajador_id,
        renglones=[{"codigo": "TEST-DUPLICADO", "cantidad": 1}],
    )

    def crear(_):
        with Session(engine, expire_on_commit=False) as s:
            actor = UsuarioRepository(s).get_by_usuario("almacenista")
            service = AutorizacionService(s)
            a = service.solicitar(actor, dto, verificador_renglones=lambda *args: [])
            return a.id, service.repetida

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(crear, range(2)))
        assert resultados[0][0] == resultados[1][0]
        assert sorted(repetida for _, repetida in resultados) == [False, True]
        with Session(engine) as s:
            assert (
                s.scalar(
                    select(func.count())
                    .select_from(Autorizacion)
                    .where(Autorizacion.id_cliente == id_cliente)
                )
                == 1
            )
    finally:
        with Session(engine) as s:
            id = s.scalar(select(Autorizacion.id).where(Autorizacion.id_cliente == id_cliente))
            s.execute(delete(Auditoria).where(Auditoria.entidad_id == str(id)))
            s.execute(delete(Autorizacion).where(Autorizacion.id_cliente == id_cliente))
            s.commit()


def suscripcion():
    key = (
        generate_private_key(SECP256R1())
        .public_key()
        .public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    )

    def b64(x):
        return base64.urlsafe_b64encode(x).decode().rstrip("=")

    return SuscripcionIn(
        endpoint="https://fcm.googleapis.com/fcm/send/prueba",
        keys={"p256dh": b64(key), "auth": b64(bytes(16))},
    )


def test_NT_01_NT_02_NT_07_NT_09_sesion_reuso_prueba_cooldown_410(datos, session, monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "vapid_clave_publica", "publica")
    monkeypatch.setattr(cfg, "vapid_clave_privada", "privada")
    usuario = UsuarioRepository(session).get_by_usuario("supervisor")
    familia = session.scalar(
        select(SesionDispositivo.familia_id).where(
            SesionDispositivo.usuario_id == usuario.id, SesionDispositivo.revocada_en.is_(None)
        )
    )
    envios = []

    class Transporte:
        status = 201

        def enviar(self, s, payload, ttl):
            envios.append(payload)
            return SimpleNamespace(status_code=self.status)

    transporte = Transporte()
    service = NotificacionService(session, transporte)
    dto = suscripcion()
    s, repeated = service.registrar(usuario, familia, dto)
    assert not repeated
    assert service.registrar(usuario, familia, dto)[1]
    assert service.contar_destinatarios(almacen(session).id, uuid.uuid4()) == 1
    assert service.prueba(usuario, familia).enviadas == 1
    with pytest.raises(DemasiadosIntentos):
        service.prueba(usuario, familia)
    transporte.status = 410
    assert not service._enviar(s.id, {"titulo": "Aviso"})
    assert s.revocada_en is not None and "410" in s.ultimo_error
    with pytest.raises(NoEncontrado):
        service.revocar(s.id, usuario, uuid.uuid4())
