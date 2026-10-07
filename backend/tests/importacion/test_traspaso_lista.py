# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""FEAT-009: traspasos por lista de Excel (TR-01 a TR-09).

Una prueba por regla, con su ID en el nombre. El traspaso resultante es un vale común (folio
`CLAVE-TRS`, EN_TRANSITO) que se recibe con el flujo de siempre.
"""

import io
import uuid

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.modulos.almacenes.models import Almacen
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import Vale
from tests.importacion.ayudas import conteos
from tests.movimientos.ayudas import abastecer, crear_articulo, existencia
from tests.movimientos.ayudas_traspasos import (
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    en_transito,
    recibir,
    renglon,
    ubicacion_de_pieza,
)
from tests.movimientos.test_entrega import pieza_en_kep

RAIZ = "/api/importacion/traspasos"
COLUMNAS = {"codigo": 0, "cantidad": 1, "codigo_pieza": 2, "serie": 3}
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def supervisor(cliente_como):
    return cliente_como("Supervisor")  # Kepler: traspasos.operar, sin inventario.entradas


@pytest.fixture
def admin(cliente_como):
    return cliente_como("Administrador")


@pytest.fixture
def compras_kep(cliente_como):
    return cliente_como("Compras")


def art(codigo: str, cantidad: int | str = "") -> list:
    return [codigo, cantidad, "", ""]


def pz(codigo_pieza: str, serie: str = "", codigo: str = "") -> list:
    return [codigo, "", codigo_pieza, serie]


def cuerpo(session, filas, destino="CON", **extra) -> dict:
    return {
        "filas": filas,
        "columnas": COLUMNAS,
        "primera_fila": 2,
        "destino_almacen_id": str(almacen_id(session, destino)),
    } | extra


def confirmacion(session, filas, destino="CON", **extra) -> dict:
    return cuerpo(session, filas, destino, id_lote=str(uuid.uuid4()), **extra)


def vista(cliente, session, filas, destino="CON", **extra) -> dict:
    r = cliente.post(f"{RAIZ}/vista-previa", json=cuerpo(session, filas, destino, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def motivos_de(fila: dict) -> list[str]:
    return [m["regla"] for m in fila["motivos"]]


@pytest.fixture
def guantes(session, compras_kep):
    articulo = crear_articulo(session, retornable=False)
    abastecer(compras_kep, articulo, 10)
    return articulo


def xlsx(filas: list[list]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    for f in filas:
        hoja.append(f)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ------------------------------------------------------------------------------- TR-01


def test_TR_01_el_xlsx_y_la_tabla_pegada_dan_la_misma_vista_previa_sin_escribir(
    supervisor, session, guantes
):
    antes = conteos(session)
    contenido = xlsx([["codigo", "cantidad", "codigo pieza", "serie"], [guantes.codigo, 3, "", ""]])
    r = supervisor.post(
        f"{RAIZ}/archivo",
        files={"archivo": ("lista.xlsx", contenido, TIPO_XLSX)},
        data={"destino_almacen_id": str(almacen_id(session, "CON"))},
    )
    assert r.status_code == 200, r.text
    archivo = r.json()
    assert archivo["columnas"]["codigo"] == 0 and archivo["columnas"]["cantidad"] == 1
    assert archivo["columnas"]["codigo_pieza"] == 2 and archivo["primera_fila"] == 2
    pegada = vista(supervisor, session, archivo["filas"], columnas=archivo["columnas"])
    assert archivo["vista_previa"]["filas"] == pegada["filas"]
    assert pegada["filas"][0]["articulo"] == guantes.nombre
    assert pegada["filas"][0]["nivel"] == "VERDE" and pegada["puede_confirmar"] is True
    assert conteos(session) == antes  # la vista previa no escribe nada


def test_TR_01_un_archivo_malo_es_422_y_la_plantilla_se_descarga(supervisor, session):
    r = supervisor.post(
        f"{RAIZ}/archivo",
        files={"archivo": ("lista.xlsx", b"no es excel", TIPO_XLSX)},
        data={"destino_almacen_id": str(almacen_id(session, "CON"))},
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    plantilla = supervisor.get(f"{RAIZ}/plantilla")
    assert plantilla.status_code == 200 and plantilla.headers["content-type"] == TIPO_XLSX
    assert plantilla.content.startswith(b"PK")


# ------------------------------------------------------------------------------- TR-02


def test_TR_02_un_archivo_es_un_traspaso_con_su_folio_en_transito(
    supervisor, session, guantes, compras_kep
):
    _, p = pieza_en_kep(compras_kep, session)
    r = supervisor.post(RAIZ, json=confirmacion(session, [art(guantes.codigo, 4), pz(p.codigo)]))
    assert r.status_code == 201, r.text
    salida = r.json()
    vale = salida["vale"]
    assert vale["folio"].startswith("KEP-TRS-") and vale["estado"] == "EN_TRANSITO"
    assert vale["origen"]["clave"] == "KEP" and vale["destino"]["clave"] == "CON"
    assert (vale["renglones"], vale["piezas"], vale["unidades"]) == (2, 1, 5)
    assert session.scalar(select(Vale.tipo).where(Vale.folio == vale["folio"])) == "TRASPASO"
    assert existencia(session, "KEP", guantes) == 6 and en_transito(session, guantes) == 4
    assert ubicacion_de_pieza(session, p.codigo) == "EN_TRANSITO"


def test_TR_02_el_destino_debe_ser_otro_y_el_origen_ajeno_solo_con_almacenes_todos(
    supervisor, admin, session, guantes
):
    r = supervisor.post(
        f"{RAIZ}/vista-previa", json=cuerpo(session, [art(guantes.codigo, 1)], "KEP")
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    r = supervisor.post(
        f"{RAIZ}/vista-previa",
        json=cuerpo(session, [art(guantes.codigo, 1)], almacen_id=str(almacen_id(session, "CON"))),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"
    sin_destino = cuerpo(session, [art(guantes.codigo, 1)])
    del sin_destino["destino_almacen_id"]
    assert supervisor.post(f"{RAIZ}/vista-previa", json=sin_destino).status_code == 422
    # Con almacenes.todos el origen se elige con `almacen_id`.
    v = vista(admin, session, [art(guantes.codigo, 1)], almacen_id=str(almacen_id(session, "KEP")))
    assert v["origen"]["clave"] == "KEP"
    r = admin.post(f"{RAIZ}/vista-previa", json=cuerpo(session, [art(guantes.codigo, 1)]))
    assert r.status_code == 422  # el administrador debe indicar el origen


# ------------------------------------------------------------------------------- TR-03


def test_TR_03_sin_traspasos_operar_es_403_en_las_cuatro_rutas(cliente_como, session, guantes):
    almacenista = cliente_como("Almacenista")
    cuerpo_ = confirmacion(session, [art(guantes.codigo, 1)])
    assert almacenista.get(f"{RAIZ}/plantilla").status_code == 403
    assert almacenista.post(f"{RAIZ}/vista-previa", json=cuerpo_).status_code == 403
    assert almacenista.post(RAIZ, json=cuerpo_).status_code == 403
    r = almacenista.post(
        f"{RAIZ}/archivo",
        files={"archivo": ("l.xlsx", xlsx([["codigo"]]), TIPO_XLSX)},
        data={"destino_almacen_id": str(almacen_id(session, "CON"))},
    )
    assert r.status_code == 403


def test_TR_03_traspasos_operar_basta_sin_inventario_entradas_y_este_no_basta(
    cliente_con, session, guantes
):
    solo_traspasos = cliente_con({"traspasos.operar"}, almacen="KEP")
    r = solo_traspasos.post(RAIZ, json=confirmacion(session, [art(guantes.codigo, 2)]))
    assert r.status_code == 201, r.text
    solo_entradas = cliente_con({"inventario.entradas"}, almacen="KEP")
    assert solo_entradas.get(f"{RAIZ}/plantilla").status_code == 403
    assert (
        solo_entradas.post(RAIZ, json=confirmacion(session, [art(guantes.codigo, 1)])).status_code
        == 403
    )


# ------------------------------------------------------------------------------- TR-04


def test_TR_04_las_columnas_extra_se_ignoran_con_aviso_y_el_nombre_sale_del_catalogo(
    supervisor, session, guantes
):
    v = supervisor.post(
        f"{RAIZ}/vista-previa",
        json=cuerpo(
            session,
            [art(guantes.codigo, 2) + ["Nombre del archivo"]],
            columnas=COLUMNAS | {"nombre": 4},
        ),
    )
    assert v.status_code == 200, v.text
    v = v.json()
    assert any("nombre" in a for a in v["avisos"])
    assert v["filas"][0]["articulo"] == guantes.nombre


def test_TR_04_el_mismo_articulo_se_une_por_cantidad(supervisor, session, guantes):
    filas = [art(guantes.codigo, 2), art(guantes.codigo, 3), art(guantes.codigo, "1")]
    v = vista(supervisor, session, filas)
    assert len(v["filas"]) == 1
    f = v["filas"][0]
    assert (f["fila"], f["cantidad"], f["unida_de"]) == (2, 6, [3, 4])
    assert "Unido: filas 2, 3, 4" in v["avisos"]
    assert v["resumen"]["unidades"] == 6


def test_TR_04_la_cantidad_debe_ser_entera_y_nunca_se_redondea_I_13(supervisor, session, guantes):
    v = vista(supervisor, session, [art(guantes.codigo, "0.25"), art(guantes.codigo, "0,25")])
    assert [f["motivos"][0]["codigo"] for f in v["filas"]] == ["CANTIDAD_NO_ENTERA"] * 2
    assert {f["motivos"][0]["regla"] for f in v["filas"]} == {"I-13"}
    assert v["resumen"]["errores"] == 2
    v = vista(
        supervisor, session, [art(guantes.codigo, 0), art(guantes.codigo, ""), art("X", "abc")]
    )
    assert all(f["nivel"] == "ROJO" for f in v["filas"])


def test_TR_04_una_pieza_es_una_fila_y_repetirla_es_error(supervisor, session, compras_kep):
    articulo, p = pieza_en_kep(compras_kep, session)
    v = vista(supervisor, session, [pz(p.codigo), pz(p.codigo)])
    assert v["filas"][0]["nivel"] == "VERDE" and v["filas"][0]["pieza"]["codigo"] == p.codigo
    assert v["filas"][1]["motivos"][0]["codigo"] == "PIEZA_REPETIDA"
    # Un artículo por pieza sin código de pieza, o con una serie que no es la suya.
    v = vista(supervisor, session, [art(articulo.codigo, 1), pz(p.codigo, serie="OTRA-SERIE")])
    assert v["filas"][0]["motivos"][0]["codigo"] == "FALTA_CODIGO_PIEZA"
    assert v["filas"][1]["motivos"][0]["codigo"] == "SERIE_NO_COINCIDE"


# ------------------------------------------------------------------------------- TR-05


def test_TR_05_X_02_sin_existencia_y_pieza_fuera_del_origen_son_rojo(supervisor, session, guantes):
    v = vista(supervisor, session, [art(guantes.codigo, 11)])
    f = v["filas"][0]
    assert f["nivel"] == "ROJO" and f["motivos"][0]["codigo"] == "SIN_EXISTENCIA_EN_ORIGEN"
    assert motivos_de(f) == ["X-02"] and f["disponible_en_origen"] == 10


def test_TR_05_X_02_la_pieza_que_no_esta_en_el_origen_es_rojo(
    cliente_almacen, supervisor, session, compras_kep
):
    _, p = pieza_en_kep(compras_kep, session)
    v = vista(cliente_almacen("CON"), session, [pz(p.codigo)], "KEP")
    f = v["filas"][0]
    assert f["nivel"] == "ROJO" and f["motivos"][0]["codigo"] == "PIEZA_NO_ESTA_EN_ORIGEN"
    assert motivos_de(f) == ["X-02"]


def test_TR_05_X_04_pieza_no_apta_es_amarillo_y_se_confirma(supervisor, session, compras_kep):
    from tests.movimientos.test_traspaso_envio import vigencia

    _, p = pieza_en_kep(compras_kep, session, estado=EstadoPieza.NO_APTO, vigente_hasta=vigencia())
    v = vista(supervisor, session, [pz(p.codigo)])
    assert v["filas"][0]["nivel"] == "AMARILLO" and motivos_de(v["filas"][0]) == ["X-04"]
    assert v["filas"][0]["motivos"][0]["codigo"] == "PIEZA_NO_APTA"
    assert v["resumen"]["avisos"] == 1 and v["puede_confirmar"] is True
    r = supervisor.post(RAIZ, json=confirmacion(session, [pz(p.codigo)]))
    assert r.status_code == 201, r.text


def test_TR_05_X_09_articulo_inactivo_es_verde(supervisor, session, guantes):
    guantes.activo = False
    guantes.motivo_inactivacion = "Ya no se compra"
    session.flush()
    v = vista(supervisor, session, [art(guantes.codigo, 2)])
    assert v["filas"][0]["nivel"] == "VERDE" and motivos_de(v["filas"][0]) == ["X-09"]
    assert v["puede_confirmar"] is True


def test_TR_05_un_codigo_que_no_existe_es_error_y_no_crea_nada(supervisor, session, guantes):
    antes = conteos(session)
    v = vista(supervisor, session, [art("NO-EXISTE-XYZ", 2), ["", 3, "", ""]])
    assert [f["nivel"] for f in v["filas"]] == ["ROJO", "ROJO"]
    assert v["filas"][0]["motivos"][0]["codigo"] == "ARTICULO_NO_EXISTE"
    assert v["filas"][0]["articulo"] is None
    r = supervisor.post(RAIZ, json=confirmacion(session, [art("NO-EXISTE-XYZ", 2)]))
    assert r.status_code == 422 or r.status_code == 409
    assert conteos(session) == antes


def test_TR_05_AL_04_un_almacen_cerrado_se_rechaza(supervisor, session, guantes):
    con = session.scalar(select(Almacen).where(Almacen.clave == "CON"))
    con.estado = "CERRADO"
    session.flush()
    v = vista(supervisor, session, [art(guantes.codigo, 1)])
    assert [m["regla"] for m in v["motivos"]] == ["AL-04"] and v["puede_confirmar"] is False
    antes = conteos(session)
    r = supervisor.post(RAIZ, json=confirmacion(session, [art(guantes.codigo, 1)]))
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"
    assert conteos(session) == antes


def test_TR_05_X_03_sin_almacenes_todos_toda_la_lista_es_rojo_y_confirmar_es_403(
    supervisor, session, guantes
):
    v = vista(supervisor, session, [art(guantes.codigo, 1)], "MID")
    assert v["ruta"] == {
        "habitual": False,
        "nivel": "ROJO",
        "pide_observacion": False,
        "mensaje": v["ruta"]["mensaje"],
    }
    assert v["puede_confirmar"] is False
    antes = conteos(session)
    r = supervisor.post(
        RAIZ, json=confirmacion(session, [art(guantes.codigo, 1)], "MID", observacion="Urgente")
    )
    assert r.status_code == 403 and r.json()["codigo"] == "RUTA_SOLO_ADMINISTRADOR"
    assert conteos(session) == antes


def test_TR_05_X_03_con_almacenes_todos_es_aviso_y_la_observacion_es_obligatoria(
    admin, session, guantes
):
    origen = str(almacen_id(session, "KEP"))
    v = vista(admin, session, [art(guantes.codigo, 1)], "MID", almacen_id=origen)
    assert v["ruta"]["nivel"] == "AMARILLO" and v["ruta"]["pide_observacion"] is True
    assert v["ruta"]["habitual"] is False
    r = admin.post(
        RAIZ, json=confirmacion(session, [art(guantes.codigo, 1)], "MID", almacen_id=origen)
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "observacion"
    r = admin.post(
        RAIZ,
        json=confirmacion(
            session, [art(guantes.codigo, 1)], "MID", almacen_id=origen, observacion="Obra urgente"
        ),
    )
    assert r.status_code == 201, r.text
    assert r.json()["vale"]["destino"]["clave"] == "MID"


# ------------------------------------------------------------------------------- TR-06


def test_TR_06_con_filas_en_rojo_no_se_guarda_nada_todo_o_nada(supervisor, session, guantes):
    antes = conteos(session)
    filas = [art(guantes.codigo, 2), art("NO-EXISTE-XYZ", 1)]
    r = supervisor.post(RAIZ, json=confirmacion(session, filas))
    assert r.status_code == 409 and r.json()["codigo"] == "FILAS_CON_ERROR"
    assert r.json()["detalles"]["filas"][0]["fila"] == 3
    assert conteos(session) == antes
    assert existencia(session, "KEP", guantes) == 10


def test_TR_06_dejar_fuera_las_filas_con_error_deja_constancia_en_el_vale_y_la_auditoria(
    supervisor, session, guantes, compras_kep
):
    tornillos = crear_articulo(session, retornable=False)
    abastecer(compras_kep, tornillos, 5)
    filas = [art(guantes.codigo, 2), art("NO-EXISTE-XYZ", 1), art(tornillos.codigo, 99)]
    r = supervisor.post(RAIZ, json=confirmacion(session, filas, dejar_fuera_errores=True))
    assert r.status_code == 201, r.text
    salida = r.json()
    assert salida["resumen"]["filas_importadas"] == 1
    assert salida["resumen"]["filas_dejadas_fuera"] == 2
    assert [f["fila"] for f in salida["filas_dejadas_fuera"]] == [3, 4]
    vale = session.scalar(select(Vale).where(Vale.folio == salida["vale"]["folio"]))
    assert "2 filas" in vale.observacion and "filas 3, 4" in vale.observacion
    auditoria = session.scalars(
        select(Auditoria).where(Auditoria.accion == "importacion.traspaso")
    ).one()
    assert auditoria.despues["filas_dejadas_fuera"] == [3, 4]
    assert auditoria.despues["folio"] == salida["vale"]["folio"]
    assert len(auditoria.despues["huella"]) == 64
    assert existencia(session, "KEP", guantes) == 8 and existencia(session, "KEP", tornillos) == 5


def test_TR_06_si_todo_esta_en_rojo_ni_dejando_fuera_se_crea_un_traspaso(
    supervisor, session, guantes
):
    antes = conteos(session)
    r = supervisor.post(
        RAIZ, json=confirmacion(session, [art("NO-EXISTE-XYZ", 1)], dejar_fuera_errores=True)
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert conteos(session) == antes


# ------------------------------------------------------------------------------- TR-07


def test_TR_07_mas_de_500_renglones_se_rechaza_y_se_pide_dividir(supervisor, session, guantes):
    filas = [art(f"NO-EXISTE-{i}", 1) for i in range(501)]
    v = vista(supervisor, session, filas)
    assert v["resumen"]["excedido"] is True and v["puede_confirmar"] is False
    antes = conteos(session)
    r = supervisor.post(RAIZ, json=confirmacion(session, filas, dejar_fuera_errores=True))
    assert r.status_code == 422 and r.json()["codigo"] == "TRASPASO_MUY_GRANDE"
    assert conteos(session) == antes
    # 500 exactos no se rechazan por el tope.
    assert vista(supervisor, session, filas[:500])["resumen"]["excedido"] is False


# ------------------------------------------------------------------------------- TR-08


def test_TR_08_el_mismo_id_lote_responde_200_repetida_con_el_mismo_vale(
    supervisor, session, guantes
):
    cuerpo_ = confirmacion(session, [art(guantes.codigo, 2)])
    primera = supervisor.post(RAIZ, json=cuerpo_)
    assert primera.status_code == 201, primera.text
    vales = len(session.scalars(select(Vale.id)).all())
    segunda = supervisor.post(RAIZ, json=cuerpo_)
    assert segunda.status_code == 200 and segunda.json()["repetida"] is True
    assert segunda.json()["vale"]["folio"] == primera.json()["vale"]["folio"]
    assert segunda.json()["vale"]["id"] == primera.json()["vale"]["id"]
    assert len(session.scalars(select(Vale.id)).all()) == vales
    assert existencia(session, "KEP", guantes) == 8


def test_TR_08_el_id_lote_de_otra_persona_es_409(supervisor, admin, session, guantes):
    cuerpo_ = confirmacion(session, [art(guantes.codigo, 1)])
    assert supervisor.post(RAIZ, json=cuerpo_).status_code == 201
    otro = admin.post(RAIZ, json=cuerpo_ | {"almacen_id": str(almacen_id(session, "KEP"))})
    assert otro.status_code == 409


def test_TR_08_el_mismo_archivo_avisa_y_pide_confirmar_repetido(supervisor, session, guantes):
    filas = [art(guantes.codigo, 1)]
    assert vista(supervisor, session, filas)["archivo_repetido"] is None
    assert supervisor.post(RAIZ, json=confirmacion(session, filas)).status_code == 201
    assert vista(supervisor, session, filas)["archivo_repetido"]["fecha"].endswith("Z")
    # Otro lote con el mismo contenido: 409 hasta que se confirme de nuevo de forma expresa.
    r = supervisor.post(RAIZ, json=confirmacion(session, filas))
    assert r.status_code == 409 and r.json()["codigo"] == "ARCHIVO_REPETIDO"
    r = supervisor.post(RAIZ, json=confirmacion(session, filas, confirmar_repetido=True))
    assert r.status_code == 201, r.text
    marcadas = session.scalars(
        select(Auditoria).where(Auditoria.accion == "importacion.traspaso")
    ).all()
    assert [bool(a.despues.get("repetido")) for a in marcadas] == [False, True]
    # Otro destino u otras filas son otro archivo.
    assert vista(supervisor, session, [art(guantes.codigo, 2)])["archivo_repetido"] is None


# ------------------------------------------------------------------------------- TR-09


def test_TR_09_el_traspaso_importado_se_recibe_con_el_flujo_de_siempre(
    supervisor, cliente_almacen, session, guantes, compras_kep
):
    _, p = pieza_en_kep(compras_kep, session)
    r = supervisor.post(RAIZ, json=confirmacion(session, [art(guantes.codigo, 5), pz(p.codigo)]))
    assert r.status_code == 201, r.text
    traspaso = r.json()["vale"]
    destino = cliente_almacen("CON")
    pendientes = destino.get("/api/traspasos/por-recibir").json()
    assert traspaso["folio"] in str(pendientes)
    recibir(destino, traspaso, [renglon(guantes.codigo, 5), renglon(p.codigo)], observacion=None)
    assert existencia(session, "CON", guantes) == 5 and en_transito(session, guantes) == 0
    assert ubicacion_de_pieza(session, p.codigo) == "CON"
    session.expire_all()
    estado = session.scalar(select(Vale.estado).where(Vale.folio == traspaso["folio"]))
    assert estado == "RECIBIDO"


def test_TR_09_la_importacion_solo_escribe_por_movimientos_y_la_vista_previa_no_escribe(
    supervisor, session, guantes
):
    filas = [art(guantes.codigo, 2)]
    antes = conteos(session)
    vista(supervisor, session, filas)
    assert conteos(session) == antes
    supervisor.post(RAIZ, json=confirmacion(session, filas))
    despues = conteos(session)
    assert despues["vales"] == antes["vales"] + 1  # un solo vale
    assert despues["articulos"] == antes["articulos"] and despues["piezas"] == antes["piezas"]
