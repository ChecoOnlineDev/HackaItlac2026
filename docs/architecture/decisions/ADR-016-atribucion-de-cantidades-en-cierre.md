# ADR-016: Atribución de cantidades en el reporte de cierre

Fecha: 9 oct 2026. Estado: implementada en el servidor, pendiente de validación de producto.

## Contexto

CP-04 pide separar lo entregado por un almacén entre devuelto y en resguardo, aunque la devolución ocurra en otro almacén. Una pieza tiene identidad; las unidades por cantidad no la tienen. El movimiento de devolución identifica trabajador y artículo, pero no la entrega de procedencia. Atribuir toda la deuda a la última entrega tampoco explica unidades enviadas por varios almacenes.

## Decisión

Reconstruir cronológicamente los movimientos hasta el final del rango. Una salida desde un trabajador descuenta primero la entrega más antigua del mismo artículo (FIFO). Una pieza sólo descuenta su propio `pieza_id`. El reporte declara `atribucion_cantidades: FIFO`. **Para cantidades, la procedencia por almacén es una aproximación:** un vale de devolución no conserva la entrega ni el almacén de origen de cada unidad. FIFO produce un reparto determinista, pero no demuestra de qué almacén salió físicamente la unidad devuelta. Esto no afecta la igualdad de entradas y salidas del almacén, que usa sus movimientos reales; sí limita la exactitud del desglose de resguardo por procedencia.

La cancelación usa `vale_origen_id` y el número de renglón del movimiento original: la de una entrega consume primero su lote; la de una devolución restaura los lotes descontados por esa devolución. No se interpreta como una entrega o devolución independiente. Si la cantidad original ya se devolvió y el motor permite cancelar gracias a unidades de otra entrega, el resto se descuenta de los lotes aún disponibles; la bitácora no identifica físicamente esas unidades.

Se mantiene el rango obligatorio del brief FEAT-002. El reporte es del almacén completo y no pretende adjudicar stock común a un proyecto: las entradas y traspasos no llevan `proyecto_id`. La futura vista por proyecto deberá definir esa atribución antes de sustituir este contrato.

## Consecuencias

No se crean saldos nuevos ni se escribe inventario desde consulta. La igualdad contable sale de movimientos y un saldo inicial anterior al rango. El resultado es reproducible y distingue una atribución de cantidades de la trazabilidad exacta de piezas. No certifica un conteo físico. Deben validarse con producto la política FIFO y la posterior vista por proyecto; las pruebas cubren retornos entre almacenes, cancelación de una entrega posterior y cancelación de devolución.
