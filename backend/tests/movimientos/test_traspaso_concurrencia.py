"""Concurrencia real de los traspasos (RG-08, RG-09, X-02, X-12, X-13): hilos con conexiones
propias y datos CONFIRMADOS, que `limpieza` borra al final (ver `conftest.py`)."""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.config import get_settings
from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models import Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.conftest import UsuarioPrueba, iniciar_sesion_en
from tests.movimientos.ayudas import abastecer
from tests.movimientos.ayudas_traspasos import USUARIO_DE_ALMACEN
from tests.movimientos.test_concurrencia import Escenario, en_paralelo

VALES = "/api/vales"


def renglon(codigo, cantidad=1):
    return {"codigo": codigo, "cantidad": cantidad}


@pytest.fixture
def escenario(sesion_independiente, limpieza, cliente_independiente) -> Iterator[Escenario]:
    yield Escenario(sesion_independiente, limpieza, cliente_independiente)
    # Una recepción apunta a su traspaso (`vale_origen_id`): se desligan antes de que `limpieza`
    # borre los vales de los artículos de la prueba.
    s = sesion_independiente()
    try:
        vales = list(
            s.scalars(
                select(Movimiento.vale_id).where(Movimiento.articulo_id.in_(limpieza.articulos))
            )
        )
        s.execute(update(Vale).where(Vale.id.in_(vales)).values(vale_origen_id=None))
        s.commit()
    finally:
        s.close()


@pytest.fixture
def almacenista_de(engine) -> Iterator[Callable[[str], TestClient]]:
    """Un cliente con sesión real (commits de verdad) del almacenista de ese almacén."""
    from app.main import create_app

    app = create_app()
    clientes: list[TestClient] = []
    ajustes = get_settings()

    def _cliente(clave: str) -> TestClient:
        c = TestClient(app)
        usuario = UsuarioPrueba(USUARIO_DE_ALMACEN[clave], ajustes.clave_datos_prueba)
        assert iniciar_sesion_en(c, usuario).status_code == 200
        clientes.append(c)
        return c

    yield _cliente
    for c in clientes:
        c.close()


def almacen(s, clave):
    from app.modulos.almacenes.service import AlmacenService

    return AlmacenService(s).obtener_por_clave(clave).id


def traspasar(cliente, destino_id, renglones, **extra):
    return cliente.post(
        VALES,
        json={
            "tipo": "TRASPASO",
            "destino_almacen_id": str(destino_id),
            "id_cliente": str(uuid.uuid4()),
            "renglones": renglones,
        }
        | extra,
    )


def recepcion(cliente, traspaso_id, renglones, **extra):
    return cliente.post(
        VALES,
        json={
            "tipo": "RECEPCION",
            "vale_origen_id": traspaso_id,
            "id_cliente": str(uuid.uuid4()),
            "renglones": renglones,
            "observacion": "Faltó en el contenedor",  # RG-14: con diferencias se exige
        }
        | extra,
    )


def cantidad_en(s, articulo, *, almacen_clave=None, virtual=None) -> int:
    consulta = (
        select(func.coalesce(func.sum(Existencia.cantidad), 0))
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == articulo.id)
    )
    if virtual:
        consulta = consulta.where(Ubicacion.virtual == virtual)
    elif almacen_clave:
        consulta = consulta.where(Ubicacion.almacen_id == almacen(s, almacen_clave))
    return int(s.scalar(consulta))


def vales_de(s, articulo, tipo) -> list[Vale]:
    return list(
        s.scalars(
            select(Vale)
            .join(Movimiento, Movimiento.vale_id == Vale.id)
            .where(Movimiento.articulo_id == articulo.id, Vale.tipo == tipo)
            .distinct()
        )
    )


def preparar_traspaso(escenario, almacenista_de, sesion_independiente, *, total=10, enviado=6):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, total)
    s = sesion_independiente()
    r = traspasar(almacenista_de("KEP"), almacen(s, "CON"), [renglon(guantes.codigo, enviado)])
    assert r.status_code == 201, r.text
    return guantes, r.json()


def test_X_13_dos_recepciones_simultaneas_del_mismo_traspaso_no_duplican_nada(
    escenario, almacenista_de, sesion_independiente
):
    guantes, traspaso = preparar_traspaso(escenario, almacenista_de, sesion_independiente)
    c1, c2 = almacenista_de("CON"), almacenista_de("CON")
    r1, r2 = en_paralelo(
        [
            lambda: recepcion(c1, traspaso["id"], [renglon(guantes.codigo, 6)]),
            lambda: recepcion(c2, traspaso["id"], [renglon(guantes.codigo, 6)]),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["codigo"] == "VALE_CAMBIO"
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "X-12"

    s = sesion_independiente()
    assert len(vales_de(s, guantes, "RECEPCION")) == 1  # el que perdió no dejó nada
    assert cantidad_en(s, guantes, almacen_clave="CON") == 6  # no se duplicó
    assert cantidad_en(s, guantes, virtual="EN_TRANSITO") == 0
    assert cantidad_en(s, guantes, almacen_clave="KEP") == 4
    assert s.get(Vale, uuid.UUID(traspaso["id"])).estado == "RECIBIDO"


def test_X_11_dos_recepciones_simultaneas_de_partes_distintas_se_turnan_y_completan_el_traspaso(
    escenario, almacenista_de, sesion_independiente
):
    guantes, traspaso = preparar_traspaso(escenario, almacenista_de, sesion_independiente)
    c1, c2 = almacenista_de("CON"), almacenista_de("CON")
    r1, r2 = en_paralelo(
        [
            lambda: recepcion(c1, traspaso["id"], [renglon(guantes.codigo, 3)]),
            lambda: recepcion(c2, traspaso["id"], [renglon(guantes.codigo, 3)]),
        ]
    )
    assert (r1.status_code, r2.status_code) == (201, 201), (r1.text, r2.text)
    s = sesion_independiente()
    assert len(vales_de(s, guantes, "RECEPCION")) == 2
    assert cantidad_en(s, guantes, almacen_clave="CON") == 6
    assert cantidad_en(s, guantes, virtual="EN_TRANSITO") == 0
    # El estado lo fija la última en confirmar, con todo lo recibido: Recibido.
    assert s.get(Vale, uuid.UUID(traspaso["id"])).estado == "RECIBIDO"
    # y los folios de recepción son consecutivos, sin repetirse
    folios = sorted(v.folio for v in vales_de(s, guantes, "RECEPCION"))
    assert len(set(folios)) == 2


def test_X_12_dos_recepciones_simultaneas_que_juntas_se_pasan_de_lo_enviado_solo_una_gana(
    escenario, almacenista_de, sesion_independiente
):
    guantes, traspaso = preparar_traspaso(escenario, almacenista_de, sesion_independiente)
    c1, c2 = almacenista_de("CON"), almacenista_de("CON")
    r1, r2 = en_paralelo(
        [
            lambda: recepcion(c1, traspaso["id"], [renglon(guantes.codigo, 4)]),
            lambda: recepcion(c2, traspaso["id"], [renglon(guantes.codigo, 4)]),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    s = sesion_independiente()
    assert cantidad_en(s, guantes, almacen_clave="CON") == 4
    assert cantidad_en(s, guantes, virtual="EN_TRANSITO") == 2
    assert s.get(Vale, uuid.UUID(traspaso["id"])).estado == "RECIBIDO_CON_DIFERENCIAS"


def test_idempotencia_dos_recepciones_simultaneas_con_el_mismo_id_cliente(
    escenario, almacenista_de, sesion_independiente
):
    guantes, traspaso = preparar_traspaso(escenario, almacenista_de, sesion_independiente)
    c1, c2 = almacenista_de("CON"), almacenista_de("CON")
    cuerpo = {
        "tipo": "RECEPCION",
        "vale_origen_id": traspaso["id"],
        "id_cliente": str(uuid.uuid4()),
        "renglones": [renglon(guantes.codigo, 6)],
    }
    r1, r2 = en_paralelo([lambda: c1.post(VALES, json=cuerpo), lambda: c2.post(VALES, json=cuerpo)])
    assert sorted([r1.status_code, r2.status_code]) == [200, 201], (r1.text, r2.text)
    assert r1.json() == r2.json()
    s = sesion_independiente()
    assert len(vales_de(s, guantes, "RECEPCION")) == 1
    assert cantidad_en(s, guantes, almacen_clave="CON") == 6


def test_X_02_dos_traspasos_simultaneos_de_la_misma_pieza_solo_uno_sale(
    escenario, almacenista_de, sesion_independiente
):
    arnes = escenario.articulo(control="PIEZA", requiere_inspeccion=False)
    codigo = escenario.pieza_en_kep(arnes)
    c1, c2 = almacenista_de("KEP"), almacenista_de("KEP")
    destino = almacen(sesion_independiente(), "CON")
    r1, r2 = en_paralelo(
        [
            lambda: traspasar(c1, destino, [renglon(codigo)]),
            lambda: traspasar(c2, destino, [renglon(codigo)]),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "X-02"
    s2 = sesion_independiente()
    assert len(vales_de(s2, arnes, "TRASPASO")) == 1
    assert cantidad_en(s2, arnes, virtual="EN_TRANSITO") == 1
    assert cantidad_en(s2, arnes, almacen_clave="KEP") == 0
    pieza = s2.scalar(select(Pieza).where(Pieza.codigo == codigo))
    transito = s2.scalar(select(Ubicacion.id).where(Ubicacion.virtual == "EN_TRANSITO"))
    assert pieza.ubicacion_id == transito


def test_RG_04_dos_traspasos_simultaneos_no_dejan_la_existencia_negativa(
    escenario, almacenista_de, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 5)
    c1, c2 = almacenista_de("KEP"), almacenista_de("KEP")
    destino = almacen(sesion_independiente(), "CON")
    r1, r2 = en_paralelo(
        [
            lambda: traspasar(c1, destino, [renglon(guantes.codigo, 3)]),
            lambda: traspasar(c2, destino, [renglon(guantes.codigo, 3)]),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "X-02"
    s2 = sesion_independiente()
    assert cantidad_en(s2, guantes, almacen_clave="KEP") == 2
    assert cantidad_en(s2, guantes, virtual="EN_TRANSITO") == 3


def test_RG_06_los_folios_de_traspasos_simultaneos_son_consecutivos(
    escenario, almacenista_de, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 20)
    clientes = [almacenista_de("KEP") for _ in range(4)]
    destino = almacen(sesion_independiente(), "CON")
    respuestas = en_paralelo(
        [lambda c=c: traspasar(c, destino, [renglon(guantes.codigo, 2)]) for c in clientes]
    )
    assert [r.status_code for r in respuestas] == [201] * 4, [r.text for r in respuestas]
    numeros = sorted(int(r.json()["folio"].rsplit("-", 1)[1]) for r in respuestas)
    assert numeros == list(range(numeros[0], numeros[0] + 4))
    s2 = sesion_independiente()
    assert cantidad_en(s2, guantes, almacen_clave="KEP") == 12
    assert cantidad_en(s2, guantes, virtual="EN_TRANSITO") == 8
