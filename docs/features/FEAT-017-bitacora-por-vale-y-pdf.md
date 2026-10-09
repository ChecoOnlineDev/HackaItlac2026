# FEAT-017: Bitácora por vale, detalle del vale y PDF

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Es parte de la [iteración 01](../releases/iteration_01/README.md) (decisión D-16) y va en el paso 4 de su orden de construcción, junto con FEAT-018. Usa las reglas BT-01 a BT-10 (sección 4 del documento maestro). Cambia la pantalla de la bitácora (SG-05 se conserva como «Detalle por renglón»), el detalle del vale (C-04) y el resultado de la importación. Agrega la columna `vale.lote_id` y los endpoints `GET /api/bitacora` y `GET /api/vales/{id}/renglones`. Las decisiones que dependen del usuario están en «Decisiones abiertas».

## Problema u oportunidad

La bitácora de hoy (SG-05, `GET /api/reportes/movimientos`, pantalla `/reportes/movimientos`) muestra **un renglón por movimiento**. Sirve para rastrear una pieza, pero no para saber qué pasó en el almacén:

1. **Una importación de 800 filas llena la bitácora con 800 renglones.** Quien busca la entrega de ayer tiene que pasar varias páginas de la misma entrada de Kepler.
2. **Una importación grande se parte en varios vales de 500** (`importacion/service.py`, `RENGLONES_POR_VALE`), y nada los une: aparecen como vales sueltos con folios seguidos.
3. **El detalle del vale es de celular.** `/vales/:id` muestra todos los renglones de una vez en una columna angosta; con 500 renglones es lento y no se lee en computadora, que es donde se revisa (D-20).
4. **No hay PDF.** Solo existe «Imprimir» del navegador. Quien quiere archivar o mandar el vale de una importación o de una entrega no tiene un archivo.

El flujo que pidió el usuario: **importar un Excel → ver en la bitácora un solo renglón → abrir el vale con el resumen de todo lo importado → descargarlo en PDF.**

## Objetivo

Que la bitácora diga **qué operaciones** hubo (un renglón por vale, o por lote cuando una operación generó varios vales), que el detalle del vale se lea completo en computadora aunque tenga cientos de renglones, y que cualquier vale o lote se descargue como un archivo PDF sin costos.

## Historia de usuario

Como supervisor, quiero ver en la bitácora un renglón por cada vale de mi almacén, para saber en un vistazo qué entró, qué salió y qué va en camino, sin perderme en los renglones de una importación.

Como Compras, quiero que una importación de 1,240 renglones aparezca como una sola operación, abrirla y ver el resumen por categoría, para comprobar que entró lo que compré.

Como supervisor o Compras, quiero descargar un vale o un lote completo en PDF, para archivarlo o mandarlo sin depender de la impresora.

Como almacenista, quiero que el PDF de un vale sea el mismo documento que el vale impreso, para dárselo al trabajador como comprobante.

Todavía no hay historias en `docs/stories/`: se escriben al empezar la construcción.

## Alcance incluido

### Reglas

| ID | Regla | Origen |
|---|---|---|
| BT-01 | **Bitácora por vale.** `GET /api/bitacora` devuelve **un renglón por vale**, del más reciente al más antiguo: folio, tipo, fecha y hora, almacén, responsable, trabajador o destino, proyecto, número de renglones, unidades, estado y, si se filtró por almacén, la dirección respecto a ese almacén (BT-04). Paginada en el servidor (`pagina`, `tamano`). Se ve con `bitacora.ver` **o** `reportes.movimientos` (lo declara el router con `requiere_alguno`, como SG-05) y con el alcance de almacenes del usuario (AC-06, y el conjunto de almacenes de AC-36 cuando exista FEAT-013). Solo lee. Nunca trae costos, CURP ni NSS. | D-16 |
| BT-02 | **Lote.** Los vales que crea **una misma importación** (que se parte en vales de 500) o **un mismo traspaso por Excel** llevan el mismo `vale.lote_id`. La bitácora los agrupa en **un renglón de lote** («Importación del 8 oct: 3 vales, 1,240 renglones») que se despliega para ver cada vale. `lote_id` se escribe al insertar el vale y no cambia (invariante 5). Los vales anteriores a la columna, y los capturados a mano, no tienen lote y salen como renglón de vale. | D-16 |
| BT-03 | **Filtros.** Fechas (`desde`, `hasta`, del centro de México, ambos inclusivos), almacén (solo dentro del alcance), tipo, usuario (quien hizo el vale, C-11), trabajador, proyecto, artículo, y pieza o serie (texto). Si se filtra por artículo, pieza o serie, cada renglón trae `coincidencias`: cuántos de sus renglones coinciden («3 de 500 renglones coinciden»). «Solo los míos» (`solo_mios=true`) se conserva. Un filtro fuera del alcance no devuelve nada y no es error. | D-16; SG-05; C-11 |
| BT-04 | **Dirección y marcas.** Con un almacén filtrado, cada vale dice si fue `ENTRADA`, `SALIDA` o `EN_CAMINO` respecto a ese almacén (como SG-05, pero por vale); sin almacén filtrado va `null`. Un vale cancelado sale marcado «Cancelado» con el folio de su cancelación. Un vale capturado sin conexión (FEAT-020) lleva la marca «Capturado sin conexión» con la hora de captura. El reporte por movimiento (SG-05) **se conserva** sin cambios como la pestaña «Detalle por renglón» y para su CSV. | D-16; SG-05; FEAT-020 |
| BT-05 | **Detalle del vale, primero computadora.** `/vales/:id` ocupa todo el ancho desde 1280 px y sigue usable en celular. Muestra: encabezado (folio, tipo, estado, fechas, almacén, responsable, trabajador, proyecto, quién validó, firma y QR); **resumen por categoría** (renglones y unidades); la tabla de renglones (BT-06); y los vales relacionados (BT-06). El resumen en **pesos** se ve solo con `reportes.valor_inventario`, solo por categoría y en total, **nunca** el costo unitario ni el importe de un renglón, y **nunca** en el PDF (RG-12, F-12, D-05). | D-16; D-20; RG-12 |
| BT-06 | **Renglones y vales relacionados.** La tabla de renglones se pide aparte, paginada en el servidor: `GET /api/vales/{id}/renglones`, con búsqueda por código, artículo o serie. El detalle enlaza los vales relacionados: el traspaso de una recepción, las recepciones de un traspaso, la cancelación de un vale cancelado y el vale que cancela una cancelación, y las otras partes de su lote. Un relacionado fuera del alcance del usuario se nombra sin folio ni enlace («Recibido en otro almacén el 8 oct»), como AC-06. | D-16; AC-06 |
| BT-07 | **PDF del vale.** Botón «Descargar PDF» en el detalle: se descarga un **archivo** PDF (no solo «Imprimir»), llamado con el folio (`KEP-ING-000123.pdf`). Lleva lo mismo que el vale impreso (E-24): folio, tipo, estado, fecha y hora, almacén, responsable, trabajador con número, puesto y área, proyecto, resumen por categoría en renglones y unidades, la tabla completa de renglones (código, artículo con marca, pieza o serie, cantidad y condición), quién validó, la firma o «Firmado con la sesión de <responsable>», y el QR del vale. **Sin costos** (RG-12, F-12), sin CURP, NSS ni foto (RG-13, T-09). | D-16; E-24; F-12 |
| BT-08 | **PDF del lote.** Desde el renglón del lote en la bitácora, y desde el detalle de cualquiera de sus vales, «Descargar PDF del lote» genera **un solo PDF**: una primera hoja con el resumen del lote (fecha, almacén, responsable, cada vale con su folio, estado y QR, y totales por categoría) y después todos los renglones, vale por vale. Nombre: `lote-<primer folio>-<último consecutivo>.pdf` (por ejemplo `lote-KEP-ING-000123-000125.pdf`). | D-16 |
| BT-09 | **Generado en el navegador.** El PDF lo arma el navegador con los datos que ya devuelve la API, sin endpoint nuevo, para que también funcione en la app de Android sin conexión (FEAT-020) y comparta la librería con el PDF de etiquetas (FEAT-019, D-19). Propuesta: `jspdf` con `jspdf-autotable` (dependencia nueva, **pide aprobación**). Un vale de 500 renglones se genera en **menos de 5 segundos** en un celular de gama media; con más renglones (un lote) los pide de 500 en 500 y avanza con un indicador «Armando el PDF: 500 de 1,240 renglones» que se puede cancelar. | D-16; D-15; D-19 |
| BT-10 | **Resultado de la importación y del traspaso por Excel.** Al confirmar una importación, el resultado ofrece «Ver en la bitácora» (abre la bitácora filtrada por ese lote y con el lote desplegado) y «Descargar PDF» (el PDF del lote, o el del vale si solo hubo uno). Al confirmar un traspaso por Excel, el resultado ofrece «Ver el vale» y «Descargar PDF», que sirve de lista impresa para verificar al recibir. | D-16 |

### A. Bitácora por vale (BT-01 a BT-04)

**Pantalla.** `/bitacora`, primero computadora (D-20), con dos pestañas sobre el patrón «Pestañas por sección»:

- **Por vale** (por omisión): la tabla nueva de BT-01.
- **Detalle por renglón** (`/bitacora?vista=renglones`): la pantalla actual de `rep-movimientos.tsx`, sin cambios de contrato (SG-05). `/reportes/movimientos` redirige a esta pestaña con sus filtros.

En el menú, la pestaña «Movimientos» de Inventario se llama «Bitácora» y abre `/bitacora`.

**Acción por acción:**

1. **Abrir la bitácora.** El supervisor ve su almacén sin elegir nada (en el caso especial de varios almacenes, AC-36, ve su conjunto completo, como en los demás reportes, sección 8 del maestro). El periodo por omisión son los últimos 7 días. La tabla trae 25 renglones por página, el más reciente arriba.
2. **Leer un renglón.** Columnas: Fecha y hora · Folio (enlace al detalle) · Tipo · Entrada o salida (icono y texto, nunca solo color) · Trabajador o destino · Proyecto · Renglones · Unidades · Responsable · Estado. Qué dice «Trabajador o destino» según el tipo:

   | Tipo | Columna |
   |---|---|
   | ENTRADA | «Proveedor» |
   | ENTREGA, NO_ADEUDO | Nombre y número del trabajador (enlace a su ficha con `trabajadores.ver`) |
   | DEVOLUCION | El trabajador; si trae piezas de varios titulares, «Varios trabajadores (3)» |
   | TRASPASO | «A Contratistas» (el destino) |
   | RECEPCION | «De Kepler» (el origen del traspaso) |
   | CANCELACION | «Cancela KEP-ENT-000045» (enlace si está en el alcance) |

   Proyecto solo tiene valor en una ENTREGA (`vale.proyecto_id`, FEAT-013); una entrega sin proyecto dice «Sin proyecto» (PR-10); los demás tipos, «—».
3. **Dirección (BT-04).** Se calcula por vale, con los movimientos del vale contra las ubicaciones del almacén filtrado: si llegan a él, `ENTRADA`; si salen de él, `SALIDA`; si es un traspaso hacia él que aún no se recibe completo, `EN_CAMINO`. Así: ENTRADA, DEVOLUCION y RECEPCION son entradas; ENTREGA (retornable o consumible) y TRASPASO son salidas para el origen; un TRASPASO es `EN_CAMINO` para el destino mientras su estado sea `EN_TRANSITO` o `RECIBIDO_CON_DIFERENCIAS`, y ya recibido completo se sigue listando para el destino con su estado «Recibido» (lo que entró son las recepciones). Una CANCELACION toma la dirección de sus movimientos (cancelar una entrega es entrada; cancelar una entrada es salida). Un NO_ADEUDO no tiene movimientos: va con `direccion: null` y el texto «Sin movimiento de inventario».
4. **Renglón de lote (BT-02).** Si varios vales del alcance comparten `lote_id`, la tabla muestra un renglón de lote en su lugar: «Importación del 8 oct · 3 vales · 1,240 renglones · 3,580 unidades», con el responsable, el almacén y una insignia del estado del lote («Emitido», «1 de 3 cancelado», «Cancelado»). Un botón «Ver los 3 vales» lo despliega dentro de la tabla con un renglón por vale (folio, renglones, unidades, estado). Un lote de **un solo vale** (lo normal en un traspaso por Excel, que no se parte, TR-07) se muestra como renglón de vale con la insignia «Desde Excel».
5. **Filtrar (BT-03).** Búsqueda de pieza o serie a la vista (espera de 300 ms, D-18) y el resto en la hoja «Filtros» (patrón `HojaFiltros`): periodo, tipo, usuario, trabajador, proyecto, artículo y, solo con varios almacenes en el alcance, almacén. Con filtro de artículo, pieza o serie, cada renglón agrega «3 de 500 renglones coinciden» y al abrir el detalle la tabla de renglones llega ya filtrada (`?q=` en la dirección).
6. **Abrir un vale.** Toda la fila abre `/vales/:id`; el folio es un enlace aparte. Un renglón de lote, desplegado, abre cada vale.
7. **Descargar.** «Descargar CSV» baja la lista por vale con los mismos filtros (un renglón por vale, los lotes desplegados en sus vales). El CSV por movimiento sigue en la pestaña «Detalle por renglón».

**Forma de la respuesta** (`{elementos, total, sin_registros, mensaje}`, como los reportes). Cada elemento es un vale o un lote:

```json
{
  "clase": "LOTE",
  "lote_id": "0192…",
  "origen_lote": "IMPORTACION",
  "creado_en": "2026-10-08T15:20:00Z",
  "tipo": "ENTRADA", "tipo_texto": "Entrada",
  "almacen": {"id": "…", "clave": "KEP", "nombre": "Kepler"},
  "responsable": {"id": "…", "nombre": "Compras Kepler"},
  "renglones": 1240, "unidades": 3580,
  "estado_texto": "Emitido",
  "direccion": "ENTRADA", "direccion_texto": "Entrada",
  "coincidencias": null,
  "vales": [
    {"clase": "VALE", "id": "…", "folio": "KEP-ING-000123", "estado": "EMITIDO", "renglones": 500, "unidades": 1500, "parte": 1},
    {"clase": "VALE", "id": "…", "folio": "KEP-ING-000124", "estado": "CANCELADO", "renglones": 500, "unidades": 1400, "parte": 2,
     "cancelacion": {"id": "…", "folio": "KEP-CAN-000007"}},
    {"clase": "VALE", "id": "…", "folio": "KEP-ING-000125", "estado": "EMITIDO", "renglones": 240, "unidades": 680, "parte": 3}
  ]
}
```

Un elemento `VALE` suelto trae además `trabajador {id, numero_empleado, nombre}`, `destino {id, clave, nombre}`, `proyecto {id, nombre}` (o `null`), `vale_origen {id, folio}` (en recepciones y cancelaciones; `folio` nulo si está fuera del alcance), `cancelacion {id, folio}` (si está cancelado), `capturado_sin_conexion` y `capturado_en` (FEAT-020). `lote_id` sirve también de filtro (`GET /api/bitacora?lote_id=…`): devuelve el lote con sus vales y es lo que abre «Ver en la bitácora».

**Paginación.** El servidor pagina por **elemento** (un lote cuenta como uno). Una importación tiene como máximo 10 vales (5,000 filas entre 500), así que los vales de un lote viajan dentro de su elemento sin otra petición. Los conteos (`renglones`, `unidades`, `coincidencias`) se calculan con una consulta agregada sobre `movimiento` **solo para los vales de la página**, no para todo el periodo.

### B. Lote (BT-02)

- **Quién lo escribe.** Solo el módulo `movimientos` escribe vales. La importación y el traspaso por Excel le pasan el `lote_id` al confirmar como un **parámetro interno** del servicio (`MovimientoService.confirmar`), no como campo del cuerpo público: `POST /api/vales` sigue rechazando campos desconocidos (422), así que nadie puede inventar un lote desde la API.
- **Qué valor lleva.** El `id_lote` que ya manda el cliente para la idempotencia (I-12, TR-08). Es un UUID del dispositivo; ya es único por usuario (un `id_lote` de otra persona da 409). Con eso, «este lote ya se confirmó» se puede buscar por `lote_id` en lugar de recorrer los `id_cliente` parte por parte.
- **Qué no lleva lote.** Los vales capturados a mano, los de antes de la columna, y las **cancelaciones**: cancelar una parte de un lote crea un vale de CANCELACION propio, que sale en la bitácora como su propio renglón («Cancela KEP-ING-000124») y no se mete al lote. La recepción de un traspaso por Excel tampoco hereda el lote: es otra operación, en otro almacén.

### C. Detalle del vale (BT-05, BT-06)

**Acción por acción:**

1. **Abrir.** Desde la bitácora, desde «Mis movimientos de hoy», desde el QR o desde un enlace. Si el vale está fuera del alcance: «No encontramos este vale. Puede que no sea de tu almacén o que ya no exista» (404, AC-06).
2. **Encabezado.** En computadora (1280 px o más), dos columnas: a la izquierda folio en grande, insignias de tipo y estado, fechas (creado y, si aplica, capturado sin conexión), almacén, responsable, trabajador (nombre, número, puesto y área), proyecto, «Validó» (A-04) y, en un despacho de EPP, quién lo aprobó (FEAT-014); a la derecha, la firma y el QR. En celular, todo en una columna con la firma y el QR plegados en «Ver firma y QR».
3. **Banda de estado.** Un vale cancelado muestra la banda «Cancelado» con el motivo y el enlace a su cancelación (como hoy). Un traspaso muestra su avance: «Recibido 38 de 40 renglones; faltan 2».
4. **Parte de un lote.** Un vale con `lote_id` muestra la tarjeta «Parte 2 de 3 de la importación del 8 oct», con los totales del lote (renglones y unidades), los enlaces a las otras partes y «Descargar PDF del lote». Es el «resumen de todo lo importado» del flujo pedido.
5. **Resumen por categoría.** Tarjetas o tabla corta: categoría, renglones y unidades, de mayor a menor. Con `reportes.valor_inventario` aparece la columna «Valor» por categoría y un total (D-05), con las salvaguardas de BT-05 y de «Decisiones abiertas» (punto 3).
6. **Renglones (BT-06).** Tabla paginada de 50 en 50 con búsqueda a la vista (espera de 300 ms): renglón, código, artículo con marca, pieza y serie (o «Serie pendiente»), cantidad, condición, nivel con su regla, observación, de y a. En celular, tarjetas. Tocar una pieza abre su ficha y su línea de tiempo (SG-03).
7. **Relacionados (BT-06).** Lista de enlaces: «Recepciones de este traspaso» (folio, fecha, quién recibió), «Traspaso que se recibió», «Cancelado por», «Cancela a», «Otras partes del lote» y, en una entrada ligada a una compra urgente, «Solicitud de compra MID-SOL-000001» (SC-06).
8. **Acciones.** «Descargar PDF» (principal en computadora), «Imprimir», «Cancelar vale» y «Cancelar y rehacer», con las reglas de siempre (K-01 a K-05).

**Datos.**

- `GET /api/vales/{id}` (`vales.ver`) **cambia**: agrega `lote` (`{id, parte, partes, renglones, unidades}` o `null`), `proyecto`, `resumen` (por categoría: `{categoria, renglones, unidades}` y, solo con `reportes.valor_inventario`, `valor` por categoría y `valor_total`), `relacionados` (lista de `{relacion, id, folio, creado_en, texto}`; `id` y `folio` nulos fuera del alcance), `capturado_sin_conexion` y `capturado_en`. Sigue trayendo `renglones` completos para no romper la impresión ni el QR; con `?renglones=false` no los trae, y es lo que usa la pantalla nueva.
- `GET /api/vales/{id}/renglones?q=&pagina=&tamano=` (`vales.ver`, mismo alcance y mismo 404 que el detalle): la forma de los renglones del detalle, `{elementos, total, sin_registros, mensaje}`. `tamano` hasta 500, para que el PDF los pida de 500 en 500. `q` busca en código de artículo, código de pieza, nombre del artículo y serie, con las mismas reglas que Seguimiento (dos caracteres mínimo).

### D. PDF (BT-07 a BT-09)

**Acción por acción:**

1. **Tocar «Descargar PDF».** El botón cambia a «Armando el PDF…» con el indicador en línea. La pantalla no se bloquea.
2. **Juntar los datos.** El navegador ya tiene el encabezado; pide los renglones con `GET /api/vales/{id}/renglones?tamano=500` hasta tenerlos todos, la firma con `GET /api/vales/{id}/firma` (si `tiene_firma`) y dibuja el QR con el mismo componente de hoy (`qrcode.react`, convertido a imagen).
3. **Armar el archivo.** Hoja carta vertical. Encabezado con el logotipo de IMHOTEP y el folio en cada página; pie «Página 3 de 12 · Generado el 08/10/2026 16:40 por <usuario>». Las fechas van en hora del centro de México. Los textos usan acentos y ñ.
4. **Descargar.** El navegador guarda `KEP-ENT-000123.pdf`. En la app de Android (FEAT-020) se abre el diálogo de compartir o guardar del sistema.
5. **Error.** Si falla una petición, «No se pudo armar el PDF. Revisa la conexión y vuelve a intentar» con «Reintentar»; no se descarga un PDF a medias.

**Qué lleva y qué no.** Lleva lo de E-24 y el resumen por categoría en renglones y unidades. Un vale de ENTREGA lleva la leyenda de responsabilidad y la firma del trabajador; uno con `firma_modo = SESION` dice «Firmado con la sesión de <responsable>». Un vale cancelado lleva una marca de agua «CANCELADO» y el folio de su cancelación. **No lleva** costos ni valor en pesos, aunque quien lo descarga tenga `reportes.valor_inventario` o `catalogo.costos` (F-12, AC-07); ni CURP, NSS o foto del trabajador.

**Lote (BT-08).** Primera hoja: «Importación del 8 de octubre de 2026», almacén, responsable, una tabla de los vales (folio, estado, renglones, unidades y su QR pequeño) y los totales por categoría. Después, los renglones de cada vale bajo un encabezado con su folio. Un vale cancelado del lote se incluye con su marca. Con 1,240 renglones son unas 30 páginas.

**Rendimiento (BT-09).** Meta: 500 renglones en menos de 5 segundos en un celular de gama media (Android 10, 4 GB de memoria, como los equipos del almacén); un lote de 5,000 renglones en menos de 60 segundos en computadora. El armado se hace por tramos para no congelar la pantalla, y se puede cancelar. Si al medir no se alcanza la meta, se usa la letra estándar del PDF en lugar de Poppins (Decisiones abiertas, punto 2).

### E. Resultado de la importación y del traspaso por Excel (BT-10)

- **Importación** (`/entrada?metodo=excel`, «Dar entrada», EK-04): el resultado conserva el resumen, los folios y la tarjeta «Piezas nuevas». Agrega dos botones: «Ver en la bitácora» (abre `/bitacora?lote_id=<id_lote>` con el lote desplegado) y «Descargar PDF» (el del lote, o el del vale si fue uno solo). «Imprimir etiquetas de las piezas nuevas» sigue siendo el principal cuando el lote creó piezas; si no creó piezas, el principal es «Ver en la bitácora».
- **Traspaso por Excel** (FEAT-009): el resultado agrega «Ver el vale» y «Descargar PDF». El PDF sirve como lista impresa para verificar al recibir (cubre la necesidad de TR-10 sin el Excel).

### Consideraciones

- **Solo lee.** `GET /api/bitacora` y `GET /api/vales/{id}/renglones` viven en `consulta` y nunca escriben. La única escritura de esta feature es `vale.lote_id` al insertar, en `movimientos`.
- **El flujo normal manda en el diseño (D-01).** Un supervisor con un almacén ve su bitácora sin elegir almacén y sin columna de almacén; la columna aparece solo si su alcance tiene más de un almacén o si tiene `almacenes.todos`.
- **La bitácora es el centro para saber dónde está cada cosa (D-16).** Desde un renglón se llega al vale; desde el vale, a cada pieza y su línea de tiempo (SG-03); desde la pieza, a Seguimiento (C-13) y a Deudores (FEAT-018).
- **Mismo alcance que SG-05.** Lo que hoy ve un usuario en el reporte de movimientos es exactamente lo que ve agrupado por vale: ni más ni menos.
- **Un renglón por vale no cambia la regla de los vales.** Los vales y movimientos no se editan ni se borran; agruparlos es solo una forma de leerlos.

### Casos límite

| # | Situación | Qué pasa | Reglas |
|---|---|---|---|
| 1 | **Vale cancelado.** | En la bitácora sale con la insignia «Cancelado» y el folio de su cancelación; su cancelación sale como su propio renglón. El detalle muestra la banda con el motivo. El PDF lleva la marca de agua «CANCELADO». | BT-04, BT-07, K-02 |
| 2 | **Traspaso con varias recepciones** (recibido con diferencias y completado después). | Para el origen, el traspaso es una salida con estado «Recibido» o «Recibido con diferencias»; para el destino, es `EN_CAMINO` mientras falte algo, y cada recepción es su propio renglón de entrada. El detalle del traspaso lista todas sus recepciones con folio, fecha y quién recibió, y el avance «Recibido 38 de 40». | BT-04, BT-06, X-13 |
| 3 | **Vale de otro almacén fuera del alcance.** | No aparece en la bitácora. Si un vale propio se relaciona con él (la recepción de mi traspaso, hecha en el destino), se nombra sin folio ni enlace: «Recibido en otro almacén el 8 oct». Abrir su `id` directo responde 404. | BT-06, AC-06 |
| 4 | **Lote con una parte cancelada.** | El renglón del lote dice «1 de 3 cancelado»; desplegado, la parte 2 sale con su insignia y el folio de su cancelación. Los totales del lote cuentan las tres partes y el detalle aclara «Incluye 500 renglones de un vale cancelado». El PDF del lote incluye la parte cancelada con su marca. | BT-02, BT-08, K-04 |
| 5 | **Importación repetida** (el mismo archivo con otro `id_lote`, aceptando el aviso de I-12). | Son dos lotes distintos y salen como dos renglones. El segundo lleva la insignia «Archivo ya importado antes» (se sabe por la auditoría `importacion.confirmar` con `repetido: true`). Reintentar el **mismo** `id_lote` no crea nada y la bitácora no cambia. | BT-02, I-12 |
| 6 | **Filtros que no devuelven nada.** | «No hay vales con esos filtros» con «Quitar filtros». Con filtro de pieza o serie que no existe, el mismo mensaje (no un error). | BT-03 |
| 7 | **PDF de un vale sin firma** (devolución, traspaso, recepción, entrada: `firma_modo = SESION`). | En lugar de la firma: «Firmado con la sesión de <responsable> el 08/10/2026 16:40». Un NO_ADEUDO sale con la leyenda «Sin adeudos al 08/10/2026» y sin tabla de renglones. | BT-07, F-03, F-08, F-09 |
| 8 | **Vale capturado sin conexión** (FEAT-020) que recibió folio al sincronizar. | La bitácora lo ordena por `creado_en` (hora del servidor al sincronizar, RG-11) y lo marca «Capturado sin conexión el 08/10 14:02». El filtro de fechas usa `creado_en`. El detalle y el PDF muestran las dos horas. | BT-04, RG-11, FEAT-020 |
| 9 | **PDF de un vale que aún no se sincroniza** (en la app de Android). | Se puede descargar desde la cola local: «Folio pendiente: se asigna al sincronizar», con el QR del `token` que genera el equipo (OF-27); el QR abre «Pendiente de sincronizar» hasta que el vale llega al servidor. Al sincronizar, el PDF se vuelve a descargar con su folio. | BT-09, FEAT-020 |
| 10 | **Usuario sin permiso de valor.** | El resumen por categoría muestra solo renglones y unidades, sin columna «Valor» ni total; la respuesta no trae `valor` (el dato no se envía, AC-05). | BT-05, RG-12 |
| 11 | **Usuario con permiso de valor que descarga el PDF.** | El PDF sale igual que para todos: sin pesos. | BT-07, F-12 |
| 12 | **Entrega de una sola categoría y un solo artículo**, vista por quien tiene `reportes.valor_inventario`. | El valor de la categoría dividido entre las unidades daría el costo unitario. El valor se oculta cuando la categoría trae un solo artículo distinto: «No se muestra para no revelar el costo de un artículo» (Decisiones abiertas, punto 3). | BT-05, RG-12, D-05 |
| 13 | **Devolución con piezas de varios titulares.** | «Varios trabajadores (3)» en la bitácora; el filtro de trabajador la encuentra por cualquiera de ellos (se busca en `movimiento.trabajador_id`, no solo en `vale.trabajador_id`). | BT-01, BT-03, V-01 |
| 14 | **Filtrar por una serie dentro de una importación de 500 renglones.** | El renglón del lote dice «1 de 1,240 renglones coinciden»; al abrir el vale, la tabla llega filtrada por esa serie. | BT-03, BT-06 |
| 15 | **Supervisor con dos almacenes** (caso especial, AC-36). | Ve la bitácora de sus dos almacenes, con la columna Almacén y el filtro para dejar uno; su almacén activo no limita lo que ve. Sin almacén filtrado no hay dirección (`null`); al filtrar uno, un traspaso entre sus dos almacenes sale como salida en uno y como en camino en el otro. | BT-01, BT-04, AC-36 |
| 16 | **Vale de 500 renglones abierto en celular.** | La tabla carga 50 renglones por página como tarjetas; no se cargan los 500 a la vez. El PDF se arma por tramos con su indicador. | BT-06, BT-09 |
| 17 | **Traspaso por Excel recibido en el destino.** | El vale TRS tiene `lote_id` (un solo vale, insignia «Desde Excel»); su recepción no lo tiene. Para el destino, el traspaso sale en camino y la recepción sale como entrada. | BT-02 |
| 18 | **Vale anterior a la columna `lote_id`** (una importación partida antes de esta feature). | Sus partes salen como vales sueltos con folios seguidos. No se reconstruye el lote hacia atrás (Decisiones abiertas, punto 4). | BT-02 |

## Fuera de alcance

- Generar el PDF en el servidor (queda como alternativa si `jspdf` no se aprueba; ver Decisiones abiertas).
- Mandar el PDF por correo o WhatsApp.
- Imprimir directo a impresoras térmicas (sigue excluido).
- Mostrar en el PDF si el vale está íntegro (sello F-06, F-07): es de FEAT-001.
- Reconstruir lotes de vales anteriores a la columna.
- Editar, agrupar a mano o borrar vales desde la bitácora.
- Gráficas en la bitácora (la regla de solo tablas en reportes se mantiene).

## Criterios de aceptación

- **BT-01.** Dada una importación de 800 filas confirmada en Kepler, cuando el supervisor de Kepler abre la bitácora, entonces ve **un** renglón para esa importación, no 800.
- **BT-01.** Dado un usuario sin `bitacora.ver` ni `reportes.movimientos`, cuando pide `GET /api/bitacora`, entonces recibe 403; y dado un almacenista de Midrex, entonces solo ve vales de Midrex aunque pida otro `almacen_id`.
- **BT-02.** Dada una importación de 1,240 filas, cuando se confirma, entonces sus tres vales tienen el mismo `lote_id` y la bitácora muestra «3 vales, 1,240 renglones», que se despliega en los tres folios.
- **BT-02.** Dado un cuerpo de `POST /api/vales` con `lote_id`, entonces responde 422 y no guarda nada.
- **BT-03.** Dado un filtro por una serie que está en un vale de 500 renglones, entonces el renglón dice «1 de 500 renglones coinciden» y el detalle abre filtrado por esa serie.
- **BT-04.** Dado un traspaso de Kepler a Contratistas en tránsito, cuando se filtra por Kepler sale como salida y cuando se filtra por Contratistas sale como «En camino»; y al recibirlo, la recepción sale como entrada de Contratistas.
- **BT-04.** Dado que se abre `/reportes/movimientos`, entonces llega a la pestaña «Detalle por renglón» con los mismos filtros y el mismo contrato de SG-05.
- **BT-05.** Dado un usuario sin `reportes.valor_inventario`, cuando abre un vale, entonces la respuesta no trae `valor` ni `valor_total`; y con el permiso, trae el valor por categoría y nunca el de un renglón.
- **BT-05.** Dada una pantalla de 1280 px o más, entonces el detalle ocupa todo el ancho con el encabezado en dos columnas; y en 375 px, todo se lee sin desplazamiento horizontal de la página.
- **BT-06.** Dado un vale de 500 renglones, cuando se pide `GET /api/vales/{id}/renglones?tamano=50&pagina=3`, entonces devuelve los renglones 101 a 150 y `total: 500`; y dado un vale fuera del alcance, entonces 404.
- **BT-06.** Dado un traspaso recibido en dos recepciones, entonces su detalle enlaza las dos recepciones con folio, fecha y quién recibió.
- **BT-07.** Dado un vale de entrega firmado en pantalla, cuando se toca «Descargar PDF», entonces se descarga `KEP-ENT-000123.pdf` con la firma, el QR y todos los renglones, y sin ningún costo aunque el usuario tenga `catalogo.costos`.
- **BT-08.** Dado un lote de tres vales, cuando se descarga su PDF, entonces es un solo archivo con la hoja de resumen y los renglones de las tres partes.
- **BT-09.** Dado un vale de 500 renglones en un celular de gama media, entonces el PDF se descarga en menos de 5 segundos; y dado un lote de 1,240 renglones, entonces el indicador muestra el avance y se puede cancelar.
- **BT-10.** Dada una importación confirmada, cuando se toca «Ver en la bitácora», entonces se abre la bitácora con solo ese lote, desplegado.

## Módulos relacionados conocidos

- `movimientos`: columna `vale.lote_id`, parámetro interno `lote_id` en `MovimientoService.confirmar`, modelo y migración. Único que escribe.
- `importacion`: `service.py` (pasa `id_lote` como `lote_id` a cada parte; `_lote_confirmado` puede buscar por `lote_id`) y `service_traspasos.py` (pasa `id_lote` al único vale).
- `consulta`: repositorio y servicio nuevos de la bitácora por vale (`repository_bitacora.py`, `service_bitacora.py`), `GET /api/vales/{id}/renglones`, cambios en el detalle del vale (resumen, relacionados, lote). Lee `auditoria` para la marca de archivo repetido.
- `acceso`: `requiere_alguno` en el router de la bitácora.
- Frontend: `routes/supervision/bitacora.tsx` (nueva), `rep-movimientos.tsx` (pasa a pestaña), `routes/consulta/vale.tsx` y `componentes/entrega/detalle-vale.tsx` (rediseño), un componente de PDF en `componentes/dominio/` compartido con FEAT-019, `componentes/importacion/` (resultado), `componentes/traspasos/` (resultado), `routes.ts` y `sesion/menu.ts`.

## Cambios de datos o API esperados

- **Migración de Alembic:** `vale.lote_id` (UUID, nulo) e índice `ix_vale_lote_id`. Sin rellenar los vales anteriores. La invariante 5 no cambia: `lote_id` se escribe al insertar.
- **API nueva:** `GET /api/bitacora` (BT-01 a BT-04; `bitacora.ver` o `reportes.movimientos` con `requiere_alguno`; acepta `formato=csv`) y `GET /api/vales/{id}/renglones` (`vales.ver`).
- **API que cambia:** `GET /api/vales/{id}` agrega `lote`, `proyecto`, `resumen`, `relacionados`, `capturado_sin_conexion`, `capturado_en` y el parámetro `renglones=false`. `POST /api/vales` sigue rechazando `lote_id`. La respuesta de `POST /api/importacion` y de `POST /api/importacion/traspasos` agrega `lote_id` (igual al `id_lote`).
- **Sin cambios:** `GET /api/reportes/movimientos` (SG-05) y `GET /api/reportes/usuarios`.
- **Dependencia nueva (a aprobar):** `jspdf` y `jspdf-autotable` en `frontend/`.

## Restricciones y compatibilidad

- Las reglas viven en el servidor; la interfaz muestra lo que el servidor devuelve. El PDF se arma en el navegador, pero solo con datos que la API ya filtró por permiso y alcance: el navegador no decide qué se ve.
- Los vales y movimientos no se actualizan ni se borran.
- El detalle del vale y su impresión siguen funcionando para quien ya tiene enlaces o QR impresos.
- Los textos nuevos van en español llano: «Entrada», «Salida», «En camino», «Capturado sin conexión», nunca la clave interna.
- Fechas en UTC en la base y en hora del centro de México en pantalla y en el PDF.

## Riesgos

- **Rendimiento de la consulta agregada.** Contar renglones y unidades por vale sobre `movimiento` con historial largo. Se mitiga contando solo los vales de la página y midiendo con el índice `(vale_id, articulo_id)` que ya prevé el data-model.
- **Memoria del celular al armar un PDF grande.** Un lote de 5,000 renglones puede agotar la memoria del WebView en un equipo modesto. Se mitiga armando por tramos y, si hace falta, limitando el lote en celular a «Descarga el PDF del lote desde una computadora».
- **Dependencia nueva.** `jspdf` agrega peso a la aplicación; se carga bajo demanda (solo al tocar «Descargar PDF»), como recharts.
- **Fuga del costo por división.** Un valor por categoría con un solo artículo revela su costo unitario (caso límite 12).
- **Dos pantallas de bitácora.** Mantener «Por vale» y «Detalle por renglón» exige que los dos usen el mismo alcance; se prueba con los mismos casos de SG-05.

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla, con su ID en el nombre (`test_BT_01_…` a `test_BT_10_…`); BT-07 a BT-09 se prueban en el servidor por los datos que entrega (sin costos, renglones completos, paginación de 500) y en el navegador con una prueba del armado del PDF.
- La prueba de integración del guion del PDF del track sigue pasando.
- Migración arriba y abajo.
- Medición del PDF de 500 renglones en un celular de gama media y en la app de Android.
- Recorrido manual en 1280 px y en 375 px con Supervisor, Almacenista, Compras y Administrador.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): BT-01 a BT-10 en la sección 7.11; nota en SG-05 (se conserva como «Detalle por renglón») y en C-04.
- [api-contracts.md](../architecture/api-contracts.md): `GET /api/bitacora`, `GET /api/vales/{id}/renglones`, cambios de `GET /api/vales/{id}` y de la respuesta de las importaciones.
- [data-model.md](../architecture/data-model.md): `vale.lote_id` y su índice.
- [app-flow.md](../product/app-flow.md): `/bitacora`, la redirección de `/reportes/movimientos`, el resultado de la importación.
- [ui-ux.md](../product/ui-ux.md): «Detalle de un vale» (primero computadora), patrón «Renglón de lote», «Descargar PDF».
- [AGENTS.md](../../AGENTS.md): la lista de rutas que declaran `requiere_alguno` pasa de cuatro a cinco (`GET /api/bitacora`).
- Un ADR nuevo si se aprueba `jspdf` (PDF en el navegador frente al servidor).

## Decisiones abiertas

1. **Librería del PDF.** Propuesta: `jspdf` + `jspdf-autotable` en el navegador, porque sirve sin conexión (FEAT-020) y para las etiquetas (FEAT-019). Alternativa: `fpdf2` en el servidor (`GET /api/vales/{id}/pdf`), más simple de probar pero sin conexión no funciona y agrega un endpoint fuera de la tabla 5.4 del maestro. Falta tu aprobación de la dependencia.
2. **Letra del PDF.** Propuesta: la letra estándar del PDF (Helvetica, que trae acentos y ñ) para que sea rápido y ligero; Poppins solo si la medición lo permite.
3. **Valor en pesos con un solo artículo.** Propuesta: ocultar el valor de una categoría (y el total) cuando la cuenta trae un solo artículo distinto, para no revelar su costo unitario por división (RG-12, D-05). La misma salvaguarda aplicaría al consumo de FEAT-018.
4. **Lotes anteriores.** Propuesta: no reconstruirlos. Alternativa: una migración que reconstruya `lote_id` a partir de los `id_cliente` deterministas de la importación (uuid5 por lote, almacén y parte) y de la auditoría. Es posible pero frágil.
5. **Periodo por omisión de la bitácora.** Propuesta: últimos 7 días. Alternativa: hoy.
6. **`GET /api/reportes/movimientos` a futuro.** Propuesta: se conserva sin fecha de retiro, porque el CSV por movimiento sirve para auditar.
