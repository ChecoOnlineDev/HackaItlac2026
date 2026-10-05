"""Límite de tamaño del cuerpo de las peticiones (H8), como middleware ASGI puro.

Sin él, una petición de decenas de megas (incluso sin sesión) se leía completa. Aquí:

- Si trae `Content-Length` mayor que el límite de su ruta, responde 413 sin
  procesar el cuerpo (solo descarta lo que llegue, acotado, para que el cliente reciba la
  respuesta y no un reinicio de la conexión).
- Si no trae `Content-Length` (transferencia por trozos, `chunked`), cuenta los bytes mientras los
  recibe y responde 413 en cuanto pasa del límite, sin llamar a la aplicación. Como mucho se
  guarda en memoria un cuerpo del tamaño del límite, que es pequeño.
- Si cabe, la aplicación recibe el cuerpo tal cual.

El 413 es JSON del contrato `{codigo, mensaje, detalles}` con el código estable
`CUERPO_MUY_GRANDE`. Los límites salen de `config.py` y se eligen por ruta: 1 MB para JSON en
general, 12 MB al crear o evaluar un vale (puede llevar la firma y fotos de daño), 3 MB para la
foto de un trabajador y 6 MB para la importación.

No usa `BaseHTTPMiddleware` (leería y copiaría el cuerpo por su cuenta).
"""

import asyncio
import json
import re
from collections.abc import Callable, MutableMapping
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings, get_settings

CODIGO = "CUERPO_MUY_GRANDE"

# ANTES de responder 413 se descarta lo que siga llegando (uvicorn ya no entrega el cuerpo una
# vez enviada la respuesta), un rato y hasta cierto tamaño: si se cierra
# la conexión con el cliente todavía enviando, el sistema la reinicia y el cliente puede perder la
# respuesta 413. No se guarda nada de lo descartado.
DRENAJE_BYTES_MAXIMO = 64 * 1024 * 1024
DRENAJE_SEGUNDOS_MAXIMO = 10

_RUTA_VALES = re.compile(r"^/api/vales(/evaluar)?/?$")
_RUTA_FOTO_TRABAJADOR = re.compile(r"^/api/trabajadores/[^/]+/foto/?$")
_RUTA_IMPORTACION = re.compile(r"^/api/importacion(/.*)?$")


def limite_para(ajustes: Settings, ruta: str) -> int:
    """El límite de bytes del cuerpo para esa ruta."""
    if _RUTA_VALES.match(ruta):
        return ajustes.limite_cuerpo_vale
    if _RUTA_FOTO_TRABAJADOR.match(ruta):
        return ajustes.limite_cuerpo_foto_trabajador
    if _RUTA_IMPORTACION.match(ruta):
        return ajustes.limite_cuerpo_importacion
    return ajustes.limite_cuerpo_json


def _megas(limite: int) -> str:
    megas = limite / (1024 * 1024)
    return f"{megas:.0f}" if megas >= 10 or megas == int(megas) else f"{megas:.1f}"


async def _responder_413(send: Send, limite: int) -> None:
    cuerpo = json.dumps(
        {
            "codigo": CODIGO,
            "mensaje": f"El envío es demasiado grande. Lo máximo permitido es {_megas(limite)} MB.",
            "detalles": {"limite_bytes": limite},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(cuerpo)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": cuerpo})


async def _descartar_resto(receive: Receive) -> None:
    """Lee y tira el resto del cuerpo (acotado en bytes y en tiempo) para que el cliente reciba
    su 413 en vez de un reinicio de la conexión."""

    async def leer() -> None:
        total = 0
        while total < DRENAJE_BYTES_MAXIMO:
            mensaje = await receive()
            if mensaje["type"] == "http.disconnect":
                return
            total += len(mensaje.get("body", b""))
            if not mensaje.get("more_body", False):
                return

    try:
        await asyncio.wait_for(leer(), timeout=DRENAJE_SEGUNDOS_MAXIMO)
    except TimeoutError:
        return


def _cabecera(scope: Scope, nombre: bytes) -> bytes | None:
    for clave, valor in scope.get("headers", []):
        if clave == nombre:
            return valor
    return None


class LimiteCuerpoMiddleware:
    """Rechaza con 413 las peticiones cuyo cuerpo pasa del límite de su ruta."""

    def __init__(
        self,
        app: ASGIApp,
        obtener_ajustes: Callable[[], Settings] = get_settings,
    ) -> None:
        self.app = app
        self.obtener_ajustes = obtener_ajustes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        longitud = _cabecera(scope, b"content-length")
        por_trozos = _cabecera(scope, b"transfer-encoding") is not None
        if longitud is None and not por_trozos:
            await self.app(scope, receive, send)  # sin cuerpo (GET, HEAD...)
            return

        limite = limite_para(self.obtener_ajustes(), scope["path"])
        if longitud is not None:
            try:
                declarado = int(longitud)
            except ValueError:
                declarado = limite + 1  # una longitud ilegible no se acepta
            if declarado > limite:
                await _descartar_resto(receive)
                await _responder_413(send, limite)
                return
            await self.app(scope, receive, send)
            return

        # Sin `Content-Length`: se cuenta lo que llega y se corta al pasar del límite.
        mensajes: list[MutableMapping[str, Any]] = []
        total = 0
        while True:
            mensaje: Message = await receive()
            if mensaje["type"] == "http.disconnect":
                return
            total += len(mensaje.get("body", b""))
            if total > limite:
                if mensaje.get("more_body", False):
                    await _descartar_resto(receive)
                await _responder_413(send, limite)
                return
            mensajes.append(mensaje)
            if not mensaje.get("more_body", False):
                break

        pendientes = iter(mensajes)

        async def repetir() -> Message:
            try:
                return next(pendientes)
            except StopIteration:
                return await receive()  # lo que siga (por ejemplo, la desconexión)

        await self.app(scope, repetir, send)


__all__ = ["CODIGO", "LimiteCuerpoMiddleware", "limite_para"]
