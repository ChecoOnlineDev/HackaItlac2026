# FEAT-014: Despacho de EPP con aprobación, autonomía y notificaciones push

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Es parte de la [iteración 01](../releases/iteration_01/README.md) (decisiones D-06, D-07, D-08 y D-14) y **amplía el alcance** del MVP (sección 6 del documento maestro). Si este brief contradice al documento maestro, manda el maestro. Reglas nuevas: **DE-01 a DE-16** y **NT-01 a NT-09**. Cambia F-04, A-01, A-02, A-03, A-05, A-07 y SM-03. Decisión técnica en [ADR-013](../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md).

## Problema u oportunidad

En la plática del 8 de octubre el track pidió corregir el flujo de captura: **el almacenista no tiene autonomía para despachar EPP a cualquiera**. Toda entrega de equipo de protección personal necesita una solicitud al supervisor de ese almacén, que llega como notificación push, el supervisor entra a la aplicación y ve la solicitud de despacho (pedido 5 de la sección 1 del maestro).

Hoy el sistema solo pide al supervisor los renglones en naranja (límite superado, E-07; artículo restringido, E-26; habilitación, E-08), el supervisor se entera porque tiene la aplicación abierta (el contador del menú consulta cada 5 segundos) y la regla F-04 dice que el supervisor no valida cada vale. Eso deja tres huecos:

1. El EPP sale sin que el supervisor lo vea, aunque el track dice que el almacenista no debe decidir solo.
2. No hay forma de avisar al supervisor que está en planta con el celular en la bolsa: si no abre la aplicación, la solicitud vence.
3. Las notas del track ponen la firma **antes** de mandar la solicitud. Si el supervisor rechaza algo, el trabajador ya firmó un vale con artículos que no recibe.

## Objetivo

Que ningún EPP salga del almacén sin la aprobación de un supervisor de ese almacén, salvo donde el Administrador decida dar autonomía; que el supervisor se entere en su celular aunque no tenga la aplicación abierta; y que el trabajador firme solo lo que de verdad recibe.

## Historia de usuario

Como **supervisor** de Midrex, quiero que me llegue un aviso al celular cuando un almacenista de mi almacén va a entregar EPP, y aprobarlo o rechazarlo desde ahí, renglón por renglón, para controlar el EPP sin estar en el mostrador.

Como **almacenista**, quiero mandar la entrega a aprobación con un toque y atender a otro trabajador mientras llega la respuesta, para no detener la fila.

Como **trabajador**, quiero firmar solo lo que me entregan, para no responder por equipo que no recibí.

Como **Administrador**, quiero prender la autonomía de un almacén o de un almacenista de confianza, para que donde no haga falta aprobar no se detenga la operación.

Todavía no hay historias en `docs/stories/`: se escriben al empezar la construcción.

## Flujo normal de referencia

Las pantallas se optimizan para el caso normal (D-01). En este documento los ejemplos usan **Midrex**:

| Persona | Rol | Turno | Almacén |
|---|---|---|---|
| Luis Gómez | Supervisor | Día (7:00 a 19:00) | Midrex |
| Marta Ríos | Supervisor | Noche (19:00 a 7:00) | Midrex |
| Ana Ruiz | Almacenista | Día | Midrex |
| Pedro Sosa | Almacenista | Noche | Midrex |
| Juan Pérez | Trabajador (contratista del proyecto de Midrex) | | |

Cada almacén tiene dos supervisores y dos almacenistas. El sistema **no sabe de turnos**: los dos supervisores de Midrex tienen `autorizaciones.resolver` en Midrex a toda hora y los dos reciben las solicitudes (ver decisión abierta 3). Lo normal es que el supervisor de turno resuelva desde su celular y el otro vea cómo se cierra el aviso.

## Términos

| Término | Qué es |
|---|---|
| **Artículo de EPP** | Un artículo cuya **categoría** es de tipo `EPP` (`categoria.tipo = EPP`; de inicio: EPP básico, EPP de dotación y Equipo de alturas). El artículo no tiene tipo propio: si se cambia de categoría, cambia también si es EPP (CF-03). |
| **Despacho con aprobación** | El almacén tiene `almacen.despacho_epp_con_aprobacion = true` (por omisión) **y** quien captura tiene `usuario.despacho_autonomo = false` (por omisión) **y** quien captura no tiene `autorizaciones.resolver` en ese almacén. |
| **Autonomía** | Lo contrario: el almacén o el almacenista despachan EPP sin aprobación. Solo la cambia quien tiene `despacho.autonomia` (de inicio, el Administrador; D-07). |
| **Solicitud de despacho** | Una `autorizacion` con `tipo = DESPACHO`. Una por vale. |
| **Renglón que se resuelve** | Un renglón de EPP o uno en naranja. El supervisor lo aprueba o lo rechaza. |
| **Renglón de contexto** | Un renglón de herramienta en verde o amarillo dentro de una solicitud de despacho. El supervisor lo ve para entender la entrega, pero no lo resuelve y no necesita aprobación. |

## Alcance incluido

### A. Reglas del despacho (DE)

| ID | Regla | Origen |
|---|---|---|
| DE-01 | **Cuándo se pide.** Toda ENTREGA con al menos un renglón de artículo de EPP necesita la aprobación del despacho cuando el despacho es con aprobación: `almacen.despacho_epp_con_aprobacion = true` **y** quien captura no tiene `usuario.despacho_autonomo = true` **y** quien captura no tiene `autorizaciones.resolver` en ese almacén (DE-07). Una entrega solo de herramienta no la pide. Nunca la piden la devolución (SM-05), el traspaso, la recepción, la cancelación, el no adeudo ni la entrada. El EPP que se entrega al contratar a alguien, antes de que entre a un mantenimiento, también la pide (pregunta 1 de la sección 10 del maestro; supuesto). | Plática 8 oct (pedido 5); D-06 |
| DE-02 | **El semáforo no cambia.** La evaluación de cada renglón da el mismo nivel que hoy (verde, amarillo, naranja o rojo). Aparte, la evaluación dice si el vale necesita aprobación (`requiere_aprobacion_despacho`) y marca cada renglón de EPP con `requiere_aprobacion: true`; la pantalla lo muestra como una etiqueta «Necesita aprobación», no como un color. El vale no se puede confirmar (`puede_confirmar: false`) mientras haya un renglón que necesite aprobación sin aprobar. | D-06; SM-03 |
| DE-03 | **Orden del flujo.** Capturar al trabajador, capturar los artículos (con el semáforo de siempre), «Enviar a aprobación», esperar, ver la respuesta (total o parcial), quitar lo rechazado, firma del trabajador y confirmar. **La firma nunca va antes de aprobar**: el paso de firma no se abre mientras falte la aprobación, y si después de firmar cambia algo que invalida la aprobación (DE-13), la firma se borra y el trabajador firma de nuevo lo que recibe. Si los renglones no cambian, la firma se conserva aunque haya que pedir otra aprobación. | D-08 |
| DE-04 | **Una sola solicitud por vale.** «Enviar a aprobación» crea una `autorizacion` de `tipo = DESPACHO` que incluye **todos** los renglones de EPP del vale y **todos** los renglones en naranja (E-07, E-26, E-08), sean de EPP o de herramienta. Así el supervisor resuelve todo junto y el vale sigue llevando un solo `autorizacion_id`. Los renglones de herramienta en verde o amarillo viajan como contexto. Un renglón en rojo no se envía (A-06): la solicitud entera responde 422 `RENGLON_NO_AUTORIZABLE` y hay que quitarlo antes. Si el vale pide aprobación del despacho, no se acepta una solicitud de `tipo = EXCEDENTE` (422 `RENGLON_NO_AUTORIZABLE` con `regla: "DE-04"`); si no la pide, una de `tipo = DESPACHO` tampoco (422 con `regla: "DE-01"`: «Este despacho no necesita aprobación; vuelve a evaluar»). Cada solicitud lleva un `id_cliente` que genera el dispositivo: un doble toque no crea dos solicitudes. | Propuesta; A-06 |
| DE-05 | **Motivo y nota.** En una solicitud de despacho sin renglones en naranja, el motivo lo pone el sistema («Despacho de EPP») y el almacenista puede agregar una nota opcional de hasta 255 caracteres («Le cambio el casco, se le rompió»). Si la solicitud incluye renglones en naranja, el motivo de ese excedente sigue siendo obligatorio (A-02) y lo escribe el almacenista. Las observaciones que ya se capturaron en renglones con E-09 viajan en la solicitud para que el supervisor las lea. | A-02; propuesta |
| DE-06 | **Aprobación parcial.** El supervisor resuelve cada renglón que se resuelve: APROBADO o RECHAZADO, con un motivo obligatorio para cada rechazo. Puede aprobar todo o rechazar todo de un toque (el rechazo total también pide motivo). La autorización queda **APROBADA** si se aprobó al menos un renglón, y **RECHAZADA** si se rechazaron todos. Lo resuelto se guarda en `autorizacion.renglones_resueltos`. Aplica igual a las solicitudes de `tipo = EXCEDENTE` (una solicitud de excedentes de dos renglones también se puede aprobar a medias). | Propuesta |
| DE-07 | **El supervisor que despacha.** Si quien captura tiene `autorizaciones.resolver` en el almacén del vale (un supervisor despachando o el Administrador), el despacho de EPP queda **aprobado por su propia captura**: no se manda solicitud de despacho y el vale dice «Validó: él mismo (despacho)». Es la excepción a A-05 que prevé el maestro. Un excedente de límite (y cualquier naranja) **sigue necesitando a otro supervisor** (A-05): en ese caso se manda una solicitud de `tipo = EXCEDENTE` solo con los naranjas. Los renglones de EPP de ese vale llevan la regla `DE-07` en `movimiento.reglas`. | D-07; A-05 |
| DE-08 | **Qué puede confirmar el vale.** Con una solicitud de despacho aprobada, el vale puede llevar solo los renglones que se resuelven y que el supervisor **aprobó**, con la misma cantidad o menos. Los renglones de contexto se pueden quitar o cambiar sin pedir otra aprobación. Si al confirmar el vale trae un renglón que necesita aprobación y que la autorización no cubre (rechazado, no incluido o con más cantidad), el servidor responde 409 `APROBACION_INVALIDA` con la lista de esos renglones y no guarda nada. Los renglones de EPP aprobados guardan la regla `DE-01` en `movimiento.reglas` y el vale lleva el `autorizacion_id`. | A-03; propuesta |
| DE-09 | **Vigencia.** Una solicitud pendiente vence a los 15 minutos de creada (`AUTORIZACION_VIGENCIA_MINUTOS`, la misma de hoy). Una aprobada sirve para confirmar el vale durante 15 minutos **desde que se aprobó** (al aprobarse, `vence_en` pasa a `resuelta_en` más la vigencia), para dar tiempo a la firma. Vencida, el almacenista tiene tres caminos: **reenviar** (una solicitud nueva con los mismos renglones; la vencida queda VENCIDA), pedir al supervisor que dé su **PIN en el mostrador** (medio PIN, A-01), o **quitar los renglones de EPP** y entregar lo demás. | A-01, A-07; parámetro de 5.4 |
| DE-10 | **Si nadie responde.** A los 5 minutos sin respuesta la pantalla del almacenista dice «Nadie ha respondido todavía» y ofrece: buscar al supervisor para que dé su PIN aquí, esperar, o quitar el EPP y entregar lo demás. También dice a cuántos supervisores les llegó el aviso (`avisados`); si fueron cero, lo dice desde el principio («Ningún supervisor tiene los avisos activos: búscalo o llámalo»). El almacenista **nunca** despacha el EPP sin aprobación: solo el Administrador puede prender la autonomía (DE-14), y el Administrador también puede aprobar la solicitud (A-01). | Situación límite del maestro (sección 8) |
| DE-11 | **Gana el primero que resuelve.** Si dos supervisores (o el supervisor en su celular y otro con PIN en el mostrador) resuelven la misma solicitud, vale la primera resolución. El segundo recibe 409 `AUTORIZACION_RESUELTA` con quién la resolvió, cuándo y cómo quedó, y su pantalla lo muestra («Ya la aprobó Luis Gómez a las 10:42»). | A-01; propuesta |
| DE-12 | **Lista del supervisor y resolución múltiple.** La lista de solicitudes pendientes se ordena de la más antigua a la más nueva y muestra por cada una: trabajador (nombre, número de empleado y foto), proyecto de la entrega (con FEAT-013), almacén (si el supervisor tiene varios), renglones (los que se resuelven arriba y el contexto abajo, en gris), quién la pide, hace cuánto y cuánto le queda. Se pueden **aprobar varias completas de un jalón** (`POST /api/autorizaciones/resolucion-multiple`) o rechazar varias, con un motivo por cada una. Las solicitudes que incluyen un excedente (naranja) se marcan «Incluye excedente» y **no** se pueden aprobar en grupo: se abren una por una. | Maestro: sección 6 y 8 (arranque de mantenimiento) |
| DE-13 | **Cambios después de aprobar.** Una aprobación deja de servir si, después de aprobada, el almacenista **agrega** un renglón de EPP o un naranja nuevo, **sube** la cantidad de uno aprobado, cambia de trabajador, de almacén o de proyecto: la pantalla dice «Cambiaste lo que se aprobó: hay que volver a enviar» y la solicitud nueva lleva otra vez todos los renglones que se resuelven. **Quitar** renglones, **bajar** cantidades y agregar, quitar o cambiar renglones de contexto no la invalidan. La aprobación anterior no se usa y se queda como APROBADA sin usar hasta que vence. | Propuesta |
| DE-14 | **Interruptor de autonomía.** `PATCH /api/almacenes/{id}/autonomia` cambia `almacen.despacho_epp_con_aprobacion` y `PATCH /api/usuarios/{id}/autonomia` cambia `usuario.despacho_autonomo`; los dos piden `despacho.autonomia` (de inicio, solo el Administrador; D-07) y un **motivo obligatorio**. El cambio aplica en la siguiente evaluación y queda en la auditoría (`almacen.autonomia`, `usuario.autonomia`) con quién, cuándo, valor anterior, valor nuevo y motivo. Se ve en `/almacenes` y en `/usuarios`. Los renglones de EPP despachados con autonomía guardan la regla `DE-14` en `movimiento.reglas`. | D-07 |
| DE-15 | **La espera del almacenista.** Mientras espera, la pantalla de la entrega consulta la solicitud cada 3 segundos (como hoy) y se actualiza sola. El almacenista puede tocar «Atender a otro mientras»: el borrador se guarda en el dispositivo (E-28) y pasa a la lista **«En espera»**, con su contador en el inicio y en Entregar, y él empieza otra entrega. Al aprobarse una solicitud en espera, el dispositivo suena y vibra y aparece «Aprobada: Juan Pérez · Continuar». Caben hasta 10 borradores en espera por dispositivo. Los borradores no salen del dispositivo: otro almacenista no los ve. | E-28; propuesta |
| DE-16 | **Revalidación al confirmar.** Al confirmar, el servidor vuelve a evaluar todo el vale (RG-08). Si un renglón aprobado quedó en rojo mientras se esperaba (se acabaron las existencias, la pieza quedó No apta, venció su inspección, el trabajador dejó de ser vigente), responde 409 `VALE_CAMBIO` con el renglón marcado; quitarlo no pide otra aprobación (DE-13). Si la autonomía se **apagó** después de evaluar un borrador que no la pedía, responde 409 `REQUIERE_APROBACION_DESPACHO` y el borrador se conserva para enviarlo a aprobación. Si se **prendió** mientras se esperaba, el vale se confirma sin esperar: la solicitud pendiente queda sin usar y vence sola (una autorización que el vale no necesita no se gasta). | RG-08, RG-09 |

### B. Reglas de las notificaciones (NT)

El canal es **Web Push desde la PWA** que ya existe ([ADR-013](../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md)). El mismo canal lleva las solicitudes de despacho (DESPACHO), las de excedente (EXCEDENTE) y las de traslado entre almacenes de tercer nivel (TRASLADO, [FEAT-015](FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md)).

| ID | Regla | Origen |
|---|---|---|
| NT-01 | **Suscribirse.** Quien tiene `autorizaciones.resolver` ve en la pantalla de Autorizaciones y en su menú de usuario un botón **«Activar avisos»**. El navegador pide el permiso **solo** cuando se toca ese botón, nunca al cargar la página. Al aceptar, el dispositivo registra su suscripción (`suscripcion_push`), ligada al usuario y a la familia de la sesión de ese dispositivo (`familia_id`, AC-14). Al abrir la aplicación con el permiso ya concedido, si la suscripción del navegador cambió o el servidor ya no la tiene, se vuelve a registrar sola, sin preguntar. «Desactivar avisos» la borra. Al salir (cerrar la sesión de ese dispositivo) la aplicación la revoca antes de cerrar; y el servidor no manda nada a una suscripción cuya sesión ya no es válida (familia cerrada o vencida, versión de sesión vieja, AC-17 a AC-22): la marca revocada al intentar enviar. | D-14; AC-19 |
| NT-02 | **A quién se manda.** A cada usuario **activo** que tiene `autorizaciones.resolver` y tiene el almacén de la solicitud en su conjunto de almacenes (AC-36; hasta que se construya FEAT-013, su almacén asignado), **menos quien la pidió**, en todos sus dispositivos con una suscripción vigente. El Administrador (`almacenes.todos`) **no** recibe avisos por omisión, para no saturarlo con los de todos los almacenes; ve el contador y la lista (decisión abierta 2). Los destinatarios se calculan al momento de enviar: a quien le quitaron el permiso o el almacén ya no le llega nada. | A-01; AC-06 |
| NT-03 | **Qué dice.** Sin datos personales sensibles: sin costos (RG-12), sin CURP ni NSS (RG-13), sin foto. Título: almacén y qué se pide; cuerpo: para quién, cuántos artículos y quién lo pide. Ejemplos: «Midrex · EPP por aprobar» / «Para Juan Pérez: 4 artículos de EPP. Lo pide Ana Ruiz.»; «Midrex · Excedente por autorizar» / «Para Juan Pérez: 1 artículo sobre su límite. Lo pide Ana Ruiz.». El contenido viaja cifrado de punta a punta (el servicio de push del navegador no lo puede leer), pero se ve en la pantalla bloqueada del celular. | RG-12, RG-13 |
| NT-04 | **Al tocarla.** Abre `/autorizaciones/{id}` en la aplicación (si ya hay una ventana abierta, la trae al frente). Si la sesión venció, pide entrar y regresa a esa solicitud (flujo 1). Si la solicitud ya no está pendiente, la pantalla dice cómo quedó y quién la resolvió. Si es un aviso agrupado (NT-05), abre la lista `/autorizaciones`. | Plática 8 oct (pedido 5) |
| NT-05 | **Agrupación.** Los avisos de un mismo almacén comparten una etiqueta (`tag`): el nuevo **reemplaza** al anterior en vez de apilarse. Si hay más de una pendiente en ese almacén, el aviso dice «Midrex · 5 solicitudes por aprobar» y abre la lista. Solo el primer aviso de cada minuto suena y vibra; los que llegan dentro de ese minuto reemplazan en silencio, con la cuenta al día. El minuto se cuenta con `suscripcion_push.ultimo_envio`, en la base, no en la memoria del proceso. | Maestro: sección 8 (arranque de mantenimiento) |
| NT-06 | **Al resolverse.** Cuando una solicitud se aprueba, se rechaza o se usa, a los **demás** destinatarios se les manda un aviso de **reemplazo** en silencio con la misma etiqueta: «Midrex · Luis Gómez ya la aprobó» o, si quedan otras pendientes, la cuenta nueva. No es un push «invisible»: los navegadores exigen que cada push muestre un aviso (Safari retira el permiso si no se hace), así que se reemplaza en silencio y el aviso se cierra al abrirlo. La que vence no genera aviso: vencer no es un evento del servidor (no hay tareas programadas); al abrirla dice que venció. | DE-11; ADR-013 |
| NT-07 | **Envío después del commit.** Los avisos se mandan **después** de que la solicitud o su resolución quedó guardada, con las tareas en segundo plano de FastAPI (`BackgroundTasks`), nunca dentro de la transacción. Un fallo al enviar no deshace ni detiene la solicitud: queda en `suscripcion_push.ultimo_error`. Si el servicio de push responde 404 o 410 (la suscripción ya no existe), la suscripción se marca revocada (`revocada_en`). Cada aviso caduca a los 15 minutos (TTL igual a la vigencia, DE-09): un celular apagado más tiempo ya no lo recibe. Sin reintentos ni colas. | ADR-013 |
| NT-08 | **El respaldo sigue.** El push es una ayuda, no el único camino: el contador del menú (cada 5 segundos para quien resuelve) y la lista de Autorizaciones funcionan sin avisos. En iPhone el aviso solo llega con la aplicación **instalada en la pantalla de inicio** (iOS 16.4 o superior); en Android, Chrome lo recibe sin instalar. La pantalla muestra el estado de los avisos de **este** dispositivo («Activos», «Bloqueados en el navegador», «Instala la aplicación para recibirlos», «Este navegador no los admite») y una ayuda corta por plataforma. | RG-15; ADR-013 |
| NT-09 | **Aviso de prueba.** `POST /api/notificaciones/prueba` manda un aviso de prueba a las suscripciones del dispositivo que lo pide («Los avisos funcionan en este equipo»), para que el supervisor compruebe que le llegan antes de irse a planta. Uno cada 10 segundos como máximo. | Propuesta |

### C. Acción por acción

Cada paso dice quién actúa, qué hace, qué valida el servidor, qué responde y qué ve cada persona. Los pasos 1 y 2 son los de hoy (flujo 6); lo nuevo empieza en el paso 3.

#### Paso 1. El almacenista identifica al trabajador

- **Quién:** Ana (almacenista de día de Midrex), con Juan enfrente.
- **Hace:** escanea la credencial, teclea el número o busca por nombre (E-18).
- **Valida el servidor:** vigencia del trabajador (E-02), pendientes (E-12) y, con FEAT-013, sus proyectos (PR-09, PR-10).
- **Responde:** la ficha breve y, en la primera evaluación, `requiere_aprobacion_despacho` y `despacho.modo` (abajo).
- **Ve Ana:** la ficha de Juan con su foto. Si el despacho de Midrex es con aprobación, una línea discreta arriba: «El EPP de esta entrega lo aprueba un supervisor». Si es autónomo: nada.
- **Ve el supervisor:** nada.

#### Paso 2. El almacenista captura los artículos

- **Hace:** escanea casco, lentes, guantes, tapones y un marro.
- **Valida el servidor:** la evaluación de siempre (SM-06: código, trabajador, ubicación y existencias, seguridad, límites, avisos) y, además, qué renglones son de EPP (DE-01).
- **Responde:** cada renglón con su nivel y sus motivos (sin cambio) y, si es de EPP en un despacho con aprobación, `requiere_aprobacion: true`.
- **Ve Ana:** el semáforo de siempre. Los cuatro renglones de EPP llevan la etiqueta «Necesita aprobación»; el marro, no. El botón de abajo dice **«Enviar a aprobación»** en lugar de «Continuar». Un rojo se quita como hoy; un naranja ya no tiene su propio botón «Pedir autorización»: va dentro de la misma solicitud (DE-04).
- **Si el despacho no pide aprobación** (autonomía o supervisor despachando): el botón dice «Continuar» y los naranjas siguen con «Pedir autorización» (flujo 7 de hoy, `tipo = EXCEDENTE`).

#### Paso 3. El almacenista envía a aprobación

- **Hace:** toca «Enviar a aprobación». Se abre una hoja con el resumen de lo que se manda (lo que se resuelve arriba y el contexto abajo), una nota opcional y, solo si hay naranjas, el campo obligatorio «Motivo del excedente». Dos botones: **«Enviar al supervisor»** y **«El supervisor está aquí»** (PIN en el mostrador).
- **Valida el servidor** (`POST /api/autorizaciones` con `tipo = DESPACHO`): permiso `entregas.crear`; el almacén sale de la sesión (AC-06, AC-13); el trabajador existe; de cada renglón toma **solo** `codigo`, `cantidad` y `observacion` y lo evalúa él mismo; que el vale de verdad pida aprobación del despacho (DE-01); que no haya rojos (A-06); motivo del excedente si hay naranjas (A-02); el `id_cliente` (DE-04).
- **Responde:** 201 `{id, tipo, estado: PENDIENTE, vence_en, avisados}`; 200 con la misma solicitud si el `id_cliente` ya existía con el mismo cuerpo. Después del commit, manda los avisos (NT-07).
- **Ve Ana:** la pantalla de espera: «Esperando aprobación de un supervisor de Midrex», un reloj con lo que falta para que venza (calculado con la hora del servidor, RG-11), «Se avisó a 2 supervisores» y los botones «Atender a otro mientras», «El supervisor está aquí» y «Quitar el EPP y entregar lo demás».
- **Ve Juan:** la misma pantalla, si mira el mostrador: «Esperando aprobación».
- **Ven Luis y Marta:** el aviso en su celular (NT-03) y el contador de Autorizaciones sube.
- **Ve el Administrador:** el contador sube; no le llega aviso (NT-02).

#### Paso 4. El supervisor abre la solicitud

- **Quién:** Luis, en planta, con el celular.
- **Hace:** toca el aviso (NT-04) o entra a Autorizaciones.
- **Valida el servidor** (`GET /api/autorizaciones/{id}`): que la vea quien la pidió o quien tiene `autorizaciones.resolver` en ese almacén (A-01, AC-06); si venció, la marca VENCIDA.
- **Responde:** la solicitud con trabajador, foto (`tiene_foto`; la imagen viene de su endpoint, que pide `trabajadores.ver`), proyecto, renglones clasificados (`clase`: EPP, EXCEDENTE o CONTEXTO), nota, observaciones, quién la pide, `creado_en`, `vence_en` y la hora del servidor.
- **Ve Luis:** la tarjeta de la solicitud: foto y nombre de Juan, proyecto, «Lo pide Ana Ruiz hace 1 min», los cuatro renglones de EPP, cada uno con su interruptor Aprobar/Rechazar (todos en Aprobar), el marro en gris como contexto, y dos botones grandes: **«Aprobar todo»** y **«Rechazar todo»**. Si cambia un renglón a Rechazar, aparece su campo de motivo y el botón dice «Aprobar 3 y rechazar 1».

#### Paso 5. El supervisor resuelve

- **Hace:** aprueba todo, aprueba a medias (rechaza los guantes: «Se le dieron ayer») o rechaza todo con motivo.
- **Valida el servidor** (`POST /api/autorizaciones/{id}/resolucion`): permiso `autorizaciones.resolver` y almacén (A-01); que siga PENDIENTE y vigente (DE-11, DE-09); que no la resuelva quien la pidió (A-05); que cada renglón que se resuelve tenga decisión y cada rechazo su motivo (DE-06); bloquea la fila para que solo gane una resolución.
- **Responde:** la solicitud con `estado` (APROBADA si se aprobó al menos uno; RECHAZADA si ninguno), `renglones_resueltos`, quién y cuándo; con `vence_en` recorrido a 15 minutos desde ahora si quedó aprobada (DE-09). Después del commit, el aviso de reemplazo a los demás (NT-06).
- **Ve Luis:** «Listo: aprobaste 3 de 4» y regresa a la lista.
- **Ve Marta:** el aviso de su celular cambia a «Midrex · Luis Gómez ya la aprobó», sin sonar. Si la abre: «Ya la aprobó Luis Gómez a las 10:42».
- **Ve Ana** (en máximo 3 segundos): «Aprobada por Luis Gómez». Los renglones aprobados quedan con una palomita; el rechazado, en gris tachado con el motivo y un botón «Quitar» (o «Quitar los rechazados» si son varios). El botón de abajo dice **«Continuar a la firma»** y solo se habilita cuando ya no queda ningún rechazado.

#### Paso 5 bis. El supervisor está en el mostrador (PIN)

- **Hace:** en el dispositivo de Ana, Luis escribe su usuario y su PIN, ve los renglones y resuelve igual que en su celular (todo, a medias o rechazo).
- **Valida el servidor:** lo de hoy (A-01 medio PIN: PIN correcto, bloqueo por intentos, Luis tiene el permiso y es de Midrex, no es quien la pidió) más lo del paso 5.
- **Responde:** la solicitud resuelta con `medio = PIN`.
- **Ve Ana:** lo mismo que en el paso 5.

#### Paso 5 ter. El supervisor resuelve varias de un jalón

- **Hace:** en la lista, marca 12 solicitudes sin excedente y toca «Aprobar 12».
- **Valida el servidor** (`POST /api/autorizaciones/resolucion-multiple`): permiso; por cada una lo mismo que en el paso 5, y que no incluya renglones en naranja si se aprueba en grupo (DE-12). Cada solicitud se resuelve en su propia transacción: si otra persona ya resolvió una, las demás siguen.
- **Responde:** 200 con un resultado por solicitud (`estado` o `error`).
- **Ve Luis:** «Aprobaste 11. 1 ya la había resuelto Marta Ríos».

#### Paso 6. Firma y confirmación

- **Hace Ana:** quita lo rechazado, toca «Continuar a la firma»; si algún renglón pide observación (E-09) y no la tiene, la escribe; Juan firma en pantalla (F-02); Ana confirma.
- **Valida el servidor** (`POST /api/vales` con `autorizacion_id`): todo lo de hoy (RG-08, RG-09, F-02, E-09, AC-13) más: que la autorización sea de `tipo` DESPACHO (o EXCEDENTE si el despacho no la pide), esté APROBADA, vigente, sin usar, del mismo almacén, trabajador y proyecto (A-03); que cada renglón que necesita aprobación esté aprobado con su cantidad o menos (DE-08); que quien confirma no sea quien aprobó (A-05). La marca USADA en la misma transacción.
- **Responde:** 201 con el vale; o 409 `APROBACION_INVALIDA`, `AUTORIZACION_INVALIDA`, `REQUIERE_APROBACION_DESPACHO` o `VALE_CAMBIO` (ver «Cambios de datos o API»). Después del commit, el aviso de reemplazo (NT-06) si alguno de los supervisores aún la tenía en pantalla.
- **Ve Ana:** el vale emitido con folio y QR. El vale impreso dice «Validó: Luis Gómez».
- **Ve Juan:** su comprobante (F-10) solo con lo que recibió.

#### Paso 7. El supervisor despacha él mismo

- **Quién:** Luis atiende el mostrador porque Ana está en su descanso.
- **Hace:** captura la entrega igual que un almacenista.
- **Valida el servidor:** Luis tiene `autorizaciones.resolver` en Midrex: `despacho.modo = SUPERVISOR` y el EPP no pide solicitud (DE-07). Si un renglón supera el límite (naranja), pide «Pedir autorización» a **otro** supervisor (Marta por aviso, o con su PIN si está ahí; A-05).
- **Ve Luis:** «Continuar» directo a la firma si no hay naranjas.
- **Ve el vale:** «Validó: Luis Gómez (despachó él mismo)».

#### Paso 8. El Administrador cambia la autonomía

- **Quién:** el Administrador, desde la computadora (D-20).
- **Hace:** en `/almacenes`, en la ficha de Contratistas, apaga «El EPP pide aprobación del supervisor»; o en `/usuarios`, en la ficha de Pedro, prende «Despacha EPP sin aprobación». Escribe el motivo.
- **Valida el servidor:** `despacho.autonomia`; motivo no vacío; almacén o usuario existentes.
- **Responde:** la ficha con el valor nuevo. Queda la auditoría `almacen.autonomia` o `usuario.autonomia`.
- **Ven los almacenistas:** en su siguiente evaluación, el botón cambia. Un borrador que ya esperaba aprobación sigue esperando, pero se puede confirmar sin ella (DE-16).
- **Ve el supervisor:** en `/almacenes` (si tiene acceso) o en la ficha del almacén, una etiqueta «Despacho de EPP sin aprobación».

#### Paso 9. El supervisor activa los avisos

- **Quién:** Luis, la primera vez que entra desde su celular.
- **Hace:** en Autorizaciones ve una tarjeta «Activa los avisos para enterarte aunque no tengas la aplicación abierta» y toca **«Activar avisos»**. El navegador pregunta; Luis acepta. Toca «Mandar un aviso de prueba».
- **Valida el servidor:** `autorizaciones.resolver`; la suscripción trae `endpoint`, `p256dh` y `auth` válidos; la liga a la familia de su sesión.
- **Responde:** la suscripción registrada con su `id`; la prueba, `{enviadas, fallidas}`.
- **Ve Luis:** «Avisos activos en este equipo» y, a los pocos segundos, el aviso de prueba.
- **En iPhone sin instalar:** en lugar del botón, «Para recibir avisos en iPhone, instala la aplicación: Compartir → Agregar a inicio» (NT-08).

### D. Pantallas que cambian o se agregan

| Pantalla | Cambio |
|---|---|
| Entregar (`/entregar`) | Paso nuevo «Aprobación» entre Artículos y Firma (el indicador muestra 4 pasos cuando aplica); etiqueta «Necesita aprobación»; hoja «Enviar a aprobación»; pantalla de espera; lista «En espera» con contador; renglones rechazados con «Quitar». |
| Inicio del almacenista | Contador «En espera (n)» junto a Entregar, con las aprobadas resaltadas. |
| Autorizaciones (`/autorizaciones`) | Lista por antigüedad con tipo (Despacho, Excedente, Traslado), foto, proyecto, contexto y selección múltiple; tarjeta «Activar avisos». |
| Detalle de una solicitud (`/autorizaciones/:id`, **ruta nueva**) | Lo que abre el aviso: renglones con Aprobar/Rechazar, motivos, cómo quedó y quién la resolvió. |
| Menú de usuario | «Avisos de este equipo»: estado, activar, desactivar y aviso de prueba. |
| Almacenes (`/almacenes`) | Columna y control «El EPP pide aprobación» con motivo. |
| Usuarios (`/usuarios`) | Columna y control «Despacha EPP sin aprobación» con motivo (solo para quien puede entregar). |
| Detalle del vale | «Validó» con el modo del despacho. |
| Service worker (`/sw.js`) | Escucha `push`, `notificationclick` y `pushsubscriptionchange`; sube su `VERSION`. |

## Consideraciones

- **El servidor decide todo.** Si un renglón es EPP, si el despacho pide aprobación, a quién se avisa y qué cubre la aprobación lo decide el servidor; la interfaz muestra lo que responde la evaluación.
- **El trabajador como ubicación no cambia.** La aprobación no mueve nada: el inventario cambia solo al confirmar el vale, en el módulo `movimientos` (E-28, RG-01).
- **La firma se pide al final** porque el vale es la prueba de lo que el trabajador recibe (F-02). Firmar antes y quitar renglones después haría que la firma cubra algo distinto de lo que se llevó.
- **Una solicitud por vale** mantiene `vale.autorizacion_id` como está y evita que el supervisor tenga que resolver dos cosas de la misma entrega.
- **Sin colas ni tareas programadas.** El vencimiento se calcula al leer (como hoy) y los avisos se mandan al terminar la petición. Por eso no hay aviso de «venció» ni recordatorios automáticos.
- **El contador y la lista siguen siendo el canal seguro.** El push no está garantizado (ADR-013): ninguna regla depende de que llegue.
- **El supervisor usa la PWA, no la app de Android.** La app de Android del almacenista (FEAT-020, Capacitor) corre en un WebView que no recibe Web Push. El supervisor abre la aplicación en Chrome o la instala como PWA.
- **El tutorial (FEAT-010) simula la aprobación.** En práctica no se crea ninguna solicitud ni se manda ningún aviso: el recorrido de Entregar muestra la espera y una aprobación ficticia.
- **El almacenista no ve a quién más se le avisó**, solo cuántos (`avisados`), para no exponer quién tiene los avisos apagados.

## Situaciones problemáticas de la operación

| Situación | Qué pasa | Reglas |
|---|---|---|
| **Arranque de mantenimiento: 40 contratistas piden su dotación a la vez.** | Ana y Pedro arman una entrega por trabajador y la envían; con «Atender a otro mientras» siguen con el siguiente sin esperar. A Luis le llega un solo aviso que se va actualizando («Midrex · 12 solicitudes por aprobar») y solo suena una vez por minuto. Luis abre la lista, marca las que no tienen excedente y las aprueba de un jalón; las que dicen «Incluye excedente» las abre una por una. Cada almacenista ve sus aprobadas en «En espera» y llama al trabajador a firmar. | DE-12, DE-15, NT-05 |
| **Supervisor sin señal en planta.** | El aviso no llega mientras no haya señal; el servicio de push lo guarda hasta 15 minutos. Si Luis recupera señal a tiempo, le llega; si no, la solicitud vence. Ana ve «Nadie ha respondido todavía» a los 5 minutos y busca a Marta, o a Luis para que dé su PIN en el mostrador, o quita el EPP. | DE-09, DE-10, NT-07 |
| **Supervisor dormido en el turno de noche.** | El aviso suena una vez; si Marta no responde, vence a los 15 minutos. Pedro reenvía (suena otra vez) o pide a Luis, que también lo recibe aunque sea de día (el sistema no sabe de turnos). Si en ese almacén de noche nadie aprueba nunca, es una decisión del Administrador prender la autonomía de noche a mano o para Pedro (DE-14). | DE-09, DE-10, DE-14 |
| **Supervisor que también despacha.** | Su captura cuenta como aprobación del despacho y no manda solicitud. Si hay un excedente, necesita a otro supervisor: Marta por aviso o con su PIN. | DE-07, A-05 |
| **El trabajador se va mientras espera.** | Ana descarta el borrador («Salir sin guardar»). La solicitud sigue pendiente para los supervisores y vence sola; si alguien la aprueba, nadie la usa. No se mueve nada de inventario. Ver decisión abierta 1 (retirar la solicitud). | E-28, DE-09 |
| **Doble toque en «Enviar al supervisor».** | Las dos peticiones llevan el mismo `id_cliente`: el servidor crea una sola solicitud y manda un solo aviso. Si el cuerpo es distinto con el mismo `id_cliente`, 409 `CONFLICTO`. | DE-04 |
| **El almacenista cierra la aplicación mientras espera.** | El borrador vive en el dispositivo (E-28). Al volver a abrir Entregar aparece en «En espera» y la pantalla vuelve a consultar el estado; si ya se aprobó, sigue en la firma. | DE-15, E-28 |
| **Cambio de turno a mitad de una solicitud.** | A las 19:00 Ana entrega el mostrador a Pedro con una solicitud pendiente: el borrador está en el dispositivo de Ana, no en el de Pedro. Si Ana se va, Pedro captura la entrega desde cero en su dispositivo y la envía (la de Ana vence). Del lado del supervisor no cambia nada: los dos reciben todo. | DE-15, RG-07 |
| **Al supervisor le quitan el permiso con avisos pendientes.** | Ya no es destinatario (NT-02). Si toca un aviso viejo, la solicitud le responde 404 y la pantalla dice «Ya no puedes ver esta solicitud». Si intenta resolver, 403. Sus suscripciones siguen registradas pero no reciben nada mientras no tenga el permiso. | NT-02, AC-10 |
| **El celular del supervisor no tiene permiso de avisos.** | El botón dice «Los avisos están bloqueados en este navegador» con los pasos para permitirlos en su configuración (la aplicación no puede volver a preguntar). Mientras tanto, el contador y la lista. El almacenista ve «Se avisó a 0 supervisores» si nadie los tiene activos. | NT-08, DE-10 |
| **El reloj del celular está desfasado.** | El servidor decide vigencia y vencimiento con su hora (RG-11). La pantalla calcula «vence en» con la diferencia entre la hora del servidor que viene en la respuesta y `vence_en`, no con el reloj del celular. | DE-09, RG-11 |
| **El trabajador deja de ser vigente mientras espera** (su contrato terminó a medianoche). | Al confirmar, E-02 pone todo el vale en rojo y responde 409 `VALE_CAMBIO`. La aprobación no sirve para nada: no se entrega. | DE-16, E-02 |
| **Las existencias se acaban mientras espera** (Pedro entregó los últimos guantes en otra ventanilla). | Al confirmar, E-04 pone ese renglón en rojo (409 `VALE_CAMBIO`). Ana lo quita y confirma lo demás sin pedir otra aprobación. | DE-16, RG-08 |
| **Un renglón aprobado queda en rojo** (la inspección del arnés venció mientras esperaba). | Igual que el anterior: E-06, se quita y se confirma lo demás. Un rojo de seguridad no lo salva ninguna aprobación (SM-04). | DE-16, SM-04 |
| **Dos supervisores aprueban al mismo tiempo.** | Gana el primero; el segundo ve quién se le adelantó. | DE-11 |

## Casos límite

| # | Caso | Qué pasa | Reglas |
|---|---|---|---|
| 1 | Entrega solo de herramienta en un almacén con aprobación. | No pide aprobación; flujo de hoy. | DE-01 |
| 2 | Entrega de un casco (EPP) y un marro (herramienta, verde). | La solicitud lleva el casco para resolver y el marro como contexto. | DE-04 |
| 3 | Un guante (EPP) supera su límite (naranja). | Es un solo renglón: es EPP y es excedente; el motivo del excedente es obligatorio y el supervisor lo resuelve una vez. | DE-04, DE-05, A-02 |
| 4 | Un minipulidor con «autorización en cada entrega» (E-26, herramienta, naranja) y EPP en el mismo vale. | Los dos van en la misma solicitud de despacho. | DE-04 |
| 5 | Un renglón en rojo al tocar «Enviar a aprobación». | 422 `RENGLON_NO_AUTORIZABLE`; hay que quitarlo antes. | DE-04, A-06 |
| 6 | Un vale de 15 renglones de EPP (dotación completa). | Una sola solicitud con los 15 (máximo 100 renglones por solicitud). | DE-04 |
| 7 | El almacenista con autonomía tiene un naranja. | Pide autorización de excedente como hoy (`tipo = EXCEDENTE`); el EPP sale sin aprobación (`DE-14` en sus movimientos). | DE-14, A-01 |
| 8 | El almacén es autónomo y el almacenista no. | Manda el almacén: sin aprobación. Basta con que cualquiera de los dos interruptores dé autonomía. | DE-01 |
| 9 | Se manda `tipo = EXCEDENTE` en un vale que pide despacho. | 422 con `regla: "DE-04"`: hay que mandar la de despacho, que ya incluye los excedentes. | DE-04 |
| 10 | Se manda `tipo = DESPACHO` y el despacho no la pide (alguien prendió la autonomía). | 422 con `regla: "DE-01"`; la pantalla vuelve a evaluar y sigue sin aprobación. | DE-01, DE-16 |
| 11 | El supervisor rechaza todo. | RECHAZADA; el almacenista quita el EPP (y los naranjas) y puede entregar la herramienta de contexto. | DE-06, A-07 |
| 12 | El supervisor rechaza un renglón sin motivo. | 422 `DATOS_INVALIDOS` con `regla: "DE-06"`; no se guarda nada. | DE-06 |
| 13 | El almacenista intenta confirmar con un renglón rechazado. | 409 `APROBACION_INVALIDA` con el renglón y la causa `RECHAZADO`. | DE-08 |
| 14 | Después de aprobada, agrega unos lentes. | La aprobación ya no cubre; la pantalla pide volver a enviar con todo. | DE-13 |
| 15 | Después de aprobada, baja los guantes de 2 a 1. | Sigue valiendo; confirma sin pedir otra. | DE-13 |
| 16 | Después de aprobada, sube los guantes de 2 a 3. | Ya no cubre ese renglón: volver a enviar. | DE-13 |
| 17 | Después de aprobada, agrega un flexómetro en verde. | Sigue valiendo: es contexto. | DE-13 |
| 18 | Después de aprobada, cambia de proyecto en el selector (trabajador con dos proyectos). | Ya no cubre: el supervisor aprobó para otro proyecto. | DE-13, PR-09 |
| 19 | La solicitud se aprueba al minuto 14 de su vigencia. | La aprobación sirve 15 minutos desde que se aprobó, así que hay tiempo para la firma. | DE-09 |
| 20 | La aprobación vence antes de confirmar (la red falló y el reintento llegó tarde). | 409 `AUTORIZACION_INVALIDA` («La autorización venció»); se reenvía con los mismos renglones y la firma se conserva porque no cambió nada. | DE-09, DE-03 |
| 21 | Se pierde la red al confirmar y se reintenta a tiempo. | Mismo `id_cliente` del vale: se guarda una vez y la autorización se usa una vez. | A-03, E-28 |
| 22 | Un supervisor resuelve con su celular y otro con PIN en el mostrador al mismo tiempo. | Gana la primera resolución que bloquea la fila; la otra recibe 409 `AUTORIZACION_RESUELTA`. | DE-11 |
| 23 | El almacenista intenta aprobar su propia solicitud con su PIN. | 403 `AUTORIZACION_PROPIA` (A-05). Solo el supervisor que captura se aprueba el despacho, y sin solicitud (DE-07). | A-05, DE-07 |
| 24 | El supervisor que aprobó intenta confirmar el vale en el dispositivo del almacenista. | 403 `AUTORIZACION_PROPIA`: quien confirma no puede ser quien aprobó. | A-05 |
| 25 | Un supervisor de HYL escribe su PIN en el mostrador de Midrex. | 403 `SIN_PERMISO` («Ese usuario no puede autorizar en este almacén»). | A-01 |
| 26 | Al almacenista lo cambian de almacén mientras espera. | Al confirmar, 409 `ALMACEN_CAMBIO`; el borrador se conserva. La aprobación de Midrex no sirve en el almacén nuevo. | AC-13, A-03 |
| 27 | Un artículo pasa de una categoría de herramienta a una de EPP mientras se espera. | Al confirmar, ese renglón ya necesita aprobación y no está cubierto: 409 `APROBACION_INVALIDA` (o `REQUIERE_APROBACION_DESPACHO` si no hay solicitud). | DE-01, DE-16 |
| 28 | Dos almacenistas atienden al mismo trabajador en dos ventanillas. | Cada uno manda su solicitud; al confirmar el segundo, el límite se recalcula con lo que ya se llevó y puede quedar en naranja (409 `VALE_CAMBIO`), lo que pide otra aprobación. | DE-16, L-02 |
| 29 | Hay 10 borradores en espera y el almacenista quiere otro. | La pantalla pide terminar o descartar uno antes. | DE-15 |
| 30 | En la resolución múltiple una solicitud trae excedente. | Esa responde con error («Ábrela para revisarla») y las demás se aprueban. | DE-12 |
| 31 | En la resolución múltiple una ya la resolvió el otro supervisor. | Esa responde `AUTORIZACION_RESUELTA`; las demás siguen. | DE-11, DE-12 |
| 32 | El supervisor tiene el celular y la computadora con avisos. | Le llegan a los dos; al resolver en uno, el otro recibe el reemplazo. | NT-02, NT-06 |
| 33 | El supervisor cierra sesión en su celular. | La aplicación borra la suscripción antes de salir; si no pudo (sin red), el servidor no envía a una familia cerrada y la marca revocada. | NT-01 |
| 34 | Le restablecen la contraseña al supervisor (cierra todas sus sesiones). | Sus suscripciones dejan de recibir hasta que entre de nuevo y la aplicación las vuelva a registrar. | NT-01, AC-22 |
| 35 | El servicio de push responde 410 (el navegador se desinstaló o borró los datos). | La suscripción se marca revocada y no se vuelve a intentar. | NT-07 |
| 36 | El servidor no tiene las claves VAPID configuradas. | `GET /api/notificaciones/clave-publica` responde 404 `NO_ENCONTRADO` («Los avisos no están configurados en este servidor») y la pantalla esconde «Activar avisos». Todo lo demás funciona con el contador. | NT-08 |
| 37 | Se cambian las claves VAPID del servidor. | Las suscripciones viejas fallan; al abrir la aplicación, el navegador nota que la clave cambió, borra su suscripción y registra una nueva (sin volver a pedir permiso). | NT-01 |
| 38 | Un aviso llega después de que la solicitud venció (el celular estuvo apagado 14 minutos). | Al tocarlo dice «Venció a las 10:55»; no se puede resolver. | NT-04, DE-09 |
| 39 | El supervisor recibe un aviso de un almacén que ya no está en su conjunto. | Al abrirlo, 404: «Ya no puedes ver esta solicitud». | NT-02, AC-06 |
| 40 | El Administrador despacha EPP en Kepler. | Tiene `autorizaciones.resolver` en todos los almacenes: aprobación propia (DE-07). | DE-07 |
| 41 | Devolución de un casco en un almacén con aprobación. | No pide nada: la devolución nunca se bloquea. | DE-01, SM-05 |
| 42 | Cancelar y rehacer (K-05) una entrega de EPP. | El borrador nuevo se evalúa completo y, si el despacho es con aprobación, se vuelve a enviar: la autorización del vale cancelado sigue USADA. | K-05, A-03 |

## Fuera de alcance

- Notificaciones por correo, SMS o WhatsApp, y avisos que mande una tarea programada del servidor (mvp-scope).
- Avisos push al **almacenista** (por ejemplo, «tu solicitud se aprobó»): espera en pantalla y en «En espera» (decisión abierta 6).
- Recordatorios automáticos a mitad de la vigencia y aviso de «venció».
- Turnos, horarios de avisos o guardias: el sistema no sabe quién está de turno.
- Que el Supervisor cambie la autonomía (D-07: por ahora solo el Administrador).
- Que una solicitud de despacho pase de un dispositivo a otro (el borrador vive en el dispositivo).
- Un tablero de tiempos de respuesta de los supervisores.
- Push dentro de la app de Android de Capacitor (FEAT-020) y app nativa para el supervisor (D-14).

## Criterios de aceptación

- **CA-01 (DE-01).** Dado Midrex con aprobación y Ana sin autonomía, cuando evalúa una entrega con un casco, entonces la evaluación trae `requiere_aprobacion_despacho: true`, el casco trae `requiere_aprobacion: true`, `puede_confirmar` es falso y el nivel del renglón es el mismo que daría sin esta feature.
- **CA-02 (DE-01).** Dada una entrega solo de herramienta, cuando se evalúa, entonces `requiere_aprobacion_despacho` es falso y el vale se confirma como hoy.
- **CA-03 (DE-01, SM-05).** Dada una devolución de EPP en un almacén con aprobación, entonces no se pide aprobación.
- **CA-04 (DE-03).** Dado un vale con EPP sin aprobar, cuando se manda `POST /api/vales` sin `autorizacion_id`, entonces responde 409 `REQUIERE_APROBACION_DESPACHO` y no guarda nada; y la interfaz no muestra el paso de firma.
- **CA-05 (DE-04).** Dado un vale con dos renglones de EPP, un naranja de herramienta y un marro verde, cuando se envía a aprobación, entonces se crea una sola autorización `DESPACHO` con tres renglones que se resuelven y uno de contexto.
- **CA-06 (DE-04, A-06).** Dado un renglón en rojo, cuando se envía a aprobación, entonces responde 422 `RENGLON_NO_AUTORIZABLE` y no se crea nada.
- **CA-07 (DE-04).** Dadas dos peticiones con el mismo `id_cliente` y el mismo cuerpo, entonces se crea una sola solicitud y se manda un solo aviso.
- **CA-08 (DE-05, A-02).** Dada una solicitud de despacho sin naranjas y sin nota, entonces se acepta con el motivo «Despacho de EPP»; y dada una con un naranja sin motivo, entonces responde 422.
- **CA-09 (DE-06).** Dado un supervisor que aprueba 3 de 4 renglones y rechaza 1 con motivo, entonces la autorización queda APROBADA con `renglones_resueltos` y el rechazo sin motivo responde 422.
- **CA-10 (DE-06).** Dado un rechazo de todos los renglones, entonces la autorización queda RECHAZADA.
- **CA-11 (DE-07).** Dado Luis (con `autorizaciones.resolver` en Midrex) capturando una entrega de EPP sin naranjas, entonces no se pide solicitud, el vale se confirma y sus movimientos de EPP llevan `DE-07`; y dado un naranja en ese vale, entonces se pide una autorización EXCEDENTE que Luis no puede resolver (403 `AUTORIZACION_PROPIA`).
- **CA-12 (DE-08).** Dado un vale con un renglón rechazado, cuando se confirma, entonces responde 409 `APROBACION_INVALIDA` con ese renglón.
- **CA-13 (DE-08).** Dado un vale aprobado con un renglón de contexto quitado, entonces se confirma con la misma autorización.
- **CA-14 (DE-09).** Dada una solicitud aprobada al minuto 14, entonces su `vence_en` es 15 minutos después de `resuelta_en` y se puede confirmar en ese plazo; y dada una pendiente con más de 15 minutos, entonces se informa VENCIDA y no se resuelve.
- **CA-15 (DE-10).** Dado que ningún supervisor de Midrex tiene suscripción vigente, cuando Ana envía, entonces la respuesta trae `avisados: 0` y la pantalla lo dice.
- **CA-16 (DE-11).** Dadas dos resoluciones simultáneas de la misma solicitud, entonces una gana y la otra responde 409 `AUTORIZACION_RESUELTA` con `detalles.resuelta_por`.
- **CA-17 (DE-12).** Dadas 12 solicitudes sin excedente y una con excedente, cuando el supervisor aprueba las 13 en grupo, entonces se aprueban 12 y la otra responde con error; y la lista sale de la más antigua a la más nueva.
- **CA-18 (DE-13).** Dada una aprobación, cuando se agrega un renglón de EPP o se sube la cantidad de uno aprobado, entonces la evaluación con esa `autorizacion_id` marca la aprobación como insuficiente y la confirmación responde 409 `APROBACION_INVALIDA`; y cuando solo se baja una cantidad, entonces se confirma.
- **CA-19 (DE-14).** Dado el Administrador, cuando apaga la aprobación de Contratistas con motivo, entonces la siguiente evaluación de un almacenista de Contratistas no pide aprobación y queda la auditoría `almacen.autonomia` con antes, después y motivo; sin motivo, 422; y sin `despacho.autonomia`, 403.
- **CA-20 (DE-14).** Dado el Administrador, cuando prende `despacho_autonomo` a Pedro, entonces Pedro despacha EPP sin aprobación y Ana no.
- **CA-21 (DE-15).** Dado un borrador en espera, cuando el almacenista empieza otra entrega y la primera se aprueba, entonces el contador «En espera» lo muestra y al abrirlo continúa en la firma.
- **CA-22 (DE-16).** Dado un borrador evaluado con autonomía, cuando el Administrador la apaga y el almacenista confirma, entonces responde 409 `REQUIERE_APROBACION_DESPACHO` y el borrador se conserva.
- **CA-23 (DE-16).** Dado un renglón aprobado cuyas existencias se acabaron, cuando se confirma, entonces responde 409 `VALE_CAMBIO` con ese renglón en rojo; y quitándolo, se confirma con la misma aprobación.
- **CA-24 (NT-01).** Dado un supervisor, cuando carga la aplicación, entonces el navegador no pide permiso de avisos; solo al tocar «Activar avisos». Dado un usuario sin `autorizaciones.resolver`, cuando registra una suscripción, entonces responde 403.
- **CA-25 (NT-01).** Dado un supervisor con suscripción, cuando cierra la sesión de ese dispositivo, entonces la suscripción queda revocada y no recibe avisos.
- **CA-26 (NT-02).** Dada una solicitud de Midrex, entonces los avisos van a Luis y Marta (activos, con el permiso y con Midrex en su conjunto), no a Ana, no al supervisor de HYL y no al Administrador.
- **CA-27 (NT-03).** Dado un aviso de despacho, entonces su contenido trae almacén, trabajador, cantidad de artículos y quién lo pide, y no trae costos, CURP, NSS ni foto.
- **CA-28 (NT-05, NT-06).** Dadas tres solicitudes pendientes de Midrex, entonces el aviso dice «3 solicitudes por aprobar» con la misma etiqueta; y al resolverse una, los demás destinatarios reciben un reemplazo silencioso con la cuenta nueva.
- **CA-29 (NT-07).** Dado un servicio de push que falla, cuando se crea una solicitud, entonces la solicitud queda guardada y el error queda en `ultimo_error`; y dado un 410, entonces la suscripción queda revocada.
- **CA-30 (NT-09).** Dado un supervisor con suscripción, cuando pide el aviso de prueba, entonces le llega solo a ese dispositivo; y una segunda petición antes de 10 segundos responde 429.

## Módulos relacionados conocidos

- `movimientos`: evaluación de la ENTREGA (`requiere_aprobacion_despacho`, `despacho.modo`, `requiere_aprobacion`, `aprobacion`), confirmación (DE-08, DE-16, `REQUIERE_APROBACION_DESPACHO`, `APROBACION_INVALIDA`), reglas `DE-01`, `DE-07`, `DE-14` en `movimiento.reglas`, verificador de renglones (`verificador.py`) que ahora clasifica EPP, EXCEDENTE y CONTEXTO. Sigue siendo el único que escribe vales y movimientos.
- `autorizaciones`: `tipo`, `renglones_resueltos`, `id_cliente`, resolución parcial, resolución múltiple, vigencia recorrida al aprobar, `AUTORIZACION_RESUELTA` con detalle, lista por antigüedad con proyecto y contexto. Llama a `notificaciones` después del commit.
- `notificaciones` (**módulo nuevo**): `suscripcion_push`, clave pública, envío con VAPID, destinatarios, agrupación, reemplazo, revocación. No importa a `movimientos`.
- `almacenes`: `almacen.despacho_epp_con_aprobacion` y su `PATCH`.
- `acceso`: `usuario.despacho_autonomo` y su `PATCH`; permiso `despacho.autonomia`; destinatarios por permiso y conjunto de almacenes; validez de la familia de sesión.
- `catalogo`: lectura de `categoria.tipo`.
- `auditoria`: `almacen.autonomia`, `usuario.autonomia`, `autorizacion.aprobar` y `autorizacion.rechazar` con `renglones_resueltos`, `notificaciones.suscribir`.
- Frontend: `routes/operacion/entregar.tsx`, `componentes/entrega/` (hoja de aprobación nueva en lugar de `hoja-autorizacion.tsx` cuando aplica, espera, «En espera»), `routes/supervision/` (lista y detalle `/autorizaciones/:id`), `sesion/contadores.ts` (contador «En espera»), `public/sw.js` (push), administración de almacenes y usuarios, `routes.ts`.

## Cambios de datos o API esperados

### Datos (una migración de Alembic)

| Tabla o columna | Qué guarda |
|---|---|
| `almacen.despacho_epp_con_aprobacion` (bool, no nulo, `true` por omisión) | DE-14. Los almacenes que ya existen quedan con aprobación. |
| `usuario.despacho_autonomo` (bool, no nulo, `false` por omisión) | DE-14. |
| `autorizacion.tipo` (`EXCEDENTE`, `DESPACHO`, `TRASLADO`; no nulo) | Las que ya existen quedan `EXCEDENTE`. `TRASLADO` lo usa FEAT-015. |
| `autorizacion.renglones_resueltos` (JSON, nulo) | `[{renglon, codigo, cantidad, decision: "APROBADO" \| "RECHAZADO", motivo}]`. Nulo en las anteriores: si están APROBADA o USADA, todos sus renglones cuentan como aprobados. |
| `autorizacion.id_cliente` (texto, único, nulo) | DE-04: evita la solicitud repetida por doble toque. **No está en la tabla 5.1 del maestro** (ver decisión abierta 10). |
| `autorizacion.detalle` (sin cambio de columna) | Gana por renglón `clase` (`EPP`, `EXCEDENTE`, `CONTEXTO`) y `observacion`; arriba, `nota` y `proyecto` (`{id, clave, nombre}`, con FEAT-013). |
| `suscripcion_push` (`id`, `usuario_id`, `familia_id`, `endpoint`, `p256dh`, `auth`, `agente`, `creada_en`, `ultimo_envio`, `ultimo_error`, `revocada_en`) | Una suscripción por dispositivo. `endpoint` único entre las vigentes: registrar el mismo `endpoint` actualiza la fila (otro usuario en el mismo navegador la toma y la anterior queda revocada). `agente` se resume como en AC-21. Dueño: `notificaciones`. |
| Permiso `despacho.autonomia` | Solo Administrador. Requiere `almacenes.administrar` o `acceso.usuarios` para ver las pantallas donde se usa. |

Invariantes nuevas: una autorización `DESPACHO` APROBADA tiene al menos un renglón APROBADO; una RECHAZADA no tiene ninguno; un vale con renglones de EPP en un despacho con aprobación lleva `autorizacion_id` de tipo DESPACHO o sus movimientos de EPP llevan `DE-07` o `DE-14`.

Variables de `.env` (en `.env.example`): `VAPID_CLAVE_PUBLICA`, `VAPID_CLAVE_PRIVADA` (secreto), `VAPID_CONTACTO` (`mailto:` del responsable del sistema). Se generan una vez con un comando nuevo de mantenimiento (`uv run python -m app.mantenimiento generar-claves-vapid`, que solo imprime el par). Sin ellas, la aplicación arranca y los avisos quedan apagados (con `ENTORNO=produccion` solo avisa en el registro).

**Dependencia a aprobar:** `pywebpush` (cifrado del contenido según RFC 8291 y firma VAPID; trae `py-vapid` y `http-ece`). La alternativa sin dependencia nueva es firmar el token VAPID con PyJWT y `cryptography` (ya instalados), cifrar con `cryptography` y enviar con `httpx`; es más código propio en una parte delicada (cifrado). Recomendación: `pywebpush`. Ver ADR-013.

### API

Cambia:

| Endpoint | Permiso | Cambio |
|---|---|---|
| `POST /api/vales/evaluar` | Según el tipo | En ENTREGA agrega arriba `requiere_aprobacion_despacho` (bool) y `despacho: {modo}` con `modo`: `CON_APROBACION`, `AUTONOMO_ALMACEN`, `AUTONOMO_USUARIO`, `SUPERVISOR` o `NO_APLICA` (sin EPP). Por renglón: `es_epp`, `requiere_aprobacion` y, si el cuerpo trae `autorizacion_id`, `aprobacion` (`APROBADO`, `RECHAZADO`, `NO_INCLUIDO`, `CANTIDAD_MAYOR`, `PENDIENTE` o `null`) y `motivo_rechazo`. `puede_confirmar` es falso si falta la aprobación (DE-02). Con `autorizacion_id` de una aprobación que ya no cubre, `autorizacion_error` lo explica (DE-13). |
| `POST /api/vales` | Según el tipo | Nuevos 409: `REQUIERE_APROBACION_DESPACHO` (`detalles: {regla: "DE-01", renglones: [{renglon, codigo}]}`) y `APROBACION_INVALIDA` (`detalles: {regla: "DE-08", renglones: [{renglon, codigo, causa: "RECHAZADO" \| "NO_INCLUIDO" \| "CANTIDAD_MAYOR"}]}`). `AUTORIZACION_INVALIDA` se queda para la autorización misma (no aprobada, vencida, usada, de otro almacén, trabajador o proyecto, o de un tipo que no corresponde). |
| `GET /api/vales/{id}` | `vales.ver` | Agrega `despacho: {modo: "APROBADO" \| "PROPIO" \| "AUTONOMO" \| null, aprobo: {id, nombre} \| null}`, derivado de `autorizacion_id` y de `movimiento.reglas`. `valido` no cambia. |
| `POST /api/autorizaciones` | `entregas.crear` | Cuerpo: `{tipo: "DESPACHO" \| "EXCEDENTE" (por omisión), trabajador_id, almacen_id?, proyecto_id?, id_cliente, motivo?, nota?, renglones: [{codigo, cantidad, observacion?}]}`. `motivo` es obligatorio en EXCEDENTE y en un DESPACHO con naranjas; en un DESPACHO sin naranjas se ignora y se guarda «Despacho de EPP». Responde 201 `{id, tipo, estado, vence_en, avisados}` (200 si el `id_cliente` ya existía con el mismo cuerpo; 409 `CONFLICTO` si el cuerpo es distinto). 422 `RENGLON_NO_AUTORIZABLE` con `detalles: {codigo, regla, nivel, motivos}` por un rojo, por un `tipo` que no corresponde (`regla` `DE-01` o `DE-04`) o, en EXCEDENTE, por un renglón que no es naranja (como hoy). |
| `GET /api/autorizaciones/{id}` | Sesión | Agrega `tipo`, `renglones` con `clase`, `renglones_resueltos`, `nota`, `proyecto`, `trabajador {id, nombre, numero_empleado, tiene_foto}`, `almacen {id, clave, nombre}` y `servidor_ahora` (para calcular lo que falta sin el reloj del dispositivo). |
| `GET /api/autorizaciones?estado=&tipo=&almacen_id=` | `autorizaciones.resolver` | Ordenada de la más antigua a la más nueva. Cada elemento agrega `tipo`, `proyecto`, `almacen`, `trabajador.tiene_foto`, `incluye_excedente`, `renglones` con `clase` y `servidor_ahora`. Con FEAT-013, las de todos los almacenes de su conjunto. |
| `POST /api/autorizaciones/{id}/resolucion` | Sesión (se verifica en el servicio, como hoy) | Cuerpo: `{decision?: "APROBAR" \| "RECHAZAR", motivo?, renglones?: [{renglon, decision: "APROBAR" \| "RECHAZAR", motivo?}], usuario?, pin?}`. Se manda `decision` (todo) **o** `renglones` (uno por cada renglón que se resuelve; los de contexto no se mandan). `RECHAZAR` total pide `motivo`; cada renglón rechazado pide `motivo` (422 `DATOS_INVALIDOS` con `regla: "DE-06"`). Responde la solicitud con `renglones_resueltos`. 409 `AUTORIZACION_RESUELTA` trae `detalles: {estado, resuelta_por: {id, nombre} \| null, resuelta_en, medio}`. Siguen 403 `AUTORIZACION_PROPIA`, 403 `PIN_INCORRECTO` y 429 `DEMASIADOS_INTENTOS`. |

Nuevos:

| Endpoint | Permiso | Qué hace |
|---|---|---|
| `POST /api/autorizaciones/resolucion-multiple` | `autorizaciones.resolver` | Cuerpo `{resoluciones: [{id, decision: "APROBAR" \| "RECHAZAR", motivo?}]}`, de 1 a 50. Solo desde la sesión de quien resuelve (sin PIN). `RECHAZAR` pide `motivo` en cada una. Cada una se resuelve en su propia transacción y se reintenta ante un interbloqueo como la individual. Responde 200 `{resultados: [{id, estado, error: {codigo, mensaje} \| null}]}`. Errores por solicitud: `AUTORIZACION_RESUELTA`, `AUTORIZACION_PROPIA`, `NO_ENCONTRADO` y `RENGLON_NO_AUTORIZABLE` (con `regla: "DE-12"`) si se aprueba en grupo una que incluye excedente. |
| `PATCH /api/almacenes/{id}/autonomia` | `despacho.autonomia` | `{despacho_epp_con_aprobacion: bool, motivo}`. Responde la ficha del almacén. Sin motivo, 422; almacén inexistente, 404. Si el valor no cambia, 200 sin registro de auditoría. |
| `PATCH /api/usuarios/{id}/autonomia` | `despacho.autonomia` | `{despacho_autonomo: bool, motivo}`. Responde el usuario. Sin motivo, 422; usuario inexistente, 404. Se guarda aunque el usuario no pueda entregar; solo tiene efecto si puede. |
| `GET /api/notificaciones/clave-publica` | Sesión | `{clave_publica}` (la VAPID, en base64url). 404 si no está configurada. |
| `POST /api/notificaciones/suscripciones` | `autorizaciones.resolver` | `{endpoint, keys: {p256dh, auth}}` como lo entrega el navegador. Liga la suscripción al usuario y a la familia de la sesión. Responde 201 `{id, creada_en}` (200 si ya existía para esa familia). `endpoint` debe ser `https` y de un máximo de 1000 caracteres; si no, 422. |
| `DELETE /api/notificaciones/suscripciones/{id}` | Sesión | Revoca una suscripción **propia** (404 si es de otro). 204. |
| `POST /api/notificaciones/prueba` | `autorizaciones.resolver` | Manda un aviso de prueba a las suscripciones de la familia de la sesión. Responde `{enviadas, fallidas}` (cero y cero si el dispositivo no tiene suscripción). 429 `DEMASIADOS_INTENTOS` si se pide antes de 10 segundos. |

Contenido de un aviso (lo lee el service worker; menos de 4 KB):

```json
{
  "evento": "NUEVA",
  "tipo": "DESPACHO",
  "autorizacion_id": "01a1…",
  "almacen": { "clave": "MDX", "nombre": "Midrex" },
  "pendientes": 1,
  "titulo": "Midrex · EPP por aprobar",
  "cuerpo": "Para Juan Pérez: 4 artículos de EPP. Lo pide Ana Ruiz.",
  "url": "/autorizaciones/01a1…",
  "etiqueta": "autorizaciones-01a0…",
  "silencioso": false
}
```

`evento` es `NUEVA`, `RESUELTA` (reemplazo, NT-06) o `PRUEBA`. Con `pendientes` mayor que 1, `url` es `/autorizaciones` y el título dice la cuenta.

## Restricciones y compatibilidad

- **Orden con FEAT-013.** El maestro pone FEAT-014 antes que FEAT-013. Mientras FEAT-013 no esté, no hay proyecto en la solicitud (se omite) y los destinatarios salen de `usuario.almacen_id`. Si se construyen en paralelo, FEAT-013 entra primero a `movimientos` y esta feature se rebasa sobre ella (sección 7 del maestro).
- **Las autorizaciones que ya existen** quedan `EXCEDENTE` y siguen sirviendo igual. El flujo 7 de hoy (excedente con motivo, PIN o celular) se conserva para los vales que no piden aprobación del despacho.
- **`AUTORIZACION_VIGENCIA_MINUTOS`** no cambia de valor; cambia que la aprobada se recorre al aprobarse (DE-09).
- **Movimientos y vales** no se actualizan ni se borran; nada de esta feature los modifica. La autorización sí cambia de estado, como hoy.
- **HTTPS.** Web Push necesita un contexto seguro: funciona por el túnel de Cloudflare y en `localhost` para desarrollo; no por la IP de la red local sin HTTPS.
- **Salida a Internet.** El servidor necesita poder conectarse por HTTPS a los servicios de push de los navegadores (Google, Mozilla, Apple, Microsoft). El túnel solo cubre la entrada.
- **Service worker.** Hoy solo sirve para instalar y para los archivos estáticos (security-model). Gana tres manejadores (`push`, `notificationclick`, `pushsubscriptionchange`) y sigue sin guardar nada de `/api/*`.
- **Permisos en el router.** Todos los endpoints nuevos declaran su permiso en el router; la lista de rutas que lo verifican en el servicio (AGENTS.md) no crece.
- **Textos** en español llano: «Necesita aprobación», «Enviar a aprobación», «Aprobada por…», nunca «autorización DESPACHO» ni «push».

## Riesgos

- **El supervisor no tiene tiempo** (principio de las reglas, plática del 3 de octubre). Si aprobar todo el EPP lo satura, la operación se detiene. Mitigación: resolución múltiple, agrupación de avisos y autonomía por almacén o almacenista (incongruencia 4 del maestro).
- **El push no llega** (sin señal, Doze de Android, iPhone sin instalar, permiso negado). Mitigación: contador, lista, `avisados`, PIN en el mostrador (NT-08, DE-10).
- **Fila en el mostrador** el primer día de un mantenimiento. Mitigación: «Atender a otro mientras» y «En espera» (DE-15).
- **Dependencia nueva** (`pywebpush`) por aprobar; sin ella, cifrado propio.
- **Choque con FEAT-013 y FEAT-015** en `movimientos` y `autorizaciones` (evaluación de la ENTREGA, `tipo`, resolución). Se integran en el orden del maestro.
- **Pruebas que cambian.** Las de autorizaciones y entregas que suponen EPP sin aprobación (`test_autorizaciones*`, guion del PDF) necesitan almacén autónomo o una aprobación en medio. Se ajustan, no se borran. El guion del PDF (p. 2) pide «entregar EPP»: la prueba de integración debe incluir el paso de aprobación.
- **Avisos que se acumulan** en un supervisor de dos almacenes. Mitigación: etiqueta por almacén.

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla, con su ID en el nombre (`test_de_01_…` a `test_de_16_…`, `test_nt_01_…` a `test_nt_09_…`). El envío de push se prueba con un cliente falso (sin salir a Internet): destinatarios, contenido, reemplazo, 404/410 y que un fallo no deshace la solicitud.
- Prueba de concurrencia de DE-11 (dos resoluciones a la vez) y de la resolución múltiple con una ya resuelta.
- Prueba de permisos: `despacho.autonomia` (con él responde, sin él 403), `autorizaciones.resolver` en las suscripciones.
- El guion del PDF sigue pasando, con la aprobación en medio.
- Migración arriba y abajo.
- Recorrido manual: Ana en Chrome de Android y Luis en otro celular Android por el túnel (aviso con la pantalla bloqueada); Luis en iPhone con la PWA instalada; aprobación parcial; resolución múltiple de 10; PIN en el mostrador; autonomía prendida y apagada a medio vale.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md):
  - **F-04**: el supervisor valida el despacho de EPP cuando el almacén o el almacenista no tienen autonomía (DE-01); fuera de eso, sigue sin validar cada vale.
  - **A-01**: la solicitud también puede ser de despacho; se avisa por push a los supervisores del almacén (NT-02); el Administrador resuelve, pero no recibe avisos por omisión.
  - **A-02**: el despacho sin naranjas lleva el motivo del sistema «Despacho de EPP» (DE-05).
  - **A-03**: vale para los renglones aprobados con su cantidad **o menos**; los de contexto pueden cambiar; la aprobación puede ser parcial (DE-06, DE-08, DE-13).
  - **A-05**: excepción DE-07 (la captura del supervisor aprueba el despacho, no los excedentes).
  - **A-07**: también aplica a los renglones de EPP sin aprobación.
  - **SM-03**: el vale se confirma sin rojos, con los naranjas autorizados **y**, si el despacho pide aprobación, con los renglones de EPP aprobados.
  - Sección 7.3 (pasos de la entrega con la aprobación antes de la firma); sección nueva con DE-01 a DE-16 y NT-01 a NT-09; 5.4 (vigencia de la aprobada); sección 8 (`despacho.autonomia`, solo Administrador); prioridades (sección 9).
- [app-flow.md](../product/app-flow.md): flujo 6 (paso de aprobación, espera y «En espera»), flujo 7 (despacho, parcial, múltiple, avisos), ruta nueva `/autorizaciones/:id`, Almacenes y Usuarios (autonomía), menú de usuario (avisos).
- [api-contracts.md](../architecture/api-contracts.md): Vales, Autorizaciones, Almacenes, Usuarios, sección nueva Notificaciones y errores `REQUIERE_APROBACION_DESPACHO` y `APROBACION_INVALIDA`.
- [data-model.md](../architecture/data-model.md): columnas nuevas, `suscripcion_push`, invariantes y dueño del módulo `notificaciones`.
- [security-model.md](../architecture/security-model.md): el service worker gana los manejadores de push; amenazas nuevas (contenido visible en la pantalla bloqueada, suscripción ligada a la sesión y revocada al salir, clave VAPID privada en `.env`, conexiones salientes a los servicios de push); la autonomía como permiso de alto impacto con auditoría.
- [trd.md](../architecture/trd.md): `pywebpush` vuelve (si se aprueba); `BackgroundTasks` para los avisos; la sección 17 deja de excluir las notificaciones push (siguen excluidas las colas y las tareas programadas); la consulta periódica sigue siendo el respaldo.
- [mvp-scope.md](../product/mvp-scope.md): ya refleja la entrada de las notificaciones push y el riesgo aceptado (no se cambia aquí).
- [overview.md](../architecture/overview.md) y [AGENTS.md](../../AGENTS.md): módulo nuevo `notificaciones`.
- [ui-ux.md](../product/ui-ux.md): etiqueta «Necesita aprobación», pantalla de espera, tarjeta de solicitud con Aprobar/Rechazar por renglón, estado de los avisos.
- `.env.example`: variables VAPID.
- [guia-almacenista.md](../guia-almacenista.md) y [guia-por-rol.md](../guia-por-rol.md): el paso de aprobación y cómo activar los avisos.
- Tutorial (FEAT-010): el recorrido de Entregar con la aprobación simulada.

## Decisiones abiertas

1. **Retirar una solicitud pendiente.** Cuando el trabajador se va o el almacenista descarta el borrador, la solicitud sigue en la lista del supervisor hasta que vence. Propuesta: `POST /api/autorizaciones/{id}/retiro` (solo quien la pidió, solo PENDIENTE) con un estado nuevo `RETIRADA` y aviso de reemplazo. No está en la sección 5.4 del maestro; mientras no se apruebe, vence sola.
2. **¿El Administrador recibe avisos?** Por omisión no (NT-02). Opción: una preferencia por usuario «Recibir avisos de todos los almacenes».
3. **Turnos.** Los dos supervisores reciben todo a toda hora; el de día puede recibir avisos de madrugada. Opción: «Pausar avisos en este equipo» por horario. Por ahora, el «No molestar» del celular.
4. **Vigencia de la aprobada (DE-09).** Se propone recorrer `vence_en` a 15 minutos desde la aprobación; hoy la aprobada vence a los 15 minutos de **creada**, y una aprobación de último minuto deja segundos para firmar. Cambia el comportamiento de `validar_para_vale`.
5. **Dependencia `pywebpush` o cifrado propio.** Recomendación: `pywebpush`. Falta aprobarla (AGENTS.md: no se agregan dependencias sin aprobación).
6. **Aviso al almacenista** cuando se resuelve su solicitud. Por ahora no: espera en pantalla y en «En espera».
7. **«Volver a avisar»** a mitad de la vigencia sin crear otra solicitud. Por ahora no: se reenvía al vencer.
8. **Cambiar el proyecto invalida la aprobación (DE-13).** Se supone que sí, porque el consumo cuenta para el proyecto (D-13). Falta confirmarlo.
9. **Preguntas al track (sección 10 del maestro):** si el EPP al contratar también pide aprobación (se supone que sí) y si 15 minutos es un tiempo de espera aceptable en el mostrador.
10. **`autorizacion.id_cliente`.** Hace falta para DE-04 y no está en la tabla 5.1 del maestro; hay que agregarla allí o resolver el doble toque buscando una pendiente igual del mismo solicitante y trabajador en el último minuto.
11. **Aprobación parcial de un EXCEDENTE.** Se propone que también sea parcial (DE-06). Hoy es todo o nada.
12. **`despacho.autonomia` es un permiso.** Como cualquier permiso, un Administrador podría dárselo al Supervisor desde `/roles` sin cambiar código. D-07 dice «por ahora, solo el Administrador»: ¿se protege (como AC-32) o se deja configurable?
13. **Tope de borradores en espera** por dispositivo: se propone 10.

## Orden de construcción sugerido

1. **Datos y evaluación** (`movimientos`, `almacenes`, `acceso`): columnas, permiso, `requiere_aprobacion_despacho`, `REQUIERE_APROBACION_DESPACHO`, DE-07 y DE-14 en las reglas del movimiento. Con esto el EPP ya no sale sin aprobación.
2. **Solicitud de despacho y resolución** (`autorizaciones`): tipo, parcial, `APROBACION_INVALIDA`, vigencia, `AUTORIZACION_RESUELTA` con detalle, resolución múltiple.
3. **Interfaz del almacenista:** paso de aprobación, espera, «En espera».
4. **Interfaz del supervisor:** lista, detalle `/autorizaciones/:id`, selección múltiple. En este punto todo funciona con el contador.
5. **Notificaciones** (`notificaciones`, service worker, «Activar avisos», prueba). Si falta tiempo, se corta aquí: el despacho con aprobación funciona sin push.
6. **Autonomía en pantalla** (`/almacenes`, `/usuarios`).
