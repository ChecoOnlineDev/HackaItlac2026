"""Endpoints del módulo `catalogo`: categorías, artículos, puestos con su dotación y etiquetas.

La ficha de pieza (`GET /piezas/{id}`) y las inspecciones son de otros módulos. Los endpoints que
devuelven artículos usan `response_model_exclude_unset`: sin `catalogo.costos` el service no pone
`costo_unitario` y la clave no aparece en la respuesta (RG-12).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.paginacion import Pagina, PaginacionDep
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.catalogo.dependencies import CatalogoServiceDep, PuestoServiceDep
from app.modulos.catalogo.schemas import (
    ArticuloCreate,
    ArticuloFichaOut,
    ArticuloFilters,
    ArticuloListItem,
    ArticuloOut,
    ArticuloUpdate,
    CategoriaCreate,
    CategoriaFilters,
    CategoriaOut,
    CategoriaUpdate,
    DotacionIn,
    DotacionOut,
    EtiquetasOut,
    InactivacionIn,
    PuestoCreate,
    PuestoFilters,
    PuestoOut,
    PuestoUpdate,
    TipoEtiqueta,
)

router = APIRouter(tags=["catalogo"])

Ver = Annotated[Usuario, Depends(requiere_permiso(P.CATALOGO_VER))]
Administrar = Annotated[Usuario, Depends(requiere_permiso(P.CATALOGO_ADMINISTRAR))]
Imprimir = Annotated[Usuario, Depends(requiere_permiso(P.ETIQUETAS_IMPRIMIR))]


# ---------------------------------------------------------------------------- categorías


@router.get("/categorias", response_model=Pagina[CategoriaOut])
def listar_categorias(
    _: Ver,
    service: CatalogoServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[CategoriaFilters, Query()],
) -> Pagina[CategoriaOut]:
    """`catalogo.ver`. Lista de categorías con su plantilla."""
    return service.listar_categorias(filtros, pagina)


@router.post("/categorias", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    datos: CategoriaCreate, usuario: Administrar, service: CatalogoServiceDep
) -> CategoriaOut:
    """`catalogo.administrar`. Crea una categoría y su plantilla (CF-01, CF-02)."""
    return service.crear_categoria(datos, usuario)


@router.patch("/categorias/{categoria_id}", response_model=CategoriaOut)
def editar_categoria(
    categoria_id: uuid.UUID,
    datos: CategoriaUpdate,
    usuario: Administrar,
    service: CatalogoServiceDep,
) -> CategoriaOut:
    """`catalogo.administrar`. Edita la plantilla; no cambia los artículos que ya existen."""
    return service.actualizar_categoria(categoria_id, datos, usuario)


# ----------------------------------------------------------------------------- artículos


@router.get(
    "/articulos", response_model=Pagina[ArticuloListItem], response_model_exclude_unset=True
)
def listar_articulos(
    usuario: Ver,
    service: CatalogoServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[ArticuloFilters, Query()],
) -> Pagina[ArticuloListItem]:
    """`catalogo.ver`. Lista. Filtros: `q`, `categoria_id`, `activo`. Costo solo con su permiso."""
    return service.listar_articulos(filtros, pagina, usuario)


@router.post(
    "/articulos",
    response_model=ArticuloOut,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
)
def crear_articulo(
    datos: ArticuloCreate, usuario: Administrar, service: CatalogoServiceDep
) -> ArticuloOut:
    """`catalogo.administrar`. Crea un artículo con la plantilla de su categoría (CF-02).

    El costo solo se acepta con `catalogo.costos`.
    """
    return service.crear(datos, usuario)


@router.get(
    "/articulos/{articulo_id}", response_model=ArticuloFichaOut, response_model_exclude_unset=True
)
def ficha_articulo(
    articulo_id: uuid.UUID, usuario: Ver, service: CatalogoServiceDep
) -> ArticuloFichaOut:
    """`catalogo.ver`. Ficha: reglas, existencias por almacén y quién lo tiene (C-03)."""
    return service.ficha_articulo(articulo_id, usuario)


@router.patch(
    "/articulos/{articulo_id}", response_model=ArticuloOut, response_model_exclude_unset=True
)
def editar_articulo(
    articulo_id: uuid.UUID,
    datos: ArticuloUpdate,
    usuario: Administrar,
    service: CatalogoServiceDep,
) -> ArticuloOut:
    """`catalogo.administrar`. Edita datos y reglas. Con movimientos, 409 (CF-05)."""
    return service.actualizar_articulo(articulo_id, datos, usuario)


@router.post(
    "/articulos/{articulo_id}/inactivacion",
    response_model=ArticuloOut,
    response_model_exclude_unset=True,
)
def inactivar_articulo(
    articulo_id: uuid.UUID,
    datos: InactivacionIn,
    usuario: Administrar,
    service: CatalogoServiceDep,
) -> ArticuloOut:
    """`catalogo.administrar`. Inactiva con `{motivo}` (CF-10)."""
    return service.inactivar_articulo(articulo_id, datos.motivo, usuario)


@router.delete(
    "/articulos/{articulo_id}/inactivacion",
    response_model=ArticuloOut,
    response_model_exclude_unset=True,
)
def reactivar_articulo(
    articulo_id: uuid.UUID, usuario: Administrar, service: CatalogoServiceDep
) -> ArticuloOut:
    """`catalogo.administrar`. Reactiva el artículo con las reglas que tenía (CF-13)."""
    return service.reactivar_articulo(articulo_id, usuario)


@router.delete("/articulos/{articulo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_articulo(
    articulo_id: uuid.UUID, usuario: Administrar, service: CatalogoServiceDep
) -> Response:
    """`catalogo.administrar`. Elimina solo si no tiene movimientos (CF-12); si no, 409."""
    service.eliminar_articulo(articulo_id, usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------------- etiquetas


@router.get("/etiquetas", response_model=EtiquetasOut, response_model_exclude_none=True)
def listar_etiquetas(
    tipo: TipoEtiqueta, usuario: Imprimir, service: CatalogoServiceDep
) -> EtiquetasOut:
    """`etiquetas.imprimir` basta para los tres tipos. Lista de `{codigo, texto}` para imprimir."""
    return service.listar_etiquetas(tipo, usuario)


# -------------------------------------------------------------------------------- puestos


@router.get("/puestos", response_model=Pagina[PuestoOut])
def listar_puestos(
    _: Ver,
    service: PuestoServiceDep,
    pagina: PaginacionDep,
    filtros: Annotated[PuestoFilters, Query()],
) -> Pagina[PuestoOut]:
    """`catalogo.ver`. Puestos con el total de artículos de su dotación. Filtro: `activo`."""
    return service.listar(filtros, pagina)


@router.post("/puestos", response_model=PuestoOut, status_code=status.HTTP_201_CREATED)
def crear_puesto(datos: PuestoCreate, usuario: Administrar, service: PuestoServiceDep) -> PuestoOut:
    """`catalogo.administrar`. Crea un puesto; el nombre no se repite (409)."""
    return service.crear(datos, usuario)


@router.patch("/puestos/{puesto_id}", response_model=PuestoOut)
def editar_puesto(
    puesto_id: uuid.UUID, datos: PuestoUpdate, usuario: Administrar, service: PuestoServiceDep
) -> PuestoOut:
    """`catalogo.administrar`. Cambia el nombre o activa o inactiva el puesto."""
    return service.actualizar(puesto_id, datos, usuario)


@router.get("/puestos/{puesto_id}/dotacion", response_model=DotacionOut)
def ver_dotacion(puesto_id: uuid.UUID, _: Ver, service: PuestoServiceDep) -> DotacionOut:
    """`catalogo.ver`. La dotación recomendada del puesto (D-01) con el límite de cada artículo."""
    return service.dotacion(puesto_id)


@router.put("/puestos/{puesto_id}/dotacion", response_model=DotacionOut)
def reemplazar_dotacion(
    puesto_id: uuid.UUID, datos: DotacionIn, usuario: Administrar, service: PuestoServiceDep
) -> DotacionOut:
    """`catalogo.administrar`. Reemplaza la dotación; la cantidad no pasa del límite (D-04)."""
    return service.reemplazar_dotacion(puesto_id, datos, usuario)
