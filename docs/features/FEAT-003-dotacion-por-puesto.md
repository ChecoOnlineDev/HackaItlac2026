# FEAT-003: Dotación por puesto y avisos no bloqueantes

**Estado: servidor construido** (migración `0004_puestos_dotacion`, endpoints de puestos, dotación y `GET /api/trabajadores/{id}/dotacion`, avisos E-09, E-10 y E-11 en la entrega y observación en el reporte de movimientos). **Pendiente: la interfaz** (catálogo de puestos, ficha con lo que falta y observación con respuestas rápidas). Contrato en [api-contracts.md](../architecture/api-contracts.md#puestos-y-dotación); reglas en la sección 4.2 de las [reglas](../product/reglas-de-negocio.md). Los puestos y dotaciones de los datos de prueba son propuestas basadas en el PDF.

## Problema u oportunidad

El EPP se define por puesto (PDF p.3, paso 5) y hay consumo que llama la atención sin llegar a un límite (plática min 34 y 36). El MVP solo conoce el límite, que bloquea. Falta un nivel intermedio: lo recomendado, que avisa.

## Objetivo

Que el almacenista vea qué le falta a un trabajador según su puesto, y que el sistema avise, sin bloquear, cuando se entrega algo fuera de lo recomendado.

## Historia de usuario

Como almacenista, quiero ver la dotación que le corresponde al trabajador y recibir un aviso si entrego de más, para surtir rápido y dejar anotado el porqué de una excepción.

## Alcance incluido

- Catálogo de puestos.
- Dotación por puesto: artículos y cantidad recomendada.
- En la entrega, la ficha del trabajador muestra lo que le falta de su dotación.
- Entregar algo fuera de la dotación, o más de lo recomendado, pone el renglón en amarillo y pide una observación, con respuestas rápidas.
- La observación queda en el movimiento y se ve en el reporte de movimientos.
- Dos avisos más, sin observación: la talla del artículo no coincide con la del trabajador (E-10), y la inspección de la pieza vence en siete días o menos (E-11).

## Fuera de alcance

- Tallas por artículo de la dotación.
- Reposición programada por tiempo.
- Reporte de consumo por puesto. El reporte de consumo por artículo y periodo ya está en el MVP (C-08).

## Criterios de aceptación

- Dado un trabajador con puesto y dotación, entonces la ficha lista lo que le falta.
- Dado un artículo fuera de su dotación, entonces el renglón queda en amarillo y pide observación; con la observación se puede confirmar.
- Dado un artículo dentro de lo recomendado, entonces el renglón es verde.
- Dado que también supera el límite, entonces gana el naranja y se muestran los dos motivos.
- Un puesto sin dotación no genera avisos.
- La dotación recomendada de un artículo no puede ser mayor que su límite.

## Módulos relacionados conocidos

`catalogo` (puestos y dotación), `trabajadores` (puesto del periodo), `movimientos` (regla E-09).

## Cambios de datos o API esperados

- Tablas `puesto` y `dotacion`; `periodo_contrato.puesto` pasa de texto a referencia.
- `GET` y `PUT /api/puestos/{id}/dotacion`; la evaluación agrega `pide_observacion`.

## Restricciones y compatibilidad

- Los periodos ya capturados con puesto en texto se relacionan con el catálogo por nombre; los que no coincidan quedan sin dotación.

## Riesgos

- Demasiados avisos hacen que se ignoren: solo avisa lo que sale de la dotación.

## Validaciones requeridas

- Pruebas de la regla E-09 en sus tres casos: dentro, fuera y combinada con el límite.

## Documentos globales que podrían actualizarse

`data-model.md`, `api-contracts.md`, `ui-ux.md` (ficha con dotación), `reglas-de-negocio.md` (D-01 a D-03).
