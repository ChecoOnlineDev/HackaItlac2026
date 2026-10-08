"""FEAT-011, sección C: trazabilidad (SG-01 a SG-04 y SG-06).

Seguimiento con la pestaña «Por cantidad», la ficha del artículo con «Quién lo tiene», la línea
de tiempo de la pieza, el permiso `resguardo.ver`, la tarjeta del inicio y el aviso de una pieza
de alto valor en manos de un trabajador dado de baja o con el contrato vencido. Los datos se
insertan con `datos`; los usuarios se crean con exactamente los permisos que cada prueba declara.
"""

from datetime import timedelta

from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.catalogo.models import Categoria
from app.modulos.movimientos.models import Existencia
from app.modulos.trabajadores.models import EstadoTrabajador

PIEZAS = "/api/seguimiento/piezas"
CANTIDAD = "/api/seguimiento/cantidad"
RESUMEN = "/api/tablero/resumen"

BASE = (P.REPORTES_EXISTENCIAS, P.TRABAJADORES_VER)


def _ok(cliente, ruta: str, **params) -> dict:
    r = cliente.get(ruta, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _admin(cliente_con):
    return cliente_con(*BASE, P.ALMACENES_TODOS)


def _categoria_alto_valor(datos) -> Categoria:
    """La categoría de la semilla (o una con el mismo nombre si la base de pruebas no la trae)."""
    existente = datos.session.scalar(
        select(Categoria).where(Categoria.nombre == "Equipo de alto valor")
    )
    if existente is not None:
        return existente
    categoria = Categoria(
        nombre="Equipo de alto valor", tipo="HERRAMIENTA", control="PIEZA", retornable=True
    )
    datos.session.add(categoria)
    datos.session.flush()
    return categoria


# ---------------------------------------------------------------------------- SG-01


def test_SG_01_seguimiento_por_cantidad_muestra_trabajador_cantidad_fecha_y_folio(
    cliente_con, datos
):
    flexometro = datos.articulo("Flexómetro SG01", control="CANTIDAD")
    juan = datos.trabajador("Juan Cantidad")
    vale = datos.entrega(juan, flexometro, almacen="KEP", cantidad=3)

    cuerpo = _ok(_admin(cliente_con), CANTIDAD, q="Flexómetro SG01")

    assert cuerpo["total"] == 1
    renglon = cuerpo["elementos"][0]
    assert renglon["trabajador"]["nombre"] == "Juan Cantidad"
    assert renglon["articulo"]["nombre"] == "Flexómetro SG01"
    assert renglon["cantidad"] == 3
    assert renglon["desde"].endswith("Z")
    assert renglon["vale"]["folio"] == vale.folio
    assert renglon["almacen"]["clave"] == "KEP"
    assert cuerpo["resumen"] == {"renglones": 1, "unidades": 3, "articulos": 1, "trabajadores": 1}


def test_SG_01_sin_piezas_la_pestana_de_piezas_avisa_cuantos_articulos_hay_por_cantidad(
    cliente_con, datos
):
    flexometro = datos.articulo("Flexómetro SG01 aviso", control="CANTIDAD")
    datos.entrega(datos.trabajador("Ana Aviso"), flexometro, almacen="KEP", cantidad=2)

    cuerpo = _ok(_admin(cliente_con), PIEZAS, q="Flexómetro SG01 aviso")

    assert cuerpo["elementos"] == []
    assert cuerpo["resumen"]["articulos_por_cantidad"] == 1


def test_SG_01_una_devolucion_total_saca_el_renglon_de_la_lista(cliente_con, datos):
    cinta = datos.articulo("Cinta SG01 devuelta", control="CANTIDAD")
    luis = datos.trabajador("Luis Devuelve")
    datos.entrega(luis, cinta, almacen="KEP", cantidad=1)
    existencia = datos.session.get(Existencia, (datos.ub_trabajador(luis).id, cinta.id))
    existencia.cantidad = 0
    datos.session.flush()

    cuerpo = _ok(_admin(cliente_con), CANTIDAD, q="Cinta SG01 devuelta")

    assert cuerpo["total"] == 0 and cuerpo["sin_registros"] is True


def test_SG_01_el_csv_trae_los_mismos_renglones(cliente_con, datos):
    nivel = datos.articulo("Nivel SG01 csv", control="CANTIDAD")
    datos.entrega(datos.trabajador("Rosa Csv"), nivel, almacen="KEP", cantidad=4)

    r = _admin(cliente_con).get(CANTIDAD, params={"q": "Nivel SG01 csv", "formato": "csv"})

    assert r.status_code == 200
    assert "Rosa Csv" in r.content.decode("utf-8-sig")
    assert "text/csv" in r.headers["content-type"]


# ---------------------------------------------------------------------------- SG-04


def test_SG_04_AC_06_el_almacenista_ve_solo_lo_entregado_desde_su_almacen(cliente_con, datos):
    martillo = datos.articulo("Martillo SG04", control="CANTIDAD")
    datos.entrega(datos.trabajador("Pedro Midrex"), martillo, almacen="MID", cantidad=2)
    datos.entrega(datos.trabajador("Pablo Contratistas"), martillo, almacen="CON", cantidad=5)

    midrex = cliente_con(P.RESGUARDO_VER, P.TRABAJADORES_VER, almacen="MID")
    cuerpo = _ok(midrex, CANTIDAD, q="Martillo SG04")

    assert [e["trabajador"]["nombre"] for e in cuerpo["elementos"]] == ["Pedro Midrex"]
    assert cuerpo["resumen"]["unidades"] == 2
    todos = _ok(_admin(cliente_con), CANTIDAD, q="Martillo SG04")
    assert todos["total"] == 2


def test_SG_04_AC_06_pedir_el_almacen_de_otro_no_devuelve_nada(cliente_con, datos):
    martillo = datos.articulo("Martillo SG04 otro", control="CANTIDAD")
    datos.entrega(datos.trabajador("Pablo Otro"), martillo, almacen="CON", cantidad=5)
    midrex = cliente_con(P.RESGUARDO_VER, P.TRABAJADORES_VER, almacen="MID")

    cuerpo = _ok(midrex, CANTIDAD, almacen_id=str(datos.almacen("CON").id))

    assert cuerpo["elementos"] == [] and cuerpo["total"] == 0


def test_SG_04_resguardo_ver_basta_sin_reportes_existencias_y_sin_ninguno_es_403(cliente_con):
    solo_resguardo = cliente_con(
        P.RESGUARDO_VER, P.TRABAJADORES_VER, P.INVENTARIO_VER, almacen="MID"
    )
    assert solo_resguardo.get(PIEZAS).status_code == 200
    assert solo_resguardo.get(CANTIDAD).status_code == 200

    solo_reporte = cliente_con(P.REPORTES_EXISTENCIAS, almacen="MID")
    assert solo_reporte.get(PIEZAS).status_code == 200
    assert solo_reporte.get(CANTIDAD).status_code == 200

    ninguno = cliente_con(P.CATALOGO_VER, almacen="MID")
    assert ninguno.get(PIEZAS).status_code == 403
    assert ninguno.get(CANTIDAD).status_code == 403
    assert ninguno.get(CANTIDAD, params={"formato": "csv"}).status_code == 403


def test_SG_04_la_tarjeta_alto_valor_fuera_solo_llega_con_resguardo_ver(cliente_con, datos):
    categoria = _categoria_alto_valor(datos)
    detector = datos.articulo("Detector SG04", control="PIEZA", categoria=categoria)
    pieza = datos.pieza(detector, datos.ub_almacen("KEP"), codigo="SG04-DET")
    juan = datos.trabajador("Juan Tarjeta")

    con = cliente_con(P.TABLERO_VER, P.INVENTARIO_VER, P.RESGUARDO_VER, P.ALMACENES_TODOS)
    sin = cliente_con(P.TABLERO_VER, P.INVENTARIO_VER, P.ALMACENES_TODOS)
    antes = _ok(con, RESUMEN)["alto_valor_fuera"]
    assert antes is not None
    assert _ok(sin, RESUMEN)["alto_valor_fuera"] is None

    datos.entrega(juan, detector, almacen="KEP", pieza=pieza)

    assert _ok(con, RESUMEN)["alto_valor_fuera"] == antes + 1
    assert _ok(sin, RESUMEN)["alto_valor_fuera"] is None


def test_SG_04_el_filtro_alto_valor_deja_solo_esas_piezas(cliente_con, datos):
    categoria = _categoria_alto_valor(datos)
    detector = datos.articulo("Detector SG04 filtro", control="PIEZA", categoria=categoria)
    taladro = datos.articulo("Taladro SG04 filtro", control="PIEZA")
    juan = datos.trabajador("Juan Filtro")
    datos.entrega(
        juan,
        detector,
        almacen="KEP",
        pieza=datos.pieza(detector, datos.ub_almacen("KEP"), codigo="SG04-F1"),
    )
    datos.entrega(
        juan,
        taladro,
        almacen="KEP",
        pieza=datos.pieza(taladro, datos.ub_almacen("KEP"), codigo="SG04-F2"),
    )

    cuerpo = _ok(_admin(cliente_con), PIEZAS, q="Juan Filtro", alto_valor="true")

    assert [e["codigo"] for e in cuerpo["elementos"]] == ["SG04-F1"]
    assert cuerpo["elementos"][0]["alto_valor"] is True


# ---------------------------------------------------------------------------- SG-02


def test_SG_02_la_ficha_de_un_articulo_por_cantidad_trae_cantidad_fecha_y_folio(cliente_con, datos):
    cinta = datos.articulo("Cinta SG02", control="CANTIDAD")
    vale = datos.entrega(datos.trabajador("Marta Ficha"), cinta, almacen="KEP", cantidad=2)

    ficha = _ok(cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS), f"/api/articulos/{cinta.id}")

    (poseedor,) = ficha["en_posesion"]
    assert poseedor["nombre"] == "Marta Ficha"
    assert poseedor["cantidad"] == 2
    assert poseedor["folio"] == vale.folio and poseedor["vale_id"] == str(vale.id)
    assert poseedor["desde"].endswith("Z")
    assert poseedor["piezas"] == []


def test_SG_02_en_un_articulo_por_pieza_cada_pieza_trae_codigo_y_serie(cliente_con, datos):
    esmeril = datos.articulo("Esmeril SG02", control="PIEZA")
    juan = datos.trabajador("Juan Piezas")
    for codigo, serie in (("SG02-A", "SN-A"), ("SG02-B", "SN-B")):
        pieza = datos.pieza(esmeril, datos.ub_almacen("KEP"), codigo=codigo, serie=serie)
        datos.entrega(juan, esmeril, almacen="KEP", pieza=pieza)

    ficha = _ok(cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS), f"/api/articulos/{esmeril.id}")

    (poseedor,) = ficha["en_posesion"]
    assert poseedor["cantidad"] == 2
    assert [(z["codigo"], z["numero_serie"]) for z in poseedor["piezas"]] == [
        ("SG02-A", "SN-A"),
        ("SG02-B", "SN-B"),
    ]
    assert poseedor["folio"] is not None


def test_SG_02_AC_06_el_folio_de_un_vale_de_otro_almacen_no_se_muestra(cliente_con, datos):
    cinta = datos.articulo("Cinta SG02 ajena", control="CANTIDAD")
    datos.entrega(datos.trabajador("Marta Ajena"), cinta, almacen="CON", cantidad=1)

    ficha = _ok(cliente_con(P.CATALOGO_VER, almacen="MID"), f"/api/articulos/{cinta.id}")

    (poseedor,) = ficha["en_posesion"]
    assert poseedor["nombre"] == "Marta Ajena"
    assert poseedor["folio"] is None and poseedor["vale_id"] is None


# ---------------------------------------------------------------------------- SG-03


def test_SG_03_la_ficha_de_la_pieza_trae_quien_entrego_a_quien_vale_almacen_y_condicion(
    cliente_con, datos
):
    taladro = datos.articulo("Taladro SG03", control="PIEZA")
    pieza = datos.pieza(taladro, datos.ub_almacen("KEP"), codigo="SG03-T")
    juan = datos.trabajador("Juan Linea")
    vale = datos.entrega(juan, taladro, almacen="KEP", pieza=pieza, responsable="almacenista")

    ficha = _ok(cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS), f"/api/piezas/{pieza.id}")

    (movimiento,) = [h for h in ficha["historial"] if h["tipo"] == "MOVIMIENTO"]
    assert movimiento["folio"] == vale.folio and movimiento["vale_id"] == str(vale.id)
    assert movimiento["responsable"] == datos.usuario("almacenista").nombre
    assert movimiento["trabajador"] == "Juan Linea"
    assert movimiento["trabajador_id"] == str(juan.id)
    assert movimiento["almacen"] == datos.almacen("KEP").nombre
    assert "condicion" in movimiento


def test_SG_03_AC_06_el_vale_de_otro_almacen_no_nombra_el_almacen(cliente_con, datos):
    taladro = datos.articulo("Taladro SG03 ajeno", control="PIEZA")
    pieza = datos.pieza(taladro, datos.ub_almacen("CON"), codigo="SG03-X")
    datos.entrega(datos.trabajador("Juan Ajeno"), taladro, almacen="CON", pieza=pieza)

    ficha = _ok(
        cliente_con(P.CATALOGO_VER, P.TRABAJADORES_VER, almacen="MID"), f"/api/piezas/{pieza.id}"
    )

    (movimiento,) = [h for h in ficha["historial"] if h["tipo"] == "MOVIMIENTO"]
    assert movimiento["almacen"] is None and movimiento["folio"] is None


# ---------------------------------------------------------------------------- SG-06


def _alto_valor_con(datos, trabajador, codigo: str):
    categoria = _categoria_alto_valor(datos)
    articulo = datos.articulo(f"Alto valor {codigo}", control="PIEZA", categoria=categoria)
    pieza = datos.pieza(articulo, datos.ub_almacen("KEP"), codigo=codigo)
    datos.entrega(trabajador, articulo, almacen="KEP", pieza=pieza)
    return pieza


def test_SG_06_pieza_de_alto_valor_con_un_trabajador_dado_de_baja_trae_aviso(cliente_con, datos):
    baja = datos.trabajador("Beto Baja", estado=EstadoTrabajador.INACTIVO)
    pieza = _alto_valor_con(datos, baja, "SG06-BAJA")
    cliente = cliente_con(*BASE, P.CATALOGO_VER, P.ALMACENES_TODOS)

    lista = _ok(cliente, PIEZAS, q="SG06-BAJA")
    ficha = _ok(cliente, f"/api/piezas/{pieza.id}")

    assert "dado de baja" in lista["elementos"][0]["aviso"]
    assert "Beto Baja" in ficha["aviso"]


def test_SG_06_pieza_de_alto_valor_con_contrato_vencido_trae_aviso(cliente_con, datos):
    vencido = datos.trabajador(
        "Vera Vencida", inicio=hoy_mx() - timedelta(days=200), fin=hoy_mx() - timedelta(days=5)
    )
    pieza = _alto_valor_con(datos, vencido, "SG06-VENC")
    cliente = cliente_con(*BASE, P.CATALOGO_VER, P.ALMACENES_TODOS)

    lista = _ok(cliente, PIEZAS, q="SG06-VENC")

    assert "contrato terminó" in lista["elementos"][0]["aviso"]
    assert "contrato terminó" in _ok(cliente, f"/api/piezas/{pieza.id}")["aviso"]


def test_SG_06_un_trabajador_vigente_o_una_pieza_comun_no_traen_aviso(cliente_con, datos):
    vigente = datos.trabajador("Vico Vigente")
    _alto_valor_con(datos, vigente, "SG06-OK")
    comun = datos.articulo("Llave SG06", control="PIEZA")
    baja = datos.trabajador("Beto Comun", estado=EstadoTrabajador.INACTIVO)
    datos.entrega(
        baja,
        comun,
        almacen="KEP",
        pieza=datos.pieza(comun, datos.ub_almacen("KEP"), codigo="SG06-COM"),
    )
    cliente = cliente_con(*BASE, P.CATALOGO_VER, P.ALMACENES_TODOS)

    assert _ok(cliente, PIEZAS, q="SG06-OK")["elementos"][0]["aviso"] is None
    assert _ok(cliente, PIEZAS, q="SG06-COM")["elementos"][0]["aviso"] is None
