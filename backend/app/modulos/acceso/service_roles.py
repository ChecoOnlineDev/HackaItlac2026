"""Roles y permisos editables (FEAT-006; AC-08 a AC-11).

Los permisos son un catálogo fijo del sistema (AC-01): aquí solo se decide qué rol tiene cuáles.
Cada cambio queda en el registro de cambios con el valor anterior y el nuevo (AC-10); aplica en la
siguiente petición porque el rol y sus permisos se leen de la base en cada una.
"""

import uuid
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_UNICO, violacion
from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.dependencias_permisos import REQUIERE, faltantes
from app.modulos.acceso.exceptions import (
    AutoBloqueo,
    RolEnUso,
    RolExiste,
    RolNoEncontrado,
    RolProtegido,
    UltimoAdministrador,
)
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.acceso.permisos import CATALOGO, CLAVES, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.acceso.schemas import (
    PermisoOut,
    RolCreate,
    RolDetalleOut,
    RolResumenOut,
    RolUpdate,
)
from app.modulos.auditoria.service import AuditoriaService

# Roles con los que nace el sistema (AC-03). El script de datos de prueba los identifica por
# nombre, así que no se eliminan ni se renombran; sus permisos sí se ajustan.
ROLES_INICIALES: frozenset[str] = frozenset(
    {"Administrador", "Almacenista", "Supervisor", "Compras", "Recursos Humanos"}
)


def es_rol_inicial(rol: Rol) -> bool:
    """Si es uno de los cinco con los que nace el sistema. Es identidad de los datos iniciales, no
    una decisión de permisos: eso se verifica siempre por clave (AC-04)."""
    nombre = rol.nombre
    return nombre in ROLES_INICIALES


def _invalido(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def catalogo_de_permisos() -> list[PermisoOut]:
    return [
        PermisoOut(
            clave=p.clave,
            descripcion=p.descripcion,
            modulo=p.clave.split(".")[0],
            es_de_informacion=p.es_de_informacion,
            mvp=p.mvp,
            llega_con=p.llega_con,
            requiere=list(REQUIERE.get(p.clave, ())),
        )
        for p in CATALOGO
    ]


class RolAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.roles = RolRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------------ lectura

    def listar(self) -> list[RolDetalleOut]:
        usuarios, permisos = self.roles.conteos()
        return [
            RolDetalleOut(
                **self._resumen(r, usuarios.get(r.id, 0), len(permisos.get(r.id, []))).model_dump(),
                permisos=permisos.get(r.id, []),
            )
            for r in self.roles.listar()
        ]

    def ver(self, rol_id: uuid.UUID) -> RolDetalleOut:
        return self._detalle(self._obtener(rol_id))

    # ---------------------------------------------------------------- escritura

    def crear(self, actor: Usuario, datos: RolCreate) -> RolDetalleOut:
        nombre = datos.nombre.strip()
        if not nombre:
            raise _invalido("nombre", "Escribe el nombre del rol.")
        if self.roles.get_by_nombre(nombre) is not None:
            raise RolExiste()
        claves = self._claves_validas(datos.permisos)
        descripcion = (datos.descripcion or "").strip() or None
        rol = Rol(nombre=nombre, descripcion=descripcion, protegido=False, activo=True)
        try:
            self.roles.add(rol)
        except DBAPIError as exc:
            if violacion(exc).errno == ERRNO_UNICO:
                self.session.rollback()
                raise RolExiste() from exc
            raise
        self.roles.reemplazar_permisos(rol.id, claves)
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="rol.crear",
            entidad="rol",
            entidad_id=rol.id,
            despues=self._instantanea(rol, claves),
        )
        self.session.commit()
        return self._detalle(rol)

    def editar(self, actor: Usuario, rol_id: uuid.UUID, datos: RolUpdate) -> RolDetalleOut:
        rol = self._obtener(rol_id)
        campos = datos.model_fields_set
        for campo in ("nombre", "activo"):
            if campo in campos and getattr(datos, campo) is None:
                raise _invalido(campo, "Este dato no puede ir vacío.")
        claves = self.roles.permisos(rol.id)
        antes = self._instantanea(rol, claves)

        if "nombre" in campos:
            nombre = datos.nombre.strip()  # type: ignore[union-attr]
            if not nombre:
                raise _invalido("nombre", "Escribe el nombre del rol.")
            if nombre != rol.nombre:
                if es_rol_inicial(rol):
                    raise RolProtegido(
                        "Los cinco roles iniciales conservan su nombre; "
                        "crea un rol nuevo si necesitas otro."
                    )
                otro = self.roles.get_by_nombre(nombre)
                if otro is not None and otro.id != rol.id:
                    raise RolExiste()
                rol.nombre = nombre
        if "descripcion" in campos:
            rol.descripcion = (datos.descripcion or "").strip() or None
        if "activo" in campos and datos.activo != rol.activo:
            if not datos.activo:
                self._puede_inactivar(actor, rol, claves)
            rol.activo = bool(datos.activo)

        despues = self._instantanea(rol, claves)
        if despues != antes:
            try:
                self.session.flush()
            except DBAPIError as exc:
                if violacion(exc).errno == ERRNO_UNICO:
                    self.session.rollback()
                    raise RolExiste() from exc
                raise
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="rol.editar",
                entidad="rol",
                entidad_id=rol.id,
                antes=antes,
                despues=despues,
            )
            self.session.commit()
        return self._detalle(rol)

    def reemplazar_permisos(
        self, actor: Usuario, rol_id: uuid.UUID, permisos: list[str]
    ) -> RolDetalleOut:
        rol = self._obtener(rol_id)
        nuevas = self._claves_validas(permisos)
        actuales = self.roles.permisos(rol.id)
        if nuevas == actuales:
            return self._detalle(rol)
        quitadas = actuales - nuevas
        agregadas = nuevas - actuales

        if P.ACCESO_ADMINISTRAR in quitadas:
            self._proteger_administracion(actor, rol)

        self.roles.reemplazar_permisos(rol.id, nuevas)
        cambios_almacen = self._ajustar_almacenes(actor, rol, agregadas)
        despues: dict[str, Any] = {
            "permisos": sorted(nuevas),
            "agregados": sorted(agregadas),
            "quitados": sorted(quitadas),
        }
        if cambios_almacen:
            despues["usuarios_sin_almacen_asignado"] = cambios_almacen
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="rol.permisos",
            entidad="rol",
            entidad_id=rol.id,
            antes={"rol": rol.nombre, "permisos": sorted(actuales)},
            despues={"rol": rol.nombre, **despues},
        )
        self.session.commit()
        return self._detalle(rol)

    def eliminar(self, actor: Usuario, rol_id: uuid.UUID) -> None:
        rol = self._obtener(rol_id)
        if rol.protegido:
            raise RolProtegido("El rol Administrador está protegido y no se puede eliminar.")
        if es_rol_inicial(rol):
            raise RolProtegido(
                "Los cinco roles iniciales no se eliminan. Si ya no lo usas, "
                "quítale los permisos o inactívalo."
            )
        if self.roles.contar_usuarios(rol.id):
            raise RolEnUso(
                "Ese rol tiene usuarios asignados. Cámbiales el rol antes de eliminarlo."
            )
        antes = self._instantanea(rol, self.roles.permisos(rol.id))
        self.roles.eliminar(rol)
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="rol.eliminar",
            entidad="rol",
            entidad_id=rol_id,
            antes=antes,
        )
        self.session.commit()

    # --------------------------------------------------------------- reglas

    def _proteger_administracion(self, actor: Usuario, rol: Rol) -> None:
        """AC-09: quitar `acceso.administrar` a un rol. No se permite en el Administrador, a quien
        lo hace sobre su propio rol, ni si deja al sistema sin administrador activo."""
        if rol.protegido:
            raise RolProtegido("El rol Administrador no puede perder el permiso de administrar.")
        if actor.rol_id == rol.id:
            raise AutoBloqueo()
        self._exigir_otro_administrador(rol)

    def _exigir_otro_administrador(self, rol: Rol) -> None:
        """Debe quedar algún administrador activo que no dependa de este rol (AC-09)."""
        administradores = self.usuarios.administradores_activos()
        del_rol = {u.id for u in self.usuarios.de_rol(rol.id, solo_activos=True)}
        if administradores & del_rol and not (administradores - del_rol):
            raise UltimoAdministrador()

    def _puede_inactivar(self, actor: Usuario, rol: Rol, claves: set[str]) -> None:
        if rol.protegido:
            raise RolProtegido("El rol Administrador está protegido y no se puede inactivar.")
        if self.roles.contar_usuarios(rol.id):
            raise RolEnUso(
                "Ese rol tiene usuarios asignados. Cámbiales el rol antes de inactivarlo."
            )
        if P.ACCESO_ADMINISTRAR in claves and actor.rol_id == rol.id:
            raise AutoBloqueo()

    def _claves_validas(self, permisos: list[str]) -> set[str]:
        claves = set(permisos)
        desconocidas = sorted(claves - CLAVES)
        if desconocidas:
            raise _invalido("permisos", f"Estos permisos no existen: {', '.join(desconocidas)}.")
        faltan = faltantes(claves)
        if faltan:
            clave, necesarios = next(iter(faltan.items()))
            descripcion = {p.clave: p.descripcion for p in CATALOGO}
            raise _invalido(
                "permisos",
                f"«{descripcion[clave]}» necesita también: "
                + ", ".join(f"«{descripcion[n]}»" for n in necesarios)
                + ".",
            )
        return claves

    def _ajustar_almacenes(self, actor: Usuario, rol: Rol, agregadas: set[str]) -> list[str]:
        """RG-07: quien tiene `almacenes.todos` no lleva almacén asignado. Si el rol lo recibe, sus
        usuarios dejan el almacén (queda en el registro de cambios). Si lo pierde, sus usuarios
        siguen sin almacén hasta que alguien con `almacenes.asignar_personal` se los asigne."""
        if P.ALMACENES_TODOS not in agregadas:
            return []
        movidos: list[str] = []
        for usuario in self.usuarios.de_rol(rol.id):
            if usuario.almacen_id is None:
                continue
            anterior = str(usuario.almacen_id)
            usuario.almacen_id = None
            movidos.append(usuario.usuario)
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="usuario.almacen",
                entidad="usuario",
                entidad_id=usuario.id,
                antes={"almacen": {"id": anterior}},
                despues={"almacen": None, "motivo": "El rol recibió almacenes.todos"},
            )
        return movidos

    # ------------------------------------------------------------ salidas

    def _obtener(self, rol_id: uuid.UUID) -> Rol:
        rol = self.roles.get(rol_id)
        if rol is None:
            raise RolNoEncontrado()
        return rol

    @staticmethod
    def _instantanea(rol: Rol, claves: set[str]) -> dict[str, Any]:
        return {
            "nombre": rol.nombre,
            "descripcion": rol.descripcion,
            "activo": rol.activo,
            "permisos": sorted(claves),
        }

    @staticmethod
    def _resumen(rol: Rol, usuarios: int, permisos: int) -> RolResumenOut:
        return RolResumenOut(
            id=rol.id,
            nombre=rol.nombre,
            descripcion=rol.descripcion,
            activo=rol.activo,
            protegido=rol.protegido,
            inicial=es_rol_inicial(rol),
            total_usuarios=usuarios,
            total_permisos=permisos,
        )

    def _detalle(self, rol: Rol) -> RolDetalleOut:
        claves = self.roles.permisos(rol.id)
        return RolDetalleOut(
            **self._resumen(rol, self.roles.contar_usuarios(rol.id), len(claves)).model_dump(),
            permisos=sorted(claves),
        )
