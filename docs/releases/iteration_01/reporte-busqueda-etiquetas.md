# Reporte FEAT-019: búsqueda, etiquetas y ancho por dispositivo

## Tarea realizada

Se implementaron búsqueda por palabras en el servidor, sugerencias automáticas en Consultar, Entregar, Devolver y Trasladar, filtros de etiquetas y descarga PDF. La clasificación de rutas ahora permite centrar las pantallas de operación a 720 px y ampliar administración hasta 1600 px.

## Archivos modificados

- Backend: `core/busqueda.py`, métodos de búsqueda de `consulta/repository.py`, `service.py`, `schemas.py` y `router.py`; filtro `q` de `trabajadores/repository.py`; etiquetas de `catalogo/repository.py`, `service.py`, `schemas.py` y `router.py`.
- Frontend: `ui/busqueda-diferida.ts`, `campo-busqueda.tsx`, `dominio/escaner-busqueda.tsx`, `escaner.tsx`, `pdf-etiquetas.ts`, `etiquetas-medidas.ts`, `hoja-etiquetas.tsx`, ruta Etiquetas y enlace desde importación/artículo; clasificación `handle.dispositivo`, Pantalla y armazón de escritorio.
- Formato compartido: `dominio/formato.ts`, reexportaciones compatibles de fechas/personas/traspasos y moneda de catálogo, artículo y tablero.
- Pruebas: `backend/tests/consulta/test_busqueda_ux.py`, `etiquetas-medidas.test.ts`, `pdf-etiquetas.test.ts` y `busqueda-diferida.test.ts`.

## Decisiones y supuestos

- La espera y cancelación se centralizan; los buscadores administrativos existentes conservan `useRetraso` mediante reexportación compatible. Su migración completa al nuevo gancho todavía está pendiente.
- La detección de pistola en el campo usa el umbral existente de Escaner, sin modificar la ventana de repetidos. Enter de un carácter intenta identificación exacta.
- Los PDF reutilizan jsPDF y Poppins instalados por FEAT-017. Los QR son tramos vectoriales de qrcode.react, sin una biblioteca adicional.
- Las etiquetas mantienen el alcance previo global, como exige la compatibilidad del brief; el endpoint sigue protegido por `etiquetas.imprimir`.
- El rango de alta usa `trabajador.creado_en`, en días completos de México. No cuenta reingresos.
- Formato 30 usa la geometría propuesta del brief; debe cotejarse con la hoja adhesiva comercial realmente comprada.
- Importación transporta códigos en el estado de navegación, evitando URL de miles de caracteres. El filtro `lote_id` ya es aceptado por el servidor junto con la columna de FEAT-017.

## Validaciones ejecutadas

- Backend búsqueda y filtros de etiquetas: 38 pruebas aprobadas, incluidas 9 nuevas y 29 anteriores de escaneo/búsqueda; base aislada `feat19_busqueda`, `ENTORNO=desarrollo`.
- Frontend: 34 pruebas aprobadas en la suite compartida. Generación de PDF de 1, 37 y 500 etiquetas para cada formato; cada archivo debajo de 5 MB, páginas y progreso verificados. Cancelar evita descargar un archivo parcial. El gancho verifica espera, Enter inmediato y descarte de respuestas viejas.
- Construcción y verificación de tipos aprobadas nuevamente después de incorporar y revisar la UI de firma en papel.
- Las 9 pruebas nuevas de backend se repitieron y aprobaron después de añadir el número de serie separado a las etiquetas.
- Se detectó y reportó una regresión anterior en SeguimientoService: faltaba `self.session`. Su propietario la corrigió; no forma parte de la nueva lógica de búsqueda.

## Riesgos o deuda pendiente

- No se acreditan lectura física de todas las etiquetas, impresora, Safari, cámara ni compartir PDF en equipo Android real.
- Falta el recorrido visual con capturas en todos los tamaños del brief, migrar todos los buscadores administrativos a estados/cancelación del nuevo gancho y completar la barra de filtros de escritorio.
- No se cambiaron las decisiones abiertas de amarillo ni las familias de insignias de compras; requieren la resolución/documentación prevista por el brief.
- No se midió carga con 20 mil registros. Se conserva LIKE y la colación vigente sin agregar índices.
- Series especialmente largas y códigos densos deben revisarse impresos; el PDF advierte cuando el módulo QR cae por debajo de 0.5 mm.

**Corrección visual aplicada el 9 de octubre de 2026:** se resolvió la diferencia de insignias entre «Mis solicitudes» y la cola de Compras. Ambas usan `frontend/app/componentes/compras/insignias.tsx`; Pendiente queda en gris, Urgente en rojo con rayo, estados en curso en azul suave y estados cerrados sin compra en gris. `frontend/app/componentes/compras/insignias.test.ts` verifica el componente y que ambas listas importan esa implementación común.

## Documentación actualizada

Reporte y notas aditivas de API, flujos, reglas de búsqueda y UI. El brief completo sigue pendiente de todos sus criterios físicos y de la migración de buscadores; no se marca FEAT-019 como terminada.

## Siguiente acción

Revisar código por otro agente y completar recorridos visuales y lectura física de etiquetas; continuar los buscadores administrativos por pantalla.
