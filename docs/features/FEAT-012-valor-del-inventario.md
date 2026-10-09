# FEAT-012: Valor del inventario

Estado: **construida.** Este documento se escribió el 9 de octubre de 2026 **a partir del código**, porque la feature se construyó sin brief (commits `b2210f2` y `5262d36`, migración `0009_permiso_valor_inventario`). Describe lo que hay; no propone nada nuevo. Lo que la amplía (el Inicio del supervisor y el uso por proyecto) está en [FEAT-013](FEAT-013-proyectos-y-supervision-por-almacenes.md), reglas TB-04 a TB-08.

## Problema u oportunidad

La empresa necesita saber cuánto dinero tiene en herramienta y equipo, y dónde está: en los almacenes, en manos de los trabajadores o en camino. El costo de cada artículo es un dato reservado (RG-12, plática del 3 de octubre, min 38 y 39): lo ve solo Compras. Hacía falta una forma de ver el **total** sin enseñar el costo de ningún artículo.

## Objetivo

Que quien tiene el permiso vea el valor del inventario de su alcance, solo en totales, sin que la respuesta traiga nunca un costo unitario ni un valor por artículo.

## Historia de usuario

Como Compras, quiero ver cuánto vale el inventario por almacén y por categoría, para decidir qué comprar y qué mover.

Como supervisor, quiero ver cuánto vale lo que hay en mi almacén y lo que traen mis trabajadores, para responder por ello.

## Alcance incluido

### Reglas

| ID | Regla | Origen |
|---|---|---|
| VI-01 | El valor del inventario lo ve quien tiene `reportes.valor_inventario`. No pide `tablero.ver`: son permisos separados. Sin el permiso, 403 `SIN_PERMISO`. | Plática 3 oct, min 39; decisión del usuario |
| VI-02 | El alcance es el del tablero (AC-06, TB-01): con `almacenes.todos` se ven todos los almacenes o el que se elija; sin él, solo el almacén asignado y el parámetro `almacen_id` se ignora. Sin almacén y sin `almacenes.todos`, todo llega en cero. | AC-06 |
| VI-03 | El valor es la existencia por el costo unitario actual del artículo. El total es la suma de sus partes: lo que hay **en almacén**, lo que está **en resguardo** de los trabajadores (atribuido al almacén de su entrega) y, solo cuando se ven todos los almacenes, lo que va **en tránsito**. | Propuesta |
| VI-04 | Un artículo **sin costo no suma**, pero se cuenta: la respuesta dice cuántos artículos y cuántas unidades no tienen costo, para que el total no parezca completo cuando no lo es. | Propuesta |
| VI-05 | La respuesta **nunca** trae el costo de un artículo, su nombre ni un valor por artículo: solo totales y su reparto por categoría y por almacén. | RG-12 |
| VI-06 | `GET /api/articulos?sin_costo=true` lista los artículos **activos** que no tienen costo, para que Compras los complete. No muestra costos. | Propuesta |
| VI-07 | El reparto **por almacén** solo viene cuando se ven todos los almacenes sin filtrar. El reparto **por categoría** trae las seis de mayor valor y junta el resto en «Otras». | Propuesta |

### Pantalla

Una pestaña «Valor» en el Inicio (`componentes/tablero/pestana-valor.tsx`), visible solo con el permiso: total, en almacén, en resguardo, en tránsito (si aplica), reparto por categoría, reparto por almacén (si aplica) y el aviso de artículos sin costo con enlace a la lista filtrada del catálogo.

### Permiso y roles

`reportes.valor_inventario`, «Ver el valor del inventario (solo totales, nunca el costo de un artículo)». La migración `0009` lo dio a **Compras, Supervisor y Administrador**.

## Fuera de alcance

- El costo unitario de un artículo (sigue siendo de `catalogo.costos`).
- El valor de un vale, de un trabajador o de un artículo.
- El valor histórico: se calcula con el costo de hoy; los movimientos no guardan el costo de cuando ocurrieron.
- El uso por proyecto y las unidades junto a los pesos (FEAT-013).

## Criterios de aceptación

Son las pruebas que ya existen en `backend/tests/consulta/test_valor_inventario.py`:

- Dado un usuario sin `reportes.valor_inventario`, cuando pide el valor, entonces recibe 403; y con el permiso lo recibe aunque no tenga `tablero.ver` (VI-01).
- Dado un usuario sin `almacenes.todos`, cuando pide el valor de otro almacén, entonces recibe el de su almacén; y el Administrador puede filtrar por uno (VI-02).
- Dadas existencias con costo en almacén y en resguardo, cuando se pide el valor, entonces el total es existencia por costo y coincide con la suma de sus partes (VI-03).
- Dado un artículo sin costo con existencia, cuando se pide el valor, entonces no suma y aparece contado en `articulos_sin_costo` y `unidades_sin_costo` (VI-04).
- Dado un artículo con costo, cuando se pide el valor, entonces la respuesta no contiene su costo ni su nombre (VI-05).
- Dado el filtro `sin_costo=true`, cuando se listan los artículos, entonces salen solo los activos sin costo (VI-06).
- Dado el alcance de todos los almacenes, cuando se pide el valor sin filtrar, entonces viene el reparto por almacén; con un almacén elegido, no (VI-07).

## Módulos relacionados conocidos

- `consulta`: `router_tablero.py` (`GET /api/tablero/valor`), `service_valor.py`, `repository_valor.py`, `schemas_tablero.py`. Solo lee.
- `catalogo`: el filtro `sin_costo` de `GET /api/articulos`.
- `acceso`: el permiso en `permisos.py` y en los datos de prueba.
- Frontend: `api/tablero.ts`, `componentes/tablero/pestana-valor.tsx`, `routes/inventario/articulos.tsx`.

## Cambios de datos o API esperados

Ninguno pendiente. Lo construido:

- Migración `0009_permiso_valor_inventario`: agrega el permiso a los roles iniciales. Sin tablas ni columnas nuevas.
- `GET /api/tablero/valor?almacen_id=`: contrato en [api-contracts.md](../architecture/api-contracts.md#get-apitablerovaloralmacen_id).
- `GET /api/articulos?sin_costo=true`.

## Restricciones y compatibilidad

- Los importes viajan como texto con dos decimales, no como número, para no perder precisión.
- El cálculo es en vivo sobre `existencia` y `articulo.costo_unitario`; no hay tablas de resumen.

## Riesgos

- **El costo se puede deducir de un total.** Si un grupo (una categoría, un almacén) tiene un solo artículo con costo, dividir el total entre las unidades da su costo unitario. Hoy la respuesta no trae unidades, así que el riesgo es bajo; FEAT-013 las agrega (TB-04) y trae la salvaguarda: mostrar «—» en ese caso a quien no tiene `catalogo.costos` (decisión transversal T-2 del [maestro](../releases/iteration_01/README.md)).
- **Total incompleto.** Con muchos artículos sin costo el total engaña; por eso VI-04 los cuenta.
- **Rendimiento.** Suma en memoria por fila de existencia; con mucho inventario conviene agregar en la consulta.

## Validaciones requeridas

`uv run pytest tests/consulta/test_valor_inventario.py`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`. No se corrieron al escribir este documento: es solo documentación.

## Documentos globales que podrían actualizarse

Hechos el 9 de octubre de 2026: las reglas VI-01 a VI-07 en [reglas-de-negocio.md](../product/reglas-de-negocio.md) (sección 7.14) y la referencia en el [maestro de la iteración 01](../releases/iteration_01/README.md). El contrato ya estaba en api-contracts.md.
