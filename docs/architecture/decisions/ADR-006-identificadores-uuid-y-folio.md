# ADR-006: Identificadores UUID versión 7 y folio consecutivo por contador

## Estado

Aceptada (4 de octubre de 2026), a petición del equipo.

## Contexto

El modelo de datos no fijaba de qué tipo son los identificadores. El equipo prefiere UUID. Aparte, el PDF pide que cada vale tenga un folio consecutivo, y hay que decidir de dónde sale.

## Fuerzas y restricciones

- Los identificadores viajan en las direcciones y en la API: no conviene que se puedan adivinar ni que dejen ver cuántos registros hay.
- MySQL ordena físicamente cada tabla por su llave primaria; una llave aleatoria dispersa las inserciones.
- El folio debe ser consecutivo por almacén y tipo de vale (RG-06), y no repetirse aunque dos personas confirmen al mismo tiempo.
- Python 3.14 ya trae UUID versión 7 (`uuid.uuid7()`); se comprobó en el entorno del proyecto.

## Alternativas consideradas

Para el identificador:

1. **Entero autoincremental.** Simple y compacto, pero se puede adivinar.
2. **UUID versión 4**, aleatorio. No se adivina, pero dispersa las inserciones.
3. **UUID versión 7**, ordenado por tiempo. No se adivina y se inserta en orden.

Para el folio:

4. **Usar el identificador.** Un autoincremental es uno solo para toda la tabla, no por almacén y tipo, y deja huecos cuando una operación falla. Un UUID no es consecutivo.
5. **Calcular el máximo más uno.** Dos confirmaciones simultáneas leen el mismo máximo y producen el mismo folio.
6. **Contador por almacén y tipo**, bloqueado dentro de la transacción del vale.

## Decisión

- Todas las tablas con `id` usan **UUID versión 7 generado por el servidor**.
- El **folio sale de `serie_folio`**: un contador por almacén y tipo de vale que se bloquea y avanza en la misma transacción que guarda el vale. La columna `folio` tiene además restricción de unicidad.
- `vale.id_cliente` sigue aparte: lo genera el dispositivo para que un reintento no duplique el vale.
- Las personas nunca ven el UUID. Lo que leen, imprimen y escanean es el folio, el código, el número de empleado o la clave del almacén.

## Justificación

La versión 7 da las dos cosas: no se puede enumerar y conserva el orden de inserción. El contador dentro de la transacción da folios sin repetidos y sin huecos: si la transacción falla, el contador tampoco avanza.

## Consecuencias positivas

- Las direcciones no se pueden recorrer cambiando un número.
- Un identificador se puede generar antes de guardar, lo que ayuda si después se agrega sincronización.
- El folio consecutivo queda garantizado por la base de datos, no por una convención.

## Consecuencias negativas

- Identificadores largos en direcciones y registros; son menos cómodos para depurar.
- Ocupan más: con el tipo `Uuid` de SQLAlchemy, MySQL los guarda en 32 caracteres. A esta escala no importa.
- Un UUID versión 7 deja ver la hora en que se creó el registro. Aquí no es un dato sensible.
- El contador hace que las confirmaciones de un mismo almacén y tipo pasen de una en una. Es el comportamiento buscado.

## Señales para reevaluar

- El volumen crece al punto de justificar guardarlos en 16 bytes binarios.
- Las confirmaciones de un almacén se estorban por el contador.
