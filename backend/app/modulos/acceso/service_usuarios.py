"""Usuarios y asignación de personal a almacenes (FEAT-006; AC-09, AC-12 y AC-13).

Quien asigna personal (`almacenes.asignar_personal`) solo cambia el almacén de un usuario; las
altas, roles y contraseñas son de `acceso.administrar`. Nunca se guardan ni se devuelven
contraseñas, PIN ni hashes; la auditoría tampoco los lleva.
"""

import uuid
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_UNICO, violacion
from app.core.excepciones import DatosInvalidos, NoEncontrado, SinPermiso
from app.modulos.acceso.exceptions import UltimoAdministrador, UsuarioExiste, UsuarioNoEncontrado
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import FiltrosUsuarios, RolRepository, UsuarioRepository
from app.modulos.acceso.schemas import (
    AlmacenSesionOut,
    PersonalOut,
    RolSesionOut,
    UsuarioCreate,
    UsuarioOut,
    UsuarioUpdate,
)
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.models import Almacen, EstadoAlmacen
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.seguridad import hashear_secreto


def _invalido(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def _almacen_auditoria(almacen: Almacen | None) -> dict[str, Any] | None:
    if almacen is None:
        return None
    return {"id": str(almacen.id), "codigo": almacen.clave, "nombre": almacen.nombre}


class UsuarioAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.almacenes = AlmacenService(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------------ lectura

    def obtener(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self.usuarios.get(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()
        return usuario

    def listar_personal(
        self,
        actor: Usuario,
        *,
        almacen_id: uuid.UUID | None,
        sin_almacen: bool,
        q: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PersonalOut], int]:
        """Usuarios que operan un almacén (sin `almacenes.todos`), con filtros (AC-12).

        AC-06: sin `almacenes.todos`, quien asigna ve solo al personal de su almacén y a quienes
        no tienen almacén (para traerlos); nunca al de otro almacén.
        """
        if almacen_id is not None and sin_almacen:
            raise _invalido("sin_almacen", "Elige un almacén o «sin almacén», no los dos.")
        propio = None
        if not self._ve_todos(actor):
            propio = actor.almacen_id
            if almacen_id is not None and almacen_id != propio:
                return [], 0
        filas, total = self.usuarios.listar(
            FiltrosUsuarios(
                q=q,
                almacen_id=almacen_id,
                sin_almacen=sin_almacen,
                solo_operativos=True,
                almacen_o_libres_id=propio,
                solo_libres=not self._ve_todos(actor) and propio is None,
            ),
            limit=limit,
            offset=offset,
        )
        return [self._personal(u, a) for u, a in filas], total

    def listar_usuarios(
        self,
        filtros: FiltrosUsuarios,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[UsuarioOut], int]:
        filas, total = self.usuarios.listar(filtros, limit=limit, offset=offset)
        return [self._usuario(u, a) for u, a in filas], total

    def listar_roles(self) -> list[Rol]:
        return self.roles.listar()

    def ver(self, usuario_id: uuid.UUID) -> UsuarioOut:
        usuario = self.obtener(usuario_id)
        return self._usuario(usuario, self._almacen_de(usuario))

    # --------------------------------------------------- asignación de personal

    def mover_almacen(
        self, actor: Usuario, usuario_id: uuid.UUID, almacen_id: uuid.UUID | None
    ) -> PersonalOut:
        """AC-12 y AC-13: asigna, mueve o deja sin almacén a quien opera un almacén.

        Aplica en la siguiente petición del usuario (su almacén se lee de la base en cada una).
        Los vales y movimientos ya hechos no se tocan (RG-03).
        """
        usuario = self.obtener(usuario_id)
        if not self._ve_todos(actor):
            # AC-06: un supervisor solo trae a su almacén a quien no tiene uno, o libera a quien
            # está en el suyo. Mover entre almacenes distintos es del Administrador.
            propio = actor.almacen_id
            if propio is None:
                raise SinPermiso("No tienes un almacén asignado.")
            if usuario.almacen_id not in (None, propio):
                raise NoEncontrado("No se encontró al usuario.")
            if almacen_id is not None and almacen_id != propio:
                raise SinPermiso("Solo puedes asignar personal a tu almacén.")
        if not usuario.activo:
            raise _invalido("usuario_id", "Un usuario inactivo no se puede mover de almacén.")
        permisos_rol = self.roles.permisos(usuario.rol_id)
        if P.ALMACENES_TODOS in permisos_rol or P.INVENTARIO_VER not in permisos_rol:
            raise _invalido(
                "usuario_id",
                "Ese usuario no trabaja en un almacén; no se le asigna uno (AC-12).",
            )
        anterior = self._almacen_de(usuario)
        nuevo = self._almacen_destino(almacen_id) if almacen_id is not None else None
        if (anterior.id if anterior else None) != (nuevo.id if nuevo else None):
            usuario.almacen_id = nuevo.id if nuevo else None
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="usuario.almacen",
                entidad="usuario",
                entidad_id=usuario.id,
                antes={"almacen": _almacen_auditoria(anterior)},
                despues={"almacen": _almacen_auditoria(nuevo)},
            )
            self.session.commit()
        return self._personal(usuario, nuevo)

    # ------------------------------------------------------- usuarios (admin)

    def crear(self, actor: Usuario, datos: UsuarioCreate) -> UsuarioOut:
        if self.usuarios.get_by_usuario(datos.usuario) is not None:
            raise UsuarioExiste()
        rol = self._rol_asignable(datos.rol_id)
        almacen = self._almacen_para_rol(rol.id, datos.almacen_id, obligatorio=True)
        if datos.pin is not None:
            self._validar_pin(rol.id, datos.pin, datos.contrasena)
        usuario = Usuario(
            nombre=datos.nombre.strip(),
            usuario=datos.usuario,
            contrasena_hash=hashear_secreto(datos.contrasena),
            pin_hash=hashear_secreto(datos.pin) if datos.pin else None,
            rol_id=rol.id,
            almacen_id=almacen.id if almacen else None,
            activo=True,
        )
        try:
            self.usuarios.add(usuario)
        except DBAPIError as exc:
            if violacion(exc).errno == ERRNO_UNICO:
                self.session.rollback()
                raise UsuarioExiste() from exc
            raise
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="usuario.crear",
            entidad="usuario",
            entidad_id=usuario.id,
            despues=self._instantanea(usuario, rol, almacen),
        )
        self.session.commit()
        return self._usuario(usuario, almacen)

    def editar(self, actor: Usuario, usuario_id: uuid.UUID, datos: UsuarioUpdate) -> UsuarioOut:
        usuario = self.obtener(usuario_id)
        campos = datos.model_fields_set
        for campo in ("nombre", "rol_id", "activo"):
            if campo in campos and getattr(datos, campo) is None:
                raise _invalido(campo, "Este dato no puede ir vacío.")

        rol_anterior = usuario.rol
        almacen_anterior = self._almacen_de(usuario)
        antes = self._instantanea(usuario, rol_anterior, almacen_anterior)

        rol = rol_anterior
        cambia_rol = "rol_id" in campos and datos.rol_id != usuario.rol_id
        if cambia_rol:
            rol = self._rol_asignable(datos.rol_id)  # type: ignore[arg-type]

        activo = usuario.activo if datos.activo is None else datos.activo
        if cambia_rol or activo != usuario.activo:
            self._proteger_ultimo_administrador(usuario, rol, activo)

        almacen = almacen_anterior
        if "almacen_id" in campos or cambia_rol:
            if "almacen_id" in campos:
                solicitado = datos.almacen_id
            else:  # solo cambió el rol: se conserva el almacén si el rol nuevo lo admite
                solicitado = almacen_anterior.id if almacen_anterior else None
                if not self._opera_almacen(rol.id):
                    solicitado = None
            almacen = self._almacen_para_rol(
                rol.id,
                solicitado,
                obligatorio=True,
                vigente=almacen_anterior.id if almacen_anterior else None,
            )

        if "nombre" in campos:
            usuario.nombre = datos.nombre.strip()  # type: ignore[union-attr]
        if cambia_rol:
            usuario.rol = rol
        usuario.almacen_id = almacen.id if almacen else None
        if activo != usuario.activo:
            usuario.version_sesion = Usuario.version_sesion + 1  # inactivar o reactivar: sin sesión
        usuario.activo = activo

        despues = self._instantanea(usuario, rol, almacen)
        if despues != antes:
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="usuario.editar",
                entidad="usuario",
                entidad_id=usuario.id,
                antes=antes,
                despues=despues,
            )
            self.session.commit()
        return self._usuario(usuario, almacen)

    def restablecer_contrasena(
        self, actor: Usuario, usuario_id: uuid.UUID, contrasena: str, pin: str | None
    ) -> UsuarioOut:
        """Cambia la contraseña (y el PIN, si se manda) y reinicia los bloqueos."""
        usuario = self.obtener(usuario_id)
        if pin is not None:
            self._validar_pin(usuario.rol_id, pin, contrasena)
        usuario.contrasena_hash = hashear_secreto(contrasena)
        restablecido = ["contrasena"]
        if pin is not None:
            usuario.pin_hash = hashear_secreto(pin)
            restablecido.append("pin")
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.pin_intentos_fallidos = 0
        usuario.pin_bloqueado_hasta = None
        usuario.version_sesion = Usuario.version_sesion + 1  # las sesiones abiertas dejan de servir
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="usuario.restablecer",
            entidad="usuario",
            entidad_id=usuario.id,
            despues={"restablecido": restablecido, "bloqueos_reiniciados": True},
        )
        self.session.commit()
        return self._usuario(usuario, self._almacen_de(usuario))

    # --------------------------------------------------------------- reglas

    def _proteger_ultimo_administrador(self, usuario: Usuario, rol: Rol, activo: bool) -> None:
        """AC-09: no se inactiva ni se le quita `acceso.administrar` al último administrador."""
        administradores = self.usuarios.administradores_activos()
        if usuario.id not in administradores:
            return
        sigue = activo and rol.activo and P.ACCESO_ADMINISTRAR in self.roles.permisos(rol.id)
        if not sigue and not (administradores - {usuario.id}):
            raise UltimoAdministrador()

    def _ve_todos(self, usuario: Usuario) -> bool:
        return P.ALMACENES_TODOS in self.roles.permisos(usuario.rol_id)

    def _opera_almacen(self, rol_id: uuid.UUID) -> bool:
        """Opera un almacén quien no tiene `almacenes.todos` (RG-07)."""
        return P.ALMACENES_TODOS not in self.roles.permisos(rol_id)

    def _rol_asignable(self, rol_id: uuid.UUID) -> Rol:
        rol = self.roles.get(rol_id)
        if rol is None:
            raise _invalido("rol_id", "No existe ese rol.")
        if not rol.activo:
            raise _invalido("rol_id", "Ese rol está inactivo.")
        return rol

    def _almacen_destino(self, almacen_id: uuid.UUID) -> Almacen:
        try:
            almacen = self.almacenes.obtener(almacen_id)
        except AlmacenNoEncontrado as exc:
            raise _invalido("almacen_id", "No existe ese almacén.") from exc
        if almacen.estado != EstadoAlmacen.ACTIVO:
            raise _invalido("almacen_id", "Ese almacén está cerrado.")
        return almacen

    def _almacen_para_rol(
        self,
        rol_id: uuid.UUID,
        almacen_id: uuid.UUID | None,
        *,
        obligatorio: bool,
        vigente: uuid.UUID | None = None,
    ) -> Almacen | None:
        """El almacén que le toca a un usuario con ese rol: obligatorio si opera un almacén y
        vacío si tiene `almacenes.todos` (RG-07). Si es el que ya tenía, no se vuelve a exigir
        activo (un almacén cerrado no impide editar el nombre, por ejemplo)."""
        if not self._opera_almacen(rol_id):
            if almacen_id is not None:
                raise _invalido(
                    "almacen_id", "Este rol opera todos los almacenes; no lleva almacén asignado."
                )
            return None
        if almacen_id is None:
            if obligatorio:
                raise _invalido("almacen_id", "Elige el almacén en el que va a trabajar.")
            return None
        if almacen_id == vigente:
            return self.almacenes.obtener(almacen_id)
        return self._almacen_destino(almacen_id)

    def _validar_pin(self, rol_id: uuid.UUID, pin: str, contrasena: str) -> None:
        if P.AUTORIZACIONES_RESOLVER not in self.roles.permisos(rol_id):
            raise _invalido("pin", "Solo quien puede autorizar lleva PIN.")
        if pin == contrasena:
            raise _invalido("pin", "El PIN debe ser distinto de la contraseña.")

    # ------------------------------------------------------------ salidas

    def _almacen_de(self, usuario: Usuario) -> Almacen | None:
        return self.almacenes.obtener(usuario.almacen_id) if usuario.almacen_id else None

    @staticmethod
    def _instantanea(usuario: Usuario, rol: Rol, almacen: Almacen | None) -> dict[str, Any]:
        """Lo que queda en la auditoría: sin contraseñas, PIN ni hashes."""
        return {
            "nombre": usuario.nombre,
            "usuario": usuario.usuario,
            "rol": {"id": str(rol.id), "nombre": rol.nombre},
            "almacen": _almacen_auditoria(almacen),
            "activo": usuario.activo,
        }

    @staticmethod
    def _personal(usuario: Usuario, almacen: Almacen | None) -> PersonalOut:
        return PersonalOut(
            id=usuario.id,
            nombre=usuario.nombre,
            usuario=usuario.usuario,
            rol=RolSesionOut(id=usuario.rol.id, nombre=usuario.rol.nombre),
            almacen=AlmacenSesionOut.model_validate(almacen) if almacen else None,
            activo=usuario.activo,
        )

    @classmethod
    def _usuario(cls, usuario: Usuario, almacen: Almacen | None) -> UsuarioOut:
        return UsuarioOut(
            **cls._personal(usuario, almacen).model_dump(),
            tiene_pin=usuario.pin_hash is not None,
            creado_en=usuario.creado_en,
        )
