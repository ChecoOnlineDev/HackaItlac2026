"""Datos de prueba de `acceso`: los cinco roles iniciales y un usuario por rol. Idempotente.

Las contraseñas y el PIN de prueba salen de `CLAVE_DATOS_PRUEBA` y `PIN_DATOS_PRUEBA` (.env).
No son datos reales.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.acceso.permisos import CLAVES_DISPONIBLES, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.almacenes.repository import AlmacenRepository
from app.modulos.auditoria.models import Auditoria
from app.seguridad import hashear_secreto, verificar_secreto

# Permisos de los roles iniciales: sección 8.2 de las reglas de negocio. El Administrador
# tiene todos los que funcionan en esta versión (los 4 de 8.3 sin uso no se asignan a nadie).
PERMISOS_INICIALES: dict[str, frozenset[str]] = {
    "Administrador": CLAVES_DISPONIBLES,
    "Almacenista": frozenset(
        {
            P.TRABAJADORES_VER,
            P.TRABAJADORES_INICIAR_BAJA,
            P.CATALOGO_VER,
            P.INVENTARIO_VER,
            P.ENTREGAS_CREAR,
            P.DEVOLUCIONES_CREAR,
            P.NO_ADEUDO_EMITIR,
            P.VALES_VER,
            P.VALES_CANCELAR,
            P.PIEZAS_INSPECCIONAR,
            P.PIEZAS_MARCAR_ESTADO,
            P.TRASPASOS_RECIBIR,
            P.RESGUARDO_VER,
            P.BITACORA_VER,
            P.COMPRAS_SOLICITAR,
            P.TABLERO_VER,
        }
    ),
    "Supervisor": frozenset(
        {
            P.TRABAJADORES_VER,
            P.TRABAJADORES_INICIAR_BAJA,
            P.CATALOGO_VER,
            P.CATALOGO_ADMINISTRAR,
            P.INVENTARIO_VER,
            P.ENTREGAS_CREAR,
            P.DEVOLUCIONES_CREAR,
            P.TRASPASOS_OPERAR,
            P.TRASPASOS_RECIBIR,
            P.PIEZAS_REGISTRAR_SERIE,
            P.NO_ADEUDO_EMITIR,
            P.VALES_VER,
            P.VALES_CANCELAR,
            P.VALES_CANCELAR_TODOS,
            P.AUTORIZACIONES_RESOLVER,
            P.PIEZAS_INSPECCIONAR,
            P.PIEZAS_AJUSTAR_VIGENCIA,
            P.PIEZAS_MARCAR_ESTADO,
            P.RESGUARDO_VER,
            P.BITACORA_VER,
            P.REPORTES_EXISTENCIAS,
            P.REPORTES_MOVIMIENTOS,
            P.REPORTES_ADEUDOS,
            P.REPORTES_CONSUMO,
            P.ALMACENES_ASIGNAR_PERSONAL,
            P.ETIQUETAS_IMPRIMIR,
            P.COMPRAS_SOLICITAR,
            P.TABLERO_VER,
        }
    ),
    "Compras": frozenset(
        {
            P.CATALOGO_VER,
            P.CATALOGO_ADMINISTRAR,
            P.CATALOGO_COSTOS,
            P.CATALOGO_LIMITES,
            P.INVENTARIO_VER,
            P.INVENTARIO_ENTRADAS,
            P.INVENTARIO_IMPORTAR,
            P.BITACORA_VER,
            P.PIEZAS_REGISTRAR_SERIE,
            P.VALES_VER,
            P.VALES_CANCELAR,
            P.REPORTES_EXISTENCIAS,
            P.REPORTES_MOVIMIENTOS,
            P.REPORTES_CONSUMO,
            P.ETIQUETAS_IMPRIMIR,
            P.COMPRAS_ATENDER,
        }
    ),
    "Recursos Humanos": frozenset(
        {
            P.TRABAJADORES_VER,
            P.TRABAJADORES_VER_DATOS_PERSONALES,
            P.TRABAJADORES_ADMINISTRAR,
            P.TRABAJADORES_INICIAR_BAJA,
            P.VALES_VER,
            P.REPORTES_ADEUDOS,
            P.ETIQUETAS_IMPRIMIR,
        }
    ),
}

DESCRIPCIONES = {
    "Administrador": "Todos los permisos.",
    "Almacenista": "Opera su almacén: entregas, devoluciones y solicitudes de compra.",
    "Supervisor": "Supervisa su almacén: autoriza excepciones, traspasos, personal y catálogo.",
    "Compras": "Carga inventario, ve costos y atiende las solicitudes de compra.",
    "Recursos Humanos": "Administra trabajadores y ve datos personales.",
}

# (usuario, nombre, rol, clave del almacén asignado, tiene PIN). Solo el Administrador tiene
# `almacenes.todos` y no lleva almacén; RH no opera almacén. Cada almacén de prueba tiene su
# supervisor y su almacenista; Compras es de Kepler (ahí se carga el inventario).
USUARIOS_PRUEBA = (
    ("admin", "Administrador de prueba", "Administrador", None, True),
    ("supervisor", "Supervisor Kepler", "Supervisor", "KEP", True),
    ("sup_con", "Supervisor Contratistas", "Supervisor", "CON", True),
    ("sup_mid", "Supervisor Midrex", "Supervisor", "MID", True),
    ("sup_hyl", "Supervisor HYL", "Supervisor", "HYL", True),
    ("sup_lam", "Supervisor Laminador", "Supervisor", "LAM", True),
    ("sup_min", "Supervisor Minas", "Supervisor", "MIN", True),
    ("compras", "Compras de prueba", "Compras", "KEP", False),
    ("rh", "Recursos Humanos de prueba", "Recursos Humanos", None, False),
    ("almacenista", "Almacenista Kepler", "Almacenista", "KEP", False),
    ("alm_con", "Almacenista Contratistas", "Almacenista", "CON", False),
    ("alm_mid", "Almacenista Midrex", "Almacenista", "MID", False),
    ("alm_hyl", "Almacenista HYL", "Almacenista", "HYL", False),
    ("alm_lam", "Almacenista Laminador", "Almacenista", "LAM", False),
    ("alm_min", "Almacenista Minas", "Almacenista", "MIN", False),
)


def _quitados_a_mano(session: Session, rol: Rol) -> set[str]:
    """Permisos que alguien le quitó a este rol desde /roles (AC-10 los deja en el registro)."""
    quitados: set[str] = set()
    filas = session.scalars(
        select(Auditoria).where(
            Auditoria.accion == "rol.permisos", Auditoria.entidad_id == str(rol.id)
        )
    )
    for fila in filas:
        quitados |= set((fila.despues or {}).get("quitados", []))
    return quitados


def _poner_permisos(
    session: Session, roles: RolRepository, rol: Rol, claves: frozenset[str], restablecer: bool
) -> None:
    """AC-33: por omisión solo agrega lo que falta; no quita ni vuelve a poner lo que se quitó
    desde /roles. Con `restablecer` deja al rol exactamente como nace."""
    if restablecer:
        roles.reemplazar_permisos(rol.id, set(claves))
        return
    actuales = roles.permisos(rol.id)
    faltan = set(claves) - actuales - _quitados_a_mano(session, rol)
    if rol.protegido:  # el Administrador siempre trae todo lo que funciona (AC-32)
        faltan = set(claves) - actuales
    if faltan:
        roles.reemplazar_permisos(rol.id, actuales | faltan)


def cargar(session: Session, *, restablecer_roles: bool = False) -> None:
    """Crea lo que falta. `restablecer_roles=True` (opción explícita) vuelve los cinco roles
    iniciales a sus permisos de fábrica; sin ella, lo editado en /roles se respeta (AC-33)."""
    ajustes = get_settings()
    roles = RolRepository(session)
    usuarios = UsuarioRepository(session)
    almacenes = AlmacenRepository(session)

    por_nombre: dict[str, Rol] = {}
    for nombre, claves in PERMISOS_INICIALES.items():
        rol = roles.get_by_nombre(nombre)
        if rol is None:
            rol = roles.add(
                Rol(
                    nombre=nombre,
                    descripcion=DESCRIPCIONES[nombre],
                    protegido=nombre == "Administrador",
                )
            )
        _poner_permisos(session, roles, rol, claves, restablecer_roles)
        por_nombre[nombre] = rol

    for nombre_usuario, nombre, nombre_rol, clave_almacen, con_pin in USUARIOS_PRUEBA:
        almacen = almacenes.get_by_clave(clave_almacen) if clave_almacen else None
        usuario = usuarios.get_by_usuario(nombre_usuario)
        if usuario is None:
            usuario = Usuario(
                usuario=nombre_usuario,
                nombre=nombre,
                contrasena_hash=hashear_secreto(ajustes.clave_datos_prueba),
                rol_id=por_nombre[nombre_rol].id,
            )
            usuarios.add(usuario)
        usuario.nombre = nombre
        usuario.rol_id = por_nombre[nombre_rol].id
        usuario.almacen_id = almacen.id if almacen else None
        usuario.activo = True
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.pin_intentos_fallidos = 0
        usuario.pin_bloqueado_hasta = None
        if not verificar_secreto(ajustes.clave_datos_prueba, usuario.contrasena_hash):
            usuario.contrasena_hash = hashear_secreto(ajustes.clave_datos_prueba)
        if con_pin and (
            usuario.pin_hash is None
            or not verificar_secreto(ajustes.pin_datos_prueba, usuario.pin_hash)
        ):
            usuario.pin_hash = hashear_secreto(ajustes.pin_datos_prueba)
    session.flush()
