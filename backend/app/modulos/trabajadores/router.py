"""Endpoints del modulo `trabajadores`: alta, periodos, codigos, foto y baja de trabajadores.

PENDIENTE: lo llena el agente del modulo. Cada endpoint declara
su permiso con `Depends(requiere_permiso(P.XXX))`. Este router ya esta montado en
`app/main.py` bajo `/api`; no hace falta tocar `main.py`.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/trabajadores", tags=["trabajadores"])
