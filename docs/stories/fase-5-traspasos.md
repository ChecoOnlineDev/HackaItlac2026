# Historias de la Fase 5 — Traspasos

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-TRS-001: Enviar un traspaso

Como supervisor del almacén de origen (o quien tenga `traspasos.operar`), quiero enviar artículos a otro almacén escaneándolos, para surtirlo sin perder de dónde salieron.

**Criterios de aceptación**

- Elige el destino; las rutas habituales aparecen primero y otra ruta muestra un aviso.
- Al escanear, solo se acepta lo que está en este almacén.
- Una pieza No apta puede enviarse, con aviso, y conserva su estado. Un artículo inactivo también puede enviarse.
- Al confirmar se emite un vale de traspaso con folio y QR, en estado En tránsito.
- Las existencias salen del origen y no cuentan para ningún almacén hasta la recepción.
- El vale conserva origen, destino, artículos, cantidades y responsable.

**Reglas:** X-01 a X-04, X-06, X-07, X-09, F-09.

**Fuera de alcance:** cancelar un traspaso (X-14); aviso por mínimo (X-05).

**Casos límite:** destino igual al origen se rechaza; un almacén cerrado no aparece como destino.

**Evidencia:** paso 5 del guion automatizado.

---

## US-TRS-002: Recibir un traspaso

Como supervisor del almacén de destino (o quien tenga `traspasos.recibir`, como un almacenista de proyecto al que se le dio ese permiso), quiero recibir un traspaso escaneando su QR, para que las existencias entren a mi almacén.

**Criterios de aceptación**

- El inicio muestra cuántos traspasos vienen en camino.
- Abre el traspaso desde la lista o escaneando su QR.
- Puede recibir todo de una vez o renglón por renglón.
- Al confirmar se emite un vale de recepción; las existencias entran al destino y las piezas cambian de ubicación.
- Quien recibe queda como responsable de lo recibido.
- Dado que no se recibe todo, entonces lo faltante sigue En tránsito y el traspaso queda "Recibido con diferencias".
- Dado que quedan diferencias, entonces se pide una observación obligatoria (RG-14); una recepción completa no la pide.
- Dado un almacén distinto al destino, entonces no puede recibirlo.
- Dado un artículo que no es de ese traspaso, entonces se rechaza.
- El historial de cada pieza muestra origen, tránsito y destino.

**Reglas:** X-08, X-10 a X-13, F-09, RG-05, RG-14.

**Fuera de alcance:** resolver las diferencias; regresar al origen lo no recibido.

**Casos límite:** un traspaso ya recibido no se puede recibir otra vez; dos personas del mismo almacén intentando recibirlo a la vez: una gana.

**Evidencia:** paso 5 del guion; existencias de ambos almacenes antes y después.

---

## US-TRP-001: Armar un traspaso desde un Excel

Como supervisor del almacén de origen, quiero armar un traspaso subiendo una lista de Excel, para enviar muchos artículos sin escanearlos uno por uno.

**Criterios de aceptación**

- Dado que elijo «Trasladar con una lista», entonces elijo un solo destino para todo el archivo, con las mismas rutas que al escanear (X-03); una ruta no habitual solo con `almacenes.todos` y observación obligatoria.
- Dado un archivo subido o pegado, entonces las columnas se proponen solas y las puedo cambiar antes de ver la vista previa.
- Dado un artículo que no está en el almacén de origen, o una cantidad mayor a la existencia, entonces su fila sale en rojo con el motivo (X-02).
- Dado que hay una fila en rojo, entonces no se confirma nada: el traspaso se guarda completo o no se guarda (RG-09).
- Dado que hay filas en rojo, cuando toco «Dejar fuera las filas con error», entonces se me pide confirmar y se me dice cuántas son y cuáles; al aceptar, el traspaso se confirma sin ellas.
- Dado un artículo que se controla por pieza, entonces el archivo trae una fila por pieza (código o serie), y la pieza repetida o que no está en el origen sale en rojo.
- Dado un archivo con más de 500 filas, entonces se rechaza completo con un motivo en español llano.
- Dado un archivo que ya se usó en otro traspaso, entonces la vista previa lo avisa y solo se confirma si lo acepto expresamente.
- Dado que toco «Confirmar» dos veces, o reintento tras perder la conexión, entonces se emite un solo vale.
- Al confirmar se emite el vale con folio `CLAVE-TRS` y QR, En tránsito; las existencias salen del origen, igual que con escaneo.
- Dado un traspaso armado así, entonces se recibe exactamente igual: «Recibir todo», casilla por renglón, escaneo y diferencias con observación (RG-14); la recepción no cambia.
- Dado un almacenista, entonces no ve «Trasladar» ni «Recibir» (X-01).

**Reglas:** X-01 a X-04, X-06, X-07, X-09, RG-09, RG-14 y las reglas TR-01 a TR-10 de FEAT-009 (cada prueba lleva el ID de su regla).

**Fuera de alcance:** cancelar un traspaso (X-14); crear artículos desde el archivo; varios destinos en un archivo; recibir con una lista de Excel.

**Casos límite:** destino igual al origen o cerrado se rechaza; filas del mismo artículo por cantidad se unen; una fila amarilla (pieza No apta, artículo inactivo) avisa y no detiene.

**Evidencia:** prueba de integración con un archivo de ejemplo; existencias de origen antes y después; recepción del vale resultante.

**Brief:** [FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md).

---

## US-TRP-002: Descargar la lista de un traspaso en Excel (segunda entrega)

Como supervisor del almacén de destino, quiero descargar en Excel la lista de lo que viene en un traspaso, para revisarla o imprimirla con los renglones en mano al recibir.

**Criterios de aceptación**

- Dado un traspaso que puedo ver, cuando toco «Descargar lista», entonces obtengo un archivo con folio, origen, destino, y por renglón código, artículo, pieza o serie, cantidad enviada, recibida y pendiente (TR-10).
- Dado un archivo descargado, entonces no trae costos ni datos reservados.
- Dado un traspaso de otro almacén que no es el mío (ni origen ni destino), entonces no puedo descargarlo.
- Dado un traspaso con diferencias, entonces el archivo distingue lo recibido de lo pendiente.

**Reglas:** TR-10, X-01, C-13.

**Fuera de alcance:** volver a subir ese archivo para recibir; formatos distintos de Excel; la primera entrega (US-TRP-001) no depende de esta.

**Evidencia:** descarga de un traspaso En tránsito y de uno con diferencias.
