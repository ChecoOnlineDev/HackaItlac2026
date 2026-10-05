"""Paginación de listas: `pagina` y `tamano`; responde `{elementos, total}`."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel

TAMANO_MAXIMO = 200


@dataclass(frozen=True)
class Paginacion:
    pagina: int
    tamano: int

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamano

    @property
    def limit(self) -> int:
        return self.tamano


def parametros_pagina(
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=TAMANO_MAXIMO)] = 50,
) -> Paginacion:
    return Paginacion(pagina=pagina, tamano=tamano)


PaginacionDep = Annotated[Paginacion, Depends(parametros_pagina)]


class Pagina[T](BaseModel):
    """Respuesta de toda lista: `{elementos, total}`."""

    elementos: list[T]
    total: int
