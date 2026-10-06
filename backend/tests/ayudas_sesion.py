"""Ayudas de las pruebas de sesiones por dispositivo (AC-14 a AC-24).

Los vencimientos se prueban moviendo las fechas de `sesion_dispositivo` en la base (nunca con
pausas): la lógica compara contra el reloj del servidor, así que una fila con fechas del pasado
es indistinguible de una que de verdad envejeció.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import SesionDispositivo, Usuario
from app.seguridad import ALGORITMO_JWT, RUTA_COOKIE_REFRESH, huella_refresh

CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)


def cookie_acceso(cliente: TestClient) -> str:
    valor = cliente.cookies.get(get_settings().cookie_nombre)
    assert valor
    return valor


def cookie_refresh(cliente: TestClient) -> str:
    valor = cliente.cookies.get(get_settings().cookie_refresh_nombre, path=RUTA_COOKIE_REFRESH)
    assert valor
    return valor


def cliente_con(app, *, acceso: str | None = None, refresh: str | None = None) -> TestClient:
    """Un navegador nuevo con esas cookies (por ejemplo, el que tiene un token ya rotado)."""
    cliente = TestClient(app)
    ajustes = get_settings()
    if acceso is not None:
        cliente.cookies.set(ajustes.cookie_nombre, acceso, path="/")
    if refresh is not None:
        cliente.cookies.set(ajustes.cookie_refresh_nombre, refresh, path=RUTA_COOKIE_REFRESH)
    return cliente


def entrar(app, usuario, *, agente: str | None = None) -> TestClient:
    """Un dispositivo nuevo con sesión iniciada."""
    cliente = TestClient(app, headers={"user-agent": agente} if agente else None)
    r = cliente.post(
        "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
    )
    assert r.status_code == 200, r.text
    return cliente


def filas_de(session: Session, nombre_usuario: str) -> list[SesionDispositivo]:
    return list(
        session.scalars(
            select(SesionDispositivo)
            .join(Usuario, Usuario.id == SesionDispositivo.usuario_id)
            .where(Usuario.usuario == nombre_usuario)
            .order_by(SesionDispositivo.creado_en, SesionDispositivo.id)
        )
    )


def fila_de_token(session: Session, token: str) -> SesionDispositivo:
    fila = session.scalar(
        select(SesionDispositivo)
        .where(SesionDispositivo.refresh_hash == huella_refresh(token))
        .execution_options(populate_existing=True)
    )
    assert fila is not None
    return fila


def mover_fechas(session: Session, familia_id, **fechas: datetime) -> None:
    """Cambia fechas de todas las filas de una familia (por ejemplo `vence_absoluto`)."""
    session.execute(
        update(SesionDispositivo)
        .where(SesionDispositivo.familia_id == familia_id)
        .values(**fechas)
        .execution_options(synchronize_session="fetch")
    )
    session.flush()


def envejecer_rotacion(session: Session, token: str, segundos: int = 60) -> None:
    """Hace que el token ya rotado haya sido rotado hace `segundos` (fuera de la tolerancia)."""
    session.execute(
        update(SesionDispositivo)
        .where(SesionDispositivo.refresh_hash == huella_refresh(token))
        .values(revocada_en=ahora_utc() - timedelta(seconds=segundos))
    )
    session.flush()


def cookies_de_respuesta(respuesta) -> list[str]:
    return respuesta.headers.get_list("set-cookie")


def token_acceso_vencido(cliente: TestClient) -> str:
    """El token de acceso del cliente, pero con la hora de vencimiento ya pasada."""
    carga = jwt.decode(
        cookie_acceso(cliente),
        get_settings().clave_sesion,
        algorithms=[ALGORITMO_JWT],
        options={"verify_exp": False},
    )
    carga["exp"] = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
    return jwt.encode(carga, get_settings().clave_sesion, algorithm=ALGORITMO_JWT)


def vencer_acceso(cliente: TestClient) -> None:
    """Deja en el cliente el token de acceso vencido (reemplaza al que puso el servidor)."""
    vencido = token_acceso_vencido(cliente)
    nombre = get_settings().cookie_nombre
    for cookie in cliente.cookies.jar:
        if cookie.name == nombre:
            cookie.value = vencido  # la misma cookie, para no duplicarla en otro dominio
