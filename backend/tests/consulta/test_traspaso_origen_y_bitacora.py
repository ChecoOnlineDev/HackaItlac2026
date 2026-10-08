"""FEAT-011: escaneo y búsqueda con almacén de origen (TR-11) y bitácora del almacén (SG-05)."""

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.models import TipoVale

ESCANEO = "/api/escaneo"
BUSQUEDA = "/api/busqueda"
MOVIMIENTOS = "/api/reportes/movimientos"
USUARIOS = "/api/reportes/usuarios"


def _escanear(cliente, codigo: str, almacen_id=None) -> dict:
    params = {"almacen_id": str(almacen_id)} if almacen_id else {}
    r = cliente.get(f"{ESCANEO}/{codigo}", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _buscar(cliente, q: str, almacen_id=None) -> dict:
    params = {"q": q} | ({"almacen_id": str(almacen_id)} if almacen_id else {})
    r = cliente.get(BUSQUEDA, params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------------------- TR-11


def test_TR_11_el_escaneo_con_almacen_trae_lo_disponible_ahi_y_sin_existencia_sigue_siendo_x02(
    cliente_con, datos
):
    aqui = datos.articulo("Disponible aqui TR11")
    solo_en_con = datos.articulo("Solo en Contratistas TR11")
    datos.existencia(datos.ub_almacen("KEP"), aqui, 5)
    datos.existencia(datos.ub_almacen("CON"), solo_en_con, 3)
    kep = datos.almacen("KEP").id
    cliente = cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS, almacen="KEP")

    assert _escanear(cliente, aqui.codigo, kep)["resumen"]["disponible"] == 5
    assert _escanear(cliente, aqui.codigo)["resumen"]["disponible"] is None
    # Sin existencia en el origen: el código se identifica (no es «no existe»); el rechazo X-02
    # lo da el servidor al evaluar el traspaso.
    sin = _escanear(cliente, solo_en_con.codigo, kep)
    assert sin["tipo"] == "ARTICULO" and sin["resumen"]["disponible"] == 0


def test_TR_11_una_pieza_escaneada_dice_si_esta_en_el_almacen_de_origen(cliente_con, datos):
    detector = datos.articulo("Detector TR11", control="PIEZA")
    en_kep = datos.pieza(detector, datos.ub_almacen("KEP"), serie="TR11-KEP")
    en_con = datos.pieza(detector, datos.ub_almacen("CON"), serie="TR11-CON")
    kep = datos.almacen("KEP").id
    cliente = cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS, almacen="KEP")

    assert _escanear(cliente, en_kep.codigo, kep)["resumen"]["disponible"] == 1
    assert _escanear(cliente, en_con.codigo, kep)["resumen"]["disponible"] == 0


def test_TR_11_la_busqueda_con_almacen_ofrece_solo_lo_que_hay_en_ese_almacen(cliente_con, datos):
    aqui = datos.articulo("Cincel de busqueda TR11 A")
    alla = datos.articulo("Cincel de busqueda TR11 B")
    datos.existencia(datos.ub_almacen("KEP"), aqui, 7)
    datos.existencia(datos.ub_almacen("CON"), alla, 2)
    detector = datos.articulo("Cincel pieza TR11", control="PIEZA")
    p_kep = datos.pieza(detector, datos.ub_almacen("KEP"), serie="TR11-S-KEP")
    datos.pieza(detector, datos.ub_almacen("CON"), serie="TR11-S-CON")
    kep = datos.almacen("KEP").id
    cliente = cliente_con(P.CATALOGO_VER, P.ALMACENES_TODOS, almacen="KEP")

    sin_filtro = _buscar(cliente, "Cincel")
    assert {a["id"] for a in sin_filtro["articulos"]["elementos"]} >= {str(aqui.id), str(alla.id)}
    assert sin_filtro["articulos"]["elementos"][0]["disponible"] is None

    con_filtro = _buscar(cliente, "Cincel", kep)
    articulos = {a["id"]: a for a in con_filtro["articulos"]["elementos"]}
    assert str(aqui.id) in articulos and str(alla.id) not in articulos
    assert articulos[str(aqui.id)]["disponible"] == 7
    piezas = con_filtro["piezas"]["elementos"]
    assert [p["id"] for p in piezas] == [str(p_kep.id)] and piezas[0]["disponible"] == 1


def test_TR_11_AC_06_sin_almacenes_todos_pedir_otro_origen_no_muestra_nada(cliente_con, datos):
    ajeno = datos.articulo("Cincel ajeno TR11")
    datos.existencia(datos.ub_almacen("CON"), ajeno, 4)
    con = datos.almacen("CON").id
    cliente = cliente_con(P.CATALOGO_VER, almacen="KEP")

    assert _buscar(cliente, "Cincel ajeno", con)["articulos"]["elementos"] == []
    assert _escanear(cliente, ajeno.codigo, con)["resumen"]["disponible"] == 0


# ------------------------------------------------------------------------------- SG-05


def _traspaso_con_recepcion(datos, articulo, pieza=None):
    """CON envía a MID (sale a En tránsito) y MID lo recibe (llega a su ubicación)."""
    transito = datos.ub_virtual(UbicacionVirtual.EN_TRANSITO)
    envio = datos.vale(TipoVale.TRASPASO, "CON", responsable="sup_con")
    envio.destino_almacen_id = datos.almacen("MID").id
    datos.session.flush()
    datos.movimiento(envio, articulo, datos.ub_almacen("CON"), transito, pieza=pieza)
    recepcion = datos.vale(TipoVale.RECEPCION, "MID", responsable="sup_mid", vale_origen=envio)
    datos.movimiento(recepcion, articulo, transito, datos.ub_almacen("MID"), pieza=pieza)
    return envio, recepcion


def test_SG_05_la_bitacora_de_cada_almacen_ve_la_salida_la_llegada_y_el_traspaso_en_camino(
    cliente_con, datos
):
    guantes = datos.articulo("Guantes SG05", retornable=False)
    envio, recepcion = _traspaso_con_recepcion(datos, guantes)
    con, mid = datos.almacen("CON").id, datos.almacen("MID").id
    cliente = cliente_con(P.BITACORA_VER, P.ALMACENES_TODOS)

    def filas(almacen_id):
        r = cliente.get(MOVIMIENTOS, params={"almacen_id": str(almacen_id), "tamano": 100})
        assert r.status_code == 200, r.text
        return {f["vale_id"]: f for f in r.json()["elementos"]}

    de_con, de_mid = filas(con), filas(mid)
    assert de_con[str(envio.id)]["direccion"] == "SALIDA"
    assert str(recepcion.id) not in de_con
    assert de_mid[str(recepcion.id)]["direccion"] == "ENTRADA"
    assert de_mid[str(recepcion.id)]["direccion_texto"] == "Entrada"
    assert de_mid[str(envio.id)]["direccion"] == "EN_CAMINO"
    # Sin almacén no hay «respecto a» qué dirección: queda en nulo.
    todos = cliente.get(MOVIMIENTOS, params={"tamano": 100}).json()["elementos"]
    assert {f["direccion"] for f in todos if f["vale_id"] == str(envio.id)} == {None}


def test_SG_05_las_entradas_cuentan_y_cada_fila_enlaza_al_vale_y_al_trabajador(cliente_con, datos):
    articulo = datos.articulo("Disco SG05", retornable=False)
    proveedor = datos.ub_virtual(UbicacionVirtual.PROVEEDOR)
    entrada = datos.vale(TipoVale.ENTRADA, "KEP", responsable="compras")
    datos.movimiento(entrada, articulo, proveedor, datos.ub_almacen("KEP"), cantidad=9)
    juan = datos.trabajador("Juan SG05")
    entrega = datos.entrega(juan, articulo, cantidad=2)
    kep = datos.almacen("KEP").id
    cliente = cliente_con(P.BITACORA_VER, almacen="KEP")

    r = cliente.get(MOVIMIENTOS, params={"almacen_id": str(kep), "articulo_id": str(articulo.id)})
    assert r.status_code == 200, r.text
    por_vale = {f["vale_id"]: f for f in r.json()["elementos"]}
    assert por_vale[str(entrada.id)]["direccion"] == "ENTRADA"
    assert por_vale[str(entrada.id)]["trabajador_id"] is None
    assert por_vale[str(entrega.id)]["direccion"] == "SALIDA"
    assert por_vale[str(entrega.id)]["trabajador_id"] == str(juan.id)


def test_SG_05_se_filtra_por_pieza_o_serie_y_por_solo_los_mios(cliente_con, datos):
    detector = datos.articulo("Detector SG05", control="PIEZA")
    a = datos.pieza(detector, datos.ub_almacen("KEP"), serie="GAS-SG05-111")
    b = datos.pieza(detector, datos.ub_almacen("KEP"), serie="GAS-SG05-222")
    juan = datos.trabajador("Juan pieza SG05")
    de_el = datos.entrega(juan, detector, pieza=a, responsable="almacenista")
    de_otro = datos.entrega(juan, detector, pieza=b, responsable="supervisor")
    kep = datos.almacen("KEP").id
    cliente = cliente_con(P.BITACORA_VER, almacen="KEP")

    def vales(**params):
        r = cliente.get(MOVIMIENTOS, params={"almacen_id": str(kep)} | params)
        assert r.status_code == 200, r.text
        return {f["vale_id"] for f in r.json()["elementos"]}

    assert vales(pieza="111") == {str(de_el.id)}  # por serie
    assert vales(pieza=b.codigo) == {str(de_otro.id)}  # por código de pieza
    assert vales(pieza="GAS-SG05") == {str(de_el.id), str(de_otro.id)}
    r = cliente.get(MOVIMIENTOS, params={"almacen_id": str(kep), "pieza": "111"})
    assert r.json()["elementos"][0]["numero_serie"] == "GAS-SG05-111"
    # «Solo los míos» es el usuario de la sesión: el de la prueba no hizo ninguno.
    assert vales(solo_mios="true") == set()


def test_SG_05_solo_los_mios_trae_lo_que_hizo_el_usuario_de_la_sesion(
    cliente_con, datos, crear_usuario, app
):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    articulo = datos.articulo("Disco mio SG05", retornable=False)
    datos.existencia(datos.ub_almacen("KEP"), articulo, 20)
    juan = datos.trabajador("Juan mio SG05")
    usuario = crear_usuario({P.BITACORA_VER}, almacen="KEP")
    mio = datos.entrega(juan, articulo, responsable=datos.usuario(usuario.usuario))
    ajeno = datos.entrega(juan, articulo, responsable="supervisor")
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200

    todos = {f["vale_id"] for f in cliente.get(MOVIMIENTOS).json()["elementos"]}
    suyos = {
        f["vale_id"]
        for f in cliente.get(MOVIMIENTOS, params={"solo_mios": "true"}).json()["elementos"]
    }
    assert {str(mio.id), str(ajeno.id)} <= todos
    assert suyos == {str(mio.id)}
    cliente.close()


def test_SG_05_la_bitacora_acepta_bitacora_ver_o_reportes_movimientos_y_si_no_es_403(
    cliente_con, datos
):
    for permiso in (P.BITACORA_VER, P.REPORTES_MOVIMIENTOS):
        cliente = cliente_con(permiso, almacen="KEP")
        assert cliente.get(MOVIMIENTOS).status_code == 200, permiso
        assert cliente.get(USUARIOS).status_code == 200, permiso
        assert cliente.get(MOVIMIENTOS, params={"formato": "csv"}).status_code == 200
    sin = cliente_con(P.CATALOGO_VER, almacen="KEP")
    r = sin.get(MOVIMIENTOS)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert sin.get(USUARIOS).status_code == 403


def test_SG_05_AC_06_un_almacenista_con_bitacora_ver_ve_solo_su_almacen(cliente_con, datos):
    articulo = datos.articulo("Disco alcance SG05", retornable=False)
    datos.existencia(datos.ub_almacen("KEP"), articulo, 10)
    juan = datos.trabajador("Juan alcance SG05")
    datos.entrega(juan, articulo, almacen="KEP")
    con = datos.almacen("CON").id
    cliente = cliente_con(P.BITACORA_VER, almacen="MID")

    assert cliente.get(MOVIMIENTOS, params={"articulo_id": str(articulo.id)}).json()["total"] == 0
    r = cliente.get(MOVIMIENTOS, params={"almacen_id": str(con)})
    assert r.status_code == 200 and r.json()["elementos"] == []
