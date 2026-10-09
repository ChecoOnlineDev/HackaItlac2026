"""Tablero de inicio (FEAT-008, TB-01 a TB-03): tarjetas y ranking de lo más usado.

Los datos de prueba ya traen inventario, así que las tarjetas se miden por diferencia (antes y
después de insertar con `datos`) y el consumo se aísla con categorías nuevas. Los usuarios se
crean con `tablero.ver` explícito, sin depender de los roles iniciales.
"""

import uuid
from datetime import timedelta

import pytest

from app.core.ids import nuevo_id
from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.catalogo.models import Categoria
from app.modulos.consulta.service import rango_utc
from app.modulos.solicitudes_compra.models import SolicitudCompra

RESUMEN = "/api/tablero/resumen"
CONSUMO = "/api/tablero/consumo"
REPORTE_CONSUMO = "/api/reportes/consumo"

DIA = hoy_mx() - timedelta(days=40)  # un día pasado fijo, lejos de lo que traen los datos


def _ok(cliente, ruta: str, **parametros) -> dict:
    r = cliente.get(ruta, params=parametros)
    assert r.status_code == 200, r.text
    return r.json()


def _momento(dia, minutos: int = 600):
    """Un instante (UTC sin zona) dentro del día de México `dia`."""
    inicio, _ = rango_utc(dia, dia)
    return inicio + timedelta(minutes=minutos)


def _categoria(datos, articulo) -> Categoria:
    return datos.session.get(Categoria, articulo.categoria_id)


def _consumible(datos, nombre: str | None = None, categoria: Categoria | None = None):
    return datos.articulo(nombre, retornable=False, unidad="pieza", categoria=categoria)


def _almacen_id(datos, clave: str) -> str:
    return str(datos.almacen(clave).id)


# ------------------------------------------------------------------------------------ TB-01


@pytest.mark.parametrize("ruta", [RESUMEN, CONSUMO])
def test_TB_01_sin_tablero_ver_el_servidor_responde_403(cliente_con, app, ruta):
    from fastapi.testclient import TestClient

    # Compras o RH: tienen otros permisos, pero no `tablero.ver`.
    sin_permiso = cliente_con(P.REPORTES_CONSUMO, P.INVENTARIO_VER, almacen="KEP")
    r = sin_permiso.get(ruta)
    assert r.status_code == 403
    assert r.json()["codigo"] == "SIN_PERMISO"
    assert TestClient(app).get(ruta).status_code == 401


def test_TB_01_sin_almacenes_todos_no_expone_almacen_fuera_del_conjunto(cliente_con, datos):
    en_con = cliente_con(P.TABLERO_VER, almacen="CON")
    base = _ok(en_con, RESUMEN)
    assert {
        k: base["alcance"][k] for k in ("almacen_id", "nombre", "es_todos", "puede_elegir")
    } == {
        "almacen_id": _almacen_id(datos, "CON"),
        "nombre": datos.almacen("CON").nombre,
        "es_todos": False,
        "puede_elegir": False,
    }

    articulo = datos.articulo("Artículo del tablero TB-01")
    datos.existencia(datos.ub_almacen("MID"), articulo, 7)
    datos.existencia(datos.ub_almacen("CON"), articulo, 5)

    pedido_a_mid = _ok(en_con, RESUMEN, almacen_id=_almacen_id(datos, "MID"))
    assert pedido_a_mid["existencias"] == {"unidades": 0, "articulos": 0}
    despues = _ok(en_con, RESUMEN)
    assert despues["existencias"]["unidades"] == base["existencias"]["unidades"] + 5
    assert despues["existencias"]["articulos"] == base["existencias"]["articulos"] + 1


def test_TB_01_con_almacenes_todos_ve_todo_y_puede_elegir_uno(cliente_con, datos):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    base_todos = _ok(todos, RESUMEN)
    base_mid = _ok(todos, RESUMEN, almacen_id=_almacen_id(datos, "MID"))
    assert {
        k: base_todos["alcance"][k] for k in ("almacen_id", "nombre", "es_todos", "puede_elegir")
    } == {
        "almacen_id": None,
        "nombre": "Todos los almacenes",
        "es_todos": True,
        "puede_elegir": True,
    }
    assert base_mid["alcance"]["almacen_id"] == _almacen_id(datos, "MID")
    assert base_mid["alcance"]["es_todos"] is False

    articulo = datos.articulo("Artículo del tablero TB-01 todos")
    datos.existencia(datos.ub_almacen("MID"), articulo, 7)
    datos.existencia(datos.ub_almacen("KEP"), articulo, 3)

    despues_todos = _ok(todos, RESUMEN)
    despues_mid = _ok(todos, RESUMEN, almacen_id=_almacen_id(datos, "MID"))
    assert despues_todos["existencias"]["unidades"] == base_todos["existencias"]["unidades"] + 10
    assert despues_mid["existencias"]["unidades"] == base_mid["existencias"]["unidades"] + 7


def test_TB_01_un_almacen_que_no_existe_es_404_y_sin_almacen_el_tablero_llega_vacio(
    cliente_con,
):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    r = todos.get(RESUMEN, params={"almacen_id": str(uuid.uuid4())})
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
    assert todos.get(CONSUMO, params={"almacen_id": str(uuid.uuid4())}).status_code == 404

    sin_almacen = cliente_con(P.TABLERO_VER)
    cuerpo = _ok(sin_almacen, RESUMEN)
    assert cuerpo["alcance"]["almacen_id"] is None
    assert cuerpo["alcance"]["es_todos"] is False
    assert cuerpo["alcance"]["nombre"] == "Sin almacén asignado"
    assert cuerpo["existencias"] == {"unidades": 0, "articulos": 0}
    for campo in (
        "resguardo_equipo_importante",
        "sin_existencia",
        "traspasos_en_transito",
        "entregas_hoy",
        "solicitudes_compra_abiertas",
    ):
        assert cuerpo[campo] == 0, campo
    assert cuerpo["inspecciones_por_vencer"] is None
    vacio = _ok(sin_almacen, CONSUMO)
    assert vacio["barras"] == [] and vacio["sin_registros"] is True


def test_TB_01_sin_existencia_cuenta_solo_lo_que_alguna_vez_tuvo_existencia(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    base = _ok(en_kep, RESUMEN)

    agotado = datos.articulo("Agotado del tablero")
    datos.existencia(datos.ub_almacen("KEP"), agotado, 0)
    datos.articulo("Nunca entró al tablero")  # sin fila de existencia: no cuenta
    con_cantidad = datos.articulo("Con cantidad del tablero")
    datos.existencia(datos.ub_almacen("KEP"), con_cantidad, 4)

    despues = _ok(en_kep, RESUMEN)
    assert despues["sin_existencia"] == base["sin_existencia"] + 1
    assert despues["existencias"]["articulos"] == base["existencias"]["articulos"] + 1


def test_TB_01_traspasos_en_transito_cuentan_de_ida_y_de_venida(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    en_con = cliente_con(P.TABLERO_VER, almacen="CON")
    en_mid = cliente_con(P.TABLERO_VER, almacen="MID")
    base = {
        c: _ok(x, RESUMEN)["traspasos_en_transito"]
        for c, x in (("KEP", en_kep), ("CON", en_con), ("MID", en_mid))
    }

    traspaso = datos.vale("TRASPASO", "KEP", estado="EN_TRANSITO")
    traspaso.destino_almacen_id = datos.almacen("CON").id
    entregado = datos.vale("TRASPASO", "KEP", estado="RECIBIDO")  # ya recibido: no cuenta
    entregado.destino_almacen_id = datos.almacen("CON").id
    datos.session.flush()

    assert _ok(en_kep, RESUMEN)["traspasos_en_transito"] == base["KEP"] + 1
    assert _ok(en_con, RESUMEN)["traspasos_en_transito"] == base["CON"] + 1
    assert _ok(en_mid, RESUMEN)["traspasos_en_transito"] == base["MID"]


def test_TB_01_solicitudes_de_compra_abiertas_son_las_pendientes_y_en_compra(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    base = _ok(en_kep, RESUMEN)["solicitudes_compra_abiertas"]
    solicitante = datos.usuario("almacenista")
    for estado in ("PENDIENTE", "EN_COMPRA", "RECHAZADA", "INGRESADA"):
        datos.session.add(
            SolicitudCompra(
                id_cliente=nuevo_id(),
                huella_cuerpo="x" * 64,
                folio=f"KEP-SOL-T{uuid.uuid4().hex[:8]}",
                almacen_id=datos.almacen("KEP").id,
                solicitante_id=solicitante.id,
                descripcion="Disco de corte",
                cantidad=2,
                motivo="Obra",
                estado=estado,
            )
        )
    datos.session.flush()
    assert _ok(en_kep, RESUMEN)["solicitudes_compra_abiertas"] == base + 2


def test_TB_01_resguardo_de_equipo_importante_cuenta_piezas_entregadas_desde_el_almacen(
    cliente_con, datos
):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    en_con = cliente_con(P.TABLERO_VER, almacen="CON")
    base_kep = _ok(en_kep, RESUMEN)["resguardo_equipo_importante"]
    base_con = _ok(en_con, RESUMEN)["resguardo_equipo_importante"]

    arnes = datos.articulo("Arnés del tablero", control="PIEZA")
    juan = datos.trabajador()
    pieza = datos.pieza(arnes, datos.ub_almacen("KEP"))
    datos.entrega(juan, arnes, almacen="KEP", pieza=pieza)
    # Un retornable por cantidad en manos del trabajador no es equipo «por pieza».
    martillo = datos.articulo("Martillo del tablero", control="CANTIDAD")
    datos.entrega(juan, martillo, almacen="KEP", cantidad=2)

    assert _ok(en_kep, RESUMEN)["resguardo_equipo_importante"] == base_kep + 1
    assert _ok(en_con, RESUMEN)["resguardo_equipo_importante"] == base_con


def test_TB_01_inspecciones_por_vencer_cuenta_de_hoy_a_siete_dias_sin_las_vencidas(
    cliente_con, datos
):
    en_kep = cliente_con(P.TABLERO_VER, P.INSPECCIONES_VER, almacen="KEP")
    en_con = cliente_con(P.TABLERO_VER, P.INSPECCIONES_VER, almacen="CON")
    base_kep = _ok(en_kep, RESUMEN)["inspecciones_por_vencer"]
    base_con = _ok(en_con, RESUMEN)["inspecciones_por_vencer"]

    arnes = datos.articulo("Arnés con inspección del tablero", control="PIEZA")
    arnes.requiere_inspeccion = True
    ub = datos.ub_almacen("KEP")
    hoy = hoy_mx()
    datos.pieza(arnes, ub, vigente_hasta=hoy)  # hoy: cuenta
    datos.pieza(arnes, ub, vigente_hasta=hoy + timedelta(days=7))  # en 7 días: cuenta
    datos.pieza(arnes, ub, vigente_hasta=hoy + timedelta(days=8))  # todavía falta
    datos.pieza(arnes, ub, vigente_hasta=hoy - timedelta(days=1))  # ya vencida
    datos.pieza(arnes, ub, vigente_hasta=hoy + timedelta(days=2), estado="NO_APTO")
    datos.session.flush()

    assert _ok(en_kep, RESUMEN)["inspecciones_por_vencer"] == base_kep + 2
    assert _ok(en_con, RESUMEN)["inspecciones_por_vencer"] == base_con


# ------------------------------------------------------------------------------------ TB-03


def test_TB_03_entregas_de_hoy_usan_el_dia_de_mexico_y_no_cuentan_canceladas(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    base = _ok(en_kep, RESUMEN)["entregas_hoy"]
    hoy = hoy_mx()
    inicio_hoy, fin_hoy = rango_utc(hoy, hoy)
    guante = _consumible(datos)
    juan = datos.trabajador()

    datos.entrega(juan, guante, creado_en=inicio_hoy + timedelta(minutes=1))  # cuenta
    datos.entrega(juan, guante, creado_en=fin_hoy - timedelta(minutes=1))  # cuenta
    datos.entrega(juan, guante, creado_en=inicio_hoy - timedelta(minutes=1))  # ayer en México
    cancelada = datos.entrega(juan, guante, creado_en=inicio_hoy + timedelta(minutes=2))
    datos.cancelar(cancelada)
    datos.entrega(juan, guante, almacen="CON", creado_en=inicio_hoy + timedelta(minutes=3))

    assert _ok(en_kep, RESUMEN)["entregas_hoy"] == base + 2


def test_TB_03_el_dia_hasta_entra_completo_en_la_hora_de_mexico(cliente_con, datos):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    guante = _consumible(datos)
    categoria = _categoria(datos, guante)
    juan = datos.trabajador()
    # 23:30 en México del día `DIA` es ya el día siguiente en UTC.
    tarde = _momento(DIA, 23 * 60 + 30)
    assert tarde.date() > DIA
    datos.entrega(juan, guante, cantidad=4, creado_en=tarde)

    en_el_dia = _ok(todos, CONSUMO, desde=str(DIA), hasta=str(DIA), categoria_id=str(categoria.id))
    assert en_el_dia["total_general"] == 4
    assert en_el_dia["desde"] == str(DIA) and en_el_dia["hasta"] == str(DIA)
    dia_siguiente = DIA + timedelta(days=1)
    despues = _ok(
        todos,
        CONSUMO,
        desde=str(dia_siguiente),
        hasta=str(dia_siguiente),
        categoria_id=str(categoria.id),
    )
    assert despues["sin_registros"] is True and despues["total_general"] == 0
    antes = DIA - timedelta(days=1)
    assert (
        _ok(todos, CONSUMO, desde=str(antes), hasta=str(antes), categoria_id=str(categoria.id))[
            "sin_registros"
        ]
        is True
    )


def test_TB_03_rango_invertido_largo_o_mal_escrito_y_limite_fuera_de_rango_son_422(cliente_con):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    hoy = hoy_mx()
    casos = [
        {"desde": str(hoy), "hasta": str(hoy - timedelta(days=1))},
        {"desde": str(hoy - timedelta(days=400)), "hasta": str(hoy)},
        {"desde": "10/10/2026"},
        {"limite": 0},
        {"limite": 21},
    ]
    for parametros in casos:
        r = todos.get(CONSUMO, params=parametros)
        assert r.status_code == 422, parametros
        assert r.json()["codigo"] == "DATOS_INVALIDOS", parametros
    # El límite del rango (366 días) todavía se acepta.
    assert (
        todos.get(
            CONSUMO, params={"desde": str(hoy - timedelta(days=366)), "hasta": str(hoy)}
        ).status_code
        == 200
    )
    assert todos.get(CONSUMO, params={"categoria_id": str(uuid.uuid4())}).status_code == 404


# ------------------------------------------------------------------------------------ TB-02


def test_TB_02_lo_usado_es_lo_entregado_neto_de_cancelaciones_y_ordenado(cliente_con, datos):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    disco = _consumible(datos, "Disco TB-02")
    categoria = _categoria(datos, disco)
    lija = _consumible(datos, "Lija TB-02", categoria=categoria)
    guante = _consumible(datos, "Guante TB-02", categoria=categoria)
    juan, ana = datos.trabajador(), datos.trabajador()
    momento = _momento(DIA)

    datos.entrega(juan, disco, cantidad=6, creado_en=momento)
    datos.entrega(ana, disco, cantidad=4, creado_en=momento)
    datos.entrega(juan, lija, cantidad=9, creado_en=momento)
    cancelada = datos.entrega(juan, guante, cantidad=50, creado_en=momento)
    datos.cancelar(cancelada, creado_en=momento + timedelta(minutes=5))
    datos.entrega(ana, guante, cantidad=2, creado_en=momento)

    cuerpo = _ok(
        todos, CONSUMO, desde=str(DIA), hasta=str(DIA), categoria_id=str(categoria.id), limite=2
    )
    assert [(b["articulo"], b["total"]) for b in cuerpo["barras"]] == [
        ("Disco TB-02", 10),
        ("Lija TB-02", 9),
    ]
    assert cuerpo["otros"] == {"total": 2, "articulos": 1}  # el guante; lo cancelado no suma
    assert cuerpo["total_general"] == 21
    assert cuerpo["categoria"] == {"id": str(categoria.id), "nombre": categoria.nombre}
    assert cuerpo["almacen"] is None
    assert cuerpo["limite"] == 2
    assert cuerpo["sin_registros"] is False
    assert all(b["por_almacen"] == [] for b in cuerpo["barras"])


def test_TB_02_el_uso_se_separa_por_categoria_y_cuenta_los_retornables_entregados(
    cliente_con, datos
):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    guante = _consumible(datos, "Guante separado TB-02")
    taladro = datos.articulo("Taladro separado TB-02", retornable=True)
    cat_guante, cat_taladro = _categoria(datos, guante), _categoria(datos, taladro)
    juan = datos.trabajador()
    momento = _momento(DIA)
    datos.entrega(juan, guante, cantidad=8, creado_en=momento)
    datos.entrega(juan, taladro, cantidad=3, creado_en=momento)
    cancelado = datos.entrega(juan, taladro, cantidad=5, creado_en=momento)
    datos.cancelar(cancelado)

    en_guantes = _ok(
        todos, CONSUMO, desde=str(DIA), hasta=str(DIA), categoria_id=str(cat_guante.id)
    )
    assert [(b["articulo"], b["total"]) for b in en_guantes["barras"]] == [
        ("Guante separado TB-02", 8)
    ]
    en_taladros = _ok(
        todos, CONSUMO, desde=str(DIA), hasta=str(DIA), categoria_id=str(cat_taladro.id)
    )
    assert [(b["articulo"], b["total"]) for b in en_taladros["barras"]] == [
        ("Taladro separado TB-02", 3)
    ]
    assert en_taladros["barras"][0]["categoria"]["id"] == str(cat_taladro.id)

    todas = _ok(todos, CONSUMO, desde=str(DIA), hasta=str(DIA), limite=20)
    por_nombre = {b["articulo"]: b for b in todas["barras"]}
    assert por_nombre["Guante separado TB-02"]["categoria"]["id"] == str(cat_guante.id)
    assert por_nombre["Taladro separado TB-02"]["categoria"]["id"] == str(cat_taladro.id)


def test_TB_02_separar_por_almacen_reparte_cada_barra_y_la_suma_es_su_total(cliente_con, datos):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    disco = _consumible(datos, "Disco por almacén TB-02")
    categoria = _categoria(datos, disco)
    juan = datos.trabajador()
    momento = _momento(DIA)
    datos.entrega(juan, disco, almacen="KEP", cantidad=3, creado_en=momento)
    datos.entrega(juan, disco, almacen="MID", cantidad=8, creado_en=momento)
    datos.entrega(juan, disco, almacen="CON", cantidad=5, creado_en=momento)
    base = {"desde": str(DIA), "hasta": str(DIA), "categoria_id": str(categoria.id)}

    separado = _ok(todos, CONSUMO, **base, separar_por_almacen="true")
    barra = separado["barras"][0]
    assert separado["separar_por_almacen"] is True
    assert barra["total"] == 16
    assert [p["total"] for p in barra["por_almacen"]] == [8, 5, 3]  # de mayor a menor
    assert sum(p["total"] for p in barra["por_almacen"]) == barra["total"]
    assert barra["por_almacen"][0]["almacen_id"] == _almacen_id(datos, "MID")

    junto = _ok(todos, CONSUMO, **base)
    assert junto["separar_por_almacen"] is False
    assert junto["barras"][0]["por_almacen"] == []
    assert junto["barras"][0]["total"] == 16

    # Con un almacén elegido el desglose no aplica, aunque se pida.
    en_mid = _ok(
        todos, CONSUMO, **base, almacen_id=_almacen_id(datos, "MID"), separar_por_almacen="true"
    )
    assert en_mid["separar_por_almacen"] is False
    assert en_mid["barras"][0]["total"] == 8
    assert en_mid["almacen"]["clave"] == "MID"


def test_TB_01_en_consumo_sin_almacenes_todos_no_cuenta_almacenes_ajenos(cliente_con, datos):
    en_kep = cliente_con(P.TABLERO_VER, almacen="KEP")
    disco = _consumible(datos, "Disco alcance TB-01")
    categoria = _categoria(datos, disco)
    juan = datos.trabajador()
    momento = _momento(DIA)
    datos.entrega(juan, disco, almacen="KEP", cantidad=3, creado_en=momento)
    datos.entrega(juan, disco, almacen="MID", cantidad=8, creado_en=momento)

    cuerpo = _ok(
        en_kep,
        CONSUMO,
        desde=str(DIA),
        hasta=str(DIA),
        categoria_id=str(categoria.id),
        almacen_id=_almacen_id(datos, "MID"),
        separar_por_almacen="true",
    )
    assert cuerpo["total_general"] == 0
    assert cuerpo["almacen"] is None
    assert cuerpo["separar_por_almacen"] is False
    assert cuerpo["barras"] == []
    propio = _ok(en_kep, CONSUMO, desde=str(DIA), hasta=str(DIA), categoria_id=str(categoria.id))
    assert propio["total_general"] == 3


def test_TB_02_la_suma_de_las_barras_coincide_con_el_reporte_de_consumo(cliente_con, datos):
    tablero = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    reporte = cliente_con(P.REPORTES_CONSUMO, P.ALMACENES_TODOS)
    disco = _consumible(datos, "Disco coincide TB-02")
    categoria = _categoria(datos, disco)
    lija = _consumible(datos, "Lija coincide TB-02", categoria=categoria)
    guante = _consumible(datos, "Guante coincide TB-02", categoria=categoria)
    juan, ana = datos.trabajador(), datos.trabajador()
    momento = _momento(DIA)
    datos.entrega(juan, disco, almacen="KEP", cantidad=7, creado_en=momento)
    datos.entrega(ana, disco, almacen="MID", cantidad=2, creado_en=momento)
    datos.entrega(juan, lija, almacen="KEP", cantidad=5, creado_en=momento)
    datos.entrega(ana, guante, almacen="CON", cantidad=1, creado_en=momento)
    datos.cancelar(datos.entrega(ana, lija, almacen="KEP", cantidad=30, creado_en=momento))

    for almacen in (None, "KEP"):
        filtros = {"desde": str(DIA), "hasta": str(DIA), "categoria_id": str(categoria.id)}
        if almacen:
            filtros["almacen_id"] = _almacen_id(datos, almacen)
        grafica = _ok(tablero, CONSUMO, **filtros, limite=1)
        informe = _ok(reporte, REPORTE_CONSUMO, **filtros)
        total_informe = sum(e["total"] for e in informe["elementos"])
        assert grafica["total_general"] == total_informe, almacen
        assert (
            sum(b["total"] for b in grafica["barras"]) + grafica["otros"]["total"] == total_informe
        )
        assert grafica["otros"]["articulos"] == len(informe["elementos"]) - 1


def test_TB_02_el_tablero_no_trae_costos_ni_datos_personales(cliente_con, datos):
    todos = cliente_con(P.TABLERO_VER, P.ALMACENES_TODOS)
    articulo = datos.articulo("Disco reservado TB-02", retornable=False, costo="987654.32")
    categoria = _categoria(datos, articulo)
    juan = datos.trabajador(curp="CURP9999999999999X", nss="77777777777")
    datos.entrega(juan, articulo, cantidad=1, creado_en=_momento(DIA))

    crudos = [
        todos.get(RESUMEN).text,
        todos.get(
            CONSUMO,
            params={"desde": str(DIA), "hasta": str(DIA), "categoria_id": str(categoria.id)},
        ).text,
    ]
    for texto in crudos:
        for prohibido in ("987654", "costo", "curp", "CURP9999", "nss", "7777777", juan.nombre):
            assert prohibido not in texto, prohibido
