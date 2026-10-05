"""Reglas puras de la cancelación (sin base de datos): K-03, K-04, X-14."""

from app.modulos.movimientos.models import EstadoVale, Nivel, TipoVale
from app.modulos.movimientos.tipos.cancelacion_reglas import (
    HechosExistenciaCancelacion,
    HechosPiezaCancelacion,
    regla_k03_existencia,
    regla_k03_pieza,
    regla_k03_ya_cancelado,
    regla_k04_tipo,
    regla_x14_traspaso,
)


def test_K_04_solo_recepcion_no_adeudo_y_cancelacion_no_se_cancelan():
    for tipo in (TipoVale.RECEPCION, TipoVale.NO_ADEUDO, TipoVale.CANCELACION):
        motivo = regla_k04_tipo(tipo)
        assert motivo is not None and motivo.regla == "K-04" and motivo.nivel == Nivel.ROJO
    for tipo in (TipoVale.ENTRADA, TipoVale.ENTREGA, TipoVale.DEVOLUCION, TipoVale.TRASPASO):
        assert regla_k04_tipo(tipo) is None


def test_K_03_un_vale_cancelado_se_rechaza_con_el_folio_de_su_cancelacion():
    assert regla_k03_ya_cancelado(EstadoVale.EMITIDO, None) is None
    motivo = regla_k03_ya_cancelado(EstadoVale.CANCELADO, "KEP-CAN-000003")
    assert motivo.regla == "K-03" and "KEP-CAN-000003" in motivo.mensaje


def test_X_14_un_traspaso_solo_se_cancela_en_transito():
    assert regla_x14_traspaso(TipoVale.TRASPASO, EstadoVale.EN_TRANSITO) is None
    assert regla_x14_traspaso(TipoVale.ENTREGA, EstadoVale.EMITIDO) is None
    for estado in (EstadoVale.RECIBIDO, EstadoVale.RECIBIDO_CON_DIFERENCIAS):
        motivo = regla_x14_traspaso(TipoVale.TRASPASO, estado)
        assert motivo.regla == "X-14" and "recibió" in motivo.mensaje


def test_K_03_pieza_en_su_destino_y_sin_movimientos_posteriores_se_cancela():
    ok = HechosPiezaCancelacion("P-1", True, False, "la tiene Ana")
    assert regla_k03_pieza(ok) is None
    movida = HechosPiezaCancelacion("P-1", False, False, "está en el almacén KEP")
    assert "ya se movió después" in regla_k03_pieza(movida).mensaje
    de_vuelta = HechosPiezaCancelacion("P-1", True, True, "la tiene Ana")
    assert "tuvo otros movimientos" in regla_k03_pieza(de_vuelta).mensaje


def test_K_03_la_existencia_debe_alcanzar_para_revertir():
    assert regla_k03_existencia(HechosExistenciaCancelacion("Guantes", "KEP", 3, 3)) is None
    motivo = regla_k03_existencia(HechosExistenciaCancelacion("Guantes", "el almacén KEP", 5, 2))
    assert (
        motivo.regla == "K-03" and "se necesitan 5" in motivo.mensaje and "hay 2" in motivo.mensaje
    )
