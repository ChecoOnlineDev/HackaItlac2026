"""Escaneo universal y búsqueda (US-CON-001): C-01 a C-04, C-06, RG-12 y RG-13."""

from datetime import timedelta

from app.core.tiempo import hoy_mx
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import TipoCodigo

ESCANEO = "/api/escaneo"
BUSQUEDA = "/api/busqueda"


def escanear(cliente, codigo: str) -> dict:
    respuesta = cliente.get(f"{ESCANEO}/{codigo}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ------------------------------------------------------------------------------ escaneo


def test_C_01_escanear_una_credencial_muestra_al_trabajador_su_vigencia_y_su_resguardo(
    cliente_como, datos
):
    juan = datos.trabajador("Juan Pérez Soto", codigo="TRB-C-0001")
    arnes = datos.articulo("Arnés de prueba", retornable=True)
    datos.existencia(datos.ub_almacen("KEP"), arnes, 5)
    datos.entrega(juan, arnes, cantidad=2)

    cuerpo = escanear(cliente_como("Almacenista"), "TRB-C-0001")

    assert cuerpo["tipo"] == "TRABAJADOR"
    assert cuerpo["id"] == str(juan.id)
    resumen = cuerpo["resumen"]
    assert resumen["nombre"] == "Juan Pérez Soto"
    assert resumen["numero_empleado"] == juan.numero_empleado
    assert resumen["vigente"] is True
    assert resumen["motivo_no_vigente"] is None
    assert resumen["puesto"] == "Soldador"
    assert resumen["area_obra"] == "Midrex"
    assert resumen["pendientes"] == 2


def test_C_01_un_trabajador_con_el_contrato_vencido_se_muestra_no_vigente_con_su_motivo(
    cliente_como, datos
):
    hoy = hoy_mx()
    maria = datos.trabajador(
        "María Torres",
        inicio=hoy - timedelta(days=100),
        fin=hoy - timedelta(days=1),
        codigo="TRB-C-0002",
    )

    resumen = escanear(cliente_como("Almacenista"), "TRB-C-0002")["resumen"]

    assert resumen["vigente"] is False
    assert "plantilla" in resumen["motivo_no_vigente"]
    assert resumen["vigente_hasta"] == (hoy - timedelta(days=1)).isoformat()
    assert maria.estado == "ACTIVO"


def test_C_01_el_numero_de_empleado_tecleado_identifica_al_trabajador(cliente_como, datos):
    luis = datos.trabajador("Luis Ramírez")

    cuerpo = escanear(cliente_como("Almacenista"), luis.numero_empleado)

    assert cuerpo["tipo"] == "TRABAJADOR"
    assert cuerpo["id"] == str(luis.id)


def test_RG_13_el_resumen_del_trabajador_nunca_trae_curp_ni_nss_ni_para_rh(cliente_como, datos):
    datos.trabajador("Ana Soto", codigo="TRB-C-0003", curp="SOAA900101MCLRNN09", nss="12345678901")

    for rol in ("Recursos Humanos", "Almacenista", "Supervisor"):
        respuesta = cliente_como(rol).get(f"{ESCANEO}/TRB-C-0003")
        assert respuesta.status_code == 200
        assert "SOAA900101MCLRNN09" not in respuesta.text
        assert "12345678901" not in respuesta.text
        assert "curp" not in respuesta.text.lower()
        assert "nss" not in respuesta.text.lower()


def test_C_02_escanear_una_pieza_muestra_su_estado_su_inspeccion_y_quien_la_tiene(
    cliente_como, datos
):
    juan = datos.trabajador("Juan Pérez")
    arnes = datos.articulo("Arnés con serie", control="PIEZA")
    vigencia = hoy_mx() + timedelta(days=40)
    pieza = datos.pieza(
        arnes,
        datos.ub_trabajador(juan),
        serie="SN-ESC-1",
        vigente_hasta=vigencia,
        codigo="PZA-C-0001",
    )

    cuerpo = escanear(cliente_como("Almacenista"), "PZA-C-0001")

    assert cuerpo["tipo"] == "PIEZA"
    assert cuerpo["id"] == str(pieza.id)
    resumen = cuerpo["resumen"]
    assert resumen["articulo"] == "Arnés con serie"
    assert resumen["numero_serie"] == "SN-ESC-1"
    assert resumen["estado"] == "APTO"
    assert resumen["inspeccion_vigente_hasta"] == vigencia.isoformat()
    assert resumen["inspeccion_vigente"] is True
    assert resumen["ubicacion"]["tipo"] == "TRABAJADOR"
    assert resumen["ubicacion"]["trabajador_id"] == str(juan.id)
    assert "Juan Pérez" in resumen["ubicacion"]["texto"]


def test_C_02_una_pieza_con_la_inspeccion_vencida_no_se_marca_vigente(cliente_como, datos):
    articulo = datos.articulo("Línea de vida", control="PIEZA")
    datos.pieza(
        articulo,
        datos.ub_almacen("KEP"),
        vigente_hasta=hoy_mx() - timedelta(days=1),
        codigo="PZA-C-0002",
    )

    resumen = escanear(cliente_como("Almacenista"), "PZA-C-0002")["resumen"]

    assert resumen["inspeccion_vigente"] is False


def test_C_03_escanear_un_articulo_muestra_su_existencia_sin_costos(cliente_como, datos):
    marro = datos.articulo("Marro de 5 libras", costo="987.65", codigo="ART-C-0001")
    datos.existencia(datos.ub_almacen("KEP"), marro, 7)
    datos.existencia(datos.ub_almacen("CON"), marro, 3)

    # El Administrador (único con `almacenes.todos`) ve la suma de todos los almacenes; Compras,
    # asignado a Kepler, solo lo de Kepler (AC-06).
    respuesta = cliente_como("Administrador").get(f"{ESCANEO}/ART-C-0001")
    assert (
        cliente_como("Compras").get(f"{ESCANEO}/ART-C-0001").json()["resumen"]["existencia_total"]
        == 7
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["tipo"] == "ARTICULO"
    assert cuerpo["id"] == str(marro.id)
    assert cuerpo["resumen"]["existencia_total"] == 10
    assert cuerpo["resumen"]["nombre"] == "Marro de 5 libras"
    assert "987.65" not in respuesta.text
    assert "costo" not in respuesta.text.lower()


def test_C_04_el_qr_de_un_vale_abre_el_vale_por_su_token_su_codigo_y_su_folio(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante de carnaza")
    datos.existencia(datos.ub_almacen("KEP"), guante, 9)
    vale = datos.entrega(juan, guante, cantidad=2)
    CodigoService(datos.session).registrar("VAL-C-0001", TipoCodigo.VALE, vale.id)
    almacenista = cliente_como("Almacenista")

    for texto in (vale.token, "VAL-C-0001", vale.folio):
        cuerpo = escanear(almacenista, texto)
        assert cuerpo["tipo"] == "VALE", texto
        assert cuerpo["id"] == str(vale.id)
    resumen = cuerpo["resumen"]
    assert resumen["folio"] == vale.folio
    assert resumen["tipo"] == "ENTREGA"
    assert resumen["estado"] == "EMITIDO"
    assert resumen["almacen_clave"] == "KEP"
    assert resumen["trabajador"] == "Juan Pérez"
    assert resumen["responsable"]


def test_C_01_un_codigo_que_no_existe_es_desconocido(cliente_como):
    cuerpo = escanear(cliente_como("Almacenista"), "NO-EXISTE-999")

    assert cuerpo["tipo"] == "DESCONOCIDO"
    assert cuerpo["id"] is None
    assert cuerpo["resumen"]["mensaje"] == "No se encontró nada con ese código o texto."


def test_C_01_un_codigo_en_blanco_se_rechaza_con_422(cliente_como):
    respuesta = cliente_como("Almacenista").get(f"{ESCANEO}/%20%20")

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"


def test_C_01_sin_trabajadores_ver_la_credencial_y_el_numero_llegan_como_desconocido(
    cliente_como, datos
):
    juan = datos.trabajador("Juan Pérez", codigo="TRB-C-0004")
    compras = cliente_como("Compras")  # tiene catalogo.ver y vales.ver, no trabajadores.ver

    assert escanear(compras, "TRB-C-0004")["tipo"] == "DESCONOCIDO"
    assert escanear(compras, juan.numero_empleado)["tipo"] == "DESCONOCIDO"


def test_C_02_sin_catalogo_ver_el_articulo_y_la_pieza_llegan_como_desconocido(cliente_como, datos):
    articulo = datos.articulo("Detector de gas", control="PIEZA", codigo="ART-C-0002")
    datos.pieza(articulo, datos.ub_almacen("KEP"), codigo="PZA-C-0003")
    rh = cliente_como("Recursos Humanos")  # RH no ve el inventario (RG-13)

    assert escanear(rh, "ART-C-0002")["tipo"] == "DESCONOCIDO"
    assert escanear(rh, "PZA-C-0003")["tipo"] == "DESCONOCIDO"


def test_C_04_sin_vales_ver_el_vale_llega_como_desconocido(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante")
    datos.existencia(datos.ub_almacen("KEP"), guante, 3)
    vale = datos.entrega(juan, guante)
    CodigoService(datos.session).registrar("VAL-C-0002", TipoCodigo.VALE, vale.id)
    rh = cliente_como("Recursos Humanos")

    assert escanear(rh, "VAL-C-0002")["tipo"] == "DESCONOCIDO"
    assert escanear(rh, vale.token)["tipo"] == "DESCONOCIDO"
    assert escanear(rh, vale.folio)["tipo"] == "DESCONOCIDO"


def test_C_01_rh_si_escanea_la_credencial_porque_tiene_trabajadores_ver(cliente_como, datos):
    datos.trabajador("Ana Soto", codigo="TRB-C-0005")

    assert escanear(cliente_como("Recursos Humanos"), "TRB-C-0005")["tipo"] == "TRABAJADOR"


def test_C_01_el_escaneo_sin_sesion_responde_401(client):
    respuesta = client.get(f"{ESCANEO}/TRB-1001")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_C_01_el_escaneo_no_escribe_nada(cliente_como, datos, session):
    datos.trabajador("Juan", codigo="TRB-C-0006")
    cliente = cliente_como("Almacenista")
    session.flush()
    antes = (len(session.new), len(session.dirty), len(session.deleted))

    cliente.get(f"{ESCANEO}/TRB-C-0006")

    assert (len(session.new), len(session.dirty), len(session.deleted)) == antes


# ----------------------------------------------------------------------------- búsqueda


def buscar(cliente, q: str, **extra) -> dict:
    respuesta = cliente.get(BUSQUEDA, params={"q": q, **extra})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_C_06_un_texto_de_menos_de_dos_caracteres_no_busca(cliente_como, datos):
    datos.articulo("Zeta único para búsqueda")
    datos.trabajador("Zacarías de prueba")
    almacenista = cliente_como("Almacenista")

    for texto in ("", " ", "z", "  z  "):
        cuerpo = buscar(almacenista, texto)
        assert cuerpo["articulos"] == {"elementos": [], "total": 0}
        assert cuerpo["piezas"] == {"elementos": [], "total": 0}
        assert cuerpo["trabajadores"] == {"elementos": [], "total": 0}
        assert cuerpo["mensaje"]


def test_C_06_dos_caracteres_ya_buscan(cliente_como, datos):
    datos.articulo("Zeta único para búsqueda")

    cuerpo = buscar(cliente_como("Almacenista"), "ze")

    assert cuerpo["articulos"]["total"] >= 1


def test_C_06_busca_articulos_por_nombre_y_por_codigo(cliente_como, datos):
    detector = datos.articulo("Detector multigás Bosch", codigo="DET-C-777")
    almacenista = cliente_como("Almacenista")

    por_nombre = buscar(almacenista, "multigás")
    por_codigo = buscar(almacenista, "DET-C-777")

    assert [a["id"] for a in por_nombre["articulos"]["elementos"]] == [str(detector.id)]
    assert [a["id"] for a in por_codigo["articulos"]["elementos"]] == [str(detector.id)]
    assert por_nombre["articulos"]["elementos"][0]["categoria"]


def test_C_06_la_busqueda_no_distingue_acentos_ni_mayusculas(cliente_como, datos):
    detector = datos.articulo("Detector multigás Bosch")

    cuerpo = buscar(cliente_como("Almacenista"), "MULTIGAS")

    assert str(detector.id) in [a["id"] for a in cuerpo["articulos"]["elementos"]]


def test_C_06_busca_piezas_por_numero_de_serie_y_dice_quien_la_tiene(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    detector = datos.articulo("Detector de gas", control="PIEZA")
    en_almacen = datos.pieza(detector, datos.ub_almacen("KEP"), serie="SERIE-XQ-100")
    con_juan = datos.pieza(detector, datos.ub_trabajador(juan), serie="SERIE-XQ-200")
    almacenista = cliente_como("Almacenista")

    por_serie = buscar(almacenista, "SERIE-XQ-200")
    assert [p["id"] for p in por_serie["piezas"]["elementos"]] == [str(con_juan.id)]
    assert "Juan Pérez" in por_serie["piezas"]["elementos"][0]["ubicacion"]

    por_nombre = buscar(almacenista, "Detector de gas")
    piezas = {p["id"]: p for p in por_nombre["piezas"]["elementos"]}
    # Las piezas de los datos de prueba (detectores de gases) también coinciden con el nombre.
    assert {str(en_almacen.id), str(con_juan.id)} <= set(piezas)
    assert "KEP" in piezas[str(en_almacen.id)]["ubicacion"]


def test_C_06_busca_trabajadores_por_nombre_y_por_numero_de_empleado(cliente_como, datos):
    ana = datos.trabajador("Anastasia Zubieta")
    almacenista = cliente_como("Almacenista")

    por_nombre = buscar(almacenista, "zubieta")
    por_numero = buscar(almacenista, ana.numero_empleado)

    assert [t["id"] for t in por_nombre["trabajadores"]["elementos"]] == [str(ana.id)]
    assert [t["id"] for t in por_numero["trabajadores"]["elementos"]] == [str(ana.id)]
    assert "curp" not in str(por_nombre).lower()
    assert "nss" not in str(por_nombre).lower()


def test_C_06_cada_grupo_respeta_los_permisos_de_quien_busca(cliente_como, datos):
    datos.articulo("Zafiro Detector", control="PIEZA")
    datos.trabajador("Zafiro Ramírez")

    como_rh = buscar(cliente_como("Recursos Humanos"), "zafiro")
    como_compras = buscar(cliente_como("Compras"), "zafiro")
    como_almacenista = buscar(cliente_como("Almacenista"), "zafiro")

    assert como_rh["articulos"]["total"] == 0 and como_rh["piezas"]["total"] == 0
    assert como_rh["trabajadores"]["total"] == 1
    assert como_compras["articulos"]["total"] == 1
    assert como_compras["trabajadores"]["total"] == 0
    assert como_almacenista["articulos"]["total"] == 1
    assert como_almacenista["trabajadores"]["total"] == 1


def test_C_06_sin_resultados_lo_indica_con_su_mensaje(cliente_como):
    cuerpo = buscar(cliente_como("Almacenista"), "qwxzvbnm-no-existe")

    assert cuerpo["sin_resultados"] is True
    assert cuerpo["mensaje"] == "No se encontró nada con ese código o texto."


def test_C_06_los_comodines_de_like_se_toman_como_texto(cliente_como, datos):
    datos.articulo("Artículo normal")

    cuerpo = buscar(cliente_como("Almacenista"), "%%")

    assert cuerpo["articulos"]["total"] == 0


def test_C_06_los_resultados_se_paginan_con_elementos_y_total(cliente_como, datos):
    for i in range(5):
        datos.articulo(f"Cincel paginado {i}")
    almacenista = cliente_como("Almacenista")

    primera = buscar(almacenista, "cincel paginado", pagina=1, tamano=2)
    tercera = buscar(almacenista, "cincel paginado", pagina=3, tamano=2)

    assert primera["articulos"]["total"] == 5
    assert len(primera["articulos"]["elementos"]) == 2
    assert len(tercera["articulos"]["elementos"]) == 1


def test_C_06_la_busqueda_sin_sesion_responde_401(client):
    assert client.get(BUSQUEDA, params={"q": "guante"}).status_code == 401


def test_RG_12_la_busqueda_nunca_trae_costos(cliente_como, datos):
    datos.articulo("Premium especial", costo="4321.99")

    respuesta = cliente_como("Compras").get(BUSQUEDA, params={"q": "premium"})

    assert respuesta.status_code == 200
    assert "4321.99" not in respuesta.text
    assert "costo" not in respuesta.text.lower()


def test_C_01_un_consumo_no_aparece_en_el_resguardo_del_trabajador(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez", codigo="TRB-C-0007")
    guante = datos.articulo("Guante desechable", retornable=False)
    datos.existencia(datos.ub_almacen("KEP"), guante, 20)
    datos.entrega(juan, guante, cantidad=4)

    resumen = escanear(cliente_como("Almacenista"), "TRB-C-0007")["resumen"]

    assert resumen["pendientes"] == 0
