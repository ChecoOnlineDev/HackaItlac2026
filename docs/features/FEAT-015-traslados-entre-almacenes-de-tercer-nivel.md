# FEAT-015: Traslados entre almacenes de tercer nivel

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Es el paso 1 del orden de construcción de la [iteración 01](../releases/iteration_01/README.md) (sección 7), junto con la verificación de punta a punta de los traspasos (D-21). Cambia X-03, A-05 (excepción de D-09) y, por consecuencia, AC-07. Reglas nuevas X-16 a X-21. Si algo de aquí contradice el [documento maestro](../releases/iteration_01/README.md), manda el maestro.

## Problema u oportunidad

En la plática del 8 de octubre el track pidió (hoja 1, punto 1): traslados entre almacenes de **tercer nivel** «permitidos siempre y cuando autorice el supervisor». Hoy no se puede: la regla X-03 solo deja pasar las rutas padre-hijo (Kepler con Contratistas, Contratistas con cada proyecto) y cualquier otra la hace **solo el Administrador** (`almacenes.todos`), con observación. En la operación real, cuando en Midrex sobra una herramienta que en HYL hace falta, el material tiene que regresar a Contratistas y volver a salir: dos traspasos, dos recepciones y un día perdido; o el supervisor le llama al Administrador para que lo haga él.

Además, D-21 pide que los traspasos queden **completamente funcionales**. La documentación dice que el traspaso por Excel (FEAT-009) y el permiso de recibir están «sin construir», pero el commit `ed7ce82` dice lo contrario. Hay que verificarlo en el entorno desplegado, no suponerlo (sección «Lista de verificación de traspasos»).

## Objetivo

Que un almacén de tercer nivel pueda mandar material directo a otro almacén de tercer nivel, con la autorización del supervisor del almacén que lo envía (D-09), sin pasar por Contratistas y sin depender del Administrador; que el destino lo reciba como cualquier traspaso; y que todos los caminos de traspaso queden comprobados en el entorno desplegado.

## Historias de usuario

Como supervisor de Midrex, quiero mandar a HYL una herramienta que me sobra, para que no tenga que regresar a Contratistas y volver a salir.

Como almacenista de Midrex al que el Administrador le dio permiso de enviar, quiero pedirle al supervisor que autorice el traslado desde su celular, para no esperar a que venga al mostrador.

Como supervisor de HYL, quiero saber que me mandaron algo desde Midrex y recibirlo como cualquier traspaso, para responder por lo que llega.

Como Administrador, quiero que los traslados entre proyectos queden con quién los autorizó y por qué, para revisarlos después.

Las historias se escriben en `docs/stories/` al empezar la construcción.

## Conceptos

- **Tercer nivel.** Un almacén de tipo `PROYECTO`: depende de un `SUBALMACEN` (hoy, Contratistas). Midrex, HYL, Laminador y Minas lo son ([red de almacenes](../product/red-de-almacenes-y-flujo.md), sección 3). No se confunde con el **proyecto** de FEAT-013 (D-02), que es otra entidad: un almacén de tercer nivel puede tener varios proyectos o ninguno.
- **Traslado lateral.** Un traspaso cuyo origen y destino son, los dos, de tercer nivel (X-18). Ejemplo: Midrex → HYL.
- **Supervisor del origen.** Quien tiene `autorizaciones.resolver` y tiene el almacén de origen en su conjunto de almacenes (AC-36 de FEAT-013; mientras FEAT-013 no se construya, el almacén asignado). Con `almacenes.todos`, el Administrador también lo es de cualquier almacén.
- **Envío propio.** El supervisor del origen arma y envía el traslado él mismo: su envío es la autorización (X-16).

## Flujo normal y casos especiales

El flujo normal (D-01) es un supervisor por almacén, y la ruta habitual sigue siendo **Kepler → Contratistas → tercer nivel** (X-03). El traslado lateral es una salida para lo que sobra en un proyecto y falta en otro; no reemplaza el surtido por Contratistas. Las pantallas se diseñan para el caso normal: **el supervisor de Midrex envía a HYL y el supervisor (o el almacenista con `traspasos.recibir`) de HYL lo recibe**. Por eso el envío propio (X-16) es el camino corto y el naranja con autorización (X-17) es el caso especial de un almacenista con `traspasos.operar`.

## Reglas

| ID | Regla | Origen |
|---|---|---|
| X-16 | **Envío propio del supervisor del origen.** Si quien envía un traslado lateral (X-18) tiene `autorizaciones.resolver` en el almacén de origen, su envío **es** la autorización. El vale sale en **amarillo** con el motivo X-16, pide una **observación obligatoria** (el motivo del traslado; sin ella, 422 con `regla: "X-16"`) y queda con «Validó: *su nombre* (envío propio)». Es una **excepción explícita a A-05 y a AC-07**, solo para este caso: no se crea ninguna solicitud de autorización y nadie se autoriza a sí mismo una solicitud. Como toda excepción resuelta con observación, entra a la lista de revisión (RG-14). | Plática del 8 oct 2026 (hoja 1, punto 1); D-09 |
| X-17 | **Traslado lateral con autorización.** Si quien envía un traslado lateral **no** tiene `autorizaciones.resolver` en el origen (por ejemplo, un almacenista al que se le dio `traspasos.operar`), el vale sale en **naranja** con el motivo X-17 y no se confirma sin una autorización `tipo = TRASLADO` aprobada por el supervisor del origen (X-19). La solicitud le llega por la misma notificación push de las solicitudes de despacho (FEAT-014, reglas NT), vence a los **15 minutos** (5.4) y se usa **una vez** (A-03). Rechazada o vencida, el traslado no sale; el borrador se conserva y se puede pedir otra. | D-09; A-01 a A-04 |
| X-18 | **Qué es un traslado lateral.** Origen y destino son de tipo `PROYECTO`, distintos y activos, **compartan o no el mismo subalmacén padre**. Se evalúa antes de la regla de ruta no habitual de X-03. Las demás rutas que no son padre-hijo (Kepler directo a un proyecto, un proyecto a Kepler, un proyecto a un subalmacén que no es su padre) **siguen igual**: solo con `almacenes.todos`, aviso amarillo X-03 y observación; para los demás, rojo `RUTA_SOLO_ADMINISTRADOR`. Quien tiene `almacenes.todos` y no tiene `autorizaciones.resolver` (un rol personalizado) hace el traslado lateral por X-03 (amarillo y observación), como cualquier ruta no habitual. | D-09; decisión de este brief |
| X-19 | **La autorización de traslado.** Cubre el origen, el destino y cada renglón con su código y su cantidad. Después de aprobada se pueden **quitar** renglones; no se puede agregar uno, subir una cantidad ni cambiar el destino (la autorización deja de cubrir el vale: 409 `AUTORIZACION_INVALIDA`). La resuelve quien tiene `autorizaciones.resolver` en el origen, o `almacenes.todos`, nunca quien la pidió (A-05); desde su celular o con su PIN en el dispositivo de quien envía (A-01). Se aprueba o se rechaza **completa**: no hay aprobación parcial por renglón (la de DE-* es solo para despachos). Un renglón en rojo no se autoriza (A-06): la solicitud se rechaza con 422 `RENGLON_NO_AUTORIZABLE`. Queda quién pidió, quién autorizó, cuándo y el motivo (A-04), y el vale lo muestra en «Validó». | D-09; A-01 a A-06 |
| X-20 | **Recepción del traslado lateral.** Se recibe igual que cualquier traspaso (X-10 a X-13 y X-15): todo, por renglón o con diferencias; lo no recibido sigue En tránsito y entra a revisión. Al confirmarse la salida, quienes tienen `traspasos.recibir` y el destino en su conjunto, y tienen los avisos activos en su dispositivo, reciben una **notificación push informativa** («HYL · Te enviaron un traslado desde Midrex», sin acción que resolver; se manda después del commit y con las reglas NT-03, NT-05 y NT-07 de FEAT-014; hoy NT-01 solo ofrece «Activar avisos» a quien tiene `autorizaciones.resolver`, así que en la práctica le llega al supervisor del destino) y el traslado aparece en «Por recibir» y en el contador del Inicio con la etiqueta «Traslado desde Midrex». Al evaluar la salida se avisa en amarillo, sin pedir observación: si en el destino no hay nadie activo con `traspasos.recibir` («Nadie en HYL puede recibir este traslado todavía»), y si el destino no tiene proyectos activos (PR-12, cuando exista FEAT-013). | D-09; propuesta (decisión abierta 2) |
| X-21 | **Envió y recibió la misma persona.** Si quien confirma una recepción es el mismo usuario que envió el traspaso (posible cuando un supervisor tiene los dos almacenes en su conjunto, AC-36), se permite, con aviso amarillo X-21 y **observación obligatoria**; el vale de recepción queda marcado «Envió y recibió la misma persona» y entra a la lista de revisión. Aplica a **todo** traspaso, no solo al lateral. | Decisión de este brief |

### Cambios en reglas existentes

| Regla | Texto propuesto |
|---|---|
| X-03 | «El destino es otro almacén activo. Rutas habituales: Kepler con Contratistas, y Contratistas con los almacenes de tercer nivel, en ambos sentidos (un almacén es padre del otro). **Entre dos almacenes de tercer nivel** la ruta es lateral y la autoriza el supervisor del origen (X-16 a X-19). **Otra ruta** (por ejemplo, Kepler directo a un proyecto) solo la hace quien tiene `almacenes.todos`, con aviso amarillo y observación obligatoria; para quien no lo tiene, es rojo.» |
| A-05 | «Quien captura el vale no puede autorizarse a sí mismo. **Excepciones:** el envío propio de un traslado lateral por el supervisor del origen (X-16) y el despacho que captura el propio supervisor (DE-07). En ninguna se crea una solicitud que la misma persona resuelva.» |
| AC-07 | Se agrega a «autorizarse a sí mismo»: «salvo las excepciones de A-05 (X-16, DE-07), que no son una autorización de una solicitud propia sino la autoridad de quien captura». |
| X-01 | Se corrige el texto: el Almacenista **sí** trae `traspasos.recibir` de inicio (AC-31 y el código lo traen; X-01 dice que no). No cambia la regla, solo la deja igual que la tabla 8.2. |
| TR-05 | Se agrega: «La ruta lateral (X-18) se evalúa una vez para todo el archivo con X-16 o X-17». |

## Alcance incluido

### A. Enviar un traslado lateral siendo el supervisor del origen (X-16, X-18)

Caso normal: Pedro es el supervisor de Midrex (`traspasos.operar` y `autorizaciones.resolver`) y manda a HYL tres eslingas y un minipulidor.

| # | Acción de Pedro | Qué hace el sistema |
|---|---|---|
| 1 | Inicio → **Trasladar**. | Abre el traspaso con origen Midrex (su almacén activo, RG-07). |
| 2 | Abre «¿A qué almacén se envía?». | La lista trae tres grupos: «Rutas habituales» (Contratistas), «**Entre proyectos** (las autorizas tú)» (HYL, Laminador, Minas) y, solo con `almacenes.todos`, «Otras rutas (piden una observación)». El texto del grupo lo decide el servidor con `ruta.autoriza` de la evaluación; la pantalla no decide. |
| 3 | Elige HYL. | Evalúa: motivo del vale X-16 en amarillo, «Traslado entre proyectos: de Midrex a HYL. Tú lo autorizas al enviarlo. Anota para qué se manda.» `pide_observacion: true`. Si HYL no tiene a nadie con `traspasos.recibir`, o no tiene proyectos activos, agrega los avisos de X-20. |
| 4 | Escanea o busca las eslingas y el minipulidor. | Solo ofrece lo que hay en Midrex con «Disponible: N» (TR-11). Cada renglón con X-02, X-04 y X-09 como hoy. |
| 5 | Escribe la observación («HYL arranca soldadura el lunes y le faltan eslingas»). | Sin observación, el botón dice «Escribe para qué se manda este traslado» y el servidor responde 422 con `regla: "X-16"`. |
| 6 | **Confirmar**. | Revalida (RG-08). Crea el vale TRASPASO `MID-TRS-…`, `EN_TRANSITO`, con QR (X-06); las existencias salen de Midrex a En tránsito (X-01). Cada movimiento lleva las reglas `X-16` y `X-18`. El detalle del vale muestra «Validó: Pedro (envío propio)». Se manda la push informativa a HYL (X-20). |
| 7 | Ve el resultado. | Folio, QR, «Va en camino a HYL» y el botón «Imprimir lista». |

### B. Enviar un traslado lateral sin ser el supervisor (X-17, X-19)

Caso especial: Ana es almacenista de Midrex y el Administrador le dio `traspasos.operar` (no tiene `autorizaciones.resolver`).

| # | Acción | Qué hace el sistema |
|---|---|---|
| 1 | Ana arma el traslado a HYL como en A, pasos 1 a 4. | El grupo de destinos dice «Entre proyectos (las autoriza el supervisor de Midrex)». El motivo del vale es X-17 en **naranja**: «Este traslado lo autoriza el supervisor de Midrex». La evaluación trae `ruta.autorizadores_disponibles` (cuántos pueden autorizar, sin contarla a ella). |
| 2 | Toca **Pedir autorización** y escribe el motivo (A-02). | `POST /api/autorizaciones` con `tipo: "TRASLADO"`, `destino_almacen_id`, los renglones (`codigo`, `cantidad`) y `motivo`. El servidor reevalúa el traslado: si algún renglón está en rojo, 422 `RENGLON_NO_AUTORIZABLE` (A-06) y no guarda nada. Si no, guarda la solicitud `PENDIENTE` con `vence_en` a 15 minutos y manda la push a los supervisores del origen (FEAT-014). |
| 3 | Ana ve «En espera de Pedro» con la cuenta regresiva. | La pantalla consulta el estado como en las autorizaciones de hoy (cada 3 s). El borrador no se puede editar mientras espera; «Cancelar la solicitud» lo libera. |
| 4a | Pedro toca la notificación, ve origen, destino, renglones (con sus avisos, por ejemplo X-04) y el motivo, y toca **Autorizar**. | La solicitud pasa a `APROBADA`. Si hay otro supervisor del origen con la misma notificación, se le cierra y su pantalla dice quién la resolvió (NT-06). |
| 4b | Pedro está en el mostrador: teclea su usuario y PIN en el celular de Ana. | Medio PIN (A-01); se verifica que Pedro tenga `autorizaciones.resolver` en Midrex. |
| 5 | La pantalla de Ana se actualiza sola a «Autorizado por Pedro». | El motivo X-17 queda `autorizado: true`. |
| 6 | Ana toca **Confirmar**. | `POST /api/vales` con `autorizacion_id`. El servidor valida que la autorización esté aprobada, vigente, sin usar, sea del origen y del destino del vale y cubra cada renglón (X-19). En la misma transacción crea el vale y la marca `USADA` (A-03). El vale muestra «Validó: Pedro (desde su celular)» o «(con su PIN)». Push informativa a HYL (X-20). |
| 7 | Si Pedro rechaza o no responde en 15 minutos. | «Pedro no autorizó el traslado» o «La solicitud venció». No se envía nada. Ana puede pedir otra, pedirle a Pedro su PIN o guardar el borrador. |

### C. Recibir el traslado en el destino (X-20, X-21)

| # | Acción | Qué hace el sistema |
|---|---|---|
| 1 | Lupita, supervisora de HYL, recibe la push «Te enviaron un traslado desde Midrex» (si tiene la PWA con notificaciones). En todo caso, su Inicio muestra «Recibir (1)». | El contador es el de hoy (`GET /api/traspasos/por-recibir?solo_contar=true`). |
| 2 | Abre **Recibir** → el traslado, con la etiqueta «Traslado desde Midrex» y «Validó: Pedro». | Es la misma recepción de X-10 a X-13 y X-15, con lista larga, búsqueda, filtros y «12 de 40 revisados». |
| 3 | Recibe todo, o marca renglón por renglón, o recibe con diferencias y escribe la observación (RG-14). | Igual que cualquier traspaso. Lo no recibido sigue En tránsito; el traspaso queda Recibido o Recibido con diferencias y se puede recibir otra vez. |
| 4 | Si quien recibe es el mismo usuario que envió (X-21). | Aviso amarillo «Tú enviaste este traspaso. Explica por qué también lo recibes.», observación obligatoria, marca en el vale y revisión. |

### D. Traslado lateral por lista de Excel (TR-05)

El traspaso por Excel evalúa la ruta una vez por archivo. En la vista previa, el banner de ruta dice «Entre proyectos: tú lo autorizas» (X-16, pide la observación del archivo) o «Entre proyectos: lo autoriza el supervisor de Midrex» (X-17, con el botón **Pedir autorización**). La solicitud lleva las filas normalizadas que **no** están en rojo (las mismas que se enviarían con «Dejar fuera las filas con error»). `POST /api/importacion/traspasos` acepta `autorizacion_id` y lo valida con X-19. Dejar fuera filas después de aprobar es quitar renglones: la autorización sigue sirviendo.

### E. Lo que no cambia

- **Rutas habituales** (Kepler ↔ Contratistas ↔ tercer nivel): verdes, sin autorización.
- **Rutas no habituales que no son laterales** (Kepler → Midrex, Midrex → Kepler): X-03 igual, solo con `almacenes.todos`.
- **Cancelación** (X-14): la hace el origen, con observación, antes de la recepción; la existencia regresa al origen. La autorización usada sigue `USADA` (A-03). Cancelar y rehacer (K-05) abre un borrador sin autorización: hay que pedir otra o, si es el supervisor, enviarlo como envío propio con observación.
- **Cierre de almacén** (AL-03): un traslado lateral en tránsito impide cerrar el origen y el destino, como cualquier traspaso.
- **Bitácora** (SG-05): sale en el origen como SALIDA y en el destino como EN_CAMINO y luego ENTRADA.

## Casos límite

| # | Situación | Qué pasa | Reglas |
|---|---|---|---|
| 1 | El destino está cerrado. | No se ofrece en la lista. Si llega por la API, la evaluación trae rojo AL-04 y confirmar responde 409 `ALMACEN_CERRADO`. Si se cierra entre la aprobación y el envío, el envío se rechaza y la autorización no se gasta. | AL-04, X-19 |
| 2 | El origen no tiene lo suficiente. | Renglón en rojo X-02. No se puede pedir autorización para él (422 `RENGLON_NO_AUTORIZABLE`); se quita o se corrige la cantidad. | X-02, A-06 |
| 3 | Se manda una pieza No apta (por ejemplo, un arnés para que HYL lo mande a reparar). | Amarillo X-04: se traslada y conserva su estado. El supervisor ve el aviso en la solicitud antes de autorizar. | X-04 |
| 4 | Un supervisor tiene Midrex y HYL en su conjunto y traslada de uno al otro. | Con Midrex como almacén activo, su envío autoriza (X-16). Para recibir cambia su almacén activo a HYL; si tiene `traspasos.recibir`, recibe con aviso X-21, observación y revisión. Lo normal sería que lo reciba el almacenista de HYL. | X-16, X-21, AC-36 |
| 5 | La solicitud vence sin respuesta. | A los 15 minutos queda `VENCIDA`. Se pide otra, o el supervisor da su PIN en el mostrador. | X-17, A-03 |
| 6 | La autorización se aprobó pero no se confirmó a tiempo. | Confirmar después de `vence_en` responde 409 `AUTORIZACION_INVALIDA` («La autorización venció»). | X-19 |
| 7 | El supervisor rechaza. | «Pedro no autorizó el traslado». No sale nada; el borrador se conserva. | X-17 |
| 8 | Traslado a un almacén sin proyectos activos (cuando exista FEAT-013). | Aviso amarillo PR-12 «HYL no tiene proyectos activos». No bloquea ni pide otra observación. | X-20, PR-12 |
| 9 | Los dos almacenes de tercer nivel dependen de subalmacenes distintos. | Es traslado lateral igual (X-18); el motivo lo dice: «Van por redes distintas (Contratistas y Contratistas Norte)». | X-18 |
| 10 | Kepler → Midrex directo. | Sin cambio: solo con `almacenes.todos`, amarillo X-03 y observación. Para el supervisor de Kepler, rojo `RUTA_SOLO_ADMINISTRADOR`. | X-03 |
| 11 | Midrex → Kepler, o Midrex → otro subalmacén que no es su padre. | No es lateral: X-03 sin cambio. | X-03, X-18 |
| 12 | Después de aprobada, se agrega un renglón o se sube una cantidad. | La autorización ya no cubre el vale: 409 `AUTORIZACION_INVALIDA`. Quitar renglones sí se permite. | X-19 |
| 13 | Entre la aprobación y el envío alguien más saca existencias del origen. | 409 `VALE_CAMBIO` con la evaluación nueva (RG-08). La autorización no se gasta; si sigue vigente y el vale ya solo quita renglones, sirve. | RG-08, X-19 |
| 14 | En Midrex nadie más que quien pide tiene `autorizaciones.resolver`. | La evaluación avisa «Nadie en Midrex puede autorizar ahora; también puede hacerlo el Administrador». La solicitud se puede mandar: el Administrador la ve en Autorizaciones. | X-17, X-19 |
| 15 | HYL quiere rechazar el traslado completo. | El destino no rechaza: recibe lo que llegó o pide al origen cancelarlo (X-14) antes de recibir. | X-10 a X-14 |
| 16 | El Administrador manda un traslado lateral. | Tiene `autorizaciones.resolver` en todos los almacenes: aplica X-16 (amarillo, observación, «Validó: él mismo»). | X-16 |
| 17 | Un rol personalizado con `almacenes.todos` y sin `autorizaciones.resolver`. | X-03 amarillo con observación, como cualquier ruta no habitual. | X-18 |
| 18 | Origen y destino son el mismo almacén. | Rojo X-03, sin cambio. | X-03 |
| 19 | Un almacenista sin `traspasos.operar`. | No ve Trasladar; la API responde 403 `SIN_PERMISO`. Tener `traspasos.recibir` no permite enviar. | X-01 |
| 20 | Se cae la señal después de aprobar. | El borrador vive en el dispositivo con su `id_cliente`; al volver la señal se confirma una sola vez. | RG-09 |
| 21 | Se cancela el traslado y se rehace (K-05). | El borrador nuevo no hereda la autorización: se pide otra o el supervisor lo envía como envío propio. | K-05, A-03 |
| 22 | Por Excel, con filas en rojo. | La solicitud de autorización lleva solo las filas que no son rojas; confirmar con «Dejar fuera las filas con error» usa la misma autorización. | TR-06, X-19 |
| 23 | El traslado llega incompleto. | Lo no recibido sigue En tránsito, el traslado queda Recibido con diferencias, entra a revisión y se recibe otra vez cuando llegue. | X-13 |
| 24 | El supervisor de HYL no tiene la PWA con notificaciones. | No pasa nada grave: el traslado aparece en su Inicio y en Recibir. La push del destino es informativa. | X-20 |

## Lista de verificación de traspasos

D-21 pide los traspasos **completamente funcionales**. Cada escenario se comprueba en el entorno desplegado (`docker compose up -d --build`, puerto 21040) con los usuarios de los datos de prueba, en celular y en computadora, y se marca solo cuando se vio funcionar. «En el código» dice lo que el repositorio tiene al 8 de octubre de 2026 según una lectura de los archivos, **no** que esté comprobado.

| # | Escenario | Quién | Resultado esperado | Reglas | En el código | Verificado |
|---|---|---|---|---|---|---|
| 1 | Enviar por la ruta habitual (Kepler → Contratistas y Contratistas → Midrex), escaneando y buscando | Supervisor del origen | Folio `CLAVE-TRS`, QR, existencias en tránsito; el buscador solo ofrece lo del origen | X-01 a X-07, TR-11 | Sí (`tipos/traspaso.py`, `trasladar.tsx`, `test_traspaso_envio.py`) | ☐ |
| 2 | Recibir todo de una vez | Supervisor del destino | Traspaso Recibido; existencias en el destino | X-10, X-11 | Sí (`tipos/recepcion.py`, `recibir-detalle.tsx`, `test_recepcion.py`) | ☐ |
| 3 | Recibir con diferencias | Supervisor del destino | Pide observación; queda Recibido con diferencias; lo demás sigue en tránsito | X-13, RG-14 | Sí | ☐ |
| 4 | Recibir de nuevo hasta completar | Supervisor del destino | El traspaso sigue en «Por recibir» hasta que no falta nada; entonces Recibido | X-13 | Sí | ☐ |
| 5 | Cancelar en tránsito | Supervisor del origen | Vale de cancelación; la existencia regresa al origen; el destino ya no lo ve; desde el destino, 409 | X-14, K-01 a K-04 | Sí (`test_cancelacion_*.py`) | ☐ |
| 6 | Traspaso por Excel (subir, vista previa sola, dejar fuera filas con error, archivo repetido, más de 500 filas) | Supervisor del origen | Un vale por archivo; las filas en rojo bloquean salvo «Dejar fuera»; aviso de archivo usado | TR-01 a TR-09, TR-12, TR-13 | Sí: backend (`importacion/router_traspasos.py`, 4 rutas; `test_traspaso_lista.py`) y frontend (`componentes/traspasos-lista/trasladar-con-lista.tsx`). Los documentos dicen «sin construir». TR-10 (descargar la lista) no está. | ☐ |
| 7 | Recepción por lista larga (búsqueda, filtro Pendientes, contador «n de m revisados», escaneo que lleva al renglón) | Quien recibe | La interfaz ayuda; el servidor evalúa igual | X-15 | Sí (`recibir-detalle.tsx`) | ☐ |
| 8 | Recibir con un almacenista que tiene `traspasos.recibir` | Almacenista del destino | Ve Recibir y recibe; sin el permiso no la ve y la API da 403 | X-01, X-10, AC-34 | Sí (permiso en `acceso/permisos.py` y en el rol Almacenista de `datos_prueba.py`) | ☐ |
| 9 | Ruta lateral con el supervisor del origen | Supervisor de Midrex | Amarillo X-16, observación, «Validó: él mismo»; HYL recibe | X-16, X-18, X-20 | No (esta feature) | ☐ |
| 10 | Ruta lateral con autorización | Almacenista con `traspasos.operar` y supervisor | Naranja X-17; push al supervisor; aprobar, enviar y recibir; probar también rechazo y vencimiento | X-17, X-19 | No (esta feature) | ☐ |
| 11 | Ruta no habitual del Administrador (Kepler → Midrex) | Administrador | Amarillo X-03 y observación; para un supervisor, rojo `RUTA_SOLO_ADMINISTRADOR` | X-03 | Sí (`test_traspaso_ruta_x03.py`) | ☐ |
| 12 | Misma persona envía y recibe | Supervisor con dos almacenes | Aviso X-21, observación, marca en el vale | X-21 | No (esta feature; necesita AC-36 de FEAT-013) | ☐ |

Al terminar la verificación se corrigen, en el mismo cambio, los documentos que dicen que FEAT-009 y `traspasos.recibir` están sin construir: [docs/README.md](../README.md), [mvp-scope.md](../product/mvp-scope.md), el encabezado de «Traspasos por lista de Excel» y la nota de 8.3 en [reglas-de-negocio.md](../product/reglas-de-negocio.md), el estado de [FEAT-009](FEAT-009-traspasos-por-lista-de-excel.md) y la sección 13 de [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md). Lo que falle se registra como un FIX en `docs/fixes/`.

## Fuera de alcance

- Que el destino **rechace** un traslado. Lo resuelve el origen cancelando (X-14).
- Aprobación parcial de un traslado (la de FEAT-014 es solo para despachos).
- Solicitud de surtido desde el proyecto («me falta esto»): sigue pospuesta ([red de almacenes](../product/red-de-almacenes-y-flujo.md), 12.2).
- Traslados laterales sin conexión: la app de Android (FEAT-020) no envía traspasos.
- Cambiar las rutas habituales o quitar a Contratistas de la cadena.
- «Devolver todo al cerrar» y la descarga de la lista (TR-10).
- Que un traslado lateral cambie el proyecto de algo: el consumo es del proyecto de la entrega (D-13), no del almacén.

## Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-15-01 | Dado el supervisor de Midrex, cuando arma un traspaso a HYL, entonces la evaluación trae X-16 en amarillo con `pide_observacion: true`; sin observación, confirmar responde 422 con `regla: "X-16"`; con ella, se crea el vale `EN_TRANSITO` y su detalle trae `valido.medio = "ENVIO_PROPIO"` con su nombre (X-16, X-18). |
| CA-15-02 | Dado un almacenista de Midrex con `traspasos.operar` y sin `autorizaciones.resolver`, cuando arma un traspaso a HYL, entonces la evaluación trae X-17 en naranja, `puede_confirmar: false`, y confirmar sin `autorizacion_id` responde 409 `VALE_CAMBIO` sin guardar nada (X-17). |
| CA-15-03 | Dado ese almacenista, cuando pide la autorización con `tipo: "TRASLADO"`, entonces se crea una solicitud `PENDIENTE` sin trabajador, con origen, destino y renglones evaluados por el servidor, que vence en 15 minutos; y un renglón en rojo hace que se rechace con 422 `RENGLON_NO_AUTORIZABLE` (X-17, X-19, A-06). |
| CA-15-04 | Dada una solicitud de traslado pendiente, cuando la resuelve el supervisor de Midrex desde su sesión o con PIN, entonces queda `APROBADA`; si la intenta resolver quien la pidió, 403 `AUTORIZACION_PROPIA`; si la intenta resolver el supervisor de HYL, 404 (X-19, A-01, A-05). |
| CA-15-05 | Dada una autorización de traslado aprobada, cuando se confirma el vale con ella, entonces el vale se crea y la autorización queda `USADA` en la misma transacción; usarla otra vez responde 409 `AUTORIZACION_INVALIDA` (X-19, A-03). |
| CA-15-06 | Dada una autorización aprobada, cuando el vale agrega un renglón, sube una cantidad o cambia de destino, entonces 409 `AUTORIZACION_INVALIDA`; y cuando solo quita un renglón, entonces se confirma (X-19). |
| CA-15-07 | Dada una solicitud de traslado vencida o rechazada, cuando se intenta confirmar con ella, entonces 409 `AUTORIZACION_INVALIDA` y no se guarda nada (X-17). |
| CA-15-08 | Dado un traspaso Kepler → Midrex, entonces sigue X-03 sin cambio: rojo `RUTA_SOLO_ADMINISTRADOR` para el supervisor de Kepler y amarillo con observación para el Administrador (X-03, X-18). |
| CA-15-09 | Dados dos almacenes de tipo `PROYECTO` con padres distintos, entonces el traspaso entre ellos se evalúa como lateral (X-18). |
| CA-15-10 | Dado un traslado lateral confirmado, entonces aparece en «Por recibir» del destino con la etiqueta del origen y quién lo validó, y quienes tienen `traspasos.recibir` en el destino reciben la notificación informativa (cuando exista FEAT-014) (X-20). |
| CA-15-11 | Dado un traslado lateral en tránsito, cuando el destino lo recibe con diferencias, entonces se comporta igual que cualquier traspaso: observación obligatoria, Recibido con diferencias, lo demás en tránsito y se puede recibir otra vez (X-20, X-13). |
| CA-15-12 | Dado un traspaso que envió un usuario, cuando ese mismo usuario confirma su recepción, entonces la evaluación trae X-21 en amarillo con `pide_observacion: true`; sin observación, 422 con `regla: "X-21"`; con ella, el vale de recepción queda marcado (X-21). |
| CA-15-13 | Dado un Excel de traspaso con destino lateral, cuando lo sube el supervisor del origen, entonces el banner trae X-16 y pide observación; cuando lo sube un almacenista con `traspasos.operar`, entonces trae X-17 y la confirmación exige `autorizacion_id` (TR-05, X-16, X-17). |
| CA-15-14 | Dado un traslado lateral en tránsito, cuando el origen lo cancela, entonces la existencia regresa al origen y la autorización sigue `USADA` (X-14, A-03). |
| CA-15-15 | Dado un destino sin nadie activo con `traspasos.recibir`, entonces la evaluación de la salida trae un aviso amarillo X-20 que no pide observación ni bloquea (X-20). |
| CA-15-16 | Dada la lista de verificación de traspasos, entonces sus 12 escenarios están marcados como verificados en el entorno desplegado y los documentos que decían «sin construir» están corregidos (D-21). |

## Módulos relacionados conocidos

- `movimientos`: `evaluador_traspasos.py` (una función pura `clasificar_ruta` que devuelve HABITUAL, LATERAL, NO_HABITUAL o MISMO; `HechosAlmacen` gana `tipo`; X-16, X-17, X-18 y X-20), `tipos/traspaso.py` (autorización de traslado al confirmar, `valido` del envío propio), `tipos/recepcion.py` (X-21), `verificador.py` (verificador de renglones para la autorización de traslado). Sigue siendo el único que escribe vales y existencias.
- `autorizaciones`: tipo TRASLADO, `trabajador_id` opcional para ese tipo, validación de traslado (origen, destino y renglones en lugar de trabajador), permiso de solicitar según el tipo.
- `notificaciones` (FEAT-014): la push al supervisor del origen y la informativa al destino.
- `importacion`: `service_traspasos.py` acepta `autorizacion_id` y muestra la ruta lateral en la vista previa. No escribe vales.
- `acceso`: quién es supervisor de un almacén con el conjunto de almacenes (FEAT-013).
- Frontend: `routes/operacion/trasladar.tsx`, `componentes/traspasos/selector-destino.tsx` (tercer grupo), `componentes/traspasos-lista/trasladar-con-lista.tsx`, `routes/operacion/recibir.tsx` y `recibir-detalle.tsx` (etiqueta y X-21), `routes/supervision/autorizaciones.tsx` (tarjeta de traslado), detalle del vale («Validó»).

## Cambios de datos o API esperados

**Datos** (una migración de Alembic; si FEAT-014 todavía no la hizo, esta crea la columna `tipo` con sus tres valores):

| Cambio | Qué guarda |
|---|---|
| `autorizacion.tipo` (`EXCEDENTE`, `DESPACHO`, `TRASLADO`; las existentes quedan `EXCEDENTE`) | Ya está en el maestro (5.1), compartido con FEAT-014. |
| `autorizacion.trabajador_id` pasa a **aceptar nulo**, con un CHECK: nulo solo si `tipo = 'TRASLADO'` | Un traslado no tiene trabajador. **No está en el maestro** (ver contradicciones). |
| `autorizacion.detalle` (JSON, ya existe) lleva `origen_almacen_id`, `destino_almacen_id` y los renglones | Sin columna nueva. `almacen_id` es el origen. |

El envío propio (X-16) no crea autorización: «Validó» se deriva de la regla `X-16` en los movimientos y del responsable del vale. La marca de X-21 se deriva de que el responsable de la recepción sea el del traspaso. Ninguna de las dos pide columna.

**API** (se actualiza [api-contracts.md](../architecture/api-contracts.md)):

| Endpoint | Cambio |
|---|---|
| `POST /api/vales/evaluar` (TRASPASO) | Trae `ruta: {clase: "HABITUAL" \| "LATERAL" \| "NO_HABITUAL" \| "MISMO", autoriza: "NADIE" \| "ENVIO_PROPIO" \| "SUPERVISOR_ORIGEN" \| "ADMINISTRADOR", autorizadores_disponibles}` y, en `motivos` del vale, X-03, X-16, X-17, X-18 o X-20 según el caso; X-17 trae `autorizable: true` y, con `autorizacion_id`, `autorizado: true`. |
| `POST /api/vales` (TRASPASO) | Acepta `autorizacion_id`. Errores: 422 con `regla: "X-16"` sin observación; 409 `AUTORIZACION_INVALIDA` (no aprobada, vencida, usada, de otro origen o destino, o que no cubre); 409 `VALE_CAMBIO` con X-17 sin autorizar. |
| `POST /api/vales/evaluar` y `POST /api/vales` (RECEPCION) | X-21 en amarillo con `pide_observacion`; 422 con `regla: "X-21"` sin observación. |
| `POST /api/autorizaciones` | Acepta `tipo: "TRASLADO"` con `destino_almacen_id`, `id_cliente`, `motivo` y `renglones` (`codigo`, `cantidad`), sin `trabajador_id`. El permiso depende del tipo: `traspasos.operar` para TRASLADO, `entregas.crear` para los demás. Por eso el router pasa a exigir solo sesión y el servicio verifica la clave (se agrega a las excepciones de [AGENTS.md](../../AGENTS.md)). La push al supervisor del origen sigue NT-02 a NT-07 con el texto «Midrex · Traslado por autorizar» / «A HYL: 4 artículos. Lo pide Ana Ruiz.». |
| `GET /api/autorizaciones`, `GET /api/autorizaciones/{id}` | Traen `tipo`, `origen` y `destino`; `trabajador` es `null` en un traslado. |
| `POST /api/autorizaciones/{id}/resolucion` | En un traslado no acepta `renglones` (422): se aprueba o se rechaza completa. Con PIN, la sesión de quien envía debe tener `traspasos.operar`. |
| `GET /api/traspasos/por-recibir` | Cada elemento trae `ruta` (`HABITUAL`, `LATERAL`, `NO_HABITUAL`) y `valido`. |
| `POST /api/importacion/traspasos/vista-previa` y `POST /api/importacion/traspasos` | La vista previa trae la `ruta` como la evaluación; la confirmación acepta `autorizacion_id`. |

Sin permisos nuevos.

## Restricciones y compatibilidad

- Solo `movimientos` escribe vales, movimientos y existencias; `autorizaciones` solo guarda la solicitud y la marca usada dentro de la transacción del vale.
- Las reglas viven en el servidor: el grupo de destinos, el color y el texto «tú lo autorizas» salen de la evaluación.
- Los permisos se verifican por clave, nunca por el nombre del rol: «supervisor del origen» es `autorizaciones.resolver` en ese almacén.
- Los traspasos ya existentes no cambian. Las autorizaciones existentes quedan `EXCEDENTE` y con trabajador.
- La push depende de FEAT-014, que va después en el orden de construcción. Sin ella, la solicitud se ve en Autorizaciones (con su contador) y el supervisor puede dar su PIN: el traslado funciona; la push se enchufa cuando exista el módulo `notificaciones`.
- Los textos van en español llano: «Entre proyectos», «Tú lo autorizas», «Lo autoriza el supervisor de Midrex».

## Riesgos

- **Que el traslado lateral se vuelva costumbre** y Contratistas pierda el control del surtido. Mitigación: observación obligatoria en el envío propio, revisión y la etiqueta en la bitácora; el Administrador puede quitar `traspasos.operar` a quien abuse.
- **Supervisores que se autorizan solos.** Es lo que pidió el track (D-09). Se deja constancia y revisión; no hay un segundo par de ojos salvo en X-17.
- **Choque con FEAT-014** en la tabla `autorizacion` y en el router: si se construyen en paralelo, la primera crea `tipo` y la otra se rebasa.
- **Dependencia del conjunto de almacenes** (FEAT-013): X-21 y «supervisor del origen» con varios almacenes no se pueden probar hasta que exista AC-36.
- **La verificación encuentra fallas** en lo que el commit `ed7ce82` dio por construido: se registran como FIX y entran antes que X-16.

## Validaciones requeridas

- Una prueba por regla con su ID en el nombre: `test_x16_*` a `test_x21_*`, más las de los cambios de X-03, A-05 y TR-05.
- Prueba de que la autorización y el vale se escriben en la misma transacción y de que dos envíos simultáneos con la misma autorización solo usan una.
- Prueba de permisos: TRASLADO sin `traspasos.operar` da 403 al pedir; resolver sin `autorizaciones.resolver` en el origen da 404.
- Prueba del Excel con ruta lateral (X-16 y X-17).
- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck`, `pnpm build` y la migración arriba y abajo.
- La lista de verificación de traspasos completa en el entorno desplegado, en celular y en computadora.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): X-16 a X-21 en 7.5 y 7.6; X-03, A-05, AC-07, X-01 y TR-05; índice de casos especiales (7.12); prioridades (sección 9); historial.
- [api-contracts.md](../architecture/api-contracts.md): Vales (TRASPASO y RECEPCION), Autorizaciones, Importación de traspasos.
- [data-model.md](../architecture/data-model.md): `autorizacion.tipo` y `trabajador_id` opcional.
- [app-flow.md](../product/app-flow.md): flujos 7, 9 y 10.
- [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md): secciones 2, 3, 7, 12 y 13 (ruta lateral y estado de lo construido).
- [AGENTS.md](../../AGENTS.md): `POST /api/autorizaciones` pasa a las rutas que verifican el permiso en el servicio.
- [guia-por-rol.md](../guia-por-rol.md), el tutorial (FEAT-010) y el [changelog](../releases/changelog.md) al construirse.

## Decisiones abiertas

| # | Decisión | Propuesta |
|---|---|---|
| 1 | ¿Traslado lateral solo entre almacenes que comparten subalmacén? | **No:** basta que los dos sean de tercer nivel (X-18). Quien responde es el supervisor del origen, y hoy solo existe Contratistas. Si el track quiere limitarlo, se cambia X-18 sin tocar lo demás. |
| 2 | ¿El destino recibe una push? | **Sí, informativa** (X-20), reutilizando las reglas NT. Le llega a quien tiene los avisos activos; con NT-01 como está, solo el supervisor puede activarlos. Si se quiere que también le llegue al almacenista con `traspasos.recibir`, hay que ampliar NT-01 en FEAT-014. Si molesta, se apaga sin cambiar la recepción. |
| 3 | ¿Se permite que la misma persona envíe y reciba? | **Sí**, con aviso, observación y revisión (X-21), y para todo traspaso. Alternativa más estricta: prohibirlo y que reciba otra persona. |
| 4 | ¿Aprobación parcial del traslado? | **No.** Quien envía quita los renglones y pide otra. |
| 5 | ¿El destino puede rechazar el traslado? | **No** en esta iteración: el origen lo cancela. |
| 6 | ¿El envío propio del supervisor entra a la lista de revisión? | **Sí**, como toda excepción con observación (RG-14). La pantalla de revisión sigue pospuesta (P2); mientras, queda en la bitácora y en la auditoría. |
