# ADR-001: La bitácora de movimientos es la fuente de verdad y el trabajador es una ubicación

## Estado

Aceptada (3 de octubre de 2026).

## Contexto

El reto pide saber qué hay en cada almacén, qué tiene cada trabajador y qué debe devolver, sin perder el historial de origen y destino. La idea del equipo es una bitácora con trazabilidad total.

## Fuerzas y restricciones

- El PDF pide registrar fecha, cantidad, almacén, responsable y saldo en cada movimiento.
- Entregas, devoluciones y traspasos pesan 35 % de la rúbrica.
- Hay poco tiempo: conviene una sola pieza de lógica bien probada.

## Alternativas consideradas

1. **Tablas separadas** para entregas, devoluciones y traspasos, con existencias que se editan. Es lo habitual, pero cada operación repite reglas y las existencias pueden desviarse sin dejar rastro.
2. **Bitácora única de movimientos**, donde las existencias son la suma de los movimientos.

## Decisión

Toda operación es un movimiento de una ubicación a otra. Las ubicaciones son almacenes, trabajadores y cuatro virtuales: Proveedor, En tránsito, Consumido y Baja. Los movimientos solo se insertan. Las existencias se guardan aparte para consultar rápido y se actualizan en la misma transacción.

## Justificación

Con el trabajador como ubicación, entregar, devolver y trasladar son la misma operación con distinto origen y destino. Lo que tiene un trabajador, lo que debe y lo que hay en un almacén salen del mismo cálculo: el saldo por ubicación.

## Consecuencias positivas

- Un solo motor para todas las operaciones, con pruebas concentradas.
- Historial completo por artículo, pieza, trabajador y almacén sin trabajo extra.
- Las existencias se pueden reconstruir y verificar contra la bitácora.
- Los movimientos que solo se insertan se llevan bien con una sincronización futura.

## Consecuencias negativas

- Un error no se corrige editando: requiere un movimiento inverso.
- Hay que cuidar que nadie escriba existencias fuera del motor.
- Las consultas de estado dependen de una tabla derivada que debe mantenerse en la misma transacción.

## Señales para reevaluar

- La comparación entre bitácora y existencias reporta diferencias.
- Aparecen operaciones que no se pueden expresar como movimiento entre dos ubicaciones.
