"""Trazabilidad de acceso y permisos: AC-02, AC-05, AC-07 y ES-25.

AC-07 son las cuatro cosas que ningún rol puede hacer porque no son permisos. Se comprueban con
el rol Administrador (todos los permisos) y con Compras (que ve costos): ni ellos pueden.
"""

import json
import uuid
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from app.core.tiempo import hoy_mx
from app.modulos.acceso.datos_prueba import PERMISOS_INICIALES
from app.modulos.acceso.permisos import CATALOGO, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import Movimiento, Vale
from tests.conftest import UsuarioPrueba, iniciar_sesion_en
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    total_movimientos,
    total_vales,
)
from tests.movimientos.test_autorizacion_integracion import AUT, solicitar
from tests.movimientos.test_entrega import evaluar, pieza_en_kep, renglon

VALES = "/api/vales"
CURP = "GAMC850505MDFRRR07"
NSS = "12345678901"


@pytest.fixture
def cliente_con(app, crear_usuario) -> Callable[..., TestClient]:
    """`cliente_con(P.X, almacen="KEP")`: sesión de un usuario con exactamente esos permisos."""
    clientes: list[TestClient] = []

    def _cliente(*permisos: str, almacen: str | None = None) -> TestClient:
        usuario: UsuarioPrueba = crear_usuario(set(permisos), almacen=almacen)
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def claves(valor) -> set[str]:
    """Todas las claves de un JSON, a cualquier profundidad."""
    if isinstance(valor, dict):
        encontradas = set(valor)
        for hijo in valor.values():
            encontradas |= claves(hijo)
        return encontradas
    if isinstance(valor, list):
        return set().union(*(claves(h) for h in valor)) if valor else set()
    return set()


def sin_costos(respuesta, *valores: str) -> None:
    assert respuesta.status_code == 200, respuesta.text
    assert not [c for c in claves(respuesta.json()) if "costo" in c.lower()], respuesta.text
    for valor in valores:
        assert valor not in respuesta.text


# ------------------------------------------------------------------------------------ AC-02


def test_AC_02_cada_usuario_tiene_un_solo_rol_y_el_esquema_no_permite_dos(engine):
    inspector = inspect(engine)
    columnas = {c["name"]: c for c in inspector.get_columns("usuario")}
    assert columnas["rol_id"]["nullable"] is False  # siempre tiene rol...
    destinos = {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspector.get_foreign_keys("usuario")
    }
    assert ("rol_id", "rol") in destinos  # ... y es uno solo: una columna, no una lista
    # No hay ninguna otra tabla que ligue usuarios con roles (una tabla puente permitiría dos).
    for tabla in inspector.get_table_names():
        if tabla == "usuario":
            continue
        referidas = {fk["referred_table"] for fk in inspector.get_foreign_keys(tabla)}
        assert not {"usuario", "rol"} <= referidas, f"{tabla} liga usuarios con roles"


def test_AC_02_la_api_no_acepta_dos_roles_y_cambiar_el_rol_lo_reemplaza(
    app, cliente_como, crear_usuario, session
):
    admin = cliente_como("Administrador")
    roles = {r["nombre"]: r["id"] for r in admin.get("/api/roles").json()}
    almacenista_id, compras_id = roles["Almacenista"], roles["Compras"]
    nuevo = {
        "nombre": "Persona de prueba",
        "usuario": "persona.prueba",
        "contrasena": "Clave-prueba-123",
        "almacen_id": str(almacen(session, "KEP").id),
    }
    # Dos roles de golpe, de cualquiera de las formas posibles, se rechaza y no crea nada.
    for extra in (
        {"rol_id": almacenista_id, "rol_ids": [almacenista_id, compras_id]},
        {"rol_id": [almacenista_id, compras_id]},
        {"rol_id": almacenista_id, "roles": [compras_id]},
    ):
        r = admin.post("/api/usuarios", json=nuevo | extra)
        assert r.status_code == 422, (extra, r.text)
    assert UsuarioRepository(session).get_by_usuario("persona.prueba") is None

    creado = admin.post("/api/usuarios", json=nuevo | {"rol_id": almacenista_id})
    assert creado.status_code == 201, creado.text
    assert creado.json()["rol"]["id"] == almacenista_id  # un rol, no una lista
    usuario_id = creado.json()["id"]
    assert (
        admin.patch(f"/api/usuarios/{usuario_id}", json={"rol_ids": [compras_id]}).status_code
        == 422
    )
    assert (
        admin.patch(
            f"/api/usuarios/{usuario_id}", json={"rol_id": [almacenista_id, compras_id]}
        ).status_code
        == 422
    )

    # Cambiar el rol reemplaza al anterior: los permisos son solo los del rol nuevo.
    cambio = admin.patch(f"/api/usuarios/{usuario_id}", json={"rol_id": compras_id})
    assert cambio.status_code == 200 and cambio.json()["rol"]["id"] == compras_id
    persona = TestClient(app)
    assert (
        iniciar_sesion_en(persona, UsuarioPrueba("persona.prueba", "Clave-prueba-123")).status_code
        == 200
    )
    sesion = persona.get("/api/sesion").json()
    assert sesion["rol"]["nombre"] == "Compras"
    assert set(sesion["permisos"]) == PERMISOS_INICIALES["Compras"]
    assert not set(sesion["permisos"]) & {P.ENTREGAS_CREAR, P.AUTORIZACIONES_RESOLVER}
    persona.close()


# ------------------------------------------------------------------------------------ AC-05


def test_AC_05_los_permisos_de_informacion_estan_marcados_en_el_catalogo():
    de_informacion = {p.clave for p in CATALOGO if p.es_de_informacion}
    assert {P.CATALOGO_COSTOS, P.TRABAJADORES_VER_DATOS_PERSONALES} <= de_informacion
    # Y son aparte de los de acción: ningún rol de operación los trae de inicio.
    for rol in ("Almacenista", "Supervisor"):
        assert not PERMISOS_INICIALES[rol] & {
            P.CATALOGO_COSTOS,
            P.TRABAJADORES_VER_DATOS_PERSONALES,
        }


def test_AC_05_sin_catalogo_costos_el_costo_no_se_envia_y_con_el_permiso_si(cliente_con, session):
    articulo = crear_articulo(session, costo_unitario=Decimal("123.45"))
    sin_permiso = cliente_con(P.CATALOGO_VER, P.CATALOGO_ADMINISTRAR)
    con_permiso = cliente_con(P.CATALOGO_VER, P.CATALOGO_ADMINISTRAR, P.CATALOGO_COSTOS)

    for cliente, debe_verlo in ((sin_permiso, False), (con_permiso, True)):
        lista = cliente.get("/api/articulos", params={"q": articulo.codigo})
        ficha = cliente.get(f"/api/articulos/{articulo.id}")
        edicion = cliente.patch(f"/api/articulos/{articulo.id}", json={"marca": "Nueva marca"})
        for respuesta in (lista, ficha, edicion):
            assert respuesta.status_code == 200, respuesta.text
        cuerpos = (lista.json()["elementos"][0], ficha.json(), edicion.json())
        for cuerpo in cuerpos:
            if debe_verlo:
                assert Decimal(str(cuerpo["costo_unitario"])) == Decimal("123.45")
            else:
                assert "costo_unitario" not in cuerpo  # no es null: la clave ni existe
        assert ("123.45" in lista.text) is debe_verlo
        assert ("123.45" in ficha.text) is debe_verlo
    # El almacenista y el supervisor, con sus permisos de siempre, tampoco lo reciben.
    assert "123.45" not in json.dumps(
        cliente_con(P.CATALOGO_VER).get(f"/api/articulos/{articulo.id}").json()
    )


def test_AC_05_sin_ver_datos_personales_curp_y_nss_no_se_envian_y_con_el_permiso_si(
    cliente_con, session, trabajador
):
    trabajador.curp, trabajador.nss = CURP, NSS
    session.flush()
    sin_permiso = cliente_con(P.TRABAJADORES_VER)
    con_permiso = cliente_con(P.TRABAJADORES_VER, P.TRABAJADORES_VER_DATOS_PERSONALES)

    ficha_sin = sin_permiso.get(f"/api/trabajadores/{trabajador.id}")
    lista_sin = sin_permiso.get("/api/trabajadores", params={"q": trabajador.numero_empleado})
    assert ficha_sin.status_code == 200 and lista_sin.status_code == 200
    for respuesta in (ficha_sin, lista_sin):
        assert not claves(respuesta.json()) & {"curp", "nss"}
        assert CURP not in respuesta.text and NSS not in respuesta.text

    ficha_con = con_permiso.get(f"/api/trabajadores/{trabajador.id}")
    assert ficha_con.status_code == 200
    assert ficha_con.json()["curp"] == CURP and ficha_con.json()["nss"] == NSS


# ------------------------------------------------------------------------------------ AC-07


@pytest.mark.parametrize("rol", ["Compras", "Administrador"])
def test_AC_07_ni_con_el_permiso_de_costos_se_muestra_un_costo_en_un_vale(
    almacenista, compras, cliente_como, session, trabajador, rol
):
    quien = cliente_como(rol)
    guantes = crear_articulo(session, retornable=False, costo_unitario=Decimal("987.65"))
    # Quien ve costos en el catálogo...
    assert Decimal(str(quien.get(f"/api/articulos/{guantes.id}").json()["costo_unitario"])) == (
        Decimal("987.65")
    )
    entrada = abastecer(compras, guantes, 10)
    entrega = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert entrega.status_code == 201

    # ... no lo ve en los vales, ni en el detalle, ni por su QR, ni en la lista ni la bitácora.
    for vale in (entrada, entrega.json()):
        sin_costos(quien.get(f"{VALES}/{vale['id']}"), "987.65")
        sin_costos(quien.get(f"{VALES}/por-token/{vale['token']}"), "987.65")
    sin_costos(quien.get(VALES), "987.65")
    sin_costos(
        quien.get("/api/reportes/movimientos", params={"articulo_id": str(guantes.id)}), "987.65"
    )
    # Tampoco al evaluar una entrega (quien tiene entregas.crear y opera el almacén).
    if rol == "Administrador":
        ev = quien.post(
            f"{VALES}/evaluar",
            json={
                "tipo": "ENTREGA",
                "trabajador_id": str(trabajador.id),
                "almacen_id": str(almacen(session, "KEP").id),
                "renglones": [renglon(guantes.codigo)],
            },
        )
        sin_costos(ev, "987.65")


def test_AC_07_ni_el_administrador_autoriza_un_rojo_de_seguridad(
    almacenista, cliente_como, compras, session, trabajador
):
    admin = cliente_como("Administrador")
    kep = str(almacen(session, "KEP").id)
    _, no_apta = pieza_en_kep(compras, session, estado=EstadoPieza.NO_APTO)
    _, vencida = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigente_hasta=hoy_mx() - timedelta(days=1)
    )

    for pieza, regla in ((no_apta, "E-05"), (vencida, "E-06")):
        # 1. No se envía a autorización: ni el almacenista, ni el Administrador.
        cuerpo = {
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": pieza.codigo, "cantidad": 1, "regla": "L-02"}],
            "motivo": "Urge",
        }
        for quien, extra in ((almacenista, {}), (admin, {"almacen_id": kep})):
            r = quien.post(AUT, json=cuerpo | extra)
            assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE", r.text
            assert r.json()["detalles"]["regla"] == regla
        # 2. El Administrador lo evalúa y sigue en rojo, sin opción de autorización.
        ev = admin.post(
            f"{VALES}/evaluar",
            json={
                "tipo": "ENTREGA",
                "trabajador_id": str(trabajador.id),
                "almacen_id": kep,
                "renglones": [renglon(pieza.codigo)],
            },
        )
        assert ev.status_code == 200
        r0 = ev.json()["renglones"][0]
        assert r0["nivel"] == "ROJO" and r0["autorizable"] is False
        assert ev.json()["puede_confirmar"] is False
    assert (
        session.scalar(
            select(func.count())
            .select_from(Autorizacion)
            .where(Autorizacion.trabajador_id == trabajador.id)
        )
        == 0
    )

    # 3. Aunque el Administrador apruebe una autorización legítima, no cubre el rojo: se rechaza.
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 5)
    assert (
        almacenista.post(
            VALES, json=cuerpo_entrega(trabajador, [renglon(arnes.codigo)])
        ).status_code
        == 201
    )
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    assert (
        admin.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"}).status_code
        == 200
    )
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador,
            [renglon(arnes.codigo), renglon(no_apta.codigo)],
            autorizacion_id=autorizacion_id,
        ),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "APROBADA"


def test_AC_07_no_existe_ruta_para_editar_o_borrar_movimientos_ni_para_ningun_rol(
    app, almacenista, cliente_como, compras, session, trabajador
):
    # 1. Las rutas: ningún PUT, PATCH o DELETE toca vales ni movimientos.
    modificables = {"PUT", "PATCH", "DELETE"}
    # El esquema de la API lista todas las rutas publicadas con sus métodos.
    rutas = {
        ruta: {m.upper() for m in metodos if m.upper() in {"GET", "POST", *modificables}}
        for ruta, metodos in app.openapi()["paths"].items()
    }
    de_inventario = {
        ruta: metodos
        for ruta, metodos in rutas.items()
        if any(t in ruta for t in ("/vales", "movimiento", "no-adeudo"))
    }
    assert "/api/vales" in de_inventario  # la búsqueda encuentra las rutas
    assert not {r: m for r, m in de_inventario.items() if m & modificables}
    # Lo único que escribe sobre los vales es crear uno nuevo, evaluar o cancelar con inversos.
    escritura = {ruta for ruta, metodos in de_inventario.items() if "POST" in metodos}
    assert escritura == {
        "/api/vales",
        "/api/vales/evaluar",
        "/api/vales/{vale_id}/cancelacion",
        "/api/trabajadores/{trabajador_id}/no-adeudo",
    }, escritura
    assert not [r for r in rutas if "movimiento" in r and rutas[r] - {"GET"}]

    # 2. Un intento directo, con el rol que tiene todos los permisos, no cambia nada.
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    ).json()
    antes = (
        total_vales(session),
        total_movimientos(session),
        almacenista.get(f"{VALES}/{vale['id']}").json(),
    )
    admin = cliente_como("Administrador")
    movimiento = session.scalar(
        select(Movimiento).where(Movimiento.vale_id == uuid.UUID(vale["id"]))
    )
    for cliente in (admin, almacenista, compras):
        for ruta in (
            f"{VALES}/{vale['id']}",
            f"{VALES}/{vale['id']}/movimientos/{movimiento.id}",
            f"/api/movimientos/{movimiento.id}",
            f"/api/vales/{vale['id']}/renglones/1",
        ):
            for metodo in ("put", "patch", "delete"):
                r = cliente.request(
                    metodo.upper(), ruta, json={"cantidad": 99, "estado": "CANCELADO"}
                )
                assert r.status_code in (404, 405), (metodo, ruta, r.status_code)
    assert (
        total_vales(session),
        total_movimientos(session),
        admin.get(f"{VALES}/{vale['id']}").json(),
    ) == antes
    session.refresh(movimiento)
    assert movimiento.cantidad == 1
    assert session.get(Vale, uuid.UUID(vale["id"])).estado == "EMITIDO"


# ------------------------------------------------------------------------------------ ES-25


def test_ES_25_activar_ver_datos_personales_en_un_rol_almacenista_aplica_en_la_siguiente_peticion(
    app, crear_usuario, session, trabajador
):
    trabajador.curp, trabajador.nss = CURP, NSS
    session.flush()
    permisos = set(PERMISOS_INICIALES["Almacenista"]) | {P.TRABAJADORES_VER_DATOS_PERSONALES}
    usuario = crear_usuario(permisos, almacen="KEP", nombre_rol="Almacenista con datos personales")
    almacenista = TestClient(app)
    assert iniciar_sesion_en(almacenista, usuario).status_code == 200  # una sola vez
    ruta = f"/api/trabajadores/{trabajador.id}"

    # Con el permiso, la ficha incluye CURP y NSS.
    ficha = almacenista.get(ruta)
    assert ficha.status_code == 200
    assert ficha.json()["curp"] == CURP and ficha.json()["nss"] == NSS
    assert P.TRABAJADORES_VER_DATOS_PERSONALES in almacenista.get("/api/sesion").json()["permisos"]

    # El administrador le quita el permiso al rol: sin cerrar sesión, la siguiente petición ya no
    # trae CURP ni NSS.
    rol_id = UsuarioRepository(session).get_by_usuario(usuario.usuario).rol_id
    RolRepository(session).reemplazar_permisos(
        rol_id, permisos - {P.TRABAJADORES_VER_DATOS_PERSONALES}
    )
    session.commit()
    despues = almacenista.get(ruta)
    assert despues.status_code == 200
    assert not claves(despues.json()) & {"curp", "nss"}
    assert CURP not in despues.text and NSS not in despues.text
    assert (
        P.TRABAJADORES_VER_DATOS_PERSONALES not in almacenista.get("/api/sesion").json()["permisos"]
    )
    # Lo demás de la ficha sigue igual: solo cambió el dato reservado.
    assert despues.json()["nombre"] == trabajador.nombre

    # Y al volver a activarlo, regresan en la petición siguiente.
    RolRepository(session).reemplazar_permisos(rol_id, permisos)
    session.commit()
    assert almacenista.get(ruta).json()["curp"] == CURP
    almacenista.close()
