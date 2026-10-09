# Interfaz web y Android de IMHOTEP

React 19, React Router 8 en modo SPA, TypeScript y Tailwind CSS 4. Android empaqueta esta misma interfaz con Capacitor 8.5.3; los archivos web se cargan desde el equipo y la API desde el servidor HTTPS fijado al construir.

## Desarrollo web

Desde `frontend/`: `pnpm install`, `pnpm dev`, `pnpm typecheck`, `pnpm test` y `pnpm build`. El servidor usa el puerto 21010 y reenvía `/api` a `API_DESTINO` (por omisión, `http://127.0.0.1:21011`). Para el backend local, configurar `API_DESTINO=http://127.0.0.1:21002`.

## Construcción Android

Requiere Node compatible con Vite 8, pnpm, JDK 21 y Android SDK con plataforma 36. Admite Android 7 (API 24) o superior y WebView equivalente a Chrome 111 o superior. Configurar `JAVA_HOME` y el SDK mediante `ANDROID_HOME` o `android/local.properties` (local e ignorado).

1. Copiar `.env.example` a `.env.android.local`. La configuración actual es `VITE_API_ORIGEN=https://imhotep-production.checodev.top`, dirección indicada por el usuario. Debe ser un origen HTTPS sin `/api`, credenciales, parámetros ni fragmentos. Se incorpora al APK: cambiar de servidor exige reconstruir.
2. Ejecutar `pnpm android:sync`: construye en modo `android` y copia los estáticos a la carpeta nativa. Repetir después de cada cambio web o de complementos.
3. Ejecutar `pnpm android:open` para Android Studio, o `cd android` y `./gradlew.bat assembleDebug` en PowerShell (`./gradlew assembleDebug` en otros sistemas).
4. El APK de prueba queda en `android/app/build/outputs/apk/debug/app-debug.apk`. Con equipo conectado y autorizado, ejecutar `adb install -r app/build/outputs/apk/debug/app-debug.apk` desde `android/`.

Para publicación, proporcionar `ANDROID_KEYSTORE_PATH` (ruta absoluta), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS` y `ANDROID_KEY_PASSWORD` por variables de entorno y ejecutar `assembleRelease`. Sin ellas, la salida release no queda firmada para distribuir. Mantener la llave y sus respaldos fuera del repositorio; las actualizaciones deben conservar la firma. Incrementar `versionCode` y `versionName` en `android/app/build.gradle` para cada publicación. El servidor exige por omisión `APP_VERSION_MINIMA=0.1.0`.

## Funciones nativas y estado real

El contenedor tiene API absoluta, `X-App-Version` obtenido del APK, peticiones nativas con cookies del servidor, aviso de versión mínima, navegación con Atrás, aviso de WebView viejo, impresión por Android y compartir CSV/PDF mediante el sistema. No registra el service worker en Android. Las imágenes protegidas se solicitan con el cliente autenticado antes de mostrarlas. Los archivos compartidos quedan temporalmente en caché privada; al abrir la app o compartir se borran los de más de una hora. Las copias exportadas a otra aplicación dependen de esa aplicación.

`CapacitorCookies` está desactivado y el puente HTTP propio excluye `Set-Cookie` de la respuesta entregada a JavaScript; el almacén nativo conserva las cookies. El registro del puente está desactivado. Verificar en Android real con HTTPS: entrada, renovación, cierre, revocación y ausencia de tokens en `document.cookie` y respuestas del puente. Usar un entorno de prueba para acortar la sesión, sin cambiar producción.

**Este hito prepara la app para operar en línea; FEAT-020 no está completa.** No hay inscripción de equipos, SQLite cifrada, PIN local, paquete del almacén, evaluador local, cola ni sincronización. Sin señal conserva el comportamiento web existente: borradores y aviso, sin confirmar operaciones como guardadas. Proyectos, aprobación de despacho y nuevas alertas siguen pendientes de FEAT-013 a FEAT-019. La aceptación exige la prueba de concepto de sesión de FEAT-020, sección B, en equipo real antes de continuar con la operación sin conexión.

Estado y validaciones: [reporte de Capacitor](../docs/releases/iteration_01/reporte-capacitor.md).
