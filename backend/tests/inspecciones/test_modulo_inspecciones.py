"""Pruebas del módulo `inspecciones` (US-INS-001): P-01 a P-07, CF-06 y permisos."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.excepciones import DatosInvalidos, NoEncontrado
from app.core.tiempo import hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Categoria, EstadoPieza, Pieza
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.inspecciones import ResultadoInspeccion
from app.modulos.inspecciones.models import AjusteVigencia, EventoPieza, Inspeccion
from app.modulos.inspecciones.service import InspeccionService
from app.modulos.trabajadores.models import Trabajador

DIAS = 30
RUTA = "/api/piezas"


def _articulo(session, codigo: str, dias: int | None = DIAS, requiere: bool = True):
    categoria = session.scalar(select(Categoria).where(Categoria.nombre == "Equipo de alturas"))
    datos = ArticuloCreate(
        codigo=codigo,
        nombre="Arnés de prueba",
        categoria_id=categoria.id,
        requiere_inspeccion=requiere,
        vigencia_inspeccion_dias=dias,
    )
    return CatalogoService(session).crear_articulo(datos, actor_id=None)


@pytest.fixture
def pieza(session) -> Pieza:
    articulo = _articulo(session, f"ART-INS-{uuid.uuid4().hex[:8]}")
    pieza = CatalogoService(session).registrar_pieza(
        articulo.id, f"PZA-INS-{uuid.uuid4().hex[:8]}", f"S-{uuid.uuid4().hex[:8]}"
    )
    session.commit()
    return pieza


def _usuario(session, nombre: str) -> Usuario:
    return session.scalar(select(Usuario).where(Usuario.usuario == nombre))


def _inspeccionar(cliente, pieza, resultado="APTO", **extra):
    return cliente.post(f"{RUTA}/{pieza.id}/inspecciones", json={"resultado": resultado} | extra)


def _ajustar(cliente, pieza, fecha, motivo="Se revisó en campo"):
    return cliente.post(
        f"{RUTA}/{pieza.id}/ajuste-vigencia",
        json={"vigente_hasta": fecha.isoformat(), "motivo": motivo},
    )


# ------------------------------------------------------------------------ P-01


def test_P_01_inspeccion_apta_deja_la_pieza_apta_y_vigente(cliente_como, session, pieza):
    cliente = cliente_como("Almacenista")
    r = _inspeccionar(
        cliente, pieza, puntos={"etiquetas": True, "costuras": True}, observacion="Todo bien"
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    esperado = hoy_mx() + timedelta(days=DIAS)
    assert cuerpo["resultado"] == "APTO"
    assert cuerpo["fecha"] == hoy_mx().isoformat()
    assert cuerpo["vigente_hasta"] == esperado.isoformat()
    assert cuerpo["puntos"] == {"etiquetas": True, "costuras": True}
    assert cuerpo["pieza"] == {
        "id": str(pieza.id),
        "estado": "APTO",
        "inspeccion_vigente_hasta": esperado.isoformat(),
    }
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.APTO and pieza.inspeccion_vigente_hasta == esperado
    assert cuerpo["usuario_id"] == str(_usuario(session, "almacenista").id)


def test_P_01_la_inspeccion_que_vence_hoy_sigue_vigente_y_la_de_ayer_no(session, pieza):
    # Vigencia de 1 día registrada ayer: vence hoy (aún vale); registrada anteayer: ya no vale.
    articulo = _articulo(session, "ART-INS-1D", dias=1)
    servicio = InspeccionService(session)
    catalogo = CatalogoService(session)
    uno = catalogo.registrar_pieza(articulo.id, "PZA-INS-1D-A")
    dos = catalogo.registrar_pieza(articulo.id, "PZA-INS-1D-B")
    usuario = _usuario(session, "almacenista")
    servicio.registrar_inicial(
        uno.id,
        fecha=hoy_mx() - timedelta(days=1),
        resultado=ResultadoInspeccion.APTO,
        observacion=None,
        usuario_id=usuario.id,
    )
    servicio.registrar_inicial(
        dos.id,
        fecha=hoy_mx() - timedelta(days=2),
        resultado=ResultadoInspeccion.APTO,
        observacion=None,
        usuario_id=usuario.id,
    )
    assert uno.inspeccion_vigente_hasta == hoy_mx()
    assert uno.inspeccion_vigente_hasta >= hoy_mx()  # vence hoy: todavía es vigente
    assert dos.inspeccion_vigente_hasta == hoy_mx() - timedelta(days=1)
    assert dos.inspeccion_vigente_hasta < hoy_mx()  # venció ayer: ya no


def test_P_01_inspeccion_no_apta_sin_observacion_se_rechaza(cliente_como, session, pieza):
    cliente = cliente_como("Almacenista")
    for extra in ({}, {"observacion": ""}, {"observacion": "   "}):
        r = _inspeccionar(cliente, pieza, "NO_APTO", **extra)
        assert r.status_code == 422, r.text
        assert r.json()["codigo"] == "DATOS_INVALIDOS"
        assert r.json()["detalles"][0]["regla"] == "P-01"
    assert session.scalar(select(func.count()).select_from(Inspeccion)) == 0
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.APTO


def test_P_01_inspeccion_no_apta_deja_la_pieza_no_apta(cliente_como, session, pieza):
    cliente = cliente_como("Almacenista")
    assert _inspeccionar(cliente, pieza).status_code == 201
    vigencia = pieza.inspeccion_vigente_hasta
    r = _inspeccionar(cliente, pieza, "NO_APTO", observacion="Cinta rota")
    assert r.status_code == 201, r.text
    assert r.json()["vigente_hasta"] is None
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    assert pieza.inspeccion_vigente_hasta == vigencia  # solo una inspección Apta la cambia


def test_P_01_resultado_y_puntos_invalidos_se_rechazan(cliente_como, pieza):
    cliente = cliente_como("Almacenista")
    assert _inspeccionar(cliente, pieza, "TAL_VEZ").status_code == 422
    assert _inspeccionar(cliente, pieza, puntos={"tornillos": True}).status_code == 422


def test_P_01_inspeccionar_pieza_inexistente_da_404(cliente_como):
    cliente = cliente_como("Almacenista")
    r = cliente.post(f"{RUTA}/{uuid.uuid4()}/inspecciones", json={"resultado": "APTO"})
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_P_01_una_pieza_que_esta_con_un_trabajador_tambien_se_inspecciona(
    cliente_como, session, pieza
):
    trabajador = Trabajador(numero_empleado=f"E-{uuid.uuid4().hex[:8]}", nombre="Juan Pérez")
    session.add(trabajador)
    session.flush()
    pieza.ubicacion_id = AlmacenService(session).asegurar_ubicacion_de_trabajador(trabajador.id).id
    session.commit()
    ubicacion = pieza.ubicacion_id

    r = _inspeccionar(cliente_como("Almacenista"), pieza, "NO_APTO", observacion="Costura floja")
    assert r.status_code == 201, r.text
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    assert pieza.ubicacion_id == ubicacion  # la ubicación es de `movimientos`


def test_P_01_sin_vigencia_en_el_articulo_no_hay_vencimiento(cliente_como, session):
    articulo = _articulo(session, "ART-INS-SIN", dias=None, requiere=False)
    pieza = CatalogoService(session).registrar_pieza(articulo.id, "PZA-INS-SIN")
    r = _inspeccionar(cliente_como("Almacenista"), pieza)
    assert r.status_code == 201 and r.json()["vigente_hasta"] is None


def test_CF_06_una_pieza_de_articulo_que_no_requiere_inspeccion_tambien_se_inspecciona(
    cliente_como, session
):
    articulo = _articulo(session, "ART-INS-NOREQ", dias=10, requiere=False)
    pieza = CatalogoService(session).registrar_pieza(articulo.id, "PZA-INS-NOREQ")
    r = _inspeccionar(cliente_como("Almacenista"), pieza)
    assert r.status_code == 201
    assert r.json()["vigente_hasta"] == (hoy_mx() + timedelta(days=10)).isoformat()


def test_P_01_una_pieza_en_baja_no_se_inspecciona(cliente_como, session, pieza):
    CatalogoService(session).actualizar_estado_pieza(pieza.id, estado=EstadoPieza.BAJA)
    session.commit()
    r = _inspeccionar(cliente_como("Almacenista"), pieza)
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLICTO"


# ------------------------------------------------------------------------ P-03


def test_P_03_marcar_no_apta_exige_observacion_y_deja_evento(cliente_como, session, pieza):
    cliente = cliente_como("Almacenista")
    sin = cliente.post(f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": " "})
    assert sin.status_code == 422 and sin.json()["detalles"][0]["regla"] == "P-03"
    assert cliente.post(f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO"}).status_code == 422

    r = cliente.post(
        f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": "Golpe fuerte"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado_anterior"] == "APTO" and r.json()["pieza"]["estado"] == "NO_APTO"
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    evento = session.scalar(select(EventoPieza).where(EventoPieza.pieza_id == pieza.id))
    assert (evento.estado_anterior, evento.estado_nuevo) == ("APTO", "NO_APTO")
    assert evento.observacion == "Golpe fuerte"
    assert evento.usuario_id == _usuario(session, "almacenista").id


def test_P_03_solo_se_puede_marcar_no_apta_y_no_dos_veces(cliente_como, pieza):
    cliente = cliente_como("Almacenista")
    # Mantenimiento y calibración son de FEAT-004.
    r = cliente.post(
        f"{RUTA}/{pieza.id}/estado", json={"estado": "EN_MANTENIMIENTO", "observacion": "x"}
    )
    assert r.status_code == 422
    cuerpo = {"estado": "NO_APTO", "observacion": "Daño"}
    assert cliente.post(f"{RUTA}/{pieza.id}/estado", json=cuerpo).status_code == 200
    repetida = cliente.post(f"{RUTA}/{pieza.id}/estado", json=cuerpo)
    assert repetida.status_code == 409


def test_P_03_una_pieza_no_apta_solo_regresa_a_apta_con_una_inspeccion(
    cliente_como, session, pieza
):
    cliente = cliente_como("Almacenista")
    cliente.post(f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": "Daño"})
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    # Ningún otro camino la regresa: ni el ajuste de vigencia (P-07).
    assert _ajustar(cliente_como("Supervisor"), pieza, hoy_mx()).status_code == 409
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    assert _inspeccionar(cliente, pieza).status_code == 201
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.APTO


def test_P_03_marcar_pieza_inexistente_da_404(cliente_como):
    r = cliente_como("Almacenista").post(
        f"{RUTA}/{uuid.uuid4()}/estado", json={"estado": "NO_APTO", "observacion": "x"}
    )
    assert r.status_code == 404


# ------------------------------------------------------------------------ P-07


def _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza):
    assert _inspeccionar(cliente_como("Almacenista"), pieza).status_code == 201
    session.refresh(pieza)


def test_P_07_acortar_la_vigencia_se_permite_y_queda_en_el_ajuste(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    anterior = pieza.inspeccion_vigente_hasta
    nueva = hoy_mx() + timedelta(days=5)
    r = _ajustar(cliente_como("Supervisor"), pieza, nueva, "Se acerca una revisión")
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["vigente_hasta_anterior"] == anterior.isoformat()
    assert cuerpo["vigente_hasta_nuevo"] == nueva.isoformat()
    assert cuerpo["pieza"]["inspeccion_vigente_hasta"] == nueva.isoformat()
    session.refresh(pieza)
    assert pieza.inspeccion_vigente_hasta == nueva
    assert pieza.estado == EstadoPieza.APTO
    fila = session.scalar(select(AjusteVigencia).where(AjusteVigencia.pieza_id == pieza.id))
    inspeccion = session.scalar(select(Inspeccion).where(Inspeccion.pieza_id == pieza.id))
    assert fila.inspeccion_id == inspeccion.id
    assert fila.motivo == "Se acerca una revisión"
    assert fila.usuario_id == _usuario(session, "supervisor").id
    # La inspección original no cambia.
    assert inspeccion.vigente_hasta == anterior and inspeccion.resultado == "APTO"


def test_P_07_acortar_a_una_fecha_pasada_deja_la_inspeccion_vencida(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    ayer = hoy_mx() - timedelta(days=1)
    assert _ajustar(cliente_como("Supervisor"), pieza, ayer).status_code == 201
    session.refresh(pieza)
    assert pieza.inspeccion_vigente_hasta < hoy_mx()


def test_P_07_alargar_hasta_el_tope_se_permite_y_pasarse_se_rechaza(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    supervisor = cliente_como("Supervisor")
    tope = hoy_mx() + timedelta(days=DIAS)
    # Primero se acorta y luego se alarga hasta el tope exacto.
    assert _ajustar(supervisor, pieza, hoy_mx() + timedelta(days=2)).status_code == 201
    assert _ajustar(supervisor, pieza, tope).status_code == 201
    session.refresh(pieza)
    assert pieza.inspeccion_vigente_hasta == tope

    r = _ajustar(supervisor, pieza, tope + timedelta(days=1))
    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "VIGENCIA_EXCEDIDA"
    assert r.json()["detalles"][0]["regla"] == "P-07"
    session.refresh(pieza)
    assert pieza.inspeccion_vigente_hasta == tope
    assert session.scalar(select(func.count()).select_from(AjusteVigencia)) == 2


def test_P_07_el_tope_cuenta_desde_la_fecha_de_la_inspeccion_no_desde_hoy(cliente_como, session):
    articulo = _articulo(session, "ART-INS-TOPE", dias=10)
    pieza = CatalogoService(session).registrar_pieza(articulo.id, "PZA-INS-TOPE")
    usuario = _usuario(session, "almacenista")
    hace_5 = hoy_mx() - timedelta(days=5)
    InspeccionService(session).registrar_inicial(
        pieza.id,
        fecha=hace_5,
        resultado=ResultadoInspeccion.APTO,
        observacion=None,
        usuario_id=usuario.id,
    )
    session.commit()
    supervisor = cliente_como("Supervisor")
    tope = hace_5 + timedelta(days=10)
    assert _ajustar(supervisor, pieza, tope + timedelta(days=1)).status_code == 422
    assert _ajustar(supervisor, pieza, tope - timedelta(days=1)).status_code == 201


def test_P_07_el_motivo_es_obligatorio(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    supervisor = cliente_como("Supervisor")
    nueva = (hoy_mx() + timedelta(days=3)).isoformat()
    assert (
        supervisor.post(
            f"{RUTA}/{pieza.id}/ajuste-vigencia", json={"vigente_hasta": nueva}
        ).status_code
        == 422
    )
    for motivo in ("", "   "):
        r = supervisor.post(
            f"{RUTA}/{pieza.id}/ajuste-vigencia", json={"vigente_hasta": nueva, "motivo": motivo}
        )
        assert r.status_code == 422
    assert session.scalar(select(func.count()).select_from(AjusteVigencia)) == 0


def test_P_07_quien_registro_la_inspeccion_no_puede_ajustar_la_suya(cliente_como, session, pieza):
    supervisor = cliente_como("Supervisor")
    assert _inspeccionar(supervisor, pieza).status_code == 201
    r = _ajustar(supervisor, pieza, hoy_mx() + timedelta(days=3))
    assert r.status_code == 403 and r.json()["codigo"] == "AJUSTE_PROPIO"
    assert session.scalar(select(func.count()).select_from(AjusteVigencia)) == 0
    # Otro usuario con el permiso sí puede.
    assert (
        _ajustar(cliente_como("Administrador"), pieza, hoy_mx() + timedelta(days=3)).status_code
        == 201
    )


def test_P_07_no_regresa_a_apta_ni_cambia_el_resultado(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    cliente_como("Almacenista").post(
        f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": "Daño"}
    )
    r = _ajustar(cliente_como("Supervisor"), pieza, hoy_mx() + timedelta(days=3))
    assert r.status_code == 409 and r.json()["codigo"] == "AJUSTE_NO_PERMITIDO"
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO


def test_P_07_sin_inspeccion_no_hay_nada_que_ajustar(cliente_como, session, pieza):
    supervisor = cliente_como("Supervisor")
    r = _ajustar(supervisor, pieza, hoy_mx())
    assert r.status_code == 409 and r.json()["codigo"] == "AJUSTE_NO_PERMITIDO"


def test_P_07_misma_fecha_o_pieza_inexistente(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    supervisor = cliente_como("Supervisor")
    igual = _ajustar(supervisor, pieza, pieza.inspeccion_vigente_hasta)
    assert igual.status_code == 422
    r = supervisor.post(
        f"{RUTA}/{uuid.uuid4()}/ajuste-vigencia",
        json={"vigente_hasta": hoy_mx().isoformat(), "motivo": "x"},
    )
    assert r.status_code == 404


def test_P_07_el_ajuste_es_atomico_si_falla_no_queda_nada(session, pieza, monkeypatch):
    almacenista = _usuario(session, "almacenista")
    servicio = InspeccionService(session)
    servicio.registrar_inicial(
        pieza.id,
        fecha=hoy_mx(),
        resultado=ResultadoInspeccion.APTO,
        observacion=None,
        usuario_id=almacenista.id,
    )
    session.commit()
    vigencia = pieza.inspeccion_vigente_hasta

    def falla(*_, **__):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(servicio.auditoria, "registrar", falla)
    from app.modulos.inspecciones.schemas import AjusteVigenciaIn

    with pytest.raises(RuntimeError):
        servicio.ajustar_vigencia(
            pieza.id,
            AjusteVigenciaIn(vigente_hasta=hoy_mx() + timedelta(days=1), motivo="Prueba"),
            _usuario(session, "supervisor"),
        )
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(AjusteVigencia)) == 0
    assert session.get(Pieza, pieza.id).inspeccion_vigente_hasta == vigencia


# --------------------------------------------------------------------- permisos


def test_P_01_permisos_de_inspeccionar_y_marcar_no_apta(cliente_como, crear_usuario, app, pieza):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    sin = crear_usuario({P.CATALOGO_VER})
    con = crear_usuario({P.PIEZAS_INSPECCIONAR})
    cuerpo_estado = {"estado": "NO_APTO", "observacion": "Daño"}
    with TestClient(app) as c:
        iniciar_sesion_en(c, sin)
        assert (
            c.post(f"{RUTA}/{pieza.id}/inspecciones", json={"resultado": "APTO"}).status_code == 403
        )
        assert c.post(f"{RUTA}/{pieza.id}/estado", json=cuerpo_estado).status_code == 403
    with TestClient(app) as c:
        iniciar_sesion_en(c, con)
        assert (
            c.post(f"{RUTA}/{pieza.id}/inspecciones", json={"resultado": "APTO"}).status_code == 201
        )
        assert c.post(f"{RUTA}/{pieza.id}/estado", json=cuerpo_estado).status_code == 200
    # Sin sesión.
    with TestClient(app) as anonimo:
        r = anonimo.post(f"{RUTA}/{pieza.id}/inspecciones", json={"resultado": "APTO"})
        assert r.status_code == 401


def test_P_07_solo_supervisor_y_administrador_ajustan_la_vigencia(
    cliente_como, session, pieza, crear_usuario, app
):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    fecha = hoy_mx() + timedelta(days=3)
    for rol in ("Almacenista", "Compras", "Recursos Humanos"):
        assert _ajustar(cliente_como(rol), pieza, fecha).status_code == 403, rol
    # Un rol con inspeccionar pero sin ajustar tampoco.
    solo_inspecciona = crear_usuario({P.PIEZAS_INSPECCIONAR})
    with TestClient(app) as c:
        iniciar_sesion_en(c, solo_inspecciona)
        assert _ajustar(c, pieza, fecha).status_code == 403
    assert _ajustar(cliente_como("Supervisor"), pieza, fecha).status_code == 201
    assert (
        _ajustar(cliente_como("Administrador"), pieza, fecha - timedelta(days=1)).status_code == 201
    )


# --------------------------------------------------------- registrar_inicial (I-03)


def test_P_01_registrar_inicial_apta_fija_estado_y_vigencia_sin_commit(session):
    articulo = _articulo(session, "ART-INS-INI")
    pieza = CatalogoService(session).registrar_pieza(articulo.id, "PZA-INS-INI")
    usuario = _usuario(session, "almacenista")
    fecha = hoy_mx() - timedelta(days=3)
    inspeccion = InspeccionService(session).registrar_inicial(
        pieza.id,
        fecha=fecha,
        resultado=ResultadoInspeccion.APTO,
        observacion="  Nueva de fábrica  ",
        usuario_id=usuario.id,
    )
    assert isinstance(inspeccion, Inspeccion) and inspeccion.id is not None
    assert inspeccion.fecha == fecha
    assert inspeccion.vigente_hasta == fecha + timedelta(days=DIAS)
    assert inspeccion.observacion == "Nueva de fábrica"
    assert pieza.estado == EstadoPieza.APTO
    assert pieza.inspeccion_vigente_hasta == fecha + timedelta(days=DIAS)


def test_P_01_registrar_inicial_no_apta_exige_observacion(session):
    articulo = _articulo(session, "ART-INS-INI2")
    pieza = CatalogoService(session).registrar_pieza(articulo.id, "PZA-INS-INI2")
    usuario = _usuario(session, "almacenista")
    servicio = InspeccionService(session)
    with pytest.raises(DatosInvalidos):
        servicio.registrar_inicial(
            pieza.id,
            fecha=hoy_mx(),
            resultado=ResultadoInspeccion.NO_APTO,
            observacion=None,
            usuario_id=usuario.id,
        )
    assert pieza.estado == EstadoPieza.APTO
    servicio.registrar_inicial(
        pieza.id,
        fecha=hoy_mx(),
        resultado=ResultadoInspeccion.NO_APTO,
        observacion="Llegó dañada",
        usuario_id=usuario.id,
    )
    assert pieza.estado == EstadoPieza.NO_APTO


def test_P_01_registrar_inicial_con_pieza_inexistente_da_no_encontrado(session):
    with pytest.raises(NoEncontrado):
        InspeccionService(session).registrar_inicial(
            uuid.uuid4(),
            fecha=hoy_mx(),
            resultado=ResultadoInspeccion.APTO,
            observacion=None,
            usuario_id=_usuario(session, "almacenista").id,
        )


# ---------------------------------------------------------------- historial y auditoría


def test_P_01_historial_completo_y_ordenado_del_mas_reciente_al_mas_antiguo(
    cliente_como, session, pieza
):
    almacenista = cliente_como("Almacenista")
    assert _inspeccionar(almacenista, pieza, observacion="Primera").status_code == 201
    almacenista.post(f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": "Daño"})
    assert _inspeccionar(almacenista, pieza, observacion="Reparada").status_code == 201
    assert (
        _ajustar(cliente_como("Supervisor"), pieza, hoy_mx() + timedelta(days=4)).status_code == 201
    )

    historial = InspeccionService(session).historial_de_pieza(pieza.id)
    assert [h.tipo for h in historial] == ["AJUSTE_VIGENCIA", "INSPECCION", "ESTADO", "INSPECCION"]
    fechas = [h.fecha for h in historial]
    assert fechas == sorted(fechas, reverse=True)
    ajuste, reparada, estado, primera = historial
    assert ajuste.motivo == "Se revisó en campo"
    assert ajuste.usuario == _usuario(session, "supervisor").nombre
    assert ajuste.vigente_hasta_anterior is not None
    assert reparada.observacion == "Reparada" and primera.observacion == "Primera"
    assert (estado.estado_anterior, estado.estado_nuevo) == ("APTO", "NO_APTO")
    assert all(h.usuario_id for h in historial)


def test_P_01_historial_de_pieza_inexistente_da_no_encontrado(session):
    with pytest.raises(NoEncontrado):
        InspeccionService(session).historial_de_pieza(uuid.uuid4())


def test_P_01_historial_de_pieza_sin_cambios_esta_vacio(session, pieza):
    assert InspeccionService(session).historial_de_pieza(pieza.id) == []


def test_P_07_todo_cambio_queda_en_la_auditoria(cliente_como, session, pieza):
    _pieza_inspeccionada_por_almacenista(cliente_como, session, pieza)
    cliente_como("Almacenista").post(
        f"{RUTA}/{pieza.id}/estado", json={"estado": "NO_APTO", "observacion": "Daño"}
    )
    _inspeccionar(cliente_como("Almacenista"), pieza)
    _ajustar(cliente_como("Supervisor"), pieza, hoy_mx() + timedelta(days=2), "Por obra")

    acciones = {
        a.accion: a
        for a in session.scalars(select(Auditoria).where(Auditoria.entidad != "sesion"))
        if a.accion.startswith(("inspeccion.", "pieza."))
    }
    assert {"inspeccion.registrar", "pieza.marcar_no_apta", "pieza.ajustar_vigencia"} <= set(
        acciones
    )
    ajuste = acciones["pieza.ajustar_vigencia"]
    assert ajuste.usuario_id == _usuario(session, "supervisor").id
    assert ajuste.despues["motivo"] == "Por obra"
    # Y el cambio de la pieza también lo audita el catálogo.
    assert session.scalar(
        select(func.count())
        .select_from(Auditoria)
        .where(Auditoria.accion == "pieza.actualizar", Auditoria.entidad_id == str(pieza.id))
    )


def test_P_01_si_falla_la_inspeccion_no_queda_nada(session, pieza, monkeypatch):
    servicio = InspeccionService(session)

    def falla(*_, **__):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(servicio.auditoria, "registrar", falla)
    from app.modulos.inspecciones.schemas import InspeccionCreate

    with pytest.raises(RuntimeError):
        servicio.registrar(
            pieza.id, InspeccionCreate(resultado="APTO"), _usuario(session, "almacenista")
        )
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(Inspeccion)) == 0
    assert session.get(Pieza, pieza.id).inspeccion_vigente_hasta is None
