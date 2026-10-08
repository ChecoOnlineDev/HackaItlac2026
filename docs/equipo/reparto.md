# Reparto del equipo

Propuesta para repartir el trabajo del hackathon entre cinco personas: **Angel, Edgar, Pedro, Sergio y Uriel** (los nombres salen de las ramas del repositorio). La asignación de rol es una sugerencia: se puede cambiar entre ustedes, pero cada rol debe tener **un dueño** que sepa recorrerlo de memoria.

Documentos de apoyo:
- [FEAT-011](../features/FEAT-011-entrada-por-kepler-trazabilidad-y-menu.md): qué se construye.
- [Flujos por rol](../product/flujos-por-rol.md): cómo se recorre cada rol y la prueba del PDF.
- [Preguntas para el track](../preguntas-para-el-track.md): lo que hay que aclarar en las reuniones.
- [Checklist del MVP](../releases/mvp-checklist.md): lo que debe quedar marcado.

## Cómo se trabaja

1. **Una rama por persona** (`Angel`, `Edgar`, `Pedro`, `Sergio`, `Uriel`). Se parte de `backend/mvp`.
2. **Dos personas no editan el mismo archivo.** La tabla de zonas de abajo dice quién toca qué. Si se necesita algo de otra zona, se pide a su dueño.
3. **Sergio integra:** junta las ramas en `backend/mvp` en el orden de la sección «Orden de integración» y resuelve conflictos.
4. **Cada regla lleva su prueba** con el ID en el nombre (`EK-01`, `TR-11`, `SG-01`, `AC-30`…) y cada cambio de regla, permiso o API actualiza su documento en el mismo cambio (ver `AGENTS.md`).
5. **Antes de entregar a Sergio:** `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build` en verde.
6. **No se suben secretos** ni el `.env`. Los usuarios de prueba están en `credenciales-prueba.local.md`.

## Zonas de trabajo

| Zona | Archivos | Dueño |
|---|---|---|
| Entrada a Kepler, almacenes | `movimientos/tipos/entrada.py`, `almacenes/service.py`, `importacion/analisis.py` | Sergio |
| Dar entrada (pantalla), importación, Excel de ejemplo | `routes/inventario/entrada-nueva.tsx`, `importar.tsx`, `componentes/importacion/`, `importacion/plantilla.py` | Pedro |
| Traspasos y bitácora | `routes/operacion/trasladar.tsx`, `componentes/traspasos*/`, `consulta/repository.py` (reporte de movimientos), `service_traspasos.py` | Edgar |
| Seguimiento y resguardo | `consulta/repository_seguimiento.py`, `routes/consulta/` (artículo, pieza, seguimiento), `componentes/seguimiento/` | Angel |
| Permisos, roles y personas | `acceso/` (permisos, seed, roles), `routes/acceso/` | Uriel |
| Menú y rutas | `routes.ts`, `sesion/menu.ts`, armazones | Sergio, **al final** |
| Tutorial | `componentes/tutorial/`, `api/practica.ts` | Angel |

## Quién hace qué

### Angel — Almacenista · trazabilidad de lo entregado

- **Rol que domina en la demostración:** Almacenista. Entregar, pedir autorización, devolver, consultar y rastrear.
- **Código (FEAT-011, frente C):**
  - Seguimiento con pestañas Piezas y Por cantidad (SG-01).
  - Ficha de artículo con la tabla «Quién lo tiene» y «Ver detalle» (SG-02).
  - Línea de tiempo en la ficha de pieza (SG-03).
  - Vista «Piezas y resguardos» con `resguardo.ver` y la tarjeta «Alto valor fuera del almacén» (SG-04).
  - Aviso de pieza de alto valor con un trabajador dado de baja (SG-06).
- **Tutorial (FEAT-010):** cerrar las pruebas pendientes: PWA instalada, «reducir movimiento», solo teclado, Devolver y Consultar en móvil, y las pruebas automáticas.
- **Pruebas que debe poder hacer sin ayuda:** flujos 3.1 a 3.4 de [flujos por rol](../product/flujos-por-rol.md), y los pasos 2 y 3 del PDF.
- **Hecho cuando:** un almacenista nuevo completa los cuatro recorridos del tutorial sin ayuda y Seguimiento ya no da cero al entregar herramientas por cantidad.

### Edgar — Supervisor · traspasos y bitácora

- **Rol que domina en la demostración:** Supervisor. Enviar, autorizar, y ver la bitácora del almacén.
- **Código (FEAT-011, frente B y SG-05):**
  - El buscador y el escaneo de Trasladar solo ofrecen lo que hay en el origen, con la cantidad disponible (TR-11).
  - La vista previa del Excel sale sola, de 12 en 12; «Relacionar columnas» solo si no se reconocen (TR-12).
  - Columna `nombre` reconocida (TR-13).
  - Bitácora del almacén con lo que llega y las entradas, permiso `bitacora.ver`, filtros por pieza y serie (SG-05).
- **Pruebas que debe poder hacer sin ayuda:** flujos 4.1 y 4.2, el paso 4 del PDF, y el camino alterno de filas en error.
- **Hecho cuando:** un traspaso de Contratistas a Midrex, armado por Excel, se recibe y aparece en la bitácora de los dos almacenes.

### Pedro — Compras · entrada de inventario y datos reales

- **Rol que domina en la demostración:** Compras. Dar entrada a Kepler, catálogo y solicitudes.
- **Código (FEAT-011, frente A en pantalla):**
  - Pantalla única «Dar entrada» con dos métodos, a mano o desde Excel, sin selector de almacén (EK-03, EK-04).
  - Plantilla e importación sin columna de almacén.
  - Compras urgentes: el vale de entrada queda en Kepler (EK-05).
- **Datos:**
  - Archivo de ejemplo de traspaso en `docs/recursos/` (TR-14).
  - Convertir `comprasejer2026.xlsx` (350 renglones) en una carga de Kepler: clasificar cada renglón por categoría y por cantidad o pieza, y anotar las dudas para el track.
  - Ajustar el seed para que **no se surta EPP a los almacenes de proyecto**.
- **Pruebas que debe poder hacer sin ayuda:** flujos 5.1 y 5.2.
- **Hecho cuando:** la carga inicial se hace por Excel a Kepler y llega a Midrex solo por traspaso.

### Uriel — RH · permisos, roles y personas

- **Rol que domina en la demostración:** RH. Alta, credencial, baja y no adeudo.
- **Código (FEAT-011, frente D sin el menú):**
  - Los siete permisos nuevos y su migración (AC-30).
  - Ajustes a los roles iniciales: Supervisor sin límites, RH con `vales.ver`, Supervisor y Almacenista con `traspasos.recibir` (AC-31).
  - Protección del Administrador (AC-32) y seed que no pisa lo editado (AC-33).
  - Pantalla «Personas y accesos» con filtro «Sin almacén» y acción «Cambiar almacén» (AC-35, parte de personas).
- **Pruebas que debe poder hacer sin ayuda:** flujos 6.1 y 6.2, los pasos 1 y 5 del PDF, y la prueba de permisos de cada rol.
- **Hecho cuando:** quitar `traspasos.recibir` a un rol cambia el menú y el servidor responde 403, y volver a correr el seed no pierde ningún cambio.

### Sergio — Administrador · integración y arquitectura

- **Rol que domina en la demostración:** Administrador, y el hilo conductor del recorrido.
- **Código (FEAT-011, frente A en el servidor y frente D en el menú):**
  - Entrada solo a Kepler en el servidor y su validación (EK-01, EK-02).
  - Validación del tipo del padre al crear un almacén (EK-06).
  - Reescribir las pruebas que suponían entrada a varios almacenes.
  - Menú reducido y rutas nuevas (AC-35), **al final**, cuando todos hayan entregado.
- **Integración:** juntar las ramas en `backend/mvp`, resolver conflictos y verificar que el guion de integración del PDF sigue pasando.
- **Documentos:** actualizar los globales que cambian (reglas, API, flujos, UI) y el ADR de la separación de permisos si se aprueba.
- **Track:** llevar las [preguntas](../preguntas-para-el-track.md) a las reuniones y aplicar las respuestas.
- **Hecho cuando:** `backend/mvp` pasa pruebas, lint, tipos y construcción con las cinco ramas dentro, y el guion de demostración se recorre completo.

## Orden de integración

1. **Primero:** Sergio (entrada a Kepler en el servidor) y Uriel (permisos), porque las demás pruebas dependen de ellos.
2. **Después:** Pedro, Edgar y Angel, en cualquier orden entre sí.
3. **Al final:** Sergio hace el menú y las rutas, y se corrigen los recorridos del tutorial que cambien.
4. Se congela el código a la hora acordada y lo que queda es ensayo, no desarrollo.

## Presentación

Cada persona presenta **su rol**, en 7 minutos. Una estructura sugerida para cada una:

| Minuto | Contenido |
|---|---|
| 0–1 | Qué problema resuelve este rol en la planta |
| 1–5 | Recorrido en vivo de su flujo (ver [flujos por rol](../product/flujos-por-rol.md)) |
| 5–6 | Una regla o caso difícil que el sistema cubre (límite, pieza vencida, diferencia al recibir…) |
| 6–7 | Qué haríamos con más tiempo |

Los 7 minutos conjuntos se arman con el [guion de demostración](../product/flujos-por-rol.md#9-guion-de-demostración-propuesta): problema, prueba en vivo de punta a punta, lo que nos diferencia (tutorial y trazabilidad) y cierre.

> Los tiempos de 7 + 7 minutos son un supuesto del equipo; hay que confirmarlos con el organizador (pregunta 31).

**Todos:**
- Tres ensayos cronometrados, con el celular y la computadora que se usarán.
- Un video de respaldo de la demostración completa.
- Una respuesta de una frase para las preguntas previsibles: sin Internet, herramienta sin etiqueta, validez de la firma, identidad del trabajador, supervisor ausente.

## Qué le toca a cada quien probar en la demostración

| Paso del PDF | Responsable de ensayarlo |
|---|---|
| 1. Registrar un trabajador | Uriel |
| 2. Surtirle EPP y una herramienta por escaneo | Angel |
| 3. Exceder un límite | Angel (pide) y Edgar (autoriza) |
| 4. Traspaso entre almacenes | Edgar (envía) y Angel (recibe) |
| 5. Mostrar pendientes al procesar la baja | Uriel |
| Carga inicial por Excel a Kepler | Pedro |
| Permisos en vivo | Sergio |

## Riesgos del reparto

- **Sergio concentra la integración.** Si se atrasa el menú, queda el menú actual; la funcionalidad no depende de él.
- **El Frente D es el más amplio.** Si no alcanza el tiempo, se entregan los permisos (Uriel) y se deja el menú como está.
- **Datos reales.** Pedro depende de las respuestas del track sobre la clave del Excel; si no llegan, clasifica con el nombre del artículo.
- **Dos personas con la misma pantalla.** Vigilar la tabla de zonas; Angel y Edgar tocan `consulta/` por caminos distintos y deben avisarse.
