# Historias de la Fase 7 — Confiabilidad

Gate de la fase y tareas técnicas: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-CAN-001: Cancelar un vale capturado por error

Como almacenista, quiero cancelar un vale que capturé mal, para corregir el error sin que nadie tenga que tocar la base de datos y sin perder el historial.

**Criterios de aceptación**

- Desde el detalle de un vale, quien lo hizo o un supervisor puede cancelarlo escribiendo un motivo.
- La cancelación genera un vale de cancelación con su propio folio y los movimientos inversos; las existencias y el resguardo regresan a como estaban.
- El vale original sigue visible, marcado como cancelado, con el motivo y el folio de su cancelación.
- Se pueden cancelar entradas, entregas, devoluciones y traspasos en tránsito.
- Dado un vale cuya pieza ya se movió después, o cuyas existencias ya no alcanzan para revertirlo, entonces no se cancela y se explica por qué.
- Una recepción y un vale de no adeudo no se pueden cancelar.
- Un vale ya cancelado no se puede cancelar otra vez.
- Dado un almacenista, entonces solo puede cancelar los vales que él hizo; el supervisor puede cancelar cualquiera.
- Ambos vales aparecen en el reporte de movimientos y en el historial de cada pieza.
- Desde el detalle, "Cancelar y rehacer" cancela el vale y abre un borrador con los mismos renglones, sin firma ni autorización, para quitar o corregir el que falló.
- Desde Consultar, "Mis movimientos de hoy" lista los vales que el usuario hizo ese día, con "Cancelar" y "Cancelar y rehacer" en cada uno.

**Reglas:** K-01 a K-05, C-12, X-14, RG-02, RG-06, RG-09.

**Fuera de alcance:** editar un vale; cancelar parcialmente; lista de revisión del supervisor; deshacer una cancelación.

**Casos límite:** cancelar una entrega que usó una autorización no la libera para otro vale; un doble toque en "Cancelar" no genera dos cancelaciones.

**Evidencia:** prueba: entrega, cancelación y comparación de existencias antes y después; prueba: intento de cancelar una entrega cuya pieza ya se devolvió.
