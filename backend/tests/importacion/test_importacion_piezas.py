"""Importación de piezas y unidad (FEAT-007): I-15 código de pieza automático, I-16 columna
unidad, I-17 serie pendiente, y lo que sigue siendo error (código y serie repetidos, RG-10)."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from openpyxl import load_workbook
from sqlalchemy import delete, select

from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Pieza
from tests.importacion.ayudas import (
    ELECTRICA,
    IMPORTACION,
    MANUAL,
    VISTA_PREVIA,
    articulo,
    confirmacion,
    cuerpo,
    fila,
    unico,
)
from tests.importacion.test_importacion_archivo import ENCABEZADOS, libro, subir
from tests.movimientos.ayudas import crear_articulo, crear_pieza


def vista(cliente, filas, **extra):
    r = cliente.post(VISTA_PREVIA, json=cuerpo(filas, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def importar(cliente, filas, esperado: int = 201, **extra):
    r = cliente.post(IMPORTACION, json=confirmacion(filas, **extra))
    assert r.status_code == esperado, r.text
    return r.json()


def motivos(vp, numero: int) -> list[dict]:
    return next(f["motivos"] for f in vp["filas_error"] if f["fila"] == numero)


# ------------------------------------------------------------------------------ I-15


def test_I_15_la_vista_previa_marca_provisional_el_codigo_de_pieza_que_se_generara(compras):
    codigo = unico("TAL")
    vp = vista(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1"),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=unico("PZA")),
        ],
    )
    generada, propia = vp["filas_validas"]
    assert generada["codigo_pieza_generado"] is True
    assert propia["codigo_pieza_generado"] is False
    assert generada["codigo_pieza"].startswith(f"{codigo}-")
    assert vp["filas_error"] == []


def test_I_15_al_confirmar_se_genera_codigo_del_articulo_guion_consecutivo(compras, session):
    codigo = unico("TAL")
    salida = importar(
        compras,
        [fila(codigo, categoria=ELECTRICA, serie=f"S-{i}") for i in range(3)],
    )
    assert [p["codigo"] for p in salida["piezas_creadas"]] == [
        f"{codigo}-001",
        f"{codigo}-002",
        f"{codigo}-003",
    ]
    assert all(p["codigo_generado"] for p in salida["piezas_creadas"])
    assert salida["resumen"]["piezas"] == 3 and salida["resumen"]["filas_con_error"] == 0
    guardadas = {p.codigo for p in session.scalars(select(Pieza))}
    assert {f"{codigo}-001", f"{codigo}-002", f"{codigo}-003"} <= guardadas


def test_I_15_el_codigo_de_un_articulo_sin_codigo_en_el_archivo_tambien_arma_el_de_la_pieza(
    compras,
):
    salida = importar(
        compras,
        [fila("", nombre=f"Taladro {unico('N')}", categoria=ELECTRICA, serie="S-1")],
    )
    pieza = salida["piezas_creadas"][0]
    assert pieza["articulo"]["codigo"].startswith("HEL-")
    assert pieza["codigo"] == f"{pieza['articulo']['codigo']}-001"


def test_I_15_el_consecutivo_es_por_articulo_y_sigue_al_que_ya_hay_en_la_base(compras, session):
    dueno = crear_articulo(session, control="PIEZA")
    crear_pieza(session, dueno, codigo=f"{dueno.codigo}-007")
    otro = unico("OTR")
    salida = importar(
        compras,
        [
            fila(dueno.codigo, serie="A-1"),
            fila(otro, categoria=ELECTRICA, serie="B-1"),
            fila(dueno.codigo, serie="A-2"),
        ],
    )
    codigos = [p["codigo"] for p in salida["piezas_creadas"]]
    assert f"{dueno.codigo}-008" in codigos and f"{dueno.codigo}-009" in codigos
    assert f"{otro}-001" in codigos


def test_I_15_un_codigo_de_pieza_del_archivo_se_respeta_y_el_generado_lo_salta(compras, session):
    codigo = unico("TAL")
    propio = f"{codigo}-001"  # el que el generador daría primero
    salida = importar(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1"),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=propio),
        ],
    )
    por_serie = {p["numero_serie"]: p for p in salida["piezas_creadas"]}
    assert por_serie["S-2"]["codigo"] == propio and por_serie["S-2"]["codigo_generado"] is False
    assert por_serie["S-1"]["codigo"] == f"{codigo}-002"
    assert por_serie["S-1"]["codigo_generado"] is True


def test_I_15_un_codigo_de_pieza_repetido_sigue_siendo_error(compras, session):
    dueno = crear_articulo(session, control="PIEZA")
    existente = crear_pieza(session, dueno)
    codigo = unico("TAL")
    propio = unico("PZA")
    vp = vista(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza=existente.codigo),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=propio),
            fila(codigo, categoria=ELECTRICA, serie="S-3", codigo_pieza=propio),
        ],
    )
    assert motivos(vp, 1)[0]["codigo"] == "CODIGO_REPETIDO"
    assert motivos(vp, 3)[0]["codigo"] == "CODIGO_REPETIDO"
    assert [f["fila"] for f in vp["filas_validas"]] == [2]


def test_I_15_un_codigo_de_articulo_muy_largo_pide_el_codigo_de_la_pieza(compras):
    largo = "L" * 62
    vp = vista(compras, [fila(largo, categoria=ELECTRICA, serie="S-1")])
    assert motivos(vp, 1)[0]["codigo"] == "DEMASIADO_LARGO"
    assert motivos(vp, 1)[0]["campo"] == "codigo_pieza"


def test_I_15_la_vista_previa_no_escribe_y_la_respuesta_repetida_lista_las_mismas_piezas(
    compras, session
):
    codigo = unico("TAL")
    filas = [fila(codigo, categoria=ELECTRICA, serie=f"S-{i}") for i in range(2)]
    lote = str(uuid.uuid4())
    primera = compras.post(IMPORTACION, json=cuerpo(filas, id_lote=lote))
    assert primera.status_code == 201, primera.text
    segunda = compras.post(IMPORTACION, json=cuerpo(filas, id_lote=lote))
    assert segunda.status_code == 200 and segunda.json()["repetida"] is True
    esperado = [(p["codigo"], p["codigo_generado"]) for p in primera.json()["piezas_creadas"]]
    real = [(p["codigo"], p["codigo_generado"]) for p in segunda.json()["piezas_creadas"]]
    assert sorted(real) == sorted(esperado) and len(real) == 2


# ------------------------------------------------------------------------------ I-17


def test_I_17_una_pieza_sin_serie_entra_con_aviso_y_serie_pendiente(compras, session):
    codigo = unico("TAL")
    filas = [
        fila(codigo, categoria=ELECTRICA, serie="", codigo_pieza=unico("PZA")),
        fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=unico("PZA")),
    ]
    vp = vista(compras, filas)
    assert vp["filas_error"] == [] and vp["resumen"]["series_pendientes"] == 1
    sin_serie, con_serie = vp["filas_validas"]
    assert sin_serie["serie_pendiente"] is True and con_serie["serie_pendiente"] is False
    assert any("Serie pendiente" in a for a in sin_serie["avisos"])
    assert not any("Serie pendiente" in a for a in con_serie["avisos"])

    salida = importar(compras, filas)
    assert salida["resumen"]["series_pendientes"] == 1 and salida["resumen"]["piezas"] == 2
    pendientes = [p for p in salida["piezas_creadas"] if p["serie_pendiente"]]
    assert len(pendientes) == 1 and pendientes[0]["numero_serie"] is None
    guardada = session.scalar(select(Pieza).where(Pieza.codigo == pendientes[0]["codigo"]))
    assert guardada.numero_serie is None


def test_I_17_varias_piezas_sin_serie_del_mismo_articulo_no_cuentan_como_repetidas(compras):
    codigo = unico("TAL")
    vp = vista(compras, [fila(codigo, categoria=ELECTRICA) for _ in range(3)])
    assert vp["filas_error"] == [] and vp["resumen"]["series_pendientes"] == 3


def test_I_17_una_serie_repetida_en_la_base_o_en_el_archivo_sigue_siendo_error(compras, session):
    dueno = crear_articulo(session, control="PIEZA")
    existente = crear_pieza(session, dueno)
    serie_base = session.scalar(select(Pieza.numero_serie).where(Pieza.id == existente.id))
    vp = vista(
        compras,
        [
            fila(dueno.codigo, serie=serie_base),
            fila(dueno.codigo, serie="NUEVA-1"),
            fila(dueno.codigo, serie="NUEVA-1"),
        ],
    )
    assert motivos(vp, 1)[0]["codigo"] == "SERIE_REPETIDA"
    assert motivos(vp, 3)[0]["codigo"] == "SERIE_REPETIDA"
    assert [f["fila"] for f in vp["filas_validas"]] == [2]


# ------------------------------------------------------------------------------ I-16


def test_I_16_la_unidad_del_archivo_se_usa_al_crear_el_articulo_y_por_omision_es_pieza(
    compras, session
):
    con, sin = unico("CAB"), unico("CIN")
    vp = vista(
        compras,
        [
            fila(con, cantidad=100, unidad="metro"),
            fila(sin, cantidad=5),
        ],
    )
    assert [f["unidad"] for f in vp["filas_validas"]] == ["metro", "pieza"]
    assert [n["unidad"] for n in vp["articulos_nuevos"]] == ["metro", "pieza"]
    salida = importar(compras, [fila(con, cantidad=100, unidad="metro"), fila(sin, cantidad=5)])
    assert {a["codigo"]: a["unidad"] for a in salida["articulos_creados"]} == {
        con: "metro",
        sin: "pieza",
    }
    assert articulo(session, con).unidad == "metro"
    assert articulo(session, sin).unidad == "pieza"


def test_I_16_en_un_articulo_que_ya_existe_la_unidad_no_cambia_y_avisa_si_difiere(compras, session):
    existente = crear_articulo(session, unidad="caja")
    vp = vista(
        compras,
        [
            fila(existente.codigo, cantidad=2, unidad="metro"),
            fila(existente.codigo, cantidad=1, unidad="Caja"),
        ],
    )
    primera = vp["filas_validas"][0]
    assert primera["unidad"] == "caja"
    avisos = [a for a in primera["avisos"] if "unidad" in a.lower()]
    assert avisos == ["La unidad del archivo es distinta de la registrada; no se cambia."]
    importar(compras, [fila(existente.codigo, cantidad=2, unidad="metro")])
    session.refresh(existente)
    assert existente.unidad == "caja"


def test_I_16_la_unidad_pasa_de_20_caracteres_es_error_y_no_convierte_cantidades(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), cantidad=1, unidad="u" * 21),
            fila(unico("B"), cantidad="0.25", unidad="kilo"),
        ],
    )
    assert (
        motivos(vp, 1)[0]["codigo"] == "DEMASIADO_LARGO" and motivos(vp, 1)[0]["campo"] == "unidad"
    )
    # I-13 intacta: con unidad «kilo» la cantidad decimal sigue rechazándose, sin convertir.
    assert motivos(vp, 2)[0]["codigo"] == "CANTIDAD_NO_ENTERA"


def test_I_16_la_columna_unidad_se_reconoce_por_su_encabezado_en_el_archivo(compras):
    for encabezado in ("Unidad", "Unidad de medida", "U.M.", "Medida"):
        contenido = libro(
            [[unico("A"), "Cable", "", MANUAL, 10, "KEP", "", "", "", "metro"]],
            ENCABEZADOS + [encabezado],
        )
        r = subir(compras, contenido)
        assert r.status_code == 200, r.text
        assert r.json()["columnas"]["unidad"] == 9, encabezado
        assert r.json()["vista_previa"]["filas_validas"][0]["unidad"] == "metro"


def test_I_16_la_plantilla_de_alta_trae_la_columna_unidad(compras):
    r = compras.get("/api/importacion/plantilla", params={"modo": "ALTA"})
    assert r.status_code == 200, r.text
    import io

    hoja = load_workbook(io.BytesIO(r.content)).worksheets[0]
    encabezados = [c.value for c in hoja[1]]
    assert "Unidad" in encabezados


# ------------------------------------------------------------------------------ concurrencia


def test_I_15_dos_importaciones_simultaneas_con_piezas_sin_codigo_no_repiten_codigos(
    cliente_independiente, sesion_independiente, limpieza
):
    codigo = f"TAL-{uuid.uuid4().hex[:6]}"
    filas = [fila(codigo, nombre=f"Taladro {codigo}", categoria=ELECTRICA) for _ in range(3)]
    lotes = [str(uuid.uuid4()), str(uuid.uuid4())]
    clientes = [cliente_independiente("Compras"), cliente_independiente("Compras")]
    barrera = threading.Barrier(2)

    def correr(i):
        barrera.wait(timeout=30)
        return clientes[i].post(
            IMPORTACION, json=cuerpo(filas, id_lote=lotes[i], confirmar_repetido=True)
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(correr, range(2)))
        buenas = [r for r in respuestas if r.status_code == 201]
        assert buenas, [r.text for r in respuestas]
        assert all(r.status_code in (201, 409, 422) for r in respuestas), [
            r.text for r in respuestas
        ]
        s = sesion_independiente()
        articulos = list(s.scalars(select(Articulo).where(Articulo.codigo == codigo)))
        assert len(articulos) == 1
        limpieza.articulos.append(articulos[0].id)
        codigos = list(s.scalars(select(Pieza.codigo).where(Pieza.articulo_id == articulos[0].id)))
        assert len(codigos) == 3 * len(buenas)
        assert len(set(codigos)) == len(codigos)  # ningún código de pieza repetido
        assert all(c.startswith(f"{codigo}-") for c in codigos)
    finally:
        s = sesion_independiente()
        s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_(lotes)))
        s.commit()
