# Red de almacenes y su flujo

> **Estado:** propuesta ajustada con las decisiones del usuario (EPP en Contratistas, herramienta especializada en el proyecto, reactivar el mismo almacén, periodo por apertura para después del MVP). Escrita a partir de los recursos oficiales del reto. Describe cómo se da de alta cada almacén, cómo se surten entre sí, dónde se entrega el equipo de protección y la herramienta, y cómo se cierra un almacén de proyecto. Lo que las fuentes dicen con claridad va marcado como **Fuente**; lo que es mi interpretación, como **Supuesto**, y está reunido en la sección 10 para confirmarlo.
> **Documentos relacionados:** [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md) (administración de almacenes y tablero), [FEAT-002](../features/FEAT-002-cierre-de-almacen.md) (cierre), `reglas-de-negocio.md` (X-01 a X-14, CP-01 a CP-05, D-01 a D-06, SC-01 a SC-08) y `app-flow.md`.

## 1. Las dudas que este documento responde

1. ¿Cómo se dan de alta los almacenes, y en qué orden?
2. ¿Cómo surte Kepler a Contratistas, y Contratistas a los almacenes de proyecto?
3. ¿Los almacenes de proyecto se pueden surtir directo de Kepler?
4. ¿En qué almacén se entrega el equipo de protección personal (EPP): en Contratistas o en los de proyecto?

## 2. Respuestas cortas

| Duda | Respuesta |
|---|---|
| **Cadena de surtido** | **Kepler → Contratistas → almacenes de proyecto** (Midrex, HYL, Laminador y Minas). Es la ruta oficial. |
| **Kepler directo a un proyecto** | Las fuentes no lo describen como flujo normal. **Decisión: es una excepción y solo la hace el Administrador** (quien tiene `almacenes.todos`), con aviso amarillo y observación obligatoria (X-03). El supervisor no puede saltarse Contratistas. |
| **Dónde se entrega el EPP** | **Decisión: en Contratistas, de forma general.** Las fuentes dicen que ahí «se queda el equipo de seguridad», y Kepler también lo entrega al contratar (caso de prueba del reto). La **herramienta especializada** de un proyecto se entrega en el **almacén de ese proyecto**. **Contratistas es donde empieza la entrega a trabajadores**; los almacenes de proyecto no se surten de EPP de consumo (la semilla de datos lo refleja). |
| **Alta de almacenes** | Una persona con `almacenes.administrar` los crea. Orden: Kepler, luego Contratistas, luego cada proyecto. Se abre el proyecto al empezar el mantenimiento y se cierra al terminar. |

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

«Proyecto» y «área» son lo mismo: un almacén «pequeñito» que se arma para el mantenimiento de un área de la planta. Cada uno tiene **almacenistas asignados**, porque se trabaja las 24 horas (plática, min 32-33).

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
| 6 | Cuando arranca un mantenimiento, dar de alta el almacén de **proyecto** (`MID`, `HYL`, `LAM` o `MIN`) dependiente de Contratistas y asignarle su personal. | Administrador |
| 7 | **Surtir el proyecto** desde Contratistas (sección 6). | Supervisor de Contratistas |

Los pasos 1 y 2 pueden hacerse de una vez con el comando `uv run python -m app.mantenimiento sembrar-almacenes` (decidido en FEAT-008, 4.1.5): crea Kepler, Contratistas, Midrex, HYL, Laminador y Minas **solo si no existe ningún almacén**. En la práctica los proyectos se abren cuando hay un mantenimiento, así que los que todavía no operan se inactivan o simplemente no reciben personal ni surtido; los futuros se dan de alta desde la pantalla (paso 6). La carga inicial de inventario (paso 4) sigue siendo de Compras.

### 4.5 Activar, inactivar y reactivar

- **Inactivar** es el cierre: el almacén deja de operar pero **conserva su historial**. Solo con existencias en cero, sin traspasos en tránsito y sin almacenes dependientes activos (FEAT-008, 4.1.2).
- **Reactivar** devuelve el almacén a operar, por ejemplo cuando el mismo proyecto vuelve en el siguiente mantenimiento, con su clave y su historial. **Decisión: se reactiva el mismo almacén**; no se crea uno nuevo cada mantenimiento. Es más simple y mantiene la trazabilidad. Queda en la auditoría.
- **Periodo por apertura (pospuesto, sección 12.2).** Reactivar el mismo almacén mezcla en su historial varios mantenimientos. Para el MVP el reporte de cierre se pide **por rango de fechas** (sección 11).
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

**Quién opera.** El traspaso lo hace **solo el Supervisor del almacén** (y el Administrador): el almacenista no (X-01). Cada movimiento guarda origen y destino (X-07).

## 6. Contratistas surte a los almacenes de proyecto

**Fuente.** «Tenemos un proyecto en esas áreas y creamos un almacén pequeñito. De ese almacén hacemos un traslado. Le decimos al almacenista: te acabo de dar este listado de herramientas para que trabajes durante este mantenimiento. Tú eres el responsable de eso.» (plática, min 32-33).

El mecanismo es **el mismo traspaso de la sección 5**, con Contratistas como origen y el almacén de proyecto como destino. Cambia la intención:

- Se envía el **listado de herramientas y consumibles que ese mantenimiento va a usar**, no el inventario completo.
- El almacenista asignado al proyecto **queda responsable** de lo recibido durante el mantenimiento (X-08).
- Durante el proyecto pueden hacerse **traspasos adicionales** si falta algo. El aviso de mínimo (X-05) avisa cuando la salida deja al origen por debajo de su mínimo.
- Los consumibles **no regresan**: se registran como consumidos, para conservar el histórico de consumo (plática, min 31-32).

## 7. ¿Kepler directo a un proyecto?

**Lo que dicen las fuentes.** Describen la cadena Kepler → Contratistas → áreas. **No** describen un surtido directo de Kepler a un almacén de proyecto como camino normal.

**Lo que hacía el sistema antes (X-03).** Un destino que no es padre ni hijo del origen se permitía a cualquiera con aviso amarillo: «Otra ruta se permite con aviso». Ya no: la decisión de abajo está escrita en `reglas-de-negocio.md` (X-03) y en `api-contracts.md`; el código se ajusta en FEAT-008, etapa 1.

**Decisión.**
- El flujo normal es por Contratistas, porque ahí está el inventario y la responsabilidad del subalmacén.
- **Kepler → proyecto directo es una excepción y solo la hace el Administrador** (quien tiene `almacenes.todos`). El supervisor y el almacenista no pueden: si intentan una ruta que no es padre-hijo, el servidor la rechaza.
- La excepción lleva **aviso amarillo y observación obligatoria**, para dejar constancia de por qué se saltó Contratistas.
- Esto **cambia X-03**: antes otra ruta se permitía a cualquiera con aviso; ahora es «otra ruta solo la hace quien tiene `almacenes.todos` (el Administrador), con aviso y observación». Ya está actualizado en `reglas-de-negocio.md` (X-03 y su cómo-se-aplica). Para quien no puede, la evaluación sale en rojo y el servidor responde 403 `RUTA_SOLO_ADMINISTRADOR` ([api-contracts.md](../architecture/api-contracts.md), fila TRASPASO).
- Dos caminos cubren la falta de material **sin saltarse Contratistas**: Kepler → Contratistas y luego Contratistas → proyecto; o una **compra urgente** que Compras ingresa directo al almacén que la pidió (sección 8).

## 8. Compras urgentes: ¿a qué almacén llega lo comprado?

**Fuente.** «El supervisor hace una solicitud de compra de manera urgente, la recibe Compras, la compra, la ingresa al almacén y ya está disponible» (plática, min 45).

- La solicitud nace en el almacén de quien la pide (SC-01), por ejemplo en un almacén de proyecto.
- Compras la toma, la compra, y al **ingresarla** crea un vale de entrada (proveedor → almacén) en el **almacén que la pidió**. Es la única forma legítima de que un almacén de proyecto reciba material **directo de un proveedor**.
- Una solicitud **no es inventario**: no mueve existencias hasta que Compras la ingresa (SC-03).

## 9. ¿Dónde se entrega el EPP y la herramienta?

### 9.1 Lo que dicen las fuentes

| Fuente | Qué dice |
|---|---|
| Anotaciones de la exposición (`anotaciones-exposicion.md`, líneas 8-11) | «Una persona es contratada, se da de alta en el sistema y acude al **almacén general de Kepler** a solicitar equipo básico de protección personal: lentes, guantes, calzado, protección auditiva y respiratoria.» |
| Plática, min 5-6 | El trabajador pasa por RH, se le da de alta y luego va al almacén a pedir su equipo; se registra con su número de empleado y se genera el vale. |
| Plática, min 35 | «En el remanente de **Contratistas** se queda el **equipo de seguridad** y las herramientas, dependiendo del proyecto, se le dan a cada uno de los trabajadores.» |
| Plática, min 31-32 | La Comisión Mixta de Seguridad de la planta pide demostrar que se entregó el EPP: «esta persona entró tal día y le dimos su dotación». Por eso la entrega queda con vale y fecha. |
| Plática, min 32-33 | A los almacenes de proyecto se les manda un **listado de herramientas** para el mantenimiento. No se menciona el EPP. |
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

- Si un almacén de proyecto tiene EPP en existencia, **puede entregarlo** sin cambios.
- Para que el EPP se entregue **solo** en Contratistas (y Kepler), basta con **no surtir EPP** a los almacenes de proyecto; no hace falta una regla nueva. Un almacén sin existencia de ese artículo no puede entregarlo.
- El vale queda con el almacén donde se entregó, y el historial del trabajador muestra cuándo y dónde recibió cada pieza.

## 10. Decisiones y pendientes

| # | Tema | Estado |
|---|---|---|
| 1 | **EPP al entrar y en reposición** | **Decidido:** se entrega en **Contratistas** de forma general; Kepler también puede entregarlo. |
| 2 | **Herramienta especializada** | **Decidido:** en el almacén del proyecto que la usa. El EPP no se surte a los proyectos. |
| 3 | **Kepler → proyecto directo** | **Decidido:** excepción, solo el **Administrador**, con aviso amarillo y observación obligatoria. |
| 4 | **Quién da de alta los almacenes** | **Decidido:** el **Administrador** da de alta, edita, inactiva y reactiva. El supervisor del proyecto ve su reporte de cierre. FEAT-002 y la tabla 8.3 se ajustaron. |
| 5 | **Reabrir un proyecto** | **Decidido:** se **reactiva el mismo almacén**. |
| 6 | **Quién recibe en un proyecto** con turnos de 24 horas | **Resuelto (7 oct 2026):** permiso `traspasos.recibir` separado de `traspasos.operar` (enviar); el Supervisor tiene los dos y al almacenista del proyecto se le puede dar el de recibir desde Roles y permisos (sección 12.1, mejora 2; X-01). Documentado, sin construir. |
| 7 | **Un trabajador que cambia de proyecto** | Lo que tiene en resguardo sigue siendo suyo (sección 11). |
| 8 | **Periodo por apertura** | **Decidido: después del MVP** (sección 12.2). |
| 9 | **Sembrar los almacenes iniciales** | **Decidido:** comando `sembrar-almacenes`, solo si no existe ningún almacén (FEAT-008). |
| 10 | **Inactivar con usuarios asignados** | **Decidido:** bloquea hasta reasignarlos (`CON_USUARIOS`, AL-03). |

> **Pendiente 6, a revisar con cuidado.** El reto dice que el Almacenista queda como responsable de lo recibido y que se asignan almacenistas por proyecto (turnos de 24 horas). Pero X-01 reserva el traspaso al Supervisor. Es una incongruencia entre las fuentes y la regla y conviene resolverla antes de construir el alta del proyecto.

## 11. Cierre de un almacén de proyecto

**Fuente.** «Cuando termine el mantenimiento, me vas a regresar esto» (plática, min 33); y «retorna toda la herramienta para el almacén que tenemos internamente» (min 49). Reglas CP-01 a CP-05.

| # | Quién | Qué hace | Regla |
|---|---|---|---|
| 1 | Supervisor del proyecto | **Devuelve el sobrante** por traspaso a Contratistas (y de ahí a Kepler si corresponde). | CP-02 |
| 2 | Supervisor | Registra los **faltantes**: lo que el sistema dice que hay y no aparece, con observación y a nombre del almacén. | CP-03 |
| 3 | Sistema | Genera el **reporte de cierre** por artículo: recibido, consumido, regresado, en resguardo de trabajadores (con nombre), cerrado sin devolución y faltantes. En el MVP el supervisor elige el **rango de fechas** del mantenimiento (desde la apertura o reapertura hasta hoy); así el reporte no mezcla mantenimientos anteriores del mismo almacén. | CP-04 |
| 4 | Administrador | **Inactiva** el almacén (existencias en cero y sin traspasos en tránsito). | AL-03 (FEAT-008) |

**Lo que sigue en manos de trabajadores no impide el cierre** (CP-05): queda como pendiente de cada uno y se devuelve en Contratistas o Kepler. Es el vale de no adeudo el que cierra al trabajador: «sin ese vale, no se le puede finiquitar en Recursos Humanos» (plática, min 4).

## 12. Mejoras a los traspasos

### 12.1 Entran al MVP

| # | Mejora | Qué hace | Por qué |
|---|---|---|---|
| 1 | **Surtido por lista** (se resuelve con [FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md), propuesta pendiente de aprobación) | Al abrir un proyecto, el supervisor de Contratistas arma la **salida** del traspaso pegando o subiendo un Excel con artículos y cantidades, con la misma vista previa en tabla de la importación (FEAT-007); la recepción no cambia (X-10 a X-13). | La plática dice: «te acabo de dar este listado de herramientas». Capturar renglón por renglón es lento y la infraestructura ya existe. |
| 2 | **Recibir separado de enviar** | **Resuelta (aprobada el 7 oct 2026; reglas al día, sin construir).** Un permiso aparte, `traspasos.recibir`, para **recibir** traspasos, que se puede dar al almacenista del proyecto desde Roles y permisos. Enviar sigue siendo de `traspasos.operar` (Supervisor). | El reto asigna almacenistas por proyecto con turnos de 24 horas y los hace responsables de lo recibido. Cambia X-01 y la sección 8 de permisos. |
| 3 | **«Devolver todo al cerrar»** | Arma el traspaso de regreso a Contratistas con las existencias del proyecto que sí regresan (herramienta y equipo; los consumibles gastados no). | Hace el cierre en un paso y alimenta el reporte de cierre. |
| 4 | **Kepler → proyecto solo por el Administrador** (**ya está en el código**: X-03 con `RUTA_SOLO_ADMINISTRADOR`) | La ruta que no es padre-hijo la hace únicamente quien tiene `almacenes.todos`, con aviso amarillo (X-03) y observación obligatoria. | Evita que se salten Contratistas por costumbre y deja constancia de la excepción. Cambia X-03. |

### 12.2 Quedan para después del MVP

| Mejora | Qué es | Por qué se pospone |
|---|---|---|
| **Periodo por apertura (ciclos)** | Cada vez que un proyecto se reactiva abre un **ciclo** con su fecha de apertura y de cierre. El reporte de cierre y los indicadores se calculan solo del ciclo actual. Pide una tabla nueva (por ejemplo `almacen_ciclo`) y que cada vale quede ligado a su ciclo. | Para el MVP basta el rango de fechas manual (sección 11). Decidido: se hace después. |
| **Solicitud de surtido desde el proyecto** | El almacenista pide a Contratistas «me falta esto» y el supervisor la convierte en traspaso. | El flujo del reto es «solicitud del área → surtido → vale o traspaso»; hoy ese primer paso no existe. Es una segunda etapa. |
| **Aviso de traspaso sin recibir** | Si un traspaso lleva demasiado tiempo en tránsito, aparece en el tablero y en el menú de quien debía recibirlo. | Mientras está en tránsito, la existencia no cuenta para ningún almacén. Se resuelve mejor con el tablero de FEAT-008. |

### 12.3 Reglas que se mantienen

- **Ruta habitual:** Kepler ↔ Contratistas ↔ proyecto, en ambos sentidos.
- **Un almacén inactivo no recibe ni envía.** Si hay un traspaso en tránsito hacia un almacén, no se puede inactivar (AL-03).
- **Cancelar solo antes de recibir**, desde el origen, con observación (X-14).
- **Diferencias al recibir:** «Recibido con diferencias» y revisión (X-13).
- **Piezas con serie por escaneo** (conservan estado e historial, X-04) y **consumibles por cantidad**.

## 13. Qué cambia o se agrega en el sistema

| Pieza | Estado |
|---|---|
| Traspasos Kepler ↔ Contratistas ↔ proyectos con salida y recepción | **Ya existe** |
| Aviso en una ruta no habitual (X-03) | **Ya existe** |
| Compras urgentes e ingreso al almacén que pide | **Ya existe** |
| Alta, edición, inactivar y reactivar almacenes | **Falta** (FEAT-008, etapas 1 y 2) |
| Rechazo de almacén cerrado en entregas, entradas y compras | **Falta** (hoy solo traspasos, usuarios e importación) |
| Reporte de cierre y faltantes | **Falta** (FEAT-002) |
| Traspaso fuera de ruta solo para el Administrador, con observación obligatoria | **Ya existe** (12.1, mejora 4): X-03 con `RUTA_SOLO_ADMINISTRADOR` |
| Comando `sembrar-almacenes` | **Falta** (FEAT-008, etapa 1) |
| Permiso de recibir separado de enviar | **Documentado, falta construirlo** (12.1, mejora 2; `traspasos.recibir`) |
| Surtido por lista (Excel) | **Falta** (12.1, mejora 1; [FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md), propuesta) |
| «Devolver todo al cerrar» | **Falta** (12.1, mejora 3) |
| Periodo por apertura, solicitud de surtido y aviso de traspaso sin recibir | **Después del MVP** (12.2) |

## 14. Documentos que se actualizan

**Hecho el 6 de octubre de 2026** con FEAT-008: `reglas-de-negocio.md` (X-03 y las reglas AL-*), `app-flow.md` (flujo 21, puesta en marcha y cierre), `guia-por-rol.md`, y los briefs FEAT-002 y FEAT-008 para que no se contradigan (quién abre y cierra almacenes). Sigue pendiente la sección 10, punto 6 (permiso de recibir separado de enviar): al decidirlo se actualizan X-01 y la sección 8 de las reglas.
