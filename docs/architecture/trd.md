# TRD — Control de herramientas y EPP (MVP)

Cómo se construye el alcance definido en [mvp-scope.md](../product/mvp-scope.md). Decide lo costoso de cambiar; lo local se resuelve en cada tarea. Los detalles están en los documentos complementarios:

- [overview.md](overview.md): mapa de módulos.
- [data-model.md](data-model.md): entidades e invariantes.
- [api-contracts.md](api-contracts.md): endpoints y errores.
- [security-model.md](security-model.md): amenazas y controles.
- [decisions/](decisions/): decisiones con historial.
- [despliegue-local-cloudflare.md](despliegue-local-cloudflare.md): entorno local con HTTPS.

## 1. Alcance técnico

El MVP (prioridad P0) y la base para las features de la segunda ola. Un solo cliente (IMHOTEP), decenas de usuarios, miles de movimientos por mantenimiento.

## 2. Stack y versiones

Lo instalado hoy, según `backend/pyproject.toml` y `frontend/package.json`:

| Capa | Tecnología |
|---|---|
| Lenguaje del servidor | Python 3.14 |
| API | FastAPI 0.141 o superior |
| Datos | SQLAlchemy 2.0, Alembic 1.19, PyMySQL 1.2 |
| Base de datos | MySQL 8.4, en Docker |
| Contraseñas y sesión | pwdlib con Argon2, PyJWT |
| Configuración | pydantic-settings |
| Interfaz | React 19, React Router 8, TypeScript 5.9 |
| Estilos | Tailwind CSS 4 |
| Construcción | Vite 8, pnpm 10 |
| Paquetes de Python | uv |

Además: `openpyxl` (leer `.xlsx` al importar), `cryptography` (la necesita PyMySQL para entrar a MySQL 8), `httpx` y `python-multipart`; `pytest` y `ruff` como dependencias de desarrollo. En la interfaz: `qrcode.react` (QR), los componentes base de shadcn sobre `@base-ui/react` y `recharts` 3.8.0 para la gráfica del tablero de inicio ([ADR-009](decisions/ADR-009-graficas-con-recharts.md)). Se retiró `pywebpush`, que entonces no usaba nada. Las notificaciones push **dejaron de estar excluidas** con la iteración 01 ([ADR-013](decisions/ADR-013-notificaciones-push-por-pwa.md)): su regreso es una dependencia por aprobar (sección 18).

## 3. Arquitectura general

Monolito modular con un solo desplegable ([ADR-002](decisions/ADR-002-un-solo-desplegable.md)).

```
Celular / computadora
        │ HTTPS (túnel de Cloudflare)
        ▼
  Aplicación FastAPI ──── /api/*   reglas, bitácora, permisos
        │           └──── /*       interfaz ya construida (modo SPA)
        ▼
     MySQL            volumen de archivos (firmas y fotos)
```

- La interfaz se construye como aplicación de una sola página (`ssr: false` en `frontend/react-router.config.ts`) y la sirve el mismo servidor. Un solo origen: sin CORS.
- Toda regla de negocio vive en el servidor. La interfaz solo muestra lo que el servidor evalúa.

## 4. Módulos y dependencias

Están en [overview.md](overview.md). La regla central: **solo el módulo `movimientos` escribe vales, movimientos, existencias y la ubicación de las piezas** ([ADR-001](decisions/ADR-001-bitacora-de-movimientos.md)).

## 5. Modelo de datos e invariantes

Está en [data-model.md](data-model.md). Los identificadores internos son UUID versión 7 y el folio de cada vale sale de un contador aparte ([ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). Las invariantes que el servidor garantiza:

- La existencia de un artículo en una ubicación es igual a la suma de sus movimientos.
- Ninguna existencia de almacén o de trabajador es negativa.
- Una pieza está en una sola ubicación.
- Un código identifica una sola cosa.
- Los movimientos no se modifican ni se borran.

## 6. Contratos de API y errores

Están en [api-contracts.md](api-contracts.md). Convenciones:

- JSON bajo `/api`, con nombres en español y sin acentos.
- Dos pasos para todo vale: `evaluar` (no escribe) y `confirmar` (escribe en una transacción).
- Idempotencia: cada confirmación lleva un `id_cliente` único; repetirla devuelve el mismo vale.
- Los errores tienen la forma `{codigo, mensaje, detalles}`; el `mensaje` se puede mostrar tal cual al usuario.

## 7. Autenticación y autorización

- Sesión con un token firmado en una cookie `HttpOnly`, `Secure` y `SameSite=Lax`. El token identifica al usuario; su rol, sus permisos y su almacén se leen en el servidor en cada petición, así un cambio de permisos aplica de inmediato.
- Cada endpoint declara el permiso que exige, con clave `modulo.accion`. El servidor nunca compara el nombre del rol ([ADR-007](decisions/ADR-007-permisos-por-clave.md)).
- Los roles son datos: un rol es un conjunto de permisos. El script de datos de prueba carga los cinco iniciales.
- La interfaz muestra menús y botones según los permisos de la sesión, pero no es el control.
- El PIN de quien autoriza es un secreto distinto de su contraseña y se guarda con Argon2.
- Los datos reservados piden un permiso de información: el costo, `catalogo.costos`; CURP y NSS, `trabajadores.ver_datos_personales`. Sin él, el dato no se envía.

## 8. Estado y navegación del frontend

- Una ruta por pantalla, las de [app-flow.md](../product/app-flow.md).
- Los datos se piden al entrar a cada ruta y se vuelven a pedir tras cada acción. No hay almacén global de estado.
- El borrador de un vale vive en el componente y se guarda en el almacenamiento local del navegador para sobrevivir a una recarga o a un corte de red.
- Las solicitudes de autorización y los traspasos por recibir se consultan cada tres segundos mientras la pantalla está abierta.
- Un componente de escáner unifica cámara, pistola y teclado. La cámara usa la API nativa `BarcodeDetector` del navegador, sin librería ni alternativa: en un navegador que no la tiene (Firefox, Safari de escritorio, algunas versiones de iOS) la cámara no está disponible y se captura con la pistola o con el teclado. Chrome en Android, la referencia del almacenista, la trae.

## 9. Validación y manejo de errores

- La forma de los datos se valida con Pydantic; las reglas de negocio, en los servicios.
- La evaluación devuelve por renglón el nivel y los motivos con el ID de la regla. Así la interfaz no interpreta nada y las pruebas apuntan a reglas concretas.
- Al confirmar, el servidor bloquea las filas afectadas, vuelve a evaluar y solo entonces escribe. Si el resultado cambió, responde con conflicto y la evaluación nueva.

## 10. Seguridad

Está en [security-model.md](security-model.md).

## 11. Rendimiento y escalabilidad necesaria

- Objetivo: evaluar un vale en menos de 500 ms con los datos de prueba, y mostrar el renglón en menos de un segundo desde la lectura.
- Índices sobre los movimientos por artículo, ubicación, trabajador y fecha.
- No se prepara para varias empresas ni para alta concurrencia. Los bloqueos por fila bastan para varios almacenistas simultáneos.

## 12. Logs, métricas y auditoría

- Registro de la aplicación a la salida estándar, visible con `docker compose logs`.
- La bitácora de movimientos es la auditoría de inventario.
- Una tabla de auditoría registra lo que no es movimiento: entradas al sistema, cambios de catálogo, inactivaciones y autorizaciones.
- Sin métricas de la aplicación. El tablero de inicio (FEAT-008) no es una métrica técnica: son consultas agregadas a la base, calculadas en el servidor con el alcance del usuario, sin tablas de resumen.

## 13. Entornos, deploy y secretos

- **Local:** Docker Compose con base de datos, aplicación y túnel, según [despliegue-local-cloudflare.md](despliegue-local-cloudflare.md).
- **Servidor:** el mismo Compose; cambia solo el archivo `.env`.
- Los secretos (clave de sesión, contraseñas de MySQL, token del túnel) viven en `.env`, que no se sube al repositorio. `.env.example` documenta cada variable sin valores reales.
- Un `Dockerfile` en la raíz construye la interfaz con pnpm y la copia a la imagen del servidor; el `frontend/Dockerfile` de la plantilla se retiró.

## 14. Migraciones, backups y recuperación

- Todo cambio de esquema es una migración de Alembic; ninguna tabla se crea a mano.
- Los datos de prueba se cargan con un script repetible.
- Respaldo: `scripts/respaldo.sh` o `respaldo.ps1` vuelcan MySQL y copian el volumen de archivos; `restaurar.sh` o `restaurar.ps1` los restauran, en la misma base o en otra para probar. Procedimiento y programación diaria en [despliegue-local-cloudflare.md](despliegue-local-cloudflare.md).
- Las existencias se pueden reconstruir desde la bitácora: `python -m app.mantenimiento verificar` compara ambas y las demás invariantes (solo lectura) y `reconstruir-existencias --simular` muestra lo que valdrían (`--aplicar` solo por línea de comandos, con confirmación y auditoría).

## 15. Estrategia de pruebas y CI

- **Reglas:** pruebas unitarias del semáforo, una por regla P0.
- **Guion del PDF:** prueba de integración que recorre el flujo principal contra la API con MySQL real. Es el gate de cada fase.
- **Permisos:** una prueba por permiso (con él, el endpoint responde; sin él, 403) y otra que compara los roles iniciales contra la sección 8.2 de las reglas.
- **Interfaz:** verificación de tipos y construcción. La prueba manual en celular forma parte de cada gate.
- **Revisión:** cada historia la revisa alguien distinto de quien la implementó.
- CI en GitHub Actions con lint, pruebas y construcción: opcional, se decide en la Fase 0.

## 16. Decisiones técnicas

Las que estaban pendientes en la Fase 0 ya se tomaron.

| Decisión | Resultado |
|---|---|
| Lectura por cámara | API nativa `BarcodeDetector`, sin librería ni alternativa para navegadores que no la traen (sección 8). Limitación aceptada: en ellos se usa pistola o teclado. |
| Generación de QR | `qrcode.react`: el navegador dibuja el código; el servidor solo entrega el texto. |
| Firma en pantalla | Lienzo (`canvas`) propio, sin librería (`firma-pad.tsx`); se envía como imagen PNG y el trazo. |
| Excel | `openpyxl`, solo para leer `.xlsx` al importar; pegar desde Excel no necesita librería. La exportación es CSV con la biblioteca estándar, con acentos y sin fórmulas inyectadas. |
| Foto del trabajador | El navegador la reduce y la recomprime antes de subirla; el servidor valida el tipo y el tamaño. Sin dependencia nueva (T-09). |
| Iconos | `lucide-react`. |
| Servidor de producción | Pendiente: antes de la Fase 8. |
| CI en GitHub Actions | No se montó; las validaciones se corren a mano. |

## 17. Fuera de alcance técnico del MVP

- Caché de datos sin conexión y sincronización en la web y la PWA ([ADR-004](decisions/ADR-004-primero-en-linea.md)). El service worker (`/sw.js`) sí existe, solo para instalar la PWA y guardar los archivos estáticos; nunca guarda `/api/*`. La operación sin conexión entra con la iteración 01 **solo** en la app de Android del almacenista ([ADR-015](decisions/ADR-015-operacion-sin-conexion-del-almacenista.md), sección 18).
- WebSockets; la actualización es por consulta periódica, que sigue siendo el respaldo cuando haya avisos push.
- Colas, procesos aparte y tareas programadas en el servidor. Las notificaciones push ya no están excluidas (iteración 01): se mandan con `BackgroundTasks` de FastAPI después del commit, en el mismo proceso y sin colas (sección 18). Siguen excluidos los avisos que mande una tarea programada (por ejemplo, el de inspección por vencer: se ve en pantalla y, en la app de Android, como notificación local).
- Varias empresas, varios idiomas.
- Almacenamiento de archivos en la nube; se usa un volumen local.
- Pruebas automáticas de interfaz de extremo a extremo.

## 18. Previsto por la iteración 01 (aprobado, sin construir)

Fuente: [documento maestro de la iteración 01](../releases/iteration_01/README.md) (secciones 5, 6, 10, 11 y 11 bis), [ADR-012](decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md) a [ADR-015](decisions/ADR-015-operacion-sin-conexion-del-almacenista.md) y FEAT-013 a FEAT-020. Nada de esto está construido; las secciones 1 a 17 describen lo que hay.

### Notificaciones push (FEAT-014, ADR-013)

- **Web Push con VAPID desde la PWA** para las solicitudes de despacho, excedente y traslado. El supervisor no tiene app nativa (D-14).
- **Envío sin colas:** después del commit de la solicitud o de su resolución, con `BackgroundTasks` de FastAPI, en el mismo proceso, uno tras otro y con tiempo de espera corto. Sin reintentos ni tareas programadas; TTL de 15 minutos. Un fallo queda en `suscripcion_push.ultimo_error`; un 404 o 410 revoca la suscripción. La agrupación por minuto se cuenta en la base (`ultimo_envio`), no en memoria.
- La consulta periódica (contador cada 5 s, solicitud cada 3 s) **se queda como respaldo**: ninguna regla depende del aviso.
- El service worker gana los manejadores `push`, `notificationclick` y `pushsubscriptionchange`.
- Variables nuevas de `.env`: `VAPID_CLAVE_PUBLICA`, `VAPID_CLAVE_PRIVADA` (secreto), `VAPID_CONTACTO`; el par se genera una vez con `uv run python -m app.mantenimiento generar-claves-vapid` (comando nuevo, solo imprime). Sin ellas los avisos quedan apagados.
- Requisitos de operación: HTTPS (túnel o `localhost`) y salida a Internet hacia los servicios de push.

### App de Android del almacenista (FEAT-020, ADR-014, ADR-015)

- **Capacitor, en el mismo repositorio:** la misma interfaz de `frontend/` empaquetada; carpeta nativa `frontend/android/` y configuración `frontend/capacitor.config.ts` (`webDir` = `build/client`). Construcción: `pnpm build` → `pnpm exec cap sync android` → Gradle (`./gradlew assembleRelease`) → APK firmado, distribuido por MDM o instalación directa, sin tienda ni iPhone. Los comandos se agregan a AGENTS.md al construirse.
- **Requisitos del equipo:** Android 7 (API 24) o superior y un WebView equivalente a Chrome 111 o superior (lo pide Tailwind CSS 4); la app lo revisa al arrancar.
- **Dentro de la app** (todo detrás de `Capacitor.isNativePlatform()`; la web no cambia): no se registra el service worker; la base de la API es absoluta (`VITE_API_ORIGEN`, una construcción por servidor); las peticiones van por `CapacitorHttp` con el almacén de cookies nativo (la sesión no cambia en el servidor; prueba de concepto primero); las descargas usan `@capacitor/filesystem` y `@capacitor/share`; cada petición manda `X-App-Version`.
- **Sin conexión:** base local SQLite cifrada (`@capacitor-community/sqlite` con SQLCipher, llave en el Keystore); paquete del almacén completo por `GET /api/sincronizacion/paquete` (JSON con `gzip` y `ETag`, sin deltas en v1); evaluador local en TypeScript para el subconjunto que se opera sin red; cola subida por lotes con `POST /api/sincronizacion/lotes`, una operación por transacción, por el servicio de `movimientos`. Ventana de 24 h medida con el reloj monótono.
- **Nativo propio, pequeño:** un complemento en `frontend/android/` con WorkManager (descarga a `almacen.hora_descarga`, aproximada), el reloj monótono y, opcional, DataWedge por *intents*. El lector Zebra funciona desde el principio en modo teclado.
- **Notificaciones locales** (`@capacitor/local-notifications`) para el aviso de inspección por vencer y la cola sin subir. Sin Web Push dentro de la app.
- Variables nuevas de `.env`: `SINCRONIZACION_HORAS_MAXIMAS` (24), `SINCRONIZACION_LOTE_MAXIMO` (20), `APP_VERSION_MINIMA`. La llave de firma del APK es un secreto fuera del repositorio.

### PDF en el navegador (FEAT-017, FEAT-019)

El PDF del vale, del lote y de las etiquetas lo arma el navegador con `jspdf` y `jspdf-autotable`, cargados bajo demanda (`import()` dinámico), con los datos que la API ya filtró por permiso: sin endpoint de PDF, para que funcione también sin conexión en la app de Android. El QR se dibuja como vector con la matriz de `qrcode.react` (sin otra librería de QR). Fuente: Poppins en TTF (archivo en `frontend/public/`, licencia OFL) o la Helvetica que trae jsPDF; se decide midiendo. La alternativa del lado del servidor (`fpdf2`) no funciona sin conexión.

### Pruebas (sección 15)

Llegan las primeras pruebas automáticas del frontend: **`vitest`** (dependencia de desarrollo) corre en TypeScript los mismos casos del evaluador que corre pytest en Python, desde una carpeta de casos compartidos (propuesta: `pruebas-compartidas/evaluador/`, un JSON por regla con su ID). Una regla del subconjunto sin su caso compartido no se acepta (OF-16). Además: prueba de integración de sincronización (lote con los tres resultados, reenvío, dos equipos con la misma pieza, equipo revocado), push con un cliente falso sin salir a Internet, y la prueba del guion del PDF con el paso de aprobación del despacho (T-7).

### Otros parámetros nuevos de `.env`

`INSPECCION_AVISO_DIAS` (7; fuera de 1 a 90 la aplicación no arranca) y `ALTO_VALOR_COSTO_MINIMO` (10000; cambiarlo pide reiniciar, T-5). Todos se documentan en `.env.example`.

### Dependencias aprobadas (maestro, sección 11)

Aprobadas por el usuario el 9 de octubre de 2026. Las de Capacitor del contenedor y `vitest` ya están instaladas; las demás se instalan al construir su feature.

| Dependencia | Para qué | Alternativa sin dependencia | FEAT |
|---|---|---|---|
| `pywebpush` (backend; trae `py-vapid` y `http-ece`) | Cifrar (RFC 8291) y firmar (VAPID) los avisos | PyJWT, `cryptography` y `httpx`, que ya están: más código propio en cifrado | 014 |
| `jspdf` y `jspdf-autotable` (frontend) | PDF del vale, del lote y de las etiquetas, también sin conexión | `fpdf2` en el servidor (no funciona sin conexión) | 017, 019 |
| Fuente Poppins en TTF (archivo) | jsPDF no lee WOFF | Helvetica de jsPDF | 017, 019 |
| `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, `@capacitor-community/sqlite`, `@capacitor/network`, `@capacitor/local-notifications`, `@capacitor/filesystem`, `@capacitor/share` y un complemento de tareas en segundo plano (WorkManager, `androidx.work`, en el complemento propio) | La app de Android, base local cifrada, red, notificaciones locales, guardar y compartir el PDF | Ninguna: son la app | 020 |
| `vitest` (desarrollo, frontend) | Los casos compartidos del evaluador local | Probar el evaluador local a mano | 020 |

### Rendimiento

Uso por proyecto, bitácora por vale, deudores y pendientes de inspección son consultas agregadas sin tablas de resumen (como el tablero), con índices nuevos por `vale(proyecto_id, tipo, creado_en)` y `vale(lote_id)`. La búsqueda por palabras (`LIKE` por palabra) no agrega índices; si con 20 000 piezas pasa de 300 ms, se propone un índice `FULLTEXT` con `ngram` en un ADR aparte. El objetivo del renglón en menos de un segundo desde la lectura vale también para el evaluador local en el equipo.
