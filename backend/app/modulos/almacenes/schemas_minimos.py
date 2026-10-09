import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MinimoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    articulo_id: uuid.UUID
    cantidad: int | None = Field(default=None, ge=0, le=100000, strict=True)


class MinimosIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimos: list[MinimoIn] = Field(max_length=500)

    @model_validator(mode="after")
    def sin_repetidos(self):
        if len({m.articulo_id for m in self.minimos}) != len(self.minimos):
            raise ValueError("Cada artículo se configura una sola vez.")
        return self


class MinimoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    articulo_id: uuid.UUID
    cantidad: int
