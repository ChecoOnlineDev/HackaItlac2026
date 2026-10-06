"""Infraestructura de pruebas contra MySQL REAL.

- La base de pruebas se llama `{MYSQL_DATABASE}_test_{TEST_DB_SUFFIX}` (sufijo por defecto `main`).
  Cada carpeta de trabajo que corra pruebas en paralelo contra el mismo servidor MySQL debe usar
  un `TEST_DB_SUFFIX` distinto. Se borra y se vuelve a crear en cada corrida.
- Se aplica `alembic upgrade head` una vez por sesión de pruebas y se cargan los datos de prueba
  (`app.datos_prueba`) como línea base.
- Cada prueba corre dentro de una transacción con savepoints que se revierte al terminar: los
  `commit()` de los services solo liberan un savepoint.

Fixtures para todos los módulos:
  client            TestClient sin sesión.
  session           Session de SQLAlchemy de la transacción de la prueba (la misma de la API).
  cliente_como      `cliente_como("Almacenista")` -> TestClient con la sesión iniciada de ese rol.
  usuario_por_rol   `usuario_por_rol("Almacenista")` -> UsuarioPrueba (usuario, contrasena, pin).
  crear_usuario     `crear_usuario({P.X}, almacen="KEP")` -> UsuarioPrueba con rol nuevo.
  iniciar_sesion    `iniciar_sesion(client, usuario)` -> login (cookie en el client).
"""

import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings, get_settings

# ---------------------------------------------------------------- base de pruebas

_BASE = Settings()
_SUFIJO = _BASE.test_db_suffix
if not re.fullmatch(r"[A-Za-z0-9_]{1,30}", _SUFIJO):
    raise RuntimeError("TEST_DB_SUFFIX solo admite letras, números y guion bajo")
# conftest puede importarse dos veces (como `conftest` y como `tests.conftest`): el nombre base
# de la base se fija la primera vez.
_NOMBRE_BASE = os.environ.setdefault("IMHOTEP_BD_BASE", _BASE.mysql_database)
NOMBRE_BD_PRUEBAS = f"{_NOMBRE_BASE}_test_{_SUFIJO}"
assert "_test_" in NOMBRE_BD_PRUEBAS

# Las pruebas crean y borran bases: usan root si hay clave de root (si no, el usuario normal).
_USUARIO_ADMIN = "root" if _BASE.mysql_root_password else _BASE.mysql_user
_CLAVE_ADMIN = _BASE.mysql_root_password or _BASE.mysql_password


def _engine_servidor() -> Engine:
    return create_engine(
        _BASE.url_servidor(_USUARIO_ADMIN, _CLAVE_ADMIN), isolation_level="AUTOCOMMIT"
    )


def recrear_base(nombre: str) -> None:
    assert "_test_" in nombre
    engine = _engine_servidor()
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{nombre}`"))
        conn.execute(
            text(f"CREATE DATABASE `{nombre}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        )
    engine.dispose()


def borrar_base(nombre: str) -> None:
    assert "_test_" in nombre
    engine = _engine_servidor()
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{nombre}`"))
    engine.dispose()


# Todo `app.*` toma la base de pruebas a través de las variables de entorno.
os.environ["MYSQL_DATABASE"] = NOMBRE_BD_PRUEBAS
os.environ["MYSQL_USER"] = _USUARIO_ADMIN
os.environ["MYSQL_PASSWORD"] = _CLAVE_ADMIN
os.environ["COOKIE_SEGURA"] = "false"
get_settings.cache_clear()

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


def config_alembic() -> Config:
    return Config(str(RAIZ_BACKEND / "alembic.ini"))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    assert get_settings().mysql_database == NOMBRE_BD_PRUEBAS
    recrear_base(NOMBRE_BD_PRUEBAS)
    command.upgrade(config_alembic(), "head")

    from app.db import get_engine, get_sessionmaker

    motor = get_engine()
    # Línea base: roles, usuarios y almacenes de prueba (más lo que carguen los demás módulos).
    from app.datos_prueba import cargar_todo

    with get_sessionmaker()() as sesion:
        cargar_todo(sesion)
        # FEAT-003: los puestos de prueba traen dotación (propuesta del PDF). La línea base de las
        # pruebas la quita para que las entregas de las demás pruebas, que no hablan de dotación,
        # no pidan observación (E-09). Las pruebas de la dotación la arman con `dotacion_de_prueba`.
        sesion.execute(text("DELETE FROM dotacion"))
        sesion.commit()
    yield motor
    motor.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Sesión dentro de una transacción externa que siempre se revierte."""
    conexion = engine.connect()
    externa = conexion.begin()
    sesion = Session(
        bind=conexion,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    yield sesion
    sesion.close()
    externa.rollback()
    conexion.close()


@pytest.fixture
def app(session: Session):
    from app.db import get_session
    from app.main import create_app

    aplicacion = create_app()
    aplicacion.dependency_overrides[get_session] = lambda: session
    return aplicacion


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as cliente:
        yield cliente


# -------------------------------------------------------------------- usuarios

# Rol -> usuario de los datos de prueba (app/modulos/acceso/datos_prueba.py).
USUARIO_DE_ROL = {
    "Administrador": "admin",
    "Almacenista": "almacenista",
    "Supervisor": "supervisor",
    "Compras": "compras",
    "Recursos Humanos": "rh",
}


@dataclass(frozen=True)
class UsuarioPrueba:
    usuario: str
    contrasena: str
    pin: str | None = None


@pytest.fixture
def usuario_por_rol() -> Callable[[str], UsuarioPrueba]:
    ajustes = get_settings()

    def _buscar(rol: str) -> UsuarioPrueba:
        return UsuarioPrueba(
            USUARIO_DE_ROL[rol], ajustes.clave_datos_prueba, ajustes.pin_datos_prueba
        )

    return _buscar


def iniciar_sesion_en(client: TestClient, usuario: UsuarioPrueba, contrasena: str | None = None):
    return client.post(
        "/api/sesion",
        json={"usuario": usuario.usuario, "contrasena": contrasena or usuario.contrasena},
    )


@pytest.fixture
def iniciar_sesion() -> Callable[..., object]:
    return iniciar_sesion_en


@pytest.fixture
def cliente_como(app, usuario_por_rol) -> Iterator[Callable[[str], TestClient]]:
    clientes: list[TestClient] = []

    def _cliente(rol: str) -> TestClient:
        cliente = TestClient(app)
        respuesta = iniciar_sesion_en(cliente, usuario_por_rol(rol))
        assert respuesta.status_code == 200, respuesta.text
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()


@pytest.fixture
def crear_usuario(session: Session) -> Callable[..., UsuarioPrueba]:
    """Crea un rol nuevo con exactamente esos permisos y un usuario con ese rol."""
    from app.modulos.acceso.models import Rol, Usuario
    from app.modulos.acceso.repository import RolRepository, UsuarioRepository
    from app.modulos.almacenes.repository import AlmacenRepository
    from app.seguridad import hashear_secreto

    contador = {"n": 0}

    @lru_cache
    def _hash_prueba() -> str:
        return hashear_secreto("Clave-prueba-123")

    def _crear(
        permisos: set[str] | frozenset[str],
        *,
        almacen: str | None = None,
        activo: bool = True,
        pin: str | None = None,
        nombre_rol: str | None = None,
    ) -> UsuarioPrueba:
        contador["n"] += 1
        n = contador["n"]
        roles = RolRepository(session)
        rol = roles.add(Rol(nombre=nombre_rol or f"Rol de prueba {n}"))
        roles.reemplazar_permisos(rol.id, set(permisos))
        sede = AlmacenRepository(session).get_by_clave(almacen) if almacen else None
        contrasena = "Clave-prueba-123"
        UsuarioRepository(session).add(
            Usuario(
                usuario=f"usuario_prueba_{n}",
                nombre=f"Usuario de prueba {n}",
                contrasena_hash=_hash_prueba(),
                pin_hash=hashear_secreto(pin) if pin else None,
                rol_id=rol.id,
                almacen_id=sede.id if sede else None,
                activo=activo,
            )
        )
        session.commit()
        return UsuarioPrueba(f"usuario_prueba_{n}", contrasena, pin)

    return _crear
