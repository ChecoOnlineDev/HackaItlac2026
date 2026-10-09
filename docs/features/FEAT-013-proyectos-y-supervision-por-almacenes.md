# FEAT-013: Proyectos, asignación de trabajadores y supervisión por almacenes

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.**

Documento maestro: [iteración 01](../releases/iteration_01/README.md) (decisiones D-01 a D-05 y D-13). Si este brief lo contradice, manda el maestro hasta que se corrija uno de los dos en el mismo cambio. Decisión de arquitectura: [ADR-012](../architecture/decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md). Reglas que usa: PR-01 a PR-14, AC-36 a AC-41 y TB-04 a TB-08. Cambia RG-07, AC-06, AC-12, AC-13, A-01, AL-03, TB-01, T-02, T-03 y E-24 (sección «Reglas existentes que cambian»). Extiende el valor del inventario que ya está en el código (FEAT-012, `GET /api/tablero/valor`, sin documento).

**Flujo normal (D-01).** Un supervisor está en **un** almacén y cada trabajador en **un** proyecto de ese almacén. Supervisor con varios almacenes, trabajador con varios proyectos y almacén con varios proyectos son **casos especiales**: el modelo los soporta desde el primer día, pero las pantallas se diseñan para el caso normal y los casos especiales aparecen solo cuando existen (sin selectores ni columnas de más).

## Problema u oportunidad

1. **El proyecto no existe como dato.** Hoy «proyecto» es un almacén de tercer nivel (tipo `PROYECTO`) y el trabajador solo tiene un texto libre, `periodo_contrato.area_obra`. No se puede saber cuánto consumió un mantenimiento, ni quién trabaja en él, ni cuándo termina.
2. **El consumo se cuenta en el almacén que entrega, no en el proyecto que usa.** El EPP sale de Contratistas, pero lo usa la gente del proyecto de Midrex. El supervisor de Midrex no lo ve.
3. **Un supervisor solo puede tener un almacén.** AC-06 dice «el suyo o todos». La plática del 8 de octubre pide que un supervisor pueda llevar más de uno y saltar entre ellos (D-04).
4. **El supervisor no ve dinero.** El valor del inventario existe en el código (FEAT-012) pero solo para Compras. La plática pide que el supervisor vea el valor de sus almacenes y el uso por proyecto, en pesos y en unidades (D-05).
5. **Un almacén de proyecto que ya no tiene trabajo se queda abierto** sin que nadie lo note.
6. **El «periodo por apertura» quedó pospuesto** (FEAT-008, sección 5): el reporte de cierre se pedía por rango de fechas a mano. El proyecto, con sus fechas, lo resuelve.

## Objetivo

- Que el proyecto sea un dato propio, con almacén, fechas y estado, que se da de alta **antes** que sus trabajadores.
- Que cada trabajador esté en un proyecto desde su alta, y que cada entrega quede ligada a ese proyecto sin que el almacenista tenga que pensarlo.
- Que el supervisor vea, al entrar, cuánto vale lo que tiene a su cargo y cuánto ha usado cada proyecto de sus almacenes.
- Que un usuario pueda tener un conjunto de almacenes y operar en uno a la vez, sin cambiar nada para quien tiene uno solo.
- Que el sistema avise cuándo un almacén de proyecto se quedó sin proyectos, sin cerrarlo solo.

## Historia de usuario

Como **Administrador**, quiero dar de alta un proyecto con su almacén y sus fechas antes de que lleguen los trabajadores, para que RH los asigne desde el primer día.

Como **Recursos Humanos**, quiero elegir el proyecto del trabajador al darlo de alta, para que todo lo que reciba cuente para ese proyecto.

Como **almacenista**, quiero que la entrega tome sola el proyecto del trabajador, y que solo me pregunte cuando tenga más de uno, para no perder tiempo en el mostrador.

Como **supervisor**, quiero ver al entrar cuánto vale el inventario de mis almacenes y cuánto ha usado cada proyecto, en pesos y en unidades, para responder por ellos.

Como **supervisor de dos almacenes**, quiero ver los dos en el Inicio y cambiar con un toque el almacén donde opero, para no tener dos cuentas.

Como **Administrador**, quiero que el sistema me avise cuando un almacén de proyecto ya no tiene proyectos activos, para decidir si lo inactivo.

Las historias de `docs/stories/` se escriben al empezar la construcción.

## Alcance incluido

### A. Reglas de proyectos (PR)

Definiciones que usan las reglas (todas las fechas son del centro de México):

| Término | Qué es |
|---|---|
| **Proyecto activo** | `estado = ACTIVO`. |
| **Proyecto vigente** | Activo y hoy cae entre `inicio` y `fin_estimado`, los dos incluidos. |
| **Proyecto por iniciar** | Activo e `inicio` posterior a hoy. |
| **Fin estimado vencido** | Activo y `fin_estimado` anterior a hoy (PR-06). |
| **Proyecto asignable** | Activo y `fin_estimado` igual o posterior a hoy: vigente o por iniciar. Es lo que se ofrece al asignar trabajadores. |
| **Asignación activa** | Renglón de `asignacion_proyecto` con `terminada_en` vacío. |

| ID | Regla | Origen |
|---|---|---|
| PR-01 | **Alta del proyecto.** Solo quien tiene `proyectos.administrar` (de inicio, el Administrador) da de alta un proyecto con: clave (única; de 2 a 20 caracteres, letras sin acento, números y guion; el servidor la pasa a mayúsculas), nombre (1 a 100 caracteres), almacén, inicio y fin estimado. El almacén puede ser **cualquier almacén activo**: lo normal es uno de tercer nivel (tipo `PROYECTO`), pero se permite Contratistas o Kepler para personal general (por ejemplo, «Operación general Contratistas»). En un almacén `CERRADO` no se crea (409 `ALMACEN_CERRADO`). El proyecto nace `ACTIVO`. Los proyectos no se borran. | Decisión del usuario (8 oct 2026); Propuesta (formato de la clave) |
| PR-02 | **Estados y fechas.** Un proyecto está `ACTIVO` o `CERRADO`. El `fin_estimado` no puede ser anterior al `inicio` (422 `DATOS_INVALIDOS`, regla PR-02). Vigente, por iniciar, fin estimado vencido y asignable se **calculan** con la fecha de hoy; no se guardan. | Decisión del usuario (8 oct 2026) |
| PR-03 | **Editar y extender.** Quien tiene `proyectos.administrar` cambia el nombre y las fechas (extender o acortar el fin estimado). La clave y el almacén solo se cambian mientras ningún vale use el proyecto (409 `PROYECTO_CON_VALES`), porque cambiarían reportes ya vistos. Un proyecto `CERRADO` no se edita (409 `PROYECTO_CERRADO`): primero se reabre. Cada cambio queda en el registro de cambios con el antes y el después. | Propuesta |
| PR-04 | **Cerrar.** Quien tiene `proyectos.administrar` cierra un proyecto con un motivo obligatorio: pasa a `CERRADO` y guarda `cerrado_en` y `motivo_cierre`. En la misma transacción **terminan todas sus asignaciones activas** (`terminada_en`, `terminada_por` y `fin` = hoy). El contrato del trabajador **no cambia**: sigue vigente si lo era. Lo que los trabajadores tienen en resguardo sigue siendo su pendiente (CP-05) y no impide cerrar. Los vales ya hechos conservan su proyecto. | Decisión del usuario (8 oct 2026) |
| PR-05 | **Reabrir.** Quien tiene `proyectos.administrar` reabre un proyecto cerrado: vuelve a `ACTIVO` y se limpian `cerrado_en` y `motivo_cierre` (el registro de cambios conserva el cierre anterior). Si su fin estimado ya pasó, la reapertura exige uno nuevo igual o posterior a hoy (422 `DATOS_INVALIDOS`). Su almacén debe estar activo (409 `ALMACEN_CERRADO`). Las asignaciones terminadas **no** se restauran: RH vuelve a asignar. | Propuesta |
| PR-06 | **Fin estimado vencido.** Un proyecto activo que pasa su fin estimado sin cerrarse **sigue operando**: sus asignaciones siguen activas y las entregas lo siguen tomando (PR-08). Aparece marcado «Fin estimado vencido» en `/proyectos` y en el Inicio del Administrador, para que lo extienda o lo cierre. No se ofrece para asignaciones nuevas hasta que se extienda (no es asignable). El sistema nunca lo cierra solo. | Decisión del usuario (8 oct 2026) |
| PR-07 | **Quién ve los proyectos.** Con `proyectos.ver`, los proyectos cuyo almacén está en el conjunto del usuario (AC-37); con `almacenes.todos`, todos. Quien tiene `proyectos.asignar` (RH, que no tiene almacén) ve **todos** los proyectos, solo con sus datos generales (clave, nombre, almacén, fechas, estado y número de asignados), para poder asignar; no ve consumo ni valor. | Propuesta |
| PR-08 | **Proyecto de la entrega, caso normal.** Si el trabajador tiene **una** asignación activa a un proyecto activo, la ENTREGA toma ese proyecto sola y lo guarda en `vale.proyecto_id`. El almacenista no elige nada; la pantalla solo muestra «Proyecto: …». Cuenta todo proyecto activo: vigente, por iniciar (el EPP que se entrega al contratar cuenta para su proyecto) o con fin estimado vencido (PR-06). | Decisión del usuario (8 oct 2026) |
| PR-09 | **Trabajador con varios proyectos.** Si tiene **más de una** asignación activa a proyectos activos, la evaluación devuelve `proyectos_del_trabajador` y `pide_proyecto: true`, con el motivo del vale PR-09 en amarillo («Elige para qué proyecto es esta entrega»). La interfaz muestra un selector con la asignación `principal` preseleccionada y a la vista. Confirmar sin `proyecto_id` responde 422 `PROYECTO_REQUERIDO`; un `proyecto_id` que no es de una asignación activa del trabajador (o de un proyecto cerrado) responde 422 `PROYECTO_INVALIDO`. | Decisión del usuario (8 oct 2026) |
| PR-10 | **Entrega sin proyecto.** Si el trabajador es vigente pero no tiene ninguna asignación activa a un proyecto activo, la entrega **sí se hace**: la evaluación trae el motivo del vale PR-10 en amarillo («Este trabajador no tiene proyecto activo») con `pide_observacion: true`. Confirmar sin observación responde 422 `DATOS_INVALIDOS` (`detalles: [{campo: "observacion", regla: "PR-10"}]`). El vale queda con `proyecto_id` vacío, entra a la lista de revisión (RG-14) y cuenta como «Sin proyecto» en los reportes. | Decisión del usuario (8 oct 2026) |
| PR-11 | **Proyecto en el alta y en el reingreso.** El alta de un trabajador pide `trabajadores.administrar` **y** `proyectos.asignar`, y un `proyecto_id` asignable, obligatorio (422 `PROYECTO_REQUERIDO` si falta; 422 `PROYECTO_INVALIDO` si está cerrado, vencido o no existe). Se crea la asignación como `principal` en la misma transacción que el trabajador. Si no hay ningún proyecto asignable, el alta lo explica: «No hay proyectos abiertos. Pide al Administrador que dé de alta el proyecto antes de registrar a sus trabajadores.» El reingreso (T-02) también pide proyecto cuando el trabajador no tiene una asignación activa a un proyecto asignable; si la tiene, se propone esa y el proyecto es opcional. `periodo_contrato.area_obra` se llena con el nombre del proyecto, para que lo que hoy lo lee siga funcionando. | Decisión del usuario (8 oct 2026) |
| PR-12 | **Almacén de tercer nivel sin proyectos.** Un almacén tipo `PROYECTO`, activo, sin ningún proyecto `ACTIVO` (los de fin vencido cuentan como activos) muestra el aviso «Sin proyectos activos: considera inactivarlo» en `/almacenes` y en el Inicio del Administrador (`almacenes_sin_proyecto`). El sistema **nunca** lo inactiva solo. Kepler y Contratistas (tipos `CENTRAL` y `SUBALMACEN`) no generan este aviso aunque no tengan proyectos. | Decisión del usuario (8 oct 2026) |
| PR-13 | **Casos especiales de asignación.** Con `proyectos.asignar` se puede: **agregar** un segundo proyecto (queda no principal, salvo que se pida); **terminar** una asignación (`terminada_en`, `terminada_por`, `fin` = hoy); y **cambiar** de proyecto, que termina una asignación y abre otra en una sola transacción (la nueva hereda `principal`). Lo que el trabajador tiene en resguardo **sigue siendo suyo** en cualquier caso. Un trabajador no tiene dos asignaciones activas al mismo proyecto (409 `ASIGNACION_REPETIDA`) ni dos principales activas. Si termina su última asignación, queda «Sin proyecto» y la respuesta lo dice. Las asignaciones no se borran. | Decisión del usuario (8 oct 2026); Propuesta (principal) |
| PR-14 | **El proyecto es del trabajador, no del almacén que entrega.** Contratistas puede entregar a un trabajador del proyecto de Midrex: el vale es de Contratistas (`vale.almacen_id`) y el consumo es del proyecto de Midrex (`vale.proyecto_id`). `vale.proyecto_id` se escribe al insertar y no cambia nunca, aunque el trabajador cambie de proyecto o el proyecto se cierre. La CANCELACION hereda el proyecto del vale original, para que el uso se descuente del mismo proyecto. DEVOLUCION, TRASPASO, RECEPCION, ENTRADA y NO_ADEUDO no llevan proyecto (un `proyecto_id` en su cuerpo es 422). | Decisión del usuario (8 oct 2026) |

### B. Alcance por un conjunto de almacenes (AC)

| ID | Regla | Origen |
|---|---|---|
| AC-36 | **Conjunto y almacén activo.** Cada usuario tiene un **conjunto** de almacenes (`usuario_almacen`); lo normal es uno. `usuario.almacen_id` se conserva como el **almacén activo** y siempre pertenece al conjunto (vacío solo si el conjunto está vacío). Quien tiene `almacenes.todos` no necesita conjunto y sigue igual: ve todos y elige almacén en cada operación. Sin conjunto y sin `almacenes.todos`, el usuario no ve ni opera nada de ningún almacén (como hoy RG-07). El conjunto, el almacén activo, el rol y los permisos se leen de la base en cada petición (AC-23). | Decisión del usuario (8 oct 2026) |
| AC-37 | **Las lecturas abarcan todo el conjunto.** Tablero, valor del inventario, uso por proyecto, reportes, bitácora, seguimiento de piezas, resguardo, deudores, vales, existencias, proyectos, autorizaciones pendientes, inspecciones y traspasos por recibir muestran lo de **todos** los almacenes del conjunto. Un `almacen_id` del conjunto filtra a ese almacén; uno fuera del conjunto se trata como hoy se trata un almacén ajeno (se ignora en el tablero, 404 en un detalle). La regla de atribución de AC-06 no cambia: una pieza es del almacén donde está; la que tiene un trabajador, del almacén de su última entrega. | Decisión del usuario (8 oct 2026) |
| AC-38 | **Las escrituras se hacen en el almacén activo.** Entregas, devoluciones, traspasos (origen), recepciones (destino), no adeudo, inspecciones, marcar estado de pieza y solicitudes de compra nuevas se hacen en el almacén activo. Para recibir un traspaso que va a otro almacén del conjunto, o entregar desde otro, primero se cambia el almacén activo. La entrada de proveedor sigue yendo a Kepler (EK-01): quien no tiene `almacenes.todos` da entrada solo si su almacén activo es Kepler. | Decisión del usuario (8 oct 2026) |
| AC-39 | **Cambiar el almacén activo.** `PUT /api/sesion/almacen` cambia el almacén activo **solo a uno del conjunto** y activo (403 `ALMACEN_NO_ASIGNADO`; 409 `ALMACEN_CERRADO`). Es del usuario, no del dispositivo: aplica desde la siguiente petición en todos sus dispositivos. Un vale capturado en el almacén anterior se rechaza al confirmar con 409 `ALMACEN_CAMBIO` y su borrador se conserva (igual que AC-13). Queda en el registro de cambios con el almacén anterior y el nuevo. Con un solo almacén en el conjunto la interfaz no muestra el selector. | Decisión del usuario (8 oct 2026); Propuesta (por usuario) |
| AC-40 | **Autorizaciones por conjunto.** Una solicitud de autorización sigue siendo del almacén en que se pidió. La ven y la resuelven quienes tienen `autorizaciones.resolver` y ese almacén **en su conjunto**, aunque no sea su almacén activo (y quien tiene `almacenes.todos`). Con PIN en el mostrador, el supervisor que da su usuario y PIN también debe tener el almacén de la solicitud en su conjunto. A-05 no cambia. | Decisión del usuario (8 oct 2026) |
| AC-41 | **Asignar el conjunto.** `PUT /api/usuarios/{id}/almacenes` deja el conjunto exactamente como se manda, con su almacén activo. Con `acceso.usuarios`, cualquier almacén activo. Con `almacenes.asignar_personal` (sin `acceso.usuarios`), solo puede agregar o quitar almacenes **de su propio conjunto** a quien trabaja en un almacén, y no toca los almacenes ajenos de esa persona (403). Nadie se amplía su propio conjunto con `almacenes.asignar_personal`. Si se quita el almacén activo, el activo pasa al primero que quede por nombre (o queda vacío). Inactivar un almacén que está en el conjunto de algún usuario activo bloquea con `CON_USUARIOS` (AL-03). `PATCH /api/usuarios/{id}/almacen` se conserva para el caso normal: deja el conjunto con ese único almacén. Cada cambio queda en el registro de cambios. | Decisión del usuario (8 oct 2026); Propuesta (detalle) |

### C. Inicio del supervisor (TB)

| ID | Regla | Origen |
|---|---|---|
| TB-04 | **Valor del inventario de sus almacenes.** El Inicio del supervisor muestra el valor del inventario de su conjunto, **en pesos y en unidades**: en almacén, en resguardo de trabajadores y total. Los pesos piden `reportes.valor_inventario`, que el Supervisor recibe de inicio (D-05). Solo totales y su reparto por categoría y por almacén; **nunca** el costo unitario de un artículo (RG-12). Un artículo sin costo no suma pesos y se cuenta aparte (VI-04 del código). Sin `reportes.valor_inventario` se ven solo las unidades. | Decisión del usuario (8 oct 2026) |
| TB-05 | **Uso por proyecto.** `GET /api/tablero/proyectos` da, por cada proyecto del alcance: **retornables en resguardo hoy** (unidades y valor) y **consumibles consumidos en el rango** (unidades y valor), netos de cancelaciones; trabajadores asignados (asignaciones activas de trabajadores en estado Activo); clave, nombre, almacén, fechas y situación. Agrega un renglón «Sin proyecto» con las entregas sin proyecto de los almacenes del alcance. El valor es la cantidad por el costo actual del catálogo (los movimientos no guardan costo) y sale solo con `reportes.valor_inventario`. Se muestra como **tabla con barras horizontales**, no como gráfica nueva. | Plática 8 oct 2026; Decisión del usuario (8 oct 2026) |
| TB-06 | **El uso se cuenta por el almacén del proyecto.** Un proyecto entra al alcance si **su almacén** está en el conjunto del usuario, sin importar qué almacén hizo la entrega (D-13, PR-14). Lo que un trabajador tiene en resguardo cuenta para el proyecto de la **última entrega** que se le hizo de ese artículo (en piezas, de esa pieza), igual que una pieza es del almacén de su última entrega (AC-06). «Sin proyecto» se cuenta por el almacén del vale. | Decisión del usuario (8 oct 2026); Propuesta (atribución del resguardo) |
| TB-07 | **Selectores del Inicio.** Con más de un almacén en el alcance, el Inicio muestra un selector «Todos mis almacenes» o uno; y la tabla de uso tiene un selector de proyecto (todos o uno; con uno, agrega su reparto por categoría). Ninguno de los dos cambia el almacén activo (como TB-01): se rotulan «Viendo: …». Con un solo almacén no hay selector de almacén; con un solo proyecto no hay selector de proyecto. | Decisión del usuario (8 oct 2026) |
| TB-08 | **Tarjetas nuevas.** `GET /api/tablero/resumen` agrega `almacenes_sin_proyecto` (lista de PR-12; solo con `almacenes.administrar`, `null` sin él) y `proyectos_por_vencer` (proyectos activos del alcance cuyo fin estimado cae en los próximos 7 días, hoy incluido, o ya pasó; con `proyectos.ver`, `null` sin él). Al tocarlas, llevan a `/almacenes` y a `/proyectos` ya filtrados. | Decisión del usuario (8 oct 2026); Propuesta (7 días) |

### D. Acción por acción

Cada acción dice quién la hace, qué toca, qué valida el servidor, qué responde y qué ve la persona.

#### D.1 Dar de alta un proyecto

- **Quién:** Administrador (`proyectos.administrar`). Pantalla `/proyectos`, primero computadora (D-20).
- **Qué toca:** inserta un `proyecto` y un renglón de auditoría `proyecto.crear`.
- **Valida:** permiso; clave con formato y única (409 `CLAVE_REPETIDA`); nombre; almacén que existe (404) y está activo (409 `ALMACEN_CERRADO`); `fin_estimado >= inicio` (422 `DATOS_INVALIDOS`, PR-02). Si el almacén no es de tipo `PROYECTO`, no es error: la respuesta trae `aviso: "Este proyecto queda en Contratistas: úsalo para personal general."` (PR-01).
- **Responde:** 201 con la ficha del proyecto (abajo, sección «Cambios de datos o API»).
- **Ve:** el proyecto en la lista con su situación («Por iniciar», «Vigente»). El formulario ofrece primero los almacenes de tercer nivel y, al final, Contratistas y Kepler con la nota «para personal general».

#### D.2 Editar o extender un proyecto

- **Quién:** Administrador. Desde la ficha del proyecto o desde el aviso «Fin estimado vencido» (botón «Extender»).
- **Qué toca:** actualiza `proyecto`; auditoría `proyecto.editar` con el antes y el después.
- **Valida:** PR-02 y PR-03 (clave y almacén solo sin vales: 409 `PROYECTO_CON_VALES`; cerrado: 409 `PROYECTO_CERRADO`). Acortar el fin estimado a una fecha pasada se permite: el proyecto queda con fin vencido al instante.
- **Responde:** 200 con la ficha.
- **Ve:** la situación recalculada. Si extendió un vencido, desaparece de `proyectos_por_vencer` y vuelve a ser asignable.

#### D.3 Cerrar un proyecto

- **Quién:** Administrador.
- **Qué toca:** `proyecto` (estado, `cerrado_en`, `motivo_cierre`) y todas sus asignaciones activas (`terminada_en`, `terminada_por`, `fin`); auditoría `proyecto.cerrar` con cuántas asignaciones terminó. No toca contratos, vales ni existencias.
- **Valida:** permiso; motivo de 1 a 500 caracteres (422); que esté `ACTIVO` (409 `CONFLICTO` si ya estaba cerrado). Nada lo bloquea: ni resguardo pendiente ni traspasos (los traspasos son del almacén, no del proyecto).
- **Responde:** 200 con la ficha y `asignaciones_terminadas` y `trabajadores_sin_proyecto` (cuántos quedaron sin ninguna asignación activa).
- **Ve:** antes de confirmar, una ventana con el nombre, cuántos trabajadores pierden la asignación, cuántos quedarán sin proyecto y cuántas unidades siguen en resguardo de su gente: «Lo que tienen en resguardo sigue siendo su pendiente.» Si era el último proyecto activo de un almacén de tercer nivel, aparece el aviso de PR-12.

#### D.4 Reabrir un proyecto

- **Quién:** Administrador.
- **Qué toca:** `proyecto`; auditoría `proyecto.reabrir`.
- **Valida:** PR-05 (fin estimado nuevo si el anterior ya pasó; almacén activo).
- **Responde:** 200 con la ficha.
- **Ve:** el aviso «Las asignaciones no se restauran. RH debe volver a asignar a los trabajadores.»

#### D.5 Dar de alta a un trabajador con su proyecto

- **Quién:** RH (`trabajadores.administrar` y `proyectos.asignar`). Pantalla `/trabajadores/nuevo`.
- **Qué toca:** `trabajador`, `periodo_contrato` (con `area_obra` = nombre del proyecto) y `asignacion_proyecto` (`principal = true`, `inicio` = hoy o el inicio del contrato si es posterior), en una sola transacción.
- **Valida:** lo de hoy (T-01 a T-10) más PR-11: los dos permisos (403 `SIN_PERMISO` si falta `proyectos.asignar`); `proyecto_id` presente (422 `PROYECTO_REQUERIDO`) y asignable (422 `PROYECTO_INVALIDO`).
- **Responde:** 201 con la ficha, que ahora trae `proyectos` (sus asignaciones activas).
- **Ve:** en el formulario, el campo «Área u obra» se reemplaza por **«Proyecto»**: una lista de los proyectos asignables, agrupados por almacén y con sus fechas. Si solo hay uno, aparece ya elegido. Si no hay ninguno, el formulario no se puede guardar y dice que primero se dé de alta un proyecto.

#### D.6 Reingresar o extender el contrato

- **Quién:** RH. `POST /api/trabajadores/{id}/periodos`.
- **Qué toca:** el periodo nuevo y, si cambia el proyecto, termina la asignación anterior y abre la nueva (PR-13).
- **Valida:** PR-11: si no tiene asignación activa a un proyecto asignable, `proyecto_id` es obligatorio. Si la tiene, es opcional; si viene uno distinto, es un cambio de proyecto.
- **Responde:** 201 con la ficha.
- **Ve:** el proyecto de su asignación anterior propuesto si sigue abierto; si ya cerró, la lista para elegir otro.

#### D.7 Agregar un segundo proyecto, cambiar de proyecto o terminar una asignación

- **Quién:** RH (`proyectos.asignar`). Desde la ficha del trabajador, sección «Proyectos».
- **Qué toca:** `asignacion_proyecto` (inserta, o termina una y abre otra); auditoría `asignacion.crear` y `asignacion.terminar`.
- **Valida:** PR-13: proyecto asignable; sin asignación activa repetida al mismo proyecto (409 `ASIGNACION_REPETIDA`); a lo más una principal activa; el trabajador no está Inactivo (409). El servicio bloquea la fila del trabajador mientras asigna, para que dos asignaciones simultáneas no dejen dos principales.
- **Responde:** 201 con las asignaciones del trabajador; al terminar, 200 con `queda_sin_proyecto: true` si era la última.
- **Ve:** en el caso normal, un solo renglón «Proyecto: …» con el botón **«Cambiar de proyecto»**. El botón «Agregar otro proyecto» queda en un menú secundario (caso especial). Al cambiar: «Lo que tiene en resguardo sigue siendo suyo.»

#### D.8 Entregar

- **Quién:** almacenista o supervisor (`entregas.crear`), en su almacén activo.
- **Qué toca:** lo de hoy, más `vale.proyecto_id` al insertar.
- **Valida:** al evaluar, PR-08, PR-09 o PR-10 (motivos del vale). Al confirmar, el servidor **vuelve a evaluar** (RG-08): si entre la evaluación y la confirmación el proyecto se cerró o la asignación cambió, responde 409 `VALE_CAMBIO` con el motivo nuevo y no guarda; el borrador se conserva.
- **Responde:** la evaluación trae `proyecto` (el que se tomará o `null`), `proyectos_del_trabajador` y `pide_proyecto`.
- **Ve:** caso normal, una línea bajo la foto del trabajador: «Proyecto: Mantenimiento Midrex (Midrex)». Varios: un selector con la principal ya elegida. Ninguno: aviso amarillo y la caja de observación obligatoria. El comprobante del vale imprime el nombre del proyecto donde hoy imprime «Área u obra» (E-24).

#### D.9 Cancelar una entrega

- **Quién:** quien hoy puede cancelar (K-01).
- **Qué toca:** el vale CANCELACION copia `proyecto_id` del original (PR-14).
- **Valida:** lo de hoy (K-03, K-04). Se puede cancelar aunque el proyecto ya esté cerrado.
- **Ve:** el uso del proyecto baja en el Inicio del supervisor en la siguiente consulta.

#### D.10 Devolver

- **Quién y qué:** lo de hoy. No lleva proyecto (PR-14). El resguardo del trabajador baja y, con él, el resguardo atribuido al proyecto de la última entrega de ese artículo (TB-06).

#### D.11 Asignar el conjunto de almacenes de un usuario

- **Quién:** con `acceso.usuarios` (Administrador) en `/usuarios`; con `almacenes.asignar_personal` (Supervisor) en `/personal`, solo con sus almacenes.
- **Qué toca:** `usuario_almacen` y, si hace falta, `usuario.almacen_id`; auditoría `usuario.almacenes` con el conjunto anterior y el nuevo.
- **Valida:** AC-41; almacenes que existen y están activos (422); el almacén activo dentro del conjunto (422); no a quien tiene `almacenes.todos` ni a RH (422, como hoy AC-12); usuario activo (422).
- **Responde:** 200 con el renglón de personal, que ahora trae `almacenes` y `almacen_activo`.
- **Ve:** caso normal, un solo selector «Almacén» (como hoy). «Agregar otro almacén» aparece como opción secundaria y convierte el campo en una lista con «Activo» marcado.

#### D.12 Cambiar el almacén activo

- **Quién:** cualquier usuario con dos o más almacenes en su conjunto.
- **Qué toca:** `usuario.almacen_id`; auditoría `usuario.almacen_activo`.
- **Valida:** AC-39.
- **Responde:** 200 con la sesión (`GET /api/sesion`).
- **Ve:** un selector en la barra superior, «Operando en: Midrex ▾». Al cambiar, la pantalla de operación se recarga y, si había un borrador en el almacén anterior, avisa: «Tienes una entrega sin terminar en Midrex. Regresa a Midrex para terminarla.»

#### D.13 Resolver una autorización

- **Quién:** supervisor con el almacén de la solicitud en su conjunto (AC-40).
- **Ve:** la lista de pendientes trae las de todos sus almacenes, con el nombre del almacén en cada una cuando tiene más de uno. Resolver no cambia su almacén activo.

#### D.14 Inactivar un almacén

- **Quién:** Administrador (`almacenes.administrar`).
- **Valida:** AL-03 con dos ajustes: `CON_PROYECTOS_ACTIVOS` (tiene proyectos `ACTIVO`; el detalle trae hasta 20 `{id, clave, nombre, fin_estimado}`) y `CON_USUARIOS` cuenta a los usuarios activos que lo tienen **en su conjunto**, no solo como activo. Orden de los bloqueos: `CON_TRASPASOS_EN_TRANSITO`, `CON_EXISTENCIAS`, `CON_HIJOS_ACTIVOS`, `CON_PROYECTOS_ACTIVOS`, `CON_USUARIOS`.
- **Ve:** el bloqueo con el enlace a `/proyectos?almacen_id=…` para cerrarlos.

#### D.15 Ver el Inicio

- **Supervisor** (`tablero.ver`, `proyectos.ver`, `reportes.valor_inventario`): arriba, «Lo que haces hoy» (como hoy); luego las tarjetas de siempre, la tarjeta **Valor del inventario** (pesos y unidades, TB-04) y **Proyectos por vencer** (TB-08); luego **Uso por proyecto** (TB-05); al final, «Lo más usado» (TB-02). En celular la tabla de uso se vuelve una lista de tarjetas, una por proyecto, con su barra.
- **Almacenista:** sin cambios, salvo que la línea del proyecto aparece en la entrega. No ve valor ni uso por proyecto (no tiene `reportes.valor_inventario`; `proyectos.ver` le sirve para ver los proyectos de su almacén en la ficha del trabajador).
- **Administrador:** lo de hoy, más las tarjetas **Almacenes sin proyectos** y **Proyectos por vencer**, y el uso por proyecto de todos los almacenes con selector.

### E. Pantallas

| Pantalla | Para quién | Qué cambia |
|---|---|---|
| `/proyectos` (nueva, grupo Administración, primero computadora) | `proyectos.ver`; editar con `proyectos.administrar` | Lista con clave, nombre, almacén, inicio, fin estimado, situación (Vigente, Por iniciar, Fin estimado vencido, Cerrado) y trabajadores asignados. Filtros: almacén, situación y búsqueda. Alta, edición, extender, cerrar y reabrir. Al abrir un proyecto: sus datos, sus trabajadores (enlace a `/trabajadores?proyecto_id=`) y, con `reportes.valor_inventario`, su uso. |
| `/trabajadores/nuevo` | RH | «Área u obra» pasa a «Proyecto» (D.5). |
| `/trabajadores/:id` (ficha) | `trabajadores.ver` | Sección «Proyectos»: la asignación activa (o «Sin proyecto») y el historial plegado. Botones de D.7 con `proyectos.asignar`. |
| `/trabajadores` | `trabajadores.ver` | Columna «Proyecto» y filtros «Proyecto» y «Sin proyecto». |
| `/entregar` | `entregas.crear` | Línea o selector de proyecto (D.8). |
| Inicio | según rol | D.15. |
| `/almacenes` | `almacenes.administrar` | Columna «Proyectos activos» y aviso PR-12. Bloqueo `CON_PROYECTOS_ACTIVOS`. |
| `/usuarios` y `/personal` | `acceso.usuarios` / `almacenes.asignar_personal` | Conjunto de almacenes (D.11). |
| Barra superior | quien tiene 2 o más almacenes | Selector del almacén activo (D.12). |

Todo texto que ve el usuario va en español llano: «proyecto», «almacén donde operas», «sin proyecto»; nunca «conjunto», «alcance» ni «asignación activa».

### F. Datos de prueba

El script de datos de prueba (repetible, AC-33) agrega:

- Un proyecto por almacén de tercer nivel: `MID-OCT26` «Mantenimiento Midrex octubre», `HYL-OCT26`, `LAM-OCT26` y `MIN-OCT26`, vigentes; y uno general en Contratistas, `CON-GENERAL` «Operación general Contratistas».
- Un proyecto con fin estimado vencido (PR-06) y uno que vence en 5 días (TB-08), para la demostración.
- Cada trabajador de prueba con una asignación principal. Para los casos especiales: un trabajador en dos proyectos (PR-09), uno vigente sin proyecto (PR-10) y un supervisor con Midrex y HYL en su conjunto (AC-36 a AC-40), con un usuario propio para no romper las pruebas que usan a los supervisores de siempre.
- Entregas de prueba con proyecto, una de ellas desde Contratistas a un trabajador del proyecto de Midrex (PR-14, TB-06), y una cancelada.

## Casos límite y situaciones que pueden darse

| # | Situación | Qué pasa | Reglas |
|---|---|---|---|
| 1 | El Administrador captura un fin estimado anterior al inicio. | 422 `DATOS_INVALIDOS` en el campo `fin_estimado`; no se guarda. | PR-02 |
| 2 | Alta de proyecto en un almacén `CERRADO`, o reabrir un proyecto cuyo almacén se cerró. | 409 `ALMACEN_CERRADO`. Primero se reactiva el almacén. | PR-01, PR-05 |
| 3 | Inactivar un almacén con proyectos activos. | 409 `CON_PROYECTOS_ACTIVOS` con la lista; se cierran primero. | AL-03 (ajustada) |
| 4 | Cerrar un proyecto mientras hay traspasos en tránsito hacia su almacén. | No aplica: el traspaso es del almacén, no del proyecto. El cierre procede y el traspaso sigue su curso. | PR-04 |
| 5 | Cerrar un proyecto con trabajadores que tienen herramienta en resguardo. | Se cierra. Cada uno conserva su pendiente (CP-05) y el resguardo sigue atribuido a ese proyecto en el Inicio hasta que se devuelva. | PR-04, TB-06 |
| 6 | El único proyecto de un trabajador se cierra mientras el almacenista tiene su entrega a medio capturar. | Al confirmar, el servidor revalida: 409 `VALE_CAMBIO` con el motivo PR-10. La pantalla reevalúa, muestra el aviso amarillo y pide observación; el borrador no se pierde. | PR-10, RG-08 |
| 7 | Dos personas de RH asignan al mismo trabajador al mismo proyecto a la vez. | Una gana; la otra recibe 409 `ASIGNACION_REPETIDA` (restricción única en la base). | PR-13 |
| 8 | Dos personas de RH asignan al mismo trabajador a dos proyectos distintos a la vez. | Las dos se guardan (caso especial válido). Solo una queda principal: el servicio bloquea al trabajador y la segunda entra como no principal. La siguiente entrega pedirá elegir (PR-09). | PR-13, PR-09 |
| 9 | A un supervisor le quitan un almacén de su conjunto mientras tiene solicitudes pendientes de ese almacén. | Desde la siguiente petición deja de verlas; si intenta resolver una, 404. Las siguen viendo los demás supervisores de ese almacén y el Administrador; si nadie responde, vencen a los 15 minutos como siempre. | AC-40, AC-41 |
| 10 | Le quitan a alguien su almacén activo. | El activo pasa al primero que quede (por nombre) o queda vacío. Un borrador en el almacén quitado se rechaza al confirmar (409 `ALMACEN_CAMBIO`). | AC-41, AC-39 |
| 11 | Un supervisor con dos almacenes cambia el activo en el celular mientras en la tableta tiene una entrega a medias. | La tableta recibe 409 `ALMACEN_CAMBIO` al confirmar; el borrador se conserva y la pantalla ofrece volver al almacén anterior. | AC-39 |
| 12 | Contratistas entrega EPP a un trabajador del proyecto de Midrex. | El vale es de Contratistas (folio `CON-…`, bitácora y «Lo más usado» de Contratistas); el uso por proyecto lo ve el supervisor de Midrex. En ninguna vista se cuenta dos veces. | PR-14, TB-06 |
| 13 | Un trabajador está en un proyecto de Midrex y en otro de HYL. | Cada entrega pide elegir; cada supervisor ve solo lo que se entregó para su proyecto. | PR-09, TB-06 |
| 14 | Un proyecto pasó su fin estimado y nadie lo ha cerrado. | Sigue operando y las entregas lo toman. No se ofrece para asignaciones nuevas. Aparece en «Proyectos por vencer» y marcado en `/proyectos`. | PR-06, TB-08 |
| 15 | Se entrega EPP a un trabajador cuyo proyecto todavía no empieza. | Cuenta para ese proyecto (está activo). Es el EPP «al contratar». | PR-08 |
| 16 | El Administrador reabre un proyecto. | Vuelve activo pero sin trabajadores; RH los asigna de nuevo. | PR-05 |
| 17 | Un trabajador recibe el vale de no adeudo y queda Inactivo con su asignación activa. | La asignación no se termina sola, pero no cuenta en «trabajadores asignados» y no permite entregas (E-02). Al reingresar, se propone ese proyecto si sigue abierto. | PR-11, TB-05 |
| 18 | El contrato del trabajador termina antes que el proyecto, o al revés. | Son independientes: sin contrato vigente no se entrega (E-02); sin proyecto activo se entrega con PR-10. | PR-10, T-07 |
| 19 | La interfaz manda un `proyecto_id` que no es del trabajador (pantalla vieja o manipulada). | 422 `PROYECTO_INVALIDO`, aunque tenga un solo proyecto. | PR-09 |
| 20 | Se cancela una entrega de un proyecto ya cerrado. | Se permite (K-01 a K-04); el vale de cancelación hereda el proyecto y el uso se descuenta. | PR-14 |
| 21 | Un trabajador cambia de proyecto con herramienta en resguardo. | Sigue siendo suya. En el Inicio, esa herramienta cuenta para el proyecto anterior hasta que la devuelva o le entreguen otra igual para el nuevo. | PR-13, TB-06 |
| 22 | El Administrador cambia el almacén de un proyecto que ya tiene vales. | 409 `PROYECTO_CON_VALES`. Para mover gente a otro almacén se crea un proyecto nuevo y se cambia su asignación. | PR-03 |
| 23 | Un almacén de tercer nivel recién creado aún no tiene proyecto. | Aparece en «Almacenes sin proyectos»; el aviso sugiere darle su proyecto o inactivarlo. | PR-12 |
| 24 | Un rol recibe `almacenes.todos`. | Sus usuarios dejan su almacén activo y su conjunto (como hoy RG-07); cada uno queda en el registro de cambios. | AC-36 |
| 25 | Un supervisor con `almacenes.asignar_personal` intenta darle a un almacenista un almacén que él no tiene. | 403. Solo el Administrador amplía conjuntos con almacenes ajenos. | AC-41 |
| 26 | Uso por proyecto con artículos sin costo. | Las unidades cuentan; los pesos no, y la tabla dice «N artículos sin costo». | TB-04, TB-05 |
| 27 | RH (sin almacén) busca un proyecto para asignar. | Ve todos los asignables, de cualquier almacén, sin consumo ni valor. | PR-07 |
| 28 | Un proyecto con el mismo nombre en dos almacenes. | Se permite; la clave los distingue y la lista muestra el almacén. | PR-01 |
| 29 | El almacenista cambia de turno y otro almacenista sigue con el mismo trabajador. | Nada cambia: el proyecto sale del trabajador, no del almacenista. | PR-08 |

## Fuera de alcance

- Presupuesto por proyecto, topes de gasto o alertas por gasto.
- Costo histórico: el valor usa el costo actual del catálogo; guardar el costo en cada movimiento queda fuera.
- Proyecto en devoluciones, traspasos y entradas.
- Reglas de dotación o límites por proyecto (siguen siendo por puesto y por artículo).
- Asignar trabajadores a proyectos por Excel.
- Que el sistema cierre proyectos o inactive almacenes solo.
- Almacén activo por dispositivo (ADR-012).
- Notificaciones por proyecto por vencer (se ve en pantalla; FEAT-014 cubre las notificaciones de despacho).
- Gráficas nuevas: el uso por proyecto es una tabla con barras (sección 6 del maestro).

## Criterios de aceptación

**Proyectos**
- Dado el Administrador, cuando da de alta `MID-OCT26` en Midrex con fin estimado anterior al inicio, entonces recibe 422 y no se guarda; con fechas válidas, aparece «Vigente» o «Por iniciar» (PR-01, PR-02).
- Dado un almacén cerrado, cuando el Administrador crea un proyecto en él, entonces recibe 409 `ALMACEN_CERRADO` (PR-01).
- Dado un supervisor, cuando llama `POST /api/proyectos`, entonces recibe 403 (PR-01).
- Dado el Administrador, cuando crea «Operación general Contratistas» en Contratistas, entonces se guarda con un aviso y no con error (PR-01).
- Dado un proyecto con vales, cuando el Administrador cambia su almacén, entonces recibe 409 `PROYECTO_CON_VALES` (PR-03).
- Dado un proyecto con 12 asignaciones activas, cuando el Administrador lo cierra con motivo, entonces queda `CERRADO`, las 12 asignaciones quedan terminadas, los contratos no cambian y el resguardo de esos trabajadores sigue como pendiente (PR-04).
- Dado un proyecto cerrado con fin estimado vencido, cuando se reabre sin fin nuevo, entonces 422; con un fin futuro, vuelve a `ACTIVO` sin asignaciones (PR-05).
- Dado un proyecto activo cuyo fin estimado fue ayer, entonces sigue tomándose en las entregas, aparece «Fin estimado vencido» y no se ofrece al asignar (PR-06).
- Dado un almacenista de Midrex, entonces ve los proyectos de Midrex y no los de HYL; y dado RH sin almacén, entonces ve los asignables de todos los almacenes sin consumo ni valor (PR-07).

**Entregas**
- Dado un trabajador con una sola asignación activa, cuando se evalúa una entrega, entonces trae `proyecto` lleno y `pide_proyecto: false`, y el vale confirmado guarda `proyecto_id` (PR-08).
- Dado un trabajador con dos asignaciones activas, cuando se confirma sin `proyecto_id`, entonces 422 `PROYECTO_REQUERIDO`; con uno ajeno, 422 `PROYECTO_INVALIDO`; con uno suyo, se guarda (PR-09).
- Dado un trabajador vigente sin proyecto activo, cuando se evalúa, entonces el vale trae el motivo amarillo PR-10 con `pide_observacion: true`; sin observación, 422; con ella, se guarda con `proyecto_id` vacío y entra a la lista de revisión (PR-10).
- Dada una entrega a medio capturar cuyo proyecto se cierra antes de confirmar, entonces el servidor responde 409 `VALE_CAMBIO` con el motivo PR-10 y no guarda (PR-10, RG-08).
- Dado Contratistas, cuando entrega a un trabajador del proyecto de Midrex, entonces `vale.almacen_id` es Contratistas y `vale.proyecto_id` es el proyecto de Midrex (PR-14).
- Dada una entrega con proyecto que se cancela, entonces el vale de cancelación lleva el mismo `proyecto_id` y el uso del proyecto baja (PR-14, TB-05).
- Dada una devolución con `proyecto_id` en el cuerpo, entonces 422 (PR-14).

**Asignación**
- Dado RH, cuando da de alta sin `proyecto_id`, entonces 422 `PROYECTO_REQUERIDO`; con uno vencido o cerrado, 422 `PROYECTO_INVALIDO`; con uno asignable, el trabajador queda con su asignación principal y `area_obra` igual al nombre del proyecto (PR-11).
- Dado que no hay proyectos asignables, cuando RH abre el alta, entonces ve que primero se dé de alta un proyecto (PR-11).
- Dado un rol con `trabajadores.administrar` sin `proyectos.asignar`, cuando da de alta, entonces 403 (PR-11).
- Dado un trabajador inactivo con su asignación terminada, cuando RH lo reingresa sin proyecto, entonces 422 `PROYECTO_REQUERIDO` (PR-11).
- Dado un trabajador en un proyecto, cuando RH lo cambia a otro, entonces la asignación anterior termina, la nueva queda principal y su resguardo no cambia (PR-13).
- Dadas dos asignaciones simultáneas al mismo proyecto, entonces una recibe 409 `ASIGNACION_REPETIDA`; dadas dos a proyectos distintos, entonces solo una queda principal (PR-13).

**Almacenes sin proyecto**
- Dado Midrex sin proyectos activos, entonces `/almacenes` y el Inicio del Administrador muestran «Sin proyectos activos: considera inactivarlo» y Midrex sigue `ACTIVO`; dado Contratistas sin proyectos, entonces no hay aviso (PR-12).
- Dado un almacén con proyectos activos, cuando se intenta inactivar, entonces 409 con el bloqueo `CON_PROYECTOS_ACTIVOS` (AL-03).

**Conjunto de almacenes**
- Dado un supervisor con un solo almacén, entonces el Inicio, el menú y las pantallas se ven exactamente como antes, sin selector de almacén (AC-36).
- Dado un supervisor con Midrex y HYL, cuando abre el tablero, reportes, bitácora o autorizaciones, entonces ve lo de los dos; y con `almacen_id` de HYL ve solo HYL; y con el de Laminador, se ignora o es 404 según el endpoint (AC-37).
- Dado ese supervisor con Midrex activo, cuando confirma una entrega, entonces el vale es de Midrex; y cuando intenta recibir un traspaso que va a HYL sin cambiar de almacén, entonces se rechaza (AC-38).
- Dado ese supervisor, cuando pide `PUT /api/sesion/almacen` con HYL, entonces su siguiente petición opera en HYL; con Laminador, 403 `ALMACEN_NO_ASIGNADO` (AC-39).
- Dado un borrador de entrega en Midrex, cuando el usuario cambia a HYL y lo confirma, entonces 409 `ALMACEN_CAMBIO` y el borrador se conserva (AC-39).
- Dada una solicitud de autorización de HYL, entonces la ve y la resuelve el supervisor con Midrex activo y HYL en su conjunto; y no la ve un supervisor solo de Midrex (AC-40).
- Dado un supervisor con `almacenes.asignar_personal`, cuando agrega un almacén que él no tiene al conjunto de otro, entonces 403; con uno suyo, se guarda (AC-41).
- Dado un almacén que está en el conjunto de un usuario activo (no como activo), cuando se intenta inactivar, entonces 409 `CON_USUARIOS` (AC-41).

**Inicio del supervisor**
- Dado un supervisor, entonces ve el valor de su conjunto en pesos y en unidades, y ninguna respuesta trae el costo unitario de un artículo; sin `reportes.valor_inventario`, solo unidades (TB-04).
- Dado un proyecto de Midrex con entregas desde Contratistas y desde Midrex, entonces su renglón suma las dos, y el supervisor de Contratistas no lo ve en el uso por proyecto (TB-05, TB-06).
- Dada una entrega cancelada en el rango, entonces no suma en el uso por proyecto (TB-05).
- La suma de los consumibles de todos los proyectos más «Sin proyecto», con alcance «todos», coincide con el consumo de consumibles del mismo rango (TB-02, TB-05).
- Dado un supervisor que elige otro almacén o un proyecto en el Inicio, entonces su almacén activo no cambia (TB-07).
- Dado el Administrador, entonces ve `almacenes_sin_proyecto`; dado un supervisor, entonces ese campo es `null`; y dado un proyecto que vence en 3 días, entonces aparece en `proyectos_por_vencer` (TB-08).

## Módulos relacionados conocidos

- `proyectos` (**nuevo**): `models.py` (`proyecto`, `asignacion_proyecto`), `repository.py`, `service.py`, `router.py`, `schemas.py`, `exceptions.py`, `datos_prueba.py`. Su `router.py` se monta en `main.py` al crearse (sección 5.2 del maestro). Expone a otros módulos un servicio de lectura: `proyectos_activos_del_trabajador(trabajador_id)`.
- `movimientos`: `tipos/entrega.py` (PR-08 a PR-10, `vale.proyecto_id`), `tipos/cancelacion.py` (hereda), `contexto.py`, `service.py`, `models.py`. Sigue siendo el único que escribe vales.
- `trabajadores`: alta y reingreso con `proyecto_id`; llama al servicio de `proyectos` para crear la asignación en la misma sesión y transacción (el service de trabajadores controla el commit).
- `acceso`: `usuario_almacen`, `alcance_del_usuario`, `PUT /api/sesion/almacen`, `PUT /api/usuarios/{id}/almacenes`, `permisos.py`, `datos_prueba.py`.
- `almacenes`: AL-03 (`CON_PROYECTOS_ACTIVOS`, `CON_USUARIOS` por conjunto) y el resumen con `proyectos_activos`.
- `consulta`: `service_tablero.py`, `service_valor.py`, `repository_valor.py` (TB-04 a TB-08), y todos los servicios que hoy aplican AC-06.
- `autorizaciones`, `inspecciones`, `solicitudes_compra`, `importacion`, `catalogo`: migran al alcance por conjunto.
- Frontend: `routes.ts` (`/proyectos`), `routes/inicio.tsx`, `routes/personas/trabajador-nuevo.tsx`, `trabajador-ficha.tsx`, `trabajadores.tsx`, `routes/operacion/entregar.tsx`, `routes/acceso/almacenes.tsx`, `usuarios.tsx`, `routes/supervision/personal.tsx`, `sesion/` (almacén activo y selector), `api/`.

## Cambios de datos o API esperados

### Datos (migración nueva)

Migración `0010_proyectos_y_conjunto_de_almacenes`, o el siguiente número libre si FEAT-015 o FEAT-014 entran antes (sección 7 del maestro). No pierde datos:

| Tabla o columna | Detalle |
|---|---|
| `proyecto` | `id`, `clave` (única, `uq_proyecto_clave`), `nombre` (100), `almacen_id` (FK), `inicio` (fecha), `fin_estimado` (fecha), `estado` (`ACTIVO`, `CERRADO`), `cerrado_en` (UTC), `motivo_cierre` (500), `creado_por` (FK usuario), `creado_en`. CHECK `fin_estimado >= inicio`. Índice por `(almacen_id, estado)`. |
| `asignacion_proyecto` | `id`, `trabajador_id`, `proyecto_id`, `inicio` (fecha), `fin` (fecha, vacía mientras está activa), `principal` (bool), `creado_por`, `creado_en`, `terminada_en` (UTC), `terminada_por`. Una asignación solo se actualiza una vez, para terminarla; nunca se borra. Restricciones con columnas generadas (el mismo patrón que `uq_almacen_un_central`): una activa por trabajador y proyecto (`uq_asignacion_proyecto_activa`) y una principal activa por trabajador (`uq_asignacion_proyecto_principal`). CHECK `fin >= inicio`. Índices por `(trabajador_id, terminada_en)` y `(proyecto_id, terminada_en)`. |
| `usuario_almacen` | Llave `(usuario_id, almacen_id)`, `asignado_por` (vacío en lo que crea la migración), `asignado_en`. Índice por `almacen_id`. La migración crea un renglón por cada usuario con `usuario.almacen_id`, así nadie pierde acceso. Si se puede, una llave foránea compuesta de `usuario(id, almacen_id)` a `usuario_almacen` garantiza en la base que el activo esté en el conjunto; si no, lo garantiza el servicio. |
| `vale.proyecto_id` | FK a `proyecto`, vacía por omisión. Índice por `(proyecto_id, tipo, creado_en)`. Los vales existentes quedan sin proyecto. |
| Permisos | `proyectos.ver` (Almacenista, Supervisor, RH), `proyectos.administrar` (Administrador), `proyectos.asignar` (RH y todo rol con `trabajadores.administrar`, para que nadie pierda el alta), y `reportes.valor_inventario` al Supervisor. El Administrador recibe todos. Dependencias: `proyectos.administrar` y `proyectos.asignar` requieren `proyectos.ver`. |

**Trabajadores que ya existen.** Quedan **sin asignación** («Sin proyecto») hasta que RH los asigne; la migración no inventa un proyecto. Ver la decisión abierta 1.

### API

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/proyectos?almacen_id=&situacion=&q=&asignables=` | `proyectos.ver` o `proyectos.asignar` (`requiere_alguno`) | Lista paginada en el alcance de PR-07. `situacion`: `VIGENTE`, `POR_INICIAR`, `FIN_VENCIDO`, `CERRADO`. `asignables=true` deja solo los asignables (lo usa el alta). |
| `POST /api/proyectos` | `proyectos.administrar` | Alta (PR-01). Cuerpo `{clave, nombre, almacen_id, inicio, fin_estimado}`. 201 con la ficha. Errores: 409 `CLAVE_REPETIDA`, 409 `ALMACEN_CERRADO`, 422 `DATOS_INVALIDOS`, 404 `NO_ENCONTRADO` (almacén). |
| `GET /api/proyectos/{id}` | `proyectos.ver` o `proyectos.asignar` | Ficha. Fuera del alcance, 404. |
| `PATCH /api/proyectos/{id}` | `proyectos.administrar` | `{nombre?, inicio?, fin_estimado?, clave?, almacen_id?}` (PR-03). 409 `PROYECTO_CERRADO`, 409 `PROYECTO_CON_VALES`. |
| `POST /api/proyectos/{id}/cierre` | `proyectos.administrar` | `{motivo}` (PR-04). 200 con la ficha más `asignaciones_terminadas` y `trabajadores_sin_proyecto`. 409 `CONFLICTO` si ya estaba cerrado. |
| `POST /api/proyectos/{id}/reapertura` | `proyectos.administrar` | `{fin_estimado?, motivo?}` (PR-05). 409 `CONFLICTO` si ya estaba activo; 409 `ALMACEN_CERRADO`; 422 si falta el fin nuevo. |
| `GET /api/trabajadores/{id}/proyectos` | `trabajadores.ver` | Asignaciones activas y terminadas del trabajador, la más reciente primero. |
| `POST /api/trabajadores/{id}/proyectos` | `proyectos.asignar` | `{proyecto_id, principal?, inicio?, reemplaza_asignacion_id?}`. Con `reemplaza_asignacion_id` es un cambio de proyecto (PR-13). 201 con las asignaciones. 409 `ASIGNACION_REPETIDA`; 422 `PROYECTO_INVALIDO`. |
| `POST /api/trabajadores/{id}/proyectos/{asignacion_id}/termino` | `proyectos.asignar` | Termina una asignación. 200 con las asignaciones y `queda_sin_proyecto`. 409 `CONFLICTO` si ya estaba terminada. |
| `POST /api/trabajadores` | `trabajadores.administrar` (y `proyectos.asignar`, en el servicio) | Acepta `proyecto_id`, obligatorio (PR-11). `area_obra` deja de pedirse: si llega, se ignora y se usa el nombre del proyecto. |
| `POST /api/trabajadores/{id}/periodos` | `trabajadores.administrar` | Acepta `proyecto_id` (PR-11). |
| `GET /api/trabajadores` y `GET /api/trabajadores/{id}` | `trabajadores.ver` | Cada trabajador trae `proyectos` (asignaciones activas: `{asignacion_id, proyecto: {id, clave, nombre, almacen}, principal}`). La lista acepta los filtros `proyecto_id` y `sin_proyecto=true`. |
| `POST /api/vales/evaluar` y `POST /api/vales` (ENTREGA) | `entregas.crear` | Aceptan `proyecto_id`. La evaluación trae `proyecto`, `proyectos_del_trabajador` y `pide_proyecto`, y los motivos del vale PR-09 o PR-10. Errores al confirmar: 422 `PROYECTO_REQUERIDO`, 422 `PROYECTO_INVALIDO`, 422 `DATOS_INVALIDOS` (observación de PR-10), 409 `VALE_CAMBIO`. El detalle del vale trae `proyecto`. |
| `PUT /api/usuarios/{id}/almacenes` | `acceso.usuarios` o `almacenes.asignar_personal` (`requiere_alguno`; el límite de AC-41 se aplica en el servicio) | `{almacenes: [ids], almacen_activo_id}`. 200 con el renglón de personal. |
| `PATCH /api/usuarios/{id}/almacen` | `almacenes.asignar_personal` | Sin cambio de forma: deja el conjunto con ese único almacén (o vacío con `null`). |
| `PUT /api/sesion/almacen` | Sesión | `{almacen_id}`. 200 con la sesión. 403 `ALMACEN_NO_ASIGNADO`, 409 `ALMACEN_CERRADO`; 422 para quien tiene `almacenes.todos` (elige en cada operación). |
| `GET /api/sesion` y `POST /api/sesion` | Sesión | Agregan `almacenes` (el conjunto) y `almacen_activo`. `almacen` se conserva igual a `almacen_activo` para no romper la interfaz actual. |
| `GET /api/personal` y `GET /api/usuarios` | sin cambio | Cada renglón trae `almacenes`; `almacen_id` filtra por pertenecer al conjunto. |
| `GET /api/almacenes?resumen=true` | `almacenes.administrar` | El resumen agrega `proyectos_activos` y `aviso_sin_proyecto` (PR-12); `usuarios` cuenta a quienes lo tienen en su conjunto. |
| `GET /api/tablero/resumen` | `tablero.ver` | `alcance` agrega `almacenes` (los del conjunto) y `nombre` dice «Tus 2 almacenes» cuando ve varios; agrega `almacenes_sin_proyecto` y `proyectos_por_vencer` (TB-08). |
| `GET /api/tablero/valor` | `reportes.valor_inventario` | Alcance por conjunto; agrega `unidades_en_almacen`, `unidades_en_resguardo` y `unidades_total` (TB-04). |
| `GET /api/tablero/proyectos?desde=&hasta=&almacen_id=&proyecto_id=` | `tablero.ver` y `proyectos.ver` | Uso por proyecto (TB-05 a TB-07). Forma abajo. |

Forma de `GET /api/tablero/proyectos` (sin costos unitarios; `valor` en `null` sin `reportes.valor_inventario`):

```json
{
  "alcance": { "almacenes": [{ "id": "01a1…", "clave": "MID", "nombre": "Midrex" }], "es_todos": false, "puede_elegir": false },
  "rango": { "desde": "2026-10-01", "hasta": "2026-10-08" },
  "proyectos": [
    {
      "id": "01a1…", "clave": "MID-OCT26", "nombre": "Mantenimiento Midrex octubre",
      "almacen": { "id": "01a1…", "clave": "MID", "nombre": "Midrex" },
      "inicio": "2026-10-01", "fin_estimado": "2026-11-15", "estado": "ACTIVO", "situacion": "VIGENTE",
      "trabajadores_asignados": 38,
      "retornables_en_resguardo": { "unidades": 112, "valor": "184500.00" },
      "consumibles_consumidos": { "unidades": 640, "valor": "21800.00" },
      "total": { "unidades": 752, "valor": "206300.00" },
      "articulos_sin_costo": 2,
      "por_categoria": null
    }
  ],
  "sin_proyecto": { "retornables_en_resguardo": { "unidades": 4, "valor": "3200.00" }, "consumibles_consumidos": { "unidades": 18, "valor": "540.00" } },
  "generado_en": "2026-10-08T16:20:00Z"
}
```

`por_categoria` solo viene cuando se pide un `proyecto_id` (hasta 6 categorías y «Otras», como el valor del inventario). Los proyectos se ordenan por `total.valor` (o por unidades sin el permiso). Se incluyen los cerrados que tienen resguardo pendiente o consumo en el rango.

## Restricciones y compatibilidad

- Las reglas viven en el servidor; la interfaz muestra lo que el servidor evalúa (proyecto tomado, selector, aviso).
- Solo `movimientos` escribe vales: `vale.proyecto_id` se escribe ahí. `proyectos` escribe proyectos y asignaciones; `trabajadores` lo llama dentro de su transacción en el alta.
- Los vales y movimientos no se actualizan ni se borran; `vale.proyecto_id` es inmutable.
- **Con un solo almacén y un solo proyecto, nada cambia en pantalla** salvo la línea «Proyecto: …» en la entrega y el campo «Proyecto» en el alta.
- `usuario.almacen_id` se conserva: todo el código que lo lee sigue funcionando para el caso normal mientras se migra al helper de alcance.
- `periodo_contrato.area_obra` se sigue llenando, para la ficha, el reporte de adeudos y los vales anteriores.
- Fechas en UTC en la base; «hoy» y las fechas de proyecto son del centro de México.
- La operación sin conexión (FEAT-020) opera solo en el almacén activo; su paquete de datos debe traer los trabajadores con asignación a proyectos de ese almacén **y** los de otros almacenes que reciben entregas ahí (Contratistas entrega a gente de los proyectos). Se resuelve en FEAT-020.
- FEAT-014 (despacho de EPP) toca la misma evaluación de la ENTREGA: FEAT-013 entra primero a `movimientos` (sección 7 del maestro). La aprobación del despacho es del supervisor del almacén **que entrega**; el uso es del proyecto.

## Riesgos

| Riesgo | Cómo se atiende |
|---|---|
| **AC-06 está en todas partes.** Unos 20 servicios del backend leen `usuario.almacen_id` o `puede_operar_todos_los_almacenes`, unos 80 archivos con pruebas tocan el alcance y unos 50 de la interfaz usan `almacen_id`. Cambiar «el suyo o todos» por «su conjunto» uno por uno deja huecos. | Un solo helper en `acceso` (dueño de `usuario_almacen`; `core` no importa módulos): `AccesoService.alcance_del_usuario(usuario) -> Alcance(todos, almacenes, activo)`, y `en_alcance` y `exigir_mismo_almacen` reescritos sobre él. Se migra un servicio por cambio (orden: `consulta/tablero` y `valor`, `autorizaciones`, `movimientos`, `consulta` reportes y seguimiento, `inspecciones`, `solicitudes_compra`, `importacion`, `catalogo`, `almacenes`), cada uno con una prueba de un usuario de dos almacenes. Una prueba de búsqueda en el código falla si queda una lectura directa de `usuario.almacen_id` fuera de `acceso` y `movimientos` (escrituras). |
| **Trabajadores existentes sin proyecto** hacen que cada entrega pida observación (PR-10) desde el primer día en producción. | Antes de desplegar, RH asigna a los trabajadores vigentes con el filtro «Sin proyecto». La guía lo dice. Ver decisión abierta 1. |
| **Contar el resguardo por proyecto** con artículos por cantidad (no hay pieza que seguir). | Regla de la última entrega (TB-06), igual que la de AC-06. Se prueba con entregas a dos proyectos y una devolución parcial. FEAT-018 (resguardo por proyecto) debe usar la misma regla. |
| **Lentitud del uso por proyecto** con mucho historial. | Índice por `(proyecto_id, tipo, creado_en)`; consultas agregadas; sin tablas de resumen. |
| **Almacén activo por usuario** sorprende a quien usa dos equipos a la vez. | 409 `ALMACEN_CAMBIO` con borrador conservado y el aviso de D.12. Señal para reevaluar en ADR-012. |
| **El supervisor ve dinero** por primera vez. | Solo totales; prueba que revisa que ninguna respuesta del tablero trae `costo_unitario`. |
| **Choque con FEAT-014** en la evaluación de la ENTREGA. | Orden del maestro: FEAT-013 entra primero; FEAT-014 se rebasa. |

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla, con su ID en el nombre (`test_pr_09_…`, `test_ac_39_…`, `test_tb_06_…`).
- Prueba de alcance con un usuario de dos almacenes en cada endpoint de lectura y de escritura.
- Prueba de concurrencia de dos asignaciones simultáneas (PR-13).
- Prueba de que el uso por proyecto cuadra con el consumo (TB-02) y descuenta cancelaciones.
- Migración arriba y abajo con datos (`alembic upgrade head` y `downgrade`), comprobando que todo usuario con almacén queda con su conjunto.
- `uv run python -m app.mantenimiento verificar` sale 0 después de migrar.
- La prueba de integración del guion del PDF sigue pasando.
- Recorrido manual: Administrador (computadora), RH (computadora), almacenista (celular), supervisor de un almacén y supervisor de dos (celular y computadora).
- Otra persona o agente revisa el cambio.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): PR-01 a PR-14 (sección nueva), AC-36 a AC-41, TB-04 a TB-08, los ajustes de la tabla siguiente y la sección 8 (permisos nuevos, `reportes.valor_inventario` sale de 8.3 y pasa a 8.2 con Compras y Supervisor).
- [data-model.md](../architecture/data-model.md): `proyecto`, `asignacion_proyecto`, `usuario_almacen`, `vale.proyecto_id`; `usuario.almacen_id` pasa a ser el almacén activo; dueños de tablas.
- [api-contracts.md](../architecture/api-contracts.md): sección nueva «Proyectos» y los cambios de Acceso, Usuarios y personal, Trabajadores, Vales, Almacenes y Tablero.
- [app-flow.md](../product/app-flow.md): `/proyectos`, alta con proyecto, selector de almacén activo, Inicio del supervisor.
- [ui-ux.md](../product/ui-ux.md): tabla con barras horizontales; selector del almacén activo en la barra superior.
- [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md): hoy dice que «proyecto» y «área» son lo mismo (sección 3); deja de ser así. El periodo por apertura (12.2) queda resuelto por el proyecto.
- [mvp-scope.md](../product/mvp-scope.md): subconjunto de almacenes y periodo por apertura salen de «Pospuesto» (aprobado en la sección 6 del maestro).
- `AGENTS.md`: los módulos pasan de doce a quince (maestro, 5.2).
- [guia-por-rol.md](../guia-por-rol.md): proyectos, alta con proyecto, selector de almacén.

### Reglas existentes que cambian

| Regla | Cambio |
|---|---|
| RG-07 | «Opera sobre su almacén asignado» pasa a «opera sobre su almacén activo, uno de su conjunto» (AC-36). |
| AC-06 | Se quita «No hay subconjuntos de almacenes por usuario: ve el suyo o todos»; el alcance de lectura es el conjunto (AC-37) y el de escritura, el almacén activo (AC-38). |
| AC-12 | «Un usuario tiene un solo almacén» pasa a «un conjunto, con uno activo»; el supervisor asigna solo almacenes de su conjunto (AC-41). |
| AC-13 | Aplica también al cambio del almacén activo (AC-39). |
| A-01 | «Quienes tienen ese almacén asignado» pasa a «quienes lo tienen en su conjunto» (AC-40). |
| AL-03 | Bloqueo nuevo `CON_PROYECTOS_ACTIVOS`; `CON_USUARIOS` cuenta el conjunto. |
| TB-01 | «Solo el almacén asignado» pasa a «los almacenes de su conjunto»; `almacen_id` filtra dentro del conjunto. |
| T-02 | El reingreso pide proyecto cuando no tiene uno asignable (PR-11). |
| T-03 | «Área u obra» se reemplaza por el proyecto (PR-11). |
| E-24 | El vale lleva el nombre del proyecto; sin proyecto, el área u obra del periodo. |

## Decisiones abiertas

1. **Trabajadores existentes sin proyecto.** Se decidió **no** crear un proyecto «Sin asignar» en la migración. Razones: un proyecto falso aparecería en los selectores, en el uso por proyecto y en el conteo de PR-12 como si fuera trabajo real; ocultaría a quién le falta asignación; y «Sin proyecto» ya tiene que existir para PR-10. A cambio, la lista de trabajadores trae el filtro «Sin proyecto» para que RH los asigne antes de desplegar. Falta tu confirmación.
2. **«Vigente» en la entrega.** El encargo define vigente como «activo y hoy dentro de inicio y fin estimado», pero PR-06 pide que un proyecto vencido siga operando, y D-02 que el proyecto exista antes que sus trabajadores (por iniciar). Se supone: la **entrega** toma cualquier proyecto activo (PR-08) y la **asignación** ofrece los asignables (vigentes o por iniciar). Falta tu confirmación.
3. **Atribución del resguardo por proyecto** a la última entrega del artículo (TB-06). Es la única forma sin cambiar el modelo de existencias. FEAT-018 debería usar la misma.
4. **Valor con el costo actual.** Los movimientos no guardan el costo; si el costo de un artículo cambia, el valor usado por un proyecto cambia también. Guardar el costo histórico es otra feature.
5. **Inactivar al trabajador no termina su asignación** (caso 17). Evita que `movimientos` escriba en tablas de `proyectos`. Si se prefiere terminarla, lo haría `proyectos` al recibir el aviso, no `movimientos`.
6. **El cambio de almacén activo queda en el registro de cambios.** Es poco frecuente en el caso normal; si un supervisor de dos almacenes cambia muchas veces al día, se puede dejar solo en la bitácora técnica.
7. **`proyectos.asignar` para todo rol con `trabajadores.administrar`** en la migración, para que nadie pierda el alta. Si se quiere separar quién da de alta de quién asigna, se quita desde `/roles` y el alta queda en 403 para ese rol.

## Orden de construcción sugerido

1. Helper de alcance en `acceso` y `usuario_almacen` (sin cambiar comportamiento: conjunto de uno). Pruebas verdes.
2. Módulo `proyectos`, migración, permisos, `/proyectos` y datos de prueba.
3. Alta y reingreso con proyecto; ficha del trabajador.
4. Proyecto en la entrega (PR-08 a PR-10, PR-14).
5. PR-12 y AL-03.
6. Inicio del supervisor (TB-04 a TB-08).
7. Casos especiales en pantalla: conjunto de almacenes, selector del almacén activo, segundo proyecto (paso 7 del maestro).
