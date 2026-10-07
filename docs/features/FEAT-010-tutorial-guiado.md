# FEAT-010: Tutorial guiado de práctica

Estado: **construida, con pruebas pendientes.** Probada a mano en navegador (computadora y vista móvil de 375 px) con supervisor y almacenista: los cuatro recorridos, `Escape`, banda de práctica, sin peticiones de escritura y sin borradores. Pendiente: PWA instalada, «reducir movimiento», recorrido solo con teclado, el diálogo de «Recibir todo» con más de 10 renglones (el traspaso de práctica no llega a ese umbral) y las pruebas automáticas que pide «Validaciones requeridas». Aprobada por el usuario. Amplía el alcance del MVP (ver [mvp-scope.md](../product/mvp-scope.md)). Es solo de interfaz: no cambia el servidor, el modelo de datos, la API ni las reglas de negocio.

## Problema u oportunidad

La hipótesis del MVP dice que un almacenista sin capacitación puede entregar, devolver y consultar escaneando, en segundos. Hoy lo único que lo respalda son dos guías en documento ([guía del almacenista](../guia-almacenista.md) y [guía por rol](../guia-por-rol.md)), que nadie lee con el escáner en la mano. Un almacenista nuevo no tiene cómo practicar sin registrar un vale real, y los vales no se borran: anular uno deja el vale y su movimiento inverso para siempre, consume folios y aparece en reportes y auditoría.

## Objetivo

Un interruptor «Tutorial» que, al encenderse, lleva a la persona paso a paso por una operación básica **sobre las pantallas reales** y con **datos de ejemplo**. En cada paso la pantalla se oscurece y se bloquea, salvo el único elemento que toca; ese elemento va rodeado por un círculo y con una flecha. Nada de lo que haga en práctica llega al servidor.

## Historia de usuario

Como almacenista nuevo, quiero practicar una entrega, una devolución, una consulta y una recepción con una guía que me diga dónde tocar, para perder el miedo a equivocarme antes de operar de verdad.

Como supervisor, quiero que mi gente practique sin crear vales ni mover existencias reales, para que el inventario no se ensucie con prácticas.

Todavía no hay historia en `docs/stories/`: se escribe al iniciar la construcción.

## Alcance incluido

- **Interruptor «Tutorial» (TU-01)** en el pie del menú lateral de computadora, en la hoja «Menú» del celular y en el encabezado móvil dentro de los flujos. Funciona igual en computadora, vista móvil y aplicación instalada (PWA).
- **Modo práctica sin servidor (TU-02).** Mientras está encendido, las pantallas reales no llaman a la API: las lecturas y las confirmaciones las responde una capa del cliente con un trabajador y unos artículos ficticios, y la confirmación devuelve un folio de práctica. Una banda fija dice «Práctica: nada de esto se guarda».
- **Bloqueo y resalte (TU-03).** Una capa por encima de todo (hojas, diálogos, avisos y la banda de sin conexión) deja pasar el toque solo al elemento del paso. Lo marcan un círculo y una flecha, y un globo corto dice qué hacer. El globo trae «Siguiente» cuando el paso es solo de lectura, y «Salir» siempre.
- **Cuatro recorridos (TU-04):** Entregar (trabajador, artículos con semáforo, firma y folio), Devolver (escanear la pieza, elegir condición, confirmar), Consultar (escanear o escribir y leer la ficha) y Recibir un traspaso (Recibir todo o marcar por renglón, y confirmar).
- **Pasos según permisos (TU-05).** El recorrido solo aparece si la sesión tiene el permiso de esa operación (`entregas.crear`, `devoluciones.crear`, `traspasos.recibir`; Consultar no pide ninguno). Nunca se decide por el nombre del rol. Trasladar (enviar) no tiene recorrido: es del supervisor con `traspasos.operar`.
- **Escaneo simulado (TU-06).** En práctica la cámara no se enciende; un botón del globo («Escanear un ejemplo») entrega el código ficticio del paso. El campo de texto sigue funcionando con los códigos de ejemplo.
- **Sin rastro (TU-07).** La práctica no escribe borradores (`imhotep.borrador.*`), no afecta los contadores del menú ni «Mis movimientos de hoy», y al salir deja la pantalla como estaba.
- **Progreso en el dispositivo (TU-08).** Qué recorridos terminó la persona se recuerda en el navegador (`localStorage`, con `try/catch`, por persona, como `menu-estado.ts`). Si falla o está vacío, todo aparece sin terminar. Nada se guarda en el servidor.
- **Accesibilidad y movimiento (TU-09).** El globo se lee con `aria-live`, el foco se queda dentro de la capa y `Escape` sale. El resalte sigue el elemento al girar, redimensionar o hacer scroll. Con «reducir movimiento» no hay transición. El resalte no usa los colores del semáforo.
- **Textos en español llano (TU-10),** una o dos frases por paso, sin términos técnicos.

## Fuera de alcance

- **Un tipo de operación «Demo» en el servidor** y anular vales de práctica: descartados por costo y por riesgo para el inventario real (afectarían modelo, contratos, reglas, folios, reportes y auditoría). Solo se reconsidera si se quiere que el supervisor vea las prácticas de su gente.
- Guardar el avance, las prácticas o su resultado en el servidor; reportes de capacitación.
- Recorridos de Trasladar (enviar), Autorización, reportes, RH, Compras y administración.
- Pantalla de bienvenida, ilustraciones, video y sonidos (siguen fuera de alcance en [ui-ux.md](../product/ui-ux.md)).
- Varios idiomas.
- Una librería de tours: se construye con lo ya instalado (`@base-ui/react`, `motion`).
- Modo práctica para la cámara real.

## Criterios de aceptación

- Dado un usuario con sesión, cuando enciende «Tutorial» en computadora, vista móvil o PWA, entonces ve la banda «Práctica: nada de esto se guarda» y la lista de recorridos que su sesión permite (TU-01, TU-05).
- Dado un recorrido en marcha, entonces el resto de la pantalla no responde al toque ni al teclado, y solo el elemento resaltado actúa (TU-03).
- Dada una entrega de práctica completa hasta «Confirmar entrega», entonces se muestra un folio de práctica y no se hace ninguna petición que cree un vale; el inventario, los folios, la auditoría y «Mis movimientos de hoy» no cambian (TU-02, TU-07).
- Dado el tutorial encendido, entonces la cámara no se activa y no se crea ningún borrador en el dispositivo (TU-06, TU-07).
- Dado un almacenista inicial, entonces no ve el recorrido de Recibir hasta que tenga `traspasos.recibir`, y no hay recorrido de Trasladar para nadie (TU-05).
- Dado un cambio de permisos de la sesión, entonces la lista de recorridos se ajusta sin leer el nombre del rol (TU-05).
- Dado un giro de pantalla o un cambio de tamaño a mitad de un paso, entonces el círculo y la flecha siguen al elemento (TU-09).
- Dado «reducir movimiento» activo, entonces el resalte aparece sin transición (TU-09).
- Dado `Escape` o «Salir», entonces la práctica termina, la capa desaparece y la pantalla vuelve a operar con datos reales (TU-03).
- Dado un recorrido terminado, entonces queda marcado como hecho en ese dispositivo y puede repetirse (TU-08).

## Módulos relacionados conocidos

Ninguno del backend. En el frontend:

- `frontend/app/componentes/tutorial/` (nuevo): proveedor, capa de bloqueo, resalte con círculo y flecha, globo y guiones de los cuatro recorridos.
- `frontend/app/componentes/dominio/escaner.tsx`: la propiedad opcional `ancla` (valor de `data-tutorial` del escáner) y el evento `tutorial:escanear` (`detail: { ancla, codigo }`), con el que «Escanear un ejemplo» entrega un código de ejemplo a un escáner con esa ancla, como si se hubiera leído. En práctica la cámara no se enciende.
- `frontend/app/api/`: capa de práctica que sustituye las respuestas mientras el tutorial esté encendido.
- `frontend/app/routes/_app.tsx` (monta el proveedor y la capa), `componentes/navegacion/armazon-escritorio.tsx`, `armazon-movil.tsx` y `menu-hoja.tsx` (interruptor).
- Atributos `data-tutorial` en `escaner`, `renglon-semaforo`, `ficha-trabajador`, `firma-pad`, `AccionPrincipal` (`componentes/pantalla.tsx`) y en las pantallas de entregar, devolver, consultar y recibir.
- `frontend/app/sesion/` (`puede` y `puedeAlguno`) para filtrar los recorridos.

## Cambios de datos o API esperados

Ninguno. No hay tablas, endpoints ni permisos nuevos. Si algún día se guarda el avance en el servidor, esta sección y [data-model.md](../architecture/data-model.md) y [api-contracts.md](../architecture/api-contracts.md) se actualizan en ese mismo cambio.

## Restricciones y compatibilidad

- El resalte va por encima de todo lo demás (`Dialog`, `Sheet` y `Popover` usan `z-50`; la banda de sin conexión, `z-60`), en un portal propio. Si un paso abre una hoja, el elemento resaltado puede estar dentro de ella: se localiza por `data-tutorial`.
- Las transiciones respetan el límite de 150 ms y «reducir movimiento» de [ui-ux.md](../product/ui-ux.md).
- La capa de práctica es el único punto que toca el cliente de la API; las pantallas no saben si están en práctica.
- El service worker no cambia, pero si cambian los estáticos se sube su `VERSION`.
- Los textos nuevos van en español llano.

## Riesgos

- **Que la práctica llegue al servidor** por una ruta que la capa no intercepte. Es el riesgo principal; la prueba lo vigila (ver validaciones).
- **Anclas frágiles:** un cambio de pantalla puede quitar un `data-tutorial`. Los pasos con ancla ausente se omiten con un aviso en consola, y una prueba revisa que cada ancla de cada guion exista.
- **Datos ficticios que se desvían** de las respuestas reales del servidor. Se mitiga tipándolos con los mismos tipos del cliente de la API.
- **Un paso que dependa de un estado** (por ejemplo, un borrador restaurado) y no se pueda alcanzar.
- **Ampliación de alcance.** Por eso este brief y la nota en [mvp-scope.md](../product/mvp-scope.md).

## Validaciones requeridas

- `pnpm typecheck` y `pnpm build`.
- Prueba de que, con el tutorial encendido, ninguna petición de escritura sale al servidor en los cuatro recorridos.
- Prueba de que cada recorrido solo aparece con su permiso y de que cada `data-tutorial` de un guion existe en su pantalla.
- Recorrido manual de los cuatro en computadora, vista móvil (375 px) y PWA instalada, con teclado y con «reducir movimiento».
- Verificar que no se escribe `imhotep.borrador.*` en práctica.

## Documentos globales que podrían actualizarse

- [mvp-scope.md](../product/mvp-scope.md): una línea en «Incluido». Con aprobación.
- [app-flow.md](../product/app-flow.md): Flujo 23 y mención en la navegación global.
- [ui-ux.md](../product/ui-ux.md): patrón «Tutorial guiado» y la aclaración sobre pantallas de bienvenida.
- [guia-almacenista.md](../guia-almacenista.md): al construirse, una línea que mencione el tutorial.
- [README.md](../README.md): la fila de «Segunda ola».
