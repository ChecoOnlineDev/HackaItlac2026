# Red de almacenes y su flujo

> **Estado:** propuesta ajustada con las decisiones del usuario (EPP en Contratistas, herramienta especializada en el proyecto, reactivar el mismo almacén, periodo por apertura para después del MVP). Escrita a partir de los recursos oficiales del reto. Describe cómo se da de alta cada almacén, cómo se surten entre sí, dónde se entrega el equipo de protección y la herramienta, y cómo se cierra un almacén de tercer nivel. Lo que las fuentes dicen con claridad va marcado como **Fuente**; lo que es mi interpretación, como **Supuesto**, y está reunido en la sección 10 para confirmarlo.
> **Documentos relacionados:** [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md) (administración de almacenes y tablero), [FEAT-002](../features/FEAT-002-cierre-de-almacen.md) (cierre), `reglas-de-negocio.md` (X-01 a X-14, CP-01 a CP-05, D-01 a D-06, SC-01 a SC-08) y `app-flow.md`.
> **Iteración 01 (aprobada el 8 de octubre de 2026, sin construir).** El [documento maestro de la iteración](../releases/iteration_01/README.md) cambia tres cosas de este documento: el **proyecto** pasa a ser una entidad propia, distinta del almacén de tercer nivel ([FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md), D-02); entre dos almacenes de tercer nivel se permite el **traslado lateral** que autoriza el supervisor del origen ([FEAT-015](../features/FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md), D-09); y el consumo cuenta para el **proyecto del trabajador**, no para el almacén que entrega (D-13). Lo marcado «Iteración 01» no está en el código.

## 1. Las dudas que este documento responde

1. ¿Cómo se dan de alta los almacenes, y en qué orden?
2. ¿Cómo surte Kepler a Contratistas, y Contratistas a los almacenes de tercer nivel?
3. ¿Los almacenes de tercer nivel se pueden surtir directo de Kepler?
4. ¿En qué almacén se entrega el equipo de protección personal (EPP): en Contratistas o en los de proyecto?

## 2. Respuestas cortas

| Duda | Respuesta |
|---|---|
| **Cadena de surtido** | **Kepler → Contratistas → almacenes de tercer nivel** (Midrex, HYL, Laminador y Minas). Es la ruta oficial. |
| **Kepler directo a un almacén de tercer nivel** | Las fuentes no lo describen como flujo normal. **Decisión: es una excepción y solo la hace el Administrador** (quien tiene `almacenes.todos`), con aviso amarillo y observación obligatoria (X-03). El supervisor no puede saltarse Contratistas. |
| **Entre dos almacenes de tercer nivel** (iteración 01) | **Se permite como traslado lateral** (por ejemplo, Midrex → HYL) y lo autoriza el supervisor del **almacén de origen**: si él lo envía, su envío es la autorización, con observación obligatoria; si lo envía otra persona con `traspasos.operar`, necesita su autorización. El destino lo recibe como cualquier traspaso (X-16 a X-21, FEAT-015). |
| **Dónde se entrega el EPP** | **Decisión: en Contratistas, de forma general.** Las fuentes dicen que ahí «se queda el equipo de seguridad», y Kepler también lo entrega al contratar (caso de prueba del reto). La **herramienta especializada** de un proyecto se entrega en el **almacén de ese proyecto**. **Contratistas es donde empieza la entrega a trabajadores**; los almacenes de tercer nivel no se surten de EPP de consumo (la semilla de datos lo refleja). **Iteración 01:** el EPP que Contratistas entrega a un trabajador de un proyecto de Midrex **cuenta para ese proyecto** y lo ve el supervisor de Midrex (D-13), y toda entrega de EPP pide la aprobación del supervisor del almacén **que entrega**, salvo autonomía (D-06, D-07, FEAT-014). |
| **Alta de almacenes** | Una persona con `almacenes.administrar` los crea. Orden: Kepler, luego Contratistas, luego cada almacén de tercer nivel. Se abre (o se reactiva) el almacén al empezar el mantenimiento y se cierra al terminar. **Iteración 01:** además, el Administrador da de alta el **proyecto** de ese mantenimiento antes que sus trabajadores (FEAT-013). |

## 3. La red

```
                  Proveedores  (entradas de proveedor)
                        │
                        ▼
              ┌──────────────────┐
              │  KEPLER (central)│   Recibe, resguarda, controla existencias
              └────────┬─────────┘   y surte a Contratistas.
                       │  traspaso
                       ▼
              ┌──────────────────┐
              │ CONTRATISTAS     │   Dentro de Mittal. Recibe de Kepler, resguarda,
              │ (subalmacén)     │   surte a las áreas y registra movimientos.
              └───┬────┬────┬────┘
        traspaso  │    │    │  traspaso
          ┌───────┘    │    └────────┐
          ▼            ▼             ▼
      ┌────────┐  ┌────────┐   ┌──────────┐  ┌───────┐
      │ MIDREX │  │  HYL   │   │LAMINADOR │  │ MINAS │   Almacenes de proyecto
      └────────┘  └────────┘   └──────────┘  └───────┘   (temporales)
                       │
                       ▼
                 Trabajadores   (entregas y devoluciones con vale)
```

**Fuente.** El reto describe: «Un almacén central en Kepler y un almacén en la colonia de Contratistas, dentro de Mittal. Este último surte a los almacenes de área de Midrex, HYL, Laminador y Minas.» (`docs/info_track/track-3-imhotep.md`, líneas 17 y 192-194). La infografía lo repite: «Contratistas surte a Midrex, HYL, Laminador y Minas».

| Almacén | Tipo en el sistema | Depende de | Duración |
|---|---|---|---|
| **Kepler** | `CENTRAL` | Nadie | Permanente |
| **Contratistas** | `SUBALMACEN` | Kepler | Permanente |
| **Midrex, HYL, Laminador, Minas** | `PROYECTO` | Contratistas | Temporal: los mantenimientos duran de uno a dos meses como máximo (plática) |

**Almacén de tercer nivel.** Es el almacén «pequeñito» que se arma en un área de la planta (Midrex, HYL, Laminador, Minas) para sus mantenimientos; en el sistema es de tipo `PROYECTO` y depende de Contratistas. Cada uno tiene **almacenistas asignados**, porque se trabaja las 24 horas (plática, min 32-33).

**«Proyecto» y «área» ya no son lo mismo (iteración 01, FEAT-013).** Hasta ahora este documento usaba «proyecto», «área» y «almacén de proyecto» como sinónimos. Con la iteración 01 se separan:

| Concepto | Qué es | Dónde vive |
|---|---|---|
| **Almacén de tercer nivel** | El **lugar**: un almacén tipo `PROYECTO` que se surte desde Contratistas y donde están las existencias. Se conserva (D-02). | Tabla `almacen` |
| **Proyecto** | El **contrato o mantenimiento** que usa ese almacén: clave, nombre, almacén al que pertenece, inicio y fin estimado, y estado (activo o cerrado). Se da de alta **antes** que sus trabajadores, y cada trabajador queda asignado a uno (PR-01, PR-11). | Tabla `proyecto` (módulo nuevo `proyectos`) |

Un almacén de tercer nivel puede tener **varios proyectos o ninguno**; lo normal es uno a la vez (D-01). Un proyecto también puede vivir en Contratistas o en Kepler para el personal general (por ejemplo, «Operación general Contratistas»; PR-01). Las existencias, los traspasos y la deuda siguen siendo **del almacén**; el consumo y el uso son **del proyecto** del trabajador (D-13, PR-14, T-3 del maestro).

## 4. Alta de los almacenes

### 4.1 Quién y con qué

Quien tiene `almacenes.administrar` (de inicio, solo el Administrador; ver FEAT-008, sección 6) abre **Administración → Almacenes → Nuevo almacén**. El permiso y la pantalla son los que describe FEAT-008. La interfaz solo muestra lo que el servidor evalúa.

### 4.2 Datos del alta

| Campo | Regla |
|---|---|
| **Clave** | Hasta 10 caracteres, en mayúsculas, única (`KEP`, `CON`, `MID`, `HYL`, `LAM`, `MIN`). Forma parte de los folios (`KEP-ENT-000123`), por eso **no se cambia** después de usarse. |
| **Nombre** | Único. |
| **Tipo** | `CENTRAL`, `SUBALMACEN` o `PROYECTO`. |
| **Depende de** | Obligatorio salvo para el central. Un `SUBALMACEN` depende del central; un `PROYECTO`, de Contratistas. Sin ciclos. |

### 4.3 Qué hace el servidor al guardar

En una sola transacción: crea el almacén, crea su **ubicación** (donde vivirán las existencias) y registra la acción en la auditoría. Si algo falla, no queda nada a medias.

### 4.4 Orden de puesta en marcha (base de producción vacía)

| Paso | Qué se hace | Quién |
|---|---|---|
| 1 | Dar de alta **Kepler** (`CENTRAL`). | Administrador |
| 2 | Dar de alta **Contratistas** (`SUBALMACEN`, depende de Kepler). | Administrador |
| 3 | Asignar a cada almacén su **personal**: un supervisor y los almacenistas. Un usuario operativo sin almacén asignado no ve nada (AC-06, RG-07). | Administrador |
| 4 | **Carga inicial de inventario** en Kepler: importación de Excel en modo Alta o entradas de proveedor (FEAT-007). Kepler es el **único punto de entrada** del inventario (EK-01, EK-02): de ahí todo se reparte por traspaso. | Compras |
| 5 | **Surtir Contratistas** con un traspaso desde Kepler (sección 5). | Supervisor de Kepler |
| 6 | Cuando arranca un mantenimiento, dar de alta (o reactivar) el almacén de **tercer nivel** (`MID`, `HYL`, `LAM` o `MIN`) dependiente de Contratistas y asignarle su personal. | Administrador |
| 6 bis | **Iteración 01:** dar de alta el **proyecto** del mantenimiento en ese almacén, con inicio y fin estimado (PR-01). Después RH da de alta a sus trabajadores con ese proyecto (PR-11). | Administrador; RH |
| 7 | **Surtir el almacén de tercer nivel** desde Contratistas (sección 6). | Supervisor de Contratistas |

Los pasos 1 y 2 pueden hacerse de una vez con el comando `uv run python -m app.mantenimiento sembrar-almacenes` (decidido en FEAT-008, 4.1.5): crea Kepler, Contratistas, Midrex, HYL, Laminador y Minas **solo si no existe ningún almacén**. En la práctica los proyectos se abren cuando hay un mantenimiento, así que los que todavía no operan se inactivan o simplemente no reciben personal ni surtido; los futuros se dan de alta desde la pantalla (paso 6). La carga inicial de inventario (paso 4) sigue siendo de Compras.

### 4.5 Activar, inactivar y reactivar

- **Inactivar** es el cierre: el almacén deja de operar pero **conserva su historial**. Solo con existencias en cero, sin traspasos en tránsito y sin almacenes dependientes activos (FEAT-008, 4.1.2).
- **Reactivar** devuelve el almacén a operar, por ejemplo cuando el mismo proyecto vuelve en el siguiente mantenimiento, con su clave y su historial. **Decisión: se reactiva el mismo almacén**; no se crea uno nuevo cada mantenimiento. Es más simple y mantiene la trazabilidad. Queda en la auditoría.
- **Periodo por apertura: lo resuelve el proyecto (iteración 01).** Reactivar el mismo almacén mezcla en su historial varios mantenimientos. Antes se había pospuesto un «ciclo por apertura» (sección 12.2); con FEAT-013 cada mantenimiento es un **proyecto** con sus fechas, y cada entrega guarda su proyecto (`vale.proyecto_id`), así que el reporte de cierre se pedirá por proyecto (maestro, sección 6). Mientras no se construya, se pide **por rango de fechas** (sección 11).
- **Aviso de almacén sin proyectos (iteración 01, PR-12).** Un almacén de tercer nivel activo sin ningún proyecto activo muestra «Sin proyectos activos: considera inactivarlo» en Almacenes y en el Inicio del Administrador. Es la **señal para inactivarlo**, pero el sistema **nunca** lo inactiva solo (D-03); Kepler y Contratistas no generan el aviso. Al revés, un almacén con proyectos activos no se puede inactivar: AL-03 gana el bloqueo `CON_PROYECTOS_ACTIVOS`.
- Un almacén inactivo **no recibe ni envía** movimientos ni solicitudes nuevas, pero sus reportes siguen disponibles.

## 5. Kepler surte a Contratistas

**Fuente.** «El almacén central, que es el de Kepler, se le surte todo y se le surte al subalmacén» (plática, min 32). El PDF define: «Registro de entregas, devoluciones y traspasos, con fecha, cantidad, almacén y usuario responsable», y un flujo «solicitud del área → surtido → vale o traspaso → recepción firmada → actualización de existencias» (línea 199).

### 5.1 Pasos (reglas X-01 a X-14)

| # | Quién | Qué hace | Qué pasa en el sistema |
|---|---|---|---|
| 1 | Supervisor de Kepler | **Trasladar** → elige el destino Contratistas y escanea o elige los artículos y cantidades. | Evalúa en el servidor: solo sale lo que hay en Kepler (X-02). Ruta habitual: sin aviso (X-03). |
| 2 | Sistema | Confirma la **salida** y genera un **folio con QR** (X-06). | Las existencias salen de Kepler y quedan **En tránsito**; no cuentan para ningún almacén (X-01). |
| 3 | Supervisor de Contratistas | **Recibir traspaso**: abre el QR o la lista de «por recibir» (X-10). | Solo el destino puede recibir. |
| 4 | Supervisor de Contratistas | Recibe **todo de una vez** o **renglón por renglón** escaneando (X-11). | Lo escaneado que no pertenece al traspaso es rojo (X-12). |
| 5 | Sistema | Confirma la **recepción**. | Las existencias entran a Contratistas. El que recibe queda como responsable de lo recibido (X-08). |
| 6 | — | Si falta algo, el traspaso queda **«Recibido con diferencias»**. | Lo no recibido sigue En tránsito y entra a revisión (X-13). |

Un traspaso en tránsito se puede **cancelar** desde el origen, con observación y solo antes de la recepción (X-14): la existencia regresa a Kepler.

**Quién opera.** **Enviar** el traspaso lo hace quien tiene `traspasos.operar`: de inicio el Supervisor del almacén y el Administrador; el almacenista no (X-01). **Recibir** lo hace quien tiene `traspasos.recibir`, permiso aparte que de inicio traen el Supervisor, el **Almacenista** y el Administrador (tabla 8.2 y AC-31; el texto de X-01 que decía que el Almacenista no lo trae estaba atrasado y la iteración 01 lo corrige). Por eso en los pasos 3 a 5 también puede recibir el almacenista del destino. Cada movimiento guarda origen y destino (X-07).

## 6. Contratistas surte a los almacenes de tercer nivel

**Fuente.** «Tenemos un proyecto en esas áreas y creamos un almacén pequeñito. De ese almacén hacemos un traslado. Le decimos al almacenista: te acabo de dar este listado de herramientas para que trabajes durante este mantenimiento. Tú eres el responsable de eso.» (plática, min 32-33).

El mecanismo es **el mismo traspaso de la sección 5**, con Contratistas como origen y el almacén de tercer nivel como destino. Cambia la intención:

- Se envía el **listado de herramientas y consumibles que ese mantenimiento va a usar**, no el inventario completo.
- El almacenista asignado al proyecto **queda responsable** de lo recibido durante el mantenimiento (X-08).
- Durante el proyecto pueden hacerse **traspasos adicionales** si falta algo. El aviso de mínimo (X-05) avisa cuando la salida deja al origen por debajo de su mínimo.
- Los consumibles **no regresan**: se registran como consumidos, para conservar el histórico de consumo (plática, min 31-32).

## 7. ¿Kepler directo a un proyecto?

**Lo que dicen las fuentes.** Describen la cadena Kepler → Contratistas → áreas. **No** describen un surtido directo de Kepler a un almacén de tercer nivel como camino normal.

**Lo que hacía el sistema antes (X-03).** Un destino que no es padre ni hijo del origen se permitía a cualquiera con aviso amarillo: «Otra ruta se permite con aviso». Ya no: la decisión de abajo está escrita en `reglas-de-negocio.md` (X-03) y en `api-contracts.md`; el código se ajusta en FEAT-008, etapa 1.

**Decisión.**
- El flujo normal es por Contratistas, porque ahí está el inventario y la responsabilidad del subalmacén.
- **Kepler → proyecto directo es una excepción y solo la hace el Administrador** (quien tiene `almacenes.todos`). El supervisor y el almacenista no pueden: si intentan una ruta que no es padre-hijo, el servidor la rechaza.
- La excepción lleva **aviso amarillo y observación obligatoria**, para dejar constancia de por qué se saltó Contratistas.
- Esto **cambia X-03**: antes otra ruta se permitía a cualquiera con aviso; ahora es «otra ruta solo la hace quien tiene `almacenes.todos` (el Administrador), con aviso y observación». Ya está actualizado en `reglas-de-negocio.md` (X-03 y su cómo-se-aplica). Para quien no puede, la evaluación sale en rojo y el servidor responde 403 `RUTA_SOLO_ADMINISTRADOR` ([api-contracts.md](../architecture/api-contracts.md), fila TRASPASO).
- Dos caminos cubren la falta de material **sin saltarse Contratistas**: Kepler → Contratistas y luego Contratistas → proyecto; o una **compra urgente** que Compras ingresa directo al almacén que la pidió (sección 8).

### 7.1 Ruta lateral entre almacenes de tercer nivel (iteración 01, FEAT-015, sin construir)

En la plática del 8 de octubre el track pidió traslados entre almacenes de **tercer nivel** «permitidos siempre y cuando autorice el supervisor» (D-09). Antes, lo que sobraba en Midrex y faltaba en HYL tenía que regresar a Contratistas y volver a salir. **X-03 cambia** así:

> «El destino es otro almacén activo. Rutas habituales: Kepler con Contratistas, y Contratistas con los almacenes de tercer nivel, en ambos sentidos. **Entre dos almacenes de tercer nivel** la ruta es lateral y la autoriza el supervisor del origen (X-16 a X-19). **Otra ruta** (por ejemplo, Kepler directo a un almacén de tercer nivel) solo la hace quien tiene `almacenes.todos`, con aviso amarillo y observación obligatoria; para quien no lo tiene, es rojo.»

| Ruta | Ejemplo | Quién y cómo | Reglas |
|---|---|---|---|
| Habitual (padre-hijo) | Kepler ↔ Contratistas ↔ Midrex | Quien tiene `traspasos.operar`, sin aviso | X-03 |
| **Lateral** (los dos de tipo `PROYECTO`, distintos y activos, compartan o no el padre) | Midrex → HYL | Si envía el supervisor del origen (`autorizaciones.resolver` en el origen, o el Administrador): amarillo, observación obligatoria y «Validó: él mismo (envío propio)», sin solicitud. Si envía otra persona con `traspasos.operar`: naranja, necesita una autorización TRASLADO del supervisor del origen (push, celular o PIN), que vence a los 15 minutos y se aprueba o rechaza completa | X-16 a X-19 |
| No habitual | Kepler → Midrex, Midrex → Kepler | Solo `almacenes.todos`, amarillo y observación; para los demás, rojo `RUTA_SOLO_ADMINISTRADOR` (sin cambio) | X-03, X-18 |

El destino recibe el traslado lateral como cualquier traspaso, con la etiqueta «Traslado desde Midrex» y un aviso push informativo; no lo rechaza: si no lo quiere, el origen lo cancela antes de la recepción (X-14, X-20). Si envía y recibe la misma persona (un supervisor con los dos almacenes en su conjunto), se pide observación y entra a revisión (X-21). El traslado lateral **no reemplaza** el surtido por Contratistas y no cambia el proyecto de nada: el consumo es del proyecto de la entrega (D-13). Tampoco hay traslados laterales sin conexión: la app de Android no envía traspasos (FEAT-020).

## 8. Compras urgentes: ¿a qué almacén llega lo comprado?

**Fuente.** «El supervisor hace una solicitud de compra de manera urgente, la recibe Compras, la compra, la ingresa al almacén y ya está disponible» (plática, min 45).

- La solicitud nace en el almacén de quien la pide (SC-01), por ejemplo en un almacén de tercer nivel.
- Compras la toma, la compra, y al **ingresarla** crea un vale de entrada (proveedor → almacén) en el **almacén que la pidió**. Es la única forma legítima de que un almacén de tercer nivel reciba material **directo de un proveedor**.
- Una solicitud **no es inventario**: no mueve existencias hasta que Compras la ingresa (SC-03).

## 9. ¿Dónde se entrega el EPP y la herramienta?

### 9.1 Lo que dicen las fuentes

| Fuente | Qué dice |
|---|---|
| Anotaciones de la exposición (`anotaciones-exposicion.md`, líneas 8-11) | «Una persona es contratada, se da de alta en el sistema y acude al **almacén general de Kepler** a solicitar equipo básico de protección personal: lentes, guantes, calzado, protección auditiva y respiratoria.» |
| Plática, min 5-6 | El trabajador pasa por RH, se le da de alta y luego va al almacén a pedir su equipo; se registra con su número de empleado y se genera el vale. |
| Plática, min 35 | «En el remanente de **Contratistas** se queda el **equipo de seguridad** y las herramientas, dependiendo del proyecto, se le dan a cada uno de los trabajadores.» |
| Plática, min 31-32 | La Comisión Mixta de Seguridad de la planta pide demostrar que se entregó el EPP: «esta persona entró tal día y le dimos su dotación». Por eso la entrega queda con vale y fecha. |
| Plática, min 32-33 | A los almacenes de tercer nivel se les manda un **listado de herramientas** para el mantenimiento. No se menciona el EPP. |
| Anotaciones (línea 8) | «Hay almacenes asociados a cada trabajador y un almacén central donde se entrega un equipo base.» |

### 9.2 Decisión: dónde se entrega cada cosa

| Qué | Dónde se entrega | Por qué |
|---|---|---|
| **EPP de dotación** (lentes, guantes, calzado, protección auditiva y respiratoria, camisola), tanto la primera entrega como la reposición | **Contratistas**, de forma general | Ahí «se queda el equipo de seguridad» (plática, min 35) y ahí está el personal de la planta. Kepler también puede entregarlo, como en el caso de prueba del reto, porque no hay una regla que lo impida. |
| **Equipo de alturas** (arnés, línea de vida) | **Contratistas o Kepler**, con vale personal e intransferible | Es pieza controlada; el reto lo trata como caso especial. |
| **Herramienta especializada** de un proyecto | **Almacén de ese proyecto** | Se surte para el mantenimiento y el almacenista asignado la entrega y la recibe. |
| **Consumibles** del proyecto | **Almacén de ese proyecto** | Se consumen ahí y no regresan. |

### 9.3 Cómo lo trata el sistema

El sistema **no ata el EPP a un almacén**. La entrega se hace en **el almacén del usuario que opera** (RG-07, AC-06) y el EPP sale **solo si ese almacén lo tiene en existencia**. La dotación sugerida sale del **puesto** del trabajador (D-01, D-02), no del almacén. Por eso:

- Si un almacén de tercer nivel tiene EPP en existencia, **puede entregarlo** sin cambios.
- Para que el EPP se entregue **solo** en Contratistas (y Kepler), basta con **no surtir EPP** a los almacenes de tercer nivel; no hace falta una regla nueva. Un almacén sin existencia de ese artículo no puede entregarlo.
- El vale queda con el almacén donde se entregó, y el historial del trabajador muestra cuándo y dónde recibió cada pieza.

**Iteración 01, sin construir (FEAT-013, FEAT-014, FEAT-018):**

- **El EPP entregado en Contratistas cuenta para el proyecto del trabajador (D-13, PR-14).** Cada entrega guarda el proyecto del trabajador (`vale.proyecto_id`), que sale de su asignación, no del almacén que entrega. Si Contratistas entrega EPP a un trabajador del proyecto de Midrex: el vale es de Contratistas (folio `CON-…`, bitácora y «Lo más usado» de Contratistas); el **consumo** cuenta para el proyecto de Midrex y lo ve el supervisor de Midrex en su Inicio («Uso por proyecto», TB-05, TB-06). En ninguna vista se cuenta dos veces.
- **La deuda sigue siendo con el almacén que entregó** (DU-02, T-3 del maestro): lo retornable que Contratistas entregó se le debe a Contratistas; el supervisor de Midrex solo ve «Tiene además N artículos de otros almacenes».
- **La aprobación del despacho es del almacén que entrega:** el EPP que sale de Contratistas lo aprueba un supervisor de Contratistas, salvo que el Administrador le haya dado autonomía al almacén o al almacenista (DE-01, DE-14).
- **El paquete de la app de Android de Contratistas** incluye a los trabajadores de los proyectos de sus almacenes hijos, porque Contratistas les entrega el EPP (maestro, sección 11 bis; OF-13).

## 10. Decisiones y pendientes

| # | Tema | Estado |
|---|---|---|
| 1 | **EPP al entrar y en reposición** | **Decidido:** se entrega en **Contratistas** de forma general; Kepler también puede entregarlo. |
| 2 | **Herramienta especializada** | **Decidido:** en el almacén del proyecto que la usa. El EPP no se surte a los proyectos. |
| 3 | **Kepler → proyecto directo** | **Decidido:** excepción, solo el **Administrador**, con aviso amarillo y observación obligatoria. |
| 4 | **Quién da de alta los almacenes** | **Decidido:** el **Administrador** da de alta, edita, inactiva y reactiva. El supervisor del proyecto ve su reporte de cierre. FEAT-002 y la tabla 8.3 se ajustaron. |
| 5 | **Reabrir un proyecto** | **Decidido:** se **reactiva el mismo almacén**. |
| 6 | **Quién recibe en un almacén de tercer nivel** con turnos de 24 horas | **Resuelto (7 oct 2026) y construido:** permiso `traspasos.recibir` separado de `traspasos.operar` (enviar). De inicio lo traen el Supervisor, el Almacenista y el Administrador (tabla 8.2, AC-31, `acceso/permisos.py` y los datos de prueba); se quita o se da desde Roles y permisos (sección 12.1, mejora 2). El texto de X-01 que decía que el Almacenista no lo trae estaba atrasado y se corrige en la iteración 01 (incongruencia 2 del maestro). Construido en el código (commit `ed7ce82`); falta comprobarlo en el entorno desplegado (lista de verificación de FEAT-015, escenario 8). |
| 7 | **Un trabajador que cambia de proyecto** | Lo que tiene en resguardo sigue siendo suyo (sección 11). **Iteración 01:** con FEAT-013 el cambio de proyecto termina una asignación y abre otra; su resguardo sigue atribuido al proyecto de la última entrega hasta que lo devuelva (PR-13, TB-06). |
| 8 | **Periodo por apertura** | **Resuelto por el proyecto (iteración 01, aprobado el 8 oct 2026):** cada mantenimiento es un proyecto con sus fechas y cada entrega guarda su proyecto; ya no hace falta el «ciclo» de la sección 12.2 (maestro, sección 6). |
| 9 | **Sembrar los almacenes iniciales** | **Decidido y construido:** comando `sembrar-almacenes`, solo si no existe ningún almacén (FEAT-008). |
| 10 | **Inactivar con usuarios asignados** | **Decidido:** bloquea hasta reasignarlos (`CON_USUARIOS`, AL-03). **Iteración 01:** cuenta a quienes tienen el almacén en su **conjunto**, no solo como activo, y se agrega el bloqueo `CON_PROYECTOS_ACTIVOS`. |
| 11 | **Traslado entre almacenes de tercer nivel** | **Decidido (8 oct 2026, D-09), sin construir:** ruta lateral que autoriza el supervisor del almacén de origen (sección 7.1; FEAT-015). |
| 12 | **Proyecto como entidad** | **Decidido (8 oct 2026, D-02), sin construir:** el proyecto es distinto del almacén de tercer nivel; se da de alta antes que sus trabajadores (sección 3; FEAT-013). |
| 13 | **Almacén de tercer nivel sin proyectos** | **Decidido (8 oct 2026, D-03), sin construir:** aviso «Sin proyectos activos: considera inactivarlo»; nunca se inactiva solo (sección 4.5; PR-12). |

> **Pendiente 6, resuelto.** La incongruencia entre las fuentes (el almacenista del proyecto responde por lo recibido) y X-01 (el traspaso solo lo hacía el Supervisor) se resolvió separando **recibir** de **enviar**: el almacenista recibe con `traspasos.recibir` y enviar sigue siendo de `traspasos.operar`. Ya está en el código.

## 11. Cierre de un almacén de tercer nivel

**Fuente.** «Cuando termine el mantenimiento, me vas a regresar esto» (plática, min 33); y «retorna toda la herramienta para el almacén que tenemos internamente» (min 49). Reglas CP-01 a CP-05.

| # | Quién | Qué hace | Regla |
|---|---|---|---|
| 1 | Supervisor del proyecto | **Devuelve el sobrante** por traspaso a Contratistas (y de ahí a Kepler si corresponde). | CP-02 |
| 2 | Supervisor | Registra los **faltantes**: lo que el sistema dice que hay y no aparece, con observación y a nombre del almacén. | CP-03 |
| 3 | Sistema | Genera el **reporte de cierre** por artículo: recibido, consumido, regresado, en resguardo de trabajadores (con nombre), cerrado sin devolución y faltantes. En el MVP el supervisor elige el **rango de fechas** del mantenimiento (desde la apertura o reapertura hasta hoy); así el reporte no mezcla mantenimientos anteriores del mismo almacén. | CP-04 |
| 4 | Administrador | **Inactiva** el almacén (existencias en cero y sin traspasos en tránsito). | AL-03 (FEAT-008) |

**Lo que sigue en manos de trabajadores no impide el cierre** (CP-05): queda como pendiente de cada uno y se devuelve en Contratistas o Kepler. Es el vale de no adeudo el que cierra al trabajador: «sin ese vale, no se le puede finiquitar en Recursos Humanos» (plática, min 4).

**Iteración 01, sin construir (FEAT-013).** Cerrar el **proyecto** y cerrar el **almacén** son dos acciones distintas:

1. Al terminar el mantenimiento, el Administrador **cierra el proyecto** con motivo: terminan las asignaciones de sus trabajadores; contratos, vales, existencias y traspasos no cambian, y el resguardo sigue como pendiente de cada uno (PR-04).
2. Si era el último proyecto activo del almacén de tercer nivel, aparece el aviso «Sin proyectos activos: considera inactivarlo» (PR-12). Es la señal para seguir con los pasos 1 a 4 de arriba y **inactivar el almacén**, que el sistema nunca hace solo.
3. Mientras el almacén tenga un proyecto activo, inactivarlo responde `CON_PROYECTOS_ACTIVOS` con la lista de proyectos (AL-03).
4. El reporte de cierre se pedirá por proyecto, con sus fechas, en lugar del rango manual (maestro, sección 6).

## 12. Mejoras a los traspasos

### 12.1 Entran al MVP

| # | Mejora | Qué hace | Por qué |
|---|---|---|---|
| 1 | **Surtido por lista** ([FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md); **construido en el código**, falta TR-10) | Al abrir un almacén de tercer nivel, el supervisor de Contratistas arma la **salida** del traspaso pegando o subiendo un Excel con artículos y cantidades, con la misma vista previa en tabla de la importación (FEAT-007); la recepción no cambia (X-10 a X-13), salvo las ayudas para listas largas. Está en `importacion/router_traspasos.py` (con `test_traspaso_lista.py`), `componentes/traspasos-lista/trasladar-con-lista.tsx` y `recibir-detalle.tsx` (commit `ed7ce82`); falta TR-10 (descargar la lista), que en parte cubre el PDF del vale de FEAT-017, y comprobarlo en el entorno desplegado (FEAT-015, escenarios 6 y 7). | La plática dice: «te acabo de dar este listado de herramientas». Capturar renglón por renglón es lento y la infraestructura ya existe. |
| 2 | **Recibir separado de enviar** | **Resuelta (aprobada el 7 oct 2026) y construida.** Un permiso aparte, `traspasos.recibir`, para **recibir** traspasos, que de inicio trae también el Almacenista y se ajusta desde Roles y permisos. Enviar sigue siendo de `traspasos.operar` (Supervisor). | El reto asigna almacenistas por proyecto con turnos de 24 horas y los hace responsables de lo recibido. Cambia X-01 (texto que se corrige en la iteración 01) y la sección 8 de permisos. |
| 3 | **«Devolver todo al cerrar»** | Arma el traspaso de regreso a Contratistas con las existencias del proyecto que sí regresan (herramienta y equipo; los consumibles gastados no). | Hace el cierre en un paso y alimenta el reporte de cierre. |
| 4 | **Kepler → proyecto solo por el Administrador** (**ya está en el código**: X-03 con `RUTA_SOLO_ADMINISTRADOR`) | La ruta que no es padre-hijo la hace únicamente quien tiene `almacenes.todos`, con aviso amarillo (X-03) y observación obligatoria. | Evita que se salten Contratistas por costumbre y deja constancia de la excepción. Cambia X-03. |

### 12.2 Quedan para después del MVP

| Mejora | Qué es | Por qué se pospone |
|---|---|---|
| ~~**Periodo por apertura (ciclos)**~~ | ~~Cada vez que un almacén de tercer nivel se reactiva abre un ciclo con su fecha de apertura y de cierre; pedía una tabla `almacen_ciclo` y ligar cada vale a su ciclo.~~ | **Resuelto por el proyecto (iteración 01, FEAT-013):** cada mantenimiento es un proyecto con sus fechas y cada entrega guarda su `proyecto_id`, así que ya no hace falta un ciclo por almacén (maestro, sección 6). |
| **Solicitud de surtido desde el proyecto** | El almacenista pide a Contratistas «me falta esto» y el supervisor la convierte en traspaso. | El flujo del reto es «solicitud del área → surtido → vale o traspaso»; hoy ese primer paso no existe. Es una segunda etapa. |
| **Aviso de traspaso sin recibir** | Si un traspaso lleva demasiado tiempo en tránsito, aparece en el tablero y en el menú de quien debía recibirlo. | Mientras está en tránsito, la existencia no cuenta para ningún almacén. Se resuelve mejor con el tablero de FEAT-008. |

### 12.3 Reglas que se mantienen

- **Ruta habitual:** Kepler ↔ Contratistas ↔ almacén de tercer nivel, en ambos sentidos. **Iteración 01:** entre dos almacenes de tercer nivel, la ruta lateral que autoriza el supervisor del origen (sección 7.1).
- **Un almacén inactivo no recibe ni envía.** Si hay un traspaso en tránsito hacia un almacén, no se puede inactivar (AL-03).
- **Cancelar solo antes de recibir**, desde el origen, con observación (X-14).
- **Diferencias al recibir:** «Recibido con diferencias» y revisión (X-13).
- **Piezas con serie por escaneo** (conservan estado e historial, X-04) y **consumibles por cantidad**.

## 13. Qué cambia o se agrega en el sistema

Estado según el código al 8 de octubre de 2026. «En el código» no quiere decir comprobado en el entorno desplegado: eso lo cierra la lista de verificación de traspasos de [FEAT-015](../features/FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md) (D-21).

| Pieza | Estado |
|---|---|
| Traspasos Kepler ↔ Contratistas ↔ almacenes de tercer nivel con salida y recepción | **Ya existe** |
| Aviso en una ruta no habitual (X-03) | **Ya existe** |
| Compras urgentes e ingreso al almacén que pide | **Ya existe** |
| Alta, edición, inactivar y reactivar almacenes | **Ya existe** (FEAT-008: `almacenes/router.py` y `/almacenes`) |
| Rechazo de almacén cerrado en vales y compras | **Ya existe** (AL-04 en la evaluación y la confirmación de todo vale, `movimientos/service.py`, y en las solicitudes de compra) |
| Reporte de cierre y faltantes | **Falta** (FEAT-002) |
| Traspaso fuera de ruta solo para el Administrador, con observación obligatoria | **Ya existe** (12.1, mejora 4): X-03 con `RUTA_SOLO_ADMINISTRADOR` |
| Comando `sembrar-almacenes` | **Ya existe** (FEAT-008; `app/mantenimiento.py`) |
| Permiso de recibir separado de enviar | **Ya existe en el código** (12.1, mejora 2; `traspasos.recibir`, también en el rol Almacenista); falta comprobarlo desplegado y corregir el texto de X-01 |
| Surtido por lista (Excel) y recepción para listas largas | **Ya existe en el código** (12.1, mejora 1; FEAT-009: `importacion/router_traspasos.py`, `trasladar-con-lista.tsx`, `recibir-detalle.tsx`); **falta TR-10** (descargar la lista) y comprobarlo desplegado |
| «Devolver todo al cerrar» | **Falta** (12.1, mejora 3) |
| Traslado lateral entre almacenes de tercer nivel | **Iteración 01, sin construir** (sección 7.1; FEAT-015) |
| Proyecto como entidad, proyecto en cada entrega y uso por proyecto | **Iteración 01, sin construir** (sección 3; FEAT-013) |
| Aviso de almacén sin proyectos y bloqueo `CON_PROYECTOS_ACTIVOS` | **Iteración 01, sin construir** (sección 4.5; PR-12, AL-03) |
| Periodo por apertura | **Resuelto por el proyecto** (iteración 01; 12.2) |
| Solicitud de surtido y aviso de traspaso sin recibir | **Después del MVP** (12.2) |

## 14. Documentos que se actualizan

**Hecho el 6 de octubre de 2026** con FEAT-008: `reglas-de-negocio.md` (X-03 y las reglas AL-*), `app-flow.md` (flujo 21, puesta en marcha y cierre), `guia-por-rol.md`, y los briefs FEAT-002 y FEAT-008 para que no se contradigan (quién abre y cierra almacenes). La sección 10, punto 6 (permiso de recibir separado de enviar) quedó resuelta y construida; falta corregir el texto de X-01 en las reglas, que dice que el Almacenista no trae `traspasos.recibir` (incongruencia 2 del maestro).

**Hecho el 8 de octubre de 2026** con la iteración 01 (sin construir): este documento (secciones 2, 3, 4.4, 4.5, 5.1, 7.1, 9.3, 10, 11, 12 y 13), `app-flow.md` y `ui-ux.md`. Siguen pendientes, en sus propios cambios: `reglas-de-negocio.md` (X-01, X-03, PR-*, X-16 a X-21), `data-model.md`, `api-contracts.md` y `mvp-scope.md`.
