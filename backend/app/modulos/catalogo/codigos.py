"""Registro único de códigos escaneables (RG-10): trabajador, artículo, pieza o vale.

Es el único lugar que escribe en la tabla `codigo`. Los demás módulos (trabajadores, movimientos,
importación) registran e identifican códigos llamando a `CodigoService`.
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import violacion
from app.core.excepciones import Conflicto, DatosInvalidos
from app.modulos.catalogo.models import Codigo, TipoCodigo


class CodigoRepetido(Conflicto):
    """El código ya identifica otra cosa. `detalles` dice de qué tipo y de quién es."""

    codigo = "CODIGO_REPETIDO"
    mensaje_defecto = "Ese código ya está en uso."


def normalizar(codigo: str) -> str:
    """Quita espacios de los extremos. No cambia mayúsculas: la base compara sin distinguirlas."""
    limpio = (codigo or "").strip()
    if not limpio:
        raise DatosInvalidos("Captura un código.", {"campo": "codigo"})
    return limpio


class CodigoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def obtener(self, codigo: str) -> Codigo | None:
        return self.session.get(Codigo, codigo)

    def de(self, tipo: TipoCodigo, ref_id: uuid.UUID) -> list[Codigo]:
        consulta = select(Codigo).where(Codigo.tipo == tipo, Codigo.ref_id == ref_id)
        return list(self.session.scalars(consulta.order_by(Codigo.codigo)))

    def ultimo_numero_con_prefijo(self, prefijo: str) -> int:
        """El consecutivo más alto de los códigos `PREFIJO-NNNN` que ya existen (0 si no hay)."""
        patron = re.compile(rf"^{re.escape(prefijo)}-(\d+)$", re.IGNORECASE)
        mayor = 0
        consulta = select(Codigo.codigo).where(Codigo.codigo.like(f"{prefijo}-%"))
        for codigo in self.session.scalars(consulta):
            encontrado = patron.match(codigo)
            if encontrado:
                mayor = max(mayor, int(encontrado.group(1)))
        return mayor

    def agregar(self, codigo: str, tipo: TipoCodigo, ref_id: uuid.UUID) -> Codigo:
        fila = Codigo(codigo=codigo, tipo=tipo, ref_id=ref_id)
        self.session.add(fila)
        self.session.flush()
        return fila


class CodigoService:
    """Registra e identifica códigos. No hace commit: lo hace el service que lo invoca."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CodigoRepository(session)

    def identificar(self, codigo: str) -> Codigo | None:
        """Qué cosa identifica el código, o `None` si no existe (DESCONOCIDO)."""
        return self.repository.obtener(normalizar(codigo))

    def siguiente_con_prefijo(self, prefijo: str) -> str:
        """El siguiente `PREFIJO-NNNN` libre (mismo formato que la importación en modo Alta).
        El llamador bloquea antes la categoría para que dos altas no reciban el mismo."""
        numero = self.repository.ultimo_numero_con_prefijo(prefijo) + 1
        return f"{prefijo}-{numero:04d}"

    def codigos_de(self, tipo: TipoCodigo, ref_id: uuid.UUID) -> list[Codigo]:
        return self.repository.de(tipo, ref_id)

    def registrar(self, codigo: str, tipo: TipoCodigo, ref_id: uuid.UUID) -> Codigo:
        """Liga `codigo` a una cosa. Repetirlo para la misma cosa no hace nada; si ya es de otra
        cosa, lanza `CodigoRepetido` con su tipo y su id para que el llamador diga de quién es."""
        codigo = normalizar(codigo)
        existente = self.repository.obtener(codigo)
        if existente is not None:
            return self._mismo_o_repetido(existente, tipo, ref_id)
        try:
            with self.session.begin_nested():
                return self.repository.agregar(codigo, tipo, ref_id)
        except DBAPIError as exc:
            # Otra transacción lo registró entre la consulta y el insert.
            if violacion(exc).errno != 1062:
                raise
            existente = self.repository.obtener(codigo)
            if existente is None:
                raise
            return self._mismo_o_repetido(existente, tipo, ref_id)

    @staticmethod
    def _mismo_o_repetido(existente: Codigo, tipo: TipoCodigo, ref_id: uuid.UUID) -> Codigo:
        if existente.tipo == tipo and existente.ref_id == ref_id:
            return existente
        raise CodigoRepetido(
            f"El código {existente.codigo} ya identifica a otra cosa.",
            {"codigo": existente.codigo, "tipo": existente.tipo, "ref_id": str(existente.ref_id)},
        )
