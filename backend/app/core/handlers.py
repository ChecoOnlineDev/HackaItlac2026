"""Traducción de excepciones a respuestas `{codigo, mensaje, detalles}`."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.excepciones import AppError

log = logging.getLogger("imhotep")

# Códigos de api-contracts.md -> estado HTTP. Un código nuevo se agrega aquí.
STATUS_POR_CODIGO: dict[str, int] = {
    "NO_AUTENTICADO": 401,
    "SIN_PERMISO": 403,
    "PIN_INCORRECTO": 403,
    "NO_ENCONTRADO": 404,
    "VALE_CAMBIO": 409,
    "ALMACEN_CAMBIO": 409,
    "CODIGO_REPETIDO": 409,
    "CON_PENDIENTES": 409,
    "CON_MOVIMIENTOS": 409,
    "NO_CANCELABLE": 409,
    "CONFLICTO": 409,
    "AUTORIZACION_PROPIA": 403,
    "AUTORIZACION_RESUELTA": 409,
    "AUTORIZACION_INVALIDA": 409,
    "RENGLON_NO_AUTORIZABLE": 422,
    "DATOS_INVALIDOS": 422,
    "DEMASIADOS_INTENTOS": 429,
}


def respuesta_error(status: int, codigo: str, mensaje: str, detalles: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"codigo": codigo, "mensaje": mensaje, "detalles": detalles},
    )


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        status = STATUS_POR_CODIGO.get(exc.codigo, 400)
        respuesta = respuesta_error(status, exc.codigo, exc.mensaje, exc.detalles)
        segundos = getattr(exc, "segundos", None)
        if status == 429 and segundos:
            respuesta.headers["Retry-After"] = str(segundos)
        return respuesta

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        detalles = [
            {
                "campo": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")),
                "mensaje": e["msg"],
            }
            for e in exc.errors()
        ]
        return respuesta_error(
            422, "DATOS_INVALIDOS", "Falta un dato o tiene una forma incorrecta.", detalles
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return respuesta_error(404, "NO_ENCONTRADO", "No se encontró lo que buscas.")
        if exc.status_code == 405:
            return respuesta_error(405, "METODO_NO_PERMITIDO", "Esa acción no está disponible.")
        return respuesta_error(exc.status_code, "ERROR", "No se pudo completar la solicitud.")

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Error inesperado en %s %s", request.method, request.url.path)
        return respuesta_error(
            500, "ERROR_INTERNO", "Ocurrió un error inesperado. Intenta de nuevo."
        )
