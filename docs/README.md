# Documentación del proyecto

Plan de desarrollo del sistema de control de herramientas y EPP para el Reto IMHOTEP (Hacka ITLAC 2026, Track 3). Sigue la guía "De la idea al MVP": cada documento elimina una clase de duda antes de que llegue al código.

Regla de uso: **los documentos globales orientan, los briefs pequeños autorizan, el repositorio confirma y las pruebas demuestran.**

## Mapa

| Paso de la guía | Documento | Responde | Estado |
|---|---|---|---|
| 1. Contexto | [context.md](context.md) | ¿Qué idea teníamos? | Antecedente |
| 2. Descubrimiento | [01-descubrimiento.md](01-descubrimiento.md) | ¿Qué sabemos, qué asumimos y qué falta? | Escrito |
| 3. PRD | [product/prd.md](product/prd.md) | ¿Qué producto y para quién? | Por aprobar |
| 3. Reglas | [product/reglas-de-negocio.md](product/reglas-de-negocio.md) | ¿Cómo debe comportarse? | Por aprobar |
| 4. Alcance | [product/mvp-scope.md](product/mvp-scope.md) | ¿Qué se construye primero y qué no? | Por aprobar |
| 5. Flujos | [product/app-flow.md](product/app-flow.md) | ¿Cómo lo recorre cada rol? | Escrito |
| 5. Escenarios | [product/escenarios.md](product/escenarios.md) | ¿Aguanta el plan lo que pasa en la planta? | Escrito |
| 6. UI/UX | [product/ui-ux.md](product/ui-ux.md) | ¿Cómo se ve y se comporta? | Escrito |
| 7. TRD | [architecture/trd.md](architecture/trd.md) | ¿Cómo se construye? | Escrito |
| 7. Complementos | [overview](architecture/overview.md), [datos](architecture/data-model.md), [API](architecture/api-contracts.md), [seguridad](architecture/security-model.md), [decisiones](architecture/decisions/) | Módulos, tablas, endpoints, controles y decisiones | Escrito |
| 7. Entorno | [despliegue-local-cloudflare.md](architecture/despliegue-local-cloudflare.md) | ¿Cómo se publica con HTTPS y cómo se respalda? | Compose y respaldo probados; el túnel, sin token real |
| 8. Roadmap | [product/roadmap.md](product/roadmap.md) | ¿En qué orden? | Escrito |
| 9. Historias | [stories/](stories/) | ¿Qué necesidad resuelve cada fase? | Fases 1 a 7 |
| 10. Tareas | En el roadmap (Fase 0 y Fase 7) | ¿Qué cambia en el código? | El resto se planea por historia |
| Segunda ola | [features/](features/) | ¿Qué sigue después del núcleo? | Diez briefs ([FEAT-010](features/FEAT-010-tutorial-guiado.md), tutorial guiado de práctica, aprobado y sin construir; [FEAT-009](features/FEAT-009-traspasos-por-lista-de-excel.md), traspasos por lista de Excel, está aprobado y construido en el código, salvo TR-10); [FEAT-008](features/FEAT-008-administracion-de-almacenes-y-tablero.md) (almacenes, tablero y menú) aprobado, con sus documentos al día y ya construido |
| Iteración 01 | [releases/iteration_01/README.md](releases/iteration_01/README.md) | ¿Qué cambia con la plática del 8 de octubre (despacho de EPP con aprobación, proyectos, traslados entre almacenes de tercer nivel, inspecciones, bitácora por vale, deudores, app de Android sin conexión)? | Aprobada, con sus dependencias aprobadas el 9 de octubre: FEAT-013 a FEAT-020 y ADR-012 a ADR-015 (sin construir, salvo el contenedor de Android de FEAT-020). [FEAT-012](features/FEAT-012-valor-del-inventario.md) documenta el valor del inventario, ya construido |
| Red de almacenes | [product/red-de-almacenes-y-flujo.md](product/red-de-almacenes-y-flujo.md) | ¿Cómo se da de alta, surte y cierra cada almacén? | Decidido; una pregunta abierta (recibir separado de enviar) |
| Release | [releases/mvp-checklist.md](releases/mvp-checklist.md), [changelog](releases/changelog.md), [guía del almacenista](guia-almacenista.md), [guía por rol](guia-por-rol.md) | ¿Cuándo está terminado, qué trae y cómo se usa? | Escritos; la checklist se va marcando |
| Plantillas | [templates/](templates/) | Historias, FEAT, FIX, TECH, ADR, reporte y prompts | Listas |

Fuentes del reto: [el PDF](HackaItlacTrack3_2026.pdf) y la carpeta [info_track/](info_track/). Las instrucciones para agentes están en [AGENTS.md](../AGENTS.md), en la raíz.

Preparación de la exposición: [guion de cinco minutos, restricciones y mejoras prioritarias](guion-demo-cinco-minutos.md), con su [reporte de revisión](releases/reporte-preparacion-demo.md).

## Pasos a seguir

1. **Aprobar el producto.** Leer [prd.md](product/prd.md) y [mvp-scope.md](product/mvp-scope.md). Lo que no convenza se corrige ahí antes de programar. Revisar en especial las decisiones abiertas de abajo.
2. **Crear el túnel.** Seguir [despliegue-local-cloudflare.md](architecture/despliegue-local-cloudflare.md) y guardar el token en `.env`.
3. **Fase 0, fundación.** Ejecutar las tareas TASK-F0-01 a TASK-F0-06 del [roadmap](product/roadmap.md) y cerrar su gate.
4. **Fases 1 a 6, una por una.** Para cada historia de la fase, seguir el ciclo de abajo. No se pasa de fase con el gate abierto.
5. **Fase 7, confiabilidad.** Construir la cancelación de vales y ejecutar sus tareas; el flujo principal debe completarse sin tocar la base de datos.
6. **Segunda ola.** Construir las features en orden, empezando por [FEAT-001](features/FEAT-001-vale-como-prueba.md), solo si el gate de la Fase 7 está cerrado. [FEAT-006](features/FEAT-006-control-de-acceso-configurable.md) es la excepción: puede avanzar en paralelo, en una rama aparte, desde el cierre de la Fase 1.
7. **Fase 8, release.** Completar [mvp-checklist.md](releases/mvp-checklist.md): servidor, entregables del PDF, ensayo y pitch.

## Ciclo de una historia

1. **Planear contra el repositorio.** Con el primer prompt de [templates/prompts.md](templates/prompts.md) se obtiene el análisis de impacto y las tareas `TASK-…`. No se modifica nada todavía.
2. **Implementar tarea por tarea.** Cada tarea termina con sus pruebas y el reporte de [templates/reporte.md](templates/reporte.md).
3. **Validar.** Pruebas, lint, verificación de tipos y construcción.
4. **Revisión independiente.** La hace alguien distinto de quien implementó, con el tercer prompt.
5. **Cerrar.** Se demuestran los criterios de aceptación y se actualizan los documentos afectados.

## Dónde se registra cada cambio

| Lo que aparece | Dónde va |
|---|---|
| Una capacidad nueva | `features/FEAT-NNN-nombre.md` |
| Un comportamiento incorrecto | `fixes/FIX-NNN-nombre.md` |
| Una mejora interna, de rendimiento o de seguridad | `technical/TECH-NNN-nombre.md` |
| Una decisión costosa de revertir | `architecture/decisions/ADR-NNN-nombre.md` |

La carpeta `fixes/` ya existe con [FIX-001](fixes/FIX-001-etiquetas-de-piezas-sin-alcance.md) (las etiquetas de piezas no respetan el alcance por almacén; abierto). `technical/` se crea con su primer brief. Las plantillas están en [templates/](templates/).

## Decisiones abiertas

Tomadas para poder escribir el plan; conviene confirmarlas antes de la Fase 1.

| Decisión | Lo que se asumió | Dónde está |
|---|---|---|
| Qué significa "elegir qué va en cada categoría" | Categorías de artículos con plantilla de reglas, tres requisitos especiales por artículo, e inactivar y reactivar | Reglas, sección 5; [ADR-003](architecture/decisions/ADR-003-catalogo-configurable.md) |
| Orden de construcción | Cortes verticales por fase, no todo el backend primero | [Roadmap](product/roadmap.md) |
| Idioma del código | Términos del dominio en español, sin acentos | [AGENTS.md](../AGENTS.md) |
| Quién administra el catálogo | Compras y supervisor; el costo solo Compras | Reglas, sección 8 |
| Vigencia de inspección | 180 días, editable por artículo | Reglas, sección 5.4 |
| Categorías iniciales | Siete, editables | Reglas, sección 5.1 |
| Qué trae cada rol inicial | Los permisos de la tabla; el Administrador, todos | Reglas, sección 8.2 |

Ya decididas con el equipo: identificadores UUID y folio por contador ([ADR-006](architecture/decisions/ADR-006-identificadores-uuid-y-folio.md)), permisos por clave con roles como datos ([ADR-007](architecture/decisions/ADR-007-permisos-por-clave.md)) y gráficas del tablero con recharts ([ADR-009](architecture/decisions/ADR-009-graficas-con-recharts.md)), códigos y series de pieza ([ADR-010](architecture/decisions/ADR-010-codigos-y-series-de-pieza.md)). Con la iteración 01: proyectos y varios almacenes por usuario ([ADR-012](architecture/decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md)), notificaciones push por PWA ([ADR-013](architecture/decisions/ADR-013-notificaciones-push-por-pwa.md)), app de Android con Capacitor ([ADR-014](architecture/decisions/ADR-014-app-android-con-capacitor.md)) y operación sin conexión del almacenista ([ADR-015](architecture/decisions/ADR-015-operacion-sin-conexion-del-almacenista.md)), que reemplaza en parte a ADR-004.

## Estado de los gates

Lo construido está en el [changelog](releases/changelog.md); lo que falta del release, en la [checklist](releases/mvp-checklist.md).

- [x] Descubrimiento: usuarios, problema e incógnitas identificados.
- [ ] PRD: escrito; falta la aprobación del equipo.
- [ ] Alcance del MVP: escrito; falta la aprobación del equipo.
- [x] App flow: cada camino del MVP tiene entrada, salida y errores.
- [x] UI/UX: cada pantalla tiene comportamiento y estados. No hay maquetas.
- [x] TRD: arquitectura, datos, contratos y seguridad definidos. Las decisiones de la Fase 0 ya se tomaron (sección 16).
- [x] Fase 0 (construida): un solo desplegable con Docker, base con migraciones, interfaz servida por FastAPI y comandos comprobados. Falta lo que depende del dueño del dominio: el túnel con un token real y la lectura de un QR con la cámara de un celular por HTTPS.
- [x] Fases 1 a 6: acceso y catálogo, entrega, límite y autorización, devolución y baja, traspasos, consulta, reportes e importación, construidas en backend y en la interfaz.
- [ ] Fase 7: construidos la cancelación de vales, el respaldo con su restauración y la verificación de consistencia. Pendiente el ensayo manual del flujo principal en el entorno publicado y, desde un celular, la revisión de estados de pantalla.
- [ ] Fase 8: en curso, ver la checklist.
