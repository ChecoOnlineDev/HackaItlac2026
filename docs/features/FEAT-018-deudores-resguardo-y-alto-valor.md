# FEAT-018: Deudores, resguardo por proyecto, consumo por trabajador y alto valor

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Es parte de la [iteración 01](../releases/iteration_01/README.md) (decisiones D-12 y D-17; puntos 6 y 7 de lo que pidió el track) y va en el paso 4 de su orden de construcción, junto con FEAT-017. Usa las reglas AV-01 a AV-05 y DU-01 a DU-09 (sección 4 del documento maestro). Cambia la sección 5.1 de las reglas (definiciones de categorías), SG-04 y SG-06 (alto valor por marca y costo, ya no por nombre), y C-05 (el reporte de adeudos pasa a la sección Deudores). Agrega la columna `categoria.alto_valor`, el parámetro `ALTO_VALOR_COSTO_MINIMO`, el permiso `deudores.ver` y los endpoints `GET /api/deudores`, `GET /api/deudores/resumen` y `GET /api/trabajadores/{id}/consumo`. Las decisiones que dependen del usuario están en «Decisiones abiertas».

## Problema u oportunidad

El track pidió dos cosas en la plática del 8 de octubre:

- **Punto 6.** «Es muy importante saber en todo momento la ubicación de todas las piezas, sobre todo las de alto valor.»
- **Punto 7.** Definir bien qué es EPP de dotación, EPP básico, herramienta eléctrica y equipo de alto valor. Una herramienta puede ser eléctrica y de alto valor; en ese caso cuenta solo como alto valor.

Hoy:

1. **El alto valor se decide por el nombre de la categoría.** `consulta/repository_seguimiento.py` compara contra `CATEGORIAS_ALTO_VALOR = ("Equipo de alto valor", "Equipo de alturas")`. Si alguien renombra la categoría, la tarjeta del Inicio y el filtro de Seguimiento dejan de contar sin avisar (incongruencia 3 del maestro). Y un minipulidor de 15,000 pesos en «Herramienta eléctrica» nunca cuenta como alto valor.
2. **No hay una vista de «quién le debe a mi almacén».** El reporte de adeudos (`/reportes/adeudos`) es una lista plana de un renglón por artículo: un trabajador con 12 cosas ocupa 12 renglones, no se filtra por proyecto ni por categoría, y no dice cuánto debe cada quien ni desde cuándo. Además, el servidor lo arma en memoria y lo pagina después (`consulta/service.py`, `_adeudos`), lo que no aguanta una planta con miles de trabajadores.
3. **Lo que no se devuelve no tiene vista por persona.** El consumo de guantes, lentes y tapones de un trabajador solo se ve en el reporte de consumo (C-08), por artículo. RH y el supervisor no ven en la ficha del trabajador cuánto EPP de dotación lleva en su contrato.
4. **Las pantallas de resguardo están dispersas.** «Quién tiene qué» vive en Seguimiento (dos pestañas, SG-01), en la ficha del artículo (SG-02) y en el reporte de adeudos (C-05), cada una con su alcance.

## Objetivo

Que cualquier supervisor sepa, en una pantalla, **quién le debe a su almacén, qué, desde cuándo y para qué proyecto**, con el alto valor siempre a la vista; que el alto valor se defina por una marca editable y por el costo, y nunca por un nombre; y que lo consumido por cada trabajador se vea por persona y por proyecto.

## Historia de usuario

Como supervisor de Midrex, quiero ver quién le debe a mi almacén, agrupado por trabajador, con lo de alto valor señalado, para recuperar el equipo antes de que termine el mantenimiento.

Como Administrador, quiero ver los deudores de todos los almacenes y un resumen por almacén y por proyecto, para saber dónde está el riesgo.

Como RH, quiero ver qué debe cada trabajador sin ver el inventario de los almacenes, para no finiquitar a quien aún tiene equipo.

Como supervisor, quiero ver cuánto EPP de dotación ha consumido un trabajador en su contrato y en qué proyecto, para detectar consumos fuera de lo normal.

Como Compras, quiero que un artículo caro cuente como alto valor aunque su categoría diga «Herramienta eléctrica», para que se vigile como tal.

Todavía no hay historias en `docs/stories/`: se escriben al empezar la construcción.

## Alcance incluido

### Reglas de alto valor y definición de categorías

| ID | Regla | Origen |
|---|---|---|
| AV-01 | **Definiciones.** **EPP básico:** EPP que se da una vez y se devuelve al terminar; retornable, por cantidad, límite de 1 en posesión (casco, respirador, peto, polainas). **EPP de dotación:** EPP que se gasta; consumible, por cantidad, con límite por periodo (guantes, lentes, tapones, filtros, camisola, calzado). **Herramienta eléctrica:** herramienta que funciona con corriente o batería; por pieza, retornable (minipulidor, reflector). **Equipo de alto valor:** herramienta o equipo caro o crítico; por pieza, retornable, límite de 1 en posesión (detector de gases, radio). Las otras tres categorías iniciales (Equipo de alturas, Herramienta manual, Consumibles de trabajo) no cambian. Reemplaza la tabla de la sección 5.1. | Track punto 7 |
| AV-02 | **Qué es alto valor.** Un artículo es de alto valor si su categoría tiene `alto_valor = true` **o** si su `costo_unitario` es igual o mayor que `ALTO_VALOR_COSTO_MINIMO` (10,000 por omisión; parámetro general de `.env`). Un artículo sin costo es de alto valor solo por su categoría. Se calcula **al leer**, nunca se guarda en el artículo: cambiar el tope o la marca aplica en la siguiente consulta, sin migración ni recálculo. | D-12 |
| AV-03 | **Alto valor gana sobre eléctrica.** Un artículo de alto valor cuenta **solo como alto valor** en los resúmenes por tipo (Deudores, tarjeta del Inicio), aunque su categoría sea «Herramienta eléctrica»: no se cuenta dos veces. Al crear o importar un artículo con costo igual o mayor que el tope, se **sugiere** la categoría «Equipo de alto valor» (amplía I-14) aunque la descripción diga eléctrica; si el archivo o el formulario ya trae otra categoría, esa manda y se avisa «Por su costo cuenta como alto valor». Un artículo de alto valor controlado por cantidad **se permite**: el catálogo avisa «Conviene controlarlo por pieza, con serie, para saber quién tiene cada uno» y no lo fuerza. | D-12; track punto 7 |
| AV-04 | **La marca se edita y no depende del nombre.** `categoria.alto_valor` se prende o apaga en Categorías con `catalogo.administrar` y queda en el registro de cambios (CF-15). Nace `true` en «Equipo de alto valor» y `false` en las demás. Reemplaza la comparación por nombre (`CATEGORIAS_ALTO_VALOR`). SG-04 y SG-06 se reescriben: la tarjeta «Alto valor fuera del almacén», el filtro `alto_valor` de Seguimiento y el aviso de baja cuentan lo que es de alto valor según AV-02 **más** lo que requiere inspección (`articulo.requiere_inspeccion`, el equipo de alturas), también sin leer el nombre de la categoría. | D-12; incongruencia 3 del maestro |
| AV-05 | **Decir «es alto valor» no revela el costo.** La API expone `alto_valor` como un booleano a quien ve el artículo; nunca expone el costo ni si la marca vino «por su costo» o «por su categoría», salvo a quien tiene `catalogo.costos`. Es una nota de RG-12: el booleano dice, como mucho, que el costo pasa del tope general, y eso se acepta. | RG-12; D-12 |

### Reglas de deudores, resguardo y consumo

| ID | Regla | Origen |
|---|---|---|
| DU-01 | **Sección Deudores.** Pantalla `/deudores`, primero computadora (D-20), con el permiso nuevo `deudores.ver` (de inicio Supervisor, Recursos Humanos y Administrador). «Deber» es tener en resguardo un artículo **retornable**: una pieza en su ubicación o una existencia mayor que cero de un artículo por cantidad. Los consumibles no cuentan (B-03). Lo que va en tránsito, lo que está en Baja y lo cerrado sin devolución (V-09) no es deuda. | D-17; B-02; B-03 |
| DU-02 | **A qué almacén y a qué proyecto se debe.** Una pieza se le debe al almacén del vale de **su entrega más reciente** (AC-06) y al proyecto de ese vale (`vale.proyecto_id`, FEAT-013; «Sin proyecto» si no tiene, PR-10). Un artículo por cantidad, igual, por la entrega más reciente de ese artículo a ese trabajador (como SG-01 y C-05). «Desde» es la fecha de esa entrega; una cancelación que le regresa algo no cambia esa fecha. | D-17; AC-06; SG-01 |
| DU-03 | **Alcance.** Con `almacenes.todos`, todos los almacenes. Sin él, solo lo que se le debe a los almacenes de su conjunto (AC-36; en el flujo normal, su único almacén); de lo que el trabajador debe a otros almacenes solo se dice cuántas cosas son, sin artículo, folio ni almacén («Tiene además 3 artículos de otros almacenes»). Con `trabajadores.administrar` (RH), todos los trabajadores y todas sus deudas, como C-05: la deuda es de la persona; RH no gana por esto acceso a existencias, vales ni Seguimiento. Sin almacén ni ninguno de esos dos permisos, nada. | D-17; C-05; AC-06 |
| DU-04 | **Vista por trabajador.** Un renglón por trabajador con deuda: nombre y número, proyecto(s) de lo que debe, vigencia, cuántas piezas y cuántas unidades debe, la deuda más antigua («desde el 2 sep, hace 36 días»), si tiene algo de alto valor (insignia con el número) y, si no es vigente (dado de baja, baja en proceso o contrato vencido), el aviso de SG-06 extendido a toda su deuda. Orden por omisión: primero los no vigentes con alto valor, luego por deuda más antigua. | D-17; SG-06 |
| DU-05 | **Lo que debe un trabajador.** Al abrir un renglón, la lista de lo que tiene: artículo con marca, pieza y serie (o «Serie pendiente»), cantidad, desde cuándo, folio del vale de entrega (enlace al detalle), proyecto para el que se solicitó, almacén al que se le debe, y la insignia «Alto valor» o «Requiere inspección». Tocar una pieza abre su ficha con su línea de tiempo (SG-03). | D-17; SG-03 |
| DU-06 | **Filtros.** Almacén (dentro del alcance), proyecto, categoría (con la opción «Alto valor», que usa AV-02 y AV-03), vigencia (vigentes, no vigentes, todos), antigüedad («debe algo desde hace más de N días»: 7, 30, 90 o un número) y texto (nombre, número de empleado, código de credencial, artículo, código o serie), con espera de 300 ms (D-18). Paginación en el servidor por trabajador (`pagina`, `tamano`). Un filtro fuera del alcance no devuelve nada y no es error. | D-17; D-18 |
| DU-07 | **Resumen general.** `GET /api/deudores/resumen`: por almacén y por proyecto, cuántos trabajadores deben, cuántas piezas, cuántas unidades, cuántas cosas de alto valor están fuera y cuántos deudores no son vigentes. Mismo alcance que DU-03 y mismos filtros que DU-06. Se descarga en CSV. Sin costos. | D-17 |
| DU-08 | **Consumo por trabajador.** `GET /api/trabajadores/{id}/consumo`: por artículo **consumible**, la cantidad entregada en el periodo, separada por proyecto, neta de cancelaciones (como C-08). Periodo por omisión: desde el inicio de su contrato vigente (o del último, si no es vigente) hasta hoy. Se ve en una pestaña «Consumo» de la ficha del trabajador y al abrir un deudor. Con `reportes.valor_inventario`, solo el total en pesos del periodo y por proyecto, nunca por artículo ni el costo unitario. El resumen general de consumo por proyecto y por almacén reutiliza el reporte de consumo (C-08) y el uso por proyecto del Inicio del supervisor (TB-05). | D-05; D-13; C-08 |
| DU-09 | **Ubicación de todo en todo momento.** Deudores, Seguimiento (C-13) y Bitácora (FEAT-017) se enlazan entre sí: de un deudor a cada pieza y a cada vale; de una pieza (en su ficha o en Seguimiento) a quién la tiene en Deudores y a su línea de tiempo (SG-03); de un vale en la bitácora a sus piezas. El reporte de adeudos (`/reportes/adeudos`) se retira como pantalla y redirige a `/deudores`; Seguimiento se conserva como la vista por pieza y por artículo («¿dónde está esto?»), y Deudores es la vista por persona («¿quién debe?»). | Track punto 6; D-16; D-17 |

### A. Alto valor (AV-01 a AV-05)

**Acción por acción:**

1. **Ver las categorías.** En Catálogo > Categorías, cada categoría muestra su insignia «Alto valor» si la tiene prendida, junto al tipo y el resumen de su plantilla. La lista de las siete iniciales lleva la definición corta de AV-01 como línea de apoyo («Se gasta; tiene límite por periodo»).
2. **Prender o apagar la marca (AV-04).** En el formulario de la categoría, un interruptor «Es de alto valor» con la ayuda «Sus artículos se vigilan en Deudores, en Seguimiento y en el Inicio aunque cuesten poco». Pide `catalogo.administrar`; guardar deja `categoria.editar` en el registro de cambios con el valor anterior y el nuevo. Aplica en la siguiente consulta. No cambia el control, el retorno ni la plantilla de los artículos.
3. **Ver si un artículo es de alto valor.** La ficha del artículo, Seguimiento, Deudores, el detalle del vale y el renglón de la entrega muestran la insignia «Alto valor» (icono y texto, no un color del semáforo). Quien tiene `catalogo.costos` ve además por qué: «Por su categoría» o «Por su costo (10,000 o más)». Los demás solo ven la insignia (AV-05).
4. **Crear un artículo con costo alto (AV-03).** En la ficha de alta del catálogo, quien tiene `catalogo.costos` y captura un costo igual o mayor que el tope ve, junto a la categoría: «Por su costo cuenta como alto valor. ¿Lo pones en «Equipo de alto valor»?» con el botón «Cambiar categoría». No se cambia solo.
5. **Importar con costo alto (AV-03).** En la importación en modo Alta, una fila de artículo nuevo **sin** categoría en el archivo y con costo igual o mayor que el tope recibe la sugerencia «Equipo de alto valor», con el motivo «Su costo es de 10,000 o más», aunque el diccionario de I-14 hubiera sugerido «Herramienta eléctrica». La sugerencia, como siempre, no se aplica sola. Si el archivo trae categoría, manda y la fila solo avisa en amarillo «Por su costo cuenta como alto valor». Sin `catalogo.costos` la columna de costo se ignora (I-04) y la sugerencia por costo no existe.
6. **Alto valor por cantidad (AV-03).** Si una categoría con la marca, o un artículo por su costo, es de control por cantidad, la ficha del artículo avisa «Conviene controlarlo por pieza, con serie, para saber quién tiene cada uno». No bloquea nada. En Deudores y en la tarjeta del Inicio, sus unidades cuentan como alto valor fuera.
7. **Tarjeta del Inicio y Seguimiento (AV-04).** «Alto valor fuera del almacén» (`alto_valor_fuera`) cuenta piezas y unidades de alto valor (AV-02) o que requieren inspección, en manos de un trabajador, dentro del alcance; se sigue viendo solo con `resguardo.ver`. El filtro `alto_valor=true` de `GET /api/seguimiento/piezas` usa el mismo criterio. El chip de la pantalla dice «Alto valor y alturas».

**Cómo se calcula en el servidor.** Una sola expresión, en `catalogo`, que los demás módulos usan al leer: `categoria.alto_valor OR (articulo.costo_unitario IS NOT NULL AND articulo.costo_unitario >= :tope)`. Para «alto valor y alturas» se le suma `OR articulo.requiere_inspeccion`. Ninguna consulta lee `categoria.nombre` para decidir.

### B. Deudores (DU-01 a DU-07)

**Pantalla.** `/deudores`, entrada propia en el menú (grupo Supervisión), con dos pestañas: **Por trabajador** (por omisión) y **Resumen**. Primero computadora: tabla a todo el ancho; en celular, tarjetas.

**Acción por acción:**

1. **Abrir Deudores.** El supervisor de Midrex ve, sin elegir nada, a quienes le deben a Midrex. Arriba, cuatro tarjetas que también filtran al tocarlas: «Trabajadores con adeudo», «Alto valor fuera», «No vigentes con adeudo» y «Deben desde hace más de 30 días». Debajo, la búsqueda a la vista y «Filtros».
2. **Leer un renglón (DU-04).** Columnas: Trabajador (nombre, número y foto pequeña) · Proyecto · Vigencia (insignia) · Debe (por ejemplo «2 piezas · 5 unidades») · Desde (la más antigua) · Alto valor (número con insignia, o «—») · Aviso. Un trabajador no vigente lleva la banda amarilla de SG-06: «Contrato terminado el 30/09/2026. Hay que recuperar lo que tiene o renovar su contrato». Si también debe a otros almacenes, una línea de apoyo: «Tiene además 3 artículos de otros almacenes» (DU-03).
3. **Abrir un trabajador (DU-05).** Una hoja lateral en computadora (página completa en celular) con su ficha breve, dos pestañas, **Lo que tiene** y **Consumo** (DU-08), y los botones «Ver ficha del trabajador» y, con `devoluciones.crear` en ese almacén, «Recibir devolución», que abre Devolver con el trabajador ya identificado.
4. **Filtrar (DU-06).** En la hoja «Filtros»: almacén (solo si su alcance tiene más de uno), proyecto (los de sus almacenes, más «Sin proyecto»), categoría (con «Alto valor» primero), vigencia y antigüedad. Los filtros van en la dirección (se comparten y sobreviven a una recarga) y cada uno es un chip que se quita con un toque.
5. **Ver el resumen (DU-07).** Pestaña Resumen: una tabla por almacén y otra por proyecto, con trabajadores con adeudo, piezas, unidades, alto valor fuera y no vigentes; cada número es un enlace a la pestaña Por trabajador ya filtrada. «Descargar CSV» baja las dos tablas.
6. **Descargar.** En la pestaña Por trabajador, «Descargar CSV» baja un renglón por cosa debida (como el CSV de adeudos de hoy) con los filtros aplicados.

**Forma de la respuesta.** `GET /api/deudores` devuelve `{elementos, total, sin_registros, mensaje, resumen}`; `resumen` son los números de las cuatro tarjetas con los filtros de texto, almacén y proyecto, sin los de vigencia ni antigüedad (para poder cambiar entre tarjetas). Cada elemento:

```json
{
  "trabajador": {"id": "…", "numero_empleado": "E-000123", "nombre": "Juan Pérez", "tiene_foto": true},
  "vigente": false,
  "aviso": "Contrato terminado el 30/09/2026. Hay que recuperar lo que tiene o renovar su contrato.",
  "proyectos": [{"id": "…", "nombre": "Paro mayor Midrex 2026"}],
  "piezas": 2, "unidades": 5, "alto_valor": 1,
  "desde": "2026-09-02T14:10:00Z",
  "otros_almacenes": 3,
  "renglones": null
}
```

Con `trabajador_id=…` responde el mismo elemento de ese trabajador con `renglones` llenos: `{articulo {id, codigo, nombre, marca}, pieza {id, codigo, numero_serie, serie_pendiente}, cantidad, desde, vale {id, folio}, proyecto {id, nombre}, almacen {id, clave, nombre}, alto_valor, requiere_inspeccion}`. `vale.id` es nulo cuando el vale queda fuera del alcance del usuario (RH ve el folio como texto, sin enlace, como en C-05). Así el detalle no necesita un endpoint aparte.

**Paginación.** El servidor agrupa y pagina **en la consulta** (por trabajador), no en memoria. Las piezas y las existencias por cantidad se unen a su entrega más reciente con una tabla derivada con `row_number()`, como `repository_seguimiento.py` y `repository_cantidad.py`.

### C. Consumo por trabajador (DU-08)

**Acción por acción:**

1. **Abrir la pestaña Consumo** en la ficha del trabajador o en su hoja de Deudores. El periodo es, por omisión, «Desde el inicio de su contrato (01/08/2026)»; se cambia con el selector de rango de los reportes.
2. **Leer.** Una tabla por artículo consumible: artículo, unidad, cantidad en el periodo y, debajo de cada uno, el desglose por proyecto («Paro mayor Midrex: 12 · Sin proyecto: 2»). Si el trabajador tiene dotación (D-02), una columna «Recomendado» con lo de su puesto, solo como referencia.
3. **Valor.** Con `reportes.valor_inventario`, una línea al pie: «Valor de lo consumido en el periodo: $3,480.00», y una por proyecto; nunca por artículo.
4. **Resumen general.** Para ver el consumo de todo un proyecto o almacén, el enlace «Ver consumo del proyecto» abre el reporte de consumo (C-08) filtrado por ese proyecto, y el Inicio del supervisor ya trae el uso por proyecto (TB-05).

**Datos.** `GET /api/trabajadores/{id}/consumo?desde=&hasta=` exige `trabajadores.ver` (como `GET /api/trabajadores/{id}/dotacion`), y la cantidad cuenta lo entregado por **todos** los almacenes, como D-02, porque es el historial de la persona. Responde `{periodo {desde, hasta, origen}, elementos: [{articulo {id, codigo, nombre}, unidad, cantidad, recomendado, por_proyecto: [{proyecto {id, nombre} | null, cantidad}]}], valor_total, valor_por_proyecto}`; los dos últimos solo con `reportes.valor_inventario`. Suma los movimientos a CONSUMIDO con ese trabajador y resta los que salen de CONSUMIDO (cancelaciones y, cuando exista, V-10). El reporte de consumo (C-08) gana el filtro `proyecto_id`.

### D. Qué queda de las pantallas actuales (DU-09)

| Pantalla | Qué pasa | Por qué |
|---|---|---|
| `/reportes/adeudos` (C-05) | Se retira; redirige a `/deudores` | Deudores es la misma información, agrupada por trabajador, con filtros y alto valor |
| `GET /api/reportes/adeudos` | Se conserva sin cambios, con `reportes.adeudos` | Compatibilidad del CSV; se retira cuando ningún rol lo use (Decisiones abiertas) |
| `/seguimiento` (C-13, SG-01) | Se conserva | Es la vista por pieza y por artículo; el almacenista la usa con `resguardo.ver` y no tiene Deudores |
| «Quién lo tiene» de la ficha del artículo (SG-02) | Se conserva | Responde «¿quién tiene este artículo?» desde el catálogo |
| Tarjeta «Alto valor fuera del almacén» (SG-04) | Se conserva con el criterio nuevo (AV-04) | Abre Seguimiento filtrado; agrega «Ver deudores de alto valor» |
| Ficha del trabajador | Gana la pestaña «Consumo» | DU-08 |

**Enlaces (DU-09).** En la ficha de una pieza en resguardo: «Lo tiene Juan Pérez · Ver lo que debe» (abre su hoja en Deudores, si se tiene `deudores.ver`). En Seguimiento, la columna «Dónde está» enlaza al trabajador en Deudores. En el detalle de un vale de entrega (FEAT-017), cada pieza enlaza a su línea de tiempo. En Deudores, cada folio enlaza al vale y cada pieza a su ficha.

### Consideraciones

- **Solo lee.** Deudores, el resumen y el consumo viven en `consulta` y nunca escriben. La única escritura nueva es la marca `categoria.alto_valor`, en `catalogo`.
- **El flujo normal manda en el diseño (D-01).** Un supervisor con un almacén no ve el filtro de almacén ni la columna; un trabajador con un proyecto ve su proyecto como texto, no como lista.
- **El proyecto es del consumo; la deuda es del almacén que entregó (D-13, DU-02).** Una entrega de Contratistas a un trabajador del proyecto de Midrex se le **debe** a Contratistas: sale en los Deudores de Contratistas, y el supervisor de Midrex solo la ve como «Tiene además 1 artículo de otros almacenes» (DU-03). En cambio, lo **consumido** cuenta para el proyecto de Midrex y el supervisor de Midrex lo ve en el consumo del trabajador (DU-08) y en el uso por proyecto (TB-05). Ver Decisiones abiertas, punto 7.
- **El aviso de no vigente es solo informativo.** No bloquea nada (SG-06). Las devoluciones nunca se bloquean (SM-05).
- **El tope es un parámetro general.** `ALTO_VALOR_COSTO_MINIMO` vive en `.env` (sección 5.4, «los parámetros generales son valores fijos de configuración»): cambiarlo pide reiniciar la aplicación, y aplica en la siguiente consulta, sin migración.

### Casos límite

| # | Situación | Qué pasa | Reglas |
|---|---|---|---|
| 1 | **Trabajador con piezas de dos almacenes** (un arnés de Contratistas y un detector de Midrex). | El supervisor de Midrex lo ve con el detector y la línea «Tiene además 1 artículo de otros almacenes»; el de Contratistas, al revés. El Administrador y RH ven los dos con su almacén. | DU-02, DU-03 |
| 2 | **Trabajador dado de baja con un detector de gases.** | Sale primero en la lista (no vigente con alto valor), con la banda de SG-06 y la tarjeta «No vigentes con adeudo» lo cuenta. RH lo ve igual y no emite el no adeudo hasta que lo devuelva (B-04, B-09). | DU-04, SG-06 |
| 3 | **Pieza reportada perdida** (V-13). | Sigue como deuda del trabajador hasta que la devuelva o un supervisor la dé por perdida (P-05, pospuesta). Cuando exista el registro de pérdida, el renglón dirá «Reportada como perdida el …»; mientras tanto se ve como cualquier deuda. Al darla por perdida (movimiento a Baja) deja de ser deuda. | DU-01, V-13, P-05 |
| 4 | **Devolución en otro almacén** (V-07): se entregó en Contratistas y se devuelve en Midrex. | Al devolverse, la pieza deja de ser deuda: no se le debe a nadie. Si era una cantidad y devuelve solo una parte, lo que queda se le sigue debiendo al almacén de la entrega más reciente (Contratistas). | DU-02, V-07 |
| 5 | **Entrega cancelada** (K-02). | Lo entregado regresa al almacén y deja de ser deuda. Si el trabajador tenía otra entrega anterior del mismo artículo por cantidad, «desde» vuelve a ser esa: la cancelación no cuenta como entrega. | DU-02, K-02 |
| 6 | **Trabajador en dos proyectos** (caso especial, PR-09). | Cada cosa debida lleva su proyecto; el renglón lista los dos. Filtrar por un proyecto deja al trabajador con solo lo de ese proyecto y cuenta solo eso. | DU-02, DU-06 |
| 7 | **Consumibles devueltos** (V-10, pospuesta). | No son deuda nunca (B-03). Mientras V-10 no exista, el consumo no se reduce por sobrantes; cuando exista, DU-08 los resta igual que C-08. | DU-01, DU-08 |
| 8 | **Supervisor con varios almacenes** (caso especial, AC-36). | Ve los deudores de todo su conjunto, no solo del almacén activo, con el filtro y la columna de almacén. Lo que se le debe a dos de sus almacenes no cuenta como «otros almacenes». | DU-03 |
| 9 | **RH sin almacén.** | Ve todos los trabajadores con deuda y todas sus deudas, con almacén y folio como texto (sin enlace al vale, que queda fuera de su alcance). No ve existencias ni Seguimiento. No tiene «Recibir devolución». | DU-03, C-05, RG-13 |
| 10 | **Cambio del tope de alto valor** (de 10,000 a 5,000). | Al reiniciar con el nuevo valor, la siguiente consulta ya cuenta como alto valor los artículos de 5,000 o más: cambian Deudores, la tarjeta del Inicio, Seguimiento y los avisos de SG-06. No hay migración ni recálculo, y los vales no cambian. | AV-02 |
| 11 | **Artículo sin costo** en una categoría sin la marca. | No es de alto valor. Si se le captura un costo de 12,000, pasa a serlo en la siguiente consulta. | AV-02 |
| 12 | **Alguien renombra «Equipo de alto valor» a «Equipo crítico».** | Nada cambia: la marca sigue prendida y el alto valor se sigue contando (era la incongruencia 3). | AV-04 |
| 13 | **Minipulidor de 15,000 en «Herramienta eléctrica».** | Es de alto valor por costo. En el resumen cuenta solo como alto valor; filtrar por la categoría «Herramienta eléctrica» lo muestra con su insignia «Alto valor». | AV-02, AV-03 |
| 14 | **Importar un artículo de 12,000 por cantidad** (una fila con cantidad 5, sin categoría). | La sugerencia es «Equipo de alto valor», que es por pieza: si se acepta, la fila pasa a error RG-05 («Una pieza va en una fila con cantidad 1») hasta que el archivo traiga una fila por pieza o se elija otra categoría. | AV-03, I-14, RG-05 |
| 15 | **Proyecto cerrado con deudas** (CP-05). | Las deudas siguen y el proyecto sale con la insignia «Cerrado». El filtro de proyecto ofrece también los cerrados que aún tienen deudas. | DU-02, CP-05 |
| 16 | **Almacén cerrado al que se le debe** (AL-04). | La deuda sigue a su nombre con la insignia «Cerrado»; la devolución se recibe en otro almacén (V-07) y la deuda se cierra. | DU-02, AL-04, V-07 |
| 17 | **Trabajador reingresado con deuda de su contrato anterior** (B-05). | La deuda sigue, con su fecha original; el renglón avisa «Viene de un contrato anterior» (como E-12). | DU-04, B-05, E-12 |
| 18 | **Pieza en tránsito o de un artículo inactivo.** | Lo que va en tránsito no es deuda de nadie. Un artículo inactivo en manos de un trabajador sí es deuda y se puede devolver (CF-11). | DU-01, CF-11 |
| 19 | **Consumo de un trabajador sin contrato vigente.** | El periodo por omisión es el de su último contrato; la pantalla lo dice («Contrato del 01/03 al 30/09/2026»). | DU-08 |
| 20 | **Total en pesos del consumo con un solo artículo.** | Revelaría el costo unitario por división: se oculta con «No se muestra para no revelar el costo de un artículo» (misma salvaguarda que FEAT-017). | DU-08, RG-12 |

## Fuera de alcance

- Cobrar o descontar al trabajador lo que debe (sigue sin cargo, V-05).
- Avisos automáticos por correo, SMS o push a los deudores.
- Registrar la pérdida (V-13) o darla por perdida (P-05): siguen pospuestas.
- Devolución de consumibles sobrantes (V-10): sigue pospuesta.
- Un tope de alto valor por almacén o por categoría (es uno general).
- Editar el tope desde una pantalla.
- Gráficas en Deudores (la regla de solo tablas en reportes se mantiene).

## Criterios de aceptación

- **AV-01.** Dada una base nueva, cuando se corren las categorías iniciales, entonces existen las siete con el control, retorno y límite de la tabla nueva de 5.1, y la pantalla de Categorías muestra la definición corta de cada una.
- **AV-02.** Dado un artículo de «Herramienta eléctrica» con costo de 15,000, entonces `GET /api/seguimiento/piezas?alto_valor=true` incluye sus piezas; y dado el tope en 20,000, entonces deja de incluirlas, sin migración.
- **AV-03.** Dada una importación en modo Alta con una fila sin categoría, descripción «Minipulidor» y costo 12,000, cuando se ve la vista previa, entonces la sugerencia es «Equipo de alto valor» con el motivo de su costo; y si el archivo trae «Herramienta eléctrica», entonces manda esa y la fila avisa en amarillo.
- **AV-03.** Dado un trabajador con un minipulidor de alto valor de «Herramienta eléctrica», entonces el resumen de Deudores lo cuenta una sola vez, como alto valor.
- **AV-04.** Dado que alguien renombra la categoría «Equipo de alto valor», entonces la tarjeta «Alto valor fuera del almacén» da el mismo número; y dado un usuario sin `catalogo.administrar`, cuando intenta cambiar `alto_valor` de una categoría, entonces 403; y con el permiso, el cambio queda en el registro de cambios.
- **AV-05.** Dado un usuario sin `catalogo.costos`, cuando consulta un artículo de alto valor, entonces recibe `alto_valor: true` y no recibe el costo ni el motivo de la marca.
- **DU-01.** Dado un trabajador con 10 pares de guantes consumidos y un casco en resguardo, entonces Deudores lo lista con 1 unidad (el casco) y nunca cuenta los guantes.
- **DU-02.** Dada una pieza entregada por Contratistas para el proyecto «Paro mayor Midrex», entonces su renglón dice almacén Contratistas y ese proyecto.
- **DU-03.** Dado el supervisor de Midrex, cuando pide `GET /api/deudores?almacen_id=<Contratistas>`, entonces no recibe nada; y dado un trabajador que debe a los dos, entonces el supervisor de Midrex ve solo lo de Midrex y `otros_almacenes` con el número de lo demás.
- **DU-03.** Dado RH, entonces ve las deudas de todos los almacenes y no ve existencias; y dado un usuario sin `deudores.ver`, entonces `GET /api/deudores` responde 403.
- **DU-04.** Dado un trabajador con el contrato vencido y un detector de gases, entonces sale primero, con el aviso de SG-06 y la insignia de alto valor.
- **DU-06.** Dado el filtro «debe desde hace más de 30 días», entonces solo salen trabajadores con al menos una cosa entregada hace más de 30 días; y dada una búsqueda por número de serie, entonces sale quien tiene esa pieza.
- **DU-06.** Dados 3,000 trabajadores con deuda, cuando se pide la página 2 de 25, entonces la respuesta llega sin cargar los 3,000 en memoria (se comprueba con una prueba de la consulta paginada).
- **DU-07.** Dado el Administrador, entonces el resumen trae una fila por almacén y una por proyecto con trabajadores, piezas, unidades y alto valor fuera, y se descarga en CSV.
- **DU-08.** Dado un trabajador con dos entregas de guantes para un proyecto (9 y 3 pares) y una de 2 sin proyecto, y la de 3 cancelada, entonces su consumo muestra 9 en ese proyecto y 2 sin proyecto; y sin `reportes.valor_inventario`, la respuesta no trae `valor_total` ni `valor_por_proyecto`.
- **DU-09.** Dado que se abre `/reportes/adeudos`, entonces llega a `/deudores`; y dada la ficha de una pieza en resguardo, entonces enlaza al trabajador en Deudores (con `deudores.ver`) y a su línea de tiempo.

## Módulos relacionados conocidos

- `catalogo`: `categoria.alto_valor` (modelo, esquemas, servicio, auditoría), la expresión de alto valor que usan los demás, `categorias_iniciales.py` (marca en «Equipo de alto valor») y el aviso de alto valor por cantidad.
- `importacion`: `categorias_sugeridas.py` y `analisis.py` (sugerencia por costo, AV-03).
- `consulta`: repositorio y servicio nuevos de Deudores (`repository_deudores.py`, `service_deudores.py`), consumo por trabajador, `repository_seguimiento.py`, `service_seguimiento.py` y `repository_tablero.py` (quitan `CATEGORIAS_ALTO_VALOR`), reporte de consumo (filtro `proyecto_id`).
- `trabajadores`: ruta `GET /api/trabajadores/{id}/consumo` (o en `consulta`, según dónde viva la de dotación).
- `acceso`: permiso `deudores.ver` en el catálogo, roles iniciales y dependencias (`requiere`: `trabajadores.ver`).
- `config.py`: `ALTO_VALOR_COSTO_MINIMO`.
- Frontend: `routes/supervision/deudores.tsx` (nueva), `rep-adeudos.tsx` (redirección), `routes/personas/trabajador-ficha.tsx` (pestaña Consumo), `routes/inventario/categorias.tsx` (interruptor), `routes/consulta/seguimiento.tsx` y `pieza.tsx` (enlaces), `routes.ts` y `sesion/menu.ts`.

## Cambios de datos o API esperados

- **Migración de Alembic:** `categoria.alto_valor` (booleano, `false` por omisión) y `true` en la categoría inicial «Equipo de alto valor» (la migración la encuentra una sola vez por su nombre; después ya nada lee el nombre). Alta del permiso `deudores.ver` en Supervisor, Recursos Humanos y Administrador, y en todo rol que tenga `reportes.adeudos`, para que nadie pierda acceso.
- **Parámetro:** `ALTO_VALOR_COSTO_MINIMO=10000` en `.env.example`; tabla 5.4 de las reglas.
- **API nueva:** `GET /api/deudores` (`deudores.ver`; acepta `trabajador_id`, filtros de DU-06, `pagina`, `tamano` y `formato=csv`), `GET /api/deudores/resumen` (`deudores.ver`; acepta `formato=csv`) y `GET /api/trabajadores/{id}/consumo` (`trabajadores.ver`).
- **API que cambia:** categorías (`GET`, `POST`, `PATCH`) aceptan y devuelven `alto_valor`; artículo, pieza y renglones de seguimiento devuelven `alto_valor` (y `alto_valor_motivo` solo con `catalogo.costos`); `alto_valor_fuera` del tablero y el filtro `alto_valor` de Seguimiento cambian de criterio (AV-04); la vista previa de la importación puede sugerir por costo (AV-03); `GET /api/reportes/consumo` acepta `proyecto_id`.
- **Sin cambios:** `GET /api/reportes/adeudos`.

## Restricciones y compatibilidad

- Las reglas viven en el servidor; la interfaz solo muestra `alto_valor` y los números que el servidor calcula.
- El costo nunca sale en Deudores, en el consumo por artículo ni en ningún vale (RG-12, F-12); CURP y NSS nunca salen (RG-13).
- Los permisos se verifican por clave en cada endpoint, nunca por el nombre del rol.
- Los vales y movimientos no cambian: esta feature solo lee.
- Los textos nuevos van en español llano: «Le debe a», «Desde hace 36 días», «Alto valor», «Ya no es vigente».

## Riesgos

- **Consulta pesada.** Agrupar por trabajador con la entrega más reciente de cada cosa, sobre todo el historial. Se mitiga con la tabla derivada ya usada en Seguimiento, con paginar en la consulta y con medir antes de agregar índices.
- **Diferencias con el reporte de adeudos.** Si Deudores y `GET /api/reportes/adeudos` calculan distinto, dos números no cuadran. Se mitiga con una prueba que compare los dos sobre los mismos datos.
- **Atribución de una cantidad entregada por dos almacenes.** Si a un trabajador le dieron 2 flexómetros en Contratistas y 1 en Midrex, los 3 se le atribuyen a Midrex (la entrega más reciente), como hoy en SG-01 y C-05. Es una simplificación conocida (Decisiones abiertas, punto 2).
- **El booleano dice algo del costo.** Que un artículo de «Herramienta eléctrica» sea de alto valor deja ver que cuesta 10,000 o más (AV-05). Se acepta por la decisión D-12.
- **Pruebas que usan el nombre.** Las pruebas de SG-04 y SG-06 suponen la comparación por nombre; hay que reescribirlas, no borrarlas.

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla, con su ID en el nombre (`test_AV_01_…` a `test_AV_05_…`, `test_DU_01_…` a `test_DU_09_…`).
- La prueba de integración del guion del PDF del track sigue pasando.
- Migración arriba y abajo.
- Prueba de que nada en `consulta` lee `categoria.nombre` para decidir el alto valor.
- Recorrido manual en 1280 px y en 375 px con Supervisor, Recursos Humanos y Administrador, y uno con un rol sin `deudores.ver`.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): tabla de 5.1 (AV-01), 5.4 (`ALTO_VALOR_COSTO_MINIMO`), AV-01 a AV-05 y DU-01 a DU-09, SG-04 y SG-06 reescritas, C-05 (pantalla en Deudores), C-08 (filtro de proyecto), nota en RG-12 (AV-05), I-14 (sugerencia por costo) y la sección 8 (`deudores.ver`).
- [api-contracts.md](../architecture/api-contracts.md): Deudores, consumo por trabajador, `alto_valor` en categorías, artículos y seguimiento, filtro `proyecto_id` del consumo.
- [data-model.md](../architecture/data-model.md): `categoria.alto_valor`.
- [app-flow.md](../product/app-flow.md): `/deudores`, redirección de `/reportes/adeudos`, pestaña Consumo de la ficha del trabajador.
- [ui-ux.md](../product/ui-ux.md): pantalla Deudores, insignia «Alto valor», interruptor de la categoría.
- `.env.example` y [FEAT-007](FEAT-007-importacion-reposicion-y-categoria-sugerida.md) (el diccionario de sugerencias gana la regla por costo).

## Decisiones abiertas

1. **Alturas en la tarjeta de alto valor.** Propuesta: «Alto valor fuera del almacén» sigue contando el equipo de alturas, identificado por `requiere_inspeccion` y no por el nombre (AV-04). Alternativa: separar en dos tarjetas, «Alto valor fuera» y «Alturas fuera».
2. **Cantidad entregada por dos almacenes.** Propuesta: se atribuye toda a la entrega más reciente, como hoy (DU-02). Alternativa: repartirla por almacén según lo entregado menos lo devuelto, que es más exacto pero no siempre se puede decidir (una devolución en un tercer almacén no dice a cuál de los dos le abona).
3. **Alto valor por cantidad.** Propuesta: se permite con un aviso en el catálogo (AV-03). Alternativa: impedir que una categoría con la marca sea por cantidad.
4. **El permiso `reportes.adeudos`.** Propuesta: se conserva para el endpoint del CSV y se marca «no disponible» cuando ningún rol lo use. Alternativa: retirarlo ya y que `GET /api/reportes/adeudos` pida `deudores.ver`.
5. **Consumo visible para el almacenista.** Propuesta: sí, con `trabajadores.ver`, igual que la dotación (D-02), porque le ayuda a explicar un E-09. Alternativa: pedir `deudores.ver` o `reportes.consumo`.
6. **Valor en pesos del consumo con un solo artículo.** Propuesta: ocultarlo (caso límite 20), igual que en FEAT-017.
7. **Deudas de los trabajadores de mi proyecto con otro almacén.** Propuesta: el supervisor de Midrex ve en Deudores solo lo que se le debe a Midrex, y de lo demás solo el número (DU-03), aunque el trabajador sea de un proyecto de Midrex. Alternativa: que también vea, con almacén y folio, lo que los trabajadores de sus proyectos le deben a Contratistas, porque el consumo de esos trabajadores sí cuenta para su proyecto (D-13). Cambia el alcance de AC-06 y conviene decidirlo junto con FEAT-013.
