# Changelog

Qué trae cada versión. Se escribe a partir del historial del repositorio (`git log`), del [roadmap](../product/roadmap.md) y de los documentos del proyecto; si algo no está construido, no aparece aquí. El formato sigue el orden del roadmap.

## Sin publicar: dotación por puesto (FEAT-003, servidor)

- Catálogo de puestos (`/api/puestos`) y dotación recomendada por puesto (`GET` y `PUT /api/puestos/{id}/dotacion`), con la cantidad limitada por el límite del artículo (D-04). Migración `0004_puestos_dotacion` (tablas `puesto` y `dotacion`, `periodo_contrato.puesto_id`).
- El alta y el reingreso de trabajadores aceptan `puesto_id`; con solo el texto se busca el puesto por nombre.
- `GET /api/trabajadores/{id}/dotacion`: lo que le falta de su dotación (D-02).
- Entrega: aviso amarillo E-09 (fuera de la dotación o más de lo recomendado) que pide observación y la exige al confirmar; avisos E-10 (talla) y E-11 (inspección que vence en 7 días o menos) sin observación. `pide_observacion` en la evaluación; la observación aparece en el reporte de movimientos.
- Datos de prueba: cuatro puestos con dotación, propuestas basadas en el PDF.
- Pendiente: la interfaz.

## 0.1.0: MVP (octubre de 2026)

Primera versión completa del flujo principal del reto IMHOTEP: de dar de alta a un trabajador hasta su vale de no adeudo, pasando por entregas con límite y autorización, devoluciones y traspasos entre almacenes. La etiqueta de git la crea el equipo al cerrar la [checklist](mvp-checklist.md); este archivo no la crea.

### Fase 0: fundación

- Esqueleto del servidor (FastAPI síncrono), configuración por `.env`, conexión a MySQL 8.4 y `GET /api/salud`.
- Esquema completo en una migración de Alembic (`0001_esquema_inicial`, 21 tablas) con nombres de restricciones estables; identificadores UUID versión 7 y folio por contador (`serie_folio`).
- Módulo `acceso`: sesión por cookie, contraseñas y PIN con Argon2, cinco roles iniciales como datos y permisos por clave verificados en el servidor.
- Infraestructura de pruebas contra MySQL real, con una base por copia de trabajo (`TEST_DB_SUFFIX`) y datos de prueba repetibles.
- Un solo desplegable: `Dockerfile` en la raíz que construye la interfaz y la sirve desde FastAPI bajo el mismo origen; `docker-compose.yml` con base, aplicación y el túnel de Cloudflare (perfil `tunel`); `.env.example`.

### Fase 1: acceso y catálogo

- Almacenes y ubicaciones (Kepler, Contratistas, Midrex, HYL, Laminador y Minas; Proveedor, En tránsito, Consumido y Baja).
- Categorías con plantilla de reglas y artículos por pieza o por cantidad, retornables o consumibles; requisitos de inspección y de autorización por artículo; inactivar y reactivar con motivo; registro de cambios (auditoría).
- Registro único de códigos compartido (`CodigoService`): un código identifica una sola cosa.
- Etiquetas con código QR: credenciales, piezas y estantes, hoja imprimible desde el navegador.
- Interfaz: base de la aplicación (una sola página, menú según permisos, componentes base), categorías, artículos e inventario.

### Fase 2: entrega

- Trabajadores: alta con periodos de contrato, vigencia, credencial, reingreso, baja y su ficha; **foto opcional del trabajador** (T-09).
- Motor de movimientos con los tipos ENTRADA y ENTREGA: semáforo de código, vigencia, existencias, estado e inspección de la pieza; confirmación en una sola transacción con bloqueos, idempotencia por `id_cliente` y folio sin huecos. El costo no viaja en el vale (I-04, RG-12).
- Inspecciones y estado de las piezas (arnés no apto o con la inspección vencida no se entrega).
- Firma en pantalla, vale con folio y QR, vale imprimible.
- **Escanear solo agrega a un borrador; las existencias cambian al confirmar** (E-28), y **aviso de cantidad inusual** por artículo (E-27).
- Interfaz: trabajadores (lista, alta, ficha y baja), componentes de dominio (escáner con cámara, pistola y teclado, renglón con semáforo, ficha breve, firma, QR), pantalla Entregar completa y detalle de vales.

### Fase 3: límite y autorización

- Límite por artículo, en posesión o por periodo (L-01 a L-05); artículos de uso especial que piden autorización en cada entrega.
- Módulo `autorizaciones`: solicitud, resolución con PIN del supervisor presente o desde su celular, vigencia de 15 minutos, y las reglas A-01 a A-07 (quien captura no se autoriza; un rojo no se autoriza).
- Interfaz: autorizaciones del supervisor, con actualización cada tres segundos.

### Fase 4: devolución y baja

- Devolución por escaneo de pieza o desde la lista del trabajador, con condición (Bueno, Desgaste por uso, Dañado), foto del daño, rechazo de equipo ajeno y pieza sin resguardo (V-01 a V-07, V-12, V-14).
- Baja con pendientes de todos los almacenes, vale de no adeudo y paso a inactivo; reingreso (B-01 a B-09).
- Interfaz: Devolver, resguardo del trabajador y vale de no adeudo desde su ficha.

### Fase 5: traspasos

- Traspaso (salida a En tránsito), recepción con QR y recepción con diferencias; lista de traspasos por recibir (X-01 a X-13).
- Interfaz: Trasladar, Recibir y detalle de recepción con casilla por renglón.

### Fase 6: consulta, reportes e importación

- Módulo `consulta` (solo lectura): escaneo universal, búsqueda por texto, fichas de pieza, artículo y trabajador con línea de tiempo.
- Cuatro reportes con descarga en CSV (con acentos y sin inyección de fórmulas): existencias, movimientos, adeudos y **consumo** (C-08). Filtro por usuario en la bitácora (C-11).
- Importación de inventario desde Excel: pegar o subir `.xlsx`, relación de columnas, vista previa y carga en una sola operación (todo o nada).
- Interfaz: Consultar, fichas, cuatro reportes, entrada de inventario e importación.

### Fase 7: confiabilidad

- **Cancelación de vales** con movimientos inversos y motivo (K-01 a K-05, X-14), y **cancelar y rehacer** (K-05). Interfaz con banda de «Cancelado».
- **Mis movimientos de hoy** (C-12): cada usuario ve y corrige lo que hizo en el día.
- **Respaldo y restauración** (TASK-F7-05): `scripts/respaldo.sh` y `respaldo.ps1` (base y archivos, con retención opcional), `restaurar.sh` y `restaurar.ps1` (con `--base` para probar en otra base). Probados respaldando y restaurando en otra base.
- **Verificación de consistencia**: `python -m app.mantenimiento verificar` (existencias contra bitácora, ubicación de piezas, folios, cancelaciones, códigos y no adeudo) y `reconstruir-existencias --simular`/`--aplicar`.

### Aplicación instalable (PWA)

- Manifiesto, iconos (192, 512 y adaptable), icono para iPhone y atajos (Entregar, Devolver, Consultar); botón «Instalar aplicación» en el menú.
- Service worker mínimo: acelera los archivos con huella y muestra una pantalla de «sin conexión» al abrir sin red. No guarda la API ni datos de negocio; el modo sin conexión sigue excluido.

### Funciones absorbidas de la segunda ola

- **Foto del trabajador** (FEAT-005, T-09): pasó al MVP como foto opcional en el alta.
- **Ajuste de vigencia de una inspección** por supervisor o administrador, con motivo (P-07, permiso `piezas.ajustar_vigencia`).
- **Usuarios y asignación de personal a almacenes** (parte de FEAT-006, AC-12 y AC-13, permiso `almacenes.asignar_personal`): API de usuarios y personal y aviso `ALMACEN_CAMBIO`. Falta su pantalla y la matriz editable de roles.
- **Reporte de consumo**, **Mis movimientos de hoy**, **cancelar y rehacer** y el filtro por usuario de la bitácora, descritos arriba.

### Seguridad

Lo que existe en el código y está documentado en [security-model.md](../architecture/security-model.md):

- Contraseñas y PIN con Argon2; el PIN es distinto de la contraseña y tiene su propio contador. Bloqueo de cinco minutos tras cinco intentos fallidos (429 `DEMASIADOS_INTENTOS`, con `Retry-After`) y mensajes de error genéricos.
- Sesión en cookie `HttpOnly` (`Secure` y `SameSite=Lax` bajo HTTPS); el rol, los permisos y el almacén se leen en cada petición, así un cambio aplica de inmediato.
- Permisos por clave verificados en el servidor en cada endpoint; datos reservados (costo, CURP y NSS) que no se envían sin su permiso de información.
- Movimientos y vales solo se insertan; las existencias cambian solo junto con un movimiento. La única excepción a la escritura de existencias es el comando de línea de comandos `reconstruir-existencias --aplicar`, con confirmación y auditoría.
- Archivos (firmas y fotos) validados por su contenido y tamaño, con nombre generado y fuera de la carpeta pública; importación de `.xlsx` en memoria, rechazando macros, archivos que no son `.xlsx`, bombas de compresión y tamaños excesivos; CSV con celdas que empiezan por `=`, `+`, `-` o `@` neutralizadas.
- Tabla de auditoría que nunca guarda contraseñas, PIN ni hashes.
- Corrección: autorización para quien opera todos los almacenes y firma visible en el detalle del vale (`d51b64d`).
- Errores con forma uniforme: métodos no permitidos (`METODO_NO_PERMITIDO`, 405) y fallas inesperadas sin detalles técnicos (`ERROR_INTERNO`, 500).
- Endurecimiento tras una revisión independiente: sesión revocable (`usuario.version_sesion`), bloqueo de intentos sin carreras, límite de tamaño por ruta (413 `CUERPO_MUY_GRANDE`), firma validada como PNG completo con trazo, huella del cuerpo para la idempotencia (409 si el `id_cliente` cambia de cuerpo), solicitud de autorización armada por el servidor, `ENTORNO=produccion` con arranque protegido, reintento ante interbloqueos (503, nunca 500) y alcance por almacén en el escaneo de vales. Migraciones `0002_version_sesion` y `0003_huella_cuerpo`.
- Correcciones de contradicciones entre código y documentos: el no adeudo de un Activo exige `trabajadores.iniciar_baja` (el supervisor lo recibe), las etiquetas piden solo `etiquetas.imprimir`, `ALMACEN_CAMBIO` se decide en un solo lugar, la recepción con diferencias exige observación (RG-14) y una prueba confirma que vales y movimientos no se editan. El no adeudo acepta `almacen_id` para quien opera todos los almacenes.

### Documentación y herramientas

- Guía del almacenista: [guia-almacenista.md](../guia-almacenista.md).
- Usuarios de prueba por rol, contraseña y PIN de prueba y procedimiento de respaldo, en el [README](../../README.md).
- Se retiró `pywebpush`, dependencia que nada usaba.
- Documentos alineados con el código: costo en el catálogo y no en la entrada (I-04), precisión de V-02, prioridades de E-27, E-28 y P-07, y los errores 405, 409 genérico y 500 en el contrato de la API.

### Conocido y pendiente

- Lo de la segunda ola sigue sin construir: vale como prueba (FEAT-001), cierre de almacén (FEAT-002), dotación (FEAT-003), mínimos y estados (FEAT-004) y la matriz de roles (FEAT-006).
- La inmutabilidad de vales y movimientos depende solo del código hasta FEAT-001 (sin sello contra alteración).
- La cámara usa la API nativa `BarcodeDetector`: en un navegador que no la trae se usa pistola o teclado.
- El túnel de Cloudflare no se ha probado con un token real, y no se ha ensayado el flujo con un celular real ni en el servidor. Ver la [checklist](mvp-checklist.md).
