# Reporte FEAT-001 / F-02: interfaz de firma en papel

## Tarea realizada

Entregar permite elegir firma en pantalla o en papel. El modo papel reserva un folio en el servidor, imprime dos copias del mismo ticket y exige la foto de la copia firmada antes de confirmar el movimiento.

## Archivos modificados

- `frontend/app/componentes/entrega/firma-papel.tsx`: contrato tipado de reserva, DosCopias, impresión aislada, captura o archivo de foto, reducción JPEG, caducidad y protección frente a fotos terminadas después de cambiar el ticket.
- `frontend/app/componentes/entrega/borrador.ts`: reserva, modo y foto dentro del borrador privado del usuario.
- `frontend/app/componentes/entrega/tipos.ts`: `firma_modo` incluye PAPEL.
- `frontend/app/routes/operacion/entregar.tsx`: prepara ticket y confirma con `reserva_papel_id`, firma PAPEL y foto, manteniendo el mismo cuerpo e identificador durante los reintentos.

## Decisiones y supuestos

- El ticket imprime únicamente datos recibidos del snapshot reservado, sin costo ni datos personales reservados.
- Reservar e imprimir no significa entregar equipo; se informa explícitamente en pantalla.
- Si cambia trabajador, proyecto, almacén, renglones, observación o autorización, la reserva/foto se invalidan. Si existía una reserva, se genera otro id_cliente para el nuevo cuerpo.
- Un ticket vencido exige preparar e imprimir otro con nuevo id_cliente y tomar la nueva foto. No acepta la foto del ticket anterior.
- La firma en pantalla conserva su flujo. El modo papel no exige trazo digital.
- Se reutiliza la reducción de imagen existente; la foto queda en el borrador local hasta confirmar o borrar/cerrar sesión, igual que la firma digital.

## Validaciones ejecutadas

- Verificación de tipos y construcción aprobadas nuevamente después de la revisión y su corrección. La suite compartida de frontend aprueba 34 pruebas.
- Revisión independiente por `auditoria_features`: encontró un bloqueo del campo si cambiaba la reserva mientras se reducía una foto; corregido reiniciando el indicador y descartando la respuesta vieja.
- Revisión del contrato real `ConfirmarIn`, `ReservaPapelOut` y `POST /api/vales/reservar-papel`; reserva y confirmación comparten la misma función que construye el cuerpo.

## Riesgos o deuda pendiente

- Falta recorrido real con impresora, foto legible y confirmación en celular/Android; no se acredita el diálogo de impresión del WebView.
- La foto se reduce a 1024 px mediante el helper existente; comprobar legibilidad de una entrega extensa en equipo real.
- La reserva cambia la numeración de folios aunque no se confirme; esta decisión pertenece al contrato implementado por el servidor.

## Documentación actualizada

Este reporte y nota aditiva en app-flow. Backend, contrato global de reserva y migración están a cargo de la tarea principal.

## Siguiente acción

Ejecutar el recorrido completo: preparar, imprimir, firmar, fotografiar, confirmar, abrir QR y reintentar sin duplicados; probar vencimiento y cambio de renglones.
