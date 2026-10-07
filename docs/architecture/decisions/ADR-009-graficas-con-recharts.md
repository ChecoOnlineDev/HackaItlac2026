# ADR-009: Las gráficas del tablero usan recharts

## Estado

Aceptada (6 de octubre de 2026).

## Contexto

[FEAT-008](../../features/FEAT-008-administracion-de-almacenes-y-tablero.md) pide un tablero de inicio con una gráfica de barras horizontales de los artículos más usados. Debe tener filtros que la actualizan sin recargar la pantalla, un detalle al pasar o tocar cada barra (tooltip), una leyenda, y un interruptor «Separar por almacén» que reparte cada barra por colores. Hasta ahora la interfaz no tenía ninguna gráfica: los reportes son tablas y el diseño fijó «Gráficas» como fuera de alcance ([ui-ux.md](../../product/ui-ux.md)). El brief recomendaba en su primera versión barras hechas con HTML y CSS, sin dependencias, y dejaba la decisión abierta (decisión 4 de la sección 10). El usuario decidió usar una librería. La regla del proyecto es no agregar dependencias que la tarea no pida ([AGENTS.md](../../../AGENTS.md)), por eso la decisión se documenta aquí.

## Fuerzas y restricciones

- El almacenista usa el celular: la gráfica debe verse bien en 375 px de ancho y ser táctil.
- La accesibilidad es obligatoria: nada se comunica solo con color (SM-02) y todo debe poder recorrerse con teclado.
- La interfaz ya usa los componentes base de shadcn/ui; su componente `chart` (`frontend/app/components/ui/chart.tsx`) está construido sobre recharts y ya está en el repositorio.
- Tiempo limitado: lo que cueste menos mantener y probar es preferible a lo que se dibuja a mano.
- El tablero lee datos que el servidor ya agrupó; la librería solo dibuja. No decide ninguna regla de negocio.

## Alternativas consideradas

1. **Barras con HTML, CSS y SVG propios, sin dependencias.** Cero peso extra y control total. Pero hay que construir y probar a mano el tooltip, la leyenda, las barras apiladas por almacén, el redimensionado y el foco con teclado; esas piezas son justo las que cuestan.
2. **Chart.js.** Dibuja en `canvas`, que es poco amigable para lectores de pantalla, y no se integra con los componentes de shadcn/ui.
3. **D3 o visx.** Máxima flexibilidad, pero es mucho código para una sola gráfica de barras.
4. **recharts, por medio del componente `chart` de shadcn/ui.** Gráficas declarativas en SVG, con tooltip, leyenda, barras horizontales y apiladas, y colores tomados de variables de tema.

## Decisión

La alternativa 4: **recharts 3.8.0**, con la versión exacta fijada en `frontend/package.json`, usado a través de `frontend/app/components/ui/chart.tsx` (`ChartContainer`, `ChartTooltip`, `ChartLegend`). El usuario ya agregó la dependencia al `package.json`.

Reglas de uso:

- Solo para el tablero de inicio. Ninguna pantalla de reporte se convierte en gráfica sin otra decisión.
- La gráfica **nunca es el único canal**: cada barra lleva su nombre y su número a la vista (no solo en el tooltip) y el color no distingue por sí solo. Con «Separar por almacén», los segmentos llevan además su nombre en la leyenda y en el tooltip.
- La gráfica solo dibuja lo que entrega `GET /api/tablero/consumo`. Ordenar, agrupar, restar cancelaciones y agrupar el resto en «Otros» lo hace el servidor.
- Los componentes de gráfica se cargan bajo demanda (`React.lazy` o importación dinámica) para que su peso no recaiga en las pantallas que no las usan.

## Justificación

Las piezas que más trabajo dan en una gráfica (tooltip, leyenda, barras apiladas, adaptación al ancho, foco con teclado) ya vienen resueltas y probadas por la comunidad. El componente de shadcn/ui, que el proyecto ya tiene, evita repetir estilos: toma los colores de las variables de tema. Se dibuja en SVG, que es texto en el DOM y se puede describir con `aria-label`, a diferencia de un `canvas`.

## Consecuencias positivas

- Tooltip, leyenda y barras horizontales por almacén sin construirlos a mano.
- Mismo lenguaje visual que el resto de la interfaz (variables de tema de shadcn/ui).
- Una gráfica nueva, si algún día se pide, cuesta poco.

## Consecuencias negativas

- Una dependencia más, que se sube al paquete de la interfaz (decenas de kilobytes comprimidos); por eso se carga bajo demanda y se mide con `pnpm build`.
- En pruebas de interfaz sin navegador real, el contenedor responsivo mide cero píxeles: las pruebas de la gráfica necesitan un tamaño fijo o una simulación de las medidas.
- Hay que actualizar la versión con cuidado: recharts cambia de forma incompatible entre versiones mayores.
- La accesibilidad no viene completa: hay que poner el texto y los números junto a las barras y comprobar el recorrido con teclado.

## Señales para reevaluar

- El paquete de la interfaz crece de forma notable por causa de la librería, o el tablero tarda en pintarse en un celular de gama baja.
- Se piden gráficas más complejas que las de recharts (mapas, diagramas de flujo).
- La librería deja de mantenerse o deja de ser compatible con la versión de React del proyecto.
