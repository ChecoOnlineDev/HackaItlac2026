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
    NO_ADEUDO_EMITIR = "no_adeudo.emitir"
    VALES_VER = "vales.ver"
    VALES_CANCELAR = "vales.cancelar"
    VALES_CANCELAR_TODOS = "vales.cancelar_todos"
    AUTORIZACIONES_RESOLVER = "autorizaciones.resolver"
    PIEZAS_INSPECCIONAR = "piezas.inspeccionar"
    PIEZAS_AJUSTAR_VIGENCIA = "piezas.ajustar_vigencia"
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

    # --- Sección 8.3 (los agregan las features o están pospuestos) ---
    REPORTES_VALOR_INVENTARIO = "reportes.valor_inventario"
    INVENTARIO_MINIMOS = "inventario.minimos"
    PIEZAS_DAR_DE_BAJA = "piezas.dar_de_baja"
    REVISION_VER = "revision.ver"


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


CATALOGO: tuple[Permiso, ...] = (
    Permiso(P.ACCESO_ADMINISTRAR, "Roles, permisos y usuarios", True),
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
    Permiso(P.TRASPASOS_OPERAR, "Enviar y recibir traspasos", True),
    Permiso(P.NO_ADEUDO_EMITIR, "Emitir el vale de no adeudo", True),
    Permiso(P.VALES_VER, "Consultar vales", True),
    Permiso(P.VALES_CANCELAR, "Cancelar los vales propios", True),
    Permiso(P.VALES_CANCELAR_TODOS, "Cancelar los vales de cualquiera", True),
    Permiso(P.AUTORIZACIONES_RESOLVER, "Autorizar o rechazar excedentes", True),
    Permiso(P.PIEZAS_INSPECCIONAR, "Inspeccionar y marcar No apta", True),
    Permiso(P.PIEZAS_AJUSTAR_VIGENCIA, "Ajustar la vigencia de una inspección", True),
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
    Permiso(P.REPORTES_VALOR_INVENTARIO, "Valor del inventario", False, "FEAT-002", True),
    Permiso(P.INVENTARIO_MINIMOS, "Fijar mínimos por almacén", False, "FEAT-004"),
    Permiso(P.PIEZAS_DAR_DE_BAJA, "Dar una pieza por perdida o de baja", False, "Pospuesto"),
    Permiso(P.REVISION_VER, "Lista de revisión", False, "Pospuesto"),
)

CLAVES: frozenset[str] = frozenset(p.clave for p in CATALOGO)
CLAVES_MVP: frozenset[str] = frozenset(p.clave for p in CATALOGO if p.mvp)

assert len(CLAVES) == len(CATALOGO), "Hay claves de permiso repetidas"


def es_clave_valida(clave: str) -> bool:
    return clave in CLAVES
