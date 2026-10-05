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

Además: `openpyxl` (leer `.xlsx` al importar), `cryptography` (la necesita PyMySQL para entrar a MySQL 8), `httpx` y `python-multipart`; `pytest` y `ruff` como dependencias de desarrollo. En la interfaz: `qrcode.react` (QR) y los componentes base de shadcn sobre `@base-ui/react`. Se retiró `pywebpush`, que no usaba nada (las notificaciones push están excluidas).

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
- Sin métricas ni tablero en el MVP.

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

- Trabajadores de servicio, caché sin conexión y sincronización ([ADR-004](decisions/ADR-004-primero-en-linea.md)).
- WebSockets; la actualización es por consulta periódica.
- Colas, tareas en segundo plano y notificaciones push.
- Varias empresas, varios idiomas.
- Almacenamiento de archivos en la nube; se usa un volumen local.
- Pruebas automáticas de interfaz de extremo a extremo.
