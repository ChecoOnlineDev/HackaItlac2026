# Reporte de FEAT-014 — servidor de aprobación y Web Push

## Tarea realizada

La entrega de EPP exige aprobación según el almacén, la autonomía del usuario y su permiso
de supervisor. Conserva el semáforo original. Las solicitudes DESPACHO incluyen EPP,
excedentes y contexto; se resuelven por renglón, por PIN o sesión, o en lotes independientes.
La aprobación cubre solo cantidades aprobadas y se consume junto al vale. Hay vigencia
renovada al aprobar, protección contra doble solicitud y resolución concurrente.

Se implementaron las suscripciones Web Push por familia de sesión, envío cifrado con VAPID,
agrupación, reemplazo silencioso y prueba por dispositivo. La tarea de envío abre su propia
sesión después del commit y su fallo no deshace la operación. También se conectaron los
avisos de uso y de traslado lateral desde el router de vales.

## Archivos modificados

- `backend/app/modulos/autorizaciones/`: modelo, contratos, repositorio, servicio, router,
  excepciones y clasificador `verificador_despacho.py`.
- `backend/app/modulos/notificaciones/`: módulo nuevo completo, adaptador Web Push,
  generación de claves y README de configuración.
- `backend/app/modulos/movimientos/`: contexto y contratos de evaluación; integración de
  confirmación, permisos y bloqueos; reglas del tipo ENTREGA y tareas del router.
- `backend/alembic/versions/0014_despacho_push.py`, `backend/app/config.py`, `.env.example`,
  `backend/pyproject.toml`, `backend/uv.lock` y `backend/app/core/handlers.py`.
- `backend/tests/test_despacho_feat014.py` y adaptaciones limitadas de pruebas anteriores:
  motivo de rechazo, nuevo error de cobertura, observación PR-10 y categoría HERRAMIENTA
  explícita para artículos genéricos del helper.
- Filtro `por_vencer` de proyectos y lectura con bloqueo opcional de sus asignaciones,
  coordinados con FEAT-013 y el tablero.

Los registros de routers, modelos, permisos, datos iniciales y los PATCH de autonomía fueron
integrados por el coordinador. Los cambios posteriores de firma en papel son otra tarea.

## Decisiones y supuestos

- `id_cliente` es obligatorio para DESPACHO y opcional para clientes anteriores EXCEDENTE
  y TRASLADO. Igual identidad y cuerpo reutilizan la solicitud; cuerpo diferente devuelve 409.
- La resolución parcial admite todas y solo las líneas que requieren decisión. Rechazar pide
  motivo. TRASLADO conserva su resolución completa.
- Se permite quitar renglones aprobados o disminuir su cantidad. Subir cantidades, añadir EPP
  o conservar un rechazado produce `APROBACION_INVALIDA`; una autorización vencida, usada,
  de otro tipo o contexto produce `AUTORIZACION_INVALIDA`.
- El aviso al otro dispositivo del supervisor se conserva: se excluye la familia que resolvió,
  en lugar de excluir al usuario entero.
- Los proveedores permitidos son Google FCM, Mozilla, Apple y Microsoft mediante HTTPS,
  sin credenciales ni IP y sin seguir redirecciones.
- No se escribieron claves VAPID en `.env`. El comando de generación imprime el par para
  que se configure una vez en el servidor.

## Validaciones ejecutadas

- `TEST_DB_SUFFIX=feat14_backend uv run pytest tests/test_despacho_feat014.py tests/autorizaciones -q -x`
  → **61 aprobadas**, 86.35 s; 21 nuevas y 40 de regresión. Incluye carreras reales de creación
  y resolución con dos conexiones MySQL, inventario intacto al rechazar, aprobación parcial,
  autonomía con auditoría, sesión por dispositivo, agrupación desde MySQL, cifrado real,
  VAPID, timeout, restricción de hosts, límite de prueba y revocación 410.
- `TEST_DB_SUFFIX=feat14_backend uv run pytest tests/movimientos/test_autorizacion_integracion.py tests/movimientos/test_autorizacion_endurecimiento.py -q -x`
  → **26 aprobadas**, 69.86 s.
- Ruff de los módulos y pruebas propios → aprobado.
- Importación de `app.main` y módulo de notificaciones → aprobada.
- Las corridas aplicaron las migraciones hasta la cabeza disponible (incluidas las de sello
  y alto valor de los otros agentes), en una base de pruebas separada.
- Único aviso de las suites: deprecación de Starlette/httpx del entorno existente.

## Riesgos o deuda pendiente

- Comprobar recepción con la PWA cerrada en un dispositivo real, tras configurar VAPID,
  service worker y permiso del navegador. Las pruebas reemplazan la red; no certifican
  que un proveedor haya entregado un aviso físico.
- Interfaz FEAT-014 y pruebas en navegador corresponden al agente frontend.
- Revisión por otro agente y validación global del repositorio corresponden al coordinador.
- Si una base persistente aplicó una versión provisional de 0014 antes del campo
  `ultima_etiqueta`, debe actualizarse mediante una migración aditiva; no se debe restablecer.

## Documentación actualizada

- Estado del servidor agregado al brief FEAT-014.
- README de notificaciones y variables VAPID documentadas sin secretos.
- Este reporte. Modelo, API y reglas globales quedan bajo la integración del coordinador.

## Siguiente acción

Completar y revisar la interfaz, configurar VAPID y demostrar el flujo con la PWA del
supervisor. Continuar FEAT-002 en paralelo a la firma en papel, coordinando los archivos
compartidos de movimientos. No se hicieron commits ni push.
