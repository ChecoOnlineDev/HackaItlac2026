"""Vista previa de la importación (US-IMP-001): I-01 a I-04, I-06, I-09, CF-02, RG-10, RG-12."""

import uuid

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen, EstadoAlmacen
from tests.importacion.ayudas import (
    ALTURAS,
    ELECTRICA,
    MANUAL,
    VISTA_PREVIA,
    categoria_id,
    conteos,
    cuerpo,
    fila,
    unico,
)
from tests.movimientos.ayudas import crear_articulo, crear_pieza, crear_trabajador


def vista(cliente, filas, **extra):
    r = cliente.post(VISTA_PREVIA, json=cuerpo(filas, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def motivos(vp, numero: int) -> list[dict]:
    return next(f["motivos"] for f in vp["filas_error"] if f["fila"] == numero)


# ------------------------------------------------------------------------------ I-06


def test_I_06_la_vista_previa_no_escribe_nada(compras, session):
    antes = conteos(session)
    vp = vista(
        compras,
        [
            fila(unico("ART"), cantidad=5),
            fila(unico("ART"), cantidad=2, almacen="CON"),
            fila(unico("PZA"), categoria=ELECTRICA, serie=unico("S"), codigo_pieza=unico("P")),
            fila(unico("MAL"), cantidad="abc"),
        ],
    )
    assert vp["resumen"]["validas"] == 3 and vp["resumen"]["con_error"] == 1
    assert conteos(session) == antes


def test_I_06_mezcla_de_filas_buenas_y_malas_cada_una_con_su_numero_y_motivo(compras):
    buena = unico("OK")
    vp = vista(
        compras,
        [
            fila(buena, cantidad=3),
            fila(unico("X"), cantidad="mucho"),
            fila(unico("Y"), nombre="", cantidad=1),
            fila("", cantidad=1),
        ],
        primera_fila=2,
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [2]
    assert [f["fila"] for f in vp["filas_error"]] == [3, 4, 5]
    assert motivos(vp, 3)[0]["codigo"] == "CANTIDAD_INVALIDA"
    assert motivos(vp, 4)[0]["codigo"] == "FALTA_NOMBRE"
    assert motivos(vp, 5)[0]["codigo"] == "FALTA_CODIGO"
    # Cada motivo trae su regla y un mensaje en español; la fila trae lo que venía en ella.
    assert all(m["regla"] and m["mensaje"] for f in vp["filas_error"] for m in f["motivos"])
    assert vp["filas_error"][0]["datos"]["cantidad"] == "mucho"


def test_I_06_resumen_y_articulos_que_se_crearian(compras):
    codigo = unico("NUEVO")
    vp = vista(
        compras,
        [
            fila(codigo, nombre="Taladro", cantidad=2, almacen="KEP"),
            fila(codigo, nombre="Taladro", cantidad=4, almacen="CON"),
        ],
    )
    assert vp["resumen"] == {
        "total": 2,
        "validas": 2,
        "con_error": 0,
        "vacias": 0,
        "articulos_nuevos": 1,
        "piezas": 0,
        "unidades": 6,
        "almacenes": 2,
    }
    nuevo = vp["articulos_nuevos"][0]
    assert nuevo["codigo"] == codigo and nuevo["filas"] == 2
    assert nuevo["categoria"]["nombre"] == MANUAL and nuevo["control"] == "CANTIDAD"
    assert all(f["articulo_nuevo"] for f in vp["filas_validas"])


def test_I_06_las_filas_vacias_se_ignoran_y_la_numeracion_se_conserva(compras):
    vp = vista(
        compras,
        [fila(unico("A"), cantidad=1), [""] * 9, [None] * 9, fila(unico("B"), cantidad="x")],
    )
    assert vp["resumen"]["vacias"] == 2 and vp["resumen"]["total"] == 4
    assert [f["fila"] for f in vp["filas_validas"]] == [1]
    assert [f["fila"] for f in vp["filas_error"]] == [4]


def test_I_06_las_columnas_se_proponen_con_los_encabezados_aunque_tengan_acentos(compras):
    encabezados = [
        "Número de serie",
        "Código",
        "Descripción",
        "Categoría",
        "Almacén",
        "Cantidad",
        "Costo unitario",
        "Marca",
        "Código de pieza",
    ]
    codigo = unico("ENC")
    r = compras.post(
        VISTA_PREVIA,
        json={
            "encabezados": encabezados,
            "filas": [["", codigo, "Martillo", MANUAL, "kepler", "7", "$1,250.50", "Truper", ""]],
        },
    )
    assert r.status_code == 200, r.text
    vp = r.json()
    assert vp["columnas"] == {
        "serie": 0,
        "codigo": 1,
        "nombre": 2,
        "categoria": 3,
        "almacen": 4,
        "cantidad": 5,
        "costo": 6,
        "marca": 7,
        "codigo_pieza": 8,
    }
    fila_valida = vp["filas_validas"][0]
    assert fila_valida["nombre"] == "Martillo" and fila_valida["cantidad"] == 7
    assert fila_valida["almacen"]["clave"] == "KEP" and fila_valida["costo"] == "1250.50"


def test_I_06_sin_la_columna_del_codigo_se_pide_indicarla(compras):
    r = compras.post(
        VISTA_PREVIA, json={"encabezados": ["Nombre", "Cantidad"], "filas": [["a", "1"]]}
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"


def test_I_06_la_tabla_necesita_columnas_o_encabezados_y_sin_columnas_repetidas(compras):
    assert compras.post(VISTA_PREVIA, json={"filas": [["a"]]}).status_code == 422
    repetidas = {"filas": [["a", "b"]], "columnas": {"codigo": 0, "nombre": 0}}
    assert compras.post(VISTA_PREVIA, json=repetidas).status_code == 422


def test_I_06_limites_de_tamano_de_la_tabla(compras):
    demasiadas = [fila(unico("F"), cantidad=1) for _ in range(5001)]
    assert compras.post(VISTA_PREVIA, json=cuerpo(demasiadas)).status_code == 422
    celda_larga = [fila(unico("F"), nombre="x" * 501, cantidad=1)]
    assert compras.post(VISTA_PREVIA, json=cuerpo(celda_larga)).status_code == 422
    ancha = [["a"] * 31]
    assert compras.post(VISTA_PREVIA, json=cuerpo(ancha)).status_code == 422


def test_I_06_un_nombre_que_parece_formula_es_solo_texto(compras):
    nombre = '=HYPERLINK("http://malo","clic")'
    vp = vista(compras, [fila(unico("INY"), nombre=nombre, marca="@SUM(A1)", cantidad=1)])
    assert vp["resumen"]["validas"] == 1
    assert vp["filas_validas"][0]["nombre"] == nombre
    assert vp["filas_validas"][0]["marca"] == "@SUM(A1)"


# ------------------------------------------------------------------------------ I-01


def test_I_01_la_cantidad_debe_ser_un_entero_mayor_que_cero(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), cantidad=""),
            fila(unico("B"), cantidad="abc"),
            fila(unico("C"), cantidad=0),
            fila(unico("D"), cantidad=-3),
            fila(unico("E"), cantidad="2.5"),
            fila(unico("F"), cantidad=1_000_001),
            fila(unico("G"), cantidad="10"),
            fila(unico("H"), cantidad=10.0),
            fila(unico("I"), cantidad="1,000"),
        ],
    )
    assert [f["fila"] for f in vp["filas_error"]] == [1, 2, 3, 4, 5, 6]
    assert motivos(vp, 1)[0]["codigo"] == "FALTA_CANTIDAD"
    assert all(m["regla"] == "I-01" for f in vp["filas_error"] for m in f["motivos"])
    assert [(f["fila"], f["cantidad"]) for f in vp["filas_validas"]] == [
        (7, 10),
        (8, 10),
        (9, 1000),
    ]


def test_I_01_el_almacen_se_reconoce_por_clave_o_nombre_y_el_desconocido_se_rechaza(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), cantidad=1, almacen="con"),
            fila(unico("B"), cantidad=1, almacen="CONTRATISTAS"),
            fila(unico("C"), cantidad=1, almacen="Bodega fantasma"),
            fila(unico("D"), cantidad=1, almacen=""),
        ],
    )
    claves = {f["fila"]: f["almacen"]["clave"] for f in vp["filas_validas"]}
    assert claves == {1: "CON", 2: "CON", 4: "KEP"}  # sin almacén, la compra entra por Kepler
    assert motivos(vp, 3)[0]["codigo"] == "ALMACEN_DESCONOCIDO"


def test_I_01_un_almacen_cerrado_se_rechaza(compras, session):
    session.query(Almacen).filter(Almacen.clave == "LAM").update({"estado": EstadoAlmacen.CERRADO})
    session.flush()
    vp = vista(compras, [fila(unico("A"), cantidad=1, almacen="LAM")])
    assert motivos(vp, 1)[0]["codigo"] == "ALMACEN_CERRADO"


def test_I_01_el_almacen_por_defecto_se_puede_elegir(compras):
    vp = vista(compras, [fila(unico("A"), cantidad=1, almacen="")], almacen_por_defecto="MID")
    assert vp["filas_validas"][0]["almacen"]["clave"] == "MID"


def test_AC_06_sin_almacenes_todos_solo_se_carga_al_almacen_asignado(cliente_con):
    kepler = cliente_con({P.INVENTARIO_ENTRADAS}, almacen="KEP")
    vp = vista(
        kepler,
        [
            fila(unico("A"), cantidad=1, almacen="KEP"),
            fila(unico("B"), cantidad=1, almacen=""),
            fila(unico("C"), cantidad=1, almacen="CON"),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [1, 2]
    assert motivos(vp, 3)[0]["codigo"] == "ALMACEN_AJENO"


# ------------------------------------------------------------------------------ CF-02


def test_CF_02_una_categoria_desconocida_se_senala_con_sus_filas(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), categoria="Cosas raras", cantidad=1),
            fila(unico("B"), categoria="cosas raras", cantidad=2),
            fila(unico("C"), categoria="", cantidad=2),
            fila(unico("D"), categoria="herramienta MANUAL", cantidad=2),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [4]  # sin acentos ni mayúsculas
    assert {m["codigo"] for f in vp["filas_error"] for m in f["motivos"]} == {
        "CATEGORIA_DESCONOCIDA"
    }
    desconocidas = {c["nombre"]: c["filas"] for c in vp["categorias_desconocidas"]}
    assert desconocidas == {"Cosas raras": [1, 2], "(sin categoría)": [3]}


def test_CF_02_la_categoria_elegida_cubre_a_las_filas_con_categoria_desconocida(compras, session):
    filas = [
        fila(unico("A"), categoria="Cosas raras", cantidad=1),
        fila(unico("B"), categoria="Otras", cantidad=2),
        fila(unico("C"), categoria="", cantidad=2),
    ]
    por_defecto = categoria_id(session, MANUAL)
    vp = vista(compras, filas, categoria_por_defecto_id=por_defecto)
    assert vp["resumen"]["validas"] == 3 and not vp["categorias_desconocidas"]

    mapa = {"Cosas raras": categoria_id(session, ELECTRICA)}
    vp = vista(
        compras,
        filas[:1] + [fila(unico("Z"), categoria="Otras", cantidad=1, serie="s", codigo_pieza="p")],
        mapa_categorias=mapa,
        categoria_por_defecto_id=por_defecto,
    )
    # "Cosas raras" -> eléctrica (por pieza, sin serie ni código de pieza): error de pieza;
    # "Otras" -> la de por defecto (manual, por cantidad).
    assert vp["filas_error"][0]["fila"] == 1
    assert vp["filas_error"][0]["motivos"][0]["regla"] == "RG-05" or any(
        m["codigo"] == "FALTA_CODIGO_PIEZA" for m in vp["filas_error"][0]["motivos"]
    )
    assert vp["filas_validas"][0]["categoria"]["nombre"] == MANUAL


def test_CF_02_una_categoria_elegida_que_no_existe_es_un_error_de_datos(compras):
    r = compras.post(
        VISTA_PREVIA,
        json=cuerpo([fila(unico("A"), cantidad=1)], categoria_por_defecto_id=str(uuid.uuid4())),
    )
    assert r.status_code == 422


def test_CF_02_el_articulo_nuevo_toma_el_control_de_su_categoria(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), categoria=MANUAL, cantidad=3),
            fila(unico("B"), categoria=ELECTRICA, serie=unico("S"), codigo_pieza=unico("P")),
        ],
    )
    assert {n["control"] for n in vp["articulos_nuevos"]} == {"CANTIDAD", "PIEZA"}


# ------------------------------------------------------------------------------ I-09


def test_I_09_un_articulo_inactivo_se_rechaza_y_los_demas_entran(compras, session):
    inactivo = crear_articulo(session, activo=False, nombre="Lámpara vieja")
    activo = crear_articulo(session)
    vp = vista(
        compras,
        [fila(inactivo.codigo, cantidad=2), fila(activo.codigo, cantidad=2)],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [2]
    motivo = motivos(vp, 1)[0]
    assert motivo["regla"] == "I-09" and "Lámpara vieja" in motivo["mensaje"]


# ----------------------------------------------------------------------------- RG-10


def test_RG_10_un_codigo_que_ya_es_de_una_pieza_o_un_trabajador_se_rechaza_como_articulo(
    compras, session
):
    dueno = crear_articulo(session, control="PIEZA")
    pieza = crear_pieza(session, dueno)
    trabajador = crear_trabajador(session)
    vp = vista(
        compras,
        [
            fila(pieza.codigo, cantidad=1),
            fila(f"CRED-{trabajador.numero_empleado}", cantidad=1),
        ],
    )
    assert [f["fila"] for f in vp["filas_error"]] == [1, 2]
    assert all(
        f["motivos"][0]["regla"] == "RG-10" and f["motivos"][0]["codigo"] == "CODIGO_REPETIDO"
        for f in vp["filas_error"]
    )


def test_RG_10_un_articulo_existente_recibe_la_entrada_sin_crearse_de_nuevo(compras, session):
    existente = crear_articulo(session, nombre="Pinzas")
    vp = vista(compras, [fila(existente.codigo, nombre="Otro nombre", cantidad=4)])
    assert vp["resumen"]["articulos_nuevos"] == 0
    f = vp["filas_validas"][0]
    assert f["articulo_nuevo"] is False and f["nombre"] == "Pinzas"


def test_RG_10_el_codigo_se_compara_sin_distinguir_mayusculas_ni_acentos(compras, session):
    existente = crear_articulo(session, codigo=unico("Ñandú"))
    vp = vista(compras, [fila(existente.codigo.lower(), cantidad=1)])
    assert vp["filas_validas"][0]["articulo_nuevo"] is False


def test_RG_10_el_mismo_articulo_por_cantidad_en_el_mismo_almacen_se_rechaza(compras):
    codigo = unico("DUP")
    vp = vista(
        compras,
        [
            fila(codigo, cantidad=1, almacen="KEP"),
            fila(codigo, cantidad=5, almacen="KEP"),
            fila(codigo, cantidad=2, almacen="CON"),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [1, 3]  # otro almacén es otra fila
    motivo = motivos(vp, 2)[0]
    assert motivo["regla"] == "RG-10" and "fila 1" in motivo["mensaje"]


def test_RG_10_un_codigo_de_pieza_repetido_en_la_tabla_se_rechaza(compras):
    repetido = unico("P")
    vp = vista(
        compras,
        [
            fila(unico("A"), categoria=ELECTRICA, serie="s1", codigo_pieza=repetido),
            fila(unico("B"), categoria=ELECTRICA, serie="s2", codigo_pieza=repetido),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [1]
    assert motivos(vp, 2)[0]["codigo"] == "CODIGO_REPETIDO"


def test_RG_10_un_codigo_de_pieza_no_puede_ser_el_de_un_articulo(compras, session):
    articulo_existente = crear_articulo(session, control="PIEZA")
    nuevo = unico("ART")
    vp = vista(
        compras,
        [
            fila(nuevo, categoria=ELECTRICA, serie="s1", codigo_pieza=nuevo),  # el mismo
            fila(
                unico("B"), categoria=ELECTRICA, serie="s2", codigo_pieza=articulo_existente.codigo
            ),
        ],
    )
    assert [f["fila"] for f in vp["filas_error"]] == [1, 2]
    assert all(f["motivos"][0]["regla"] in ("RG-10", "I-02") for f in vp["filas_error"])


# ------------------------------------------------------------------------------ I-02


def test_I_02_cada_fila_de_un_articulo_por_pieza_es_una_pieza(compras):
    codigo = unico("TAL")
    vp = vista(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza=unico("P")),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=unico("P")),
            fila(codigo, categoria=ELECTRICA, serie="S-3", codigo_pieza=unico("P")),
        ],
    )
    assert vp["resumen"]["validas"] == 3 and vp["resumen"]["piezas"] == 3
    assert vp["resumen"]["unidades"] == 3 and vp["resumen"]["articulos_nuevos"] == 1
    assert vp["articulos_nuevos"][0]["filas"] == 3
    assert all(f["cantidad"] == 1 and f["control"] == "PIEZA" for f in vp["filas_validas"])


def test_I_02_la_pieza_sin_serie_o_sin_codigo_de_pieza_se_rechaza(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), categoria=ELECTRICA, serie="", codigo_pieza=unico("P")),
            fila(unico("B"), categoria=ELECTRICA, serie="S-9", codigo_pieza=""),
        ],
    )
    assert motivos(vp, 1)[0]["codigo"] == "FALTA_SERIE"
    assert motivos(vp, 2)[0]["codigo"] == "FALTA_CODIGO_PIEZA"
    assert all(m["regla"] == "I-02" for f in vp["filas_error"] for m in f["motivos"])


def test_I_02_un_codigo_de_pieza_que_ya_existe_en_la_base_se_rechaza(compras, session):
    dueno = crear_articulo(session, control="PIEZA")
    existente = crear_pieza(session, dueno)
    vp = vista(
        compras,
        [fila(unico("A"), categoria=ELECTRICA, serie="S-1", codigo_pieza=existente.codigo)],
    )
    motivo = motivos(vp, 1)[0]
    assert motivo["regla"] == "I-02" and motivo["codigo"] == "CODIGO_REPETIDO"


def test_I_02_una_serie_repetida_del_mismo_articulo_se_rechaza_en_la_tabla_y_en_la_base(
    compras, session
):
    dueno = crear_articulo(session, control="PIEZA")
    existente = crear_pieza(session, dueno)
    vp = vista(
        compras,
        [
            fila(dueno.codigo, serie=existente.numero_serie, codigo_pieza=unico("P")),
            fila(dueno.codigo, serie="NUEVA-1", codigo_pieza=unico("P")),
            fila(dueno.codigo, serie="nueva-1", codigo_pieza=unico("P")),
        ],
    )
    assert [f["fila"] for f in vp["filas_validas"]] == [2]
    assert motivos(vp, 1)[0]["codigo"] == "SERIE_REPETIDA"
    assert motivos(vp, 3)[0]["codigo"] == "SERIE_REPETIDA"


def test_RG_05_una_pieza_entra_de_una_en_una(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), categoria=ELECTRICA, cantidad=3, serie="S", codigo_pieza=unico("P")),
            fila(unico("B"), categoria=ELECTRICA, cantidad=1, serie="S", codigo_pieza=unico("P")),
        ],
    )
    assert motivos(vp, 1)[0]["regla"] == "RG-05"
    assert [f["fila"] for f in vp["filas_validas"]] == [2]


def test_I_03_una_pieza_que_pide_inspeccion_avisa_que_entra_pendiente(compras):
    vp = vista(
        compras,
        [fila(unico("ARN"), categoria=ALTURAS, serie="S-1", codigo_pieza=unico("P"))],
    )
    assert any("pendiente de inspección" in a for a in vp["filas_validas"][0]["avisos"])


def test_I_02_un_articulo_por_cantidad_ignora_el_codigo_de_pieza_y_avisa(compras):
    vp = vista(compras, [fila(unico("A"), cantidad=2, serie="S-1", codigo_pieza=unico("P"))])
    assert vp["resumen"]["validas"] == 1 and vp["filas_validas"][0]["codigo_pieza"] is None
    assert vp["filas_validas"][0]["avisos"]


# ------------------------------------------------------------------------------ RG-12


def test_RG_12_sin_catalogo_costos_la_columna_de_costo_se_ignora_con_aviso(cliente_con):
    sin_costos = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS})
    r = sin_costos.post(VISTA_PREVIA, json=cuerpo([fila(unico("A"), cantidad=2, costo="99.90")]))
    assert r.status_code == 200, r.text
    vp = r.json()
    assert vp["resumen"]["validas"] == 1  # la fila entra: el costo solo se ignora
    assert "costo" not in vp["filas_validas"][0]
    assert "costo" not in vp["articulos_nuevos"][0]
    assert any("costo" in a for a in vp["avisos"])
    assert "99.9" not in r.text


def test_RG_12_sin_catalogo_costos_el_costo_tampoco_vuelve_en_las_filas_con_error(cliente_con):
    sin_costos = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS})
    r = sin_costos.post(
        VISTA_PREVIA, json=cuerpo([fila(unico("A"), cantidad="mal", costo="123.45")])
    )
    assert "costo" not in r.json()["filas_error"][0]["datos"] and "123.45" not in r.text


def test_RG_12_con_catalogo_costos_se_muestra_y_un_costo_invalido_se_rechaza(compras):
    vp = vista(
        compras,
        [
            fila(unico("A"), cantidad=1, costo="12.5"),
            fila(unico("B"), cantidad=1, costo="gratis"),
            fila(unico("C"), cantidad=1, costo=-4),
            fila(unico("D"), cantidad=1, costo=""),
        ],
    )
    assert vp["filas_validas"][0]["costo"] == "12.50"
    assert vp["articulos_nuevos"][0]["costo"] == "12.50"
    assert motivos(vp, 2)[0]["codigo"] == "COSTO_INVALIDO" and motivos(vp, 2)[0]["regla"] == "I-04"
    assert motivos(vp, 3)[0]["codigo"] == "COSTO_INVALIDO"
    assert [f["fila"] for f in vp["filas_validas"]] == [1, 4]


def test_RG_12_el_costo_de_un_articulo_que_ya_existe_no_cambia_y_avisa(compras, session):
    existente = crear_articulo(session)
    vp = vista(compras, [fila(existente.codigo, cantidad=1, costo="500")])
    f = vp["filas_validas"][0]
    assert "costo" not in f and any("costo" in a for a in f["avisos"])


# --------------------------------------------------------------------------- permisos


def test_I_06_sin_inventario_entradas_los_tres_endpoints_dan_403(almacenista, cliente_con):
    sin_permiso = cliente_con({P.CATALOGO_VER}, almacen="KEP")
    for cliente in (almacenista, sin_permiso):
        assert cliente.post(VISTA_PREVIA, json=cuerpo([fila("X", cantidad=1)])).status_code == 403
        assert (
            cliente.post(
                "/api/importacion", json=cuerpo([fila("X", cantidad=1)], id_lote=str(uuid.uuid4()))
            ).status_code
            == 403
        )
        r = cliente.post("/api/importacion/archivo", files={"archivo": ("a.xlsx", b"x")})
        assert r.status_code == 403


def test_I_06_sin_sesion_los_endpoints_dan_401(client):
    assert client.post(VISTA_PREVIA, json=cuerpo([fila("X", cantidad=1)])).status_code == 401
    assert client.post("/api/importacion", json=cuerpo([])).status_code == 401


def test_I_06_dos_filas_buenas_de_un_articulo_nuevo_con_nombres_distintos_avisan(compras):
    codigo = unico("N")
    vp = vista(
        compras,
        [
            fila(codigo, nombre="Primero", cantidad=1, almacen="KEP"),
            fila(codigo, nombre="Segundo", cantidad=1, almacen="CON"),
        ],
    )
    assert vp["articulos_nuevos"][0]["nombre"] == "Primero"
    assert any("Primero" in a for a in vp["filas_validas"][1]["avisos"])
