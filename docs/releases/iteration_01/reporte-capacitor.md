# Reporte de FEAT-020: contenedor Android en línea e integración visual

## Tarea realizada

Se retomó la sesión anterior de Claude Code, que dejó la iteración 01 documentada y se detuvo por límite de uso antes de completar su revisión. Sus documentos locales se conservaron. Se revisaron los briefs FEAT-001 a FEAT-011 y FEAT-013 a FEAT-020 (FEAT-012 no tiene brief), el maestro y la evidencia del código; el listado de archivos y la captura no se tomaron como prueba de que las nuevas funciones estuvieran implementadas.

Se integró el rediseño de `56da615` de la rama `codex/imhotep-002-dashboard`: identidad azul común, navegación, botones y tablero administrativo, conservando los cambios locales. La revisión corrigió el contraste de Tutorial/Instalar en el menú móvil. Los reportes IMHOTEP-002 a IMHOTEP-004 se conservan como evidencia histórica de esa rama; sus restricciones de aquella entrega no sustituyen la petición actual del usuario de integrar el rediseño.

Se construyó el contenedor Capacitor para la SPA existente, con API fija `https://imhotep-production.checodev.top`, versión `0.1.0`, cabecera de versión, comprobación del servidor OF-02, sesión por peticiones nativas, imágenes autenticadas, conexión, navegación Atrás, compartir archivos e impresión Android. No se implementó operación sin conexión.

Como primer fragmento aislado de OF-06/OF-07 se añadió una primitiva frontend para crear y verificar el PIN local con PBKDF2-SHA256 (600 000 iteraciones y sal aleatoria), rechazar formatos/secuencias/fechas triviales y calcular el bloqueo tras cinco fallos y el borrado tras diez. Sus pruebas unitarias pasan. **No persiste la credencial ni el estado de intentos, no está conectada a la interfaz o al inicio de sesión y no habilita entrada sin conexión.** No reemplaza SQLite cifrada ni el resguardo de la llave con Android Keystore.

## Archivos modificados

- Contenedor y primitiva local OF-06/07: `frontend/capacitor.config.ts`, `frontend/android/`, `frontend/scripts/android.mjs`, `frontend/app/movil/` (incluye `credencial-local.ts` y sus pruebas), `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/.env.example` y `frontend/vitest.config.ts`.
- Integración web: `frontend/app/api/cliente.ts` y sus pruebas, `app/pwa/registrar.ts`, `app/root.tsx`, avatar, QR y vale imprimible; estilos, navegación, identidad y tablero del rediseño.
- Servidor: `backend/app/version_app.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/tests/seguridad/test_version_app.py`, `.env.example` y `.gitignore`.
- Documentación: `AGENTS.md`, `frontend/README.md`, FEAT-020, maestro de iteración, este reporte, notas de estado en arquitectura/API/seguridad/flujos/UI y reportes visuales IMHOTEP-002 a IMHOTEP-004.
- Los demás documentos de iteración, briefs, ADR y recursos ya eran cambios locales de la sesión anterior; no atribuirlos íntegramente a este hito.

## Decisiones y supuestos

- El servidor HTTPS lo indicó el usuario. Se incorpora al construir; no hay credenciales dentro del APK ni selector arbitrario de servidor.
- Se conserva la interfaz local y la sesión existente del servidor. `CapacitorCookies` está desactivado; el complemento HTTP conserva cookies nativas y elimina `Set-Cookie` de lo que recibe JavaScript, con registro del puente desactivado.
- Los archivos compartidos permanecen temporalmente en caché privada para que el receptor pueda copiarlos. Los de más de una hora se limpian al abrir o compartir. La impresión usa Android; no agrega generación PDF de FEAT-017/019.
- No hay cambios de esquema ni migraciones. La excepción OF-02 para el POST exacto de lotes no crea el endpoint ni autoriza operaciones.
- Capacitor 8.5.3, JDK 21, SDK 36, Android mínimo API 24 y WebView 111+. El APK debug es para pruebas; no sustituye una publicación firmada con llave conservada.
- Las dependencias nativas y Vitest corresponden a lo solicitado por FEAT-020. SQLite, notificaciones locales y WorkManager no se instalaron ni presentaron como disponibles.

## Validaciones ejecutadas

- `pnpm typecheck` → pasó.
- `pnpm test` → pasó: 14 pruebas en 3 archivos, incluidas configuración HTTPS, cabecera/cliente y retención/limpieza de exportaciones.
- `pnpm android:sync` → pasó la construcción web para el origen HTTPS real y la sincronización nativa.
- `pnpm build` → pasó la construcción web.
- `pnpm exec vitest run app/movil/credencial-local.test.ts` → 4 pruebas pasaron para la primitiva OF-06/OF-07; no prueban persistencia, interfaz ni operación offline integrada.
- `pnpm typecheck` y `pnpm build` → pasaron después de añadir la primitiva de PIN local.
- Validación de esta continuación (2026-10-09): `pnpm typecheck`, `pnpm build`, `pnpm test` (47 pruebas), `VITE_API_ORIGEN=https://imhotep-production.checodev.top pnpm android:sync` y `frontend/android/gradlew.bat assembleDebug` → pasaron. APK debug actualizado en `frontend/android/app/build/outputs/apk/debug/app-debug.apk`; el bundle incluye el origen HTTPS indicado por el usuario.
- `adb devices` no encontró equipos conectados; no se pudo instalar ni demostrar inicio de sesión autenticado en Android/Zebra. El APK es de depuración y la app sigue siendo en línea.
- Desde `backend/`, `$env:ENTORNO='desarrollo'; $env:TEST_DB_SUFFIX='codex_capacitor'; uv run pytest tests/seguridad/test_version_app.py tests/seguridad/test_arranque_seguro.py -q` → 25 pruebas pasaron (versión OF-02 y configuración de arranque seguro; no son pruebas de sesión HTTP reales).
- Regresión completa (2026-10-09): `uv run pytest -q --tb=short` → **no pasó**: 2,067 aprobadas, 303 fallidas y 21 errores en 31:45. Los fallos abarcan contratos/permisos y varios módulos; un error capturado en teardown no pudo borrar `periodo_contrato` por la FK desde `vale.periodo_contrato_id`. Esta corrida no se ha triageado por completo; no se declara la suite verde.
- `uv run pytest tests/seguridad -q` con el mismo entorno → **72 pruebas pasaron** en 69.60 s; un aviso de obsolescencia de Starlette. Incluye sesiones revocables, renovación, rotación, concurrencia, datos reservados, tamaño y versión. Son pruebas del servidor y no reemplazan la sesión desde un APK instalado.
- `uv run ruff check .` → pasó. Comprobación de formato de los cuatro archivos backend cambiados → pasó.
- `git diff --check` → pasó.
- Revisión del rediseño por otro agente → cambios aplicados sin sobrescribir los documentos previos; tipos y contraste de los controles móviles revisados. Navegador llegó a Entrar; tablero autenticado pendiente de sesión disponible.
- `./gradlew.bat assembleDebug` con Gradle 8.14.3 y checksum oficial fijado → pasó. APK `frontend/android/app/build/outputs/apk/debug/app-debug.apk`, `mx.imhotep.almacen`, versión `0.1.0`, `versionCode=1`, API mínima 24. Inspección del APK: origen HTTPS real incluido, sin mapas de fuente, HTTP nativo activado, CapacitorCookies desactivado y registro del puente desactivado.
- `./gradlew.bat assembleDebug lintDebug testDebugUnitTest` con el wrapper del repositorio → BUILD SUCCESS, código 0. JUnit: una prueba del filtro de encabezados AC-24 pasó; no demuestra cookies en un dispositivo. Se retiraron las pruebas de ejemplo generadas. Lint: 0 errores y 20 avisos después de corregir el texto español literal y el orden de permisos del manifiesto. La descarga/compilación inicial encontró tiempos de espera de red y se recuperó al reintentar.
- `apksigner verify --verbose` → APK verificado, firma v2 y un firmante de depuración. `adb devices` → lista vacía; sin prueba instalada.
- Infraestructura para la suite completa → Docker Desktop se reparó con autorización del usuario, conservando respaldos de los archivos afectados antes de regenerar IPC obsoleto. Engine 29.6.2 y MySQL saludable en 21001; pruebas con `TEST_DB_SUFFIX=codex_capacitor`.
- Dispositivo Android/Zebra real y prueba de concepto de sesión de FEAT-020 B → no ejecutadas: no hay dispositivo ADB disponible.

## Riesgos o deuda pendiente

- **FEAT-020 no está completa.** Falta demostrar entrada, renovación, cierre/revocación y ausencia de tokens en JavaScript en equipo real con HTTPS. Falta comprobar cámara, lector Zebra, formularios, imágenes, Compartir e impresión. La compilación no demuestra estos recorridos.
- Inscripción, dispositivo/secretos, SQLite cifrada, persistencia e integración UI de la credencial local OF-06/OF-07, paquete, evaluador, cola, subida de lotes, conflictos, descarga programada, notificaciones locales y revocación permanecen pendientes. La primitiva PBKDF2 y su política de intentos no equivalen a esos flujos.
- FEAT-013 a FEAT-019 tienen implementación sustancial local; siguen incompletas sus listas de aceptación, recorridos visuales y pruebas físicas indicadas en el reporte de integración. Son dependencias funcionales de la app sin conexión. Mantener el orden de la sección 7 del maestro.
- La sesión anterior dejó decisiones abiertas: `dispositivo_usuario`, secreto del equipo, idempotencia de inspecciones, comprobante público, Kepler, devolución por verificar y política de seguridad al subir. Resolver antes de migrar o implementar esos comportamientos.
- La auditoría del maestro sigue detectando FEAT-012 sin brief y contradicciones entre estado documentado y código de FEAT-008/009/011, alcance de etiquetas, búsquedas y alto valor. Este hito no las resuelve ni certifica todas las features anteriores.
- La suite backend completa no queda certificada: se detuvo por la aserción previa de VI-05. La regresión de seguridad sí pasó completa; corregir la prueba de valor en una tarea propia, preservando su intención de no revelar costos por artículo.
- Falta llave de publicación y aceptación de APK en equipo real. Revisar antes de publicar los avisos de lint sobre recursos generados, actualizaciones de dependencias, atributo `allowBackup` obsoleto desde Android 12 y el icono redondo. No se desplegó el servidor de producción ni se modificaron sus parámetros de sesión. El usuario autorizó posteriormente commit y push de la integración visual y Capacitor en la rama `android/capacitor`.

## Documentación actualizada

FEAT-020 y el maestro distinguen contenedor en línea de operación sin conexión. API documenta el 426 implementado y su excepción exacta. Seguridad y arquitectura diferencian medidas construidas y planeadas. Flujos y UI aclaran qué pantallas nativas existen. `frontend/README.md` y `AGENTS.md` documentan configuración, requisitos, construcción, instalación y firma. Se conservaron los reportes y patrones visuales del commit integrado.

## Siguiente acción

Instalar el APK de prueba en Android/Zebra y cerrar el criterio de salida de FEAT-020 B contra un servidor HTTPS de prueba, sin acortar la sesión de producción. Después completar las dependencias de FEAT-013 a FEAT-019 y las decisiones abiertas, y construir el mínimo sin conexión en el orden del brief. No marcar OF-01 ni FEAT-020 aceptadas antes de demostrar el recorrido real.
