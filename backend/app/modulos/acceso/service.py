"""Reglas del módulo `acceso`: entrada, bloqueo por intentos, permisos, PIN y almacén operativo."""

import math
import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.excepciones import DatosInvalidos, DemasiadosIntentos, SinPermiso
from app.core.reintento import reintentar_si_interbloqueo
from app.core.tiempo import ahora_utc
from app.modulos.acceso.exceptions import AlmacenCambio, CredencialesIncorrectas, PinIncorrecto
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import CLAVES, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.acceso.schemas import (
    AlmacenSesionOut,
    RolSesionOut,
    SesionOut,
    UsuarioSesionOut,
)
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.seguridad import HASH_RELLENO, leer_token, verificar_secreto


class AccesoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.auditoria = AuditoriaService(session)
        self.almacenes = AlmacenService(session)

    # ------------------------------------------------------------------ sesión

    def autenticar(self, nombre_usuario: str, contrasena: str) -> Usuario:
        """Valida usuario y contraseña. 5 intentos fallidos bloquean 5 minutos (US-ACC-001).

        El mensaje de error es el mismo si falla el usuario, la contraseña o está inactivo. Un
        interbloqueo de la base se reintenta (3 veces) y nunca llega como 500.
        """
        return reintentar_si_interbloqueo(
            self.session, lambda: self._autenticar(nombre_usuario, contrasena)
        )

    def _autenticar(self, nombre_usuario: str, contrasena: str) -> Usuario:
        ajustes = get_settings()
        usuario = self.usuarios.get_by_usuario(nombre_usuario)
        if usuario is None:
            verificar_secreto(contrasena, HASH_RELLENO)  # mismo tiempo que un usuario real
            raise CredencialesIncorrectas()

        # La fila se bloquea ANTES de verificar la contraseña: las ráfagas del mismo usuario se
        # atienden una por una y cada una ve el contador y el bloqueo de la anterior. Así no hay
        # más de `intentos_maximos` intentos reales por ventana ni choques de bloqueos.
        usuario = self.usuarios.bloquear(usuario.id)
        ahora = ahora_utc()
        if usuario.bloqueado_hasta is not None:
            if usuario.bloqueado_hasta > ahora:
                raise DemasiadosIntentos(_segundos_restantes(usuario.bloqueado_hasta, ahora))
            usuario.bloqueado_hasta = None  # el bloqueo ya venció

        if not verificar_secreto(contrasena, usuario.contrasena_hash):
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= ajustes.intentos_maximos:
                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = ahora + timedelta(seconds=ajustes.bloqueo_segundos)
                self.auditoria.registrar(
                    usuario_id=usuario.id,
                    accion="sesion.bloqueo",
                    entidad="usuario",
                    entidad_id=usuario.id,
                    despues={"bloqueado_hasta": usuario.bloqueado_hasta},
                )
                self.session.commit()
                raise DemasiadosIntentos(ajustes.bloqueo_segundos)
            self.session.commit()
            raise CredencialesIncorrectas()

        if not usuario.activo:
            raise CredencialesIncorrectas()

        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        self.auditoria.registrar(
            usuario_id=usuario.id, accion="sesion.entrada", entidad="usuario", entidad_id=usuario.id
        )
        self.session.commit()
        return usuario

    def usuario_de_token(self, token: str | None) -> Usuario | None:
        """El usuario activo al que pertenece el token, leído de la base en cada petición."""
        if not token:
            return None
        leido = leer_token(token)
        if leido is None:
            return None
        usuario_id, version = leido
        usuario = self.usuarios.get(usuario_id)
        if usuario is None or not usuario.activo or usuario.version_sesion != version:
            return None  # un token de una sesión ya cerrada o revocada no sirve
        return usuario

    def cerrar_sesiones(self, usuario: Usuario) -> None:
        """Cierra TODAS las sesiones del usuario (en todos sus dispositivos): sube su versión de
        sesión y los tokens emitidos antes dejan de servir. Hace commit."""
        usuario.version_sesion = Usuario.version_sesion + 1
        self.auditoria.registrar(
            usuario_id=usuario.id, accion="sesion.salida", entidad="usuario", entidad_id=usuario.id
        )
        self.session.commit()

    def construir_sesion(self, usuario: Usuario) -> SesionOut:
        almacen = self.almacenes.obtener(usuario.almacen_id) if usuario.almacen_id else None
        return SesionOut(
            usuario=UsuarioSesionOut(id=usuario.id, nombre=usuario.nombre, usuario=usuario.usuario),
            rol=RolSesionOut(id=usuario.rol.id, nombre=usuario.rol.nombre),
            almacen=AlmacenSesionOut.model_validate(almacen) if almacen else None,
            permisos=sorted(self.permisos_de(usuario)),
        )

    # ---------------------------------------------------------------- permisos

    def permisos_de(self, usuario: Usuario) -> frozenset[str]:
        """Permisos del rol del usuario, leídos de la base en cada llamada (AC-04, AC-10)."""
        if not usuario.rol.activo:
            return frozenset()
        return frozenset(self.roles.permisos(usuario.rol_id) & CLAVES)

    def tiene_permiso(self, usuario: Usuario, clave: str) -> bool:
        return clave in self.permisos_de(usuario)

    def exigir_permiso(self, usuario: Usuario, clave: str) -> None:
        if not self.tiene_permiso(usuario, clave):
            raise SinPermiso()

    def puede_operar_todos_los_almacenes(self, usuario: Usuario) -> bool:
        """AC-06: con `almacenes.todos` el usuario elige almacén; sin él, solo el suyo."""
        return self.tiene_permiso(usuario, P.ALMACENES_TODOS)

    def en_alcance(self, usuario: Usuario, *almacenes_id: uuid.UUID | None) -> bool:
        """AC-06: el usuario ve algo que pertenece a esos almacenes (origen y, si lo hay, destino
        de un traspaso en tránsito) si tiene `almacenes.todos` o si el suyo es uno de ellos."""
        if self.puede_operar_todos_los_almacenes(usuario):
            return True
        return usuario.almacen_id is not None and usuario.almacen_id in almacenes_id

    def resolver_almacen(self, usuario: Usuario, almacen_id: uuid.UUID | None = None) -> uuid.UUID:
        """El almacén sobre el que opera el usuario (RG-07, AC-06).

        Sin `almacenes.todos` sale del usuario de la sesión (y si se indica otro, se rechaza).
        Con `almacenes.todos` hay que indicarlo con `almacen_id`.
        """
        if self.puede_operar_todos_los_almacenes(usuario):
            if almacen_id is None:
                raise DatosInvalidos(
                    "Indica el almacén.",
                    [{"campo": "almacen_id", "mensaje": "Indica el almacén."}],
                )
            self.almacenes.obtener(almacen_id)
            return almacen_id
        if usuario.almacen_id is None:
            raise SinPermiso("No tienes un almacén asignado.")
        if almacen_id is not None and almacen_id != usuario.almacen_id:
            raise SinPermiso("Solo puedes operar tu almacén.")
        return usuario.almacen_id

    def exigir_mismo_almacen(self, usuario: Usuario, almacen_id_captura: uuid.UUID | None) -> None:
        """AC-13: rechaza al confirmar un vale capturado en un almacén que ya no es el del usuario.

        `almacen_id_captura` es el almacén en el que se capturó (opcional en `POST /api/vales`).
        Sin él, o si el usuario tiene `almacenes.todos` (elige almacén en cada vale), no hay nada
        que comparar. Si no coincide con el almacén actual del usuario, lanza `AlmacenCambio`
        (409 `ALMACEN_CAMBIO`) con el almacén nuevo en `detalles`; el borrador se conserva.
        Hay que llamarla con el usuario de la petición actual (su almacén sale de la base).
        """
        if almacen_id_captura is None or self.puede_operar_todos_los_almacenes(usuario):
            return
        if usuario.almacen_id == almacen_id_captura:
            return
        nuevo = self.almacenes.obtener(usuario.almacen_id) if usuario.almacen_id else None
        raise AlmacenCambio(
            detalles={
                "almacen_captura_id": str(almacen_id_captura),
                "almacen": (
                    AlmacenSesionOut.model_validate(nuevo).model_dump(mode="json")
                    if nuevo
                    else None
                ),
            }
        )

    # --------------------------------------------------------------------- PIN

    def verificar_pin(self, usuario: Usuario, pin: str) -> None:
        """Verifica el PIN de `usuario` (secreto distinto de la contraseña) con su bloqueo.

        Éxito: reinicia el contador (sin commit; lo hace quien llama). Fallo: guarda el contador
        con commit, lo que también confirma lo pendiente de la sesión, así que llámese ANTES de
        escribir lo demás. Cinco fallos bloquean cinco minutos (429). Para autorizar, quien llama
        verifica además que el usuario tenga el permiso (`autorizaciones.resolver`).

        La fila del usuario se bloquea (`FOR UPDATE`) antes de verificar: las ráfagas se atienden
        una por una y no pasan de `intentos_maximos` intentos reales por ventana. No reintenta
        por sí misma un interbloqueo (la transacción de quien llama podría perder su trabajo):
        quien la llama envuelve toda la operación con `reintentar_si_interbloqueo`.
        """
        ajustes = get_settings()
        usuario = self.usuarios.bloquear(usuario.id)
        ahora = ahora_utc()
        if usuario.pin_bloqueado_hasta is not None:
            if usuario.pin_bloqueado_hasta > ahora:
                raise DemasiadosIntentos(_segundos_restantes(usuario.pin_bloqueado_hasta, ahora))
            usuario.pin_bloqueado_hasta = None

        hash_pin = usuario.pin_hash or HASH_RELLENO
        if usuario.pin_hash is not None and verificar_secreto(pin, hash_pin):
            usuario.pin_intentos_fallidos = 0
            self.session.flush()
            return

        if usuario.pin_hash is None:
            verificar_secreto(pin, HASH_RELLENO)
        usuario.pin_intentos_fallidos += 1
        if usuario.pin_intentos_fallidos >= ajustes.intentos_maximos:
            usuario.pin_intentos_fallidos = 0
            usuario.pin_bloqueado_hasta = ahora + timedelta(seconds=ajustes.bloqueo_segundos)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="pin.bloqueo",
                entidad="usuario",
                entidad_id=usuario.id,
                despues={"pin_bloqueado_hasta": usuario.pin_bloqueado_hasta},
            )
            self.session.commit()
            raise DemasiadosIntentos(ajustes.bloqueo_segundos)
        self.session.commit()
        raise PinIncorrecto()


def _segundos_restantes(hasta, ahora) -> int:
    return max(1, math.ceil((hasta - ahora).total_seconds()))
