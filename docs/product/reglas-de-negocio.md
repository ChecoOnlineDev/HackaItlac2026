# Reglas de negocio — Reto IMHOTEP (Track 3)

Catálogo de reglas, limitantes y casos especiales de cada operación. Es el anexo del [PRD](prd.md): el PRD explica el producto y este documento fija cómo debe comportarse. Las historias de usuario citan las reglas por su ID.

Versión 5 (4 de octubre de 2026). Alcance: flujo en línea.

Cada regla indica su **origen**:

- **PDF**: lo exige `docs/HackaItlacTrack3_2026.pdf` (página o función indispensable). No se puede recortar.
- **Plática**: lo dijo el patrocinador en la reunión ([transcripcion_track.md](../info_track/transcripcion_track.md)); se indica el minuto.
- **Propuesta**: decisión de diseño nuestra. Se puede recortar si falta tiempo.

**Principio que ordena todo** (plática min 11 y 42): el sistema debe ser lo más simple posible para gente poco familiarizada con la tecnología, y el supervisor casi no tiene tiempo. Por eso el sistema bloquea solo lo que el PDF exige bloquear o lo que es de seguridad. Lo demás lo resuelve el almacenista con una observación obligatoria, y queda en una lista para revisarse después.

---

## 1. Conceptos

**Ubicación.** Lugar donde puede estar un artículo. Hay tres clases:

- Almacén: Kepler (central, fuera de la planta), Contratistas (dentro de Mittal) y los almacenes de área (Midrex, HYL, Laminador, Minas). Los de área son temporales: contenedores que se abren para un mantenimiento y se cierran al terminar (plática min 32 y 49).
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

**Pieza.** Unidad física de un artículo controlado por pieza. Tiene código único, número de serie del fabricante, estado (Apto, No apto, En mantenimiento, En calibración, Baja), vigencia de su inspección y ubicación actual.

**Trabajador vigente.** Trabajador en estado Activo cuyo periodo de contrato incluye la fecha de hoy. Solo a un trabajador vigente se le entrega.

**Vale.** Documento de una operación: folio, tipo, origen, destino, responsable, trabajador y firmas.

**Movimiento.** Renglón del vale y de la bitácora: artículo (y pieza si aplica), cantidad, ubicación de origen, ubicación de destino, condición y saldo resultante.

**Lista de revisión.** Excepciones que resolvió el almacenista con una observación: cancelaciones, cierres sin devolución, diferencias de traspaso, faltantes. El supervisor la revisa cuando puede; no detiene la operación.

**Permiso.** Lo que un usuario puede hacer o ver, identificado por una clave como `entregas.crear`.

**Rol.** Conjunto de permisos con nombre; cada usuario tiene uno. El PDF los llama perfiles (sección 8).

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
| RG-06 | El folio es consecutivo por tipo de vale y almacén (ejemplo: `KEP-ENT-000123`). No se reutiliza, ni siquiera al cancelar. | PDF p.8; plática min 52 |
| RG-07 | Cada usuario opera sobre su almacén asignado y no lo elige en cada operación; solo quien tiene `almacenes.todos` (de inicio, el Administrador) elige almacén (AC-06). Quien no tiene almacén asignado y no tiene `almacenes.todos` no ve ni opera nada de ningún almacén. Cada almacén tiene su(s) supervisor(es), independientes de los almacenistas. Un almacén puede tener varios almacenistas: operan las 24 horas y una sola persona no los cubre. Cada almacenista usa su propia cuenta y su propio dispositivo, y cada operación queda ligada a quien la hizo. El MVP no avisa cuando a un almacén le falta cobertura. | Plática min 33 |
| RG-08 | Todo se valida dos veces: al escanear (semáforo inmediato) y al confirmar (el servidor revalida). Si algo cambió entre ambos momentos, el vale no se guarda y se indica el renglón que falló. | Propuesta |
| RG-09 | Un vale se guarda completo o no se guarda. | Propuesta |
| RG-10 | Los códigos se aceptan tal como vienen, en QR o barras. Un código identifica una sola cosa: trabajador, pieza, artículo o vale. | PDF p.2; plática min 57 |
| RG-11 | La fecha y hora válidas son las del servidor. | Propuesta |
| RG-12 | El costo de un artículo lo ve solo quien tiene el permiso de costos; de inicio, Compras. En vales, tickets y comprobantes no aparece nunca, lo vea quien lo vea. | Plática min 38 |
| RG-13 | La CURP y el NSS del trabajador los ve solo quien tiene el permiso de datos personales; de inicio, RH. El almacenista ve nombre, número, puesto, área, vigencia y foto. El sistema no guarda sueldos. De inicio, RH no ve el inventario. | Plática min 28 |
| RG-14 | Toda excepción que resuelve el almacenista exige una observación y entra a la lista de revisión. | Plática min 36 y 42 |
| RG-15 | La aplicación es web, funciona en celular, tableta y computadora, y no requiere instalarse. | PDF p.2; plática min 10 y 26 |

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
| SM-03 | El vale se puede confirmar cuando no queda ningún rojo y todos los naranjas están autorizados. |
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
| A-01 | Autoriza cualquier usuario con el permiso de autorizar; de inicio, los supervisores de almacén y el Administrador. Una solicitud es del almacén en que se pidió: solo la ven y la resuelven quienes tienen ese almacén asignado (y el Administrador); un supervisor de otro almacén o sin almacén no la ve (AC-06). Lo hace desde su propio celular, donde ve la solicitud y responde, o con su PIN en el dispositivo del almacenista si está presente; en ese caso, el supervisor que da su usuario y PIN también debe ser del almacén de la solicitud (o Administrador). | PDF función 6; plática min 42 |
| A-02 | La autorización exige un motivo. | Plática min 36 |
| A-03 | Vale para los renglones señalados de ese vale y se usa una sola vez. No cambia el límite del artículo. | Propuesta |
| A-04 | Se registra quién la pidió, quién autorizó, cuándo, el motivo y el excedente. En el vale aparece como "Validó". | PDF p.3: firma "Validó" |
| A-05 | Quien captura el vale no puede autorizarse a sí mismo. | Propuesta |
| A-06 | Un rojo no se autoriza (SM-04). | PDF p.2 |
| A-07 | Si la autorización no llega, el almacenista quita el renglón excedente y entrega lo demás. | Propuesta |

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

Categorías iniciales. Son un punto de partida; la empresa las cambia cuando quiera.

| Categoría | Tipo | Control | Retorno | Reglas de la plantilla | Ejemplos |
|---|---|---|---|---|---|
| EPP básico | EPP | Por cantidad | Retornable | Límite de 1 en posesión | Casco, respirador, peto, polainas |
| EPP de dotación | EPP | Por cantidad | Consumible | Límite por periodo | Guantes, lentes, tapones, filtros, camisola, calzado |
| Equipo de alturas | EPP | Por pieza | Retornable | Inspección vigente | Arnés, bandola, gancho doble de vida, retráctil |
| Herramienta manual | Herramienta | Por cantidad | Retornable | Sin reglas extra | Marro, cincel, flexómetro, extensión |
| Herramienta eléctrica | Herramienta | Por pieza | Retornable | Sin reglas extra | Minipulidor, reflector |
| Equipo de alto valor | Herramienta | Por pieza | Retornable | Límite de 1 en posesión | Detector de gases, radio |
| Consumibles de trabajo | Herramienta | Por cantidad | Consumible | Límite por periodo | Discos de corte, soldadura |

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
| Vigencia de la inspección | Artículo; lo propone la categoría | 180 días (supuesto) |
| Aviso de inspección por vencer | General | 7 días antes |
| Mínimo de existencias | Artículo y almacén | Sin mínimo |
| Dotación recomendada | Puesto | Vacía |
| Vigencia de una solicitud de autorización | General | 15 minutos |
| Intentos fallidos de PIN antes de bloquear | General | 5 intentos, bloqueo de 5 minutos |
| Formas de firma permitidas | General | En pantalla y en papel |

En el MVP los parámetros generales son valores fijos de configuración; los de artículo, categoría y almacén se editan en pantalla.

---

## 6. Firma y evidencia del vale

Objetivo: que el vale sirva como prueba de que el trabajador recibió el equipo, y que el trabajador también confíe en él. En la plática pidieron las dos cosas: la firma, porque sin ella el trabajador puede decir que no lo sacó (min 22), y una copia en su poder, porque teme que el registro electrónico se manipule (min 23).

| ID | Regla | Origen |
|---|---|---|
| F-01 | **Pospuesta (T-04).** En el alta, el trabajador firma una sola vez en papel una carta en la que acepta que los vales firmados en el sistema valen como firmados a mano, y recibe el aviso de privacidad. | Propuesta |
| F-02 | Cada entrega se firma de una de dos formas. En pantalla: con el dedo, debajo de la lista de artículos y de la leyenda de responsabilidad. En papel: se imprime el ticket en dos copias, el trabajador firma y el almacenista fotografía la copia firmada. Sin una de las dos, el vale no se cierra. | PDF p.8 paso 5; plática min 22–23 |
| F-03 | El almacenista firma con su sesión (usuario y contraseña). No dibuja firma en cada vale. | Propuesta |
| F-04 | El supervisor firma solo cuando autoriza (sección 4.3). No valida cada vale. | Plática min 42 |
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
| T-01 | La persona se identifica por su número de empleado. La CURP o el NSS son opcionales y solo los ve RH. | Plática min 56; RG-13 |
| T-02 | Si el número de empleado o la CURP ya existen, es un reingreso: RH registra el nuevo periodo y la misma persona se reactiva. Su historial y sus pendientes se conservan. Extender un contrato se hace igual: se registra el periodo nuevo. | Plática min 18 |
| T-03 | Datos obligatorios: nombre, número de empleado, puesto, área u obra, y periodo del contrato (inicio y fin). Opcionales: tallas, CURP o NSS. | PDF p.3, p.5; plática min 17 y 40 |
| T-04 | **Pospuesta.** La carta de aceptación firmada (F-01) no es requisito del alta en el MVP: el trabajador queda Activo al guardar. Se mantiene en el plan del producto para el hackathon, sin bloquear el alta. | Decisión del equipo |
| T-05 | La credencial que se escanea es la que emite la planta: en el alta se escanea una vez para ligarla al trabajador. Si no trae código legible, el sistema genera un QR para imprimir. También se puede teclear el número. | Plática min 17 y 57; PDF p.8 paso 1 |
| T-06 | Estados: Activo, Baja en proceso, Inactivo. | PDF función 7; plática min 19 |
| T-07 | Un trabajador es vigente si está Activo y hoy cae dentro de su periodo de contrato. | Plática min 17–18 |
| T-08 | RH consulta desde su celular la situación de cada trabajador: qué tiene pendiente y si ya tiene vale de no adeudo. | Plática min 15 |
| T-09 | En el alta, RH toma la foto del trabajador con la cámara del dispositivo o sube una imagen (F-11). Es opcional: sin foto, la ficha dice "Sin foto registrada" y la entrega continúa. RH la puede reemplazar y el cambio queda en el registro de cambios. La foto es un dato personal: solo la ve quien tiene `trabajadores.ver` y nunca aparece en un comprobante. | Decisión del equipo |

### 7.2 Entrada de inventario (Compras)

| ID | Regla | Origen |
|---|---|---|
| I-01 | Las existencias nacen solo con una entrada: de Proveedor a un almacén. Las compras entran por Kepler; la carga inicial puede ir a cualquier almacén. | Plática min 5 y 32 |
| I-02 | Cada pieza entra con su código único, marca y número de serie del fabricante. Un código repetido se rechaza. | PDF p.2; plática min 37 |
| I-03 | Una pieza que requiere inspección entra con su inspección inicial (fecha y resultado). Sin ella queda pendiente y no se puede entregar. | PDF p.2 |
| I-04 | El costo unitario se captura en el catálogo, al crear o editar el artículo, y en la importación de inventario (solo en artículos nuevos), siempre con el permiso `catalogo.costos`. La entrada de inventario no recibe costos: el vale nunca lleva costos (RG-12, F-12). Sirve para valuar el inventario y solo lo ve quien tiene `catalogo.costos`; de inicio, Compras. | PDF p.10; plática min 38–39; decisión del equipo |
| I-05 | Cada artículo puede tener un mínimo por almacén. Se compara contra lo disponible: no cuenta lo No apto, en mantenimiento ni en calibración. Al bajar del mínimo se marca en rojo en la pantalla de Compras. | Plática min 47 y 50 |
| I-06 | El inventario inicial se carga pegando o subiendo una tabla de Excel, con vista previa antes de guardar. | Plática min 34 |
| I-07 | Todo artículo por cantidad tiene un QR de producto que se imprime como etiqueta de estante. | Plática min 20–21 |
| I-08 | Si falta una herramienta, el supervisor genera una solicitud de compra; Compras la atiende y registra la entrada. | Plática min 45 (opcional) |
| I-09 | No se registran entradas de un artículo inactivo (CF-10). | Idea del equipo |

### 7.3 Entrega (almacenista)

Pasos: escanear credencial, confirmar la foto, escanear artículos, resolver naranjas, firma del trabajador, vale.

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
| E-11 | La inspección vence en 7 días o menos (hoy incluido). Sin observación. | Amarillo | Propuesta |
| E-12 | El trabajador trae pendientes de un periodo anterior. | Amarillo | Plática min 9 |
| E-14 | La entrega deja al almacén por debajo del mínimo (I-05). | Amarillo | Plática min 47 |
| E-15 | La pieza ya está en este vale. | Se ignora con sonido | Propuesta |
| E-16 | El artículo por cantidad ya está en este vale; incluye volver a escanear el QR del estante. | Suma 1 a la cantidad | PDF p.8 paso 3; plática min 21 |
| E-19 | El artículo está inactivo (CF-10). | Rojo | Idea del equipo |
| E-26 | El artículo pide autorización del supervisor en cada entrega (CF-06). Se muestra su motivo. | Naranja | Idea del equipo |
| E-27 | La cantidad del renglón es igual o mayor que el aviso de cantidad inusual del artículo (5.4). Se pide confirmar la cantidad antes de continuar. | Amarillo | Idea del equipo |

Otras reglas de la entrega:

| ID | Regla | Origen |
|---|---|---|
| E-17 | Al identificar al trabajador se muestran su foto, su vigencia y lo que ya tiene en resguardo. | Plática min 10 y 16 |
| E-18 | Si el artículo no tiene etiqueta, se escanea el QR de su estante o se busca por nombre. Si la etiqueta de una pieza no se lee, se busca por su número de serie. Si la credencial no se puede leer, se teclea el número del trabajador. | Plática min 3 y 20–21 |
| E-20 | Retornable: movimiento de almacén a trabajador. | PDF función 4 |
| E-21 | Consumible: movimiento de almacén a Consumido, con el trabajador anotado. Así queda su historial de consumo. | Plática min 31 |
| E-22 | Se registra la condición al salir de cada renglón. | PDF p.4 |
| E-24 | El vale lleva folio, fecha y hora, trabajador, área u obra, descripción con marca, código o serie, cantidad, condición, responsable y QR. No lleva costos. | PDF p.8 paso 6; plática min 38 y 51 |
| E-25 | No hay plazo por préstamo: la herramienta puede quedarse todo el proyecto. El plazo es el fin del contrato. | Plática min 37 y 52 |
| E-28 | Escanear un código agrega el renglón a un borrador del vale, y el servidor lo evalúa sin escribir nada. Las existencias y el resguardo cambian solo al confirmar el vale, en una sola operación (RG-01, RG-09). Mientras no se confirme, cualquier renglón se puede quitar. | RG-01, RG-09; idea del equipo |

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
| V-14 | Una pieza con la etiqueta ilegible se devuelve eligiéndola de la lista del trabajador o buscándola por su número de serie. El almacenista compara la serie grabada con la de la pantalla. | Verde | Propuesta |

Caso "me devolvió una que no es": con código único por pieza, el escaneo lo detecta de inmediato. Si la pieza es de otro trabajador, se abona a su titular y la del que la trajo sigue pendiente. Si el código no existe, aplica V-12.

### 7.5 Traspaso: salida (almacenista de origen)

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| X-01 | El traspaso tiene dos pasos: salida y recepción. Los opera el Supervisor del almacén (`traspasos.operar`): el del origen envía y el del destino recibe; el Almacenista no. Entre ambos la existencia está En tránsito y no cuenta para ningún almacén. | — | PDF p.6 |
| X-02 | Solo sale lo que está en el almacén de origen. | Rojo si no | PDF función 4 |
| X-03 | El destino es otro almacén. Rutas habituales: Kepler con Contratistas, y Contratistas con las áreas, en ambos sentidos. Otra ruta se permite con aviso. | Amarillo | PDF p.6; plática min 30 |
| X-04 | Una pieza No apta puede trasladarse (para reparación o baja). Conserva su estado. | Amarillo | Propuesta |
| X-05 | La salida deja al origen por debajo del mínimo. | Amarillo | Plática min 47 |
| X-06 | Se genera el folio del traspaso con QR. Estado: En tránsito. | — | PDF p.6 |
| X-07 | Cada movimiento conserva origen y destino. | — | PDF p.1 |
| X-09 | Un artículo inactivo sí puede trasladarse, para concentrar o retirar sus existencias (CF-11). | — | Propuesta |

### 7.6 Traspaso: recepción (almacenista de destino)

| ID | Regla | Nivel | Origen |
|---|---|---|---|
| X-08 | El almacenista que recibe queda como responsable de lo recibido. | — | Plática min 32–33 |
| X-10 | Solo el almacén de destino puede recibir. El QR del traspaso lo abre. | Rojo si es otro | PDF p.6 |
| X-11 | Se puede recibir todo de una vez o escanear renglón por renglón. | — | Propuesta |
| X-12 | Lo escaneado no pertenece a este traspaso. | Rojo | Propuesta |
| X-13 | Si falta algo, lo no recibido sigue En tránsito, el traspaso queda "Recibido con diferencias" y entra a la lista de revisión. | Amarillo | Propuesta |
| X-14 | Un traspaso en tránsito lo cancela el almacén de origen, con observación y solo antes de la recepción. La existencia regresa al origen. | Amarillo | Propuesta |

Cómo se aplican en el servidor (salida y recepción). El destino de una salida es habitual si un almacén es el padre del otro en la red (`almacen.padre_id`); mismo almacén, un destino que no existe o uno cerrado son rojos de X-03. X-04 cubre toda pieza que no esté Apta (No apta, En mantenimiento, En calibración): se traslada con aviso y conserva su estado. X-09 solo informa (nivel verde). Una salida con un renglón en rojo no se confirma (RG-09) y un traspaso sin renglones se rechaza. En la recepción, "todo de una vez" es mandar todos los renglones pendientes del traspaso (la lista de por recibir los trae) y "renglón por renglón" es mandar los escaneados; una recepción sin renglones se rechaza. Lo pendiente de un traspaso es lo enviado menos lo recibido en todas sus recepciones: lo que no se escanea sigue En tránsito (X-13), y una recepción que deja algo pendiente exige una observación (RG-14; sin ella, rojo en la evaluación y 422 al confirmar). Cada recepción deja el traspaso en Recibido con diferencias si aún queda algo pendiente, o en Recibido si ya no queda nada; un traspaso con diferencias puede recibirse otra vez, las veces que haga falta, hasta completarse. Lo ya recibido no se recibe de nuevo ni se recibe más de lo enviado (X-12, rojo), y un traspaso cancelado no se recibe (X-14). Resolver lo que nunca llega queda fuera del MVP.

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
| P-01 | La inspección la registra el almacenista o el supervisor antes de entregar: fecha, resultado (Apto o No apto), observaciones y vigencia. Revisa etiquetas, costuras, cintas, herrajes y conectores. | PDF p.4, p.9 |
| P-02 | Qué artículos requieren inspección se define en el catálogo (CF-06). | PDF p.2 |
| P-03 | Cualquier almacenista puede marcar una pieza como No apta al ver un daño. Solo una inspección la regresa a Apto. | Propuesta |
| P-04 | Si vence la inspección de una pieza que está con un trabajador, aparece en la lista de revisión. | Propuesta |
| P-05 | Dar una pieza por perdida, o darla de baja definitiva, lo hace el supervisor. Es un movimiento a Baja y no se revierte. | PDF p.3 paso 9 |
| P-06 | Una pieza puede marcarse En mantenimiento o En calibración, con observación. Mientras tanto no se entrega y no cuenta como disponible. | Plática min 46–47 |
| P-07 | Un supervisor o un administrador puede ajustar la fecha hasta la que vale la inspección vigente de una pieza, con un motivo obligatorio. Requiere el permiso `piezas.ajustar_vigencia`. El ajuste no cambia el resultado ni la fecha de la inspección, y no regresa a Apta a una pieza No apta (P-03). Acortar la vigencia es libre; alargarla no puede pasar de la fecha de la inspección más la vigencia del artículo. Quien registró la inspección no puede ajustar la suya. Queda en el historial de la pieza con la fecha anterior, la nueva, el motivo y el usuario, y entra a la lista de revisión. | Idea del equipo |

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
| C-04 | Vale: muestra su detalle y si está íntegro. | PDF p.8 paso 6 |
| C-05 | Reportes de existencias, movimientos y adeudos, con filtros por almacén, fecha y trabajador. El de movimientos filtra además por artículo, tipo y usuario. El de adeudos es una consulta de personas: lo ven completo quien tiene `almacenes.todos` o `trabajadores.administrar` (RH); el resto, solo lo entregado por su almacén, y sin almacén nada. | PDF función 8; idea del equipo |
| C-06 | Búsqueda por texto: nombre de artículo, número de serie, nombre o número de trabajador. Los artículos son catálogo y se ven siempre; las piezas se limitan igual que en C-02 (AC-06). | Plática min 38 |
| C-07 | EPP entregado a un trabajador, con fechas y vales. Sirve como prueba ante la Comisión Mixta de Seguridad. | Plática min 31 |
| C-08 | Reporte de consumo: por artículo consumible y periodo, el total consumido, con el desglose por trabajador, de mayor a menor. Suma las entregas de consumibles (E-21) y resta las cancelaciones (K-02). Filtros: periodo, almacén, categoría, artículo y trabajador. Se descarga en CSV y no muestra costos (RG-12). Requiere `reportes.consumo`. | Plática min 35–36 |
| C-09 | Valor del inventario por almacén. Solo Compras. | Plática min 39 |
| C-10 | Lista de revisión: excepciones con su observación, para el supervisor. | Propuesta |
| C-11 | Rastrear una desaparición: el reporte de movimientos se filtra por usuario, artículo, almacén y periodo para ver quién tocó el equipo y cuándo, y el historial de la pieza (C-02) completa el rastro. Quien tiene `reportes.movimientos` ve el filtro de usuario siempre dentro de su alcance (AC-06): el almacenista, su almacén; quien tiene `almacenes.todos`, todos los almacenes y usuarios. Es informativo y no forma parte de la operación habitual. | Idea del equipo |
| C-12 | **Mis movimientos de hoy.** Cada usuario ve la lista de los vales que hizo en el día, con acceso a su detalle y a cancelarlos o rehacerlos (K-01, K-05). Es una consulta de apoyo y no forma parte de la operación habitual. | Idea del equipo |
| C-13 | **Seguimiento de piezas.** Para ver dónde está cada pieza, no solo cuántas hay: lista las piezas de un artículo (o de lo que se busque por artículo, serie, código o trabajador) y a cada una le pone dónde está o quién la tiene ("En resguardo de Juan Pérez", "En Kepler", "En tránsito a Contratistas"), su estado e inspección, desde cuándo está ahí y con qué vale. "Desde" es el movimiento que la dejó en su ubicación actual; con un trabajador, su entrega más reciente (una cancelación que se la regresa no cambia desde cuándo la tiene). Trae un resumen de conteos (total, en almacén, en resguardo, en tránsito y no aptas) y se descarga en CSV. Requiere `reportes.existencias` (de inicio, Administrador, Supervisor y Compras) y respeta el alcance de C-02 (AC-06): con `almacenes.todos`, todas; sin él, las de su almacén, las que tienen trabajadores (con `trabajadores.ver`) y el tránsito desde o hacia su almacén. El folio de un vale de otro almacén no se muestra. Solo lee: no mueve nada, y nunca muestra costos, CURP ni NSS (RG-12, RG-13). | Idea del equipo |

### 7.12 Índice de casos especiales

Dónde está resuelto cada caso que se sale de lo habitual.

| Caso | Qué pasa | Reglas | Prioridad |
|---|---|---|---|
| Equipo de alturas | Va por pieza, con inspección; no apto o sin inspección vigente no se entrega y nadie lo autoriza. | E-05, E-06, SM-04, P-01 a P-03 | P0 |
| Herramienta sin etiqueta | Se escanea el QR de su estante o se busca por nombre. | I-07, E-18 | P0 |
| Etiqueta de una pieza ilegible | Se busca por número de serie o se elige de la lista del trabajador. | E-18, V-14 | P0 |
| Equipo de alto valor | Va por pieza con número de serie; se sabe quién lo tiene. | I-02, C-02, C-03 | P0 |
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
| Supervisor ausente | Autoriza desde su celular; si no responde, se quita el renglón. | A-01, A-07 | P0 |
| Traspaso incompleto | Lo no recibido sigue En tránsito. | X-13 | P0 |
| Dos personas operan lo mismo | Gana la primera; la otra ve qué cambió. | RG-08, RG-09 | P0 |
| Se captura algo por error | Antes de confirmar se quita el renglón; después, se cancela el vale, o se cancela y se rehace con los mismos renglones. | K-01 a K-05, X-14 | P0 |
| Una inspección necesita otra fecha de vigencia | Un supervisor o un administrador la ajusta, con motivo; queda en el historial. | P-07 | P0 |
| Escaneo accidental | Es un borrador: se quita el renglón o se deshace en unos segundos. No cambia las existencias hasta confirmar. | E-28 | P0 |
| Cantidad inusualmente alta | El servidor lo marca y se pide confirmar la cantidad antes de continuar. | E-27 | P0 |
| Desaparece un equipo | El reporte de movimientos se filtra por usuario, artículo, almacén y periodo; el historial de la pieza lo completa. | C-02, C-11 | P0 |
| Un rol necesita ver o hacer algo más | El administrador le activa el permiso; aplica en la siguiente consulta. | AC-08 a AC-11 | P1 |
| Hay que mover a un almacenista de almacén | Un supervisor con `almacenes.asignar_personal` lo reasigna; aplica en la siguiente petición y el historial no cambia. | AC-12, AC-13 | P1 |
| En mantenimiento o calibración | No se entrega ni cuenta como disponible. | P-06, E-05 | P1 |
| Quedó instalado en planta | Se cierra sin devolución y sin pendiente. | V-09 | P2 |
| Pérdida o robo | Sigue como pendiente hasta que un supervisor lo dé por perdido. | V-13, P-05 | P2 |

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
| AC-06 | El alcance de cada usuario sale de su almacén asignado: opera y ve solo lo de ese almacén (existencias, piezas, movimientos, vales, autorizaciones, inspecciones y personal), salvo que su rol tenga `almacenes.todos`, que de inicio es solo el Administrador. Sin almacén asignado y sin `almacenes.todos`, el usuario no ve nada de ningún almacén. No hay subconjuntos de almacenes por usuario: ve el suyo o todos. De un traspaso, el origen y el destino ven lo que les toca. Una pieza es del almacén donde está; la que tiene un trabajador, del almacén de su última entrega (inspecciones, H11). | Plática min 33; decisión del usuario |
| AC-07 | Hay cuatro cosas que ningún rol puede hacer, porque no son permisos: editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale. | Propuesta |
| AC-08 | El administrador crea roles, activa o quita permisos y administra a los usuarios desde la pantalla. | Idea del equipo |
| AC-09 | Siempre existe al menos un usuario activo con `acceso.administrar`, y el rol Administrador no puede perderlo. | Propuesta |
| AC-10 | Un cambio de permisos aplica en la siguiente petición y queda en el registro de cambios. | Propuesta |
| AC-11 | Un rol con usuarios asignados no se inactiva ni se elimina hasta reasignarlos. | Propuesta |
| AC-12 | Asignar a un usuario a un almacén, o moverlo de uno a otro, requiere el permiso `almacenes.asignar_personal`, que de inicio tiene el Supervisor. Con él se asigna solo a quienes trabajan en un almacén (sin `almacenes.todos` y con algún permiso de almacén; RH no), sin acceso a roles, permisos ni altas de usuarios. Un supervisor de almacén solo ve al personal de su almacén y a quien no tiene almacén, y solo puede traerlo a su almacén o dejarlo sin almacén; mover personas entre almacenes distintos es de quien tiene `almacenes.todos`. Un usuario tiene un solo almacén; un almacén puede tener varios usuarios (RG-07). | Decisión del equipo |
| AC-13 | Un cambio de almacén aplica en la siguiente petición y queda en el registro de cambios, con el almacén anterior y el nuevo. Los vales y movimientos ya hechos conservan el almacén en el que se hicieron (RG-03). Un vale a medio capturar en el almacén anterior se rechaza al confirmar y su borrador se conserva. | Decisión del equipo |
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

### 8.2 Permisos y roles iniciales

A es Almacenista, S Supervisor (de almacén), C Compras y R Recursos Humanos. El Administrador tiene todos. Todo permiso de operación vale solo dentro del almacén asignado (AC-06); Compras está asignado a Kepler y RH no tiene almacén porque no opera inventario.

| Módulo | Permiso | Qué permite | Roles iniciales |
|---|---|---|---|
| Acceso | `acceso.administrar` | Roles, permisos y usuarios | Solo Administrador |
| Trabajadores | `trabajadores.ver` | Ficha básica: nombre, número, puesto, vigencia y resguardo | A, S, R |
| | `trabajadores.ver_datos_personales` | CURP y NSS | R |
| | `trabajadores.administrar` | Alta, reingreso, credencial y cancelar una baja | R |
| | `trabajadores.iniciar_baja` | Iniciar la baja | A, S, R |
| Catálogo | `catalogo.ver` | Categorías, artículos y piezas | A, S, C |
| | `catalogo.administrar` | Categorías, artículos, requisitos, límites e inactivar | S, C |
| | `catalogo.costos` | Ver y capturar costos | C |
| Inventario | `inventario.ver` | Existencias del almacén asignado (de todos, con `almacenes.todos`) | A, S, C |
| | `inventario.entradas` | Entradas e importación | C |
| Operación | `entregas.crear` | Entregar y pedir autorización | A, S |
| | `devoluciones.crear` | Recibir devoluciones | A, S |
| | `traspasos.operar` | Enviar y recibir traspasos entre almacenes (el almacenista no los opera) | S |
| | `no_adeudo.emitir` | Emitir el vale de no adeudo | A, S |
| | `vales.ver` | Consultar vales | A, S, C |
| | `vales.cancelar` | Cancelar los vales propios | A, S, C |
| | `vales.cancelar_todos` | Cancelar los de cualquiera de su almacén | S |
| Autorizaciones | `autorizaciones.resolver` | Autorizar o rechazar excedentes y entregas restringidas de su almacén | S |
| Piezas | `piezas.inspeccionar` | Inspeccionar y marcar No apta | A, S |
| | `piezas.ajustar_vigencia` | Ajustar la fecha de vigencia de una inspección (P-07) de piezas de su almacén | S |
| Reportes | `reportes.existencias` | Reporte de existencias y seguimiento de piezas (C-13) | S, C |
| | `reportes.movimientos` | Reporte de movimientos, con su filtro por usuario | S, C |
| | `reportes.adeudos` | Reporte de adeudos | S, R |
| | `reportes.consumo` | Reporte de consumo | S, C |
| Almacenes | `almacenes.todos` | Operar cualquier almacén y ver los movimientos de todos | Solo Administrador |
| | `almacenes.asignar_personal` | Asignar personal a su almacén o liberarlo, sin tocar roles ni permisos (AC-12); entre almacenes, solo con `almacenes.todos` | S |
| Etiquetas | `etiquetas.imprimir` | Hojas de QR | S, C, R |

Un permiso de acción incluye el de ver su módulo: quien puede entregar ve la ficha básica del trabajador y las existencias de su almacén.

El Almacenista conserva lo indispensable: entregar, devolver (lo que un trabajador regresa), consultar (trabajadores por nombre, número de empleado o QR, e inventario solo de su almacén), sus movimientos de hoy, ver las existencias de su almacén (`inventario.ver`, por eso no necesita ningún permiso de reportes), inspeccionar piezas, cancelar sus vales y la baja con no adeudo. Los traspasos entre almacenes (enviar y recibir) son del Supervisor del almacén y del Administrador (X-01). No tiene reportes, etiquetas, catálogo ni puestos.

Usuarios iniciales por almacén: cada almacén (Kepler, Contratistas, Midrex, HYL, Laminador y Minas) tiene su Supervisor y su Almacenista; Compras queda asignado a Kepler, donde carga el inventario; el Administrador y RH no llevan almacén. El Supervisor no da de alta trabajadores: eso es de RH (`trabajadores.administrar`).

### 8.3 Permisos que agregan las features

| Llega con | Permiso | Qué permite | Roles iniciales |
|---|---|---|---|
| FEAT-002 | `almacenes.administrar` | Abrir y cerrar almacenes de proyecto | S |
| FEAT-002 | `reportes.valor_inventario` | Valor del inventario | C |
| FEAT-004 | `inventario.minimos` | Fijar mínimos por almacén | C |
| Pospuesto | `piezas.dar_de_baja` | Dar una pieza por perdida o de baja definitiva | S |
| Pospuesto | `revision.ver` | Lista de revisión | S |
| Pospuesto | `tablero.ver` | Tablero general por almacén | Solo Administrador |

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
| P0 | Surtir EPP y una herramienta por escaneo | E-01 a E-06, E-15 a E-18, E-20 a E-22, E-24, E-25, E-27, E-28, F-02 (en pantalla), F-03, F-05, F-07 (con sesión), F-12 |
| P0 | Intentar una entrega que exceda el límite | L-01 a L-05, E-07, A-01 a A-07, F-04 |
| P0 | Traspaso entre almacenes | X-01 a X-04, X-06 a X-13, F-09 |
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
| P2 | Casos poco frecuentes | V-09, V-10, V-13, P-04, P-05, I-08 |
| P2 | Habilitaciones y carta de aceptación | E-08, F-01, T-04 |

En el MVP, las excepciones que resuelve el almacenista ya piden observación; lo que queda en P2 de RG-14 es la pantalla donde el supervisor las revisa.

---

## 10. Supuestos

Los supuestos con los que se escribieron estas reglas, y qué pasa si resultan distintos, están en [01-descubrimiento.md](../01-descubrimiento.md).

---

## 11. Historial

- **Sin publicar (6 oct 2026).** Sesiones por dispositivo: token de acceso de 15 minutos y token de renovación de 7 días, renovado con el uso hasta un tope de 30 días, con rotación y detección de reutilización (AC-14 a AC-24). Salir cierra solo ese dispositivo; cambiar la contraseña o el PIN, inactivar o reactivar cierra todas. Sustituye al token único de 12 horas.
- **Versión 7 (5 oct 2026).** Dotación por puesto construida en el servidor (FEAT-003): D-04 (la dotación no pasa del límite), el criterio de lo entregado en D-02 y los avisos E-09, E-10 y E-11. Sin permisos nuevos: puestos y dotación usan `catalogo.ver` y `catalogo.administrar`.
- **Versión 6 (5 oct 2026).** Alineación con el código construido, sin reglas nuevas. I-04: el costo unitario se captura en el catálogo y en la importación, no en la entrada. V-02: un vale con solo renglones V-02 sale en rojo y no se confirma. Prioridades (sección 9): E-27, E-28 y P-07 pasan a P0, y T-09 y F-11 quedan solo en P0.
- **Versión 5 (4 oct 2026).** Escanear solo agrega a un borrador y las existencias cambian al confirmar (E-28); aviso de cantidad inusual por artículo (E-27, sección 5.4); filtro por usuario en el reporte de movimientos y rastreo de desapariciones (C-05, C-11). La carta de aceptación queda pospuesta (T-04, F-01). Cancelar y rehacer (K-05), Mis movimientos de hoy (C-12) y ajuste de la vigencia de una inspección por un supervisor o administrador (P-07, permiso `piezas.ajustar_vigencia`). RG-07 aclara que cada almacenista usa su propia cuenta y dispositivo. Entran el reporte de consumo (C-08, permiso `reportes.consumo`) y la foto opcional del trabajador (T-09). Se agregan AC-12 y AC-13 y el permiso `almacenes.asignar_personal` para asignar personal a almacenes con FEAT-006.
- **Versión 4 (4 oct 2026).** El acceso pasa de perfiles fijos a roles con permisos por clave (sección 8, reglas AC-01 a AC-11). RG-07, RG-12, RG-13 y A-01 se redactan en términos de permisos. De los [escenarios](escenarios.md) salen dos aclaraciones: T-02 dice cómo se extiende un contrato, y V-14 y E-18 qué hacer con una etiqueta ilegible.
- **Versión 3 (4 oct 2026).** Se agrega el catálogo configurable (sección 5): categorías con plantilla de reglas, requisitos especiales por artículo, e inactivar y reactivar. Reglas nuevas E-19, E-26, I-09, X-09 y K-04. El daño en artículos por cantidad va a Baja (V-05). La cancelación de vales entra al MVP y se agrega el índice de casos especiales (7.12).
- **Versión 2 (4 oct 2026).** Se incorpora la plática del patrocinador: el vale de no adeudo lo emite el almacén, el contrato vencido bloquea, los costos solo los ve Compras, el supervisor queda para excepciones, se elimina el plazo de devolución y la firma admite papel.
- **Versión 1 (3 oct 2026).** Primera versión, a partir del PDF y las notas.
