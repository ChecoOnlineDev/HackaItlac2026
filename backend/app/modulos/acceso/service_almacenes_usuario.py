"""AC-36 a AC-41: conjunto y almacén activo, independientes de los dispositivos."""

from app.core.excepciones import Conflicto, DatosInvalidos, NoEncontrado, SinPermiso
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import PERMISOS_DE_ALMACEN
from app.modulos.acceso.schemas import PersonalOut, RolSesionOut
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado


class AlmacenesUsuarioService:
    def __init__(self, session):
        self.session = session
        self.acceso = AccesoService(session)
        self.usuarios = self.acceso.usuarios

    def cambiar_activo(self, actor, datos):
        try:
            usuario = self.usuarios.bloquear(actor.id)
            if self.acceso.tiene_permiso(usuario, P.ALMACENES_TODOS):
                raise DatosInvalidos(
                    "Tu cuenta consulta todos los almacenes y no necesita uno activo.",
                    [{"regla": "AC-39"}],
                )
            if datos.almacen_id not in self.acceso.almacenes_del_usuario(usuario.id):
                error = SinPermiso(
                    "Este almacén no está asignado a tu cuenta.", [{"regla": "AC-39"}]
                )
                error.codigo = "ALMACEN_NO_ASIGNADO"
                raise error
            almacen = self.acceso.almacenes.obtener(datos.almacen_id)
            if almacen.estado != "ACTIVO":
                error = Conflicto("El almacén está cerrado.", [{"regla": "AC-39"}])
                error.codigo = "ALMACEN_CERRADO"
                raise error
            anterior = usuario.almacen_id
            usuario.almacen_id = almacen.id
            self.acceso.auditoria.registrar(
                usuario_id=actor.id,
                accion="usuario.almacen_activo",
                entidad="usuario",
                entidad_id=usuario.id,
                antes={"almacen_id": anterior},
                despues={"almacen_id": almacen.id, "regla": "AC-39"},
            )
            self.session.commit()
            return self.acceso.construir_sesion(usuario)
        except Exception:
            self.session.rollback()
            raise

    def asignar_conjunto(self, id, datos, actor):
        administrador = self.acceso.tiene_permiso(actor, P.ACCESO_USUARIOS)
        if not administrador:
            self.acceso.exigir_permiso(actor, P.ALMACENES_ASIGNAR_PERSONAL)
        try:
            usuario = self.usuarios.bloquear(id)
            if usuario is None:
                raise NoEncontrado("No se encontró el usuario.")
            permisos = self.acceso.permisos_de(usuario)
            if (
                not usuario.activo
                or P.ALMACENES_TODOS in permisos
                or not set(PERMISOS_DE_ALMACEN).intersection(permisos)
            ):
                raise DatosInvalidos(
                    "Elige un usuario activo que opere en almacenes.", [{"regla": "AC-41"}]
                )
            anteriores = self.acceso.almacenes_del_usuario(id)
            conjunto = set(datos.almacenes_id)
            if not administrador:
                propios = self.acceso.almacenes_del_usuario(actor.id)
                if (anteriores ^ conjunto) - propios or (actor.id == id and conjunto - anteriores):
                    raise SinPermiso(
                        "Solo puedes asignar tus almacenes a otras personas.", [{"regla": "AC-41"}]
                    )
            try:
                almacenes = [self.acceso.almacenes.obtener(almacen_id) for almacen_id in conjunto]
            except AlmacenNoEncontrado as exc:
                raise DatosInvalidos(
                    "Uno de los almacenes elegidos no existe.", [{"regla": "AC-41"}]
                ) from exc
            if any(a.estado != "ACTIVO" for a in almacenes):
                raise DatosInvalidos(
                    "Solo se pueden asignar almacenes activos.", [{"regla": "AC-41"}]
                )
            if datos.almacen_activo_id is not None and datos.almacen_activo_id not in conjunto:
                raise DatosInvalidos(
                    "El almacén activo debe estar dentro del conjunto.", [{"regla": "AC-41"}]
                )
            elegido = datos.almacen_activo_id or (
                usuario.almacen_id if usuario.almacen_id in conjunto else None
            )
            if elegido is None and almacenes:
                elegido = min(almacenes, key=lambda a: a.nombre.casefold()).id
            usuario.almacen_id = elegido
            self.usuarios.reemplazar_almacenes(usuario, conjunto)
            self.acceso.auditoria.registrar(
                usuario_id=actor.id,
                accion="usuario.almacenes",
                entidad="usuario",
                entidad_id=id,
                antes={"almacenes_id": sorted(map(str, anteriores))},
                despues={
                    "almacenes_id": sorted(map(str, conjunto)),
                    "almacen_activo_id": elegido,
                    "regla": "AC-41",
                },
            )
            self.session.commit()
            sesion = self.acceso.construir_sesion(usuario)
            return PersonalOut(
                id=usuario.id,
                nombre=usuario.nombre,
                usuario=usuario.usuario,
                rol=RolSesionOut(id=usuario.rol.id, nombre=usuario.rol.nombre),
                almacen=sesion.almacen,
                activo=usuario.activo,
                almacenes=sesion.almacenes,
                almacen_activo=sesion.almacen_activo,
            )
        except Exception:
            self.session.rollback()
            raise
