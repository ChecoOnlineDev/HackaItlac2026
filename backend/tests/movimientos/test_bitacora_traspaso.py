# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""SG-05 con el flujo real: un traspaso recibido queda en la bitácora de los dos almacenes.

Contratistas envía a Midrex y Midrex recibe: en Contratistas es una salida; en Midrex, primero
«en camino» y, al recibirlo, una entrada.
"""

from tests.movimientos.ayudas import abastecer, crear_articulo
from tests.movimientos.ayudas_traspasos import (
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    enviar,
    recibir,
    renglon,
)

MOVIMIENTOS = "/api/reportes/movimientos"


def _por_vale(cliente, session, clave, articulo):
    r = cliente.get(
        MOVIMIENTOS,
        params={"almacen_id": str(almacen_id(session, clave)), "articulo_id": str(articulo.id)},
    )
    assert r.status_code == 200, r.text
    return {f["vale_id"]: f for f in r.json()["elementos"]}


def test_SG_05_un_traspaso_recibido_es_salida_en_el_origen_y_entrada_en_el_destino(
    cliente_almacen, cliente_como, compras, session
):
    kep, con, mid = cliente_almacen("KEP"), cliente_almacen("CON"), cliente_almacen("MID")
    admin = cliente_como("Administrador")
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    a_con = enviar(kep, session, "CON", [renglon(guantes.codigo, 10)])
    recibir(con, a_con, [renglon(guantes.codigo, 10)])
    envio = enviar(con, session, "MID", [renglon(guantes.codigo, 4)])

    # Mientras viaja: sale de Contratistas y va en camino hacia Midrex.
    de_con = _por_vale(admin, session, "CON", guantes)
    de_mid = _por_vale(admin, session, "MID", guantes)
    assert de_con[envio["id"]]["direccion"] == "SALIDA"
    assert de_mid[envio["id"]]["direccion"] == "EN_CAMINO"

    recepcion = recibir(mid, envio, [renglon(guantes.codigo, 4)])
    de_con = _por_vale(admin, session, "CON", guantes)
    de_mid = _por_vale(admin, session, "MID", guantes)
    assert de_con[envio["id"]]["direccion"] == "SALIDA"
    assert de_mid[recepcion["id"]]["direccion"] == "ENTRADA"
    assert de_mid[recepcion["id"]]["cantidad"] == 4
    # Un almacén sin `almacenes.todos` solo ve la bitácora de su almacén: Midrex no ve la de
    # Contratistas, pero sí lo que le llega.
    propia = mid.get(MOVIMIENTOS, params={"articulo_id": str(guantes.id)}).json()["elementos"]
    assert {f["vale_id"] for f in propia} == {envio["id"], recepcion["id"]}
