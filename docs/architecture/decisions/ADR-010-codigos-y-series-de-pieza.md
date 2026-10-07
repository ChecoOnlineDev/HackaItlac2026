# ADR-010: Códigos y series de pieza

## Estado

Aceptada (7 de octubre de 2026).

## Contexto

La importación de inventario ([FEAT-007](../../features/FEAT-007-importacion-reposicion-y-categoria-sugerida.md)) rechazaba como error toda pieza sin código de pieza o sin número de serie (I-02). Al preparar la carga con el Excel del reto, unas 137 piezas de 23 artículos no tenían serie ni un código propio por pieza: las claves de producto de ese archivo (como la clave UNSPSC) identifican un tipo de producto, no una pieza física. Rechazarlas obligaba a inventar series para poder dar de alta el equipo o a dejarlo fuera del sistema, que es peor: una herramienta sin registro no se controla.

Hay que decidir cómo entra una pieza cuando no se conoce su serie, de dónde sale su código cuando el archivo no lo trae y dónde se completa lo que faltó, sin cambiar el modelo de datos que ya está construido ([data-model.md](../data-model.md)).

## Fuerzas y restricciones

- `pieza.numero_serie` ya admite nulo, y el índice único `(articulo_id, numero_serie)` de MySQL tolera varios nulos. `pieza.codigo` ya es único y está registrado en la tabla `codigo`.
- El control de piezas depende de su código (el QR contiene exactamente el código; ver [ui-ux.md](../../product/ui-ux.md), «Impresión»); la serie del fabricante es un dato de verificación, no la llave del sistema.
- Los movimientos y los vales no se actualizan ni se borran; completar una serie no es un movimiento y no debe tocar existencias ni ubicación.
- Las reglas de negocio las evalúa el servidor; la interfaz solo muestra lo que él devuelve.
- Los códigos de artículo ya tienen la forma `PREFIJO-NNNN` y se generan por categoría al importar; el código de pieza no debe confundirse con un artículo ni chocar con ese consecutivo.
- Dos importaciones simultáneas no pueden repetir códigos.
- Evitar una migración reduce el riesgo en un sistema ya desplegado.

## Alternativas consideradas

1. **Mantener la serie obligatoria.** Es lo que había. Obliga a capturar series que no existen o a excluir equipo del sistema. Descartada.
2. **Una pieza sin serie con un estado nuevo («Serie pendiente») o una columna `serie_pendiente`.** Es explícito, pero duplica un dato que ya se sabe (serie nula), exige migración y un estado más que cuidar en todas las reglas. Descartada.
3. **Generar una serie provisional** (por ejemplo `PEND-0001`). Evita el nulo, pero ensucia el campo con valores falsos que parecen verdaderos, rompe la búsqueda por serie y obliga a distinguir las provisionales por convención. Descartada.
4. **Serie nula = pendiente, derivada y sin migración.** Aprovecha lo que el esquema ya permite y deja claro en el dato mismo que falta. Elegida.
5. **Usar las claves de producto del Excel original como código de pieza.** No son únicas por pieza (varias piezas comparten clave) y la clave UNSPSC es un cajón de sastre para clasificar, no un identificador. Descartada.
6. **Código de pieza secuencial global** (`PZA-000123`). Único y simple, pero no dice de qué artículo es y compite con la numeración de otros códigos. Descartada frente a un tercer segmento sobre el código del artículo.

## Decisión

1. **Serie derivada y opcional, con aviso.** `pieza.numero_serie` nulo significa serie pendiente. No hay estado nuevo ni columna nueva ni migración; la API la expone como `serie_pendiente: true`. Una cadena vacía se guarda como nulo. La serie que sí existe sigue siendo única por artículo; el nulo no cuenta como repetido.
2. **La importación Alta ya no rechaza la pieza sin serie.** La fila entra con un aviso amarillo (`SERIE_PENDIENTE`). Una serie repetida (en la base o en el mismo archivo) sigue siendo error.
3. **La entrega avisa, no bloquea.** La evaluación de ENTREGA agrega un motivo amarillo `SERIE_PENDIENTE` (regla E-29) a la pieza sin serie. Traspaso, recepción y devolución no miran la serie.
4. **La serie se completa después, con un permiso propio.** `POST /api/piezas/{id}/serie` con `piezas.registrar_serie`: solo pone la serie a una pieza que no la tiene (409 `SERIE_YA_REGISTRADA`) y rechaza la que ya existe en ese artículo (409 `SERIE_REPETIDA`). Deja la auditoría `pieza.registrar_serie` con el antes y el después. Cambiar una serie ya registrada queda fuera de esta etapa. Es una clave nueva y no `catalogo.administrar`, porque los permisos se verifican por clave, no por rol ([ADR-007](ADR-007-permisos-por-clave.md)).
5. **Código de pieza automático en la importación Alta.** `codigo_pieza` es opcional. Si el archivo lo trae, se respeta tal cual (RG-10). Si no, el servidor lo genera al confirmar como `CÓDIGO-DEL-ARTÍCULO-NNN` (`HEL-0003-001`): un tercer segmento sobre el código del artículo, con consecutivo por artículo, único contra la tabla `codigo`, dentro de la misma transacción y con el artículo bloqueado. La vista previa lo marca `codigo_pieza_generado: true` (provisional). La confirmación devuelve las piezas creadas para imprimir sus etiquetas. La entrada manual por vale no genera: ahí se captura.
6. **No se usan las claves de producto del Excel original.** Ni como código de pieza ni como serie: identifican un tipo de producto, no una pieza, y no son únicas.
7. **Columna `unidad` opcional** en la importación Alta, que solo se aplica al crear un artículo; la unidad de uno existente no cambia (aviso si difiere). Las cantidades siguen enteras (I-13).

## Justificación

La serie del fabricante es información que a veces simplemente no se tiene el día que el equipo llega al almacén; el código propio (con su QR) basta para controlar la pieza. Derivar la condición del dato nulo evita un estado más y una migración, y deja una sola fuente de verdad. El aviso amarillo en la entrega respeta la lógica del semáforo: se avisa lo que falta sin detener la operación cuando no hay riesgo inmediato, mientras que el reporte, el filtro y la tarjeta del tablero hacen visible la deuda hasta que se complete. El tercer segmento sobre el código del artículo identifica de qué artículo es la pieza a simple vista y no choca con el consecutivo de artículos. Generar el código dentro de la transacción, con el artículo bloqueado y contra `codigo`, reutiliza el mecanismo que ya impide duplicados.

## Consecuencias positivas

- El equipo del reto entra completo al sistema desde el primer día.
- No hay migración ni cambio de esquema; el cambio es de reglas, servicio e interfaz.
- Cada pieza queda controlada por su código aunque no tenga serie.
- La deuda de series es visible (filtro, tarjeta y aviso) y se salda con un solo endpoint.

## Consecuencias negativas

- Sin serie no hay verificación física contra el fabricante ni unicidad de ese dato: la pieza depende solo de su código.
- La búsqueda por serie no encuentra estas piezas; se identifican por código de pieza (QR).
- Un código generado no está pegado en la herramienta: hay que imprimir y pegar la etiqueta, y reimprimirla si el código se cambia después.
- Una cadena vacía y el nulo se tratan igual; hay que normalizar al guardar.
- Hay un permiso nuevo (`piezas.registrar_serie`) que mantener en la sección 8 de las reglas.

## Señales para reevaluar

- Se acumulan piezas con serie pendiente durante semanas: puede hacer falta el bloqueo de entrega para equipo de alto valor o completar series por Excel (segunda entrega).
- Se necesita corregir series ya registradas: hará falta un cambio de serie con auditoría y permiso propio.
- Se requiere que el código de pieza lo imponga el proveedor o una norma: el formato generado dejaría de servir.
- Otra importación (por ejemplo, de trabajadores o de traspasos) necesita generar códigos: habría que extraer el generador a un servicio compartido.
