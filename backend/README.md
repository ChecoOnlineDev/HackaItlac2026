# Backend

FastAPI síncrono (PyMySQL), SQLAlchemy 2, Alembic y MySQL 8.4. Las reglas del proyecto están en
`../AGENTS.md` y el mapa de módulos en `../docs/architecture/overview.md`.

## Puesta en marcha

```
cp ../.env.example ../.env              # y cambia los valores
docker compose up -d db                 # en la raíz del repo; espera a "healthy"
uv sync
uv run alembic upgrade head
uv run python -m app.datos_prueba       # repetible
uv run fastapi dev app/main.py --port 21002
```

`GET http://localhost:21002/api/salud` responde `{"estado":"ok","base":"ok"}`.
Documentación interactiva de la API: `http://localhost:21002/api/docs`.

## Comandos

| Acción | Comando |
|---|---|
| Pruebas | `uv run pytest` |
| Lint / formato | `uv run ruff check .` / `uv run ruff format .` |
| Migración nueva | `uv run alembic revision --autogenerate -m "descripcion"` (revisar a mano) |
| Verificar que modelos y migraciones coinciden | `uv run alembic check` |
| Deshacer todo | `uv run alembic downgrade base` |
| Verificar la consistencia de la base (solo lectura; `0` si cuadra, `1` si no) | `uv run python -m app.mantenimiento verificar` |
| Existencias según la bitácora, sin escribir | `uv run python -m app.mantenimiento reconstruir-existencias --simular` |

## Variables de entorno (`../.env`)

| Variable | Para qué | Por defecto |
|---|---|---|
| `MYSQL_HOST`, `MYSQL_PUERTO` | Dónde está MySQL (puerto del host) | `localhost`, `21001` |
| `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | Base y usuario de la aplicación | `imhotep`, `imhotep`, sin valor |
| `MYSQL_ROOT_PASSWORD` | Crea el contenedor y las bases de pruebas | sin valor |
| `ENTORNO` | `desarrollo` solo avisa de una configuración insegura; `produccion` se niega a arrancar con una clave de sesión de ejemplo o de menos de 32 caracteres, sin `COOKIE_SEGURA=true`, o con `CARGAR_DATOS_PRUEBA=true` y `CLAVE_DATOS_PRUEBA` vacía, y apaga `/api/docs`, `/api/redoc` y `/api/openapi.json` | `desarrollo` |
| `CLAVE_SESION` | Firma del token de sesión (mín. 32 caracteres en producción; `python -c "import secrets; print(secrets.token_urlsafe(48))"`) | cambiarla |
| `SESION_HORAS` | Duración de la sesión | `12` |
| `COOKIE_SEGURA` | `true` bajo HTTPS; `false` en desarrollo local por http | `false` |
| `FORWARDED_ALLOW_IPS` | Redes de las que `uvicorn` acepta `X-Forwarded-*` (solo en el contenedor; acótala a la subred de la red de compose) | redes privadas |
| `LIMITE_CUERPO_JSON`, `LIMITE_CUERPO_VALE`, `LIMITE_CUERPO_FOTO_TRABAJADOR`, `LIMITE_CUERPO_IMPORTACION` | Bytes máximos del cuerpo de una petición (413 `CUERPO_MUY_GRANDE`) | 1 MB, 12 MB, 3 MB, 6 MB |
| `ARCHIVOS_DIR` | Volumen de firmas y fotos | `./almacenamiento` |
| `ARCHIVO_TAMANO_MAXIMO` | Bytes máximos por archivo | `2097152` |
| `CLAVE_DATOS_PRUEBA`, `PIN_DATOS_PRUEBA` | Contraseña y PIN de los usuarios de prueba | ver `.env.example` |
| `TEST_DB_SUFFIX` | Sufijo de la base de pruebas | `main` |

## Datos de prueba

`uv run python -m app.datos_prueba` carga los seis almacenes (KEP, CON, MID, HYL, LAM, MIN), las
ubicaciones, los cinco roles iniciales con los permisos de la sección 8.2 de las reglas y un
usuario por rol. **Son datos de prueba, no reales.** Todos usan la contraseña `CLAVE_DATOS_PRUEBA`;
`admin` y `supervisor` tienen además el PIN `PIN_DATOS_PRUEBA`.

| Usuario | Rol | Almacén |
|---|---|---|
| `admin` | Administrador | todos |
| `supervisor` | Supervisor | todos |
| `compras` | Compras | todos |
| `rh` | Recursos Humanos | ninguno |
| `almacenista` | Almacenista | KEP |
| `alm_con`, `alm_mid`, `alm_hyl`, `alm_lam`, `alm_min` | Almacenista | CON, MID, HYL, LAM, MIN |

También carga las existencias iniciales de los artículos por cantidad en Kepler y Contratistas con vales de entrada reales (`movimientos/datos_prueba.py`, usuario `compras`): folios `KEP-ING-000001` y `CON-ING-000001`. Es repetible y no duplica.

### Piezas de prueba (equipo de alturas y herramientas por serie)

`app/datos_prueba_piezas.py` (módulo neutral: depende de `catalogo`, `movimientos` e `inspecciones` a la vez; corre al final del orquestador) da entrada en Kepler a las piezas de abajo con **un vale de entrada real** (`KEP-ING-000002`, usuario `compras`) y su inspección inicial (I-03). Es repetible: cada pieza se identifica por su código, solo se da entrada a las que faltan y el `id_cliente` del vale es determinista, así que no duplica. Una pieza apta ya cargada no se reinspecciona: su vigencia corre desde el día de la primera carga.

| Código | Artículo | Serie | Situación |
|---|---|---|---|
| `ALT-001`, `ALT-002` | Arnés Kevlar | `SN-ARN-K-0001`, `0002` | Apta, inspección vigente (180 días) |
| `ALT-003` | Arnés Kevlar | `SN-ARN-K-0003` | **No apta** (costura dañada) |
| `ALT-004` | Arnés Poliéster | `SN-ARN-P-0001` | Apta, inspección vigente |
| `ALT-005` | Arnés Poliéster | `SN-ARN-P-0002` | **Inspección vencida** (hace 20 días) |
| `ALT-006`, `ALT-007`, `ALT-008` | Bandola, gancho doble de vida, retráctil 3 mts | `SN-BAN-0001`, `SN-GAN-0001`, `SN-RET-0001` | Aptas, inspección vigente |
| `HER-001`, `HER-002` | Minipulidor | `SN-MIN-0001`, `0002` | Aptas |
| `HER-003`, `HER-004` | Detector de gases | `SN-DET-0001`, `0002` | Aptas |
| `HER-005` | Radio de comunicación (artículo `RADIO`, nuevo; categoría «Equipo de alto valor») | `SN-RAD-0001` | Apta |

Cómo queda vencida la `ALT-005` sin escribir en la base a mano: la inspección inicial de la entrada admite `fecha` (no futura) y el servicio de inspecciones calcula `vigente_hasta = fecha + vigencia del artículo`. La pieza entra con `fecha = hoy - 200 días` y vigencia de 180, así que venció hace 20 días, igual que si pasara el tiempo. Los minipulidores, detectores y el radio no requieren inspección.

## Pruebas de punta a punta

| Archivo | Qué cubre |
|---|---|
| `tests/test_guion_pdf.py` | El guion del PDF (los seis pasos del «Flujo principal») en un solo escenario encadenado, solo por la API con sesiones reales, con existencias exactas, folios, estados, responsable y ausencia de costos en cada paso; al final corre el verificador de invariantes y compara los reportes con lo operado. |
| `tests/test_guion_extremos.py` | Los escenarios más delicados de `docs/product/escenarios.md`: ES-05, 09, 10, 11, 12, 13, 14, 15, 19, 26 y 28. |
| `tests/test_permisos_sistematicos.py` | Descubre todas las rutas de `app`: 401 sin sesión, un permiso por clave en cada ruta (y su coincidencia con `api-contracts.md`), la matriz de la sección 8.2 por rol y por permiso, datos reservados (CURP, NSS, costos) y la cookie de sesión. |
| `tests/invariantes.py` | `verificar_invariantes(session, huella=None)`: las invariantes de `data-model.md` y los folios sobre la base de la prueba. `tomar_huella(session)` hace la foto de vales, movimientos e inspecciones para detectar ediciones. Reutilizable en cualquier prueba; `tests/test_verificador_invariantes.py` comprueba que detecta cada una. |
| `tests/ayudas_guion.py` | Ayudas de esas pruebas: alta de trabajador por la API, evaluar y confirmar, existencias por la API. |

## Mantenimiento y respaldo

`app/mantenimiento.py` es un módulo aislado (solo importa modelos) con dos comandos de línea de comandos: `verificar` compara la base con las invariantes de `docs/architecture/data-model.md` y `reconstruir-existencias` recalcula las existencias desde la bitácora (`--simular` no escribe; `--aplicar` pide confirmación y deja auditoría, y es la única escritura de `existencia` fuera del motor). Usa la base de `MYSQL_DATABASE`, así que para revisar una copia restaurada: `MYSQL_DATABASE=otra_base uv run python -m app.mantenimiento verificar`. Sus pruebas están en `tests/test_mantenimiento.py`. Los scripts de respaldo y restauración están en `../scripts/` y se explican en el README de la raíz.

## El motor de vales

`app/modulos/movimientos/` es el motor: evaluar el semáforo, confirmar vales y consultarlos. Su diseño, el contrato para agregar un tipo de vale (`ManejadorTipo`) y lo que falta de cada tipo están en `app/modulos/movimientos/README.md`; el porqué de sus bloqueos, en [ADR-008](../docs/architecture/decisions/ADR-008-bloqueos-del-motor-de-vales.md).

## Importación de inventario

`app/modulos/importacion/` carga inventario desde una tabla de Excel (US-IMP-001). Contrato en `docs/architecture/api-contracts.md` (sección Importación). No tiene tablas propias: crea artículos con `CatalogoService.crear_articulo` y un vale de ENTRADA por almacén con `MovimientoService.confirmar` (`aislar=False, commit=False`), todo en una sola transacción (todo o nada, RG-09).

| Archivo | Qué es |
|---|---|
| `analisis.py` | La revisión fila por fila (la misma en la vista previa y al confirmar). Cada motivo lleva el ID de su regla. |
| `lectura.py` | Texto de las celdas, propuesta de columnas por encabezado y lectura segura de `.xlsx` (`openpyxl` con `read_only=True, data_only=True`; rechaza macros, archivos que no son `.xlsx` por su contenido, zip bombs, más de 5 MB o 5 000 filas; en memoria, sin escribir en disco). |
| `service.py` | Vista previa, archivo y confirmación (`id_cliente` determinista por lote, almacén y parte; idempotencia). |
| `repository.py` | Consultas de solo lectura, en bloques. |

Decisiones: el costo se acepta solo con `catalogo.costos` y se guarda únicamente en artículos nuevos; sin el permiso la columna se ignora con un aviso y las filas entran (RG-12). Un almacén con más de 500 renglones se parte en vales de 500. `openpyxl` es la única dependencia agregada.

## Pruebas

Corren contra MySQL real. La base se llama `{MYSQL_DATABASE}_test_{TEST_DB_SUFFIX}`, se vuelve a
crear en cada corrida y se carga con los datos de prueba. Cada prueba corre en una transacción que
se revierte. **Si varias carpetas de trabajo corren pruebas en paralelo contra el mismo MySQL, cada
una debe usar un `TEST_DB_SUFFIX` distinto.**

Fixtures (`tests/conftest.py`): `client`, `session`, `cliente_como("Almacenista")`,
`usuario_por_rol("Almacenista")`, `crear_usuario({permisos}, almacen="KEP")` e `iniciar_sesion`.
Las pruebas de reglas llevan su ID en el nombre, por ejemplo `test_AC_04_...`.

Las pruebas de `movimientos` (`tests/movimientos/`) tienen sus fixtures en su propio `conftest.py`: `compras`, `almacenista`, `supervisor` y un doble de `InspeccionService`. Las de concurrencia (`test_concurrencia.py`) no pueden usar la transacción con savepoints, porque dos hilos no se verían: usan `cliente_independiente` y `sesion_independiente`, con conexiones propias y datos confirmados que el fixture `limpieza` borra al final (y devuelve el contador de folios a su valor).

## Cómo construir un módulo

1. Llena su `models.py` (si tiene tablas nuevas: migración nueva, nunca editar `0001`), `schemas.py`,
   `repository.py`, `service.py`, `exceptions.py` y `router.py`. El router ya está montado en `main.py`.
2. Cada endpoint declara su permiso: `Depends(requiere_permiso(P.ENTREGAS_CREAR))`.
3. El service hace el `commit`; el repository solo `add`, `flush` y consultas.
4. Una excepción de dominio hereda de `app.core.excepciones`; si usa un código nuevo, agrégalo a
   `STATUS_POR_CODIGO` en `app/core/handlers.py` y al contrato de la API.
5. Para detectar un constraint violado captura `DBAPIError` (un CHECK llega como `OperationalError`) y
   usa `app.core.errores_bd.es_restriccion(exc, "uq_...")`.
