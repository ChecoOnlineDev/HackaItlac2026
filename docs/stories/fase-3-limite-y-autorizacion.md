# Historias de la Fase 3 — Límite y autorización

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-LIM-001: Respetar el límite por artículo

Como supervisor, quiero que el sistema detenga las entregas que superan el límite de un artículo, para controlar el consumo excesivo y la acumulación de equipo.

**Criterios de aceptación**

- Dado un artículo retornable con límite, entonces la cuenta es lo que el trabajador tiene más lo que pide.
- Dado un consumible con límite y periodo, entonces la cuenta es lo entregado en los últimos N días más lo que pide.
- Dado que la cuenta supera el límite, entonces el renglón queda en naranja con el detalle, por ejemplo "límite 2, tiene 2, pide 1".
- Sin límite configurado, la regla no aplica.
- Un renglón en naranja impide confirmar hasta que se autoriza o se quita.
- Dado que el trabajador devuelve un retornable, entonces puede volver a recibirlo sin autorización.

**Reglas:** L-01 a L-05, E-07, SM-03.

**Fuera de alcance:** dotación recomendada (FEAT-003); límite sumado por categoría.

**Casos límite:** el límite se alcanza sumando dos renglones del mismo artículo en un vale; una entrega hecha hace exactamente N días ya no cuenta.

**Evidencia:** pruebas unitarias de la cuenta en posesión y por periodo.

---

## US-AUT-001: Autorizar un excedente

Como supervisor, quiero autorizar o rechazar un excedente desde mi celular, o con mi PIN en el mostrador, para no detener la operación ni tener que ir al almacén.

**Criterios de aceptación**

- El almacenista pide la autorización escribiendo un motivo.
- La solicitud muestra al supervisor: trabajador, artículo, límite, cuánto tiene, cuánto pide, motivo y quién la pide.
- El supervisor la ve en su lista en menos de cinco segundos y responde Autorizar o Rechazar.
- Dado que el supervisor está presente, entonces puede escribir su usuario y su PIN en el dispositivo del almacenista.
- Autorizada: el renglón queda autorizado y la entrega se puede confirmar.
- Rechazada o vencida: el almacenista quita el renglón y entrega lo demás.
- La autorización sirve una sola vez y solo para esos renglones.
- Quien captura no puede autorizarse. Un rojo no se puede enviar a autorización.
- El vale registra quién pidió, quién autorizó, cuándo, por qué medio y el motivo; aparece como "Validó".
- Cinco PIN incorrectos bloquean cinco minutos.

**Reglas:** A-01 a A-07, SM-03, SM-04.

**Fuera de alcance:** notificaciones push; delegar la autorización; autorizar varias solicitudes a la vez.

**Casos límite:** la solicitud vence a los 15 minutos; si el almacenista cambia la cantidad después de autorizada, la autorización ya no la cubre y el renglón vuelve a naranja.

**Evidencia:** paso 4 del guion automatizado; demostración con dos celulares.

---

## US-ESP-001: Entregar artículos de uso especial

Como responsable del catálogo, quiero marcar ciertos artículos para que cada entrega pida autorización, para controlar el equipo que la empresa decida restringir.

**Criterios de aceptación**

- Dado un artículo con "autorización del supervisor" activa, entonces cualquier entrega lo pone en naranja y muestra su motivo.
- Se autoriza con el mismo flujo que un excedente.
- Dado que se quita el requisito, entonces la siguiente entrega ya no lo pide.
- Dado que además supera el límite, entonces se muestran los dos motivos y una sola autorización cubre ambos.
- La ficha del artículo y el catálogo indican que es de uso especial y por qué.

**Reglas:** CF-06 a CF-08, E-26, SM-01.

**Fuera de alcance:** habilitaciones del trabajador (E-08).

**Casos límite:** activar el requisito con una entrega a medio capturar: al confirmar, el servidor responde con el cambio.

**Evidencia:** prueba: activar el requisito y ver naranja, autorizar y confirmar, quitar el requisito y ver verde.
