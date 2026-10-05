# FEAT-002: Cierre de almacén de proyecto y valor del inventario

## Problema u oportunidad

Al terminar un mantenimiento la empresa solo ve lo que quedó en el contenedor y no sabe quién perdió qué (plática min 33). Tampoco sabe cuánto vale lo que tiene en almacén (min 39). La bitácora ya tiene los datos; falta mostrarlos.

## Objetivo

Que al cerrar un almacén de área cada artículo quede explicado, y que Compras vea el valor del inventario por almacén.

## Historia de usuario

Como supervisor, quiero un reporte de cierre de un almacén de proyecto, para saber qué se envió, qué regresó, qué falta y quién lo tiene.

Como Compras, quiero ver el valor del inventario por almacén, para saber cuánto dinero hay en existencias.

## Alcance incluido

- **Reporte de cierre** por almacén: por artículo, lo recibido por traspaso, lo consumido, lo regresado, lo que sigue en resguardo de trabajadores con su nombre, y los faltantes.
- **Faltante.** Lo que el sistema dice que hay y no aparece se registra con un vale de ajuste, con observación obligatoria, a nombre del almacén.
- **Cerrar almacén.** Con existencias en cero y sin traspasos en tránsito, el supervisor lo marca como cerrado; deja de aparecer para operar.
- **Abrir almacén.** El supervisor crea un almacén de proyecto con su almacén padre.
- **Valor del inventario.** Existencias por costo unitario, por almacén y por categoría. Solo Compras.

## Fuera de alcance

- Conteos parciales o cíclicos.
- Sobrantes: equipo que aparece y el sistema no tenía.
- Dar por perdido lo que está con trabajadores.
- Depreciación y valuación contable.

## Criterios de aceptación

- Dado un almacén de área con operaciones, entonces el reporte cuadra por artículo: lo que entró es igual a lo que salió más la existencia actual, y cada salida está clasificada como consumida, regresada, entregada a trabajadores o faltante.
- Lo entregado a trabajadores se separa en devuelto y todavía en resguardo, con el nombre de quien lo tiene.
- Dado un faltante registrado, entonces baja la existencia del almacén y queda el vale de ajuste con su observación y su responsable.
- Dado un almacén con existencias o con traspasos en tránsito, entonces no se puede cerrar y se indica qué falta.
- Lo que sigue en resguardo de trabajadores no impide cerrar.
- El valor del inventario solo responde a quien tiene el permiso `reportes.valor_inventario`; de inicio, Compras.

## Módulos relacionados conocidos

`movimientos` (vale de ajuste), `almacenes` (abrir y cerrar), `consulta` (reportes).

## Cambios de datos o API esperados

- Tipo de vale AJUSTE, con movimientos de almacén a BAJA y motivo "faltante".
- `POST /api/almacenes`, `POST /api/almacenes/{id}/cierre`, `GET /api/almacenes/{id}/reporte-cierre`, `GET /api/reportes/valor-inventario`.

## Restricciones y compatibilidad

- Un almacén cerrado conserva su historial y sigue apareciendo en los reportes.
- Los artículos sin costo capturado se listan aparte en el valor del inventario.

## Riesgos

- Si el reporte no cuadra, la causa es un movimiento mal clasificado; la igualdad del primer criterio es la prueba.

## Validaciones requeridas

- Prueba de la igualdad con los datos del guion.
- Prueba de permiso del valor del inventario.
- Cierre manual de un almacén de prueba.

## Documentos globales que podrían actualizarse

`data-model.md`, `api-contracts.md`, `app-flow.md` (cierre de almacén), `reglas-de-negocio.md` (CP-01 a CP-05, C-09).
