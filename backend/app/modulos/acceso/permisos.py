"""Catálogo fijo de permisos con clave `modulo.accion` (AC-01, ADR-007).

El catálogo vive en el código; lo que cambia es qué rol tiene cada permiso (tabla `rol_permiso`).
Los routers usan las constantes de `P` para no escribir claves a mano:

    Depends(requiere_permiso(P.ENTREGAS_CREAR))

Fuente: secciones 8.2 y 8.3 de `docs/product/reglas-de-negocio.md`.
"""

from dataclasses import dataclass


class P:
    """Claves de permiso. Un permiso nuevo se agrega aquí y en `CATALOGO`."""

    # --- Sección 8.2 (MVP) ---
    ACCESO_ADMINISTRAR = "acceso.administrar"
    TRABAJADORES_VER = "trabajadores.ver"
    TRABAJADORES_VER_DATOS_PERSONALES = "trabajadores.ver_datos_personales"
    TRABAJADORES_ADMINISTRAR = "trabajadores.administrar"
    TRABAJADORES_INICIAR_BAJA = "trabajadores.iniciar_baja"
    TRABAJADORES_NUMERO_EXTERNO = "trabajadores.numero_externo"
    CATALOGO_VER = "catalogo.ver"
    CATALOGO_ADMINISTRAR = "catalogo.administrar"
    CATALOGO_COSTOS = "catalogo.costos"
    INVENTARIO_VER = "inventario.ver"
    INVENTARIO_ENTRADAS = "inventario.entradas"
    ENTREGAS_CREAR = "entregas.crear"
    DEVOLUCIONES_CREAR = "devoluciones.crear"
    TRASPASOS_OPERAR = "traspasos.operar"
    TRASPASOS_RECIBIR = "traspasos.recibir"
    NO_ADEUDO_EMITIR = "no_adeudo.emitir"
    VALES_VER = "vales.ver"
    VALES_CANCELAR = "vales.cancelar"
    VALES_CANCELAR_TODOS = "vales.cancelar_todos"
    AUTORIZACIONES_RESOLVER = "autorizaciones.resolver"
    DEUDORES_VER = "deudores.ver"
    INSPECCIONES_VER = "inspecciones.ver"
    PIEZAS_INSPECCIONAR = "piezas.inspeccionar"
    PIEZAS_AJUSTAR_VIGENCIA = "piezas.ajustar_vigencia"
    PIEZAS_REGISTRAR_SERIE = "piezas.registrar_serie"
    REPORTES_EXISTENCIAS = "reportes.existencias"
    REPORTES_MOVIMIENTOS = "reportes.movimientos"
    REPORTES_ADEUDOS = "reportes.adeudos"
    REPORTES_CONSUMO = "reportes.consumo"
    ALMACENES_TODOS = "almacenes.todos"
    ALMACENES_ASIGNAR_PERSONAL = "almacenes.asignar_personal"
    ALMACENES_ADMINISTRAR = "almacenes.administrar"
    TABLERO_VER = "tablero.ver"
    ETIQUETAS_IMPRIMIR = "etiquetas.imprimir"
    COMPRAS_SOLICITAR = "compras.solicitar"
    COMPRAS_ATENDER = "compras.atender"

    # --- FEAT-011, sección D (AC-30) ---
    BITACORA_VER = "bitacora.ver"
    RESGUARDO_VER = "resguardo.ver"
    INVENTARIO_IMPORTAR = "inventario.importar"
    CATALOGO_LIMITES = "catalogo.limites"
    PIEZAS_MARCAR_ESTADO = "piezas.marcar_estado"
    ACCESO_USUARIOS = "acceso.usuarios"
    ACCESO_ROLES = "acceso.roles"
    AUDITORIA_VER = "auditoria.ver"

    # --- Sección 8.3 (los agregan las features o están pospuestos) ---
    REPORTES_VALOR_INVENTARIO = "reportes.valor_inventario"
    INVENTARIO_MINIMOS = "inventario.minimos"
    INVENTARIO_AJUSTAR = "inventario.ajustar"
    REPORTES_CIERRE = "reportes.cierre"
    PIEZAS_DAR_DE_BAJA = "piezas.dar_de_baja"
    REVISION_VER = "revision.ver"
    PROYECTOS_VER = "proyectos.ver"
    PROYECTOS_ADMINISTRAR = "proyectos.administrar"
    PROYECTOS_ASIGNAR = "proyectos.asignar"
    DESPACHO_AUTONOMIA = "despacho.autonomia"


@dataclass(frozen=True)
class Permiso:
    clave: str
    descripcion: str
    # True si es del MVP (8.2); False si lo agrega una feature o está pospuesto (8.3).
    mvp: bool
    # De dónde viene: "MVP", "FEAT-002", "FEAT-004", "FEAT-006" o "Pospuesto".
    llega_con: str = "MVP"
    # Permiso de información (AC-05): sin él, el dato no se envía.
    es_de_informacion: bool = False
    # Grupo con el que la matriz de /roles junta el permiso. Vacío: el módulo de su clave.
    grupo: str = ""
    # False: está en el catálogo pero no tiene función en esta versión (se oculta de la matriz y
    # ningún rol inicial lo recibe).
    disponible: bool = True


CATALOGO: tuple[Permiso, ...] = (
    Permiso(P.DESPACHO_AUTONOMIA, "Cambiar la aprobación del despacho de EPP", False, "FEAT-014"),
    Permiso(P.PROYECTOS_VER, "Ver proyectos y sus trabajadores", False, "FEAT-013"),
    Permiso(P.PROYECTOS_ADMINISTRAR, "Crear, editar y cerrar proyectos", False, "FEAT-013"),
    Permiso(P.PROYECTOS_ASIGNAR, "Asignar trabajadores a proyectos", False, "FEAT-013"),
    Permiso(
        P.ACCESO_ADMINISTRAR,
        "Administrador del sistema: siempre debe quedar alguien con este permiso",
        True,
    ),
    Permiso(P.TRABAJADORES_VER, "Ficha básica del trabajador", True),
    Permiso(P.TRABAJADORES_VER_DATOS_PERSONALES, "Ver CURP y NSS", True, es_de_informacion=True),
    Permiso(P.TRABAJADORES_ADMINISTRAR, "Alta, reingreso, credencial y cancelar una baja", True),
    Permiso(P.TRABAJADORES_INICIAR_BAJA, "Iniciar la baja", True),
    Permiso(
        P.TRABAJADORES_NUMERO_EXTERNO,
        "Capturar a mano el número de empleado al dar de alta (número propio del centro)",
        True,
        "FEAT-008",
    ),
    Permiso(P.CATALOGO_VER, "Ver categorías, artículos y piezas", True),
    Permiso(P.CATALOGO_ADMINISTRAR, "Administrar categorías, artículos y requisitos", True),
    Permiso(P.CATALOGO_COSTOS, "Ver y capturar costos", True, es_de_informacion=True),
    Permiso(
        P.INVENTARIO_VER, "Ver existencias de su almacén (de todos, con almacenes.todos)", True
    ),
    Permiso(P.INVENTARIO_ENTRADAS, "Entradas e importación", True),
    Permiso(P.ENTREGAS_CREAR, "Entregar y pedir autorización", True),
    Permiso(P.DEVOLUCIONES_CREAR, "Recibir devoluciones", True),
    Permiso(P.TRASPASOS_OPERAR, "Enviar traspasos", True),
    Permiso(P.TRASPASOS_RECIBIR, "Recibir traspasos en el almacén de destino", True),
    Permiso(P.NO_ADEUDO_EMITIR, "Emitir el vale de no adeudo", True),
    Permiso(P.VALES_VER, "Consultar vales", True),
    Permiso(P.VALES_CANCELAR, "Cancelar los vales propios", True),
    Permiso(P.VALES_CANCELAR_TODOS, "Cancelar los vales de cualquiera", True),
    Permiso(P.AUTORIZACIONES_RESOLVER, "Autorizar o rechazar excedentes", True),
    Permiso(P.DEUDORES_VER, "Ver deudores", True),
    Permiso(P.INSPECCIONES_VER, "Ver inspecciones pendientes", True),
    Permiso(P.PIEZAS_INSPECCIONAR, "Inspeccionar y marcar No apta", True),
    Permiso(P.PIEZAS_AJUSTAR_VIGENCIA, "Ajustar la vigencia de una inspección", True),
    Permiso(
        P.PIEZAS_REGISTRAR_SERIE,
        "Poner el número de serie a una pieza que no lo tiene",
        True,
    ),
    Permiso(P.REPORTES_EXISTENCIAS, "Reporte de existencias", True),
    Permiso(P.REPORTES_MOVIMIENTOS, "Reporte de movimientos", True),
    Permiso(P.REPORTES_ADEUDOS, "Reporte de adeudos", True),
    Permiso(P.REPORTES_CONSUMO, "Reporte de consumo", True),
    Permiso(P.ALMACENES_TODOS, "Ver y operar todos los almacenes (solo el Administrador)", True),
    Permiso(
        P.ALMACENES_ASIGNAR_PERSONAL,
        "Asignar personal a su almacén o liberarlo; entre almacenes, solo con almacenes.todos",
        True,
    ),
    Permiso(
        P.ALMACENES_ADMINISTRAR,
        "Dar de alta, editar, inactivar y reactivar almacenes",
        True,
        "FEAT-008",
    ),
    Permiso(
        P.TABLERO_VER,
        "Tablero de inicio (todos los almacenes con almacenes.todos; si no, el suyo)",
        True,
        "FEAT-008",
    ),
    Permiso(P.ETIQUETAS_IMPRIMIR, "Hojas de QR", True),
    Permiso(P.COMPRAS_SOLICITAR, "Pedir una compra urgente", True),
    Permiso(P.COMPRAS_ATENDER, "Atender las solicitudes de compra", True),
    Permiso(
        P.BITACORA_VER,
        "Ver la bitácora de un almacén: lo que sale, lo que llega y las entradas",
        True,
        "FEAT-011",
        grupo="inventario",
    ),
    Permiso(
        P.RESGUARDO_VER,
        "Ver quién tiene qué: las piezas y herramientas en manos de cada trabajador",
        True,
        "FEAT-011",
        grupo="trabajadores",
    ),
    Permiso(
        P.INVENTARIO_IMPORTAR,
        "Cargar inventario desde un archivo de Excel (capturar a mano es inventario.entradas)",
        True,
        "FEAT-011",
        grupo="inventario",
    ),
    Permiso(
        P.CATALOGO_LIMITES,
        "Cambiar los límites de entrega de categorías y artículos",
        True,
        "FEAT-011",
    ),
    Permiso(
        P.PIEZAS_MARCAR_ESTADO,
        "Pasar una pieza a mantenimiento o calibración y devolverla al servicio",
        True,
        "FEAT-011",
    ),
    Permiso(
        P.ACCESO_USUARIOS,
        "Dar de alta y administrar usuarios, contraseñas y PIN",
        True,
        "FEAT-011",
    ),
    Permiso(P.ACCESO_ROLES, "Crear roles y cambiar sus permisos", True, "FEAT-011"),
    Permiso(P.AUDITORIA_VER, "Ver el registro de cambios del sistema", True, "FEAT-011"),
    Permiso(
        P.REPORTES_VALOR_INVENTARIO,
        "Ver el valor del inventario (solo totales, nunca el costo de un artículo)",
        True,
        "FEAT-012",
        True,
    ),
    Permiso(P.INVENTARIO_MINIMOS, "Fijar mínimos por almacén", True, "FEAT-004"),
    Permiso(P.INVENTARIO_AJUSTAR, "Registrar faltantes del almacén", True, "FEAT-002"),
    Permiso(P.REPORTES_CIERRE, "Ver el reporte de cierre del almacén", True, "FEAT-002"),
    Permiso(
        P.PIEZAS_DAR_DE_BAJA,
        "Dar una pieza por perdida o de baja",
        False,
        "Pospuesto",
        disponible=False,
    ),
    Permiso(P.REVISION_VER, "Lista de revisión", False, "Pospuesto", disponible=False),
)

CLAVES: frozenset[str] = frozenset(p.clave for p in CATALOGO)
CLAVES_MVP: frozenset[str] = frozenset(p.clave for p in CATALOGO if p.mvp)
# Los que sí funcionan en esta versión: el Administrador recibe estos y la matriz solo ofrece estos.
CLAVES_DISPONIBLES: frozenset[str] = frozenset(p.clave for p in CATALOGO if p.disponible)

# AC-32: el rol Administrador (protegido) nunca pierde estos.
PROTEGIDOS_DEL_ADMINISTRADOR: tuple[str, ...] = (
    P.ACCESO_ADMINISTRAR,
    P.ACCESO_USUARIOS,
    P.ACCESO_ROLES,
    P.ALMACENES_TODOS,
    P.ALMACENES_ADMINISTRAR,
)

assert len(CLAVES) == len(CATALOGO), "Hay claves de permiso repetidas"


def es_clave_valida(clave: str) -> bool:
    return clave in CLAVES
