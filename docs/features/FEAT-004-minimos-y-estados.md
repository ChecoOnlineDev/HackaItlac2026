# FEAT-004: Mínimos, estados de pieza y alertas

**Estado (8 oct 2026): servidor construido; interfaz y validación integral en curso.** Migración `0013_minimos`, configuración por almacén con `inventario.minimos`, disponibles/no disponibles, filtro de agotados y avisos E-14/X-05. El endpoint de estado admite mantenimiento y calibración con P-06; regreso sin inspección sólo cuando el artículo no la exige. Las pruebas específicas están en `backend/tests/test_minimos_feat004.py`; el cierre de esta feature exige terminar la pantalla y sus recorridos.

## Problema u oportunidad

La empresa quiere una alerta antes de quedarse sin un equipo, y hay equipo que no está ni en el almacén ni con un trabajador porque se mandó a mantenimiento o a calibración (plática min 46–47 y 50). El MVP solo distingue Apto y No apto, y no conoce mínimos.

## Objetivo

Que Compras vea en rojo lo que está por agotarse, contando solo lo que de verdad se puede entregar.

## Historia de usuario

Como Compras, quiero fijar un mínimo por artículo y almacén y ver cuáles están por debajo, para surtir antes de que falte.

Como almacenista, quiero marcar una pieza como "en mantenimiento" o "en calibración", para que el sistema no la cuente como disponible.

## Alcance incluido

- Mínimo por artículo y almacén.
- El inventario separa disponible de no disponible (No apto, en mantenimiento, en calibración).
- Estados nuevos de pieza: En mantenimiento y En calibración, con observación; mientras tanto no se entrega.
- El inventario marca en rojo lo que está por debajo del mínimo; filtro "por debajo del mínimo".
- Aviso amarillo en la entrega o el traspaso que deja al almacén por debajo del mínimo.

## Fuera de alcance

- Notificaciones push o por correo.
- Solicitud de compra automática.
- Agenda de mantenimiento o de calibración.

## Criterios de aceptación

- Dado un mínimo de 5 y 6 disponibles, cuando se entregan 2, entonces el renglón avisa en amarillo y el inventario muestra el artículo en rojo.
- Dado un artículo con 3 piezas en almacén y 2 en calibración, entonces el disponible es 1.
- Dada una pieza en mantenimiento, entonces la entrega la bloquea en rojo.
- Regresar una pieza de mantenimiento o calibración a Apto exige una inspección si su artículo la requiere; si no, basta marcarla.
- Sin mínimo configurado, no hay alerta.

## Módulos relacionados conocidos

`catalogo` (mínimos), `inspecciones` (estados), `almacenes` (disponibles), `movimientos` (reglas E-14 y X-05).

## Cambios de datos o API esperados

- Tabla `minimo`.
- `PUT /api/almacenes/{id}/minimos`; `POST /api/piezas/{id}/estado` admite los estados nuevos; las existencias responden `disponible` y `no_disponible`.

## Restricciones y compatibilidad

- Los valores de estado ya existen en el modelo desde el MVP; esta feature agrega la pantalla y las reglas.

## Riesgos

- El disponible de artículos por cantidad es igual a la existencia: no tienen estado por unidad.

## Validaciones requeridas

- Pruebas del cálculo de disponible y de las reglas E-14 y X-05.

## Documentos globales que podrían actualizarse

`data-model.md`, `api-contracts.md`, `ui-ux.md` (inventario), `reglas-de-negocio.md` (I-05, P-06).
