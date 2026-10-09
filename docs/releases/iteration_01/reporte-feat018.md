# Reporte FEAT-018

## Tarea realizada

Implementación de alto valor configurable, deudores paginados por trabajador, resumen y CSV por almacén/proyecto, y consumo del trabajador. FEAT-018 se implementa sobre las atribuciones de proyectos de FEAT-013 y sin escribir movimientos desde consulta.

## Archivos modificados

- Catálogo: `alto_valor.py`, modelos, esquemas, service/router y categorías iniciales.
- Consulta: nuevos `repository_deudores.py`, `service_deudores.py`, `schemas_deudores.py`, `router_deudores.py`, `repository_consumo_trabajador.py` y `service_consumo_trabajador.py`; integración puntual en router, ficha de pieza, seguimiento, consumo y contador de alto valor del tablero.
- Configuración, permiso `deudores.ver`, dependencias y roles iniciales; `.env.example` documenta umbral general.
- Migración `0017_alto_valor_deudores`, después de `0016_vale_sello`.
- Pruebas `test_deudores_feat018.py`. Interfaz implementada por la tarea principal.

## Decisiones y supuestos

- AV-02/AV-04: alto valor se resuelve al leer: bandera de categoría o costo igual/mayor que `ALTO_VALOR_COSTO_MINIMO`, por defecto 10000. Los nombres de categoría no deciden la condición. La vigilancia de seguimiento incluye también inspección obligatoria.
- AV-05: el booleano es público; el motivo basado en costo y el umbral requieren `catalogo.costos`. La ficha agrega aviso para artículos de alto valor controlados por cantidad. La importación propone categoría sin aplicarla y respeta categoría explícita.
- DU-01/DU-02: sólo retornables en ubicación de trabajador. Almacén, proyecto y antigüedad provienen de la última ENTREGA vigente, sin sustituirla por una cancelada. Se conserva aviso de contrato anterior.
- DU-03: alcance por conjunto de almacenes; Recursos Humanos con `trabajadores.administrar` consulta global. Lo ajeno sólo produce un conteo, sin artículos, nombres de almacenes o costos. Un folio accesible para RH no implica acceso al detalle del vale: `vale.id` es null fuera de su alcance.
- DU-04/DU-06: agrupación, filtros, conteos y paginación se ejecutan en SQL. Sólo se cargan renglones de los trabajadores de la página solicitada; tarjetas no heredan filtros de vigencia/antigüedad. Máximo 200 trabajadores por página.
- DU-07: CSV reutiliza filtros y protección contra fórmulas. Resumen agrupa trabajadores, piezas, unidades, alto valor y no vigentes por almacén/proyecto; no devuelve costos.
- DU-08/C-08: consumo neto descuenta inversos usando fecha/proyecto del original. Incluye todos los almacenes y dotación orientativa. Montos agregados requieren `reportes.valor_inventario`, sin precios unitarios. Grupos de un solo artículo y combinaciones que permiten reconstruir su precio no publican monto.
- Contratos nuevos: GET `/api/deudores`, GET `/api/deudores/resumen` (JSON/CSV), GET `/api/trabajadores/{id}/consumo`; GET `/api/catalogo/configuracion` publica umbral sólo con permiso. `/api/adeudos` conserva compatibilidad.

## Validaciones ejecutadas

- Migración 0017: upgrade, downgrade a 0016 y upgrade en base aislada `_test_feat018mig`: aprobado; base temporal eliminada.
- Ruff sobre archivos nuevos de consulta, helper de alto valor y pruebas: aprobado.
- API con datos locales: listado, resumen y consumo respondieron correctamente; no se imprimieron datos personales.
- Suite ampliada: 89 pruebas aprobadas (once nuevas FEAT-018 y regresiones de seguimiento/importación) en 89.15 segundos, `ENTORNO=desarrollo`, `TEST_DB_SUFFIX=feataudit`. Sólo advertencia heredada de Starlette/httpx. La primera ejecución sin sobrescribir entorno encontró COOKIE_SEGURA incompatible con configuración de producción; el ajuste fue sólo del proceso de pruebas.
- Revisión secundaria de interfaz: se comunicaron correcciones de permisos de enlaces, tarjetas, resumen y acciones de devolución. La tarea principal integra esos ajustes y valida tipos/construcción.

## Riesgos o deuda pendiente

- Falta recorrido manual y medición con una carga real de 3000 trabajadores. Las pruebas comprueban SQL con agrupación y paginación; no acreditan rendimiento físico ni sesión Android.
- La tarea principal integra documentación global y validación general. Este reporte no acredita como terminadas las veinte features.

## Documentación actualizada

- Este reporte complementa el brief FEAT-018 y la matriz inicial `estado-features-001-020.md`; los documentos globales de API, datos y reglas quedan bajo integración de la tarea principal.

## Siguiente acción

Completar suite ampliada, integrar correcciones de revisión, ejecutar verificaciones globales y demostrar el recorrido por permisos en web/Android.
