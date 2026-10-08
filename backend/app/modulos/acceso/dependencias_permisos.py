"""Qué permisos de ver exige cada permiso de acción (FEAT-006: «un permiso de acción incluye el
de ver su módulo»). El servidor no deja guardar un rol que activa uno sin los que necesita; la
interfaz usa el mismo mapa (`requiere` en `GET /api/permisos`) para activarlos juntos.

El catálogo de claves vive en `permisos.py`; aquí solo se relacionan.
"""

from app.modulos.acceso.permisos import P

REQUIERE: dict[str, tuple[str, ...]] = {
    P.TRABAJADORES_VER_DATOS_PERSONALES: (P.TRABAJADORES_VER,),
    P.TRABAJADORES_ADMINISTRAR: (P.TRABAJADORES_VER,),
    P.TRABAJADORES_INICIAR_BAJA: (P.TRABAJADORES_VER,),
    P.TRABAJADORES_NUMERO_EXTERNO: (P.TRABAJADORES_ADMINISTRAR,),
    P.ALMACENES_ADMINISTRAR: (P.INVENTARIO_VER,),
    P.TABLERO_VER: (P.INVENTARIO_VER,),
    P.CATALOGO_ADMINISTRAR: (P.CATALOGO_VER,),
    P.CATALOGO_COSTOS: (P.CATALOGO_VER,),
    # FEAT-011 (AC-30). Cambiar límites se hace editando artículos y categorías.
    P.CATALOGO_LIMITES: (P.CATALOGO_ADMINISTRAR,),
    P.BITACORA_VER: (P.INVENTARIO_VER,),
    P.RESGUARDO_VER: (P.TRABAJADORES_VER, P.INVENTARIO_VER),
    P.INVENTARIO_IMPORTAR: (P.INVENTARIO_VER, P.CATALOGO_VER),
    P.PIEZAS_MARCAR_ESTADO: (P.CATALOGO_VER, P.INVENTARIO_VER),
    P.INVENTARIO_ENTRADAS: (P.INVENTARIO_VER,),
    P.ENTREGAS_CREAR: (P.TRABAJADORES_VER, P.CATALOGO_VER, P.INVENTARIO_VER),
    P.DEVOLUCIONES_CREAR: (P.TRABAJADORES_VER, P.INVENTARIO_VER),
    P.TRASPASOS_OPERAR: (P.INVENTARIO_VER,),
    P.TRASPASOS_RECIBIR: (P.INVENTARIO_VER,),
    P.PIEZAS_REGISTRAR_SERIE: (P.INVENTARIO_VER,),
    P.NO_ADEUDO_EMITIR: (P.TRABAJADORES_VER,),
    P.VALES_CANCELAR: (P.VALES_VER,),
    P.VALES_CANCELAR_TODOS: (P.VALES_VER,),
    P.PIEZAS_AJUSTAR_VIGENCIA: (P.PIEZAS_INSPECCIONAR,),
    # Pedir una compra permite buscar el artículo; atenderla, ver el artículo y el vale de entrada.
    P.COMPRAS_SOLICITAR: (P.CATALOGO_VER,),
    P.COMPRAS_ATENDER: (P.CATALOGO_VER, P.VALES_VER),
}


def faltantes(claves: set[str]) -> dict[str, list[str]]:
    """Por cada permiso de `claves` al que le falta alguno que necesita: los que faltan."""
    return {
        c: sorted(set(REQUIERE.get(c, ())) - claves)
        for c in sorted(claves)
        if set(REQUIERE.get(c, ())) - claves
    }
