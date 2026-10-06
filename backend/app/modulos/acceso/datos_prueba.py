"""Datos de prueba de `acceso`: los cinco roles iniciales y un usuario por rol. Idempotente.

Las contraseñas y el PIN de prueba salen de `CLAVE_DATOS_PRUEBA` y `PIN_DATOS_PRUEBA` (.env).
No son datos reales.
"""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.acceso.permisos import CATALOGO, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.almacenes.repository import AlmacenRepository
from app.seguridad import hashear_secreto, verificar_secreto

# Permisos de los roles iniciales: sección 8.2 de las reglas de negocio. El Administrador
# tiene todos los del catálogo.
PERMISOS_INICIALES: dict[str, frozenset[str]] = {
    "Administrador": frozenset(p.clave for p in CATALOGO),
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
            P.NO_ADEUDO_EMITIR,
            P.VALES_VER,
            P.VALES_CANCELAR,
            P.VALES_CANCELAR_TODOS,
            P.AUTORIZACIONES_RESOLVER,
            P.PIEZAS_INSPECCIONAR,
            P.PIEZAS_AJUSTAR_VIGENCIA,
            P.REPORTES_EXISTENCIAS,
            P.REPORTES_MOVIMIENTOS,
            P.REPORTES_ADEUDOS,
            P.REPORTES_CONSUMO,
            P.ALMACENES_ASIGNAR_PERSONAL,
            P.ETIQUETAS_IMPRIMIR,
        }
    ),
    "Compras": frozenset(
        {
            P.CATALOGO_VER,
            P.CATALOGO_ADMINISTRAR,
            P.CATALOGO_COSTOS,
            P.INVENTARIO_VER,
            P.INVENTARIO_ENTRADAS,
            P.VALES_VER,
            P.VALES_CANCELAR,
            P.REPORTES_EXISTENCIAS,
            P.REPORTES_MOVIMIENTOS,
            P.REPORTES_CONSUMO,
            P.ETIQUETAS_IMPRIMIR,
        }
    ),
    "Recursos Humanos": frozenset(
        {
            P.TRABAJADORES_VER,
            P.TRABAJADORES_VER_DATOS_PERSONALES,
            P.TRABAJADORES_ADMINISTRAR,
            P.TRABAJADORES_INICIAR_BAJA,
            P.REPORTES_ADEUDOS,
            P.ETIQUETAS_IMPRIMIR,
        }
    ),
}

DESCRIPCIONES = {
    "Administrador": "Todos los permisos.",
    "Almacenista": "Opera su almacén: entregas, devoluciones y traspasos.",
    "Supervisor": "Supervisa su almacén: autoriza excepciones, traspasos, personal y catálogo.",
    "Compras": "Carga inventario y ve costos.",
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


def cargar(session: Session) -> None:
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
        roles.reemplazar_permisos(rol.id, set(claves))
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
