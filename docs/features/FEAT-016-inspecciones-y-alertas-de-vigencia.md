# FEAT-016: Inspecciones y alertas de vigencia

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Es el paso 5 del orden de construcción de la [iteración 01](../releases/iteration_01/README.md) (sección 7). Cambia P-01, P-04, E-11, I-03, el parámetro «Aviso de inspección por vencer» de 5.4 y la sección 8 (permiso `inspecciones.ver`). Reglas nuevas P-09 a P-17. Si algo de aquí contradice el [documento maestro](../releases/iteration_01/README.md), manda el maestro.

## Problema u oportunidad

En la plática del 8 de octubre el track pidió (hoja 1, puntos 2 a 4):

1. Definir bien las reglas del **equipo de alturas**, entre ellas las inspecciones, y quién las hace: ¿almacenista o supervisor?
2. Poder **modificar la vigencia** de la inspección.
3. **Alertas** para el equipo que pide inspección: cuando a un equipo de alturas le falte poco para vencer (por ejemplo, 10 días), poder **configurar** el aviso y **verlo**. **Rehacer el flujo de la pantalla.**

Hoy las reglas del equipo de alturas están repartidas en siete secciones (E-05, E-06, E-11, SM-04, P-01 a P-08, I-03, CF-09). El aviso de «por vencer» es un número fijo de 7 días en el código (`DIAS_AVISO_INSPECCION` en `movimientos/evaluador.py`) y solo se ve en un renglón amarillo al entregar y en una tarjeta del Inicio que no lleva a ninguna lista. No hay una pantalla que diga qué piezas vencieron, cuáles están por vencer y dónde está cada una. La inspección se registra desde la ficha de la pieza, una por una, en una hoja que no muestra el historial ni la fecha que va a quedar.

## Objetivo

Que el almacenista sepa cada día qué equipo de alturas tiene que inspeccionar y dónde está, que lo inspeccione en pocos toques desde el celular (una pieza o varias seguidas), y que la empresa configure con cuánta anticipación se avisa y cuánto dura una inspección, con todas las reglas del equipo de alturas escritas en un solo lugar.

## Historias de usuario

Como almacenista, quiero abrir una lista con el equipo de alturas vencido y por vencer de mi almacén, para inspeccionarlo antes de que alguien lo pida.

Como almacenista, quiero escanear diez arneses seguidos y marcarlos Aptos de un toque, abriendo solo el que tiene algo mal, para no perder la mañana.

Como supervisor, quiero ver qué arnés vencido tiene un trabajador y desde cuándo, para pedirle que lo devuelva.

Como encargado del catálogo, quiero decir que los retráctiles avisan 15 días antes y los arneses 10, para que cada equipo avise con el tiempo que necesita su revisión.

Las historias se escriben en `docs/stories/` al empezar la construcción.

## Reglas del equipo de alturas en un solo lugar

Resumen de lo que ya existe y de lo que cambia esta feature. Cada regla se sigue escribiendo completa en [reglas-de-negocio.md](../product/reglas-de-negocio.md); esta tabla es el índice que pidió el track.

| Tema | Qué dice | Reglas |
|---|---|---|
| Qué es | La categoría inicial «Equipo de alturas»: EPP, por pieza, retornable, con inspección vigente como requisito (arnés, bandola, gancho doble de vida, retráctil). Cada pieza tiene código y, si se conoce, número de serie. | 5.1, CF-06, SG-07 |
| Alta | Cada pieza entra con su código. La inspección inicial es opcional; sin ella la pieza queda «Sin inspección» y no se entrega. La fecha de esa inspección no puede ser posterior a hoy. | I-02, I-03, P-17 |
| Quién inspecciona | Quien tiene `piezas.inspeccionar`: de inicio, almacenista y supervisor. El flujo y la pantalla se diseñan para el **almacenista**. | P-01, D-10 |
| Qué se revisa | Etiquetas, costuras, cintas, herrajes y conectores. Cada punto se marca Bien, Mal o No aplica. | P-01, P-14 |
| Resultado | Apto o No apto. No apto pide observación; Apto con algún punto Mal también. Solo una inspección regresa a Apta una pieza No apta. | P-01, P-03, P-14 |
| Cuánto dura | Fecha de la inspección más la vigencia del artículo (180 días si nadie la cambia). | 5.4, P-09 |
| Modificar la vigencia | Dos cosas distintas: el **periodo** del artículo o de la categoría (`catalogo.administrar`) y la **fecha** de una pieza (`piezas.ajustar_vigencia`, con motivo y sin pasar del tope; quien inspeccionó no ajusta la suya). | P-07, P-09 |
| Aviso | La inspección que vence en N días o menos (hoy incluido) da amarillo al entregar. N se configura en general, por categoría y por artículo. | E-11, P-10 |
| Entrega | No apta, en mantenimiento, en calibración, en baja, sin inspección o vencida: **rojo**. Nadie lo autoriza en el mostrador: solo se resuelve inspeccionando. | E-05, E-06, SM-04, A-06 |
| Dónde verlo | Pantalla Inspecciones (vencidas, por vencer y sin inspección), tarjeta del Inicio y contador del menú. | P-11 a P-13 |
| Con un trabajador | Si vence mientras la tiene un trabajador, aparece en Vencidas con quién la tiene y desde cuándo, para pedirle que la devuelva. Su devolución nunca se bloquea. | P-04, P-12, SM-05 |
| Avisos fuera de la pantalla | No hay tarea programada en el servidor. En la app de Android, notificación local. | P-15 |
| Activar la inspección en un artículo | Sus piezas quedan sin inspección vigente y no se entregan hasta inspeccionarse; lo ya entregado no se recoge. | CF-08, CF-09 |
| Daño | Cualquiera con `piezas.inspeccionar` la marca No apta con observación; una devolución Dañada la deja No apta. | P-03, V-05 |
| Mantenimiento y calibración | No se entrega ni se inspecciona hasta regresarla al servicio. | P-06, P-17 |
| Traslado | Una pieza No apta se puede trasladar y conserva su estado. | X-04 |
| Pérdida o baja | Lo decide el supervisor; es un movimiento a Baja. | P-05 |
| Serie pendiente | Se entrega con aviso y se inspecciona igual; quien tiene permiso registra la serie. | E-29, P-08 |
| Alto valor fuera | Las piezas de alturas en manos de trabajadores cuentan en la tarjeta «Alto valor fuera del almacén». | SG-04, SG-06 |
| Capacitación del trabajador | La habilitación vigente (por ejemplo, curso de alturas) es un requisito que se activa por artículo; sigue en P2. | CF-06, E-08 |

## Reglas

| ID | Regla | Origen |
|---|---|---|
| P-09 | **Dos formas de modificar la vigencia, y las dos se ven.** (1) **Periodo**: cuántos días dura una inspección de un artículo (`articulo.vigencia_inspeccion_dias`, que propone la categoría, CF-02; 180 por omisión). Lo cambia quien tiene `catalogo.administrar` y aplica a las inspecciones que se registren desde ese momento: no recalcula la fecha de las piezas ya inspeccionadas (CF-08). (2) **Fecha de una pieza**: el ajuste de P-07 con `piezas.ajustar_vigencia`. La ficha de la pieza y la pantalla Inspecciones muestran las dos: «Una inspección dura 180 días» y «Esta pieza vale hasta 12/03/2027», con el botón «Ajustar fecha» para quien tiene el permiso. Al acortar el periodo de un artículo, la pantalla dice cuántas de sus piezas quedan con una fecha más lejana que el periodo nuevo y no las cambia. | Plática del 8 oct 2026 (hoja 1, punto 3); decisión de este brief |
| P-10 | **Aviso configurable.** Los días de aviso antes del vencimiento se resuelven así: el del **artículo** (`articulo.dias_aviso_inspeccion`), si no tiene, el de su **categoría** (`categoria.dias_aviso_inspeccion`), y si tampoco, el **general** (`INSPECCION_AVISO_DIAS`, 7). Nulo es «hereda». Es un entero de **1 a 90**. Se cambia con `catalogo.administrar` y queda en el registro de cambios (CF-15). La herencia es **en vivo**: a diferencia de la plantilla (CF-02, que se copia al crear), cambiar el valor de una categoría cambia desde ese momento a sus artículos que heredan, no a los que tienen el suyo. E-11, la pantalla Inspecciones, la tarjeta del Inicio, el contador del menú, el tablero (`inspecciones_por_vencer`) y la app de Android usan el valor resuelto de cada artículo. Si el aviso resuelto es igual o mayor que la vigencia del artículo, se avisa al guardar y no se bloquea. | Plática del 8 oct 2026 (hoja 1, punto 4); D-11 |
| P-11 | **Pantalla Inspecciones** (`/inspecciones`, permiso `inspecciones.ver`), primero celular. Lista las piezas de artículos que requieren inspección, sin contar las que están en baja, en tres pestañas: **Vencidas** (Aptas con `inspeccion_vigente_hasta` anterior a hoy), **Por vencer** (Aptas que vencen entre hoy y hoy más el aviso resuelto, hoy incluido) y **Sin inspección** (Aptas sin fecha de vigencia: nunca inspeccionadas o con la inspección recién activada, CF-09). Las No aptas, en mantenimiento y en calibración no entran en las pestañas; la pantalla dice cuántas hay y enlaza a Seguimiento. Cada pieza muestra artículo, código, serie (o «Serie pendiente»), **dónde está** (en qué almacén; con qué trabajador, desde cuándo y con qué vale; o en tránsito hacia dónde), la fecha de vigencia y los días en palabras («Vence hoy», «Vence en 3 días», «Venció hace 5 días»). Orden: la más urgente primero. Filtros: almacén (si ve más de uno), categoría, texto (código, serie o artículo) y «En el almacén» o «Con trabajadores». Alcance de C-02 y AC-06: una pieza es del almacén donde está; la que tiene un trabajador, del de su última entrega; la que va en tránsito, del origen y del destino. Solo lee. | Plática del 8 oct 2026 (hoja 1, punto 4: «cómo se podría visibilizar») |
| P-12 | **Qué se hace con cada pieza según dónde está.** En el almacén del usuario: botón **Inspeccionar**, que abre el flujo de P-14 con la pieza ya cargada. Con un trabajador: botón **Pedir que la devuelva**, que muestra el nombre, el número de empleado, el puesto, desde cuándo la tiene y el folio, con el texto «Pídele que la devuelva para inspeccionarla» y un atajo a Devolver; es solo un recordatorio para quien lo ve: no manda mensajes al trabajador ni guarda nada. En tránsito: sin botón, «Inspecciónala cuando la reciban». **P-04 cambia:** una pieza vencida en manos de un trabajador aparece en la pestaña Vencidas (antes, en la lista de revisión, que sigue pospuesta). Una pieza No apta en manos de un trabajador se anuncia arriba de la pantalla («1 pieza No apta está con un trabajador»). La devolución nunca se bloquea (SM-05). | P-04; decisión de este brief |
| P-13 | **Inicio y menú.** Quien tiene `inspecciones.ver` y `tablero.ver` ve en su Inicio la tarjeta **Inspecciones** con tres números (vencidas, por vencer y sin inspección); al tocarla abre la pestaña más urgente que tenga piezas. La entrada «Inspecciones» del menú lleva un **contador** con la suma de las tres pestañas, que se consulta con `solo_contar=true` (como el de «Recibir»). Los números respetan el mismo alcance que la lista. | Plática del 8 oct 2026; decisión de este brief |
| P-14 | **Inspeccionar una pieza (flujo rehecho).** Escanear la pieza (o llegar desde la lista o la ficha) → ficha breve: artículo, código, serie, estado, dónde está, vigencia actual, el periodo del artículo y sus **últimas inspecciones** (fecha, resultado y quién) → **cinco puntos** (etiquetas, costuras, cintas, herrajes y conectores), cada uno **Bien**, **Mal** o **No aplica**; los cinco se contestan → **resultado**: un punto Mal propone No apto, pero decide la persona → **observación**, obligatoria si es No apto o si es Apto con algún punto Mal → **foto** opcional (una) → antes de guardar, la pantalla muestra la fecha que va a quedar, calculada por el servidor («Quedará vigente hasta el 6/04/2027») → **Guardar**. La fecha de la inspección es la de hoy del servidor (RG-11): no se captura. | Plática del 8 oct 2026 («rehacer el flujo de la pantalla»); P-01; D-10 |
| P-15 | **Avisos de inspección fuera de la pantalla.** No hay tarea programada en el servidor ni notificación push por vencimiento (sigue excluido, maestro sección 6). En la PWA el aviso se ve en pantalla (P-11 a P-13 y E-11). En la app de Android del almacenista (FEAT-020), a partir del paquete descargado, se programa una **notificación local** por día con las piezas de su almacén que entran en aviso o vencen («3 arneses de Midrex vencen esta semana»), después de aplicar cada paquete descargado (OF-29) y a la hora de descarga del almacén (`almacen.hora_descarga`); se recalcula con cada descarga y al tocarla abre Inspecciones. | Maestro, sección 6; D-14, D-15 |
| P-16 | **Inspección por lote.** En el flujo de inspección, el modo **Varias piezas** deja escanear piezas seguidas (una repetida se ignora con sonido, como E-15). Cada pieza se ve en una lista con su vigencia actual y lo que quedará. **Todas Apto** pide confirmar «Revisé etiquetas, costuras, cintas, herrajes y conectores de estas 12 piezas y están bien» y las guarda con los cinco puntos en Bien; las que tienen algo mal se abren una por una con el flujo de P-14 antes de guardar el lote. Cada pieza es **su propia inspección**, guardada en **su propia transacción**: una que no se puede inspeccionar (P-17) sale rechazada con su motivo y no detiene a las demás. Máximo **50 piezas** por lote. Un lote reintentado no duplica nada: cada pieza lleva su `id_cliente`. | Plática del 8 oct 2026; decisión de este brief |
| P-17 | **Cuándo no se registra una inspección.** Pieza en tránsito: 409 `PIEZA_EN_TRANSITO` («Inspecciónala cuando la reciban»). En mantenimiento o en calibración: 409 `PIEZA_EN_MANTENIMIENTO` («Regrésala al servicio y luego inspecciónala»; regresarla pide `piezas.marcar_estado`). En baja: 409 (como hoy). Fuera del alcance del usuario: 404, igual que si no existiera (AC-06). Un código que no es de una pieza: 422 («Escanea el código de la pieza, no el del artículo»). Una fecha de inspección posterior a hoy: 422 `FECHA_FUTURA` (solo la inspección inicial de I-03 recibe fecha; las demás usan la del servidor). La ficha de la pieza trae `inspeccion_posible` con el motivo, para que la pantalla lo diga al escanear y no al guardar. | Decisión de este brief; RG-11 |

### Cambios en reglas existentes

| Regla | Texto propuesto |
|---|---|
| P-01 | «La inspección la registra quien tiene `piezas.inspeccionar` (de inicio, almacenista y supervisor); el flujo y la pantalla se diseñan para el **almacenista** (D-10). Se registra la fecha (hoy, del servidor), el resultado (Apto o No apto), los puntos revisados (etiquetas, costuras, cintas, herrajes y conectores: Bien, Mal o No aplica), las observaciones, la foto opcional y la vigencia que resulta (P-14).» |
| P-04 | «Si vence la inspección de una pieza que está con un trabajador, aparece en la pestaña Vencidas de Inspecciones con quién la tiene y desde cuándo (P-11, P-12).» Pasa de P2 a P1. |
| E-11 | «La inspección vence en N días o menos (hoy incluido), donde N es el aviso resuelto del artículo (P-10). Sin observación.» |
| I-03 | Se agrega: «La fecha de la inspección inicial no puede ser posterior a hoy (P-17).» |
| 5.4 | Fila «Aviso de inspección por vencer»: «General (`INSPECCION_AVISO_DIAS`), categoría y artículo; el artículo gana (P-10) · 7 días antes». Fila «Vigencia de la inspección»: se aclara que cambiarla aplica a las inspecciones nuevas (P-09). |
| 7.12 | Fila «Equipo de alturas»: reglas E-05, E-06, E-11, SM-04, P-01 a P-04, P-09 a P-17; y la fila «Una inspección necesita otra fecha de vigencia» cita P-07 y P-09. |
| 8.2 | Permiso nuevo `inspecciones.ver` (A, S y Administrador), que requiere `catalogo.ver` e `inventario.ver`. `piezas.inspeccionar` se describe como «Inspeccionar (una pieza o un lote) y marcar No apta». |

## Alcance incluido

### A. Modificar la vigencia: los dos sentidos (P-09)

| Quién | Dónde | Acción | Qué pasa |
|---|---|---|---|
| Quien tiene `catalogo.administrar` | Catálogo → Categorías → «Equipo de alturas» | Cambia «Una inspección dura» de 180 a 120 días. | Es la plantilla (CF-02): los artículos nuevos la toman; los existentes solo si se reaplica la plantilla (CF-04), con la vista de qué cambia. |
| Quien tiene `catalogo.administrar` | Catálogo → Artículos → «Arnés de cuerpo completo» | Cambia «Una inspección dura» a 120 días. | Desde ese momento, una inspección Apta de ese artículo vale 120 días. Aviso: «8 piezas tienen una fecha más lejana que el periodo nuevo; no se cambian. Si hace falta, ajústalas una por una.» |
| Quien tiene `piezas.ajustar_vigencia` (supervisor) | Ficha de la pieza o pantalla Inspecciones → **Ajustar fecha** | Elige la nueva fecha y escribe el motivo. | P-07 sin cambios: no pasa del tope (fecha de la inspección más el periodo actual del artículo), no regresa a Apta una No apta, quien hizo la inspección no ajusta la suya, queda en el historial y en revisión. |

### B. Configurar el aviso (P-10)

| Quién | Dónde | Acción | Qué pasa |
|---|---|---|---|
| Quien tiene `catalogo.administrar` | Catálogo → Categorías → «Equipo de alturas» | En «Avisar antes de que venza», escribe 10 días. | Los artículos de la categoría que heredan avisan con 10. La pantalla dice «3 artículos tienen su propio aviso y no cambian». |
| Quien tiene `catalogo.administrar` | Catálogo → Artículos → «Retráctil 6 m» | Escribe 15 días. | Ese artículo avisa con 15 aunque la categoría diga 10. Junto al campo se ve de dónde sale el valor: «15 (de este artículo)», «10 (de la categoría)» o «7 (general)». «Usar el de la categoría» lo regresa a heredar (nulo). |
| Administrador del sistema | `.env` | `INSPECCION_AVISO_DIAS=7`. | El valor general. Fuera de 1 a 90, la aplicación no arranca y lo dice en la bitácora. |

### C. Ver lo que hay que inspeccionar (P-11 a P-13)

Caso normal: Ana, almacenista de Contratistas, empieza el turno.

| # | Acción | Qué hace el sistema |
|---|---|---|
| 1 | Abre la aplicación. | Inicio: tarjeta «Inspecciones: 2 vencidas · 5 por vencer · 1 sin inspección». El menú muestra «Inspecciones (8)». |
| 2 | Toca la tarjeta. | Abre `/inspecciones` en **Vencidas** (la más urgente con piezas). |
| 3 | Ve el primer renglón: «Arnés cuerpo completo · ALT-0031 · Venció hace 5 días · En Contratistas» con **Inspeccionar**. | La pieza está en su almacén. |
| 4 | Ve el segundo: «Bandola · ALT-0102 · Venció hace 2 días · Con Juan Pérez (E-0457) desde 12/09/2026, vale CON-ENT-000812» con **Pedir que la devuelva**. | La pieza es de Contratistas porque de ahí salió su última entrega. |
| 5 | Toca **Pedir que la devuelva**. | Hoja con los datos de Juan y «Pídele que la devuelva para inspeccionarla». Atajo «Ir a Devolver». No se guarda nada. |
| 6 | Cambia a **Por vencer**. | «Retráctil 6 m · ALT-0207 · Vence hoy · En Contratistas»; los demás, de menos a más días. |
| 7 | Cambia a **Sin inspección**. | Piezas que nunca se inspeccionaron (por ejemplo, entraron sin inspección inicial). |
| 8 | Toca **Inspeccionar** en una. | Abre el flujo de la sección D con la pieza cargada. Al volver, la lista ya no la trae. |

### D. Inspeccionar una pieza (P-14, P-17)

| # | Acción de Ana | Qué hace el sistema |
|---|---|---|
| 1 | Menú → Inspecciones → **Inspeccionar**, y escanea la etiqueta de la pieza (o llega desde la lista o la ficha). | Identifica la pieza (`GET /api/escaneo/{codigo}`) y trae la ficha (`GET /api/piezas/{id}`) con `inspeccion_posible`. Si no se puede (en tránsito, en mantenimiento, de otro almacén, código de artículo), lo dice aquí con su motivo (P-17) y no deja seguir. |
| 2 | Lee la ficha breve. | Artículo, código, serie (o «Serie pendiente» con «Registrar serie» si tiene `piezas.registrar_serie`), estado, dónde está, «Vale hasta 01/10/2026 (venció hace 5 días)», «Una inspección dura 180 días» y las tres últimas inspecciones. |
| 3 | Marca cada punto: Etiquetas Bien, Costuras Bien, Cintas **Mal**, Herrajes Bien, Conectores No aplica. | Al marcar Mal, el resultado se propone en No apto. Hasta contestar los cinco no se puede guardar. |
| 4 | Deja No apto y escribe «Cinta deshilachada en la pierna izquierda». | La observación es obligatoria (422 con `regla: "P-01"` si falta). |
| 5 | Toma una foto (opcional). | Una imagen PNG, JPEG o WebP de hasta 3 MB. |
| 6 | Ve el resumen: «Quedará No apta. No se podrá entregar hasta una nueva inspección.» (Si fuera Apto: «Quedará vigente hasta el 6/04/2027».) | La fecha la calcula el servidor (`vigencia_si_apta_hoy` en la ficha). |
| 7 | Toca **Guardar**. | `POST /api/piezas/{id}/inspecciones` con `id_cliente`, resultado, puntos, observación y foto. Una transacción: inspección, estado y vigencia de la pieza, foto y auditoría. |
| 8 | Ve «Inspección guardada: la pieza quedó No apta» y «Inspeccionar otra». | El semáforo de la entrega la respeta de inmediato (E-05). |

Si Ana marca **Apto** con algún punto Mal (por ejemplo, la etiqueta se ve borrosa pero legible), la observación también es obligatoria: «Explica por qué sigue Apta».

### E. Inspeccionar varias piezas (P-16)

| # | Acción | Qué hace el sistema |
|---|---|---|
| 1 | En Inspeccionar, Ana toca **Varias piezas**. | Abre el escáner continuo. |
| 2 | Escanea 12 arneses seguidos. | Cada uno entra a la lista con su vigencia actual y la que quedará. Uno repetido suena y no se agrega. Uno que no se puede inspeccionar entra en rojo con su motivo y no cuenta. |
| 3 | En uno ve una costura abierta y toca **Revisar esta**. | Abre el flujo de la sección D para esa pieza; al terminar regresa a la lista con su resultado. |
| 4 | Toca **Todas Apto** para las demás. | Pide confirmar «Revisé etiquetas, costuras, cintas, herrajes y conectores de estas 11 piezas y están bien». |
| 5 | Confirma. | `POST /api/inspecciones/lote` con un `id_lote` y, por pieza, su `id_cliente`, resultado y puntos. Cada pieza se guarda en su propia transacción. |
| 6 | Ve el resultado: «11 guardadas, 1 no se guardó: ALT-0300 se envió a HYL y va en tránsito». | Las guardadas ya no salen en la lista de pendientes. |
| 7 | Si se cae la señal y reintenta. | Las piezas ya guardadas responden `REPETIDA`; no se duplica ninguna inspección. |

**Por qué una transacción por pieza y no todo o nada.** RG-09 (todo o nada) es de los vales, que son un solo documento con su folio. Cada inspección es un hecho independiente sobre una pieza física que ya se revisó: si el lote fuera todo o nada, una pieza que se envió a otro almacén mientras tanto haría perder las once revisiones buenas, y Ana tendría que repetirlas. Con `id_cliente` por pieza, reintentar es seguro.

### F. Avisos fuera de la pantalla (P-15)

- **PWA (computadora y celular):** sin push por vencimiento. El aviso está en el Inicio, en el contador del menú, en la lista y en el amarillo E-11 al entregar.
- **App de Android (FEAT-020):** el paquete de datos trae, por pieza de su almacén, `inspeccion_vigente_hasta` y el aviso resuelto. La app programa en el teléfono una notificación por día, agrupada, a la hora de inicio de turno (`almacen.hora_descarga`), con las piezas que ese día entran en aviso o vencen. Cada descarga borra las programadas y las vuelve a calcular. Sin paquete nuevo, avisa con lo último que descargó.

## Casos límite

| # | Situación | Qué pasa | Reglas |
|---|---|---|---|
| 1 | La pieza vence hoy. | Sigue vigente todo el día (hora del centro de México): se entrega con amarillo E-11 «Vence hoy» y aparece en Por vencer. Mañana es Vencida y la entrega da rojo E-06. | E-06, E-11, P-11 |
| 2 | Se intenta registrar una inspección con fecha futura. | `POST /api/piezas/{id}/inspecciones` y el lote no aceptan fecha (422 por campo desconocido). En la inspección inicial de la entrada, una fecha posterior a hoy da 422 `FECHA_FUTURA`. | P-17, I-03, RG-11 |
| 3 | Pieza en tránsito. | Aparece en la lista del origen y del destino como «En tránsito a HYL», sin botón. Inspeccionarla da 409 `PIEZA_EN_TRANSITO`. | P-12, P-17 |
| 4 | Pieza en mantenimiento o calibración. | No sale en las pestañas (se cuenta abajo). Inspeccionarla da 409 `PIEZA_EN_MANTENIMIENTO`; primero se regresa al servicio con `piezas.marcar_estado` y entonces, si su fecha ya pasó, aparece en Vencidas. | P-06, P-17 |
| 5 | El supervisor inspeccionó y quiere ajustar la fecha de esa misma inspección. | 403 `AJUSTE_PROPIO` (P-07). Con un solo supervisor por almacén (D-01), solo el Administrador puede ajustarla. Por eso el flujo es del almacenista. | P-07, D-10 |
| 6 | Se cambian los días de aviso de una categoría con artículos que tienen su propio valor. | Esos artículos conservan el suyo; los que heredan cambian en ese momento. La pantalla dice cuántos no cambian. | P-10 |
| 7 | Se activa la inspección en un artículo con piezas entregadas. | Todas sus piezas pasan a Sin inspección (CF-09). Las que tienen trabajadores salen con «Pedir que la devuelva»; no se recogen (CF-08) y su devolución no se bloquea (SM-05). | CF-08, CF-09, P-12 |
| 8 | Pieza con serie pendiente. | Se inspecciona igual. La lista y la ficha muestran «Serie pendiente» y, con `piezas.registrar_serie`, el botón «Registrar serie». | E-29, P-08 |
| 9 | Un almacenista de Midrex escanea un arnés que está en HYL. | «Esta pieza no está registrada en tu almacén» (404, AC-06). Si un trabajador trae a Midrex un arnés que le entregó HYL, primero se recibe en devolución en Midrex (V-07) y ya es de Midrex. | AC-06, V-07, P-17 |
| 10 | Supervisor con varios almacenes en su conjunto (AC-36). | La lista trae los de todo su conjunto, con el filtro de almacén y la columna «Almacén» (AC-37). Inspecciona en su almacén activo (AC-38): en una pieza de otro almacén de su conjunto, el botón dice «Cambiar a HYL e inspeccionar», cambia el almacén activo (AC-39) y abre el flujo. | P-11, AC-37 a AC-39 |
| 11 | El aviso resuelto es mayor que la vigencia (por ejemplo, aviso 90 y vigencia 30). | Al guardar se avisa «Con este aviso, las piezas estarán siempre por vencer». No se bloquea. | P-10 |
| 12 | Se inspecciona Apta una pieza de un artículo que no pide inspección. | Se permite (P-02 solo decide qué se exige al entregar). Queda en su historial; no aparece en las listas. | P-02, P-11 |
| 13 | Inspección No apto de una pieza que tiene un trabajador (la trajo al mostrador). | Queda No apta y sigue con el trabajador. Sale de las pestañas y se anuncia arriba: «1 pieza No apta está con un trabajador». Lo correcto es recibirla en devolución como Dañada. | P-03, P-12, V-05 |
| 14 | Una pieza No apta se inspecciona y resulta Apta (ya se reparó). | Regresa a Apta con su vigencia nueva. Es la única forma (P-03). | P-03, P-14 |
| 15 | Dos almacenistas inspeccionan la misma pieza al mismo tiempo. | Se guardan las dos, una después de la otra (la pieza se bloquea al escribir). La vigencia es la de la última y el historial muestra las dos. | P-14 |
| 16 | En el lote hay una pieza repetida. | Se ignora con sonido, como E-15. | P-16 |
| 17 | En el lote hay piezas de otro almacén o en tránsito. | Esas salen rechazadas con su motivo; las demás se guardan. | P-16, P-17 |
| 18 | Se reintenta un lote tras perder la señal. | Las ya guardadas responden `REPETIDA`. | P-16 |
| 19 | Un lote de más de 50 piezas. | 422: «Guarda este lote y empieza otro». La pantalla no deja escanear la 51. | P-16 |
| 20 | Pieza vencida con un trabajador dado de baja o con el contrato vencido. | Aparece en Vencidas con el aviso de SG-06. | P-12, SG-06 |
| 21 | Alguien tiene `piezas.inspeccionar` pero no `inspecciones.ver`. | No ve la lista ni la tarjeta; sí inspecciona desde el escaneo o la ficha. | P-11, P-14 |
| 22 | Se escanea el código de un artículo por cantidad o el código de artículo de un arnés. | «Escanea el código de la pieza, no el del artículo» (422). | P-17 |
| 23 | Se acorta el periodo de un artículo. | Las piezas ya inspeccionadas conservan su fecha; la pantalla dice cuántas quedan más lejos que el periodo nuevo. P-07 deja acortarlas una por una. | P-09, P-07 |
| 24 | La pieza está dada de baja. | No aparece en ninguna lista; inspeccionarla da 409. | P-17 |

## Fuera de alcance

- Tarea programada en el servidor y notificación push por vencimiento (excluido, maestro sección 6).
- Un mensaje al trabajador (correo, SMS, WhatsApp) para pedirle la devolución.
- Una lista de puntos distinta por categoría o por artículo (por ejemplo, para un detector de gases). Por ahora son los cinco de P-01, con «No aplica».
- Cambiar en un solo paso la fecha de muchas piezas (ajuste masivo de P-07).
- La pantalla de la lista de revisión (sigue en P2).
- Habilitaciones del trabajador (E-08, P2).
- Inspeccionar sin conexión: lo decide FEAT-020; si lo permite, la fecha es la del día capturado y nunca futura (P-17).

## Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-16-01 | Dado un artículo con `dias_aviso_inspeccion` 15, una categoría con 10 y el general en 7, cuando se entrega una pieza que vence en 12 días, entonces el renglón trae E-11 en amarillo; y si el artículo tuviera nulo, no lo traería (P-10, E-11). |
| CA-16-02 | Dada una categoría que cambia su aviso de 10 a 20, entonces sus artículos que heredan avisan con 20 desde ese momento y los que tienen valor propio no cambian (P-10). |
| CA-16-03 | Dado un aviso de 0, 91 o con decimales en un artículo o una categoría, entonces 422 con `regla: "P-10"`; y dado `INSPECCION_AVISO_DIAS` fuera de 1 a 90, entonces la aplicación no arranca (P-10). |
| CA-16-04 | Dado un artículo cuyo periodo baja de 180 a 120 días, entonces las piezas ya inspeccionadas conservan su fecha y la siguiente inspección Apta vale 120 días (P-09). |
| CA-16-05 | Dado un usuario con `inspecciones.ver`, cuando abre `/inspecciones`, entonces ve las tres pestañas con las piezas de su alcance y cada una dice dónde está y cuántos días le quedan; y sin el permiso, `GET /api/inspecciones/pendientes` responde 403 (P-11). |
| CA-16-06 | Dada una pieza cuya vigencia es hoy, entonces aparece en Por vencer con «Vence hoy» y se entrega con E-11; y dada una que venció ayer, entonces aparece en Vencidas y la entrega da E-06 (P-11, E-06, E-11). |
| CA-16-07 | Dada una pieza vencida en manos de un trabajador, entonces aparece en Vencidas con el trabajador, la fecha y el folio, y su acción es «Pedir que la devuelva», que no escribe nada (P-12, P-04). |
| CA-16-08 | Dado el Inicio de un almacenista con `inspecciones.ver`, entonces la tarjeta Inspecciones trae los tres números y el menú un contador igual a su suma (P-13). |
| CA-16-09 | Dada una inspección con un punto Mal y resultado Apto sin observación, entonces 422 con `regla: "P-14"`; dada una No apto sin observación, entonces 422 con `regla: "P-01"`; y dada una inspección sin los cinco puntos, entonces 422 (P-14). |
| CA-16-10 | Dada la ficha de una pieza Apta, entonces trae `vigencia_si_apta_hoy` igual a hoy más el periodo del artículo, y la inspección Apta guardada deja exactamente esa fecha (P-14). |
| CA-16-11 | Dada una inspección con foto, entonces la foto queda como adjunto ligado a la inspección y se ve en el historial; una foto de más de 3 MB o de otro tipo da 422 (P-14). |
| CA-16-12 | Dado un lote de 12 piezas con una en tránsito, entonces se guardan 11 inspecciones, la otra sale rechazada con `PIEZA_EN_TRANSITO`, y reenviar el mismo lote responde las 11 como `REPETIDA` sin crear nada (P-16, P-17). |
| CA-16-13 | Dado un lote de 51 piezas, entonces 422 y no se guarda ninguna (P-16). |
| CA-16-14 | Dada una pieza en mantenimiento, cuando se inspecciona, entonces 409 `PIEZA_EN_MANTENIMIENTO`; y dada una pieza en tránsito, 409 `PIEZA_EN_TRANSITO` (P-17). |
| CA-16-15 | Dada una entrada de una pieza con inspección inicial de fecha posterior a hoy, entonces 422 `FECHA_FUTURA` (P-17, I-03). |
| CA-16-16 | Dado el tablero, entonces `inspecciones_por_vencer` cuenta con el aviso resuelto de cada artículo, no con 7 fijo (P-10). |
| CA-16-17 | Dado el paquete de la app de Android, entonces trae por pieza la vigencia y el aviso resuelto, y la app programa la notificación local sin pedir nada al servidor (P-15; se comprueba con FEAT-020). |
| CA-16-18 | Dado un supervisor que registró una inspección, cuando quiere ajustar su fecha, entonces 403 `AJUSTE_PROPIO`, y la pantalla le dice que lo haga otro supervisor o el Administrador (P-07, P-09). |

## Módulos relacionados conocidos

- `inspecciones`: dueño de `inspeccion`, `ajuste_vigencia` y `evento_pieza`. Gana el endpoint del lote, la consulta de pendientes, la vigencia que quedaría y las validaciones de P-14 y P-17. Solo lee de `movimientos` (dónde está la pieza y su última entrega), como ya hace `almacenes_de_pieza`.
- `catalogo`: `dias_aviso_inspeccion` en categoría y artículo, la resolución del aviso (un servicio que usan los demás), y el estado de la pieza (sigue siendo su dueño).
- `movimientos`: E-11 con el aviso resuelto (quita la constante `DIAS_AVISO_INSPECCION`); la fecha de la inspección inicial (I-03, P-17). No escribe inspecciones.
- `consulta`: `inspecciones_por_vencer` del tablero con el aviso resuelto y los conteos nuevos.
- `archivos`: tipo de adjunto `FOTO_INSPECCION`.
- `sincronizacion` (FEAT-020): vigencia y aviso en el paquete.
- `acceso`: permiso `inspecciones.ver`.
- Frontend: rutas nuevas `routes/operacion/inspecciones.tsx` (lista) e `inspeccionar.tsx` (flujo de una pieza y lote), `routes/consulta/pieza.tsx` (bloque de vigencia y botón que abre el flujo nuevo en lugar de `HojaInspeccion`), `componentes/consulta/hojas-pieza.tsx`, formularios de categoría y artículo, tarjeta del Inicio, `sesion/menu.ts` (entrada y contador).

## Cambios de datos o API esperados

**Datos** (una migración de Alembic):

| Cambio | Qué guarda |
|---|---|
| `categoria.dias_aviso_inspeccion`, `articulo.dias_aviso_inspeccion` (entero, nulo = hereda, CHECK 1 a 90) | Ya están en el maestro (5.1). |
| `INSPECCION_AVISO_DIAS` en `.env` y `.env.example` (7) | Ya está en el maestro (5.1). |
| `inspeccion.id_cliente` (único, nulo en las existentes) | Idempotencia del lote y de la inspección individual. **No está en el maestro.** |
| `adjunto.inspeccion_id` y el tipo `FOTO_INSPECCION` | La foto de la inspección. **No está en el maestro.** |

`inspeccion.puntos` (JSON) no cambia de forma: `true` es Bien, `false` es Mal y `null` es No aplica; desde esta feature trae las cinco claves.

**API** (se actualiza [api-contracts.md](../architecture/api-contracts.md)):

| Endpoint | Cambio |
|---|---|
| `GET /api/inspecciones/pendientes?estado=&almacen_id=&categoria_id=&q=&ubicacion=&pagina=&tamano=&solo_contar=` | Nuevo, `inspecciones.ver`. `estado`: `VENCIDA`, `POR_VENCER` o `SIN_INSPECCION`. Responde `{conteos: {vencidas, por_vencer, sin_inspeccion, no_aptas, en_mantenimiento, no_aptas_con_trabajador}, elementos: [{pieza: {id, codigo, numero_serie, serie_pendiente, estado}, articulo: {id, codigo, nombre, categoria}, vigente_hasta, dias_restantes, dias_aviso, ubicacion: {tipo, almacen, trabajador, desde, folio, vale_id, destino}, accion}], total}`. `accion`: `INSPECCIONAR`, `PEDIR_DEVOLUCION` o `NINGUNA`. Con `solo_contar=true`, solo `conteos`. Folio y vale de otro almacén en `null` (AC-06). Sin costos, CURP ni NSS. |
| `POST /api/inspecciones/lote` | Nuevo, `piezas.inspeccionar`. Cuerpo `{id_lote, piezas: [{id_cliente, codigo, resultado, puntos, observacion?, foto?}]}`, de 1 a 50. Responde 200 `{guardadas, rechazadas, repetidas, resultados: [{id_cliente, codigo, estado: "GUARDADA" \| "REPETIDA" \| "RECHAZADA", inspeccion?, error?: {codigo, mensaje, regla}}]}`. 422 si el cuerpo no es válido o pasa de 50; 403 sin el permiso. |
| `POST /api/piezas/{id}/inspecciones` | `puntos` obligatorio con las cinco claves; acepta `id_cliente` y `foto`; nuevos errores 422 `regla: "P-14"`, 409 `PIEZA_EN_TRANSITO`, 409 `PIEZA_EN_MANTENIMIENTO`. Con un `id_cliente` ya guardado, 200 con la misma inspección. |
| `GET /api/piezas/{id}` | Trae `vigencia_inspeccion_dias`, `dias_aviso_inspeccion` (resuelto) y su `origen` (`ARTICULO`, `CATEGORIA`, `GENERAL`), `dias_restantes`, `vigencia_si_apta_hoy` e `inspeccion_posible: {puede, motivo, regla}`. El historial de inspecciones trae `puntos` y la foto. |
| `GET/POST /api/categorias`, `PATCH /api/categorias/{id}`, `GET/POST /api/articulos`, `GET/PATCH /api/articulos/{id}` | Campo `dias_aviso_inspeccion` (1 a 90 o nulo). El artículo devuelve además el valor resuelto y su origen, y la categoría `articulos_con_aviso_propio`. |
| `POST /api/vales` (ENTRADA) | La inspección inicial con fecha posterior a hoy: 422 `FECHA_FUTURA`. |
| `GET /api/tablero/resumen` | `inspecciones_por_vencer` con el aviso resuelto; nuevos `inspecciones_vencidas` e `inspecciones_sin_registro`. Los tres valen `null` sin `inspecciones.ver`. |
| `GET /api/sincronizacion/paquete` (FEAT-020) | Por pieza, `inspeccion_vigente_hasta` y `dias_aviso_inspeccion` resuelto. |

Permiso nuevo `inspecciones.ver` (A, S y Administrador), ya en el maestro (5.3). Las dos rutas nuevas declaran su permiso en el router.

## Restricciones y compatibilidad

- Solo `inspecciones` escribe inspecciones, ajustes y eventos; el estado de la pieza lo cambia `catalogo` a pedido de `inspecciones`, como hoy. Nada de esta feature escribe vales ni existencias.
- Las reglas viven en el servidor: la pestaña de cada pieza, los días restantes, la acción, la fecha que quedaría y si se puede inspeccionar los calcula el servidor.
- Las inspecciones, ajustes y eventos se siguen insertando sin actualizar ni borrar.
- Las inspecciones existentes sin las cinco claves de `puntos` se siguen mostrando como están; la exigencia es para las nuevas.
- Fechas: «hoy» es el día del centro de México (`hoy_mx`); en la base, UTC.
- La pantalla es primero celular (D-20): botones grandes, escáner continuo, una mano.
- Los textos van en español llano: «Vence hoy», «Venció hace 5 días», «Pídele que la devuelva».

## Riesgos

- **«Todas Apto» se usa sin revisar.** Mitigación: la confirmación nombra los cinco puntos y cuántas piezas; cada inspección queda a nombre de quien la hizo y con su hora.
- **Consulta de pendientes lenta** con miles de piezas: resolver el aviso por artículo y la última entrega de cada pieza en una sola consulta; medir con los datos de prueba ampliados.
- **Herencia en vivo confunde** con la plantilla que se copia (CF-02). Mitigación: junto al campo se dice de dónde sale el valor.
- **Dependencias:** el conjunto de almacenes (FEAT-013) para el supervisor con varios almacenes; FEAT-020 para la notificación local.
- **Puntos obligatorios** rompen pruebas existentes que inspeccionan sin `puntos`: se reescriben, no se borran.

## Validaciones requeridas

- Una prueba por regla con su ID en el nombre: `test_p09_*` a `test_p17_*`, y las de los cambios de P-01, P-04, E-11 e I-03.
- Prueba del lote: una transacción por pieza, rechazo parcial, idempotencia por `id_cliente` y tope de 50.
- Prueba de la herencia del aviso (artículo, categoría, general) y del rango 1 a 90.
- Prueba de alcance (AC-06): pendientes y lote de otro almacén.
- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck`, `pnpm build` y la migración arriba y abajo.
- Recorrido manual en celular con el rol Almacenista y en computadora con el Supervisor.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): P-09 a P-17 en 7.8; P-01, P-04, E-11, I-03; 5.4; 7.12; sección 8.2 (`inspecciones.ver`); prioridades (sección 9); historial.
- [api-contracts.md](../architecture/api-contracts.md): Catálogo (piezas, categorías y artículos), Tablero y la sección nueva «Inspecciones».
- [data-model.md](../architecture/data-model.md): columnas nuevas de categoría, artículo, inspección y adjunto.
- [app-flow.md](../product/app-flow.md): flujo 13 rehecho, flujo 22 (tarjeta) y la lista de pantallas.
- [ui-ux.md](../product/ui-ux.md): días en palabras, escáner continuo del lote, «de dónde sale el valor».
- `.env.example`: `INSPECCION_AVISO_DIAS`.
- [guia-almacenista.md](../guia-almacenista.md), [guia-por-rol.md](../guia-por-rol.md), el tutorial (FEAT-010) y el [changelog](../releases/changelog.md) al construirse.

## Decisiones abiertas

| # | Decisión | Propuesta |
|---|---|---|
| 1 | ¿Qué quiso decir el track con «modificar la vigencia»? | Se cubren los dos sentidos (P-09): el periodo del artículo o categoría y la fecha de una pieza. Si pedía otra cosa (por ejemplo, alargar la fecha de una pieza más allá del tope, o que el supervisor cambie el periodo sin `catalogo.administrar`), se pregunta al track. |
| 2 | Rango del aviso. | **1 a 90 días.** Cubre el ejemplo del track (10 días) y un trimestre. |
| 3 | Lote: ¿una transacción por pieza o todo o nada? | **Por pieza** (sección E). |
| 4 | ¿Las No aptas y en mantenimiento entran en una pestaña? | **No**: se cuentan y enlazan a Seguimiento; la No apta con un trabajador se anuncia arriba. |
| 5 | ¿Se inspecciona una pieza en mantenimiento para regresarla al servicio en un paso? | **No**: primero se regresa al servicio (`piezas.marcar_estado`) y luego se inspecciona, para no mezclar permisos. |
| 6 | ¿El supervisor con varios almacenes inspecciona sin cambiar su almacén activo? | **No**: FEAT-013 (AC-38) pone las inspecciones entre las escrituras que se hacen en el almacén activo. La lista abarca todo el conjunto (AC-37) y ofrece cambiar de almacén en un toque. Si se quisiera inspeccionar sin cambiar, hay que cambiar AC-38. |
| 7 | Lista de puntos por categoría (para equipo que no es de alturas). | Fuera de esta feature; por ahora «No aplica». |
| 8 | Hora de la notificación local en Android. | La hora de descarga del almacén (`almacen.hora_descarga`, FEAT-020). |


## Evidencia de implementación local (8 de octubre de 2026)

Backend implementado: herencia viva del aviso categoría/artículo/general (P-10), cola y conteos con agregación/paginación SQL (P-11), cinco puntos obligatorios con valores sí/no/no aplica y observación cuando Apta tiene una falla (P-14), fotos de hasta 3 MB protegidas por sesión y alcance, lotes de hasta 50 con confirmación independiente por pieza y reintentos por UUID/huella (P-16), y restricciones de tránsito/mantenimiento/calibración/Baja (P-17). La inspección inicial rechaza fechas futuras con `FECHA_FUTURA` e I-03. La salida de mantenimiento de un artículo que requiere inspección debe dejarlo No apto antes de revisarlo. La ficha y su historial incluyen puntos y foto.

Migración: `0015_inspecciones_alertas`, sobre `0014_despacho_push`. Verificados upgrade, downgrade a 0014 y upgrade otra vez en `imhotep_test_feat016mig`; la base aislada fue eliminada al terminar.

Pruebas específicas: seis casos FEAT-016 pasaron. Las 47 pruebas de inspecciones existentes y mínimos FEAT-004 pasaron. La regresión ampliada de catálogo/trazabilidad llegó a 77 casos aprobados y dos fallos de fixtures anteriores que no suministran el proyecto ahora obligatorio por PR-11; no se considera verde la suite completa.

Pendientes: avisos locales Android y su recorrido físico (P-15, depende de FEAT-020), recorrido visual/manual con cada permiso, medir la cola a volumen de planta. La integración global de documentos y tablero está a cargo de la tarea principal. Este registro no acredita completados los criterios de Android.
