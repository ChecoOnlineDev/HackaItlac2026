"""Endpoints del módulo `movimientos`: vales, traspasos por recibir y no adeudo.

Router delgado: cada endpoint declara su permiso y delega en `MovimientoService`.

`POST /vales/evaluar` y `POST /vales` exigen un permiso que depende del tipo de vale
(`entregas.crear`, `inventario.entradas`, ...; api-contracts, "Permiso y campos propios"). Esa
tabla vive en los tipos (`ManejadorTipo.permiso`) y el service la aplica por clave antes de tocar
nada (`exigir_permiso_del_tipo`); aquí basta con tener sesión.

Los endpoints de traspasos por recibir, no adeudo y cancelación delegan en su tipo: mientras el
tipo sea un stub responden 501 `TIPO_NO_IMPLEMENTADO` (con permiso) o 403 (sin él).
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Response, status

from app.core.paginacion import Pagina, PaginacionDep
from app.db import SesionDep
from app.modulos.acceso.dependencies import UsuarioActual, requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.schemas import (
    CancelacionIn,
    ConfirmarIn,
    EvaluacionOut,
    EvaluarIn,
    NoAdeudoIn,
    ValeConfirmadoOut,
    ValeDetalleOut,
    ValeFilters,
    ValeListItem,
)
from app.modulos.movimientos.schemas_cancelacion import CancelacionOut
from app.modulos.movimientos.service import MovimientoService

router = APIRouter(tags=["movimientos"])


def get_service(session: SesionDep) -> MovimientoService:
    return MovimientoService(session)


ServiceDep = Annotated[MovimientoService, Depends(get_service)]
UsuarioVer = Annotated[Usuario, Depends(requiere_permiso(P.VALES_VER))]
UsuarioRecibir = Annotated[Usuario, Depends(requiere_permiso(P.TRASPASOS_RECIBIR))]
UsuarioNoAdeudo = Annotated[Usuario, Depends(requiere_permiso(P.NO_ADEUDO_EMITIR))]
UsuarioCancelar = Annotated[Usuario, Depends(requiere_permiso(P.VALES_CANCELAR))]


@router.post("/vales/evaluar", response_model=EvaluacionOut)
def evaluar(cuerpo: EvaluarIn, usuario: UsuarioActual, service: ServiceDep) -> EvaluacionOut:
    """Permiso según el tipo. Evalúa el borrador sin escribir nada (E-28): nivel y motivos por
    renglón, cada uno con el ID de su regla."""
    return service.evaluar(usuario, cuerpo)


@router.post("/vales", response_model=ValeConfirmadoOut, status_code=status.HTTP_201_CREATED)
def confirmar(
    cuerpo: ConfirmarIn,
    usuario: UsuarioActual,
    service: ServiceDep,
    respuesta: Response,
    user_agent: Annotated[str | None, Header()] = None,
) -> ValeConfirmadoOut:
    """Permiso según el tipo. Confirma el vale en una sola transacción. 201 con el vale nuevo;
    200 si el `id_cliente` ya existía (un doble toque nunca crea dos vales); 409 `VALE_CAMBIO`
    si la evaluación ya no es la misma."""
    vale, creado = service.confirmar(usuario, cuerpo, dispositivo=user_agent)
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return vale


@router.get("/vales/por-token/{token}", response_model=ValeDetalleOut)
def ver_por_token(token: str, usuario: UsuarioVer, service: ServiceDep) -> ValeDetalleOut:
    """`vales.ver`. El vale que abre su QR."""
    return service.obtener_por_token(usuario, token)


@router.get("/vales/{vale_id}", response_model=ValeDetalleOut)
def ver(vale_id: uuid.UUID, usuario: UsuarioVer, service: ServiceDep) -> ValeDetalleOut:
    """`vales.ver`. Detalle con renglones; sin costos (F-12)."""
    return service.obtener(usuario, vale_id)


@router.get("/vales/{vale_id}/firma")
def ver_firma(vale_id: uuid.UUID, usuario: UsuarioVer, service: ServiceDep) -> Response:
    """`vales.ver`. La imagen de la firma del trabajador (detalle e impresión del vale)."""
    mime, contenido = service.firma_de(usuario, vale_id)
    return Response(
        content=contenido,
        media_type=mime,
        headers={"Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/vales", response_model=Pagina[ValeListItem])
def listar(
    usuario: UsuarioVer,
    service: ServiceDep,
    pagina: PaginacionDep,
    tipo: TipoVale | None = None,
    almacen_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    trabajador_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
) -> Pagina[ValeListItem]:
    """`vales.ver`. Lista paginada; sin `almacenes.todos`, solo los del almacén asignado (AC-06)."""
    filtros = ValeFilters(
        tipo=tipo,
        almacen_id=almacen_id,
        desde=desde,
        hasta=hasta,
        trabajador_id=trabajador_id,
        usuario_id=usuario_id,
    )
    return service.listar(usuario, filtros, pagina)


@router.get("/traspasos/por-recibir", response_model=None)
def traspasos_por_recibir(
    usuario: UsuarioRecibir,
    service: ServiceDep,
    solo_contar: bool = False,
    almacen_id: uuid.UUID | None = None,
) -> Any:
    """`traspasos.recibir`. Traspasos en tránsito hacia el almacén de la sesión (tipo RECEPCION).
    `solo_contar=true` responde solo `{total}` (contador del inicio); `almacen_id` solo lo usa
    quien tiene `almacenes.todos`."""
    return service.traspasos_por_recibir(usuario, solo_contar=solo_contar, almacen_id=almacen_id)


@router.post(
    "/trabajadores/{trabajador_id}/no-adeudo",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
def emitir_no_adeudo(
    trabajador_id: uuid.UUID,
    datos: NoAdeudoIn,
    usuario: UsuarioNoAdeudo,
    service: ServiceDep,
    respuesta: Response,
) -> Any:
    """`no_adeudo.emitir`. Emite el vale de no adeudo (B-04); 409 `CON_PENDIENTES` si los hay.
    201 con el vale nuevo; 200 si el `id_cliente` ya existía."""
    salida = service.emitir_no_adeudo(usuario, trabajador_id, datos)
    if getattr(salida, "repetido", False):
        respuesta.status_code = status.HTTP_200_OK
    return salida


@router.post(
    "/vales/{vale_id}/cancelacion",
    response_model=CancelacionOut,
    status_code=status.HTTP_201_CREATED,
)
def cancelar(
    vale_id: uuid.UUID,
    datos: CancelacionIn,
    usuario: UsuarioCancelar,
    service: ServiceDep,
    respuesta: Response,
) -> CancelacionOut:
    """`vales.cancelar` (los propios) o `vales.cancelar_todos`. Cancela con movimientos inversos
    (K-01 a K-05): 201 con la cancelación; 200 si el `id_cliente` ya existía; 409 `NO_CANCELABLE`
    si no procede. Con `rehacer`, trae el `borrador` del vale cancelado."""
    cancelacion = service.cancelar(usuario, vale_id, datos)
    if not cancelacion.creado:
        respuesta.status_code = status.HTTP_200_OK
    return cancelacion
