# Historias de la Fase 4 — Devolución y baja

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-DEV-001: Devolver por escaneo

Como almacenista, quiero recibir una devolución escaneando el equipo, para descargarlo del resguardo del trabajador sin tener que buscarlo.

**Criterios de aceptación**

- Dada una pieza en resguardo, cuando se escanea, entonces se muestran el artículo y su titular sin pedir credencial.
- La condición al volver es obligatoria: Bueno, Desgaste por uso o Dañado.
- Dañado exige observación y admite una foto. Una pieza entra al almacén como No apta; un artículo por cantidad va a Baja.
- Para artículos por cantidad se identifica al trabajador y se elige de su lista; no se puede devolver más de lo que tiene.
- Dada una pieza con la etiqueta ilegible, entonces se devuelve eligiéndola de la lista del trabajador o buscándola por su número de serie.
- Dada una pieza traída por otra persona, entonces se abona a su titular.
- Dado un código que no existe, entonces se rechaza con "No es de la empresa" y el pendiente sigue abierto.
- Dada una pieza que no está en resguardo, entonces se muestra dónde está y no se genera movimiento.
- El equipo entra al almacén de la sesión aunque lo haya entregado otro, con un aviso.
- Se emite un vale de devolución con folio; baja el resguardo y suben las existencias.
- La devolución de un artículo inactivo se recibe normal, y ninguna condición del trabajador la bloquea.

**Reglas:** V-01 a V-07, V-11, V-12, V-14, SM-05, CF-11, F-08.

**Fuera de alcance:** cierre sin devolución (V-09); devolución de consumible sobrante (V-10); pérdida reportada (V-13); comprobante público (FEAT-001).

**Casos límite:** un trabajador inactivo o con contrato vencido también puede devolver; en una misma devolución pueden venir piezas de dos titulares y cada renglón se abona al suyo.

**Evidencia:** pruebas con pieza propia, pieza de otro titular y código ajeno.

---

## US-BAJ-001: Procesar la baja y emitir el vale de no adeudo

Como almacenista de Kepler, quiero ver lo que un trabajador tiene pendiente y emitir su vale de no adeudo cuando haya devuelto todo, para que RH pueda finiquitarlo.

**Criterios de aceptación**

- RH o el almacenista inician la baja desde la ficha; el trabajador pasa a Baja en proceso y ya no recibe entregas.
- Al iniciarla se muestran sus pendientes de todos los almacenes: artículo, código o serie, fecha de entrega, folio y almacén.
- Los consumibles no aparecen como pendientes.
- Dado que tiene pendientes, entonces "Emitir vale de no adeudo" no procede y muestra lo que falta.
- Dado que no tiene pendientes, entonces se emite el vale de no adeudo con folio y el trabajador queda Inactivo.
- RH ve en su lista la situación de cada trabajador: Sin pendientes, Con pendientes o No adeudo emitido.
- RH puede cancelar una baja en proceso; el trabajador vuelve a Activo.
- La lista de pendientes no muestra costos.

**Reglas:** B-01 a B-05, B-07 a B-09, T-08, RG-12.

**Fuera de alcance:** dar equipo por perdido (P-05); cálculo del finiquito.

**Casos límite:** un trabajador que nunca recibió nada obtiene su vale de inmediato; un pendiente de otro almacén se ve igual desde Kepler.

**Evidencia:** paso 6 del guion automatizado.

---

## US-TRB-002: Reingresar a un trabajador y respetar su vigencia

Como RH, quiero reingresar a un trabajador con un nuevo periodo, para que vuelva a recibir equipo sin perder su historial.

**Criterios de aceptación**

- Dado un número de empleado que ya existe, entonces se muestra a la persona y se ofrece el reingreso.
- El reingreso registra un periodo nuevo y regresa al trabajador a Activo; los periodos anteriores se conservan.
- Sus pendientes de periodos anteriores siguen en su resguardo y se avisan al entregar.
- Dado un trabajador cuyo periodo terminó ayer, entonces la entrega se bloquea con "ya no forma parte de la plantilla".
- Dado un trabajador Inactivo, entonces la entrega se bloquea hasta su reingreso.
- Un retornable pendiente de un periodo anterior cuenta para el límite en posesión.

**Reglas:** T-02, T-06, T-07, E-02, E-12, B-05, L-02.

**Fuera de alcance:** contratos, sueldos y documentos del trabajador.

**Casos límite:** un periodo que termina hoy todavía es vigente; un reingreso con fecha de inicio futura deja al trabajador Activo pero no vigente.

**Evidencia:** prueba con tres fechas: vigente, vencido ayer y reingresado.
