"""Subir un `.xlsx` (US-IMP-001): lectura segura. I-06 y límites del archivo."""

import io
import zipfile

from openpyxl import Workbook

from app.modulos.acceso.permisos import P
from tests.importacion.ayudas import ARCHIVO, ELECTRICA, IMPORTACION, MANUAL, conteos, unico

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ENCABEZADOS = [
    "Código",
    "Descripción",
    "Marca",
    "Categoría",
    "Cantidad",
    "Almacén",
    "Número de serie",
    "Costo unitario",
    "Código de pieza",
]


def libro(filas: list[list], encabezados: list | None = ENCABEZADOS, antes: int = 0) -> bytes:
    wb = Workbook()
    ws = wb.active
    for _ in range(antes):
        ws.append([])
    if encabezados is not None:
        ws.append(encabezados)
    for f in filas:
        ws.append(f)
    memoria = io.BytesIO()
    wb.save(memoria)
    return memoria.getvalue()


def subir(cliente, contenido: bytes, nombre: str = "inventario.xlsx"):
    return cliente.post(ARCHIVO, files={"archivo": (nombre, contenido, MIME)})


def error(r, mensaje_contiene: str | None = None):
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["codigo"] == "DATOS_INVALIDOS"
    if mensaje_contiene:
        assert mensaje_contiene in cuerpo["mensaje"]
    return cuerpo


# ------------------------------------------------------------------------- lo válido


def test_I_06_un_xlsx_valido_devuelve_filas_columnas_propuestas_y_vista_previa(compras, session):
    codigo, pieza = unico("ART"), unico("PZA")
    antes = conteos(session)
    contenido = libro(
        [
            [codigo, "Martillo", "Truper", MANUAL, 12, "Kepler", None, 85.5, None],
            [unico("TAL"), "Taladro", "DeWalt", ELECTRICA, None, "KEP", "SN-77", 4200, pieza],
        ]
    )
    r = subir(compras, contenido)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["encabezados"] == ENCABEZADOS and cuerpo["primera_fila"] == 2
    assert cuerpo["columnas"] == {
        "codigo": 0,
        "nombre": 1,
        "marca": 2,
        "categoria": 3,
        "cantidad": 4,
        "almacen": 5,
        "serie": 6,
        "costo": 7,
        "codigo_pieza": 8,
        "unidad": None,  # el archivo de ejemplo no trae la columna opcional (I-16)
    }
    assert cuerpo["filas"][0][:5] == [codigo, "Martillo", "Truper", MANUAL, "12"]
    vp = cuerpo["vista_previa"]
    assert vp["resumen"]["validas"] == 2 and vp["resumen"]["piezas"] == 1
    assert vp["filas_validas"][0]["costo"] == "85.50"
    assert conteos(session) == antes  # subir el archivo no escribe nada


def test_I_06_las_filas_del_archivo_se_pueden_confirmar_con_las_columnas_propuestas(
    compras, session
):
    codigo = unico("ART")
    r = subir(compras, libro([[codigo, "Cinta", "3M", MANUAL, 9, "KEP", None, None, None]]))
    cuerpo = r.json()
    confirmacion = compras.post(
        IMPORTACION,
        json={
            "filas": cuerpo["filas"],
            "columnas": cuerpo["columnas"] | {},
            "primera_fila": cuerpo["primera_fila"],
            "id_lote": "00000000-0000-4000-8000-000000000042",
        },
    )
    assert confirmacion.status_code == 201, confirmacion.text
    assert confirmacion.json()["resumen"]["unidades"] == 9


def test_I_06_encabezados_en_otro_orden_con_otros_nombres_y_filas_arriba(compras):
    contenido = libro(
        [["Kepler", "7", "Pinzas", "PIN-1"]],
        encabezados=["Bodega", "Existencias", "Producto", "Clave"],
        antes=2,
    )
    r = subir(compras, contenido)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["primera_fila"] == 4  # dos filas vacías, encabezado en la 3, datos desde la 4
    assert cuerpo["columnas"]["almacen"] == 0 and cuerpo["columnas"]["codigo"] == 3
    vp = cuerpo["vista_previa"]
    # Sin categoría en el archivo: «Pinzas» trae una sugerencia (I-14) que no se aplica sola.
    fila_vista = vp["filas_validas"][0]
    assert fila_vista["fila"] == cuerpo["primera_fila"]
    assert fila_vista["categoria"] is None
    assert fila_vista["categoria_sugerida"]["nombre"] == MANUAL


def test_I_06_celdas_numericas_y_filas_vacias_en_medio(compras):
    contenido = libro(
        [
            [1001, "Llave", "Urrea", MANUAL, 3.0, "KEP", None, None, None],
            [None] * 9,
            [1002, "Dado", "Urrea", MANUAL, "abc", "KEP", None, None, None],
        ]
    )
    vp = subir(compras, contenido).json()["vista_previa"]
    assert vp["filas_validas"][0]["codigo"] == "1001" and vp["filas_validas"][0]["cantidad"] == 3
    assert vp["resumen"]["vacias"] == 1
    assert vp["filas_error"][0]["fila"] == 4  # el encabezado es la fila 1: la vacía, la 3


def test_I_06_sin_la_columna_del_codigo_no_hay_vista_previa_pero_si_las_filas(compras):
    contenido = libro([["Algo", 1]], encabezados=["Detalle", "Cantidad"])
    cuerpo = subir(compras, contenido).json()
    assert cuerpo["vista_previa"] is None and cuerpo["columnas"]["codigo"] is None
    assert cuerpo["filas"] == [["Algo", "1"]]


def test_I_06_una_formula_no_se_ejecuta(compras):
    """Con `data_only` se lee el último valor guardado: una fórmula escrita por otra
    herramienta (sin valor guardado) queda vacía; nunca se calcula ni se toma como texto."""
    wb = Workbook()
    ws = wb.active
    ws.append(ENCABEZADOS)
    ws.append([unico("F"), "=1+1", '=HYPERLINK("http://malo")', MANUAL, "=2*5", "KEP"])
    ws.append([unico("G"), "Normal", "Marca", MANUAL, 4, "KEP"])
    memoria = io.BytesIO()
    wb.save(memoria)
    cuerpo = subir(compras, memoria.getvalue()).json()
    primera = cuerpo["filas"][0]
    assert primera[1] == "" and primera[2] == "" and primera[4] == ""  # no se evaluaron
    assert "2" not in primera[1:5] and "10" not in primera
    vp = cuerpo["vista_previa"]
    assert [f["fila"] for f in vp["filas_error"]] == [2]
    assert vp["filas_error"][0]["motivos"][0]["codigo"] == "FALTA_NOMBRE"
    assert [f["fila"] for f in vp["filas_validas"]] == [3]


def test_I_06_un_texto_con_forma_de_formula_en_el_archivo_se_lee_como_texto(compras):
    wb = Workbook()
    ws = wb.active
    ws.append(ENCABEZADOS)
    ws.append([unico("F"), "x", "m", MANUAL, 2, "KEP"])
    celda = ws["B2"]
    celda.value = "=1+1"
    celda.data_type = "s"  # texto que empieza con "=": no es una fórmula
    memoria = io.BytesIO()
    wb.save(memoria)
    vp = subir(compras, memoria.getvalue()).json()["vista_previa"]
    assert vp["filas_validas"][0]["nombre"] == "=1+1"


# ----------------------------------------------------------------------- lo rechazado


def test_I_06_un_xlsm_con_macros_se_rechaza_por_su_extension(compras):
    error(subir(compras, libro([["a"]]), nombre="inventario.xlsm"), "macros")


def test_I_06_un_libro_con_macros_se_rechaza_aunque_se_llame_xlsx(compras):
    base = libro([[unico("A"), "x", "m", MANUAL, 1, "KEP"]])
    contenido = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base)) as origen, zipfile.ZipFile(contenido, "w") as destino:
        for info in origen.infolist():
            datos = origen.read(info.filename)
            if info.filename == "[Content_Types].xml":
                datos = datos.replace(
                    b"spreadsheetml.sheet.main+xml", b"ms-excel.sheet.macroEnabled.main+xml"
                )
            destino.writestr(info.filename, datos)
        destino.writestr("xl/vbaProject.bin", b"\x00macro")
    error(subir(compras, contenido.getvalue()), "macros")


def test_I_06_un_archivo_de_texto_con_extension_xlsx_se_rechaza(compras):
    error(subir(compras, b"codigo,nombre\nA,B\n"), "Excel")


def test_I_06_un_zip_que_no_es_excel_se_rechaza(compras):
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("hola.txt", "hola")
    error(subir(compras, memoria.getvalue()), "Excel")


def test_I_06_un_zip_roto_se_rechaza(compras):
    base = libro([["a"]])
    error(subir(compras, base[: len(base) // 2]))


def test_I_06_extensiones_que_no_son_xlsx_se_rechazan(compras):
    for nombre in ("datos.xls", "datos.csv", "datos.txt", "datos", "datos.xlsb"):
        error(subir(compras, libro([["a"]]), nombre=nombre))


def test_I_06_un_archivo_vacio_o_solo_con_encabezados_se_rechaza(compras):
    error(subir(compras, b""), "vacío")
    error(subir(compras, libro([])), "encabezados")
    wb = Workbook()
    memoria = io.BytesIO()
    wb.save(memoria)
    error(subir(compras, memoria.getvalue()), "no trae datos")


def test_I_06_un_archivo_muy_grande_se_rechaza(compras):
    grande = b"PK\x03\x04" + b"0" * (5 * 1024 * 1024 + 10)
    error(subir(compras, grande), "pesa más")


def test_I_06_demasiadas_filas_se_rechazan(compras):
    filas = [[unico("F"), "n", "m", MANUAL, 1, "KEP"] for _ in range(5001)]
    error(subir(compras, libro(filas)), "demasiadas filas")


def test_I_06_demasiadas_columnas_se_rechazan(compras):
    error(subir(compras, libro([["a"] * 31], encabezados=[f"c{i}" for i in range(31)])), "columnas")


def test_I_06_una_hoja_con_una_celda_lejana_no_hace_trabajar_de_mas(compras):
    wb = Workbook()
    ws = wb.active
    ws.append(ENCABEZADOS)
    ws["A1048576"] = "lejos"
    memoria = io.BytesIO()
    wb.save(memoria)
    error(subir(compras, memoria.getvalue()), "demasiadas filas")


def test_I_06_una_celda_enorme_se_rechaza(compras):
    error(subir(compras, libro([["x" * 600, "n", "m", MANUAL, 1, "KEP"]])), "celda")


def test_I_06_un_zip_bomba_se_rechaza_sin_descomprimirlo(compras):
    """Pesa pocos KB comprimido y declara cientos de MB descomprimido."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "x")
        z.writestr("xl/workbook.xml", "x")
        z.writestr("xl/worksheets/sheet1.xml", b"0" * (80 * 1024 * 1024))
    assert len(memoria.getvalue()) < 1024 * 1024
    error(subir(compras, memoria.getvalue()), "demasiado grande")


def test_I_06_un_xml_malicioso_dentro_del_xlsx_da_un_error_claro_y_no_un_500(compras):
    base = libro([[unico("A"), "x", "m", MANUAL, 1, "KEP"]])
    contenido = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base)) as origen, zipfile.ZipFile(contenido, "w") as destino:
        for info in origen.infolist():
            datos = origen.read(info.filename)
            if info.filename.startswith("xl/worksheets/sheet1"):
                datos = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>'
            destino.writestr(info.filename, datos)
    r = subir(compras, contenido.getvalue())
    assert r.status_code in (200, 422), r.text  # nunca 500


def test_I_06_sin_el_campo_archivo_da_422(compras):
    r = compras.post(ARCHIVO, files={"otro": ("a.xlsx", b"x", MIME)})
    assert r.status_code == 422


def test_I_06_el_archivo_exige_inventario_entradas(cliente_con):
    sin_permiso = cliente_con({P.CATALOGO_VER})
    assert subir(sin_permiso, libro([["a"]])).status_code == 403


def test_RG_12_sin_catalogo_costos_el_costo_del_archivo_no_vuelve_en_la_respuesta(cliente_con):
    sin_costos = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS, P.CATALOGO_ADMINISTRAR})
    r = subir(sin_costos, libro([[unico("C"), "Cosa", "m", MANUAL, 1, "KEP", None, 777.77, None]]))
    assert r.status_code == 200, r.text
    vp = r.json()["vista_previa"]
    assert "costo" not in vp["filas_validas"][0] and any("costo" in a for a in vp["avisos"])
