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

Los títulos pueden ocupar dos líneas; nada se corta con "…". Una frase de ayuda por pantalla como máximo.
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

**Observación.** Hoja que sube desde abajo, con el motivo que la pide, un campo de texto y respuestas rápidas cuando aplica.

**Condición de lo devuelto.** `ControlCondicion` (`frontend/app/componentes/devolucion/`): tres botones de 48 px, Bueno, Desgaste por uso y Dañado, con icono y texto; el elegido lleva palomita y relleno azul (no usa los colores del semáforo). Va debajo de cada renglón de una devolución y en la hoja de cantidad. Al elegir Dañado se abre la hoja de observación obligatoria (V-05) y el renglón admite una foto del daño, que el navegador reduce a unos 1024 px antes de mandarla. Una devolución nunca se pinta en rojo por la vigencia del trabajador (SM-05): su resguardo es una lista neutra con "Devolver" en cada artículo.

**Confirmación.** Solo para lo que no se puede deshacer: confirmar un vale, inactivar un artículo, emitir el no adeudo. Dice qué va a pasar en una frase. En la captura solo aparece cuando el servidor marca una cantidad inusual en un renglón (E-27), por ejemplo "¿Entregar 10 pares de guantes?", con "Sí, confirmar" y "Corregir"; en las demás lecturas no hay ventana.

**Impresión.** Lo que se imprime (el vale y la hoja de etiquetas) se marca con la clase `zona-impresion`, que pone `EstiloImpresion` (`frontend/app/componentes/dominio/`). Al imprimir solo sale esa zona, en hoja carta, sin menús, botones ni avisos. El QR se dibuja en el navegador, siempre negro sobre blanco y con margen, y contiene exactamente el código registrado. Ningún vale muestra costos.

**Renglón de recepción.** En Recibir, cada renglón del traspaso es una fila completa que funciona como casilla de recibido (48 px o más): nombre, código o serie, "Enviado, ya recibido, falta" y, en un artículo por cantidad, − y + con cuántas llegaron. Escanear el código marca el renglón; un código que no es del traspaso baja a "Códigos que no son de este traspaso" en rojo con el motivo del servidor. Lo no marcado se avisa como diferencia antes de confirmar. Componente: `frontend/app/componentes/traspasos/renglon-recepcion.tsx`.

**Pasos visibles.** Un asistente de varios pasos (Importar) muestra siempre sus pasos como una lista numerada: el actual resaltado, los hechos con palomita, cada uno con número o icono y su nombre. Componente: `frontend/app/componentes/importacion/pasos.tsx`.

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
- **Paso 1, trabajador.** Título "Escanea la credencial del trabajador" y una línea de apoyo; luego el escáner y, debajo, "Escribir número o nombre". Al identificarlo, la pantalla cambia a "Confirma que es la persona correcta" con su ficha compacta, y el pie fijo trae "Continuar" y "No es esta persona", siempre a la vista sin desplazarse. El mismo pie sirve de patrón para cualquier ficha de confirmación.
- **Paso 2, artículos.** Ficha del trabajador reducida arriba; lista de renglones con semáforo; botón "Escanear" siempre visible. Cada lectura se agrega al borrador; nada se descuenta hasta "Confirmar entrega". Acción primaria: "Continuar", deshabilitada mientras haya rojos o naranjas sin resolver, con el motivo escrito debajo.
- **Paso 3, firma.** Resumen de artículos, leyenda de responsabilidad y un recuadro para firmar con el dedo, con "Borrar". Acción primaria: "Confirmar entrega".
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

### Trabajadores (RH)

- **Lista:** búsqueda por nombre o número; columnas: nombre, puesto, vigencia y situación (Sin pendientes, Con pendientes, No adeudo emitido).
- **Alta:** formulario corto en un solo paso; el número de empleado se valida al salir del campo y ofrece el reingreso si ya existe. Incluye la foto, opcional: se toma con la cámara o se sube una imagen.
- **Ficha:** datos, periodos anteriores, pendientes y acciones: Reingresar, Iniciar baja, Cancelar baja.

### Inventario, entradas e importación (Compras)

- **Inventario:** tabla por almacén con artículo, categoría, existencia y disponible; búsqueda a la vista y filtros de almacén y categoría en la hoja "Filtros".
- **Entrada:** renglones como en la entrega; un artículo por pieza abre la captura de códigos de pieza.
- **Importar:** tres pasos visibles: pegar o subir, relacionar columnas, vista previa. Las filas con error van en rojo con su motivo.

### Catálogo (Compras y supervisor)

- **Categorías:** lista con tipo y resumen de su plantilla; formulario con interruptores para cada regla.
- **Artículos:** lista con búsqueda a la vista y filtros por categoría y estado (activos, inactivos) en la hoja "Filtros". Los inactivos aparecen atenuados con su motivo.
- **Detalle de artículo:** datos generales; sección "Reglas de entrega" con límite y requisitos especiales, cada uno con su interruptor y su motivo; sección "Estado" con Inactivar o Reactivar. Control y retorno aparecen bloqueados con una nota si ya hay movimientos.
- **Estados:** al guardar, aviso breve "Cambio guardado. Aplica desde la siguiente entrega."

### Detalle de un vale

- **Jerarquía:** folio, tipo y fecha; trabajador o almacenes; renglones; firma y responsable; QR.
- **Acciones:** Imprimir, Cancelar vale y Cancelar y rehacer. Cancelar pide el motivo en una hoja y confirma, en una frase, qué se va a revertir. "Cancelar y rehacer" hace lo mismo y abre la captura con los mismos renglones, sin firma, para corregirlos (K-05).
- **Estados:** un vale cancelado muestra una banda "Cancelado" con el motivo y el folio de su cancelación.

### Mis movimientos de hoy

- **Objetivo:** que cada usuario vea lo que hizo en el día y corrija un error sin buscarlo (C-12).
- **Jerarquía:** lista de los vales del día, el más reciente primero, con folio, tipo, hora, trabajador o almacén y estado. Cada vale abre su detalle, con "Cancelar" y "Cancelar y rehacer".
- **Acceso:** desde Consultar; no ocupa un botón del inicio.
- **Estados:** sin vales hoy, "Todavía no has hecho movimientos hoy".

### Reportes y etiquetas

- **Reportes:** botón "Filtros" (hoja lateral), tabla, total de registros y "Descargar CSV". El periodo se elige con un selector de rango de fechas, con atajos como Hoy, Ayer, Últimos 7 días y Este mes. El reporte de movimientos filtra además por almacén, tipo, trabajador, artículo y usuario; el filtro de usuario es informativo y no estorba la operación habitual. El reporte de consumo muestra el total por artículo y se abre para ver el desglose por trabajador.
- **Patrón de reporte (`MarcoReporte`):** los filtros viven en la dirección (se comparten y sobreviven a una recarga); en todos los tamaños van en la hoja "Filtros" (con contador y "Aplicar"/"Limpiar"), junto a "Descargar CSV". Cada filtro activo es un chip que se quita con un toque. Quien no tiene `almacenes.todos` no ve el filtro de almacén: una nota dice que solo ve el suyo. Tabla en computadora y tarjetas en celular; "Descargar CSV" usa los mismos filtros.
- **Etiquetas:** selección de elementos y vista previa de la hoja; cada etiqueta lleva QR y texto legible.
- **Credencial (`TarjetaCredencial`, `HojaCredenciales`, `VistaCredencial`):** tarjeta de 85.6 × 54 mm (CR80) en Poppins: banda azul marino con el logo de IMHOTEP, nombre completo y grande (nunca se corta: baja de tamaño y usa hasta 3 renglones si es largo), puesto, número de empleado (único por trabajador), QR a la derecha con el código en texto legible. No lleva pie. Nunca lleva CURP, NSS ni otros datos reservados. En credenciales, la pantalla Etiquetas ofrece "Credencial completa" o "Solo el código QR". La hoja carta lleva 8 tarjetas (2 × 4) con guías de corte. Cada credencial se descarga como PNG (`credencial-<código>.png`, ≈ 600 ppp, dibujada en el navegador) o se imprime / guarda como PDF con el diálogo del navegador; `ImpresionAparte` deja la hoja fuera de la pantalla para poder imprimir desde una ventana lateral. Al terminar el alta y en la ficha del trabajador se ofrece "Credencial" solo si el usuario tiene `etiquetas.imprimir`.

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
