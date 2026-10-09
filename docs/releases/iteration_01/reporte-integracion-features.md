# Reporte de integración FEAT-001 a FEAT-020

## Tarea realizada

Implementación local en curso sobre `main`, conservando el trabajo previo de traslados laterales y los cambios locales existentes. El inventario inicial de faltantes está en `estado-features-001-020.md`; es una fotografía de la auditoría inicial, no una certificación del estado final. No se crearon commits ni se hizo push.

Ya están construidos localmente proyectos/asignaciones, alcance por conjunto, mínimos, inspecciones, tablero por proyecto, despacho de EPP, deudores/alto valor, bitácora por vale/lote y búsqueda/etiquetas. FEAT-002 agrega cierre/AJUSTE. FEAT-001 suma sello, comprobante público y firma en papel con reserva de folio, ticket de dos copias y foto obligatoria. FEAT-009 ahora permite descargar una lista de recepción `.xlsx` desde revisión y resultado. FEAT-019 tiene búsqueda por palabras, PDF de etiquetas, ajuste de ancho por dispositivo e insignias compartidas de Compras; conserva criterios administrativos y físicos pendientes. FEAT-020 sigue siendo principalmente el contenedor Android en línea, con primitivas locales de PIN aún sin persistencia ni integración.

## Archivos modificados

- Backend: módulos `proyectos`, `trabajadores`, `acceso`, `almacenes`, `movimientos`, `consulta`, `catalogo`, `inspecciones`, `notificaciones`; migraciones 0011 a 0020 y sus registros.
- Frontend: proyectos, trabajadores, entrega, sesión/identidad, mínimos, inspecciones, tablero por proyecto, comprobante público y deudores; rutas y permisos correspondientes.
- Reportes específicos: `reporte-frontend-proyectos-minimos.md` y `reporte-frontend-inspecciones.md`.

## Decisiones y supuestos

- Se conservan los vales existentes sin proyecto y se exige una explicación para nuevas entregas a trabajadores aún sin asignación.
- El almacén activo se usa para escribir; el conjunto asignado delimita la lectura. Los filtros del tablero no cambian el activo.
- Una asignación principal adicional explícita se rechaza mientras haya otra activa. La historia se conserva al reemplazarla.
- El cuerpo definitivo para conjuntos usa `almacenes_id` y los resúmenes de proyecto en ENTREGA contienen id, clave y nombre.

## Validaciones ejecutadas

- FEAT-013 backend de proyectos/trabajadores: 24 pruebas contra MySQL pasan, incluidas concurrencia y rollback.
- FEAT-004: 64 pruebas pasan entre mínimos, almacenes, valor e inspecciones.
- Integración AC-37/AC-39/PR-08/PR-10: cuatro pruebas pasan contra MySQL con sufijo `feat13_integracion`.
- FEAT-016: 53 pruebas nuevas y anteriores pasan; migración 0015 baja y sube correctamente en una base aislada.
- TB-04 a TB-08: 36 pruebas comprobadas, incluidas diez nuevas del tablero por proyecto y privacidad del valor.
- FEAT-001: pruebas previas de sello/comprobante y prueba nueva del ciclo PAPEL (reserva, borrador QR, foto y mismo folio/token) pasan. El ciclo de papel, búsqueda UX y round-trip de migración pasan en una regresión de 12 pruebas. Ticket revisado; no hay prueba de impresora o cámara física.
- FEAT-002: 21 pruebas de cierre/AJUSTE pasan, Ruff pasa y revisión secundaria completada; FIFO es una atribución aproximada por cantidad.
- FEAT-009 / TR-10: descarga imprimible `.xlsx` desde revisión y resultado, con código, serie, cantidades y columnas de recepción; respeta filas excluidas. 3 pruebas nuevas pasan y el archivo abre con `openpyxl`. Sigue pendiente la descarga desde vales históricos y la impresión física.
- FEAT-017: 11 pruebas backend y 3 de PDF frontend pasan; `0020` bajó/subió en base aislada. La regresión dirigida de movimientos y dos flujos de importación pasó con 67 pruebas; se ajustaron fixtures/expectativas para cumplir reglas y contratos actuales. Esto no certifica toda la suite backend.
- FEAT-019: backend (38 pruebas, incluidas 9 nuevas y su repetición) y frontend (47 pruebas totales en 9 archivos) pasan; tipos, build y Ruff pasan. La revisión independiente del flujo de búsqueda/tránsito y reserva de papel quedó atendida; siguen pendientes buscadores administrativos y pruebas físicas.
- FEAT-020: 4 pruebas para derivación PBKDF2 y política de intentos pasan; typecheck/build pasan. No hay persistencia cifrada, UI/login offline, sincronización ni prueba en dispositivo.
- Otras verificaciones y límites por feature están en los reportes enlazados desde este directorio. Las migraciones aplican en bases aisladas; no se actualizó la base de producción.

## Riesgos o deuda pendiente

Las veinte features no están completas. Quedan criterios y regresiones documentados por feature, recorridos de impresora/cámara/PDF en equipos reales y pruebas de accesibilidad/rendimiento físico. La regresión dirigida de 67 pruebas, el smoke de migración/búsqueda/papel de 12 y las 47 pruebas frontend pasaron. La regresión backend completa no pasó: 2,067 aprobadas, 303 fallidas y 21 errores; hay discrepancias de contratos/permisos y errores de teardown por FK que requieren triage. FEAT-020 no implementa aún inscripción del dispositivo, SQLite cifrada/Keystore, evaluación offline, cola, sincronización, conflictos ni revocación local; las primitivas de PIN tampoco persisten ni se integran con el login. El APK debug se reconstruyó con los cambios recientes, pero no se instaló porque no había dispositivo conectado por ADB. Los cambios siguen locales, sin commit ni push.

## Documentación actualizada

Contratos de API, modelo de datos, reglas, flujo y reportes específicos. Los contratos aprobados de las features siguen siendo el objetivo; los avances parciales se señalan explícitamente.

## Siguiente acción

Triagear los 303 fallos y 21 errores de la regresión completa; después cerrar criterios pendientes por feature y decisiones de FEAT-020 antes de continuar la operación offline y validar el APK en un equipo Android.
