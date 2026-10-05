"""Reportes (US-REP-001, US-REP-002): existencias, movimientos, adeudos y consumo.

Reglas: C-05, C-08, C-11, RG-12, AC-06 y las de la sección 8 (permisos por endpoint). Cada
reporte se prueba en JSON y en CSV con los mismos filtros.
"""

import csv
import io
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.models import TipoVale

EXISTENCIAS = "/api/reportes/existencias"
MOVIMIENTOS = "/api/reportes/movimientos"
ADEUDOS = "/api/reportes/adeudos"
CONSUMO = "/api/reportes/consumo"
TODOS = (EXISTENCIAS, MOVIMIENTOS, ADEUDOS, CONSUMO)

MX = ZoneInfo("America/Mexico_City")


def local_a_utc(anio, mes, dia, hora=0, minuto=0, segundo=0) -> datetime:
    """Una hora local de México como la guarda la base: UTC sin zona."""
    local = datetime(anio, mes, dia, hora, minuto, segundo, tzinfo=MX)
    return local.astimezone(UTC).replace(tzinfo=None)


def pedir(cliente, ruta: str, **params) -> dict:
    respuesta = cliente.get(ruta, params={k: str(v) for k, v in params.items() if v is not None})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def pedir_csv(cliente, ruta: str, **params):
    respuesta = cliente.get(ruta, params={"formato": "csv", **params})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta


def filas_csv(respuesta) -> list[list[str]]:
    texto = respuesta.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto)))


# ------------------------------------------------------------------------- permisos (8.2)


@pytest.mark.parametrize(
    ("ruta", "permiso"),
    [
        (EXISTENCIAS, P.REPORTES_EXISTENCIAS),
        (MOVIMIENTOS, P.REPORTES_MOVIMIENTOS),
        (ADEUDOS, P.REPORTES_ADEUDOS),
        (CONSUMO, P.REPORTES_CONSUMO),
    ],
)
def test_AC_04_cada_reporte_exige_su_permiso_en_json_y_en_csv(cliente_con, ruta, permiso):
    otros = {
        p
        for p in (
            P.REPORTES_EXISTENCIAS,
            P.REPORTES_MOVIMIENTOS,
            P.REPORTES_ADEUDOS,
            P.REPORTES_CONSUMO,
            P.CATALOGO_VER,
            P.VALES_VER,
        )
        if p != permiso
    }
    sin_permiso = cliente_con(*otros, almacen="KEP")
    con_permiso = cliente_con(permiso, almacen="KEP")

    for formato in ("json", "csv"):
        negado = sin_permiso.get(ruta, params={"formato": formato})
        assert negado.status_code == 403
        assert negado.json()["codigo"] == "SIN_PERMISO"
        assert con_permiso.get(ruta, params={"formato": formato}).status_code == 200


@pytest.mark.parametrize("ruta", TODOS)
def test_AC_04_un_reporte_sin_sesion_responde_401(client, ruta):
    assert client.get(ruta).status_code == 401


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("Almacenista", {EXISTENCIAS: 200, MOVIMIENTOS: 200, ADEUDOS: 200, CONSUMO: 403}),
        ("Supervisor", {EXISTENCIAS: 200, MOVIMIENTOS: 200, ADEUDOS: 200, CONSUMO: 200}),
        ("Compras", {EXISTENCIAS: 200, MOVIMIENTOS: 200, ADEUDOS: 403, CONSUMO: 200}),
        ("Recursos Humanos", {EXISTENCIAS: 403, MOVIMIENTOS: 403, ADEUDOS: 200, CONSUMO: 403}),
    ],
)
def test_AC_04_los_roles_iniciales_ven_los_reportes_de_la_tabla_8_2(cliente_como, rol, esperado):
    cliente = cliente_como(rol)

    for ruta, codigo in esperado.items():
        assert cliente.get(ruta).status_code == codigo, (rol, ruta)


# ----------------------------------------------------------------------------- existencias


def _escenario_existencias(datos):
    guante = datos.articulo("Guante existencias")
    arnes = datos.articulo("Arnés existencias", control="PIEZA")
    datos.existencia(datos.ub_almacen("KEP"), guante, 12)
    datos.existencia(datos.ub_almacen("CON"), guante, 4)
    datos.existencia(datos.ub_almacen("KEP"), arnes, 2)
    datos.pieza(arnes, datos.ub_almacen("KEP"), estado="APTO")
    datos.pieza(arnes, datos.ub_almacen("KEP"), estado="NO_APTO")
    return guante, arnes


def _por_articulo(cuerpo, articulo):
    return [e for e in cuerpo["elementos"] if e["articulo_id"] == str(articulo.id)]


def test_C_05_existencias_por_almacen_y_articulo_separan_disponible_de_no_disponible(
    cliente_como, datos
):
    guante, arnes = _escenario_existencias(datos)

    cuerpo = pedir(cliente_como("Supervisor"), EXISTENCIAS)

    por_almacen = {e["almacen_clave"]: e for e in _por_articulo(cuerpo, guante)}
    assert por_almacen["KEP"]["cantidad"] == 12 and por_almacen["KEP"]["disponible"] == 12
    assert por_almacen["CON"]["cantidad"] == 4
    arnes_kep = _por_articulo(cuerpo, arnes)[0]
    assert arnes_kep["cantidad"] == 2
    assert arnes_kep["disponible"] == 1  # la pieza No apta no está disponible (I-05)
    assert arnes_kep["categoria"] and arnes_kep["unidad"] == "pieza"


def test_C_05_existencias_se_filtran_por_almacen_y_por_categoria(cliente_como, datos):
    guante, arnes = _escenario_existencias(datos)
    supervisor = cliente_como("Supervisor")
    kep = datos.almacen("KEP")

    solo_kep = pedir(supervisor, EXISTENCIAS, almacen_id=kep.id)
    por_categoria = pedir(supervisor, EXISTENCIAS, categoria_id=arnes.categoria_id)

    assert {e["almacen_clave"] for e in solo_kep["elementos"]} == {"KEP"}
    assert {e["articulo_id"] for e in por_categoria["elementos"]} == {str(arnes.id)}


def test_C_11_el_almacenista_solo_ve_las_existencias_de_su_almacen(cliente_como, datos):
    guante, *_ = _escenario_existencias(datos)

    cuerpo = pedir(cliente_como("Almacenista"), EXISTENCIAS)

    assert {e["almacen_clave"] for e in cuerpo["elementos"]} == {"KEP"}
    assert cuerpo["total"] == len(cuerpo["elementos"])


def test_C_11_un_almacenista_que_pide_otro_almacen_no_ve_nada_de_el(cliente_como, datos):
    _escenario_existencias(datos)
    con = datos.almacen("CON")

    cuerpo = pedir(cliente_como("Almacenista"), EXISTENCIAS, almacen_id=con.id)

    assert cuerpo["elementos"] == [] and cuerpo["total"] == 0
    assert cuerpo["sin_registros"] is True


def test_C_11_con_almacenes_todos_se_ven_todos_los_almacenes(cliente_como, datos):
    guante, *_ = _escenario_existencias(datos)

    cuerpo = pedir(cliente_como("Compras"), EXISTENCIAS)

    assert {e["almacen_clave"] for e in _por_articulo(cuerpo, guante)} == {"KEP", "CON"}


def test_C_11_sin_almacen_asignado_ni_almacenes_todos_no_ve_nada(cliente_con, datos):
    _escenario_existencias(datos)

    cuerpo = pedir(cliente_con(P.REPORTES_EXISTENCIAS), EXISTENCIAS)

    assert cuerpo["total"] == 0


def test_C_05_existencias_en_csv_tiene_el_mismo_conteo_y_encabezados_en_espanol(
    cliente_como, datos
):
    _escenario_existencias(datos)
    supervisor = cliente_como("Supervisor")

    cuerpo = pedir(supervisor, EXISTENCIAS, tamano=200)
    respuesta = pedir_csv(supervisor, EXISTENCIAS)
    filas = filas_csv(respuesta)

    assert filas[0] == [
        "Clave del almacén", "Almacén", "Código", "Artículo", "Categoría", "Unidad",
        "Cantidad", "Disponible",
    ]  # fmt: skip
    assert len(filas) - 1 == cuerpo["total"]
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.headers["content-type"].startswith("text/csv")


def test_C_05_existencias_se_paginan_con_elementos_y_total(cliente_como, datos):
    _escenario_existencias(datos)
    supervisor = cliente_como("Supervisor")

    pagina = pedir(supervisor, EXISTENCIAS, pagina=1, tamano=2)

    assert len(pagina["elementos"]) == 2
    assert pagina["total"] >= 3


def test_RG_12_el_reporte_de_existencias_no_muestra_costos(cliente_como, datos):
    articulo = datos.articulo("Caro de existencias", costo="7777.77")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 3)
    compras = cliente_como("Compras")

    assert "7777.77" not in compras.get(EXISTENCIAS).text
    assert "7777.77" not in compras.get(EXISTENCIAS, params={"formato": "csv"}).text
    assert "costo" not in compras.get(EXISTENCIAS).text.lower()


# ---------------------------------------------------------------------------- movimientos


def _escenario_movimientos(datos):
    juan = datos.trabajador("Juan Pérez")
    ana = datos.trabajador("Ana Soto")
    guante = datos.articulo("Guante movimientos")
    casco = datos.articulo("Casco movimientos")
    datos.existencia(datos.ub_almacen("KEP"), guante, 50)
    datos.existencia(datos.ub_almacen("KEP"), casco, 50)
    datos.existencia(datos.ub_almacen("CON"), casco, 50)
    ent_juan = datos.entrega(juan, guante, cantidad=2, creado_en=local_a_utc(2026, 9, 10, 10))
    ent_ana = datos.entrega(ana, casco, cantidad=1, creado_en=local_a_utc(2026, 9, 20, 10))
    ent_con = datos.entrega(
        juan, casco, almacen="CON", responsable="alm_con", creado_en=local_a_utc(2026, 9, 25, 10)
    )
    return juan, ana, guante, casco, ent_juan, ent_ana, ent_con


def _folios(cuerpo) -> set[str]:
    return {e["folio"] for e in cuerpo["elementos"]}


def test_C_05_el_reporte_de_movimientos_trae_las_columnas_del_contrato(cliente_como, datos):
    juan, _, guante, _, ent_juan, *_ = _escenario_movimientos(datos)

    cuerpo = pedir(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=guante.id)

    assert cuerpo["total"] == 1
    fila = cuerpo["elementos"][0]
    assert fila["folio"] == ent_juan.folio
    assert fila["tipo"] == "ENTREGA" and fila["tipo_texto"] == "Entrega"
    assert fila["articulo"] == "Guante movimientos"
    assert fila["cantidad"] == 2
    assert "KEP" in fila["origen"]
    assert "Juan Pérez" in fila["destino"]
    assert fila["responsable"]
    assert fila["saldo_origen"] == 0 and fila["saldo_destino"] == 2
    assert fila["fecha"].startswith("2026-09-10T16:00:00")  # 10:00 en México son las 16:00 UTC


def test_C_05_los_filtros_de_movimientos_se_combinan(cliente_como, datos):
    juan, ana, guante, casco, ent_juan, ent_ana, ent_con = _escenario_movimientos(datos)
    supervisor = cliente_como("Supervisor")
    kep, con = datos.almacen("KEP"), datos.almacen("CON")

    assert _folios(pedir(supervisor, MOVIMIENTOS, trabajador_id=juan.id, articulo_id=casco.id)) == {
        ent_con.folio
    }
    assert _folios(pedir(supervisor, MOVIMIENTOS, tipo="ENTREGA", articulo_id=casco.id)) == {
        ent_ana.folio,
        ent_con.folio,
    }
    assert _folios(pedir(supervisor, MOVIMIENTOS, articulo_id=casco.id, almacen_id=con.id)) == {
        ent_con.folio
    }
    assert _folios(
        pedir(supervisor, MOVIMIENTOS, articulo_id=casco.id, almacen_id=kep.id,
              desde="2026-09-15", hasta="2026-09-30")
    ) == {ent_ana.folio}  # fmt: skip
    assert pedir(supervisor, MOVIMIENTOS, articulo_id=casco.id, tipo="TRASPASO")["total"] == 0


def test_C_05_el_filtro_de_tipo_rechaza_un_valor_desconocido(cliente_como):
    respuesta = cliente_como("Supervisor").get(MOVIMIENTOS, params={"tipo": "INVENTADO"})

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"


def test_C_11_el_filtro_por_usuario_muestra_quien_toco_el_equipo_y_cuando(cliente_como, datos):
    juan, _, guante, casco, *_ = _escenario_movimientos(datos)
    almacenista = datos.usuario("almacenista")
    alm_con = datos.usuario("alm_con")
    supervisor = cliente_como("Supervisor")

    del_almacenista = pedir(
        supervisor, MOVIMIENTOS, usuario_id=almacenista.id, articulo_id=casco.id
    )
    de_alm_con = pedir(supervisor, MOVIMIENTOS, usuario_id=alm_con.id, articulo_id=casco.id)

    assert del_almacenista["total"] == 1
    assert del_almacenista["elementos"][0]["responsable"] == almacenista.nombre
    assert de_alm_con["total"] == 1
    assert de_alm_con["elementos"][0]["responsable"] == alm_con.nombre


def test_C_11_el_rastro_de_un_equipo_por_articulo_almacen_y_periodo_lista_sus_vales(
    cliente_como, datos
):
    """Equipo que desapareció: artículo + almacén + periodo listan los vales y su responsable."""
    juan = datos.trabajador("Juan Pérez")
    detector = datos.articulo("Detector desaparecido", control="PIEZA")
    pieza = datos.pieza(detector, datos.ub_almacen("KEP"))
    entrega = datos.vale(
        TipoVale.ENTREGA, "KEP", trabajador=juan, creado_en=local_a_utc(2026, 8, 3, 9)
    )
    datos.movimiento(
        entrega, detector, datos.ub_almacen("KEP"), datos.ub_trabajador(juan), pieza=pieza
    )
    fuera_de_periodo = datos.vale(TipoVale.ENTRADA, "KEP", creado_en=local_a_utc(2026, 1, 3, 9))
    datos.movimiento(
        fuera_de_periodo,
        detector,
        datos.ub_virtual(UbicacionVirtual.PROVEEDOR),
        datos.ub_almacen("KEP"),
        pieza=pieza,
    )

    cuerpo = pedir(
        cliente_como("Supervisor"),
        MOVIMIENTOS,
        articulo_id=detector.id,
        almacen_id=datos.almacen("KEP").id,
        desde="2026-08-01",
        hasta="2026-08-31",
    )

    assert [e["folio"] for e in cuerpo["elementos"]] == [entrega.folio]
    assert cuerpo["elementos"][0]["responsable"]
    assert cuerpo["elementos"][0]["pieza"] == pieza.codigo


def test_C_11_el_almacenista_ve_solo_los_movimientos_de_su_almacen(cliente_como, datos):
    _, _, _, casco, ent_juan, ent_ana, ent_con = _escenario_movimientos(datos)

    cuerpo = pedir(cliente_como("Almacenista"), MOVIMIENTOS, articulo_id=casco.id)

    assert _folios(cuerpo) == {ent_ana.folio}  # la entrega de CON no aparece
    assert ent_con.folio not in _folios(cuerpo)


def test_C_11_el_almacenista_que_filtra_por_un_usuario_de_otro_almacen_no_ve_nada(
    cliente_como, datos
):
    _, _, _, casco, *_ = _escenario_movimientos(datos)
    alm_con = datos.usuario("alm_con")

    cuerpo = pedir(cliente_como("Almacenista"), MOVIMIENTOS, usuario_id=alm_con.id)

    assert cuerpo["elementos"] == [] and cuerpo["total"] == 0
    assert cuerpo["sin_registros"] is True
    assert cuerpo["mensaje"] == "No hay registros con esos filtros."


def test_C_11_el_almacenista_filtra_por_usuario_dentro_de_su_almacen_como_dato_informativo(
    cliente_como, datos
):
    _, _, _, casco, ent_juan, ent_ana, _ = _escenario_movimientos(datos)
    almacenista = datos.usuario("almacenista")

    cuerpo = pedir(
        cliente_como("Almacenista"), MOVIMIENTOS, usuario_id=almacenista.id, articulo_id=casco.id
    )

    assert _folios(cuerpo) == {ent_ana.folio}


def test_C_11_el_almacenista_que_pide_otro_almacen_no_ve_nada(cliente_como, datos):
    _escenario_movimientos(datos)

    cuerpo = pedir(cliente_como("Almacenista"), MOVIMIENTOS, almacen_id=datos.almacen("CON").id)

    assert cuerpo["total"] == 0


def test_C_11_con_almacenes_todos_se_ven_todos_los_almacenes_y_usuarios(cliente_como, datos):
    _, _, _, casco, _, ent_ana, ent_con = _escenario_movimientos(datos)

    for rol in ("Supervisor", "Compras"):
        cuerpo = pedir(cliente_como(rol), MOVIMIENTOS, articulo_id=casco.id)
        assert _folios(cuerpo) == {ent_ana.folio, ent_con.folio}, rol


def test_C_11_el_csv_de_movimientos_respeta_el_mismo_alcance(cliente_como, datos):
    _, _, _, casco, _, ent_ana, ent_con = _escenario_movimientos(datos)

    como_almacenista = filas_csv(pedir_csv(cliente_como("Almacenista"), MOVIMIENTOS))
    como_supervisor = filas_csv(
        pedir_csv(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=casco.id)
    )

    folios_almacenista = {fila[1] for fila in como_almacenista[1:]}
    assert ent_con.folio not in folios_almacenista
    assert {fila[1] for fila in como_supervisor[1:]} == {ent_ana.folio, ent_con.folio}


def test_C_05_un_rango_de_fechas_invertido_se_rechaza_en_todos_los_reportes(
    cliente_como,
):
    supervisor = cliente_como("Supervisor")

    for ruta in (MOVIMIENTOS, CONSUMO):
        for formato in ("json", "csv"):
            respuesta = supervisor.get(
                ruta, params={"desde": "2026-10-05", "hasta": "2026-10-01", "formato": formato}
            )
            assert respuesta.status_code == 422, (ruta, formato)
            assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"


def test_C_05_un_rango_de_un_solo_dia_es_valido(cliente_como):
    respuesta = cliente_como("Supervisor").get(
        MOVIMIENTOS, params={"desde": "2026-10-05", "hasta": "2026-10-05"}
    )

    assert respuesta.status_code == 200


def test_C_05_el_dia_termina_a_las_23_59_59_hora_de_mexico_no_en_utc(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante de horarios")
    datos.existencia(datos.ub_almacen("KEP"), guante, 100)
    # Instantes locales de México (UTC-6) alrededor del día 5 de octubre.
    antes_del_dia = datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 4, 23, 59, 59))
    inicio_del_dia = datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 5, 0, 0, 0))
    tarde = datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 5, 23, 30))
    ultimo_segundo = datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 5, 23, 59, 59))
    despues_del_dia = datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 6, 0, 0, 1))
    supervisor = cliente_como("Supervisor")

    del_dia = pedir(
        supervisor, MOVIMIENTOS, articulo_id=guante.id, desde="2026-10-05", hasta="2026-10-05"
    )

    assert _folios(del_dia) == {inicio_del_dia.folio, tarde.folio, ultimo_segundo.folio}
    assert antes_del_dia.folio not in _folios(del_dia)
    assert despues_del_dia.folio not in _folios(del_dia)
    # El movimiento de las 23:30 locales es del 6 de octubre en UTC: no se pierde.
    assert tarde.creado_en.day == 6


def test_C_05_una_fecha_sin_la_otra_acota_solo_un_lado(cliente_como, datos):
    _, _, guante, casco, ent_juan, ent_ana, ent_con = _escenario_movimientos(datos)
    supervisor = cliente_como("Supervisor")

    desde = pedir(supervisor, MOVIMIENTOS, articulo_id=casco.id, desde="2026-09-22")
    hasta = pedir(supervisor, MOVIMIENTOS, articulo_id=casco.id, hasta="2026-09-22")

    assert _folios(desde) == {ent_con.folio}
    assert _folios(hasta) == {ent_ana.folio}


def test_C_05_los_movimientos_se_paginan_con_elementos_y_total(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante paginado")
    datos.existencia(datos.ub_almacen("KEP"), guante, 100)
    for i in range(5):
        datos.entrega(juan, guante, creado_en=local_a_utc(2026, 9, 1 + i, 12))
    supervisor = cliente_como("Supervisor")

    primera = pedir(supervisor, MOVIMIENTOS, articulo_id=guante.id, pagina=1, tamano=2)
    ultima = pedir(supervisor, MOVIMIENTOS, articulo_id=guante.id, pagina=3, tamano=2)

    assert primera["total"] == 5 and len(primera["elementos"]) == 2
    assert len(ultima["elementos"]) == 1
    assert primera["sin_registros"] is False and primera["mensaje"] is None
    # Más reciente primero.
    assert primera["elementos"][0]["fecha"] > primera["elementos"][1]["fecha"]


def test_C_05_sin_registros_lo_indica_para_mostrar_el_aviso(cliente_como, datos):
    articulo = datos.articulo("Artículo sin movimientos")

    cuerpo = pedir(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=articulo.id)

    assert cuerpo == {
        "elementos": [],
        "total": 0,
        "sin_registros": True,
        "mensaje": "No hay registros con esos filtros.",
    }


def test_C_05_el_csv_de_movimientos_tiene_el_mismo_conteo_que_el_json(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante conteo")
    datos.existencia(datos.ub_almacen("KEP"), guante, 100)
    for i in range(7):
        datos.entrega(juan, guante, creado_en=local_a_utc(2026, 9, 1 + i, 12))
    supervisor = cliente_como("Supervisor")
    filtros = {"articulo_id": guante.id, "desde": "2026-09-02", "hasta": "2026-09-06"}

    cuerpo = pedir(supervisor, MOVIMIENTOS, **filtros)
    filas = filas_csv(pedir_csv(supervisor, MOVIMIENTOS, **filtros))

    assert cuerpo["total"] == 5
    assert len(filas) - 1 == cuerpo["total"]
    assert filas[0] == [
        "Fecha", "Folio", "Tipo", "Código del artículo", "Artículo", "Pieza", "Cantidad",
        "Origen", "Destino", "Responsable", "Trabajador", "Saldo origen", "Saldo destino",
    ]  # fmt: skip
    assert {f[1] for f in filas[1:]} == {e["folio"] for e in cuerpo["elementos"]}


def test_C_05_el_csv_muestra_la_hora_local_de_mexico(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante hora")
    datos.existencia(datos.ub_almacen("KEP"), guante, 5)
    datos.entrega(juan, guante, creado_en=local_a_utc(2026, 10, 5, 23, 30))

    filas = filas_csv(pedir_csv(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=guante.id))

    assert filas[1][0] == "05/10/2026 23:30:00"


def test_C_05_el_csv_conserva_los_acentos_para_excel(cliente_como, datos):
    juan = datos.trabajador("José Ángel Muñoz Peña")
    articulo = datos.articulo("Lámpara de cabeza — ñandú", codigo="ART-ÁÉ-1")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 5)
    datos.entrega(juan, articulo)

    respuesta = pedir_csv(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=articulo.id)

    assert respuesta.content.startswith(b"\xef\xbb\xbf")  # BOM de utf-8-sig
    assert "charset=utf-8" in respuesta.headers["content-type"]
    texto = respuesta.content.decode("utf-8-sig")
    assert "José Ángel Muñoz Peña" in texto
    assert "Lámpara de cabeza — ñandú" in texto
    assert "Código del artículo" in texto and "Destino" in texto


@pytest.mark.parametrize("peligroso", ["=cmd()", "+1+1", "-2+3", "@SUMA(A1)", "\t=1+1"])
def test_C_05_el_csv_neutraliza_la_inyeccion_de_formulas(cliente_como, datos, peligroso):
    juan = datos.trabajador("Juan Pérez")
    articulo = datos.articulo(peligroso)
    datos.existencia(datos.ub_almacen("KEP"), articulo, 5)
    datos.entrega(juan, articulo)

    filas = filas_csv(pedir_csv(cliente_como("Supervisor"), MOVIMIENTOS, articulo_id=articulo.id))

    nombre = filas[1][4]
    assert nombre == "'" + peligroso
    assert not any(c.startswith(("=", "+", "-", "@")) for fila in filas for c in fila)


def test_C_05_la_inyeccion_de_formulas_tambien_se_neutraliza_en_nombres_de_trabajador(
    cliente_como, datos
):
    atacante = datos.trabajador('=HYPERLINK("http://x")')
    guante = datos.articulo("Guante inyección")
    datos.existencia(datos.ub_almacen("KEP"), guante, 5)
    datos.entrega(atacante, guante)

    filas = filas_csv(pedir_csv(cliente_como("Supervisor"), ADEUDOS))

    assert not any(c.startswith("=") for fila in filas for c in fila)


def test_RG_12_el_reporte_de_movimientos_no_muestra_costos(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    articulo = datos.articulo("Equipo costoso de bitácora", costo="31415.92")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 5)
    datos.entrega(juan, articulo)
    compras = cliente_como("Compras")

    json_texto = compras.get(MOVIMIENTOS, params={"articulo_id": str(articulo.id)}).text
    csv_texto = pedir_csv(compras, MOVIMIENTOS, articulo_id=articulo.id).content.decode("utf-8")

    for texto in (json_texto, csv_texto):
        assert "31415.92" not in texto
        assert "costo_unitario" not in texto
        assert "Costo" not in texto


# -------------------------------------------------------------------------------- adeudos


def _escenario_adeudos(datos):
    hoy = hoy_mx()
    vigente = datos.trabajador("Vigente Pérez")
    vencido = datos.trabajador(
        "Vencido Gómez", inicio=hoy - timedelta(days=200), fin=hoy - timedelta(days=5)
    )
    en_baja = datos.trabajador("Baja López", estado="BAJA_EN_PROCESO")
    sin_nada = datos.trabajador("Sin Adeudos")
    taladro = datos.articulo("Taladro adeudos", control="PIEZA")
    marro = datos.articulo("Marro adeudos")
    guante = datos.articulo("Guante consumible adeudos", retornable=False)
    datos.existencia(datos.ub_almacen("KEP"), marro, 20)
    datos.existencia(datos.ub_almacen("CON"), marro, 20)
    datos.existencia(datos.ub_almacen("KEP"), guante, 20)
    pieza = datos.pieza(taladro, datos.ub_almacen("KEP"), serie="SN-ADEUDO-1")
    datos.entrega(
        vigente, taladro, pieza=pieza, creado_en=local_a_utc(2026, 9, 1, 9), almacen="KEP"
    )
    datos.entrega(vigente, marro, cantidad=3, creado_en=local_a_utc(2026, 9, 2, 9), almacen="KEP")
    datos.entrega(
        vencido, marro, cantidad=2, creado_en=local_a_utc(2026, 8, 2, 9), almacen="CON",
        responsable="alm_con",
    )  # fmt: skip
    datos.entrega(en_baja, marro, cantidad=1, creado_en=local_a_utc(2026, 8, 3, 9), almacen="KEP")
    datos.entrega(vigente, guante, cantidad=5)  # consumible: no es adeudo (B-03)
    return vigente, vencido, en_baja, sin_nada, pieza


def _de(cuerpo, *trabajadores):
    ids = {str(t.id) for t in trabajadores}
    return [e for e in cuerpo["elementos"] if e["trabajador_id"] in ids]


def test_C_05_adeudos_dice_que_tiene_cada_trabajador_desde_cuando_y_de_que_almacen(
    cliente_como, datos
):
    vigente, vencido, en_baja, sin_nada, pieza = _escenario_adeudos(datos)

    cuerpo = pedir(cliente_como("Supervisor"), ADEUDOS, tamano=200)

    del_vigente = {e["articulo"]: e for e in _de(cuerpo, vigente)}
    assert set(del_vigente) == {"Taladro adeudos", "Marro adeudos"}  # sin el consumible
    taladro = del_vigente["Taladro adeudos"]
    assert taladro["codigo"] == pieza.codigo and taladro["numero_serie"] == "SN-ADEUDO-1"
    assert taladro["cantidad"] == 1
    assert taladro["almacen_clave"] == "KEP"
    assert taladro["folio"].startswith("KEP-ENT")
    assert taladro["desde"].startswith("2026-09-01T15:00:00")
    assert del_vigente["Marro adeudos"]["cantidad"] == 3
    assert _de(cuerpo, sin_nada) == []
    (de_vencido,) = _de(cuerpo, vencido)
    assert de_vencido["almacen_clave"] == "CON" and de_vencido["cantidad"] == 2


def test_C_05_solo_no_vigentes_deja_a_quienes_ya_no_forman_parte_de_la_plantilla(
    cliente_como, datos
):
    vigente, vencido, en_baja, *_ = _escenario_adeudos(datos)
    supervisor = cliente_como("Supervisor")

    todos = pedir(supervisor, ADEUDOS, tamano=200)
    no_vigentes = pedir(supervisor, ADEUDOS, solo_no_vigentes="true", tamano=200)

    assert _de(todos, vigente) and _de(todos, vencido) and _de(todos, en_baja)
    assert _de(no_vigentes, vigente) == []
    assert {e["trabajador_id"] for e in _de(no_vigentes, vencido, en_baja)} == {
        str(vencido.id),
        str(en_baja.id),
    }
    assert all(e["vigente"] is False and e["motivo_no_vigente"] for e in no_vigentes["elementos"])
    assert all(e["vigente"] is True for e in _de(todos, vigente))


def test_C_11_el_almacenista_solo_ve_los_adeudos_que_entrego_su_almacen(cliente_como, datos):
    vigente, vencido, en_baja, *_ = _escenario_adeudos(datos)

    cuerpo = pedir(cliente_como("Almacenista"), ADEUDOS, tamano=200)

    assert _de(cuerpo, vigente) and _de(cuerpo, en_baja)
    assert _de(cuerpo, vencido) == []  # su marro salió de CON
    assert {e["almacen_clave"] for e in cuerpo["elementos"]} == {"KEP"}


def test_C_11_rh_sin_almacen_ve_los_adeudos_de_todos(cliente_como, datos):
    vigente, vencido, en_baja, *_ = _escenario_adeudos(datos)

    cuerpo = pedir(cliente_como("Recursos Humanos"), ADEUDOS, tamano=200)

    assert _de(cuerpo, vigente) and _de(cuerpo, vencido) and _de(cuerpo, en_baja)


def test_C_05_adeudos_en_csv_respeta_los_filtros_y_tiene_el_mismo_conteo(cliente_como, datos):
    vigente, vencido, en_baja, *_ = _escenario_adeudos(datos)
    supervisor = cliente_como("Supervisor")

    cuerpo = pedir(supervisor, ADEUDOS, solo_no_vigentes="true", tamano=200)
    filas = filas_csv(pedir_csv(supervisor, ADEUDOS, solo_no_vigentes="true"))

    assert len(filas) - 1 == cuerpo["total"]
    assert filas[0][:4] == ["Número de empleado", "Trabajador", "Situación", "Motivo"]
    assert all(fila[2] == "No vigente" for fila in filas[1:])
    nombres = {fila[1] for fila in filas[1:]}
    assert {"Vencido Gómez", "Baja López"} <= nombres
    assert "Vigente Pérez" not in nombres


def test_C_05_adeudos_sin_registros_lo_indica(cliente_como, datos):
    # Nada se entregó desde MIN.
    cuerpo = pedir(cliente_como("Supervisor"), ADEUDOS, almacen_id=datos.almacen("MIN").id)

    assert cuerpo["sin_registros"] is True
    assert cuerpo["mensaje"] == "No hay registros con esos filtros."


def test_RG_12_el_reporte_de_adeudos_no_muestra_costos(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    articulo = datos.articulo("Adeudo costoso", costo="2718.28")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 5)
    datos.entrega(juan, articulo)
    supervisor = cliente_como("Supervisor")

    assert "2718.28" not in supervisor.get(ADEUDOS).text
    assert "2718.28" not in pedir_csv(supervisor, ADEUDOS).content.decode("utf-8")


# --------------------------------------------------------------------------------- consumo


def _escenario_consumo(datos):
    juan = datos.trabajador("Juan Pérez")
    ana = datos.trabajador("Ana Soto")
    guante = datos.articulo("Guante de consumo", retornable=False, unidad="par")
    datos.existencia(datos.ub_almacen("KEP"), guante, 100)
    datos.existencia(datos.ub_almacen("CON"), guante, 100)
    diez = datos.entrega(juan, guante, cantidad=10, creado_en=local_a_utc(2026, 9, 10, 9))
    cinco = datos.entrega(ana, guante, cantidad=5, creado_en=local_a_utc(2026, 9, 11, 9))
    return juan, ana, guante, diez, cinco


def _total(cuerpo, articulo) -> int | None:
    for e in cuerpo["elementos"]:
        if e["articulo_id"] == str(articulo.id):
            return e["total"]
    return None


def test_C_08_el_consumo_suma_las_entregas_de_consumibles_por_trabajador_de_mayor_a_menor(
    cliente_como, datos
):
    juan, ana, guante, *_ = _escenario_consumo(datos)

    cuerpo = pedir(cliente_como("Supervisor"), CONSUMO, articulo_id=guante.id)

    assert cuerpo["total"] == 1
    (item,) = cuerpo["elementos"]
    assert item["total"] == 15
    assert item["unidad"] == "par"
    assert item["articulo"] == "Guante de consumo"
    assert [(t["trabajador"], t["cantidad"]) for t in item["trabajadores"]] == [
        ("Juan Pérez", 10),
        ("Ana Soto", 5),
    ]
    assert item["trabajadores"][0]["numero_empleado"] == juan.numero_empleado


def test_C_08_un_vale_cancelado_no_cuenta_el_total_resta_la_cancelacion(cliente_como, datos):
    """Guion de US-REP-002: diez guantes a uno, cinco a otro, se cancela un vale."""
    juan, ana, guante, diez, cinco = _escenario_consumo(datos)
    supervisor = cliente_como("Supervisor")
    assert _total(pedir(supervisor, CONSUMO, articulo_id=guante.id), guante) == 15

    datos.cancelar(cinco, creado_en=local_a_utc(2026, 9, 12, 9))

    cuerpo = pedir(supervisor, CONSUMO, articulo_id=guante.id)
    (item,) = cuerpo["elementos"]
    assert item["total"] == 10
    assert [(t["trabajador"], t["cantidad"]) for t in item["trabajadores"]] == [("Juan Pérez", 10)]


def test_C_08_un_trabajador_sin_consumo_en_el_periodo_no_aparece(cliente_como, datos):
    juan, ana, guante, diez, cinco = _escenario_consumo(datos)
    datos.cancelar(diez, creado_en=local_a_utc(2026, 9, 12, 9))

    cuerpo = pedir(cliente_como("Supervisor"), CONSUMO, articulo_id=guante.id)

    (item,) = cuerpo["elementos"]
    assert [t["trabajador"] for t in item["trabajadores"]] == ["Ana Soto"]
    assert item["total"] == 5


def test_C_08_si_se_cancela_todo_el_articulo_deja_de_aparecer(cliente_como, datos):
    juan, ana, guante, diez, cinco = _escenario_consumo(datos)
    datos.cancelar(diez, creado_en=local_a_utc(2026, 9, 12, 9))
    datos.cancelar(cinco, creado_en=local_a_utc(2026, 9, 12, 10))

    cuerpo = pedir(cliente_como("Supervisor"), CONSUMO, articulo_id=guante.id)

    assert cuerpo["elementos"] == [] and cuerpo["sin_registros"] is True


def test_C_08_una_cancelacion_posterior_al_periodo_tambien_descuenta_el_vale_cancelado(
    cliente_como, datos
):
    """El vale cancelado no cuenta en ningún periodo: la cancelación se fecha con su vale."""
    juan, ana, guante, diez, cinco = _escenario_consumo(datos)
    datos.cancelar(diez, creado_en=local_a_utc(2026, 10, 20, 9))  # fuera de septiembre
    supervisor = cliente_como("Supervisor")

    septiembre = pedir(
        supervisor, CONSUMO, articulo_id=guante.id, desde="2026-09-01", hasta="2026-09-30"
    )
    octubre = pedir(
        supervisor, CONSUMO, articulo_id=guante.id, desde="2026-10-01", hasta="2026-10-31"
    )

    assert _total(septiembre, guante) == 5  # los diez de Juan ya están cancelados
    assert octubre["elementos"] == []  # y la cancelación no deja un consumo negativo


def test_C_08_los_retornables_no_son_consumo(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    retornable = datos.articulo("Marro retornable", retornable=True)
    datos.existencia(datos.ub_almacen("KEP"), retornable, 5)
    datos.entrega(juan, retornable, cantidad=2)

    cuerpo = pedir(cliente_como("Supervisor"), CONSUMO, articulo_id=retornable.id)

    assert cuerpo["elementos"] == []


def test_C_08_los_filtros_de_periodo_almacen_categoria_articulo_y_trabajador(cliente_como, datos):
    juan, ana, guante, diez, cinco = _escenario_consumo(datos)
    tapon = datos.articulo("Tapón auditivo", retornable=False, unidad="par")
    datos.existencia(datos.ub_almacen("CON"), tapon, 100)
    datos.entrega(
        juan, tapon, cantidad=7, almacen="CON", responsable="alm_con",
        creado_en=local_a_utc(2026, 9, 11, 9),
    )  # fmt: skip
    supervisor = cliente_como("Supervisor")

    por_periodo = pedir(supervisor, CONSUMO, articulo_id=guante.id, desde="2026-09-11",
                        hasta="2026-09-30")  # fmt: skip
    por_almacen = pedir(
        supervisor, CONSUMO, articulo_id=tapon.id, almacen_id=datos.almacen("KEP").id
    )
    en_con = pedir(supervisor, CONSUMO, articulo_id=tapon.id, almacen_id=datos.almacen("CON").id)
    por_categoria = pedir(supervisor, CONSUMO, categoria_id=tapon.categoria_id)
    por_trabajador = pedir(supervisor, CONSUMO, articulo_id=guante.id, trabajador_id=ana.id)

    assert _total(por_periodo, guante) == 5  # solo la entrega del 11
    assert por_almacen["elementos"] == []
    assert _total(en_con, tapon) == 7
    assert [e["articulo_id"] for e in por_categoria["elementos"]] == [str(tapon.id)]
    (item,) = por_trabajador["elementos"]
    assert item["total"] == 5 and [t["trabajador"] for t in item["trabajadores"]] == ["Ana Soto"]


def test_C_11_el_consumo_sin_almacenes_todos_solo_ve_su_almacen(cliente_con, datos):
    juan, ana, guante, *_ = _escenario_consumo(datos)
    datos.entrega(
        juan, guante, cantidad=40, almacen="CON", responsable="alm_con",
        creado_en=local_a_utc(2026, 9, 13, 9),
    )  # fmt: skip
    en_kep = cliente_con(P.REPORTES_CONSUMO, almacen="KEP")
    en_con = cliente_con(P.REPORTES_CONSUMO, almacen="CON")
    supervisor_total = pedir(cliente_con(P.REPORTES_CONSUMO, P.ALMACENES_TODOS), CONSUMO,
                             articulo_id=guante.id)  # fmt: skip

    assert _total(pedir(en_kep, CONSUMO, articulo_id=guante.id), guante) == 15
    assert _total(pedir(en_con, CONSUMO, articulo_id=guante.id), guante) == 40
    assert _total(supervisor_total, guante) == 55
    # Pedir el almacén ajeno no revela nada.
    assert (
        pedir(en_kep, CONSUMO, articulo_id=guante.id, almacen_id=datos.almacen("CON").id)[
            "elementos"
        ]
        == []
    )


def test_C_08_el_consumo_se_pagina_con_elementos_y_total(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    for i in range(3):
        articulo = datos.articulo(f"Consumible paginado {i}", retornable=False)
        datos.existencia(datos.ub_almacen("KEP"), articulo, 10)
        datos.entrega(juan, articulo, cantidad=i + 1, creado_en=local_a_utc(2026, 9, 14, 9))
    supervisor = cliente_como("Supervisor")

    primera = pedir(supervisor, CONSUMO, desde="2026-09-14", hasta="2026-09-14", pagina=1,
                    tamano=2)  # fmt: skip
    segunda = pedir(supervisor, CONSUMO, desde="2026-09-14", hasta="2026-09-14", pagina=2,
                    tamano=2)  # fmt: skip

    assert primera["total"] == 3
    assert len(primera["elementos"]) == 2 and len(segunda["elementos"]) == 1
    assert primera["elementos"][0]["total"] >= primera["elementos"][1]["total"]


def test_C_08_el_csv_de_consumo_respeta_los_filtros_y_neutraliza_formulas(cliente_como, datos):
    juan = datos.trabajador("=Juan Peligroso")
    ana = datos.trabajador("Ana Soto")
    guante = datos.articulo("Guante csv", retornable=False, unidad="par")
    datos.existencia(datos.ub_almacen("KEP"), guante, 50)
    datos.entrega(juan, guante, cantidad=10, creado_en=local_a_utc(2026, 9, 10, 9))
    datos.entrega(ana, guante, cantidad=5, creado_en=local_a_utc(2026, 9, 11, 9))
    supervisor = cliente_como("Supervisor")

    respuesta = pedir_csv(supervisor, CONSUMO, articulo_id=guante.id)
    filas = filas_csv(respuesta)
    solo_ana = filas_csv(
        pedir_csv(supervisor, CONSUMO, articulo_id=guante.id, trabajador_id=ana.id)
    )

    assert filas[0] == [
        "Código", "Artículo", "Categoría", "Unidad", "Total del artículo",
        "Número de empleado", "Trabajador", "Cantidad del trabajador",
    ]  # fmt: skip
    assert len(filas) == 3  # encabezado y un renglón por trabajador
    assert [f[6] for f in filas[1:]] == ["'=Juan Peligroso", "Ana Soto"]
    assert [f[7] for f in filas[1:]] == ["10", "5"]
    assert filas[1][4] == "15" and filas[1][3] == "par"
    assert [f[6] for f in solo_ana[1:]] == ["Ana Soto"]


def test_RG_12_el_reporte_de_consumo_no_muestra_costos(cliente_como, datos):
    juan = datos.trabajador("Juan Pérez")
    articulo = datos.articulo("Consumible caro", retornable=False, costo="1618.03")
    datos.existencia(datos.ub_almacen("KEP"), articulo, 50)
    datos.entrega(juan, articulo, cantidad=3)
    compras = cliente_como("Compras")

    json_texto = compras.get(CONSUMO, params={"articulo_id": str(articulo.id)}).text
    csv_texto = pedir_csv(compras, CONSUMO, articulo_id=articulo.id).content.decode("utf-8")

    for texto in (json_texto, csv_texto):
        assert "1618.03" not in texto
        assert "costo" not in texto.lower()


def test_C_08_un_consumo_atribuido_al_vale_sin_trabajador_en_el_renglon_usa_el_del_vale(
    cliente_como, datos
):
    juan = datos.trabajador("Juan Pérez")
    guante = datos.articulo("Guante sin renglón", retornable=False)
    datos.existencia(datos.ub_almacen("KEP"), guante, 5)
    vale = datos.vale(TipoVale.ENTREGA, "KEP", trabajador=juan, creado_en=ahora_utc())
    datos.movimiento(
        vale, guante, datos.ub_almacen("KEP"), datos.ub_virtual(UbicacionVirtual.CONSUMIDO),
        cantidad=2,
    )  # fmt: skip

    (item,) = pedir(cliente_como("Supervisor"), CONSUMO, articulo_id=guante.id)["elementos"]

    assert item["trabajadores"][0]["trabajador"] == "Juan Pérez"
