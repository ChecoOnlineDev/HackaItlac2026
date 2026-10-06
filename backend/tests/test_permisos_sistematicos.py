"""Prueba sistemática de permisos sobre TODAS las rutas de la API (AC-01 a AC-07, RG-12, RG-13).

Descubre las rutas de la aplicación y comprueba:

  (a) sin sesión toda ruta responde 401, salvo las públicas (`POST /api/sesion`, `GET /api/salud`
      y la documentación de la API);
  (b) por introspección de las dependencias, toda ruta protegida declara un permiso por clave
      (`requiere_permiso`) o está en la lista explícita de las que solo piden sesión; y lo que
      declara el código coincide con la columna «Permiso» de `docs/architecture/api-contracts.md`;
  (c) la matriz de la sección 8.2 de las reglas: los roles iniciales tienen exactamente sus
      permisos, y para una muestra de endpoints de cada permiso se responde distinto de 403 con él
      y 403 sin él (con un rol de UN solo permiso, con ninguno y con todos menos ese);
  (d) los datos reservados no se envían sin su permiso de información (CURP y NSS; costos), y un
      vale nunca muestra costos, ni siquiera a Compras;
  (e) la cookie de sesión: HttpOnly, SameSite=Lax y Secure con `COOKIE_SEGURA=true`.
"""

import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.modulos.acceso.permisos import CLAVES, CLAVES_MVP, P
from tests.ayudas_guion import (
    COSTOS_DE_PRUEBA,
    FIRMA,
    alta_trabajador,
    confirmar,
    entregar,
    ids_de_almacen,
)
from tests.conftest import iniciar_sesion_en
from tests.importacion.ayudas import COLUMNAS, fila
from tests.movimientos.ayudas_traspasos import cliente_almacen  # noqa: F401  (fixture)

UUID_FALSO = "00000000-0000-7000-8000-000000000000"
RAIZ = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------ descubrimiento de rutas


def _rutas_de(contenedor, prefijo: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Las `APIRoute` de la app, también las de routers incluidos (FastAPI las envuelve)."""
    for ruta in contenedor.routes:
        if type(ruta).__name__ == "_IncludedRouter":
            yield from _rutas_de(
                ruta.original_router, prefijo + (ruta.include_context.prefix or "")
            )
        elif isinstance(ruta, APIRoute):
            yield prefijo + ruta.path, ruta


def _dependencias(dependant) -> Iterator:
    for d in dependant.dependencies:
        yield d
        yield from _dependencias(d)


def _claves_de_permiso(ruta: APIRoute) -> set[str]:
    """Las claves de `requiere_permiso(...)` de la ruta (viven en el cierre de la dependencia)."""
    claves = set()
    for d in _dependencias(ruta.dependant):
        for celda in getattr(d.call, "__closure__", None) or ():
            if isinstance(celda.cell_contents, str) and celda.cell_contents in CLAVES:
                claves.add(celda.cell_contents)
    return claves


def _pide_sesion(ruta: APIRoute) -> bool:
    return any(
        getattr(d.call, "__name__", "") == "usuario_actual" for d in _dependencias(ruta.dependant)
    )


def _metodos(ruta: APIRoute) -> list[str]:
    return sorted(ruta.methods - {"HEAD", "OPTIONS"})


APP = create_app()
RUTAS: list[tuple[str, str, APIRoute]] = [
    (metodo, camino, ruta) for camino, ruta in _rutas_de(APP) for metodo in _metodos(ruta)
]

# Públicas por diseño: entrar con usuario y contraseña, renovar la sesión (la identifica el token
# de renovación, no el de acceso, que para entonces ya pudo vencer) y comprobar que la aplicación
# vive.
PUBLICAS = {("POST", "/api/sesion"), ("POST", "/api/sesion/refresh"), ("GET", "/api/salud")}
# Rutas del propio framework (documentación interactiva): públicas, sin datos del negocio.
PUBLICAS_DEL_FRAMEWORK = {
    "/api/docs",
    "/api/openapi.json",
    "/docs/oauth2-redirect",
    "/api/redoc",
}

# Rutas que piden SOLO sesión (api-contracts: «Sesión»). Cada una explica por qué no lleva un
# permiso fijo en la dependencia.
SOLO_SESION: dict[tuple[str, str], str] = {
    ("GET", "/api/sesion"): "Devuelve la sesión y los permisos del propio usuario.",
    ("DELETE", "/api/sesion"): "Cierra la sesión propia, solo la de este dispositivo.",
    (
        "DELETE",
        "/api/sesion/todas",
    ): "Cierra todas las sesiones propias, en todos los dispositivos.",
    ("DELETE", "/api/sesion/otras"): "Cierra las sesiones propias de los demás dispositivos.",
    (
        "GET",
        "/api/sesion/dispositivos",
    ): "Lista los dispositivos con sesión abierta del propio usuario.",
    ("GET", "/api/escaneo/{codigo}"): (
        "Identifica un código; el servicio devuelve solo lo que el usuario puede ver "
        "(lo demás llega como DESCONOCIDO)."
    ),
    (
        "GET",
        "/api/busqueda",
    ): "Cada grupo llega vacío si falta su permiso (trabajadores, catálogo).",
    ("GET", "/api/autorizaciones/{autorizacion_id}"): (
        "La ve quien la pidió o quien puede resolver en su almacén; el servicio lo verifica."
    ),
    ("POST", "/api/autorizaciones/{autorizacion_id}/resolucion"): (
        "Resuelve con la sesión o con el PIN de otro usuario: el servicio exige "
        "`autorizaciones.resolver` sobre quien autoriza."
    ),
    ("POST", "/api/vales/evaluar"): (
        "El permiso depende del `tipo` del cuerpo (entregas.crear, devoluciones.crear, ...): "
        "el servicio lo verifica por clave antes de leer nada."
    ),
    ("POST", "/api/vales"): "Igual que evaluar: el permiso sale del `tipo` del vale.",
}


def _url(camino: str) -> str:
    return re.sub(r"\{codigo\}|\{token\}", "NO-EXISTE", re.sub(r"\{[^}]+\}", UUID_FALSO, camino))


def _id(metodo: str, camino: str) -> str:
    return f"{metodo} {camino}"


# ===================================================================== (a) sin sesión: 401


def test_se_descubren_todas_las_rutas_de_la_api():
    # 65 rutas de negocio al construir esta prueba; si crece, la prueba las cubre sola. El piso
    # evita que un cambio en el descubrimiento deje la prueba vacía sin que nadie lo note.
    assert len(RUTAS) >= 60
    de_openapi = {
        (m.upper(), camino) for camino, ops in APP.openapi()["paths"].items() for m in ops
    }
    assert {(m, c) for m, c, _ in RUTAS} == de_openapi
    assert all(c.startswith("/api/") for _, c, _ in RUTAS)


@pytest.mark.parametrize(
    "metodo,camino",
    [(m, c) for m, c, _ in RUTAS if (m, c) not in PUBLICAS],
    ids=lambda v: str(v),
)
def test_AC_04_sin_sesion_toda_ruta_protegida_responde_401(client, metodo, camino):
    cuerpo = {} if metodo in ("POST", "PUT", "PATCH") else None
    r = client.request(metodo, _url(camino), json=cuerpo)
    assert r.status_code == 401, f"{metodo} {camino}: {r.status_code} {r.text}"
    assert r.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize("cookie", ["", "basura", "a.b.c", "x" * 400])
def test_AC_04_una_cookie_falsa_o_manipulada_es_401(client, cookie):
    client.cookies.set(get_settings().cookie_nombre, cookie)
    for ruta in ("/api/sesion", "/api/trabajadores", "/api/vales"):
        r = client.get(ruta)
        assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO", ruta


def test_AC_04_un_token_de_otro_usuario_inactivo_deja_de_servir(client, crear_usuario, session):
    from app.modulos.acceso.models import Usuario

    usuario = crear_usuario({P.TRABAJADORES_VER}, almacen="KEP")
    assert iniciar_sesion_en(client, usuario).status_code == 200
    assert client.get("/api/trabajadores").status_code == 200
    from sqlalchemy import update

    session.execute(update(Usuario).where(Usuario.usuario == usuario.usuario).values(activo=False))
    # El rol, el estado y los permisos se leen en CADA petición (AC-10).
    assert client.get("/api/trabajadores").status_code == 401


def test_las_publicas_son_solo_las_documentadas(client):
    assert client.get("/api/salud").status_code == 200
    r = client.post("/api/sesion", json={"usuario": "nadie", "contrasena": "x"})
    assert r.status_code == 401  # público, pero rechaza credenciales malas
    r = client.post("/api/sesion/refresh")
    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"  # público, sin token
    for ruta in PUBLICAS_DEL_FRAMEWORK:
        assert any(getattr(r, "path", None) == ruta for r in APP.routes), ruta


# ================================================== (b) cada ruta declara su permiso


@pytest.mark.parametrize("metodo,camino,ruta", RUTAS, ids=lambda v: v if isinstance(v, str) else "")
def test_AC_01_cada_ruta_declara_un_permiso_por_clave_o_esta_en_la_lista_de_solo_sesion(
    metodo, camino, ruta
):
    claves = _claves_de_permiso(ruta)
    if (metodo, camino) in PUBLICAS:
        assert not claves and not _pide_sesion(ruta)
    elif (metodo, camino) in SOLO_SESION:
        assert _pide_sesion(ruta), "debe pedir al menos la sesión"
        assert not claves, "ya no es «solo sesión»: quítala de SOLO_SESION"
    else:
        assert _pide_sesion(ruta), f"{metodo} {camino} no exige sesión"
        assert len(claves) == 1, f"{metodo} {camino} debe exigir UN permiso por clave: {claves}"
        assert claves <= CLAVES


def test_AC_01_la_lista_de_solo_sesion_no_tiene_rutas_que_ya_no_existen():
    existentes = {(m, c) for m, c, _ in RUTAS}
    assert set(SOLO_SESION) <= existentes
    assert PUBLICAS <= existentes


def test_AC_04_ninguna_ruta_compara_el_nombre_del_rol():
    """El servidor verifica permisos, nunca el nombre del rol (AC-04): no hay `rol.nombre ==`."""
    patron = re.compile(r"(rol\.nombre|\.rol\.nombre|nombre_rol)\s*(==|!=|in\b)")
    culpables = []
    for archivo in (RAIZ / "backend" / "app").rglob("*.py"):
        if "datos_prueba" in archivo.name:
            continue
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if patron.search(linea):
                culpables.append(f"{archivo.relative_to(RAIZ)}:{numero}: {linea.strip()}")
    assert culpables == []


def _contrato() -> dict[tuple[str, str], str]:
    """Las filas `METODO /ruta | permiso` de las tablas de api-contracts.md (sin «Previsto»)."""
    texto = (RAIZ / "docs/architecture/api-contracts.md").read_text(encoding="utf-8")
    texto = texto.split("## Previsto por la segunda ola")[0]
    filas: dict[tuple[str, str], str] = {}
    for linea in texto.splitlines():
        if not linea.startswith("| `"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) < 2:
            continue
        permiso = celdas[1].strip("` ")
        for metodo, camino in re.findall(
            r"`(GET|POST|PATCH|PUT|DELETE) (/api/[^`\s?]+)", celdas[0]
        ):
            filas[(metodo, re.sub(r"\{[^}]+\}", "{}", camino))] = permiso
    return filas


def test_AC_01_los_permisos_del_codigo_coinciden_con_el_contrato_de_api():
    contrato = _contrato()
    codigo: dict[tuple[str, str], str] = {}
    for metodo, camino, ruta in RUTAS:
        llave = (metodo, re.sub(r"\{[^}]+\}", "{}", camino))
        claves = _claves_de_permiso(ruta)
        codigo[llave] = (
            "Público"
            if (metodo, camino) in PUBLICAS
            else next(iter(claves))
            if claves
            else "Sesión"
        )
    sin_documentar = sorted(set(codigo) - set(contrato) - {("GET", "/api/salud")})
    sin_codigo = sorted(set(contrato) - set(codigo))
    # La columna dice «Según el tipo» para vales; en el código ese permiso sale del tipo. La
    # resolución de una autorización la documenta con `autorizaciones.resolver`, pero lo exige el
    # servicio sobre quien autoriza (la sesión o el PIN de otro usuario): se comprueba por
    # comportamiento en `test_guion_pdf.py` y en los tests de `autorizaciones`.
    verificadas_en_el_servicio = {("POST", "/api/autorizaciones/{}/resolucion")}
    distintos = {
        k: (contrato[k], codigo[k])
        for k in set(contrato) & set(codigo)
        if contrato[k] != codigo[k]
        and not (contrato[k] == "Según el tipo" and codigo[k] == "Sesión")
        and k not in verificadas_en_el_servicio
    }
    assert sin_documentar == [], f"rutas sin documentar en api-contracts.md: {sin_documentar}"
    assert sin_codigo == [], f"rutas documentadas que no existen: {sin_codigo}"
    assert distintos == {}, f"permiso distinto entre contrato y código: {distintos}"


# ================================================== (c) matriz de la sección 8.2

# Sección 8.2 de las reglas de negocio: roles iniciales por permiso. A Almacenista, S Supervisor,
# C Compras, R Recursos Humanos. El Administrador tiene todos.
ROLES_8_2: dict[str, str] = {
    P.ACCESO_ADMINISTRAR: "",
    P.TRABAJADORES_VER: "ASR",
    P.TRABAJADORES_VER_DATOS_PERSONALES: "R",
    P.TRABAJADORES_ADMINISTRAR: "R",
    P.TRABAJADORES_INICIAR_BAJA: "ASR",
    P.CATALOGO_VER: "ASC",
    P.CATALOGO_ADMINISTRAR: "SC",
    P.CATALOGO_COSTOS: "C",
    P.INVENTARIO_VER: "ASC",
    P.INVENTARIO_ENTRADAS: "C",
    P.ENTREGAS_CREAR: "AS",
    P.DEVOLUCIONES_CREAR: "AS",
    P.TRASPASOS_OPERAR: "S",
    P.NO_ADEUDO_EMITIR: "AS",
    P.VALES_VER: "ASC",
    P.VALES_CANCELAR: "ASC",
    P.VALES_CANCELAR_TODOS: "S",
    P.AUTORIZACIONES_RESOLVER: "S",
    P.PIEZAS_INSPECCIONAR: "AS",
    P.PIEZAS_AJUSTAR_VIGENCIA: "S",
    P.REPORTES_EXISTENCIAS: "SC",
    P.REPORTES_MOVIMIENTOS: "SC",
    P.REPORTES_ADEUDOS: "SR",
    P.REPORTES_CONSUMO: "SC",
    P.ALMACENES_TODOS: "",
    P.ALMACENES_ASIGNAR_PERSONAL: "S",
    P.ETIQUETAS_IMPRIMIR: "SCR",
}
LETRA_DE_ROL = {
    "Almacenista": "A",
    "Supervisor": "S",
    "Compras": "C",
    "Recursos Humanos": "R",
    "Administrador": "*",
}
assert set(ROLES_8_2) == CLAVES_MVP, "la tabla de 8.2 debe cubrir los permisos del MVP"

# Muestra de endpoints por permiso: (método, ruta, cuerpo, permisos extra que el endpoint pide
# además por sus propias reglas). Todos son inofensivos: ids falsos o cuerpos vacíos. El «sin el
# permiso» de la prueba de roles es 403; el «con él» solo cuenta si el rol trae también los extras.
MUESTRAS: dict[str, list[tuple[str, str, dict | None, set[str]]]] = {
    P.ACCESO_ADMINISTRAR: [
        ("GET", "/api/roles", None, set()),
        ("GET", "/api/usuarios", None, set()),
        ("GET", "/api/permisos", None, set()),
        ("GET", f"/api/roles/{UUID_FALSO}", None, set()),
        ("POST", "/api/roles", {}, set()),
        ("PATCH", f"/api/roles/{UUID_FALSO}", {"descripcion": "x"}, set()),
        ("PUT", f"/api/roles/{UUID_FALSO}/permisos", {"permisos": []}, set()),
        ("DELETE", f"/api/roles/{UUID_FALSO}", None, set()),
    ],
    P.TRABAJADORES_VER: [
        ("GET", "/api/trabajadores", None, set()),
        ("GET", f"/api/trabajadores/{UUID_FALSO}/dotacion", None, set()),
    ],
    P.TRABAJADORES_ADMINISTRAR: [
        ("GET", "/api/trabajadores/puestos", None, set()),
        ("POST", "/api/trabajadores", {}, set()),
        ("POST", f"/api/trabajadores/{UUID_FALSO}/periodos", {}, set()),
        ("DELETE", f"/api/trabajadores/{UUID_FALSO}/baja", None, set()),
    ],
    P.TRABAJADORES_INICIAR_BAJA: [("POST", f"/api/trabajadores/{UUID_FALSO}/baja", None, set())],
    P.CATALOGO_VER: [
        ("GET", "/api/categorias", None, set()),
        ("GET", "/api/articulos", None, set()),
        ("GET", f"/api/piezas/{UUID_FALSO}", None, set()),
        ("GET", "/api/puestos", None, set()),
        ("GET", f"/api/puestos/{UUID_FALSO}/dotacion", None, set()),
    ],
    P.CATALOGO_ADMINISTRAR: [
        ("POST", "/api/categorias", {}, set()),
        ("POST", "/api/articulos", {}, set()),
        ("DELETE", f"/api/articulos/{UUID_FALSO}", None, set()),
        ("POST", "/api/puestos", {}, set()),
        ("PATCH", f"/api/puestos/{UUID_FALSO}", {}, set()),
        ("PUT", f"/api/puestos/{UUID_FALSO}/dotacion", {"renglones": []}, set()),
    ],
    P.INVENTARIO_VER: [
        ("GET", "/api/almacenes", None, set()),
        ("GET", f"/api/almacenes/{UUID_FALSO}/existencias", None, set()),
    ],
    P.INVENTARIO_ENTRADAS: [
        ("POST", "/api/importacion/vista-previa", {}, set()),
        ("POST", "/api/importacion", {}, set()),
        ("POST", "/api/vales/evaluar", {"tipo": "ENTRADA", "renglones": []}, set()),
    ],
    P.ENTREGAS_CREAR: [
        ("POST", "/api/autorizaciones", {}, set()),
        (
            "POST",
            "/api/vales/evaluar",
            {"tipo": "ENTREGA", "trabajador_id": UUID_FALSO, "renglones": []},
            set(),
        ),
    ],
    P.DEVOLUCIONES_CREAR: [
        ("POST", "/api/vales/evaluar", {"tipo": "DEVOLUCION", "renglones": []}, set())
    ],
    P.TRASPASOS_OPERAR: [
        ("GET", "/api/traspasos/por-recibir", None, set()),
        (
            "POST",
            "/api/vales/evaluar",
            {"tipo": "TRASPASO", "destino_almacen_id": UUID_FALSO, "renglones": []},
            set(),
        ),
        (
            "POST",
            "/api/vales/evaluar",
            {"tipo": "RECEPCION", "vale_origen_id": UUID_FALSO, "renglones": []},
            set(),
        ),
    ],
    P.NO_ADEUDO_EMITIR: [
        ("POST", f"/api/trabajadores/{UUID_FALSO}/no-adeudo", {"id_cliente": UUID_FALSO}, set()),
        ("POST", "/api/vales/evaluar", {"tipo": "NO_ADEUDO", "trabajador_id": UUID_FALSO}, set()),
    ],
    P.VALES_VER: [
        ("GET", "/api/vales", None, set()),
        ("GET", f"/api/vales/{UUID_FALSO}", None, set()),
        ("GET", "/api/vales/por-token/NO-EXISTE", None, set()),
        ("GET", f"/api/vales/{UUID_FALSO}/firma", None, set()),
    ],
    P.VALES_CANCELAR: [
        (
            "POST",
            f"/api/vales/{UUID_FALSO}/cancelacion",
            {"motivo": "prueba", "id_cliente": UUID_FALSO},
            set(),
        ),
        (
            "POST",
            "/api/vales/evaluar",
            {"tipo": "CANCELACION", "vale_origen_id": UUID_FALSO},
            set(),
        ),
    ],
    P.AUTORIZACIONES_RESOLVER: [("GET", "/api/autorizaciones", None, set())],
    P.PIEZAS_INSPECCIONAR: [
        ("POST", f"/api/piezas/{UUID_FALSO}/inspecciones", {"resultado": "APTO"}, set()),
        (
            "POST",
            f"/api/piezas/{UUID_FALSO}/estado",
            {"estado": "NO_APTO", "observacion": "x"},
            set(),
        ),
    ],
    P.PIEZAS_AJUSTAR_VIGENCIA: [
        (
            "POST",
            f"/api/piezas/{UUID_FALSO}/ajuste-vigencia",
            {"vigente_hasta": "2030-01-01", "motivo": "x"},
            set(),
        ),
    ],
    P.REPORTES_EXISTENCIAS: [("GET", "/api/reportes/existencias", None, set())],
    P.REPORTES_MOVIMIENTOS: [
        ("GET", "/api/reportes/movimientos", None, set()),
        ("GET", "/api/reportes/usuarios", None, set()),
    ],
    P.REPORTES_ADEUDOS: [("GET", "/api/reportes/adeudos", None, set())],
    P.REPORTES_CONSUMO: [("GET", "/api/reportes/consumo", None, set())],
    P.ALMACENES_ASIGNAR_PERSONAL: [
        ("GET", "/api/personal", None, set()),
        ("PATCH", f"/api/usuarios/{UUID_FALSO}/almacen", {"almacen_id": None}, set()),
    ],
    # Basta `etiquetas.imprimir` para los tres tipos (api-contracts, Etiquetas).
    P.ETIQUETAS_IMPRIMIR: [
        ("GET", "/api/etiquetas?tipo=credenciales", None, set()),
        ("GET", "/api/etiquetas?tipo=estantes", None, set()),
        ("GET", "/api/etiquetas?tipo=piezas", None, set()),
    ],
}
# Permisos del catálogo sin endpoint propio que devuelva 403 (se prueban por comportamiento):
# `trabajadores.ver_datos_personales` y `catalogo.costos` (datos reservados, sección d),
# `vales.cancelar_todos` y `almacenes.todos` (alcance, más abajo).
SIN_MUESTRA = {
    P.TRABAJADORES_VER_DATOS_PERSONALES,
    P.CATALOGO_COSTOS,
    P.VALES_CANCELAR_TODOS,
    P.ALMACENES_TODOS,
}


def test_8_2_la_tabla_de_muestras_cubre_todos_los_permisos_con_endpoint():
    assert set(MUESTRAS) | SIN_MUESTRA == CLAVES_MVP


def _llamar(cliente: TestClient, metodo: str, ruta: str, cuerpo):
    return cliente.request(
        metodo, ruta, json=cuerpo if metodo in ("POST", "PUT", "PATCH") else None
    )


def _cliente_de(app, usuario) -> TestClient:
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    return cliente


@pytest.mark.parametrize("rol", list(LETRA_DE_ROL))
def test_8_2_los_roles_iniciales_tienen_exactamente_sus_permisos(cliente_como, rol):
    permisos = set(cliente_como(rol).get("/api/sesion").json()["permisos"])
    letra = LETRA_DE_ROL[rol]
    if letra == "*":
        esperado = set(CLAVES)  # el Administrador tiene todos los del catálogo
    else:
        esperado = {p for p, roles in ROLES_8_2.items() if letra in roles}
    assert permisos == esperado, (
        f"{rol}: de más {sorted(permisos - esperado)}, de menos {sorted(esperado - permisos)}"
    )


@pytest.mark.parametrize("rol", list(LETRA_DE_ROL))
def test_8_2_cada_rol_inicial_recibe_403_justo_en_los_endpoints_que_no_son_suyos(cliente_como, rol):
    cliente = cliente_como(rol)
    letra = LETRA_DE_ROL[rol]
    del_rol = set(cliente.get("/api/sesion").json()["permisos"])
    fallas = []
    probados = 0
    for permiso, muestras in MUESTRAS.items():
        tiene = letra == "*" or letra in ROLES_8_2[permiso]
        for metodo, ruta, cuerpo, extra in muestras:
            r = _llamar(cliente, metodo, ruta, cuerpo)
            probados += 1
            if tiene and extra <= del_rol and r.status_code in (401, 403):
                fallas.append(f"{rol} CON {permiso}: {metodo} {ruta} -> {r.status_code}")
            if not (tiene and extra <= del_rol) and r.status_code != 403:
                fallas.append(f"{rol} SIN {permiso}: {metodo} {ruta} -> {r.status_code}")
            if r.status_code == 403:
                assert r.json()["codigo"] == "SIN_PERMISO"
    assert probados >= 40
    assert fallas == []


@pytest.mark.parametrize("permiso", sorted(MUESTRAS))
def test_AC_01_con_el_permiso_responde_distinto_de_403_y_sin_el_responde_403(
    app, crear_usuario, permiso
):
    muestras = MUESTRAS[permiso]
    extra = set().union(*(m[3] for m in muestras))
    solo = crear_usuario({permiso} | extra, almacen="KEP")
    ninguno = crear_usuario(set(), almacen="KEP")
    todos_menos = crear_usuario(
        (
            set(CLAVES)
            - {permiso}
            - ({P.ALMACENES_TODOS} if permiso == P.ALMACENES_TODOS else set())
        ),
        almacen=None if P.ALMACENES_TODOS in CLAVES - {permiso} else "KEP",
    )
    c_solo, c_ninguno, c_menos = (_cliente_de(app, u) for u in (solo, ninguno, todos_menos))
    for metodo, ruta, cuerpo, _ in muestras:
        con = _llamar(c_solo, metodo, ruta, cuerpo)
        assert con.status_code not in (401, 403), f"CON {permiso}: {metodo} {ruta} {con.text}"
        for quien, cliente in (("ninguno", c_ninguno), ("todos menos él", c_menos)):
            sin = _llamar(cliente, metodo, ruta, cuerpo)
            assert sin.status_code == 403, (
                f"SIN {permiso} ({quien}): {metodo} {ruta} {sin.status_code}"
            )
            assert sin.json()["codigo"] == "SIN_PERMISO"
    for c in (c_solo, c_ninguno, c_menos):
        c.close()


def test_AC_01_las_rutas_solo_sesion_no_dan_403_a_quien_no_tiene_ningun_permiso(app, crear_usuario):
    """Quien entró puede consultar su sesión, escanear y buscar (ve «nada», no recibe 403)."""
    cliente = _cliente_de(app, crear_usuario(set(), almacen="KEP"))
    assert cliente.get("/api/sesion").json()["permisos"] == []
    r = cliente.get("/api/escaneo/EMP-1001")
    assert r.status_code == 200 and r.json()["tipo"] == "DESCONOCIDO" and r.json()["id"] is None
    busqueda = cliente.get("/api/busqueda", params={"q": "guante"}).json()
    assert busqueda["sin_resultados"] is True and busqueda["articulos"]["elementos"] == []
    assert busqueda["trabajadores"]["elementos"] == [] and busqueda["piezas"]["elementos"] == []
    assert cliente.delete("/api/sesion").status_code == 204


@pytest.mark.parametrize(
    "tipo,permiso",
    [
        ("ENTRADA", P.INVENTARIO_ENTRADAS),
        ("ENTREGA", P.ENTREGAS_CREAR),
        ("DEVOLUCION", P.DEVOLUCIONES_CREAR),
        ("TRASPASO", P.TRASPASOS_OPERAR),
        ("RECEPCION", P.TRASPASOS_OPERAR),
        ("NO_ADEUDO", P.NO_ADEUDO_EMITIR),
        ("CANCELACION", P.VALES_CANCELAR),
    ],
)
def test_AC_04_el_permiso_de_un_vale_se_verifica_por_clave_segun_su_tipo(
    app, crear_usuario, tipo, permiso
):
    cuerpo = {"tipo": tipo, "id_cliente": UUID_FALSO, "renglones": [], "firma": FIRMA}
    todos_los_demas = set(CLAVES_MVP) - {permiso, P.ALMACENES_TODOS}
    sin = _cliente_de(app, crear_usuario(todos_los_demas, almacen="KEP"))
    for ruta in ("/api/vales/evaluar", "/api/vales"):
        r = sin.post(ruta, json=cuerpo)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO", (tipo, ruta, r.text)
    con = _cliente_de(app, crear_usuario({permiso}, almacen="KEP"))
    for ruta in ("/api/vales/evaluar", "/api/vales"):
        assert con.post(ruta, json=cuerpo).status_code != 403, (tipo, ruta)


# ----------------------------------------- permisos que se prueban por su efecto (alcance)


def test_AC_06_almacenes_todos_decide_si_se_ven_los_movimientos_de_todos_los_almacenes(
    app, crear_usuario
):
    solo_el_suyo = _cliente_de(app, crear_usuario({P.REPORTES_MOVIMIENTOS}, almacen="MID"))
    con_todos = _cliente_de(
        app, crear_usuario({P.REPORTES_MOVIMIENTOS, P.ALMACENES_TODOS}, almacen=None)
    )
    sin_almacen = _cliente_de(app, crear_usuario({P.REPORTES_MOVIMIENTOS}, almacen=None))
    # Los datos de prueba son entradas de Kepler y Contratistas: Midrex no tiene movimientos.
    assert solo_el_suyo.get("/api/reportes/movimientos").json()["elementos"] == []
    assert sin_almacen.get("/api/reportes/movimientos").json()["elementos"] == []
    visto = con_todos.get("/api/reportes/movimientos", params={"tamano": 100}).json()
    assert visto["total"] > 0
    # Pedir otro almacén no da error: simplemente no devuelve nada (AC-06).
    r = solo_el_suyo.get("/api/reportes/movimientos", params={"almacen_id": UUID_FALSO})
    assert r.status_code == 200 and r.json()["elementos"] == []


def test_AC_07_vales_cancelar_es_solo_de_los_propios_y_cancelar_todos_de_cualquiera(
    app, cliente_como, crear_usuario, session
):
    rh, kep = cliente_como("Recursos Humanos"), cliente_como("Almacenista")
    trabajador = alta_trabajador(rh)
    propios = {P.VALES_CANCELAR, P.VALES_VER, P.ENTREGAS_CREAR, P.TRABAJADORES_VER, P.CATALOGO_VER}
    de_otro = _cliente_de(app, crear_usuario(propios, almacen="KEP"))
    de_todos = _cliente_de(app, crear_usuario(propios | {P.VALES_CANCELAR_TODOS}, almacen="KEP"))
    cuerpo = {"motivo": "prueba de permisos", "id_cliente": str(uuid.uuid4())}
    vale = entregar(kep, trabajador["id"], [{"codigo": "LENTE-CL"}])
    r = de_otro.post(f"/api/vales/{vale['id']}/cancelacion", json=cuerpo)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert kep.get(f"/api/vales/{vale['id']}").json()["estado"] == "EMITIDO"
    r = de_todos.post(f"/api/vales/{vale['id']}/cancelacion", json=cuerpo)
    assert r.status_code == 201, r.text
    assert kep.get(f"/api/vales/{vale['id']}").json()["estado"] == "CANCELADO"


# ============================================ (d) datos reservados: CURP, NSS y costos

CURP = "ZZZZ900101HCLRTN09"
NSS = "98765432109"


def _sin_mapa_de_columnas(texto: str) -> str:
    """Quita `"columnas": {...,"costo": 7,...}` de la importación: es el mapa de columnas de la
    tabla (qué columna es cada dato), no un costo."""
    return re.sub(r'"columnas"\s*:\s*\{[^}]*\}', '"columnas":{}', texto)


def _hay_clave(texto: str, *claves: str) -> bool:
    return any(re.search(rf'"{c}"\s*:', texto, re.IGNORECASE) for c in claves)


def _aparece_costo(texto: str) -> list[str]:
    hallados = [
        v for v in COSTOS_DE_PRUEBA if re.search(rf"(?<![\d.]){re.escape(v)}(?![\d])", texto)
    ]
    return hallados + (["clave costo*"] if _hay_clave(texto, r"costo\w*") else [])


def test_el_detector_de_datos_reservados_si_detecta_lo_que_busca():
    """Prueba de la prueba: si el detector no viera un costo, las de abajo pasarían en vano."""
    assert _aparece_costo('{"costo_unitario": "800.00"}') == ["800.00", "clave costo*"]
    assert _aparece_costo('{"x": 800.00}') == ["800.00"]
    assert _aparece_costo('{"precio": 1250.00, "n": 6.02}') == ["1250.00", "6.02"]
    assert _aparece_costo('{"cantidad": 800, "hora": "09:12.0001"}') == []
    assert _hay_clave('{"CURP": "x"}', "curp") and _hay_clave('{"nss":1}', "nss")
    assert not _hay_clave('{"curpa": "x"}', "curp")


@pytest.fixture
def con_datos_reservados(cliente_como, session):
    """Un trabajador con CURP y NSS, y un vale suyo con un artículo que cuesta (guantes, 800.00)."""
    rh, kep = cliente_como("Recursos Humanos"), cliente_como("Almacenista")
    trabajador = alta_trabajador(
        rh, nombre="Rosa Datos Reservados", numero="EMP-RES-001", curp=CURP, nss=NSS
    )
    vale = entregar(
        kep, trabajador["id"], [{"codigo": "GUANTE-CAR", "cantidad": 2}, {"codigo": "HER-001"}]
    )
    return {"trabajador": trabajador, "vale": vale, "ids": ids_de_almacen(session)}


def _recorrido(cliente: TestClient, c: dict, *, con_ficha: bool = True) -> dict[str, str]:
    """Pide, como lo haría la interfaz, todo lo que puede mencionar al trabajador o a un costo."""
    t, v, kep = c["trabajador"], c["vale"], str(c["ids"]["KEP"])
    rutas = [
        "/api/trabajadores?q=Rosa",
        f"/api/trabajadores?situacion=CON_PENDIENTES&q={t['numero_empleado']}",
        f"/api/escaneo/{t['credencial']}",
        f"/api/escaneo/{t['numero_empleado']}",
        "/api/escaneo/GUANTE-CAR",
        "/api/escaneo/HER-001",
        f"/api/escaneo/{v['token']}",
        "/api/busqueda?q=Rosa",
        f"/api/busqueda?q={t['numero_empleado']}",
        "/api/busqueda?q=guante",
        "/api/busqueda?q=minipulidor",
        "/api/reportes/adeudos",
        "/api/reportes/adeudos?formato=csv",
        f"/api/reportes/movimientos?trabajador_id={t['id']}",
        "/api/reportes/movimientos?formato=csv",
        "/api/reportes/movimientos?tamano=200",
        "/api/reportes/consumo",
        "/api/reportes/consumo?formato=csv",
        f"/api/reportes/existencias?almacen_id={kep}",
        "/api/reportes/existencias?formato=csv",
        f"/api/almacenes/{kep}/existencias",
        f"/api/vales/{v['id']}",
        f"/api/vales/por-token/{v['token']}",
        "/api/vales?tamano=100",
        "/api/articulos",
        "/api/articulos?q=guante",
        "/api/categorias",
        "/api/etiquetas?tipo=estantes",
        "/api/etiquetas?tipo=credenciales",
    ]
    if con_ficha:
        rutas.append(f"/api/trabajadores/{t['id']}")
    respuestas: dict[str, str] = {}
    for ruta in rutas:
        r = cliente.get(ruta)
        assert r.status_code in (200, 403), f"{ruta}: {r.status_code} {r.text}"
        respuestas[ruta] = r.text if r.status_code == 200 else ""
    for ruta, art in (("/api/articulos/", "GUANTE-CAR"),):
        lista = cliente.get("/api/articulos", params={"q": art})
        if lista.status_code == 200 and lista.json()["elementos"]:
            ficha = cliente.get(ruta + lista.json()["elementos"][0]["id"])
            respuestas[ruta + art] = ficha.text if ficha.status_code == 200 else ""
    return respuestas


def test_RG_13_sin_el_permiso_de_datos_personales_no_se_envia_curp_ni_nss_en_ninguna_respuesta(
    app, cliente_como, crear_usuario, con_datos_reservados
):
    c = con_datos_reservados
    # Los roles iniciales sin el permiso y un rol con TODO menos ese permiso.
    todos_menos = crear_usuario(set(CLAVES) - {P.TRABAJADORES_VER_DATOS_PERSONALES}, almacen=None)
    clientes = {
        "Almacenista": cliente_como("Almacenista"),
        "Supervisor": cliente_como("Supervisor"),
        "Compras": cliente_como("Compras"),
        "todos menos datos personales": _cliente_de(app, todos_menos),
    }
    for nombre, cliente in clientes.items():
        for ruta, texto in _recorrido(cliente, c).items():
            assert CURP not in texto and NSS not in texto, f"{nombre}: {ruta} filtra CURP o NSS"
            assert not _hay_clave(texto, "curp", "nss"), f"{nombre}: {ruta} trae la clave curp/nss"
    # Las respuestas de escritura de trabajadores (baja) tampoco, para quien puede iniciarla.
    r = clientes["Almacenista"].post(f"/api/trabajadores/{c['trabajador']['id']}/baja")
    assert r.status_code == 200 and CURP not in r.text and NSS not in r.text
    assert not _hay_clave(r.text, "curp", "nss")


def test_RG_13_con_el_permiso_solo_la_ficha_y_el_alta_traen_curp_y_nss(
    cliente_como, con_datos_reservados
):
    c, rh = con_datos_reservados, cliente_como("Recursos Humanos")
    ficha = rh.get(f"/api/trabajadores/{c['trabajador']['id']}").json()
    assert (ficha["curp"], ficha["nss"]) == (CURP, NSS)
    # Aun con el permiso, ni el escaneo, ni la búsqueda, ni las listas, ni los reportes lo traen.
    for ruta, texto in _recorrido(rh, c, con_ficha=False).items():
        assert CURP not in texto and NSS not in texto, f"RH: {ruta}"
        assert not _hay_clave(texto, "curp", "nss"), f"RH: {ruta}"


def test_RG_12_sin_el_permiso_de_costos_no_se_envia_costo_unitario_en_ninguna_respuesta(
    app, cliente_como, crear_usuario, con_datos_reservados
):
    c = con_datos_reservados
    todos_menos = crear_usuario(set(CLAVES) - {P.CATALOGO_COSTOS}, almacen=None)
    clientes = {
        "Almacenista": cliente_como("Almacenista"),
        "Supervisor": cliente_como("Supervisor"),
        "Recursos Humanos": cliente_como("Recursos Humanos"),
        "todos menos costos": _cliente_de(app, todos_menos),
    }
    for nombre, cliente in clientes.items():
        for ruta, texto in _recorrido(cliente, c).items():
            assert _aparece_costo(texto) == [], f"{nombre}: {ruta} filtra costos"


def test_RG_12_el_costo_lo_ve_y_lo_captura_solo_quien_tiene_el_permiso(
    app, cliente_como, crear_usuario, session
):
    compras = cliente_como("Compras")
    articulos = compras.get("/api/articulos", params={"q": "GUANTE-CAR"}).json()["elementos"]
    assert str(articulos[0]["costo_unitario"]).startswith("800")
    ficha = compras.get(f"/api/articulos/{articulos[0]['id']}").json()
    assert str(ficha["costo_unitario"]).startswith("800")
    # Sin el permiso: capturar un costo es 403 y la clave nunca aparece.
    sin = _cliente_de(app, crear_usuario({P.CATALOGO_ADMINISTRAR, P.CATALOGO_VER}, almacen="KEP"))
    categoria = compras.get("/api/categorias").json()["elementos"][0]["id"]
    nuevo = {"codigo": "ART-COSTO-1", "nombre": "Artículo con costo", "categoria_id": categoria}
    r = sin.post("/api/articulos", json=nuevo | {"costo_unitario": "10.50"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    r = sin.post("/api/articulos", json=nuevo)
    assert r.status_code == 201 and "costo_unitario" not in r.json()
    r = sin.patch(f"/api/articulos/{r.json()['id']}", json={"costo_unitario": "99.00"})
    assert r.status_code == 403
    # Con el permiso sí se captura y solo él lo ve.
    con = _cliente_de(
        app,
        crear_usuario({P.CATALOGO_ADMINISTRAR, P.CATALOGO_VER, P.CATALOGO_COSTOS}, almacen="KEP"),
    )
    r = con.post(
        "/api/articulos", json=nuevo | {"codigo": "ART-COSTO-2", "costo_unitario": "10.50"}
    )
    assert r.status_code == 201 and str(r.json()["costo_unitario"]).startswith("10.5")
    assert "costo_unitario" not in sin.get(f"/api/articulos/{r.json()['id']}").text


def test_RG_12_la_importacion_ignora_el_costo_sin_permiso_y_lo_oculta(
    app, cliente_como, crear_usuario, session
):
    tabla = [fila("IMP-COSTO-1", "Pinza de prueba", cantidad=3, costo="85.50")]
    cuerpo = {"filas": tabla, "columnas": COLUMNAS, "almacen_por_defecto": "KEP"}
    categorias = cliente_como("Compras").get("/api/categorias").json()["elementos"]
    manual = next(c for c in categorias if c["nombre"] == "Herramienta manual")["id"]
    cuerpo["categoria_por_defecto_id"] = manual
    # Con costos (Compras): la vista previa lo muestra.
    previa = cliente_como("Compras").post("/api/importacion/vista-previa", json=cuerpo)
    assert previa.status_code == 200 and "85.50" in previa.text
    # Sin costos: el almacén de la sesión, un aviso, y el costo no vuelve en NINGUNA respuesta.
    sin = _cliente_de(app, crear_usuario({P.INVENTARIO_ENTRADAS}, almacen="KEP"))
    previa = sin.post("/api/importacion/vista-previa", json=cuerpo)
    assert previa.status_code == 200, previa.text
    assert "85.50" not in previa.text
    assert not _hay_clave(_sin_mapa_de_columnas(previa.text), r"costo\w*")
    assert any("costo" in a.lower() for a in previa.json()["avisos"])
    confirmada = sin.post("/api/importacion", json=cuerpo | {"id_lote": str(uuid.uuid4())})
    assert confirmada.status_code == 201, confirmada.text
    assert "85.50" not in confirmada.text
    assert not _hay_clave(_sin_mapa_de_columnas(confirmada.text), r"costo\w*")
    articulo = cliente_como("Compras").get("/api/articulos", params={"q": "IMP-COSTO-1"}).json()
    assert articulo["elementos"][0].get("costo_unitario") is None  # la columna se ignoró (RG-12)


def test_RG_12_un_vale_nunca_muestra_costos_ni_siquiera_el_de_compras(
    cliente_como, con_datos_reservados
):
    c = con_datos_reservados
    compras = cliente_como("Compras")
    v = c["vale"]
    # Compras SÍ ve costos en el catálogo...
    assert "costo_unitario" in compras.get("/api/articulos", params={"q": "GUANTE-CAR"}).text
    # ...pero en ningún vale, comprobante, reporte, escaneo ni CSV.
    por_ver = [
        f"/api/vales/{v['id']}",
        f"/api/vales/por-token/{v['token']}",
        "/api/vales?tamano=200",
        f"/api/escaneo/{v['token']}",
        f"/api/escaneo/{v['folio']}",
        "/api/reportes/movimientos?tamano=200",
        "/api/reportes/movimientos?formato=csv",
        "/api/reportes/existencias?formato=csv",
        "/api/reportes/consumo",
        "/api/reportes/consumo?formato=csv",
        "/api/busqueda?q=guante",
        "/api/escaneo/GUANTE-CAR",
    ]
    for ruta in por_ver:
        r = compras.get(ruta)
        assert r.status_code == 200, f"{ruta}: {r.status_code}"
        assert _aparece_costo(r.text) == [], f"{ruta} muestra costos"
    # Tampoco la respuesta de crear una entrada con costos en el catálogo (el cuerpo no los acepta).
    r = compras.post(
        "/api/vales",
        json={
            "tipo": "ENTRADA",
            "id_cliente": str(uuid.uuid4()),
            "renglones": [{"codigo": "GUANTE-CAR", "cantidad": 1, "costo_unitario": "1.00"}],
        },
    )
    assert r.status_code == 422, "una entrada rechaza campos de costo (el cuerpo no los admite)"
    entrada = confirmar(
        compras, {"tipo": "ENTRADA", "renglones": [{"codigo": "GUANTE-CAR", "cantidad": 1}]}
    )
    assert _aparece_costo(str(entrada)) == []
    detalle = compras.get(f"/api/vales/{entrada['id']}")
    assert _aparece_costo(detalle.text) == []


# ============================================================== (e) la cookie de sesión


def _cookie(respuesta) -> str:
    return respuesta.headers["set-cookie"].lower()


def test_AC_04_la_cookie_de_sesion_es_httponly_samesite_lax_y_sin_valor_visible_al_script(
    client, usuario_por_rol
):
    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    assert r.status_code == 200
    cookie = _cookie(r)
    assert cookie.startswith(f"{get_settings().cookie_nombre}=")
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert "max-age=" in cookie and "secure" not in cookie  # COOKIE_SEGURA=false en las pruebas
    # La respuesta nunca trae contraseñas ni hashes ni el PIN.
    assert not re.search(
        r"hash|contrasena|pin", r.text.replace('"permisos"', ""), re.IGNORECASE
    ) or ("contrasena" not in r.text and "hash" not in r.text and '"pin"' not in r.text)


def test_AC_04_con_cookie_segura_la_cookie_lleva_secure(app, usuario_por_rol, monkeypatch):
    monkeypatch.setattr(get_settings(), "cookie_segura", True)
    cliente = TestClient(
        app, base_url="https://testserver"
    )  # la cookie Secure solo viaja por https
    r = iniciar_sesion_en(cliente, usuario_por_rol("Almacenista"))
    assert r.status_code == 200
    cookie = _cookie(r)
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    # Al salir, la cookie que se borra conserva los mismos atributos.
    sale = cliente.delete("/api/sesion")
    assert sale.status_code == 204
    borrada = _cookie(sale)
    assert "secure" in borrada and "httponly" in borrada and "samesite=lax" in borrada
    assert "max-age=0" in borrada or "expires=" in borrada


def test_AC_04_la_cookie_vence_con_la_sesion_y_al_salir_ya_no_sirve(client, usuario_por_rol):
    assert iniciar_sesion_en(client, usuario_por_rol("Supervisor")).status_code == 200
    assert client.get("/api/sesion").status_code == 200
    assert client.delete("/api/sesion").status_code == 204
    assert client.get("/api/sesion").status_code == 401


def test_AC_04_credenciales_malas_dan_el_mismo_mensaje_sin_decir_cual_fallo(
    client, usuario_por_rol
):
    malo = client.post("/api/sesion", json={"usuario": "supervisor", "contrasena": "no-es"})
    otro = client.post("/api/sesion", json={"usuario": "no-existe", "contrasena": "no-es"})
    assert malo.status_code == otro.status_code == 401
    assert malo.json() == otro.json()
    assert "set-cookie" not in malo.headers and "set-cookie" not in otro.headers
