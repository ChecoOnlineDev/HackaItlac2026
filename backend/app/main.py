"""Crea la aplicación: monta los routers de todos los módulos bajo `/api` y los handlers.

Todos los routers de módulo ya están registrados aquí (aunque estén vacíos): quien construya un
módulo llena su `router.py` y no toca este archivo.
"""

import logging

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import app.modelos_registro  # noqa: F401  (todos los modelos en Base.metadata)
from app.core.handlers import registrar_handlers
from app.db import SesionDep
from app.modulos.acceso.router import router as acceso_router
from app.modulos.almacenes.router import router as almacenes_router
from app.modulos.archivos.router import router as archivos_router
from app.modulos.auditoria.router import router as auditoria_router
from app.modulos.autorizaciones.router import router as autorizaciones_router
from app.modulos.catalogo.router import router as catalogo_router
from app.modulos.consulta.router import router as consulta_router
from app.modulos.importacion.router import router as importacion_router
from app.modulos.inspecciones.router import router as inspecciones_router
from app.modulos.movimientos.router import router as movimientos_router
from app.modulos.trabajadores.router import router as trabajadores_router

log = logging.getLogger("imhotep")

ROUTERS = (
    acceso_router,
    almacenes_router,
    catalogo_router,
    trabajadores_router,
    movimientos_router,
    autorizaciones_router,
    inspecciones_router,
    consulta_router,
    importacion_router,
    archivos_router,
    auditoria_router,
)

salud_router = APIRouter(tags=["salud"])


@salud_router.get("/salud")
def salud(session: SesionDep):
    """Confirma que la aplicación responde y que llega a la base de datos."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.exception("La base de datos no responde")
        return JSONResponse(
            status_code=503,
            content={
                "codigo": "SERVICIO_NO_DISPONIBLE",
                "mensaje": "El servicio no está disponible por ahora.",
                "detalles": None,
            },
        )
    return {"estado": "ok", "base": "ok"}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Control de herramientas y EPP", docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    registrar_handlers(app)

    api = APIRouter(prefix="/api")
    api.include_router(salud_router)
    for router in ROUTERS:
        api.include_router(router)
    app.include_router(api)
    return app


app = create_app()
