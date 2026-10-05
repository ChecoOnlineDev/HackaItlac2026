"""El verificador de invariantes (`tests/invariantes.py`) detecta lo que dice detectar.

Una prueba por invariante: se opera por la API, se comprueba que todo cuadra y después se
corrompe la base A MANO (dentro de la transacción de la prueba, que se revierte) y se comprueba
que el verificador lo señala con el número de la invariante.
"""

import uuid

import pytest
from sqlalchemy import delete, select, update

from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models import Articulo, Codigo, Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, SerieFolio, Vale
from tests.ayudas_guion import alta_trabajador, entregar
from tests.invariantes import tomar_huella, verificar_invariantes, violaciones


@pytest.fixture
def escenario(cliente_como, session):
    """Un trabajador con un respirador (por cantidad) y un minipulidor (pieza) en resguardo."""
    rh, kep = cliente_como("Recursos Humanos"), cliente_como("Almacenista")
    trabajador = alta_trabajador(rh)
    vale = entregar(
        kep,
        trabajador["id"],
        [{"codigo": "RESP-6200"}, {"codigo": "HER-001"}, {"codigo": "GUANTE-CAR", "cantidad": 2}],
    )
    return {"trabajador": trabajador, "vale": vale, "huella": tomar_huella(session)}


def _articulo(session, codigo: str) -> Articulo:
    return session.scalar(select(Articulo).where(Articulo.codigo == codigo))


def _ub_trabajador(session, trabajador_id: str) -> Ubicacion:
    return session.scalar(
        select(Ubicacion).where(Ubicacion.trabajador_id == uuid.UUID(trabajador_id))
    )


def _ub_virtual(session, virtual: str) -> Ubicacion:
    return session.scalar(select(Ubicacion).where(Ubicacion.virtual == virtual))


def _debe_romper(session, marca: str, huella=None) -> list[str]:
    errores = violaciones(session, huella)
    assert any(marca in e for e in errores), f"no se detectó {marca}: {errores}"
    with pytest.raises(AssertionError, match="Invariantes rotas"):
        verificar_invariantes(session, huella)
    return errores


def test_la_linea_base_y_una_entrega_real_cumplen_todas_las_invariantes(escenario, session):
    verificar_invariantes(session)
    verificar_invariantes(session, escenario["huella"])


def test_invariante_1_existencia_distinta_de_la_suma_de_movimientos(escenario, session):
    articulo = _articulo(session, "RESP-6200")
    session.execute(
        update(Existencia)
        .where(Existencia.articulo_id == articulo.id)
        .where(Existencia.cantidad == 39)
        .values(cantidad=40)
    )
    _debe_romper(session, "[1]")


def test_invariante_1_el_saldo_guardado_en_un_movimiento_no_coincide(escenario, session):
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(escenario["vale"]["id"]))
        .where(Movimiento.renglon == 1)
        .values(saldo_destino=99)
    )
    _debe_romper(session, "saldo_destino=99")


def test_invariante_2_proveedor_no_lleva_existencia(escenario, session):
    articulo = _articulo(session, "RESP-6200")
    session.add(
        Existencia(
            ubicacion_id=_ub_virtual(session, "PROVEEDOR").id,
            articulo_id=articulo.id,
            cantidad=1,
        )
    )
    _debe_romper(session, "[2] PROVEEDOR lleva existencia")


def test_invariante_3_una_pieza_sin_pieza_id_o_un_articulo_por_cantidad_con_pieza_id(
    escenario, session
):
    vale_id = uuid.UUID(escenario["vale"]["id"])
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == vale_id, Movimiento.renglon == 2)  # el minipulidor
        .values(pieza_id=None)
    )
    _debe_romper(session, "artículo por pieza sin pieza_id")
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == "HER-001"))
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == vale_id, Movimiento.renglon == 2)
        .values(pieza_id=pieza.id)
    )
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == vale_id, Movimiento.renglon == 1)  # respirador por cantidad
        .values(pieza_id=pieza.id, cantidad=1)
    )
    _debe_romper(session, "artículo por cantidad con pieza_id")


def test_invariante_4_la_pieza_no_esta_donde_termino_su_ultimo_movimiento(escenario, session):
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == "HER-001"))
    kepler = session.scalar(select(Ubicacion).where(Ubicacion.almacen_id.is_not(None)))
    assert pieza.ubicacion_id != kepler.id
    session.execute(update(Pieza).where(Pieza.id == pieza.id).values(ubicacion_id=kepler.id))
    _debe_romper(session, "[4] pieza HER-001")


def test_invariante_5_un_movimiento_modificado_se_detecta_contra_la_huella(escenario, session):
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(escenario["vale"]["id"]), Movimiento.renglon == 1)
        .values(observacion="editado a escondidas")
    )
    _debe_romper(session, "[5/10]", escenario["huella"])


def test_invariante_5_un_vale_borrado_o_con_estado_incoherente(escenario, session):
    vale_id = uuid.UUID(escenario["vale"]["id"])
    session.execute(update(Vale).where(Vale.id == vale_id).values(estado="CANCELADO"))
    _debe_romper(session, "está CANCELADO y tiene 0 vales de cancelación")
    session.execute(update(Vale).where(Vale.id == vale_id).values(estado="RECIBIDO"))
    _debe_romper(session, "tiene estado RECIBIDO")


def test_invariante_5_solo_el_estado_del_vale_puede_cambiar(escenario, session):
    # El estado cambia (aunque aquí sea incoherente, la huella no lo cuenta como edición del vale).
    session.execute(
        update(Vale).where(Vale.id == uuid.UUID(escenario["vale"]["id"])).values(estado="RECIBIDO")
    )
    errores = violaciones(session, escenario["huella"])
    assert not any("[5/10]" in e for e in errores)


def test_invariante_6_un_codigo_que_no_esta_registrado_o_apunta_a_otra_cosa(escenario, session):
    session.execute(delete(Codigo).where(Codigo.codigo == "HER-001"))
    _debe_romper(session, "el código 'HER-001' no está registrado")
    articulo = _articulo(session, "RESP-6200")
    session.add(Codigo(codigo="HER-001", tipo="ARTICULO", ref_id=articulo.id))
    _debe_romper(session, "[6] pieza HER-001")


def test_invariante_8_no_adeudo_vigente_con_retornables_en_resguardo(escenario, session):
    vale = session.get(Vale, uuid.UUID(escenario["vale"]["id"]))
    session.add(
        Vale(
            id_cliente=uuid.uuid4(),
            tipo="NO_ADEUDO",
            folio="KEP-NAD-000001",
            almacen_id=vale.almacen_id,
            trabajador_id=vale.trabajador_id,
            responsable_id=vale.responsable_id,
            token="token-de-prueba-no-adeudo",
            creado_en=vale.creado_en.replace(year=vale.creado_en.year + 1),
        )
    )
    session.flush()
    errores = _debe_romper(session, "[8]")
    assert any("tenía retornables en resguardo" in e for e in errores)
    assert any("tiene el no adeudo KEP-NAD-000001 vigente" in e for e in errores)


def test_invariante_9_un_vale_sin_movimientos(escenario, session):
    session.execute(
        delete(Movimiento).where(Movimiento.vale_id == uuid.UUID(escenario["vale"]["id"]))
    )
    _debe_romper(session, "no tiene movimientos")


def test_RG_06_huecos_y_contador_atrasado_en_los_folios(escenario, session):
    vale = session.get(Vale, uuid.UUID(escenario["vale"]["id"]))
    serie = session.get(SerieFolio, (vale.almacen_id, "ENTREGA"))
    assert vale.folio.endswith(f"{serie.ultimo:06d}")
    session.execute(
        update(SerieFolio)
        .where(SerieFolio.almacen_id == vale.almacen_id, SerieFolio.tipo == "ENTREGA")
        .values(ultimo=serie.ultimo + 1)
    )
    _debe_romper(session, "serie_folio KEP-ENT")
    session.execute(update(Vale).where(Vale.id == vale.id).values(folio="KEP-ENT-000007"))
    _debe_romper(session, "huecos o repetidos")
