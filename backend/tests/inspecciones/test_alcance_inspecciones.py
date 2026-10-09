"""AC-06 y H11: las inspecciones y el ajuste de vigencia solo alcanzan piezas del almacén propio.

Una pieza es del almacén donde está; la que tiene un trabajador, del almacén de su última entrega.
Fuera de alcance se responde 404, igual que una pieza que no existe. El Administrador alcanza todas.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Categoria
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import Trabajador

PUNTOS = {k: None for k in ("etiquetas", "costuras", "cintas", "herrajes", "conectores")}

RUTA = "/api/piezas"


@pytest.fixture
def armar(session):
    """`armar("MID")` crea una pieza por serie ubicada en ese almacén."""
    categoria = session.scalar(select(Categoria).where(Categoria.nombre == "Equipo de alturas"))
    articulo = CatalogoService(session).crear_articulo(
        ArticuloCreate(
            codigo=f"ART-ALC-{uuid.uuid4().hex[:6]}",
            nombre="Arnés de prueba",
            categoria_id=categoria.id,
            requiere_inspeccion=True,
            vigencia_inspeccion_dias=30,
        ),
        actor_id=None,
    )
    almacenes = AlmacenService(session)

    def _armar(clave: str):
        pieza = CatalogoService(session).registrar_pieza(
            articulo.id, f"PZA-ALC-{uuid.uuid4().hex[:8]}", f"S-{uuid.uuid4().hex[:8]}"
        )
        pieza.ubicacion_id = almacenes.ubicacion_de_almacen(
            almacenes.obtener_por_clave(clave).id
        ).id
        session.commit()
        return pieza

    return _armar


def _inspeccionar(cliente, pieza):
    return cliente.post(
        f"{RUTA}/{pieza.id}/inspecciones", json={"resultado": "APTO", "puntos": PUNTOS}
    )


def _marcar_no_apta(cliente, pieza):
    return cliente.post(f"{RUTA}/{pieza.id}/estado", json={"observacion": "Costura floja"})


def test_AC_06_H11_un_almacenista_no_inspecciona_piezas_de_otro_almacen(
    cliente_como, session, armar
):
    de_midrex = armar("MID")
    kepler = cliente_como("Almacenista")  # almacenista de Kepler
    assert _inspeccionar(kepler, de_midrex).status_code == 404
    assert _marcar_no_apta(kepler, de_midrex).status_code == 404
    session.refresh(de_midrex)
    assert de_midrex.estado == "APTO" and de_midrex.inspeccion_vigente_hasta is None


def test_AC_06_H11_el_almacenista_inspecciona_las_piezas_de_su_almacen(cliente_como, armar):
    assert _inspeccionar(cliente_como("Almacenista"), armar("KEP")).status_code == 201


def test_AC_06_H11_el_administrador_inspecciona_piezas_de_cualquier_almacen(cliente_como, armar):
    admin = cliente_como("Administrador")
    assert _inspeccionar(admin, armar("MID")).status_code == 201
    assert _inspeccionar(admin, armar("KEP")).status_code == 201


def test_AC_06_H11_el_ajuste_de_vigencia_del_supervisor_es_solo_de_su_almacen(
    cliente_como, app, armar, session
):
    from datetime import timedelta

    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.core.tiempo import hoy_mx
    from tests.conftest import UsuarioPrueba, iniciar_sesion_en

    de_midrex = armar("MID")
    assert _inspeccionar(cliente_como("Administrador"), de_midrex).status_code == 201
    ajuste = {"vigente_hasta": (hoy_mx() + timedelta(days=10)).isoformat(), "motivo": "Revisión"}
    supervisor_kepler = cliente_como("Supervisor")
    r = supervisor_kepler.post(f"{RUTA}/{de_midrex.id}/ajuste-vigencia", json=ajuste)
    assert r.status_code == 404
    sup_mid = TestClient(app)
    ajustes = get_settings()
    assert (
        iniciar_sesion_en(sup_mid, UsuarioPrueba("sup_mid", ajustes.clave_datos_prueba)).status_code
        == 200
    )
    r = sup_mid.post(f"{RUTA}/{de_midrex.id}/ajuste-vigencia", json=ajuste)
    assert r.status_code == 201, r.text


def test_AC_06_H11_una_pieza_con_un_trabajador_es_del_almacen_de_su_ultima_entrega(
    cliente_como, session, armar
):
    pieza = armar("KEP")
    trabajador = Trabajador(numero_empleado=f"E-{uuid.uuid4().hex[:8]}", nombre="Ana Ruiz")
    session.add(trabajador)
    session.flush()
    almacenes = AlmacenService(session)
    origen = almacenes.ubicacion_de_almacen(almacenes.obtener_por_clave("MID").id)
    destino = almacenes.asegurar_ubicacion_de_trabajador(trabajador.id)
    responsable = session.scalar(select(Usuario).where(Usuario.usuario == "alm_mid"))
    vale = Vale(
        id_cliente=uuid.uuid4(),
        tipo=TipoVale.ENTREGA,
        folio=f"MID-ENT-ALC{uuid.uuid4().hex[:6]}",
        almacen_id=almacenes.obtener_por_clave("MID").id,
        trabajador_id=trabajador.id,
        estado="EMITIDO",
        responsable_id=responsable.id,
        token=uuid.uuid4().hex,
        creado_en=ahora_utc(),
    )
    session.add(vale)
    session.flush()
    session.add(
        Movimiento(
            vale_id=vale.id,
            renglon=1,
            articulo_id=pieza.articulo_id,
            pieza_id=pieza.id,
            cantidad=1,
            origen_id=origen.id,
            destino_id=destino.id,
        )
    )
    pieza.ubicacion_id = destino.id
    session.commit()
    # Con el trabajador, la pieza sigue siendo de Midrex (donde se entregó), no de Kepler.
    assert _inspeccionar(cliente_como("Almacenista"), pieza).status_code == 404
    assert _inspeccionar(cliente_como("Administrador"), pieza).status_code == 201
