# FEAT-016: interfaz de inspecciones

## Tarea realizada

Se implementaron `/inspecciones` y `/inspeccionar`, con permiso por ruta y una entrada de menú con contador tomado de `GET /api/inspecciones/pendientes?solo_contar=true`.

La lista ofrece Vencidas, Por vencer y Sin inspección, sus conteos, filtros por almacén, categoría, ubicación y búsqueda, y paginación. La pestaña inicial usa la urgencia que indica la respuesta. Cada pieza presenta código, serie, días en palabras y ubicación. La acción del servidor decide entre inspeccionar, mostrar un recordatorio de devolución o esperar su recepción. El recordatorio no envía mensajes ni escribe datos. Al inspeccionar en otro almacén asignado, la interfaz cambia el almacén activo antes de abrir el registro.

El registro individual carga la ficha desde la API, muestra su vigencia, periodo, últimas inspecciones y la posibilidad de inspeccionarla. Los cinco puntos admiten Bien, Mal o No aplica; un punto Mal propone No apta y el usuario decide el resultado. Se pide observación para No apta o Apta con un punto Mal. La fecha que quedará viene del servidor. La foto opcional admite JPG, PNG o WebP de hasta 3 MB. Cada intento conserva su `id_cliente` para reintentar sin duplicar.

«Varias piezas» admite hasta 50 códigos y evita duplicados. Las piezas con problemas se revisan individualmente antes del envío. La confirmación nombra los cinco puntos revisados. Se envía un único lote con un identificador estable por pieza; las respuestas guardadas, repetidas y rechazadas se muestran por renglón. Reintentar conserva los identificadores originales. La captura se congela al enviarse para evitar que una respuesta incierta se reintente con otro contenido.

En los formularios de artículo y categoría se agregó el aviso de 1 a 90 días, vacío para heredar. El artículo muestra el valor resuelto y de dónde sale; la categoría indica cuántos artículos conservan su propio aviso. La aplicación de una plantilla no convierte el aviso de la categoría en un valor propio del artículo. El tablero utiliza los tres conteos del servidor y dirige a la pestaña más urgente, sin asumir un aviso fijo de siete días.

## Archivos modificados

- `frontend/app/api/inspecciones.ts`, `api/tipos.ts` y `api/tablero.ts`.
- `frontend/app/routes/operacion/inspecciones.tsx`, `inspeccionar.tsx`, `routes/consulta/pieza.tsx` y `routes.ts`.
- `frontend/app/componentes/inspecciones/registro-inspeccion.tsx`, `lote-inspecciones.tsx`, `consulta/tipos.ts`, `consulta/linea-de-tiempo.tsx`, `consulta/hoja-estado-pieza.tsx`.
- `frontend/app/componentes/catalogo/tipos.ts`, `formulario-reglas.tsx`, `hoja-articulo.tsx` y `hoja-categoria.tsx`.
- `frontend/app/componentes/tablero/tarjetas-indicadores.tsx`, `sesion/menu.ts` y `sesion/contadores.ts`.
- Componentes `toggle.tsx` y `toggle-group.tsx` agregados mediante el CLI de shadcn. Usan la dependencia Base UI existente; no cambió `package.json` ni el archivo de bloqueo.

## Decisiones y supuestos

La lista, urgencia, permisos, transiciones, alcance y fechas se basan en la respuesta del servidor. La interfaz solo valida la captura para ayudar a quien inspecciona. Se conservaron los estilos existentes y la sesión por cookie. El formulario de mantenimiento permite regresar una pieza que requiere inspección a No apta, pendiente de inspección, conforme al contrato P-06 confirmado durante la construcción.

## Validaciones y límites

`pnpm typecheck`, `pnpm build` y `git diff --check` pasaron; `pnpm test` pasó con las 14 pruebas existentes. Las pruebas de API y la verificación final del conjunto se registran en el reporte de la tarea principal. El contrato fue coordinado con el agente del backend, que estaba implementándolo al escribir este reporte; todavía no se ha demostrado el recorrido autenticado de lista, inspección y lote. Por eso este reporte acredita la construcción de la interfaz, no el cumplimiento completo de FEAT-016.

## Riesgos, documentación y siguiente acción

Falta comprobar en navegador y Android real la cámara, la foto, los reintentos, los cambios de almacén y el rechazo parcial de un lote. Las notificaciones locales de Android dependen de FEAT-020 y no se implementaron aquí. El APK anterior debe reconstruirse para incluir estas pantallas.

Este documento deja el estado verificable de la interfaz; las reglas, contratos, migraciones y estado de FEAT-016 se actualizan con el cambio de backend. La siguiente acción es ejecutar las pruebas de API y el recorrido Almacenista/Supervisor con la base migrada, y cerrar las diferencias que aparezcan.
