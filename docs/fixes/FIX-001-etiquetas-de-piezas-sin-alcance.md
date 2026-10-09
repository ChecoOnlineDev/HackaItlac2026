# FIX-001: Las etiquetas de piezas no respetan el alcance por almacén

Estado: **abierto, sin corregir.** Encontrado el 8 de octubre de 2026 al escribir [FEAT-019](../features/FEAT-019-busqueda-etiquetas-y-diseno-por-dispositivo.md) y confirmado en el código el 9 de octubre.

## Comportamiento actual

`GET /api/etiquetas?tipo=piezas` devuelve el código y el texto de **todas las piezas de todos los almacenes** a cualquier usuario con `etiquetas.imprimir` (de inicio: Supervisor, Compras y RH). El servicio recibe al usuario pero no lo usa para limitar la lista.

## Comportamiento esperado

La lista de piezas para etiquetas sigue el mismo alcance que la ficha de una pieza (AC-06, C-02):

- Con `almacenes.todos`: todas.
- Sin él: las piezas que están en su almacén, las que tiene un trabajador y las que van en tránsito desde o hacia su almacén.
- Sin almacén asignado y sin `almacenes.todos`: ninguna.

Las etiquetas de **estantes** (artículos por cantidad) son catálogo y se ven siempre. Las **credenciales** no cambian con este FIX (ver «Fuera de alcance»).

## Pasos para reproducir

1. Entrar como el supervisor de Midrex.
2. Abrir Etiquetas y elegir «Piezas» (o pedir `GET /api/etiquetas?tipo=piezas`).
3. Aparecen las piezas de Kepler, Contratistas y los demás almacenes, con su código y su serie.

## Evidencia: capturas, logs o prueba fallida

- `backend/app/modulos/catalogo/router.py`, `listar_etiquetas`: pide solo `etiquetas.imprimir`.
- `backend/app/modulos/catalogo/service.py`, `listar_etiquetas`: para `PIEZAS` llama a `self.etiquetas.piezas()` sin pasar el alcance del usuario.
- No hay prueba que cubra el alcance de este endpoint.

## Alcance

- Limitar `tipo=piezas` al alcance de C-02 en el servicio y el repositorio de `catalogo`.
- Una prueba con el ID de la regla (`AC-06`) en el nombre.

## Fuera de alcance

- Las credenciales: hoy quien imprime ve a todos los trabajadores. RH no tiene almacén y los necesita todos; decidir si el Supervisor ve solo a los de sus proyectos depende de [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) y queda como decisión abierta de FEAT-019.
- El PDF de etiquetas y sus tamaños (FEAT-019, UX-05 a UX-07).
- El alcance por conjunto de almacenes (AC-36, FEAT-013): cuando exista, este endpoint lo usa por el mismo camino.

## Causa conocida o hipótesis

El endpoint se construyó en la Fase 1, antes de que AC-06 limitara la vista por almacén (los cambios de «visibilidad por almacén» llegaron después y no pasaron por las etiquetas).

## Criterios de aceptación

- Dado un supervisor de Midrex, cuando pide las etiquetas de piezas, entonces recibe solo las piezas de Midrex, las que tienen trabajadores y las que van en tránsito desde o hacia Midrex (AC-06).
- Dado un usuario con `almacenes.todos`, cuando las pide, entonces recibe todas.
- Dado un usuario con `etiquetas.imprimir` sin almacén y sin `almacenes.todos`, cuando las pide, entonces recibe una lista vacía, no un error.
- Las etiquetas de estantes y de credenciales responden igual que antes.

## Pruebas de regresión

- La prueba nueva del alcance.
- Las pruebas actuales de etiquetas en `backend/tests/test_acceso.py` siguen pasando.
- A mano: la pantalla Etiquetas con un supervisor muestra el estado vacío correcto si su almacén no tiene piezas.

## Plataformas afectadas

Servidor (API). La pantalla Etiquetas no cambia: muestra lo que el servidor devuelve.
