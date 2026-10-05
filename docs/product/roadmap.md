# Roadmap de implementación del MVP

Divide el [alcance](mvp-scope.md) en fases pequeñas, ordenadas por dependencias. Cada fase es un corte vertical: termina con pantalla, API, datos y pruebas, y con un gate que se puede demostrar. No se avanza con un gate abierto.

Las historias están en [stories/](../stories/). Las tareas técnicas de cada historia se planean contra el repositorio justo antes de implementarla (ver [README](../README.md)).

## Fase 0 — Fundación

**Resultado.** Proyecto ejecutable, desplegable y con la cámara probada.

**Tareas.** No tiene historias de usuario.

| Tarea | Salida verificable |
|---|---|
| TASK-F0-01 Backend ejecutable | `backend/main.py` pasa a `backend/app/main.py` con una aplicación FastAPI y `GET /api/salud`; `config.py` y `db.py`; `pytest` y `ruff` como dependencias de desarrollo. |
| TASK-F0-02 Base de datos | MySQL en Docker Compose; Alembic iniciado y una migración que corre. |
| TASK-F0-03 Interfaz de una sola página | `ssr: false`; sin la pantalla de bienvenida; cliente de la API; página temporal de prueba del escáner. |
| TASK-F0-04 Un solo desplegable | `Dockerfile` en la raíz; el servidor entrega la interfaz; `docker-compose.yml` con base, aplicación y túnel; `.env.example`; se retira `frontend/Dockerfile`. |
| TASK-F0-05 Prueba de cámara | Desde un celular, por el subdominio, se lee un QR y un código de barras; queda elegida la librería. |
| TASK-F0-06 Comandos reales | README raíz y [AGENTS.md](../../AGENTS.md) con los comandos comprobados. |

**Dependencias.** Token del túnel de Cloudflare, que crea el dueño del dominio ([guía](../architecture/despliegue-local-cloudflare.md)).

**Gate de salida.**

- `docker compose up -d --build` levanta base, aplicación y túnel.
- `GET /api/salud` responde y confirma la conexión a la base.
- La interfaz carga desde el mismo servidor.
- Pruebas, lint, verificación de tipos y construcción pasan.
- Desde un celular, por HTTPS, la cámara lee un QR.

## Fase 1 — Acceso y catálogo

**Resultado.** Cada rol entra a lo suyo y la empresa define su catálogo.

**Historias.** [US-ACC-001, US-CAT-001, US-CAT-002, US-CAT-003, US-ETQ-001](../stories/fase-1-acceso-y-catalogo.md).

**Incluido.** Sesión; roles como datos y permisos verificados por clave, con los cinco roles iniciales; almacenes y ubicaciones; categorías con plantilla; artículos con requisitos especiales; inactivar y reactivar; registro de cambios; etiquetas QR; datos de prueba.

**Fuera de alcance.** Pantalla para administrar roles y usuarios (FEAT-006); reaplicar plantilla; habilitaciones.

**Gate de salida.**

- Los cinco usuarios de prueba, uno por rol, entran y cada uno ve solo su menú.
- Una petición a un endpoint cuyo permiso no tiene el rol responde 403.
- Compras crea una categoría y un artículo que toma su plantilla.
- Un artículo se inactiva con motivo y se reactiva.
- Una hoja de etiquetas impresa se lee con el celular.

## Fase 2 — Entrega

**Resultado.** Primera mitad del ciclo de valor: del alta del trabajador al vale firmado.

**Historias.** [US-TRB-001, US-INV-001, US-ENT-001, US-ENT-002, US-INS-001, US-ENT-003](../stories/fase-2-entrega.md).

**Incluido.** Alta de trabajador con foto opcional; entrada de inventario; motor de vales para entradas y entregas; escáner con cámara, pistola y teclado; semáforo de código, vigencia, existencias y seguridad; inspección; firma en pantalla; vale con folio y QR.

**Fuera de alcance.** Límites y autorización; devoluciones; exigir la foto para entregar.

**Gate de salida.** Desde un celular, pasos 1 a 3 del flujo principal:

- RH registra a un trabajador y su credencial lo identifica.
- Compras da entrada a EPP, una herramienta y un arnés.
- El almacenista los entrega escaneando; las existencias bajan y la ficha del trabajador los muestra.
- Un arnés no apto, o con la inspección vencida, no se puede entregar.
- El vale tiene folio, firma y QR.

## Fase 3 — Límite y autorización

**Resultado.** Las reglas de entrega que pide el PDF.

**Historias.** [US-LIM-001, US-AUT-001, US-ESP-001](../stories/fase-3-limite-y-autorizacion.md).

**Incluido.** Límite en posesión y por periodo; solicitud de autorización; resolución desde el celular del supervisor o con PIN; artículos que piden autorización en cada entrega.

**Fuera de alcance.** Dotación por puesto; notificaciones push.

**Gate de salida.** Paso 4 del flujo principal:

- Una entrega que excede el límite queda bloqueada con su detalle.
- El supervisor la autoriza desde otro celular y la entrega se completa.
- El vale muestra quién autorizó y por qué.
- Un artículo marcado como de uso especial pide autorización aunque no exceda.

## Fase 4 — Devolución y baja

**Resultado.** Segunda mitad del ciclo de valor: el equipo regresa y el trabajador cierra sin pendientes.

**Historias.** [US-DEV-001, US-BAJ-001, US-TRB-002](../stories/fase-4-devolucion-y-baja.md).

**Incluido.** Devolución por escaneo; condición al volver; rechazo de equipo ajeno; baja con pendientes; vale de no adeudo; reingreso; vigencia por periodo.

**Fuera de alcance.** Cierre sin devolución; equipo dado por perdido.

**Gate de salida.** Paso 6 del flujo principal:

- Al iniciar la baja se ven los pendientes de todos los almacenes.
- Tras devolverlos se emite el vale de no adeudo y el trabajador queda inactivo.
- Un trabajador con contrato vencido no recibe nada.
- Tras el reingreso vuelve a recibir y conserva su historial.

## Fase 5 — Traspasos

**Resultado.** La red de almacenes funciona.

**Historias.** [US-TRS-001, US-TRS-002](../stories/fase-5-traspasos.md).

**Incluido.** Salida, tránsito, recepción con QR, recepción con diferencias.

**Fuera de alcance.** Cancelar traspasos; cierre de almacén.

**Gate de salida.** Paso 5 del flujo principal:

- Un traspaso de Kepler a Contratistas, y otro de Contratistas a Midrex, se envían y se reciben.
- Las existencias cuadran en origen, tránsito y destino en cada momento.
- El historial de una pieza muestra su recorrido completo.

## Fase 6 — Consulta, reportes e importación

**Resultado.** La información sale tan rápido como entra, y el inventario se carga de una vez.

**Historias.** [US-CON-001, US-REP-001, US-REP-002, US-IMP-001](../stories/fase-6-consulta-reportes-e-importacion.md).

**Incluido.** Escaneo universal; búsqueda por texto; fichas; cuatro reportes con CSV (existencias, movimientos, adeudos y consumo); importación con relación de columnas.

**Fuera de alcance.** Gráficas; reporte de valor del inventario.

**Gate de salida.**

- "Detector" en la búsqueda muestra quién tiene cada uno.
- Los cuatro reportes coinciden con lo operado en las fases anteriores.
- Un Excel preparado por alguien ajeno al sistema se importa sin tocar la base de datos.

## Fase 7 — Confiabilidad

**Resultado.** El flujo completo resiste errores, permisos y uso simultáneo.

**Historias.** [US-CAN-001](../stories/fase-7-confiabilidad.md).

**Tareas.**

| Tarea | Salida verificable |
|---|---|
| TASK-F7-01 Guion completo | Una sola prueba recorre los seis pasos del flujo principal. |
| TASK-F7-02 Permisos | Una prueba por permiso: con él, el endpoint responde; sin él, 403. Otra compara los roles iniciales con la sección 8.2 de las reglas. |
| TASK-F7-03 Uso simultáneo | Dos confirmaciones de la misma pieza: una gana y la otra recibe el cambio; un doble envío no duplica el vale. |
| TASK-F7-04 Estados de pantalla | Carga, vacío, error y sin conexión revisados en cada pantalla, en celular y en computadora. |
| TASK-F7-05 Respaldo | Respaldo y restauración probados; comparación entre bitácora y existencias sin diferencias. |
| TASK-F7-06 Revisión independiente | El motor de movimientos lo revisa alguien distinto de quien lo escribió; hallazgos bloqueantes corregidos. |

**Gate de salida.** Todas las pruebas pasan; el flujo principal se completa a mano en el entorno publicado, sin intervención en la base de datos; una entrega capturada por error se cancela desde la pantalla y las existencias regresan.

## Segunda ola — Features

Después del gate de la Fase 7, en este orden. Cada una tiene su brief y su propio criterio de aceptación.

1. [FEAT-001](../features/FEAT-001-vale-como-prueba.md): vale como prueba.
2. [FEAT-002](../features/FEAT-002-cierre-de-almacen.md): cierre de almacén y valor del inventario.
3. [FEAT-003](../features/FEAT-003-dotacion-por-puesto.md): dotación por puesto.
4. [FEAT-004](../features/FEAT-004-minimos-y-estados.md): mínimos y estados de pieza.
5. [FEAT-005](../features/FEAT-005-identidad-con-foto.md): identidad con foto. Pasó al MVP como foto opcional en el alta (Fase 2); el brief queda como referencia.

En paralelo, sin competir por ese orden: [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md), control de acceso configurable. Puede avanzar en una rama aparte desde el cierre de la Fase 1, porque su base ya queda en esa fase ([ADR-007](../architecture/decisions/ADR-007-permisos-por-clave.md)). Se integra solo si pasa sus criterios y no hay un gate abierto.

## Fase 8 — Release

**Resultado.** MVP desplegado, con sus entregables y listo para la demostración.

**Incluido.** Paso al servidor; datos de prueba y usuarios por rol; entregables del PDF; guía del almacenista; ensayo cronometrado; video de respaldo.

**Gate de salida.** [mvp-checklist.md](../releases/mvp-checklist.md) completo.

## Riesgos y orden de dependencias

- La Fase 0 va primero porque la cámara por HTTPS es el mayor riesgo técnico y desbloquea todo lo demás.
- La Fase 2 construye el motor de movimientos; las fases 3, 4 y 5 lo extienden. Un error ahí se multiplica, por eso cada fase agrega pruebas al guion.
- La importación va en la Fase 6, pero es indispensable para la demostración: no se recorta.
- Las features de la segunda ola no se empiezan con un gate anterior abierto.

## Calendario objetivo

Es una meta, no un compromiso: manda el gate.

| Día | Meta |
|---|---|
| Domingo 4 de octubre | Fases 0 y 1 |
| Lunes 5 | Fases 2 y 3 |
| Martes 6 | Fases 4, 5 y 6 |
| Miércoles 7, hackathon | Fase 7, FEAT-001 y FEAT-002; cargar los datos que entreguen |
| Jueves 8, hackathon | Fase 8, ensayo y pitch |

Regla de recorte: si al cierre del martes la Fase 6 no pasó su gate, las features se recortan empezando por la última. La Fase 7 y la Fase 8 no se recortan.

## Trabajo pospuesto

Lo listado como pospuesto en [mvp-scope.md](mvp-scope.md): lista de revisión, cierre sin devolución, pérdidas, reporte de EPP por trabajador, habilitaciones y solicitud de compra. El modo sin conexión está excluido.
