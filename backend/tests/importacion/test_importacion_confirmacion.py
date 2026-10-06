"""Confirmación de la importación (US-IMP-001): I-01, I-02, I-03, I-06, I-09, CF-02, RG-06,
RG-09, RG-10, RG-12."""

import uuid

from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Codigo, EstadoPieza, Pieza, TipoCodigo
from app.modulos.movimientos.exceptions import ValeCambio
from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.movimientos.service import MovimientoService
from tests.importacion.ayudas import (
    ALTURAS,
    ELECTRICA,
    IMPORTACION,
    MANUAL,
    articulo,
    categoria_id,
    confirmacion,
    conteos,
    cuerpo,
    fila,
    numero_de_folio,
    unico,
)
from tests.movimientos.ayudas import almacen, crear_articulo, existencia


def importar(cliente, filas, esperado: int = 201, **extra):
    r = cliente.post(IMPORTACION, json=confirmacion(filas, **extra))
    assert r.status_code == esperado, r.text
    return r.json()


# ------------------------------------------------------------------------------ I-01


def test_I_01_un_vale_de_entrada_por_almacen_con_folios_consecutivos_y_existencias_exactas(
    compras, session
):
    a, b, c = unico("A"), unico("B"), unico("C")
    primera = importar(
        compras,
        [
            fila(a, nombre="Martillo", cantidad=10, almacen="KEP"),
            fila(b, nombre="Pinzas", cantidad=4, almacen="KEP"),
            fila(c, nombre="Cinta", cantidad=7, almacen="CON"),
        ],
    )
    assert primera["repetida"] is False
    claves = [v["almacen"]["clave"] for v in primera["vales"]]
    assert claves == ["CON", "KEP"]  # un vale por almacén
    vales = {v["almacen"]["clave"]: v for v in primera["vales"]}
    assert vales["KEP"]["renglones"] == 2 and vales["KEP"]["unidades"] == 14
    assert vales["CON"]["renglones"] == 1 and vales["CON"]["unidades"] == 7
    assert vales["KEP"]["folio"].startswith("KEP-ING-")
    assert vales["CON"]["folio"].startswith("CON-ING-")
    assert primera["resumen"] == {
        "filas_importadas": 3,
        "filas_con_error": 0,
        "articulos_creados": 3,
        "existentes": 0,
        "unidos": 0,
        "excluidas": 0,
        "vales": 2,
        "piezas": 0,
        "unidades": 21,
    }
    assert existencia(session, "KEP", articulo(session, a)) == 10
    assert existencia(session, "KEP", articulo(session, b)) == 4
    assert existencia(session, "CON", articulo(session, c)) == 7
    assert existencia(session, "CON", articulo(session, a)) == 0

    # RG-06: la siguiente importación al mismo almacén sigue la numeración (sin huecos).
    segunda = importar(compras, [fila(a, cantidad=5, almacen="KEP")])
    folio_nuevo = segunda["vales"][0]["folio"]
    assert numero_de_folio(folio_nuevo) == numero_de_folio(vales["KEP"]["folio"]) + 1
    assert existencia(session, "KEP", articulo(session, a)) == 15


def test_I_01_los_vales_son_de_entrada_de_proveedor_al_almacen_y_no_llevan_costos(compras, session):
    codigo = unico("COS")
    salida = importar(compras, [fila(codigo, cantidad=3, costo="1500.75")])
    vale_id = salida["vales"][0]["id"]
    vale = session.get(Vale, uuid.UUID(vale_id))
    assert vale.tipo == "ENTRADA" and vale.responsable_id is not None
    movs = list(session.scalars(select(Movimiento).where(Movimiento.vale_id == vale.id)))
    assert len(movs) == 1 and movs[0].cantidad == 3 and movs[0].saldo_destino == 3
    detalle = compras.get(f"/api/vales/{vale_id}")
    assert detalle.status_code == 200
    assert "costo" not in detalle.text and "1500" not in detalle.text


def test_I_01_un_articulo_que_ya_existe_solo_recibe_la_entrada(compras, session):
    existente = crear_articulo(session, nombre="Pinzas")
    antes = conteos(session)
    salida = importar(compras, [fila(existente.codigo, nombre="Otro", cantidad=6)])
    assert salida["articulos_creados"] == []
    despues = conteos(session)
    assert despues["articulos"] == antes["articulos"]
    assert despues["vales"] == antes["vales"] + 1
    assert existencia(session, "KEP", existente) == 6
    assert session.get(Articulo, existente.id).nombre == "Pinzas"


def test_I_01_un_almacen_con_mas_de_500_renglones_se_parte_en_varios_vales(compras, session):
    filas = [fila(unico("M"), nombre=f"Masivo {i}", cantidad=1) for i in range(501)]
    salida = importar(compras, filas)
    assert [v["renglones"] for v in salida["vales"]] == [500, 1]
    folios = [numero_de_folio(v["folio"]) for v in salida["vales"]]
    assert folios[1] == folios[0] + 1
    assert salida["resumen"]["unidades"] == 501


def test_AC_06_sin_almacenes_todos_solo_carga_a_su_almacen(cliente_con, session):
    kepler = cliente_con({P.INVENTARIO_ENTRADAS, P.CATALOGO_ADMINISTRAR}, almacen="KEP")
    ok, ajena = unico("OK"), unico("AJ")
    salida = importar(
        kepler,
        [fila(ok, cantidad=2, almacen="KEP"), fila(ajena, cantidad=2, almacen="CON")],
    )
    assert salida["resumen"]["filas_importadas"] == 1
    assert salida["filas_error"][0]["motivos"][0]["codigo"] == "ALMACEN_AJENO"
    assert articulo(session, ok) is not None and articulo(session, ajena) is None


def test_AC_06_compras_es_de_kepler_y_no_carga_otros_almacenes(compras_de_kepler, session):
    # Decisión de producto: solo el Administrador tiene `almacenes.todos`; Compras carga Kepler.
    ok, ajena = unico("OK"), unico("AJ")
    salida = importar(
        compras_de_kepler,
        [fila(ok, cantidad=2, almacen="KEP"), fila(ajena, cantidad=2, almacen="CON")],
    )
    assert salida["resumen"]["filas_importadas"] == 1
    assert salida["filas_error"][0]["motivos"][0]["codigo"] == "ALMACEN_AJENO"
    assert articulo(session, ok) is not None and articulo(session, ajena) is None


# ------------------------------------------------------------------------------ I-06


def test_I_06_las_filas_con_error_no_se_importan_y_las_buenas_si(compras, session):
    buena, mala = unico("BUENA"), unico("MALA")
    salida = importar(
        compras,
        [fila(mala, cantidad="mucho"), fila(buena, cantidad=3)],
        primera_fila=2,
    )
    assert salida["resumen"]["filas_importadas"] == 1 and salida["resumen"]["filas_con_error"] == 1
    error = salida["filas_error"][0]
    assert error["fila"] == 2 and error["motivos"][0]["codigo"] == "CANTIDAD_INVALIDA"
    assert error["datos"]["codigo"] == mala  # lo que traía la fila, para descargarla
    assert articulo(session, buena) is not None and articulo(session, mala) is None
    assert existencia(session, "KEP", articulo(session, buena)) == 3


def test_I_06_sin_ninguna_fila_valida_no_se_guarda_nada(compras, session):
    antes = conteos(session)
    r = compras.post(
        IMPORTACION,
        json=confirmacion([fila(unico("A"), cantidad="x"), fila("", nombre="", cantidad=1)]),
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert len(r.json()["detalles"]["filas_error"]) == 2
    assert conteos(session) == antes


def test_I_06_confirmar_exige_el_id_del_lote(compras):
    r = compras.post(IMPORTACION, json=cuerpo([fila(unico("A"), cantidad=1)]))
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "id_lote"


def test_I_06_el_servidor_revisa_otra_vez_al_confirmar_aunque_la_vista_previa_dijera_otra_cosa(
    compras, session
):
    inactivo = crear_articulo(session, activo=False)
    salida = importar(compras, [fila(inactivo.codigo, cantidad=1), fila(unico("OK"), cantidad=1)])
    assert salida["resumen"]["filas_importadas"] == 1
    assert salida["filas_error"][0]["motivos"][0]["regla"] == "I-09"
    assert existencia(session, "KEP", inactivo) == 0


# ----------------------------------------------------------------------------- RG-09


def test_RG_09_si_falla_una_entrada_no_se_guarda_nada_de_la_importacion(
    compras, session, monkeypatch
):
    filas = [
        fila(unico("A"), cantidad=2, almacen="CON"),
        fila(unico("B"), cantidad=3, almacen="KEP"),
    ]
    antes = conteos(session)
    original = MovimientoService.confirmar
    llamadas = {"n": 0}

    def falla_la_segunda(self, *args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise ValeCambio()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MovimientoService, "confirmar", falla_la_segunda)
    r = compras.post(IMPORTACION, json=confirmacion(filas))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert llamadas["n"] == 2
    # Ni artículos, ni vales, ni movimientos, ni existencias, ni folios quemados.
    assert conteos(session) == antes

    monkeypatch.setattr(MovimientoService, "confirmar", original)
    salida = importar(compras, filas)
    assert salida["resumen"]["vales"] == 2


def test_RG_09_un_error_del_catalogo_a_media_importacion_tambien_lo_deshace_todo(
    compras, session, monkeypatch
):
    from app.modulos.catalogo.service import CatalogoService

    antes = conteos(session)
    original = CatalogoService.crear_articulo
    contador = {"n": 0}

    def falla_el_tercero(self, *args, **kwargs):
        contador["n"] += 1
        if contador["n"] == 3:
            from app.modulos.catalogo.codigos import CodigoRepetido

            raise CodigoRepetido()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CatalogoService, "crear_articulo", falla_el_tercero)
    r = compras.post(
        IMPORTACION, json=confirmacion([fila(unico("A"), cantidad=1) for _ in range(4)])
    )
    assert r.status_code == 409 and r.json()["codigo"] == "CODIGO_REPETIDO"
    assert conteos(session) == antes


def test_RG_09_la_confirmacion_deja_un_renglon_de_auditoria(compras, session):
    salida = importar(compras, [fila(unico("A"), cantidad=2)])
    registro = session.scalar(
        select(Auditoria).where(
            Auditoria.accion == "importacion.confirmar",
            Auditoria.entidad_id == salida["id_lote"],
        )
    )
    assert registro is not None and registro.despues["vales"] == 1
    assert registro.despues["folios"] == [salida["vales"][0]["folio"]]


# ------------------------------------------------------------- idempotencia (RG-09)


def test_RG_09_confirmar_dos_veces_el_mismo_lote_no_duplica_articulos_ni_entradas(compras, session):
    codigo = unico("IDEM")
    filas = [fila(codigo, cantidad=5), fila(unico("OTRO"), cantidad=1, almacen="CON")]
    lote = str(uuid.uuid4())
    primera = compras.post(IMPORTACION, json=cuerpo(filas, id_lote=lote))
    assert primera.status_code == 201
    despues_de_la_primera = conteos(session)

    segunda = compras.post(IMPORTACION, json=cuerpo(filas, id_lote=lote))
    assert segunda.status_code == 200, segunda.text
    repetida = segunda.json()
    assert repetida["repetida"] is True and repetida["articulos_creados"] == []
    assert [v["folio"] for v in repetida["vales"]] == [
        v["folio"] for v in sorted(primera.json()["vales"], key=lambda v: v["folio"])
    ]
    assert repetida["resumen"]["unidades"] == 6 and repetida["resumen"]["vales"] == 2
    assert conteos(session) == despues_de_la_primera
    assert existencia(session, "KEP", articulo(session, codigo)) == 5


def test_RG_09_el_lote_de_otra_persona_no_se_puede_reusar(compras, cliente_con):
    otra = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS})
    lote = str(uuid.uuid4())
    assert (
        compras.post(
            IMPORTACION, json=cuerpo([fila(unico("A"), cantidad=1)], id_lote=lote)
        ).status_code
        == 201
    )
    r = otra.post(IMPORTACION, json=cuerpo([fila(unico("B"), cantidad=1)], id_lote=lote))
    assert r.status_code == 409


def test_RG_09_un_lote_nuevo_con_las_mismas_filas_rechaza_lo_que_ya_se_importo(compras, session):
    codigo, pieza = unico("ART"), unico("PZA")
    filas = [
        fila(codigo, cantidad=2),
        fila(unico("T"), categoria=ELECTRICA, serie="S-1", codigo_pieza=pieza),
    ]
    importar(compras, filas)
    articulos_antes = conteos(session)["articulos"]
    segunda = importar(compras, filas, confirmar_repetido=True)  # el mismo archivo: I-12
    # Ningún artículo se duplica; la pieza que ya existe se avisa como error de su fila.
    assert segunda["resumen"]["articulos_creados"] == 0
    assert conteos(session)["articulos"] == articulos_antes
    assert [f["fila"] for f in segunda["filas_error"]] == [2]
    assert segunda["filas_error"][0]["motivos"][0]["codigo"] in (
        "CODIGO_REPETIDO",
        "SERIE_REPETIDA",
    )
    assert len(list(session.scalars(select(Pieza).where(Pieza.codigo == pieza)))) == 1


# ------------------------------------------------------------------------------ CF-02


def test_CF_02_los_articulos_nuevos_toman_la_plantilla_de_su_categoria(compras, session):
    codigo = unico("PLANT")
    importar(compras, [fila(codigo, categoria="EPP de dotación", cantidad=10)])
    nuevo = articulo(session, codigo)
    assert nuevo.control == "CANTIDAD" and nuevo.retornable is False
    assert nuevo.limite_cantidad == 3 and nuevo.limite_periodo_dias == 7
    assert nuevo.activo is True


def test_CF_02_la_categoria_elegida_para_las_filas_desconocidas_se_aplica(compras, session):
    a, b = unico("A"), unico("B")
    salida = importar(
        compras,
        [
            fila(a, categoria="Cosas raras", cantidad=1),
            fila(b, categoria="Otras", cantidad=1),
        ],
        mapa_categorias={"Cosas raras": categoria_id(session, "EPP de dotación")},
        categoria_por_defecto_id=categoria_id(session, MANUAL),
    )
    assert salida["resumen"]["articulos_creados"] == 2
    por_codigo = {x["codigo"]: x for x in salida["articulos_creados"]}
    assert por_codigo[a]["categoria"] == "EPP de dotación"
    assert por_codigo[b]["categoria"] == MANUAL
    assert articulo(session, a).limite_cantidad == 3


def test_CF_02_sin_categoria_elegida_las_filas_de_categoria_desconocida_no_entran(compras, session):
    desconocida, buena = unico("D"), unico("B")
    salida = importar(
        compras,
        [fila(desconocida, categoria="Cosas raras", cantidad=1), fila(buena, cantidad=1)],
    )
    assert articulo(session, desconocida) is None and articulo(session, buena) is not None
    assert salida["filas_error"][0]["motivos"][0]["codigo"] == "CATEGORIA_DESCONOCIDA"


# ------------------------------------------------------------------------------ I-02


def test_I_02_cada_fila_por_pieza_crea_su_pieza_con_codigo_y_serie_en_el_almacen(compras, session):
    codigo = unico("TAL")
    codigos_pieza = [unico("PZA") for _ in range(3)]
    salida = importar(
        compras,
        [
            fila(codigo, nombre="Taladro", categoria=ELECTRICA, serie=f"SN-{i}", codigo_pieza=p)
            for i, p in enumerate(codigos_pieza)
        ],
    )
    assert salida["resumen"]["piezas"] == 3 and salida["resumen"]["articulos_creados"] == 1
    assert existencia(session, "KEP", articulo(session, codigo)) == 3
    piezas = list(session.scalars(select(Pieza).where(Pieza.codigo.in_(codigos_pieza))))
    assert sorted(p.numero_serie for p in piezas) == ["SN-0", "SN-1", "SN-2"]
    kepler = almacen(session, "KEP")
    for p in piezas:
        assert p.estado == EstadoPieza.APTO and p.ubicacion_id is not None
        registro = session.get(Codigo, p.codigo)
        assert registro.tipo == TipoCodigo.PIEZA and registro.ref_id == p.id
    movs = list(
        session.scalars(select(Movimiento).where(Movimiento.pieza_id.in_([p.id for p in piezas])))
    )
    assert len(movs) == 3 and all(m.cantidad == 1 for m in movs)
    assert kepler is not None


def test_I_03_la_pieza_que_pide_inspeccion_entra_pendiente_y_no_se_puede_entregar(compras, session):
    codigo, pieza_codigo = unico("ARN"), unico("PZA")
    salida = importar(
        compras,
        [fila(codigo, categoria=ALTURAS, serie="ARN-1", codigo_pieza=pieza_codigo)],
    )
    assert salida["resumen"]["piezas"] == 1
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == pieza_codigo))
    assert pieza.inspeccion_vigente_hasta is None  # sin inspección vigente: pendiente (I-03)
    assert articulo(session, codigo).requiere_inspeccion is True


def test_I_02_una_pieza_con_serie_o_codigo_repetido_no_entra_pero_las_demas_si(compras, session):
    repetido = unico("PZA")
    codigo = unico("TAL")
    salida = importar(
        compras,
        [
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza=repetido),
            fila(codigo, categoria=ELECTRICA, serie="S-2", codigo_pieza=repetido),
            fila(codigo, categoria=ELECTRICA, serie="S-1", codigo_pieza=unico("PZA")),
            fila(codigo, categoria=ELECTRICA, serie="S-3", codigo_pieza=unico("PZA")),
        ],
    )
    assert salida["resumen"]["piezas"] == 2 and salida["resumen"]["filas_con_error"] == 2
    assert {f["fila"] for f in salida["filas_error"]} == {2, 3}
    assert existencia(session, "KEP", articulo(session, codigo)) == 2


# ------------------------------------------------------------------------------ RG-12


def test_RG_12_con_catalogo_costos_el_costo_queda_en_el_articulo_nuevo(compras, session):
    codigo = unico("COS")
    importar(compras, [fila(codigo, cantidad=1, costo="$1,234.50")])
    assert str(articulo(session, codigo).costo_unitario) == "1234.50"


def test_RG_12_sin_catalogo_costos_el_costo_se_ignora_y_el_articulo_entra_sin_costo(
    cliente_con, session
):
    sin_costos = cliente_con({P.INVENTARIO_ENTRADAS, P.ALMACENES_TODOS, P.CATALOGO_ADMINISTRAR})
    codigo = unico("SINCOS")
    salida = importar(sin_costos, [fila(codigo, cantidad=2, costo="999")])
    assert salida["resumen"]["filas_importadas"] == 1
    assert articulo(session, codigo).costo_unitario is None
    assert any("costo" in a for a in salida["avisos"])
    assert existencia(session, "KEP", articulo(session, codigo)) == 2


def test_RG_12_un_costo_invalido_deja_la_fila_fuera_de_la_importacion(compras, session):
    codigo = unico("MALCOS")
    salida = importar(
        compras, [fila(codigo, cantidad=1, costo="caro"), fila(unico("OK"), cantidad=1)]
    )
    assert salida["filas_error"][0]["motivos"][0]["codigo"] == "COSTO_INVALIDO"
    assert articulo(session, codigo) is None


# ------------------------------------------------------------------------------ I-09


def test_I_09_la_importacion_no_registra_entradas_de_un_articulo_inactivo(compras, session):
    inactivo = crear_articulo(session, activo=False)
    antes = conteos(session)
    r = compras.post(IMPORTACION, json=confirmacion([fila(inactivo.codigo, cantidad=3)]))
    assert r.status_code == 422
    assert conteos(session) == antes


# ----------------------------------------------------------------------------- RG-10


def test_RG_10_un_codigo_ya_usado_por_otra_cosa_no_se_importa_como_articulo(compras, session):
    dueno = crear_articulo(session, control="PIEZA")
    from tests.movimientos.ayudas import crear_pieza

    pieza = crear_pieza(session, dueno)
    salida = importar(compras, [fila(pieza.codigo, cantidad=1), fila(unico("OK"), cantidad=1)])
    assert salida["filas_error"][0]["motivos"][0]["regla"] == "RG-10"
    assert salida["resumen"]["filas_importadas"] == 1


def test_I_06_un_nombre_con_formula_se_guarda_como_texto_y_no_rompe_nada(compras, session):
    codigo = unico("INY")
    importar(compras, [fila(codigo, nombre="=1+1", marca='@cmd|"/c calc"!A1', cantidad=1)])
    guardado = articulo(session, codigo)
    assert guardado.nombre == "=1+1" and guardado.marca.startswith("@cmd")
