"""OF-02: versión mínima del APK; la web y la subida de colas siguen disponibles."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def version_numerica(valor: str) -> tuple[int, int, int] | None:
    partes = valor.split(".")
    if len(partes) != 3 or any(not p.isascii() or not p.isdecimal() or len(p) > 6 for p in partes):
        return None
    return tuple(int(p) for p in partes)


class VersionAppMiddleware:
    def __init__(self, app: ASGIApp, version_minima: str):
        self.app = app
        self.minima = version_numerica(version_minima)
        if self.minima is None:
            raise ValueError("APP_VERSION_MINIMA debe usar tres números, como 0.1.0.")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/api/"):
            encabezados = dict(scope.get("headers", []))
            version = encabezados.get(b"x-app-version")
            es_lote = (
                scope["method"] == "POST"
                and scope["path"].rstrip("/") == "/api/sincronizacion/lotes"
            )
            if version is not None and not es_lote:
                actual = version_numerica(version.decode("latin-1"))
                if actual is None or actual < self.minima:
                    respuesta = JSONResponse(
                        status_code=426,
                        content={
                            "codigo": "APP_DESACTUALIZADA",
                            "mensaje": "Hay una versión nueva de la app. Pídela a tu "
                            "supervisor o al área de sistemas para seguir.",
                            "detalles": {"version_minima": ".".join(map(str, self.minima))},
                        },
                    )
                    await respuesta(scope, receive, send)
                    return
        await self.app(scope, receive, send)
