"""Pruebas de `almacenes`: la red y las existencias (`inventario.ver`).

`existencia` y `pieza.ubicacion_id` los escribe `movimientos` (aún no existe): estas pruebas los
insertan directo, solo para probar lo que `almacenes` lee.
"""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Articulo, EstadoPieza, Pieza
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Existencia
from tests.conftest import iniciar_sesion_en


@pytest.fixture
def cliente_con(app, crear_usuario) -> Callable[..., TestClient]:
    clientes: list[TestClient] = []

    def _hacer(permisos: set[str]) -> TestClient:
        usuario = crear_usuario(set(permisos))
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente

    yield _hacer
    for c in clientes:
        c.close()


def _almacen(session: Session, clave: str):
    return AlmacenRepository(session).get_by_clave(clave)


def _ubicacion(session: Session, clave: str) -> uuid.UUID:
    return UbicacionRepository(session).de_almacen(_almacen(session, clave).id).id


def _articulo(session: Session, codigo: str) -> Articulo:
    return session.scalar(select(Articulo).where(Articulo.codigo == codigo))


def test_AC_01_listar_almacenes_pide_inventario_ver(cliente_con, cliente_como):
    assert cliente_con({P.INVENTARIO_VER}).get("/api/almacenes").status_code == 200
    assert cliente_con({P.CATALOGO_VER}).get("/api/almacenes").status_code == 403
    # RH no ve el inventario (RG-13).
    assert cliente_como("Recursos Humanos").get("/api/almacenes").status_code == 403


def test_RG_07_la_lista_de_almacenes_trae_la_red(cliente_como):
    r = cliente_como("Almacenista").get("/api/almacenes")
    assert r.status_code == 200
    almacenes = {a["clave"]: a for a in r.json()}
    assert set(almacenes) == {"KEP", "CON", "MID", "HYL", "LAM", "MIN"}
    assert almacenes["KEP"]["tipo"] == "CENTRAL" and almacenes["KEP"]["padre_id"] is None
    assert [h["clave"] for h in almacenes["KEP"]["hijos"]] == ["CON"]
    assert almacenes["CON"]["padre_clave"] == "KEP"
    assert [h["clave"] for h in almacenes["CON"]["hijos"]] == ["HYL", "LAM", "MID", "MIN"]
    assert almacenes["MID"]["padre_clave"] == "CON" and almacenes["MID"]["hijos"] == []


def test_AC_01_existencias_pide_inventario_ver(cliente_con, session):
    ruta = f"/api/almacenes/{_almacen(session, 'KEP').id}/existencias"
    assert cliente_con({P.INVENTARIO_VER, P.ALMACENES_TODOS}).get(ruta).status_code == 200
    assert cliente_con({P.CATALOGO_ADMINISTRAR}).get(ruta).status_code == 403


def test_AC_06_las_existencias_de_otro_almacen_responden_404_sin_almacenes_todos(
    cliente_con, cliente_como, session
):
    # El almacenista de Kepler ve las de Kepler; las de Contratistas responden como si no
    # existieran. Sin almacén asignado ni `almacenes.todos`, ninguno. El Administrador, todos.
    kep, con = _almacen(session, "KEP").id, _almacen(session, "CON").id
    almacenista = cliente_como("Almacenista")
    assert almacenista.get(f"/api/almacenes/{kep}/existencias").status_code == 200
    ajeno = almacenista.get(f"/api/almacenes/{con}/existencias")
    inexistente = almacenista.get(f"/api/almacenes/{uuid.uuid4()}/existencias")
    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.json() == inexistente.json()
    sin_almacen = cliente_con({P.INVENTARIO_VER})
    assert sin_almacen.get(f"/api/almacenes/{kep}/existencias").status_code == 404
    administrador = cliente_como("Administrador")
    assert administrador.get(f"/api/almacenes/{con}/existencias").status_code == 200


def test_RG_08_existencias_de_un_almacen_inexistente_responde_404(cliente_como):
    r = cliente_como("Almacenista").get(f"/api/almacenes/{uuid.uuid4()}/existencias")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_I_05_existencias_y_disponibles_por_articulo(cliente_como, session):
    # La carga inicial de `movimientos` dejó existencias: esta prueba parte de un inventario vacío.
    session.execute(delete(Existencia))
    session.execute(update(Pieza).values(ubicacion_id=None))  # y sin las piezas de prueba
    kep = _ubicacion(session, "KEP")
    flexometro = _articulo(session, "FLEXOM")
    arnes = _articulo(session, "ARN-KEV")
    session.add(Existencia(ubicacion_id=kep, articulo_id=flexometro.id, cantidad=12))

    # Tres arneses en Kepler: uno Apto, uno No apto y uno en calibración.
    servicio = CatalogoService(session)
    estados = [EstadoPieza.APTO, EstadoPieza.NO_APTO, EstadoPieza.EN_CALIBRACION]
    for n, estado in enumerate(estados):
        pieza = servicio.registrar_pieza(arnes.id, f"ALT-ALM-{n}", f"SA-{n}", estado=estado)
        pieza.ubicacion_id = kep
    session.add(Existencia(ubicacion_id=kep, articulo_id=arnes.id, cantidad=3))
    # Existencia de otro almacén: no debe aparecer en el de Kepler.
    session.add(
        Existencia(ubicacion_id=_ubicacion(session, "CON"), articulo_id=flexometro.id, cantidad=4)
    )
    session.flush()

    cliente = cliente_como("Almacenista")
    r = cliente.get(f"/api/almacenes/{_almacen(session, 'KEP').id}/existencias")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["almacen"]["clave"] == "KEP" and cuerpo["total"] == 2
    filas = {e["codigo"]: e for e in cuerpo["elementos"]}
    assert (filas["FLEXOM"]["cantidad"], filas["FLEXOM"]["disponible"]) == (12, 12)
    assert (filas["ARN-KEV"]["cantidad"], filas["ARN-KEV"]["disponible"]) == (3, 1)
    assert filas["ARN-KEV"]["categoria_nombre"] == "Equipo de alturas"
    # Sin costos (RG-12).
    assert "costo_unitario" not in filas["FLEXOM"]

    # Lo de Contratistas lo ve el Administrador (AC-06); no el almacenista de Kepler.
    ruta_con = f"/api/almacenes/{_almacen(session, 'CON').id}/existencias"
    assert cliente.get(ruta_con).status_code == 404
    con = cliente_como("Administrador").get(ruta_con)
    assert [e["codigo"] for e in con.json()["elementos"]] == ["FLEXOM"]


def test_CF_11_las_existencias_de_un_articulo_inactivo_siguen_visibles_y_marcadas(
    cliente_como, session
):
    # La carga inicial de `movimientos` dejó existencias: esta prueba parte de un inventario vacío.
    session.execute(delete(Existencia))
    kep = _ubicacion(session, "KEP")
    cincel = _articulo(session, "CINCEL")
    session.add(Existencia(ubicacion_id=kep, articulo_id=cincel.id, cantidad=5))
    session.flush()
    compras = cliente_como("Compras")
    compras.post(f"/api/articulos/{cincel.id}/inactivacion", json={"motivo": "Obsoleto"})

    ruta = f"/api/almacenes/{_almacen(session, 'KEP').id}/existencias"
    (fila,) = compras.get(ruta).json()["elementos"]
    assert fila["codigo"] == "CINCEL" and fila["activo"] is False and fila["cantidad"] == 5
    assert compras.get(ruta, params={"activo": True}).json()["total"] == 0
    assert compras.get(ruta, params={"activo": False}).json()["total"] == 1


def test_C_03_las_existencias_se_filtran_y_se_paginan(cliente_como, session):
    # La carga inicial de `movimientos` dejó existencias: esta prueba parte de un inventario vacío.
    session.execute(delete(Existencia))
    kep = _ubicacion(session, "KEP")
    for codigo in ("FLEXOM", "CINCEL", "MARRO-B"):
        articulo = _articulo(session, codigo)
        session.add(Existencia(ubicacion_id=kep, articulo_id=articulo.id, cantidad=1))
    # Una existencia en cero no se lista.
    peto = _articulo(session, "PETO")
    session.add(Existencia(ubicacion_id=kep, articulo_id=peto.id, cantidad=0))
    session.flush()
    cliente = cliente_como("Almacenista")
    ruta = f"/api/almacenes/{_almacen(session, 'KEP').id}/existencias"

    assert cliente.get(ruta).json()["total"] == 3
    assert cliente.get(ruta, params={"q": "cincel"}).json()["total"] == 1
    assert len(cliente.get(ruta, params={"tamano": 2}).json()["elementos"]) == 2
    ultima = cliente.get(ruta, params={"tamano": 2, "pagina": 2}).json()
    assert ultima["total"] == 3 and len(ultima["elementos"]) == 1


def test_RG_01_almacenes_solo_lee_las_existencias(session):
    """`AlmacenService` solo lee `existencia`: ni un método de escritura ni cambios al listar."""
    publicos = {n for n in dir(AlmacenService) if not n.startswith("_")}
    assert not {n for n in publicos if n.startswith(("registrar", "ajustar", "mover", "guardar"))}
    antes = session.scalar(select(Existencia).limit(1))
    AlmacenService(session).listar()
    assert session.scalar(select(Existencia).limit(1)) == antes
