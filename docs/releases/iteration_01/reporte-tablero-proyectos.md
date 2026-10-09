# Reporte de FEAT-013: tablero de proyectos (TB-04 a TB-08)

## Tarea realizada

Inicio muestra el uso de cada proyecto como tabla con barras en escritorio y tarjetas en celular. Separa retornables en resguardo hoy de consumibles consumidos en el rango, netos de cancelaciones. Permite ver todos los almacenes asignados o uno, y todos los proyectos o uno, sin cambiar el almacén activo. Un proyecto único muestra su reparto por categoría sin selector adicional.

Valor del inventario agrega unidades al total y a su reparto por categoría y almacén. Sin permiso de valor, las unidades de almacén y resguardo siguen visibles en el resumen. Las tarjetas de proyectos por vencer y almacenes sin proyecto llevan a listados filtrados.

## Archivos modificados

- `backend/app/modulos/consulta/`: nuevos `repository_tablero_proyectos.py`, `service_tablero_proyectos.py` y `schemas_tablero_proyectos.py`; cambios en `router_tablero.py`, `repository.py`, `schemas_tablero.py`, `service_tablero.py` y `service_valor.py`.
- `frontend/app/api/tablero.ts`, `componentes/tablero/{tablero,uso-proyectos,pestana-valor,tarjetas-indicadores}.tsx`, listados de proyectos y almacenes y tipos de almacenes.
- Pruebas de tablero, valor y nuevas pruebas `backend/tests/consulta/test_tablero_proyectos.py`.
- El filtro `GET /proyectos?por_vencer=true` lo construyó el agente propietario de proyectos.

## Decisiones y supuestos

- TB-06: el proyecto del retornable se obtiene de su última ENTREGA no cancelada, por trabajador y artículo o pieza. Una devolución parcial no cambia esa atribución. Una entrega cancelada deja de atribuir resguardo; la cancelación de una devolución conserva la entrega anterior.
- Consumibles: los movimientos hacia CONSUMIDO suman y los inversos restan. Una cancelación toma la fecha de su vale original; no la fecha de cancelación. El alcance se decide por el almacén del proyecto, y «Sin proyecto» por el almacén del vale.
- T-2: cada importe va `null` sin `reportes.valor_inventario`, o cuando permite deducir el costo de un único artículo con costo y falta `catalogo.costos`. Se preservan las unidades. Si hay importes reservados, orden y barras usan unidades.
- Los cerrados aparecen si aún tienen resguardo o consumo neto en el rango. Los trabajadores asignados cuentan sólo asignaciones activas de personas activas.
- No hay datos simulados ni operaciones de escritura en consulta. No se agregan dependencias ni migraciones.

## Contratos aditivos implementados

- `GET /api/tablero/proyectos?desde=&hasta=&almacen_id=&proyecto_id=` exige **ambos** permisos `tablero.ver` y `proyectos.ver`. Responde `{alcance,rango,proyectos,sin_proyecto,generado_en}` conforme al brief. Cada proyecto lleva los tres totales `{unidades,valor}`, `articulos_sin_costo`, sus referencias y fechas, situación y trabajadores asignados. «Sin proyecto» lleva los mismos tres totales y `articulos_sin_costo`.
- `por_categoria` es `null` en la lista general; con `proyecto_id` es una lista de `{categoria:{id,nombre}|null,nombre,retornables_en_resguardo,consumibles_consumidos,total,articulos_sin_costo}`. Hasta seis categorías y una fila «Otras» con `categoria:null`.
- `GET /api/tablero/resumen`: `alcance.almacenes` es la lista completa permitida para los selectores; `nombre` dice «Tus N almacenes» en un conjunto. `almacenes_sin_proyecto` es lista de almacenes de tercer nivel activos sin proyecto activo, o `null` sin `almacenes.administrar`. `proyectos_por_vencer` es lista `{id,clave,nombre,almacen,fin_estimado}` de activos cuyo fin es hasta hoy+7, incluidos vencidos, o `null` sin `proyectos.ver`.
- El resumen agrega `inventario_unidades:{en_almacen,en_resguardo,total}`. Estos tres totales no llevan pesos y no exigen permiso de valor. Las tres cifras de inspección son `null` sin `inspecciones.ver`.
- `GET /api/tablero/valor`: agrega `unidades_en_almacen`, `unidades_en_resguardo`, `unidades_total`; cada categoría agrega `unidades`; cada almacén agrega los tres totales de unidades. El reparto por almacén también viene en conjuntos de más de uno, sólo con sus almacenes. Se conserva el valor y unidades de tránsito en el alcance global conforme al endpoint existente.
- Transiciones: `/proyectos?por_vencer=true`, `/proyectos?proyecto_id=UUID` abre la ficha y `/almacenes?sin_proyecto=true` filtra almacenes sin proyectos activos.

## Validaciones ejecutadas

- `pnpm typecheck`: pasó tras integrar selector, tarjetas y tabla.
- `pnpm build`: pasó con el reparto por categoría y almacén integrado.
- `pnpm test`: 14 pruebas pasaron.
- `ruff check` de los archivos backend y pruebas del alcance: pasó.
- Pruebas MySQL: 35 pasaron, incluidas las diez específicas TB-04 a TB-08/T-2, y una falló en la modificación concurrente del helper de alto valor de FEAT-018. Su propietario corrigió la normalización de Decimal y VI-06 pasó al repetirse: las 36 pruebas quedan comprobadas entre ambas corridas, con `TEST_DB_SUFFIX=tbproyectos_ui` y `ENTORNO=desarrollo`.

## Riesgos o deuda pendiente

- Falta recorrido visual interactivo en navegador y teléfono real. Tipos y construcción no prueban el comportamiento táctil en un dispositivo.
- `pendientes()` lee resguardo real antes de agrupar; utiliza el mecanismo compartido existente. Un volumen mayor requiere medir antes de introducir índices o reemplazarlo por agregación SQL.
- Este reporte abarca TB-04 a TB-08; no declara completa FEAT-013 ni las demás features. La documentación global se integra en la tarea principal para evitar conflictos entre agentes.

## Documentación actualizada

Este reporte registra endpoints, DTOs y transiciones que deben reconciliarse con `api-contracts.md` y `app-flow.md` en la integración principal. El esquema no cambió.

## Siguiente acción

Revisar visualmente el tablero con el usuario supervisor de dos almacenes y el administrador, y reconciliar los documentos globales en la integración principal.
