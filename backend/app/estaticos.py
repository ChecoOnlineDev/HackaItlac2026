"""Entrega de la interfaz ya construida (aplicación de una sola página) y cabeceras de seguridad.

El servidor de la API también sirve los archivos de `frontend/build/client` (ADR-002):

- Un archivo que existe en la carpeta se entrega tal cual. Los de `/assets/` llevan un nombre con
  huella (hash), así que se guardan un año; el resto, una hora.
- Cualquier otra ruta que no empiece con `/api` responde `index.html` sin caché: la pantalla la
  resuelve React Router en el navegador (`/entrar`, `/v/:token`, `/vales/:id`...).
- `/api/*` que no existe sigue siendo 404 JSON del contrato, nunca `index.html`.
- Sin la carpeta (desarrollo y pruebas) no se monta nada y el servidor solo ofrece la API.
"""

import base64
import hashlib
import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CACHE_CON_HUELLA = "public, max-age=31536000, immutable"
CACHE_ESTATICO = "public, max-age=3600"
CACHE_INDEX = "no-cache"

# Los <script> en línea que genera React Router en el index.html (modo de una sola página).
_SCRIPT_EN_LINEA = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL)


def _hashes_de_scripts(index: Path) -> list[str]:
    """Huellas `'sha256-...'` de los scripts en línea, para permitirlos sin `unsafe-inline`."""
    try:
        html = index.read_text(encoding="utf-8")
    except OSError:
        return []
    huellas = set()
    for contenido in _SCRIPT_EN_LINEA.findall(html):
        digest = hashlib.sha256(contenido.encode("utf-8")).digest()
        huellas.add(f"'sha256-{base64.b64encode(digest).decode()}'")
    return sorted(huellas)


def politica_csp(hashes_scripts: list[str]) -> str:
    """Content-Security-Policy de la interfaz: solo el propio origen, sin `unsafe-eval`."""
    script = " ".join(["'self'", *hashes_scripts])
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src {script}",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "media-src 'self' blob:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "worker-src 'self' blob:",
            "manifest-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def agregar_cabeceras_seguridad(
    app: FastAPI, *, csp: str, hsts: bool = False, rutas_sin_csp: tuple[str, ...] = ("/api",)
) -> None:
    """Agrega las cabeceras de seguridad a todas las respuestas.

    La CSP no se pone a `/api` (respuestas JSON y la documentación interactiva, que carga recursos
    de otro origen).
    """

    @app.middleware("http")
    async def _cabeceras(request: Request, call_next):
        respuesta = await call_next(request)
        h = respuesta.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if hsts:
            h.setdefault("Strict-Transport-Security", "max-age=31536000")
        ruta = request.url.path
        if not any(ruta == p or ruta.startswith(p + "/") for p in rutas_sin_csp):
            h.setdefault("Content-Security-Policy", csp)
        return respuesta


def montar_interfaz(app: FastAPI, directorio: Path) -> bool:
    """Monta los archivos de la interfaz y el respaldo de SPA. Devuelve si había interfaz."""
    raiz = directorio.resolve()
    index = raiz / "index.html"
    if not index.is_file():
        return False

    def interfaz(ruta: str):
        if ruta == "api" or ruta.startswith("api/"):
            raise StarletteHTTPException(404)
        if ruta:
            candidato = (raiz / ruta).resolve()
            if candidato.is_file() and candidato.is_relative_to(raiz) and candidato != index:
                con_huella = ruta.startswith("assets/")
                return FileResponse(
                    candidato,
                    headers={"Cache-Control": CACHE_CON_HUELLA if con_huella else CACHE_ESTATICO},
                )
            if ruta.startswith("assets/"):
                # Un recurso con huella que no existe nunca debe contestar con una página.
                raise StarletteHTTPException(404)
        return FileResponse(index, media_type="text/html", headers={"Cache-Control": CACHE_INDEX})

    app.add_api_route("/{ruta:path}", interfaz, methods=["GET", "HEAD"], include_in_schema=False)
    return True


def configurar_interfaz(app: FastAPI, directorio: Path, *, cookie_segura: bool) -> bool:
    """Cabeceras de seguridad y, si existe la carpeta, la interfaz. Va al final de `create_app`."""
    hay_interfaz = (directorio / "index.html").is_file()
    hashes = _hashes_de_scripts(directorio / "index.html") if hay_interfaz else []
    agregar_cabeceras_seguridad(app, csp=politica_csp(hashes), hsts=cookie_segura)
    return montar_interfaz(app, directorio)
