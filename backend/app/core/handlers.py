"""Traducción de excepciones a respuestas `{codigo, mensaje, detalles}`."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.excepciones import AppError
from app.core.reintento import es_interbloqueo

log = logging.getLogger("imhotep")

# Códigos de api-contracts.md -> estado HTTP. Un código nuevo se agrega aquí.
STATUS_POR_CODIGO: dict[str, int] = {
    "NO_AUTENTICADO": 401,
    "SESION_VENCIDA": 401,
    "SIN_PERMISO": 403,
    "PIN_INCORRECTO": 403,
    "NO_ENCONTRADO": 404,
    "VALE_CAMBIO": 409,
    "ALMACEN_CAMBIO": 409,
    "USUARIO_EXISTE": 409,
    "ULTIMO_ADMINISTRADOR": 409,
    "ROL_EXISTE": 409,
    "ROL_PROTEGIDO": 409,
    "ROL_EN_USO": 409,
    "AUTO_BLOQUEO": 409,
    "CODIGO_REPETIDO": 409,
    "TRABAJADOR_EXISTE": 409,
    "CON_PENDIENTES": 409,
    "CON_MOVIMIENTOS": 409,
    "NO_CANCELABLE": 409,
    "CONFLICTO": 409,
    "TRANSICION_INVALIDA": 409,
    "ID_CLIENTE_EN_USO": 409,
    "ARCHIVO_REPETIDO": 409,
    "CLAVE_REPETIDA": 409,
    "NOMBRE_REPETIDO": 409,
    "ARTICULO_REPETIDO": 409,
    "YA_HAY_CENTRAL": 409,
    "CLAVE_CON_FOLIOS": 409,
    "CON_EXISTENCIAS": 409,
    "CON_TRASPASOS_EN_TRANSITO": 409,
    "CON_HIJOS_ACTIVOS": 409,
    "CON_USUARIOS": 409,
    "PADRE_CERRADO": 409,
    "ALMACEN_CERRADO": 409,
    "FILAS_CON_ERROR": 409,
    "SERIE_YA_REGISTRADA": 409,
    "SERIE_REPETIDA": 409,
    "TRASPASO_MUY_GRANDE": 422,
    "PADRE_INVALIDO": 422,
    "ENTRADA_SOLO_KEPLER": 422,
    "RUTA_SOLO_ADMINISTRADOR": 403,
    "AUTORIZACION_PROPIA": 403,
    "AUTORIZACION_RESUELTA": 409,
    "AUTORIZACION_INVALIDA": 409,
    "RENGLON_NO_AUTORIZABLE": 422,
    "AJUSTE_PROPIO": 403,
    "AJUSTE_NO_PERMITIDO": 409,
    "VIGENCIA_EXCEDIDA": 422,
    "DATOS_INVALIDOS": 422,
    "DEMASIADOS_INTENTOS": 429,
    "CUERPO_MUY_GRANDE": 413,
    "SERVICIO_NO_DISPONIBLE": 503,
    "TIPO_NO_IMPLEMENTADO": 501,
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
        if es_interbloqueo(exc):  # un choque transitorio de la base no es un error interno
            log.warning("Interbloqueo sin reintento en %s %s", request.method, request.url.path)
            return respuesta_error(
                503,
                "SERVICIO_NO_DISPONIBLE",
                "El servicio está ocupado en este momento. Intenta de nuevo.",
            )
        log.exception("Error inesperado en %s %s", request.method, request.url.path)
        return respuesta_error(
            500, "ERROR_INTERNO", "Ocurrió un error inesperado. Intenta de nuevo."
        )
