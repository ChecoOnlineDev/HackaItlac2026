"""Persistencia del módulo `acceso`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Rol, RolPermiso, Usuario


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.session.get(Usuario, usuario_id)

    def get_by_usuario(self, nombre_usuario: str) -> Usuario | None:
        return self.session.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario))

    def add(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        self.session.flush()
        return usuario


class RolRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_nombre(self, nombre: str) -> Rol | None:
        return self.session.scalar(select(Rol).where(Rol.nombre == nombre))

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
