# Reporte IMHOTEP-003 — Unificación visual global

## Tarea realizada

El sidebar azul es ahora la navegación compartida de todas las pantallas autenticadas y perfiles, sin depender de Inicio ni del alcance administrativo. El menú móvil usa el mismo lenguaje visual. Las tarjetas de acceso de Inicio comparten fondo azul industrial, iconos y texto blancos, espaciado y foco visibles. Se centraliza la paleta para encabezados, botones, campos, tablas y pestañas, conservando errores y semáforos.

## Archivos modificados

- `frontend/app/app.css`: tokens azul profundo, industrial, activo, suave y fondo; estilos compartidos de navegación, accesos, menú móvil y superficies.
- `frontend/app/componentes/navegacion/armazon-escritorio.tsx`: sidebar en todas las rutas y perfiles, con ámbito de sesión.
- `frontend/app/componentes/navegacion/identidad-usuario.tsx`: identidad reutilizable, nombre/rol/ámbito y marca demo recibidos de sesión.
- `frontend/app/componentes/navegacion/menu-hoja.tsx`: menú azul y componente común de identidad.
- `frontend/app/componentes/navegacion/armazon-movil.tsx`: encabezado con altura adaptable para nombres largos.
- `frontend/app/componentes/ui/hoja.tsx`: className opcional para aplicar el tema únicamente a la hoja de navegación.
- `frontend/app/routes/inicio.tsx`: apariencia común de todos los accesos, conservando destinos y precarga.
- `frontend/app/componentes/tablero/tablero-admin.css`: se trasladaron los estilos de navegación global a app.css; conserva los del dashboard.
- `docs/product/ui-ux.md`, este reporte y referencia en el reporte IMHOTEP-002.

## Decisiones y supuestos

Rama `codex/imhotep-002-dashboard`, HEAD `577074a9f18581de2f047298ce2983b508a71b98`. Se conservaron los cambios locales IMHOTEP-002 y R3. No hubo commits, push, merges, rebase, PR, cambios de rama o despliegues.

Paleta compartida: #102F70 profundo, #0755A8 industrial, #1769EA activo, #E8F1FC suave y #F5F8FD fondo. Se mantienen superficies blancas y bordes legibles. La navegación por permisos, clasificación funcional y precarga permanecen intactas. Semáforos y text-destructive no se recolorean. No se modificaron backend, API de demostración, datos, autenticación, consultas, cálculos ni operaciones.

Se reutilizaron frontend y API activos, sin reiniciar la sesión ni reinstalar dependencias. La demo no representa toda la API del producto.

## Validaciones ejecutadas

- `pnpm typecheck`: código 0 tras los cambios finales.
- `pnpm build`: código 0 tras los cambios finales. Avisos informativos de tiempos de plugins; sin fallo de construcción.
- `git diff --check`: código 0.
- Revisión independiente: permisos/destinos/precarga preservados. Se corrigieron dos problemas detectados: contador móvil blanco sobre fondo pálido e iniciales de avatar de escritorio con bajo contraste.
- Escritorio 1440 x 1000: navegación Inicio → Entregar y entre Inventario, Catálogo, Consultar, Devolver, Traspasos, Trabajadores, Compras, Supervisión y Almacenes. Marco azul e identidad coherentes, opción activa visible.
- Inicio: accesos uniformes y dashboard con cifras ficticias anteriores intactas.
- Entregar, Devolver, Consultar y Traspasos: formularios iniciales y ayudas visibles. No se confirmó ninguna operación; cámara no disponible en este navegador.
- Inventario, Catálogo y Trabajadores: encabezados, búsquedas y estado de error por endpoint no incluido en la demo. Listas/datos no validados.
- Compras y Supervisión: estados sin solicitudes/autorizaciones visibles. No se validaron expedientes, resoluciones o compras reales.
- Almacenes: tabla visible con registros mínimos ficticios. El adaptador no proporciona todos sus atributos; etiquetas derivadas de datos incompletos no validan el estado real de almacenes.
- Móvil 390 x 844: Inicio y menú azul, acceso a Entregar y retorno. Sin desbordamiento horizontal (Inicio 375/375 px; Entregar 390/390 px de ancho/contenido). Se permitió crecer al encabezado móvil para evitar recortar el nombre largo.
- Consola revisada durante navegación: sin errores ni advertencias registrados. Los errores de módulos no respaldados son estados controlados de la interfaz.

## Evidencias

Capturas en `tmp/imhotep-demo/capturas/`, ignoradas por Git y Docker:

- `003-inicio.jpg`: Inicio administrativo.
- `003-entregar.jpg`: Entregar con sidebar azul.
- `003-inventario.jpg`: Inventario, con limitación visible de la demo.
- `003-catalogo.jpg`: Catálogo, con limitación visible de la demo.
- `003-consultar.jpg`: módulo representativo adicional.
- `003-inicio-movil.jpg`: Inicio móvil.
- `003-menu-movil.jpg`: navegación móvil.
- `003-almacenes.jpg`: tabla con datos mínimos ficticios; no valida estados operativos.

## Riesgos o deuda pendiente

La revisión visual cubre los marcos y controles disponibles, no los flujos completos de entrega, devolución, escaneo, traspasos, permisos o autenticación real. Pantallas de detalle, edición, importación, reportes no visitados y otros perfiles no se validaron exhaustivamente en navegador. Requieren API real local con datos completos. No se reemplazaron pantallas por maquetas ni se ampliaron artificialmente las respuestas del adaptador.

Los tokens son globales, por lo que también armonizan las superficies de acceso y otros componentes existentes. No se modificó su flujo. Las tablas conservan su desplazamiento propio cuando corresponde. No se observaron regresiones de presentación en las vistas revisadas; se requiere aprobación visual del usuario.

## Documentación actualizada

`docs/product/ui-ux.md` registra la nueva identidad global y supera el alcance solo administrativo de IMHOTEP-002. El reporte anterior enlaza esta continuación.

## Siguiente acción

Revisar en http://127.0.0.1:21010/. Se dejan los servicios activos y se detiene el trabajo para aprobación visual. No se publica nada.
