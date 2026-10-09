# FEAT-020: App de Android del almacenista y operación sin conexión

Estado: **aprobada por el usuario el 8 de octubre de 2026; contenedor Android en línea construido, aceptación en equipo real pendiente. De OF-06/OF-07 solo están implementadas y probadas las primitivas de derivación/verificación local PBKDF2 y la política pura de intentos; no tienen persistencia, interfaz ni integración de inicio de sesión. La operación sin conexión sigue sin construir y va al final del orden de construcción.**

## Hito de implementación del 8 de octubre de 2026

Se incorporaron Capacitor 8.5.3 y `frontend/android/` con la misma SPA local, API HTTPS absoluta fijada a `https://imhotep-production.checodev.top` por indicación del usuario, versión inicial `0.1.0`, `X-App-Version`, exclusión del service worker, detección de red, Atrás, impresión Android y exportaciones por Filesystem/Share. Los archivos compartidos se retienen temporalmente; los de más de una hora se limpian al abrir la app o volver a compartir. `CapacitorCookies` permanece desactivado. El puente HTTP nativo excluye `Set-Cookie` de las respuestas a JavaScript y no registra datos del puente; la sesión permanece en el almacén nativo. Las fotos y firmas protegidas se obtienen con el cliente autenticado.

OF-02 ya está implementada en el servidor: `APP_VERSION_MINIMA=0.1.0` por omisión; versión ausente permite la web, versión mal formada o menor devuelve 426. Solo el **POST exacto** a `/api/sincronizacion/lotes` (con o sin barra final) queda exceptuado; esa excepción no crea el endpoint ni concede permisos. No se añadieron tablas, migraciones, módulos o permisos de sincronización.

**La sección B todavía no tiene su criterio de salida demostrado:** falta instalar el APK en Android/Zebra real y verificar entrada, renovación, cierre/revocación, cookies y formularios contra HTTPS. No hay equipo disponible por ADB en esta sesión. Los pasos 2 a 4 del mínimo de demostración (inscripción, base cifrada, credencial local, paquete, evaluación, cola, lotes y conflictos) siguen pendientes, al igual que FEAT-013 a FEAT-019. La detección de red de este hito no implementa la recuperación por dos respuestas de salud ni el indicador avanzado OF-08/OF-14. Ver [reporte de estado y validaciones](../releases/iteration_01/reporte-capacitor.md) y [construcción Android](../../frontend/README.md).

Brief de la decisión D-15 del [documento maestro de la iteración 01](../releases/iteration_01/README.md). Usa los IDs **OF-01 a OF-30**, las tablas `dispositivo` y `conflicto_sincronizacion`, las columnas `vale.capturado_sin_conexion`, `vale.capturado_en`, `vale.dispositivo_id` y `almacen.hora_descarga`, los permisos `sincronizacion.operar` y `sincronizacion.administrar`, los parámetros `SINCRONIZACION_HORAS_MAXIMAS`, `SINCRONIZACION_LOTE_MAXIMO` y `APP_VERSION_MINIMA`, y los endpoints de la sección 5.4 del maestro. Decisiones de arquitectura: [ADR-014](../architecture/decisions/ADR-014-app-android-con-capacitor.md) (Capacitor, mismo repositorio) y [ADR-015](../architecture/decisions/ADR-015-operacion-sin-conexion-del-almacenista.md) (operación sin conexión; reemplaza en parte a [ADR-004](../architecture/decisions/ADR-004-primero-en-linea.md)). Lo que este brief propone y el maestro todavía no trae está marcado y listado en «Decisiones abiertas».

**Principio que ordena todo este documento.** El almacenista opera **en línea casi siempre**, igual que en la web: mismas pantallas, mismas reglas, mismo servidor. La operación sin conexión es la **excepción** para cuando la señal de la planta se cae en el mostrador o en un contenedor de área. Nada de lo que aquí se describe cambia el flujo en línea; solo agrega qué pasa cuando no hay red, y cómo se pone al día el servidor cuando vuelve.

---

## Problema u oportunidad

1. **La señal en la planta es inestable.** Los contenedores de área y algunos puntos de Contratistas pierden la red por minutos u horas. Con la web «primero en línea» ([ADR-004](../architecture/decisions/ADR-004-primero-en-linea.md)) la captura se detiene: el trabajador espera o se va sin su equipo, o el almacenista entrega «a mano» y lo registra después, de memoria, que es justo lo que el sistema quiere evitar.
2. **El almacenista usa un equipo Zebra compartido por turnos.** El de día y el de noche usan el mismo equipo con lector integrado. La web no deja entrar sin red, y una sesión abierta en un equipo compartido es un riesgo ([security-model.md](../architecture/security-model.md), «Riesgo de equipos compartidos»).
3. **La PWA no alcanza para trabajar sin red.** El navegador puede borrar lo guardado, no programa descargas a una hora y no da un lugar cifrado para los datos del almacén ([ADR-014](../architecture/decisions/ADR-014-app-android-con-capacitor.md)).
4. **El track pidió saber en todo momento dónde está cada pieza** (maestro, pedido 6). Un registro atrasado es mejor que uno que no existe, siempre que el servidor sepa que llegó atrasado y lo trate como tal.

## Objetivo

Que el almacenista siga entregando, recibiendo devoluciones, recibiendo traspasos e inspeccionando cuando se cae la señal, **solo con los datos de su almacén** y **solo en lo que no pide aprobación**; que todo lo capturado sin conexión llegue al servidor en orden, sin duplicarse, con la hora real de captura y la del servidor; y que lo que ya no se pueda guardar tal cual llegue a un supervisor como conflicto, sin romper ninguna invariante de la bitácora.

## Historia de usuario

Como almacenista de Midrex, quiero seguir entregando herramienta y recibiendo devoluciones cuando se cae la señal en el contenedor, para no detener al trabajador ni anotar en papel.

Como almacenista del turno de noche, quiero entrar al equipo Zebra que dejó el turno de día con mi propio PIN, aunque no haya señal, para que cada vale quede a mi nombre.

Como supervisor de Midrex, quiero ver qué equipos de mi almacén operan sin conexión, cuándo subieron por última vez y qué vales no se pudieron guardar, para resolverlos y para revocar un equipo perdido.

Como trabajador, quiero llevarme un comprobante aunque no haya señal, para demostrar lo que recibí.

Todavía no hay historias en `docs/stories/`: se escriben al empezar la construcción de esta feature.

---

## Alcance incluido

### A. La app: la misma interfaz empaquetada con Capacitor

- **Qué es.** La **misma** interfaz React 19 + TypeScript + Tailwind CSS 4 de `frontend/`, empaquetada con Capacitor como app de Android. No es un proyecto aparte: la carpeta nativa vive en `frontend/android/` y el archivo de configuración en `frontend/capacitor.config.ts`. Cualquier otro proyecto móvil que exista en el repositorio o fuera de él (por ejemplo, un proyecto Flutter) **se ignora**: no es la app de esta feature.
- **Para quién.** Para el almacenista (permiso `sincronizacion.operar`). Cualquier otro rol puede abrir la app y operar **en línea**, exactamente como en la web; solo quien tiene `sincronizacion.operar` en un equipo inscrito opera sin conexión.
- **Construcción** (comandos dentro de `frontend/`; se documentan en AGENTS.md al construirse):
  1. `pnpm build` genera la aplicación de una sola página en `build/client` (`react-router.config.ts` ya tiene `ssr: false`). `capacitor.config.ts` apunta `webDir` a `build/client`.
  2. `pnpm exec cap sync android` copia esos archivos y los complementos nativos a `frontend/android/`.
  3. Android Studio o Gradle (`./gradlew assembleRelease` dentro de `frontend/android/`) produce el APK.
  4. El APK se **firma** con la llave de publicación del proyecto. La llave y sus contraseñas son secretos: no se suben al repositorio (`.gitignore`), se guardan junto con los respaldos y se documentan en `.env.example` solo por nombre. **Perder la llave impide actualizar la app instalada**: habría que desinstalarla, y desinstalar borra la cola sin subir (CL-02).
  5. Se distribuye **sin tienda**: por el MDM de la empresa (lo habitual con equipos Zebra, que además puede impedir que se desinstale) o por instalación directa del APK. Sin iPhone.
- **Requisitos del equipo.** Android 7 (API 24) o superior y **Android System WebView reciente**: Tailwind CSS 4 necesita un motor equivalente a Chrome 111 o superior (capas de cascada, `color-mix()`, `@property`); con un WebView más viejo la interfaz se ve rota aunque funcione. La app revisa la versión del WebView al arrancar y, si es menor, muestra «Este equipo necesita actualizar Android System WebView» en vez de una pantalla rota (CL-39). En equipos Zebra sin servicios de Google, el WebView se actualiza con el MDM o con la actualización del sistema de Zebra (maestro, pregunta 4).
- **Versión mínima (OF-02).** La app manda su versión en cada petición (`X-App-Version: 1.4.0`, el `versionName` del APK). Si es menor que `APP_VERSION_MINIMA`, el servidor responde **426** con código `APP_DESACTUALIZADA` y la app muestra «Hay una versión nueva de la app. Pídela a tu supervisor o al área de sistemas para seguir». La web no manda el encabezado y no se ve afectada. Excepción: la subida de lotes (`POST /api/sincronizacion/lotes`) se acepta de una versión anterior para que la cola nunca quede atrapada (OF-02).
- **Qué cambia frente a la web dentro de la app** (todo detrás de `Capacitor.isNativePlatform()`; en el navegador nada cambia):
  - **El service worker no se registra.** `app/pwa/registrar.ts` lo registra en «contexto seguro (HTTPS o localhost)», y dentro de la app el origen es `https://localhost`: hay que excluir la plataforma nativa, porque los archivos ya son locales y un service worker dentro del WebView solo estorba.
  - **La dirección del servidor es absoluta.** `app/api/cliente.ts` usa `BASE_API = "/api"`, relativa al origen. En la app el origen es `https://localhost`, así que la base sale de una constante de construcción (`VITE_API_ORIGEN`, por ejemplo `https://imhotep.empresa.mx`) y queda `https://imhotep.empresa.mx/api`. Una construcción por servidor.
  - **Descargas de archivos.** `descargarArchivo` crea un enlace `blob:` y lo «hace clic»; en el WebView de Android eso no descarga nada. En la app, los CSV y PDF se guardan con `@capacitor/filesystem` y se ofrecen con `@capacitor/share`, o se ocultan (el almacenista casi no los usa). Se decide al construir.
  - **Notificaciones push.** Sin Web Push dentro de la app en v1: las notificaciones push son para el supervisor ([ADR-013](../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md)), que usa la PWA. La app usa solo notificaciones **locales** (sección Q).
  - **Botón «atrás» de Android.** Se conecta con `@capacitor/app` a la navegación de React Router; en la pantalla de inicio pregunta antes de cerrar.
  - **Cámara.** Hace falta el permiso `CAMERA` en el manifiesto; Capacitor pide el permiso cuando la página llama a `getUserMedia`. La lectura por cámara usa `BarcodeDetector`, como en la web ([trd.md](../architecture/trd.md), sección 8); en equipos sin servicios de Google puede no estar disponible y se usa el lector integrado (sección P).

### B. Sesión y cookies (riesgo técnico central)

**El problema.** Hoy la sesión son dos cookies `HttpOnly` y `SameSite=Lax` (AC-14, AC-24), pensadas para **un solo origen**: la interfaz y la API salen del mismo servidor ([ADR-002](../architecture/decisions/ADR-002-un-solo-desplegable.md)) y `vite.config.ts` reenvía `/api` en desarrollo justamente para no usar CORS. En la app, los archivos de la interfaz se cargan **desde el propio equipo** (origen `https://localhost` en Android) y la API está en `https://imhotep.empresa.mx`. Para el WebView eso es **otro sitio**:

- un `fetch` con `credentials: "include"` exigiría CORS con credenciales (el servidor hoy no lo tiene, a propósito);
- las cookies `SameSite=Lax` no viajan en peticiones de otro sitio hechas con `fetch`;
- el WebView de Android trae las cookies de terceros desactivadas por omisión.

Resultado: sin cambios, la app no podría ni iniciar sesión.

**Solución propuesta: peticiones nativas (`CapacitorHttp`) con el almacén de cookies nativo.**

- En `capacitor.config.ts` se activa `plugins.CapacitorHttp.enabled = true`. Capacitor reemplaza `window.fetch` y `XMLHttpRequest` por peticiones hechas por la capa nativa de Android. Una petición nativa **no es de un navegador**: no hay CORS ni noción de «sitio», así que `SameSite` no aplica.
- Las cookies que manda el servidor (`Set-Cookie`) se guardan en el **almacén de cookies nativo** de Android (`CookieManager`) y se reenvían solas en las siguientes peticiones nativas al mismo dominio, respetando `Path` (la de renovación sigue yendo solo a `/api/sesion`), `Secure` y la caducidad. El modelo del servidor **no cambia**: mismas dos cookies `HttpOnly`, misma rotación, misma detección de reutilización, mismo tope de 30 días (AC-14 a AC-24).
- `app/api/cliente.ts` no cambia su lógica (renovación de una sola vez, reintento, 401 `SESION_VENCIDA`); solo cambia la base de la URL (sección A).
- **`CapacitorCookies`** (el complemento que sincroniza `document.cookie` con el almacén nativo) **solo se activa si la prueba de concepto lo necesita**: si expone las cookies `HttpOnly` a JavaScript a través de `document.cookie`, se pierde la protección de `HttpOnly` contra un XSS. La prueba de concepto decide (abajo).

**Limitaciones conocidas de las peticiones nativas que hay que revisar en la prueba de concepto:**

| Punto | Qué se revisa | Si falla |
|---|---|---|
| Cookies `HttpOnly` | Que `Set-Cookie` de `POST /api/sesion` quede guardada y viaje en la siguiente petición; que la de renovación solo viaje a `/api/sesion`; que `document.cookie` **no** muestre `sesion` ni `sesion_renovar`. | Sin `CapacitorCookies`; si aun así no persisten, alternativa (c). |
| Rotación y carrera | Dos peticiones que reciben 401 a la vez comparten una sola renovación (la lógica de `renovarSesion` ya lo hace) y la cookie rotada queda guardada antes de la siguiente petición. | Ajustar el cliente; la tolerancia de 10 s (AC-16) cubre la carrera. |
| `FormData` | La foto del trabajador y otros envíos multipart. El almacenista casi no los usa; la firma y la foto de daño viajan como `data:` dentro del JSON. | Enviar esas rutas como JSON o desde la web. |
| `AbortSignal` | Los buscadores cancelan la búsqueda anterior (D-18). Las peticiones nativas pueden no cancelarse. | Ignorar la respuesta vieja en la interfaz (ya se descarta por orden). |
| Respuestas grandes y `304` | El paquete (sección E) llega comprimido con `ETag`; se revisa que `If-None-Match` y `304` funcionen y que la descompresión `gzip` sea transparente. | Comparar la huella en el cuerpo en lugar de `304`. |
| Peticiones a los archivos locales | Que las peticiones a `https://localhost` (los archivos de la app) no pasen por la capa nativa. | Excluirlas en el cliente. |

**Criterio de salida de la prueba de concepto** (es el **primer paso** de la construcción, antes de cualquier pantalla): con el APK de prueba contra el servidor real por HTTPS se entra, se espera a que venza el token de acceso (se baja `ACCESO_MINUTOS` a 1 en el servidor de prueba), se renueva solo, se cierra la sesión y se confirma con la base que la familia quedó revocada, y `document.cookie` no muestra ningún token.

**Alternativas si la solución propuesta falla:**

- **(b) Cargar la interfaz desde el servidor** (`server.url` en `capacitor.config.ts`). La app sería una ventana del sitio: mismo origen, cookies como en la web, sin cambios en el servidor. **Se pierde lo esencial:** sin red la app no arranca, porque la interfaz no está en el equipo; además, el puente nativo de Capacitor quedaría expuesto a contenido remoto. Solo sirve como plan de emergencia para la demostración en línea.
- **(c) Token `Bearer` guardado cifrado.** El servidor entregaría, solo a clientes de la app, el token de renovación en el cuerpo de la respuesta; la app lo guardaría cifrado con una llave del Android Keystore y mandaría el de acceso en `Authorization: Bearer`. Funciona sin cookies, pero **cambia el modelo de seguridad** (AC-14 y AC-24 dicen cookies `HttpOnly`): el token pasa por JavaScript y un XSS podría leerlo de la memoria. Exige un ADR nuevo y actualizar [security-model.md](../architecture/security-model.md).

### C. Inscripción del equipo

- **Quién y cuándo (OF-03).** Con señal, un usuario con `sincronizacion.operar` abre «Preparar este equipo para trabajar sin señal» y lo inscribe en **su almacén activo** con `POST /api/dispositivos` (nombre visible, por ejemplo «Zebra 2 Midrex», plataforma, versión de la app y modelo). El servidor crea la fila de `dispositivo` y devuelve un **secreto del equipo** (32 bytes aleatorios) que la app guarda cifrado con una llave del Android Keystore; el servidor guarda solo su huella SHA-256 (columna propuesta `dispositivo.secreto_hash`, ver «Decisiones abiertas»). Desde entonces cada petición de sincronización lleva `X-Dispositivo: <id>.<secreto>`.
- **Un equipo, un almacén.** Un equipo inscrito pertenece a **un solo almacén**, el que era el activo de quien lo inscribió. Un almacén puede tener **varios** equipos (maestro, sección 8: «dos equipos sin conexión del mismo almacén»). Para usar el equipo en otro almacén se revoca y se inscribe de nuevo, después de subir su cola.
- **Sin inscripción, solo en línea.** Un equipo no inscrito funciona como la web: sin red no opera.
- **Quién lo administra (OF-04).** El supervisor con `sincronizacion.administrar` ve los equipos de **sus** almacenes (`GET /api/dispositivos`, alcance de AC-06 y AC-36): nombre, quién lo inscribió y cuándo, usuarios registrados en él, versión de la app, última descarga del paquete (`ultimo_paquete_en`), última subida (`ultima_subida_en`) y estado («En uso», «Sin contacto hace 30 h», «Revocado»). Revoca con motivo (`POST /api/dispositivos/{id}/revocacion`). Cada inscripción y revocación queda en `auditoria` (`dispositivo.inscribir`, `dispositivo.revocar`).
- **Borrado remoto (OF-05).** Tres cosas borran datos locales **en la siguiente conexión** del equipo: revocar el equipo (borra **toda** la base local), inactivar al usuario o subir su `version_sesion` con «cerrar todas», restablecer contraseña o PIN (borran **la credencial local de ese usuario**). Antes de borrar, la app intenta subir la cola (OF-24 dice qué pasa con la cola de un equipo revocado): **nunca se borra una operación sin haberla presentado al servidor**, salvo que el equipo no vuelva a conectarse.

### D. Varios usuarios en el mismo equipo y credencial local

El caso normal: el turno de día y el de noche comparten el mismo Zebra.

- **Primera vez, siempre con señal (OF-06).** Cada usuario debe haber entrado **con señal** al menos una vez **en ese equipo**, con su usuario y contraseña normales (`POST /api/sesion`, AC-14). Al entrar en un equipo inscrito, la app le pide crear un **PIN local de 6 dígitos**, elegido por él:
  - distinto de su PIN de supervisor si lo tiene (la app no lo puede comprobar; el texto lo pide) y sin secuencias triviales (`123456`, `000000`, `111111`, fecha de hoy);
  - se guarda **solo en el equipo**, como derivación PBKDF2-SHA256 con sal aleatoria y al menos 600 000 iteraciones (WebCrypto del WebView; Argon2 no existe en el navegador sin agregar una librería);
  - nunca viaja al servidor.

  En esa misma entrada, el servidor registra al usuario **en el equipo** (tabla propuesta `dispositivo_usuario`, ver «Decisiones abiertas»): es lo que después le permite aceptar los vales que ese usuario capturó sin conexión aunque los suba otra persona (OF-24).
- **Entrar sin conexión (OF-07).** Sin señal, la pantalla «Entrar» muestra solo a los usuarios con credencial local vigente en ese equipo (nombre y usuario, sin foto). Se entra con el PIN local. Cinco intentos fallidos bloquean esa credencial cinco minutos (igual que AC-24); diez seguidos la **borran** y ese usuario necesita entrar otra vez con señal. Sin conexión **solo entra quien ya tiene credencial local**: un usuario nuevo, o uno que nunca entró en ese equipo, no puede (CL-16).
- **Nunca se descargan** contraseñas, hashes de contraseña, PIN de supervisores ni hashes de PIN. Por eso **sin conexión no se puede autorizar con PIN en el mostrador** (A-01): el equipo no tiene con qué comprobarlo.
- **La credencial local caduca** cuando: el usuario lleva 30 días sin entrar con señal en ese equipo (el tope absoluto de AC-18); el paquete dice que el usuario está inactivo, perdió `sincronizacion.operar`, cambió de almacén activo o su `version_sesion` cambió (OF-05); o se borran los datos de la app.
- **La sesión del servidor sigue a la persona.** Las cookies nativas son de **un** usuario. Cuando cambia el usuario local sin señal (el de noche entra con su PIN), la app **borra las cookies del usuario anterior** del almacén nativo: nadie opera en línea con la sesión de otro. Al volver la señal, el usuario local escribe su contraseña una vez para operar en línea. La cola, en cambio, es **del equipo** y la sube cualquier usuario registrado en él con sesión en línea (OF-24).
- **Salir** cierra la sesión local; con señal, además, cierra la sesión del servidor de ese equipo (`DELETE /api/sesion`, AC-19). La cola no se toca.

### E. Paquete del almacén (`GET /api/sincronizacion/paquete`)

Lo que el equipo necesita para evaluar y operar sin conexión. Lo arma el servidor con el alcance del almacén del equipo y del usuario (AC-06) y con reglas ya **resueltas** cuando se pueda (por ejemplo, los días de aviso efectivos del artículo, no la cadena de herencia), para que el evaluador local tenga menos lógica.

**Qué incluye:**

| Sección | Contenido | Para qué |
|---|---|---|
| `almacen` | Id, clave, nombre, tipo, estado, `despacho_epp_con_aprobacion`, `hora_descarga`, mínimos por artículo (si FEAT-004 está construida) | AL-04, autonomía (FEAT-014), E-14, hora de la descarga |
| `usuarios_del_equipo` | Por usuario registrado en el equipo: id, nombre, usuario, permisos de operación que importan sin conexión (`entregas.crear`, `devoluciones.crear`, `traspasos.recibir`, `piezas.inspeccionar`, `compras.solicitar`), si despacha EPP sin aprobación (autonomía del almacén, excepción del usuario o DE-07, ya calculado por el servidor) y si su credencial local sigue válida | Evaluar con los permisos y la autonomía del usuario que captura; borrado de credenciales (OF-05) |
| `categorias` | Todas: nombre, tipo, control, retornable, alto valor, días de aviso de inspección | E-01, E-11, alto valor |
| `articulos` | Todo el catálogo, **activos e inactivos** (para mostrar E-19 y aceptar la devolución de un inactivo, CF-11): código, nombre, marca, categoría, control, retornable, talla, unidad, requisitos (inspección, autorización por entrega, habilitación, motivo), límite y periodo, aviso de cantidad inusual, días de aviso efectivos, si es EPP y si es de alto valor. **Sin `costo_unitario`.** | E-01 a E-29, L-01 a L-05 |
| `codigos` | Códigos escaneables de artículos (incluidos los QR de estante), de las piezas del paquete y de las credenciales de los trabajadores del paquete | Escanear sin red (RG-10) |
| `piezas` | Las que están en el almacén y las que están en resguardo de los trabajadores del paquete: código, serie (o serie pendiente), estado, `inspeccion_vigente_hasta`, ubicación (almacén o trabajador) y desde cuándo | E-03, E-05, E-06, E-11, E-29, V-01, P-01 |
| `existencias` | Del almacén, por artículo (por cantidad) | E-04, E-14 |
| `trabajadores` | Ver «Qué trabajadores» abajo. Por trabajador: número de empleado, nombre, estado, periodo vigente (inicio y fin), puesto y área, tallas, proyectos vigentes del almacén (o de sus hijos) con cuál es el principal, dotación del puesto, **resguardo** completo (retornables con código, cantidad, fecha de entrega, folio y si es de un periodo anterior), consumo de consumibles de los últimos N días por artículo y huella `sha256` de su foto. **Sin CURP ni NSS.** | E-02, E-09, E-10, E-12, E-17, L-02, L-03, V-01, V-03, PR-09, PR-10 |
| `traspasos_en_transito` | Los que van hacia el almacén y aún tienen algo pendiente: folio, token del QR, origen, renglones con lo enviado y lo ya recibido | X-10 a X-15 sin red |
| `proyectos` | Proyectos vigentes del almacén y de sus hijos: id, clave, nombre, periodo | D-13, PR-09 |
| `parametros` | `SINCRONIZACION_HORAS_MAXIMAS`, `SINCRONIZACION_LOTE_MAXIMO`, `INSPECCION_AVISO_DIAS`, la ventana N de consumo, la hora del servidor (`generado_en`) y el formato del paquete | Ventana sin conexión, lotes, avisos |

**Qué trabajadores.** Los asignados a un proyecto vigente del almacén del equipo **o de un almacén hijo** (Contratistas entrega EPP a los trabajadores de los proyectos de Midrex, HYL y los demás, D-13; sin incluir a los hijos, Contratistas no tendría a nadie), más los que tienen pendientes (resguardo) entregados por ese almacén. Para el almacén central (Kepler), que está fuera de la planta y suele tener señal, se propone **no** habilitar la operación sin conexión en v1 (ver «Decisiones abiertas»). Un trabajador fuera del paquete no se atiende sin conexión, salvo la devolución de una pieza «por verificar» (OF-12).

**La ventana N de consumo** es el mayor `limite_periodo_dias` entre los artículos consumibles activos con límite (por ejemplo, 30): con eso L-03 se calcula igual que en el servidor.

**Qué NUNCA incluye:** costos (`costo_unitario`, valor del inventario; RG-12, AC-05), CURP, NSS ni otros datos personales reservados (RG-13), contraseñas, PIN ni sus hashes, tokens de sesión, datos de otros almacenes que no sean el resguardo de los trabajadores del paquete (AC-06; el resguardo se ve completo porque el trabajador es una ubicación, [security-model.md](../architecture/security-model.md)), vales completos, firmas ni fotos de daño, solicitudes de autorización, ni datos de usuarios que no estén registrados en el equipo.

**Formato.**

- Un solo documento JSON con `formato` (entero, empieza en 1), `generado_en` (hora del servidor), `almacen_id`, `dispositivo_id` y las secciones de arriba, comprimido con `gzip` en la respuesta (`Content-Encoding: gzip`).
- `ETag` = huella SHA-256 del contenido sin comprimir. La app manda `If-None-Match` con la huella que tiene; si no cambió, **304** sin cuerpo. Armar el paquete cuesta lo mismo aunque responda 304 (la huella sale del contenido); a esta escala no importa.
- **Fotos aparte.** El paquete trae la huella `sha256` de cada foto; la app pide solo las que cambiaron con el endpoint que ya existe (`GET /api/trabajadores/{id}/foto`) y las **reduce en el equipo** a unos 200 px de lado (como `reducirImagen` de `componentes/personas/foto.tsx`) antes de guardarlas. No se agrega una librería de imágenes al servidor. La primera descarga de fotos es la pesada; conviene hacerla con la Wi-Fi de la oficina.
- **Sin deltas en v1.** Se descarga completo cada vez. Razón: `articulo`, `categoria`, `trabajador`, `periodo_contrato`, `pieza` y `existencia` **no tienen `actualizado_en`** ([data-model.md](../architecture/data-model.md)), así que el servidor no puede responder «qué cambió desde X» sin agregar columnas y disparadores a medio modelo. Los movimientos sí tienen fecha, pero los cambios de catálogo, de vigencia y de estado de pieza no son movimientos. Con el tamaño estimado, el paquete completo cabe sin problema.

**Tamaño estimado** (almacén grande, como Contratistas, con unos 2 000 trabajadores en sus proyectos y los de sus hijos):

| Parte | Cálculo aproximado | Sin comprimir |
|---|---|---|
| Catálogo | 600 artículos × 450 B | 0.3 MB |
| Piezas | 3 000 × 180 B | 0.5 MB |
| Existencias y códigos | 600 × 40 B + 8 000 códigos × 50 B | 0.4 MB |
| Trabajadores con resguardo y dotación | 2 000 × 600 B | 1.2 MB |
| Consumo de N días | 10 000 filas × 50 B | 0.5 MB |
| Traspasos en tránsito | 20 × 80 renglones × 120 B | 0.2 MB |
| **Total JSON** | | **~3 MB**, unos **400 a 600 KB** con `gzip` |
| Fotos (aparte, solo la primera vez o al cambiar) | 2 000 × 15 a 30 KB (descarga), ~8 KB ya reducidas | 30 a 60 MB de descarga una vez; ~16 MB en el equipo |

Un almacén de área (Midrex, con unos 200 trabajadores) baja menos de 100 KB comprimidos.

**Base local.** SQLite **cifrada** con `@capacitor-community/sqlite` en modo cifrado (SQLCipher). La frase de cifrado es aleatoria, la genera la app al instalarse y la guarda el complemento protegida por el Android Keystore; **no** es el PIN de nadie, para que la base se abra con cualquier usuario y desde la descarga en segundo plano. Tablas locales (nombres orientativos): las del paquete (`p_articulo`, `p_pieza`, `p_existencia`, `p_trabajador`, …), `cola` (las operaciones capturadas), `ajuste_local` (lo que la cola ya movió en el equipo), `credencial_local`, `foto` y `meta` (versión del esquema, huella y hora del paquete, hora del servidor en la última conexión, contador monótono, almacén y equipo). La versión del esquema local va en `PRAGMA user_version` y se migra al arrancar una versión nueva de la app (CL-12).

**Aplicar un paquete.** Se descarga a un archivo temporal, se comprueba su huella contra el `ETag`, se carga en tablas de paso dentro de una transacción y solo entonces se reemplazan las anteriores. Si algo falla, se conserva el paquete anterior y la pantalla dice «No se pudo actualizar; sigues con los datos de hace 3 h» (CL-11). Si la cola tiene operaciones sin subir, después de aplicar el paquete se **reaplican** sus ajustes locales encima (sección K), porque el paquete nuevo todavía no las conoce (CL-35).

### F. Cuándo se descarga el paquete (D-15)

| Momento | Cómo | Nota |
|---|---|---|
| **Al iniciar sesión o turno** | Al entrar con señal, antes de mostrar el inicio (con un indicador «Preparando datos del almacén»). Si tarda más de 15 s, se deja en segundo plano y se puede operar en línea mientras tanto. | Es la descarga principal del día. |
| **A la hora del almacén** (`almacen.hora_descarga`) | Tarea programada con **WorkManager** de Android, en un complemento nativo propio dentro de `frontend/android/`, con la condición «hay red». Descarga el paquete a un archivo; la app lo aplica al abrirse o en el momento si está abierta. | **La hora no es exacta**: Android agrupa las tareas en ventanas y, en reposo profundo (Doze), las retrasa hasta la siguiente ventana de mantenimiento. Se programa un margen (por ejemplo, entre 30 y 15 minutos antes del cambio de turno) y se acepta un retraso de minutos. Un equipo en su base de carga sale de Doze con más frecuencia. Esto pasa con cualquier tecnología, no solo con Capacitor (ADR-014). |
| **Cada vez que vuelve la señal** | `@capacitor/network` avisa del cambio; la app confirma con `GET /api/salud` (una red sin salida a Internet también dice «conectado»). Primero **sube la cola** y luego descarga **si el paquete tiene más de 30 minutos**. | 30 minutos evita descargar en cada parpadeo de la señal sin dejar datos viejos. |
| **Botón «Actualizar ahora»** | En el indicador de conexión. Sube la cola y descarga sin importar la antigüedad. | Para antes de salir al contenedor. |

- **`almacen.hora_descarga`** (hora del centro de México, nula = sin descarga programada; valor inicial propuesto 06:00) la edita el Administrador desde Almacenes (`PATCH /api/almacenes/{id}`, con `almacenes.administrar`, AL-01). El supervisor la ve pero no la cambia, por ahora (igual que la autonomía, D-07).
- La descarga en segundo plano usa la sesión en línea que tenga el equipo; si no hay (por ejemplo, porque el usuario local cambió sin señal, sección D), no descarga y lo dice en el indicador.
- **La pantalla dice siempre la edad de los datos**: «Datos de hace 2 h». La edad se mide con el reloj monótono del equipo desde la última descarga (no con la hora del equipo, que se puede cambiar; sección G).

### G. Ventana sin conexión

- Se opera sin conexión **hasta `SINCRONIZACION_HORAS_MAXIMAS` (24 h)** contadas desde la última **descarga exitosa del paquete** (OF-15). Pasado ese tiempo, la app **bloquea las operaciones nuevas** y solo deja consultar, con el aviso «Tus datos tienen más de 24 horas. Busca señal para seguir operando». La cola sigue esperando para subir.
- Un vale que ya estaba en captura cuando se cumplió el plazo se puede terminar y confirmar; uno nuevo no (CL-22).
- **El reloj no se puede usar para alargar la ventana.** La app guarda, en cada conexión, la hora del servidor (encabezado `Date`) y la lectura del reloj monótono del equipo (`SystemClock.elapsedRealtime`, a través del mismo complemento nativo, porque JavaScript no lo tiene). La edad de los datos se calcula con el monótono. Si el equipo se reinició (el monótono vuelve a cero), se usa la hora del equipo, pero si es **anterior** a la última hora del servidor vista, la app supone que el reloj se movió hacia atrás y bloquea hasta sincronizar (CL-03).
- La ventana es la misma para todos los usuarios del equipo: la frescura es de los datos, no de la persona.

### H. Qué se puede hacer sin conexión

| Función | ¿Sin conexión? | Por qué |
|---|---|---|
| **Devolución** (V-01 a V-09, V-11, V-14) | **Sí** | Recuperar equipo es prioritario (SM-05) y nunca pide aprobación. El titular de una pieza y el resguardo de un trabajador vienen en el paquete. |
| Devolución de una pieza cuyo código **no está en el paquete** | **Sí, «Por verificar»** | Puede ser una pieza de un trabajador fuera del paquete o equipo ajeno (V-12). Se recibe físicamente con aviso amarillo y observación obligatoria, y el servidor decide al sincronizar (OF-12). Por cantidad, no: hace falta el trabajador. |
| **Recibir traspaso** (X-10 a X-15) | **Sí, solo los descargados** | El paquete trae los traspasos en tránsito hacia el almacén con lo pendiente. Uno enviado después de la última descarga no se conoce: espera señal. |
| **Registrar inspección y marcar No apta** (P-01, P-03) | **Sí** | Es el flujo diseñado para el almacenista (D-10) y no mueve inventario. Ver OF-21 para el orden frente a una inspección hecha en línea. |
| **Consultar** quién tiene qué, ficha de trabajador, ficha de pieza, existencias | **Sí, con la fecha de los datos** | Todo sale del paquete más lo hecho sin conexión. Cada pantalla dice «Datos de hace X» y no muestra lo que no está en el paquete. |
| **Entrega con autonomía**, renglones verdes y amarillos (herramienta; EPP en almacén o usuario con autonomía) | **Sí** | Evaluación local con las mismas reglas (sección J). La herramienta no pide aprobación (D-06); el EPP solo sin aprobación cuando hay autonomía (D-07). Los límites se calculan con lo descargado más lo hecho sin conexión. |
| **Entrega que pide aprobación**: EPP sin autonomía, o cualquier renglón naranja (E-07, E-08, E-26) | **No**: queda en «Espera señal para aprobación» | La aprobación del supervisor necesita red (DE-*, A-01); el PIN no se puede comprobar en el equipo (sección D). El trabajador no se lleva ese renglón hasta que se apruebe (OF-10). |
| Entrega a un trabajador **fuera del paquete** | **No** | Sin su vigencia, su resguardo y su consumo no se pueden evaluar E-02, L-02 ni L-03. |
| **Solicitud de compra urgente** (SC-01) | **Se encola** | No es inventario (SC-11). Se captura y se manda en el siguiente lote; el folio `CLAVE-SOL-…` llega al sincronizar. |
| Enviar traspasos, también por Excel | **No** | Cambia la existencia de dos almacenes y lo pendiente del destino; el destino no lo vería. Además lo opera el supervisor (`traspasos.operar`). |
| Cancelar un vale (K-01 a K-05) | **No** | Exige revisar lo que pasó después (K-03) con datos del servidor. Un vale de la cola se cancela después de subirlo (CL-29). |
| Vale de no adeudo (B-04) | **No** | Exige ver los pendientes del trabajador **en todos** los almacenes (B-02). |
| Alta y reingreso de trabajadores, foto, credencial | **No** | Es de RH y genera el número de empleado en el servidor (T-10). |
| Importar, dar entrada | **No** | Es de Compras y solo en Kepler (EK-01). |
| Ajustar vigencia de inspección (P-07) | **No** | Es del supervisor y exige comparar con la inspección original en el servidor. |
| Registrar serie (P-08) | **No** | La unicidad de la serie se comprueba contra toda la base. |
| Mantenimiento o calibración (P-06) | **No** en v1 | Lo hace casi siempre el supervisor; se puede agregar después con la misma cola. |
| Autorizaciones, reportes, bitácora, deudores, administración | **No** | Son de supervisión, del Administrador o de la web; necesitan datos completos. |

### I. Se pierde la señal en el mostrador (OF-08 a OF-12)

Es la situación del maestro (sección 8): «lo que no pide aprobación sigue por la cola; el EPP de un almacén sin autonomía espera a que vuelva la señal».

1. **Detección (OF-08).** La app sabe que no hay conexión por tres vías: el aviso de `@capacitor/network`, una petición que falla por red (`cliente.ts` ya marca `CODIGO_SIN_CONEXION` y `red.ts` publica el estado) y `GET /api/salud` sin respuesta en 5 s. Para no saltar de un modo a otro con una señal intermitente, se pasa a «Sin conexión» en cuanto falla una petición, y se vuelve a «En línea» después de dos respuestas buenas de `/api/salud` separadas por 5 s (CL-19).
2. **El vale en captura no se pierde.** El borrador ya vive en el equipo (E-28; hoy en `localStorage`, en la app en la base local). Al caer la señal, los renglones ya evaluados por el servidor **se vuelven a evaluar con el evaluador local** y la pantalla lo dice: «Sin señal: revisado con los datos de hace 2 h». Un vale que empezó sin conexión se termina sin conexión, aunque vuelva la señal a media captura; la app ofrece «Revisar en línea» para pasarlo al flujo normal si la persona quiere.
3. **Lo que no pide aprobación sigue (OF-09)**: firma del trabajador en pantalla, confirmación local, comprobante con QR y «Folio pendiente», y el vale entra a la cola «Por sincronizar».
4. **Lo que pide aprobación espera (OF-10)**: ver la tabla de la sección H. La app separa esos renglones, los deja en un borrador «Espera señal para aprobación» con el trabajador y la hora, y ofrece entregar ya lo demás (A-07). Al volver la señal, la app avisa («Hay 1 entrega esperando aprobación»), manda la solicitud (FEAT-014) y sigue el flujo en línea de siempre: aprobar, firmar, confirmar (D-08). Si el trabajador ya no está, el borrador se descarta con un toque; no hay vale que cancelar porque no se confirmó nada.
5. **Confirmación sin respuesta (OF-11).** Si `POST /api/vales` salió y la señal se cayó antes de la respuesta, **no se sabe** si el servidor lo guardó. La app **no** captura un vale nuevo sin conexión con otro `id_cliente`: mueve ese mismo vale, con el **mismo `id_cliente` y el mismo cuerpo**, a la cola como «Confirmación sin respuesta» y entrega al trabajador un comprobante con «Folio pendiente». Al sincronizar, la idempotencia del servidor resuelve: si ya existía, responde con su folio (GUARDADO); si no, lo guarda. El trabajador nunca recibe dos vales por lo mismo.
6. **Lo que no se puede (OF-12)** muestra «Necesitas señal para enviar un traspaso» (o la función que sea) en lugar del botón, nunca un error técnico.

### J. Evaluación local

- **Por qué hace falta.** El motor de reglas vive en Python (`backend/app/modulos/movimientos/evaluador*.py`, unas 1 000 líneas con `cargador.py`). Sin red, el semáforo lo tiene que calcular el equipo. Se escribe un **evaluador local en TypeScript** (propuesta: `frontend/app/sin-conexion/evaluador/`) **solo para el subconjunto que se opera sin conexión**: ENTREGA sin naranjas, DEVOLUCION, RECEPCION, inspección y No apta.
- **Reglas que evalúa** (las mismas, con el mismo ID y el mismo texto que el servidor; SM-01 y SM-06 igual):
  - ENTREGA: E-01, E-02, E-03, E-04, E-05, E-06, E-07 (con L-02 y L-03), E-08 y E-26 (solo para detectar el naranja y mandar a «Espera señal»), E-09, E-10, E-11 (con los días de aviso efectivos de FEAT-016), E-12, E-14 (si hay mínimos), E-15, E-16, E-19, E-27, E-29, AL-04, la regla de despacho de EPP con aprobación de FEAT-014 (con la autonomía del paquete) y la de proyecto de FEAT-013 (PR-09 y PR-10).
  - DEVOLUCION: V-01 a V-07, V-09, V-12 («Por verificar» sin conexión, OF-12), V-14.
  - RECEPCION: X-10, X-11, X-12, X-13 (con la observación obligatoria de RG-14), X-15.
  - INSPECCION: P-01, P-03, E-05 y E-06 en el sentido de la vigencia.
- **Con qué datos.** Los del paquete **más lo hecho sin conexión** en el equipo: los ajustes locales de la cola (existencias, ubicación de piezas, resguardo y consumo). Así, la segunda entrega de guantes del día ya cuenta la primera para L-03 aunque ninguna haya subido.
- **Con qué fecha.** La del equipo, en la zona del centro de México, para vigencias de contrato y de inspección (T-07, E-06, E-11). El servidor vuelve a evaluar con su propia fecha al sincronizar (OF-17).
- **La salida tiene la misma forma** que `POST /api/vales/evaluar` (nivel por renglón, motivos con ID de regla, `pide_observacion`, `requiere_confirmacion`), más `evaluado_sin_conexion: true` y la huella del paquete usado. Así los componentes `renglon-semaforo` y `lista-renglones` no cambian.
- **Riesgo de divergencia y cómo se mitiga.** Dos implementaciones de la misma regla tarde o temprano dicen cosas distintas. Se propone un **archivo de casos compartidos**:
  - Carpeta propuesta `pruebas-compartidas/evaluador/` en la raíz del repositorio, un archivo JSON por regla (`E-07-limite-retornable.json`, …). Cada caso trae el contexto (artículos, trabajador, existencias, resguardo, consumo, piezas, fecha de hoy), el vale y lo esperado (`nivel` y la lista de reglas por renglón).
  - **pytest** los corre contra el evaluador de Python con un `cargador` en memoria (el evaluador ya lee por `cargador.py`, así que se puede sustituir sin tocar las reglas); **vitest** los corre contra el evaluador de TypeScript. Una regla nueva o cambiada sin su caso compartido no pasa la revisión.
  - Agrega `vitest` como dependencia de desarrollo del frontend (hoy no hay pruebas de frontend, [trd.md](../architecture/trd.md), sección 15). Es una dependencia que esta feature pide.
  - El nombre de cada prueba lleva el ID de la regla, como pide AGENTS.md.
- **El servidor manda.** Lo que el evaluador local dice es una ayuda para operar; la verdad sale de la revaluación del servidor al sincronizar (OF-17), y una diferencia nunca rompe una invariante: o se guarda con avisos o va a conflictos.

### K. Captura sin conexión y comprobante

- **Identificadores del equipo.** Cada operación nace con su `id_cliente` (UUID; el mismo campo que ya usa `POST /api/vales`) y con un **`token`** de 128 bits aleatorios (`crypto.getRandomValues`, base64url, igual que el `secrets.token_urlsafe(16)` del servidor) que es el contenido del QR. Hoy el servidor genera el token al confirmar; para los vales sin conexión **acepta el del equipo** si tiene la forma correcta y no existe (si existiera, es conflicto `TOKEN_REPETIDO`; la probabilidad es despreciable).
- **Hora de captura.** `capturado_en` es la hora del equipo al confirmar, con su zona. Se guarda tal cual; nunca la corrige nadie (OF-19).
- **Secuencia.** Un contador local del equipo, que solo crece, ordena la cola sin depender del reloj.
- **Firma.** La firma del trabajador en pantalla (F-02: imagen PNG y trazo con sus tiempos) se guarda en la base local con la operación. Sin conexión no hay firma en papel: necesita imprimir y fotografiar el ticket.
- **Responsable.** La operación lleva el `usuario_id` de quien la capturó (el usuario local). El servidor lo pone como `responsable_id` del vale al sincronizar (OF-24, RG-07).
- **Folio «Pendiente».** El folio se asigna al sincronizar (RG-06 sigue: consecutivo por almacén y tipo, sin huecos). El comprobante dice «Folio pendiente», trae el QR del token, el trabajador, la hora de captura, los renglones (sin costos, F-12) y «Capturado sin señal: el folio se asigna al sincronizar».
- **El QR** abre `/v/:token`. Mientras el servidor no tiene ese vale, la vista dice «Pendiente de sincronizar: este vale se capturó sin señal y todavía no llega al servidor». Si llegó como conflicto, «Este vale lo está revisando el supervisor del almacén»; si el supervisor lo descartó, «Este vale no se guardó» con el motivo. La vista de `/v/:token` hoy **exige sesión** (está dentro del layout con guardia y en [security-model.md](../architecture/security-model.md) «en el MVP además pide sesión»): el trabajador sin cuenta ve la pantalla de entrar. Ver «Decisiones abiertas».
- **Ajustes locales.** Al confirmar en el equipo, la base local se ajusta en la misma transacción que guarda la operación: baja la existencia, la pieza pasa al trabajador, sube el consumo del trabajador, el traspaso deja de tener pendiente lo recibido, la pieza inspeccionada cambia de estado. Así la siguiente entrega ve lo real del equipo. Estos ajustes se guardan aparte (`ajuste_local`) para poder **reaplicarlos** sobre un paquete nuevo mientras la operación no suba (sección E) y **retirarlos** cuando el servidor responde (el paquete siguiente ya los trae, o los descarta si fue conflicto).
- **La cola no se edita ni se borra (OF-09).** Una operación confirmada en el equipo ya produjo un comprobante en manos del trabajador. No hay «borrar de la cola»: un error se corrige después de subir, con una cancelación (K-01 a K-05). Si fuera a conflicto, lo resuelve el supervisor.
- **Guardar antes de dar el comprobante.** El comprobante se muestra solo cuando la operación quedó escrita en la base local (transacción confirmada). Si el equipo se queda sin espacio o falla la escritura, la app lo dice y no da comprobante (CL-31).

### L. Sincronización por lotes (`POST /api/sincronizacion/lotes`)

**En el equipo:**

- La cola se sube **en orden de captura** (por la secuencia), en lotes de hasta `SINCRONIZACION_LOTE_MAXIMO` (20) operaciones o unos 2 MB, lo que ocurra primero. Una operación que sola pasa de 2 MB (una devolución con fotos de daño) va sola en su lote.
- **Un lote a la vez**, para no saturar una señal débil. El siguiente sale cuando responde el anterior.
- Con fallo de red o respuesta 5xx: reintento con **espera creciente** (2 s, 4 s, 8 s… hasta 5 minutos, con un poco de azar para que varios equipos no reintenten a la vez). El **mismo lote** se reenvía igual (mismo `lote_id`, mismas operaciones).
- **Compresión.** El cuerpo va comprimido con `gzip` cuando el WebView tenga `CompressionStream` y las peticiones nativas acepten un cuerpo binario; si no, sin comprimir (las firmas y fotos ya van comprimidas; el JSON es lo único que gana). Se decide en la prueba de concepto.
- Se sube con la sesión en línea del usuario que esté en el equipo, siempre que esté registrado en él (OF-24).
- Primero se sube, luego se descarga el paquete (sección F).

**Cuerpo** (forma orientativa; el contrato exacto va a [api-contracts.md](../architecture/api-contracts.md) al construirse):

```json
{
  "lote_id": "0192…",
  "formato": 1,
  "enviado_en": "2026-10-08T22:14:03.120-06:00",
  "operaciones": [
    {
      "id_cliente": "0192…",
      "secuencia": 41,
      "tipo": "ENTREGA",
      "responsable_id": "0191…",
      "capturado_en": "2026-10-08T21:02:11.500-06:00",
      "paquete_huella": "9f2c…",
      "evaluacion_local": { "nivel": "AMARILLO", "reglas": ["E-10"] },
      "cuerpo": { "...": "el mismo cuerpo de POST /api/vales, con token, proyecto_id, observacion y firma" }
    }
  ]
}
```

`tipo` es `ENTREGA`, `DEVOLUCION`, `RECEPCION` (vales, van al servicio de `movimientos`), `INSPECCION`, `NO_APTA` (van al servicio de `inspecciones`) o `SOLICITUD_COMPRA` (va al servicio de `solicitudes_compra`). Encabezados: la cookie de sesión, `X-Dispositivo` y `X-App-Version`.

**En el servidor:**

- El router de `sincronizacion` exige `sincronizacion.operar`. El servicio comprueba el equipo (`X-Dispositivo`: que exista, que el secreto coincida, que no esté revocado y que su almacén sea el del usuario de la sesión o uno de sus almacenes) y la forma del lote.
- **Cada operación va en su propia transacción**, en el orden de `secuencia`, llamando al **servicio del módulo dueño**: los vales, al de `movimientos` (solo `movimientos` escribe vales, movimientos, existencias y ubicación de piezas; maestro 5.2), las inspecciones al de `inspecciones` y las solicitudes al de `solicitudes_compra`. `sincronizacion` no escribe nada de eso: recibe, valida la forma, decide qué hacer con el resultado y escribe solo sus tablas (`dispositivo`, `conflicto_sincronizacion`, y la propuesta `dispositivo_usuario`).
- `movimientos` necesita un camino de confirmación para vales sincronizados (por ejemplo, `confirmar_sincronizado(responsable, cuerpo, dispositivo, capturado_en)`) que: usa como almacén el del **equipo** (no el activo del usuario hoy; OF-22), acepta el `token` del equipo, escribe `capturado_sin_conexion = true`, `capturado_en` y `dispositivo_id`, pone `creado_en` con la hora del servidor, vuelve a evaluar con las filas bloqueadas (como hoy) y, en vez de rechazar con `VALE_CAMBIO`, **clasifica** el resultado (abajo).
- **Idempotente.** Un vale ya guardado con el mismo `id_cliente` y la misma `huella_cuerpo` responde su resultado original (con su folio); con otro cuerpo es conflicto `ID_CLIENTE_OTRO_CUERPO` (como el 409 de hoy). Las inspecciones y la No apta hoy no tienen `id_cliente`: hace falta un registro de lo ya recibido (propuesta en «Decisiones abiertas») para que reenviar un lote cuya respuesta se perdió no las duplique (CL-18).
- Al terminar, actualiza `dispositivo.ultima_subida_en` y responde **200** con un resultado por operación y la hora del servidor.

**Resultado por operación:**

| Resultado | Cuándo | Qué hace la app |
|---|---|---|
| `GUARDADO` | El servidor lo guardó y hoy cumple todas las reglas. Trae `folio`, `vale_id` (o el id de la inspección o de la solicitud). | Marca la operación como subida, muestra el folio, permite reimprimir el comprobante con folio. |
| `GUARDADO_CON_AVISOS` | Lo guardó, pero alguna regla de política **hoy** no se cumpliría (OF-21): por ejemplo, el límite se rebasó por una entrega hecha en otro almacén mientras tanto, el trabajador ya no es vigente, el artículo se inactivó, se apagó la autonomía. Los avisos llevan su ID de regla; el vale entra a la **lista de revisión** (C-10, RG-14) con una observación automática. | Igual que GUARDADO, con el aviso visible en la cola: «Guardado. Revisión: el límite de guantes ya se había cubierto en Contratistas». |
| `CONFLICTO` | No se puede guardar sin romper una invariante (OF-22). Trae `conflicto_id` y `motivo`. Se crea un renglón en `conflicto_sincronizacion` para el supervisor. | Lo deja visible en la cola como «En revisión del supervisor», retira sus ajustes locales y sigue con la siguiente. |

**Errores del lote completo:** 401 (renovar o pedir contraseña; la cola espera), 403 `DISPOSITIVO_REVOCADO` (ver OF-24), 403 `DISPOSITIVO_NO_INSCRITO` o `DISPOSITIVO_DE_OTRO_ALMACEN`, 413 `CUERPO_MUY_GRANDE` (la app parte el lote a la mitad y reintenta), 422 `LOTE_INVALIDO` (forma del lote; una operación mal formada dentro de un lote bueno es conflicto `FORMA_INVALIDA`, para que nunca trabe la cola), 5xx y falta de red (reintento con espera).

**Dependencias dentro del lote.** Si una operación cae en conflicto, las siguientes del mismo equipo que tocan la misma pieza, o el mismo trabajador y artículo, se marcan también como conflicto `DEPENDE_DE_CONFLICTO` sin intentarse, para que el supervisor resuelva primero la de origen (CL-17).

**Lista de revisión.** Todo lo `GUARDADO_CON_AVISOS` entra a la lista de revisión con la observación automática «Capturado sin señal el 8 oct 21:02 en Zebra 2 Midrex por Juan López; al sincronizar: …» y su regla. El supervisor lo ve como cualquier otra excepción (C-10).

### M. Conflictos y su resolución (`GET/POST /api/sincronizacion/conflictos`)

- **Quién.** El supervisor con `sincronizacion.administrar`, de los equipos de sus almacenes (AC-06, AC-36). En la **web** (es una tarea de computadora, D-20); también se ve en el celular. **Quien capturó la operación no resuelve su propio conflicto** (como A-05).
- **Qué ve.** Una lista con: equipo, quién capturó, cuándo (hora del equipo y hora de llegada), tipo, trabajador, motivo en español llano y estado. Al abrir uno: el vale capturado completo (renglones, firma, observación), la evaluación local que tenía el equipo (con la edad de sus datos), lo que dijo el servidor renglón por renglón y qué otro vale chocó (por ejemplo, «la pieza ALT-003 ya está con Pedro Ruiz por MID-ENT-000245, capturado en Zebra 1 a las 20:40»).
- **Opciones** (`POST /api/sincronizacion/conflictos/{id}/resolucion`, motivo obligatorio en todas):

| Opción | Qué hace | Cuándo |
|---|---|---|
| **Reintentar** | Vuelve a presentar la operación tal cual, por el mismo camino del lote. | Cuando ya se arregló la causa: llegó el traspaso que faltaba recibir, se registró la devolución que liberaba la pieza, se reactivó el artículo. |
| **Guardar sin los renglones en conflicto** | Guarda un vale con los renglones que sí se pueden (nuevo `id_cliente` derivado del original), con la misma hora de captura, el mismo responsable y la observación del supervisor. | Un vale con varios renglones donde solo uno choca. |
| **Guardar como diferencia según la regla existente** | Solo donde ya existe una regla: una recepción con renglones ya recibidos se guarda con lo que falta como diferencia (X-13); un faltante de existencias, como ajuste de FEAT-002 cuando exista. | Recepciones parciales en dos equipos; faltantes. |
| **Descartar** | No guarda nada en el inventario; el conflicto queda `DESCARTADO` con el motivo y el comprobante del trabajador dice «Este vale no se guardó». | El registro estaba mal (escanearon la pieza equivocada) o ya se registró de otra forma. |

- **Nunca se edita un vale guardado** (RG-02). Resolver crea, en su caso, un vale **nuevo** por el servicio de `movimientos`, que vuelve a evaluar como siempre; el conflicto guarda `vale_id`, `resuelto_por`, `resolucion` (la opción y el motivo) y `resuelto_en`. Todo queda en `auditoria` (`sincronizacion.resolver_conflicto`).
- `conflicto_sincronizacion.estado`: `PENDIENTE`, `RESUELTO` o `DESCARTADO`. Un conflicto resuelto no se vuelve a abrir.
- **Aviso al supervisor.** El Inicio del supervisor muestra «Vales sin sincronizar en conflicto: 3» y «Equipos sin contacto: 1» (OF-30). La notificación push de un conflicto nuevo usa la de FEAT-014 si se decide (ver «Decisiones abiertas»).

### N. Excepciones a las reglas generales (OF-17 a OF-22)

Solo para operaciones **capturadas sin conexión**. En línea, todo sigue igual (maestro, sección 4).

| Regla | Qué dice | Excepción sin conexión |
|---|---|---|
| RG-08 | Todo se valida dos veces: al escanear y al confirmar en el servidor; si algo cambió, no se guarda. | No hubo validación del servidor al capturar. La primera validación es la local; la segunda es la del servidor al sincronizar, que **clasifica** (GUARDADO, GUARDADO_CON_AVISOS o CONFLICTO) en vez de rechazar (OF-17). |
| RG-09 | Un vale se guarda completo o no se guarda. | **El lote** no es todo o nada; **cada operación** sí (OF-18). |
| RG-11 | La hora válida es la del servidor. | `creado_en` sigue siendo la del servidor (al sincronizar); la del equipo se guarda aparte en `capturado_en` y se muestra junto (OF-19). |
| RG-06 | El folio es consecutivo por almacén y tipo. | Se sigue cumpliendo, pero se asigna **al sincronizar**: el orden de los folios puede no coincidir con el de la captura (OF-19). |
| E-28 | El borrador vive en el dispositivo y no cambia nada hasta confirmar. | Confirmar sin conexión **sí** cambia la base **local** (ajustes locales), pero no el servidor; la invariante 9 del modelo de datos sigue: nada llega a la base hasta que el servidor lo guarda. |
| A-01 a A-07 | El naranja necesita autorización del supervisor. | Sin conexión **no hay autorizaciones**: un naranja espera señal (OF-10). Si al sincronizar una regla que el equipo vio verde resulta naranja (por ejemplo, el límite), se guarda con aviso y va a revisión: **nadie autoriza después del hecho**, porque la entrega ya ocurrió (OF-21). |
| SM-04, E-02, E-19 | Un rojo no se entrega. | Si el equipo lo evaluó verde con sus datos y el servidor lo ve rojo por un cambio posterior (pieza marcada No apta en otro equipo, trabajador dado de baja, artículo inactivado), el vale **se guarda con aviso** porque la pieza ya está físicamente con el trabajador, y entra a revisión; en el caso de seguridad (E-05, E-06) con prioridad «Recuperar la pieza» (OF-21). Nunca se autoriza un rojo. |
| AC-13 | Un vale capturado en el almacén anterior se rechaza al confirmar (`ALMACEN_CAMBIO`). | La operación sin conexión se guarda **en el almacén del equipo** donde se capturó, aunque el usuario ya tenga otro almacén activo (OF-22). |

### O. Seguridad

- **Base cifrada** con SQLCipher; la llave, protegida por el Android Keystore (sección E). Sin la app, el archivo de la base no se lee.
- **Datos mínimos:** el paquete no trae costos, CURP, NSS, contraseñas ni PIN (sección E). Lo más sensible del equipo son los nombres, las fotos reducidas y las firmas de la cola.
- **Borrado remoto** al revocar el equipo, inactivar al usuario o cerrar todas sus sesiones (OF-05).
- **Equipo perdido o robado (CL-23):** el supervisor revoca el equipo y, en la misma pantalla, puede cerrar las sesiones de todos los usuarios registrados en él (sube su `version_sesion`, AC-22). Quien tenga el equipo necesita además un PIN local para entrar; con diez intentos fallidos la credencial se borra, y la ventana de 24 h limita cuánto puede operar contra datos locales. Nada de lo que capture llega al inventario: un equipo revocado manda sus lotes a conflictos (OF-24).
- **Bloqueo por inactividad.** En un equipo compartido, la app vuelve a pedir el PIN local tras 10 minutos sin uso (propuesta; la web no lo tiene, [security-model.md](../architecture/security-model.md) «Qué falta»). Ver «Decisiones abiertas».
- **El servidor no confía en el equipo:** vuelve a evaluar todo, toma del cuerpo solo los mismos datos que toma en línea (códigos y cantidades, A-02 y A-06), verifica que el responsable esté registrado en el equipo y nunca acepta del equipo un folio, una existencia ni un saldo.
- **Permisos en el servidor.** `sincronizacion.operar` y `sincronizacion.administrar` se declaran en cada `router.py`. Dentro del lote, el permiso de cada operación (`entregas.crear`, `devoluciones.crear`, `traspasos.recibir`, `piezas.inspeccionar`, `compras.solicitar`) se verifica en el servicio contra el **usuario que capturó**, porque depende del tipo de cada operación: es una ruta más que verifica en el servicio y hay que agregarla a la lista de AGENTS.md y de [security-model.md](../architecture/security-model.md).

### P. Lector Zebra

- **Hoy ya funciona.** Con DataWedge en **modo teclado** (salida por pulsaciones, sufijo Enter), el lector integrado se comporta como una pistola: `escaner.tsx` distingue la pistola por la velocidad (menos de ~30 ms entre teclas) y procesa el código al recibir Enter o Tab, sin tocar ningún campo. Hay que crear en DataWedge un perfil asociado al paquete de la app (por ejemplo `mx.imhotep.almacen`), con la salida de teclado y el sufijo Enter.
- **Mejora opcional: DataWedge por *intents*.** Un complemento de Capacitor recibe la difusión de DataWedge (acción configurada en el perfil) y la entrega a JavaScript como evento; `escaner.tsx` la procesa como `origen: "pistola"`. Ventajas: no depende del foco ni de la velocidad del teclado, no se mezcla con lo que se escribe y trae el tipo de código. Se hace solo si la prueba en el equipo real muestra lecturas perdidas en modo teclado.
- **Cámara.** `BarcodeDetector` necesita los servicios de Google en el WebView; en un Zebra sin ellos la cámara puede no estar disponible y se usa el lector integrado, que es lo normal en esos equipos. Un complemento con ML Kit empaquetado sería la alternativa si el track lo pide (ver «Decisiones abiertas»).

### Q. Notificaciones locales

- **Sin push dentro de la app en v1.** Las notificaciones push son para el supervisor por la PWA ([ADR-013](../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md)); la app del almacenista no las necesita y en equipos sin servicios de Google no llegarían (maestro, pregunta 3).
- **Notificaciones locales** con `@capacitor/local-notifications` (en Android 13 o superior la app pide el permiso de notificaciones la primera vez):
  - **Inspección por vencer** (P-15 de FEAT-016): calculada **del paquete**, con los días de aviso efectivos de cada artículo. Una vez al día, después de aplicar el paquete: «3 arneses vencen su inspección en los próximos 7 días». Al tocarla abre la lista de inspecciones.
  - **«Tienes 12 vales sin sincronizar»**: cuando la cola tiene operaciones de más de 2 horas, y al acercarse el límite de la ventana («En 2 horas ya no podrás operar sin señal»).
- No se programan alarmas exactas; basta la ventana aproximada de Android.

### R. Pantallas

| Pantalla | Dónde | Qué muestra |
|---|---|---|
| **Indicador de conexión** | Siempre visible en la barra superior de la app | «En línea» · «Sin conexión · datos de hace 2 h» · «Sincronizando 3 de 12» · «12 por sincronizar» · «Datos vencidos: busca señal». Al tocarlo: la edad de los datos, la última subida, el botón «Actualizar ahora» y el enlace a la cola. Color, icono y texto, no solo color (SM-02). |
| **Por sincronizar** (la cola) | Menú de la app | Cada operación con su tipo, trabajador, quién la capturó, hora de captura y estado: «Pendiente», «Enviando», «Guardado · MID-ENT-000245», «Guardado con aviso», «En revisión del supervisor», «Espera señal para aprobación», «Confirmación sin respuesta». Reimprimir el comprobante (con folio si ya lo tiene). No hay botón de borrar. |
| **Preparar este equipo** (inscripción) | Menú de la app, con `sincronizacion.operar` y señal | Nombre del equipo, almacén en que queda, resultado. Una sola vez por equipo. |
| **Crear PIN local** | Tras la primera entrada con señal en un equipo inscrito | Dos campos de 6 dígitos con el teclado numérico de la app, reglas en español llano. |
| **Entrar sin señal** | Pantalla «Entrar» sin conexión | Lista de usuarios con credencial local en el equipo y teclado numérico. |
| **Equipos** | Web y celular del supervisor, con `sincronizacion.administrar` | Lista de equipos de sus almacenes con su estado, usuarios registrados, última descarga y subida; revocar con motivo y, opcional, cerrar las sesiones de sus usuarios. |
| **Conflictos de sincronización** | Web del supervisor (primero computadora, D-20) | Lista y detalle (sección M). |
| Hora de descarga | Almacenes (Administrador) | Campo «Hora de descarga para equipos sin señal». |

Las rutas nuevas se registran en `routes.ts` y en [app-flow.md](../product/app-flow.md) al construirse; las de la app se muestran solo en la plataforma nativa.

---

## Reglas

| ID | Regla | Origen |
|---|---|---|
| OF-01 | La app de Android es la **misma interfaz** de `frontend/` empaquetada con Capacitor, con su carpeta nativa en `frontend/android/`; se distribuye como APK firmado por MDM o instalación directa, sin tienda, para Android 7 o superior con un WebView equivalente a Chrome 111 o superior. **En línea se comporta igual que la web**: mismas pantallas, mismas reglas, mismos endpoints. Sin conexión solo hace lo que dice esta feature. | D-15; ADR-014 |
| OF-02 | La app manda `X-App-Version` en cada petición. Si es menor que `APP_VERSION_MINIMA`, el servidor responde 426 `APP_DESACTUALIZADA` y la app pide actualizar. Excepción: `POST /api/sincronizacion/lotes` acepta el formato de lote de la versión anterior, para que una cola pendiente nunca quede atrapada por una actualización. Sin el encabezado (la web), no se revisa. | Maestro 5.1; propuesta |
| OF-03 | Con señal, un usuario con `sincronizacion.operar` inscribe el equipo en su almacén activo (`POST /api/dispositivos`). Un equipo pertenece a un solo almacén; un almacén puede tener varios equipos. Un equipo no inscrito solo opera en línea. Para cambiar de almacén se revoca y se inscribe de nuevo, después de subir su cola. | D-15; propuesta |
| OF-04 | El supervisor con `sincronizacion.administrar` ve los equipos de sus almacenes (`GET /api/dispositivos`) con quién los inscribió, sus usuarios, versión, última descarga y última subida, y los revoca con motivo (`POST /api/dispositivos/{id}/revocacion`). Inscripción y revocación quedan en `auditoria`. | Maestro 5.3 |
| OF-05 | Revocar el equipo borra **toda** su base local; inactivar al usuario, «cerrar todas» o restablecer su contraseña o PIN (cambia `version_sesion`) borran **su** credencial local. El borrado ocurre en la siguiente conexión del equipo y **después** de presentar la cola al servidor. | D-15; AC-22 |
| OF-06 | Cada usuario entra **con señal** al menos una vez en cada equipo, con su contraseña. Al hacerlo crea un PIN local de 6 dígitos, que se guarda solo en el equipo como derivación PBKDF2 con sal, y el servidor lo registra en el equipo. Nunca se descargan contraseñas, PIN ni sus hashes. | D-15; propuesta |
| OF-07 | Sin conexión solo entra quien tiene credencial local vigente en ese equipo. Cinco fallos la bloquean 5 minutos; diez la borran. Caduca a los 30 días sin entrar con señal en el equipo, o cuando el paquete dice que el usuario está inactivo, perdió `sincronizacion.operar` o cambió de almacén. Al cambiar de usuario sin señal se borran las cookies del anterior. | Propuesta; AC-18, AC-24 |
| OF-08 | Al caer la señal, la app pasa a «Sin conexión» con la primera petición que falle por red y vuelve a «En línea» tras dos respuestas buenas de `GET /api/salud` separadas por 5 s. El vale en captura conserva sus renglones y se vuelve a evaluar con el evaluador local, con el aviso de la edad de los datos. Un vale empezado sin conexión se termina sin conexión, salvo que la persona elija «Revisar en línea». | Maestro, sección 8 |
| OF-09 | Sin conexión siguen, por la cola «Por sincronizar», las operaciones que no piden aprobación: devolución, entrega de herramienta y de EPP con autonomía en verde o amarillo, recepción de traspasos descargados, inspección, No apta y solicitud de compra. Se firman, se confirman en el equipo y dan comprobante con QR y «Folio pendiente». Una operación de la cola **no se edita ni se borra**: se corrige después de subir, con cancelación. | Maestro, sección 8; RG-02 |
| OF-10 | Sin conexión **no se entrega** lo que pide aprobación: EPP de un almacén y un usuario sin autonomía, y cualquier renglón naranja (E-07, E-08, E-26). Esos renglones quedan en un borrador «Espera señal para aprobación»; lo demás se puede entregar ya (A-07). Al volver la señal, la app manda la solicitud y sigue el flujo en línea (D-08). Sin señal no hay autorización con PIN en el mostrador. | Maestro, sección 8; D-06, D-07 |
| OF-11 | Si una confirmación en línea salió y no llegó respuesta, la app no captura otro vale: pasa **el mismo** (mismo `id_cliente`, mismo cuerpo) a la cola como «Confirmación sin respuesta» y da comprobante con «Folio pendiente». La idempotencia del servidor decide al sincronizar si ya existía. | ADR-004; ADR-006 |
| OF-12 | Sin conexión no se puede: enviar traspasos, cancelar, emitir no adeudo, dar de alta o reingresar trabajadores, importar o dar entrada, ajustar vigencia, registrar serie, poner en mantenimiento o calibración, pedir o resolver autorizaciones, ni atender a un trabajador fuera del paquete. La pantalla dice «Necesitas señal para…». Única salida para un código fuera del paquete: la devolución de una **pieza** «Por verificar», con observación obligatoria, que el servidor evalúa al sincronizar. | Maestro, sección 8; SM-05 |
| OF-13 | El paquete (`GET /api/sincronizacion/paquete`) trae solo lo del almacén del equipo y de los trabajadores de sus proyectos y de los de sus almacenes hijos, más los que tienen pendientes con él (sección E). Nunca trae costos, CURP, NSS, contraseñas, PIN ni datos de otros almacenes fuera del resguardo de esos trabajadores. Viaja completo, comprimido, con `ETag`; responde 304 si no cambió; las fotos se piden aparte solo si cambió su `sha256`. | D-15; AC-05, AC-06, RG-12, RG-13 |
| OF-14 | El paquete se descarga al iniciar sesión o turno, a la hora del almacén (`almacen.hora_descarga`, aproximada), cada vez que vuelve la señal si tiene más de 30 minutos, y con «Actualizar ahora». Con señal, primero se sube la cola y luego se descarga; si quedan operaciones sin subir, sus ajustes locales se reaplican sobre el paquete nuevo. La pantalla muestra siempre «Datos de hace X». La hora la edita el Administrador. | D-15; propuesta |
| OF-15 | Se opera sin conexión hasta `SINCRONIZACION_HORAS_MAXIMAS` (24 h) desde la última descarga exitosa, medidas con el reloj monótono del equipo. Pasado eso, solo se consulta hasta sincronizar; un vale ya en captura se puede terminar. Si el reloj del equipo está antes de la última hora del servidor vista, se bloquea hasta sincronizar. | Maestro 5.1; propuesta |
| OF-16 | Sin conexión, el semáforo lo calcula un evaluador local en TypeScript con las **mismas reglas, IDs y textos** que el servidor, para el subconjunto de la sección J, con los datos del paquete más lo hecho sin conexión y la fecha del equipo. Cada regla del subconjunto tiene casos compartidos que corren pytest y vitest; una regla sin su caso compartido no se acepta. | Propuesta |
| OF-17 | **Excepción a RG-08.** Una operación capturada sin conexión no tuvo validación del servidor al capturarse. El servidor la revalida al sincronizar, con su fecha y las filas bloqueadas, y en vez de rechazarla por un cambio la clasifica: GUARDADO, GUARDADO_CON_AVISOS o CONFLICTO. | Maestro, sección 4 |
| OF-18 | **Excepción a RG-09.** Un lote no es todo o nada: cada operación va en su propia transacción y en orden de captura; una que va a conflicto no detiene a las demás. Cada operación sí es todo o nada. Las que dependen de una operación en conflicto (misma pieza, o mismo trabajador y artículo) van también a conflicto sin intentarse. | Maestro, sección 4 |
| OF-19 | **Excepción a RG-11 y nota a RG-06.** `creado_en` es la hora del servidor al sincronizar; `capturado_en` es la del equipo y se guarda aparte sin corregirse. Si al recibir el lote el reloj del equipo difiere del servidor en más de 10 minutos, o `capturado_en` es posterior a la hora del servidor, el vale se marca «Hora del equipo dudosa». La vigencia de una inspección capturada sin conexión se cuenta desde su fecha de captura. El folio se asigna al sincronizar y sigue consecutivo, aunque su orden no coincida con el de la captura. | Maestro, sección 4 |
| OF-20 | Si dos equipos sin conexión registran la **misma pieza** (por ejemplo, la entregan a dos trabajadores o la reciben dos veces), se guarda **el primero que sincroniza**; el segundo va a conflictos para el supervisor con el motivo `PIEZA_EN_OTRA_UBICACION` y el folio del vale que ganó. Nunca se guardan los dos (RG-05). | Maestro, sección 8 |
| OF-21 | Si al sincronizar una regla de **política** ya no se cumple (límite L-02 o L-03, vigencia E-02, artículo inactivo E-19, aprobación de despacho por autonomía apagada, proyecto cerrado PR-10, autorización por entrega E-26, o un aviso que pide observación y el equipo no pidió, como E-09), el vale **se guarda con avisos**, con sus IDs de regla, y entra a la lista de revisión con una observación automática; nadie lo autoriza después del hecho. Si es de **seguridad** (pieza No apta E-05 o inspección vencida E-06 al sincronizar), también se guarda, porque la pieza ya está con el trabajador, y entra a revisión como «Recuperar la pieza». Una inspección Apto capturada sin conexión no regresa a Apta una pieza que otro marcó No apta **después** de esa captura; una No apta capturada sin conexión siempre se aplica. | Propuesta; ADR-015 |
| OF-22 | Va a **conflicto** (`conflicto_sincronizacion`) lo que no se puede guardar sin romper una invariante: existencia insuficiente (RG-04, E-04), pieza en otra ubicación o ya no con ese trabajador (RG-05, E-03, V-02), recepción ya recibida o de más (X-12), traspaso cancelado (X-14), código, trabajador o artículo inexistente (E-01, V-12), almacén cerrado (AL-04), `id_cliente` con otro cuerpo, token repetido, forma inválida, usuario no registrado en el equipo y equipo revocado. Las operaciones se evalúan en el **almacén del equipo** donde se capturaron, aunque el usuario ya tenga otro almacén activo (excepción a AC-13). | Maestro, sección 8; RG-04, RG-05 |
| OF-23 | La cola sube con `POST /api/sincronizacion/lotes`: en orden de captura, hasta `SINCRONIZACION_LOTE_MAXIMO` (20) operaciones o unos 2 MB por lote, un lote a la vez, con reintentos de espera creciente y el mismo `lote_id`. Cada vale va al servicio de `movimientos` (único que escribe vales y existencias), cada inspección al de `inspecciones` y cada solicitud al de `solicitudes_compra`. Es idempotente por `id_cliente` y `huella_cuerpo`; reenviar un lote devuelve los mismos resultados sin duplicar nada. | D-15; maestro 5.2; ADR-006 |
| OF-24 | El responsable de cada operación es **quien la capturó**, aunque la suba otro usuario del equipo. El servidor la acepta solo si ese usuario está registrado en el equipo y el lote viene de un equipo inscrito, no revocado, de ese almacén. Si el usuario que capturó ya está inactivo, se guarda igual con aviso y queda en auditoría. Un lote de un **equipo revocado** no toca el inventario: cada operación va a conflictos con motivo `DISPOSITIVO_REVOCADO`, y la respuesta le ordena al equipo borrar sus datos. | RG-07; F-05; propuesta |
| OF-25 | Los conflictos los resuelve un supervisor con `sincronizacion.administrar` de ese almacén, que no sea quien capturó, desde «Conflictos de sincronización»: **reintentar**, **guardar sin los renglones en conflicto**, **guardar como diferencia** donde ya existe la regla (X-13) o **descartar**, siempre con motivo. Nunca se edita un vale guardado (RG-02): resolver crea un vale nuevo por `movimientos`. Todo queda en `auditoria`. | D-15; RG-02, A-05 |
| OF-26 | La base local es SQLite cifrada con una llave protegida por el Android Keystore; no guarda costos, CURP, NSS, contraseñas ni PIN; se borra por OF-05. El servidor no confía en el equipo: revalida todo y nunca acepta de él un folio, un saldo ni una existencia. | AC-05; RG-12, RG-13 |
| OF-27 | El comprobante de una operación sin conexión trae QR con el token generado en el equipo, «Folio pendiente» y la hora de captura, sin costos. El QR abre `/v/:token`, que dice «Pendiente de sincronizar» mientras el servidor no lo tiene, «En revisión del supervisor» si es conflicto y «No se guardó» si se descartó. El comprobante se da solo después de escribir la operación en la base local. | F-07, F-10, F-12 |
| OF-28 | El lector integrado de Zebra se usa por DataWedge en modo teclado con sufijo Enter, como una pistola; la recepción por *intents* con un complemento de Capacitor es una mejora opcional. | Propuesta |
| OF-29 | Sin notificaciones push en la app en v1. La app usa notificaciones locales para el aviso de inspección por vencer, calculado del paquete (P-15), y para «Tienes N vales sin sincronizar» y el fin cercano de la ventana. | ADR-013; propuesta |
| OF-30 | El Inicio del supervisor muestra cuántos conflictos de sincronización están pendientes y cuántos equipos de sus almacenes llevan más de `SINCRONIZACION_HORAS_MAXIMAS` sin subir (por `ultima_subida_en`) habiendo descargado datos después (por `ultimo_paquete_en`): «Equipo con vales posiblemente sin subir». | Propuesta |

---

## Recorridos acción por acción

### 1. Inscribir el equipo (una vez)

1. El almacenista abre la app con señal y entra con su usuario y contraseña (AC-14). La app ve que el equipo no está inscrito y que él tiene `sincronizacion.operar`: muestra «Preparar este equipo para trabajar sin señal».
2. Escribe el nombre del equipo («Zebra 2 Midrex»). La app manda `POST /api/dispositivos` con nombre, `plataforma: ANDROID`, versión y modelo.
3. El servidor revisa el permiso y el almacén activo (no cerrado, AL-04), crea `dispositivo` con `usuario_id` = quien inscribe y `almacen_id` = su almacén activo, registra al usuario en el equipo y responde el `id` y el secreto. Auditoría `dispositivo.inscribir`.
4. La app guarda el secreto cifrado, crea la base local cifrada, pide crear el PIN local (paso 2 del recorrido siguiente) y descarga el primer paquete con fotos. Muestra «Equipo listo: Midrex. Datos de hace 0 min».

### 2. Primera entrada de otro usuario en el equipo (con señal)

1. La almacenista del turno de noche entra con su contraseña en el Zebra 2. El servidor la registra en el equipo (por la cabecera `X-Dispositivo` de su primera petición de sincronización).
2. La app pide «Crea un PIN de 6 dígitos para entrar a este equipo cuando no haya señal». Lo escribe dos veces; la app rechaza `123456` con «Elige un PIN más difícil de adivinar».
3. La app guarda la derivación PBKDF2 con su sal y la marca «válida hasta 30 días sin entrar con señal».

### 3. Inicio de turno con señal

1. Entra con contraseña (o con la sesión que el equipo ya tenía, si es la misma persona).
2. La app sube la cola si hay algo (recorrido 10) y descarga el paquete con `If-None-Match`. Si responde 304, solo actualiza «Datos de hace 0 min».
3. Aplica el paquete (tablas de paso, transacción, reemplazo), reaplica ajustes locales pendientes si los hay, pide las fotos que cambiaron y programa la notificación local de inspecciones por vencer.

### 4. Entrega con señal (el caso de siempre)

Igual que en la web: escanea la credencial, ve la foto (F-11), escanea artículos, el servidor evalúa (`POST /api/vales/evaluar`), se piden las aprobaciones de EPP si hacen falta (FEAT-014), firma y confirma (`POST /api/vales`). El indicador dice «En línea». **Nada de esta feature interviene.**

### 5. Se cae la señal a media entrega

1. El almacenista escanea el tercer artículo; la evaluación falla por red. El indicador cambia a «Sin conexión · datos de hace 40 min».
2. Los tres renglones se vuelven a evaluar con el evaluador local; la pantalla avisa «Sin señal: revisado con los datos de hace 40 min».
3. Si los tres son herramienta en verde o amarillo, sigue al paso 4 del recorrido 6. Si uno es EPP de un almacén sin autonomía, sigue el recorrido 7.

### 6. Entrega sin conexión con autonomía (o de herramienta)

1. Escanea la credencial: el evaluador local busca el código en el paquete, muestra la foto reducida, la vigencia (E-02 con la fecha del equipo) y el resguardo (E-17). Si el trabajador no está en el paquete: «Este trabajador no está en los datos de tu almacén. Necesitas señal para entregarle» (OF-12).
2. Si tiene dos proyectos del almacén, aparece el selector (PR-09).
3. Escanea artículos: semáforo local con las reglas de la sección J, límites con lo descargado más lo entregado hoy sin conexión.
4. Los amarillos que piden observación la piden (E-09); los que piden confirmar cantidad la piden (E-27).
5. El trabajador firma en pantalla (F-02).
6. «Confirmar»: la app genera `id_cliente`, token, `capturado_en` y secuencia; en **una transacción local** guarda la operación en la cola con la firma y aplica los ajustes locales (existencia, pieza al trabajador, consumo).
7. Muestra el comprobante con QR y «Folio pendiente». La cola dice «1 por sincronizar».

### 7. Entrega de EPP sin autonomía, sin conexión

1. Igual que el recorrido 6 hasta el paso 3. El renglón de EPP sale «Necesita aprobación del supervisor: espera señal».
2. La app ofrece «Entregar lo demás ahora» y «Guardar para cuando haya señal».
3. «Guardar para cuando haya señal» deja un borrador en «Espera señal para aprobación» (no es un vale, no hay firma, no hay comprobante, no se mueve nada). El trabajador no se lleva ese EPP.
4. Al volver la señal, la app avisa «Hay 1 entrega esperando aprobación»; al abrirla, se reevalúa en línea y se manda la solicitud (FEAT-014). Desde ahí es el flujo normal.

### 8. Devolución sin conexión

1. Escanea la pieza: el paquete dice quién es el titular (V-01); si está en resguardo de un trabajador del paquete, verde.
2. Si el código no está en el paquete: renglón amarillo «No se puede verificar sin señal», pide trabajador (si lo hay) y observación. Queda «Por verificar» (OF-12).
3. Condición obligatoria (V-04); dañado pide observación y admite foto (V-05).
4. Confirmar: transacción local con la operación y los ajustes (la pieza regresa al almacén, o a No apta si está dañada). Comprobante con «Folio pendiente» (V-11, F-08).

### 9. Recibir un traspaso sin conexión

1. Escanea el QR del traspaso: el token está en `traspasos_en_transito` del paquete. Si no está: «Este traspaso no está en tus datos. Necesitas señal para recibirlo».
2. «Recibir todo», por renglón o escaneando (X-11, X-15). Lo que falte pide observación (X-13, RG-14).
3. Confirmar: transacción local; las existencias locales suben y el traspaso local deja de tener pendiente lo recibido.

### 10. Vuelve la señal: subida de la cola

1. `@capacitor/network` avisa; dos `GET /api/salud` buenas confirman. El indicador pasa a «Sincronizando 0 de 12».
2. Si el usuario local no tiene sesión en línea (cambió sin señal), la app pide su contraseña; mientras tanto, si otro usuario registrado tiene sesión, la cola sube con ella (OF-24).
3. Sale el lote 1 (20 operaciones o 2 MB). El servidor procesa cada una en su transacción y responde.
4. La app marca cada operación: GUARDADO con folio, GUARDADO_CON_AVISOS con su aviso, CONFLICTO «En revisión del supervisor». Retira los ajustes locales de las que ya resolvió el servidor.
5. Siguiente lote, hasta vaciar la cola. Luego descarga el paquete (si tiene más de 30 minutos) y aplica.
6. Notificación local si quedó algo en revisión: «2 vales quedaron en revisión del supervisor».

### 11. El supervisor resuelve un conflicto

1. En su Inicio ve «Conflictos de sincronización: 1». Abre la lista y el conflicto: «Entrega de ALT-003 a Luis Gómez, capturada sin señal en Zebra 2 a las 21:02. La pieza ya estaba con Pedro Ruiz por MID-ENT-000245 (Zebra 1, 20:40)».
2. Llama al almacén, confirman que en Zebra 2 escanearon la etiqueta equivocada (era ALT-004).
3. Elige «Descartar» con motivo «Se escaneó ALT-003 por error; la entregada fue ALT-004» y, por separado, el almacenista registra en línea la entrega real de ALT-004 (o el supervisor elige «Guardar sin los renglones en conflicto» si el vale traía más renglones).
4. El conflicto queda DESCARTADO con su motivo; auditoría `sincronizacion.resolver_conflicto`. El QR del comprobante ahora dice «Este vale no se guardó: se registró por error una pieza distinta».

### 12. Cambio de turno en el mismo equipo

1. El de día toca «Salir». Con señal: se cierra su sesión del servidor (AC-19). Sin señal: se cierra la sesión local y se borran sus cookies del almacén nativo; la cola se queda.
2. La de noche entra: con señal, con contraseña; sin señal, con su PIN local (si ya tiene credencial en ese equipo).
3. Lo que capture va a su nombre. La cola mezcla operaciones de los dos, cada una con su responsable, en orden de captura.

### 13. Revocar un equipo perdido

1. El supervisor abre Equipos, elige «Zebra 2 Midrex», «Revocar», motivo «Extraviado en el contenedor», y marca «Cerrar también las sesiones de sus usuarios».
2. El servidor pone `revocado_en` y `revocado_por`, sube la `version_sesion` de los usuarios registrados en el equipo (AC-22) y deja auditoría.
3. Si el equipo vuelve a conectarse: sus lotes van a conflictos (`DISPOSITIVO_REVOCADO`), la respuesta ordena borrar y la app borra toda la base local y vuelve a la pantalla de entrar.

---

## Fuera de alcance

- Operación sin conexión en la **web** o en la PWA: sigue «primero en línea» (ADR-004, ADR-015).
- App para iPhone, publicación en tiendas, app distinta de la interfaz web (maestro, sección 6).
- Deltas del paquete (v1 descarga completo).
- Autorizaciones sin conexión de cualquier tipo, también con PIN en el mostrador.
- Enviar traspasos, cancelar, no adeudo, altas de trabajadores, importación, ajuste de vigencia, serie, mantenimiento y calibración sin conexión.
- Operación sin conexión en el almacén central (Kepler), salvo que el usuario decida lo contrario.
- Notificaciones push dentro de la app; biometría para entrar; impresión directa a impresoras térmicas.
- Resolución automática de conflictos: siempre la decide una persona.
- Recuperar una cola de un equipo desinstalado o con los datos borrados.

## Criterios de aceptación

| ID | Criterio | Reglas |
|---|---|---|
| CA-01 | Dado el repositorio, cuando se corre `pnpm build`, `pnpm exec cap sync android` y Gradle en `frontend/android/`, entonces se obtiene un APK firmado que muestra la misma interfaz de la web, y en línea entrega, devuelve y recibe exactamente como la web. | OF-01 |
| CA-02 | Dada la app con versión menor que `APP_VERSION_MINIMA`, cuando hace cualquier petición, entonces recibe 426 `APP_DESACTUALIZADA` y ve «Hay una versión nueva…»; y dado un lote pendiente con el formato anterior, cuando lo sube, entonces el servidor lo acepta. | OF-02 |
| CA-03 | Dada la prueba de concepto de sesión, cuando se entra desde el APK contra el servidor por HTTPS, vence el token de acceso y se renueva, entonces la operación sigue sin pedir contraseña, `document.cookie` no muestra ningún token y al salir la familia queda revocada en la base. | OF-01; AC-14 a AC-24 |
| CA-04 | Dado un almacenista con `sincronizacion.operar` y señal, cuando inscribe el equipo, entonces queda en su almacén activo, el supervisor lo ve en Equipos y hay un registro en auditoría; y dado un usuario sin el permiso, entonces `POST /api/dispositivos` responde 403. | OF-03, OF-04 |
| CA-05 | Dado un usuario que nunca entró con señal en el equipo, cuando no hay conexión, entonces no aparece en «Entrar sin señal» y no puede entrar. | OF-06, OF-07 |
| CA-06 | Dados dos usuarios con credencial local en el mismo equipo, cuando el segundo entra sin señal con su PIN, entonces lo que captura queda a su nombre y las cookies del primero ya no están en el equipo. | OF-07, OF-24 |
| CA-07 | Dado un PIN local equivocado cinco veces, entonces esa credencial se bloquea 5 minutos; y dado diez veces, entonces se borra y el usuario necesita señal para volver a entrar. | OF-07 |
| CA-08 | Dado el paquete de Midrex descargado, cuando se inspecciona la base local, entonces no hay costos, CURP, NSS, contraseñas, PIN ni existencias de otros almacenes, y sí está el resguardo completo de los trabajadores de sus proyectos. | OF-13 |
| CA-09 | Dado el paquete de Contratistas, entonces incluye a los trabajadores de los proyectos de sus almacenes hijos. | OF-13; D-13 |
| CA-10 | Dado un paquete sin cambios, cuando la app lo pide con `If-None-Match`, entonces el servidor responde 304 y la pantalla actualiza «Datos de hace 0 min». | OF-13, OF-14 |
| CA-11 | Dada la señal que vuelve con un paquete de más de 30 minutos y cola pendiente, entonces primero sube la cola y luego descarga; y con un paquete de menos de 30 minutos, solo sube. | OF-14 |
| CA-12 | Dado un paquete descargado hace más de 24 h (por el reloj monótono), cuando el almacenista intenta una entrega nueva sin conexión, entonces la app la bloquea y solo deja consultar. | OF-15 |
| CA-13 | Dado un reloj del equipo atrasado respecto de la última hora del servidor vista, cuando se intenta operar sin conexión, entonces la app bloquea hasta sincronizar. | OF-15 |
| CA-14 | Dado un vale en captura en línea, cuando se cae la señal, entonces sus renglones se conservan y se reevalúan con el evaluador local con el aviso de la edad de los datos. | OF-08 |
| CA-15 | Dada una entrega de herramienta sin conexión con renglones verdes, cuando se firma y confirma, entonces se da un comprobante con QR y «Folio pendiente», la cola suma una operación y la existencia local baja. | OF-09, OF-27 |
| CA-16 | Dado un almacén sin autonomía, cuando sin conexión se escanea EPP, entonces el renglón queda «Necesita aprobación del supervisor: espera señal», no se puede firmar ese renglón y lo demás sí se puede entregar. | OF-10 |
| CA-17 | Dado un renglón que excede el límite (E-07) sin conexión, entonces no se entrega y queda en «Espera señal para aprobación». | OF-10 |
| CA-18 | Dada una confirmación en línea sin respuesta, cuando se sincroniza, entonces no hay dos vales: si el servidor ya lo tenía, la cola muestra su folio original. | OF-11 |
| CA-19 | Dado un trabajador fuera del paquete, cuando se intenta entregarle sin conexión, entonces la app dice «Necesitas señal para entregarle»; y cuando se intenta enviar un traspaso, cancelar o emitir no adeudo sin conexión, entonces dice «Necesitas señal para…». | OF-12 |
| CA-20 | Dados los casos compartidos de cada regla del subconjunto, cuando corren pytest y vitest, entonces los dos evaluadores dan el mismo nivel y las mismas reglas en cada caso. | OF-16 |
| CA-21 | Dadas 45 operaciones en cola, cuando vuelve la señal, entonces suben en tres lotes de 20, 20 y 5, uno a la vez, en orden de captura. | OF-23 |
| CA-22 | Dado un lote cuya respuesta se perdió, cuando la app lo reenvía con el mismo `lote_id`, entonces el servidor devuelve los mismos resultados y no crea ningún vale, movimiento ni inspección de más. | OF-23 |
| CA-23 | Dado un lote con una operación en conflicto en medio, entonces las demás se guardan y la que depende de la misma pieza va a conflicto `DEPENDE_DE_CONFLICTO`. | OF-18 |
| CA-24 | Dado un vale sincronizado, entonces `creado_en` es la hora del servidor, `capturado_en` la del equipo, `capturado_sin_conexion` es verdadero, `dispositivo_id` es el del equipo y el folio es el siguiente consecutivo del almacén y tipo. | OF-19 |
| CA-25 | Dado un equipo con el reloj 2 horas adelantado, cuando sube un lote, entonces sus vales quedan marcados «Hora del equipo dudosa». | OF-19 |
| CA-26 | Dados dos equipos sin conexión que entregan la misma pieza a dos trabajadores, cuando sincronizan, entonces se guarda el primero y el segundo queda en conflicto `PIEZA_EN_OTRA_UBICACION` con el folio del primero. | OF-20 |
| CA-27 | Dada una entrega de guantes sin conexión que, al sincronizar, rebasa L-03 por una entrega hecha en otro almacén mientras tanto, entonces se guarda con aviso `L-03` y aparece en la lista de revisión con su observación automática. | OF-21 |
| CA-28 | Dada una pieza marcada No apta en línea después de que otro equipo la entregó sin conexión, cuando ese equipo sincroniza, entonces la entrega se guarda con aviso «Recuperar la pieza»; y dada una inspección Apto sin conexión anterior a esa No apta, entonces la pieza sigue No apta. | OF-21 |
| CA-29 | Dada una recepción sin conexión de un traspaso que el origen canceló mientras tanto, cuando se sincroniza, entonces va a conflicto `TRASPASO_CANCELADO` y no cambia ninguna existencia. | OF-22 |
| CA-30 | Dado un usuario que cambió de almacén activo con cola pendiente, cuando la cola sube, entonces sus vales se guardan en el almacén del equipo, no en el nuevo. | OF-22 |
| CA-31 | Dado un vale capturado por la usuaria de noche y subido con la sesión del usuario de día, entonces el responsable del vale es la de noche; y dado un `responsable_id` que no está registrado en el equipo, entonces va a conflicto. | OF-24 |
| CA-32 | Dado un equipo revocado con cola pendiente, cuando se conecta, entonces sus operaciones quedan en conflictos `DISPOSITIVO_REVOCADO`, ninguna existencia cambia, y la app borra su base local. | OF-05, OF-24 |
| CA-33 | Dado un usuario inactivado con operaciones en cola, cuando el equipo se conecta, entonces sus operaciones se guardan con aviso y quedan en auditoría, y luego se borra su credencial local. | OF-05, OF-24 |
| CA-34 | Dado un supervisor de Midrex, cuando abre Conflictos, entonces ve solo los de los equipos de Midrex; y dado un conflicto que él mismo capturó, entonces no puede resolverlo. | OF-25 |
| CA-35 | Dado un conflicto resuelto con «Guardar sin los renglones en conflicto», entonces se crea un vale nuevo por `movimientos` con la hora de captura original y el responsable original, el conflicto queda RESUELTO con `vale_id`, y ningún vale existente cambia. | OF-25; RG-02 |
| CA-36 | Dado el QR de un comprobante sin conexión, cuando se abre `/v/:token` antes de sincronizar, entonces dice «Pendiente de sincronizar»; después, muestra el vale con su folio; y si se descartó, «Este vale no se guardó». | OF-27 |
| CA-37 | Dado el Zebra con DataWedge en modo teclado, cuando se dispara el lector en Entregar sin tocar ningún campo, entonces el código entra como lectura de pistola. | OF-28 |
| CA-38 | Dado un paquete con piezas que vencen su inspección en los próximos días de aviso, entonces aparece una notificación local; y dada una cola con operaciones de más de 2 horas, aparece «Tienes N vales sin sincronizar». | OF-29 |
| CA-39 | Dado un equipo de Midrex que descargó datos hace 30 h y no sube desde hace 30 h, entonces el Inicio del supervisor de Midrex lo muestra como «Equipo con vales posiblemente sin subir». | OF-30 |
| CA-40 | Dado un paquete que llega dañado (huella distinta o descompresión fallida), entonces la app conserva el anterior y dice «No se pudo actualizar; sigues con los datos de hace X». | OF-14 |

## Casos límite

| ID | Caso | Qué pasa | Reglas |
|---|---|---|---|
| CL-01 | **Batería muerta con cola sin subir.** | La cola está en SQLite y cada operación se escribió en una transacción confirmada antes de dar el comprobante: al encender, sigue ahí. Lo que se pierde es solo lo que no se confirmó (el borrador también se conserva). La ventana de 24 h sigue corriendo con el reloj del equipo tras el reinicio (OF-15). | OF-09, OF-15 |
| CL-02 | **Desinstalar la app (o borrar sus datos) con cola pendiente.** | Android no avisa a la app antes de desinstalarla. La app muestra un aviso permanente cuando hay cola («No desinstales ni borres los datos: hay 12 vales sin subir»); el MDM puede impedir la desinstalación. Si aun así se desinstala, **los datos se pierden**. El supervisor lo descubre por OF-30 (descargó datos y no sube) y por los trabajadores con comprobante cuyo QR dice «Pendiente» sin fin; se registran de nuevo en línea, con observación, a partir de los comprobantes. | OF-30, OF-27 |
| CL-03 | **Reloj del equipo mal** (adelantado, atrasado, zona equivocada o cambiado a mano). | `capturado_en` se guarda tal cual. La ventana usa el reloj monótono; un reloj anterior a la última hora del servidor bloquea. Al subir, el desfase de más de 10 minutos marca los vales. El servidor revalida vigencias con su propia fecha (OF-17). | OF-15, OF-19 |
| CL-04 | **Dos equipos del mismo almacén sin conexión entregan un artículo por cantidad.** | Cada uno ve la existencia completa del paquete. Si entre los dos entregan más de lo que había, el primero que sube se guarda y el segundo va a conflicto `EXISTENCIA_INSUFICIENTE`. Físicamente no puede pasar salvo que el sistema tuviera menos de lo real (un traspaso sin recibir, una entrada atrasada): el supervisor arregla la causa y reintenta. | OF-20, OF-22; RG-04 |
| CL-05 | **Dos equipos registran la misma pieza.** | Gana el primero que sincroniza; el segundo va a conflicto con el folio del ganador (OF-20). | OF-20; RG-05 |
| CL-06 | **Entrega a un trabajador que dejó de ser vigente mientras el equipo estaba sin conexión** (RH inició su baja). | El equipo no lo sabía y entregó. Al sincronizar, E-02 sale rojo; como la entrega ya ocurrió, se guarda con aviso E-02 y entra a revisión («Entregado a un trabajador en baja: recuperar»). Si su contrato vencía a medianoche, el evaluador local sí lo ve con la fecha del equipo y no entrega. | OF-21; E-02 |
| CL-07 | **Artículo inactivado mientras el equipo estaba sin conexión.** | Se guarda con aviso E-19 y entra a revisión. La devolución de un inactivo sigue permitida (CF-11). | OF-21; E-19 |
| CL-08 | **Autonomía apagada mientras el equipo estaba sin conexión.** | El equipo entregó EPP con la autonomía del paquete. Se guarda con el aviso de despacho de FEAT-014 («Entregado sin aprobación con datos atrasados») y entra a revisión. No hay aprobación después del hecho. | OF-21; D-07 |
| CL-09 | **Traspaso cancelado en el origen mientras se recibía sin conexión.** | Va a conflicto `TRASPASO_CANCELADO` y no cambia nada: el origen ya regresó la existencia a su almacén (X-14), así que aceptarlo duplicaría. El supervisor del destino coordina con el origen: el origen envía un traspaso nuevo y el destino lo recibe; el conflicto se descarta con ese motivo. | OF-22; X-14 |
| CL-10 | **Pieza marcada No apta por otro equipo, luego entregada sin conexión por éste.** | Se guarda con aviso de seguridad E-05 y entra a revisión «Recuperar la pieza». Nunca se autoriza el rojo; se registra lo que pasó para poder recuperarla. | OF-21; SM-04 |
| CL-11 | **Paquete corrupto** (descarga interrumpida, huella distinta, JSON inválido, `gzip` dañado). | No se aplica; se conserva el anterior y se reintenta en la siguiente ocasión. Si no hay ninguno (primera descarga), no se opera sin conexión. | OF-14 |
| CL-12 | **Actualización de la app con cola pendiente.** | Actualizar un APK conserva los datos. Al arrancar la versión nueva, primero migra la base local (`PRAGMA user_version`) y después hace cualquier otra cosa. Si la migración falla, la app queda en solo consulta y sube la cola en su formato original (el servidor acepta el formato anterior, OF-02). | OF-02 |
| CL-13 | **Cambio de almacén activo con cola pendiente.** | La cola sube con su almacén original (el del equipo, OF-22), no con el nuevo. Mientras el almacén activo del usuario no sea el del equipo, ese usuario no opera sin conexión en ese equipo y la app lo avisa. | OF-22; AC-13 |
| CL-14 | **Usuario inactivado con cola pendiente.** | La cola sí se sube: se guarda con aviso «Capturado por un usuario que hoy está inactivo» y queda en auditoría. Después se borra su credencial local. | OF-05, OF-24 |
| CL-15 | **Cambio de turno en el mismo equipo sin señal.** | Recorrido 12. Cada operación queda a nombre de quien la capturó; las cookies del anterior se borran. | OF-07, OF-24 |
| CL-16 | **Llega un almacenista nuevo sin señal y nunca entró en ese equipo.** | No puede entrar sin conexión. Usa otro equipo con señal, espera señal, o el compañero del turno anterior sigue operando. No hay forma de dar de alta una credencial sin señal. | OF-06, OF-07 |
| CL-17 | **Conflicto que arrastra otras operaciones.** | Una entrega de ALT-003 en conflicto y luego su devolución en el mismo equipo: la devolución va a `DEPENDE_DE_CONFLICTO`. El supervisor resuelve primero la entrega y luego reintenta la devolución. | OF-18 |
| CL-18 | **Se pierde la respuesta de un lote** (el servidor guardó, la señal se fue). | La app reenvía el mismo lote; el servidor responde lo mismo por idempotencia: no hay vales ni inspecciones duplicados. | OF-23 |
| CL-19 | **Señal intermitente** (aparece y desaparece cada pocos segundos). | Se pasa a «Sin conexión» con el primer fallo y a «En línea» solo tras dos `/api/salud` buenas separadas por 5 s; un vale empezado sin conexión se termina sin conexión. Un lote a la vez y reintentos con espera creciente evitan saturar la red. | OF-08, OF-23 |
| CL-20 | **Confirmación en línea sin respuesta.** | El mismo vale pasa a la cola (OF-11); nunca se capturan dos. | OF-11 |
| CL-21 | **Devolución de una pieza cuyo código no está en el paquete.** | Se recibe «Por verificar» con observación. Al sincronizar: si la pieza existe y la tiene un trabajador, se guarda (V-01); si no existe, conflicto (V-12) y el supervisor decide qué hacer con el equipo ajeno que está en el almacén. | OF-12, OF-22 |
| CL-22 | **Se cumplen las 24 h a media captura.** | El vale en captura se puede terminar; no se pueden empezar vales nuevos. | OF-15 |
| CL-23 | **Equipo perdido o robado.** | Recorrido 13. Base cifrada, PIN local, ventana de 24 h y lotes a conflictos. | OF-04, OF-05, OF-24, OF-26 |
| CL-24 | **Equipo revocado por error con cola pendiente.** | Sus operaciones llegan como conflictos `DISPOSITIVO_REVOCADO`; el supervisor las reintenta una por una (se guardan normalmente) y el equipo se inscribe de nuevo. Nada se perdió. | OF-24, OF-25 |
| CL-25 | **Límite rebasado por una entrega en otro almacén mientras tanto.** | Guardado con aviso L-02 o L-03 y a revisión. | OF-21 |
| CL-26 | **El mismo traspaso recibido en dos equipos sin conexión.** | El primero se guarda; el segundo va a conflicto `YA_RECIBIDO` (X-12). Si el segundo recibió además renglones que el primero no, el supervisor elige «Guardar sin los renglones en conflicto». | OF-20, OF-22; X-12 |
| CL-27 | **Devolución sin conexión de una pieza que el trabajador ya devolvió en otro almacén con señal.** | Al sincronizar la pieza ya no está con él: conflicto `PIEZA_EN_OTRA_UBICACION`. Uno de los dos registros está mal (físicamente solo una devolución pudo ocurrir); el supervisor lo aclara con el otro almacén. | OF-20, OF-22; V-02 |
| CL-28 | **Entrega y devolución de lo mismo, ambas sin conexión, antes de subir.** | La secuencia las ordena; el servidor procesa la entrega y luego la devolución, como pasó. | OF-23 |
| CL-29 | **Se quiere cancelar un vale que sigue en la cola.** | No se puede: el vale aún no está en el servidor y la cola no se edita. Se cancela cuando se suba (K-01 a K-05); la app lo dice: «Se podrá cancelar cuando se sincronice». | OF-09, OF-12 |
| CL-30 | **Devolución con foto de daño grande.** | Si sola pasa de 2 MB, sale sola en su lote. Los límites de tamaño de la foto son los de siempre (3 MB por foto, 10 MB por vale). | OF-23 |
| CL-31 | **Equipo sin espacio.** | Si la escritura local falla, la app no da comprobante y lo dice. Con menos de 200 MB libres avisa al iniciar turno. | OF-27 |
| CL-32 | **Supervisor con `sincronizacion.operar` captura sin conexión y su operación va a conflicto.** | No la puede resolver él; la resuelve otro supervisor del almacén o el Administrador (como A-05). | OF-25 |
| CL-33 | **El trabajador escanea el QR antes de que se sincronice.** | `/v/:token` dice «Pendiente de sincronizar» (con sesión, ver «Decisiones abiertas»). | OF-27 |
| CL-34 | **La hora de descarga cae con el equipo apagado o sin señal.** | WorkManager la corre cuando se cumplen las condiciones; si ya pasó el inicio de turno, la descarga al entrar la cubre. | OF-14 |
| CL-35 | **Llega un paquete nuevo con cola pendiente.** | Se aplica y se reaplican encima los ajustes locales de lo que no ha subido; así la existencia que ve el almacenista no «regresa» lo ya entregado. | OF-14 |
| CL-36 | **Inspección Apto sin conexión y No apta en línea posterior** (o al revés). | Una Apto capturada sin conexión no levanta una No apta registrada después de su captura; una No apta sin conexión siempre se aplica (P-03: solo una inspección nueva la regresa a Apta). Ambas quedan en el historial. | OF-21 |
| CL-37 | **Trabajador con dos proyectos, uno cerrado mientras el equipo estaba sin conexión.** | Si eligió el cerrado, se guarda con aviso PR-10 y cuenta según la regla de FEAT-013. | OF-21 |
| CL-38 | **Sesión en línea vencida (7 días sin uso o tope de 30) al volver la señal.** | La cola espera hasta que un usuario registrado en el equipo entre con contraseña. No se pierde nada. | OF-07, OF-24 |
| CL-39 | **WebView viejo en el Zebra.** | La app lo detecta al arrancar y pide actualizar Android System WebView en vez de mostrar una interfaz rota. | OF-01 |
| CL-40 | **Equipo inscrito en Midrex usado por un almacenista con almacén activo Contratistas.** | En línea opera Contratistas como siempre. Sin conexión no opera: «Este equipo es de Midrex; sin señal solo puede operar ese almacén». | OF-03, OF-22 |
| CL-41 | **Paquete descargado por un usuario y operado por otro sin conexión.** | El paquete es del equipo y del almacén; trae a todos los usuarios registrados con sus permisos y autonomía, así que el evaluador usa los del que captura. | OF-13, OF-16 |
| CL-42 | **El almacén se cierra (AL-03) mientras un equipo está sin conexión.** | AL-03 exige existencias en cero y sin traspasos en tránsito, así que es raro; si pasa, las operaciones van a conflicto `ALMACEN_CERRADO`. | OF-22; AL-04 |

## Módulos relacionados conocidos

- **`sincronizacion`** (módulo nuevo, maestro 5.2): `router.py` (paquete, lotes, dispositivos, conflictos), `service.py`, `repository.py`, `models.py` (`dispositivo`, `conflicto_sincronizacion` y lo propuesto), `schemas.py`, `exceptions.py`. Lee de `catalogo`, `trabajadores`, `almacenes`, `proyectos`, `movimientos` (existencias, traspasos en tránsito, consumo) e `inspecciones` para armar el paquete. **No escribe** vales, movimientos, existencias, piezas ni inspecciones.
- **`movimientos`**: camino de confirmación para vales sincronizados (almacén del equipo, token del equipo, `capturado_sin_conexion`, `capturado_en`, `dispositivo_id`, clasificación en vez de `VALE_CAMBIO`). `huella_del_cuerpo` incluye los campos nuevos. El folio se asigna como siempre.
- **`inspecciones`**: registrar una inspección o una No apta llegada por sincronización, con su fecha de captura y la regla de orden de OF-21.
- **`solicitudes_compra`**: sin cambios de regla; recibe la solicitud por el servicio con su `id_cliente`.
- **`acceso`**: el middleware de versión de la app (426), el registro del usuario en el equipo al entrar, y subir `version_sesion` desde la revocación.
- **`almacenes`**: `almacen.hora_descarga` en el alta y edición.
- **`auditoria`**: acciones `dispositivo.inscribir`, `dispositivo.revocar`, `sincronizacion.lote` (resumen por lote), `sincronizacion.resolver_conflicto`.
- **`consulta`**: `/v/:token` (vista pública o con sesión del vale) con los estados de OF-27; lista de revisión con lo guardado con avisos.
- **Frontend:** `capacitor.config.ts`; `frontend/android/` (complemento nativo propio: WorkManager, reloj monótono, opcional DataWedge por *intents*); `app/api/cliente.ts` (base absoluta, `X-App-Version`, `X-Dispositivo` en las rutas de sincronización); `app/api/red.ts` (estado con `/api/salud`); `app/pwa/registrar.ts` (no registrar en nativo); `app/sin-conexion/` (base local, cola, paquete, evaluador, credencial local); `app/componentes/dominio/escaner.tsx` (sin cambios para el modo teclado); `app/sesion/` (entrar sin señal, cambio de usuario); pantallas nuevas de la sección R; `routes.ts`.

## Cambios de datos o API esperados

### Tablas y columnas (migraciones de Alembic)

| Tabla o columna | Detalle |
|---|---|
| `dispositivo` | Como en el maestro: `id`, `usuario_id` (quien lo inscribió), `almacen_id`, `nombre`, `plataforma` (ANDROID), `version_app`, `registrado_en`, `ultimo_paquete_en`, `ultima_subida_en`, `revocado_en`, `revocado_por`. **Propuesto:** `secreto_hash` (SHA-256 del secreto del equipo, único) y `motivo_revocacion`. Índices por `almacen_id` y por `revocado_en`. |
| `conflicto_sincronizacion` | Como en el maestro: `id`, `dispositivo_id`, `usuario_id` (quien capturó), `id_cliente` (único), `tipo_operacion` (el tipo de la operación: ENTREGA, DEVOLUCION, RECEPCION, INSPECCION, NO_APTA o SOLICITUD_COMPRA), `cuerpo` (JSON de la operación, con la firma como referencia a un archivo del volumen, no en la base), `motivo` (código), `detalle` (JSON con lo que dijo el servidor por renglón y el vale con que chocó), `estado` (PENDIENTE, RESUELTO, DESCARTADO), `resuelto_por` (distinto de `usuario_id`, CHECK como en `autorizacion`), `resolucion` (JSON: opción y motivo), `vale_id`, `creado_en`, `resuelto_en`. Solo se inserta y se actualiza su resolución una vez. |
| `vale.capturado_sin_conexion` (bool, `false`), `vale.capturado_en` (UTC, nulo en línea), `vale.dispositivo_id` (FK a `dispositivo`, nulo en línea) | Se escriben al insertar y no cambian (invariante 5). `vale.dispositivo` (el agente del navegador, que ya existe) se conserva. |
| `almacen.hora_descarga` (TIME, nulo) | Hora del centro de México. |
| **Propuesto:** `dispositivo_usuario` (`dispositivo_id`, `usuario_id`, `version_sesion`, `registrado_en`, `ultima_entrada_en`) | Los usuarios que entraron con señal en el equipo. Sostiene OF-06, OF-07, OF-24 y el borrado por `version_sesion` (OF-05). No está en el maestro: ver «Decisiones abiertas». |
| **Propuesto:** registro de operaciones recibidas (por ejemplo, `operacion_recibida`: `id_cliente` único, `dispositivo_id`, `tipo`, `resultado`, `entidad_id`, `folio`, `avisos`, `recibido_en`) | Idempotencia de las inspecciones y No apta (no tienen `id_cliente`) y respuesta igual al reenviar un lote. Alternativa: `id_cliente` en `inspeccion` y `evento_pieza`. Ver «Decisiones abiertas». |

### Endpoints

| Endpoint | Permiso | Qué hace |
|---|---|---|
| `POST /api/dispositivos` | `sincronizacion.operar` | Inscribe el equipo en el almacén activo; 201 con `id` y `secreto` (una sola vez). 409 `ALMACEN_CERRADO`. |
| `GET /api/dispositivos` | `sincronizacion.administrar` | Equipos de sus almacenes con estado, usuarios y fechas. |
| `POST /api/dispositivos/{id}/revocacion` | `sincronizacion.administrar` | `{motivo, cerrar_sesiones}`; motivo obligatorio (422). 409 si ya estaba revocado. |
| `GET /api/sincronizacion/paquete` | `sincronizacion.operar` (+ `X-Dispositivo`) | Paquete comprimido con `ETag`; 304 con `If-None-Match`. Actualiza `ultimo_paquete_en` y registra al usuario en el equipo. 403 `DISPOSITIVO_REVOCADO` (con la orden de borrar), `DISPOSITIVO_NO_INSCRITO`, `DISPOSITIVO_DE_OTRO_ALMACEN`. |
| `POST /api/sincronizacion/lotes` | `sincronizacion.operar` (+ `X-Dispositivo`) | Sube un lote (sección L). 200 con un resultado por operación. Límite de cuerpo: 12 MB, como los vales. |
| `GET /api/sincronizacion/conflictos` | `sincronizacion.administrar` | Lista con filtros por estado, equipo y fecha; `GET /api/sincronizacion/conflictos/{id}` el detalle. |
| `POST /api/sincronizacion/conflictos/{id}/resolucion` | `sincronizacion.administrar` | `{accion: REINTENTAR \| GUARDAR_SIN_RENGLONES \| GUARDAR_CON_DIFERENCIAS \| DESCARTAR, renglones?, motivo}`. 409 si ya está resuelto; 403 si quien resuelve capturó la operación. |
| `PATCH /api/almacenes/{id}` | `almacenes.administrar` | Acepta `hora_descarga`. |
| `GET /api/vales/por-token/{token}` | (como hoy) | Si el token no es de un vale pero sí de un conflicto, responde su estado («en revisión», «no se guardó»); si no existe en ningún lado, «pendiente de sincronizar» (sin revelar nada más). |
| Todas | — | Encabezado `X-App-Version`: 426 `APP_DESACTUALIZADA` si es menor que `APP_VERSION_MINIMA`. |

### Parámetros y códigos

- `.env` (ya en el maestro): `SINCRONIZACION_HORAS_MAXIMAS=24`, `SINCRONIZACION_LOTE_MAXIMO=20`, `APP_VERSION_MINIMA`. Constantes de la app (no de `.env`): 2 MB por lote, 30 minutos para volver a descargar, 10 minutos de desfase, 30 días de credencial local, 10 minutos de bloqueo por inactividad.
- Códigos nuevos: `APP_DESACTUALIZADA` (426), `DISPOSITIVO_REVOCADO`, `DISPOSITIVO_NO_INSCRITO`, `DISPOSITIVO_DE_OTRO_ALMACEN` (403), `LOTE_INVALIDO` (422), `CONFLICTO_YA_RESUELTO` (409). Motivos de conflicto: `EXISTENCIA_INSUFICIENTE`, `PIEZA_EN_OTRA_UBICACION`, `YA_RECIBIDO`, `TRASPASO_CANCELADO`, `CODIGO_DESCONOCIDO`, `TRABAJADOR_NO_EXISTE`, `ALMACEN_CERRADO`, `ID_CLIENTE_OTRO_CUERPO`, `TOKEN_REPETIDO`, `FORMA_INVALIDA`, `USUARIO_NO_REGISTRADO`, `DISPOSITIVO_REVOCADO`, `DEPENDE_DE_CONFLICTO`.

### Dependencias nuevas (las pide esta feature)

Frontend: `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, `@capacitor/network`, `@capacitor/local-notifications`, `@capacitor-community/sqlite`; opcionales `@capacitor/filesystem` y `@capacitor/share`; de desarrollo, `vitest`. Nativas, en el complemento propio: `androidx.work` (WorkManager). Backend: ninguna (la compresión `gzip` de la respuesta ya la trae Starlette).

## Restricciones y compatibilidad

- **La web no cambia.** Todo lo nuevo de la interfaz va detrás de `Capacitor.isNativePlatform()`; en el navegador, el código sin conexión no se carga (importación diferida).
- **Solo `movimientos` escribe** vales, movimientos, existencias y ubicación de piezas, también los sincronizados (maestro 5.2).
- **Los vales y movimientos no se actualizan ni se borran**; las columnas nuevas se escriben al insertar.
- **Las reglas viven en el servidor.** El evaluador local es una copia para operar sin red, verificada con casos compartidos; la decisión final es del servidor.
- **Permisos por clave en cada endpoint** (`sincronizacion.operar`, `sincronizacion.administrar`); el permiso de cada operación del lote se verifica en el servicio (se agrega a la lista de excepciones de AGENTS.md y [security-model.md](../architecture/security-model.md)).
- **Textos en español llano**, sin «sincronización fallida», «HTTP» ni «token» en pantalla: «Pendiente de subir», «En revisión del supervisor», «Necesitas señal para…».
- Las cookies `HttpOnly` y `SameSite=Lax` de la web no cambian (sección B).

## Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| **Cookies en la app** (sección B). | Sin sesión no hay app. | Prueba de concepto **primero**; alternativas (b) y (c) documentadas. |
| **WebView viejo en los Zebra.** | Interfaz rota con Tailwind 4. | Verificar la versión en los equipos reales (maestro, pregunta 4); pantalla de aviso; actualización por MDM. |
| **Divergencia de evaluadores.** | El equipo entrega algo que el servidor no habría dejado. | Casos compartidos; el servidor revalida y nunca rompe una invariante (OF-17, OF-21, OF-22). |
| **WorkManager sin hora exacta.** | La descarga programada llega tarde. | Descarga al iniciar turno y al volver la señal; ventana amplia; aplica a cualquier tecnología. |
| **Conflictos que nadie resuelve.** | Vales en el limbo y comprobantes «en revisión». | Contador en el Inicio del supervisor (OF-30); notificación push opcional. |
| **Llave de firma del APK perdida.** | No se puede actualizar sin desinstalar, y desinstalar borra la cola. | Guardarla con los respaldos; documentar el procedimiento. |
| **Pérdida de datos por desinstalación.** | Vales que nunca llegan. | Aviso permanente, MDM que impide desinstalar, OF-30. |
| **Alcance grande al final de la iteración.** | No alcanza el tiempo. | Alcance mínimo para la demostración (abajo); el resto queda documentado. |
| **Rendimiento de SQLite cifrada en equipos modestos.** | Evaluación local lenta. | Índices locales por código y por trabajador; objetivo igual al del servidor: renglón en menos de un segundo desde la lectura ([trd.md](../architecture/trd.md), sección 11). |
| **Dos renovaciones a la vez** (la app abierta y la descarga en segundo plano). | Reutilización detectada y sesión cerrada (AC-17). | La descarga en segundo plano no corre si la app está al frente; la tolerancia de 10 s cubre la carrera. |

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck`, `pnpm build` y, nuevo, las pruebas de vitest del evaluador local.
- Una prueba por regla nueva con su ID en el nombre (`test_OF_20_misma_pieza_dos_equipos`, …) y los casos compartidos del evaluador.
- Prueba de integración de sincronización: lote con GUARDADO, GUARDADO_CON_AVISOS y CONFLICTO; reenvío del mismo lote; dos equipos con la misma pieza; equipo revocado.
- `uv run python -m app.mantenimiento verificar` da 0 después de sincronizar y de resolver conflictos (las invariantes no cambian).
- Migraciones arriba y abajo.
- **Prueba en un equipo real** (Zebra o Android 7+): prueba de concepto de sesión, DataWedge en modo teclado, pérdida de señal con el modo avión a media entrega, descarga programada, cambio de turno y desinstalación con cola (para confirmar el aviso).
- El guion del PDF sigue pasando en línea.

## Para la demostración

Alcance mínimo, en este orden:

1. Prueba de concepto de sesión (sección B) y APK que opera **en línea** igual que la web.
2. Inscripción del equipo, credencial local de un usuario y paquete completo (sin descarga programada; con «Actualizar ahora»).
3. **Devolución**, **entrega con autonomía** y **recepción de traspaso** sin conexión, con comprobante «Folio pendiente».
4. **Sincronización por lotes** con los tres resultados y un conflicto visible en la web del supervisor (con «Descartar» y «Reintentar»).

Guion sugerido: modo avión a media entrega → la entrega sigue → devolución → recepción → quitar el modo avión → la cola sube y los folios aparecen → un segundo equipo entregó la misma pieza → conflicto en la web del supervisor.

El resto (descarga programada, varios usuarios, notificaciones locales, DataWedge por *intents*, inspección sin conexión, revocación con borrado) queda documentado aquí y se construye después.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): sección nueva con OF-01 a OF-30; notas de excepción en RG-06, RG-08, RG-09, RG-11, AC-13, E-28 y A-01; RG-15 (la app de Android sí se instala); sección 8 con `sincronizacion.operar` y `sincronizacion.administrar`; 5.4 con los parámetros nuevos.
- [data-model.md](../architecture/data-model.md): `dispositivo`, `conflicto_sincronizacion`, columnas de `vale` y `almacen`, lo propuesto; dueños del módulo `sincronizacion`.
- [api-contracts.md](../architecture/api-contracts.md): endpoints, cuerpos, códigos y el 426.
- [security-model.md](../architecture/security-model.md): sesión desde la app (peticiones nativas), base local cifrada, credencial local, equipo perdido, ruta más que verifica en el servicio.
- [trd.md](../architecture/trd.md): Capacitor, SQLite, WorkManager, vitest; secciones 8, 15, 16 y 17.
- [app-flow.md](../product/app-flow.md) y [ui-ux.md](../product/ui-ux.md): pantallas nuevas e indicador de conexión.
- [overview.md](../architecture/overview.md): el módulo `sincronizacion` y el flujo de la cola.
- [AGENTS.md](../../AGENTS.md): comandos de Capacitor, lista de módulos (quince), rutas que verifican en el servicio.
- [mvp-scope.md](../product/mvp-scope.md): ya lo menciona; ajustar si cambia el alcance mínimo.
- [guia-almacenista.md](../guia-almacenista.md): qué hacer cuando se cae la señal.

## Decisiones abiertas

1. **Usuarios del equipo (`dispositivo_usuario`).** El maestro trae `dispositivo.usuario_id` (uno solo), pero varios usuarios comparten el equipo y el servidor necesita saber quiénes entraron en él para aceptar sus vales (OF-24) y para invalidar su credencial local por `version_sesion` (OF-05). Se propone la tabla `dispositivo_usuario`. **Ya está en la sección 5.1 del maestro** (con `primera_entrada_en`, `ultima_entrada_en` y `revocado_en`); falta tu confirmación.
2. **Secreto del equipo (`dispositivo.secreto_hash`).** Sin él, cualquier usuario con sesión podría decir que es cualquier equipo de su almacén. Se propone la columna. **Ya está en la sección 5.1 del maestro.**
3. **Idempotencia de inspecciones.** `inspeccion` y `evento_pieza` no tienen `id_cliente`. El maestro fija la tabla `operacion_recibida` en `sincronizacion` (sirve para todos los tipos); `inspeccion.id_cliente` existe aparte para la inspección por lote en línea (FEAT-016).
4. **Firma digital de cada operación por usuario.** Para que el vale pruebe quién lo capturó aun si otro lo sube, cada usuario podría tener un par de llaves por equipo (la privada protegida por su PIN local, la pública en `dispositivo_usuario`) y firmar cada operación. Más fuerte para F-05, más trabajo. Se propone dejarlo para después de la demostración.
5. **`/v/:token` sin sesión.** Hoy la vista del vale exige sesión, así que el trabajador que escanea su comprobante ve «Entrar». ¿Se abre una vista pública mínima (estado y renglones, sin datos personales) o se queda con sesión?
6. **Operación sin conexión en Kepler.** Kepler está fuera de la planta y su paquete sería el de todos los trabajadores. Se propone no habilitarla en v1.
7. **Devolución «Por verificar».** Se propone aceptarla sin conexión para piezas fuera del paquete (SM-05). ¿De acuerdo, o se pide señal?
8. **Seguridad atrasada (OF-21).** Una entrega de una pieza que resultó No apta o con inspección vencida al sincronizar se propone **guardar con aviso urgente**, no mandar a conflicto, porque la pieza ya está con el trabajador. ¿De acuerdo?
9. **Bloqueo por inactividad** a los 10 minutos en la app. La web no lo tiene.
10. **Dirección del servidor resuelta para este hito:** el usuario indicó `https://imhotep-production.checodev.top`; queda fija en la construcción (`VITE_API_ORIGEN`). El paquete implementado es `mx.imhotep.almacen`. Una construcción por servidor.
11. **Hora de descarga inicial** 06:00 propuesta; y si el supervisor también puede cambiarla.
12. **Notificación push al supervisor** por conflicto nuevo (usaría FEAT-014).
13. **Lectura por cámara sin servicios de Google** (complemento con ML Kit empaquetado), solo si el track lo pide.
14. **Compresión de la subida** (depende de la prueba de concepto).

## Orden de construcción sugerido

1. **Prueba de concepto de sesión** en un equipo real (sección B). Si falla, se decide entre (b) y (c) antes de seguir.
2. App que opera en línea (base absoluta, sin service worker, versión mínima).
3. Módulo `sincronizacion`: dispositivos, paquete, base local cifrada y aplicación del paquete.
4. Credencial local y entrar sin señal.
5. Evaluador local con casos compartidos (empezar por devolución y entrega).
6. Cola, comprobante y lotes con el camino de `movimientos` para vales sincronizados.
7. Conflictos en la web del supervisor.
8. Descarga programada, notificaciones locales, inspección sin conexión, revocación con borrado y DataWedge por *intents*.
