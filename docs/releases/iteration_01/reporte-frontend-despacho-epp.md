# FEAT-014: captura, resolución y avisos del supervisor

## Tarea realizada

Interfaz conectada al contrato real de autorizaciones de despacho. La entrega incorpora el paso Aprobación antes de la firma; solicita todos los renglones en una sola autorización DESPACHO cuando lo indica la evaluación del servidor. La firma solo aparece con una evaluación actual que permita confirmar, incluso al recuperar un borrador. Una modificación de trabajador, proyecto, almacén o renglones elimina la firma anterior, sin eliminar automáticamente la aprobación: el servidor determina su cobertura.

Las solicitudes envían UUID de cliente estable durante el reintento, proyecto, códigos, cantidades y observaciones. Sin excedente, la nota es opcional. La resolución por PIN consulta primero la solicitud guardada y usa sus posiciones y clases, porque EXCEDENTE renumera las filas. Admite aprobación parcial y exige motivo de cada rechazo. La misma interfaz por renglón se utiliza en la bandeja del supervisor.

La bandeja muestra almacén, proyecto, nota, observaciones y clases EPP, EXCEDENTE y CONTEXTO. Los conteos de vencimiento toman como referencia la hora del servidor. Hay filtro por almacén asignado y resolución múltiple hasta cincuenta seleccionadas, con errores por solicitud. Las solicitudes con excedentes siguen requiriendo revisión individual por el servidor. El enlace `/autorizaciones/:id` permite abrir un aviso y consultar o resolver según el permiso de sesión. Una falla de consulta no se presenta como un vencimiento.

La cola local conserva hasta diez capturas por usuario y dispositivo. Permite Atender a otro mientras, retomar la entrega o descartar solamente su captura local. Sondeo, sonido, aviso y vibración anuncian respuestas mientras Inicio o Entregar están abiertos. Inicio muestra el contador en el acceso de Entregar. Al salir o vencer la sesión, el borrado existente de claves `imhotep.borrador.*` incluye esta cola. Una falla al guardar impide reemplazar la captura activa.

Los avisos Web Push se habilitan por acción explícita. La carga solo registra una suscripción si el navegador ya tiene permiso; no pide permiso automáticamente. Las claves públicas se consultan al servidor y nunca se copia una clave privada al cliente. Se detecta la rotación de clave pública, se conserva la preferencia al desactivar y se revoca la suscripción antes de cerrar sesión. La pantalla explica la instalación en iPhone/iPad y mantiene la bandeja como respaldo. El service worker muestra avisos con la etiqueta enviada, reemplazos silenciosos y navegación limitada al mismo origen; también intenta registrar una renovación sin pedir permiso. No guarda respuestas de la API.

La ficha del almacén y la edición de un usuario que puede entregar incorporan el control de autonomía, visible solo con `despacho.autonomia`. El cambio tiene su botón separado y motivo obligatorio de hasta mil caracteres; se envía al endpoint de autonomía y refleja la respuesta.

El detalle imprimible del vale presenta el modo de despacho y quién aprobó cuando el servidor devuelve ese dato. Como compatibilidad con FEAT-002 se añadió AJUSTE al tipo y etiquetas del vale y a Mis movimientos; no se construyó la pantalla de ajuste en esta tarea.

## Archivos modificados

- `frontend/app/componentes/entrega/{borrador,hoja-autorizacion,banda-autorizacion,tipos,vale-adaptador}.ts(x)`; nuevos `use-entregas-en-espera.ts` y su prueba.
- `frontend/app/componentes/supervision/{resolucion-renglones,avisos-supervisor}.tsx`, `tarjeta-solicitud.tsx`, `use-solicitudes.ts` y `control-autonomia.tsx`.
- `frontend/app/componentes/{consulta/tipos.ts,dominio/tipos.ts,dominio/vale-imprimible.tsx}`.
- `frontend/app/routes/{operacion/entregar,supervision/autorizaciones,supervision/autorizacion-detalle,inicio,consulta/mis-movimientos}.tsx` y registro de la ruta de detalle.
- `frontend/app/componentes/acceso/{tipos.ts,hoja-usuario.tsx}`, `frontend/app/componentes/almacenes/{tipos.ts,hoja-detalle.tsx}` y permiso de presentación `despacho.autonomia` en `api/tipos.ts`.
- `frontend/app/pwa/avisos.ts`, `frontend/app/sesion/sesion.tsx`, `frontend/public/sw.js` (versión 3).

## Decisiones y supuestos

Las clasificaciones, cobertura, autonomía y transiciones finales proceden del servidor. Los controles por renglón validan únicamente que el usuario complete su decisión y motivo. El sondeo sigue funcionando sin VAPID o Web Push. Se conserva el flujo de traslado existente; no se incorpora push a Capacitor ni trabajo sin conexión.

## Validaciones

- `pnpm typecheck`: correcto después de las conexiones finales.
- `pnpm test`: 18 pruebas correctas, incluidas cuatro nuevas DE-15 sobre aislamiento entre usuarios, fallo de persistencia, datos dañados y límite de recuperación.
- `pnpm build`: correcto después de las conexiones finales.
- `git diff --check` sobre los archivos de esta tarea: correcto; únicamente aviso de normalización LF/CRLF en un archivo anterior.
- Revisión del contrato por otro agente: detectó y confirmó la renumeración de EXCEDENTE; ya se utilizan las filas reales de la solicitud en el PIN.
- Revisión estática independiente de avisos, service worker, sesión, controles de autonomía y resolución/PIN: sin hallazgos P1/P2. Comprobó permiso explícito, exclusión de práctica/Capacitor, cookies, registro único, revocación previa al logout, origen del enlace y protección de fotos. No sustituye una prueba física.
- Una ejecución simultánea de build y typecheck interfirió con los tipos generados de rutas; se repitió typecheck de forma secuencial para verificar el resultado final.

## Riesgos y deuda

No se realizó prueba manual con dos sesiones reales ni recepción física de Web Push. Necesita servidor con VAPID, HTTPS y navegador compatible. No se afirma la entrega efectiva de un aviso solo porque el servidor aceptó enviarlo. La documentación global de API y flujos se reconciliará con el resto de la iteración.

## Siguiente acción

Validar en dos dispositivos la aprobación parcial, rechazo, vencimiento y reenvío conservando firma, reingreso de capturas, aviso recibido y revocación al salir; validar los controles administrativos de autonomía y reconciliar los documentos globales.
