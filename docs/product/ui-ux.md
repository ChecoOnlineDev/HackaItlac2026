# Especificación UI/UX — MVP

Cómo se presenta y se comporta cada pantalla del [app flow](app-flow.md). Cubre solo el MVP.

## Principios visuales

1. **Escanear primero.** La acción principal de casi toda pantalla es leer un código. Escribir es el plan B.
2. **Una acción principal por pantalla.** Un solo botón grande, siempre en el mismo lugar.
3. **Se entiende sin leer mucho.** Cada resultado se comunica con color, icono y una frase corta. Nunca solo con color (SM-02).
4. **Pensado para el mostrador.** Texto grande, alto contraste y botones que se aciertan con guantes o con prisa.
5. **Lenguaje del almacén.** "Vale", "resguardo", "pendiente"; nunca términos técnicos ni códigos de error.
6. **Sin costos donde no toca.** Los precios aparecen solo para quien tiene el permiso de costos, y nunca en un vale (RG-12).

## Sistema de diseño

- **Tipografía.** Poppins en toda la aplicación (servida desde el propio sitio), sin `font-mono`: los códigos también van en Poppins, con `tabular-nums` si ayuda a alinear cifras. Escala única en celular, tableta y computadora:

| Uso | Tamaño | Peso |
|---|---|---|
| Título de página (`h1`) | 20 px (24 px desde 768 px) | Semibold |
| Título de sección (`h2`) | 16 px | Semibold |
| Cuerpo | 16 px | Regular |
| Subtítulo, ayudas y datos secundarios | 14 px, color apagado | Regular |
| Etiquetas de sección y encabezados de tabla | 12 px, mayúsculas | Semibold |
| Datos clave (nombre del trabajador, folio) | 16 px | Semibold |

Los títulos pueden ocupar dos líneas; nada se corta con "…", salvo el nombre en la credencial y en la etiqueta QR cuando no cabe en 3 renglones (la pantalla y la imagen PNG lo recortan igual, con "…"). Una frase de ayuda por pantalla como máximo.
- **Colores.** Azul IMHOTEP como primario (`#0054A6`), azul marino para encabezados (`#1B1F8A`), fondo blanco y grises neutros para el texto secundario. El logotipo está en `docs/recursos/logo_imhotep.jpg`.
- **Semáforo.** Colores reservados; no se usan para nada más:

| Nivel | Color | Icono | Texto |
|---|---|---|---|
| Verde | `#15803D` | Palomita | "Listo" |
| Amarillo | `#CA8A04` | Triángulo de aviso | "Aviso" |
| Naranja | `#EA580C` | Candado | "Requiere autorización" |
| Rojo | `#B91C1C` | Cruz | "No se puede entregar" |

- **Espaciado.** Múltiplos de 4 px; 16 px de margen lateral en celular.
- **Radios y sombras.** Tarjetas y tablas con `rounded-2xl` (18 px), botones y campos con `rounded-xl` (12 px), borde sutil (`#E2E5EA`) y sombra muy suave (`shadow-xs`) en las tarjetas; las hojas y los avisos que flotan llevan sombra propia. Los avisos de color (semáforo) usan borde de 1 px y fondo al 10 %.
- **Iconografía.** Un solo juego de iconos de trazo; se elige en la Fase 0.
- **Objetivos táctiles.** Botón normal de 40 px de alto (nunca menos), campos y listas de 44 px, botón principal de 48 px y a todo el ancho. Las filas que son un solo toque (una tarjeta, un renglón de lista) miden 48 px o más.

## Navegación

- **Celular.** El inicio del almacenista es una cuadrícula de botones grandes: Entregar, Devolver, Trasladar, Recibir y Consultar. Arriba, el nombre del almacén y el usuario. Dentro de un flujo solo hay "Atrás" (uno solo, en la barra de arriba; en los flujos de pasos regresa un paso en vez de salir) y la acción principal, fija en la parte baja.
- **Tableta.** Igual que el celular, con la lista de renglones y el detalle lado a lado en horizontal.
- **Computadora.** Menú lateral con las secciones que permite el rol; tablas con filtros arriba; formularios a un ancho máximo de 720 px.
- **Sección activa del menú.** Tanto el menú lateral como la hoja "Menú" del celular remarcan dónde estás: contorno azul (`ring` del color primario), fondo suave (`bg-accent`), texto en azul marino y semibold, y `aria-current="page"`. Cuenta la subruta (`/trabajadores/<id>` marca "Trabajadores", `/recibir/<id>` marca "Recibir"); si dos opciones coinciden gana la más específica; "Inicio" solo se marca en `/`. En computadora, el cursor encima da el mismo fondo más suave. Al abrir la hoja, la opción activa se desplaza hasta quedar a la vista. La lógica vive en `idActivo` (`sesion/menu.ts`).

## Patrones reutilizables

**Escáner.** Un solo componente con tres entradas que entregan lo mismo: un código.

- Cámara: se abre al tocar "Escanear" y queda abierta para leer varios códigos seguidos.
- Pistola: escribe el código como teclado; la pantalla lo recibe sin tocar ningún campo.
- Teclado: un campo "Escribir código o buscar".
- Cada lectura da respuesta inmediata: sonido, vibración donde exista y el renglón nuevo resaltado un instante. Una lectura repetida en menos de un segundo y medio se ignora.

**Renglón con semáforo.** Franja de color a la izquierda, icono, nombre con marca, código o serie, cantidad con botones + y -, y debajo los motivos en frases cortas. Al tocar el número de la cantidad se abre un teclado numérico para teclearla. Todo renglón tiene un botón "Quitar" a la mano, sin importar su nivel; uno naranja muestra además "Pedir autorización". Al agregar un renglón aparece un aviso "Se agregó <artículo>. Deshacer" durante 5 segundos; tocarlo quita el renglón. Escanear solo agrega al borrador: nada se descuenta hasta confirmar el vale (E-28).

**Ficha breve del trabajador.** Tarjeta compacta: foto, nombre (puede ocupar dos líneas), número, puesto y área, una píldora con la vigencia y su fecha, y cuántos artículos tiene en resguardo; la lista de lo que tiene queda plegada en "Ver lo que tiene en resguardo". Sin foto, una píldora "Sin foto registrada" que no bloquea. Si no es vigente, la tarjeta lleva borde rojo y una banda con el motivo.

**Pie fijo de acciones.** `AccionPrincipal` (`frontend/app/componentes/pantalla.tsx`) fija en la parte baja, con el área segura del teléfono (`env(safe-area-inset-bottom)`), la acción principal de un flujo y, debajo, las secundarias que no deben quedar fuera de alcance ("No es esta persona"). Mide unos 130 px como máximo, así que cabe completo en 375 x 667. En computadora va al final del contenido.

**Tabla.** Contenedor redondeado con borde (`components/ui/table.tsx`), encabezado en fondo suave con texto de 12 px en mayúsculas, filas con separador fino y resalte al pasar el cursor, números a la derecha con `tabular-nums`, y desplazamiento horizontal dentro del contenedor. La primera celda de una fila (`scope="row"`) se ve como dato, no como encabezado. En celular y tableta (menos de 1024 px, o 768 px en Trabajadores) la misma lista se presenta como tarjetas.

**Hoja de filtros.** `HojaFiltros` (`frontend/app/componentes/ui/hoja-filtros.tsx`): un botón "Filtros" con el contador de filtros activos que abre una hoja (por la derecha en computadora, desde abajo en celular). Los campos trabajan sobre un borrador y no se aplican hasta tocar "Aplicar"; "Limpiar" quita todos. La búsqueda por texto no va dentro: queda visible junto al botón, en `CampoBusqueda`, y todas las búsquedas usan `useRetraso` (300 ms). Lo usan Inventario, Artículos y los cuatro reportes.

**Formulario guiado de una solicitud.** `frontend/app/componentes/compras/solicitar/` (lo usa Pedir una compra urgente). Un bloque por pregunta, en una sola columna de 720 px como máximo y pensado para 375 x 812: cada bloque tiene su título de 16 px (`h2` en azul marino) y, si hace falta, una línea de apoyo de 14 px. Las opciones son botones de alternancia (`aria-pressed`) y no controles nativos: **respuestas rápidas** en chips redondos de 40 px (`ChipsMotivo`) que rellenan un campo de texto que se puede editar, y **opciones grandes** de al menos 80 px de alto con icono, título y una frase (`OpcionesUrgencia`), una elegida por omisión. La cantidad lleva menos, más y el número en grande de 48 px, que abre el teclado numérico. Debajo, un **resumen** (`ResumenSolicitud`) con lo que se enviará y "Falta este dato" donde aún no hay respuesta, y en el pie fijo (`AccionPrincipal`) una sola acción principal, deshabilitada hasta tener lo obligatorio, con una nota que dice qué falta. Lo escrito se guarda en un borrador del dispositivo con el `id_cliente`; se borra al enviar o al cerrar la sesión. El resultado reemplaza al formulario: folio en grande, estado, resumen y dos botones ("Ver mis solicitudes" como principal, "Pedir otra" de contorno).

**Estado de una solicitud.** `InsigniaEstadoCompra` y `InsigniaUrgencia` (`componentes/compras/solicitar/insignias.tsx`): insignia redonda con icono y texto, nunca solo color. No usa el semáforo, que sigue reservado al nivel de un renglón o una pieza: Pendiente (azul suave, reloj), En compra (celeste, carrito), Comprada (violeta, recibo), Ingresada al almacén (verde azulado, paquete), Rechazada (rojo de error, círculo tachado) y Cancelada (gris, equis). Urgente va en azul marino con un rayo; Normal, en gris.

**Observación.** Hoja que sube desde abajo, con el motivo que la pide, un campo de texto y respuestas rápidas cuando aplica.

**Observación obligatoria de la entrega (E-09).** `ObservacionEntrega` (`frontend/app/componentes/entrega/observacion-entrega.tsx`): una tarjeta amarilla `rounded-2xl` con el título "¿Por qué se entrega esto?", el motivo que dio el servidor, un campo de texto corto con contador ("12 de 200") y cinco respuestas rápidas en chips redondos de 40 px ("Se mojaron", "Se llenaron de grasa", "Se perdieron", "Desgaste por uso", "Otro motivo") que rellenan el campo y se pueden editar. Aparece en el paso de la firma cuando la evaluación trae `pide_observacion`; "Confirmar entrega" queda deshabilitada mientras el campo esté vacío y, si el servidor responde 422 con la regla E-09, el error se muestra junto al campo. La observación va en el vale (`observacion`), se guarda en el borrador local y se borra con él. El amarillo nunca impide "Continuar".

**Hoja de dotación sugerida (FEAT-003).** `HojaDotacion` (`frontend/app/componentes/entrega/hoja-dotacion.tsx`), sobre `Hoja`. Lista los artículos de la dotación del trabajador con nombre, código y "Falta 2 de 2" o "Completo". En el paso de artículos (modo selección) cada artículo con faltante trae una casilla de al menos 56 px de alto, sin marcar por omisión; "Marcar lo que falta" y "Quitar marcas" ayudan a elegir, y "Agregar a la entrega" agrega lo marcado como renglones normales con la cantidad que falta, por el mismo camino que escanear (el servidor evalúa y el semáforo manda). Los completos salen atenuados y sin casilla; lo que ya está en la entrega dice "Ya está en la lista"; un artículo que se entrega por pieza dice "Escanea la pieza" y no trae casilla. En el paso del trabajador la misma hoja se abre en modo consulta, sin casillas, desde "Ver dotación" en la ficha, que trae la línea "Dotación: faltan 4 de 11". Es una sugerencia: nunca se carga sola ni genera avisos si no hay dotación.

**Condición de lo devuelto.** `ControlCondicion` (`frontend/app/componentes/devolucion/`): tres botones de 48 px, Bueno, Desgaste por uso y Dañado, con icono y texto; el elegido lleva palomita y relleno azul (no usa los colores del semáforo). Va debajo de cada renglón de una devolución y en la hoja de cantidad. Al elegir Dañado se abre la hoja de observación obligatoria (V-05) y el renglón admite una foto del daño, que el navegador reduce a unos 1024 px antes de mandarla. Una devolución nunca se pinta en rojo por la vigencia del trabajador (SM-05): su resguardo es una lista neutra con "Devolver" en cada artículo.

**Confirmación.** Solo para lo que no se puede deshacer: confirmar un vale, inactivar un artículo, emitir el no adeudo. Dice qué va a pasar en una frase. En la captura solo aparece cuando el servidor marca una cantidad inusual en un renglón (E-27), por ejemplo "¿Entregar 10 pares de guantes?", con "Sí, confirmar" y "Corregir"; en las demás lecturas no hay ventana.

**Impresión.** Lo que se imprime (el vale y la hoja de etiquetas) se marca con la clase `zona-impresion`, que pone `EstiloImpresion` (`frontend/app/componentes/dominio/`). Al imprimir solo sale esa zona, en hoja carta, sin menús, botones ni avisos. El QR se dibuja en el navegador, siempre negro sobre blanco y con margen, y contiene exactamente el código registrado. Ningún vale muestra costos.

**Renglón de recepción.** En Recibir, cada renglón del traspaso es una fila completa que funciona como casilla de recibido (48 px o más): nombre, código o serie, "Enviado, ya recibido, falta" y, en un artículo por cantidad, − y + con cuántas llegaron. Escanear el código marca el renglón; un código que no es del traspaso baja a "Códigos que no son de este traspaso" en rojo con el motivo del servidor. Lo no marcado se avisa como diferencia antes de confirmar. Componente: `frontend/app/componentes/traspasos/renglon-recepcion.tsx`.

**Pasos visibles.** Un asistente de varios pasos (Importar) muestra siempre sus pasos como una lista numerada: el actual resaltado, los hechos con palomita, cada uno con número o icono y su nombre. Componente: `frontend/app/componentes/importacion/pasos.tsx`.

**Tabla de vista previa de la importación.** `frontend/app/componentes/importacion/` (tabla sobre `~/components/ui/table`, ver «Tabla»). Arriba, un resumen en cuatro contadores que también filtran la lista al tocarlos: Nuevos, Existentes, Unidos y Errores. Cada fila lleva su número de fila del archivo, el estado en una insignia con icono y texto (nunca solo color: Nuevo, Existente (suma), Unido y Error, este último con el rojo de error de la solicitud y no con el del semáforo), el artículo con su código, la cantidad y el **saldo antes → después** en ese almacén. Una fila «Unida» dice «Unido: filas 2, 5, 9» debajo del nombre. En el alta, la **categoría sugerida** es un selector dentro de la fila, con el motivo en una línea de apoyo («La descripción dice «arnés»»); lo que viene del archivo no se edita, y lo que quedó «por revisar» muestra el selector vacío y la fila bloqueada hasta elegir. Los avisos (nombre distinto, servicio excluido, archivo ya importado) van en un recuadro amarillo arriba o debajo de la fila, sin impedir «Confirmar»; los errores traen su motivo en español llano y «Descargar filas con error». En celular la misma lista se presenta como tarjetas. La acción «Confirmar» está en el pie fijo y dice cuántas filas entran, por ejemplo «Confirmar: entran 40, 3 con error se quedan fuera».

**Línea de tiempo de una solicitud (SC-08).** `LineaDeTiempoSolicitud` (`frontend/app/componentes/compras/atender/linea-de-tiempo.tsx`): una lista ordenada del evento más antiguo al más reciente. Cada evento lleva un círculo de 40 px con el icono de su estado, una línea que lo une con el siguiente, la fecha y hora de México, una frase que dice qué pasó ("Compras la tomó"), "Por <nombre>" y, si la hay, la nota en un recuadro suave. El último evento lleva el círculo con borde azul. Es distinta de la línea de tiempo de una pieza (que va del más reciente al más antiguo) porque cuenta una historia que avanza hacia un final.

**Acciones por estado de una solicitud.** Los botones salen de `acciones` de la respuesta del servidor, nunca del rol ni del estado que deduzca la pantalla (`BotonesAccion`, `frontend/app/componentes/compras/atender/botones-accion.tsx`). La acción que hace avanzar la solicitud (Tomar, Marcar como comprada o Ingresar al almacén) es la principal, azul y a la derecha; las demás (Rechazar, Cancelar solicitud) son secundarias, con contorno y texto rojo. Nunca hay dos principales. Cada una abre lo mínimo que necesita: Tomar, una confirmación de una frase; Rechazar, una hoja con la nota obligatoria y respuestas rápidas; Marcar como comprada y Cancelar, una hoja con una nota opcional; Ingresar, una hoja con el vale de entrada opcional (lista de las últimas entradas o el folio escrito) y una nota. El error del servidor se escribe dentro de esa misma ventana, junto a lo que falló. En el detalle el pie es fijo en celular y tableta; en el renglón de la cola solo va la acción principal, con etiqueta corta (Tomar, Comprada, Ingresar).

**Insignias de urgencia y de estado.** `InsigniaUrgencia` e `InsigniaEstadoSolicitud` (`frontend/app/componentes/compras/atender/insignias.tsx`). URGENTE lleva un rayo y el rojo de error (`destructive`, no el rojo del semáforo, que es solo para renglones y piezas); NORMAL, gris. El estado nunca usa el semáforo: Pendiente y las que se cierran sin comprar (Rechazada, Cancelada) van en gris, y En compra, Comprada e Ingresada en azul suave, siempre con su icono y su texto. Una solicitud pendiente y urgente se distingue además por la franja roja a la izquierda del renglón o de la tarjeta y un fondo rojo muy suave.

**Estado de una lista.** Carga con esqueleto; vacío con mensaje y acción sugerida; error con "Reintentar".

**Indicador de carga.** El logotipo de IMHOTEP con tres puntos que brincan en cascada. Hay tres variantes: de pantalla completa (al abrir la aplicación o una ruta), solo los puntos dentro de un botón que espera respuesta, y en línea para una sección. Con "reducir movimiento" activo, los puntos parpadean en lugar de brincar.

**Navegación por ancho.** Computadora desde 1024 px: menú lateral. Celular y tableta (menos de 1024 px): sin menú lateral; el inicio es la cuadrícula de botones y un botón "Menú" abre una hoja con todas las secciones permitidas. El menú y los botones del inicio salen de los permisos de la sesión, nunca del nombre del rol.

## Pantallas

### Entrar

- **Objetivo:** iniciar sesión.
- **Jerarquía:** logotipo, usuario, contraseña, botón "Entrar".
- **Estados:** botón deshabilitado mientras responde; error bajo el botón; bloqueo temporal con el tiempo restante.
- **Accesibilidad:** el teclado del celular no tapa el botón; se entra con Enter.

### Inicio del almacenista

- **Objetivo:** llegar a cualquier operación con un toque.
- **Jerarquía:** almacén actual; cinco botones grandes con icono y texto; "Recibir" muestra cuántos traspasos esperan.
- **Estados:** sin traspasos, "Recibir" aparece sin contador.

### Entregar

- **Objetivo:** emitir un vale de entrega en el menor número de toques.
- **Paso 1, trabajador.** Título "Escanea la credencial del trabajador" y una línea de apoyo; luego el escáner y, debajo, "Escribir número o nombre". Al identificarlo, la pantalla cambia a "Confirma que es la persona correcta" con su ficha compacta (con la línea "Dotación: faltan 4 de 11" y "Ver dotación" si su puesto tiene dotación), y el pie fijo trae "Continuar" y "No es esta persona", siempre a la vista sin desplazarse. El mismo pie sirve de patrón para cualquier ficha de confirmación.
- **Paso 2, artículos.** Ficha del trabajador reducida arriba; lista de renglones con semáforo; botón "Escanear" siempre visible; "Dotación sugerida" debajo del escáner si el trabajador tiene dotación. Cada lectura se agrega al borrador; nada se descuenta hasta "Confirmar entrega". Acción primaria: "Continuar", deshabilitada mientras haya rojos o naranjas sin resolver, con el motivo escrito debajo.
- **Paso 3, firma.** Si la evaluación pide observación (E-09), arriba "¿Por qué se entrega esto?" con respuestas rápidas; luego resumen de artículos (con "Motivo de la entrega"), leyenda de responsabilidad y un recuadro para firmar con el dedo, con "Borrar". Acción primaria: "Confirmar entrega", deshabilitada hasta que haya observación cuando se pide.
- **Resultado.** Folio en grande, QR del vale y dos botones: "Nueva entrega" y "Imprimir".
- **Estados:** revalidación fallida regresa al paso 2 con el renglón marcado; sin conexión conserva el borrador y ofrece "Reintentar".
- **Responsive:** en horizontal, renglones a la izquierda y firma a la derecha.

### Autorización

- **Almacenista:** hoja con el motivo a escribir y dos caminos: "El supervisor está aquí" (pide su usuario y PIN) o "Enviar a su celular". En espera muestra un indicador y "Quitar renglón y continuar".
- **Supervisor (`/autorizaciones`):** tarjetas con trabajador, artículo, cuánto excede, motivo y quién lo pide. Dos botones: "Autorizar" y "Rechazar". La lista se actualiza sola.
- **Estados:** sin solicitudes, "No hay nada por autorizar"; solicitud vencida aparece atenuada.

### Devolver

- **Objetivo:** recibir equipo con un escaneo.
- **Jerarquía:** escáner; al leer una pieza, tarjeta con artículo, titular y tres botones de condición: Bueno, Desgaste por uso y Dañado. Los renglones recibidos se acumulan abajo.
- **Acción primaria:** "Confirmar devolución".
- **Estados:** equipo ajeno en rojo con "No es de la empresa"; pieza que no está en resguardo, en amarillo con su ubicación.

### Trasladar y Recibir

- **Trasladar:** selector de destino con las rutas habituales primero; después, la misma lista de renglones de la entrega. Resultado: folio y QR del traspaso.
- **Recibir:** lista de traspasos en tránsito hacia este almacén; al abrir uno, sus renglones con casilla de recibido, "Recibir todo" y "Confirmar recepción". Lo no marcado se indica como diferencia antes de confirmar.

### Consultar

- **Objetivo:** responder "quién lo tiene" y "qué tiene" en una pantalla.
- **Jerarquía:** escáner y campo de búsqueda; el resultado reemplaza al escáner.
- **Ficha de pieza:** estado e inspección arriba, ubicación actual, y el historial como línea de tiempo: movimientos, inspecciones y cambios de estado.
- **Ficha de artículo:** existencias por almacén y lista de trabajadores que lo tienen.
- **Atajos:** desde cada ficha, la acción siguiente (entregarle, devolver, inspeccionar). En la ficha de una pieza, quien tiene el permiso ve "Ajustar vigencia": una hoja con la fecha nueva y el motivo, que confirma en una frase qué va a cambiar (P-07). También hay un acceso a "Mis movimientos de hoy".

### Seguimiento de piezas (administrador y supervisor)

- **Objetivo:** saber dónde está cada pieza y quién la tiene, no solo cuántas hay (C-13). Ejemplo: buscar "minipulidor" y ver todas sus piezas, cada una con su lugar.
- **Jerarquía:** título y una línea de apoyo; buscador grande (`CampoBusqueda`, con `useRetraso` de 300 ms) junto a "Filtros" (`HojaFiltros`: almacén solo con `almacenes.todos`, estado y lugar) y "Descargar CSV"; cinco tarjetas de resumen (Total, En almacén, En resguardo, En tránsito, No aptas) que son botones y filtran la lista al tocarlas (otra vez, la quitan); chips de los filtros activos; la lista.
- **Lista:** en tableta y computadora (768 px o más) una tabla (`~/components/ui/table`) con Pieza y serie, Artículo, Estado, Dónde está o quién la tiene, Desde y Vale; en celular, una tarjeta por pieza. Toda la fila abre la ficha de la pieza; el folio del vale es un enlace aparte. "Dónde está" es una insignia con icono y el texto del servidor ("En resguardo de Juan Pérez", "En Kepler", "En tránsito a Contratistas"); "Estado" usa el semáforo solo para el estado de la pieza (Apta en verde, no apta o en mantenimiento en rojo, apta con la inspección vencida en amarillo). Los conteos de las tarjetas no cambian al elegir un estado o un lugar, para poder pasar de uno a otro.
- **Estados:** esqueleto al cargar; vacío "No hay piezas con ese filtro" con "Quitar filtros"; error con "Reintentar"; paginación de 20. Sin `reportes.existencias`: "Tu rol no puede hacer esto".
- **Acceso:** menú Supervisión y botón del inicio; desde la ficha de un artículo por pieza, "Ver todas sus piezas" abre la pantalla ya filtrada (`/seguimiento?articulo=<id>`).

### Trabajadores (RH)

- **Lista:** búsqueda por nombre o número; columnas: nombre, puesto, vigencia y situación (Sin pendientes, Con pendientes, No adeudo emitido).
- **Alta:** el puesto se elige de una lista de puestos activos (si no hay, un aviso con el enlace a Puestos o la indicación de pedirlo a Compras o al supervisor); formulario corto en un solo paso; el número de empleado se valida al salir del campo y ofrece el reingreso si ya existe. Incluye la foto, opcional: se toma con la cámara o se sube una imagen.
- **Ficha:** datos, periodos anteriores, pendientes y acciones: Reingresar, Iniciar baja, Cancelar baja. Incluye "Dotación del puesto": por artículo, una barra sencilla con "entregado de recomendado" y una insignia "Falta N" o "Completo" (siempre con texto, no solo color).

### Inventario, entradas e importación (Compras)

- **Inventario:** tabla por almacén con artículo, categoría, existencia y disponible; búsqueda a la vista y filtros de almacén y categoría en la hoja "Filtros".
- **Entrada:** renglones como en la entrega; un artículo por pieza abre la captura de códigos de pieza.
- **Importar:** cuatro pasos visibles: elegir el modo (Alta o Reposición, con su plantilla), pegar o subir, relacionar columnas, vista previa. La vista previa usa el patrón «Tabla de vista previa de la importación»; las filas con error van en rojo con su motivo.

### Catálogo (Compras y supervisor)

- **Categorías:** lista con tipo y resumen de su plantilla; formulario con interruptores para cada regla.
- **Artículos:** lista con búsqueda a la vista y filtros por categoría y estado (activos, inactivos) en la hoja "Filtros". Los inactivos aparecen atenuados con su motivo.
- **Detalle de artículo:** datos generales; sección "Reglas de entrega" con límite y requisitos especiales, cada uno con su interruptor y su motivo; sección "Estado" con Inactivar o Reactivar. Control y retorno aparecen bloqueados con una nota si ya hay movimientos.
- **Estados:** al guardar, aviso breve "Cambio guardado. Aplica desde la siguiente entrega."
- **Puestos (`/puestos`):** misma estructura que Artículos: búsqueda a la vista y filtro de estado en "Filtros"; tabla en tableta y computadora, tarjetas en celular, con nombre, cuántos artículos tiene su dotación ("Sin dotación" si ninguno) e insignia Activo o Inactivo. Acciones pequeñas: Dotación, Renombrar, Inactivar o Reactivar (con confirmación). Crear un puesto abre enseguida su dotación.
- **Editor de dotación:** una `Hoja` (inferior en celular, lateral en computadora). Cada renglón es una tarjeta con artículo (nombre y código), "Cantidad recomendada" y, de apoyo, el límite del artículo ("Límite: 3 cada 7 días"); "Quitar" en el renglón. Abajo, un buscador de artículos activos. El pie dice en una frase qué cambia ("Se agregan 2 artículos y se quita 1") antes de "Guardar dotación". Los errores del servidor (D-01, D-04) salen junto al renglón. Sin renglones se explica: "Sin dotación no se generan avisos al entregar".

### Solicitudes de compra (Compras)

- **Cola (`/compras`).** Título "Solicitudes de compra"; tres tarjetas táctiles de resumen (Pendientes, con "n urgentes" en rojo; En compra; Compradas por ingresar) en una fila de tres incluso en celular, con el número arriba y el nombre debajo; tocar una filtra la lista. Debajo, la búsqueda de 48 px y el botón "Filtros" (estado, urgencia, almacén y periodo), los chips de lo aplicado y "n solicitudes". La lista es una tabla desde 768 px (folio, qué se pidió con su motivo, cantidad, almacén, urgencia y estado en una celda, solicitante desde 1280 px, fecha desde 1536 px, y la acción rápida) y tarjetas en celular, cada una con su acción principal al pie. Al volver a la pestaña la cola se actualiza sola.
- **Detalle (`/compras/:id`).** Una tarjeta con las dos insignias, el nombre de lo que se pidió, sus datos en dos columnas (una en celular), la nota de Compras y el vale ligado; otra con la línea de tiempo; y el pie de acciones. En computadora, un "Volver a la lista" arriba; en celular, el "Atrás" de la barra. Una solicitud que el usuario no puede ver dice "No encontramos esta solicitud. Puede que no sea de tu almacén o que ya no exista".

### Personal por almacén (supervisor y administrador)

- Título y una línea de apoyo; búsqueda por nombre o usuario a la vista y filtro "Almacén" (con "Sin almacén") en la hoja "Filtros".
- Computadora y tableta: tabla con nombre, usuario, rol y almacén actual en una insignia; celular: tarjetas redondeadas. Cada persona lleva un botón "Cambiar almacén".
- Ese botón abre una hoja con la persona, su almacén actual, una lista desplegable con los almacenes activos y "Sin almacén", y una frase de lo que cambiará. "Guardar" (única acción principal) y "Cancelar". Los rechazos del servidor se muestran junto a la lista. Al guardar, aviso breve y la lista se actualiza sin recargar.

### Usuarios y roles (administrador)

- **Usuarios (`/usuarios`):** mismo patrón que Personal: búsqueda siempre visible y filtros de rol, almacén y estado en la hoja "Filtros". En tableta y computadora, una tabla con la persona (nombre y usuario), rol, almacén, estado en una insignia y tres acciones de solo icono de 40 px (Editar, Restablecer contraseña, Inactivar o Reactivar) con su nombre accesible; en celular, tarjetas redondeadas con las mismas acciones con texto. "Nuevo usuario" arriba a la derecha abre una `Hoja`. Los errores del servidor se escriben junto al campo.
- **Roles (`/roles`):** cuadrícula de tarjetas con nombre, insignia "Protegido" o "Rol inicial", descripción, número de usuarios y de permisos, y los botones "Ver permisos" y "Duplicar".
- **Matriz de permisos (`/roles/:id`):** tarjetas por módulo ("Operación del almacén", "Trabajadores", "Catálogo"...), en una columna en celular y dos en pantallas anchas. Cada renglón: interruptor, descripción del permiso en lenguaje de persona y la clave técnica en pequeño y gris. Lo reservado (costos, CURP y NSS) lleva la insignia "Información reservada" y, activo, una frase de qué deja ver. Un renglón cambiado se resalta y dice "Se agrega" o "Se quita". Lo que no se puede cambiar queda deshabilitado con la razón debajo, con candado.
- **Barra de cambios:** con cambios, una barra fija al pie (acción principal) dice en una frase qué cambia y lista los permisos agregados y quitados antes de "Guardar cambios" (que pide confirmación) o "Descartar".

### Detalle de un vale

- **Jerarquía:** folio, tipo y fecha; trabajador o almacenes; renglones; firma y responsable; QR.
- **Acciones:** Imprimir, Cancelar vale y Cancelar y rehacer. Cancelar pide el motivo en una hoja y confirma, en una frase, qué se va a revertir. "Cancelar y rehacer" hace lo mismo y abre la captura con los mismos renglones, sin firma, para corregirlos (K-05).
- **Estados:** un vale cancelado muestra una banda "Cancelado" con el motivo y el folio de su cancelación.

### Mis movimientos de hoy

- **Objetivo:** que cada usuario vea lo que hizo en el día y corrija un error sin buscarlo (C-12).
- **Jerarquía:** lista de los vales del día, el más reciente primero, con folio, tipo, hora, trabajador o almacén y estado. Cada vale abre su detalle, con "Cancelar" y "Cancelar y rehacer".
- **Acceso:** desde Consultar; no ocupa un botón del inicio.
- **Estados:** sin vales hoy, "Todavía no has hecho movimientos hoy".

### Pedir una compra urgente y Compras urgentes

- **Objetivo:** que quien nota que falta una herramienta que el almacén no tiene avise a Compras en menos de un minuto, desde el celular y de pie.
- **Pedir una compra urgente (`/compras/nueva`).** Formulario guiado (ver el patrón) con, en orden: el almacén (solo con `almacenes.todos`; los demás leen "Se pide para tu almacén: Midrex (MID)"), "¿Qué hace falta?" (buscador del catálogo con `CampoBusqueda` y espera de 300 ms, y el botón "No está en el catálogo" que cambia a un campo de descripción libre, con "Mejor buscarlo en el catálogo" para volver; el artículo elegido queda en una tarjeta con "Cambiar"), "¿Cuántas se necesitan?", "¿Para qué trabajo?" con chips y el campo "Motivo", "¿Qué tan urgente es?" con Urgente y Normal, y "Tu solicitud" (resumen). Pie fijo con "Enviar solicitud". Los errores del servidor salen junto al campo en español llano.
- **Resultado.** "Solicitud enviada" con el folio en grande, la insignia de estado, el resumen y los botones "Ver mis solicitudes" y "Pedir otra".
- **Compras urgentes de mi almacén (`/compras/mias`)**, "Solicitudes de compra" para el Administrador. Título y apoyo, botón "Pedir compra urgente" arriba a la derecha, `CampoBusqueda` y "Filtros" (estado, urgencia, "Solo las que yo pedí" y, con `almacenes.todos`, almacén), chips de los filtros activos y la lista. En 768 px o más es una tabla (Folio con la urgencia debajo hasta 1024 px, Qué se pidió, Cantidad, Urgencia desde 1024 px, Estado, Quién y cuándo, y "Cancelar"); en celular, una tarjeta por solicitud. Toda la fila o tarjeta abre `/compras/:id`; el folio es un enlace. Si Compras dejó una nota, se lee junto al estado. "Cancelar" solo sale en las pendientes que el servidor marca como cancelables y abre una confirmación de una frase con "Agregar una nota" (opcional, escondida para no abrir el teclado) y los botones "Conservarla" y "Sí, cancelarla".
- **Estados:** esqueleto al cargar; vacío "Todavía no hay solicitudes" (con filtros, "No hay solicitudes con ese filtro" y "Quitar filtros"); error con "Reintentar"; paginación de 20. Sin `compras.solicitar`: "Tu rol no puede hacer esto".
- **Acceso:** Operación en el menú; no ocupa botón en el inicio.

### Reportes y etiquetas

- **Reportes:** botón "Filtros" (hoja lateral), tabla, total de registros y "Descargar CSV". El periodo se elige con un selector de rango de fechas, con atajos como Hoy, Ayer, Últimos 7 días y Este mes. El reporte de movimientos filtra además por almacén, tipo, trabajador, artículo y usuario; el filtro de usuario es informativo y no estorba la operación habitual. El reporte de consumo muestra el total por artículo y se abre para ver el desglose por trabajador.
- **Patrón de reporte (`MarcoReporte`):** los filtros viven en la dirección (se comparten y sobreviven a una recarga); en todos los tamaños van en la hoja "Filtros" (con contador y "Aplicar"/"Limpiar"), junto a "Descargar CSV". Cada filtro activo es un chip que se quita con un toque. Quien no tiene `almacenes.todos` no ve el filtro de almacén: una nota dice que solo ve el suyo. Tabla en computadora y tarjetas en celular; "Descargar CSV" usa los mismos filtros.
- **Seguimiento de piezas** usa los mismos bloques del patrón de reporte (filtros en la dirección, chips, `Paginador`, descarga con los mismos filtros), pero con su propio buscador y tarjetas de resumen; ver su sección arriba.
- **Etiquetas:** selección de elementos y vista previa de la hoja; cada etiqueta lleva QR y texto legible.
- **Credencial (`TarjetaCredencial`, `HojaCredenciales`, `VistaCredencial`):** tarjeta de 85.6 × 54 mm (CR80) en Poppins: banda azul marino con el logo de IMHOTEP, nombre completo y grande (baja de tamaño y usa hasta 3 renglones si es largo; si aun así no cabe, termina en "…" tanto en pantalla como en el PNG), puesto, número de empleado (único por trabajador), QR a la derecha con el código en texto legible. No lleva pie. Nunca lleva CURP, NSS ni otros datos reservados. En credenciales, la pantalla Etiquetas ofrece "Credencial completa" o "Solo el código QR". La hoja carta lleva 8 tarjetas (2 × 4) con guías de corte. Cada credencial se descarga como PNG (`credencial-<código>.png`, ≈ 600 ppp, dibujada en el navegador) o se imprime / guarda como PDF con el diálogo del navegador; `ImpresionAparte` deja la hoja fuera de la pantalla para poder imprimir desde una ventana lateral. Al terminar el alta y en la ficha del trabajador se ofrece "Credencial" solo si el usuario tiene `etiquetas.imprimir`.

## Accesibilidad

- Contraste mínimo de 4.5 a 1 en texto.
- Foco visible en computadora; todo se puede recorrer con teclado.
- Los niveles del semáforo llevan icono y texto además de color.
- Los errores de formulario se escriben junto al campo.

## Animaciones y respuesta

- Sin animaciones decorativas. Solo transiciones cortas, de 150 ms, al agregar un renglón o abrir una hoja.
- Sonido distinto para lectura correcta, aviso y bloqueo.
- La pantalla no se apaga mientras el escáner está abierto.

## Elementos fuera de alcance

- Tema oscuro y personalización de colores.
- Ilustraciones y pantallas de bienvenida.
- Gráficas; los reportes son tablas.
- Diseño del ticket impreso y del comprobante público ([FEAT-001](../features/FEAT-001-vale-como-prueba.md)).
