"""Mínimo disponible por artículo y almacén (FEAT-004, I-05)."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Minimo(Base):
    __tablename__ = "minimo"
    __table_args__ = (CheckConstraint("cantidad >= 0", name="cantidad_no_negativa"),)

    almacen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("almacen.id"), primary_key=True)
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulo.id"), primary_key=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
