"""Persistencia del módulo `acceso`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, delete, exists, func, or_, select, update
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Rol, RolPermiso, SesionDispositivo, Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _rol_tiene(clave: str) -> ColumnElement[bool]:
    """Condición: el rol del usuario tiene el permiso `clave` (como dato en `rol_permiso`)."""
    return exists().where(RolPermiso.rol_id == Usuario.rol_id, RolPermiso.permiso == clave)


# Quien tiene alguno de estos permisos trabaja en un almacén (RG-07). RH no: administra personas.
PERMISOS_DE_ALMACEN = (
    P.INVENTARIO_VER,
    P.INVENTARIO_ENTRADAS,
    P.ENTREGAS_CREAR,
    P.DEVOLUCIONES_CREAR,
    P.TRASPASOS_OPERAR,
    P.TRASPASOS_RECIBIR,
    P.AUTORIZACIONES_RESOLVER,
)


@dataclass(frozen=True)
class FiltrosUsuarios:
    q: str | None = None
    rol_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    sin_almacen: bool = False
    activo: bool | None = None
    # Solo quienes operan un almacén (no tienen `almacenes.todos`).
    # Y que tienen algún permiso de almacén (`PERMISOS_DE_ALMACEN`): RH no opera ninguno (RG-07).
    solo_operativos: bool = False
    # AC-06: alcance de quien asigna sin `almacenes.todos`: los de ese almacén y los libres.
    almacen_o_libres_id: uuid.UUID | None = None
    # Lo mismo para quien no tiene almacén: solo los libres.
    solo_libres: bool = False


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
            condiciones.append(or_(*(_rol_tiene(clave) for clave in PERMISOS_DE_ALMACEN)))
        if filtros.almacen_o_libres_id is not None:
            condiciones.append(
                or_(
                    Usuario.almacen_id == filtros.almacen_o_libres_id,
                    Usuario.almacen_id.is_(None),
                )
            )
        if filtros.solo_libres:
            condiciones.append(Usuario.almacen_id.is_(None))

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

    def de_rol(self, rol_id: uuid.UUID, *, solo_activos: bool = False) -> list[Usuario]:
        consulta = select(Usuario).where(Usuario.rol_id == rol_id)
        if solo_activos:
            consulta = consulta.where(Usuario.activo.is_(True))
        return list(self.session.scalars(consulta.order_by(Usuario.nombre, Usuario.id)))

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

    def eliminar(self, rol: Rol) -> None:
        """Quita el rol y sus permisos (el service ya comprobó que nadie lo usa)."""
        self.session.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol.id))
        self.session.delete(rol)
        self.session.flush()

    def conteos(self) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, list[str]]]:
        """Usuarios por rol y permisos de cada rol (ordenados): `(usuarios, permisos)`."""
        usuarios = dict(
            self.session.execute(
                select(Usuario.rol_id, func.count()).group_by(Usuario.rol_id)
            ).all()
        )
        permisos: dict[uuid.UUID, list[str]] = {}
        for rol_id, clave in self.session.execute(
            select(RolPermiso.rol_id, RolPermiso.permiso).order_by(RolPermiso.permiso)
        ):
            permisos.setdefault(rol_id, []).append(clave)
        return usuarios, permisos

    def contar_usuarios(self, rol_id: uuid.UUID) -> int:
        return (
            self.session.scalar(
                select(func.count()).select_from(Usuario).where(Usuario.rol_id == rol_id)
            )
            or 0
        )

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


class SesionDispositivoRepository:
    """Los tokens de renovación por dispositivo. Nunca hace commit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fila: SesionDispositivo) -> SesionDispositivo:
        self.session.add(fila)
        self.session.flush()
        return fila

    def por_huella(self, huella: str, *, bloquear: bool = False) -> SesionDispositivo | None:
        """La fila de ese token de renovación. Con `bloquear` toma la fila (`FOR UPDATE`): dos
        renovaciones simultáneas con el mismo token se atienden una por una."""
        consulta = select(SesionDispositivo).where(SesionDispositivo.refresh_hash == huella)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(consulta)

    def vigente_de_familia(self, familia_id: uuid.UUID) -> SesionDispositivo | None:
        """La fila sin revocar de la familia (la que se renovó la última vez), si la hay."""
        return self.session.scalar(
            select(SesionDispositivo).where(
                SesionDispositivo.familia_id == familia_id,
                SesionDispositivo.revocada_en.is_(None),
            )
        )

    def familia_abierta(self, familia_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        """True si la familia es del usuario y no está revocada (se pregunta en cada petición)."""
        return bool(
            self.session.scalar(
                select(
                    exists().where(
                        SesionDispositivo.familia_id == familia_id,
                        SesionDispositivo.usuario_id == usuario_id,
                        SesionDispositivo.revocada_en.is_(None),
                    )
                )
            )
        )

    def revocar_familia(self, familia_id: uuid.UUID, motivo: str, ahora: datetime) -> int:
        """Revoca lo que siga vigente de la familia. Devuelve cuántas filas revocó."""
        resultado = self.session.execute(
            update(SesionDispositivo)
            .where(
                SesionDispositivo.familia_id == familia_id, SesionDispositivo.revocada_en.is_(None)
            )
            .values(revocada_en=ahora, motivo_revocacion=motivo)
            .execution_options(synchronize_session="fetch")
        )
        return resultado.rowcount

    def revocar_de_usuario(
        self,
        usuario_id: uuid.UUID,
        motivo: str,
        ahora: datetime,
        *,
        excepto_familia: uuid.UUID | None = None,
    ) -> int:
        """Revoca todas las sesiones vigentes del usuario (menos `excepto_familia`)."""
        condiciones = [
            SesionDispositivo.usuario_id == usuario_id,
            SesionDispositivo.revocada_en.is_(None),
        ]
        if excepto_familia is not None:
            condiciones.append(SesionDispositivo.familia_id != excepto_familia)
        resultado = self.session.execute(
            update(SesionDispositivo)
            .where(*condiciones)
            .values(revocada_en=ahora, motivo_revocacion=motivo)
            .execution_options(synchronize_session="fetch")
        )
        return resultado.rowcount

    def abiertas_de_usuario(
        self, usuario_id: uuid.UUID, ahora: datetime
    ) -> list[SesionDispositivo]:
        """Una fila por dispositivo con sesión abierta: la vigente de cada familia, sin revocar,
        dentro de su ventana y de su tope. La más reciente primero."""
        filas = self.session.scalars(
            select(SesionDispositivo)
            .where(
                SesionDispositivo.usuario_id == usuario_id,
                SesionDispositivo.revocada_en.is_(None),
                SesionDispositivo.expira_en > ahora,
                SesionDispositivo.vence_absoluto > ahora,
            )
            .order_by(SesionDispositivo.ultimo_uso.desc(), SesionDispositivo.id)
        )
        return list(filas)

    def purgar(self, vencidas_antes_de: datetime, *, maximo: int = 500) -> int:
        """Borra las familias cuyo tope absoluto ya pasó hace tiempo (todas sus filas comparten
        el tope), para que la tabla no crezca sin fin. Primero lee (sin bloquear) y borra por
        llave primaria: un `DELETE` por rango bloquearía huecos del índice y haría esperar a los
        inicios de sesión simultáneos."""
        ids = list(
            self.session.scalars(
                select(SesionDispositivo.id)
                .where(SesionDispositivo.vence_absoluto < vencidas_antes_de)
                .limit(maximo)
            )
        )
        if not ids:
            return 0
        resultado = self.session.execute(
            delete(SesionDispositivo).where(SesionDispositivo.id.in_(ids))
        )
        return resultado.rowcount
