"""Serie pendiente en la consulta (E-29, I-02): bandera en ficha y seguimiento, filtro y tablero."""

from app.modulos.acceso.permisos import P

SEGUIMIENTO = "/api/seguimiento/piezas"
RESUMEN = "/api/tablero/resumen"


def _pieza_sin_serie(datos, ubicacion, articulo):
    pieza = datos.pieza(articulo, ubicacion)
    pieza.numero_serie = None
    datos.session.flush()
    return pieza


def test_E_29_la_ficha_y_el_seguimiento_marcan_la_serie_pendiente(cliente_con, datos):
    admin = cliente_con(P.REPORTES_EXISTENCIAS, P.CATALOGO_VER, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés de serie pendiente", control="PIEZA")
    ub = datos.ub_almacen("KEP")
    sin = _pieza_sin_serie(datos, ub, arnes)
    con = datos.pieza(arnes, ub, serie="SER-CONSULTA-1")

    ficha = admin.get(f"/api/piezas/{sin.id}").json()
    assert ficha["numero_serie"] is None and ficha["serie_pendiente"] is True
    assert admin.get(f"/api/piezas/{con.id}").json()["serie_pendiente"] is False

    lista = admin.get(SEGUIMIENTO, params={"articulo_id": str(arnes.id)}).json()
    por_codigo = {e["codigo"]: e for e in lista["elementos"]}
    assert por_codigo[sin.codigo]["serie_pendiente"] is True
    assert por_codigo[con.codigo]["serie_pendiente"] is False


def test_E_29_el_seguimiento_filtra_por_serie_pendiente(cliente_con, datos):
    admin = cliente_con(P.REPORTES_EXISTENCIAS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés filtrado por serie", control="PIEZA")
    ub = datos.ub_almacen("KEP")
    sin = _pieza_sin_serie(datos, ub, arnes)
    con = datos.pieza(arnes, ub, serie="SER-CONSULTA-2")
    base = {"articulo_id": str(arnes.id), "tamano": 100}

    solo_pendientes = admin.get(SEGUIMIENTO, params=base | {"serie_pendiente": "true"}).json()
    assert {e["codigo"] for e in solo_pendientes["elementos"]} == {sin.codigo}
    con_serie = admin.get(SEGUIMIENTO, params=base | {"serie_pendiente": "false"}).json()
    assert {e["codigo"] for e in con_serie["elementos"]} == {con.codigo}
    todas = admin.get(SEGUIMIENTO, params=base).json()
    assert {e["codigo"] for e in todas["elementos"]} == {sin.codigo, con.codigo}
    assert admin.get(SEGUIMIENTO, params={"serie_pendiente": "quizas"}).status_code == 422


def test_TB_01_el_tablero_cuenta_las_piezas_con_serie_pendiente_del_alcance(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    en_con = cliente_con(P.TABLERO_VER, almacen="CON")
    base_kep = en_kep.get(RESUMEN).json()["piezas_serie_pendiente"]
    base_con = en_con.get(RESUMEN).json()["piezas_serie_pendiente"]

    arnes = datos.articulo("Arnés contado en el tablero", control="PIEZA")
    ub = datos.ub_almacen("KEP")
    _pieza_sin_serie(datos, ub, arnes)
    _pieza_sin_serie(datos, ub, arnes)
    datos.pieza(arnes, ub, serie="SER-CONSULTA-3")  # con serie: no cuenta
    baja = _pieza_sin_serie(datos, ub, arnes)
    baja.estado = "BAJA"  # de baja: no cuenta
    datos.session.flush()

    assert en_kep.get(RESUMEN).json()["piezas_serie_pendiente"] == base_kep + 2
    assert en_con.get(RESUMEN).json()["piezas_serie_pendiente"] == base_con
