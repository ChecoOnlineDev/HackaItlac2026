# FEAT-009: Traspasos por lista de Excel

Estado: **aprobada por el usuario, sin construir.** Amplía el alcance del MVP; el orden de construcción está en [plan-de-implementacion.md](../product/plan-de-implementacion.md).

## Problema u oportunidad

Al abrir un proyecto, Contratistas lo surte con un listado de herramientas y EPP («te acabo de dar este listado de herramientas», plática del patrocinador). Hoy el traspaso se captura renglón por renglón, escaneando o buscando cada artículo, y con cientos de renglones es lento y propenso a errores. La infraestructura para leer un Excel, mostrarlo en una tabla y revisarlo fila por fila ya existe en la importación de inventario ([FEAT-007](FEAT-007-importacion-reposicion-y-categoria-sugerida.md)), pero esa importación es de entradas de Compras y no mueve existencias entre almacenes.

## Objetivo

Que el supervisor que envía arme la **salida** de un traspaso subiendo un `.xlsx` o pegando una tabla, vea en una vista previa qué renglón sale bien, cuál avisa y cuál tiene error, y confirme un solo traspaso con su folio y su QR. La recepción no cambia.

## Historias de usuario

Como supervisor de un almacén, quiero armar un traspaso desde una lista de Excel, para surtir un proyecto sin capturar cada renglón a mano.

Como supervisor, quiero ver antes de confirmar qué filas tienen error y por qué, para corregir el archivo o dejarlas fuera a propósito.

Como supervisor que recibe, quiero recibir el traspaso como siempre (todo de una vez, casilla por renglón o escaneo), para no aprender nada nuevo.

Todavía no hay historia en `docs/stories/`: se escribe al aprobarse la feature.

## Alcance incluido

- Armar un traspaso subiendo un `.xlsx` o pegando una tabla, con la misma lectura y vista previa en tabla de la importación (TR-01).
- Un archivo es un traspaso: un origen y un destino elegido en pantalla (TR-02).
- Endpoints propios que exigen `traspasos.operar` (TR-03).
- Columnas `codigo`, `cantidad`, `codigo_pieza` y `serie`; las demás se ignoran con aviso (TR-04).
- Evaluación de cada fila con las mismas reglas de la captura manual: X-02, X-03, X-04, X-09 y AL-04 (TR-05).
- Todo o nada, con la decisión explícita «Dejar fuera las filas con error» (TR-06); esta opción entra al MVP solo si se aprueba (ver decisiones).
- Tope de 500 renglones por archivo (TR-07).
- Idempotencia por `id_lote` y aviso de archivo ya usado (TR-08).
- Plantilla `.xlsx` descargable para traspaso.
- Segunda entrega: descargar la lista de un traspaso como Excel para imprimirla y usarla como lista de verificación al recibir (TR-10).

## Fuera de alcance

- **Cambiar la recepción.** X-10 a X-13 y la pantalla de recibir con detalle (Recibir todo, casilla por renglón con − y +, escaneo, diferencias con observación RG-14) ya cubren la «lista con palomitas». El Excel solo arma la salida (TR-09).
- Un permiso de **recibir** separado de enviar: sigue pendiente (mejora 2 de [la red de almacenes](../product/red-de-almacenes-y-flujo.md), sección 12.1) y no entra aquí.
- Varios destinos en un archivo (se suben varios archivos).
- Nuevos modos en `/api/importacion`: el traspaso **no** es un tercer modo de esa ruta.
- Crear artículos o piezas desde el archivo del traspaso: solo mueve lo que ya existe.
- Resolver lo que nunca llega (fuera del MVP, X-13) y «Devolver todo al cerrar» (mejora 3).
- Importar el archivo con cantidades parciales de recepción: la recepción parcial ya existe y se hace en pantalla.

## Criterios de aceptación

- Dado un supervisor con `traspasos.operar` y un `.xlsx` con códigos y cantidades de su almacén, cuando elige el destino y lo sube, entonces ve la vista previa en tabla con el estado de cada fila y puede confirmar un solo traspaso con folio `CLAVE-TRS` y QR (TR-01, TR-02, TR-07).
- Dado un usuario sin `traspasos.operar` (por ejemplo, un almacenista), cuando llama a los endpoints del traspaso por lista, entonces recibe 403; y dado un usuario con `traspasos.operar` y sin `inventario.entradas`, entonces sí puede usarlos (TR-03).
- Dado un archivo con una fila cuyo artículo no tiene suficiente en el origen, o cuya pieza no está en él, entonces esa fila sale en rojo con la regla X-02 y no se confirma el traspaso (TR-05, TR-06).
- Dado un archivo con una pieza no apta, entonces la fila sale en amarillo con la regla X-04 y se puede confirmar; dado un artículo inactivo, entonces la fila sale verde (X-09) (TR-05).
- Dado un código que no existe en el catálogo ni como pieza, entonces la fila es un error y no crea nada (TR-05).
- Dado un archivo cuyo origen o destino es un almacén cerrado, entonces se rechaza con AL-04 (TR-05).
- Dado un destino que no es padre ni hijo del origen, cuando quien sube no tiene `almacenes.todos`, entonces todo el archivo sale en rojo con X-03; y cuando sí lo tiene, sale un aviso amarillo y la observación es obligatoria (TR-05).
- Dado un archivo con una pieza repetida, entonces es error; dado el mismo artículo por cantidad en varias filas, entonces se consolida en una («Unido: filas 2, 5, 9») (TR-04).
- Dada una cantidad `0.25` o `0,25`, entonces se rechaza y nunca se redondea (I-13) (TR-04).
- Dadas columnas extra como el nombre, entonces se ignoran con aviso y la vista previa muestra el nombre del catálogo (TR-04).
- Dado un archivo con filas en rojo, cuando la persona confirma, entonces el servidor no guarda nada (RG-09); y cuando toca «Dejar fuera las filas con error», entonces el traspaso se crea sin esas filas, la observación y la auditoría dicen cuántas y cuáles fueron (TR-06).
- Dado un archivo de más de 500 renglones (cada pieza cuenta uno), entonces se rechaza y se pide dividirlo (TR-07).
- Dado un lote confirmado dos veces con el mismo `id_lote`, entonces la segunda responde 200 con `repetida: true` y no crea otro vale (TR-08).
- Dado un archivo con el mismo contenido, modo, origen y destino que otro ya usado, entonces la vista previa avisa «este archivo ya se usó» y la confirmación pide `confirmar_repetido: true` (TR-08).
- Dado un traspaso creado por lista, cuando el destino lo recibe, entonces lo hace con las reglas X-10 a X-13 sin ningún cambio, y lo no recibido sigue En tránsito (TR-09).
- Segunda entrega: dado un traspaso, cuando se descarga su lista, entonces sale un Excel con sus renglones listo para imprimir (TR-10).

## Módulos relacionados conocidos

- `importacion`: lectura del `.xlsx` y de la tabla pegada, normalización, consolidación, huella y plantilla. **Solo lee el archivo y valida**; no escribe vales ni existencias.
- `movimientos`: es el único que escribe. Recibe los renglones normalizados y confirma el vale con tipo TRASPASO, con X-01 a X-14, RG-09 y el folio por `serie_folio`.
- `almacenes` (destino y estado, AL-04), `catalogo` (artículos y piezas), `auditoria` (eventos de la importación y del traspaso), `acceso` (permisos).

## Cambios de datos o API esperados

- Endpoints propios, todos con `traspasos.operar` declarado en su `router.py`. El contrato completo (cuerpos, esquema de la vista previa, errores) está en [api-contracts.md](../architecture/api-contracts.md), sección «Importación de traspasos», y es el que manda:
  - `GET /api/importacion/traspasos/plantilla`: `.xlsx` con las columnas `codigo`, `cantidad`, `codigo pieza` y `serie`.
  - `POST /api/importacion/traspasos/archivo`: lee un `.xlsx` (multipart) y devuelve columnas propuestas, filas y vista previa. No escribe.
  - `POST /api/importacion/traspasos/vista-previa`: `{filas, columnas, primera_fila, destino_almacen_id, almacen_id?}`; evalúa y no escribe.
  - `POST /api/importacion/traspasos`: confirma con lo anterior más `{id_lote, observacion?, dejar_fuera_errores, confirmar_repetido}`. 201; con un `id_lote` ya confirmado, 200 con `repetida: true`. Errores: 409 `ARCHIVO_REPETIDO`, 409 `FILAS_CON_ERROR`, 422 `TRASPASO_MUY_GRANDE` (más de 500 renglones, TR-07) y los de X-03 y RG-14 ya existentes.
  - Segunda entrega: `GET /api/traspasos/{id}/lista?formato=xlsx` para TR-10.
- Se evalúa si hace falta agregar la ruta a la lista de excepciones de `AGENTS.md`; con el permiso en el router no hace falta.
- Datos: ninguna tabla nueva ni migración. El `id_cliente` del vale se deriva del `id_lote`; la huella `sha256` queda en `despues.huella` de la auditoría, como en I-12.
- Tope de 500 renglones y tamaño del cuerpo: ajustes en `config.py`; el límite de 6 MB de `/api/importacion*` se extiende a estas rutas.

## Restricciones y compatibilidad

- La confirmación debe llamar al servicio de movimientos con tipo TRASPASO; el módulo `importacion` no importa modelos de vales ni escribe existencias.
- No cambia ningún contrato existente: `POST /api/vales` con TRASPASO y `/api/importacion` siguen igual.
- El traspaso resultante es un vale común: se cancela (X-14), se recibe y se consulta como cualquier otro.
- Los textos que ve la persona van en español llano.

## Riesgos

- Un archivo de 500 renglones de piezas puede ser lento de evaluar: medir con un archivo real.
- «Dejar fuera las filas con error» puede ocultar faltantes si se usa sin leer: por eso es explícito, deja constancia en la observación y la auditoría, y se propone mostrar la cuenta en el aviso de confirmación.
- Que el Excel traiga códigos de otro sistema: se rechazan como código inexistente; no se adivina.
- Dividir en varios archivos rompe la unidad «un surtido, un folio»: se acepta por el tope de 500.
- Permiso de recibir: hasta que exista uno separado, quien recibe en un proyecto sigue siendo un supervisor.

## Validaciones requeridas

- Una prueba por regla TR-01 a TR-10, con su ID en el nombre.
- Prueba de que `importacion` no escribe vales ni existencias (solo lo hace `movimientos`).
- Prueba de permisos: 403 sin `traspasos.operar`; acceso con `traspasos.operar` sin `inventario.entradas`.
- Prueba de idempotencia por `id_lote` y de la huella.
- Prueba de concurrencia: dos lotes simultáneos con las mismas piezas no duplican la salida.
- Prueba del tope de 500 y de la ruta no habitual (X-03) para todo el archivo.
- Ensayo con un Excel que el equipo no preparó.

## Documentos globales que podrían actualizarse

[reglas-de-negocio.md](../product/reglas-de-negocio.md) (TR-01 a TR-10, ya agregadas como propuesta; prioridades y sección 8 si cambia un permiso), [api-contracts.md](../architecture/api-contracts.md) (endpoints nuevos), [app-flow.md](../product/app-flow.md) (flujo del traspaso: armar por lista), [ui-ux.md](../product/ui-ux.md) si hay un patrón visual nuevo, [mvp-scope.md](../product/mvp-scope.md) (aprobación), [guia-por-rol.md](../guia-por-rol.md) y el [changelog](../releases/changelog.md) al construirse.

## Decisiones pendientes

Las decisiones 1, 4 y 5 están tomadas; la 2 y la 3 llevan su recomendación.

| # | Decisión | Recomendación |
|---|---|---|
| 1 | Quién arma el Excel de salida | **Decidido:** el supervisor que envía, el del almacén de origen (X-01). En la práctica: el supervisor de Kepler (o el Administrador) cuando surte a Contratistas, y el supervisor de Contratistas cuando surte a un proyecto. El Almacenista no. |
| 2 | Recepción con cantidades parciales | Ya existe (X-11, X-13, RG-14): se documenta y no se construye nada. Lo no recibido sigue En tránsito y exige observación. |
| 3 | Quién recibe en el proyecto | **Decidido:** un permiso de recibir (`traspasos.recibir`) separado de enviar (`traspasos.operar`). El Supervisor lo trae; se le puede dar al Almacenista desde Roles y permisos. La recepción por lista es X-15 y su lógica no cambia. |
| 4 | Si «Dejar fuera las filas con error» entra al MVP | **Decidido: sí**, como acción explícita que deja cuántas y cuáles filas en la observación y la auditoría. Sin ella, la persona corrige el archivo y lo sube otra vez. |
| 5 | Aprobar la feature como ampliación del alcance | **Decidido: aprobada** por el usuario. |
