"""Registro único de códigos (RG-10)."""

import pytest
from sqlalchemy.orm import Session

from app.core.excepciones import DatosInvalidos
from app.core.ids import nuevo_id
from app.modulos.catalogo.codigos import CodigoRepetido, CodigoService
from app.modulos.catalogo.models import TipoCodigo


def test_RG_10_registrar_e_identificar(session: Session) -> None:
    servicio = CodigoService(session)
    ref = nuevo_id()
    servicio.registrar("  ALT-900 ", TipoCodigo.PIEZA, ref)

    encontrado = servicio.identificar("ALT-900")
    assert encontrado is not None
    assert encontrado.tipo == TipoCodigo.PIEZA
    assert encontrado.ref_id == ref


def test_RG_10_codigo_desconocido_devuelve_none(session: Session) -> None:
    assert CodigoService(session).identificar("NO-EXISTE-123") is None


def test_RG_10_registrar_dos_veces_lo_mismo_no_falla(session: Session) -> None:
    servicio = CodigoService(session)
    ref = nuevo_id()
    primero = servicio.registrar("TRB-900", TipoCodigo.TRABAJADOR, ref)
    segundo = servicio.registrar("TRB-900", TipoCodigo.TRABAJADOR, ref)
    assert primero.codigo == segundo.codigo
    assert len(servicio.codigos_de(TipoCodigo.TRABAJADOR, ref)) == 1


def test_RG_10_un_codigo_identifica_una_sola_cosa(session: Session) -> None:
    servicio = CodigoService(session)
    dueno = nuevo_id()
    servicio.registrar("DUP-900", TipoCodigo.ARTICULO, dueno)

    with pytest.raises(CodigoRepetido) as error:
        servicio.registrar("DUP-900", TipoCodigo.PIEZA, nuevo_id())

    assert error.value.codigo == "CODIGO_REPETIDO"
    assert error.value.detalles["tipo"] == "ARTICULO"
    assert error.value.detalles["ref_id"] == str(dueno)


def test_RG_10_un_trabajador_puede_tener_varios_codigos(session: Session) -> None:
    servicio = CodigoService(session)
    ref = nuevo_id()
    servicio.registrar("TRB-901", TipoCodigo.TRABAJADOR, ref)
    servicio.registrar("TRB-902", TipoCodigo.TRABAJADOR, ref)
    assert [c.codigo for c in servicio.codigos_de(TipoCodigo.TRABAJADOR, ref)] == [
        "TRB-901",
        "TRB-902",
    ]


def test_RG_10_codigo_vacio_se_rechaza(session: Session) -> None:
    with pytest.raises(DatosInvalidos):
        CodigoService(session).registrar("   ", TipoCodigo.PIEZA, nuevo_id())
