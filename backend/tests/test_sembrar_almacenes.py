"""Comando `uv run python -m app.mantenimiento sembrar-almacenes` (FEAT-008, 4.1.5).

Corre contra una base vacía (solo migraciones), aparte de la de pruebas.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from app.config import get_settings
from app.mantenimiento import main
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.auditoria.models import Auditoria
from tests.conftest import NOMBRE_BD_PRUEBAS, borrar_base, config_alembic, recrear_base


@pytest.fixture
def base_vacia():
    nombre = f"{NOMBRE_BD_PRUEBAS}_siembra"
    recrear_base(nombre)
    motor = create_engine(get_settings().database_url.set(database=nombre))
    cfg = config_alembic()
    with motor.begin() as conexion:
        cfg.attributes["connection"] = conexion
        command.upgrade(cfg, "head")
    try:
        yield motor
    finally:
        motor.dispose()
        borrar_base(nombre)


def correr(motor) -> tuple[int, str]:
    lineas: list[str] = []
    with Session(bind=motor) as s:
        codigo = main(["sembrar-almacenes"], session=s, salida=lineas.append)
    return codigo, "\n".join(lineas)


def test_sembrar_almacenes_crea_la_red_del_reto_en_una_base_vacia(base_vacia):
    codigo, texto = correr(base_vacia)
    assert codigo == 0 and "6 almacenes" in texto
    with Session(bind=base_vacia) as s:
        por_clave = {a.clave: a for a in s.scalars(select(Almacen))}
        assert set(por_clave) == {"KEP", "CON", "MID", "HYL", "LAM", "MIN"}
        assert por_clave["KEP"].tipo == "CENTRAL" and por_clave["KEP"].padre_id is None
        assert por_clave["CON"].tipo == "SUBALMACEN"
        assert por_clave["CON"].padre_id == por_clave["KEP"].id
        for clave in ("MID", "HYL", "LAM", "MIN"):
            assert por_clave[clave].tipo == "PROYECTO"
            assert por_clave[clave].padre_id == por_clave["CON"].id
        ubicaciones = list(s.scalars(select(Ubicacion)))
        assert sum(u.almacen_id is not None for u in ubicaciones) == 6
        assert {u.virtual for u in ubicaciones if u.virtual} == {
            "PROVEEDOR", "EN_TRANSITO", "CONSUMIDO", "BAJA",
        }  # fmt: skip
        acciones = list(s.scalars(select(Auditoria.accion)))
        assert acciones.count("almacen.crear") == 6


def test_sembrar_almacenes_es_seguro_de_repetir(base_vacia):
    correr(base_vacia)
    codigo, texto = correr(base_vacia)
    assert codigo == 0 and "Ya hay almacenes" in texto
    with Session(bind=base_vacia) as s:
        assert len(list(s.scalars(select(Almacen)))) == 6


def test_sembrar_almacenes_no_hace_nada_si_ya_hay_alguno(session):
    # La base de pruebas ya trae los almacenes de prueba.
    lineas: list[str] = []
    antes = len(list(session.scalars(select(Almacen))))
    assert main(["sembrar-almacenes"], session=session, salida=lineas.append) == 0
    assert "Ya hay almacenes" in lineas[0]
    assert len(list(session.scalars(select(Almacen)))) == antes
