"""Comando `uv run python -m app.mantenimiento sembrar-categorias`.

Corre contra una base vacía (solo migraciones), aparte de la de pruebas.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from app.config import get_settings
from app.mantenimiento import main
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.categorias_iniciales import CATEGORIAS
from app.modulos.catalogo.models import Categoria
from tests.conftest import NOMBRE_BD_PRUEBAS, borrar_base, config_alembic, recrear_base


@pytest.fixture
def base_vacia():
    nombre = f"{NOMBRE_BD_PRUEBAS}_categorias"
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
        codigo = main(["sembrar-categorias"], session=s, salida=lineas.append)
    return codigo, "\n".join(lineas)


def test_sembrar_categorias_crea_las_siete_en_una_base_vacia(base_vacia):
    codigo, texto = correr(base_vacia)
    assert codigo == 0 and "7 categorías" in texto
    with Session(bind=base_vacia) as s:
        por_nombre = {c.nombre: c for c in s.scalars(select(Categoria))}
        assert set(por_nombre) == set(CATEGORIAS) and len(por_nombre) == 7
        alturas = por_nombre["Equipo de alturas"]
        assert alturas.control == "PIEZA" and alturas.requiere_inspeccion is True
        assert por_nombre["Consumibles de trabajo"].retornable is False
        assert por_nombre["Herramienta manual"].control == "CANTIDAD"
        assert list(s.scalars(select(Auditoria.accion))).count("categoria.crear") == 7


def test_sembrar_categorias_es_seguro_de_repetir(base_vacia):
    correr(base_vacia)
    codigo, texto = correr(base_vacia)
    assert codigo == 0 and "Ya están todas" in texto
    with Session(bind=base_vacia) as s:
        assert len(list(s.scalars(select(Categoria)))) == 7


def test_sembrar_categorias_no_pisa_lo_que_la_empresa_edito(base_vacia):
    correr(base_vacia)
    with Session(bind=base_vacia) as s:
        manual = s.scalar(select(Categoria).where(Categoria.nombre == "Herramienta manual"))
        manual.limite_cantidad = 9
        s.delete(s.scalar(select(Categoria).where(Categoria.nombre == "EPP básico")))
        s.commit()
    codigo, texto = correr(base_vacia)
    assert codigo == 0 and "1 categorías" in texto and "EPP básico" in texto
    with Session(bind=base_vacia) as s:
        manual = s.scalar(select(Categoria).where(Categoria.nombre == "Herramienta manual"))
        assert manual.limite_cantidad == 9  # lo editado se conserva
        assert len(list(s.scalars(select(Categoria)))) == 7
