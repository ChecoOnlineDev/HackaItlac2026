# Mapa del sistema

> Estado Android del 8 de octubre de 2026: frontend/capacitor.config.ts empaqueta build/client; frontend/android/ contiene el proyecto nativo y complementos HTTP e impresión; frontend/app/movil/ adapta versión, red, navegación, imágenes protegidas y archivos. La API HTTPS se fija al construir. backend/app/version_app.py implementa OF-02. El contenedor en línea requiere aceptación de sesión en equipo real. proyectos, notificaciones y sincronizacion siguen planeados: no se agregaron tablas ni migraciones y FEAT-020 sin conexión está pendiente.


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
- **Cada endpoint declara su permiso en el `router.py`**, por clave; nunca se compara el nombre del rol. Las reglas de negocio van en `service.py`. Excepción documentada: ocho rutas verifican el permiso en el servicio (con `AccesoService.exigir_permiso`) porque depende del tipo de vale o del usuario, o porque aceptan uno de dos permisos: `POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}`, `POST /api/autorizaciones/{id}/resolucion`, `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}`. En ellas el router solo exige sesión. Otras cuatro aceptan uno de dos permisos y lo declaran en el router con `requiere_alguno` (`GET /api/reportes/movimientos`, `GET /api/reportes/usuarios`, `GET /api/seguimiento/piezas` y `GET /api/seguimiento/cantidad`), como dice AGENTS.md.
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

## Previsto por la iteración 01 (aprobado, sin construir)

Fuente: [documento maestro de la iteración 01](../releases/iteration_01/README.md) (secciones 5.2 y 7), [ADR-012](decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md) a [ADR-015](decisions/ADR-015-operacion-sin-conexion-del-almacenista.md) y FEAT-013 a FEAT-020. Nada de esto existe todavía; lo de arriba describe lo construido.

### Módulos nuevos (de doce a quince)

Cada uno sigue `Router -> Service -> Repository -> Model` y su `router.py` se monta en `main.py` al crearse.

| Módulo | Responsabilidad | Depende de | FEAT |
|---|---|---|---|
| `proyectos` (previsto) | Dueño de `proyecto` y `asignacion_proyecto`. Alta, edición, cierre y reapertura de proyectos; asignar, cambiar y terminar la asignación de un trabajador. Ofrece a los demás `proyectos_activos_del_trabajador(trabajador_id)`. `trabajadores` lo llama dentro de su transacción en el alta y el reingreso. | `acceso`, `almacenes`, `trabajadores`, `auditoria` | 013 |
| `notificaciones` (previsto) | Dueño de `suscripcion_push`. Clave pública VAPID, suscripciones por dispositivo, destinatarios, agrupación, reemplazo, revocación y envío Web Push después del commit (`BackgroundTasks`). No importa a `movimientos`; lo llaman `autorizaciones` (despacho, excedente, traslado) y `movimientos` solo para el aviso informativo del traslado confirmado (X-20), siempre fuera de la transacción. | `acceso` | 014 |
| `sincronizacion` (previsto) | Dueño de `dispositivo`, `dispositivo_usuario`, `conflicto_sincronizacion` y `operacion_recibida`. Inscripción y revocación de equipos, paquete del almacén, recepción de lotes y conflictos. Lee de `catalogo`, `trabajadores`, `almacenes`, `proyectos`, `movimientos` e `inspecciones` para armar el paquete. **No escribe** vales, movimientos, existencias, piezas ni inspecciones: recibe, valida la forma y llama al servicio del dueño. | `acceso`, `movimientos`, `inspecciones`, `solicitudes_compra` y los de lectura | 020 |

Cambian módulos existentes: `acceso` (conjunto de almacenes, almacén activo, `despacho_autonomo`, permisos nuevos, middleware de `X-App-Version`), `almacenes` (autonomía, `hora_descarga`, bloqueo `CON_PROYECTOS_ACTIVOS`), `autorizaciones` (tipos DESPACHO y TRASLADO, aprobación parcial, resolución múltiple), `movimientos` (proyecto, lote, despacho, traslado lateral y camino de confirmación de vales sincronizados), `inspecciones` (lote y pendientes), `catalogo` (alto valor y días de aviso), `consulta` (bitácora por vale, deudores, consumo por trabajador, uso por proyecto, búsqueda por palabras).

### Límites que se conservan y se precisan

- **Solo `movimientos` escribe vales, movimientos, existencias y la ubicación de las piezas, también los que llegan por sincronización.** `sincronizacion` llama a un camino de confirmación de `movimientos` para vales sincronizados (almacén del equipo, token del equipo, `capturado_en`, `dispositivo_id`; clasifica GUARDADO, GUARDADO_CON_AVISOS o CONFLICTO en vez de rechazar con `VALE_CAMBIO`). Resolver un conflicto crea un vale nuevo por ese mismo servicio. `vale.proyecto_id` y `vale.lote_id` se escriben ahí, al insertar; la importación pasa el lote como parámetro interno.
- **`consulta` sigue sin escribir:** la bitácora por vale, Deudores, el consumo por trabajador, el uso por proyecto y la lista de inspecciones pendientes solo leen.
- **Un solo helper de alcance (AC-36 a AC-41).** `AccesoService.alcance_del_usuario(usuario) -> Alcance(todos, almacenes, activo)`, en `acceso` (dueño de `usuario_almacen`; `core` no importa módulos). `en_alcance` y `exigir_mismo_almacen` se reescriben sobre él: las lecturas abarcan el conjunto y las escrituras usan el almacén activo. Los servicios migran uno por cambio (orden: `consulta/tablero` y `valor`, `autorizaciones`, `movimientos`, `consulta` reportes y seguimiento, `inspecciones`, `solicitudes_compra`, `importacion`, `catalogo`, `almacenes`), cada uno con una prueba de un usuario de dos almacenes; una prueba de búsqueda en el código falla si queda una lectura directa de `usuario.almacen_id` fuera de `acceso` y de las escrituras de `movimientos`.
- **Rutas que verifican el permiso en el servicio:** se suma `POST /api/autorizaciones` (según `tipo`), y el permiso de cada operación de `POST /api/sincronizacion/lotes`. **Rutas con `requiere_alguno`:** se suman `GET /api/bitacora`, `PUT /api/usuarios/{id}/almacenes` y `GET /api/proyectos`. AGENTS.md actualiza sus listas al construirse.

### Flujo de una entrega de EPP con aprobación (FEAT-014)

```
Interfaz: captura trabajador y artículos -> POST /api/vales/evaluar (requiere_aprobacion_despacho)
  -> POST /api/autorizaciones {tipo: DESPACHO}      autorizaciones: guarda; tras el commit,
                                                    notificaciones manda el push a los supervisores
Supervisor: toca el aviso -> POST /api/autorizaciones/{id}/resolucion (total o por renglón)
Interfaz (cada 3 s): ve la aprobación, quita lo rechazado, firma
  -> POST /api/vales {autorizacion_id}              movimientos: revalida, escribe, marca USADA
```

### Flujo de la sincronización (FEAT-020)

```
App de Android (equipo inscrito, X-Dispositivo)
  GET /api/sincronizacion/paquete  -> base local cifrada (catálogo, piezas, existencias, trabajadores)
  sin señal: evaluador local -> cola local (id_cliente, token, capturado_en, secuencia)
  vuelve la señal: POST /api/sincronizacion/lotes
       sincronizacion: valida equipo y forma; por cada operación, en su transacción y en orden:
         vales -> movimientos (revalida con filas bloqueadas; folio del servidor)
         inspecciones y No apta -> inspecciones; solicitudes -> solicitudes_compra
       -> GUARDADO | GUARDADO_CON_AVISOS (lista de revisión) | CONFLICTO (conflicto_sincronizacion)
Supervisor (web): GET/POST /api/sincronizacion/conflictos
```

### Áreas del frontend

| Área | Rutas o carpetas | Notas |
|---|---|---|
| Administración | `/proyectos` | Primero computadora. |
| Supervisión | `/autorizaciones/:id`, `/deudores`, `/bitacora` (pestañas «Por vale» y «Detalle por renglón»; `/reportes/movimientos` y `/reportes/adeudos` redirigen), equipos y conflictos de sincronización | |
| Operación | `/inspecciones` y el flujo de inspección (una pieza o lote) | Primero celular. |
| Sesión | Selector del almacén activo en la barra superior (solo con dos o más almacenes); «Avisos de este equipo» en el menú de usuario | `sesion/` |
| **App de Android** | `frontend/android/` (proyecto nativo y complemento propio: WorkManager, reloj monótono, DataWedge opcional), `frontend/capacitor.config.ts`, `frontend/app/sin-conexion/` (base local, paquete, cola, evaluador local, credencial local) | La misma interfaz empaquetada con Capacitor, no un proyecto aparte; lo nativo va detrás de `Capacitor.isNativePlatform()` y la web no lo carga. Cualquier otro proyecto móvil del repositorio no es esta app. |
| Componentes comunes | `componentes/ui/busqueda-diferida.ts` (`useBusquedaDiferida`), `componentes/dominio/formato.ts`, `componentes/dominio/etiquetas-medidas.ts` y el armado de PDF compartido (jsPDF) | FEAT-017 y FEAT-019. Cada ruta declara en su `handle` si es primero celular o primero computadora (UX-08). |

Propuesto en la raíz: `pruebas-compartidas/evaluador/`, casos JSON por regla que corren pytest y vitest (OF-16).

## Cómo validar

Los comandos están en [AGENTS.md](../../AGENTS.md). El gate de cada fase está en el [roadmap](../product/roadmap.md).
