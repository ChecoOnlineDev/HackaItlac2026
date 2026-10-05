# FEAT-001: Vale como prueba

## Problema u oportunidad

Sin firma, el trabajador puede decir que no sacó el equipo (plática min 22). A la vez, el trabajador desconfía del registro electrónico y quiere una copia en su poder (min 23). El MVP deja la firma en pantalla, pero todavía sin sello, sin copia para el trabajador y sin opción de papel.

## Objetivo

Que cada vale quede sellado contra alteraciones, que el trabajador se lleve su copia y que la empresa pueda firmar en papel donde lo prefiera.

## Historia de usuario

Como trabajador, quiero llevarme un comprobante de lo que recibí y poder comprobar que no fue alterado, para confiar en el registro de la empresa.

Como almacenista, quiero imprimir el vale y firmarlo en papel cuando el trabajador lo pida, para no tener fricción en el mostrador.

## Alcance incluido

- **Sello.** Al guardar un vale se calcula una huella de su contenido encadenada con la del vale anterior del mismo almacén.
- **Comprobante público.** El QR del vale abre, sin sesión, una vista de solo lectura con folio, fecha, trabajador, artículos y el estado "Íntegro" o "Alterado".
- **Ticket imprimible.** Formato para papel de 80 mm y para carta, en dos copias, con folio, artículos, leyenda de responsabilidad, espacio de firma y QR.
- **Firma en papel.** Segundo modo de firma: se imprime, se firma a mano y el almacenista fotografía la copia firmada, que queda ligada al vale.
- **Verificación.** Un reporte recorre la cadena completa y señala el primer vale que no coincide.

## Fuera de alcance

- Constancias NOM-151 y firma electrónica avanzada.
- Envío del comprobante por WhatsApp, correo o SMS.
- Impresión directa a impresoras térmicas; se imprime desde el navegador.

## Criterios de aceptación

- Dado un vale emitido, cuando se modifica uno de sus movimientos directamente en la base, entonces el comprobante público muestra "Alterado" y el reporte señala ese vale.
- Dado el QR de un vale, cuando se abre desde un celular sin sesión, entonces se ve el comprobante.
- El comprobante y el ticket no muestran costos, CURP ni NSS.
- Dado el modo de firma en papel, entonces el vale no se cierra hasta adjuntar la foto del ticket firmado.
- El ticket se imprime en dos copias desde el navegador.
- Dos vales confirmados al mismo tiempo en el mismo almacén quedan encadenados sin romper la cadena.

## Módulos relacionados conocidos

`movimientos` (sello al confirmar), `consulta` (comprobante y verificación), interfaz del vale emitido.

## Cambios de datos o API esperados

- `vale.hash`, `vale.hash_anterior`; tabla `cadena_sello`; `vale.firma_modo` admite PAPEL; `adjunto.tipo` admite TICKET_FIRMADO.
- `GET /api/publico/vales/{token}` sin sesión; `GET /api/reportes/integridad`.

## Restricciones y compatibilidad

- Los vales emitidos antes de esta feature no tienen sello; la cadena empieza en el primero posterior y el comprobante de los anteriores dice "Sin sello".
- El contenido que se sella debe serializarse siempre igual.
- `vale.estado` queda fuera del sello, porque un traspaso cambia de estado al recibirse.

## Riesgos

- Una serialización inestable daría falsos "Alterado".
- La cadena exige confirmar en orden dentro de cada almacén; hay que bloquear su último eslabón.
- El comprobante público expone datos del trabajador a quien tenga el QR: se limita a nombre y número.

## Validaciones requeridas

- Prueba de alteración detectada.
- Prueba de que el comprobante público no entrega campos restringidos.
- Prueba de dos confirmaciones simultáneas.
- Impresión real del ticket en dos copias.

## Documentos globales que podrían actualizarse

`data-model.md`, `api-contracts.md`, `security-model.md`, `app-flow.md` (comprobante y modo de firma), `ui-ux.md` (ticket y comprobante).
