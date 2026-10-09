# ADR-014: App de Android del almacenista con Capacitor, en el mismo repositorio

## Estado

Aceptada (8 de octubre de 2026), por decisión del usuario (D-15 del [documento maestro de la iteración 01](../../releases/iteration_01/README.md)). Se construye al final del orden de construcción ([FEAT-020](../../features/FEAT-020-app-android-sin-conexion.md)).

## Contexto

En la plática del 8 de octubre de 2026 se decidió que el almacenista opere sin conexión, limitado a su almacén ([ADR-015](ADR-015-operacion-sin-conexion-del-almacenista.md)). Hasta ahora la interfaz es una aplicación web de una sola página (React 19, React Router 8 sin SSR, TypeScript, Tailwind CSS 4, Vite 8) que FastAPI entrega desde el mismo origen que la API ([ADR-002](ADR-002-un-solo-desplegable.md)), instalable como PWA y sin modo sin conexión ([ADR-004](ADR-004-primero-en-linea.md)).

Trabajar sin conexión de verdad exige cosas que la web sola no da con confianza: guardar los datos del almacén en un lugar cifrado que el sistema no borre, descargar a una hora programada aunque la app esté cerrada y saber con certeza cuándo hay red. Los almacenes usan equipos Android, en muchos casos Zebra con lector integrado y compartidos entre turnos. No hay iPhone en el almacén ni se publicará en tiendas (maestro, sección 6).

## Fuerzas y restricciones

- **Reutilizar lo construido.** La interfaz ya tiene el escáner (cámara, pistola y teclado), el renglón con semáforo, la firma, el comprobante con QR, las pantallas de entregar, devolver y recibir, y el cliente de la API con la renovación de sesión. Reescribirlos cuesta semanas y duplica el mantenimiento.
- **Una sola fuente de reglas.** El evaluador local (FEAT-020, OF-16) es una copia del motor de Python para el subconjunto sin conexión. Si la app está en TypeScript, ese evaluador y sus pruebas viven junto a la interfaz y comparten tipos con ella.
- **Tiempo.** La iteración termina con FEAT-020; lo que quede debe ser una extensión de lo que ya existe, no un segundo producto.
- **Equipo de trabajo.** El equipo conoce React y TypeScript; no Dart ni Kotlin a fondo.
- **Equipos reales.** Android 7 o superior; WebView del sistema, que en Zebra sin servicios de Google se actualiza por MDM; lector integrado configurable con DataWedge.
- **Lo que pide el sistema operativo.** Programar trabajo en segundo plano en Android se hace con WorkManager, que **no garantiza la hora exacta** (agrupa tareas y respeta el reposo profundo, Doze). Esto aplica a cualquier tecnología, nativa o no.
- **Sesión.** El servidor usa cookies `HttpOnly` y `SameSite=Lax` de un solo origen ([security-model.md](../security-model.md)). Cualquier app que cargue la interfaz desde el equipo llama a la API desde otro origen.

## Alternativas consideradas

1. **Capacitor.** Empaqueta la misma interfaz web en una app de Android con un WebView y le da acceso a funciones nativas por complementos (SQLite cifrada, red, notificaciones locales, ciclo de vida) y por código nativo propio cuando haga falta (WorkManager, reloj monótono, DataWedge por *intents*).
2. **Flutter.** App nativa compilada, en Dart, con sus propios componentes.
3. **React Native.** App con componentes nativos controlados desde JavaScript o TypeScript.
4. **PWA sola** (la que ya existe), con IndexedDB, un service worker y Background Sync o Periodic Background Sync.

| Criterio | Capacitor | Flutter | React Native | PWA sola |
|---|---|---|---|---|
| Reutiliza las pantallas de React | **Sí, todas** | No: se reescriben en Dart | No: los componentes web (Tailwind, `div`, `canvas`) no sirven; se rehacen | Sí |
| Evaluador local compartido con la interfaz | Sí (TypeScript) | No (Dart), sería una tercera implementación | Sí (TypeScript), pero en otra app | Sí |
| Base local cifrada que el sistema no borra | Sí (SQLite con SQLCipher, llave en Keystore) | Sí | Sí | **No**: el navegador puede borrar IndexedDB por espacio o por política; no hay cifrado con llave del sistema |
| Descarga programada | WorkManager (aproximada) | WorkManager (aproximada) | WorkManager (aproximada) | **No confiable**: Periodic Background Sync solo en Chrome, con intervalos que decide el navegador y solo para PWA instaladas con uso frecuente; no hay hora programada |
| Sincronización en segundo plano | Sí, con WorkManager | Sí | Sí | Solo Background Sync de Chrome; **iOS no sincroniza en segundo plano** |
| Lector Zebra | DataWedge en modo teclado ya funciona; *intents* con un complemento | *Intents* con un canal nativo | *Intents* con un módulo nativo | Solo modo teclado |
| Un solo repositorio y una sola construcción de la interfaz | Sí (`frontend/android/`) | No: proyecto aparte | No: proyecto aparte | Sí |
| Riesgo principal | WebView viejo; cookies entre orígenes | Reescritura total; dos interfaces que divergen | Reescritura de pantallas; dos interfaces | No cumple lo que pide D-15 |

## Decisión

**Capacitor**, en el **mismo repositorio**: la app de Android es la interfaz de `frontend/` empaquetada, con su carpeta nativa en `frontend/android/` y su configuración en `frontend/capacitor.config.ts`. No es un proyecto aparte; cualquier otro proyecto móvil (por ejemplo, uno en Flutter) no es la app del almacenista y se ignora.

- Construcción: `pnpm build` → `pnpm exec cap sync android` → Android Studio o Gradle → APK firmado, distribuido por MDM o instalación directa, sin tienda.
- La sesión desde la app usa peticiones nativas (`CapacitorHttp`) con el almacén de cookies nativo, conservando el modelo de cookies `HttpOnly` del servidor; la prueba de concepto de eso es el primer paso de la construcción, con dos alternativas documentadas en FEAT-020 (sección B).
- La web sigue igual; lo propio de la app va detrás de `Capacitor.isNativePlatform()`.

## Justificación

- **Una interfaz, no dos.** Cada pantalla, regla de presentación y texto que se mejore en la web llega a la app con la siguiente construcción. Con Flutter o React Native, cada cambio se haría dos veces y las dos interfaces divergirían, que es lo contrario de «las reglas viven en el servidor y la interfaz solo muestra».
- **El evaluador local se comparte.** En TypeScript, el evaluador sin conexión usa los mismos tipos que la interfaz y se prueba con los mismos casos compartidos que pytest (OF-16). En Dart sería una tercera implementación del motor.
- **La PWA no alcanza.** No da almacenamiento que el sistema respete ni cifrado con llave del sistema, no programa descargas a una hora y su sincronización en segundo plano depende del navegador; en iPhone no existe. D-15 pide descargar a una hora configurable y operar con datos del almacén guardados en el equipo.
- **Lo nativo que hace falta es poco y acotado:** WorkManager, el reloj monótono y, opcionalmente, DataWedge por *intents*. Cabe en un complemento propio pequeño dentro de `frontend/android/`.
- **El costo del WebView es conocido** y se controla en los equipos del almacén, que se administran con MDM.

## Consecuencias positivas

- La app sale de la misma base de código; el equipo trabaja en lo que ya conoce.
- La demostración puede mostrar la misma interfaz en la web y en el Zebra.
- El lector integrado funciona desde el primer día en modo teclado, porque el escáner ya distingue la pistola por la velocidad de las teclas.
- Las funciones nativas se agregan de una en una, por complementos, sin cambiar la arquitectura.

## Consecuencias negativas

- **Depende del WebView del equipo.** Tailwind CSS 4 necesita un motor equivalente a Chrome 111 o superior; un Zebra con WebView viejo muestra la interfaz rota hasta que se actualice. La app debe detectarlo y avisar.
- **Cookies entre orígenes.** La interfaz se carga desde `https://localhost` y la API está en otro dominio; sin peticiones nativas la sesión no funciona. Si `CapacitorHttp` no conserva bien las cookies `HttpOnly`, hay que cargar la interfaz desde el servidor (se pierde el arranque sin conexión) o pasar a un token `Bearer` cifrado (cambia el modelo de seguridad y pide otro ADR).
- **Diferencias con el navegador** que hay que cuidar en la app: el service worker no se registra, las descargas de archivos por enlace `blob:` no funcionan, la cámara por `BarcodeDetector` puede no estar en equipos sin servicios de Google, y algunas capacidades de `fetch` (cancelar, `FormData`) se comportan distinto con peticiones nativas.
- **Más cosas que mantener:** el proyecto de Android, las versiones de Capacitor y sus complementos, la llave de firma del APK (si se pierde, no se puede actualizar la app sin desinstalarla) y un complemento nativo propio.
- **WorkManager no da hora exacta.** La descarga «a las 06:00» puede llegar minutos tarde. No es propio de Capacitor: le pasaría igual a una app nativa. Se compensa con la descarga al iniciar turno y al volver la señal.
- Una construcción por servidor, porque la dirección de la API queda fija en la app.

## Señales para reevaluar

- La prueba de concepto de sesión falla y ninguna de las dos alternativas es aceptable.
- Los equipos del almacén no pueden tener un WebView reciente (sin MDM, sin actualizaciones de Zebra).
- La evaluación local o la base cifrada son lentas en los equipos reales (más de un segundo desde la lectura hasta el renglón).
- El track pide iPhone, una tienda de aplicaciones o funciones nativas pesadas (por ejemplo, lectura continua por cámara a alta velocidad) que el WebView no sostiene.
- La app empieza a necesitar pantallas propias que la web no tiene, al punto de que la interfaz compartida estorba más de lo que ayuda.
