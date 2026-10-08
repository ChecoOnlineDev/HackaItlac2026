"""Puestos y dotación por puesto (FEAT-003): D-01 a D-04 y la dotación del trabajador.

Cada prueba lleva en su nombre el ID de la regla que comprueba. La línea base de las pruebas no
trae dotaciones: cada una arma la suya (`tests/ayudas_dotacion.py`).
"""

import itertools
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo
from app.modulos.trabajadores.models import PeriodoContrato
from tests.ayudas_dotacion import dotacion_de_prueba, puesto_de_prueba
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
)
from tests.movimientos.test_entrega import renglon

UUID_FALSO = "00000000-0000-7000-8000-000000000000"
_n = itertools.count(1)


def nombre_unico(base: str = "Puesto") -> str:
    return f"{base} {next(_n)} {uuid.uuid4().hex[:6]}"


@pytest.fixture
def rh(cliente_como):
    return cliente_como("Recursos Humanos")


def crear_puesto(cliente, nombre=None):
    r = cliente.post("/api/puestos", json={"nombre": nombre or nombre_unico()})
    assert r.status_code == 201, r.text
    return r.json()


def poner_dotacion(cliente, puesto_id, renglones):
    return cliente.put(f"/api/puestos/{puesto_id}/dotacion", json={"renglones": renglones})


# ------------------------------------------------------------------------------ D-01


def test_D_01_se_crea_un_puesto_y_aparece_en_la_lista_con_su_total_de_articulos(
    supervisor, session
):
    puesto = crear_puesto(supervisor)
    assert puesto["activo"] is True and puesto["total_articulos"] == 0
    lentes = crear_articulo(session, retornable=False)
    assert poner_dotacion(
        supervisor, puesto["id"], [{"articulo_id": str(lentes.id), "cantidad": 2}]
    )
    lista = supervisor.get("/api/puestos", params={"tamano": 200}).json()
    fila = next(p for p in lista["elementos"] if p["id"] == puesto["id"])
    assert fila["total_articulos"] == 1 and lista["total"] >= 1


def test_D_01_el_nombre_del_puesto_no_se_repite_sin_importar_mayusculas_ni_acentos(supervisor):
    base = f"Técnico {uuid.uuid4().hex[:6]}"
    crear_puesto(supervisor, base)
    for repetido in (base.upper(), base.replace("é", "e")):
        r = supervisor.post("/api/puestos", json={"nombre": repetido})
        assert r.status_code == 409, r.text
    otro = crear_puesto(supervisor)
    r = supervisor.patch(f"/api/puestos/{otro['id']}", json={"nombre": base.lower()})
    assert r.status_code == 409


def test_D_01_se_edita_y_se_inactiva_un_puesto_y_la_lista_filtra_por_activo(supervisor):
    puesto = crear_puesto(supervisor)
    nuevo = nombre_unico("Renombrado")
    r = supervisor.patch(f"/api/puestos/{puesto['id']}", json={"nombre": nuevo, "activo": False})
    assert r.status_code == 200 and r.json()["nombre"] == nuevo and r.json()["activo"] is False
    activos = supervisor.get("/api/puestos", params={"activo": True, "tamano": 200}).json()
    inactivos = supervisor.get("/api/puestos", params={"activo": False, "tamano": 200}).json()
    assert puesto["id"] not in [p["id"] for p in activos["elementos"]]
    assert puesto["id"] in [p["id"] for p in inactivos["elementos"]]
    assert supervisor.patch(f"/api/puestos/{UUID_FALSO}", json={"activo": True}).status_code == 404


def test_D_01_se_pone_y_se_reemplaza_la_dotacion_de_un_puesto(supervisor, session):
    puesto = crear_puesto(supervisor)
    a = crear_articulo(session, retornable=False, nombre="Aaa guantes")
    b = crear_articulo(session, retornable=True, limite_cantidad=2, nombre="Bbb arnés")
    r = poner_dotacion(
        supervisor,
        puesto["id"],
        [{"articulo_id": str(a.id), "cantidad": 3}, {"articulo_id": str(b.id), "cantidad": 1}],
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["puesto"] == {"id": puesto["id"], "nombre": puesto["nombre"]}
    assert [x["articulo"]["codigo"] for x in cuerpo["renglones"]] == [a.codigo, b.codigo]
    assert cuerpo["renglones"][0]["limite"] is None
    assert cuerpo["renglones"][1]["limite"] == {"cantidad": 2, "periodo_dias": None}
    assert set(cuerpo["renglones"][0]["articulo"]) == {
        "id",
        "codigo",
        "nombre",
        "unidad",
        "control",
    }
    # Reemplazar: lo que no viene se quita.
    r = poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(b.id), "cantidad": 2}])
    assert [(x["articulo"]["id"], x["cantidad"]) for x in r.json()["renglones"]] == [(str(b.id), 2)]
    assert supervisor.get(f"/api/puestos/{puesto['id']}/dotacion").json() == r.json()
    # Vacía: sin dotación.
    assert poner_dotacion(supervisor, puesto["id"], []).json()["renglones"] == []


def test_D_01_la_dotacion_rechaza_articulos_inexistentes_inactivos_o_repetidos(supervisor, session):
    puesto = crear_puesto(supervisor)
    activo = crear_articulo(session, retornable=False)
    inactivo = crear_articulo(session, retornable=False, activo=False)
    for renglones in (
        [{"articulo_id": UUID_FALSO, "cantidad": 1}],
        [{"articulo_id": str(inactivo.id), "cantidad": 1}],
        [
            {"articulo_id": str(activo.id), "cantidad": 1},
            {"articulo_id": str(activo.id), "cantidad": 2},
        ],
        [{"articulo_id": str(activo.id), "cantidad": 0}],
    ):
        r = poner_dotacion(supervisor, puesto["id"], renglones)
        assert r.status_code == 422, r.text
        assert r.json()["codigo"] == "DATOS_INVALIDOS"
    assert supervisor.get(f"/api/puestos/{puesto['id']}/dotacion").json()["renglones"] == []
    assert poner_dotacion(supervisor, UUID_FALSO, []).status_code == 404


def test_D_01_los_cambios_del_puesto_y_de_su_dotacion_quedan_en_el_registro(supervisor, session):
    puesto = crear_puesto(supervisor)
    a = crear_articulo(session, retornable=False)
    supervisor.patch(f"/api/puestos/{puesto['id']}", json={"activo": False})
    poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(a.id), "cantidad": 1}])
    acciones = set(
        session.scalars(select(Auditoria.accion).where(Auditoria.entidad_id == puesto["id"])).all()
    )
    assert acciones == {"puesto.crear", "puesto.editar", "puesto.dotacion"}


# ------------------------------------------------------------------------------ D-04


def test_D_04_la_cantidad_recomendada_no_puede_pasar_del_limite_del_articulo(supervisor, session):
    puesto = crear_puesto(supervisor)
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    r = poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(guantes.id), "cantidad": 4}])
    assert r.status_code == 422
    detalle = r.json()["detalles"][0]
    assert detalle["regla"] == "D-04" and detalle["campo"] == "renglones.0.cantidad"
    # Igual al límite sí.
    r = poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(guantes.id), "cantidad": 3}])
    assert r.status_code == 200
    assert r.json()["renglones"][0]["limite"] == {"cantidad": 3, "periodo_dias": 7}


def test_D_04_el_limite_de_un_articulo_no_baja_de_lo_recomendado_en_una_dotacion(
    supervisor, compras, session
):
    puesto = crear_puesto(supervisor)
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(guantes.id), "cantidad": 3}])
    # Cambiar un límite pide `catalogo.limites`, que el Supervisor ya no tiene (AC-31).
    r = compras.patch(f"/api/articulos/{guantes.id}", json={"limite_cantidad": 2})
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "D-04"
    assert (
        compras.patch(f"/api/articulos/{guantes.id}", json={"limite_cantidad": 4}).status_code
        == 200
    )


def test_D_01_un_articulo_en_una_dotacion_no_se_elimina(supervisor, session):
    puesto = crear_puesto(supervisor)
    guantes = crear_articulo(session, retornable=False)
    poner_dotacion(supervisor, puesto["id"], [{"articulo_id": str(guantes.id), "cantidad": 1}])
    r = supervisor.delete(f"/api/articulos/{guantes.id}")
    assert r.status_code == 409
    poner_dotacion(supervisor, puesto["id"], [])
    assert supervisor.delete(f"/api/articulos/{guantes.id}").status_code == 204


# ------------------------------------------------------------------------------ permisos


def test_AC_01_los_endpoints_de_puestos_piden_su_permiso_por_clave(app, crear_usuario):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    solo_ver = crear_usuario({P.CATALOGO_VER}, almacen="KEP")
    ninguno = crear_usuario(set(), almacen="KEP")
    admin = crear_usuario({P.CATALOGO_ADMINISTRAR}, almacen="KEP")
    llamadas = [
        ("GET", "/api/puestos", None, "ver"),
        ("GET", f"/api/puestos/{UUID_FALSO}/dotacion", None, "ver"),
        ("POST", "/api/puestos", {"nombre": nombre_unico()}, "admin"),
        ("PATCH", f"/api/puestos/{UUID_FALSO}", {"activo": True}, "admin"),
        ("PUT", f"/api/puestos/{UUID_FALSO}/dotacion", {"renglones": []}, "admin"),
    ]
    for usuario, nivel in ((ninguno, "nada"), (solo_ver, "ver"), (admin, "admin")):
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        for metodo, ruta, cuerpo, pide in llamadas:
            r = cliente.request(metodo, ruta, json=cuerpo)
            permitido = (nivel == "ver" and pide == "ver") or (nivel == "admin" and pide == "admin")
            if permitido:
                assert r.status_code != 403, f"{nivel} {metodo} {ruta}"
            else:
                assert r.status_code == 403, f"{nivel} {metodo} {ruta}: {r.status_code}"
                assert r.json()["codigo"] == "SIN_PERMISO"


def test_AC_01_la_dotacion_del_trabajador_pide_trabajadores_ver(app, crear_usuario, session):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    trabajador = crear_trabajador(session)
    for permisos, esperado in (
        ({P.TRABAJADORES_VER}, 200),
        ({P.ENTREGAS_CREAR}, 403),
        (set(), 403),
    ):
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, crear_usuario(permisos, almacen="KEP")).status_code == 200
        r = cliente.get(f"/api/trabajadores/{trabajador.id}/dotacion")
        assert r.status_code == esperado, (permisos, r.status_code)


# ------------------------------------------------------------------------------ D-02


def test_D_02_la_dotacion_del_trabajador_muestra_lo_que_le_falta(almacenista, compras, session):
    trabajador = crear_trabajador(session)
    lentes = crear_articulo(session, retornable=False, nombre="Lente")
    detector = crear_articulo(session, retornable=True, nombre="Detector")
    tapones = crear_articulo(session, retornable=False, nombre="Tapón")
    puesto = dotacion_de_prueba(session, trabajador, {lentes: 2, detector: 1, tapones: 3})
    for articulo in (lentes, detector, tapones):
        abastecer(compras, articulo, 20)

    def dotacion():
        r = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion")
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["puesto"] == {"id": str(puesto.id), "nombre": puesto.nombre}
        return {
            x["articulo"]["codigo"]: (x["recomendada"], x["entregada"], x["falta"])
            for x in cuerpo["renglones"]
        }

    assert dotacion() == {
        lentes.codigo: (2, 0, 2),
        detector.codigo: (1, 0, 1),
        tapones.codigo: (3, 0, 3),
    }
    r = almacenista.post(
        "/api/vales",
        json=cuerpo_entrega(
            trabajador,
            [renglon(lentes.codigo, 1), renglon(detector.codigo, 1), renglon(tapones.codigo, 3)],
        ),
    )
    assert r.status_code == 201, r.text
    assert dotacion() == {
        lentes.codigo: (2, 1, 1),  # consumible: lo consumido en el periodo
        detector.codigo: (1, 1, 0),  # retornable: lo que tiene ahora
        tapones.codigo: (3, 3, 0),
    }
    # Pasarse de lo recomendado no deja `falta` negativa.
    r = almacenista.post(
        "/api/vales",
        json=cuerpo_entrega(trabajador, [renglon(lentes.codigo, 4)], observacion="Se mojaron"),
    )
    assert r.status_code == 201, r.text
    assert dotacion()[lentes.codigo] == (2, 5, 0)


def test_D_02_un_consumible_anterior_al_periodo_de_contrato_vigente_no_cuenta(
    almacenista, compras, session
):
    trabajador = crear_trabajador(session)
    lentes = crear_articulo(session, retornable=False)
    dotacion_de_prueba(session, trabajador, {lentes: 2})
    abastecer(compras, lentes, 10)
    assert (
        almacenista.post(
            "/api/vales", json=cuerpo_entrega(trabajador, [renglon(lentes.codigo, 2)])
        ).status_code
        == 201
    )
    # El periodo vigente empieza mañana: lo anterior es de otro contrato.
    periodo = session.scalar(
        select(PeriodoContrato).where(PeriodoContrato.trabajador_id == trabajador.id)
    )
    periodo.inicio = hoy_mx() + timedelta(days=1)
    periodo.fin = hoy_mx() + timedelta(days=300)
    session.flush()
    r = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion").json()
    assert [(x["recomendada"], x["entregada"], x["falta"]) for x in r["renglones"]] == [(2, 0, 2)]


def test_D_02_un_vale_cancelado_no_cuenta_como_entregado(almacenista, supervisor, compras, session):
    trabajador = crear_trabajador(session)
    lentes = crear_articulo(session, retornable=False)
    dotacion_de_prueba(session, trabajador, {lentes: 2})
    abastecer(compras, lentes, 10)
    r = almacenista.post("/api/vales", json=cuerpo_entrega(trabajador, [renglon(lentes.codigo, 2)]))
    assert r.status_code == 201, r.text
    c = supervisor.post(
        f"/api/vales/{r.json()['id']}/cancelacion",
        json={"motivo": "Prueba", "id_cliente": str(uuid.uuid4())},
    )
    assert c.status_code in (200, 201), c.text
    d = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion").json()
    assert [(x["entregada"], x["falta"]) for x in d["renglones"]] == [(0, 2)]


def test_D_02_sin_puesto_o_sin_dotacion_la_lista_va_vacia(almacenista, session):
    sin_puesto = crear_trabajador(session)  # texto "Soldador", sin `puesto_id`
    r = almacenista.get(f"/api/trabajadores/{sin_puesto.id}/dotacion")
    assert r.status_code == 200 and r.json() == {"puesto": None, "renglones": []}
    con_puesto_vacio = crear_trabajador(session)
    puesto = puesto_de_prueba(session)
    from tests.ayudas_dotacion import asignar_puesto

    asignar_puesto(session, con_puesto_vacio, puesto)
    r = almacenista.get(f"/api/trabajadores/{con_puesto_vacio.id}/dotacion")
    assert r.json() == {"puesto": {"id": str(puesto.id), "nombre": puesto.nombre}, "renglones": []}
    assert almacenista.get(f"/api/trabajadores/{UUID_FALSO}/dotacion").status_code == 404


def test_D_02_un_articulo_inactivo_no_se_lista_en_la_dotacion_del_trabajador(
    supervisor, almacenista, session
):
    trabajador = crear_trabajador(session)
    lentes = crear_articulo(session, retornable=False)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    assert (
        supervisor.post(
            f"/api/articulos/{lentes.id}/inactivacion", json={"motivo": "Prueba"}
        ).status_code
        == 200
    )
    r = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion").json()
    assert r["renglones"] == []


def test_D_02_la_dotacion_no_envia_costos(almacenista, session):
    trabajador = crear_trabajador(session)
    lentes = crear_articulo(session, retornable=False, costo_unitario=12)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    r = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion")
    assert "costo" not in r.text


# ------------------------------------------------------------------ puesto del trabajador


def datos_alta(**cambios):
    hoy = hoy_mx()
    n = uuid.uuid4().hex[:8]
    datos = {
        "nombre": f"Persona {n}",
        "area_obra": "Midrex",
        "inicio": (hoy - timedelta(days=5)).isoformat(),
        "fin": (hoy + timedelta(days=200)).isoformat(),
    }
    return datos | cambios


def test_D_01_el_alta_acepta_puesto_id_y_deja_el_nombre_del_puesto_en_el_texto(rh, supervisor):
    puesto = crear_puesto(supervisor)
    r = rh.post("/api/trabajadores", json=datos_alta(puesto_id=puesto["id"]))
    assert r.status_code == 201, r.text
    ficha = r.json()
    assert ficha["puesto"] == puesto["nombre"] and ficha["puesto_id"] == puesto["id"]
    assert ficha["periodo"]["puesto_id"] == puesto["id"]
    assert ficha["periodos"][0]["puesto"] == puesto["nombre"]
    assert rh.get(f"/api/trabajadores/{ficha['id']}").json()["puesto_id"] == puesto["id"]


def test_D_01_el_alta_con_solo_texto_busca_el_puesto_por_nombre(rh, supervisor):
    puesto = crear_puesto(supervisor, f"Pintor {uuid.uuid4().hex[:6]}")
    r = rh.post("/api/trabajadores", json=datos_alta(puesto=puesto["nombre"].upper()))
    assert r.status_code == 201, r.text
    assert r.json()["puesto_id"] == puesto["id"] and r.json()["puesto"] == puesto["nombre"]
    # Un texto que no existe en el catálogo se conserva, sin `puesto_id` (sin dotación).
    r = rh.post("/api/trabajadores", json=datos_alta(puesto="Puesto que no existe"))
    assert r.status_code == 201 and r.json()["puesto_id"] is None
    assert r.json()["puesto"] == "Puesto que no existe"


def test_D_01_el_alta_pide_el_puesto_en_alguna_de_sus_dos_formas(rh):
    r = rh.post("/api/trabajadores", json=datos_alta())
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "puesto"


def test_D_01_el_alta_rechaza_un_puesto_inexistente_o_inactivo(rh, supervisor):
    assert rh.post("/api/trabajadores", json=datos_alta(puesto_id=UUID_FALSO)).status_code == 422
    puesto = crear_puesto(supervisor)
    supervisor.patch(f"/api/puestos/{puesto['id']}", json={"activo": False})
    r = rh.post("/api/trabajadores", json=datos_alta(puesto_id=puesto["id"]))
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "puesto_id"


def test_D_01_el_reingreso_acepta_puesto_id_y_sin_puesto_conserva_el_anterior(rh, supervisor):
    uno, dos = crear_puesto(supervisor), crear_puesto(supervisor)
    ficha = rh.post("/api/trabajadores", json=datos_alta(puesto_id=uno["id"])).json()
    hoy = hoy_mx()
    periodo = {
        "inicio": (hoy + timedelta(days=300)).isoformat(),
        "fin": (hoy + timedelta(days=600)).isoformat(),
    }
    r = rh.post(f"/api/trabajadores/{ficha['id']}/periodos", json=periodo)
    assert r.status_code == 201, r.text
    assert r.json()["periodos"][0]["puesto_id"] == uno["id"]  # conserva el anterior
    periodo = {
        "inicio": (hoy + timedelta(days=700)).isoformat(),
        "fin": (hoy + timedelta(days=900)).isoformat(),
    }
    r = rh.post(
        f"/api/trabajadores/{ficha['id']}/periodos", json=periodo | {"puesto_id": dos["id"]}
    )
    assert r.status_code == 201, r.text
    nuevo = r.json()["periodos"][0]
    assert nuevo["puesto_id"] == dos["id"] and nuevo["puesto"] == dos["nombre"]
    assert (
        rh.post(
            f"/api/trabajadores/{ficha['id']}/periodos",
            json=periodo | {"puesto_id": UUID_FALSO},
        ).status_code
        == 422
    )


def test_D_01_la_lista_de_trabajadores_trae_el_puesto_id(rh, supervisor):
    puesto = crear_puesto(supervisor)
    ficha = rh.post("/api/trabajadores", json=datos_alta(puesto_id=puesto["id"])).json()
    lista = rh.get("/api/trabajadores", params={"q": ficha["numero_empleado"]}).json()
    assert lista["elementos"][0]["puesto_id"] == puesto["id"]


def test_D_01_la_ficha_breve_de_la_entrega_trae_el_puesto_id(almacenista, session):
    trabajador = crear_trabajador(session)
    puesto = puesto_de_prueba(session)
    from tests.ayudas_dotacion import asignar_puesto

    asignar_puesto(session, trabajador, puesto)
    cualquiera = crear_articulo(session, retornable=False)
    r = almacenista.post(
        "/api/vales/evaluar",
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [renglon(cualquiera.codigo)],
        },
    )
    assert r.status_code == 200 and r.json()["trabajador"]["puesto_id"] == str(puesto.id)


def test_D_01_el_pdf_y_los_articulos_sembrados_cumplen_los_limites(session):
    """La dotación de prueba (propuesta del PDF) respeta D-04: cada cantidad cabe en el límite."""
    from app.modulos.catalogo import datos_prueba

    articulos = {a.codigo: a for a in session.scalars(select(Articulo))}
    for puesto, renglones in datos_prueba.PUESTOS.items():
        for codigo, cantidad in renglones.items():
            limite = articulos[codigo].limite_cantidad
            assert limite is None or cantidad <= limite, (puesto, codigo)


def test_D_02_las_piezas_por_serie_de_la_dotacion_cuentan_las_que_tiene(
    almacenista, compras, session
):
    trabajador = crear_trabajador(session)
    arnes = crear_articulo(session, control="PIEZA", retornable=True)
    dotacion_de_prueba(session, trabajador, {arnes: 1})
    _, codigo = entrar_pieza(compras, arnes)
    r = almacenista.post("/api/vales", json=cuerpo_entrega(trabajador, [renglon(codigo)]))
    assert r.status_code == 201, r.text
    d = almacenista.get(f"/api/trabajadores/{trabajador.id}/dotacion").json()
    assert [(x["recomendada"], x["entregada"], x["falta"]) for x in d["renglones"]] == [(1, 1, 0)]
