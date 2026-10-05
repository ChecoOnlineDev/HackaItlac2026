"""Persistencia del módulo `acceso`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Rol, RolPermiso, Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _rol_tiene(clave: str) -> ColumnElement[bool]:
    """Condición: el rol del usuario tiene el permiso `clave` (como dato en `rol_permiso`)."""
    return exists().where(RolPermiso.rol_id == Usuario.rol_id, RolPermiso.permiso == clave)


@dataclass(frozen=True)
class FiltrosUsuarios:
    q: str | None = None
    rol_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    sin_almacen: bool = False
    activo: bool | None = None
    # Solo quienes operan un almacén (no tienen `almacenes.todos`).
    solo_operativos: bool = False


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.session.get(Usuario, usuario_id)

    def bloquear(self, usuario_id: uuid.UUID) -> Usuario:
        """El usuario releído de la base con su fila bloqueada (`FOR UPDATE`) hasta el commit.

        Sirve para contar intentos fallidos sin carreras: quien llega después espera y ve el
        contador y el bloqueo ya actualizados. Refresca el objeto aunque ya esté en la sesión.
        Solo bloquea la fila de `usuario` (no la de su rol).
        """
        return self.session.scalars(
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .with_for_update(of=Usuario)
            .execution_options(populate_existing=True)
        ).one()

    def get_by_usuario(self, nombre_usuario: str) -> Usuario | None:
        return self.session.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario))

    def add(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        self.session.flush()
        return usuario

    def listar(
        self, filtros: FiltrosUsuarios, *, limit: int, offset: int
    ) -> tuple[list[tuple[Usuario, Almacen | None]], int]:
        """Usuarios con su almacén (si lo tienen), ordenados por nombre, y el total."""
        condiciones: list[ColumnElement[bool]] = []
        if filtros.q:
            patron = f"%{_escapar_like(filtros.q.strip())}%"
            condiciones.append(
                or_(
                    Usuario.nombre.like(patron, escape="\\"),
                    Usuario.usuario.like(patron, escape="\\"),
                )
            )
        if filtros.rol_id is not None:
            condiciones.append(Usuario.rol_id == filtros.rol_id)
        if filtros.almacen_id is not None:
            condiciones.append(Usuario.almacen_id == filtros.almacen_id)
        if filtros.sin_almacen:
            condiciones.append(Usuario.almacen_id.is_(None))
        if filtros.activo is not None:
            condiciones.append(Usuario.activo.is_(filtros.activo))
        if filtros.solo_operativos:
            condiciones.append(~_rol_tiene(P.ALMACENES_TODOS))

        total = self.session.scalar(select(func.count()).select_from(Usuario).where(*condiciones))
        filas = self.session.execute(
            select(Usuario, Almacen)
            .outerjoin(Almacen, Almacen.id == Usuario.almacen_id)
            .where(*condiciones)
            .order_by(Usuario.nombre, Usuario.usuario, Usuario.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return [(u, a) for u, a in filas], total or 0

    def administradores_activos(self) -> set[uuid.UUID]:
        """Ids de los usuarios activos, con rol activo, que tienen `acceso.administrar`.

        Bloquea esas filas (`FOR UPDATE`) para que dos cambios simultáneos no dejen el sistema sin
        administrador (AC-09).
        """
        ids = self.session.scalars(
            select(Usuario.id)
            .join(Rol, Rol.id == Usuario.rol_id)
            .where(Usuario.activo.is_(True), Rol.activo.is_(True), _rol_tiene(P.ACCESO_ADMINISTRAR))
            .with_for_update()
        )
        return set(ids)


class RolRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, rol_id: uuid.UUID) -> Rol | None:
        return self.session.get(Rol, rol_id)

    def get_by_nombre(self, nombre: str) -> Rol | None:
        return self.session.scalar(select(Rol).where(Rol.nombre == nombre))

    def listar(self) -> list[Rol]:
        return list(self.session.scalars(select(Rol).order_by(Rol.nombre)))

    def add(self, rol: Rol) -> Rol:
        self.session.add(rol)
        self.session.flush()
        return rol

    def permisos(self, rol_id: uuid.UUID) -> set[str]:
        filas = self.session.scalars(select(RolPermiso.permiso).where(RolPermiso.rol_id == rol_id))
        return set(filas)

    def reemplazar_permisos(self, rol_id: uuid.UUID, claves: set[str]) -> None:
        """Deja al rol exactamente con `claves` (agrega y quita solo la diferencia)."""
        actuales = self.permisos(rol_id)
        sobran = actuales - claves
        if sobran:
            self.session.execute(
                delete(RolPermiso).where(
                    RolPermiso.rol_id == rol_id, RolPermiso.permiso.in_(sobran)
                )
            )
        for clave in claves - actuales:
            self.session.add(RolPermiso(rol_id=rol_id, permiso=clave))
        self.session.flush()
