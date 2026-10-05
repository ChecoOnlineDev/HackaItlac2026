# Historias de la Fase 5 — Traspasos

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-TRS-001: Enviar un traspaso

Como almacenista del almacén de origen, quiero enviar artículos a otro almacén escaneándolos, para surtirlo sin perder de dónde salieron.

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

Como almacenista del almacén de destino, quiero recibir un traspaso escaneando su QR, para que las existencias entren a mi almacén.

**Criterios de aceptación**

- El inicio muestra cuántos traspasos vienen en camino.
- Abre el traspaso desde la lista o escaneando su QR.
- Puede recibir todo de una vez o renglón por renglón.
- Al confirmar se emite un vale de recepción; las existencias entran al destino y las piezas cambian de ubicación.
- Quien recibe queda como responsable de lo recibido.
- Dado que no se recibe todo, entonces lo faltante sigue En tránsito y el traspaso queda "Recibido con diferencias".
- Dado un almacén distinto al destino, entonces no puede recibirlo.
- Dado un artículo que no es de ese traspaso, entonces se rechaza.
- El historial de cada pieza muestra origen, tránsito y destino.

**Reglas:** X-08, X-10 a X-13, F-09, RG-05.

**Fuera de alcance:** resolver las diferencias; regresar al origen lo no recibido.

**Casos límite:** un traspaso ya recibido no se puede recibir otra vez; dos personas del mismo almacén intentando recibirlo a la vez: una gana.

**Evidencia:** paso 5 del guion; existencias de ambos almacenes antes y después.
