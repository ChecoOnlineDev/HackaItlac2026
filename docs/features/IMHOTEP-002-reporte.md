# Reporte de IMHOTEP-002

## Tarea realizada

Propuesta visual local para el tablero administrativo basada en la referencia proporcionada. Sidebar azul profundo con degradado discreto, pestañas activas azules, filtros con borde azulado, tarjetas blancas con iconos y detalles suaves, barras por categoría con azules compatibles y desglose por almacén adaptado a celular.

## Archivos modificados

- `frontend/app/componentes/navegacion/armazon-escritorio.tsx`: activa la apariencia del sidebar solo en `/` con `tablero.ver` y `almacenes.todos`.
- `frontend/app/componentes/tablero/tablero.tsx`: limita la apariencia al tablero administrativo y pasa su variante a Valor.
- `frontend/app/componentes/tablero/tarjetas-indicadores.tsx`: iconos decorativos y sufijo MXN pequeño.
- `frontend/app/componentes/tablero/pestana-valor.tsx`: títulos con iconos, moneda explícita y desglose móvil con los mismos datos.
- `frontend/app/componentes/tablero/tablero-admin.css`: estilos de la propuesta, limitados por clases de alcance.
- `docs/product/ui-ux.md`: patrón administrativo y estado de propuesta.
- Este reporte.

## Decisiones y supuestos

- Rama de trabajo: `codex/imhotep-002-dashboard`, creada desde HEAD `577074a9f18581de2f047298ce2983b508a71b98`. El repositorio estaba limpio antes del trabajo. No se hicieron commits, push, merges, rebase ni cherry-pick.
- Se inspeccionó producción mediante navegador, con sesión iniciada por el usuario, únicamente para lectura. Se observó el total real de $978,364.08 y sus desgloses por categoría y almacén.
- Se conserva el formateador mexicano existente, sus dos decimales y todos los cálculos, consultas, filtros, permisos y agrupaciones. MXN se indica en tarjetas y categorías; la tabla usa una nota de moneda común.
- Los estilos administrativos se activan por permisos existentes, no por nombre del rol. Fuera del Inicio administrativo el sidebar conserva su apariencia habitual.
- No se añadieron dependencias ni se modificaron backend, datos o secretos.

## Validaciones ejecutadas

- `git branch --show-current` y `git status --short`: rama correcta; cambios locales de esta tarea conservados.
- `git diff --check`: pasa.
- Revisión estática por otro agente: identificó que el color de las cifras ocultaba el resaltado de inspecciones por vencer; corregido excluyendo `.text-destructive` del nuevo color.
- `pnpm install --frozen-lockfile`: bloqueado por errores de conexión al registro npm y verificación incompleta del lockfile.
- Reintento con menor concurrencia: descargó parte de las dependencias, pero no completó la instalación; detenido antes de entregar la propuesta.
- `pnpm typecheck` y `pnpm build`: intentados; pnpm inició la instalación pendiente antes de ejecutar los scripts. No hay resultado de tipos o construcción y no se consideran aprobados.
- Localhost, consola, escritorio, móvil y capturas finales: pendientes porque no se completó la instalación. No se conectó el frontend local a producción.

## Riesgos o deuda pendiente

- La propuesta todavía requiere validación en navegador; no se afirma que su layout esté visualmente aprobado.
- Completar las dependencias y correr tipos y construcción antes de aceptar el cambio para publicación.

## Documentación actualizada

- `docs/product/ui-ux.md`, sección «Propuesta local IMHOTEP-002: tablero administrativo».

## Siguiente acción

Revisión del usuario de esta propuesta. Cuando el entorno permita completar las dependencias, levantar el frontend con una API local segura, revisar escritorio y móvil y obtener capturas. Toda publicación queda fuera de esta misión y requiere autorización expresa posterior.

## IMHOTEP-002-V1: intento de validación local (8 de octubre de 2026)

### Tarea realizada

Se conservó `codex/imhotep-002-dashboard`, HEAD y todos los cambios locales. No se modificó la estética ni se corrigió código de aplicación: el bloqueo ocurre al cargar las herramientas, antes de analizar el rediseño.

### Archivos modificados

Solo se actualizó este reporte. La instalación generó las dependencias locales ignoradas por Git. `package.json` y `pnpm-lock.yaml` no cambiaron.

### Decisiones y supuestos

Se intentó el arranque con `API_DESTINO=http://127.0.0.1:21011` y `--host 127.0.0.1`, sin destino de producción. No se levantó un backend, no se usaron credenciales, no se hicieron peticiones a producción ni se crearon datos de demostración. No se creó una vista alternativa que sustituyera la aplicación.

### Validaciones ejecutadas

- `git branch --show-current`, `git status --short` y `git rev-parse HEAD`: rama y HEAD sin cambios; modificaciones anteriores conservadas.
- `pnpm install --frozen-lockfile --network-concurrency=4 --fetch-retries=0 --fetch-timeout=15000`: terminó con código 0; 436 paquetes instalados.
- SHA256 del lockfile antes y después: `54D533534D1407787F6FF81ED42F866AEE1D5E4F45B51D9F730C53AD57B327DF`; idéntico.
- `pnpm typecheck`: código 1 antes de generar tipos, por `Cannot find native binding` de Rolldown 1.2.9.
- `pnpm build`: código 1 por el mismo componente nativo ausente. No hay construcción validada.
- `pnpm dev --host 127.0.0.1`, con destino de API local explícito: código 1 por el mismo error. El error también informa que no encuentra el respaldo `@rolldown/binding-wasm32-wasi`.
- `git diff --check`: pasa.

### Riesgos o deuda pendiente

Localhost no pudo arrancar. No se validaron escritorio, móvil, cifras, filtros, gráficas, consola ni otros perfiles en navegador. No hay capturas locales de antes y después ni una URL activa para aprobación visual. Este resultado es un bloqueo de dependencias, no evidencia de un fallo del rediseño.

### Documentación actualizada

Este reporte registra el resultado V1 sin reemplazar el historial de la propuesta.

### Siguiente acción

Se detiene la validación conforme a la instrucción del usuario. Resolver la dependencia nativa de Rolldown y repetir los tres comandos antes de preparar la vista previa segura. No se hicieron commits, push, merges, cambios de rama, PR ni despliegues.

## Estado vigente: Rolldown reparado y demostración local lista

### Tarea realizada

Se reparó la instalación local de Rolldown y se preparó una API de demostración aislada para revisar el frontend auténtico. Este resultado supera los bloqueos V1 anteriores. Se conserva la rama `codex/imhotep-002-dashboard` y HEAD `577074a9f18581de2f047298ce2983b508a71b98`, sin nuevos cambios estéticos, commits, push, merges ni despliegues.

### Causa y reparación de Rolldown

Node v24.20.0, Windows x64; pnpm 11.25.0; Rolldown 1.2.9. El lockfile contemplaba `@rolldown/binding-win32-x64-msvc@1.2.9` y no había configuraciones para omitir dependencias opcionales. Existían la carpeta del almacén virtual y su enlace, pero faltaban los archivos del paquete; la carga directa devolvía MODULE_NOT_FOUND. La reparación sin conexión no recuperó el archivo ausente de la caché.

Se obtuvo la versión exacta con pnpm en un proyecto temporal ignorado dentro de node_modules y se repusieron únicamente los archivos del binding en su destino existente. La carga directa del binding y Rolldown pasó. No se agregó una dependencia permanente ni se reinstalaron destructivamente todas las dependencias. `package.json` y `pnpm-lock.yaml` permanecen intactos; SHA256 del lockfile: `54D533534D1407787F6FF81ED42F866AEE1D5E4F45B51D9F730C53AD57B327DF`.

### Archivos modificados y aislamiento

Solo se actualizó este reporte dentro de los archivos de la propuesta. El material auxiliar está en `tmp/imhotep-demo/`: `imhotep-local.mjs`, `README.md`, `verificar.mjs` y capturas. La carpeta tmp está excluida de Git y Docker; el servidor además rechaza arrancar fuera de esa ubicación. No se modificaron backend, dependencias declaradas, configuración productiva ni lógica de negocio.

### Decisiones y supuestos

Se revisó el backend original y su autenticación por cookies, Argon2 y JWT. No están disponibles uv, Docker, MySQL ni un entorno Python del backend preparado. Conforme a la autorización del usuario, se eligió la API simulada aislada para completar la revisión visual sin instalar infraestructura adicional.

La API escucha exclusivamente en `127.0.0.1:21011`; no carga .env, no conecta bases ni realiza solicitudes externas. El frontend se inició con `API_DESTINO=http://127.0.0.1:21011` y `--host 127.0.0.1`. Las escrituras de inventario, configuración y usuarios se rechazan. Solo se crean y cierran sesiones temporales en memoria.

Hay cinco perfiles: `local.admin`, `local.almacenista`, `local.supervisor`, `local.compras` y `local.rh`. El primer ingreso permite elegir una contraseña de 12 a 128 caracteres directamente en el navegador; se guarda únicamente un hash scrypt con sal en memoria. Reiniciar la API elimina contraseñas y sesiones. El usuario ya ingresó como administrador y su contraseña no quedó registrada en el chat. La sesión muestra DEMOSTRACIÓN LOCAL. Todos los datos son ficticios.

### Validaciones ejecutadas y resultado

- `pnpm typecheck`: aprobado, código 0.
- `pnpm build`: aprobado, código 0; sin errores independientes de Rolldown.
- Revisión independiente del adaptador: sin bloqueos; verificó aislamiento, ausencia de accesos externos y exclusión del material de demostración del despliegue.
- `node tmp/imhotep-demo/verificar.mjs`: 43 comprobaciones aprobadas en un servidor de prueba separado, sin reiniciar la sesión del usuario. Cubren perfiles, cookies, cierre de sesión, rechazo de escrituras, alcances y respuestas del tablero.
- Navegador, escritorio 1440 x 1000: acceso administrativo, cuatro tarjetas, seis categorías y seis almacenes visibles. Total ficticio $917,000.08 MXN; almacén $915,799.58, resguardo $1,200.50 y tránsito $0.00. Categorías y almacenes suman el total.
- Filtros: categoría, almacén, fechas, limpiar filtros, agrupación de consumo por almacén y estados sin registros funcionan con las respuestas ficticias. Consumo total de todas las categorías: 18 unidades; categoría predeterminada: 12.
- Móvil 390 x 844: tarjetas, categorías, desglose por almacén y gráfica de consumo revisados. Sin desbordamiento horizontal de página.
- Consola del navegador: sin errores ni advertencias observados durante estas comprobaciones.
- Otros perfiles: comprobados mediante el adaptador y revisión del alcance CSS; no se afirma una revisión visual completa de cada perfil ni una validación de permisos del backend real.

Capturas válidas del frontend actual: `tmp/imhotep-demo/capturas/escritorio-tablero.jpg`, `escritorio-dashboard.jpg`, `movil-indicadores.jpg`, `movil-categorias.jpg` y `movil-grafica.jpg`. No se generó un antes local equivalente; la referencia inicial no es una captura comparable con estos datos ficticios.

### Riesgos o deuda

Estas pruebas validan presentación y controles del frontend con una API simulada. No validan autenticación, permisos, reglas de negocio ni integración de la API real. El backend original con MySQL local queda pendiente. Los perfiles Compras y RH no tienen tablero en la demostración. Reiniciar el servidor elimina todas las sesiones y obliga a establecer nuevamente las contraseñas locales.

### Documentación y siguiente acción

Procedimiento de arranque y acceso en `tmp/imhotep-demo/README.md`. Vista previa activa en http://127.0.0.1:21010/. Se dejan frontend y API local funcionando para aprobación visual del usuario. No se amplía el rediseño ni se publica nada.

## IMHOTEP-002-R3: ajustes finales (8 de octubre de 2026)

### Tarea realizada

Se retiró la descripción repetida de las cuatro tarjetas monetarias administrativas y se agregó una nota común debajo del grupo. Se conservan títulos, iconos, colores, importes, formato mexicano y MXN. La nota aparece solo en Valor administrativo con indicadores, nunca en el estado vacío ni en otras pestañas.

El bloque de usuario del sidebar administrativo separa nombre, rol y ámbito; la identificación DEMOSTRACIÓN LOCAL aparece como etiqueta discreta únicamente si el nombre recibido trae ese sufijo. Se usa el rol de la sesión, el almacén asignado o el permiso de alcance global; nunca el almacén seleccionado en el tablero. Los datos faltantes tienen un texto neutral. Otros perfiles y secciones conservan la presentación anterior. La navegación móvil existente no utiliza este sidebar y no se rediseñó.

### Archivos modificados en R3

- `frontend/app/componentes/tablero/pestana-valor.tsx`: nota común administrativa.
- `frontend/app/componentes/tablero/tarjetas-indicadores.tsx`: detalle opcional, sin párrafos vacíos.
- `frontend/app/componentes/navegacion/armazon-escritorio.tsx`: jerarquía de identidad desde sesión.
- `frontend/app/componentes/tablero/tablero-admin.css`: descripción por posición específica para que la cifra no herede su tamaño al quitarla; etiqueta discreta.
- `docs/product/ui-ux.md`: documentación del refinamiento.
- Este reporte. Capturas ignoradas en `tmp/imhotep-demo/capturas/r3-escritorio.jpg`, `r3-movil.jpg` y `r3-identidad.jpg`.

### Decisiones y supuestos

Rama y cambios previos conservados. Frontend respondió 200 y API local 401 sin sesión, como corresponde. Se reutilizaron ambos servicios sin reiniciar y la sesión del usuario siguió activa. No se reinstalaron dependencias ni se alteró la API simulada, el backend real, contratos o permisos.

### Validaciones ejecutadas

- `pnpm typecheck`: código 0.
- `pnpm build`: código 0; advertencia informativa de tiempos de plugins, sin fallo de construcción.
- Revisión independiente por otro agente: sin hallazgos bloqueantes; importes, alcance y contraste de advertencias conservados.
- Escritorio 1440 x 1000: cuatro tarjetas alineadas, nota única y usuario con nombre, rol, ámbito y etiqueta legibles; captura general y acercamiento guardados.
- Móvil 390 x 844: cuatro tarjetas y nota con ajuste de línea; ancho de documento y contenido 375 px, sin desbordamiento horizontal. Menú móvil abre y cierra.
- Navegación Resumen, Piezas, Consumo y Valor comprobada. La nota solo está en Valor. Cambio a Consultar conserva el sidebar habitual; retorno a Inicio restaura el administrativo.
- Botón Salir abre la confirmación; Quedarme la cierra. No se ejecutó el cierre definitivo para conservar la sesión del usuario.
- Consola: sin errores ni advertencias observados.
- `git diff --check`: aprobado.

### Riesgos o deuda pendiente

Se valida el frontend real con datos ficticios y API de demostración. Autenticación y reglas del backend real siguen fuera de esta validación. El marcador de demostración se interpreta del sufijo existente en el nombre de sesión, sin agregar campos al contrato. No se hizo una revisión visual completa de todos los perfiles; el alcance de los cambios fue revisado estáticamente.

### Documentación actualizada y siguiente acción

Reporte y patrón visual actualizados. Localhost continúa en http://127.0.0.1:21010/ para aprobación visual. No hubo commits, push, cambios de rama, PR, merges ni despliegues. Se detiene el trabajo para revisión del usuario.

## Continuación IMHOTEP-003
La misión autorizó ampliar la identidad visual al frontend completo. El resultado vigente y sus limitaciones están documentados en [IMHOTEP-003-reporte.md](IMHOTEP-003-reporte.md). Los cambios anteriores se conservan.
