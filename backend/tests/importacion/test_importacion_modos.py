"""Importación por modos (US-IMP-001 ampliada, US-IMP-002, FEAT-007): I-04, I-06, I-10, I-11, I-12,
I-13, RG-10 (consolidación) y la plantilla."""

import io
import uuid
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.config import get_settings
from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from app.modulos.importacion.analisis import parsear_cantidad
from app.modulos.importacion.lectura import leer_xlsx, proponer_columnas
from tests.importacion.ayudas import (
    ELECTRICA,
    IMPORTACION,
    MANUAL,
    VISTA_PREVIA,
    articulo,
    categoria_id,
    confirmacion,
    conteos,
    cuerpo,
    fila,
    unico,
)
from tests.movimientos.ayudas import crear_articulo, existencia

PLANTILLA = "/api/importacion/plantilla"
ARCHIVO_URL = "/api/importacion/archivo"
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONSUMIBLES = "Consumibles de trabajo"
EPP_BASICO = "EPP básico"


def vista(cliente, filas, esperado: int = 200, **extra):
    r = cliente.post(VISTA_PREVIA, json=cuerpo(filas, **extra))
    assert r.status_code == esperado, r.text
    return r.json()


def importar(cliente, filas, esperado: int = 201, **extra):
    cuerpo_ = cuerpo(filas, **extra) if "id_lote" in extra else confirmacion(filas, **extra)
    r = cliente.post(IMPORTACION, json=cuerpo_)
    assert r.status_code == esperado, r.text
    return r.json()


def motivos(vp, numero: int) -> list[dict]:
    return next(f["motivos"] for f in vp["filas_error"] if f["fila"] == numero)


def valida(vp, numero: int) -> dict:
    return next(f for f in vp["filas_validas"] if f["fila"] == numero)


# ------------------------------------------------------------------------------ I-10: modos


def test_I_10_sin_modo_el_cuerpo_se_interpreta_como_alta_y_otro_valor_da_422(compras):
    vp = vista(compras, [fila(unico("NUE"), cantidad=2)])
    assert vp["modo"] == "ALTA" and vp["filas_validas"][0]["estado"] == "NUEVO"
    r = compras.post(VISTA_PREVIA, json=cuerpo([fila(unico("X"), cantidad=1)], modo="OTRO"))
    assert r.status_code == 422


def test_I_10_reposicion_un_codigo_que_no_existe_es_error_y_no_crea_nada(compras, session):
    existente = crear_articulo(session, nombre="Pinzas")
    desconocido = unico("NOEXISTE")
    antes = conteos(session)
    vp = vista(
        compras,
        [fila(desconocido, cantidad=3), fila(existente.codigo, cantidad=4)],
        modo="REPOSICION",
    )
    assert vp["modo"] == "REPOSICION"
    assert [f["fila"] for f in vp["filas_error"]] == [1]
    motivo = motivos(vp, 1)[0]
    assert motivo["regla"] == "I-10" and motivo["codigo"] == "ARTICULO_NO_EXISTE"
    assert motivo["mensaje"] == "Ese artículo no existe: dalo de alta primero."
    assert vp["resumen"]["articulos_nuevos"] == 0 and vp["resumen"]["existentes"] == 1
    assert conteos(session) == antes

    salida = importar(
        compras,
        [fila(desconocido, cantidad=3), fila(existente.codigo, cantidad=4)],
        modo="REPOSICION",
    )
    assert salida["modo"] == "REPOSICION" and salida["articulos_creados"] == []
    assert salida["resumen"]["filas_importadas"] == 1 and salida["resumen"]["existentes"] == 1
    assert articulo(session, desconocido) is None  # nunca crea
    assert existencia(session, "KEP", existente) == 4  # las demás filas sí entran


def test_I_10_reposicion_ignora_nombre_marca_categoria_y_costo_con_aviso(compras, session):
    existente = crear_articulo(session, nombre="Pinzas", costo_unitario=Decimal("10.00"))
    vp = vista(
        compras,
        [
            fila(
                existente.codigo,
                nombre="Otro",
                marca="Otra",
                categoria=ELECTRICA,
                cantidad=2,
                costo="999",
            )
        ],
        modo="REPOSICION",
    )
    assert any("Se ignoraron" in a and "costo" in a for a in vp["avisos"])
    f = vp["filas_validas"][0]
    assert f["estado"] == "EXISTENTE" and f["nombre"] == "Pinzas"
    assert f["categoria_sugerida"] is None and "costo" not in f
    assert f["avisos"] == []  # no compara nombre, marca ni categoría: se ignoran
    importar(
        compras,
        [fila(existente.codigo, nombre="Otro", categoria=ELECTRICA, cantidad=2, costo="999")],
        modo="REPOSICION",
    )
    session.refresh(existente)
    assert existente.costo_unitario == Decimal("10.00") and existente.nombre == "Pinzas"
    assert existencia(session, "KEP", existente) == 2


def test_I_10_reposicion_exige_la_columna_del_codigo_y_en_alta_basta_el_nombre(compras):
    solo_nombre = {"filas": [["Pinzas", "3"]], "columnas": {"nombre": 0, "cantidad": 1}}
    r = compras.post(VISTA_PREVIA, json={**solo_nombre, "modo": "REPOSICION"})
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert compras.post(VISTA_PREVIA, json=solo_nombre).status_code == 200  # ALTA
    sin_ninguna = {"filas": [["3"]], "columnas": {"cantidad": 0}}
    assert compras.post(VISTA_PREVIA, json=sin_ninguna).status_code == 422


def test_I_10_reposicion_no_pide_catalogo_administrar(cliente_con, session):
    solo_entradas = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS})
    existente = crear_articulo(session)
    salida = importar(solo_entradas, [fila(existente.codigo, cantidad=5)], modo="REPOSICION")
    assert salida["resumen"]["filas_importadas"] == 1
    assert existencia(session, "KEP", existente) == 5


def test_I_10_SIN_PERMISO_CREAR_el_alta_que_crea_exige_catalogo_administrar(cliente_con, session):
    sin_administrar = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS})
    existente = crear_articulo(session)
    nuevo = unico("NUEVO")
    filas = [fila(nuevo, cantidad=1), fila(existente.codigo, cantidad=2)]
    vp = vista(sin_administrar, filas)
    assert (
        motivos(vp, 1)[0]["codigo"] == "SIN_PERMISO_CREAR" and motivos(vp, 1)[0]["regla"] == "I-10"
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [2]  # los que ya existen sí entran
    salida = importar(sin_administrar, filas)
    assert salida["resumen"]["filas_importadas"] == 1 and salida["articulos_creados"] == []
    assert articulo(session, nuevo) is None and existencia(session, "KEP", existente) == 2


# ------------------------------------------------------------------------------ I-11


def test_I_11_una_cantidad_mayor_al_tope_por_fila_es_error(compras):
    vp = vista(
        compras,
        [fila(unico("A"), cantidad=100_000), fila(unico("B"), cantidad=100_001)],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [1]
    motivo = motivos(vp, 2)[0]
    assert motivo["regla"] == "I-11" and motivo["codigo"] == "CANTIDAD_EXCESIVA"


def test_I_11_el_tope_se_ajusta_por_configuracion(compras, monkeypatch):
    monkeypatch.setattr(get_settings(), "importacion_cantidad_maxima", 50)
    vp = vista(compras, [fila(unico("A"), cantidad=50), fila(unico("B"), cantidad=51)])
    assert [f["fila"] for f in vp["filas_validas"]] == [1]
    assert motivos(vp, 2)[0]["codigo"] == "CANTIDAD_EXCESIVA"


# ------------------------------------------------------------------------------ I-13


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("10", (10, None)),
        ("12.0", (12, None)),
        ("1,000", (1000, None)),
        ("1,250", (1250, None)),
        ("1,250,000", (1250000, None)),
        ("1,250.00", (1250, None)),
        ("0.25", (None, "NO_ENTERA")),
        ("0,25", (None, "NO_ENTERA")),
        ("1,5", (None, "NO_ENTERA")),
        ("1,2500", (None, "NO_ENTERA")),
        ("12,00", (None, "NO_ENTERA")),
        ("2.5", (None, "NO_ENTERA")),
        ("abc", (None, "INVALIDA")),
        ("", (None, "INVALIDA")),
        ("1e3", (None, "INVALIDA")),
    ],
)
def test_I_13_la_cantidad_es_un_entero_y_nunca_se_redondea(texto, esperado):
    assert parsear_cantidad(texto) == esperado


def test_I_13_una_cantidad_con_decimales_se_rechaza_con_un_mensaje_que_pide_una_unidad_menor(
    compras,
):
    vp = vista(
        compras,
        [
            fila(unico("A"), cantidad="0.25"),
            fila(unico("B"), cantidad="0,25"),
            fila(unico("C"), cantidad="1,250"),
        ],
    )
    for numero in (1, 2):
        motivo = motivos(vp, numero)[0]
        assert motivo["regla"] == "I-13" and motivo["codigo"] == "CANTIDAD_NO_ENTERA"
        assert "250 gramos en lugar de 0.25 kilos" in motivo["mensaje"]
    assert valida(vp, 3)["cantidad"] == 1250


# ------------------------------------------------------------------------------ I-12


def test_I_12_un_archivo_ya_importado_avisa_y_pide_confirmar_repetido(compras, session):
    codigo = unico("REP")
    filas = [fila(codigo, nombre="Cinta", cantidad=5), fila(unico("OTRA"), cantidad=1)]
    assert vista(compras, filas)["archivo_repetido"] is None
    primera = importar(compras, filas)
    assert primera["resumen"]["filas_importadas"] == 2

    # Mismo archivo, en otro orden: la huella es la misma. Es un aviso, no un error.
    vp = vista(compras, list(reversed(filas)))
    assert vp["archivo_repetido"]["fecha"].endswith("Z") and vp["resumen"]["validas"] == 2

    antes = conteos(session)
    r = compras.post(IMPORTACION, json=confirmacion(filas))
    assert r.status_code == 409 and r.json()["codigo"] == "ARCHIVO_REPETIDO"
    assert r.json()["detalles"]["regla"] == "I-12" and r.json()["detalles"]["fecha"]
    assert conteos(session) == antes  # no se escribió nada

    segunda = importar(compras, filas, confirmar_repetido=True)
    assert segunda["resumen"]["filas_importadas"] == 2
    assert existencia(session, "KEP", articulo(session, codigo)) == 10


def test_I_12_la_huella_queda_en_la_auditoria_y_distingue_el_modo(compras, session):
    codigo = unico("HUE")
    filas = [fila(codigo, nombre="Cinta", cantidad=5)]
    lote = str(uuid.uuid4())
    importar(compras, filas, id_lote=lote)
    registro = session.scalar(
        select(Auditoria).where(
            Auditoria.accion == "importacion.confirmar", Auditoria.entidad_id == lote
        )
    )
    assert registro.despues["modo"] == "ALTA" and "repetido" not in registro.despues
    huella = registro.despues["huella"]
    assert len(huella) == 64 and int(huella, 16) >= 0  # sha256 en hexadecimal

    # El mismo contenido en otro modo es otra huella: no avisa.
    assert vista(compras, filas, modo="REPOSICION")["archivo_repetido"] is None
    lote_2 = str(uuid.uuid4())
    importar(compras, filas, id_lote=lote_2, confirmar_repetido=True)
    segundo = session.scalar(
        select(Auditoria).where(
            Auditoria.accion == "importacion.confirmar", Auditoria.entidad_id == lote_2
        )
    )
    assert segundo.despues["huella"] == huella and segundo.despues["repetido"] is True


def test_I_12_repetir_el_mismo_id_lote_se_resuelve_antes_y_no_pide_confirmacion(compras):
    filas = [fila(unico("A"), cantidad=2)]
    lote = str(uuid.uuid4())
    importar(compras, filas, id_lote=lote)
    repetida = importar(compras, filas, id_lote=lote, esperado=200)
    assert repetida["repetida"] is True


# ----------------------------------------------------------------- I-06 / RG-10 consolidación


def test_RG_10_consolidacion_las_filas_del_mismo_articulo_y_almacen_salen_como_unido(
    compras, session
):
    codigo, otro = unico("UNI"), unico("OTRO")
    filas = [
        fila(codigo, nombre="Disco de lija", cantidad=10),
        fila(otro, nombre="Cinta", cantidad=1),
        fila(unico("X"), nombre="Pila", cantidad="mucho"),
        fila(codigo, nombre="Disco de lija", cantidad=5),
        fila(codigo, nombre="Disco de lija", cantidad=20, almacen="CON"),
        fila(codigo, nombre="Disco de lija", cantidad=3),
    ]
    vp = vista(compras, filas, primera_fila=2)
    unida = valida(vp, 2)
    assert unida["estado"] == "UNIDO" and unida["cantidad"] == 18 and unida["unida_de"] == [5, 7]
    assert "Unido: filas 2, 5, 7" in unida["avisos"]
    assert valida(vp, 6)["estado"] == "NUEVO"  # otro almacén, otra fila
    assert vp["resumen"]["unidos"] == 1 and vp["resumen"]["con_error"] == 1
    assert vp["resumen"]["unidades"] == 18 + 1 + 20

    salida = importar(compras, filas, primera_fila=2)
    assert salida["resumen"]["unidos"] == 1 and salida["resumen"]["articulos_creados"] == 2
    assert existencia(session, "KEP", articulo(session, codigo)) == 18
    assert existencia(session, "CON", articulo(session, codigo)) == 20


def test_RG_10_consolidacion_una_fila_sin_codigo_se_une_por_nombre_y_marca(compras, session):
    nombre = f"Disco {uuid.uuid4().hex[:6]}"
    vp = vista(
        compras,
        [
            fila("", nombre=nombre, marca="Truper", categoria=CONSUMIBLES, cantidad=4),
            fila(
                "", nombre=f"  {nombre.upper()} ", marca="truper", categoria=CONSUMIBLES, cantidad=6
            ),
            fila("", nombre=nombre, marca="Urrea", categoria=CONSUMIBLES, cantidad=1),
        ],
    )
    assert vp["resumen"]["unidos"] == 1 and vp["resumen"]["articulos_nuevos"] == 2
    unida = valida(vp, 1)
    assert unida["cantidad"] == 10 and unida["unida_de"] == [2] and unida["codigo_generado"]
    assert valida(vp, 3)["estado"] == "NUEVO"  # otra marca


def test_RG_10_consolidacion_una_fila_sin_codigo_suma_al_articulo_existente_por_nombre(
    compras, session
):
    existente = crear_articulo(session, nombre=f"Cuchara {uuid.uuid4().hex[:6]}", marca="Urrea")
    vp = vista(compras, [fila("", nombre=existente.nombre, marca="Urrea", cantidad=3)])
    f = vp["filas_validas"][0]
    assert f["estado"] == "EXISTENTE" and f["codigo"] == existente.codigo
    salida = importar(compras, [fila("", nombre=existente.nombre, marca="Urrea", cantidad=3)])
    assert salida["articulos_creados"] == []
    assert existencia(session, "KEP", existente) == 3


def test_RG_10_consolidacion_un_codigo_de_pieza_o_una_serie_repetidos_siguen_siendo_error(
    compras,
):
    codigo = unico("TAL")
    vp = vista(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza="P-A" + codigo),
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza="P-B" + codigo),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza="P-A" + codigo),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [1]
    assert motivos(vp, 2)[0]["codigo"] == "SERIE_REPETIDA"
    assert motivos(vp, 3)[0]["codigo"] == "CODIGO_REPETIDO"
    assert vp["resumen"]["unidos"] == 0


def test_I_06_saldo_antes_y_despues_leen_la_existencia_del_almacen(compras, session):
    codigo = unico("SAL")
    importar(compras, [fila(codigo, nombre="Cinta", cantidad=10)])
    vp = vista(
        compras,
        [
            fila(codigo, cantidad=3),
            fila(codigo, cantidad=2),
            fila(codigo, cantidad=7, almacen="CON"),
            fila(unico("NUE"), cantidad=4),
        ],
    )
    unida = valida(vp, 1)
    assert unida["estado"] == "UNIDO" and unida["cantidad"] == 5
    assert (unida["saldo_antes"], unida["saldo_despues"]) == (10, 15)
    en_con = valida(vp, 3)
    assert en_con["estado"] == "EXISTENTE" and (en_con["saldo_antes"], en_con["saldo_despues"]) == (
        0,
        7,
    )
    assert (valida(vp, 4)["saldo_antes"], valida(vp, 4)["saldo_despues"]) == (0, 4)
    assert vp["resumen"]["existentes"] == 1


def test_I_06_un_articulo_existente_avisa_las_diferencias_y_no_cambia_nada(compras, session):
    existente = crear_articulo(session, nombre="Pinzas", marca="Truper")
    vp = vista(
        compras,
        [
            fila(
                existente.codigo,
                nombre="Pinzas de presión",
                marca="Urrea",
                categoria=ELECTRICA,
                cantidad=1,
            )
        ],
    )
    avisos = valida(vp, 1)["avisos"]
    assert "El nombre del archivo es distinto del registrado; no se cambia." in avisos
    assert "La marca del archivo es distinta de la registrada; no se cambia." in avisos
    assert "La categoría del archivo es distinta de la registrada; no se cambia." in avisos
    importar(
        compras,
        [fila(existente.codigo, nombre="Pinzas de presión", marca="Urrea", cantidad=1)],
    )
    session.refresh(existente)
    assert existente.nombre == "Pinzas" and existente.marca == "Truper"


def test_I_06_una_fila_que_dice_servicio_se_excluye_con_aviso_y_no_cuenta_como_error(
    compras, session
):
    codigo = unico("SERV")
    filas = [
        fila(codigo, nombre="Servicio de calibración", cantidad=1),
        fila(unico("OK"), nombre="Cinta", cantidad=2),
    ]
    vp = vista(compras, filas, primera_fila=2)
    assert vp["filas_error"] == [] and vp["resumen"]["excluidas"] == 1
    assert vp["filas_excluidas"] == [
        {
            "fila": 2,
            "nombre": "Servicio de calibración",
            "motivo": "Es un servicio, no un artículo.",
        }
    ]
    salida = importar(compras, filas, primera_fila=2)
    assert salida["resumen"]["excluidas"] == 1 and salida["filas_error"] == []
    assert articulo(session, codigo) is None


def test_I_06_el_nombre_se_limpia_de_prefijos_claves_internas_y_sufijo(compras):
    vp = vista(
        compras,
        [
            fila(
                unico("L"),
                nombre="/SP/  ANTEOJO   ECO LINE (RF005) .",
                categoria=MANUAL,
                cantidad=1,
            )
        ],
    )
    assert vp["filas_validas"][0]["nombre"] == "ANTEOJO ECO LINE"


# ------------------------------------------------------------------- código generado


def test_I_06_el_codigo_generado_es_prefijo_y_consecutivo_por_categoria(compras, session):
    nombres = [f"Casco {uuid.uuid4().hex[:6]}", f"Peto {uuid.uuid4().hex[:6]}"]
    filas = [fila("", nombre=n, categoria=EPP_BASICO, cantidad=1) for n in nombres]
    vp = vista(compras, filas)
    provisionales = [f["codigo"] for f in vp["filas_validas"]]
    assert all(f["codigo_generado"] for f in vp["filas_validas"])
    assert all(c.startswith("EPB-") and len(c) == 8 for c in provisionales)
    primero = int(provisionales[0].split("-")[1])
    assert int(provisionales[1].split("-")[1]) == primero + 1

    salida = importar(compras, filas)
    codigos = [a["codigo"] for a in salida["articulos_creados"]]
    assert codigos == provisionales and all(
        a["codigo_generado"] for a in salida["articulos_creados"]
    )
    # Otro lote sigue la numeración.
    nuevo = f"Casco {uuid.uuid4().hex[:6]}"
    siguiente = importar(compras, [fila("", nombre=nuevo, categoria=EPP_BASICO, cantidad=1)])
    assert siguiente["articulos_creados"][0]["codigo"] == f"EPB-{primero + 2:04d}"


def test_I_06_una_categoria_sin_prefijo_no_genera_codigo(compras, session):
    from app.modulos.catalogo.models import Categoria

    propia = Categoria(
        nombre="Categoría de la empresa", tipo="HERRAMIENTA", control="CANTIDAD", retornable=True
    )
    session.add(propia)
    session.flush()
    vp = vista(compras, [fila("", nombre="Algo", categoria=propia.nombre, cantidad=1)])
    assert motivos(vp, 1)[0]["codigo"] == "FALTA_CODIGO"
    assert (
        vista(compras, [fila("MIO-1", nombre="Algo", categoria=propia.nombre, cantidad=1)])[
            "resumen"
        ]["validas"]
        == 1
    )


# ------------------------------------------------------------------------------ I-14


def test_I_14_la_sugerencia_trae_su_motivo_y_nunca_se_aplica_sola(compras, session):
    nombre = f"Disco de corte {uuid.uuid4().hex[:6]}"
    filas = [fila(unico("D"), nombre=nombre, categoria="", cantidad=5)]
    vp = vista(compras, filas)
    f = vp["filas_validas"][0]
    assert f["categoria"] is None  # nada se aplica sin que la persona lo vea
    assert f["categoria_sugerida"]["nombre"] == CONSUMIBLES
    assert f["motivo_sugerencia"] == "La descripción dice «disco»"
    assert vp["resumen"]["por_revisar"] == 0

    # Al confirmar solo cuenta lo que la persona eligió: sin `categoria_por_fila` no entra.
    r = compras.post(IMPORTACION, json=confirmacion(filas))
    assert r.status_code == 422
    assert r.json()["detalles"]["filas_error"][0]["motivos"][0]["codigo"] == "CATEGORIA_DESCONOCIDA"
    assert articulo(session, filas[0][0]) is None

    elegida = categoria_id(session, CONSUMIBLES)
    salida = importar(compras, filas, categoria_por_fila={"1": elegida})
    assert salida["articulos_creados"][0]["categoria"] == CONSUMIBLES


def test_I_14_la_persona_puede_cambiar_la_categoria_de_la_fila(compras, session):
    codigo = unico("CAM")
    filas = [fila(codigo, nombre=f"Disco {uuid.uuid4().hex[:6]}", categoria="", cantidad=1)]
    manual = categoria_id(session, MANUAL)
    vp = vista(compras, filas, categoria_por_fila={"1": manual})
    f = vp["filas_validas"][0]
    assert f["categoria"]["nombre"] == MANUAL  # lo elegido manda
    assert f["categoria_sugerida"]["nombre"] == CONSUMIBLES  # y la sugerencia sigue a la vista
    salida = importar(compras, filas, categoria_por_fila={"1": manual})
    assert salida["articulos_creados"][0]["categoria"] == MANUAL


def test_I_14_lo_que_no_coincide_queda_por_revisar_y_no_entra(compras, session):
    codigo = unico("RAR")
    filas = [fila(codigo, nombre="Zzz Qqq", categoria="", cantidad=1)]
    vp = vista(compras, filas)
    assert vp["resumen"]["por_revisar"] == 1 and vp["filas_validas"] == []
    assert motivos(vp, 1)[0]["codigo"] == "CATEGORIA_DESCONOCIDA"
    assert "categoria_sugerida" not in vp["filas_error"][0]
    assert vp["categorias_desconocidas"] == [{"nombre": "(sin categoría)", "filas": [1]}]
    assert compras.post(IMPORTACION, json=confirmacion(filas)).status_code == 422
    assert articulo(session, codigo) is None
    # Elegida la categoría, la fila entra.
    importar(compras, filas, categoria_por_fila={"1": categoria_id(session, MANUAL)})
    assert articulo(session, codigo) is not None


def test_I_14_si_el_archivo_trae_categoria_esa_manda_y_no_se_sugiere(compras):
    vp = vista(compras, [fila(unico("A"), nombre="Disco de corte", categoria=MANUAL, cantidad=1)])
    f = vp["filas_validas"][0]
    assert f["categoria"]["nombre"] == MANUAL
    assert f["categoria_sugerida"] is None and f["motivo_sugerencia"] is None


def test_I_14_la_sugerencia_solo_aplica_en_alta_a_articulos_nuevos(compras, session):
    existente = crear_articulo(session, nombre="Disco viejo")
    vp = vista(compras, [fila(existente.codigo, nombre="Disco", categoria="", cantidad=1)])
    assert vp["filas_validas"][0]["categoria_sugerida"] is None
    vp = vista(compras, [fila(existente.codigo, cantidad=1)], modo="REPOSICION")
    assert vp["filas_validas"][0]["categoria_sugerida"] is None


def test_I_14_una_categoria_elegida_que_no_existe_da_422(compras):
    r = compras.post(
        VISTA_PREVIA,
        json=cuerpo([fila(unico("A"), cantidad=1)], categoria_por_fila={"1": str(uuid.uuid4())}),
    )
    assert r.status_code == 422
    r = compras.post(
        VISTA_PREVIA,
        json=cuerpo([fila(unico("A"), cantidad=1)], categoria_por_fila={"uno": str(uuid.uuid4())}),
    )
    assert r.status_code == 422


# ------------------------------------------------------------------------------ plantilla


def _encabezados(respuesta) -> list[str]:
    libro = load_workbook(io.BytesIO(respuesta.content))
    return [c.value for c in libro["Plantilla"][1]]


def test_I_10_plantilla_de_alta_trae_costo_solo_con_catalogo_costos(compras, cliente_con):
    r = compras.get(PLANTILLA, params={"modo": "ALTA"})
    assert r.status_code == 200 and "spreadsheetml.sheet" in r.headers["content-type"]
    assert "plantilla-alta.xlsx" in r.headers["content-disposition"]
    assert "Costo" in _encabezados(r)
    sin_costos = cliente_con({P.INVENTARIO_ENTRADAS})
    r = sin_costos.get(PLANTILLA)  # sin modo: ALTA
    assert r.status_code == 200 and "Costo" not in _encabezados(r)
    assert "Nombre" in _encabezados(r)


def test_I_10_plantilla_de_reposicion_trae_solo_lo_que_se_lee(compras):
    r = compras.get(PLANTILLA, params={"modo": "REPOSICION"})
    assert r.status_code == 200
    assert _encabezados(r) == ["Código", "Cantidad", "Almacén", "Serie", "Código de la pieza"]
    assert "plantilla-reposicion.xlsx" in r.headers["content-disposition"]


@pytest.mark.parametrize("modo", ["ALTA", "REPOSICION"])
def test_I_10_la_plantilla_se_lee_de_vuelta_y_sus_columnas_se_reconocen(compras, modo):
    r = compras.get(PLANTILLA, params={"modo": modo})
    _, filas = leer_xlsx("plantilla.xlsx", r.content)
    columnas = proponer_columnas(filas[0])
    esperadas = {"codigo", "cantidad", "almacen", "serie", "codigo_pieza"}
    if modo == "ALTA":
        esperadas |= {"nombre", "marca", "categoria", "costo"}
    assert {c for c, i in columnas.items() if i is not None} == esperadas
    # La fila de ejemplo es una tabla válida en su modo.
    vp = compras.post(
        ARCHIVO_URL, files={"archivo": ("p.xlsx", r.content, MIME)}, data={"modo": modo}
    )
    assert vp.status_code == 200, vp.text
    assert vp.json()["vista_previa"]["modo"] == modo


def test_I_10_la_plantilla_exige_inventario_entradas_y_un_modo_valido(compras, cliente_con):
    sin_permiso = cliente_con({P.CATALOGO_VER})
    assert sin_permiso.get(PLANTILLA).status_code == 403
    assert compras.get(PLANTILLA, params={"modo": "OTRO"}).status_code == 422


def test_I_10_la_plantilla_responde_el_xlsx_aunque_el_cliente_acepte_json(compras):
    r = compras.get(PLANTILLA, headers={"Accept": "application/json"})
    assert r.status_code == 200 and "spreadsheetml.sheet" in r.headers["content-type"]
