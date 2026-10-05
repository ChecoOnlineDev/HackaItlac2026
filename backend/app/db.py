"""Motor, sesión y base declarativa.

La sesión NO hace commit automático: el commit lo controla el service (una operación = una
transacción). El repository solo hace `add`, `flush` y `execute`.
"""

from collections.abc import Iterator
from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import CheckConstraint, DateTime, MetaData, create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Fecha y hora UTC sin zona (RG-11), con microsegundos en MySQL para ordenar movimientos.
FechaHora = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def check_enum(columna: str, enum: type[StrEnum], nombre: str | None = None) -> CheckConstraint:
    """CHECK que limita una columna VARCHAR a los valores de un enum de dominio.

    El nombre final queda `ck_<tabla>_<nombre>` por la convención de nombres.
    """
    valores = ", ".join(f"'{e.value}'" for e in enum)
    return CheckConstraint(f"{columna} IN ({valores})", name=nombre or columna)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=3600)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición, sin commit automático."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


SesionDep = Annotated[Session, Depends(get_session)]
