# ADR-008: Bloqueos del motor de vales: orden fijo y READ COMMITTED

## Estado

Aceptada (5 de octubre de 2026).

## Contexto

Dos almacenistas pueden confirmar a la vez la misma pieza, el mismo artículo por cantidad o vales del mismo trabajador. El servidor debe garantizar que solo uno gane, que la existencia no quede negativa, que el folio no se repita ni deje huecos y que un vale se guarde completo o no se guarde (RG-04, RG-06, RG-08, RG-09). La base es MySQL 8.4 con InnoDB, que por defecto usa REPEATABLE READ.

## Fuerzas y restricciones

- La autenticación ya leyó de la base en la misma sesión antes de confirmar. En REPEATABLE READ esa primera lectura fija una foto: tras esperar un bloqueo, las lecturas normales de la confirmación no verían lo que la otra confirmación guardó, y se evaluaría sobre datos viejos.
- Crear una fila de existencia que no existe, desde dos transacciones a la vez, con `SELECT ... FOR UPDATE` seguido de `INSERT`, produce un interbloqueo clásico.
- Otros agentes agregarán tipos de vale (devolución, traspaso, recepción, cancelación): el orden de bloqueo debe ser el mismo para todos.

## Alternativas consideradas

1. **Bloquear con `FOR UPDATE` y seguir en REPEATABLE READ**, leyendo todo con bloqueo. Obliga a convertir cada consulta de hechos (conteos del límite, ficha del trabajador) en lecturas con bloqueo.
2. **Cambiar el nivel de aislamiento de todo el motor de la aplicación** en `db.py`. Funciona, pero afecta a todos los módulos.
3. **Abrir la transacción de la confirmación en READ COMMITTED** y bloquear en un orden fijo.

## Decisión

La alternativa 3. `MovimientoService.confirmar` hace commit de lo que leyó la autenticación, abre una transacción nueva con `isolation_level = READ COMMITTED` y toma los bloqueos en este orden: vales, trabajador, existencias por `(ubicacion_id, articulo_id)`, piezas por `id` y `serie_folio`. Las existencias que no existen se crean en cero con `INSERT ... ON DUPLICATE KEY UPDATE cantidad = cantidad`, que toma el bloqueo exclusivo sin la carrera. Después de bloquear se descarta lo leído (`expire_all`) y se vuelve a evaluar. Si MySQL aun así resuelve un interbloqueo, la confirmación se repite hasta tres veces.

Dos confirmaciones con el mismo `id_cliente` se resuelven igual: la primera gana y la segunda devuelve su vale (se vuelve a buscar el `id_cliente` después de bloquear); el índice único es la red de seguridad.

## Justificación

El bloqueo del trabajador serializa los límites y las autorizaciones por persona; el de las existencias y las piezas, la disputa por el mismo equipo; el del contador de folios, la numeración consecutiva, que además es una instrucción del PDF. Con un orden único no hay ciclos de espera. READ COMMITTED hace que cada consulta de la confirmación vea lo último confirmado sin tocar el resto de la aplicación.

## Consecuencias positivas

- Solo una de dos confirmaciones concurrentes gana; la otra recibe 409 `VALE_CAMBIO` con la evaluación nueva.
- El folio es consecutivo y sin huecos: si la transacción falla, el contador no avanza.
- Un tipo nuevo hereda todo esto declarando qué filas necesita en `bloqueos`.

## Consecuencias negativas

- Las confirmaciones de un mismo almacén y tipo pasan de una en una (por el contador de folios, que ya decidía [ADR-006](ADR-006-identificadores-uuid-y-folio.md)).
- En las pruebas, la sesión va dentro de una transacción externa y el motor no cambia el nivel de aislamiento ahí; las pruebas de concurrencia usan conexiones propias con datos confirmados.
- Quien escriba un tipo nuevo debe respetar el orden de bloqueo.

## Señales para reevaluar

- Aparecen interbloqueos o esperas largas bajo carga real.
- Otro módulo necesita escribir en las tablas que bloquea el motor.
