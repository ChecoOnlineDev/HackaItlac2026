"""Sesiones por dispositivo: token de acceso corto + token de renovación (AC-14 a AC-24).

Esquema, en una línea: el inicio de sesión abre una *familia* (un dispositivo) con un token de
renovación de hasta `REFRESH_DIAS` días; cada vez que se usa se **rota** (el viejo queda
revocado y se entrega uno nuevo, con otros `REFRESH_DIAS` días, sin pasar de `REFRESH_TOPE_DIAS`
desde el inicio). Usar un token ya rotado, fuera de la tolerancia, revoca toda la familia: o se
copió o se está usando por dos lados.

El token de renovación es una cadena aleatoria; aquí solo se guarda su huella SHA-256. El rol,
los permisos y el almacén NO viajan en ningún token: se leen de la base en cada petición.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.reintento import reintentar_si_interbloqueo
from app.core.tiempo import ahora_utc
from app.modulos.acceso.exceptions import SesionVencida
from app.modulos.acceso.models import SesionDispositivo, Usuario
from app.modulos.acceso.repository import SesionDispositivoRepository, UsuarioRepository
from app.modulos.acceso.schemas import DispositivoOut
from app.modulos.auditoria.service import AuditoriaService
from app.seguridad import (
    crear_token_acceso,
    huella_refresh,
    nuevo_token_refresh,
)

# Motivos de revocación (`sesion_dispositivo.motivo_revocacion`).
ROTADA = "rotada"  # se renovó: la fila siguiente la reemplaza
SALIDA = "salida"  # el usuario cerró la sesión de este dispositivo
SALIDA_TODAS = "salida_todas"  # el usuario cerró todas sus sesiones
SALIDA_OTRAS = "salida_otras"  # el usuario cerró las demás
VERSION = "version"  # contraseña, PIN, inactivación o reactivación del usuario
REUTILIZADA = "reutilizacion"  # un token ya rotado se usó fuera de la tolerancia
NUEVA_ENTRADA = "nueva_entrada"  # el mismo navegador volvió a entrar
VENCIDA = "vencida"  # la ventana de uso o el tope absoluto ya pasaron

LARGO_MAXIMO_AGENTE = 120
# Cuánto tiempo se conservan las familias ya vencidas antes de borrarlas.
RETENCION_VENCIDAS = timedelta(days=1)


@dataclass(frozen=True)
class SesionEmitida:
    """Lo que el router deja en las cookies. `token_refresh` en None significa que la cookie de
    renovación no se toca (renovación dentro de la tolerancia: otra petición ya la rotó)."""

    usuario: Usuario
    token_acceso: str
    token_refresh: str | None
    refresh_segundos: int


def resumir_agente(agente: str | None) -> str | None:
    """«Chrome en Windows» a partir del User-Agent. Sin versiones ni más detalle: sirve para que
    la persona reconozca su dispositivo y no es un dato de huella digital."""
    if not agente:
        return None
    texto = agente.strip()
    if not texto:
        return None
    # El orden importa: Edge, Opera y Samsung dicen también «Chrome»; Chrome dice «Safari».
    navegadores = (
        (r"Edg(?:e|A|iOS)?/", "Edge"),
        (r"OPR/|Opera", "Opera"),
        (r"SamsungBrowser/", "Samsung Internet"),
        (r"Firefox/|FxiOS/", "Firefox"),
        (r"Chrome/|CriOS/", "Chrome"),
        (r"Safari/", "Safari"),
    )
    sistemas = (
        (r"Windows", "Windows"),
        (r"Android", "Android"),
        (r"iPhone|iPad|iPod", "iOS"),
        (r"Mac OS X|Macintosh", "macOS"),
        (r"CrOS", "ChromeOS"),
        (r"Linux|X11", "Linux"),
    )
    navegador = next((n for patron, n in navegadores if re.search(patron, texto)), None)
    sistema = next((n for patron, n in sistemas if re.search(patron, texto)), None)
    if navegador and sistema:
        resumen = f"{navegador} en {sistema}"
    elif navegador or sistema:
        resumen = navegador or sistema or ""
    else:
        resumen = "Dispositivo desconocido"
    return resumen[:LARGO_MAXIMO_AGENTE]


class SesionesService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.filas = SesionDispositivoRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.auditoria = AuditoriaService(session)

    # ----------------------------------------------------------------- entrar

    def abrir(
        self, usuario: Usuario, agente: str | None, refresh_previo: str | None = None
    ) -> SesionEmitida:
        """AC-14: abre la sesión de un dispositivo después de validar la contraseña. Si el mismo
        navegador traía otra sesión, esa se cierra. Hace commit."""
        ajustes = get_settings()
        ahora = ahora_utc()
        if refresh_previo:
            previa = self.filas.por_huella(huella_refresh(refresh_previo))
            if previa is not None:
                self.filas.revocar_familia(previa.familia_id, NUEVA_ENTRADA, ahora)
        self.filas.purgar(ahora - RETENCION_VENCIDAS)

        familia = uuid.uuid4()
        token = nuevo_token_refresh()
        tope = ahora + timedelta(days=ajustes.refresh_tope_dias)
        fila = self.filas.add(
            SesionDispositivo(
                usuario_id=usuario.id,
                familia_id=familia,
                refresh_hash=huella_refresh(token),
                version_sesion=usuario.version_sesion,
                creado_en=ahora,
                inicio=ahora,
                ultimo_uso=ahora,
                expira_en=min(ahora + timedelta(days=ajustes.refresh_dias), tope),
                vence_absoluto=tope,
                agente=resumir_agente(agente),
            )
        )
        self.session.commit()
        return self._emitir(usuario, fila, token, ahora)

    # --------------------------------------------------------------- renovar

    def renovar(self, token_refresh: str | None, agente: str | None) -> SesionEmitida:
        """AC-15 a AC-18: cambia un token de renovación válido por un token de acceso nuevo y un
        token de renovación nuevo. Cualquier otro caso es `SesionVencida`. Hace commit."""
        if not token_refresh:
            raise SesionVencida()
        return reintentar_si_interbloqueo(
            self.session, lambda: self._renovar(token_refresh, agente)
        )

    def _renovar(self, token_refresh: str, agente: str | None) -> SesionEmitida:
        ajustes = get_settings()
        ahora = ahora_utc()
        fila = self.filas.por_huella(huella_refresh(token_refresh), bloquear=True)
        if fila is None:
            raise SesionVencida()

        if fila.revocada_en is not None:
            if fila.motivo_revocacion == ROTADA:
                tolerancia = timedelta(seconds=ajustes.refresh_tolerancia_segundos)
                if ahora - fila.revocada_en <= tolerancia:
                    return self._dentro_de_tolerancia(fila, ahora)
                self._revocar_por_reutilizacion(fila, ahora)
            raise SesionVencida()

        if fila.expira_en <= ahora or fila.vence_absoluto <= ahora:
            self.filas.revocar_familia(fila.familia_id, VENCIDA, ahora)
            self.session.commit()
            raise SesionVencida()

        usuario = self.usuarios.get(fila.usuario_id)
        if usuario is None or not usuario.activo or usuario.version_sesion != fila.version_sesion:
            self.filas.revocar_familia(fila.familia_id, VERSION, ahora)
            self.session.commit()
            raise SesionVencida()

        token = nuevo_token_refresh()
        nueva = self.filas.add(
            SesionDispositivo(
                usuario_id=usuario.id,
                familia_id=fila.familia_id,
                refresh_hash=huella_refresh(token),
                version_sesion=usuario.version_sesion,
                creado_en=ahora,
                inicio=fila.inicio,
                ultimo_uso=ahora,
                expira_en=min(ahora + timedelta(days=ajustes.refresh_dias), fila.vence_absoluto),
                vence_absoluto=fila.vence_absoluto,
                agente=resumir_agente(agente) or fila.agente,
            )
        )
        fila.revocada_en = ahora
        fila.motivo_revocacion = ROTADA
        fila.reemplazada_por = nueva.id
        self.session.commit()
        return self._emitir(usuario, nueva, token, ahora)

    def _dentro_de_tolerancia(self, rotada: SesionDispositivo, ahora: datetime) -> SesionEmitida:
        """AC-16: el token ya se había rotado hace unos segundos (dos pestañas, un reintento).
        No se rota otra vez ni se toca la cookie de renovación, que ya trae la nueva; solo se da
        un token de acceso fresco a la misma sesión, si sigue abierta."""
        vigente = self.filas.vigente_de_familia(rotada.familia_id)
        usuario = self.usuarios.get(rotada.usuario_id)
        if (
            vigente is None
            or usuario is None
            or not usuario.activo
            or usuario.version_sesion != vigente.version_sesion
            or vigente.expira_en <= ahora
            or vigente.vence_absoluto <= ahora
        ):
            raise SesionVencida()
        acceso = crear_token_acceso(usuario.id, usuario.version_sesion, vigente.familia_id)
        return SesionEmitida(usuario, acceso, None, 0)

    def _revocar_por_reutilizacion(self, fila: SesionDispositivo, ahora: datetime) -> None:
        """AC-17: un token ya rotado, fuera de la tolerancia, revoca la sesión del dispositivo."""
        revocadas = self.filas.revocar_familia(fila.familia_id, REUTILIZADA, ahora)
        if revocadas:
            self.auditoria.registrar(
                usuario_id=fila.usuario_id,
                accion="sesion.reutilizacion",
                entidad="usuario",
                entidad_id=fila.usuario_id,
                despues={"familia": fila.familia_id},
            )
        self.session.commit()

    def _emitir(
        self, usuario: Usuario, fila: SesionDispositivo, token_refresh: str, ahora: datetime
    ) -> SesionEmitida:
        acceso = crear_token_acceso(usuario.id, usuario.version_sesion, fila.familia_id)
        segundos = int((fila.expira_en - ahora).total_seconds())
        return SesionEmitida(usuario, acceso, token_refresh, segundos)

    # ------------------------------------------------------ revisar el acceso

    def familia_abierta(self, familia_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        """AC-19: se consulta en cada petición; cerrar un dispositivo corta su token de acceso
        de inmediato, sin esperar a que venza."""
        return self.filas.familia_abierta(familia_id, usuario_id)

    # ------------------------------------------------------------------ salir

    def cerrar_dispositivo(self, usuario: Usuario, familia_id: uuid.UUID) -> None:
        """AC-19: cierra solo la sesión de este dispositivo. Hace commit."""
        self.filas.revocar_familia(familia_id, SALIDA, ahora_utc())
        self.auditoria.registrar(
            usuario_id=usuario.id, accion="sesion.salida", entidad="usuario", entidad_id=usuario.id
        )
        self.session.commit()

    def cerrar_todas(self, usuario: Usuario) -> None:
        """AC-20: cierra todas las sesiones del usuario. Sube `version_sesion`, lo que invalida
        también los tokens de acceso ya emitidos. Hace commit."""
        usuario.version_sesion = Usuario.version_sesion + 1
        self.filas.revocar_de_usuario(usuario.id, SALIDA_TODAS, ahora_utc())
        self.auditoria.registrar(
            usuario_id=usuario.id,
            accion="sesion.salida_todas",
            entidad="usuario",
            entidad_id=usuario.id,
        )
        self.session.commit()

    def cerrar_otras(self, usuario: Usuario, familia_actual: uuid.UUID) -> int:
        """AC-20: cierra las sesiones de los demás dispositivos y deja la de este. No cambia la
        versión de sesión. Devuelve cuántos dispositivos cerró. Hace commit."""
        ahora = ahora_utc()
        cerradas = len(
            [
                d
                for d in self.filas.abiertas_de_usuario(usuario.id, ahora)
                if d.familia_id != familia_actual
            ]
        )
        self.filas.revocar_de_usuario(
            usuario.id, SALIDA_OTRAS, ahora, excepto_familia=familia_actual
        )
        if cerradas:
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="sesion.salida_otras",
                entidad="usuario",
                entidad_id=usuario.id,
                despues={"cerradas": cerradas},
            )
        self.session.commit()
        return cerradas

    # ------------------------------------------------------------- consultar

    def dispositivos(self, usuario: Usuario, familia_actual: uuid.UUID) -> list[DispositivoOut]:
        """AC-21: las sesiones abiertas del usuario, una por dispositivo. Sin huellas ni IP."""
        return [
            DispositivoOut(
                id=fila.familia_id,
                inicio=fila.inicio,
                ultimo_uso=fila.ultimo_uso,
                vence_en=min(fila.expira_en, fila.vence_absoluto),
                agente=fila.agente,
                actual=fila.familia_id == familia_actual,
            )
            for fila in self.filas.abiertas_de_usuario(usuario.id, ahora_utc())
        ]
