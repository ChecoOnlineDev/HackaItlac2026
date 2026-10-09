"""Valor del inventario (FEAT-012, VI-01 a VI-07). Solo totales en pesos, nunca costos de artículo.

Los datos de prueba ya traen inventario con costos, así que las cifras se miden por diferencia
(antes y después de insertar con `datos`).
"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual

VALOR = "/api/tablero/valor"
CAMPOS = {
    "moneda",
    "alcance",
    "total",
    "en_almacen",
    "en_resguardo",
    "en_transito",
    "articulos_sin_costo",
    "unidades_sin_costo",
    "por_categoria",
    "por_almacen",
    "generado_en",
    "unidades_en_almacen",
    "unidades_en_resguardo",
    "unidades_total",
}


def _ok(cliente, **parametros) -> dict:
    r = cliente.get(VALOR, params=parametros)
    assert r.status_code == 200, r.text
    return r.json()


def _d(texto: str | None) -> Decimal:
    assert texto is not None
    return Decimal(texto)


def _almacen_id(datos, clave: str) -> str:
    return str(datos.almacen(clave).id)


def test_VI_01_sin_el_permiso_responde_403_y_con_el_permiso_no_pide_tablero_ver(cliente_con, app):
    sin = cliente_con(P.TABLERO_VER, P.CATALOGO_COSTOS, P.REPORTES_EXISTENCIAS, almacen="KEP")
    r = sin.get(VALOR)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert "total" not in r.text
    assert TestClient(app).get(VALOR).status_code == 401
    solo = cliente_con(P.REPORTES_VALOR_INVENTARIO, almacen="KEP")  # sin tablero.ver
    assert set(_ok(solo)) == CAMPOS


def test_VI_02_sin_almacenes_todos_solo_ve_su_almacen_y_con_el_admin_filtra(cliente_con, datos):
    articulo = datos.articulo("Artículo VI-02", costo="10.00")
    datos.existencia(datos.ub_almacen("MID"), articulo, 5)
    datos.existencia(datos.ub_almacen("CON"), articulo, 3)

    supervisor = cliente_con(P.REPORTES_VALOR_INVENTARIO, almacen="CON")
    en_con = _ok(supervisor)
    assert en_con["alcance"] == {
        "todos": False,
        "almacen_id": _almacen_id(datos, "CON"),
        "almacen_nombre": datos.almacen("CON").nombre,
    }
    # Pedir otro almacén no muestra información ajena (AC-37).
    pedido = _ok(supervisor, almacen_id=_almacen_id(datos, "MID"))
    assert pedido["en_almacen"] == "0.00"

    admin = cliente_con(P.REPORTES_VALOR_INVENTARIO, P.ALMACENES_TODOS)
    todos = _ok(admin)
    assert todos["alcance"] == {"todos": True, "almacen_id": None, "almacen_nombre": None}
    en_mid = _ok(admin, almacen_id=_almacen_id(datos, "MID"))
    assert en_mid["alcance"]["almacen_id"] == _almacen_id(datos, "MID")
    assert en_mid["alcance"]["todos"] is False
    assert _d(en_mid["en_almacen"]) >= Decimal("50.00")
    assert _d(todos["en_almacen"]) >= _d(en_mid["en_almacen"]) + _d(en_con["en_almacen"])
    r = admin.get(VALOR, params={"almacen_id": str(uuid.uuid4())})
    assert r.status_code == 404

    sin_almacen = _ok(cliente_con(P.REPORTES_VALOR_INVENTARIO))
    assert sin_almacen["total"] == "0.00" and sin_almacen["por_categoria"] == []


def test_VI_03_el_total_es_existencia_por_costo_y_coincide_con_la_suma_de_sus_partes(
    cliente_con, datos
):
    admin = cliente_con(P.REPORTES_VALOR_INVENTARIO, P.ALMACENES_TODOS)
    antes, antes_kep = _ok(admin), _ok(admin, almacen_id=_almacen_id(datos, "KEP"))

    articulo = datos.articulo("Artículo VI-03", costo="12.50")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 4)  # en almacén: 50.00
    trabajador = datos.trabajador()
    datos.entrega(trabajador, articulo, almacen="KEP", cantidad=2)  # en resguardo: 25.00
    datos.existencia(datos.ub_virtual(UbicacionVirtual.EN_TRANSITO), articulo, 3)  # 37.50

    despues, despues_kep = _ok(admin), _ok(admin, almacen_id=_almacen_id(datos, "KEP"))
    assert _d(despues["en_almacen"]) - _d(antes["en_almacen"]) == Decimal("50.00")
    assert _d(despues["en_resguardo"]) - _d(antes["en_resguardo"]) == Decimal("25.00")
    assert _d(despues["en_transito"]) - _d(antes["en_transito"]) == Decimal("37.50")
    assert _d(despues["total"]) - _d(antes["total"]) == Decimal("112.50")
    for cuerpo in (despues, despues_kep):
        transito = _d(cuerpo["en_transito"]) if cuerpo["en_transito"] is not None else 0
        partes = _d(cuerpo["en_almacen"]) + _d(cuerpo["en_resguardo"]) + transito
        assert _d(cuerpo["total"]) == partes
        assert sum(_d(c["valor"]) for c in cuerpo["por_categoria"]) == _d(cuerpo["total"])
        assert len(cuerpo["por_categoria"]) <= 7
    # Un solo almacén: sin tránsito (no se atribuye) y con su almacén y su resguardo.
    assert despues_kep["en_transito"] is None
    assert _d(despues_kep["en_almacen"]) - _d(antes_kep["en_almacen"]) == Decimal("50.00")
    assert _d(despues_kep["en_resguardo"]) - _d(antes_kep["en_resguardo"]) == Decimal("25.00")
    assert _d(despues["total"]).as_tuple().exponent == -2


def test_VI_04_un_articulo_sin_costo_no_suma_pero_se_cuenta(cliente_con, datos):
    admin = cliente_con(P.REPORTES_VALOR_INVENTARIO, P.ALMACENES_TODOS)
    antes = _ok(admin)
    articulo = datos.articulo("Artículo VI-04 sin costo")  # sin costo
    datos.existencia(datos.ub_almacen("KEP"), articulo, 6)
    datos.entrega(datos.trabajador(), articulo, almacen="KEP", cantidad=2)
    despues = _ok(admin)
    assert despues["articulos_sin_costo"] == antes["articulos_sin_costo"] + 1
    assert despues["unidades_sin_costo"] == antes["unidades_sin_costo"] + 8
    assert despues["total"] == antes["total"]
    assert despues["en_almacen"] == antes["en_almacen"]


def test_VI_05_la_respuesta_no_trae_costos_unitarios_ni_valor_por_articulo(cliente_con, datos):
    articulo = datos.articulo("Artículo VI-05", costo="777.77")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 1)
    admin = cliente_con(P.REPORTES_VALOR_INVENTARIO, P.ALMACENES_TODOS)
    r = admin.get(VALOR)
    assert r.status_code == 200
    assert "Artículo VI-05" not in r.text
    # VI-05 prohíbe valores por artículo; un total agregado puede coincidir con su costo.
    assert "costo_unitario" not in r.text and "articulo_id" not in r.text

    def claves(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from claves(v)
        elif isinstance(x, list):
            for v in x:
                yield from claves(v)

    con_costo = {k for k in claves(r.json()) if "costo" in k}
    assert con_costo == {"articulos_sin_costo", "unidades_sin_costo"}


def test_VI_06_el_filtro_sin_costo_lista_solo_articulos_activos_sin_costo(cliente_con, datos):
    sin = datos.articulo("Zeta VI-06 sin costo")
    con = datos.articulo("Zeta VI-06 con costo", costo="5.00")
    inactivo = datos.articulo("Zeta VI-06 inactivo sin costo")
    inactivo.activo = False
    inactivo.motivo_inactivacion = "Fuera de uso en esta prueba"
    datos.session.flush()

    ver = cliente_con(P.CATALOGO_VER, almacen="KEP")  # sin catalogo.costos
    r = ver.get("/api/articulos", params={"q": "Zeta VI-06", "sin_costo": "true"})
    assert r.status_code == 200, r.text
    assert {a["id"] for a in r.json()["elementos"]} == {str(sin.id)}
    assert "costo_unitario" not in r.text
    # Sin el filtro, el contrato sigue igual.
    r = ver.get("/api/articulos", params={"q": "Zeta VI-06"})
    assert {a["id"] for a in r.json()["elementos"]} == {str(sin.id), str(con.id), str(inactivo.id)}
    # El filtro sigue pidiendo catalogo.ver.
    sin_permiso = cliente_con(P.REPORTES_VALOR_INVENTARIO, almacen="KEP")
    assert sin_permiso.get("/api/articulos", params={"sin_costo": "true"}).status_code == 403


def test_VI_07_por_almacen_solo_viene_en_el_alcance_todos_sin_filtrar(cliente_con, datos):
    articulo = datos.articulo("Artículo VI-07", costo="2.00")
    datos.existencia(datos.ub_almacen("MID"), articulo, 10)
    datos.entrega(datos.trabajador(), articulo, almacen="MID", cantidad=1)

    admin = cliente_con(P.REPORTES_VALOR_INVENTARIO, P.ALMACENES_TODOS)
    todos = _ok(admin)
    por_nombre = {a["nombre"]: a for a in todos["por_almacen"]}
    assert datos.almacen("MID").nombre in por_nombre and datos.almacen("KEP").nombre in por_nombre
    for a in todos["por_almacen"]:
        assert _d(a["total"]) == _d(a["en_almacen"]) + _d(a["en_resguardo"])
    mid = por_nombre[datos.almacen("MID").nombre]
    assert _d(mid["en_almacen"]) >= Decimal("20.00") and _d(mid["en_resguardo"]) >= Decimal("2.00")

    assert _ok(admin, almacen_id=_almacen_id(datos, "MID"))["por_almacen"] == []
    assert _ok(cliente_con(P.REPORTES_VALOR_INVENTARIO, almacen="MID"))["por_almacen"] == []
