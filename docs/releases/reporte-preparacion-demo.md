# Reporte de preparación de la demostración

## Tarea realizada

Preparar una exposición de menos de cinco minutos para el Reto IMHOTEP, con cobertura del PDF, restricciones operativas, estado del código, mejoras prioritarias y preguntas para validar el valor del sistema.

## Archivos modificados

- `docs/guion-demo-cinco-minutos.md`: documento nuevo con guion, preparación, cobertura, casos límite, ajustes de QR y búsqueda, dotación, indicadores y encuesta.
- `docs/README.md`: enlace al guion y a este reporte; se conservaron los cambios previos del archivo.
- `docs/releases/reporte-preparacion-demo.md`: este reporte.

## Decisiones y supuestos

- Se interpretó «Por ahora no modifiques todo eso» como solicitud de análisis y documento, sin implementar cambios de aplicación.
- El guion sigue a un trabajador e incluye alta, escaneo, entrega, excedente autorizado, bloqueo de alturas, traspaso, devolución, baja y consulta final.
- El objetivo es 4:40 con 20 segundos de margen. El discurso tiene 361 palabras; la duración efectiva necesita ensayo de las acciones y cambios de sesión.
- Se interpretó «encuesta de valor» como indicadores de inventario y una encuesta breve para usuarios; no se consultaron saldos reales ni se estimaron ahorros.
- La propuesta de dotación usa puestos existentes y listas configurables. No agrega reglas automáticas por área ni certifica capacitación.
- Los botones QR desde la ficha y la descarga individual PNG quedan como propuesta para concretar FEAT-019. No se modificaron roles, reglas, endpoints, modelos ni dependencias.
- Se distinguió código presente de mejoras aprobadas sin construir y de funcionamiento comprobado en el despliegue.

## Validaciones ejecutadas

- Lectura visual del PDF: páginas 1, 2, 3, 8 y 10, renderizadas con Poppler. Comprobada cobertura de las funciones indispensables y del escenario de prueba.
- Contraste de reglas y código de movimientos, inspecciones, autorizaciones, consulta, roles iniciales, ficha de artículo, Etiquetas y dotación de Entregar.
- Revisión de otro agente: encontró una afirmación incorrecta sobre `catalogo.ver`, una referencia P-04 que debía ser P-07 y una aclaración necesaria de consumible sin periodo. Correcciones aplicadas; segunda lectura confirmada sin nuevos hallazgos.
- Comprobación con Python: documento UTF-8 legible, discurso de 361 palabras y enlaces locales verificados.
- Primera ejecución de pruebas: 31 aprobadas y 12 errores de preparación. La configuración heredada tenía `ENTORNO=produccion`; la infraestructura de pruebas usa `COOKIE_SEGURA=false`, por lo que el arranque rechazó esa combinación. No se modificó la configuración guardada.
- Segunda ejecución: `uv run pytest tests/test_guion_pdf.py tests/test_guion_extremos.py tests/movimientos/test_evaluador.py -q --tb=short`, con `ENTORNO=desarrollo` y `TEST_DB_SUFFIX=demo_20261008` únicamente en el proceso: **43 aprobadas en 82.61 segundos**. Una advertencia de deprecación del cliente HTTP de Starlette; sin cambios de dependencias.
- Lint, tipos y build no se ejecutaron: esta tarea modifica solo documentación. Tampoco se probó la interfaz en el despliegue ni un dispositivo real.

## Riesgos o deuda pendiente

- Ensayar el guion con cronómetro y con los datos que entregue el jurado. Las fechas de inspección y el consumo acumulado cambian qué casos se pueden demostrar.
- La documentación de dotación y algunos textos de roles no reflejan todo el código presente. El guion señala estas diferencias sin reescribir las reglas globales en esta tarea.
- Revisar la semántica de «Disponible»: la consulta de existencias cuenta piezas aptas, mientras la entrega también exige inspección vigente. No utilizar el contador como prueba suficiente de que una pieza se puede entregar.
- Aprobar el permiso de etiquetas para el rol que realmente hará la operación si se quiere que el almacenista descargue QR; el rol inicial carece de `etiquetas.imprimir`.
- Las mejoras de FEAT-013 a FEAT-020 conservan sus dependencias y sus límites de alcance; la propuesta no acredita que estén construidas.

## Documentación actualizada

Guion y reporte nuevos, con entrada en el índice. Sin cambios a contratos, modelo de datos, reglas de negocio, alcance ni decisiones de arquitectura.

## Siguiente acción

Ensayar el flujo indispensable en el entorno de exposición. Después, convertir el QR desde la ficha en un cambio acotado dentro de FEAT-019 y construirlo con validación de permisos, alcance y lectura de los archivos descargados. Mantener offline al final.
