# Mapa del sistema

Qué módulos existen, de qué se encarga cada uno y de quién depende. Es la orientación para cualquier tarea que cruce módulos.

Estado: los doce módulos del backend están construidos y montados en `main.py`, y la interfaz cubre todas las pantallas del MVP (una ruta por pantalla en `frontend/app/routes.ts`). Quedan por hacer lo de la segunda ola (FEAT-001 a FEAT-004) y la matriz editable de roles (FEAT-006); el trabajo del release está en la [checklist](../releases/mvp-checklist.md).

## Estructura del repositorio

```
backend/
  app/
    main.py               crea la aplicación; monta todos los routers bajo /api y los handlers
    config.py             ajustes leídos de variables de entorno
    db.py                 motor, sesión (sin commit automático) y base declarativa
    seguridad.py          contraseñas, PIN y token de sesión
    modelos_registro.py   importa todos los models.py (Alembic y pruebas)
    mantenimiento.py      comandos de línea de comandos: verificar consistencia y reconstruir existencias
    datos_prueba.py       carga repetible de datos de prueba; orquesta una función por módulo
    core/                 excepciones base, handlers de errores, paginación, ids, fechas,
                          traducción de constraints; NO importa módulos de negocio
    integraciones/        adaptadores a lo externo; hoy archivos.py (volumen de archivos)
    modulos/<dominio>/    uno por dominio (ver tabla)
  alembic/                migraciones
  tests/                  pruebas
frontend/
  app/
    routes/               una ruta por pantalla (operacion, consulta, personas, inventario, supervision)
    componentes/          por área; `dominio/` trae el escáner, el renglón con semáforo, fichas, firma y QR
    api/                  cliente de la API
    sesion/               sesión y menú según permisos
scripts/                  respaldo y restauración (bash y PowerShell)
docs/                     esta documentación
```

## Capas del backend

El backend es **síncrono** (el driver es PyMySQL): los endpoints son `def` y la sesión es `Session` de SQLAlchemy 2. Cada módulo sigue el mismo flujo, `Router -> Service -> Repository -> Model`:

| Archivo | Responsabilidad |
|---|---|
| `router.py` | Adapta HTTP y declara el permiso de cada endpoint (`requiere_permiso`). Sin queries ni commits. |
| `schemas.py` | Contratos de entrada y salida; aquí se aplican los permisos de información. |
| `service.py` | Reglas de negocio y **control de la transacción** (commit y rollback). |
| `repository.py` | Consultas y persistencia: `add`, `flush`, `execute`; **nunca commit**. |
| `models.py` | Tablas, constraints e índices. Cada tabla tiene un solo módulo dueño. |
| `exceptions.py` | Fallos esperados, sin HTTP; heredan de `app.core.excepciones`. Un handler global las traduce a `{codigo, mensaje, detalles}`. |
| `permisos.py` | Solo `acceso`: el catálogo de claves de permiso. |
| `datos_prueba.py` | `cargar(session)` idempotente que llama `app/datos_prueba.py`. |

Dependencias permitidas: `Router -> Service`, `Service -> Repository`, `Service -> Service de otro módulo`, `Service -> integraciones`, `Repository -> Model`. Un módulo no usa el repository ni escribe los modelos de otro: llama a su service. `core/` no importa módulos.

## Módulos del backend

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `acceso` | Usuarios, sesión, PIN, roles y el catálogo de permisos. Ofrece a los demás módulos `usuario_actual`, `requiere_permiso`, `verificar_pin` y la resolución del almacén de la operación. | `almacenes`, `auditoria` |
| `almacenes` | Almacenes, ubicaciones y lectura de existencias. | `acceso` (permisos) |
| `catalogo` | Categorías, artículos, piezas, registro de códigos; inactivar y reactivar; auditoría de cambios. | `acceso` |
| `trabajadores` | Personas, periodos de contrato, vigencia, baja y reingreso. | `acceso` |
| `movimientos` | El motor: evalúa el semáforo, confirma vales, escribe movimientos, actualiza existencias, asigna folios. | `catalogo`, `trabajadores`, `almacenes`, `autorizaciones` |
| `autorizaciones` | Solicitudes de autorización y su resolución, por PIN o a distancia. | `acceso` |
| `inspecciones` | Inspecciones y cambios de estado de pieza. | `catalogo` |
| `consulta` | Escaneo universal, búsqueda, fichas y reportes. Solo lee. | Todos |
| `importacion` | Vista previa y carga desde tabla; crea artículos y entradas a través de `catalogo` y `movimientos`. | `catalogo`, `movimientos` |
| `archivos` | Dueño de `adjunto`. Guarda y lee firmas y fotos del volumen (por `integraciones/archivos.py`), valida el tipo por el contenido y el tamaño, y calcula el `sha256`. Sin endpoints propios: los usan `movimientos` y `trabajadores`. | — |
| `solicitudes_compra` | Dueño de `solicitud_compra`, su historial `solicitud_compra_evento` y el contador `serie_solicitud_compra`. La solicitud de compra urgente y su seguimiento (SC-01 a SC-11). No es inventario: no escribe vales, movimientos ni existencias; solo lee el vale de ENTRADA para ligarlo. | `acceso`, `catalogo`, `almacenes` |
| `auditoria` | Dueño de `auditoria`. Ofrece `registrar(...)` a los demás módulos para el registro de cambios (CF-15, AC-10). Nunca guarda secretos. | — |

## Límites

- **Solo `movimientos` escribe** en vales, movimientos, existencias y en la ubicación de las piezas. Los demás módulos le piden la operación; nunca tocan esas tablas.
- **`consulta` no escribe nada.**
- **Única excepción a «solo `movimientos` escribe existencias»:** `python -m app.mantenimiento reconstruir-existencias --aplicar`, un comando de línea de comandos que corrige las existencias desde la bitácora con confirmación y registro en auditoría. No es un endpoint ni una pantalla (ver [security-model.md](security-model.md), Respaldos y recuperación).
- **Cada endpoint declara su permiso en el `router.py`**, por clave; nunca se compara el nombre del rol. Las reglas de negocio van en `service.py`. Excepción documentada: seis rutas verifican el permiso en el servicio (con `AccesoService.exigir_permiso`) porque depende del tipo de vale o del usuario: `POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}` y `POST /api/autorizaciones/{id}/resolucion`. En ellas el router solo exige sesión.
- **Los permisos de información** (costos, datos personales) se aplican al armar la respuesta, en `schemas.py`.

## Flujo de una entrega

```
Interfaz: escanea un código
  -> POST /api/vales/evaluar
       movimientos.service: identifica el código (catalogo), revisa al trabajador (trabajadores),
       existencias (almacenes), estado e inspección (catalogo), límites y requisitos
       -> devuelve nivel y motivos por renglón
Interfaz: firma y confirma
  -> POST /api/vales
       movimientos.service: bloquea filas, vuelve a evaluar, escribe vale y movimientos,
       actualiza existencias y ubicación de piezas, asigna folio
       -> devuelve el vale emitido
```

## El motor de vales

El módulo `movimientos` es un motor genérico más un manejador por tipo de vale. Está documentado a fondo en `backend/app/modulos/movimientos/README.md`; aquí su forma:

```
router.py ──► service.py (MovimientoService: permisos por tipo, evaluar, confirmar, consultar)
                 │
                 ├─ tipos/__init__.py  TIPOS: un ManejadorTipo por TipoVale
                 │     entrada, entrega, devolucion, no_adeudo, traspaso, recepcion, cancelacion   completos
                 ├─ cargador.py        lee los hechos de la base (no escribe)
                 ├─ evaluador.py       funciones puras: una por regla, con su ID (SM-01, SM-06)
                 └─ repository.py      consultas, bloqueos FOR UPDATE e inserciones
```

- **Un tipo nuevo no toca el motor.** Implementa `ManejadorTipo` (`evaluar`, `bloqueos`, `datos_vale`, `construir_movimientos` y, si hace falta, `al_confirmar`) y se registra en `TIPOS`.
- **Confirmar es una transacción en READ COMMITTED** que bloquea las filas en un orden fijo (vales, trabajador, existencias, piezas, folio), vuelve a evaluar y solo entonces escribe vale, movimientos, existencias y ubicación de piezas. Ver [ADR-008](decisions/ADR-008-bloqueos-del-motor-de-vales.md).
- **El semáforo es una función pura** de hechos ya cargados: la base se lee antes (cargador) y las reglas se prueban sin base de datos.
- `autorizaciones` y `movimientos` se hablan en una sola dirección: `movimientos` llama a `AutorizacionService` (validar y marcar usada en la transacción del vale), y el router de `autorizaciones` toma de `movimientos.verificador` el verificador de renglones en rojo (A-06).

## Áreas del frontend

| Área | Rutas | Notas |
|---|---|---|
| Operación | `/entregar`, `/devolver`, `/trasladar`, `/recibir` | Comparten el escáner y la lista de renglones. |
| Consulta | `/consultar`, fichas de trabajador, artículo, pieza y vale | Solo lectura, con atajos a la operación. |
| Personas | `/trabajadores` | RH. |
| Inventario y catálogo | `/inventario`, `/entradas`, `/importar`, `/catalogo`, `/etiquetas` | Compras y supervisor. |
| Supervisión | `/autorizaciones`, `/reportes` | Autorizaciones, y los reportes que permite cada rol. |

## Cómo validar

Los comandos están en [AGENTS.md](../../AGENTS.md). El gate de cada fase está en el [roadmap](../product/roadmap.md).
