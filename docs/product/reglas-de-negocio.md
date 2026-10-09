# Reglas de negocio — Reto IMHOTEP (Track 3)

Catálogo de reglas, limitantes y casos especiales de cada operación. Es el anexo del [PRD](prd.md): el PRD explica el producto y este documento fija cómo debe comportarse. Las historias de usuario citan las reglas por su ID.

Versión 9 (8 de octubre de 2026). Alcance: flujo en línea y, con la iteración 01, la app de Android del almacenista con operación sin conexión limitada (sección 7.20).

**Reglas aprobadas y sin construir.** Esta versión incorpora las reglas de la [iteración 01](../releases/iteration_01/README.md) (plática del 8 de octubre de 2026), aprobadas por el usuario el mismo día y **todavía sin construir**. Las secciones nuevas llevan la marca «Iteración 01, aprobada, sin construir» y enlazan su FEAT; las reglas existentes que cambian conservan su texto y agregan el cambio con la nota «(cambia con FEAT-0NN, iteración 01, sin construir)». Mientras no se construyan, el código sigue la regla anterior. Si una FEAT y el documento maestro de la iteración difieren, manda el maestro.

Cada regla indica su **origen**:

- **PDF**: lo exige `docs/HackaItlacTrack3_2026.pdf` (página o función indispensable). No se puede recortar.
- **Plática**: lo dijo el patrocinador en la reunión ([transcripcion_track.md](../info_track/transcripcion_track.md)); se indica el minuto. «Plática 8 oct 2026» es la segunda plática ([ajustes_01.pdf](../releases/iteration_01/ajustes_01.pdf)).
- **Decisión del usuario (8 oct 2026)**: decisiones D-01 a D-21 del [maestro de la iteración 01](../releases/iteration_01/README.md#2-decisiones-del-usuario-8-de-octubre-de-2026). En el texto se citan como «decisión D-NN» para no confundirlas con las reglas de dotación D-01 a D-04 (sección 4.2); «T-1» a «T-7» son las decisiones transversales de la sección 10 del maestro.
- **Propuesta**: decisión de diseño nuestra. Se puede recortar si falta tiempo.

**Principio que ordena todo** (plática min 11 y 42): el sistema debe ser lo más simple posible para gente poco familiarizada con la tecnología, y el supervisor casi no tiene tiempo. Por eso el sistema bloquea solo lo que el PDF exige bloquear o lo que es de seguridad. Lo demás lo resuelve el almacenista con una observación obligatoria, y queda en una lista para revisarse después.

**Ajuste de la iteración 01** (plática 8 oct 2026, pedido 5): el almacenista no tiene autonomía para despachar EPP; toda entrega de EPP necesita la aprobación del supervisor del almacén (DE-01). Manda la plática nueva sobre el principio anterior; para no saturar al supervisor hay resolución múltiple, avisos agrupados y un interruptor de autonomía por almacén y por almacenista (DE-12, NT-05, DE-14). Las pantallas se optimizan para el **flujo normal** (decisión D-01): un supervisor en un almacén y cada trabajador en un proyecto; lo demás son casos especiales que el sistema soporta.

---

## 1. Conceptos

**Ubicación.** Lugar donde puede estar un artículo. Hay tres clases:

- Almacén: Kepler (central, fuera de la planta), Contratistas (dentro de Mittal) y los almacenes de área (Midrex, HYL, Laminador, Minas). Los de área son temporales: contenedores que se abren para un mantenimiento y se cierran al terminar (plática min 32 y 49). Los almacenes de área son los de **tercer nivel** (tipo `PROYECTO`); en este documento se les llama «almacén de tercer nivel» o «almacén de proyecto» para no confundirlos con el **proyecto** de la iteración 01.
- Trabajador: cada trabajador es una ubicación. Lo que "tiene" es su saldo.
- Virtual: Proveedor, En tránsito, Consumido, Baja. No son lugares físicos; sirven para que todo movimiento tenga origen y destino.

**Categoría.** Grupo de artículos definido por la empresa, por ejemplo "Equipo de alturas". Trae una plantilla de reglas que sus artículos toman al crearse (sección 5).

**Artículo.** Renglón del catálogo. Su nombre es breve e incluye la marca, por ejemplo "Minipulidor Bosch", para notar si devuelven otro (plática min 51). Puede estar activo o inactivo. Tiene dos propiedades independientes:

| Propiedad | Valores | Qué cambia |
|---|---|---|
| Control | **Por pieza**: cada unidad tiene código único e historial propio. **Por cantidad**: un código de producto y se cuenta. | Cómo se escanea y si tiene estado e inspección |
| Retorno | **Retornable**: debe regresar; mientras no regrese es un pendiente del trabajador. **Consumible**: no regresa; no genera pendiente. | Si aparece en la baja y cómo se mide el límite |

El equipo caro se controla por pieza, con número de serie; la herramienta común, por cantidad (plática min 0 y 37). Los artículos por cantidad que no admiten etiqueta, como un marro o un cincel, se escanean con el QR de su estante (plática min 20–21).

**Requisito especial.** Condición extra para entregar un artículo: inspección vigente, autorización del supervisor o habilitación del trabajador. Se activa o se quita por artículo (sección 5.2).

**Pieza.** Unidad física de un artículo controlado por pieza. Tiene código único, número de serie del fabricante (que puede quedar **pendiente**: una pieza sin número de serie registrado se identifica solo por su código, I-02), estado (Apto, No apto, En mantenimiento, En calibración, Baja), vigencia de su inspección y ubicación actual. La serie pendiente no es un estado: se deriva de que el número de serie esté vacío.

**Trabajador vigente.** Trabajador en estado Activo cuyo periodo de contrato incluye la fecha de hoy. Solo a un trabajador vigente se le entrega.

**Vale.** Documento de una operación: folio, tipo, origen, destino, responsable, trabajador y firmas.

**Movimiento.** Renglón del vale y de la bitácora: artículo (y pieza si aplica), cantidad, ubicación de origen, ubicación de destino, condición y saldo resultante.

**Lista de revisión.** Excepciones que resolvió el almacenista con una observación: cancelaciones, cierres sin devolución, diferencias de traspaso, faltantes. El supervisor la revisa cuando puede; no detiene la operación.

**Permiso.** Lo que un usuario puede hacer o ver, identificado por una clave como `entregas.crear`.

**Rol.** Conjunto de permisos con nombre; cada usuario tiene uno. El PDF los llama perfiles (sección 8).

Conceptos de la iteración 01 (aprobados, sin construir):

**Proyecto.** Entidad propia, distinta del almacén: clave, nombre, almacén al que pertenece y periodo (inicio y fin estimado). Se da de alta **antes** que sus trabajadores; cada trabajador está asignado a un proyecto (lo normal, uno). El consumo de una entrega cuenta para el proyecto del trabajador, no para el almacén que entregó (sección 7.15, decisión D-02, decisión D-13).

**Conjunto de almacenes y almacén activo.** Cada usuario tiene un conjunto de almacenes (lo normal, uno) y opera en uno a la vez, su almacén activo; lee lo de todo su conjunto (AC-36 a AC-41).

**Artículo de EPP.** Artículo cuya categoría es de tipo EPP. Su entrega pide la aprobación del supervisor salvo autonomía (sección 7.16).

**Alto valor.** Artículo cuya categoría está marcada como de alto valor o cuyo costo unitario llega al tope (sección 5.5).

---

## 2. Reglas generales

Aplican a todas las operaciones.

| ID | Regla | Origen |
|---|---|---|
| RG-01 | Las existencias solo cambian mediante un movimiento. Nadie edita saldos directamente. | Propuesta |
| RG-02 | Los vales y movimientos no se editan ni se borran. Un error se corrige con una cancelación que genera los movimientos inversos (sección 7.10). | PDF p.1: "sin perder el historial" |
| RG-03 | Cada movimiento registra fecha y hora, usuario responsable, almacén, artículo, cantidad, origen, destino, folio y saldo resultante. | PDF función 4; p.6 |
| RG-04 | El saldo de un artículo en un almacén nunca es negativo. | Propuesta |
| RG-05 | Una pieza está en una sola ubicación a la vez y su cantidad siempre es 1. | PDF p.2 |
| RG-06 | El folio es consecutivo por tipo de vale y almacén (ejemplo: `KEP-ENT-000123`). No se reutiliza, ni siquiera al cancelar. **Nota sin conexión (FEAT-020, iteración 01, sin construir):** un vale capturado sin conexión recibe su folio al sincronizar; sigue consecutivo, pero su orden puede no coincidir con el de la captura (OF-19). | PDF p.8; plática min 52 |
| RG-07 | Cada usuario opera sobre su almacén asignado y no lo elige en cada operación; solo quien tiene `almacenes.todos` (de inicio, el Administrador) elige almacén (AC-06). Quien no tiene almacén asignado y no tiene `almacenes.todos` no ve ni opera nada de ningún almacén. Cada almacén tiene su(s) supervisor(es), independientes de los almacenistas. Un almacén puede tener varios almacenistas: operan las 24 horas y una sola persona no los cubre. Cada almacenista usa su propia cuenta y su propio dispositivo, y cada operación queda ligada a quien la hizo. El MVP no avisa cuando a un almacén le falta cobertura. **(Cambia con FEAT-013, iteración 01, sin construir):** «su almacén asignado» pasa a «su **almacén activo**, uno de su conjunto de almacenes» (AC-36); lo normal sigue siendo un solo almacén y nada cambia en pantalla. **(Cambia con FEAT-020):** en un equipo compartido por turnos (app de Android), cada almacenista entra con su propia credencial y la operación queda a nombre de quien la capturó, aunque la suba otro usuario del equipo (OF-24). | Plática min 33; decisión del usuario (8 oct 2026) |
| RG-08 | Todo se valida dos veces: al escanear (semáforo inmediato) y al confirmar (el servidor revalida). Si algo cambió entre ambos momentos, el vale no se guarda y se indica el renglón que falló. **Excepción sin conexión (FEAT-020, iteración 01, sin construir):** en línea no cambia; una operación capturada sin conexión la evalúa primero el equipo y el servidor la revalida al sincronizar, y en vez de rechazarla la clasifica en guardada, guardada con avisos o conflicto (OF-17, OF-21, OF-22). | Propuesta |
| RG-09 | Un vale se guarda completo o no se guarda. **Excepción sin conexión (FEAT-020, iteración 01, sin construir):** cada operación sincronizada sigue siendo todo o nada, pero el lote que la lleva no (OF-18). | Propuesta |
| RG-10 | Los códigos se aceptan tal como vienen, en QR o barras. Un código identifica una sola cosa: trabajador, pieza, artículo o vale. En la importación, un código de pieza o una serie repetidos se rechazan (una serie vacía no cuenta como repetida); si una pieza no trae código en la importación de alta, el sistema le asigna uno (I-15), y si lo trae se respeta tal como viene. En cambio, las filas del mismo artículo por cantidad en el mismo almacén no son un código repetido: se consolidan (I-06). | PDF p.2; plática min 57 |
| RG-11 | La fecha y hora válidas son las del servidor. **Excepción sin conexión (FEAT-020, iteración 01, sin construir):** `creado_en` sigue siendo la hora del servidor (al sincronizar); la hora del equipo se guarda aparte en `capturado_en`, nunca se corrige y se muestra junto (OF-19). | Propuesta |
| RG-12 | El costo de un artículo lo ve solo quien tiene el permiso de costos; de inicio, Compras. En vales, tickets y comprobantes no aparece nunca, lo vea quien lo vea. **Nota de la iteración 01 (sin construir):** el Supervisor ve el valor del inventario y el uso por proyecto en pesos, solo como totales y nunca el costo unitario (TB-04); un total en pesos que cubre un solo artículo se muestra como «—» a quien no tiene `catalogo.costos`, porque dividirlo revelaría el costo (T-2 del maestro). Decir que un artículo es de alto valor no revela su costo (AV-05). | Plática min 38 |
| RG-13 | La CURP y el NSS del trabajador los ve solo quien tiene el permiso de datos personales; de inicio, RH. El almacenista ve nombre, número, puesto, área, vigencia y foto. El sistema no guarda sueldos. De inicio, RH no ve el inventario. | Plática min 28 |
| RG-14 | Toda excepción que resuelve el almacenista exige una observación y entra a la lista de revisión. | Plática min 36 y 42 |
| RG-15 | La aplicación es web, funciona en celular, tableta y computadora, y no requiere instalarse. **(Cambia con FEAT-020, iteración 01, sin construir):** además hay una **app de Android** para el almacenista, que es la misma interfaz empaquetada con Capacitor y sí se instala (APK por MDM o instalación directa, sin tienda ni iPhone); en línea se comporta igual que la web (OF-01). La web sigue sin requerir instalación; las notificaciones push del supervisor usan la PWA (NT-08). | PDF p.2; plática min 10 y 26; decisión del usuario (8 oct 2026) |

---

## 3. Semáforo

Al escanear, cada renglón recibe un nivel. El almacenista no interpreta reglas; solo ve el nivel y el motivo.

| Nivel | Significado | Qué hace el almacenista |
|---|---|---|
| Verde | Cumple todo. | Continúa. |
| Amarillo | Aviso. No bloquea. | Lee el aviso, anota la observación si se pide y continúa. |
| Naranja | Requiere autorización del supervisor. | Pide la autorización o quita el renglón. |
| Rojo | No se puede. Nadie lo autoriza en el mostrador. | Quita el renglón y aparta el equipo. |

Principios:

| ID | Regla |
|---|---|
| SM-01 | Si un renglón cae en varias reglas, se muestra el nivel más grave y todos los motivos. |
| SM-02 | Cada nivel se distingue por color, icono, texto y sonido. No depende solo del color. |
| SM-03 | El vale se puede confirmar cuando no queda ningún rojo y todos los naranjas están autorizados. **(Cambia con FEAT-014, iteración 01, sin construir):** y, si el despacho pide aprobación, con los renglones de EPP aprobados (DE-02). La aprobación del despacho no es un color: el renglón lleva la etiqueta «Necesita aprobación». |
| SM-04 | Un rojo de seguridad (pieza no apta o sin inspección vigente) no admite autorización. Solo se resuelve registrando una inspección (sección 7.8). |
| SM-05 | La devolución de algo que está en resguardo nunca se bloquea. Recuperar el equipo es prioritario. |
| SM-06 | El orden de evaluación es: código, trabajador, ubicación y existencias, seguridad, límites, avisos. |

Los criterios concretos están en cada operación de la sección 7.

---

## 4. Límites y dotación

### 4.1 Límite por artículo (bloquea)

El PDF dice: "Límite de entrega por artículo: si se supera, bloquear la operación hasta que un supervisor la autorice". La plática aclaró cómo se cuenta, y cada forma aplica a un tipo de artículo:

- **Por periodo**, para consumibles: "en una semana tú no puedes pedir más de tres guantes" (min 36). Como no regresan, es la única forma de limitarlos.
- **En posesión**, para retornables: que un trabajador no acumule tres arneses o tres detectores de gases (min 10). Si devuelve el suyo, puede recibir otro el mismo día.

| ID | Regla | Origen |
|---|---|---|
| L-01 | Cada artículo puede tener un límite por trabajador. Sin límite configurado, la regla no aplica. | PDF función 6; plática min 50 |
| L-02 | Retornables: la cuenta es lo que el trabajador tiene ahora más lo que lleva este vale. | Plática min 10 |
| L-03 | Consumibles: la cuenta es lo entregado en los últimos N días más lo que lleva este vale. | Plática min 36 |
| L-04 | Si la cuenta supera el límite, el renglón queda en naranja y muestra el detalle ("límite 2, tiene 2, pide 1"). | PDF función 6 |
| L-05 | El artículo guarda dos campos: cantidad límite y periodo en días. Periodo vacío significa "en posesión". | Propuesta |

Cómo se aplica en el servidor: el motivo del límite lleva el ID `L-02` (retornables) o `L-03` (consumibles) y el detalle de L-04. Un retornable cuenta lo que el trabajador tiene ahora (su existencia); un consumible sin periodo compara el límite solo contra lo que pide el vale (no hay nada "en posesión"). Si un vale trae varios renglones del mismo artículo (por ejemplo dos piezas), cada renglón cuenta también lo pedido en los anteriores: el que cruza el límite queda en naranja. Una entrega hecha hace exactamente N días ya no cuenta, y un vale cancelado tampoco.

### 4.2 Dotación recomendada por puesto (avisa, no bloquea)

El PDF muestra que el EPP se define por puesto (p.3, paso 5) y lista el equipo de un trabajador dentro de Mittal (p.7).

| ID | Regla | Origen |
|---|---|---|
| D-01 | Cada puesto tiene una dotación: lista de artículos con cantidad recomendada. | PDF p.3, p.7 |
| D-02 | Al identificar al trabajador se muestra qué le falta de su dotación. El almacenista escanea para completarla. | Propuesta |
| D-03 | Entregar algo fuera de la dotación, o más de lo recomendado, da aviso amarillo y pide una observación corta ("se mojaron", "se llenaron de grasa"). | Idea del equipo; plática min 36 |
| D-04 | La cantidad recomendada de un artículo en una dotación no puede ser mayor que su límite (4.1). Si el artículo no tiene límite, no hay tope. Tampoco se puede bajar el límite de un artículo por debajo de lo recomendado en alguna dotación. | Propuesta |

La dotación es lo recomendado (amarillo) y el límite es el máximo (naranja). La dotación siempre debe ser menor o igual al límite.

**Estado: construido en el servidor** (FEAT-003; la interfaz está pendiente). Cómo se aplica:

- **Puesto y dotación.** El catálogo de puestos y su dotación son datos que administra quien tiene `catalogo.administrar`. Los puestos de los datos de prueba y sus dotaciones son **propuestas basadas en el PDF** (EPP por trabajador de la p. 10 y equipo y herramienta de la p. 7 del documento); el PDF no dice qué puestos existen: los reales los define la empresa. Cada periodo de contrato guarda el puesto como texto y, si coincide con el catálogo, también su `puesto_id`. Sin `puesto_id` o con un puesto sin dotación, el trabajador no tiene dotación y no hay avisos.
- **D-02: lo que `entregada` y `falta` significan.** Para cada artículo de la dotación del puesto del periodo de contrato vigente hoy: `entregada` es, en un **retornable**, lo que el trabajador tiene ahora (su existencia en su ubicación, de cualquier almacén); en un **consumible**, lo que se le entregó desde el primer día del periodo de contrato vigente (a las 00:00 hora del centro de México), sin contar vales cancelados. `falta` es lo recomendado menos lo entregado, nunca negativa. Los artículos inactivos no se listan.
- **E-09.** En una entrega, el renglón avisa si el trabajador tiene dotación y (a) el artículo no está en ella, o (b) `entregada` más lo que ya pidieron los renglones anteriores del mismo artículo en el vale más la cantidad del renglón supera la recomendada. Es amarillo con el ID `E-09`; si también supera el límite gana el naranja (SM-01) y se muestran los dos motivos. La evaluación trae `pide_observacion: true` (en el renglón y en el vale) y la confirmación exige una observación en el renglón (`renglones[].observacion`) o en el vale (`observacion`); sin ella responde 422 con la regla `E-09`. La observación queda en el movimiento (`movimiento.observacion`) y se ve en el reporte de movimientos. Un renglón en rojo no pide observación.

### 4.3 Autorización del supervisor

| ID | Regla | Origen |
|---|---|---|
| A-01 | Autoriza cualquier usuario con el permiso de autorizar; de inicio, los supervisores de almacén y el Administrador. Una solicitud es del almacén en que se pidió: solo la ven y la resuelven quienes tienen ese almacén asignado (y el Administrador); un supervisor de otro almacén o sin almacén no la ve (AC-06). Lo hace desde su propio celular, donde ve la solicitud y responde, o con su PIN en el dispositivo del almacenista si está presente; en ese caso, el supervisor que da su usuario y PIN también debe ser del almacén de la solicitud (o Administrador). **(Cambia con FEAT-013 y FEAT-014, iteración 01, sin construir):** «quienes tienen ese almacén asignado» pasa a «quienes lo tienen **en su conjunto**» (AC-40), también para el PIN en el mostrador. La solicitud puede ser de excedente, de **despacho de EPP** (DE-04) o de **traslado** entre almacenes de tercer nivel (X-17). Se avisa por notificación push a los supervisores del almacén (NT-02); el Administrador resuelve, pero no recibe avisos por omisión. Sin conexión no hay autorizaciones ni PIN en el mostrador (OF-10). | PDF función 6; plática min 42; plática 8 oct 2026 |
| A-02 | La autorización exige un motivo. **(Cambia con FEAT-014, iteración 01, sin construir):** una solicitud de despacho sin renglones en naranja lleva el motivo del sistema «Despacho de EPP» y una nota opcional; con naranjas, el motivo del excedente sigue siendo obligatorio (DE-05). | Plática min 36 |
| A-03 | Vale para los renglones señalados de ese vale y se usa una sola vez. No cambia el límite del artículo. **(Cambia con FEAT-014 y FEAT-015, iteración 01, sin construir):** vale para los renglones aprobados con su cantidad **o menos**; la aprobación puede ser parcial, renglón por renglón (DE-06, DE-08), salvo la de traslado, que se aprueba completa (X-19); quitar renglones o bajar cantidades no la invalida, agregar o subir sí (DE-13, X-19). | Propuesta |
| A-04 | Se registra quién la pidió, quién autorizó, cuándo, el motivo y el excedente. En el vale aparece como "Validó". | PDF p.3: firma "Validó" |
| A-05 | Quien captura el vale no puede autorizarse a sí mismo. **(Cambia con FEAT-014 y FEAT-015, iteración 01, sin construir):** dos excepciones: el despacho de EPP que captura el propio supervisor del almacén (DE-07) y el envío propio de un traslado lateral por el supervisor del origen (X-16). En ninguna se crea una solicitud que la misma persona resuelva; el vale dice «Validó: él mismo». Un excedente de límite sigue necesitando a otro supervisor. | Propuesta; decisión del usuario (8 oct 2026) |
| A-06 | Un rojo no se autoriza (SM-04). | PDF p.2 |
| A-07 | Si la autorización no llega, el almacenista quita el renglón excedente y entrega lo demás. **(Cambia con FEAT-014, iteración 01, sin construir):** también aplica a los renglones de EPP sin aprobación del despacho (DE-09, DE-10). | Propuesta |

---

## 5. Catálogo configurable

La empresa decide qué artículos existen, a qué categoría pertenece cada uno y cuáles piden un trato especial. Nada de esto está fijo en el programa: se cambia desde la pantalla de catálogo.

### 5.1 Categorías

| ID | Regla | Origen |
|---|---|---|
| CF-01 | Las categorías las define la empresa. Cada una tiene nombre, tipo (EPP o Herramienta, como en el vale del PDF) y una plantilla de reglas. | Idea del equipo; PDF p.5 |
| CF-02 | La plantilla propone, para los artículos de esa categoría: control, retorno, requisitos especiales, límite y aviso de cantidad inusual. Al crear un artículo se copia la plantilla, y el artículo puede cambiar cualquier valor. | Propuesta |
| CF-03 | Al mover un artículo a otra categoría, el sistema pregunta si se aplican las reglas de la nueva. | Propuesta |
| CF-04 | Una categoría puede reaplicar su plantilla a todos sus artículos. Antes de guardar se muestra qué cambia en cada uno. | Propuesta |
| CF-05 | El control (por pieza o por cantidad) y el retorno (retornable o consumible) quedan fijos cuando el artículo ya tiene movimientos. Para cambiarlos se crea un artículo nuevo y se inactiva el anterior. | Propuesta |

Categorías iniciales. Son un punto de partida; la empresa las cambia cuando quiera. **(Cambia con FEAT-018, iteración 01, sin construir):** la columna «Qué es» lleva las definiciones de AV-01 que pidió el track (plática 8 oct 2026, punto 7), y la columna «Alto valor» es la marca editable `categoria.alto_valor` (AV-04). Una herramienta que es eléctrica y de alto valor cuenta **solo como alto valor** (AV-03).

| Categoría | Tipo | Qué es (AV-01) | Control | Retorno | Reglas de la plantilla | Alto valor | Ejemplos |
|---|---|---|---|---|---|---|---|
| EPP básico | EPP | EPP que se da una vez y se devuelve al terminar | Por cantidad | Retornable | Límite de 1 en posesión | No | Casco, respirador, peto, polainas |
| EPP de dotación | EPP | EPP que se gasta | Por cantidad | Consumible | Límite por periodo | No | Guantes, lentes, tapones, filtros, camisola, calzado |
| Equipo de alturas | EPP | — (AV-01 no la cambia) | Por pieza | Retornable | Inspección vigente | No (cuenta con el alto valor en las vistas de «alto valor y alturas», AV-04) | Arnés, bandola, gancho doble de vida, retráctil |
| Herramienta manual | Herramienta | — (AV-01 no la cambia) | Por cantidad | Retornable | Sin reglas extra | No | Marro, cincel, flexómetro, extensión |
| Herramienta eléctrica | Herramienta | Herramienta que funciona con corriente o batería | Por pieza | Retornable | Sin reglas extra | No | Minipulidor, reflector |
| Equipo de alto valor | Herramienta | Herramienta o equipo caro o crítico | Por pieza | Retornable | Límite de 1 en posesión | **Sí** | Detector de gases, radio |
| Consumibles de trabajo | Herramienta | — (AV-01 no la cambia) | Por cantidad | Consumible | Límite por periodo | No | Discos de corte, soldadura |

Un artículo de cualquier categoría es además de alto valor si su costo unitario llega al tope `ALTO_VALOR_COSTO_MINIMO` (AV-02, sección 5.5).

### 5.2 Requisitos especiales

Un requisito especial es una condición extra para entregar un artículo. Sirve para la herramienta que pide un uso especial por la razón que la empresa decida.

| ID | Regla | Origen |
|---|---|---|
| CF-06 | Hay tres requisitos, cada uno se activa o se quita por artículo: **inspección vigente** de la pieza (rojo si falta), solo en artículos por pieza; **autorización del supervisor** en cada entrega (naranja); **habilitación vigente** del trabajador, como la capacitación de alturas (naranja). | PDF p.2 y p.4; idea del equipo |
| CF-07 | Un artículo con requisitos lleva un motivo corto que el almacenista ve al escanear, por ejemplo "Equipo de alturas" o "Uso restringido por seguridad". | Idea del equipo |
| CF-08 | Activar o quitar un requisito aplica desde ese momento. No cambia los vales ya emitidos ni recoge lo que ya está con trabajadores. | Propuesta |
| CF-09 | Al activar la inspección en un artículo, sus piezas quedan sin inspección vigente y no se entregan hasta inspeccionarse. | Propuesta |

### 5.3 Inactivar y reactivar

| ID | Regla | Origen |
|---|---|---|
| CF-10 | Inactivar un artículo exige un motivo. Desde ese momento no se entrega ni se le registran entradas. Su historial se conserva. | Idea del equipo |
| CF-11 | Las existencias de un artículo inactivo siguen visibles y se pueden trasladar. Lo que esté con trabajadores se sigue pudiendo devolver (SM-05). | Propuesta |
| CF-12 | Un artículo solo se elimina si no tiene movimientos. Con movimientos, solo se inactiva. | Propuesta |
| CF-13 | Reactivar un artículo lo regresa a operar con las reglas que tenía. | Idea del equipo |
| CF-14 | Inactivar una categoría impide asignarla a artículos nuevos. Los artículos que ya la tienen la conservan. | Propuesta |
| CF-15 | Todo cambio de catálogo queda registrado: quién, cuándo, valor anterior y valor nuevo. | Propuesta |

### 5.4 Parámetros que la empresa ajusta

| Parámetro | Dónde se define | Valor inicial |
|---|---|---|
| Límite por trabajador (cantidad y periodo) | Artículo; lo propone la categoría | Sin límite |
| Aviso de cantidad inusual por renglón | Artículo; lo propone la categoría | Sin aviso |
| Vigencia de la inspección | Artículo; lo propone la categoría. **(Cambia con FEAT-016, sin construir):** cambiarla aplica a las inspecciones que se registren desde ese momento; no recalcula las piezas ya inspeccionadas (P-09) | 180 días (supuesto) |
| Aviso de inspección por vencer | General. **(Cambia con FEAT-016, sin construir):** general (`INSPECCION_AVISO_DIAS`), categoría (`categoria.dias_aviso_inspeccion`) y artículo (`articulo.dias_aviso_inspeccion`); gana el artículo, luego la categoría, luego el general; de 1 a 90 días (P-10) | 7 días antes |
| Mínimo de existencias | Artículo y almacén | Sin mínimo |
| Dotación recomendada | Puesto | Vacía |
| Tope de cantidad por fila en la importación (I-11) | General | 100 000 |
| Vigencia de una solicitud de autorización | General. **(Cambia con FEAT-014, sin construir):** una solicitud **aprobada** sirve 15 minutos desde que se aprobó, para dar tiempo a la firma (DE-09) | 15 minutos |
| Intentos fallidos de PIN antes de bloquear | General | 5 intentos, bloqueo de 5 minutos |
| Formas de firma permitidas | General | En pantalla y en papel |
| Despacho de EPP con aprobación (FEAT-014, sin construir) | Almacén (`almacen.despacho_epp_con_aprobacion`) y usuario (`usuario.despacho_autonomo`); solo los cambia quien tiene `despacho.autonomia` (DE-14) | Con aprobación; ningún almacenista con autonomía |
| Tope de alto valor (FEAT-018, sin construir) | General (`ALTO_VALOR_COSTO_MINIMO`) (AV-02) | 10 000 pesos |
| Proyectos por vencer en el Inicio (FEAT-013, sin construir) | General (fijo) (TB-08) | 7 días |
| Horas máximas sin conexión (FEAT-020, sin construir) | General (`SINCRONIZACION_HORAS_MAXIMAS`) (OF-15) | 24 horas desde la última descarga |
| Tamaño máximo del lote de sincronización (FEAT-020, sin construir) | General (`SINCRONIZACION_LOTE_MAXIMO`) (OF-23) | 20 operaciones (o unos 2 MB) |
| Versión mínima de la app de Android (FEAT-020, sin construir) | General (`APP_VERSION_MINIMA`) (OF-02) | La que fije el despliegue |
| Hora de descarga del paquete sin conexión (FEAT-020, sin construir) | Almacén (`almacen.hora_descarga`); la edita el Administrador; vacía = sin descarga programada (OF-14) | 06:00 (propuesta) |

En el MVP los parámetros generales son valores fijos de configuración; los de artículo, categoría y almacén se editan en pantalla. Los generales de la iteración 01 viven en `.env` (documentados en `.env.example`): cambiarlos pide reiniciar la aplicación y no tienen pantalla; una pantalla de ajustes generales queda pospuesta (T-5 del maestro).

### 5.5 Alto valor

**Iteración 01, aprobada, sin construir.** [FEAT-018](../features/FEAT-018-deudores-resguardo-y-alto-valor.md). Responde a la plática del 8 oct 2026 (puntos 6 y 7): saber en todo momento dónde está el equipo de alto valor y definir qué es cada categoría.

| ID | Regla | Origen |
|---|---|---|
| AV-01 | **Definiciones.** EPP básico: EPP que se da una vez y se devuelve al terminar (retornable, por cantidad, límite de 1 en posesión). EPP de dotación: EPP que se gasta (consumible, por cantidad, límite por periodo). Herramienta eléctrica: herramienta que funciona con corriente o batería (por pieza, retornable). Equipo de alto valor: herramienta o equipo caro o crítico (por pieza, retornable, límite de 1 en posesión). Las otras tres categorías iniciales no cambian. Están en la tabla de 5.1. | Plática 8 oct 2026 |
| AV-02 | **Qué es alto valor.** Un artículo es de alto valor si su categoría tiene `alto_valor = true` **o** si su costo unitario es igual o mayor que `ALTO_VALOR_COSTO_MINIMO` (10 000 por omisión). Sin costo, solo cuenta su categoría. Se calcula **al leer** y nunca se guarda en el artículo: cambiar el tope o la marca aplica en la siguiente consulta, sin migración. | Decisión del usuario (8 oct 2026) |
| AV-03 | **Alto valor gana sobre eléctrica.** En los resúmenes por tipo (Deudores, Inicio) un artículo de alto valor cuenta solo como alto valor, aunque su categoría sea eléctrica. Al crear o importar un artículo con costo igual o mayor que el tope se **sugiere** «Equipo de alto valor» (amplía I-14); si el formulario o el archivo traen otra categoría, esa manda y se avisa «Por su costo cuenta como alto valor». Un artículo de alto valor por cantidad se permite, con el aviso «Conviene controlarlo por pieza, con serie». | Decisión del usuario (8 oct 2026); plática 8 oct 2026 |
| AV-04 | **La marca se edita y no depende del nombre.** `categoria.alto_valor` se cambia en Categorías con `catalogo.administrar` y queda en el registro de cambios (CF-15). Nace `true` en «Equipo de alto valor» y `false` en las demás. Ningún cálculo lee el nombre de la categoría: la tarjeta «Alto valor fuera del almacén», el filtro de Seguimiento y el aviso de baja cuentan lo de alto valor (AV-02) **más** lo que requiere inspección (equipo de alturas). Reemplaza la comparación por nombre de SG-04 y SG-06. | Decisión del usuario (8 oct 2026) |
| AV-05 | **Decir «es alto valor» no revela el costo.** La API expone `alto_valor` como booleano a quien ve el artículo; el costo y si la marca vino por la categoría o por el costo solo los ve quien tiene `catalogo.costos` (RG-12). | Propuesta |

Cómo se aplica en el servidor: una sola expresión en `catalogo`, `categoria.alto_valor OR (articulo.costo_unitario IS NOT NULL AND articulo.costo_unitario >= tope)`, que usan los demás módulos al leer; para «alto valor y alturas» se le suma `OR articulo.requiere_inspeccion`. El tope vive en `.env` (T-5 del maestro).

---

## 6. Firma y evidencia del vale

Objetivo: que el vale sirva como prueba de que el trabajador recibió el equipo, y que el trabajador también confíe en él. En la plática pidieron las dos cosas: la firma, porque sin ella el trabajador puede decir que no lo sacó (min 22), y una copia en su poder, porque teme que el registro electrónico se manipule (min 23).

| ID | Regla | Origen |
|---|---|---|
| F-01 | **Pospuesta (T-04).** En el alta, el trabajador firma una sola vez en papel una carta en la que acepta que los vales firmados en el sistema valen como firmados a mano, y recibe el aviso de privacidad. | Propuesta |
| F-02 | Cada entrega se firma de una de dos formas. En pantalla: con el dedo, debajo de la lista de artículos y de la leyenda de responsabilidad. En papel: se imprime el ticket en dos copias, el trabajador firma y el almacenista fotografía la copia firmada. Sin una de las dos, el vale no se cierra. | PDF p.8 paso 5; plática min 22–23 |
| F-03 | El almacenista firma con su sesión (usuario y contraseña). No dibuja firma en cada vale. | Propuesta |
| F-04 | El supervisor firma solo cuando autoriza (sección 4.3). No valida cada vale. **(Cambia con FEAT-014, iteración 01, sin construir):** el supervisor también aprueba el **despacho de EPP** cuando el almacén o el almacenista no tienen autonomía (DE-01); se aprueba **antes** de la firma del trabajador, para que firme solo lo que recibe (DE-03). Fuera de eso, sigue sin validar cada vale. | Plática min 42; plática 8 oct 2026 |
| F-05 | Con el vale se guarda: lectura de la credencial, firma o foto del ticket firmado, fecha y hora, dispositivo y usuario. | Propuesta |
| F-06 | Al guardar, el vale se sella: se calcula una huella criptográfica de su contenido encadenada con la del vale anterior. Cualquier alteración posterior se detecta. | Plática min 23 |
| F-07 | El QR del vale abre una vista de solo lectura que indica si el vale está íntegro. | PDF p.8 paso 6, p.9 |
| F-08 | En la devolución firma el almacenista con su sesión y el trabajador recibe un comprobante. | PDF p.8 paso 7; plática min 5 |
| F-09 | En el traspaso firman con su sesión quien envía y quien recibe. | PDF p.6: "recepción firmada" |
| F-10 | El trabajador siempre se lleva una copia: el ticket impreso, o el QR del vale, que abre su comprobante en el celular. | Plática min 23 |
| F-11 | Al escanear la credencial se muestra la foto del trabajador tomada en el alta (T-09). El almacenista confirma que es la persona. Si no tiene foto, se avisa y la entrega continúa. | Plática min 16 |
| F-12 | Ningún vale, ticket o comprobante muestra costos (RG-12). | Plática min 38 |

Sustento (referencia, no asesoría legal; la empresa debe validarlo con su abogado):

- La Ley Federal del Trabajo admite como prueba documentos digitales, firma electrónica y contraseña (art. 776 fracción VIII y arts. 836-A a 836-D). Si el trabajador desconoce el vale, un perito revisa que el documento esté íntegro y sea atribuible a él.
- El Código de Comercio (arts. 89 y 97) distingue la firma electrónica simple de la avanzada. La firma en pantalla es simple: es válida, pero su fuerza depende de la evidencia que la acompaña. Por eso F-01, F-05 y F-06.
- En producción, el sello F-06 se refuerza con una constancia de conservación NOM-151-SCFI-2016 emitida por un prestador autorizado.
- El trabajador no responde por el desgaste normal (LFT art. 134 fracción VI). Coincide con lo dicho en la plática: no se cobra el daño, solo se anota (min 41).
- La huella dactilar se trata como dato personal sensible: exige consentimiento expreso y medidas de seguridad. No se incluye en el prototipo; la foto de F-11 cubre la verificación de identidad.

---

## 7. Reglas por operación

### 7.1 Alta y reingreso de trabajador (RH)

| ID | Regla | Origen |
|---|---|---|
| T-01 | La persona se identifica por su número de empleado, que **genera el servidor** al dar de alta (T-10). La CURP o el NSS son opcionales y solo los ve RH. | Plática min 56; RG-13; decisión del usuario |
| T-02 | Si la **CURP** ya existe, es un reingreso: RH registra el nuevo periodo y la misma persona se reactiva. Si el alta no trae CURP y el **nombre completo** (sin distinguir mayúsculas ni acentos) coincide con el de otra persona, el sistema avisa de la coincidencia y RH elige: reingresar a esa persona o confirmar que es otra. Un número de empleado externo (T-10) que ya existe también ofrece el reingreso. Su historial y sus pendientes se conservan. Extender un contrato se hace igual: se registra el periodo nuevo. **(Cambia con FEAT-013, iteración 01, sin construir):** el reingreso pide proyecto cuando el trabajador no tiene una asignación activa a un proyecto asignable; si la tiene, se propone esa (PR-11). | Plática min 18; decisión del usuario |
| T-03 | Datos obligatorios: nombre, puesto, área u obra, y periodo del contrato (inicio y fin); el número de empleado lo asigna el servidor. Opcionales: tallas, CURP o NSS. **(Cambia con FEAT-013, iteración 01, sin construir):** «área u obra» se reemplaza por el **proyecto**, obligatorio y asignable; el alta pide además `proyectos.asignar` y el área u obra se llena con el nombre del proyecto (PR-11). | PDF p.3, p.5; plática min 17 y 40; decisión del usuario |
| T-04 | **Pospuesta.** La carta de aceptación firmada (F-01) no es requisito del alta en el MVP: el trabajador queda Activo al guardar. Se mantiene en el plan del producto para el hackathon, sin bloquear el alta. | Decisión del equipo |
| T-05 | La credencial que se escanea es la que emite la planta: en el alta se escanea una vez para ligarla al trabajador. Si no trae código legible, el sistema genera un QR para imprimir. También se puede teclear el número. | Plática min 17 y 57; PDF p.8 paso 1 |
| T-06 | Estados: Activo, Baja en proceso, Inactivo. | PDF función 7; plática min 19 |
| T-07 | Un trabajador es vigente si está Activo y hoy cae dentro de su periodo de contrato. | Plática min 17–18 |
| T-08 | RH consulta desde su celular la situación de cada trabajador: qué tiene pendiente y si ya tiene vale de no adeudo. | Plática min 15 |
| T-09 | En el alta, RH toma la foto del trabajador con la cámara del dispositivo o sube una imagen (F-11). Es opcional: sin foto, la ficha dice "Sin foto registrada" y la entrega continúa. RH la puede reemplazar y el cambio queda en el registro de cambios. La foto es un dato personal: solo la ve quien tiene `trabajadores.ver` y nunca aparece en un comprobante. | Decisión del equipo |
| T-10 | **El número de empleado lo genera el servidor** y no se repite. Es un consecutivo propio con formato `E-000001`, de un contador (`serie_empleado`) que se bloquea y avanza en la misma transacción que guarda al trabajador: sin huecos ni repetidos, aunque dos personas den de alta a la vez. El formulario de alta no lo pide y la respuesta devuelve el asignado. Solo quien tiene `trabajadores.numero_externo` (de inicio, el Administrador) puede capturar a mano un número propio del centro, por ejemplo en una carga histórica: debe ser único y el trabajador queda marcado como **externo** (`numero_externo`). Quien no tiene el permiso y manda un número recibe 403. Los trabajadores que ya existían conservan su número y quedan marcados como externos. No es el código de la credencial (`TRB-XXXXXXXX`), que es lo que lleva el QR (T-05). | Decisión del usuario |

### 7.2 Entrada de inventario (Compras)

| ID | Regla | Origen |
|---|---|---|
| I-01 | Las existencias nacen solo con una entrada: de Proveedor al **almacén central (Kepler)**. Las compras y la carga inicial entran por Kepler; de ahí se reparten por traspaso (EK-01, EK-02). | Plática min 5 y 32; FEAT-011 |
| EK-01 | La entrada de proveedor (vale ENTRADA) y la importación de inventario (altas y reposición) entran **únicamente al almacén de tipo CENTRAL**, que el servidor resuelve por su tipo y no por su clave. Si el cuerpo trae otro `almacen_id` o `destino_almacen_id`, se rechaza con 422 `ENTRADA_SOLO_KEPLER`, también para quien tiene `almacenes.todos`. Sin `almacenes.todos`, además, el usuario debe estar asignado a Kepler (AC-06). Si Kepler está cerrado, no recibe (AL-04). | FEAT-011 |
| EK-02 | La carga inicial también entra por Kepler y se reparte por traspaso. En la importación, una columna `almacen` del archivo se **ignora con un aviso**: nunca crea entradas fuera de Kepler. | FEAT-011 |
| EK-03 | La interfaz no ofrece selector de almacén en «Entrada de proveedor» ni en la importación, y la plantilla de Excel no trae la columna `almacen`; el texto dice «Entra a Kepler». | FEAT-011 |
| EK-04 | Entrada de proveedor e importación se presentan como una sola pantalla «Dar entrada», con dos métodos (a mano o Excel). Conservan la diferencia entre Alta y Reposición. | FEAT-011 |
| EK-05 | El vale de entrada de una solicitud de compra ingresada es de Kepler; el almacén que la pidió la recibe después por traspaso (SC-06). | FEAT-011 |
| EK-06 | Al crear o editar un almacén, el servidor valida el tipo del padre (422 `PADRE_INVALIDO`): un PROYECTO solo depende de un SUBALMACEN, un SUBALMACEN solo del CENTRAL y el CENTRAL no tiene padre, para que la ruta X-03 no se rompa por configuración. | FEAT-011 |
| EK-07 | Crear un artículo desde «Dar entrada». En «Capturar a mano», cuando lo buscado no existe, quien tiene `catalogo.administrar` puede darlo de alta con nombre, categoría y unidad: la categoría decide si es por cantidad o por pieza (CF-02) y el servidor genera el código `PREFIJO-NNNN` de esa categoría con el mismo consecutivo de la importación en modo Alta (`POST /api/articulos` sin `codigo`). Se rechaza un nombre que ya existe (409 `ARTICULO_REPETIDO`), una categoría inactiva (422 `categoria_id`) y una categoría de la empresa que no genera códigos (422 con `motivo` `FALTA_CODIGO`: se escribe el código). Sin el permiso la pantalla solo dice que el artículo no existe y que pidan darlo de alta. El artículo queda en el catálogo aunque la entrada no se confirme. | FEAT-011 |
| I-02 | Cada pieza entra con su código único; el código es obligatorio o lo genera el sistema (I-15). El número de serie del fabricante es **opcional**: sin él la pieza entra con **serie pendiente** (se deriva de `numero_serie` vacío; no hay estado nuevo) y se completa después (P-08). Un código repetido se rechaza, y una serie repetida en el mismo artículo sigue siendo error. La serie pendiente no bloquea la entrada, el traspaso ni la devolución; en la entrega da un aviso (E-29). | PDF p.2; plática min 37; decisión del usuario |
| I-03 | Una pieza que requiere inspección entra con su inspección inicial (fecha y resultado). Sin ella queda pendiente y no se puede entregar. **(Cambia con FEAT-016, iteración 01, sin construir):** la fecha de la inspección inicial no puede ser posterior a hoy (P-17). | PDF p.2 |
| I-04 | El costo unitario se captura en el catálogo, al crear o editar el artículo, y en la importación de inventario (solo en artículos nuevos), siempre con el permiso `catalogo.costos`. La reposición (I-10) nunca cambia el costo de un artículo. La entrada de inventario no recibe costos: el vale nunca lleva costos (RG-12, F-12). Sirve para valuar el inventario y solo lo ve quien tiene `catalogo.costos`; de inicio, Compras. | PDF p.10; plática min 38–39; decisión del equipo |
| I-05 | Cada artículo puede tener un mínimo por almacén. Se compara contra lo disponible: no cuenta lo No apto, en mantenimiento ni en calibración. Al bajar del mínimo se marca en rojo en la pantalla de Compras. | Plática min 47 y 50 |
| I-06 | El inventario se carga pegando o subiendo una tabla de Excel, con vista previa antes de guardar. Hay dos modos (I-10): **alta**, que crea los artículos nuevos y suma a los que ya existen, y **reposición**, que solo suma a los que ya existen. Las filas del mismo artículo por cantidad y almacén se consolidan en una (se suman y se avisa «Unido: filas 2, 5, 9»); un código de pieza o una serie repetidos siguen siendo error; la columna de serie puede ir vacía (serie pendiente, I-02) y el código de pieza también (I-15). Una fila cuya descripción dice SERVICIO no es un artículo: se excluye con aviso. | Plática min 34; decisión del usuario |
| I-07 | Todo artículo por cantidad tiene un QR de producto que se imprime como etiqueta de estante. | Plática min 20–21 |
| I-08 | Si falta una herramienta, el supervisor o el almacenista levanta una solicitud de compra urgente; Compras la atiende y registra la entrada. Construida: ver la sección 7.13 (SC-01 a SC-11). | Plática min 45; decisión del usuario |
| I-09 | No se registran entradas de un artículo inactivo (CF-10). | Idea del equipo |
| I-10 | La importación tiene dos modos, `ALTA` (por omisión) y `REPOSICION`. **Alta:** carga inicial; crea los artículos nuevos y suma a los que ya existen. **Reposición:** solo suma a artículos que ya existen y nunca crea; un código que no existe es un error de esa fila (`ARTICULO_NO_EXISTE`, «Ese artículo no existe: dalo de alta primero»). En reposición las columnas nombre, marca, categoría y costo se ignoran con un aviso y el costo del artículo no cambia (I-04). Los dos exigen `inventario.entradas`; el alta, cuando va a crear artículos, exige además `catalogo.administrar` (sección 8.2). (Nota: el traspaso por lista de Excel no es un tercer modo; tiene sus propios endpoints, ver TR-01 y TR-03.) | Decisión del usuario |
| I-11 | Cada fila trae como máximo 100 000 unidades; más se rechaza como error de esa fila (`CANTIDAD_EXCESIVA`). El tope es un ajuste general (sección 5.4) y protege contra un cero de más al capturar. | Decisión del usuario |
| I-12 | Si el mismo archivo ya se importó, el sistema avisa; no es un error. El aviso sale en la vista previa y la confirmación pide `confirmar_repetido: true` para continuar. «El mismo archivo» es la misma huella: el `sha256` del modo, las filas ya normalizadas (sin vacías, sin espacios de más y en un orden fijo) y el almacén por defecto. La huella queda en `despues.huella` del registro de auditoría `importacion.confirmar`; no hay tabla nueva. Es distinta de la repetición por `id_lote`, que reintenta una misma confirmación sin crear nada. | Decisión del usuario |
| I-13 | La cantidad es un entero. Un decimal como `0.25` se rechaza con un mensaje que pide usar una unidad entera menor («250 gramos» en lugar de «0.25 kilos»); **nunca se redondea**. Una coma decimal ambigua como `0,25` o `1,5` también se rechaza: la coma solo vale como separador de miles, en grupos de tres dígitos (`1,250` es 1250). Un valor entero escrito como `12.0` se acepta como 12. Código de motivo: `CANTIDAD_NO_ENTERA`. Se mantiene aunque exista la columna `unidad` (I-16): no hay conversión automática de unidades; el archivo declara la unidad menor y la cantidad en esa unidad. | Decisión del usuario |
| I-14 | Sugerencia de categoría. Para un artículo nuevo cuyo archivo no trae categoría, el servidor **sugiere** una según las palabras de la descripción (diccionario en [FEAT-007](../features/FEAT-007-importacion-reposicion-y-categoria-sugerida.md)). Es solo una sugerencia: la vista previa la muestra por fila con su motivo y se puede cambiar; nada se aplica sin que el usuario la vea. Lo que no coincide con ninguna regla queda «por revisar» y esa fila no entra hasta elegir una categoría. Si el archivo trae la columna de categoría, esa manda. Solo aplica en el modo alta. **(Cambia con FEAT-018, iteración 01, sin construir):** un artículo nuevo sin categoría y con costo igual o mayor que el tope de alto valor recibe la sugerencia «Equipo de alto valor», aunque la descripción diga eléctrica; si el archivo trae categoría, manda esa y la fila avisa «Por su costo cuenta como alto valor» (AV-03). Sin `catalogo.costos` no hay sugerencia por costo. | Decisión del usuario |
| I-15 | **Código de pieza automático (modo alta).** Si el archivo no trae código de pieza, el servidor lo genera al confirmar con el formato `CÓDIGO-DEL-ARTÍCULO-NNN` (por ejemplo `HEL-0003-001`, `HEL-0003-002`), único contra la tabla de códigos y bajo el mismo bloqueo que el código de artículo. Si el archivo lo trae, se respeta tal como viene (RG-10). La vista previa lo muestra como provisional. El código generado no está pegado en la herramienta hasta imprimir su etiqueta. El alta manual de una pieza por vale **no cambia**: el usuario captura el código. | Decisión del usuario |
| I-16 | **Columna `unidad` (modo alta).** Es opcional: texto de hasta 20 caracteres, por omisión «pieza». Se usa al crear un artículo nuevo. No cambia la unidad de un artículo que ya existe: si el archivo trae otra, solo avisa en esa fila, igual que con el nombre y la marca. I-13 se mantiene: cantidades enteras, sin conversión automática y sin redondeo. | Decisión del usuario |
| I-17 | **Serie pendiente en la importación.** En el modo alta, una fila de pieza sin número de serie ya no es error: entra con aviso amarillo `SERIE_PENDIENTE` («Serie pendiente»). Una serie repetida, contra la base o dentro del mismo archivo, sigue siendo error. | Decisión del usuario |

Cómo se aplican I-06 y I-10 a I-14 en el servidor (la forma exacta está en [api-contracts.md](../architecture/api-contracts.md#importación)):

- **Un solo camino.** La vista previa y la confirmación aplican la misma revisión a cada fila; las filas buenas entran sin esperar a las malas, y todo lo que entra va en una sola transacción (RG-09).
- **Consolidación (I-06).** Filas con el mismo artículo y el mismo almacén, en un artículo por cantidad, se suman en una sola y se avisa «Unido: filas 2, 5, 9». Una fila sin código se une con otra del mismo nombre y marca, comparados sin acentos, sin mayúsculas y sin espacios de más. En un artículo por pieza cada fila es una pieza y no se une con nada.
- **Código generado.** Si una fila de un artículo nuevo no trae código, el servidor lo genera: `PREFIJO-NNNN`, consecutivo por categoría, asignado dentro de la transacción de la confirmación (en la vista previa solo se muestra como provisional). Prefijos: EPB (EPP básico), EPD (EPP de dotación), ALT (Equipo de alturas), HMA (Herramienta manual), HEL (Herramienta eléctrica), EAV (Equipo de alto valor) y CON (Consumibles de trabajo). Una categoría creada por la empresa no tiene prefijo: en ella el código se pide en el archivo.
- **Artículo que ya existe.** Solo recibe la entrada. Si el nombre, la marca o la categoría del archivo no coinciden con los del artículo, se avisa en esa fila y no se actualiza nada.
- **Servicio.** Una fila cuya descripción tiene la palabra SERVICIO se excluye con un aviso y no cuenta como error.
- **Permisos.** Con `inventario.entradas` se importa en cualquiera de los dos modos. Una fila de alta que crearía un artículo, sin `catalogo.administrar`, es un error de esa fila (`SIN_PERMISO_CREAR`); las filas de artículos que ya existen sí entran. Hasta ahora el alta no pedía `catalogo.administrar`: es un cambio de política. Compras ya tiene los dos permisos y no cambia nada para ella.
- **Concurrencia.** Dos importaciones al mismo tiempo con los mismos códigos nunca duplican un artículo ni una pieza ni descuadran las existencias: una gana, y la otra suma al artículo que ya existe o recibe el conflicto del servidor sin guardar nada.
- **Descarga de errores.** El archivo de filas con error neutraliza toda celda que empiece con `=`, `+`, `-`, `@`, tabulador o retorno de carro, anteponiéndole un apóstrofo, para que Excel no la ejecute como fórmula.

### 7.3 Entrega (almacenista)

Pasos: escanear credencial, confirmar la foto, escanear artículos, resolver naranjas, firma del trabajador, vale.

**(Cambia con FEAT-013 y FEAT-014, iteración 01, sin construir):** al identificar al trabajador, la entrega toma su proyecto (PR-08 a PR-10). Si el despacho pide aprobación (DE-01), después de escanear los artículos se envía **una** solicitud al supervisor con el EPP y los naranjas, y la firma del trabajador va **después** de la aprobación: capturar, solicitar, aprobar, quitar lo rechazado, firmar y confirmar (DE-03, decisión D-08).

| ID | Condición al escanear | Nivel | Origen |
|---|---|---|---|
| E-01 | El código no existe en el catálogo. | Rojo | Propuesta |
| E-02 | El trabajador no es vigente: está Inactivo, en Baja en proceso o fuera de su periodo de contrato. Mensaje: "ya no forma parte de la plantilla". | Rojo (todo el vale) | PDF función 7; plática min 18 |
| E-03 | La pieza no está en este almacén según el sistema: la tiene otro trabajador, está en otro almacén o en tránsito. El renglón queda en rojo. Quien tiene `almacenes.todos` (el Administrador) ve dónde está; los demás ven solo «Esta pieza no está registrada en tu almacén. No se puede entregar.», sin el almacén ni el trabajador que la tiene (AC-06). Una pieza en tránsito desde o hacia el almacén del usuario sí se explica (se envió o se recibe por el traspaso). | Rojo | Propuesta |
| E-04 | La cantidad supera la existencia disponible del almacén. | Rojo | PDF p.8 paso 4 |
| E-05 | La pieza está No apta, En mantenimiento, En calibración o en Baja. | Rojo | PDF p.2; plática min 46–47 |
| E-06 | La pieza requiere inspección y no tiene una vigente. | Rojo | PDF p.2, p.8 |
| E-07 | Supera el límite del artículo (4.1). | Naranja | PDF función 6 |
| E-08 | El artículo pide una habilitación (CF-06) y el trabajador no la tiene vigente. | Naranja | PDF p.4, p.9 (opcional) |
| E-09 | Está fuera de la dotación o supera lo recomendado (4.2). Pide observación. | Amarillo | Idea del equipo; plática min 36 |
| E-10 | La talla no coincide con la del trabajador. Sin observación. | Amarillo | PDF p.8 paso 4 |
| E-11 | La inspección vence en 7 días o menos (hoy incluido). Sin observación. **(Cambia con FEAT-016, iteración 01, sin construir):** vence en N días o menos, donde N es el aviso resuelto del artículo: el suyo, el de su categoría o el general (P-10). | Amarillo | Propuesta |
| E-12 | El trabajador trae pendientes de un periodo anterior. | Amarillo | Plática min 9 |
| E-14 | La entrega deja al almacén por debajo del mínimo (I-05). | Amarillo | Plática min 47 |
| E-15 | La pieza ya está en este vale. | Se ignora con sonido | Propuesta |
| E-16 | El artículo por cantidad ya está en este vale; incluye volver a escanear el QR del estante. | Suma 1 a la cantidad | PDF p.8 paso 3; plática min 21 |
| E-19 | El artículo está inactivo (CF-10). | Rojo | Idea del equipo |
| E-26 | El artículo pide autorización del supervisor en cada entrega (CF-06). Se muestra su motivo. | Naranja | Idea del equipo |
| E-27 | La cantidad del renglón es igual o mayor que el aviso de cantidad inusual del artículo (5.4). Se pide confirmar la cantidad antes de continuar. | Amarillo | Idea del equipo |
| E-29 | La pieza no tiene número de serie registrado (serie pendiente, I-02). Aviso: no bloquea la entrega ni pide observación; el aviso invita a completar la serie (P-08). Traspaso y devolución no cambian. | Amarillo | Decisión del usuario |

Otras reglas de la entrega:

| ID | Regla | Origen |
|---|---|---|
| E-17 | Al identificar al trabajador se muestran su foto, su vigencia y lo que ya tiene en resguardo. | Plática min 10 y 16 |
| E-18 | Si el artículo no tiene etiqueta, se escanea el QR de su estante o se busca por nombre. Si la etiqueta de una pieza no se lee, se busca por su número de serie (una pieza con serie pendiente no se encuentra así: se identifica por su código, I-02). Si la credencial no se puede leer, se teclea el número del trabajador. **(Cambia con FEAT-019, iteración 01, sin construir):** el trabajador también se encuentra por su nombre en cualquier orden y por el inicio del código de su credencial, mientras se escribe (UX-01, UX-03). | Plática min 3 y 20–21 |
| E-20 | Retornable: movimiento de almacén a trabajador. | PDF función 4 |
| E-21 | Consumible: movimiento de almacén a Consumido, con el trabajador anotado. Así queda su historial de consumo. | Plática min 31 |
| E-22 | Se registra la condición al salir de cada renglón. | PDF p.4 |
| E-24 | El vale lleva folio, fecha y hora, trabajador, área u obra, descripción con marca, código o serie, cantidad, condición, responsable y QR. No lleva costos. **(Cambia con FEAT-013, iteración 01, sin construir):** donde imprime el área u obra, el vale de entrega imprime el **proyecto de la entrega** (`vale.proyecto_id`); sin proyecto, el área u obra del periodo (PR-14). Con FEAT-014, «Validó» dice quién aprobó el despacho o «él mismo». | PDF p.8 paso 6; plática min 38 y 51 |
| E-25 | No hay plazo por préstamo: la herramienta puede quedarse todo el proyecto. El plazo es el fin del contrato. | Plática min 37 y 52 |
| E-28 | Escanear un código agrega el renglón a un borrador del vale, y el servidor lo evalúa sin escribir nada. Las existencias y el resguardo cambian solo al confirmar el vale, en una sola operación (RG-01, RG-09). Mientras no se confirme, cualquier renglón se puede quitar. **Excepción sin conexión (FEAT-020, iteración 01, sin construir):** confirmar sin conexión sí ajusta la base **local** del equipo para que la siguiente evaluación vea lo real, pero no cambia el servidor hasta que la operación se sincroniza (sección 7.20). | RG-01, RG-09; idea del equipo |

Cómo se aplican en el servidor: E-01 también cubre escanear el código de un artículo controlado por pieza en lugar del de la pieza (no hay a cuál pieza entregar). E-02 pone en rojo todos los renglones y se muestra también como motivo del vale; E-12 es un aviso del vale, no de un renglón. E-10 compara la talla del artículo (`articulo.talla`) con las tallas del trabajador (`trabajador.tallas`, por ejemplo camisa y calzado): como las tallas del trabajador no dicen a qué prenda corresponde cada una, avisa si la talla del artículo no coincide con ninguna de ellas (sin distinguir mayúsculas); si el artículo no tiene talla o el trabajador no tiene tallas, no avisa. E-11 solo aplica a piezas de artículos que requieren inspección y que ya tienen una vigente: una inspección vencida es E-06 (rojo). Una pieza se entrega de una en una (RG-05) y la condición al salir es Bueno si no se indica (E-22; un equipo dañado no se entrega). El motivo de cada renglón lleva el ID de su regla y se guarda en `movimiento.reglas`.

### 7.4 Devolución (almacenista)

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| V-01 | Pieza: al escanearla el sistema sabe quién es el titular; no hace falta la credencial. La devolución se abona al titular, la traiga quien la traiga. | Verde | Plática min 5 |
| V-02 | La pieza no está en resguardo de nadie. No hay nada que devolver; se muestra dónde está según el sistema. El renglón es Amarillo y no genera movimiento. Si todos los renglones del vale son V-02, el vale completo sale Rojo (no hay nada que devolver) y no se confirma. | Amarillo (Rojo si es lo único que trae el vale) | Propuesta |
| V-03 | Por cantidad: se identifica al trabajador y se elige de su lista. No se puede devolver más de lo que tiene. | Rojo si excede | Propuesta |
| V-04 | La condición al volver es obligatoria: Bueno, Desgaste por uso o Dañado. | — | PDF p.4; plática min 41 |
| V-05 | Dañado: exige observación y admite foto. Una pieza entra al almacén como No apta. Un artículo por cantidad no regresa a existencias: va a Baja. En ningún caso genera cargo al trabajador. | Amarillo | Plática min 41–42 |
| V-06 | Desgaste por uso no genera pendiente ni observación. | — | Plática min 41 |
| V-07 | Entra al almacén que la recibe, aunque la haya entregado otro. | Amarillo si es otro | PDF p.6; plática min 8 |
| V-09 | Cierre sin devolución: el equipo quedó instalado en planta por instrucción, o se destruyó. Exige observación con quién lo indicó y admite foto. Movimiento de trabajador a Baja, sin pendiente para el trabajador. | Amarillo | Plática min 43 |
| V-10 | Consumible sobrante: se puede devolver y reduce el consumo del trabajador en el periodo. | Verde | PDF p.4 paso 7 |
| V-11 | Se genera vale de devolución con folio y el trabajador recibe comprobante. | — | PDF p.8 paso 7 |
| V-12 | El código no existe en el catálogo: el equipo no es de la empresa. No se recibe y el pendiente del trabajador sigue abierto. | Rojo | Plática min 37 |
| V-13 | Pérdida o robo reportado: se anota en el pendiente, con observación. El artículo sigue como pendiente del trabajador hasta que lo devuelva o un supervisor lo dé por perdido (P-05). | Amarillo | Plática min 9 y 33 |
| V-14 | Una pieza con la etiqueta ilegible se devuelve eligiéndola de la lista del trabajador o buscándola por su número de serie. El almacenista compara la serie grabada con la de la pantalla. Una pieza con serie pendiente (I-02) no se encuentra por serie: se elige de la lista del trabajador o se identifica por su código. | Verde | Propuesta |

Caso "me devolvió una que no es": con código único por pieza, el escaneo lo detecta de inmediato. Si la pieza es de otro trabajador, se abona a su titular y la del que la trajo sigue pendiente. Si el código no existe, aplica V-12.

### 7.5 Traspaso: salida (almacenista de origen)

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| X-01 | El traspaso tiene dos pasos: **enviar** exige `traspasos.operar` y **recibir** exige `traspasos.recibir`; ambos con el alcance de AC-06 (el origen envía, el destino recibe). El Supervisor tiene los dos. El Almacenista trae `traspasos.recibir` de inicio (AC-31, tabla 8.2 y el script de datos de prueba), para recibir en un almacén de tercer nivel con turnos de 24 horas, y no trae `traspasos.operar`; los dos se dan o se quitan a cualquier rol desde Roles y permisos (FEAT-006, AC-34). Entre ambos pasos la existencia está En tránsito y no cuenta para ningún almacén. (Ver también TR-03: el traspaso por lista de Excel usa `traspasos.operar`.) **Corregida el 8 oct 2026 (FEAT-015):** el texto anterior decía que el Almacenista no traía ninguno de los dos de inicio; la regla no cambia, solo se alinea con la tabla 8.2. | — | PDF p.6; decisión del usuario |
| X-02 | Solo sale lo que está en el almacén de origen. | Rojo si no | PDF función 4 |
| X-03 | El destino es otro almacén activo. Rutas habituales: Kepler con Contratistas, y Contratistas con las áreas, en ambos sentidos (un almacén es padre del otro). **Otra ruta** (por ejemplo, Kepler directo a un almacén de tercer nivel) **solo la hace quien tiene `almacenes.todos`** (de inicio, el Administrador), con aviso amarillo y **observación obligatoria**. Para quien no lo tiene, es rojo. **(Cambia con FEAT-015, iteración 01, sin construir):** **entre dos almacenes de tercer nivel** la ruta es **lateral** y la autoriza el supervisor del origen: su envío es la autorización (X-16) o, si envía otro, se pide la autorización (X-17); se evalúa antes que la ruta no habitual (X-18). Las demás rutas que no son padre-hijo siguen igual. | Amarillo (habitual: verde); Rojo si no puede; lateral: amarillo (X-16) o naranja (X-17) | PDF p.6; plática min 30; decisión del usuario (FEAT-008); plática 8 oct 2026 |
| X-04 | Una pieza No apta puede trasladarse (para reparación o baja). Conserva su estado. | Amarillo | Propuesta |
| X-05 | La salida deja al origen por debajo del mínimo. | Amarillo | Plática min 47 |
| X-06 | Se genera el folio del traspaso con QR. Estado: En tránsito. | — | PDF p.6 |
| X-07 | Cada movimiento conserva origen y destino. | — | PDF p.1 |
| X-09 | Un artículo inactivo sí puede trasladarse, para concentrar o retirar sus existencias (CF-11). | — | Propuesta |

#### Traslado entre almacenes de tercer nivel

**Iteración 01, aprobada, sin construir.** [FEAT-015](../features/FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md). La plática del 8 oct 2026 pidió traslados entre almacenes de tercer nivel «siempre y cuando autorice el supervisor» (decisión D-09). La ruta habitual sigue siendo Kepler, Contratistas, tercer nivel; el traslado lateral es para lo que sobra en un almacén y falta en otro. «Tercer nivel» es el almacén de tipo `PROYECTO`, no el proyecto de 7.15.

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| X-16 | **Envío propio del supervisor del origen.** Si quien envía un traslado lateral (X-18) tiene `autorizaciones.resolver` en el almacén de origen, su envío **es** la autorización. El vale sale en amarillo con el motivo X-16, pide **observación obligatoria** (para qué se manda; sin ella, 422 con `regla: "X-16"`) y queda «Validó: *su nombre* (envío propio)». Es una excepción explícita a A-05 y AC-07: no se crea solicitud. Entra a la lista de revisión (RG-14). | Amarillo | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |
| X-17 | **Traslado lateral con autorización.** Si quien envía no tiene `autorizaciones.resolver` en el origen (por ejemplo, un almacenista con `traspasos.operar`), el vale sale en naranja con el motivo X-17 y no se confirma sin una autorización de tipo TRASLADO aprobada por el supervisor del origen (X-19). Le llega por la misma notificación push del despacho (NT), vence a los 15 minutos y se usa una vez (A-03). Rechazada o vencida, el traslado no sale y el borrador se conserva. | Naranja | Decisión del usuario (8 oct 2026) |
| X-18 | **Qué es un traslado lateral.** Origen y destino son de tipo `PROYECTO`, distintos y activos, compartan o no el subalmacén padre. Se evalúa antes de la ruta no habitual de X-03. Las demás rutas que no son padre-hijo (Kepler a un tercer nivel, un tercer nivel a Kepler, a un subalmacén que no es su padre) siguen con X-03. Quien tiene `almacenes.todos` sin `autorizaciones.resolver` hace el lateral por X-03 (amarillo y observación). | — | Decisión del usuario (8 oct 2026); Propuesta |
| X-19 | **La autorización de traslado.** Cubre origen, destino y cada renglón con su código y cantidad. Después de aprobada se pueden **quitar** renglones; agregar uno, subir una cantidad o cambiar el destino la invalida (409 `AUTORIZACION_INVALIDA`). La resuelve quien tiene `autorizaciones.resolver` en el origen, o `almacenes.todos`, nunca quien la pidió (A-05), desde su celular o con PIN en el mostrador (A-01). Se aprueba o se rechaza **completa** (sin aprobación parcial). Un renglón en rojo no se autoriza (422 `RENGLON_NO_AUTORIZABLE`, A-06). Queda quién pidió, quién autorizó, cuándo y el motivo (A-04). | — | Decisión del usuario (8 oct 2026); A-01 a A-06 |

Cómo se aplica en el servidor: la evaluación del TRASPASO trae `ruta` (`HABITUAL`, `LATERAL`, `NO_HABITUAL` o `MISMO`) y quién autoriza; los movimientos del envío propio llevan las reglas `X-16` y `X-18`, y «Validó» se deriva de ellas, sin crear autorización (el CHECK `no_autorizarse` sigue). `POST /api/autorizaciones` acepta `tipo: "TRASLADO"` sin trabajador; el permiso depende del tipo (`traspasos.operar` para TRASLADO), por eso lo verifica el servicio.

### 7.6 Traspaso: recepción (almacenista de destino)

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| X-08 | Quien recibe (con `traspasos.recibir`, por ejemplo el almacenista de un almacén de tercer nivel) queda como responsable de lo recibido. | — | Plática min 32–33; decisión del usuario |
| X-10 | Solo el almacén de destino puede recibir, y solo quien tiene `traspasos.recibir` (sin él, 403). El QR del traspaso lo abre. | Rojo si es otro | PDF p.6; decisión del usuario |
| X-11 | Se puede recibir todo de una vez o escanear renglón por renglón. | — | Propuesta |
| X-12 | Lo escaneado no pertenece a este traspaso. | Rojo | Propuesta |
| X-13 | Si falta algo, lo no recibido sigue En tránsito, el traspaso queda "Recibido con diferencias" y entra a la lista de revisión. | Amarillo | Propuesta |
| X-14 | Un traspaso en tránsito lo cancela el almacén de origen, con observación y solo antes de la recepción. La existencia regresa al origen. | Amarillo | Propuesta |
| X-15 | **Recepción por lista.** La lista de lo que debería llegar es el propio vale de traspaso, venga de un Excel (TR-01) o de captura manual. Quien recibe puede «Recibir todo», marcar renglón por renglón o escanear, y modificar la cantidad recibida si no llega exacto. **La lógica no cambia** (X-10 a X-13 y RG-14 ya lo cubren); solo mejora la interfaz para listas largas: búsqueda dentro de la lista, filtro de pendientes y progreso («12 de 80 recibidos»). | — | Decisión del usuario |
| X-20 | **Recepción del traslado lateral.** (Iteración 01, [FEAT-015](../features/FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md), sin construir.) Se recibe igual que cualquier traspaso (X-10 a X-13, X-15). Al confirmarse la salida, quienes tienen `traspasos.recibir` y el destino en su conjunto, con los avisos activos, reciben una notificación push **informativa** («HYL · Te enviaron un traslado desde Midrex», después del commit, con NT-03, NT-05 y NT-07); el traslado aparece en «Por recibir» con la etiqueta «Traslado desde Midrex» y quién lo validó. Al evaluar la salida se avisa en amarillo, sin pedir observación, si en el destino no hay nadie activo con `traspasos.recibir` o si el destino no tiene proyectos activos (PR-12). | Amarillo (avisos) | Decisión del usuario (8 oct 2026); Propuesta |
| X-21 | **Envió y recibió la misma persona.** (Iteración 01, FEAT-015, sin construir.) Si quien confirma una recepción es quien envió el traspaso (posible con dos almacenes en su conjunto, AC-36), se permite con aviso amarillo X-21 y **observación obligatoria** (422 con `regla: "X-21"` sin ella); el vale de recepción queda marcado «Envió y recibió la misma persona» y entra a revisión. Aplica a todo traspaso. | Amarillo | Propuesta |

Cómo se aplican en el servidor (salida y recepción). El destino de una salida es habitual si un almacén es el padre del otro en la red (`almacen.padre_id`); mismo almacén, un destino que no existe o uno cerrado son rojos de X-03. **Ruta que no es habitual:** quien no tiene `almacenes.todos` ve el vale en rojo con el motivo X-03 («Solo el Administrador puede enviar por una ruta que no es habitual: usa la ruta por Contratistas.») y, al confirmar, el servidor responde 403 `RUTA_SOLO_ADMINISTRADOR` sin guardar nada; quien sí lo tiene ve un aviso amarillo X-03, la evaluación trae `pide_observacion: true` y la confirmación exige una `observacion` en el vale (sin ella, 422 con `detalles: [{campo: "observacion", mensaje, regla: "X-03"}]`, como en RG-14). Lo que decide es el permiso, nunca el nombre del rol. Un traspaso que sale o llega a un almacén cerrado se rechaza por AL-04. X-04 cubre toda pieza que no esté Apta (No apta, En mantenimiento, En calibración): se traslada con aviso y conserva su estado. X-09 solo informa (nivel verde). Una salida con un renglón en rojo no se confirma (RG-09) y un traspaso sin renglones se rechaza. Enviar pide `traspasos.operar` y recibir pide `traspasos.recibir` (X-01, X-10); un usuario con uno y sin el otro recibe 403 en el paso que no tiene. En la recepción, "todo de una vez" es mandar todos los renglones pendientes del traspaso (la lista de por recibir los trae) y "renglón por renglón" es mandar los escaneados; una recepción sin renglones se rechaza. Lo pendiente de un traspaso es lo enviado menos lo recibido en todas sus recepciones: lo que no se escanea sigue En tránsito (X-13), y una recepción que deja algo pendiente exige una observación (RG-14; sin ella, rojo en la evaluación y 422 al confirmar). Cada recepción deja el traspaso en Recibido con diferencias si aún queda algo pendiente, o en Recibido si ya no queda nada; un traspaso con diferencias puede recibirse otra vez, las veces que haga falta, hasta completarse. Lo ya recibido no se recibe de nuevo ni se recibe más de lo enviado (X-12, rojo), y un traspaso cancelado no se recibe (X-14). Resolver lo que nunca llega queda fuera del MVP.

#### Traspasos por lista de Excel

[FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md), **aprobada por el usuario y sin construir**. El Excel solo arma la **salida**; la recepción no cambia. Solo `movimientos` escribe vales y existencias: la importación lee el archivo, valida y llama al servicio de movimientos con tipo TRASPASO.

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| TR-01 | Un traspaso puede armarse subiendo un `.xlsx` o pegando una tabla, con la misma lectura y vista previa en tabla de la importación (FEAT-007). Es solo otra forma de capturar los renglones; lo confirma el servicio de traspaso (tipo TRASPASO) con X-01 a X-14. | — | Propuesta (FEAT-009) |
| TR-02 | Un archivo es un traspaso: un origen (el almacén que opera quien lo sube; con `almacenes.todos` lo elige) y un destino elegido en pantalla, nunca por fila. Para varios destinos, varios archivos. | — | Propuesta (FEAT-009) |
| TR-03 | Exige `traspasos.operar` (enviar, X-01) y el alcance de AC-06; no exige `inventario.entradas` ni `traspasos.recibir`. Tiene endpoints propios, para que el permiso se declare en el `router.py`. **Resuelto:** el permiso de recibir quedó separado (`traspasos.recibir`) y no interviene en el Excel, que solo arma la salida. | Rojo si no | FEAT-009; decisión del usuario |
| TR-04 | Columnas: `codigo` (de artículo o de pieza), `cantidad` (artículos por cantidad), `codigo_pieza` y `serie` (piezas; la serie puede ir vacía si la pieza tiene serie pendiente, I-02, porque el traspaso no la exige). Las demás columnas se ignoran con aviso; el nombre (`nombre`) es solo de ayuda (TR-13) y el que se muestra es el del catálogo. Una pieza es una fila con cantidad 1 (RG-05) y repetida es error; el mismo artículo por cantidad repetido se consolida (como I-06); la cantidad es entera, sin redondeo (I-13). | Rojo (pieza repetida, cantidad no entera) | Propuesta (FEAT-009) |
| TR-05 | Cada fila se evalúa con las mismas reglas que la captura manual: X-02 (rojo: no hay suficiente en el origen o la pieza no está en él), X-04 (amarillo: pieza no apta), X-09 (verde: el inactivo sí se traslada), código inexistente (error), AL-04 (almacén cerrado) y X-03. La ruta se evalúa una vez para todo el archivo: no habitual solo con `almacenes.todos`, con aviso amarillo y observación obligatoria. **(Cambia con FEAT-015, iteración 01, sin construir):** la ruta lateral (X-18) también se evalúa una vez para todo el archivo, con X-16 (observación del archivo) o X-17 (la confirmación exige `autorizacion_id`; la solicitud lleva las filas que no están en rojo). | Según la regla | Propuesta (FEAT-009) |
| TR-06 | Todo o nada (RG-09): no se confirma con una fila en rojo. La persona corrige el archivo y lo sube otra vez, o toca «Dejar fuera las filas con error», decisión explícita que queda en la observación y en la auditoría con cuántas y cuáles filas. | Rojo | Propuesta (FEAT-009) |
| TR-07 | Un archivo es un vale: máximo 500 renglones (cada pieza cuenta uno). Con más se rechaza y se pide dividir el archivo, así un traspaso sigue siendo un vale con un folio `CLAVE-TRS` y un QR. | Rojo | Propuesta (FEAT-009) |
| TR-08 | Idempotencia: el `id_lote` del cliente genera un `id_cliente` determinista del vale (repetir el lote responde 200 con `repetida: true`) y una huella `sha256` del contenido (modo, origen, destino y filas normalizadas) avisa «este archivo ya se usó»; el aviso se acepta con `confirmar_repetido`, igual que I-12. | Amarillo | Propuesta (FEAT-009) |
| TR-09 | La recepción no cambia (X-10 a X-13): el Excel solo arma la salida. Recibir sigue siendo con «Recibir todo», la casilla por renglón o el escaneo, con `traspasos.recibir` (X-01, X-10) y la mejora de interfaz para listas largas de X-15. | — | FEAT-009; decisión del usuario |
| TR-10 | (Segunda entrega.) La lista de un traspaso se puede descargar como Excel para imprimirla y usarla de lista de verificación al recibir. | — | Propuesta (FEAT-009) |
| TR-11 | **Origen guiado.** El escaneo (`GET /api/escaneo/{codigo}`) y el buscador (`GET /api/busqueda`) de Trasladar, y los de «Trasladar con una lista», reciben el `almacen_id` del origen elegido y devuelven `disponible`: lo que hay en ese almacén (en una pieza, 1 si está en él y 0 si no). Con `almacen_id`, la búsqueda por texto ofrece solo artículos con existencia y piezas que están en ese almacén; un código escaneado que no hay en el origen se identifica igual (`disponible` 0) y el servidor lo rechaza como X-02 al evaluar. Respeta AC-06: un origen fuera del alcance del usuario no muestra nada. La pantalla muestra «Disponible: N». | Rojo (X-02) | FEAT-011 |
| TR-12 | **Vista previa sola.** Al cargar el Excel de traspaso (o el de importación), la vista previa aparece sola, con esqueleto de carga y paginada de 12 en 12. El paso «Relacionar columnas» solo se muestra si las columnas obligatorias (`codigo` y `cantidad` o `codigo pieza`) no se reconocen por sus encabezados; el servidor devuelve la vista previa en `POST /archivo` cuando se reconocen. | — | FEAT-011 |
| TR-13 | **Nombre de ayuda.** La columna `nombre` se reconoce como ayuda de quien arma el archivo, sin aviso de columna ignorada. Si el nombre no coincide con el del catálogo para ese código (se comparan sin acentos ni mayúsculas, y vale que uno contenga al otro), la fila avisa en amarillo (`NOMBRE_NO_COINCIDE`) para que se revise un código mal escrito; no bloquea. La plantilla descargable incluye la columna `nombre`. | Amarillo | FEAT-011 |

### 7.7 Cierre de almacén de proyecto

Hoy, al terminar un mantenimiento, la empresa solo ve lo que quedó y no sabe quién perdió qué (plática min 33). Estas reglas responden a eso.

| ID | Regla | Origen |
|---|---|---|
| CP-01 | Un almacén de área se abre para un mantenimiento y se cierra al terminar. | Plática min 32 y 49 |
| CP-02 | Para cerrarlo, lo que queda regresa por traspaso a Contratistas, y de ahí a Kepler si corresponde. | Plática min 30 y 49 |
| CP-03 | Lo que el sistema dice que hay y no aparece físicamente se registra como faltante, con observación, a nombre del almacén. | Plática min 33 |
| CP-04 | El reporte de cierre muestra, por artículo: lo recibido, lo consumido, lo regresado, lo que sigue en resguardo de trabajadores (con nombre), lo cerrado sin devolución y los faltantes. | Plática min 33 |
| CP-05 | Lo que sigue en resguardo de trabajadores no impide el cierre: queda como pendiente de cada uno y se devuelve en Contratistas o Kepler. | Plática min 8 |

### 7.8 Inspección y estado de pieza

| ID | Regla | Origen |
|---|---|---|
| P-01 | La inspección la registra el almacenista o el supervisor antes de entregar: fecha, resultado (Apto o No apto), observaciones y vigencia. Revisa etiquetas, costuras, cintas, herrajes y conectores. **(Cambia con FEAT-016, iteración 01, sin construir):** la registra quien tiene `piezas.inspeccionar` (de inicio, almacenista y supervisor); el flujo y la pantalla se diseñan para el **almacenista** (decisión D-10). Se registran la fecha (hoy, del servidor), el resultado, cada punto revisado (Bien, Mal o No aplica), las observaciones, una foto opcional y la vigencia que resulta (P-14). | PDF p.4, p.9; decisión del usuario (8 oct 2026) |
| P-02 | Qué artículos requieren inspección se define en el catálogo (CF-06). | PDF p.2 |
| P-03 | Cualquier almacenista puede marcar una pieza como No apta al ver un daño. Solo una inspección la regresa a Apto. | Propuesta |
| P-04 | Si vence la inspección de una pieza que está con un trabajador, aparece en la lista de revisión. **(Cambia con FEAT-016, iteración 01, sin construir):** aparece en la pestaña Vencidas de Inspecciones con quién la tiene y desde cuándo (P-11, P-12); pasa de P2 a P1. | Propuesta |
| P-05 | Dar una pieza por perdida, o darla de baja definitiva, lo hace el supervisor. Es un movimiento a Baja y no se revierte. | PDF p.3 paso 9 |
| P-06 | Una pieza puede marcarse En mantenimiento o En calibración, con observación. Mientras tanto no se entrega y no cuenta como disponible. | Plática min 46–47 |
| P-07 | Un supervisor o un administrador puede ajustar la fecha hasta la que vale la inspección vigente de una pieza, con un motivo obligatorio. Requiere el permiso `piezas.ajustar_vigencia`. El ajuste no cambia el resultado ni la fecha de la inspección, y no regresa a Apta a una pieza No apta (P-03). Acortar la vigencia es libre; alargarla no puede pasar de la fecha de la inspección más la vigencia del artículo. Quien registró la inspección no puede ajustar la suya. Queda en el historial de la pieza con la fecha anterior, la nueva, el motivo y el usuario, y entra a la lista de revisión. | Idea del equipo |
| P-08 | Quien tiene `piezas.registrar_serie` (de inicio, Supervisor, Compras y Administrador) puede **poner** el número de serie a una pieza que no lo tiene. No puede cambiar una serie ya registrada. La serie no puede estar repetida en el mismo artículo (error, como en I-02). El cambio queda en el registro de cambios con el valor anterior (vacío) y el nuevo, y la pieza deja de ser serie pendiente. Solo piezas de su almacén o, con `almacenes.todos`, de cualquiera (AC-06). Completar muchas series con un Excel es de una segunda entrega. | Decisión del usuario |

#### Inspecciones y avisos de vigencia

**Iteración 01, aprobada, sin construir.** [FEAT-016](../features/FEAT-016-inspecciones-y-alertas-de-vigencia.md). La plática del 8 oct 2026 pidió definir las reglas del equipo de alturas, poder modificar la vigencia, configurar el aviso de inspección por vencer y rehacer la pantalla. El índice de todas las reglas del equipo de alturas está en FEAT-016.

| ID | Regla | Origen |
|---|---|---|
| P-09 | **Dos formas de modificar la vigencia.** (1) **Periodo**: cuántos días dura una inspección de un artículo (lo propone la categoría, CF-02; 180 por omisión); lo cambia quien tiene `catalogo.administrar` y aplica a las inspecciones nuevas, sin recalcular las ya hechas (CF-08). (2) **Fecha de una pieza**: el ajuste de P-07 con `piezas.ajustar_vigencia`. La ficha de la pieza y la pantalla Inspecciones muestran las dos. Al acortar el periodo, la pantalla dice cuántas piezas quedan con una fecha más lejana y no las cambia. | Plática 8 oct 2026; Propuesta |
| P-10 | **Aviso configurable.** Los días de aviso antes del vencimiento salen del artículo; si no tiene, de su categoría; si tampoco, del general (`INSPECCION_AVISO_DIAS`, 7). Vacío es «hereda»; entero de 1 a 90; se cambia con `catalogo.administrar` y queda en el registro de cambios (CF-15). La herencia es **en vivo** (a diferencia de la plantilla de CF-02). E-11, la pantalla Inspecciones, la tarjeta del Inicio, el contador del menú y la app de Android usan el valor resuelto. Si el aviso es igual o mayor que la vigencia, se avisa al guardar y no se bloquea. | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |
| P-11 | **Pantalla Inspecciones** (`/inspecciones`, `inspecciones.ver`, primero celular). Lista las piezas de artículos que requieren inspección, sin las de baja, en tres pestañas: **Vencidas**, **Por vencer** (dentro del aviso resuelto, hoy incluido) y **Sin inspección**. Las No aptas, en mantenimiento y en calibración se cuentan aparte y enlazan a Seguimiento. Cada pieza dice dónde está (almacén, trabajador con desde cuándo y vale, o en tránsito), su fecha y los días en palabras («Vence en 3 días»). La más urgente primero; filtros de almacén, categoría, texto y «En el almacén» o «Con trabajadores». Alcance de C-02 y AC-06. Solo lee. | Plática 8 oct 2026 |
| P-12 | **Qué se hace según dónde está la pieza.** En el almacén: **Inspeccionar**. Con un trabajador: **Pedir que la devuelva**, que muestra sus datos y el folio y un atajo a Devolver; no manda mensajes ni guarda nada. En tránsito: sin botón, «Inspecciónala cuando la reciban». Una pieza No apta en manos de un trabajador se anuncia arriba de la pantalla. La devolución nunca se bloquea (SM-05). | Propuesta |
| P-13 | **Inicio y menú.** Con `inspecciones.ver` y `tablero.ver`, el Inicio muestra la tarjeta **Inspecciones** (vencidas, por vencer y sin inspección), que abre la pestaña más urgente; la entrada del menú lleva un contador con la suma. Mismo alcance que la lista. | Plática 8 oct 2026; Propuesta |
| P-14 | **Inspeccionar una pieza (flujo rehecho).** Escanear la pieza → ficha breve con su vigencia, el periodo del artículo y sus últimas inspecciones → **cinco puntos** (etiquetas, costuras, cintas, herrajes y conectores), cada uno Bien, Mal o No aplica, todos contestados → resultado (un Mal propone No apto; decide la persona) → observación obligatoria si es No apto o si es Apto con algún Mal → foto opcional → la fecha que quedará, calculada por el servidor → Guardar. La fecha de la inspección es la de hoy del servidor (RG-11). | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |
| P-15 | **Avisos fuera de la pantalla.** No hay tarea programada en el servidor ni push por vencimiento. En la PWA el aviso se ve en pantalla (P-11 a P-13, E-11). En la app de Android, una **notificación local** al día con las piezas de su almacén que entran en aviso o vencen, calculada del paquete descargado, a la hora de descarga del almacén (OF-29). | Decisión del usuario (8 oct 2026) |
| P-16 | **Inspección por lote.** El modo **Varias piezas** deja escanear piezas seguidas (una repetida se ignora, como E-15). **Todas Apto** pide confirmar que se revisaron los cinco puntos; las que tienen algo mal se abren una por una con P-14. Cada pieza es su propia inspección, en su propia transacción: una que no se puede (P-17) sale rechazada y no detiene a las demás. Máximo 50 piezas por lote; cada pieza lleva su `id_cliente`, así que reintentar no duplica. | Propuesta |
| P-17 | **Cuándo no se registra una inspección.** Pieza en tránsito: 409 `PIEZA_EN_TRANSITO`. En mantenimiento o calibración: 409 `PIEZA_EN_MANTENIMIENTO` (primero se regresa al servicio). En baja: 409. Fuera del alcance: 404 (AC-06). Código que no es de una pieza: 422. Fecha de inspección posterior a hoy: 422 `FECHA_FUTURA` (solo la inspección inicial de I-03 recibe fecha). La ficha trae `inspeccion_posible` con el motivo, para decirlo al escanear. | Propuesta; RG-11 |

Con varios almacenes en su conjunto, la lista de inspecciones abarca todo el conjunto (AC-37), pero inspeccionar es una escritura en el almacén activo (AC-38): la pantalla ofrece cambiar de almacén (T-6 del maestro).

### 7.9 Baja y vale de no adeudo

El trabajador devuelve en la planta la herramienta y el equipo de alturas, y en Kepler su equipo personal. Kepler le da el vale de no adeudo y con él RH lo finiquita (plática min 4 y 8).

| ID | Regla | Origen |
|---|---|---|
| B-01 | La baja la inicia RH, o el almacenista cuando el trabajador se presenta a pedir su vale de no adeudo. El trabajador pasa a Baja en proceso y ya no recibe entregas. | PDF función 7; plática min 4 |
| B-02 | Al iniciar se muestran sus pendientes de todos los almacenes: retornables en resguardo, con código, fecha de entrega, folio del vale y almacén. | PDF función 7; plática min 8 |
| B-03 | Los consumibles no cuentan como pendientes. | PDF p.2; plática min 30 |
| B-04 | Con los pendientes en cero, el almacén emite el vale de no adeudo, con folio. | Plática min 4 y 8 |
| B-05 | Lo no devuelto sigue como pendiente del trabajador y reaparece si se le recontrata. | Plática min 9 |
| B-07 | RH puede cancelar una baja en proceso; el trabajador vuelve a Activo. | Propuesta |
| B-08 | Al emitirse el vale de no adeudo, el trabajador queda Inactivo hasta que RH lo reingrese (T-02). | Plática min 19 |
| B-09 | RH no finiquita sin vale de no adeudo: en su consulta ve "Con pendientes" o "No adeudo emitido". | Plática min 4 |

### 7.10 Cancelación de un vale

| ID | Regla | Origen |
|---|---|---|
| K-01 | Cancela quien hizo el vale, o un supervisor, con motivo. Entra a la lista de revisión. | Propuesta |
| K-02 | La cancelación genera los movimientos inversos, en un vale de cancelación con su propio folio. El vale original queda visible y marcado como cancelado. | Propuesta |
| K-03 | No se cancela un vale si lo que movió ya se movió después (por ejemplo, la pieza ya se devolvió) o si las existencias ya no alcanzan para revertirlo. | Propuesta |
| K-04 | Se cancelan entradas, entregas, devoluciones y traspasos en tránsito (X-14). Una recepción y un vale de no adeudo no se cancelan. | Propuesta |
| K-05 | **Cancelar y rehacer.** Al cancelar un vale, quien lo hizo puede abrir un borrador nuevo con los mismos renglones, para quitar o corregir el que falló sin escanear todo otra vez. No es una cancelación parcial: el vale original se cancela completo. El borrador no hereda la firma ni la autorización (A-03), y sus renglones se evalúan de nuevo. | Idea del equipo |

### 7.11 Consulta y reportes

| ID | Regla | Origen |
|---|---|---|
| C-01 | Credencial o número: muestra al trabajador, su vigencia y lo que tiene en resguardo. | PDF función 5; plática min 10 |
| C-02 | Pieza: muestra estado, inspección, quién la tiene e historial. Sin `almacenes.todos`, solo se ve una pieza que está en el almacén del usuario, que tiene un trabajador (su resguardo) o que va en tránsito desde o hacia su almacén; cualquier otra llega como desconocida al escanear y responde 404 en su ficha, igual que una que no existe. En el historial, de otros almacenes solo se ve lo que pasó con un trabajador, sin nombrar el almacén ni el vale (AC-06). | PDF p.9 paso 7 |
| C-03 | Artículo: muestra existencias por almacén, separando disponibles de no disponibles, y qué trabajadores lo tienen. Sin `almacenes.todos`, las existencias son solo las del almacén del usuario (el escaneo trae `existencia_total` de su almacén); lo que tienen los trabajadores se ve completo, porque el trabajador no es un almacén (AC-06). | PDF función 5; plática min 0 y 38 |
| C-04 | Vale: muestra su detalle y si está íntegro. **(Cambia con FEAT-017, iteración 01, sin construir):** el detalle es primero computadora, con resumen por categoría, renglones paginados, vales relacionados y descarga en PDF (BT-05 a BT-08). | PDF p.8 paso 6 |
| C-05 | Reportes de existencias, movimientos y adeudos, con filtros por almacén, fecha y trabajador. El de movimientos filtra además por artículo, tipo y usuario. El de adeudos es una consulta de personas: lo ven completo quien tiene `almacenes.todos` o `trabajadores.administrar` (RH); el resto, solo lo entregado por su almacén, y sin almacén nada. **(Cambia con FEAT-013 y FEAT-018, iteración 01, sin construir):** los reportes filtran también por proyecto; la pantalla de adeudos se retira y redirige a la sección **Deudores** (DU-01 a DU-09), con el mismo alcance de personas; el endpoint `GET /api/reportes/adeudos` se conserva para el CSV. «Su almacén» pasa a «los almacenes de su conjunto» (AC-37). | PDF función 8; idea del equipo |
| C-06 | Búsqueda por texto: nombre de artículo, número de serie, nombre o número de trabajador. La búsqueda por serie no encuentra piezas con serie pendiente (I-02): se encuentran por su código. Los artículos son catálogo y se ven siempre; las piezas se limitan igual que en C-02 (AC-06). **(Cambia con FEAT-019, iteración 01, sin construir):** busca mientras se escribe (UX-01) y encuentra trabajadores por palabras del nombre en cualquier orden, por número de empleado y por el inicio del código de credencial; artículos por nombre, marca y código; piezas por código, serie y nombre del artículo (UX-03). Cada resultado dice dónde está o cuánto hay (UX-04). | Plática min 38; decisión del usuario (8 oct 2026) |
| C-07 | EPP entregado a un trabajador, con fechas y vales. Sirve como prueba ante la Comisión Mixta de Seguridad. | Plática min 31 |
| C-08 | Reporte de consumo: por artículo consumible y periodo, el total consumido, con el desglose por trabajador, de mayor a menor. Suma las entregas de consumibles (E-21) y resta las cancelaciones (K-02). Filtros: periodo, almacén, categoría, artículo y trabajador. Se descarga en CSV y no muestra costos (RG-12). Requiere `reportes.consumo`. **(Cambia con FEAT-013 y FEAT-018, iteración 01, sin construir):** agrega el filtro de **proyecto** (`proyecto_id`), y el consumo cuenta para el proyecto de la entrega, no para el almacén que entregó (PR-14). | Plática min 35–36 |
| C-09 | Valor del inventario por almacén. Solo Compras. **(Cambia con FEAT-013, iteración 01, sin construir):** además de Compras, el **Supervisor** ve el valor del inventario de sus almacenes y el uso por proyecto, en pesos y en unidades, **solo totales** y su reparto por categoría y almacén, nunca el costo unitario (TB-04, TB-05; decisión D-05). Un total en pesos que cubre un solo artículo se muestra como «—» a quien no tiene `catalogo.costos`, porque dividirlo revelaría el costo (T-2 del maestro). Ya construido en el código como FEAT-012 (`GET /api/tablero/valor`, reglas VI-01 a VI-07 en sus comentarios), sin documento todavía. | Plática min 39; decisión del usuario (8 oct 2026) |
| C-10 | Lista de revisión: excepciones con su observación, para el supervisor. | Propuesta |
| C-11 | Rastrear una desaparición: el reporte de movimientos se filtra por usuario, artículo, almacén y periodo para ver quién tocó el equipo y cuándo, y el historial de la pieza (C-02) completa el rastro. Quien tiene `reportes.movimientos` ve el filtro de usuario siempre dentro de su alcance (AC-06): el almacenista, su almacén; quien tiene `almacenes.todos`, todos los almacenes y usuarios. Es informativo y no forma parte de la operación habitual. | Idea del equipo |
| C-12 | **Mis movimientos de hoy.** Cada usuario ve la lista de los vales que hizo en el día, con acceso a su detalle y a cancelarlos o rehacerlos (K-01, K-05). Es una consulta de apoyo y no forma parte de la operación habitual. | Idea del equipo |
| C-13 | **Seguimiento de piezas.** Para ver dónde está cada pieza, no solo cuántas hay: lista las piezas de un artículo (o de lo que se busque por artículo, serie, código o trabajador) y a cada una le pone dónde está o quién la tiene ("En resguardo de Juan Pérez", "En Kepler", "En tránsito a Contratistas"), su estado e inspección, desde cuándo está ahí y con qué vale. "Desde" es el movimiento que la dejó en su ubicación actual; con un trabajador, su entrega más reciente (una cancelación que se la regresa no cambia desde cuándo la tiene). Trae un resumen de conteos (total, en almacén, en resguardo, en tránsito y no aptas) y se descarga en CSV. Requiere `reportes.existencias` (de inicio, Administrador, Supervisor y Compras) y respeta el alcance de C-02 (AC-06): con `almacenes.todos`, todas; sin él, las de su almacén, las que tienen trabajadores (con `trabajadores.ver`) y el tránsito desde o hacia su almacén. El folio de un vale de otro almacén no se muestra. Solo lee: no mueve nada, y nunca muestra costos, CURP ni NSS (RG-12, RG-13). **Serie pendiente:** una pieza sin número de serie sale con la etiqueta «Serie pendiente»; el seguimiento tiene un filtro «Con serie pendiente» y el resumen cuenta cuántas hay, y el tablero de inicio (`tablero.ver`) trae una tarjeta «Piezas con serie pendiente» dentro del mismo alcance (AC-06). Es solo lectura. **Dos pestañas (SG-01):** Piezas y Por cantidad (lo que tienen los trabajadores de artículos sin serie). Se ve con `reportes.existencias` o `resguardo.ver` (SG-04). | Idea del equipo; decisión del usuario |
| SG-01 | **Seguimiento por cantidad.** Seguimiento (C-13) tiene dos pestañas: **Piezas** (como hasta ahora, con serie) y **Por cantidad**, que lista los artículos de control por cantidad que están en resguardo de un trabajador (existencia en su ubicación con cantidad mayor a cero): trabajador, artículo, cantidad, desde cuándo y folio del vale de su entrega más reciente (una cancelación que se lo regresa no cambia la fecha). Trae un resumen (unidades, artículos y trabajadores) y se descarga en CSV. La pestaña Piezas avisa cuántos artículos por cantidad hay, para que una lista de piezas vacía no parezca rota. Filtros: `q` (artículo o trabajador), `articulo_id` y `almacen_id` (el almacén que entregó). Alcance (AC-06): con `almacenes.todos`, todo; sin él, solo lo entregado con un vale de su almacén y solo con `trabajadores.ver`; el folio de un vale de otro almacén no se muestra. Solo lee: nunca costos, CURP ni NSS. | FEAT-011 |
| SG-02 | **Quién lo tiene (ficha del artículo).** `en_posesion` de `GET /api/articulos/{id}` trae por trabajador la cantidad, `desde` (su entrega más reciente), `folio` y `vale_id` (nulos si el vale es de otro almacén, AC-06) y, en artículos por pieza, `piezas` con el código y la serie de cada una. La pantalla lo muestra como tabla con el botón «Ver detalle». El endpoint conserva `catalogo.ver`. | FEAT-011 |
| SG-03 | **Línea de tiempo de la pieza.** Cada movimiento del historial de `GET /api/piezas/{id}` trae `responsable` (quién hizo el vale), `trabajador` y `trabajador_id` (a quién se la dieron o quién la devolvió), el vale, `condicion` y `almacen` (el del vale). Con AC-06, un vale de otro almacén no nombra almacén ni vale. | FEAT-011 |
| SG-04 | **Quién tiene qué con `resguardo.ver`.** Los dos endpoints de seguimiento (`/api/seguimiento/piezas` y `/api/seguimiento/cantidad`) aceptan `reportes.existencias` **o** `resguardo.ver` (se declara en el router). El tablero trae `alto_valor_fuera`: piezas de las categorías «Equipo de alto valor» y «Equipo de alturas» en manos de un trabajador, dentro del alcance de AC-06; solo llega a quien tiene `resguardo.ver` (para los demás es `null` y la tarjeta no se muestra). La tarjeta abre `/seguimiento?alto_valor=true&ubicacion=TRABAJADOR`. **(Cambia con FEAT-018, iteración 01, sin construir):** el alto valor ya no se decide por el nombre de la categoría: cuenta lo que es de alto valor según AV-02 (marca de la categoría o costo igual o mayor que el tope) **más** lo que requiere inspección (`articulo.requiere_inspeccion`), en piezas y en unidades (AV-04). El filtro `alto_valor` de Seguimiento usa el mismo criterio. | FEAT-011; decisión del usuario (8 oct 2026) |
| SG-06 | **Aviso de alto valor con baja o contrato vencido.** Una pieza de alto valor o de alturas (SG-04) que está en resguardo de un trabajador dado de baja (`INACTIVO` o `BAJA_EN_PROCESO`) o con el contrato terminado trae `aviso` en la lista de seguimiento y en su ficha. Quien aún no empieza su contrato o no tiene periodos no genera aviso. Es solo informativo: no bloquea nada. **(Cambia con FEAT-018, iteración 01, sin construir):** «de alto valor o de alturas» sigue el criterio nuevo de SG-04 (AV-02 más `requiere_inspeccion`), sin leer el nombre de la categoría; en Deudores el aviso se extiende a toda la deuda del trabajador (DU-04). | FEAT-011 |
| SG-07 | **Alto valor y alturas son por pieza.** Las categorías iniciales «Equipo de alto valor» (herramienta) y «Equipo de alturas» (EPP) son de control PIEZA y retornables (`categorias_iniciales.py`); el resto de EPP y de herramienta manual es por cantidad, salvo la herramienta eléctrica, que también es por pieza. Se confirma sin cambiar categorías. | FEAT-011 |
| SG-05 | **Bitácora del almacén.** `GET /api/reportes/movimientos` es la bitácora de un almacén: filtrando por `almacen_id` incluye lo que **sale** (el vale lo emitió ese almacén o el movimiento sale de sus ubicaciones), lo que **llega** (el vale va hacia él, como un traspaso en camino, o el movimiento llega a sus ubicaciones, como una recepción) y las **entradas**, con quién, qué y cuándo. Cada fila dice si fue `ENTRADA`, `SALIDA` o `EN_CAMINO` respecto al almacén que se ve, y trae `vale_id` y `trabajador_id` para enlazar. Se filtra además por pieza o serie (texto) y por «Solo los míos» (lo que hizo el usuario de la sesión; reemplaza a «Mis movimientos de hoy», que sigue existiendo). Se ve con `bitacora.ver` **o** `reportes.movimientos` (cualquiera de los dos, que el servicio verifica), con el alcance de AC-06: sin `almacenes.todos`, solo el almacén asignado. **Nota (FEAT-017, iteración 01, sin construir):** la bitácora pasa a mostrar un renglón por vale (BT-01); este reporte por movimiento se conserva sin cambios como la pestaña «Detalle por renglón» y para su CSV (BT-04). | — | FEAT-011 |

### 7.12 Índice de casos especiales

Dónde está resuelto cada caso que se sale de lo habitual.

| Caso | Qué pasa | Reglas | Prioridad |
|---|---|---|---|
| Equipo de alturas | Va por pieza, con inspección; no apto o sin inspección vigente no se entrega y nadie lo autoriza. Con la iteración 01: pantalla Inspecciones, aviso configurable e inspección por lote. | E-05, E-06, E-11, SM-04, P-01 a P-04; P-09 a P-17 (iteración 01) | P0 |
| Herramienta sin etiqueta | Se escanea el QR de su estante o se busca por nombre. | I-07, E-18 | P0 |
| Etiqueta de una pieza ilegible | Se busca por número de serie o se elige de la lista del trabajador. | E-18, V-14 | P0 |
| Equipo de alto valor | Va por pieza, con número de serie cuando se conoce; se sabe quién lo tiene. Con la iteración 01: alto valor por marca de la categoría o por costo, y quién lo debe en Deudores. | I-02, C-02, C-03; AV-01 a AV-05, DU-01 a DU-09 (iteración 01) | P0 |
| Pieza que llega sin número de serie | Entra con serie pendiente; se entrega con aviso, se traspasa y devuelve sin cambio, no se encuentra por serie, y quien tiene `piezas.registrar_serie` la completa. | I-02, I-17, E-29, P-08, C-13 | P1 |
| Pieza sin código en el archivo de importación | El sistema le genera `CÓDIGO-DEL-ARTÍCULO-NNN` al confirmar; hay que imprimir su etiqueta. | I-15, RG-10 | P1 |
| De noche no hay supervisor para recibir un traspaso en un almacén de tercer nivel | Quien tenga `traspasos.recibir` recibe el traspaso; el almacenista lo trae de inicio (X-01, AC-31). | X-01, X-10, X-15 | P1 |
| Herramienta de uso especial | La empresa le activa un requisito y su motivo. | CF-06 a CF-08, E-26 | P0 |
| Artículo que ya no se usa | Se inactiva: no se entrega, pero se puede devolver y trasladar. | CF-10 a CF-13, E-19 | P0 |
| Consumibles | No regresan ni generan pendiente; se limitan por periodo y queda su historial y su reporte de consumo. | E-21, L-03, B-03, C-08 | P0 |
| Devuelven una pieza distinta | Se abona a su titular; la del que la trajo sigue pendiente. | V-01 | P0 |
| Devuelven equipo de otra compañía | No se recibe y el pendiente sigue abierto. | V-12 | P0 |
| Lo trae otra persona | La devolución se abona al titular. | V-01 | P0 |
| Lo devuelven en otro almacén | Se recibe con aviso y entra a ese almacén. | V-07 | P0 |
| Regresa dañado | Se anota con observación; no hay cargo al trabajador. | V-05, V-06 | P0 |
| Contrato vencido | No se le entrega nada; sí puede devolver. | E-02, T-07, SM-05 | P0 |
| Trabajador que regresa | RH lo reingresa; conserva historial y pendientes. | T-02, E-12, B-05 | P0 |
| Excede el límite | Se bloquea hasta que el supervisor autoriza, con motivo. | L-01 a L-05, A-01 a A-07 | P0 |
| Supervisor ausente | Autoriza desde su celular; si no responde, se quita el renglón. Con la iteración 01 le llega un aviso push y el despacho de EPP sin respuesta se reenvía, se aprueba con PIN en el mostrador o se quita el EPP. | A-01, A-07; DE-09, DE-10, NT-02 (iteración 01) | P0 |
| Traspaso incompleto | Lo no recibido sigue En tránsito. | X-13 | P0 |
| Dos personas operan lo mismo | Gana la primera; la otra ve qué cambió. | RG-08, RG-09 | P0 |
| Se captura algo por error | Antes de confirmar se quita el renglón; después, se cancela el vale, o se cancela y se rehace con los mismos renglones. | K-01 a K-05, X-14 | P0 |
| Una inspección necesita otra fecha de vigencia | Un supervisor o un administrador la ajusta, con motivo; queda en el historial. El periodo del artículo se cambia aparte, para las inspecciones nuevas. | P-07; P-09 (iteración 01) | P0 |
| Escaneo accidental | Es un borrador: se quita el renglón o se deshace en unos segundos. No cambia las existencias hasta confirmar. | E-28 | P0 |
| Cantidad inusualmente alta | El servidor lo marca y se pide confirmar la cantidad antes de continuar. | E-27 | P0 |
| Desaparece un equipo | El reporte de movimientos se filtra por usuario, artículo, almacén y periodo; el historial de la pieza lo completa. | C-02, C-11 | P0 |
| Un rol necesita ver o hacer algo más | El administrador le activa el permiso; aplica en la siguiente consulta. | AC-08 a AC-11 | P1 |
| Hay que mover a un almacenista de almacén | Un supervisor con `almacenes.asignar_personal` lo reasigna; aplica en la siguiente petición y el historial no cambia. | AC-12, AC-13 | P1 |
| En mantenimiento o calibración | No se entrega ni cuenta como disponible. | P-06, E-05 | P1 |
| Llega material de un artículo que ya está en el catálogo | Se importa en modo reposición: solo suma, nunca crea; un código que no existe es error. | I-10, I-11, I-13 | P1 |
| Falta una herramienta que el almacén no tiene (por ejemplo, de medidas europeas) | El supervisor o el almacenista levanta una solicitud de compra urgente; Compras la toma, la compra y la ingresa con un vale de entrada. | I-08, SC-01 a SC-11 | P1 |
| Falta material en un almacén de tercer nivel y Contratistas no lo tiene | Un traspaso por una ruta que no es padre-hijo (por ejemplo, Kepler a un almacén de tercer nivel) solo lo hace el Administrador, con aviso y observación; el resto usa la cadena Kepler, Contratistas, almacén de tercer nivel, o una compra urgente. Con la iteración 01, si otro almacén de tercer nivel lo tiene de sobra, se traslada lateralmente (siguiente fila). | X-03, SC-01 | P1 |
| Termina un mantenimiento y el almacén de proyecto deja de operar | El Administrador lo inactiva con existencias en cero, sin traspasos en tránsito, sin almacenes dependientes y sin usuarios (con la iteración 01, también sin proyectos activos); vuelve a operar reactivándolo. | AL-03, CP-01 a CP-05; PR-12 (iteración 01) | P1 |
| Abre un almacén de tercer nivel nuevo | El Administrador da de alta el almacén y su personal; recibe su surtido por traspaso desde Contratistas. Con la iteración 01, aparece en «Almacenes sin proyectos» hasta que se le dé un proyecto. | AL-01, AL-02, X-03; PR-12 (iteración 01) | P1 |
| Hay que dar de alta a un trabajador que ya tiene número de empleado en el centro | Solo quien tiene `trabajadores.numero_externo` lo captura; queda marcado como externo. | T-10 | P1 |
| Quedó instalado en planta | Se cierra sin devolución y sin pendiente. | V-09 | P2 |
| Pérdida o robo | Sigue como pendiente hasta que un supervisor lo dé por perdido. | V-13, P-05 | P2 |
| **Iteración 01 (aprobada, sin construir)** | | | |
| Empieza un proyecto o contrato | El Administrador da de alta el proyecto con su almacén y sus fechas **antes** que sus trabajadores; RH asigna a cada trabajador desde su alta. | PR-01, PR-02, PR-11 | P1 |
| Trabajador en dos proyectos | La entrega pide elegir el proyecto, con el principal ya elegido. | PR-09, PR-13 | P1 |
| Trabajador vigente sin proyecto activo (su proyecto cerró) | La entrega sale con aviso amarillo y observación, y cuenta como «Sin proyecto». | PR-10 | P1 |
| Contratistas entrega EPP a un trabajador del proyecto de Midrex | El vale es de Contratistas; el consumo cuenta para el proyecto de Midrex y lo ve su supervisor. La deuda es con Contratistas. | PR-14, TB-06, DU-02 | P1 |
| Proyecto que pasa su fin estimado sin cerrarse | Sigue operando y aparece como «Fin estimado vencido» para que el Administrador lo extienda o lo cierre; no se ofrece para asignar. | PR-06, TB-08 | P1 |
| Almacén de tercer nivel sin proyectos activos | Aviso «Sin proyectos activos: considera inactivarlo»; el sistema nunca lo inactiva solo. | PR-12, AL-03 | P1 |
| Supervisor con dos almacenes | Ve los dos en el Inicio, reportes y autorizaciones; opera en su almacén activo y lo cambia con el selector. | AC-36 a AC-41 | P1 |
| Supervisor ve el valor de su inventario | Solo totales en pesos y unidades, por categoría, almacén y proyecto; nunca el costo unitario. | TB-04, TB-05, C-09 | P1 |
| Entrega de EPP | Pide la aprobación del supervisor del almacén antes de la firma, salvo autonomía del almacén o del almacenista. | DE-01 a DE-03, DE-14, F-04 | P1 |
| Despacho de EPP sin respuesta del supervisor | A los 5 minutos la pantalla lo dice; vence a los 15. Se reenvía, el supervisor da su PIN en el mostrador o se quita el EPP y se entrega lo demás. | DE-09, DE-10, A-07 | P1 |
| Los dos supervisores (día y noche) reciben la misma solicitud | Resuelve el primero; al otro se le cierra el aviso y ve quién la resolvió. | DE-11, NT-06 | P1 |
| El supervisor despacha él mismo | Su captura aprueba el despacho; un excedente sigue necesitando a otro supervisor. | DE-07, A-05 | P1 |
| Arranque de un mantenimiento: muchos trabajadores piden su dotación a la vez | El almacenista atiende a otro mientras espera; el supervisor recibe un aviso agrupado y aprueba varias de un jalón. | DE-12, DE-15, NT-05 | P1 |
| El supervisor rechaza parte del EPP | Se quita lo rechazado y el trabajador firma solo lo que recibe. | DE-03, DE-06, DE-08 | P1 |
| Sobra material en un almacén de tercer nivel y falta en otro | Traslado lateral: lo autoriza el supervisor del origen con su envío o con una autorización; el destino lo recibe como cualquier traspaso. | X-16 a X-20 | P1 |
| La misma persona envía y recibe un traspaso | Se permite con aviso, observación y revisión. | X-21 | P1 |
| Inspección por vencer | Aviso configurable por artículo, categoría o general; la pantalla Inspecciones lo lista y en Android hay notificación local. | P-10 a P-13, P-15, E-11 | P1 |
| Pieza con la inspección vencida en manos de un trabajador | Aparece en Vencidas con «Pedir que la devuelva»; la devolución nunca se bloquea. | P-04, P-12, SM-05 | P1 |
| Muchas piezas que inspeccionar | Inspección por lote; cada pieza en su propia transacción. | P-16, P-17 | P1 |
| Una importación grande se parte en varios vales | La bitácora la muestra como un lote; se abre y se descarga en un solo PDF. | BT-02, BT-08, BT-10 | P1 |
| Quién le debe a mi almacén | Sección Deudores por trabajador, con alto valor y no vigentes primero. | DU-01 a DU-07 | P1 |
| Herramienta eléctrica cara | Cuenta como alto valor por su costo, y solo como alto valor. | AV-02, AV-03 | P1 |
| Se pierde la señal en el mostrador | En la app de Android, lo que no pide aprobación sigue por la cola; el EPP de un almacén sin autonomía y los naranjas esperan a que vuelva la señal. | OF-08 a OF-12 | P1 |
| Se confirmó un vale y no llegó la respuesta | El mismo vale pasa a la cola con «Folio pendiente»; la idempotencia decide al sincronizar. | OF-11, OF-23 | P1 |
| Dos equipos sin conexión registran la misma pieza | El primero que sincroniza se guarda; el segundo va a conflictos para el supervisor. | OF-20, OF-22, OF-25 | P1 |
| Al sincronizar, una regla ya no se cumple (límite, vigencia, inspección) | Se guarda con avisos y va a revisión; nadie autoriza después del hecho. | OF-17, OF-21 | P1 |
| Cambio de turno en el mismo equipo sin señal | Cada almacenista entra con su PIN local; cada vale queda a su nombre. | OF-06, OF-07, OF-24 | P1 |
| Equipo perdido o robado | El supervisor lo revoca; se borra su base local y sus lotes van a conflictos. | OF-04, OF-05, OF-24 | P1 |

### 7.13 Solicitud de compra urgente

Cuando falta un equipo o una herramienta para un trabajo y el almacén no la tiene, el supervisor o el almacenista levanta una **solicitud de compra urgente**; Compras la recibe, la compra y la ingresa al almacén con un vale de entrada, y desde ahí ya está disponible. La plática del patrocinador lo dice así: «El supervisor hace una solicitud de compra de manera urgente, la recibe Compras, la compra, la ingresa al almacén y ya está disponible» (min 45); el ejemplo fue una herramienta de medidas europeas para el laminador nuevo, que la planta no tiene. Una solicitud **no es inventario**: no mueve existencias ni escribe vales; la entrada la sigue haciendo `movimientos` (I-01) y la solicitud solo se liga con su vale. El permiso de pedir es `compras.solicitar` y el de atender, `compras.atender` (sección 8.2).

Estados: PENDIENTE, EN_COMPRA, COMPRADA, INGRESADA, RECHAZADA y CANCELADA. Las transiciones que existen: PENDIENTE a EN_COMPRA, RECHAZADA o CANCELADA; EN_COMPRA a COMPRADA o RECHAZADA; COMPRADA a INGRESADA. INGRESADA, RECHAZADA y CANCELADA son finales.

| ID | Regla | Origen |
|---|---|---|
| SC-01 | Quien tiene `compras.solicitar` (de inicio, Almacenista, Supervisor y Administrador) levanta una solicitud. Nace PENDIENTE en el almacén del solicitante en ese momento (RG-07, AC-06); con `almacenes.todos` se indica el almacén. Sin almacén asignado y sin `almacenes.todos`, no puede pedir. Compras (`compras.atender`) no pide: atiende. | Plática min 45; decisión del usuario |
| SC-02 | Qué se pide: un artículo del catálogo o, si el equipo no está en el catálogo, una descripción en texto libre (obligatoria sin artículo). Con artículo se toma su nombre y el texto libre se ignora; un artículo inactivo no se pide (CF-10, I-09). La cantidad es un entero de 1 en adelante; el motivo (para qué trabajo o área) es obligatorio; la urgencia es URGENTE o NORMAL, y por omisión URGENTE. | Plática min 45 (el pedido es urgente) |
| SC-03 | Quién ve qué. Quien tiene `compras.atender` ve las solicitudes de **todos** los almacenes sin ver su inventario: es la excepción a AC-06, porque una solicitud no es inventario. Quien solo tiene `compras.solicitar` ve las de su almacén, incluidas las de sus compañeros (para saber si ya se pidió), y nada si no tiene almacén. `almacenes.todos` ve todas. Una solicitud fuera de su alcance responde 404. La lista pone primero lo pendiente, luego lo que está en compra, luego lo comprado y al final lo cerrado; en cada grupo, las urgentes primero y las más antiguas primero (lo cerrado, la más reciente primero). | Plática min 45; AC-06 |
| SC-04 | Solo Compras (`compras.atender`) hace avanzar una solicitud: **tomar** la pendiente (EN_COMPRA), **rechazarla** (RECHAZADA) desde PENDIENTE o EN_COMPRA, marcarla **comprada** (COMPRADA) e **ingresarla** (INGRESADA). Cualquier otra transición se rechaza (409 `TRANSICION_INVALIDA`, con el estado actual y los permitidos). El servidor dice qué acciones puede hacer cada usuario con cada solicitud. | Plática min 45: «la recibe Compras, la compra, la ingresa» |
| SC-05 | Rechazar exige una nota que diga por qué (422). Quien pidió la lee en su solicitud. En las demás transiciones la nota es opcional; la última nota de Compras queda a la vista. | Propuesta |
| SC-06 | Al ingresar, Compras puede ligar el vale de ENTRADA con el que la metió al almacén (`vale_entrada_id`, opcional). Debe ser un vale de ENTRADA que exista, no esté cancelado, sea del **almacén central (Kepler)** (EK-05; el almacén que pidió la compra la recibe después por traspaso) y esté dentro del alcance de quien lo liga; si no, 422. Solo se indica al pasar a INGRESADA, y la base no deja ligar un vale a una solicitud que no esté ingresada. El mismo vale puede cubrir varias solicitudes. | Plática min 45: «la ingresa al almacén»; I-01 |
| SC-07 | Se cancela solo mientras está PENDIENTE (después, Compras ya la tomó: se rechaza, no se cancela; 409 `NO_CANCELABLE`) y solo por quien la pidió, por un supervisor de su almacén (quien tiene `vales.cancelar_todos` en ese almacén) o por quien tiene `almacenes.todos`, siempre con `compras.solicitar`. La nota es opcional. | Propuesta |
| SC-08 | Cada cambio de estado agrega un evento (estado anterior y nuevo, quién, cuándo y su nota), también el primero (nace PENDIENTE). Las solicitudes y sus eventos no se editan ni se borran: no hay endpoint que lo haga y un error se corrige con otra solicitud. El evento y el cambio van en la misma transacción. | AC-07, ADR-001 |
| SC-09 | El folio es `CLAVE-SOL-CONSECUTIVO` (por ejemplo `MID-SOL-000001`), por almacén del solicitante, sin huecos, de un contador propio (`serie_solicitud_compra`) que se bloquea al asignarlo; nunca sale del `id`. Se usa un contador aparte de `serie_folio` porque este lleva un CHECK con los tipos de vale y es de `movimientos`. | RG-06, ADR-006 |
| SC-10 | La solicitud lleva un `id_cliente` que genera el dispositivo, para que un doble toque no duplique: repetir la petición con el mismo cuerpo devuelve la misma solicitud (200); con otro cuerpo, o desde otro usuario, 409 `ID_CLIENTE_EN_USO`. | RG-09 |
| SC-11 | El módulo de solicitudes **no escribe inventario**: ni vales, ni movimientos, ni existencias (solo `movimientos` lo hace). Ingresar una solicitud no sube existencias: lo hace el vale de entrada que Compras registra aparte (I-01); la solicitud solo lo lee para ligarlo. | Reglas generales |

### 7.14 Administración de almacenes y tablero

Parte de [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md). Hasta ahora los almacenes solo existían en el script de datos de prueba; estas reglas dicen cómo se dan de alta, se inactivan y se reactivan, y qué muestra el tablero de inicio. Contratos en [api-contracts.md](../architecture/api-contracts.md#almacenes-y-existencias) y [api-contracts.md](../architecture/api-contracts.md#tablero).

| ID | Regla | Origen |
|---|---|---|
| AL-01 | Solo quien tiene `almacenes.administrar` (de inicio, el Administrador; el Supervisor no) crea, edita, inactiva y reactiva almacenes. Cada acción queda en el registro de cambios (`almacen.crear`, `almacen.editar`, `almacen.inactivar`, `almacen.reactivar`) con el antes y el después. | Decisión del usuario |
| AL-02 | Hay **un solo almacén central** (`CENTRAL`). Los demás (`SUBALMACEN` o `PROYECTO`) dependen de otro almacén activo, sin ciclos: no pueden depender de sí mismos ni de uno de sus descendientes. La clave y el nombre son únicos. El alta crea el almacén y su ubicación en una sola transacción. | Propuesta; decisión del usuario |
| AL-03 | Un almacén se inactiva (`CERRADO`, con `cerrado_en`) solo si: todas sus existencias están en cero, no hay traspasos en tránsito desde ni hacia él, no tiene almacenes dependientes activos y **no tiene usuarios asignados** (hay que reasignarlos primero). Lo que tienen los trabajadores no impide inactivar (CP-05). Reactivarlo devuelve el mismo almacén, con su clave y su historial, y limpia `cerrado_en`; no se crea uno nuevo. No se borran almacenes. **(Cambia con FEAT-013, iteración 01, sin construir):** bloqueo nuevo `CON_PROYECTOS_ACTIVOS` (tiene proyectos `ACTIVO`; se cierran primero), y `CON_USUARIOS` cuenta a los usuarios activos que lo tienen **en su conjunto**, no solo como almacén activo. Orden de los bloqueos: `CON_TRASPASOS_EN_TRANSITO`, `CON_EXISTENCIAS`, `CON_HIJOS_ACTIVOS`, `CON_PROYECTOS_ACTIVOS`, `CON_USUARIOS`. | Decisión del usuario; CP-05 |
| AL-04 | Un almacén `CERRADO` no recibe ni envía movimientos ni solicitudes nuevas: entregas, devoluciones, entradas, traspasos (origen o destino) y solicitudes de compra se rechazan con «Ese almacén está cerrado.» (`ALMACEN_CERRADO`). Su historial y sus reportes siguen visibles. | Decisión del usuario |
| AL-05 | La clave de un almacén que ya tiene folios (de vales o de solicitudes) no se cambia, porque forma parte de ellos (`KEP-ENT-000123`). Sin folios se puede corregir. | Propuesta |
| TB-01 | El tablero respeta AC-06: con `almacenes.todos` ve todos los almacenes y puede filtrar por uno; sin él, solo el almacén asignado (el parámetro `almacen_id` se ignora). Sin almacén asignado y sin `almacenes.todos`, el tablero llega vacío. Elegir un almacén en el tablero no cambia el almacén en el que se opera. **(Cambia con FEAT-013, iteración 01, sin construir):** «solo el almacén asignado» pasa a «los almacenes de su conjunto» (AC-37); `almacen_id` filtra dentro del conjunto y uno fuera de él se ignora. | Decisión del usuario |
| TB-02 | «Usado» es lo **entregado** en el rango, **neto de cancelaciones** y **separado por categoría**. Para los consumibles es lo que suma el reporte de consumo (C-08); para los retornables, las unidades de los vales de entrega no cancelados. Se agrupa en el servidor por artículo (y, si se pide, por almacén). | Decisión del usuario |
| TB-03 | Las fechas del rango del tablero son fechas del centro de México y el día `hasta` entra completo, igual que en los reportes. «Hoy» (entregas de hoy) es el día en esa zona. | Propuesta |

Cómo se aplican en el servidor:

- **Permisos.** `almacenes.administrar` en los cuatro endpoints de escritura de almacenes y en `GET /api/almacenes?resumen=true`; `tablero.ver` en los dos endpoints del tablero (§8.2). El alcance sale del servicio, nunca del nombre del rol.
- **Alta y edición.** Errores: `CLAVE_REPETIDA`, `NOMBRE_REPETIDO`, `YA_HAY_CENTRAL`, `PADRE_INVALIDO` (no existe, está cerrado, es sí mismo o un descendiente, o un `CENTRAL` con padre y un no central sin padre) y `CLAVE_CON_FOLIOS` (AL-05). La concurrencia de dos altas con la misma clave la resuelve la restricción única de la base.
- **Cierre.** El servidor revisa las cuatro condiciones de AL-03 y, si falla alguna, responde 409 con el código del primer bloqueo y la lista completa de lo que falta (`CON_EXISTENCIAS`, `CON_TRASPASOS_EN_TRANSITO`, `CON_HIJOS_ACTIVOS`, `CON_USUARIOS`). Reabrir con el padre cerrado responde `PADRE_CERRADO`.
- **Almacén cerrado (AL-04).** La evaluación de un vale de un almacén cerrado trae un motivo rojo con la regla `AL-04`; confirmar responde 409 `ALMACEN_CERRADO`. Las lecturas no cambian.
- **Primer arranque.** `uv run python -m app.mantenimiento sembrar-almacenes` crea Kepler, Contratistas, Midrex, HYL, Laminador y Minas solo si no existe ningún almacén; repetirlo no hace nada.

#### Inicio del supervisor: valor y uso por proyecto

**Iteración 01, aprobada, sin construir.** [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md). Extiende el valor del inventario que ya está en el código (FEAT-012, sin documento). Un total en pesos que cubre un solo artículo se muestra como «—» a quien no tiene `catalogo.costos`, porque dividirlo entre las unidades revelaría el costo (T-2 del maestro, RG-12).

| ID | Regla | Origen |
|---|---|---|
| TB-04 | **Valor del inventario de sus almacenes.** El Inicio del supervisor muestra el valor del inventario de su conjunto, **en pesos y en unidades**: en almacén, en resguardo de trabajadores y total. Los pesos piden `reportes.valor_inventario`, que el Supervisor trae de inicio (decisión D-05). Solo totales y su reparto por categoría y por almacén; **nunca** el costo unitario (RG-12). Un artículo sin costo no suma pesos y se cuenta aparte. Sin el permiso, solo unidades. | Decisión del usuario (8 oct 2026) |
| TB-05 | **Uso por proyecto.** Por cada proyecto del alcance: retornables en resguardo hoy y consumibles consumidos en el rango (unidades y valor), netos de cancelaciones; trabajadores asignados; clave, nombre, almacén, fechas y situación. Un renglón «Sin proyecto» junta las entregas sin proyecto. El valor es la cantidad por el costo actual del catálogo y sale solo con `reportes.valor_inventario`. Se muestra como **tabla con barras horizontales**, no como gráfica nueva. | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |
| TB-06 | **El uso se cuenta por el almacén del proyecto.** Un proyecto entra al alcance si **su almacén** está en el conjunto del usuario, sin importar qué almacén entregó (decisión D-13, PR-14). Lo que un trabajador tiene en resguardo cuenta para el proyecto de la **última entrega** de ese artículo (en piezas, de esa pieza). «Sin proyecto» se cuenta por el almacén del vale. | Decisión del usuario (8 oct 2026); Propuesta |
| TB-07 | **Selectores del Inicio.** Con más de un almacén en el alcance, un selector «Todos mis almacenes» o uno; la tabla de uso tiene un selector de proyecto (con uno, su reparto por categoría). Ninguno cambia el almacén activo (como TB-01) y se rotulan «Viendo: …». Con un solo almacén o un solo proyecto no hay selector. | Decisión del usuario (8 oct 2026) |
| TB-08 | **Tarjetas nuevas.** El resumen del tablero agrega `almacenes_sin_proyecto` (lista de PR-12; solo con `almacenes.administrar`) y `proyectos_por_vencer` (proyectos activos del alcance cuyo fin estimado cae en los próximos 7 días, hoy incluido, o ya pasó; con `proyectos.ver`). Al tocarlas llevan a Almacenes y a Proyectos ya filtrados. | Decisión del usuario (8 oct 2026); Propuesta (7 días) |

### 7.15 Proyectos

**Iteración 01, aprobada, sin construir.** [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) y [ADR-012](../architecture/decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md). El proyecto es una entidad nueva, distinta del almacén de tercer nivel (que se conserva): sirve para saber quién trabaja en cada mantenimiento o contrato y cuánto consumió. **Flujo normal (decisión D-01):** cada trabajador en **un** proyecto de un almacén; trabajador con varios proyectos y almacén con varios proyectos son casos especiales que se muestran solo cuando existen.

Definiciones (fechas del centro de México): **activo** es `estado = ACTIVO`; **vigente**, activo y hoy entre `inicio` y `fin_estimado`, ambos incluidos; **por iniciar**, activo con `inicio` posterior a hoy; **fin estimado vencido**, activo con `fin_estimado` anterior a hoy; **asignable**, activo con `fin_estimado` igual o posterior a hoy (vigente o por iniciar). Para **entregar** cuenta cualquier proyecto activo, aunque haya pasado su fin estimado; para **asignar** se ofrecen solo los asignables (T-1 del maestro).

| ID | Regla | Origen |
|---|---|---|
| PR-01 | **Alta del proyecto.** Solo quien tiene `proyectos.administrar` (de inicio, el Administrador) da de alta un proyecto con clave (única, de 2 a 20 caracteres, letras sin acento, números y guion; se pasa a mayúsculas), nombre, almacén, inicio y fin estimado. El almacén puede ser cualquier almacén activo: lo normal es uno de tercer nivel, pero se permite Contratistas o Kepler para personal general, con un aviso. En un almacén cerrado no se crea (409 `ALMACEN_CERRADO`). Nace `ACTIVO`. Los proyectos no se borran. | Decisión del usuario (8 oct 2026); Propuesta (formato de la clave) |
| PR-02 | **Estados y fechas.** Un proyecto está `ACTIVO` o `CERRADO`. El fin estimado no puede ser anterior al inicio (422). Vigente, por iniciar, fin estimado vencido y asignable se calculan con la fecha de hoy; no se guardan. | Decisión del usuario (8 oct 2026) |
| PR-03 | **Editar y extender.** Con `proyectos.administrar` se cambian el nombre y las fechas. La clave y el almacén solo se cambian mientras ningún vale use el proyecto (409 `PROYECTO_CON_VALES`). Un proyecto cerrado no se edita (409 `PROYECTO_CERRADO`): primero se reabre. Cada cambio queda en el registro de cambios. | Propuesta |
| PR-04 | **Cerrar.** Con `proyectos.administrar` y un motivo obligatorio. En la misma transacción **terminan todas sus asignaciones activas**. El contrato del trabajador no cambia; lo que tiene en resguardo sigue siendo su pendiente (CP-05) y no impide cerrar. Los vales ya hechos conservan su proyecto. | Decisión del usuario (8 oct 2026) |
| PR-05 | **Reabrir.** Vuelve a `ACTIVO`; si su fin estimado ya pasó, exige uno nuevo igual o posterior a hoy (422), y su almacén debe estar activo (409 `ALMACEN_CERRADO`). Las asignaciones terminadas **no** se restauran: RH vuelve a asignar. | Propuesta |
| PR-06 | **Fin estimado vencido.** Un proyecto activo que pasa su fin estimado sin cerrarse **sigue operando**: sus asignaciones siguen y las entregas lo siguen tomando. Aparece marcado «Fin estimado vencido» en Proyectos y en el Inicio del Administrador para que lo extienda o lo cierre. No se ofrece para asignaciones nuevas hasta que se extienda. El sistema nunca lo cierra solo. | Decisión del usuario (8 oct 2026) |
| PR-07 | **Quién ve los proyectos.** Con `proyectos.ver`, los de los almacenes de su conjunto (AC-37); con `almacenes.todos`, todos. Quien tiene `proyectos.asignar` (RH, sin almacén) ve todos, solo con sus datos generales y el número de asignados, sin consumo ni valor. | Propuesta |
| PR-08 | **Proyecto de la entrega, caso normal.** Si el trabajador tiene **una** asignación activa a un proyecto activo, la ENTREGA toma ese proyecto sola y lo guarda en el vale; el almacenista no elige nada y la pantalla dice «Proyecto: …». Cuenta un proyecto vigente, por iniciar (el EPP que se entrega al contratar) o con fin estimado vencido. | Decisión del usuario (8 oct 2026) |
| PR-09 | **Trabajador con varios proyectos.** Con más de una asignación activa, la evaluación trae sus proyectos y un aviso amarillo «Elige para qué proyecto es esta entrega»; el selector muestra el principal ya elegido. Confirmar sin proyecto responde 422 `PROYECTO_REQUERIDO`; con uno que no es de una asignación activa suya (o de un proyecto cerrado), 422 `PROYECTO_INVALIDO`. | Decisión del usuario (8 oct 2026) |
| PR-10 | **Entrega sin proyecto.** Si el trabajador es vigente pero no tiene ninguna asignación activa a un proyecto activo, la entrega **sí se hace**, con aviso amarillo «Este trabajador no tiene proyecto activo» y observación obligatoria (422 sin ella). El vale queda sin proyecto, entra a la lista de revisión (RG-14) y cuenta como «Sin proyecto». | Decisión del usuario (8 oct 2026) |
| PR-11 | **Proyecto en el alta y en el reingreso.** El alta de un trabajador pide `trabajadores.administrar` **y** `proyectos.asignar`, y un proyecto asignable obligatorio (422 `PROYECTO_REQUERIDO` o `PROYECTO_INVALIDO`); la asignación se crea como principal en la misma transacción. Sin proyectos asignables, el alta dice que primero se dé de alta el proyecto. El reingreso (T-02) pide proyecto si el trabajador no tiene uno asignable; si lo tiene, se propone. El área u obra del periodo se llena con el nombre del proyecto. | Decisión del usuario (8 oct 2026) |
| PR-12 | **Almacén de tercer nivel sin proyectos.** Un almacén tipo `PROYECTO` activo sin ningún proyecto `ACTIVO` muestra «Sin proyectos activos: considera inactivarlo» en Almacenes y en el Inicio del Administrador. El sistema **nunca** lo inactiva solo. Kepler y Contratistas no generan este aviso. | Decisión del usuario (8 oct 2026) |
| PR-13 | **Casos especiales de asignación.** Con `proyectos.asignar` se puede agregar un segundo proyecto (no principal salvo que se pida), terminar una asignación o cambiar de proyecto (termina una y abre otra en una transacción; la nueva hereda principal). Lo que el trabajador tiene en resguardo sigue siendo suyo. No hay dos asignaciones activas al mismo proyecto (409 `ASIGNACION_REPETIDA`) ni dos principales activas. Si termina su última asignación, queda «Sin proyecto». Las asignaciones no se borran. | Decisión del usuario (8 oct 2026); Propuesta (principal) |
| PR-14 | **El proyecto es del trabajador, no del almacén que entrega.** Contratistas puede entregar a un trabajador del proyecto de Midrex: el vale es de Contratistas y el consumo es del proyecto de Midrex. El proyecto del vale se escribe al insertar y no cambia nunca, aunque el trabajador cambie de proyecto o el proyecto se cierre. La cancelación hereda el proyecto del vale original. Devolución, traspaso, recepción, entrada y no adeudo no llevan proyecto (422 si lo traen). | Decisión del usuario (8 oct 2026) |

Cómo se aplica en el servidor: módulo nuevo `proyectos` (tablas `proyecto` y `asignacion_proyecto`), que da a los demás la lectura de los proyectos activos de un trabajador; `movimientos` escribe `vale.proyecto_id` y sigue siendo el único que escribe vales. Al confirmar una entrega el servidor vuelve a evaluar (RG-08): si el proyecto se cerró o la asignación cambió, responde 409 `VALE_CAMBIO` y el borrador se conserva. La deuda es con el almacén que entregó; el consumo, con el proyecto (T-3 del maestro, DU-02).

### 7.16 Despacho de EPP con aprobación y notificaciones

**Iteración 01, aprobada, sin construir.** [FEAT-014](../features/FEAT-014-despacho-de-epp-con-aprobacion.md) y [ADR-013](../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md). La plática del 8 oct 2026 (pedido 5) pidió que el almacenista no despache EPP sin la aprobación del supervisor del almacén, con notificación push. La herramienta y las devoluciones no la piden. Se aprueba **antes** de firmar (decisión D-08).

Términos: un **artículo de EPP** es el que pertenece a una categoría de tipo EPP (de inicio, EPP básico, EPP de dotación y Equipo de alturas). El despacho es **con aprobación** cuando el almacén lo pide (`almacen.despacho_epp_con_aprobacion`, por omisión sí), quien captura no tiene la excepción (`usuario.despacho_autonomo`, por omisión no) y quien captura no tiene `autorizaciones.resolver` en ese almacén. Un **renglón que se resuelve** es uno de EPP o uno en naranja; un **renglón de contexto** es herramienta en verde o amarillo, que el supervisor ve pero no resuelve.

| ID | Regla | Origen |
|---|---|---|
| DE-01 | **Cuándo se pide.** Toda ENTREGA con al menos un renglón de EPP necesita la aprobación del despacho cuando el despacho es con aprobación. Una entrega solo de herramienta no la pide. Nunca la piden la devolución (SM-05), el traspaso, la recepción, la cancelación, el no adeudo ni la entrada. El EPP que se entrega al contratar también la pide (supuesto; pregunta 1 de la sección 12 del maestro). | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |
| DE-02 | **El semáforo no cambia.** Cada renglón da el mismo nivel que hoy. Aparte, la evaluación dice si el vale necesita aprobación y marca cada renglón de EPP con la etiqueta «Necesita aprobación», que no es un color. El vale no se confirma mientras falte una aprobación. | Decisión del usuario (8 oct 2026); SM-03 |
| DE-03 | **Orden del flujo.** Capturar al trabajador, capturar los artículos, «Enviar a aprobación», esperar, ver la respuesta, quitar lo rechazado, firma del trabajador y confirmar. **La firma nunca va antes de aprobar.** Si después de firmar cambia algo que invalida la aprobación (DE-13), la firma se borra y el trabajador firma de nuevo; si los renglones no cambian, se conserva. | Decisión del usuario (8 oct 2026) |
| DE-04 | **Una sola solicitud por vale.** «Enviar a aprobación» crea una solicitud de tipo DESPACHO con **todos** los renglones de EPP y **todos** los naranjas (E-07, E-26, E-08); la herramienta en verde o amarillo viaja como contexto. Un rojo no se envía (422 `RENGLON_NO_AUTORIZABLE`, A-06). Si el vale pide aprobación del despacho no se acepta una solicitud de excedente, y si no la pide no se acepta una de despacho (422). Cada solicitud lleva un `id_cliente`: un doble toque no crea dos. | Propuesta; A-06 |
| DE-05 | **Motivo y nota.** Sin naranjas, el motivo lo pone el sistema («Despacho de EPP») y el almacenista puede agregar una nota de hasta 255 caracteres. Con naranjas, el motivo del excedente sigue siendo obligatorio (A-02). Las observaciones de E-09 viajan en la solicitud. | A-02; Propuesta |
| DE-06 | **Aprobación parcial.** El supervisor aprueba o rechaza cada renglón que se resuelve, con motivo obligatorio en cada rechazo; puede aprobar o rechazar todo de un toque. Queda APROBADA si aprobó al menos uno y RECHAZADA si rechazó todos. Aplica también a las solicitudes de excedente. | Propuesta |
| DE-07 | **El supervisor que despacha.** Si quien captura tiene `autorizaciones.resolver` en el almacén del vale (un supervisor o el Administrador), su captura **aprueba** el despacho de EPP: no se manda solicitud y el vale dice «Validó: él mismo (despacho)». Es la excepción a A-05. Un excedente (y cualquier naranja) **sigue necesitando a otro supervisor**, con una solicitud de excedente solo con los naranjas. Los movimientos de EPP llevan la regla `DE-07`. | Decisión del usuario (8 oct 2026); A-05 |
| DE-08 | **Qué puede confirmar el vale.** Con una aprobación, el vale lleva solo los renglones que se resuelven y que se aprobaron, con la misma cantidad o menos; los de contexto se pueden quitar o cambiar. Un renglón que necesita aprobación y no está cubierto (rechazado, no incluido o con más cantidad) responde 409 `APROBACION_INVALIDA` y no se guarda nada. | A-03; Propuesta |
| DE-09 | **Vigencia.** Una solicitud pendiente vence a los 15 minutos de creada; una aprobada sirve 15 minutos **desde que se aprobó**, para dar tiempo a la firma. Vencida, el almacenista reenvía (solicitud nueva con los mismos renglones), pide al supervisor su PIN en el mostrador o quita el EPP y entrega lo demás. | A-01, A-07; Propuesta |
| DE-10 | **Si nadie responde.** A los 5 minutos la pantalla dice «Nadie ha respondido todavía» y ofrece PIN en el mostrador, esperar o quitar el EPP. Dice a cuántos supervisores les llegó el aviso; si a ninguno, lo dice desde el principio. El almacenista **nunca** despacha EPP sin aprobación: solo el Administrador puede prender la autonomía (DE-14), y también puede aprobar la solicitud. | Decisión del usuario (8 oct 2026) |
| DE-11 | **Gana el primero que resuelve.** Si dos supervisores (o uno en su celular y otro con PIN) resuelven la misma solicitud, vale la primera; el segundo recibe 409 `AUTORIZACION_RESUELTA` y ve quién la resolvió y cuándo. | A-01; Propuesta |
| DE-12 | **Lista del supervisor y resolución múltiple.** Las pendientes van de la más antigua a la más nueva, con trabajador (nombre, número y foto), proyecto, almacén (si tiene varios), renglones (los que se resuelven arriba y el contexto abajo), quién la pide y cuánto le queda. Se pueden **aprobar o rechazar varias de un jalón**, con motivo en cada rechazo. Las que incluyen un excedente se marcan «Incluye excedente» y se abren una por una. | Decisión del usuario (8 oct 2026) |
| DE-13 | **Cambios después de aprobar.** La aprobación deja de servir si el almacenista agrega un renglón de EPP o un naranja, sube una cantidad aprobada, o cambia de trabajador, de almacén o de proyecto: hay que volver a enviar con todos los renglones que se resuelven. Quitar renglones, bajar cantidades y cambiar el contexto no la invalidan. | Propuesta |
| DE-14 | **Interruptor de autonomía.** Un interruptor por almacén y una excepción por almacenista permiten despachar EPP sin aprobación. Los cambia quien tiene `despacho.autonomia` (de inicio, solo el Administrador; decisión D-07), con motivo obligatorio; aplica en la siguiente evaluación y queda en el registro de cambios. Basta con que uno de los dos dé autonomía. Los movimientos de EPP despachados así llevan la regla `DE-14`. | Decisión del usuario (8 oct 2026) |
| DE-15 | **La espera del almacenista.** Mientras espera, la pantalla consulta la solicitud cada 3 segundos. «Atender a otro mientras» guarda el borrador en el dispositivo en la lista «En espera» (hasta 10 por dispositivo) y deja empezar otra entrega; al aprobarse, el dispositivo suena y vibra. Los borradores no salen del dispositivo. | E-28; Propuesta |
| DE-16 | **Revalidación al confirmar.** El servidor vuelve a evaluar todo el vale (RG-08). Si un renglón aprobado quedó en rojo mientras se esperaba, responde 409 `VALE_CAMBIO`; quitarlo no pide otra aprobación. Si la autonomía se apagó después de evaluar, responde 409 `REQUIERE_APROBACION_DESPACHO` y el borrador se conserva; si se prendió, el vale se confirma sin esperar y la solicitud vence sola. | RG-08, RG-09 |

**Notificaciones push.** El canal es **Web Push desde la PWA** (decisión D-14); lleva las solicitudes de despacho, de excedente y de traslado (X-17), y el aviso informativo de traslado (X-20). Ninguna regla depende de que el aviso llegue.

| ID | Regla | Origen |
|---|---|---|
| NT-01 | **Suscribirse.** Quien tiene `autorizaciones.resolver` ve el botón **«Activar avisos»** en Autorizaciones y en su menú de usuario; por la decisión transversal T-4 del maestro, también quien tiene `traspasos.recibir`, para recibir el aviso de un traslado (X-20). El navegador pide el permiso solo al tocar el botón. La suscripción queda ligada al usuario y a la sesión de ese dispositivo; se vuelve a registrar sola si cambió, «Desactivar avisos» la borra y salir la revoca. No se manda nada a una suscripción cuya sesión ya no es válida. | Decisión del usuario (8 oct 2026); AC-19 |
| NT-02 | **A quién se manda.** A cada usuario activo con `autorizaciones.resolver` que tiene el almacén de la solicitud en su conjunto, **menos quien la pidió**, en todos sus dispositivos con suscripción vigente. El Administrador no recibe avisos por omisión; ve el contador y la lista. Los destinatarios se calculan al enviar. | A-01; AC-06 |
| NT-03 | **Qué dice.** Sin costos, CURP, NSS ni foto. Título: almacén y qué se pide; cuerpo: para quién, cuántos artículos y quién lo pide («Midrex · EPP por aprobar» / «Para Juan Pérez: 4 artículos de EPP. Lo pide Ana Ruiz.»). Viaja cifrado, pero se ve en la pantalla bloqueada. | RG-12, RG-13 |
| NT-04 | **Al tocarla.** Abre la solicitud en la aplicación; si la sesión venció, pide entrar y regresa a ella; si ya no está pendiente, dice cómo quedó y quién la resolvió; un aviso agrupado abre la lista. | Plática 8 oct 2026 |
| NT-05 | **Agrupación.** Los avisos de un almacén comparten etiqueta: el nuevo reemplaza al anterior y, con varias pendientes, dice «Midrex · 5 solicitudes por aprobar». Solo el primer aviso de cada minuto suena y vibra. | Decisión del usuario (8 oct 2026) |
| NT-06 | **Al resolverse.** Cuando una solicitud se aprueba, se rechaza o se usa, a los demás destinatarios les llega un reemplazo silencioso («Luis Gómez ya la aprobó» o la cuenta nueva). La que vence no genera aviso: vencer no es un evento del servidor. | DE-11; ADR-013 |
| NT-07 | **Envío después del commit.** Los avisos se mandan cuando la solicitud o su resolución ya quedó guardada, nunca dentro de la transacción. Un fallo al enviar no deshace nada; una suscripción que ya no existe se marca revocada. Cada aviso caduca a los 15 minutos. Sin reintentos ni colas. | ADR-013 |
| NT-08 | **El respaldo sigue.** El contador del menú y la lista de Autorizaciones funcionan sin avisos. En iPhone el aviso solo llega con la aplicación instalada en la pantalla de inicio; en Android, Chrome lo recibe sin instalar. La pantalla muestra el estado de los avisos de ese dispositivo. La app de Android del almacenista no recibe push (OF-29). | RG-15; ADR-013 |
| NT-09 | **Aviso de prueba.** Quien tiene `autorizaciones.resolver` puede mandarse un aviso de prueba a su dispositivo, como máximo uno cada 10 segundos. | Propuesta |

Cómo se aplica en el servidor: la solicitud es una `autorizacion` con `tipo` (EXCEDENTE, DESPACHO o TRASLADO) y los renglones resueltos; las existentes quedan como EXCEDENTE. El despacho propio (DE-07) y el autónomo (DE-14) no crean autorización: se marcan con su regla en `movimiento.reglas` y el CHECK `no_autorizarse` sigue. El módulo nuevo `notificaciones` guarda las suscripciones y manda los avisos con las claves VAPID de `.env`. La prueba de integración del guion del PDF incluye el paso de aprobación o corre en un almacén con autonomía (T-7 del maestro).

### 7.17 Bitácora por vale

**Iteración 01, aprobada, sin construir.** [FEAT-017](../features/FEAT-017-bitacora-por-vale-y-pdf.md). La bitácora es el centro para saber dónde está cada cosa (decisión D-16): un renglón por vale, el detalle del vale a todo el ancho en computadora y descarga en PDF. Solo lee; la única escritura es `vale.lote_id` al insertar, en `movimientos`.

| ID | Regla | Origen |
|---|---|---|
| BT-01 | **Bitácora por vale.** Un renglón por vale, del más reciente al más antiguo: folio, tipo, fecha y hora, almacén, responsable, trabajador o destino, proyecto, número de renglones, unidades, estado y, si se filtró por almacén, la dirección. Paginada en el servidor. Se ve con `bitacora.ver` **o** `reportes.movimientos`, con el alcance del usuario (AC-06, AC-37). Nunca trae costos, CURP ni NSS. | Decisión del usuario (8 oct 2026) |
| BT-02 | **Lote.** Los vales de una misma importación (que se parte en vales de 500) o de un mismo traspaso por Excel llevan el mismo `lote_id` y la bitácora los agrupa en un renglón de lote que se despliega. El lote se escribe al insertar y no cambia. Los vales anteriores, los capturados a mano y las cancelaciones no tienen lote. | Decisión del usuario (8 oct 2026) |
| BT-03 | **Filtros.** Fechas del centro de México (ambas inclusivas), almacén dentro del alcance, tipo, usuario, trabajador, proyecto, artículo y pieza o serie; con filtro de artículo, pieza o serie, cada renglón dice cuántos de sus renglones coinciden. «Solo los míos» se conserva. Un filtro fuera del alcance no devuelve nada y no es error. | Decisión del usuario (8 oct 2026); SG-05; C-11 |
| BT-04 | **Dirección y marcas.** Con un almacén filtrado, cada vale dice si fue entrada, salida o en camino respecto a él. Un vale cancelado sale marcado con el folio de su cancelación; uno capturado sin conexión, con «Capturado sin conexión» y su hora. El reporte por movimiento (SG-05) se conserva como la pestaña «Detalle por renglón». | Decisión del usuario (8 oct 2026); SG-05 |
| BT-05 | **Detalle del vale, primero computadora.** A todo el ancho desde 1280 px y usable en celular: encabezado (folio, tipo, estado, fechas, almacén, responsable, trabajador, proyecto, quién validó, firma y QR), resumen por categoría (renglones y unidades), renglones y vales relacionados. El resumen en pesos solo se ve con `reportes.valor_inventario`, solo por categoría y total, nunca el costo unitario ni el importe de un renglón, nunca en el PDF; con un solo artículo en la cuenta se muestra «—» (T-2 del maestro). | Decisión del usuario (8 oct 2026); RG-12 |
| BT-06 | **Renglones y vales relacionados.** Los renglones se piden aparte, paginados, con búsqueda por código, artículo o serie. El detalle enlaza el traspaso de una recepción, las recepciones de un traspaso, la cancelación y lo cancelado, y las otras partes del lote. Un relacionado fuera del alcance se nombra sin folio ni enlace (AC-06). | Decisión del usuario (8 oct 2026); AC-06 |
| BT-07 | **PDF del vale.** «Descargar PDF» descarga un archivo con el folio de nombre y lo mismo que el vale impreso (E-24): datos del vale, trabajador, proyecto, resumen por categoría, todos los renglones, quién validó, la firma o «Firmado con la sesión de …» y el QR. **Sin costos** (RG-12, F-12), sin CURP, NSS ni foto. Un vale cancelado lleva marca de agua «CANCELADO». | Decisión del usuario (8 oct 2026); E-24; F-12 |
| BT-08 | **PDF del lote.** Un solo PDF: una hoja de resumen del lote (fecha, almacén, responsable, cada vale con folio, estado y QR, y totales por categoría) y después los renglones, vale por vale. | Decisión del usuario (8 oct 2026) |
| BT-09 | **Generado en el navegador.** El PDF lo arma el navegador con los datos que la API ya filtró por permiso y alcance, sin endpoint nuevo, para que funcione también en la app de Android sin conexión. Meta: 500 renglones en menos de 5 segundos en un celular de gama media; con más, por tramos de 500, con avance y cancelable. La librería (`jspdf`) pide aprobación. | Decisión del usuario (8 oct 2026); Propuesta |
| BT-10 | **Resultado de la importación y del traspaso por Excel.** La importación ofrece «Ver en la bitácora» (el lote desplegado) y «Descargar PDF»; el traspaso por Excel ofrece «Ver el vale» y «Descargar PDF», que sirve de lista impresa para verificar al recibir. | Decisión del usuario (8 oct 2026) |

### 7.18 Deudores

**Iteración 01, aprobada, sin construir.** [FEAT-018](../features/FEAT-018-deudores-resguardo-y-alto-valor.md). Sección propia para saber quién le debe a cada almacén, qué, desde cuándo y para qué proyecto (decisión D-17), con el alto valor siempre a la vista (sección 5.5). Solo lee. El consumo cuenta para el **proyecto**; la deuda es con el **almacén** que entregó (T-3 del maestro).

| ID | Regla | Origen |
|---|---|---|
| DU-01 | **Sección Deudores.** Pantalla `/deudores`, primero computadora, con `deudores.ver` (de inicio Supervisor, Recursos Humanos y Administrador). «Deber» es tener en resguardo un artículo **retornable**. Los consumibles no cuentan (B-03); lo que va en tránsito, lo que está en Baja y lo cerrado sin devolución (V-09) no es deuda. | Decisión del usuario (8 oct 2026); B-02; B-03 |
| DU-02 | **A qué almacén y a qué proyecto se debe.** Al almacén del vale de su **entrega más reciente** (AC-06) y al proyecto de ese vale («Sin proyecto» si no tiene). Un artículo por cantidad, igual, por la entrega más reciente de ese artículo a ese trabajador. «Desde» es la fecha de esa entrega; una cancelación no la cambia. | Decisión del usuario (8 oct 2026); AC-06; SG-01 |
| DU-03 | **Alcance.** Con `almacenes.todos`, todo. Sin él, lo que se le debe a los almacenes de su conjunto; de lo que el trabajador debe a otros almacenes solo se dice cuántas cosas son («Tiene además 3 artículos de otros almacenes»). Con `trabajadores.administrar` (RH), todos los trabajadores y todas sus deudas, sin ganar acceso a existencias, vales ni Seguimiento. Sin almacén ni esos permisos, nada. | Decisión del usuario (8 oct 2026); C-05; AC-06 |
| DU-04 | **Vista por trabajador.** Un renglón por trabajador con deuda: nombre y número, proyectos, vigencia, piezas y unidades que debe, la deuda más antigua, cuántas cosas de alto valor y, si no es vigente, el aviso de SG-06 extendido a toda su deuda. Primero los no vigentes con alto valor, luego la deuda más antigua. | Decisión del usuario (8 oct 2026); SG-06 |
| DU-05 | **Lo que debe un trabajador.** Artículo con marca, pieza y serie (o «Serie pendiente»), cantidad, desde cuándo, folio del vale, proyecto, almacén al que se le debe e insignia «Alto valor» o «Requiere inspección». Una pieza abre su ficha y su línea de tiempo (SG-03). | Decisión del usuario (8 oct 2026); SG-03 |
| DU-06 | **Filtros.** Almacén, proyecto, categoría (con «Alto valor», AV-02 y AV-03), vigencia, antigüedad (7, 30, 90 días o un número) y texto (nombre, número, credencial, artículo, código o serie) con espera de 300 ms. Paginación por trabajador en el servidor. Un filtro fuera del alcance no devuelve nada. | Decisión del usuario (8 oct 2026) |
| DU-07 | **Resumen general.** Por almacén y por proyecto: trabajadores que deben, piezas, unidades, alto valor fuera y deudores no vigentes. Mismo alcance y filtros; se descarga en CSV. Sin costos. | Decisión del usuario (8 oct 2026) |
| DU-08 | **Consumo por trabajador.** Por artículo consumible, lo entregado en el periodo separado por proyecto, neto de cancelaciones (como C-08), de **todos** los almacenes. Periodo por omisión: desde el inicio de su contrato vigente (o del último). Se ve en la ficha del trabajador (pestaña «Consumo», con `trabajadores.ver`) y al abrir un deudor. Con `reportes.valor_inventario`, solo el total en pesos del periodo y por proyecto, nunca por artículo; con un solo artículo, «—» (T-2 del maestro). | Decisión del usuario (8 oct 2026); C-08 |
| DU-09 | **Ubicación de todo en todo momento.** Deudores, Seguimiento (C-13) y la bitácora (7.17) se enlazan entre sí: de un deudor a cada pieza y cada vale; de una pieza a quién la tiene y a su línea de tiempo. El reporte de adeudos se retira como pantalla y redirige a Deudores; Seguimiento se conserva como la vista por pieza. | Plática 8 oct 2026; decisión del usuario (8 oct 2026) |

### 7.19 Búsqueda, etiquetas y diseño por dispositivo

**Iteración 01, aprobada, sin construir.** [FEAT-019](../features/FEAT-019-busqueda-etiquetas-y-diseno-por-dispositivo.md). Aquí van las reglas de comportamiento (UX-01 a UX-07); las de diseño (UX-08 a UX-12) se resumen en una línea y su detalle está en [ui-ux.md](ui-ux.md).

| ID | Regla | Origen |
|---|---|---|
| UX-01 | **Cuándo se busca.** Todo buscador busca 300 ms después de la última tecla, con 2 caracteres o más; Enter busca de inmediato (con 1 carácter, solo la identificación exacta). Lo que llega de la pistola o de la cámara es una lectura que va directo al escaneo, sin espera ni lista. | Decisión del usuario (8 oct 2026) |
| UX-02 | **Una búsqueda a la vez y estados claros.** Una búsqueda nueva cancela la anterior y una respuesta vieja nunca se pinta. Estados visibles: texto corto, buscando, sin coincidencias, error con «Reintentar» y sin conexión. Mientras llega la respuesta, la lista anterior se atenúa y no se puede tocar. | Decisión del usuario (8 oct 2026) |
| UX-03 | **Qué encuentra.** Amplía C-06: trabajadores por palabras del nombre en cualquier orden y sin acentos, por número de empleado (contiene) y por código de credencial (empieza con); artículos por nombre, marca y código; piezas por código, serie y nombre del artículo (una con serie pendiente, solo por código). Primero la coincidencia exacta, luego lo que empieza con el texto, luego lo que lo contiene. Respeta permisos y alcance (AC-05, AC-06, C-02). | Decisión del usuario (8 oct 2026); C-06 |
| UX-04 | **Qué dice cada resultado.** Una pieza dice dónde está o quién la tiene, como Seguimiento; un artículo retornable por cantidad, cuánto hay en el almacén y cuánto tienen los trabajadores; un consumible, lo que hay; un trabajador, su número, puesto y vigencia. Sin costos, CURP ni NSS. 10 resultados por grupo (8 en las hojas de un flujo, 50 como máximo), con «Ver más». | Decisión del usuario (8 oct 2026); AC-06, C-03, C-13 |
| UX-05 | **Etiquetas en un solo PDF.** Etiquetas descarga un PDF en hoja carta con 9, 18 o 30 etiquetas por hoja (la credencial completa, 8). Cada QR contiene exactamente el código registrado (RG-10), mide 20 mm o más con módulos de 0.5 mm o más, y lleva el texto legible. Se arma en el navegador; «Imprimir» queda como acción secundaria. | Decisión del usuario (8 oct 2026) |
| UX-06 | **Tipos y orígenes.** Credencial (completa o solo QR), pieza y estante. Orígenes: selección manual, piezas de una importación, trabajadores dados de alta en un rango y todas las piezas de un artículo; se puede empezar en la etiqueta N de la hoja. Pide `etiquetas.imprimir`, sin cambio. | Decisión del usuario (8 oct 2026); I-07, I-15 |
| UX-07 | **Límites.** Hasta 1000 etiquetas por PDF, con avance y cancelable. Un nombre largo se corta con «…»; el código nunca se corta. Un código largo que no se leería en tamaño chico da un aviso, sin impedirlo. | Decisión del usuario (8 oct 2026); RG-10 |
| UX-08 | Regla de diseño: cada pantalla es **primero celular** o **primero computadora** y lo declara en su ruta; anchos fijos (ver ui-ux). | Decisión del usuario (8 oct 2026) |
| UX-09 | Regla de diseño: lo de celular se prueba a 360 × 640 y 412 × 915, con objetivos táctiles de 44 px o más y la acción principal fija abajo (ver ui-ux). | Decisión del usuario (8 oct 2026) |
| UX-10 | Regla de diseño: lo de computadora se prueba a 1366 × 768 y 1920 × 1080 con tablas densas, y sigue funcionando en el celular (ver ui-ux). | Decisión del usuario (8 oct 2026) |
| UX-11 | Regla de diseño: plan de mejoras estéticas, en cambios chicos y sin cambiar reglas ni flujos (ver FEAT-019). | Decisión del usuario (8 oct 2026) |
| UX-12 | Regla de diseño: consistencia visual verificable (formato único de fechas y números, insignias con icono y texto, contraste AA; ver ui-ux). | Decisión del usuario (8 oct 2026); SM-02 |

### 7.20 App de Android y operación sin conexión

**Iteración 01, aprobada, sin construir; va al final del orden de construcción.** [FEAT-020](../features/FEAT-020-app-android-sin-conexion.md), [ADR-014](../architecture/decisions/ADR-014-app-android-con-capacitor.md) y [ADR-015](../architecture/decisions/ADR-015-operacion-sin-conexion-del-almacenista.md). El almacenista opera **en línea casi siempre**, igual que en la web; la operación sin conexión es la excepción para cuando se cae la señal, limitada a su almacén y a los trabajadores de sus proyectos (decisión D-15). Nada de esta sección cambia el flujo en línea.

| ID | Regla | Origen |
|---|---|---|
| OF-01 | La app de Android es la **misma interfaz** empaquetada con Capacitor, con su carpeta nativa en `frontend/android/`; se distribuye como APK firmado por MDM o instalación directa, sin tienda, para Android 7 o superior con un WebView equivalente a Chrome 111 o superior. En línea se comporta igual que la web. | Decisión del usuario (8 oct 2026); ADR-014 |
| OF-02 | La app manda su versión en cada petición; si es menor que `APP_VERSION_MINIMA`, el servidor responde 426 `APP_DESACTUALIZADA` y la app pide actualizar. La subida de lotes acepta la versión anterior, para que una cola nunca quede atrapada. La web no se revisa. | Propuesta |
| OF-03 | Con señal, quien tiene `sincronizacion.operar` inscribe el equipo en su almacén activo. Un equipo pertenece a un solo almacén; un almacén puede tener varios. Un equipo no inscrito solo opera en línea. Para cambiarlo de almacén se revoca y se inscribe de nuevo, después de subir su cola. | Decisión del usuario (8 oct 2026); Propuesta |
| OF-04 | El supervisor con `sincronizacion.administrar` ve los equipos de sus almacenes (quién los inscribió, sus usuarios, versión, última descarga y última subida) y los revoca con motivo. Inscripción y revocación quedan en el registro de cambios. | Decisión del usuario (8 oct 2026) |
| OF-05 | Revocar el equipo borra toda su base local; inactivar al usuario, cerrar todas sus sesiones o restablecer su contraseña o PIN borran su credencial local. Ocurre en la siguiente conexión y **después** de presentar la cola al servidor. | Decisión del usuario (8 oct 2026); AC-22 |
| OF-06 | Cada usuario entra **con señal** al menos una vez en cada equipo, con su contraseña, y crea un PIN local de 6 dígitos que se guarda solo en el equipo (derivación con sal); el servidor lo registra en el equipo. Nunca se descargan contraseñas, PIN ni sus hashes. | Decisión del usuario (8 oct 2026); Propuesta |
| OF-07 | Sin conexión solo entra quien tiene credencial local vigente en ese equipo. Cinco fallos la bloquean 5 minutos; diez la borran. Caduca a los 30 días sin entrar con señal, o si el usuario quedó inactivo, perdió `sincronizacion.operar` o cambió de almacén. Al cambiar de usuario sin señal se borra la sesión del anterior. | Propuesta; AC-18, AC-24 |
| OF-08 | Al caer la señal, la app pasa a «Sin conexión» con la primera petición que falle y vuelve a «En línea» tras dos respuestas buenas separadas por 5 s. El vale en captura conserva sus renglones y se reevalúa con el evaluador local, con la edad de los datos a la vista. Un vale empezado sin conexión se termina sin conexión, salvo que la persona elija «Revisar en línea». | Decisión del usuario (8 oct 2026) |
| OF-09 | Sin conexión siguen, por la cola «Por sincronizar», las operaciones que no piden aprobación: devolución, entrega de herramienta y de EPP con autonomía en verde o amarillo, recepción de traspasos descargados, inspección, No apta y solicitud de compra. Se firman, se confirman en el equipo y dan comprobante con QR y «Folio pendiente». Una operación de la cola **no se edita ni se borra**: se corrige después de subir, con cancelación. | Decisión del usuario (8 oct 2026); RG-02 |
| OF-10 | Sin conexión **no se entrega** lo que pide aprobación: EPP sin autonomía y cualquier naranja (E-07, E-08, E-26). Esos renglones esperan señal en un borrador; lo demás se entrega ya (A-07). Al volver la señal se manda la solicitud y sigue el flujo en línea. Sin señal no hay autorización con PIN en el mostrador. | Decisión del usuario (8 oct 2026) |
| OF-11 | Si una confirmación en línea salió y no llegó respuesta, la app no captura otro vale: pasa **el mismo** (mismo `id_cliente` y cuerpo) a la cola como «Confirmación sin respuesta» y da comprobante con «Folio pendiente». La idempotencia del servidor decide al sincronizar. | ADR-004; ADR-006 |
| OF-12 | Sin conexión no se puede enviar traspasos, cancelar, emitir no adeudo, dar de alta o reingresar trabajadores, importar o dar entrada, ajustar vigencia, registrar serie, poner en mantenimiento o calibración, pedir o resolver autorizaciones, ni atender a un trabajador fuera del paquete; la pantalla dice «Necesitas señal para…». Única salida para un código fuera del paquete: la devolución de una **pieza** «Por verificar», con observación obligatoria. | Decisión del usuario (8 oct 2026); SM-05 |
| OF-13 | El paquete del almacén trae solo lo del almacén del equipo y de los trabajadores de sus proyectos y de los proyectos de sus almacenes hijos, más quienes tienen pendientes con él. Nunca trae costos, CURP, NSS, contraseñas, PIN ni datos de otros almacenes fuera del resguardo de esos trabajadores. Viaja completo y comprimido; si no cambió, no se descarga de nuevo; las fotos van aparte. | Decisión del usuario (8 oct 2026); AC-05, AC-06, RG-12, RG-13 |
| OF-14 | El paquete se descarga al iniciar sesión o turno, a la hora de descarga del almacén (aproximada), cada vez que vuelve la señal si tiene más de 30 minutos, y con «Actualizar ahora». Primero se sube la cola y luego se descarga; lo que quede sin subir se reaplica sobre el paquete nuevo. La pantalla dice siempre la edad de los datos. La hora la edita el Administrador. | Decisión del usuario (8 oct 2026); Propuesta |
| OF-15 | Se opera sin conexión hasta `SINCRONIZACION_HORAS_MAXIMAS` (24 h) desde la última descarga, medidas con el reloj monótono del equipo. Después solo se consulta; un vale ya en captura se puede terminar. Si el reloj del equipo quedó antes de la última hora del servidor vista, se bloquea hasta sincronizar. | Decisión del usuario (8 oct 2026); Propuesta |
| OF-16 | Sin conexión, el semáforo lo calcula un evaluador local con las **mismas reglas, IDs y textos** que el servidor, para la entrega sin naranjas, la devolución, la recepción y la inspección, con los datos del paquete más lo hecho sin conexión y la fecha del equipo. Cada regla del subconjunto tiene casos de prueba compartidos con el servidor. | Propuesta |
| OF-17 | **Excepción a RG-08.** Una operación sin conexión no tuvo validación del servidor al capturarse. El servidor la revalida al sincronizar con su fecha y, en vez de rechazarla por un cambio, la clasifica: GUARDADO, GUARDADO_CON_AVISOS o CONFLICTO. | Decisión del usuario (8 oct 2026) |
| OF-18 | **Excepción a RG-09.** El lote no es todo o nada: cada operación va en su propia transacción, en orden de captura; una en conflicto no detiene a las demás. Las que dependen de una en conflicto (misma pieza, o mismo trabajador y artículo) van también a conflicto sin intentarse. | Decisión del usuario (8 oct 2026) |
| OF-19 | **Excepción a RG-11 y nota a RG-06.** `creado_en` es la hora del servidor al sincronizar; `capturado_en`, la del equipo, se guarda aparte sin corregirse. Si difieren más de 10 minutos, o la captura es posterior a la hora del servidor, el vale se marca «Hora del equipo dudosa». Una inspección sin conexión cuenta su vigencia desde su fecha de captura. El folio se asigna al sincronizar. | Decisión del usuario (8 oct 2026) |
| OF-20 | Si dos equipos sin conexión registran la **misma pieza**, se guarda el primero que sincroniza; el segundo va a conflictos con el folio del que ganó. Nunca se guardan los dos (RG-05). | Decisión del usuario (8 oct 2026) |
| OF-21 | Si al sincronizar una regla de **política** ya no se cumple (límite, vigencia del trabajador, artículo inactivo, autonomía apagada, proyecto cerrado, autorización por entrega, observación que faltó), el vale **se guarda con avisos** y entra a revisión; nadie lo autoriza después del hecho. Si es de **seguridad** (pieza No apta o inspección vencida), también se guarda, porque la pieza ya está con el trabajador, y entra a revisión como «Recuperar la pieza». Una inspección Apto sin conexión no regresa a Apta una pieza que otro marcó No apta después; una No apta sin conexión siempre se aplica. | Propuesta; ADR-015 |
| OF-22 | Va a **conflicto** lo que no se puede guardar sin romper una invariante: existencia insuficiente, pieza en otra ubicación o ya no con ese trabajador, recepción ya recibida o de más, traspaso cancelado, código, trabajador o artículo inexistente, almacén cerrado, `id_cliente` con otro cuerpo, token repetido, forma inválida, usuario no registrado en el equipo y equipo revocado. Las operaciones se evalúan en el **almacén del equipo**, aunque el usuario ya tenga otro activo (excepción a AC-13). | Decisión del usuario (8 oct 2026); RG-04, RG-05 |
| OF-23 | La cola sube en orden de captura, en lotes de hasta `SINCRONIZACION_LOTE_MAXIMO` (20) operaciones o unos 2 MB, un lote a la vez, con reintentos de espera creciente y el mismo identificador de lote. Cada vale va al servicio de `movimientos` (único que escribe vales y existencias), cada inspección al de `inspecciones` y cada solicitud al de `solicitudes_compra`. Reenviar un lote no duplica nada. | Decisión del usuario (8 oct 2026); ADR-006 |
| OF-24 | El responsable de cada operación es **quien la capturó**, aunque la suba otro usuario del equipo; se acepta solo si ese usuario está registrado en el equipo y el lote viene de un equipo inscrito, no revocado, de ese almacén. Si quien capturó ya está inactivo, se guarda con aviso. Un lote de un equipo revocado no toca el inventario: todo va a conflictos y el equipo borra sus datos. | RG-07; F-05; Propuesta |
| OF-25 | Los conflictos los resuelve un supervisor con `sincronizacion.administrar` de ese almacén, que no sea quien capturó: **reintentar**, **guardar sin los renglones en conflicto**, **guardar como diferencia** donde ya existe la regla (X-13) o **descartar**, siempre con motivo. Nunca se edita un vale guardado (RG-02): resolver crea un vale nuevo por `movimientos`. Queda en el registro de cambios. | Decisión del usuario (8 oct 2026); RG-02, A-05 |
| OF-26 | La base local es SQLite cifrada con una llave protegida por el Android Keystore; no guarda costos, CURP, NSS, contraseñas ni PIN y se borra por OF-05. El servidor no confía en el equipo: revalida todo y nunca acepta de él un folio, un saldo ni una existencia. | AC-05; RG-12, RG-13 |
| OF-27 | El comprobante sin conexión trae QR con un token generado en el equipo, «Folio pendiente» y la hora de captura, sin costos. El QR dice «Pendiente de sincronizar», «En revisión del supervisor» o «No se guardó» según el caso. El comprobante se da solo después de escribir la operación en la base local. | F-07, F-10, F-12 |
| OF-28 | El lector integrado de Zebra se usa por DataWedge en modo teclado con sufijo Enter, como una pistola; la recepción por *intents* es una mejora opcional. | Propuesta |
| OF-29 | Sin notificaciones push en la app. Usa notificaciones locales para la inspección por vencer (P-15), «Tienes N vales sin sincronizar» y el fin cercano de la ventana sin conexión. | ADR-013; Propuesta |
| OF-30 | El Inicio del supervisor muestra cuántos conflictos de sincronización están pendientes y cuántos equipos de sus almacenes llevan más de 24 h sin subir habiendo descargado datos después («Equipo con vales posiblemente sin subir»). | Propuesta |

Cómo se aplica en el servidor: módulo nuevo `sincronizacion` (equipos, usuarios del equipo, operaciones recibidas y conflictos); recibe los lotes, valida la forma y llama al servicio dueño de cada operación, que es el único que escribe. El permiso de cada operación del lote se verifica en el servicio contra quien la capturó. El vale sincronizado guarda `capturado_sin_conexion`, `capturado_en` y el equipo. En línea, ninguna regla cambia.

---

## 8. Control de acceso

El sistema decide qué puede hacer y qué puede ver cada usuario por **permisos**, no por el nombre de su rol ([ADR-007](../architecture/decisions/ADR-007-permisos-por-clave.md)). El PDF llama perfiles a lo que aquí son roles.

### 8.1 Reglas

| ID | Regla | Origen |
|---|---|---|
| AC-01 | Cada acción y cada grupo de datos reservados tiene un permiso con clave `modulo.accion`. El catálogo de permisos es fijo: lo define el sistema. | Idea del equipo |
| AC-02 | Un rol es un conjunto de permisos con nombre. Cada usuario tiene un solo rol. | Idea del equipo |
| AC-03 | El sistema nace con cinco roles: Administrador, con todos los permisos, y los cuatro que pide el PDF: Almacenista, Supervisor (de almacén), Compras y Recursos Humanos. No existe un «supervisor general»: el Administrador cubre esa función. | PDF función 1 |
| AC-04 | El servidor verifica el permiso, nunca el nombre del rol. La interfaz muestra solo lo que el rol permite, pero no es el control. | Propuesta |
| AC-05 | Hay permisos de acción (qué puede hacer) y de información (qué datos puede ver). Sin el permiso de información, el dato no se envía. | Plática min 28 |
| AC-06 | El alcance de cada usuario sale de su almacén asignado: opera y ve solo lo de ese almacén (existencias, piezas, movimientos, vales, autorizaciones, inspecciones y personal), salvo que su rol tenga `almacenes.todos`, que de inicio es solo el Administrador. Sin almacén asignado y sin `almacenes.todos`, el usuario no ve nada de ningún almacén. No hay subconjuntos de almacenes por usuario: ve el suyo o todos. La entrada de proveedor y la importación van siempre a Kepler (EK-01): quien no tiene `almacenes.todos` da entrada solo si está asignado a Kepler. De un traspaso, el origen y el destino ven lo que les toca. Una pieza es del almacén donde está; la que tiene un trabajador, del almacén de su última entrega (inspecciones, H11). Única excepción: quien atiende compras (`compras.atender`) ve las solicitudes de compra de todos los almacenes, porque una solicitud no es inventario (SC-03). **(Cambia con FEAT-013, iteración 01, sin construir):** se quita «No hay subconjuntos de almacenes por usuario: ve el suyo o todos». Cada usuario tiene un **conjunto** de almacenes (AC-36): lee lo de todo su conjunto (AC-37) y escribe en su almacén activo (AC-38). La regla de atribución no cambia. Con FEAT-018, RH (`trabajadores.administrar`) ve las deudas de todas las personas en Deudores, como en C-05 (DU-03). | Plática min 33; decisión del usuario |
| AC-07 | Hay cuatro cosas que ningún rol puede hacer, porque no son permisos: editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale. **(Cambia con FEAT-014 y FEAT-015, iteración 01, sin construir):** «autorizarse a sí mismo» tiene las excepciones de A-05: el despacho de EPP que captura el supervisor (DE-07) y el envío propio de un traslado lateral (X-16). No son la autorización de una solicitud propia, sino la autoridad de quien captura; ninguna crea una solicitud. | Propuesta |
| AC-08 | El administrador crea roles, activa o quita permisos y administra a los usuarios desde la pantalla. | Idea del equipo |
| AC-09 | Siempre existe al menos un usuario activo con `acceso.administrar`, y el rol Administrador no puede perderlo. `acceso.administrar` marca al administrador del sistema; ya no abre rutas (AC-30). | Propuesta |
| AC-10 | Un cambio de permisos aplica en la siguiente petición y queda en el registro de cambios. | Propuesta |
| AC-11 | Un rol con usuarios asignados no se inactiva ni se elimina hasta reasignarlos. | Propuesta |
| AC-12 | Asignar a un usuario a un almacén, o moverlo de uno a otro, requiere el permiso `almacenes.asignar_personal`, que de inicio tiene el Supervisor. Con él se asigna solo a quienes trabajan en un almacén (sin `almacenes.todos` y con algún permiso de almacén; RH no), sin acceso a roles, permisos ni altas de usuarios. Un supervisor de almacén solo ve al personal de su almacén y a quien no tiene almacén, y solo puede traerlo a su almacén o dejarlo sin almacén; mover personas entre almacenes distintos es de quien tiene `almacenes.todos`. Un usuario tiene un solo almacén; un almacén puede tener varios usuarios (RG-07). **(Cambia con FEAT-013, iteración 01, sin construir):** «un usuario tiene un solo almacén» pasa a «un **conjunto**, con uno activo»; quien tiene `almacenes.asignar_personal` solo agrega o quita almacenes de su propio conjunto, y ampliar con almacenes ajenos es de quien tiene `acceso.usuarios` (AC-41). | Decisión del equipo |
| AC-13 | Un cambio de almacén aplica en la siguiente petición y queda en el registro de cambios, con el almacén anterior y el nuevo. Los vales y movimientos ya hechos conservan el almacén en el que se hicieron (RG-03). Un vale a medio capturar en el almacén anterior se rechaza al confirmar y su borrador se conserva. **(Cambia con FEAT-013, iteración 01, sin construir):** aplica también al cambio del almacén activo (AC-39, 409 `ALMACEN_CAMBIO`). **Excepción sin conexión (FEAT-020):** una operación capturada sin conexión se guarda en el almacén del equipo donde se capturó, aunque el usuario ya tenga otro activo (OF-22). | Decisión del equipo |
| AC-14 | Entrar abre la sesión de **un dispositivo** con dos cookies que el navegador guarda y la interfaz no puede leer: un token de acceso de 15 minutos y un token de renovación de 7 días. El de renovación es una cadena aleatoria que no lleva datos; el servidor solo guarda su huella, nunca el token. | Decisión del usuario |
| AC-15 | Cuando el token de acceso vence, la interfaz lo renueva sola con el de renovación, sin pedir la contraseña ni interrumpir lo que se hace. Cada renovación entrega un token de renovación nuevo y el anterior deja de servir. | Decisión del usuario |
| AC-16 | Para no tomar por robo una carrera legítima (dos pestañas que renuevan a la vez, un reintento de red), un token de renovación ya cambiado se acepta durante 10 segundos: da un token de acceso nuevo a la misma sesión y no se cambia otra vez. | Decisión del usuario |
| AC-17 | Pasados esos 10 segundos, usar un token de renovación ya cambiado se toma como una copia o un robo: se cierra la sesión de ESE dispositivo (también su token nuevo) y hay que entrar con la contraseña. No afecta a los demás dispositivos de la persona. Un token inventado, vencido o ya cerrado se rechaza sin más (401 `SESION_VENCIDA`). | Decisión del usuario |
| AC-18 | La sesión dura al menos 7 días sin volver a escribir la contraseña. La vigencia se renueva con el uso (cada renovación da otros 7 días) hasta un tope absoluto de 30 días desde que se entró: pasado el tope hay que entrar de nuevo, aunque se use todos los días. Sin usar durante 7 días, la sesión vence. | Decisión del usuario |
| AC-19 | Salir cierra solo la sesión de ESE dispositivo, y de inmediato: ni su token de renovación ni su token de acceso (aunque lo hayan copiado) vuelven a servir. Las sesiones de los demás dispositivos siguen abiertas. | Decisión del usuario |
| AC-20 | La persona puede cerrar las sesiones de sus otros dispositivos, o todas las suyas (también la actual). | Decisión del usuario |
| AC-21 | La persona ve sus dispositivos con sesión abierta: cuándo entró, el último uso, el navegador y el sistema ("Chrome en Windows") y cuál es el actual. No se guarda ni se muestra la dirección IP. | Decisión del usuario |
| AC-22 | Restablecer la contraseña o el PIN de un usuario, inactivarlo o reactivarlo cierra TODAS sus sesiones, en todos los dispositivos. El token de renovación se rechaza si la versión de sesión del usuario ya cambió. | Decisión del usuario |
| AC-23 | El rol, los permisos y el almacén de la persona se leen de la base en cada petición; ni el token de acceso ni el de renovación los llevan. Un cambio aplica en la siguiente petición sin volver a entrar, y renovar la sesión no congela nada (AC-10, AC-13). | Decisión del usuario |
| AC-24 | Las cookies de sesión son `HttpOnly` y `SameSite=Lax`, y `Secure` cuando se sirve por HTTPS; la de renovación solo viaja a `/api/sesion`. El bloqueo por intentos (cinco fallos, cinco minutos) y el mensaje genérico de credenciales incorrectas no cambian. | Decisión del usuario |

AC-01 a AC-07 son parte del MVP. AC-08 a AC-13 son de [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md) y ya están construidas, con sus pantallas (`/usuarios`, `/roles`). AC-14 a AC-24 son las sesiones por dispositivo (token de acceso y token de renovación); el detalle y las decisiones están en [security-model.md](../architecture/security-model.md#sesión-por-dispositivo). Los roles y usuarios iniciales siguen cargándose con el script de datos de prueba.

Cómo se cumplen AC-08 a AC-11 en el servidor (`acceso/service_roles.py`):

- **Rol Administrador (AC-09).** Marcado `protegido`: no pierde `acceso.administrar`, no se inactiva ni se elimina. Nadie se quita a sí mismo `acceso.administrar` de su propio rol (`AUTO_BLOQUEO`) y ningún cambio de un rol deja al sistema sin un administrador activo (`ULTIMO_ADMINISTRADOR`); inactivar o cambiar de rol al último administrador ya lo rechazaba el alta y edición de usuarios.
- **Roles iniciales.** Los cinco nacen con el sistema: se ajustan sus permisos, pero no se eliminan ni cambian de nombre (`ROL_PROTEGIDO`), porque el script de datos de prueba los identifica por nombre.
- **Rol en uso (AC-11).** Se cuentan todos los usuarios asignados, incluso los inactivos (`ROL_EN_USO`).
- **Un permiso de acción incluye el de ver su módulo.** Un rol no se guarda con `entregas.crear` sin `trabajadores.ver`, `catalogo.ver` e `inventario.ver`, por ejemplo (422); el mapa viaja como `requiere` en `GET /api/permisos`. Los cinco roles iniciales lo cumplen.
- **Alcance (RG-07).** Si un rol recibe `almacenes.todos`, sus usuarios dejan el almacén asignado y cada uno queda en el registro de cambios; si lo pierde, quedan sin almacén hasta que alguien con `almacenes.asignar_personal` se lo asigne.
- **Registro de cambios (AC-10).** `rol.crear`, `rol.editar`, `rol.permisos` (con la lista anterior, la nueva y lo agregado y quitado) y `rol.eliminar`, con quién, cuándo, valor anterior y nuevo.

### 8.1 bis Roles, permisos y datos de prueba (FEAT-011, sección D)

Estas cinco reglas llevan el ID AC-30 a AC-34 de [FEAT-011](../features/FEAT-011-entrada-por-kepler-trazabilidad-y-menu.md). AC-35 (el menú simplificado) es de la misma feature y es solo de interfaz.

| ID | Regla |
|---|---|
| AC-30 | Los permisos `bitacora.ver`, `resguardo.ver`, `inventario.importar`, `catalogo.limites`, `piezas.marcar_estado`, `acceso.usuarios`, `acceso.roles` y `auditoria.ver` se eligen en `/roles`, con su descripción y su grupo. Cada uno exige los permisos de ver que necesita (tabla 8.2). `acceso.administrar` se conserva, pero ya no abre pantallas: `/usuarios` pide `acceso.usuarios` y `/roles` pide `acceso.roles` (ADR-011). Cambiar el límite de entrega de una categoría o artículo (al crear o editar) pide `catalogo.limites`, además de `catalogo.administrar`. |
| AC-31 | Roles iniciales: el Supervisor no tiene `catalogo.limites`; Recursos Humanos tiene `vales.ver`; Supervisor y Almacenista traen `traspasos.recibir`; el Almacenista tiene `resguardo.ver` y `bitacora.ver` (de su almacén); el Supervisor tiene `bitacora.ver` y `resguardo.ver`; Compras tiene `inventario.importar`, `catalogo.limites` y `bitacora.ver`; Almacenista y Supervisor tienen `piezas.marcar_estado`; el Administrador tiene todos los disponibles. Los cuatro permisos de 8.3 sin función en esta versión (`reportes.valor_inventario`, `inventario.minimos`, `piezas.dar_de_baja`, `revision.ver`) siguen en el catálogo pero se marcan «no disponible» (`disponible: false`), se ocultan de la matriz y no se asignan a ningún rol. **Ajustada el 8 oct 2026:** `reportes.valor_inventario` ya está disponible en el código desde la migración `0009_permiso_valor_inventario` (FEAT-012), con Compras, Supervisor y Administrador; pasa a la tabla 8.2. Quedan tres «no disponible»: `inventario.minimos`, `piezas.dar_de_baja` y `revision.ver`. **Iteración 01 (sin construir):** los roles iniciales reciben los permisos nuevos de la tabla 8.2 (`proyectos.*`, `despacho.autonomia`, `inspecciones.ver`, `deudores.ver`, `sincronizacion.*`). |
| AC-32 | El rol Administrador no puede perder `acceso.administrar`, `acceso.usuarios`, `acceso.roles`, `almacenes.todos` ni `almacenes.administrar`: 409 `ROL_PROTEGIDO` con el nombre del permiso. |
| AC-33 | Correr el script de datos de prueba no pisa los permisos editados en `/roles`: solo crea los roles que faltan y agrega los permisos iniciales que les faltan a los roles iniciales, salvo los que alguien les quitó a mano (quedan en el registro de cambios). Siempre se repone al Administrador. La opción explícita `uv run python -m app.datos_prueba --restablecer-roles` deja los cinco roles como nacen. |
| AC-34 | Quién recibe traspasos se cambia siempre desde `/roles`, con `traspasos.recibir`: solo el Supervisor, solo el Almacenista o ambos. El servidor verifica la clave, no el nombre del rol. |

La migración `0008_permisos_feat011` agrega los permisos nuevos sin quitar acceso a nadie: `acceso.usuarios` y `acceso.roles` a todo rol con `acceso.administrar`; `catalogo.limites` a todo rol con `catalogo.administrar` salvo el Supervisor; `inventario.importar` a quien tiene `inventario.entradas`; `piezas.marcar_estado` a quien tiene `piezas.inspeccionar`; y lo de AC-31 a los roles iniciales por su nombre.

### 8.1 ter Conjunto de almacenes y almacén activo

**Iteración 01, aprobada, sin construir.** [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) y [ADR-012](../architecture/decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md). Lo normal es un supervisor en **un** almacén (decisión D-01): con un solo almacén nada cambia en pantalla. El supervisor con varios almacenes es un caso especial (decisión D-04).

| ID | Regla | Origen |
|---|---|---|
| AC-36 | **Conjunto y almacén activo.** Cada usuario tiene un conjunto de almacenes; lo normal es uno. `usuario.almacen_id` se conserva como el **almacén activo** y siempre pertenece al conjunto (vacío solo si el conjunto está vacío). Quien tiene `almacenes.todos` no necesita conjunto y sigue igual. Sin conjunto y sin `almacenes.todos`, no ve ni opera nada (como RG-07). Conjunto, almacén activo, rol y permisos se leen de la base en cada petición (AC-23). | Decisión del usuario (8 oct 2026) |
| AC-37 | **Las lecturas abarcan todo el conjunto.** Tablero, valor del inventario, uso por proyecto, reportes, bitácora, seguimiento, resguardo, deudores, vales, existencias, proyectos, autorizaciones pendientes, inspecciones y traspasos por recibir muestran lo de todos los almacenes del conjunto. Un `almacen_id` del conjunto filtra a ese almacén; uno fuera se trata como hoy un almacén ajeno (se ignora en el tablero, 404 en un detalle). La regla de atribución de AC-06 no cambia. | Decisión del usuario (8 oct 2026) |
| AC-38 | **Las escrituras se hacen en el almacén activo.** Entregas, devoluciones, traspasos (origen), recepciones (destino), no adeudo, inspecciones, marcar estado de pieza y solicitudes de compra nuevas. Para recibir un traspaso que va a otro almacén del conjunto, o entregar desde otro, primero se cambia el almacén activo. La entrada de proveedor sigue yendo a Kepler (EK-01). | Decisión del usuario (8 oct 2026) |
| AC-39 | **Cambiar el almacén activo.** Solo a uno del conjunto y activo (403 `ALMACEN_NO_ASIGNADO`; 409 `ALMACEN_CERRADO`). Es del usuario, no del dispositivo: aplica desde la siguiente petición en todos sus dispositivos. Un vale capturado en el almacén anterior se rechaza al confirmar con 409 `ALMACEN_CAMBIO` y su borrador se conserva (como AC-13). Queda en el registro de cambios. Con un solo almacén no hay selector. | Decisión del usuario (8 oct 2026); Propuesta (por usuario) |
| AC-40 | **Autorizaciones por conjunto.** Una solicitud sigue siendo del almacén en que se pidió. La ven y la resuelven quienes tienen `autorizaciones.resolver` y ese almacén **en su conjunto**, aunque no sea su activo (y quien tiene `almacenes.todos`); con PIN en el mostrador, igual. A-05 no cambia. | Decisión del usuario (8 oct 2026) |
| AC-41 | **Asignar el conjunto.** Con `acceso.usuarios`, cualquier almacén activo. Con `almacenes.asignar_personal` (sin `acceso.usuarios`), solo se agregan o quitan almacenes **de su propio conjunto** a quien trabaja en un almacén, sin tocar sus almacenes ajenos (403); nadie se amplía su propio conjunto así. Si se quita el almacén activo, el activo pasa al primero que quede por nombre (o queda vacío). Inactivar un almacén que está en el conjunto de un usuario activo se bloquea con `CON_USUARIOS` (AL-03). La asignación de un solo almacén se conserva para el caso normal. Cada cambio queda en el registro de cambios. | Decisión del usuario (8 oct 2026); Propuesta (detalle) |

Cómo se aplica en el servidor: un solo cálculo de alcance en `acceso` (dueño de la tabla `usuario_almacen`) que usan todos los servicios en lugar de leer `usuario.almacen_id` directamente; la migración crea el conjunto de cada usuario con su almacén actual, así nadie pierde acceso.

### 8.2 Permisos y roles iniciales

A es Almacenista, S Supervisor (de almacén), C Compras y R Recursos Humanos. El Administrador tiene todos. Todo permiso de operación vale solo dentro del almacén asignado (AC-06); Compras está asignado a Kepler y RH no tiene almacén porque no opera inventario. Con la iteración 01 (sin construir), «almacén asignado» se lee como el conjunto para leer y el almacén activo para escribir (AC-37, AC-38). Los permisos marcados «Iteración 01» están aprobados y sin construir.

| Módulo | Permiso | Qué permite | Roles iniciales |
|---|---|---|---|
| Acceso | `acceso.administrar` | Marca al administrador del sistema (AC-09): siempre debe quedar alguien con él. Ya no abre ninguna pantalla; usuarios y roles tienen su permiso (ADR-011) | Solo Administrador |
| | `acceso.usuarios` | Alta y administración de usuarios, contraseñas y PIN (`/usuarios`) | Solo Administrador |
| | `acceso.roles` | Crear roles y cambiar sus permisos (`/roles`) | Solo Administrador |
| | `auditoria.ver` | Ver el registro de cambios. Lo usa la pantalla de auditoría (FEAT-011) | Solo Administrador |
| Trabajadores | `trabajadores.ver` | Ficha básica: nombre, número, puesto, vigencia y resguardo | A, S, R |
| | `trabajadores.numero_externo` | Capturar a mano el número de empleado al dar de alta, para números propios del centro; el trabajador queda marcado como externo (T-10). Requiere `trabajadores.administrar` | Solo Administrador |
| | `trabajadores.ver_datos_personales` | CURP y NSS | R |
| | `trabajadores.administrar` | Alta, reingreso, credencial y cancelar una baja | R |
| | `trabajadores.iniciar_baja` | Iniciar la baja | A, S, R |
| Catálogo | `catalogo.ver` | Categorías, artículos y piezas | A, S, C |
| | `catalogo.administrar` | Categorías, artículos, requisitos e inactivar (los límites de entrega piden además `catalogo.limites`); también dar de alta artículos nuevos al importar (I-10) | S, C |
| | `catalogo.costos` | Ver y capturar costos | C |
| Inventario | `inventario.ver` | Existencias del almacén asignado (de todos, con `almacenes.todos`) | A, S, C |
| | `inventario.entradas` | Entradas e importación, en alta y en reposición (I-10) | C |
| Operación | `entregas.crear` | Entregar y pedir autorización | A, S |
| | `devoluciones.crear` | Recibir devoluciones | A, S |
| | `traspasos.operar` | **Enviar** traspasos entre almacenes, también por lista de Excel (X-01, TR-03). Requiere `inventario.ver` | S |
| | `traspasos.recibir` | **Recibir** traspasos en el almacén de destino (X-01, X-10). Requiere `inventario.ver`. Se puede quitar o dar a cualquier rol desde Roles y permisos (AC-34) | A, S |
| | `no_adeudo.emitir` | Emitir el vale de no adeudo | A, S |
| | `vales.ver` | Consultar vales | A, S, C, R |
| | `vales.cancelar` | Cancelar los vales propios | A, S, C |
| | `vales.cancelar_todos` | Cancelar los de cualquiera de su almacén | S |
| Autorizaciones | `autorizaciones.resolver` | Autorizar o rechazar excedentes y entregas restringidas de su almacén. Con la iteración 01, también los despachos de EPP (DE-06) y los traslados laterales del origen (X-19); quien lo tiene en un almacén despacha EPP y envía traslados laterales con su propia autoridad (DE-07, X-16) | S |
| | `despacho.autonomia` | **Iteración 01 (FEAT-014).** Prender y apagar la autonomía del despacho de EPP de un almacén o de un almacenista, con motivo (DE-14). Requiere `almacenes.administrar` o `acceso.usuarios` para ver las pantallas donde se usa | Solo Administrador |
| Piezas | `piezas.inspeccionar` | Inspeccionar y marcar No apta. Con la iteración 01, una pieza o un lote (P-14, P-16) | A, S |
| | `inspecciones.ver` | **Iteración 01 (FEAT-016).** Pantalla Inspecciones: vencidas, por vencer y sin inspección de sus almacenes, con tarjeta y contador (P-11 a P-13). Requiere `catalogo.ver` e `inventario.ver` | A, S |
| | `piezas.ajustar_vigencia` | Ajustar la fecha de vigencia de una inspección (P-07) de piezas de su almacén | S |
| | `piezas.registrar_serie` | Poner el número de serie a una pieza que no lo tiene (P-08); no cambia una serie ya registrada. Requiere `inventario.ver` | S, C |
| Reportes | `reportes.existencias` | Reporte de existencias y seguimiento de piezas (C-13) | S, C |
| | `reportes.movimientos` | Reporte de movimientos, con su filtro por usuario | S, C |
| | `reportes.adeudos` | Reporte de adeudos | S, R |
| | `reportes.consumo` | Reporte de consumo | S, C |
| | `reportes.valor_inventario` | Valor del inventario en pesos, solo totales y nunca el costo unitario (C-09). Disponible en el código desde la migración `0009` (FEAT-012). Con la iteración 01 (sin construir), también el valor del Inicio del supervisor, el uso por proyecto en pesos, el resumen en pesos del vale y el valor del consumo de un trabajador (TB-04, TB-05, BT-05, DU-08) | C, S |
| | `deudores.ver` | **Iteración 01 (FEAT-018).** Sección Deudores (DU-01 a DU-09). Requiere `trabajadores.ver`. La migración lo da también a todo rol con `reportes.adeudos` | S, R |
| Proyectos | `proyectos.ver` | **Iteración 01 (FEAT-013).** Ver los proyectos de sus almacenes; quien además tiene `proyectos.asignar` (RH, sin almacén) los ve todos, solo con datos generales (PR-07) | A, S, R |
| | `proyectos.administrar` | **Iteración 01 (FEAT-013).** Dar de alta, editar, extender, cerrar y reabrir proyectos (PR-01 a PR-05). Requiere `proyectos.ver` | Solo Administrador |
| | `proyectos.asignar` | **Iteración 01 (FEAT-013).** Asignar trabajadores a proyectos y cambiarlos; el alta de un trabajador lo pide junto con `trabajadores.administrar` (PR-11, PR-13). Requiere `proyectos.ver`. La migración lo da a todo rol con `trabajadores.administrar`, para que nadie pierda el alta | R |
| Sin conexión | `sincronizacion.operar` | **Iteración 01 (FEAT-020).** Inscribir un equipo de Android y operar sin conexión en él (OF-03, OF-09) | A |
| | `sincronizacion.administrar` | **Iteración 01 (FEAT-020).** Ver los equipos de sus almacenes, revocarlos y resolver conflictos de sincronización (OF-04, OF-25) | S |
| Almacenes | `almacenes.todos` | Operar cualquier almacén y ver los movimientos de todos | Solo Administrador |
| | `almacenes.asignar_personal` | Asignar personal a su almacén o liberarlo, sin tocar roles ni permisos (AC-12); entre almacenes, solo con `almacenes.todos` | S |
| | `almacenes.administrar` | Dar de alta, editar, inactivar y reactivar almacenes, y ver el resumen de cada uno (AL-01 a AL-05); el traspaso por una ruta que no es habitual lo decide `almacenes.todos` (X-03). Requiere `inventario.ver` | Solo Administrador |
| Tablero | `tablero.ver` | Tablero de inicio: tarjetas y gráfica de lo más usado (TB-01 a TB-03). Con `almacenes.todos`, de todos los almacenes con selector; sin él, solo el del usuario. Requiere `inventario.ver` | A, S (y Administrador) |
| Etiquetas | `etiquetas.imprimir` | Hojas de QR | S, C, R |
| Bitácora | `bitacora.ver` | Bitácora de un almacén: lo que sale, lo que llega y las entradas (SG-05). Requiere `inventario.ver`. Vale solo en el almacén asignado, salvo `almacenes.todos` | A, S, C |
| Resguardo | `resguardo.ver` | «Quién tiene qué»: lo que tiene cada trabajador. Requiere `trabajadores.ver` e `inventario.ver`. Vale en el almacén asignado | A, S |
| Importación | `inventario.importar` | Cargar inventario desde Excel, separado de capturar a mano (`inventario.entradas`). Requiere `inventario.ver` y `catalogo.ver` | C |
| Límites | `catalogo.limites` | Cambiar los límites de entrega y su periodo en categorías y artículos. Requiere `catalogo.administrar`. El Supervisor no lo tiene (AC-31) | C |
| Piezas | `piezas.marcar_estado` | Pasar una pieza a mantenimiento o calibración y devolverla al servicio. Requiere `catalogo.ver` e `inventario.ver` | A, S |
| Compras | `compras.solicitar` | Pedir una compra urgente y consultar las solicitudes de su almacén (7.13) | A, S |
| | `compras.atender` | Atender las solicitudes de compra de todos los almacenes: tomar, rechazar, marcar comprada e ingresar (7.13) | C |

Un permiso de acción incluye el de ver su módulo: quien puede entregar ve la ficha básica del trabajador y las existencias de su almacén.

El Almacenista conserva lo indispensable: entregar, devolver (lo que un trabajador regresa), consultar (trabajadores por nombre, número de empleado o QR, e inventario solo de su almacén), sus movimientos de hoy, ver las existencias de su almacén (`inventario.ver`, por eso no necesita ningún permiso de reportes), inspeccionar piezas, cancelar sus vales y la baja con no adeudo, y el tablero de su almacén (`tablero.ver`). Enviar traspasos es del Supervisor del almacén y del Administrador (`traspasos.operar`); recibir lo hacen el Supervisor y el Almacenista, que trae `traspasos.recibir` de inicio para recibir en un almacén de tercer nivel con turnos de 24 horas (X-01, AC-31); los dos permisos se cambian desde Roles y permisos (AC-34). Por una ruta que no es habitual, solo el Administrador envía (X-03). No tiene reportes, etiquetas, catálogo ni puestos. Con la iteración 01 (sin construir) recibe además `proyectos.ver` (el proyecto del trabajador), `inspecciones.ver` (pantalla Inspecciones) y `sincronizacion.operar` (app de Android sin conexión); su EPP pide aprobación del supervisor salvo autonomía (DE-01), y no ve valor ni uso por proyecto.

Usuarios iniciales por almacén: cada almacén (Kepler, Contratistas, Midrex, HYL, Laminador y Minas) tiene su Supervisor y su Almacenista; Compras queda asignado a Kepler, donde carga el inventario; el Administrador y RH no llevan almacén. El Supervisor no da de alta trabajadores: eso es de RH (`trabajadores.administrar`).

### 8.3 Permisos que agregan las features

| Llega con | Permiso | Qué permite | Roles iniciales |
|---|---|---|---|
| FEAT-004 | `inventario.minimos` | Fijar mínimos por almacén | C |
| Pospuesto | `piezas.dar_de_baja` | Dar una pieza por perdida o de baja definitiva | S |
| Pospuesto | `revision.ver` | Lista de revisión | S |

`almacenes.administrar` (declarado aquí con FEAT-002 para el Supervisor) y `tablero.ver` (pospuesto, solo Administrador) **pasaron a la tabla 8.2 con FEAT-008**: el primero es solo del Administrador y el segundo es de Administrador, Supervisor y Almacenista. `trabajadores.numero_externo` llega con la misma feature y también está en 8.2. `traspasos.recibir` y `piezas.registrar_serie` (planeados el 7 de octubre de 2026) ya están en la tabla 8.2; los roles iniciales que los traen son: `traspasos.recibir` para Supervisor, Almacenista y Administrador (AC-31; corregido el 8 oct 2026, antes decía solo Supervisor y Administrador), y `piezas.registrar_serie` para Supervisor, Compras y Administrador. `reportes.valor_inventario` (declarado aquí con FEAT-002 solo para Compras) **pasó a la tabla 8.2 el 8 oct 2026**: ya está disponible en el código desde la migración `0009` (FEAT-012), con Compras y Supervisor (decisión D-05). Los permisos de la iteración 01 (`proyectos.*`, `despacho.autonomia`, `inspecciones.ver`, `deudores.ver`, `sincronizacion.*`) están en 8.2 marcados como tales. Un permiso nuevo no llega solo a los roles de una base que ya existe: se vuelve a correr el script de datos de prueba o se activa en `/roles`.

---

## 9. Prioridades

**P0** es el MVP: el guion de la demostración del PDF (p.2), sus ocho funciones indispensables y el catálogo configurable. **P1** son los diferenciadores, que se construyen como features después del núcleo. **P2** queda pospuesto. El orden de construcción está en el [roadmap](roadmap.md).

| Prioridad | Qué cubre | Reglas |
|---|---|---|
| P0 | Reglas generales y semáforo | RG-01 a RG-13, RG-15, SM-01 a SM-06 |
| P0 | Acceso por roles y permisos | AC-01 a AC-07 |
| P1 | Sesiones por dispositivo (7 días, tope de 30) | AC-14 a AC-24 |
| P0 | Catálogo configurable | CF-01, CF-02, CF-05 a CF-13, CF-15, E-19, E-26, I-09 |
| P0 | Registrar y reingresar a un trabajador | T-01 a T-03, T-05 a T-08, E-12 |
| P0 | Cargar inventario | I-01 a I-04, I-06, I-07 |
| P1 | Importación por modos, vista previa en tabla y categoría sugerida | I-10 a I-14 |
| P0 | Surtir EPP y una herramienta por escaneo | E-01 a E-06, E-15 a E-18, E-20 a E-22, E-24, E-25, E-27, E-28, F-02 (en pantalla), F-03, F-05, F-07 (con sesión), F-12 |
| P0 | Intentar una entrega que exceda el límite | L-01 a L-05, E-07, A-01 a A-07, F-04 |
| P0 | Traspaso entre almacenes | X-01 a X-04, X-06 a X-13, F-09 |
| P1 | Traspasos por lista de Excel (aprobada, FEAT-009) y permiso de recibir separado | TR-01 a TR-09 (TR-10 en la segunda entrega), X-15 |
| P1 | Serie pendiente, código de pieza automático y columna `unidad` | I-02, I-15 a I-17, E-29, P-08 |
| P1 | Administración de almacenes y tablero de inicio | AL-01 a AL-05, TB-01 a TB-03, X-03 (ruta no habitual), T-10 |
| P0 | Devolución | V-01 a V-07, V-11, V-12, V-14, F-08 |
| P0 | Baja con pendientes y vale de no adeudo | B-01 a B-05, B-07 a B-09 |
| P0 | Caso especial de alturas | E-05, E-06, P-01 a P-03, P-07 |
| P0 | Consulta y reportes | C-01 a C-06, C-08, C-11 a C-13 |
| P0 | Identidad con foto (opcional) | T-09, F-11 |
| P0 | Corregir un error | K-01 a K-05, X-14 |
| P1 | Vale como prueba | F-02 (en papel), F-06, F-07 (integridad y acceso sin sesión), F-10 |
| P1 | Cierre de mantenimiento y valor del inventario | CP-01 a CP-05, C-09 |
| P1 | Dotación y avisos no bloqueantes | D-01 a D-03, E-09, E-10, E-11 |
| P1 | Mínimos y estados de pieza | I-05, P-06, E-14, X-05 |
| P1 | Ajustes finos del catálogo | CF-03, CF-04, CF-14 |
| P1 | Control de acceso configurable y asignación de personal | AC-08 a AC-13 |
| P2 | Lista de revisión y reporte de EPP por trabajador | RG-14, C-07, C-10 |
| P1 | Solicitud de compra urgente | I-08, SC-01 a SC-11 |
| P2 | Casos poco frecuentes | V-09, V-10, V-13, P-04 (pasa a P1 con FEAT-016), P-05 |
| P2 | Habilitaciones y carta de aceptación | E-08, F-01, T-04 |

**Iteración 01 (aprobada el 8 oct 2026, sin construir).** Amplía el alcance del MVP ([maestro, sección 6](../releases/iteration_01/README.md#6-cambio-de-alcance-aprobado-por-el-usuario-el-8-de-octubre-de-2026)). El orden de construcción está en la [sección 7 del maestro](../releases/iteration_01/README.md#7-orden-de-construcción); lo del PDF del track y los traspasos completamente funcionales van primero, y la app de Android al final.

| Prioridad | Qué cubre | Reglas |
|---|---|---|
| P1 | Traslado entre almacenes de tercer nivel y traspasos completamente funcionales (FEAT-015) | X-16 a X-21; cambios en X-01, X-03, A-05, AC-07, TR-05 |
| P1 | Despacho de EPP con aprobación, autonomía y notificaciones push (FEAT-014) | DE-01 a DE-16, NT-01 a NT-09; cambios en SM-03, A-01 a A-03, A-05, A-07, F-04 |
| P1 | Proyectos, conjunto de almacenes e Inicio del supervisor con valor y uso por proyecto (FEAT-013) | PR-01 a PR-14, AC-36 a AC-41, TB-04 a TB-08; cambios en RG-07, AC-06, AC-12, AC-13, A-01, AL-03, TB-01, T-02, T-03, E-24, C-09 |
| P1 | Bitácora por vale y PDF (FEAT-017) | BT-01 a BT-10; notas en C-04 y SG-05 |
| P1 | Deudores, consumo por trabajador y alto valor (FEAT-018) | DU-01 a DU-09, AV-01 a AV-05; cambios en 5.1, C-05, C-08, I-14, SG-04, SG-06 |
| P1 | Inspecciones y avisos de vigencia (FEAT-016) | P-09 a P-17; cambios en P-01, P-04, E-11, I-03, 5.4 |
| P1 | Búsqueda con espera, etiquetas en PDF y diseño por dispositivo (FEAT-019) | UX-01 a UX-12; cambios en C-06, E-18 |
| P1 | App de Android y operación sin conexión (FEAT-020) | OF-01 a OF-30; excepciones en RG-06, RG-08, RG-09, RG-11, E-28, AC-13; cambio en RG-15 |

En el MVP, las excepciones que resuelve el almacenista ya piden observación; lo que queda en P2 de RG-14 es la pantalla donde el supervisor las revisa.

---

## 10. Supuestos

Los supuestos con los que se escribieron estas reglas, y qué pasa si resultan distintos, están en [01-descubrimiento.md](../01-descubrimiento.md).

---

## 11. Historial

- **Versión 9, sin publicar (8 oct 2026, iteración 01, aprobada).** Solo documentación; el código aún no refleja estos cambios. Incorpora la plática del 8 de octubre de 2026 y las decisiones D-01 a D-21 del [maestro de la iteración 01](../releases/iteration_01/README.md). (1) **Reglas nuevas:** proyectos PR-01 a PR-14 (7.15), conjunto de almacenes y almacén activo AC-36 a AC-41 (8.1 ter), Inicio del supervisor TB-04 a TB-08 (7.14), despacho de EPP con aprobación DE-01 a DE-16 y notificaciones push NT-01 a NT-09 (7.16), traslado entre almacenes de tercer nivel X-16 a X-21 (7.5 y 7.6), inspecciones y avisos P-09 a P-17 (7.8), bitácora por vale BT-01 a BT-10 (7.17), alto valor AV-01 a AV-05 (5.5), deudores DU-01 a DU-09 (7.18), búsqueda, etiquetas y diseño UX-01 a UX-12 (7.19) y app de Android sin conexión OF-01 a OF-30 (7.20). (2) **Reglas que cambian**, con su texto anterior conservado: RG-07, RG-15, SM-03, A-01, A-02, A-03, A-05, A-07, 5.1 (definiciones y columna de alto valor), 5.4 (parámetros nuevos), F-04, T-02, T-03, I-03, I-14, E-11, E-18, E-24, X-03, TR-05, P-01, P-04, C-04, C-05, C-06, C-08, C-09, SG-04, SG-06, AL-03, TB-01, AC-06, AC-07, AC-12 y AC-13; notas de la excepción sin conexión en RG-06, RG-08, RG-09, RG-11 y E-28, y nota en RG-12 y SG-05. (3) **Correcciones sin cambio de regla:** X-01 y el texto de 8.3 decían que el Almacenista no traía `traspasos.recibir` de inicio; la tabla 8.2, AC-31 y el script de datos de prueba sí se lo dan. `reportes.valor_inventario` pasa de 8.3 («no disponible») a 8.2: el código lo tiene disponible desde la migración `0009` (FEAT-012), con Compras y Supervisor; AC-31 ajustada. (4) **Permisos nuevos** en 8.2: `proyectos.ver`, `proyectos.administrar`, `proyectos.asignar`, `despacho.autonomia`, `inspecciones.ver`, `deudores.ver`, `sincronizacion.operar` y `sincronizacion.administrar`. (5) Las menciones de «proyecto» que significaban un almacén de tipo `PROYECTO` dicen ahora «almacén de tercer nivel» o «almacén de proyecto». (6) Índice de casos especiales (7.12) y prioridades (sección 9) con los casos y bloques de la iteración. Ajustes de las decisiones transversales T-1 a T-7 del maestro aplicados (por ejemplo, NT-01 ofrece los avisos también a quien tiene `traspasos.recibir`, T-4).

- **Sin publicar (7 oct 2026, decisiones aprobadas).** Solo documentación; el código aún no refleja estos cambios. (1) **Serie pendiente:** I-02 pasa a «el código es obligatorio o se genera; la serie es opcional y queda pendiente» (se deriva de `numero_serie` vacío, sin estado nuevo ni migración); reglas nuevas I-17, E-29 (amarillo: la entrega no se bloquea) y P-08; ajustes en la definición de Pieza, RG-10, I-06, E-18, V-14, C-06, C-13 y TR-04. (2) **Código de pieza automático** en la importación de alta (I-15). (3) **Columna `unidad`** (I-16); I-13 se mantiene. (4) **Permiso `traspasos.recibir`** separado de `traspasos.operar`, que queda para enviar: X-01 reescrita, X-08, X-10 y TR-03 ajustadas, sección 8.2 y 8.3; con esto quedan resueltos el pendiente de TR-03 y la mejora 2 de [red-de-almacenes-y-flujo.md](red-de-almacenes-y-flujo.md). (5) **Permiso `piezas.registrar_serie`** (Supervisor, Compras y Administrador). (6) **Recepción por lista** (X-15): no cambia la lógica, solo la interfaz. Decisiones D2 y D4 del plan confirmadas. FEAT-009 pasa de propuesta a aprobada.
- **Sin publicar (7 oct 2026, antes).** Traspasos por lista de Excel ([FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md)): reglas nuevas TR-01 a TR-10 (sección 7.6). Notas de referencia en X-01 e I-10.
- **Sin publicar (6 oct 2026).** Administración de almacenes y tablero de inicio ([FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md)): reglas nuevas AL-01 a AL-05 y TB-01 a TB-03 (sección 7.14) y T-10 (el número de empleado lo genera el servidor). Cambios: **X-03** (la ruta que no es padre-hijo solo la hace quien tiene `almacenes.todos`, con observación obligatoria; antes cualquiera con aviso), **T-01 a T-03** (reingreso por CURP o, sin CURP, por nombre completo). Permisos: `almacenes.administrar` (solo Administrador; antes se declaraba para el Supervisor), `tablero.ver` (activo: Administrador, Supervisor y Almacenista) y `trabajadores.numero_externo` (nuevo, solo Administrador), todos en la sección 8.2.
- **Sin publicar (6 oct 2026).** Importación por modos (I-10 a I-14): alta y reposición, tope de cantidad por fila, aviso de archivo ya importado, cantidades solo enteras y categoría sugerida por la descripción. Se consolidan las filas del mismo artículo por cantidad y almacén (I-06, RG-10). Cambio de política: el alta que crea artículos exige además `catalogo.administrar` (sección 8.2). Parámetro nuevo en 5.4.
- **Sin publicar (6 oct 2026).** Sesiones por dispositivo: token de acceso de 15 minutos y token de renovación de 7 días, renovado con el uso hasta un tope de 30 días, con rotación y detección de reutilización (AC-14 a AC-24). Salir cierra solo ese dispositivo; cambiar la contraseña o el PIN, inactivar o reactivar cierra todas. Sustituye al token único de 12 horas.
- **Versión 8 (6 oct 2026).** Solicitud de compra urgente (I-08, sección 7.13, SC-01 a SC-11): el supervisor o el almacenista la levanta, Compras la ve de todos los almacenes, la toma, la compra y la ingresa ligándola con su vale de entrada. Permisos nuevos `compras.solicitar` (A, S) y `compras.atender` (C) en la sección 8.2. Pasa de pospuesta a incluida.
- **Versión 7 (5 oct 2026).** Dotación por puesto construida en el servidor (FEAT-003): D-04 (la dotación no pasa del límite), el criterio de lo entregado en D-02 y los avisos E-09, E-10 y E-11. Sin permisos nuevos: puestos y dotación usan `catalogo.ver` y `catalogo.administrar`.
- **Versión 6 (5 oct 2026).** Alineación con el código construido, sin reglas nuevas. I-04: el costo unitario se captura en el catálogo y en la importación, no en la entrada. V-02: un vale con solo renglones V-02 sale en rojo y no se confirma. Prioridades (sección 9): E-27, E-28 y P-07 pasan a P0, y T-09 y F-11 quedan solo en P0.
- **Versión 5 (4 oct 2026).** Escanear solo agrega a un borrador y las existencias cambian al confirmar (E-28); aviso de cantidad inusual por artículo (E-27, sección 5.4); filtro por usuario en el reporte de movimientos y rastreo de desapariciones (C-05, C-11). La carta de aceptación queda pospuesta (T-04, F-01). Cancelar y rehacer (K-05), Mis movimientos de hoy (C-12) y ajuste de la vigencia de una inspección por un supervisor o administrador (P-07, permiso `piezas.ajustar_vigencia`). RG-07 aclara que cada almacenista usa su propia cuenta y dispositivo. Entran el reporte de consumo (C-08, permiso `reportes.consumo`) y la foto opcional del trabajador (T-09). Se agregan AC-12 y AC-13 y el permiso `almacenes.asignar_personal` para asignar personal a almacenes con FEAT-006.
- **Versión 4 (4 oct 2026).** El acceso pasa de perfiles fijos a roles con permisos por clave (sección 8, reglas AC-01 a AC-11). RG-07, RG-12, RG-13 y A-01 se redactan en términos de permisos. De los [escenarios](escenarios.md) salen dos aclaraciones: T-02 dice cómo se extiende un contrato, y V-14 y E-18 qué hacer con una etiqueta ilegible.
- **Versión 3 (4 oct 2026).** Se agrega el catálogo configurable (sección 5): categorías con plantilla de reglas, requisitos especiales por artículo, e inactivar y reactivar. Reglas nuevas E-19, E-26, I-09, X-09 y K-04. El daño en artículos por cantidad va a Baja (V-05). La cancelación de vales entra al MVP y se agrega el índice de casos especiales (7.12).
- **Versión 2 (4 oct 2026).** Se incorpora la plática del patrocinador: el vale de no adeudo lo emite el almacén, el contrato vencido bloquea, los costos solo los ve Compras, el supervisor queda para excepciones, se elimina el plazo de devolución y la firma admite papel.
- **Versión 1 (3 oct 2026).** Primera versión, a partir del PDF y las notas.
