import base64
import ipaddress
import uuid
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, EllipticCurvePublicKey
from pydantic import BaseModel, Field, field_validator

from app.modulos.autorizaciones.schemas import FechaUtc


class ClavesPush(BaseModel):
    p256dh: str = Field(max_length=120)
    auth: str = Field(max_length=50)

    @field_validator("p256dh", "auth")
    @classmethod
    def validar_clave(cls, valor, info):
        try:
            decoded = base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4))
            if info.field_name == "auth":
                if len(decoded) != 16:
                    raise ValueError()
            else:
                EllipticCurvePublicKey.from_encoded_point(SECP256R1(), decoded)
        except (ValueError, TypeError) as exc:
            raise ValueError("La clave de notificaciones no es válida.") from exc
        return valor


class SuscripcionIn(BaseModel):
    endpoint: str = Field(max_length=1000)
    keys: ClavesPush

    @field_validator("endpoint")
    @classmethod
    def validar_endpoint(cls, valor):
        u = urlsplit(valor)
        host = (u.hostname or "").lower()
        allowed = host in {
            "fcm.googleapis.com",
            "updates.push.services.mozilla.com",
            "web.push.apple.com",
        } or host.endswith(".notify.windows.com")
        try:
            ipaddress.ip_address(host)
            allowed = False
        except ValueError:
            pass
        if (
            u.scheme != "https"
            or not allowed
            or u.username
            or u.password
            or u.fragment
            or u.port not in (None, 443)
            or not u.path
        ):
            raise ValueError(
                "Usa una dirección HTTPS del servicio de notificaciones del navegador."
            )
        return valor


class SuscripcionOut(BaseModel):
    id: uuid.UUID
    creada_en: FechaUtc


class ClavePublicaOut(BaseModel):
    clave_publica: str


class PruebaOut(BaseModel):
    enviadas: int
    fallidas: int
