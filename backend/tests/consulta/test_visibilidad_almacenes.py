"""AC-06 en la consulta: solo el Administrador (con `almacenes.todos`) ve lo de todos los almacenes.

Escaneo (C-02, C-03), búsqueda (C-06), ficha de pieza e historial (C-02), ficha de artículo (C-03)
y reportes (C-11). Un almacenista de Midrex no se entera de qué piezas ni qué inventario hay en
Kepler, Contratistas u otros almacenes. Lo que tiene un trabajador (su resguardo) sí se ve.

Los datos se insertan con el constructor `datos` (ver `conftest.py`). Los usuarios limitados se
crean con `cliente_con(..., almacen="MID")`; el global, con `almacenes.todos` y sin almacén.
"""

import uuid

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.models import TipoVale

ESCANEO = "/api/escaneo"
BUSQUEDA = "/api/busqueda"
PIEZAS = "/api/piezas"
ARTICULOS = "/api/articulos"

CATALOGO = (P.CATALOGO_VER, P.TRABAJADORES_VER, P.REPORTES_EXISTENCIAS)


def _escanear(cliente, codigo: str) -> dict:
    r = cliente.get(f"{ESCANEO}/{codigo}")
    assert r.status_code == 200, r.text
    return r.json()


def _midrex(cliente_con):
    return cliente_con(*CATALOGO, almacen="MID")


def _global(cliente_con):
    return cliente_con(*CATALOGO, P.ALMACENES_TODOS)


def _traspaso_en_transito(datos, pieza, articulo, origen="KEP", destino="MID"):
    """Un TRASPASO origen -> destino con la pieza en tránsito (lo que deja el motor, X-01)."""
    vale = datos.vale(TipoVale.TRASPASO, origen)
    vale.destino_almacen_id = datos.almacen(destino).id
    en_transito = datos.ub_virtual(UbicacionVirtual.EN_TRANSITO)
    datos.movimiento(vale, articulo, datos.ub_almacen(origen), en_transito, pieza=pieza)
    pieza.ubicacion_id = en_transito.id
    datos.session.flush()
    return vale


# ------------------------------------------------------------------------------ escaneo


def test_C_02_AC_06_escanear_una_pieza_de_otro_almacen_llega_como_desconocido(cliente_con, datos):
    taladro = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(taladro, datos.ub_almacen("KEP"), codigo="PZA-VIS-1")

    de_midrex = _escanear(_midrex(cliente_con), "PZA-VIS-1")
    inexistente = _escanear(_midrex(cliente_con), "PZA-NO-EXISTE")

    assert de_midrex == inexistente  # no se distingue de un código que no existe
    assert de_midrex["tipo"] == "DESCONOCIDO"
    # El Administrador sí la ve, con su ubicación.
    admin = _escanear(_global(cliente_con), "PZA-VIS-1")
    assert admin["tipo"] == "PIEZA" and admin["id"] == str(pieza.id)
    assert admin["resumen"]["ubicacion"]["almacen_clave"] == "KEP"


def test_C_02_AC_06_una_pieza_de_mi_almacen_si_se_ve(cliente_con, datos):
    taladro = datos.articulo("Taladro", control="PIEZA")
    datos.pieza(taladro, datos.ub_almacen("MID"), codigo="PZA-VIS-2")

    cuerpo = _escanear(_midrex(cliente_con), "PZA-VIS-2")

    assert cuerpo["tipo"] == "PIEZA"
    assert cuerpo["resumen"]["ubicacion"]["almacen_clave"] == "MID"


def test_C_02_AC_06_el_resguardo_de_un_trabajador_se_ve_aunque_la_haya_entregado_otro_almacen(
    cliente_con, datos
):
    juan = datos.trabajador("Juan Pérez")
    arnes = datos.articulo("Arnés", control="PIEZA")
    pieza = datos.pieza(arnes, datos.ub_almacen("KEP"), codigo="PZA-VIS-3")
    datos.entrega(juan, arnes, almacen="KEP", pieza=pieza)

    cuerpo = _escanear(_midrex(cliente_con), "PZA-VIS-3")

    assert cuerpo["tipo"] == "PIEZA"
    assert "Juan Pérez" in cuerpo["resumen"]["ubicacion"]["texto"]


def test_C_02_AC_06_una_pieza_en_transito_se_ve_en_el_origen_y_el_destino_y_no_en_otros(
    cliente_con, datos
):
    taladro = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(taladro, datos.ub_almacen("KEP"), codigo="PZA-VIS-4")
    _traspaso_en_transito(datos, pieza, taladro, origen="KEP", destino="MID")

    assert _escanear(cliente_con(*CATALOGO, almacen="MID"), "PZA-VIS-4")["tipo"] == "PIEZA"
    assert _escanear(cliente_con(*CATALOGO, almacen="KEP"), "PZA-VIS-4")["tipo"] == "PIEZA"
    assert _escanear(cliente_con(*CATALOGO, almacen="CON"), "PZA-VIS-4")["tipo"] == "DESCONOCIDO"


def test_C_02_AC_06_sin_almacen_asignado_ni_almacenes_todos_no_se_ve_ninguna_pieza(
    cliente_con, datos
):
    taladro = datos.articulo("Taladro", control="PIEZA")
    datos.pieza(taladro, datos.ub_almacen("KEP"), codigo="PZA-VIS-5")

    assert _escanear(cliente_con(*CATALOGO), "PZA-VIS-5")["tipo"] == "DESCONOCIDO"


def test_C_03_AC_06_el_articulo_muestra_la_existencia_solo_de_mi_almacen(cliente_con, datos):
    marro = datos.articulo("Marro", codigo="ART-VIS-1")
    datos.existencia(datos.ub_almacen("KEP"), marro, 7)
    datos.existencia(datos.ub_almacen("CON"), marro, 3)
    datos.existencia(datos.ub_almacen("MID"), marro, 2)

    de_midrex = _escanear(_midrex(cliente_con), "ART-VIS-1")["resumen"]["existencia_total"]
    de_admin = _escanear(_global(cliente_con), "ART-VIS-1")["resumen"]["existencia_total"]
    sin_almacen = _escanear(cliente_con(*CATALOGO), "ART-VIS-1")["resumen"]["existencia_total"]

    assert de_midrex == 2
    assert de_admin == 12
    assert sin_almacen == 0


# ------------------------------------------------------------------------------- búsqueda


def test_C_06_AC_06_la_busqueda_de_piezas_se_limita_al_almacen_del_usuario(cliente_con, datos):
    juan = datos.trabajador("Juan Pérez")
    detector = datos.articulo("Detector VISIBLE", control="PIEZA")
    en_kep = datos.pieza(detector, datos.ub_almacen("KEP"), serie="SERIE-VIS-KEP")
    en_mid = datos.pieza(detector, datos.ub_almacen("MID"), serie="SERIE-VIS-MID")
    con_juan = datos.pieza(detector, datos.ub_trabajador(juan), serie="SERIE-VIS-JUAN")

    de_midrex = _midrex(cliente_con).get(f"{BUSQUEDA}?q=Detector VISIBLE").json()
    de_admin = _global(cliente_con).get(f"{BUSQUEDA}?q=Detector VISIBLE").json()

    ids_midrex = {p["id"] for p in de_midrex["piezas"]["elementos"]}
    assert ids_midrex == {str(en_mid.id), str(con_juan.id)}
    assert de_midrex["piezas"]["total"] == 2
    assert str(en_kep.id) not in ids_midrex
    assert {p["id"] for p in de_admin["piezas"]["elementos"]} == {
        str(en_kep.id),
        str(en_mid.id),
        str(con_juan.id),
    }
    # El artículo del catálogo se ve igual: es catálogo maestro, no inventario.
    assert [a["nombre"] for a in de_midrex["articulos"]["elementos"]] == ["Detector VISIBLE"]


# ----------------------------------------------------------------------- ficha de la pieza


def test_C_02_AC_06_la_ficha_de_una_pieza_de_otro_almacen_responde_404_igual_que_una_inexistente(
    cliente_con, datos
):
    taladro = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(taladro, datos.ub_almacen("KEP"))
    midrex = _midrex(cliente_con)

    ajena = midrex.get(f"{PIEZAS}/{pieza.id}")
    inexistente = midrex.get(f"{PIEZAS}/{uuid.uuid4()}")

    assert ajena.status_code == inexistente.status_code == 404
    assert ajena.json() == inexistente.json()
    assert _global(cliente_con).get(f"{PIEZAS}/{pieza.id}").status_code == 200


def test_C_02_AC_06_el_historial_no_muestra_los_movimientos_de_otros_almacenes(cliente_con, datos):
    # La pieza nació en Kepler, se entregó en Kepler, la devolvió el trabajador en Midrex.
    juan = datos.trabajador("Juan Pérez")
    arnes = datos.articulo("Arnés", control="PIEZA")
    pieza = datos.pieza(arnes, None)
    entrada = datos.vale(TipoVale.ENTRADA, "KEP", responsable="compras")
    datos.movimiento(
        entrada,
        arnes,
        datos.ub_virtual(UbicacionVirtual.PROVEEDOR),
        datos.ub_almacen("KEP"),
        pieza=pieza,
    )
    datos.entrega(juan, arnes, almacen="KEP", pieza=pieza)
    devolucion = datos.vale(TipoVale.DEVOLUCION, "MID", responsable="alm_mid", trabajador=juan)
    datos.movimiento(
        devolucion, arnes, datos.ub_trabajador(juan), datos.ub_almacen("MID"), pieza=pieza
    )
    pieza.ubicacion_id = datos.ub_almacen("MID").id
    datos.session.flush()

    de_midrex = _midrex(cliente_con).get(f"{PIEZAS}/{pieza.id}").json()["historial"]
    de_admin = _global(cliente_con).get(f"{PIEZAS}/{pieza.id}").json()["historial"]

    assert len(de_admin) == 3
    # Sin la entrada a Kepler; la entrega a Juan se ve (es su resguardo) sin nombrar el almacén.
    assert [h["tipo_vale"] for h in de_midrex] == [TipoVale.DEVOLUCION, TipoVale.ENTREGA]
    entrega = de_midrex[1]
    assert entrega["origen"] == "Otro almacén" and "KEP" not in str(entrega)
    assert entrega["folio"] is None and entrega["vale_id"] is None
    assert "Kepler" not in str(de_midrex)


def test_C_02_AC_06_el_traspaso_que_llega_a_mi_almacen_se_ve_completo_en_el_historial(
    cliente_con, datos
):
    taladro = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(taladro, None)
    vale = _traspaso_en_transito(datos, pieza, taladro, origen="KEP", destino="MID")
    assert vale is not None

    historial = _midrex(cliente_con).get(f"{PIEZAS}/{pieza.id}").json()["historial"]

    assert len(historial) == 1 and "KEP" in historial[0]["origen"]


# --------------------------------------------------------------------- ficha del artículo


def test_C_03_AC_06_la_ficha_del_articulo_trae_las_existencias_solo_de_mi_almacen(
    cliente_con, datos
):
    marro = datos.articulo("Marro")
    datos.existencia(datos.ub_almacen("KEP"), marro, 7)
    datos.existencia(datos.ub_almacen("MID"), marro, 2)

    de_midrex = _midrex(cliente_con).get(f"{ARTICULOS}/{marro.id}").json()
    de_admin = _global(cliente_con).get(f"{ARTICULOS}/{marro.id}").json()

    assert [e["clave"] for e in de_midrex["existencias"]] == ["MID"]
    assert [e["cantidad"] for e in de_midrex["existencias"]] == [2]
    assert [e["clave"] for e in de_admin["existencias"]] == ["KEP", "MID"]


def test_C_03_AC_06_la_ficha_del_articulo_muestra_el_resguardo_de_los_trabajadores(
    cliente_con, datos
):
    juan = datos.trabajador("Juan Pérez")
    casco = datos.articulo("Casco")
    datos.existencia(datos.ub_almacen("KEP"), casco, 5)
    datos.entrega(juan, casco, almacen="KEP", cantidad=1)

    ficha = _midrex(cliente_con).get(f"{ARTICULOS}/{casco.id}").json()

    assert ficha["existencias"] == []  # nada en Midrex
    assert [(p["nombre"], p["cantidad"]) for p in ficha["en_posesion"]] == [("Juan Pérez", 1)]


# ---------------------------------------------------------------------------- reportes


def test_C_11_AC_06_el_reporte_de_existencias_solo_trae_el_almacen_del_usuario(cliente_con, datos):
    marro = datos.articulo("Marro")
    datos.existencia(datos.ub_almacen("KEP"), marro, 7)
    datos.existencia(datos.ub_almacen("MID"), marro, 2)

    de_midrex = _midrex(cliente_con).get("/api/reportes/existencias").json()
    pidiendo_kepler = _midrex(cliente_con).get(
        f"/api/reportes/existencias?almacen_id={datos.almacen('KEP').id}"
    )

    assert {e["almacen_clave"] for e in de_midrex["elementos"]} == {"MID"}
    assert pidiendo_kepler.json()["elementos"] == []
