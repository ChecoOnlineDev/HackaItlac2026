"""Guarda y lee archivos (firmas, fotos) del volumen y es dueño de la tabla `adjunto`.

Otros módulos (movimientos para la firma, trabajadores para la foto) llaman a `guardar`; no
escriben `adjunto` ni tocan el volumen. `guardar` solo hace `flush`: el commit es de quien llama.
Si esa transacción falla después, el archivo queda huérfano en el volumen; es inofensivo.
"""

import base64
import binascii
import uuid

from sqlalchemy.orm import Session

from app.config import get_settings
from app.integraciones import archivos as volumen
from app.modulos.archivos.exceptions import AdjuntoNoEncontrado, ArchivoInvalido
from app.modulos.archivos.models import Adjunto, TipoAdjunto
from app.modulos.archivos.repository import AdjuntoRepository

# Tipos de contenido que acepta cada clase de adjunto.
MIME_PERMITIDOS: dict[TipoAdjunto, frozenset[str]] = {
    TipoAdjunto.FIRMA: frozenset({"image/png", "image/jpeg", "image/webp"}),
    TipoAdjunto.FOTO_DANO: frozenset({"image/png", "image/jpeg", "image/webp"}),
    TipoAdjunto.FOTO_TRABAJADOR: frozenset({"image/png", "image/jpeg", "image/webp"}),
}

SUBCARPETA: dict[TipoAdjunto, str] = {
    TipoAdjunto.FIRMA: "firmas",
    TipoAdjunto.FOTO_DANO: "fotos_dano",
    TipoAdjunto.FOTO_TRABAJADOR: "fotos_trabajadores",
}


def decodificar_data_url(data_url: str) -> bytes:
    """Bytes de una imagen `data:image/png;base64,...` (como llega la firma de la interfaz)."""
    if "," not in data_url:
        raise ArchivoInvalido("La imagen no tiene un formato válido.")
    try:
        return base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ArchivoInvalido("La imagen no tiene un formato válido.") from exc


class ArchivoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.adjuntos = AdjuntoRepository(session)

    def guardar(
        self,
        *,
        tipo: TipoAdjunto,
        contenido: bytes,
        subido_por: uuid.UUID,
        vale_id: uuid.UUID | None = None,
        movimiento_id: uuid.UUID | None = None,
    ) -> Adjunto:
        """Valida (contenido, tamaño), guarda en el volumen y registra el adjunto (sin commit)."""
        if not contenido:
            raise ArchivoInvalido("El archivo está vacío.")
        maximo = get_settings().archivo_tamano_maximo
        if len(contenido) > maximo:
            raise ArchivoInvalido(
                f"El archivo pesa más de {maximo // (1024 * 1024)} MB.",
                {"tamano_maximo": maximo},
            )
        mime = volumen.detectar_mime(contenido)
        if mime is None or mime not in MIME_PERMITIDOS[tipo]:
            raise ArchivoInvalido("Solo se aceptan imágenes PNG, JPEG o WEBP.")

        ruta = volumen.guardar(SUBCARPETA[tipo], volumen.extension_de(mime), contenido)
        return self.adjuntos.add(
            Adjunto(
                tipo=tipo,
                ruta=ruta,
                mime=mime,
                tamano=len(contenido),
                sha256=volumen.sha256_de(contenido),
                vale_id=vale_id,
                movimiento_id=movimiento_id,
                subido_por=subido_por,
            )
        )

    def obtener(self, adjunto_id: uuid.UUID) -> Adjunto:
        adjunto = self.adjuntos.get(adjunto_id)
        if adjunto is None:
            raise AdjuntoNoEncontrado()
        return adjunto

    def leer(self, adjunto_id: uuid.UUID) -> tuple[Adjunto, bytes]:
        """El adjunto y su contenido. El permiso lo verifica el endpoint que lo entrega."""
        adjunto = self.obtener(adjunto_id)
        try:
            return adjunto, volumen.leer(adjunto.ruta)
        except FileNotFoundError as exc:
            raise AdjuntoNoEncontrado() from exc
