# Plan de implementación afinado

> **Estado:** plan para revisar. **No modifica código ni reglas todavía.** Reúne las decisiones tomadas por el usuario, lo que cada una cambia en el sistema (verificado en el código y en los documentos) y el orden para construirlo. Los puntos de [inconsistencias-y-pendientes.md](inconsistencias-y-pendientes.md) que aquí se resuelven quedan marcados.
> **Regla de trabajo:** primero se actualizan los documentos afectados (tabla «Cuándo actualizar documentación» de `AGENTS.md`), después se escribe el código, y cada regla lleva su ID en la respuesta del servidor y en el nombre de su prueba.

## 1. Decisiones registradas

| # | Decisión | Estado | Nota |
|---|---|---|---|
| D1 | La pieza **entra con serie pendiente** | Decidido | Cambia I-02 (sección 3) |
| D2 | **Código de pieza automático** cuando el archivo no lo trae | Decidido y **confirmado** (7 oct 2026) | Formato `CÓDIGO-DEL-ARTÍCULO-NNN`; regla I-15 |
| D3 | **Traspaso por Excel** (FEAT-009) aprobado | Decidido | Amplía el alcance del MVP con aprobación |
| D4 | **«Dejar fuera las filas con error»** entra al MVP | Decidido y **confirmado** (7 oct 2026) | Acción explícita en TR-06 |
| D5 | Decimales: **convertir a unidad entera menor** | Decidido | Sin conversión automática (sección 5) |
| D6 | El supervisor que envía arma el Excel de traspaso | Decidido | Kepler (o Administrador) → Contratistas; Contratistas → proyecto |
| D7 | El Administrador da de alta los almacenes; EPP en Contratistas; el proyecto se reactiva; periodo por apertura después del MVP | Decidido | Ya en FEAT-008 y en [red-de-almacenes-y-flujo.md](red-de-almacenes-y-flujo.md) |

**Siguen abiertas** (sección 8): quién recibe en un proyecto, «Pedir compra urgente» del administrador, columnas de almacén en la plantilla de traslados, filtros del inventario, EPP básico y de dotación, y qué cuenta como «usado» en el tablero.

## 2. Qué no requiere migración

Verificado en el modelo y en las migraciones (`0001` a `0007`):

| Cambio | Migración | Por qué |
|---|---|---|
| Serie pendiente | **No** | `pieza.numero_serie` ya acepta nulo, y el índice único `(articulo_id, numero_serie)` tolera varios nulos en MySQL |
| Código de pieza automático | **No** | `pieza.codigo` ya es único y la tabla `codigo` registra la unicidad |
| Columna `unidad` en la importación | **No** | `articulo.unidad` ya existe (texto de 20, por omisión «pieza») |
| Traspaso por Excel | **No** | El traspaso importado es un vale `TRASPASO` normal; la huella va en la auditoría |

Solo habría migración si se agrega un estado nuevo de pieza o un campo `serie_pendiente`; se recomienda **no** hacerlo (sección 3.1).

## 3. Serie pendiente (D1)

### 3.1 Cómo se modela

La serie pendiente se **deriva** de `numero_serie` vacío, igual que hoy se deriva la inspección pendiente (I-03: artículo que requiere inspección sin `inspeccion_vigente_hasta`). No se crea un estado nuevo (`EstadoPieza` queda en Apto, No apto, En mantenimiento, En calibración y Baja). Así no hay migración ni cambios en las restricciones de la base.

### 3.2 Reglas que cambian

| Regla | Hoy | Cambio propuesto |
|---|---|---|
| **I-02** | «Cada pieza entra con su código único, marca y número de serie del fabricante» | La **serie es opcional al entrar**; sin ella la pieza queda con serie pendiente. El código sigue siendo obligatorio o se genera (sección 4). Una serie repetida sigue siendo error |
| **RG-10** | Menciona «código de pieza o serie repetidos» | Se mantiene para la serie que sí viene; aclarar que el vacío no cuenta como repetido |
| **I-06 y TR-04** | Hablan de la columna `serie` | Aclarar que puede ir vacía |
| Definición de **Pieza** (reglas, sección 1) | «Tiene código único, número de serie del fabricante…» | «…y su número de serie, que puede quedar pendiente» |
| **Regla nueva de entrega** | No existe | **Decidido (reemplaza la propuesta de bloquear):** la entrega **no se bloquea**; E-29 es un aviso amarillo «la pieza no tiene número de serie registrado». Traspaso y devolución tampoco cambian (hoy no miran la serie y conservan el estado, X-04) |
| **Regla nueva de captura** | No existe | Quien tiene el permiso de registrar series puede completarla después (sección 3.3) |

Los IDs de las reglas nuevas se asignan al redactarlas, siguiendo la numeración de las reglas de entrega y de piezas.

### 3.3 Cómo se completa la serie

- **Hoy no existe** ningún endpoint para editar la serie o el código de una pieza (el único escritor posterior es el cambio de estado y de vigencia de inspección). Hay que crear uno.
- **Propuesta:** `POST /api/piezas/{id}/serie` con `{numero_serie}`. Valida que no esté repetida en ese artículo (error de serie repetida que ya existe), la guarda y deja renglón de auditoría con el valor anterior y el nuevo. Solo se puede **poner** una serie a una pieza que no la tiene; **cambiar** una ya registrada no entra en esta etapa.
- **Permiso:** una clave nueva, por ejemplo `piezas.registrar_serie`, para Supervisor, Compras y Administrador, o reutilizar `catalogo.administrar`. Se recomienda la clave nueva (los permisos se verifican por clave, nunca por rol) y exige actualizar la sección 8 de las reglas. **Decisión pendiente.**
- **Segunda entrega:** completar muchas series de una vez con un Excel (`codigo pieza`, `serie`). Son 137 piezas en 23 artículos; capturarlas una por una es lento. Reutiliza la lectura y la vista previa de la importación.

### 3.4 Dónde se ve

- Ficha y lista de piezas, y el seguimiento de piezas: la serie sale vacía con la etiqueta «Serie pendiente».
- Un filtro «Con serie pendiente» en el seguimiento de piezas y en inventario, y una tarjeta del tablero «Piezas con serie pendiente» (el tablero ya es de solo lectura sobre los datos de `consulta`).
- La búsqueda por serie no las encuentra: se identifican por código de pieza (QR). Las reglas E-18, V-14 y C-06 se aclaran en ese sentido.

### 3.5 Importación (modo Alta)

- Hoy `FALTA_SERIE` es un error rojo (regla I-02). Pasa a **aviso amarillo** «Serie pendiente» (motivo `SERIE_PENDIENTE`): la fila entra.
- Hay que relajar la comprobación interna que da por hecho que toda pieza trae serie.
- La serie repetida contra la base o contra el mismo archivo sigue siendo error.

### 3.6 Riesgos

- Sin serie no hay unicidad ni verificación física con el fabricante; la pieza depende solo de su código. Por eso el bloqueo de entrega y el reporte de pendientes.
- «Equipo de alto valor» está descrito en las reglas con serie; se ajusta el texto, no la lógica de control.

## 4. Código de pieza automático (D2)

### 4.1 Cómo funciona

- Si el archivo trae el código de pieza, **se respeta tal como viene** (RG-10). Si no lo trae, el servidor lo **genera** al confirmar.
- **Formato:** `CÓDIGO-DEL-ARTÍCULO-NNN`, por ejemplo `HEL-0003-001`, `HEL-0003-002`… Es un tercer segmento sobre el código del artículo, que ya es `PREFIJO-NNNN`. Así no se confunde con un artículo ni choca con el consecutivo de artículos (que cuenta códigos `PREFIJO-número`).
- **Unicidad:** se genera contra la tabla `codigo`, que ya es el registro único de códigos, y bajo el mismo bloqueo de categorías que usa la importación para los códigos de artículo; dos importaciones simultáneas no repiten.
- La vista previa muestra el código como «provisional: se asigna al confirmar», igual que el de artículo.
- Hoy `FALTA_CODIGO_PIEZA` es error; pasa a no ser error cuando el código se puede generar.

### 4.2 Lo que hay que aclarar en las reglas

- **RG-10** dice que «los códigos se aceptan tal como vienen». Se amplía: «…y si una pieza no trae código, el sistema le asigna uno».
- **I-02:** el código es único, ya sea el que viene o el generado.

### 4.3 Efecto en las etiquetas

El QR de la pieza contiene exactamente su código. Un código generado **no está pegado en la herramienta todavía**: tras importar hay que imprimir y pegar las etiquetas. Se propone un acceso directo en la pantalla de resultado de la importación: «Imprimir etiquetas de las piezas nuevas». Si el código se cambia después de pegar la etiqueta, hay que reimprimirla.

### 4.4 Alta manual de una pieza

La entrada por vale no tiene generador: el usuario captura el código. Se mantiene así en esta etapa; el generador es solo de la importación.

### 4.5 Decisión técnica

Un ADR nuevo (**ADR-010, «Códigos y series de pieza»**) que registre: serie derivada y opcional, código automático con tercer segmento y por qué no se usan las claves de producto del Excel original (no son únicas por pieza).

## 5. Decimales a unidad menor (D5)

### 5.1 Lo que se encontró

- La cantidad es **entera** en todo el sistema (movimientos y existencias); I-13 dice que nunca se redondea.
- El artículo ya tiene `unidad` (texto libre), pero **la importación no la lee**: un artículo nuevo importado queda en «pieza».
- El mensaje de error ya sugiere convertir («250 gramos en lugar de 0.25 kilos»).

### 5.2 Cambio mínimo

1. Agregar una columna opcional **`unidad`** a la importación en modo Alta (con sus sinónimos: «unidad», «u.m.», «medida»), a la plantilla y a la vista previa.
2. Pasar la unidad al crear el artículo nuevo.
3. Para un artículo que ya existe, **no se cambia su unidad** (coherente con «la importación no actualiza nada de lo existente»); si el archivo trae otra, sale un aviso, como ya pasa con el nombre y la marca.
4. **Se mantiene I-13.** No hay conversión automática: el archivo declara la unidad menor y la cantidad en esa unidad. Una conversión automática exigiría una tabla de equivalencias y contradiría «nunca se redondea».

### 5.3 Las tres filas del Excel de compras

Se convierten **en el Excel**, no en el sistema, y solo cuando la columna `unidad` exista:

| Artículo | Cantidad original | Conversión propuesta | Verificar |
|---|---|---|---|
| Clavo para madera de 2" | 0.25 | 250 g | Que la unidad original sea kilos |
| Alambre recocido cal. 16 | 60.12 | 60 120 g | Ídem |
| Bolsa negra jumbo 90×120 cm | 25.15 | 25 150 g, o piezas | **Confirmar con Compras la unidad**: no se sabe si son kilos o bolsas |

El costo unitario se recalcula como importe entre la cantidad nueva. **No inventar unidades:** las que no se confirmen quedan fuera hasta tenerlas. El servicio de maniobras sigue excluido.

## 6. Traspaso por Excel (D3, D4, D6)

Ya documentado en [FEAT-009](../features/FEAT-009-traspasos-por-lista-de-excel.md), el contrato (`api-contracts.md`, «Importación de traspasos») y las historias US-TRP-001 y 002. Resumen de lo que se construye, sin tocar la recepción:

- **Backend:** cuatro rutas bajo `/api/importacion/traspasos/` con `traspasos.operar`, que leen el archivo, evalúan cada fila con las reglas de traspaso (X-02, X-04, X-09, AL-04, X-03) y confirman **a través del servicio de movimientos** (tipo `TRASPASO`). Todo o nada (RG-09) con la acción explícita «Dejar fuera las filas con error»; un archivo es un vale de hasta 500 renglones; idempotencia por `id_lote` y aviso por huella.
- **Frontend:** botón «Trasladar con una lista» en la pantalla de trasladar; pasos de destino, archivo, columnas y vista previa (reutiliza lectura de archivo, columnas, paginación de 12 y esqueleto); banner de ruta; confirmación de dejar fuera.
- **No cambia:** `recibir-detalle` (casilla por renglón, «Recibir todo», escaneo y diferencias).
- **Segunda entrega:** descargar la lista de un traspaso en Excel (TR-10).

## 7. Orden de construcción

### Fase 0: documentos (sin código)

Se hace primero y en paralelo por documento, como en FEAT-007, FEAT-008 y FEAT-009.

| Documento | Qué cambia |
|---|---|
| `reglas-de-negocio.md` | I-02, RG-10, I-06, TR-04, definición de Pieza, E-18, V-14 y C-06; reglas nuevas de serie pendiente y de entrega; I-13 y columna `unidad`; sección 8 si hay permiso nuevo; D4 y D3 pasan a decididas |
| `data-model.md` | Aclarar la derivación de «serie pendiente», la unidad y el código generado; la invariante de unicidad |
| `api-contracts.md` | `POST /api/piezas/{id}/serie`, motivo `SERIE_PENDIENTE`, `codigo_pieza` opcional, columna `unidad`, filtro de serie pendiente |
| `app-flow.md` y `ui-ux.md` | Ficha de pieza con serie pendiente, resultado de importación con etiquetas, tabla de vista previa con unidad |
| ADR-010 | Códigos y series de pieza |
| `mvp-scope.md` | Registrar la ampliación aprobada |
| Correcciones | Historias US-TRS-001 y 002 («supervisor»), `README` (FEAT-008 construido), criterio de siete grupos de menú |

### Fase 1: backend, tres pistas en paralelo (archivos distintos)

| Pista | Qué | Archivos principales |
|---|---|---|
| **A. Importación de inventario** | Serie pendiente (aviso en vez de error), código de pieza automático, columna `unidad`, plantilla | `importacion/analisis.py`, `schemas.py`, `lectura.py`, `plantilla.py`, `service.py` |
| **B. Traspaso por Excel** | Las cuatro rutas, el análisis de traspasos y la llamada a movimientos | Archivos nuevos en `importacion/` y su router incluido desde `importacion/router.py` |
| **C. Serie y entrega** | Endpoint para registrar la serie, regla nueva de entrega, permiso nuevo, reporte y filtro de pendientes | `catalogo/`, `movimientos/evaluador.py`, `acceso/permisos.py`, `consulta/` |

Cada pista lleva su prueba por regla con su ID, usa su propio `TEST_DB_SUFFIX` y valida con `ruff` y `pytest`.

### Fase 2: frontend, tres pistas en paralelo

| Pista | Qué |
|---|---|
| **F1. Importación** | Columna `unidad`, aviso de serie pendiente, acceso a etiquetas tras importar |
| **F2. Traspaso por lista** | Pantallas de la sección 6 |
| **F3. Piezas** | Serie pendiente en ficha y lista, captura de serie, filtro y tarjeta del tablero |

### Fase 3: verificación

`pytest` completo, `pnpm typecheck`, `pnpm build`, reconstruir con Docker y probar en el navegador con cada rol (necesita sesión de administrador). Revisión por otro agente.

### Después de las tres fases

Regenerar los dos Excel de importación con la columna `unidad`, las tres filas convertidas y las piezas sin serie, y probarlos de punta a punta.

## 8. Lo que sigue abierto

| # | Decisión | Recomendación |
|---|---|---|
| 1 | Quién recibe en un proyecto | **Resuelto:** `traspasos.recibir` separado de `traspasos.operar` (X-01) |
| 2 | Permiso de registrar series | **Resuelto:** clave nueva `piezas.registrar_serie` (S, C y Administrador; P-08) |
| 3 | Completar series por Excel en la primera entrega o la segunda | Segunda |
| 4 | «Pedir compra urgente» del administrador | Ocultarlo del menú |
| 5 | Columnas de almacén en la plantilla de traslados | Solo para verificar |
| 6 | Filtros del inventario (existencia, tipo, control, marca, estado) | Sí |
| 7 | EPP básico y de dotación | Mantener las dos |
| 8 | Qué cuenta como «usado» en el tablero | Entregas netas de cancelaciones |
| 9 | Unidad original de clavo, alambre y bolsa | Confirmar con Compras |
| 10 | Confirmar la lectura de D2 y D4 | **Resuelto:** confirmadas |

## 9. Riesgos y deuda conocida

- **16 pruebas de sesiones** fallan desde antes de estos cambios cuando corre la suite completa; hay que aislarlas antes de dar por buena cualquier verificación completa.
- **Dos archivos `test_visibilidad_almacenes.py`** con el mismo nombre rompen la recolección de la suite completa.
- **Desplegable de almacén** al entregar equipo, sin reproducir.
- **Docker** corre una versión anterior; reconstruir antes de probar.
- **Códigos generados** sin etiqueta física hasta imprimirla y pegarla.
- **Piezas con serie pendiente** sin verificación física posible hasta completar la serie.
