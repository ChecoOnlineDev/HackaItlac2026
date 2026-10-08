# FEAT-011: Entrada solo por Kepler, trazabilidad de lo entregado y menú simplificado

Estado: **en construcción: backend de A, B, C y D listo; falta frontend (Dar entrada, menú, Personas y accesos).** Amplía el alcance del MVP y cambia reglas (I-01, AC-06, SC-06, C-13) y permisos de la sección 8. Las reglas de roles de la sección D llevan los IDs AC-30 a AC-35 en [reglas-de-negocio.md](../product/reglas-de-negocio.md) (AC-24 ya era de las cookies de sesión). Las decisiones que dependen del usuario están en «Decisiones abiertas».

## Problema u oportunidad

La revisión del sistema contra el reto y la plática del track encontró cuatro problemas:

1. **La entrada de inventario no sigue la red de almacenes.** Hoy el Administrador puede dar entrada a cualquier almacén, y la regla I-01 deja cargar la carga inicial donde sea. En la operación real la mercancía sale de Kepler, pasa por Contratistas (donde empieza la entrega a trabajadores) y llega a los proyectos por traspaso.
2. **Los traspasos no guían a quien los arma.** El buscador y el escaneo de Trasladar ofrecen todo el catálogo, no lo que hay en el origen; la vista previa del Excel no sale sola al cargar el archivo; y la bitácora de un almacén no registra lo que le llega por traspaso.
3. **No se puede rastrear lo entregado.** Seguimiento de piezas solo cuenta piezas individuales y sale en cero cuando se entregaron herramientas por cantidad (flexómetro, marro, cincel). «Quién tiene qué» es una lista corta en la ficha del artículo, y el almacenista no tiene una vista propia.
4. **Hay demasiados módulos y permisos gruesos.** El menú tiene unas 25 entradas, Personal y Usuarios se solapan, el Supervisor puede cambiar los límites de entrega que debería respetar, el seed pisa los permisos editados en `/roles`, y cuatro permisos de la sección 8.3 no los usa ningún endpoint.

## Objetivo

Que cada pieza y cada cantidad entregada se pueda ubicar con quién la tiene, desde cuándo y con qué vale; que el inventario entre a la red por un solo punto y fluya por traspaso; y que cada rol llegue a lo que hace con menos módulos y permisos más finos.

## Historia de usuario

Como almacenista, quiero ver en un par de toques quién tiene cada herramienta, aunque sea de poco valor, para localizarla sin buscar en vales.

Como supervisor, quiero ver todo lo que entra, sale y llega a mi almacén, para responder por él.

Como Compras, quiero cargar lo comprado solo en Kepler, para que el resto de los almacenes lo reciban por traspaso, con el mismo orden que la planta.

Como administrador, quiero decidir con permisos finos qué hace cada rol, incluido quién puede recibir traspasos, para ajustar la operación sin tocar código.

Todavía no hay historias en `docs/stories/`: se escriben al aprobarse la feature.

## Alcance incluido

### A. Entrada solo por Kepler (reglas EK)

- **EK-01.** La entrada de proveedor y la importación de inventario (altas y reposición) entran **únicamente al almacén central (Kepler)**. El servidor resuelve el almacén central por su tipo; no se acepta otro destino.
- **EK-02.** La carga inicial también entra por Kepler y se reparte por traspaso.
- **EK-03.** Se quita el selector de almacén de «Entrada de proveedor» y la columna `almacen` de la plantilla y de la importación; el texto de la pantalla dice que entra a Kepler.
- **EK-04.** Entrada de proveedor e importación se presentan como **una sola pantalla «Dar entrada»** con dos métodos: capturar a mano o subir un Excel. Conservan la diferencia entre Alta (crea artículos) y Reposición (solo suma).
- **EK-05.** Una solicitud de compra urgente ingresada queda ligada a un vale de entrada de **Kepler**; el almacén que la pidió la recibe después por traspaso (SC-06 se ajusta). *Supuesto, ver decisiones abiertas.*
- **EK-06.** Al crear o editar un almacén, el servidor valida el tipo del padre: un proyecto depende de un subalmacén y un subalmacén del central, para que la regla de ruta X-03 no se rompa por configuración.
- **EK-07.** Crear un artículo desde «Dar entrada»: si lo buscado en «Capturar a mano» no existe, quien tiene `catalogo.administrar` ve «Crear este artículo» con un formulario corto (nombre, categoría y unidad). La categoría decide si es por cantidad o por pieza y el servidor genera el código `PREFIJO-NNNN` (el mismo consecutivo de la importación en modo Alta). El usuario sigue en la misma pantalla con el renglón agregado, listo para capturar cantidad o marca y serie. Sin el permiso solo ve «Este artículo no existe en el catálogo; pide que lo den de alta».

### B. Traspasos guiados

- **TR-11.** El escaneo y el buscador de Trasladar (y de «Trasladar con una lista») muestran solo lo que tiene existencia en el **almacén de origen elegido**, con la cantidad disponible. Sigue vigente X-02 como validación final del servidor.
- **TR-12.** Al cargar el Excel de traspaso o de importación, la **vista previa aparece sola**, con esqueleto de carga y paginada de **12 en 12**. El paso «Relacionar columnas» solo aparece cuando las columnas no se reconocen.
- **TR-13.** La plantilla de traspaso reconoce una columna `nombre` como ayuda para quien arma el archivo, sin aviso, y compara el nombre con el catálogo para detectar un código mal escrito (se avisa, no se bloquea).
- **TR-14.** Se entrega un archivo de ejemplo lleno de traspaso en `docs/recursos/` (ver [las preguntas para el track](../preguntas-para-el-track.md), sección «Ejemplo de plantilla de traspaso»).
- **TR-15.** La cadena Kepler, Contratistas y proyectos sigue siendo X-03. Una ruta distinta la hace solo quien tiene `almacenes.todos`, con observación obligatoria.

### C. Trazabilidad y bitácora (reglas SG)

- **SG-01.** Seguimiento tiene dos pestañas: **Piezas** (como hoy, con serie) y **Por cantidad** (a quién se entregó cuánto, desde cuándo y con qué vale). Con ello Seguimiento deja de dar cero cuando solo hay entregas por cantidad. Se actualiza C-13.
- **SG-02.** La ficha de un artículo por cantidad muestra «Quién lo tiene» como tabla con trabajador, cantidad, fecha y folio, y un botón «Ver detalle». En un artículo por pieza muestra además el código y la serie de cada pieza.
- **SG-03.** La ficha de una pieza muestra una **línea de tiempo**: cada movimiento con quién la entregó, a quién, el vale, la fecha, la condición y el almacén.
- **SG-04.** Permiso nuevo `resguardo.ver`: el almacenista ve «quién tiene qué» con alcance de su almacén (AC-06) y una tarjeta en el inicio «Alto valor fuera del almacén».
- **SG-05.** Permiso nuevo `bitacora.ver`: la bitácora de un almacén incluye lo que **sale, lo que llega** (traspasos recibidos) y **las entradas**, con quién, qué y cuándo. Se puede filtrar por pieza o serie, y cada renglón enlaza al vale y al trabajador. «Mis movimientos de hoy» pasa a ser el filtro «Solo los míos».
- **SG-06.** Aviso cuando una pieza de alto valor queda en resguardo de un trabajador dado de baja o con contrato vencido.
- **SG-07.** Se confirma que todo lo de alto valor y alturas es **por pieza con serie** (C-06); lo demás es por cantidad. La definición exacta depende de la respuesta del track (preguntas 11 y 15).

### D. Roles, permisos y menú (reglas AC)

- **AC-30.** Permisos nuevos seleccionables en `/roles`:

  | Permiso | Para qué |
  |---|---|
  | `bitacora.ver` | Bitácora de un almacén |
  | `resguardo.ver` | «Quién tiene qué» |
  | `inventario.importar` | Separar importar de capturar a mano |
  | `catalogo.limites` | Cambiar límites y requisitos de entrega, separado de `catalogo.administrar` |
  | `piezas.marcar_estado` | Pasar una pieza a mantenimiento o calibración |
  | `acceso.usuarios` y `acceso.roles` | Separar usuarios de roles |
  | `auditoria.ver` | Ver la auditoría de cambios |

- **AC-31.** Roles iniciales: el Supervisor deja de tener `catalogo.limites`; RH gana `vales.ver`; Supervisor y Almacenista traen `traspasos.recibir`; el Almacenista gana `resguardo.ver` y puede ver su bitácora; los cuatro permisos de 8.3 sin uso se ocultan o se asignan a quien dice la sección 8.3.
- **AC-32.** El rol Administrador queda protegido también contra perder `almacenes.todos` y `almacenes.administrar`.
- **AC-33.** El script de datos de prueba **no pisa** los permisos editados en `/roles` al volver a correr; solo crea lo que falta.
- **AC-34.** Quién recibe traspasos se puede cambiar siempre desde `/roles`: solo el supervisor, solo el almacenista, o ambos.
- **AC-35.** Menú reducido de unas 25 entradas a unas 10: Traspasos (Enviar y Recibir), Inventario (Existencias, Movimientos, Piezas y resguardos, Dar entrada), Catálogo (Artículos, Categorías, Puestos, Etiquetas), Compras (Pedir, Mis solicitudes, Cola), Reportes con pestañas y **Personas y accesos** (Usuarios, Roles, Personal por almacén) visible con `acceso.usuarios` o `almacenes.asignar_personal`. No se mezclan existencias y catálogo.

### E. Reparto de EPP y herramientas (sin regla nueva)

- El código **no** impide entregar un tipo de artículo en un tipo de almacén y no se agrega esa restricción. La operación se logra por cómo se surte: el EPP se entrega en Contratistas (y Kepler como alternativa) y la herramienta especializada en el almacén del proyecto, **sin surtir EPP a los almacenes de proyecto**. La semilla de datos y la guía lo reflejan.

## Fuera de alcance

- Una regla que prohíba un tipo de artículo en un tipo de almacén.
- Un tipo de operación «Demo» en el servidor (descartado; la práctica vive en el tutorial, FEAT-010).
- Modo sin conexión y sincronización (siguen excluidos).
- Sello y copia del vale (FEAT-001), mínimos y alertas (FEAT-004), cierre de almacén y valor del inventario (FEAT-002). Son otras features.
- Cambiar la recepción de traspasos, salvo el permiso configurable.
- Crear artículos desde el Excel de traspaso.
- Resolver qué es la «clave» del Excel de compras: depende de la respuesta del track (preguntas 16 a 22).

## Criterios de aceptación

- Dado un usuario con `inventario.entradas`, cuando da entrada por captura o por Excel, entonces la mercancía entra a Kepler y no se ofrece otro almacén; y dado un intento de enviar otro destino por la API, entonces el servidor lo rechaza (EK-01, EK-03).
- Dada una importación con una columna de almacén, entonces se ignora con aviso o se rechaza la fila, y nunca crea una entrada fuera de Kepler (EK-01, EK-02).
- Dado un administrador que crea un proyecto con Kepler como padre, entonces el servidor lo rechaza (EK-06).
- Dado un usuario con `catalogo.administrar` que busca en «Dar entrada» un artículo que no existe, cuando lo crea con una categoría por pieza, entonces queda en el catálogo con un código generado por el servidor y el renglón listo para capturar su pieza en la misma pantalla; y sin ese permiso solo ve el aviso de que pida darlo de alta (EK-07).
- Dado un supervisor armando un traspaso con origen Contratistas, cuando busca o escanea, entonces solo ve lo que hay en Contratistas con su cantidad; y un artículo que no hay se rechaza con X-02 (TR-11).
- Dado un Excel de traspaso con columnas reconocidas, cuando se carga, entonces la vista previa paginada de 12 aparece sola con esqueleto de carga, sin pasar por «Relacionar columnas» (TR-12).
- Dado un Excel con una columna `nombre` distinta a la del catálogo, entonces la fila avisa pero no se bloquea (TR-13).
- Dado un traspaso recibido en Midrex, entonces aparece en la bitácora de Midrex como entrada y en la de Contratistas como salida (SG-05).
- Dada una entrega de flexómetros a un trabajador, entonces Seguimiento, pestaña Por cantidad, lo muestra con el trabajador, la cantidad, la fecha y el folio (SG-01).
- Dado un almacenista, entonces ve «quién tiene qué» de su almacén y no el de otros (SG-04, AC-06).
- Dada una pieza de alto valor, entonces su ficha muestra la línea de tiempo con todos sus movimientos (SG-03).
- Dado el rol Supervisor, entonces no puede cambiar límites de entrega (AC-31); y dado el seed corrido de nuevo, entonces no se pierden los permisos editados (AC-33).
- Dado el Administrador, entonces no puede quitarse `almacenes.todos` ni `almacenes.administrar` (AC-32).
- Dado el rol Almacenista con y sin `traspasos.recibir`, entonces aparece o no la pestaña Recibir, sin leer el nombre del rol (AC-34).
- Dado el menú de cualquier rol, entonces muestra solo las entradas que sus permisos permiten y no más de 10 grupos o entradas principales (AC-35).

## Módulos relacionados conocidos

- `movimientos`: `tipos/entrada.py` (almacén central), `tipos/traspaso.py`, `service.py`. Único que escribe.
- `importacion`: `analisis.py` (almacén), `service_traspasos.py`, plantillas.
- `almacenes`: validación del tipo del padre (`service.py`).
- `consulta`: `repository_seguimiento.py`, `service_seguimiento.py`, reporte de movimientos (`repository.py`, `service.py`), búsqueda y escaneo con filtro por almacén.
- `catalogo`: «quién lo tiene» (`service.py`) y permisos de límites.
- `acceso`: `permisos.py`, `datos_prueba.py` (seed), `service_roles.py`, `dependencias_permisos.py`.
- `solicitudes_compra`: SC-06.
- `auditoria`: pantalla de lectura.
- Frontend: `routes.ts`, `sesion/menu.ts`, `routes/inventario/`, `routes/consulta/`, `routes/supervision/`, `routes/acceso/`, `componentes/traspasos*/`, `componentes/importacion/`, `componentes/seguimiento/`.

## Cambios de datos o API esperados

- **Migración de Alembic:** altas de los permisos nuevos en el catálogo de permisos y asignación a los roles iniciales; sin cambios de tablas de negocio.
- **API:** `GET /api/seguimiento/*` gana el bloque por cantidad y `cantidad` en sus filas; `GET /api/escaneo/{codigo}` y `GET /api/busqueda` aceptan `almacen_id` y devuelven `disponible`; el reporte de movimientos incluye el almacén de destino y las ubicaciones del almacén; los endpoints de entrada y de importación dejan de aceptar almacén destino; los endpoints nuevos exigen `bitacora.ver` o `resguardo.ver`.
- Se actualizan [data-model.md](../architecture/data-model.md) (si hay permisos nuevos en seed), [api-contracts.md](../architecture/api-contracts.md) y la sección 8 de [reglas-de-negocio.md](../product/reglas-de-negocio.md).

## Restricciones y compatibilidad

- Las reglas viven en el servidor; la interfaz muestra lo que el servidor evalúa.
- Las entradas existentes en almacenes distintos de Kepler siguen válidas; solo cambia lo nuevo.
- Los permisos viejos (`catalogo.administrar`, `acceso.administrar`) se conservan hasta migrar los roles; la migración los reemplaza por los nuevos sin quitar acceso a nadie por sorpresa.
- Los movimientos y vales no se actualizan ni se borran; nada de esta feature los modifica.
- Los textos nuevos van en español llano.

## Riesgos

- **Pruebas rotas.** Unas 15 pruebas suponen entrada a varios almacenes (`test_entrada.py`, importación, solicitudes de compra, `test_alcance_roles.py`). Hay que reescribirlas, no borrarlas.
- **Compras urgentes.** Con la entrada solo en Kepler, el almacén solicitante necesita un traspaso adicional; puede sentirse lento en la demostración.
- **Menú y rutas.** Cambiar rutas rompe enlaces, atajos del manifiesto y los recorridos del tutorial (FEAT-010). Hay que migrarlos juntos.
- **Permisos migrados.** Un rol personalizado puede quedar sin acceso si la migración se equivoca; se prueba con los cinco roles iniciales y con uno personalizado.
- **Alcance grande.** Son cuatro frentes; si no hay tiempo se corta por frentes completos, no a medias (ver orden).

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla nueva, con su ID en el nombre (EK-01…, TR-11…, SG-01…, AC-30…).
- La prueba de integración del guion del PDF sigue pasando.
- Recorrido manual en computadora y en vista móvil con los cinco roles.
- Migración arriba y abajo (`alembic upgrade head` y `downgrade`).

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md): I-01, AC-06, SC-06, C-13, sección 8 (permisos y roles iniciales).
- [api-contracts.md](../architecture/api-contracts.md), [data-model.md](../architecture/data-model.md).
- [app-flow.md](../product/app-flow.md): menú, flujos 4, 5, 9, 10, 17 y 18, y pantallas.
- [ui-ux.md](../product/ui-ux.md): pestañas, tabla «Quién lo tiene», línea de tiempo.
- [mvp-scope.md](../product/mvp-scope.md): una entrada nueva, con aprobación.
- [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md): Kepler como punto de partida y Contratistas como inicio de la entrega.
- [guia-almacenista.md](../guia-almacenista.md) y [guia-por-rol.md](../guia-por-rol.md).
- Un ADR si se aprueba separar `acceso.administrar` en usuarios y roles.

## Decisiones abiertas

1. **Compras urgentes (EK-05).** Se supone que el vale de entrada queda en Kepler y el proyecto lo recibe por traspaso. Falta tu confirmación.
2. **Carga inicial (EK-02).** Se supone que también va solo a Kepler.
3. **Equipo de alturas.** Se supone por pieza con serie. Falta la respuesta del track (preguntas 11 y 15).
4. **Quién recibe traspasos.** Se supone Supervisor y Almacenista de inicio, editable en `/roles`.
5. **Dónde se entrega el EPP.** Se supone Contratistas, con Kepler como alternativa. Falta la respuesta del track (pregunta 1).

## Orden de construcción sugerido

1. **Frentes A y B** (entrada, traspasos): cambian el flujo central y las pruebas; hay que hacerlos primero.
2. **Frente C** (trazabilidad): lo que más se nota en la demostración.
3. **Frente D** (permisos y menú): el cambio más amplio; va al final y en una rama aparte.
