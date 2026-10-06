"""Registro explícito de TODOS los modelos, para Alembic y las pruebas.

Quien agregue un `models.py` nuevo lo importa aquí.
"""

from app.modulos.acceso import models as _acceso
from app.modulos.almacenes import models as _almacenes
from app.modulos.archivos import models as _archivos
from app.modulos.auditoria import models as _auditoria
from app.modulos.autorizaciones import models as _autorizaciones
from app.modulos.catalogo import models as _catalogo
from app.modulos.inspecciones import models as _inspecciones
from app.modulos.movimientos import models as _movimientos
from app.modulos.solicitudes_compra import models as _solicitudes_compra
from app.modulos.trabajadores import models as _trabajadores

MODELOS = (
    _acceso,
    _almacenes,
    _archivos,
    _auditoria,
    _autorizaciones,
    _catalogo,
    _inspecciones,
    _movimientos,
    _solicitudes_compra,
    _trabajadores,
)
