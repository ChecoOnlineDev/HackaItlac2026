"""Adaptador del volumen de archivos (firmas y fotos). Solo lo usa el módulo `archivos`.

Guarda con nombre generado por el servidor, fuera de cualquier carpeta pública, y nunca sale de
la raíz configurada (`ARCHIVOS_DIR`).
"""

import hashlib
import uuid
from pathlib import Path

from app.config import get_settings

# Firmas de contenido ("magic bytes") de los tipos permitidos.
TIPOS_POR_CONTENIDO: tuple[tuple[str, str], ...] = (
    ("image/png", ".png"),
    ("image/jpeg", ".jpg"),
    ("image/webp", ".webp"),
)


def detectar_mime(contenido: bytes) -> str | None:
    """Tipo MIME según el contenido real del archivo (no según el nombre)."""
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def extension_de(mime: str) -> str:
    return dict(TIPOS_POR_CONTENIDO)[mime]


def sha256_de(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def raiz() -> Path:
    ruta = get_settings().archivos_dir
    if not ruta.is_absolute():
        ruta = (Path(__file__).resolve().parents[2] / ruta).resolve()
    return ruta


def _resolver(ruta_relativa: str) -> Path:
    destino = (raiz() / ruta_relativa).resolve()
    if raiz() not in destino.parents:
        raise ValueError("Ruta fuera del volumen de archivos")
    return destino


def guardar(subcarpeta: str, extension: str, contenido: bytes) -> str:
    """Escribe el archivo con nombre generado y devuelve su ruta relativa (con `/`)."""
    nombre = f"{uuid.uuid4().hex}{extension}"
    relativa = f"{subcarpeta}/{nombre}"
    destino = _resolver(relativa)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa


def leer(ruta_relativa: str) -> bytes:
    return _resolver(ruta_relativa).read_bytes()


def borrar(ruta_relativa: str) -> None:
    _resolver(ruta_relativa).unlink(missing_ok=True)
