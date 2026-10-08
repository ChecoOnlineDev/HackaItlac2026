"""C-13 Seguimiento de piezas: dónde está cada pieza, quién la tiene, desde cuándo y con qué vale.

`GET /api/seguimiento/piezas` (permiso `reportes.existencias`). El alcance es el de la ficha de la
pieza (AC-06): solo quien tiene `almacenes.todos` ve todas; los demás, su almacén, el resguardo de
los trabajadores y el tránsito desde o hacia su almacén. Los datos se insertan con `datos`.
"""

from datetime import timedelta

from sqlalchemy import event

from app.core.tiempo import ahora_utc
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.models import TipoVale

RUTA = "/api/seguimiento/piezas"

BASE = (P.REPORTES_EXISTENCIAS, P.TRABAJADORES_VER)


def _admin(cliente_con):
    return cliente_con(*BASE, P.ALMACENES_TODOS)


def _supervisor(cliente_con, almacen="MID"):
    return cliente_con(*BASE, almacen=almacen)


def _listar(cliente, **params) -> dict:
    r = cliente.get(RUTA, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _codigos(cuerpo: dict) -> set[str]:
    return {e["codigo"] for e in cuerpo["elementos"]}


def _en_transito(datos, pieza, articulo, origen="KEP", destino="MID"):
    """Un TRASPASO origen -> destino con la pieza en tránsito (lo que deja el motor, X-01)."""
    vale = datos.vale(TipoVale.TRASPASO, origen)
    vale.destino_almacen_id = datos.almacen(destino).id
    en_transito = datos.ub_virtual(UbicacionVirtual.EN_TRANSITO)
    datos.movimiento(vale, articulo, datos.ub_almacen(origen), en_transito, pieza=pieza)
    pieza.ubicacion_id = en_transito.id
    datos.session.flush()
    return vale


def _escenario(datos):
    """Piezas del artículo «Minipulidor SEG» en cinco lugares distintos."""
    art = datos.articulo("Minipulidor SEG", control="PIEZA")
    datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-KEP")
    datos.pieza(art, datos.ub_almacen("MID"), codigo="SEG-MID")
    datos.pieza(art, datos.ub_almacen("CON"), codigo="SEG-CON", estado="NO_APTO")
    a_mid = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-TRS-MID")
    a_con = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-TRS-CON")
    _en_transito(datos, a_mid, art, "KEP", "MID")
    _en_transito(datos, a_con, art, "KEP", "CON")
    trabajador = datos.trabajador("Juan Seguimiento")
    con_juan = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-JUAN")
    vale = datos.entrega(trabajador, art, almacen="KEP", pieza=con_juan)
    return art, trabajador, vale


# ------------------------------------------------------------------------------ permisos


def test_C_13_AC_01_un_almacenista_sin_el_permiso_recibe_403(cliente_con):
    cliente = cliente_con(P.CATALOGO_VER, P.VALES_VER, almacen="MID")
    assert cliente.get(RUTA).status_code == 403
    assert cliente.get(RUTA, params={"formato": "csv"}).status_code == 403


def test_C_13_sin_sesion_responde_401(client):
    assert client.get(RUTA).status_code == 401


def test_C_13_AC_06_sin_almacen_asignado_ni_almacenes_todos_no_ve_nada(cliente_con, datos):
    _escenario(datos)
    cliente = cliente_con(*BASE)
    cuerpo = _listar(cliente)
    assert cuerpo["elementos"] == [] and cuerpo["total"] == 0
    assert cuerpo["resumen"]["total"] == 0
    assert cliente.get(RUTA, params={"formato": "csv"}).status_code == 200


# ------------------------------------------------------------------------------- alcance


def test_C_13_AC_06_el_administrador_ve_todas_las_piezas(cliente_con, datos):
    _escenario(datos)

    cuerpo = _listar(_admin(cliente_con), q="Minipulidor SEG")

    assert _codigos(cuerpo) == {
        "SEG-KEP",
        "SEG-MID",
        "SEG-CON",
        "SEG-TRS-MID",
        "SEG-TRS-CON",
        "SEG-JUAN",
    }
    assert cuerpo["total"] == 6


def test_C_13_AC_06_el_supervisor_de_midrex_ve_solo_lo_de_su_almacen_y_su_transito(
    cliente_con, datos
):
    _escenario(datos)

    cuerpo = _listar(_supervisor(cliente_con, "MID"), q="Minipulidor SEG")

    # Las suyas, la que le llega en tránsito y lo que tiene Juan (el resguardo se ve completo).
    # No ve la de Kepler ni la de Contratistas ni el tránsito de Kepler a Contratistas.
    assert _codigos(cuerpo) == {"SEG-MID", "SEG-TRS-MID", "SEG-JUAN"}
    assert cuerpo["resumen"]["total"] == 3


def test_C_13_AC_06_sin_ver_trabajadores_no_aparecen_las_piezas_de_los_trabajadores(
    cliente_con, datos
):
    _escenario(datos)
    cliente = cliente_con(P.REPORTES_EXISTENCIAS, almacen="MID")

    cuerpo = _listar(cliente, q="Minipulidor SEG")

    assert _codigos(cuerpo) == {"SEG-MID", "SEG-TRS-MID"}


def test_C_13_AC_06_pedir_el_almacen_de_otro_no_devuelve_nada(cliente_con, datos):
    _escenario(datos)
    kep = datos.almacen("KEP")

    cuerpo = _listar(_supervisor(cliente_con, "MID"), almacen_id=str(kep.id))

    assert cuerpo["elementos"] == [] and cuerpo["resumen"]["total"] == 0


def test_C_13_el_filtro_de_almacen_del_administrador_incluye_su_transito(cliente_con, datos):
    _escenario(datos)
    con = datos.almacen("CON")

    cuerpo = _listar(_admin(cliente_con), q="Minipulidor SEG", almacen_id=str(con.id))

    assert _codigos(cuerpo) == {"SEG-CON", "SEG-TRS-CON"}


def test_C_13_AC_06_el_vale_de_otro_almacen_no_se_nombra(cliente_con, datos):
    _escenario(datos)

    cuerpo = _listar(_supervisor(cliente_con, "MID"), q="SEG-JUAN")

    (juan,) = cuerpo["elementos"]
    assert juan["ubicacion"]["tipo"] == "TRABAJADOR"  # la tiene un trabajador de Midrex
    assert juan["vale"] is None  # pero la entregó Kepler: sin folio ni enlace
    assert juan["desde"] is not None


# ------------------------------------------------------------------ dónde está y desde cuándo


def test_C_13_una_pieza_en_un_almacen_dice_en_cual(cliente_con, datos):
    _escenario(datos)

    (pieza,) = _listar(_admin(cliente_con), q="SEG-KEP")["elementos"]

    assert pieza["ubicacion"]["tipo"] == "ALMACEN"
    assert pieza["ubicacion"]["texto"].startswith("En ")
    assert pieza["ubicacion"]["almacen"]["clave"] == "KEP"
    assert pieza["ubicacion"]["trabajador"] is None


def test_C_13_la_pieza_de_un_trabajador_dice_quien_la_tiene_desde_cuando_y_con_que_vale(
    cliente_con, datos
):
    _, trabajador, vale = _escenario(datos)

    (pieza,) = _listar(_admin(cliente_con), q="SEG-JUAN")["elementos"]

    assert pieza["ubicacion"]["tipo"] == "TRABAJADOR"
    assert pieza["ubicacion"]["texto"] == "En resguardo de Juan Seguimiento"
    assert pieza["ubicacion"]["trabajador"] == {
        "id": str(trabajador.id),
        "numero_empleado": trabajador.numero_empleado,
        "nombre": "Juan Seguimiento",
    }
    assert pieza["vale"] == {"id": str(vale.id), "folio": vale.folio}
    assert pieza["desde"].endswith("Z")


def test_C_13_una_pieza_en_transito_dice_hacia_donde_va(cliente_con, datos):
    _escenario(datos)
    con = datos.almacen("CON")

    (pieza,) = _listar(_admin(cliente_con), q="SEG-TRS-CON")["elementos"]

    assert pieza["ubicacion"]["tipo"] == "TRANSITO"
    assert pieza["ubicacion"]["texto"] == f"En tránsito a {con.nombre}"
    assert pieza["ubicacion"]["almacen"]["clave"] == "CON"
    assert pieza["vale"]["folio"].startswith("KEP-TRA")


def test_C_13_desde_es_el_movimiento_que_la_dejo_ahi_no_el_primero(cliente_con, datos):
    art = datos.articulo("Taladro SEG", control="PIEZA")
    pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-DESDE")
    trabajador = datos.trabajador("Ana Desde")
    hace_diez = ahora_utc() - timedelta(days=10)
    hace_dos = ahora_utc() - timedelta(days=2)
    primero = datos.entrega(trabajador, art, pieza=pieza, creado_en=hace_diez)
    # Se devuelve y se entrega otra vez: cuenta la entrega más reciente.
    dev = datos.vale(TipoVale.DEVOLUCION, "KEP", trabajador=trabajador, creado_en=hace_diez)
    datos.movimiento(
        dev, art, datos.ub_trabajador(trabajador), datos.ub_almacen("KEP"), pieza=pieza
    )
    segundo = datos.entrega(trabajador, art, pieza=pieza, creado_en=hace_dos)

    (fila,) = _listar(_admin(cliente_con), q="SEG-DESDE")["elementos"]

    assert fila["vale"]["folio"] == segundo.folio != primero.folio


def test_C_13_la_cancelacion_de_una_devolucion_no_cambia_desde_cuando_la_tiene(cliente_con, datos):
    art = datos.articulo("Esmeril SEG", control="PIEZA")
    pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-CANC")
    trabajador = datos.trabajador("Beto Cancelación")
    entrega = datos.entrega(trabajador, art, pieza=pieza, creado_en=ahora_utc() - timedelta(days=9))
    dev = datos.vale(
        TipoVale.DEVOLUCION, "KEP", trabajador=trabajador, creado_en=ahora_utc() - timedelta(days=5)
    )
    datos.movimiento(
        dev, art, datos.ub_trabajador(trabajador), datos.ub_almacen("KEP"), pieza=pieza
    )
    datos.cancelar(dev, creado_en=ahora_utc() - timedelta(days=1))
    pieza.ubicacion_id = datos.ub_trabajador(trabajador).id
    datos.session.flush()

    (fila,) = _listar(_admin(cliente_con), q="SEG-CANC")["elementos"]

    assert fila["ubicacion"]["tipo"] == "TRABAJADOR"
    assert fila["vale"]["folio"] == entrega.folio


def test_C_13_la_inspeccion_vigente_se_calcula_con_su_fecha(cliente_con, datos):
    from app.core.tiempo import hoy_mx

    art = datos.articulo("Arnés SEG", control="PIEZA")
    datos.pieza(
        art, datos.ub_almacen("KEP"), codigo="SEG-VIG", vigente_hasta=hoy_mx() + timedelta(days=5)
    )
    datos.pieza(
        art, datos.ub_almacen("KEP"), codigo="SEG-VENC", vigente_hasta=hoy_mx() - timedelta(days=1)
    )

    filas = {e["codigo"]: e for e in _listar(_admin(cliente_con), q="Arnés SEG")["elementos"]}

    assert filas["SEG-VIG"]["inspeccion_vigente"] is True
    assert filas["SEG-VENC"]["inspeccion_vigente"] is False
    assert filas["SEG-VIG"]["estado_texto"] == "Apta"


# ------------------------------------------------------------------------------- filtros


def test_C_13_C_06_el_texto_busca_por_articulo_serie_codigo_y_trabajador(cliente_con, datos):
    art, trabajador, _ = _escenario(datos)
    pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-SERIE", serie="XQ-98765")
    admin = _admin(cliente_con)

    assert _codigos(_listar(admin, q="minipulidor seg")) >= {"SEG-KEP", "SEG-JUAN"}
    assert _codigos(_listar(admin, q="XQ-98765")) == {pieza.codigo}
    assert _codigos(_listar(admin, q="SEG-TRS-")) == {"SEG-TRS-MID", "SEG-TRS-CON"}
    assert _codigos(_listar(admin, q="Juan Seguimiento")) == {"SEG-JUAN"}
    assert _codigos(_listar(admin, q=trabajador.numero_empleado)) == {"SEG-JUAN"}
    # Varias palabras: todas deben coincidir.
    assert _codigos(_listar(admin, q="Minipulidor Juan")) == {"SEG-JUAN"}
    assert _listar(admin, q="Minipulidor zzzz-nada")["elementos"] == []


def test_C_13_una_busqueda_de_un_solo_caracter_no_busca_y_lo_dice(cliente_con, datos):
    _escenario(datos)

    cuerpo = _listar(_admin(cliente_con), q="m")

    assert cuerpo["elementos"] == [] and cuerpo["total"] == 0
    assert cuerpo["mensaje"] == "Escribe al menos dos caracteres para buscar."


def test_C_13_el_texto_no_interpreta_comodines(cliente_con, datos):
    _escenario(datos)

    assert _listar(_admin(cliente_con), q="%%")["elementos"] == []
    assert _listar(_admin(cliente_con), q="__")["elementos"] == []


def test_C_13_filtra_por_articulo_estado_y_ubicacion(cliente_con, datos):
    art, _, _ = _escenario(datos)
    otro = datos.articulo("Otro SEG", control="PIEZA")
    datos.pieza(otro, datos.ub_almacen("KEP"), codigo="SEG-OTRO")
    admin = _admin(cliente_con)

    assert _codigos(_listar(admin, articulo_id=str(otro.id))) == {"SEG-OTRO"}
    assert _codigos(_listar(admin, articulo_id=str(art.id), estado="NO_APTO")) == {"SEG-CON"}
    en_transito = _listar(admin, articulo_id=str(art.id), ubicacion="TRANSITO")
    assert _codigos(en_transito) == {"SEG-TRS-MID", "SEG-TRS-CON"}
    con_trabajador = _listar(admin, articulo_id=str(art.id), ubicacion="TRABAJADOR")
    assert _codigos(con_trabajador) == {"SEG-JUAN"}
    en_almacen = _listar(admin, articulo_id=str(art.id), ubicacion="ALMACEN")
    assert _codigos(en_almacen) == {"SEG-KEP", "SEG-MID", "SEG-CON"}
    combinado = _listar(admin, articulo_id=str(art.id), ubicacion="ALMACEN", estado="NO_APTO")
    assert _codigos(combinado) == {"SEG-CON"}


def test_C_13_un_valor_de_filtro_invalido_responde_422(cliente_con):
    admin = _admin(cliente_con)
    assert admin.get(RUTA, params={"estado": "ROTA"}).status_code == 422
    assert admin.get(RUTA, params={"ubicacion": "LUNA"}).status_code == 422
    assert admin.get(RUTA, params={"articulo_id": "no-es-uuid"}).status_code == 422


def test_C_13_el_orden_es_estable_por_articulo_y_codigo_y_se_pagina(cliente_con, datos):
    art = datos.articulo("Orden SEG", control="PIEZA")
    for n in (3, 1, 2, 5, 4):
        datos.pieza(art, datos.ub_almacen("KEP"), codigo=f"SEG-ORD-{n}")
    admin = _admin(cliente_con)

    todas = _listar(admin, q="Orden SEG")
    pagina_1 = _listar(admin, q="Orden SEG", pagina=1, tamano=2)
    pagina_3 = _listar(admin, q="Orden SEG", pagina=3, tamano=2)

    assert [e["codigo"] for e in todas["elementos"]] == [f"SEG-ORD-{n}" for n in (1, 2, 3, 4, 5)]
    assert [e["codigo"] for e in pagina_1["elementos"]] == ["SEG-ORD-1", "SEG-ORD-2"]
    assert [e["codigo"] for e in pagina_3["elementos"]] == ["SEG-ORD-5"]
    assert pagina_1["total"] == pagina_3["total"] == 5
    assert pagina_1["resumen"]["total"] == 5


# ------------------------------------------------------------------------------- resumen


def test_C_13_el_resumen_cuenta_por_lugar_y_estado(cliente_con, datos):
    art, _, _ = _escenario(datos)
    admin = _admin(cliente_con)

    resumen = _listar(admin, articulo_id=str(art.id))["resumen"]

    assert resumen == {
        "total": 6,
        "en_almacen": 3,
        "en_resguardo": 1,
        "en_transito": 2,
        "no_aptas": 1,
        "articulos_por_cantidad": 0,
    }


def test_C_13_el_resumen_ignora_el_estado_y_la_ubicacion_para_que_las_tarjetas_cambien_de_filtro(
    cliente_con, datos
):
    art, _, _ = _escenario(datos)

    cuerpo = _listar(_admin(cliente_con), articulo_id=str(art.id), ubicacion="TRANSITO")

    assert cuerpo["total"] == 2  # la lista, filtrada
    assert cuerpo["resumen"]["total"] == 6  # los conteos, de todo el artículo
    assert cuerpo["resumen"]["en_resguardo"] == 1


def test_C_13_el_resumen_del_supervisor_cuenta_solo_lo_que_ve(cliente_con, datos):
    art, _, _ = _escenario(datos)

    resumen = _listar(_supervisor(cliente_con, "MID"), articulo_id=str(art.id))["resumen"]

    assert resumen == {
        "total": 3,
        "en_almacen": 1,
        "en_resguardo": 1,
        "en_transito": 1,
        "no_aptas": 0,
        "articulos_por_cantidad": 0,
    }


def test_C_13_sin_piezas_el_listado_viene_vacio_con_mensaje_y_resumen_en_cero(cliente_con):
    cuerpo = _listar(_admin(cliente_con), q="Nada-que-exista-zzz")

    assert cuerpo["elementos"] == []
    assert cuerpo["sin_registros"] is True
    assert cuerpo["mensaje"] == "No hay registros con esos filtros."
    assert cuerpo["resumen"] == {
        "total": 0,
        "en_almacen": 0,
        "en_resguardo": 0,
        "en_transito": 0,
        "no_aptas": 0,
        "articulos_por_cantidad": 0,
    }


# --------------------------------------------------------------------------- csv y reservados


def test_C_13_el_csv_lleva_las_mismas_filas_y_neutraliza_formulas(cliente_con, datos):
    art = datos.articulo("=Peligro SEG", control="PIEZA")
    trabajador = datos.trabajador('=HYPERLINK("http://x")')
    pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-CSV", serie="+1234")
    datos.entrega(trabajador, art, pieza=pieza)
    datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-CSV-2")

    r = _admin(cliente_con).get(RUTA, params={"formato": "csv", "q": "Peligro SEG"})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    texto = r.content.decode("utf-8-sig")
    lineas = [linea for linea in texto.split("\r\n") if linea]
    assert len(lineas) == 3  # encabezado y dos piezas
    assert lineas[0].startswith("Código de la pieza,Número de serie")
    assert "'=Peligro SEG" in texto and "'+1234" in texto and "'=HYPERLINK" in texto
    for linea in lineas[1:]:
        assert not linea.startswith(("=", "+", "-", "@"))


def test_C_13_el_csv_respeta_el_alcance_del_supervisor(cliente_con, datos):
    _escenario(datos)

    r = _supervisor(cliente_con, "MID").get(RUTA, params={"formato": "csv", "q": "Minipulidor SEG"})

    texto = r.content.decode("utf-8-sig")
    assert "SEG-MID" in texto and "SEG-TRS-MID" in texto
    assert "SEG-KEP" not in texto and "SEG-CON" not in texto and "SEG-TRS-CON" not in texto


def test_C_13_RG_13_RG_12_no_filtra_curp_nss_ni_costos(cliente_con, datos):
    art = datos.articulo("Reservado SEG", control="PIEZA", costo="987.65")
    trabajador = datos.trabajador("Rosa Reservada", curp="ROPR800101MDFSZR09", nss="12345678901")
    pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo="SEG-RESERV")
    datos.entrega(trabajador, art, pieza=pieza)
    admin = _admin(cliente_con)

    for params in ({"q": "Rosa Reservada"}, {"q": "Rosa Reservada", "formato": "csv"}):
        r = admin.get(RUTA, params=params)
        assert r.status_code == 200
        assert "Rosa Reservada" in r.text
        for reservado in ("ROPR800101MDFSZR09", "12345678901", "987.65", "costo", "curp", "nss"):
            assert reservado.lower() not in r.text.lower(), reservado


# --------------------------------------------------------------------------- eficiencia


def test_C_13_el_listado_hace_pocas_consultas_aunque_haya_muchas_piezas(
    cliente_con, datos, session
):
    art = datos.articulo("Masivo SEG", control="PIEZA")
    trabajadores = [datos.trabajador(f"Masivo {n}") for n in range(5)]
    for n in range(60):
        pieza = datos.pieza(art, datos.ub_almacen("KEP"), codigo=f"SEG-MAS-{n:03d}")
        if n % 3 == 0:
            datos.entrega(trabajadores[n % 5], art, pieza=pieza)
    admin = _admin(cliente_con)
    consultas: list[str] = []

    def contar(conn, cursor, statement, *args):
        consultas.append(statement)

    motor = session.get_bind()
    event.listen(motor, "before_cursor_execute", contar)
    try:
        cuerpo = _listar(admin, q="Masivo SEG", tamano=100)
    finally:
        event.remove(motor, "before_cursor_execute", contar)

    assert cuerpo["total"] == 60 and len(cuerpo["elementos"]) == 60
    seguimiento = [c for c in consultas if "FROM pieza" in c]
    assert len(seguimiento) == 3  # el listado, el total y el resumen; ninguna por pieza
    assert len(consultas) <= 12  # con la sesión, el usuario y sus permisos
