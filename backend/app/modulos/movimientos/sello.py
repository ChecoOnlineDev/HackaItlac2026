"""F-06/F-07: contenido canónico y verificación de la cadena por almacén.

El estado de recepción/cancelación queda fuera del sello. Se firman identificadores y
contenido original; renombrar una categoría, proyecto o trabajador no reescribe vales.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from app.modulos.archivos.exceptions import AdjuntoNoEncontrado
from app.modulos.archivos.service import ArchivoService
from app.modulos.movimientos.repository_sello import SelloRepository

CERO = "0" * 64
CAMPOS_VALE = (
    "id",
    "id_cliente",
    "tipo",
    "folio",
    "almacen_id",
    "trabajador_id",
    "periodo_contrato_id",
    "proyecto_id",
    "destino_almacen_id",
    "vale_origen_id",
    "responsable_id",
    "autorizacion_id",
    "observacion",
    "firma_modo",
    "firma_adjunto_id",
    "token",
    "dispositivo",
    "creado_en",
    "hash_anterior",
    "sello_anterior_id",
)
CAMPOS_MOVIMIENTO = (
    "id",
    "vale_id",
    "renglon",
    "articulo_id",
    "pieza_id",
    "cantidad",
    "origen_id",
    "destino_id",
    "trabajador_id",
    "condicion",
    "motivo_baja",
    "nivel",
    "reglas",
    "observacion",
    "saldo_origen",
    "saldo_destino",
    "creado_en",
)


def normalizar(valor):
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, datetime):
        # DATETIME del esquema conserva segundos; el sello coincide antes/después del commit.
        return valor.replace(tzinfo=UTC).isoformat(timespec="seconds")
    return valor


def huella(vale, movimientos, firma_sha256):
    contenido = {
        "version": 1,
        "vale": {campo: normalizar(getattr(vale, campo)) for campo in CAMPOS_VALE},
        "movimientos": [
            {campo: normalizar(getattr(m, campo)) for campo in CAMPOS_MOVIMIENTO}
            for m in sorted(movimientos, key=lambda m: m.renglon)
        ],
        "firma_sha256": firma_sha256,
    }
    texto = json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class SelloService:
    def __init__(self, session):
        self.session = session
        self.repository = SelloRepository(session)
        self.archivos = ArchivoService(session)

    def _firma(self, vale):
        if vale.firma_adjunto_id is None:
            return None
        _, contenido = self.archivos.leer(vale.firma_adjunto_id)
        return hashlib.sha256(contenido).hexdigest()

    def sellar(self, vale, movimientos=None):
        """El motor llama una vez antes del commit, después de guardar renglones y firma."""
        if vale.hash is not None:
            raise ValueError("El vale ya tiene sello; no se reescribe.")
        cadena = self.repository.bloquear_cadena(vale.almacen_id)
        vale.sello_anterior_id = cadena.ultimo_vale_id
        vale.hash_anterior = cadena.ultimo_hash or CERO
        vale.hash = huella(
            vale,
            movimientos if movimientos is not None else self.repository.movimientos(vale.id),
            self._firma(vale),
        )
        cadena.ultimo_vale_id = vale.id
        cadena.ultimo_hash = vale.hash
        self.session.flush()

    def verificar_almacen(self, almacen_id):
        """Solo lee. Recorre los enlaces reales, incluso si se emitieron simultáneamente."""
        vales = self.repository.vales(almacen_id)
        sellados = {v.id: v for v in vales if v.hash is not None}
        ordenados = []
        visitados = set()
        cadena = self.repository.cadena(almacen_id)
        siguiente = cadena.ultimo_vale_id if cadena else None
        enlace_roto = bool(sellados) and cadena is None
        while siguiente is not None:
            if siguiente in visitados or siguiente not in sellados:
                enlace_roto = True
                break
            v = sellados[siguiente]
            visitados.add(v.id)
            ordenados.append(v)
            siguiente = v.sello_anterior_id
        ordenados.reverse()
        estados = {v.id: "Sin sello" for v in vales if v.hash is None}
        anterior = CERO
        anterior_id = None
        primer_alterado = None
        roto = enlace_roto or len(visitados) != len(sellados)
        for v in ordenados:
            try:
                calculado = huella(v, self.repository.movimientos(v.id), self._firma(v))
                coincide = calculado == v.hash
            except AdjuntoNoEncontrado:
                coincide = False
            coincide = (
                coincide and v.hash_anterior == anterior and v.sello_anterior_id == anterior_id
            )
            if not coincide:
                roto = True
                primer_alterado = primer_alterado or v
            estados[v.id] = "Alterado" if roto else "Íntegro"
            anterior, anterior_id = v.hash, v.id
        if cadena and cadena.ultimo_hash != anterior:
            roto = True
            if ordenados:
                primer_alterado = primer_alterado or ordenados[-1]
                estados[ordenados[-1].id] = "Alterado"
        for v in sellados.values():
            if v.id not in estados:
                estados[v.id] = "Alterado"
                primer_alterado = primer_alterado or v
        return {
            "regla": "F-06",
            "integro": not roto,
            "sellados": len(sellados),
            "sin_sello": len(vales) - len(sellados),
            "estados": estados,
            "primer_alterado": {"id": primer_alterado.id, "folio": primer_alterado.folio}
            if primer_alterado
            else None,
        }
