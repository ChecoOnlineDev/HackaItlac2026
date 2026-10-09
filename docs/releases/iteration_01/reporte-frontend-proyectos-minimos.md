# Proyectos, mínimos y operación por almacén: interfaz implementada

## Tarea realizada

Se agregó `/proyectos` con búsqueda, filtros por almacén y situación, paginación y ficha. Quien tiene `proyectos.administrar` puede crear, editar, extender, cerrar y reabrir. El servidor valida las fechas, el almacén, los permisos y los impedimentos; los errores se conservan junto al formulario.

El alta y reingreso de trabajadores muestran proyectos disponibles agrupados por almacén. La ficha permite cambiar, agregar o terminar un proyecto y revisar el historial, sin modificar el resguardo. La lista admite `proyecto_id` y `sin_proyecto` en la URL y muestra los proyectos de cada persona.

El inventario muestra mínimo y no disponible, destaca con texto y color los artículos por debajo del mínimo y permite filtrarlos. Con `inventario.minimos`, «Configurar mínimos» permite establecer o quitar un mínimo por artículo en el almacén elegido. Quitar el mínimo envía `null` y conserva las existencias. La ficha de pieza permite mantenimiento, calibración y vuelta a apta cuando corresponde; para piezas que requieren inspección se indica usar «Inspeccionar». El servidor sigue siendo quien autoriza cada transición.

La identidad de la sesión muestra «Almacén donde operas» cuando hay más de un almacén asignado, sin permiso de todos los almacenes. Cambiarlo actualiza la sesión desde `PUT /api/sesion/almacen`. La entrega conserva su captura y avisa cuando cambia el almacén activo. La evaluación muestra el proyecto decidido por el servidor o un selector cuando la persona tiene varios; el borrador conserva `proyectoId`. Evaluación y confirmación envían el proyecto y la observación, incluidos los motivos PR-10.

## Archivos modificados

- `frontend/app/api/proyectos.ts`, `api/tipos.ts` y `sesion/sesion.tsx`.
- `frontend/app/componentes/proyectos/`, `personas/tipos.ts` y `navegacion/identidad-usuario.tsx`.
- `frontend/app/routes/personas/proyectos.tsx`, `trabajador-nuevo.tsx`, `trabajador-ficha.tsx` y `trabajadores.tsx`.
- `frontend/app/componentes/catalogo/hoja-minimos.tsx`, `catalogo/tipos.ts`, `consulta/hoja-estado-pieza.tsx`.
- `frontend/app/routes/inventario/inventario.tsx` y `routes/consulta/pieza.tsx`.
- `frontend/app/componentes/entrega/tipos.ts`, `use-evaluacion.ts`, `borrador.ts` y `routes/operacion/entregar.tsx`.

El registro de ruta y menú se integró en la tarea principal.

## Decisiones y supuestos

Se reutilizaron los componentes y colores existentes, sin dependencias nuevas. Las respuestas fuera de orden se cancelan con los mecanismos actuales; después de guardar se recarga únicamente la consulta afectada. Los selectores recorren las páginas del catálogo para no omitir proyectos o artículos fuera de la primera página. Los campos de sesión nuevos son opcionales en TypeScript para conservar compatibilidad con la demostración y las respuestas anteriores.

## Validaciones

`pnpm typecheck` y `pnpm build` pasaron con proyectos, mínimos, estados, selector de sesión y proyecto en la entrega. La verificación final del conjunto se registra en el reporte de la tarea principal. No se ejecutó aún un recorrido autenticado en navegador o Android físico contra estos endpoints nuevos.

## Riesgos y deuda

Esto no declara FEAT-013 completa. Faltan el uso por proyecto del tablero (TB-05), los contadores detallados previos al cierre y la administración del conjunto de almacenes de otros usuarios. El cierre muestra el número de trabajadores proporcionado por la ficha y luego los resultados reales que devuelve el servidor; no inventa un conteo de resguardo ni de trabajadores que perderán su último proyecto.

El APK previamente generado debe reconstruirse y sincronizarse para incluir estas pantallas. Este cambio no implementa almacenamiento o sincronización sin conexión.

## Documentación actualizada y siguiente acción

Este reporte describe las pantallas y transiciones construidas. La tarea principal integra los contratos, reglas y estado global, revisa los cambios y verifica el flujo Administrador → proyecto → RH → trabajador → entrega con la base migrada.
