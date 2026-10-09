# Reporte de FEAT-002 — servidor

## Tarea realizada

Vale AJUSTE por faltante del almacén, reporte de cierre por rango y alias del valor del inventario. El motor normal conserva responsable, observación, folio AJU, firma por sesión, idempotencia, bloqueos, movimiento, existencias y sello en la misma transacción. El reporte lee también almacenes cerrados, reconstruye saldos históricos, clasifica movimientos y muestra nombres/unidades pendientes de trabajadores.

## Archivos modificados

- `backend/app/modulos/movimientos/tipos/ajuste.py`, registro de tipos y enum/prefijo en `models.py`.
- `backend/app/modulos/consulta/{router,router_cierre,schemas_cierre,repository_cierre,service_cierre}.py`.
- Catálogo, dependencias y datos de prueba de permisos de acceso.
- `backend/alembic/versions/0019_ajuste_cierre.py` y `backend/tests/test_cierre_feat002.py`.
- Corrección secundaria NT-02 en notificaciones: perder permiso suspende avisos sin revocar el dispositivo; comentario de aprobación parcial corregido en autorizaciones y prueba ampliada FEAT-014.

## Decisiones y supuestos

- `inventario.ajustar` y `reportes.cierre` se asignan inicialmente a Supervisor y Administrador; toda verificación operativa usa claves, no nombres de roles. Roles nuevos se configuran explícitamente.
- El rango usa días inclusivos de México. El saldo al final del rango es histórico, no necesariamente la existencia de hoy.
- Cantidades indistinguibles se atribuyen FIFO declarado; piezas y cancelaciones usan la referencia exacta disponible. ADR-016 documenta esta decisión y su limitación.
- El valor del inventario conserva el servicio y reglas VI/TB existentes, incluida la supresión de totales que revelarían costos unitarios.
- No hay pantallas nuevas de FEAT-002; el frontend añadió sólo la etiqueta AJUSTE a las vistas existentes.

## Validaciones ejecutadas

- `TEST_DB_SUFFIX=feat002_backend uv run pytest tests/test_cierre_feat002.py tests/movimientos/test_cancelacion_reglas.py -q -x` → **21 aprobadas**, última repetición 50.10 s: 16 nuevas de FEAT-002 y 5 de reglas de cancelación. Incluyen evaluación HTTP sin escritura, cierre real con trabajador en resguardo, igualdad, saldos anteriores, retornos entre almacenes, cancelación de entrega posterior/devolución, piezas, permisos, idempotencia y límites. La última repetición precede el reencadenado a `0018_vale_papel`.
- Upgrade completo → downgrade a `0017_alto_valor_deudores` → upgrade head → **aprobado en base MySQL aislada** `feat002_migration`; base de prueba eliminada al concluir.
- Ruff en archivos de FEAT-002 y corrección NT-02 → aprobado. `git diff --check` → aprobado, sólo avisos de conversión LF/CRLF.
- FEAT-014 después de la corrección NT-02 → **21 aprobadas**, 51.80 s.
- Una corrida ampliada con `tests/test_roles.py` llegó a 29 aprobadas y falló en `test_AC_08_un_rol_nuevo_sin_permisos_no_ve_ningun_modulo`: su helper asigna almacén a un rol vacío y el servidor actual lo rechaza. No se modificó ese comportamiento ajeno a FEAT-002.
- Revisión secundaria por el agente frontend: hallazgos de cancelación FIFO y longitud de observación corregidos y cubiertos por nuevas pruebas; permisos, alcance y ausencia de costos revisados.

## Riesgos o deuda pendiente

- **Encadenado de migraciones coordinado con sus responsables:** `0019_ajuste_cierre` depende de `0018_vale_papel`, y `0020_bitacora_lote` depende de `0019`. Mientras el responsable de FEAT-001 no cree el archivo `0018`, Alembic no puede resolver el árbol completo. Falta repetir upgrade/downgrade en ese árbol final. La prueba ida/vuelta anterior se hizo con el enlace provisional `0019` → `0017`. No se aplicaron migraciones a la base real de la aplicación.
- La decisión de atribución FIFO y la futura vista por proyecto necesitan validación de producto (ADR-016). El reporte por rango no adjudica entradas comunes al proyecto.
- Faltan pantallas de ajuste/reporte y pruebas de volumen; el historial se lee por lotes de artículos, sin consultas por renglón, pero aún sin medición con una bitácora grande.
- No se certifican pruebas, tipos y build globales del conjunto de cambios de todos los agentes.
- Web Push físico continúa pendiente; se probó cifrado/transporte con HTTP controlado, no un teléfono real.

## Documentación actualizada

Brief FEAT-002, reglas CP-03/04 y K-04, catálogo de permisos, modelo de datos, contratos de API y ADR-016. El flujo de cierre administrativo continúa en FEAT-008.

## Siguiente acción

Completar las pantallas de FEAT-002, integrar la migración de firma en papel sin crear dos heads y ejecutar verificación global antes de desplegar o reconstruir el APK. Sin commits ni push.
