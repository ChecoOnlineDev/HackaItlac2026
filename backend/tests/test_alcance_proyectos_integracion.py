"""FEAT-013: conjunto de lectura, almacén activo y atribución de las entregas."""

import uuid

from fastapi.testclient import TestClient

from app.modulos.acceso.models import UsuarioAlmacen
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.service import AlmacenService
from app.modulos.movimientos.models import Existencia
from tests.conftest import iniciar_sesion_en
from tests.movimientos.ayudas import crear_articulo, crear_trabajador, firma_valida
from tests.test_proyectos import asignar, crear


def test_AC_39_cambio_activo_exige_asignacion_y_conserva_conjunto(
    app, session, crear_usuario, cliente_como
):
    usuario = crear_usuario({P.INVENTARIO_VER, P.TABLERO_VER}, almacen="KEP")
    usuario_id = UsuarioRepository(session).get_by_usuario(usuario.usuario).id
    a = AlmacenService(session).obtener_por_clave("CON")
    admin = cliente_como("Administrador")
    r = admin.put(
        f"/api/usuarios/{usuario_id}/almacenes",
        json={
            "almacenes_id": [str(AlmacenService(session).obtener_por_clave("KEP").id), str(a.id)]
        },
    )
    assert r.status_code == 200, r.text
    with TestClient(app) as cliente:
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        antes = cliente.get("/api/sesion").json()
        assert len(antes["almacenes"]) == 2
        r = cliente.put("/api/sesion/almacen", json={"almacen_id": str(a.id)})
        assert r.status_code == 200, r.text
        assert r.json()["almacen_activo"]["id"] == str(a.id)
        assert len(r.json()["almacenes"]) == 2
        ajeno = AlmacenService(session).obtener_por_clave("MID")
        r = cliente.put("/api/sesion/almacen", json={"almacen_id": str(ajeno.id)})
        assert r.status_code == 403 and r.json()["codigo"] == "ALMACEN_NO_ASIGNADO"
        assert cliente.get("/api/sesion").json()["almacen_activo"]["id"] == str(a.id)


def test_AC_37_consulta_existencias_suma_solo_conjunto_asignado(app, session, crear_usuario):
    usuario = crear_usuario({P.INVENTARIO_VER, P.REPORTES_EXISTENCIAS}, almacen="KEP")
    servicio = AlmacenService(session)
    con = servicio.obtener_por_clave("CON")
    session.add(
        UsuarioAlmacen(
            usuario_id=UsuarioRepository(session).get_by_usuario(usuario.usuario).id,
            almacen_id=con.id,
        )
    )
    articulo = crear_articulo(session)
    for clave, cantidad in (("KEP", 2), ("CON", 3), ("MID", 7)):
        a = servicio.obtener_por_clave(clave)
        session.add(
            Existencia(
                ubicacion_id=servicio.ubicacion_de_almacen(a.id).id,
                articulo_id=articulo.id,
                cantidad=cantidad,
            )
        )
    session.commit()
    with TestClient(app) as cliente:
        iniciar_sesion_en(cliente, usuario)
        r = cliente.get("/api/reportes/existencias")
        assert r.status_code == 200, r.text
        filas = [x for x in r.json()["elementos"] if x["codigo"] == articulo.codigo]
        assert sum(x["cantidad"] for x in filas) == 5
        assert len(filas) == 2


def test_PR_08_entrega_proyecto_unico_automatico_y_vale_lo_conserva(session, cliente_como):
    admin = cliente_como("Administrador")
    p = crear(admin, session)
    t = crear_trabajador(session)
    assert asignar(admin, t, p).status_code == 201
    articulo = crear_articulo(session, requiere_inspeccion=False)
    servicio = AlmacenService(session)
    almacen = servicio.obtener_por_clave("KEP")
    session.add(
        Existencia(
            ubicacion_id=servicio.ubicacion_de_almacen(almacen.id).id,
            articulo_id=articulo.id,
            cantidad=10,
        )
    )
    session.flush()
    cuerpo = {
        "tipo": "ENTREGA",
        "id_cliente": str(uuid.uuid4()),
        "almacen_id": str(almacen.id),
        "trabajador_id": str(t.id),
        "renglones": [{"codigo": articulo.codigo}],
        "firma": firma_valida(),
    }
    r = admin.post("/api/vales/evaluar", json=cuerpo)
    assert r.status_code == 200, r.text
    assert r.json()["proyecto"]["id"] == p["id"]
    r = admin.post("/api/vales", json=cuerpo)
    assert r.status_code == 201, r.text
    detalle = admin.get(f"/api/vales/{r.json()['id']}")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["proyecto"]["id"] == p["id"]


def test_PR_10_entrega_sin_proyecto_exige_observacion(session, cliente_como):
    t = crear_trabajador(session)
    servicio = AlmacenService(session)
    articulo = crear_articulo(session, requiere_inspeccion=False)
    a = servicio.obtener_por_clave("KEP")
    session.add(
        Existencia(
            ubicacion_id=servicio.ubicacion_de_almacen(a.id).id,
            articulo_id=articulo.id,
            cantidad=10,
        )
    )
    session.flush()
    admin = cliente_como("Administrador")
    cuerpo = {
        "tipo": "ENTREGA",
        "id_cliente": str(uuid.uuid4()),
        "almacen_id": str(a.id),
        "trabajador_id": str(t.id),
        "renglones": [{"codigo": articulo.codigo}],
        "firma": firma_valida(),
    }
    r = admin.post("/api/vales", json=cuerpo)
    assert r.status_code == 422, r.text
    assert r.json()["detalles"][0]["regla"] == "PR-10"
    r = admin.post(
        "/api/vales", json={**cuerpo, "observacion": "Trabajador pendiente de asignación"}
    )
    assert r.status_code == 201, r.text
