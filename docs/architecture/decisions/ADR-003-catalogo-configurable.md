# ADR-003: La categoría es una plantilla y el artículo guarda sus propias reglas

## Estado

Propuesta (4 de octubre de 2026). Falta la revisión del equipo.

## Contexto

La empresa debe poder decidir qué va en cada categoría, qué herramientas piden un trato especial y cuáles dejan de usarse, sin tocar el programa. El PDF ya trae un caso: el equipo de alturas se identifica por pieza y exige inspección.

## Fuerzas y restricciones

- Quien administra el catálogo está poco familiarizado con la tecnología: lo que ve en pantalla debe ser lo que aplica.
- Las reglas de un artículo afectan vales que ya se emitieron y equipo que ya está con trabajadores.
- Cambiar un artículo de "por cantidad" a "por pieza" con existencias no tiene una conversión automática.

## Alternativas consideradas

1. **Reglas fijas en el código** por tipo de artículo. Rápido, pero cualquier cambio necesita programador.
2. **Herencia:** el artículo no guarda reglas y toma siempre las de su categoría, salvo excepciones. Un cambio en la categoría se propaga solo, pero la pantalla del artículo ya no dice de dónde sale cada regla.
3. **Plantilla:** la categoría propone las reglas y el artículo guarda una copia que puede cambiar.

## Decisión

La alternativa 3.

- La categoría tiene una plantilla: control, retorno, requisitos especiales y límite.
- Al crear un artículo se copia la plantilla; el artículo guarda sus reglas y las puede cambiar.
- Los requisitos especiales son tres interruptores por artículo: inspección vigente, autorización del supervisor y habilitación del trabajador.
- Control y retorno quedan fijos cuando el artículo tiene movimientos.
- Un artículo con movimientos no se borra: se inactiva, con motivo, y se puede reactivar.

## Justificación

El motor lee las reglas en un solo lugar, el artículo, y lo que muestra la pantalla es exactamente lo que se evalúa. La categoría sigue ahorrando trabajo al crear artículos.

## Consecuencias positivas

- Evaluación simple y predecible.
- Un artículo puede salirse de su categoría sin crear otra.
- Inactivar conserva el historial y deja devolver lo que está en campo.

## Consecuencias negativas

- Cambiar una regla para toda una categoría no se propaga sola: hace falta la acción "reaplicar a todos" (CF-04), que llega después del MVP.
- Corregir un control mal elegido exige crear un artículo nuevo e inactivar el anterior.

## Señales para reevaluar

- La empresa cambia reglas por categoría con frecuencia y reaplicar resulta molesto.
- Aparecen requisitos que no caben en los tres interruptores.
