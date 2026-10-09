"""Genera un par VAPID una sola vez: uv run python -m app.modulos.notificaciones.generar_claves."""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02


def generar():
    vapid = Vapid02()
    vapid.generate_keys()
    publica = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    privada = vapid.private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    def encode(valor):
        return base64.urlsafe_b64encode(valor).decode().rstrip("=")

    return encode(publica), encode(privada)


if __name__ == "__main__":
    publica, privada = generar()
    print(f"VAPID_CLAVE_PUBLICA={publica}")
    print(f"VAPID_CLAVE_PRIVADA={privada}")
