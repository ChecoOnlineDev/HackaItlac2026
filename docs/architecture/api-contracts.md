# Contratos de API

> Avance de implementación de FEAT-013 (8 de octubre de 2026): ya existen proyectos y asignaciones, alta/reingreso con proyecto, sesión por conjunto y atribución del proyecto en las entregas. La integración completa del tablero está en construcción; no confundir contratos aprobados con pruebas de aceptación terminadas.

### Contratos de proyectos integrados

- `GET /api/proyectos` devuelve `{elementos, total}`; `GET /api/trabajadores/{id}/proyectos` devuelve asignaciones completas, cada una con `proyecto`. Alta y reingreso validan el proyecto en el servidor y guardan trabajador, periodo y asignación juntos.
- `PUT /api/usuarios/{id}/almacenes` usa `{almacenes_id: UUID[], almacen_activo_id?: UUID}`. El campo definitivo es `almacenes_id`. Exige `acceso.usuarios` o `almacenes.asignar_personal`, con los límites de AC-41 en el servicio.
- `PUT /api/sesion/almacen` recibe `{almacen_id}` y devuelve la sesión. Almacén ajeno: 403 `ALMACEN_NO_ASIGNADO`; cerrado: 409 `ALMACEN_CERRADO`. La sesión incluye `almacenes` y `almacen_activo`; el campo compatible `almacen` representa el activo.
- ENTREGA acepta `proyecto_id`. La evaluación incluye `proyecto` y `proyectos_del_trabajador` como `{id, clave, nombre}`, además de `pide_proyecto`. Uno se toma automáticamente; varios exigen elegir; ninguno exige observación no vacía al confirmar (PR-10). El detalle del vale conserva `proyecto`; la respuesta breve de confirmación conserva su forma anterior.
- Una solicitud explícita de principal cuando ya hay otra asignación principal activa responde 409 `CONFLICTO` (PR-13). Cambiar la principal se hace terminando/reemplazando la anterior y creando otra asignación; no se reescribe su historia.
- `PATCH /api/usuarios/{id}/almacen` reduce el conjunto al único almacén indicado, incluso si ya era el activo; `null` vacía el conjunto.
- FEAT-014 en integración: ambos `PATCH /almacenes/{id}/autonomia` y `PATCH /usuarios/{id}/autonomia` exigen `despacho.autonomia` y un motivo no vacío. Los campos son `despacho_epp_con_aprobacion` y `despacho_autonomo`; se devuelve la ficha y se registra el cambio. Un valor idéntico no añade auditoría.

> Implementado en este hito (OF-02): el middleware revisa X-App-Version en rutas bajo /api/. Si está ausente, no bloquea la web. Si no usa tres números separados por puntos o es menor que APP_VERSION_MINIMA (0.1.0 por omisión), responde 426 con codigo APP_DESACTUALIZADA, mensaje «Hay una versión nueva de la app. Pídela a tu supervisor o al área de sistemas para seguir.» y detalles.version_minima. Solo queda exceptuado POST /api/sincronizacion/lotes, con o sin barra final; otros métodos y rutas hijas no quedan exceptuados. La excepción no crea ese endpoint ni concede permisos. Los contratos de sincronización de la iteración 01 siguen planeados.


Endpoints, cuerpos, errores y permisos del MVP. Todo va bajo `/api`, en JSON, con la sesión en una cookie.

Estado: es el contrato acordado para construir. Si al implementar cambia, se actualiza aquí en el mismo cambio.

### Rutas adicionales integradas: permiso declarado en el router

La columna muestra el permiso exigido por el router. Cuando dice «Sesión», el router solo exige una sesión y el servicio puede aplicar una regla adicional según el tipo de operación o los datos enviados.

| Ruta | Permiso | Contrato |
|---|---|---|
| `DELETE /api/notificaciones/suscripciones/{id}` | Sesión | Revoca la suscripción propia; una ajena responde 404. |
| `GET /api/almacenes/{id}/minimos` | `inventario.minimos` | Devuelve los mínimos configurados para el almacén. |
| `GET /api/almacenes/{id}/reporte-cierre` | `reportes.cierre` | Devuelve el cierre del almacén para el rango solicitado. |
| `GET /api/bitacora` | `bitacora.ver` o `reportes.movimientos` | Lista vales de la bitácora dentro del alcance. |
| `GET /api/catalogo/configuracion` | `catalogo.ver` | Devuelve opciones de configuración del catálogo. |
| `GET /api/deudores` | `deudores.ver` | Lista adeudos dentro del alcance del usuario. |
| `GET /api/deudores/resumen` | `deudores.ver` | Devuelve el resumen de adeudos dentro del alcance. |
| `GET /api/inspecciones/pendientes` | `inspecciones.ver` | Lista inspecciones pendientes o devuelve solo sus conteos si se solicita. |
| `GET /api/inspecciones/{id}/foto` | `inspecciones.ver` | Devuelve la foto de la inspección dentro del alcance. |
| `GET /api/notificaciones/clave-publica` | Sesión | Devuelve la clave pública de avisos, si está configurada. |
| `GET /api/proyectos` | `proyectos.asignar` o `proyectos.ver` | Lista proyectos permitidos para consulta o asignación. |
| `GET /api/proyectos/{id}` | `proyectos.asignar` o `proyectos.ver` | Devuelve la ficha del proyecto dentro del alcance. |
| `GET /api/publico/vales/{token}` | Público | Devuelve el comprobante público asociado al token. |
| `GET /api/reportes/integridad` | `reportes.movimientos` | Lista vales con problemas de integridad. |
| `GET /api/reportes/valor-inventario` | `reportes.valor_inventario` | Devuelve el valor del inventario permitido al usuario. |
| `GET /api/salud` | Público | Confirma que la aplicación responde y alcanza la base de datos. |
| `GET /api/tablero/proyectos` | `proyectos.ver` o `tablero.ver` | Devuelve uso y resguardo por proyecto dentro del alcance. |
| `GET /api/tablero/valor` | `reportes.valor_inventario` | Devuelve los importes del tablero de valor. |
| `GET /api/trabajadores/{id}/consumo` | `trabajadores.ver` | Devuelve el consumo del trabajador dentro del alcance. |
| `GET /api/trabajadores/{id}/proyectos` | `trabajadores.ver` | Devuelve asignaciones activas y terminadas del trabajador. |
| `GET /api/vales/{id}/renglones` | `vales.ver` | Devuelve los renglones del vale. |
| `PATCH /api/almacenes/{id}/autonomia` | `despacho.autonomia` | Cambia la autonomía de despacho del almacén con motivo. |
| `PATCH /api/proyectos/{id}` | `proyectos.administrar` | Actualiza los datos permitidos del proyecto. |
| `PATCH /api/usuarios/{id}/autonomia` | `despacho.autonomia` | Cambia la autonomía de despacho del usuario con motivo. |
| `POST /api/autorizaciones/resolucion-multiple` | `autorizaciones.resolver` | Resuelve hasta 50 solicitudes en una operación agrupada. |
| `POST /api/inspecciones/lotes` | `piezas.inspeccionar` | Registra inspecciones por lote. |
| `POST /api/notificaciones/prueba` | `autorizaciones.resolver` | Envía un aviso de prueba a las suscripciones de la sesión. |
| `POST /api/notificaciones/suscripciones` | `autorizaciones.resolver` | Registra la suscripción de avisos del usuario y dispositivo. |
| `POST /api/proyectos` | `proyectos.administrar` | Crea un proyecto en el almacén indicado. |
| `POST /api/proyectos/{id}/cierre` | `proyectos.administrar` | Cierra el proyecto y termina sus asignaciones activas. |
| `POST /api/proyectos/{id}/reapertura` | `proyectos.administrar` | Reabre el proyecto con las fechas y motivo permitidos. |
| `POST /api/trabajadores/{id}/proyectos` | `proyectos.asignar` | Asigna el trabajador a un proyecto. |
| `POST /api/trabajadores/{id}/proyectos/{asignacion_id}/termino` | `proyectos.asignar` | Termina la asignación indicada. |
| `PUT /api/almacenes/{id}/minimos` | `inventario.minimos` | Reemplaza la configuración de mínimos del almacén. |
| `PUT /api/sesion/almacen` | Sesión | Cambia el almacén activo entre los asignados al usuario. |
| `PUT /api/usuarios/{id}/almacenes` | `acceso.usuarios` o `almacenes.asignar_personal` | Cambia el conjunto de almacenes y, opcionalmente, el activo. |

## Convenciones

- Los `id` son UUID en texto, por ejemplo `01a10a17-3a3b-74ed-89d0-2082afd9941a` ([ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). En los ejemplos se abrevian.
- Las fechas van en ISO 8601; las horas, en UTC.
- Las listas admiten `pagina` y `tamano` y responden `{elementos, total}`.
- La columna "Permiso" muestra exactamente lo declarado por cada router. "Sesión" significa que el router solo exige una sesión; algunas de esas rutas verifican además permisos en el servicio según el tipo o los datos de la operación. En `POST /api/vales` y `/api/vales/evaluar`, el servicio exige la clave correspondiente al tipo de vale; en `POST /api/vales/reservar-papel`, solo admite ENTREGA. `POST /api/autorizaciones` exige `entregas.crear` para EXCEDENTE/DESPACHO y `traspasos.operar` para TRASLADO. `POST /api/autorizaciones/{id}/resolucion` valida `autorizaciones.resolver` en la sesión o en el usuario autorizado por PIN. `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}` exigen `compras.solicitar` o `compras.atender` en el servicio. `GET /api/escaneo/{codigo}` y `GET /api/busqueda` deciden el acceso en el servicio según los permisos de consulta. Cuatro rutas declaran una alternativa en el router con `requiere_alguno`: `GET /api/reportes/movimientos` y `GET /api/reportes/usuarios` (`bitacora.ver` o `reportes.movimientos`), `GET /api/seguimiento/piezas` y `GET /api/seguimiento/cantidad` (`reportes.existencias` o `resguardo.ver`). Sin el permiso, responden 403 `SIN_PERMISO`.
- El almacén sale del usuario de la sesión. Quien tiene `almacenes.todos` lo indica con `almacen_id`.
- Los datos reservados no se envían sin su permiso de información: `costo_unitario` pide `catalogo.costos`; `curp` y `nss` piden `trabajadores.ver_datos_personales`.

### Errores

```json
{ "codigo": "SIN_PERMISO", "mensaje": "Tu rol no puede hacer esto.", "detalles": null }
```

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTENTICADO` | No hay sesión, o el token de acceso venció (dura 15 minutos): la interfaz llama a `POST /api/sesion/refresh` y repite la petición. |
| 401 | `SESION_VENCIDA` | Solo en `POST /api/sesion/refresh`: el token de renovación no existe, venció, llegó al tope de 30 días, ya se había cambiado hace más de 10 segundos, lo revocaron (salir, contraseña o PIN, inactivar) o el usuario ya no está activo. Borra las dos cookies; hay que entrar con la contraseña (AC-17, AC-18, AC-22). |
| 403 | `SIN_PERMISO` | El rol del usuario no tiene el permiso del endpoint. |
| 404 | `NO_ENCONTRADO` | El recurso no existe. |
| 409 | `VALE_CAMBIO` | Al confirmar, la evaluación ya no es la misma. Incluye la evaluación nueva en `detalles`. |
| 409 | `ALMACEN_CAMBIO` | Al confirmar o evaluar, el usuario ya no está asignado al almacén en el que capturó el vale (`almacen_id` del cuerpo). No se guarda; `detalles` trae `{almacen_captura_id, almacen: {id, clave, nombre} o null}` con el almacén actual del usuario, y el borrador se conserva (AC-13). Lo lanza `AccesoService.exigir_mismo_almacen`. |
| 409 | `USUARIO_EXISTE` | Al dar de alta, el nombre de usuario ya lo usa otra persona (sin distinguir mayúsculas). |
| 409 | `ULTIMO_ADMINISTRADOR` | No se inactiva ni se le quita el rol al último usuario activo con `acceso.administrar`, ni se le quita ese permiso a su rol (AC-09). |
| 409 | `ROL_EXISTE` | Ya hay un rol con ese nombre (sin distinguir mayúsculas). |
| 409 | `ROL_PROTEGIDO` | El rol Administrador no pierde `acceso.administrar`, `acceso.usuarios`, `acceso.roles`, `almacenes.todos` ni `almacenes.administrar` (AC-09, AC-32; el mensaje dice cuál), no se inactiva ni se elimina; los cinco roles iniciales no se eliminan ni cambian de nombre (AC-09). |
| 409 | `ROL_EN_USO` | Un rol con usuarios asignados no se inactiva ni se elimina (AC-11). |
| 409 | `AUTO_BLOQUEO` | Quien administra intenta quitarle `acceso.administrar` a su propio rol o inactivarlo (AC-09). |
| 409 | `CODIGO_REPETIDO` | El código ya identifica otra cosa. Incluye en `detalles` su `tipo`, su `ref_id` y una `descripcion` de quién es. |
| 409 | `TRABAJADOR_EXISTE` | Al dar de alta, la CURP ya existe, el nombre completo coincide con el de otra persona cuando el alta no trae CURP, o el número de empleado externo ya existe (T-02, T-10). Incluye en `detalles.trabajador` a la persona (`id`, `numero_empleado`, `nombre`, `estado`) y en `detalles.coincide_por` el dato que coincidió (`curp`, `nombre` o `numero_empleado`), para ofrecer el reingreso. Cuando coincide solo el `nombre`, `detalles.puede_confirmar_distinta` es `true`: se puede repetir el alta con `confirmar_distinta: true` si es otra persona (nunca con CURP ni número externo repetidos). Si coincidió la CURP y quien da de alta no tiene `trabajadores.ver_datos_personales`, solo dice que ya existe (`detalles` solo trae `regla`), sin `coincide_por` ni la persona (AC-05). |
| 409 | `CON_PENDIENTES` | No se puede emitir el vale de no adeudo. `detalles` trae `{regla: "B-04", pendientes}`: cada pendiente con `articulo`, `codigo`, `numero_serie`, `cantidad`, `entregado_en`, `folio` y almacén (`almacen_clave`, `almacen`); sin costos. |
| 409 | `CON_MOVIMIENTOS` | No se puede eliminar ni cambiar control o retorno. |
| 409 | `NO_CANCELABLE` | El vale no se puede cancelar (K-03, K-04, X-14). `mensaje` explica por qué en español llano y `detalles` trae, por cada motivo, `{regla, mensaje}` (y `renglon` y `codigo` si es de un renglón). No se escribe nada. |
| 409 | `TRANSICION_INVALIDA` | La solicitud de compra no puede pasar a ese estado desde el que tiene (SC-04). `detalles`: `{regla, estado_actual, estado_pedido, estados_permitidos}`. |
| 409 | `ARCHIVO_REPETIDO` | La confirmación de una importación trae un archivo con la misma huella que otra ya confirmada (I-12) y no manda `confirmar_repetido: true`. `detalles: {regla: "I-12", fecha}` (UTC). No se escribe nada. |
| 409 | `ID_CLIENTE_EN_USO` | El `id_cliente` de una solicitud de compra ya se usó con otro cuerpo o por otro usuario (SC-10). |
| 409 | `CLAVE_REPETIDA` | Ya hay un almacén con esa clave (sin distinguir mayúsculas) (AL-02). |
| 409 | `NOMBRE_REPETIDO` | Ya hay un almacén con ese nombre (sin distinguir mayúsculas ni acentos) (AL-02). |
| 409 | `YA_HAY_CENTRAL` | Ya existe el almacén central; solo hay uno (AL-02). |
| 409 | `CLAVE_CON_FOLIOS` | La clave de un almacén que ya tiene folios no se cambia (AL-05). |
| 409 | `CON_EXISTENCIAS`, `CON_TRASPASOS_EN_TRANSITO`, `CON_HIJOS_ACTIVOS`, `CON_USUARIOS` | No se puede inactivar el almacén (AL-03). El código es el primer bloqueo y `detalles.bloqueos` los lista todos con lo que falta (ver [Almacenes y existencias](#almacenes-y-existencias)). |
| 409 | `PADRE_CERRADO` | No se reactiva un almacén cuyo almacén padre está cerrado (AL-03). |
| 409 | `ALMACEN_CERRADO` | El almacén está cerrado y no recibe ni envía movimientos ni solicitudes: «Ese almacén está cerrado.» `detalles: {regla: "AL-04", almacen: {id, clave, nombre}}` (AL-04). Lo dan la confirmación de vales y las solicitudes de compra nuevas; la evaluación lo trae como motivo rojo del vale. |
| 422 | `PADRE_INVALIDO` | El almacén padre no existe, está cerrado, es el mismo almacén o uno de sus descendientes, un `CENTRAL` trae padre o un no central no lo trae (AL-02). `detalles: {regla: "AL-02", motivo}`. |
| 403 | `RUTA_SOLO_ADMINISTRADOR` | El traspaso va por una ruta que no es padre-hijo y quien lo confirma no tiene `almacenes.todos` (X-03). `detalles: {regla: "X-03", origen, destino}`. Sin observación obligatoria el caso del Administrador es 422 `DATOS_INVALIDOS` con `regla: "X-03"`. |
| 403 | `AUTORIZACION_PROPIA` | Quien pidió la autorización intenta autorizarla (A-05, AC-07). |
| 409 | `AUTORIZACION_RESUELTA` | La solicitud ya se resolvió o venció; no se resuelve de nuevo. |
| 409 | `AUTORIZACION_INVALIDA` | La autorización no sirve para este vale: no está aprobada, venció, ya se usó, es de otro almacén o trabajador, o no cubre los renglones ni la cantidad (A-03). En un traslado (X-19): es de otro origen o destino, o el vale agrega un renglón o sube una cantidad (solo se pueden quitar). |
| 403 | `AJUSTE_PROPIO` | Quien registró la inspección intenta ajustar su vigencia (P-07). |
| 409 | `AJUSTE_NO_PERMITIDO` | La pieza está No apta o no tiene inspección Apta: no hay vigencia que ajustar (P-07). |
| 422 | `VIGENCIA_EXCEDIDA` | La fecha pasa de la inspección más la vigencia del artículo (P-07). |
| 409 | `SERIE_YA_REGISTRADA` | La pieza ya tiene número de serie: `POST /api/piezas/{id}/serie` solo pone la serie a una pieza que no la tiene; cambiar una registrada no entra en esta etapa (P-08). `detalles: {regla: "P-08"}`. |
| 409 | `SERIE_REPETIDA` | La serie que se quiere registrar ya existe en ese artículo (I-02). `detalles: {regla: "I-02", pieza: {id, codigo}}` con la pieza que ya la tiene (solo si está en el alcance del usuario). Se eligió 409 y no 422 porque choca con un dato existente, igual que `CODIGO_REPETIDO`. En la importación, `SERIE_REPETIDA` sigue siendo un motivo de fila, no un error de la petición. |
| 422 | `RENGLON_NO_AUTORIZABLE` | Un renglón que no es naranja en la evaluación del servidor no se envía a autorización: uno en rojo (A-06) o uno verde o amarillo que no la necesita. |
| 422 | `DATOS_INVALIDOS` | Falta un dato o tiene forma incorrecta. Incluye el campo. |
| 413 | `CUERPO_MUY_GRANDE` | El cuerpo de la petición pasa del límite de su ruta, por `Content-Length` o contando los bytes cuando viaja por trozos. Se responde sin leerlo completo. `detalles.limite_bytes` dice el límite. Límites (en `config.py`): 1 MB de JSON en general; 12 MB en `POST /api/vales` y `/api/vales/evaluar` (puede llevar la firma y fotos de daño); 3 MB en `POST /api/trabajadores/{id}/foto`; 6 MB en `/api/importacion*`. |
| 403 | `PIN_INCORRECTO` | El PIN de autorización no es válido (403 y no 401, para no cerrar la sesión). |
| 429 | `DEMASIADOS_INTENTOS` | Cinco contraseñas o PIN fallidos seguidos: bloqueo de cinco minutos. Incluye `detalles.segundos_espera` y la cabecera `Retry-After`. Se responde ya en el quinto intento fallido. El conteo resiste peticiones simultáneas: no hay más de cinco intentos reales por ventana. |
| 503 | `SERVICIO_NO_DISPONIBLE` | La base de datos canceló la operación por un choque entre transacciones (interbloqueo) y no se pudo repetir. Es transitorio: el login y la resolución de autorizaciones lo reintentan tres veces antes de responder esto; intentar de nuevo suele funcionar. Nunca sale como 500. |
| 409 | `CONFLICTO` | 409 genérico: la operación choca con el estado actual y no tiene un código más específico. Es la base de los demás 409; el `mensaje` se puede mostrar tal cual. |
| 405 | `METODO_NO_PERMITIDO` | El método HTTP no existe para esa ruta (por ejemplo, `DELETE` donde solo hay `GET`). |
| 413 | `CUERPO_MUY_GRANDE` | El cuerpo de la petición pasa del límite de tamaño de su ruta: 1 MB en JSON normal, 12 MB en vales (firma y foto de daño), 3 MB en la foto de un trabajador y 6 MB en la importación. Incluye `detalles.limite_bytes`. |
| 500 | `ERROR_INTERNO` | Falla inesperada. El mensaje es genérico, sin detalles técnicos; el detalle queda en la bitácora de la aplicación. |
| otro | `ERROR` | Cualquier otro error HTTP que el servidor devuelve sin código propio. Mensaje genérico. |
| 501 | `TIPO_NO_IMPLEMENTADO` | El tipo de vale existe pero su operación no está construida. Los siete tipos del MVP ya están implementados; el código se conserva para tipos futuros. |

## Acceso

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/sesion` | Público | Entra con `{usuario, contrasena}` y abre la sesión de ESTE dispositivo (AC-14). Deja dos cookies `HttpOnly` y `SameSite=Lax` (y `Secure` con `COOKIE_SEGURA=true`): `sesion` (token de acceso, `Path=/`, `Max-Age` de `ACCESO_MINUTOS`, 15 min) y `sesion_renovar` (token de renovación opaco, `Path=/api/sesion`, `Max-Age` de `REFRESH_DIAS`, 7 días). Si el navegador ya traía una sesión, esa se cierra. Responde `{usuario: {id, nombre, usuario}, rol: {id, nombre}, almacen: {id, clave, nombre} o null, permisos: [claves]}`. Credenciales incorrectas o usuario inactivo: 401 con "Usuario o contraseña incorrectos", sin decir cuál falló y sin cookies; cinco fallos seguidos bloquean cinco minutos (429). |
| `POST /api/sesion/refresh` | Público | Sin cuerpo; lo identifica la cookie `sesion_renovar`, no la de acceso. Cambia el token de renovación por un token de acceso nuevo y un token de renovación nuevo (AC-15). Responde lo mismo que `POST /api/sesion` (permisos y almacén recién leídos de la base, AC-23) y vuelve a fijar las dos cookies; la ventana se extiende `REFRESH_DIAS` días desde ahora, sin pasar de `inicio + REFRESH_TOPE_DIAS` (30 días, AC-18). **Tolerancia (AC-16):** si el token ya se había cambiado hace `REFRESH_TOLERANCIA_SEGUNDOS` (10) o menos, responde 200 con la misma sesión y fija solo la cookie `sesion` (acceso nuevo); no cambia otra vez ni toca `sesion_renovar`. **Reutilización (AC-17):** un token ya cambiado hace más de 10 segundos revoca toda la familia de ese dispositivo y responde 401 `SESION_VENCIDA`. Sin cookie, inventado, vencido, pasado el tope, revocado, de una versión de sesión vieja o de un usuario inactivo: 401 `SESION_VENCIDA` y se borran las dos cookies. No depende de un token de acceso vigente. |
| `GET /api/sesion` | Sesión | Devuelve la sesión actual con la lista de permisos. La interfaz la usa para mostrar menús y botones; al arrancar, si responde 401 intenta renovar antes de pedir la contraseña. |
| `DELETE /api/sesion` | Sesión | Sale: cierra SOLO la sesión de este dispositivo y borra las dos cookies. Responde 204. Su token de acceso, aunque lo hayan copiado, y su token de renovación dejan de servir de inmediato (401); las sesiones de los demás dispositivos siguen abiertas (AC-19). |
| `DELETE /api/sesion/otras` | Sesión | Cierra las sesiones de los demás dispositivos del usuario y conserva esta. Responde `{cerradas: n}`. No cambia `version_sesion` (AC-20). |
| `DELETE /api/sesion/todas` | Sesión | Cierra las sesiones de TODOS los dispositivos del usuario, también esta: sube `usuario.version_sesion` (con lo que todo token de acceso ya emitido deja de servir) y borra las cookies. Responde 204 (AC-20). |
| `GET /api/sesion/dispositivos` | Sesión | Los dispositivos con sesión abierta del usuario (no cerrados, dentro de su ventana y de su tope), el más reciente primero: `{dispositivos: [{id, inicio, ultimo_uso, vence_en, agente, actual}]}`. `id` es el de la familia del dispositivo; `ultimo_uso` es la última renovación (se precisa al `ACCESO_MINUTOS`); `vence_en` es hasta cuándo sirve sin usarla; `agente` es el navegador y sistema resumidos ("Chrome en Windows", sin versión); `actual` marca el de esta petición. Sin huellas, tokens ni IP (AC-21). |

## Usuarios y personal

Parte de [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md). Ninguna respuesta trae contraseñas, PIN ni hashes. Los cambios quedan en el registro de cambios sin secretos.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/personal?almacen_id=&sin_almacen=&q=` | `almacenes.asignar_personal` | `{elementos, total}` de los usuarios que trabajan en un almacén (sin `almacenes.todos` y con algún permiso de almacén; RH y el Administrador no). Sin `almacenes.todos`, solo los de su almacén y quienes no tienen almacén (AC-06); pedir otro almacén no devuelve nada: `{id, nombre, usuario, rol: {id, nombre}, almacen: {id, clave, nombre} o null, activo}`. `sin_almacen=true` trae a quienes no tienen almacén; no se combina con `almacen_id` (422). `q` busca en nombre y usuario. |
| `PATCH /api/usuarios/{id}/almacen` | `almacenes.asignar_personal` | `{almacen_id}`; `null` deja al usuario sin almacén. Responde el renglón de personal. Solo se asigna a quien trabaja en un almacén (no a quien tiene `almacenes.todos` ni a RH), el almacén debe existir y estar activo y el usuario no puede estar inactivo; si no, 422. Aplica en la siguiente petición del usuario y queda en el registro de cambios con el almacén anterior y el nuevo (AC-12, AC-13). No toca vales ni movimientos ya hechos. No cambia roles ni permisos. Sin `almacenes.todos`, solo se asigna a su propio almacén o se libera a quien está en el suyo (403 si pide otro almacén; 404 si el usuario está en otro almacén); mover entre almacenes es de quien tiene `almacenes.todos`. |
| `GET /api/usuarios?q=&rol_id=&almacen_id=&sin_almacen=&activo=` | `acceso.usuarios` | `{elementos, total}`: lo del personal más `tiene_pin` y `creado_en`; sin límite de roles. |
| `GET /api/usuarios/{id}` | `acceso.usuarios` | Un usuario. |
| `POST /api/usuarios` | `acceso.usuarios` | Alta con `{nombre, usuario, contrasena, rol_id, almacen_id, pin}`. `almacen_id` es obligatorio si el rol no tiene `almacenes.todos` y va vacío si lo tiene (RG-07). `pin` (4 a 8 dígitos, distinto de la contraseña) solo si el rol tiene `autorizaciones.resolver`. Responde 201. 409 `USUARIO_EXISTE`. |
| `PATCH /api/usuarios/{id}` | `acceso.usuarios` | Solo `nombre`, `rol_id`, `activo` y `almacen_id`; cualquier otro campo es 422. Cambiar a un rol con `almacenes.todos` quita el almacén; volver a uno que no lo tiene exige indicarlo. 409 `ULTIMO_ADMINISTRADOR` (AC-09). |
| `POST /api/usuarios/{id}/contrasena` | `acceso.usuarios` | `{contrasena, pin}` (`pin` opcional). Restablece la contraseña y, si se manda, el PIN, y reinicia los bloqueos. |

## Roles y permisos

Parte de [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md) (AC-08 a AC-11). Los roles y el catálogo de permisos piden `acceso.roles`; los usuarios, `acceso.usuarios` (ADR-011; `acceso.administrar` ya no abre ninguna ruta, solo marca al administrador del sistema, AC-09). Un cambio aplica en la siguiente petición de los usuarios del rol (el rol y sus permisos se leen de la base en cada petición) y queda en el registro de cambios con el valor anterior y el nuevo.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/permisos` | `acceso.roles` | El catálogo fijo de permisos: `[{clave, descripcion, modulo, grupo, disponible, es_de_informacion, mvp, llega_con, requiere: [claves]}]`. `modulo` es la parte de la clave antes del punto; `grupo` es con el que la matriz junta el permiso (por omisión, el módulo). `disponible: false` marca los cuatro permisos de la sección 8.3 sin función en esta versión: la interfaz los oculta o los marca «no disponible» y ningún rol inicial los trae. `requiere` lista los permisos de ver que ese permiso de acción necesita (la interfaz los activa juntos). `es_de_informacion` marca los datos reservados (costos, CURP y NSS). El catálogo no se edita desde la pantalla (AC-01). |
| `GET /api/roles` | `acceso.roles` | `[{id, nombre, descripcion, activo, protegido, inicial, total_usuarios, total_permisos, permisos: [claves]}]`. `inicial` marca los cinco roles con los que nace el sistema; `protegido`, al Administrador. |
| `GET /api/roles/{id}` | `acceso.roles` | Un rol, con la misma forma. 404 si no existe. |
| `POST /api/roles` | `acceso.roles` | `{nombre, descripcion, permisos: [claves]}` (`permisos` puede ir vacío: un rol sin permisos no ve ningún módulo). Responde 201 con el detalle. 409 `ROL_EXISTE` si el nombre ya se usa; 422 si una clave no existe o falta un permiso de ver que necesita otro. |
| `PATCH /api/roles/{id}` | `acceso.roles` | Solo `nombre`, `descripcion` y `activo`; otro campo es 422. Los roles iniciales no cambian de nombre (409 `ROL_PROTEGIDO`). Inactivar: 409 `ROL_PROTEGIDO` si es el Administrador y 409 `ROL_EN_USO` si tiene usuarios asignados (AC-11). 409 `AUTO_BLOQUEO` si inactivaría el rol del propio actor con `acceso.administrar`. |
| `PUT /api/roles/{id}/permisos` | `acceso.roles` | `{permisos: [claves]}`: deja al rol exactamente con esa lista (agrega y quita la diferencia). Responde el detalle. 422 si una clave no existe o falta un permiso de ver. Quitar `acceso.administrar`: 409 `ROL_PROTEGIDO` si es el Administrador, 409 `AUTO_BLOQUEO` si es el rol de quien lo hace, 409 `ULTIMO_ADMINISTRADOR` si no quedaría un administrador activo (AC-09). Si el rol recibe `almacenes.todos`, sus usuarios dejan el almacén asignado (RG-07) y cada uno queda en el registro de cambios; si lo pierde, sus usuarios quedan sin almacén hasta que alguien con `almacenes.asignar_personal` se lo asigne. |
| `DELETE /api/roles/{id}` | `acceso.roles` | Responde 204. 409 `ROL_PROTEGIDO` si es el Administrador o uno de los cinco iniciales; 409 `ROL_EN_USO` si tiene usuarios, aunque estén inactivos (AC-11). |

## Escaneo y búsqueda

Responden solo lo que el usuario puede ver: trabajadores con `trabajadores.ver`, artículos y piezas con `catalogo.ver`, y vales con `vales.ver`.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/escaneo/{codigo}?almacen_id=` | Sesión | Identifica un código: `{tipo, id, resumen}`. **TR-11:** con `almacen_id` (el origen elegido de un traspaso) el resumen de un artículo o de una pieza trae `disponible`: lo que hay en ese almacén (en una pieza, 1 si está en él y 0 si no; 0 si el almacén queda fuera del alcance del usuario, AC-06). Un código que no hay allí se identifica igual, con `disponible` 0: el rechazo lo da el servidor como X-02 al evaluar. Sin `almacen_id`, `disponible` es `null`. `tipo`: TRABAJADOR, ARTICULO, PIEZA, VALE o DESCONOCIDO. Lo que el usuario no puede ver llega como DESCONOCIDO (`id` en `null`); un vale solo se identifica dentro del alcance del usuario (AC-06): su almacén es el de origen o el de destino de un traspaso, o tiene `almacenes.todos` (la misma regla que `GET /api/vales/{id}`). Lo mismo vale para una pieza: sin `almacenes.todos` solo se identifica la que está en su almacén, la que tiene un trabajador (con `trabajadores.ver`) o la que va en tránsito desde o hacia su almacén; cualquier otra es DESCONOCIDO, idéntica a un código que no existe. En un artículo, `existencia_total` es lo que hay en el almacén del usuario (todos los almacenes, solo con `almacenes.todos`; 0 sin almacén asignado). Reconoce el código de una credencial, artículo o pieza, el QR (token) o el folio de un vale y el número de empleado tecleado. `resumen` es breve y nunca trae costos, CURP ni NSS. |
| `GET /api/busqueda?q=&almacen_id=` | Sesión | **TR-11:** con `almacen_id` (el origen de un traspaso) solo ofrece artículos con existencia y piezas que están en ese almacén, cada uno con `disponible` (lo que hay ahí; en piezas, 1); los trabajadores no cambian. Sin `almacen_id`, `disponible` es `null` y no se filtra. Coincidencias en artículos (nombre o código), piezas (serie, código o nombre del artículo, con quién las tiene) y trabajadores (nombre o número). Responde `{q, articulos, piezas, trabajadores, sin_resultados, mensaje}`; cada grupo es `{elementos, total}` y admite `pagina` y `tamano`. Un grupo sin permiso llega vacío. Menos de dos caracteres no busca y lo dice en `mensaje`. Los artículos son catálogo y se ven siempre; las piezas se limitan al alcance del usuario como en el escaneo (AC-06). |

## Trabajadores

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/trabajadores` | `trabajadores.ver` | Lista con vigencia y situación (cada elemento trae `puesto` y `puesto_id`). Filtros: `q` (parte del nombre o del número) y `situacion` (`SIN_PENDIENTES`, `CON_PENDIENTES`, `NO_ADEUDO_EMITIDO`). Nunca trae CURP ni NSS. |
| `POST /api/trabajadores` | `trabajadores.administrar` | Alta (T-03): `{nombre, area_obra, inicio, fin}`, el puesto como `puesto_id` (del catálogo) o como texto `puesto` (al menos uno; con los dos manda `puesto_id`) y opcionales `{referencia, tallas, curp, nss, confirmar_distinta, numero_empleado}`. **El número de empleado lo genera el servidor** (T-10, `E-000001`, desde `serie_empleado`) y la respuesta (201) lo trae en `numero_empleado` junto con `numero_externo: false`. `numero_empleado` solo se acepta con el permiso `trabajadores.numero_externo` (de inicio, el Administrador): único, de 1 a 30 caracteres, y el trabajador queda con `numero_externo: true`; sin el permiso, mandarlo es 403 `SIN_PERMISO`. **Reingreso (T-02):** si la CURP ya existe, o el alta no trae CURP y el nombre completo (sin distinguir mayúsculas ni acentos) coincide con el de otra persona, responde 409 `TRABAJADOR_EXISTE` para ofrecer el reingreso (`POST /api/trabajadores/{id}/periodos`); en la coincidencia por nombre, `confirmar_distinta: true` crea al trabajador de todos modos. `GET /api/trabajadores` y la ficha traen también `numero_externo`. Con `puesto_id`, el texto del periodo queda con el nombre del puesto; un `puesto_id` que no existe o está inactivo es 422 (`detalles.campo = "puesto_id"`). Con solo texto se busca el puesto por nombre (sin importar mayúsculas ni acentos): si existe se liga y, si no, el periodo queda sin `puesto_id` (sin dotación). Responde 201 con la ficha. Fin anterior a inicio: 422 con `detalles.campo = "fin"`. |
| `GET /api/trabajadores/puestos` | `trabajadores.administrar` | Los puestos **activos** para elegir el del alta y el reingreso: `{elementos: [{id, nombre}], total}`. Existe porque Recursos Humanos da de alta pero no tiene `catalogo.ver` y por eso no puede usar `GET /api/puestos`. Paginado (`pagina`, `tamano`). |
| `GET /api/trabajadores/{id}` | `trabajadores.ver` | Ficha: datos, `puesto` y `puesto_id` del periodo vigente, `periodo` vigente (con su `puesto_id`), `periodos` (todos, del más reciente al más antiguo), `vigencia` `{vigente, motivo, regla}`, `situacion`, `codigos`, `tiene_foto` y `foto_url`, `resguardo` (retornables con código, fecha de entrega, folio y almacén) y `pendientes` `{total, de_periodos_anteriores, regla}`. `curp` y `nss` solo existen en la respuesta con `trabajadores.ver_datos_personales`; sin el permiso la clave no se envía. |
| `GET /api/trabajadores/{id}/dotacion` | `trabajadores.ver` | Lo que le falta de la dotación de su puesto (D-02): `{puesto: {id, nombre} \| null, renglones: [{articulo: {id, codigo, nombre, unidad, control}, recomendada, entregada, falta}]}`. Forma y ejemplo en [Puestos y dotación](#puestos-y-dotación). Sin puesto del catálogo o con el puesto sin dotación, `renglones` va vacío. Es el permiso de la ficha (`GET /api/trabajadores/{id}`), que el almacenista, el supervisor y RH tienen. |
| `POST /api/trabajadores/{id}/periodos` | `trabajadores.administrar` | Reingreso o extensión: `{inicio, fin}` y opcionales `{puesto_id, puesto, area_obra, referencia}` (el puesto se resuelve igual que en el alta; sin puesto o área se conservan los del periodo anterior, también su `puesto_id`). Registra el periodo nuevo, regresa a Activo (T-02) y responde 201 con la ficha. |
| `POST /api/trabajadores/{id}/codigos` | `trabajadores.administrar` | Liga una credencial escaneada con `{codigo}` o, sin `codigo`, genera un código propio para imprimir (T-05). Responde 201 `{codigo, tipo, generado}`. Un código ya usado responde 409 `CODIGO_REPETIDO` diciendo de quién es. |
| `POST /api/trabajadores/{id}/foto` | `trabajadores.administrar` | Sube o reemplaza la foto (T-09). Multipart con el campo `archivo`. Solo acepta imágenes PNG, JPEG o WEBP (por su contenido) y rechaza las que pesan más del tamaño permitido (422). Responde `{tiene_foto, foto_url}`. El cambio queda en el registro de cambios. |
| `GET /api/trabajadores/{id}/foto` | `trabajadores.ver` | Entrega la imagen con su tipo de contenido, solo con sesión. 404 "Sin foto registrada." si no tiene. La ficha indica si el trabajador tiene foto. |
| `POST /api/trabajadores/{id}/baja` | `trabajadores.iniciar_baja` | Inicia la baja (B-01): pasa a Baja en proceso y responde `{id, estado, estado_texto, pendientes, puede_emitir_no_adeudo, reglas}` con los pendientes de todos los almacenes (B-02, sin consumibles, B-03). Si ya estaba en proceso solo repite los pendientes; si está Inactivo, 409. |
| `DELETE /api/trabajadores/{id}/baja` | `trabajadores.administrar` | Cancela la baja en proceso (B-07): vuelve a Activo y responde la ficha. Si la baja no está en proceso, 409. |

La emisión del vale de no adeudo (B-04, B-08) es de `movimientos`, en `POST /api/trabajadores/{id}/no-adeudo` (sección Vales).

## Catálogo

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/categorias` | `catalogo.ver` | Lista con su plantilla. Filtro: `activo`. |
| `POST /api/categorias`, `PATCH /api/categorias/{id}` | `catalogo.administrar` | Crea (201) o edita una categoría y su plantilla (CF-01, CF-02); poner o cambiar un límite pide además `catalogo.limites` (403, AC-30 de FEAT-011). El nombre no se repite (409). Una plantilla con inspección en control por cantidad se rechaza (422, CF-06). Editar la plantilla no cambia los artículos que ya existen. |
| `GET /api/articulos` | `catalogo.ver` | Lista. Filtros: `q` (nombre, código, marca o modelo), `categoria_id`, `activo`; sin `activo` trae activos e inactivos, y la pantalla manda `activo=true` por defecto (CF-10). `costo_unitario` solo con `catalogo.costos`: sin el permiso la clave no aparece. |
| `POST /api/articulos` | `catalogo.administrar` | Crea (201) un artículo; si indica un límite, 403 sin `catalogo.limites` (AC-30 de FEAT-011); control, retorno y reglas salen de la plantilla de su categoría si no se indican (un campo de regla en `null` significa "sin esa regla"). El código no puede repetir el de ningún artículo, pieza o credencial (409 `CODIGO_REPETIDO`) y queda registrado como su QR de producto o de estante (I-07). El costo solo se acepta con `catalogo.costos`; sin él, 403. | **EK-07:** `codigo` es opcional; sin él, el servidor lo genera `PREFIJO-NNNN` por categoría (el mismo consecutivo de la importación en modo Alta) y exige categoría activa (422, `campo` `categoria_id`) y un nombre que no exista (409 `ARTICULO_REPETIDO`, con `articulo_id` del existente); si la categoría no genera códigos (una de la empresa), 422 con `motivo` `FALTA_CODIGO`.
| `GET /api/articulos/{id}` | `catalogo.ver` | Ficha: reglas, `tiene_movimientos` (control y retorno bloqueados), `existencias` por almacén (`cantidad` y `disponible`, que no cuenta piezas No aptas, en mantenimiento ni en calibración) y `en_posesion` (quién lo tiene, con `cantidad`, `desde`, `folio` y `vale_id`, y en artículos por pieza `piezas` con `id`, `codigo` y `numero_serie` de cada una; folio y vale en `null` si el vale es de otro almacén) (C-03, SG-02). Sin `almacenes.todos`, `existencias` trae solo el almacén del usuario (AC-06); `en_posesion` es el resguardo de los trabajadores y se ve completo. El costo, solo con `catalogo.costos`. |
| `PATCH /api/articulos/{id}` | `catalogo.administrar` | Edita datos, límite (cambiarlo pide además `catalogo.limites`: 403), aviso de cantidad inusual y requisitos; solo cambia lo que viene (omitido no es `null`). No cambia el código ni la inactivación (422 si se envían). Rechaza cambios de control o retorno con movimientos (409 `CON_MOVIMIENTOS`, CF-05). Activar la inspección deja sus piezas sin inspección vigente (CF-09). Cambiar el costo pide `catalogo.costos`. |
| `POST /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Inactiva con `{motivo}` (CF-10). Responde el artículo. 409 si ya estaba inactivo. |
| `DELETE /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Reactiva (CF-13). Responde el artículo. 409 si ya estaba activo. |
| `DELETE /api/articulos/{id}` | `catalogo.administrar` | Elimina solo si no tiene movimientos (CF-12); responde 204, o 409 `CON_MOVIMIENTOS`. Libera su código. |
| `GET /api/piezas/{id}` | `catalogo.ver` | Ficha (C-02): artículo, `numero_serie` (nulo si está pendiente), `serie_pendiente` (booleano derivado: `true` si `numero_serie` es nulo), estado, `inspeccion_vigente_hasta` e `inspeccion_vigente`, `ultima_inspeccion`, `ubicacion` (almacén, trabajador o virtual) e `historial`: movimientos, inspecciones, cambios de estado y ajustes de vigencia en una sola lista, del más reciente al más antiguo (`tipo`, `fecha` UTC, `titulo`, `detalle`, `usuario` y los campos propios de cada tipo). Sin costos. Sin `almacenes.todos`, una pieza fuera del alcance (no está en su almacén, ni la tiene un trabajador, ni va en tránsito desde o hacia él) responde 404 `NO_ENCONTRADO`, igual que una que no existe; de su historial, los movimientos de un vale de otro almacén solo se muestran si pasan por un trabajador, con el almacén como «Otro almacén» y sin `folio`, `vale_id` ni responsable (AC-06). |
| `POST /api/piezas/{id}/inspecciones` | `piezas.inspeccionar` | Registra una inspección (P-01) con `{resultado, puntos?, observacion?}`; `puntos` admite `etiquetas`, `costuras`, `cintas`, `herrajes` y `conectores` (booleanos). Responde 201 con la inspección y `pieza: {id, estado, inspeccion_vigente_hasta}`. Apto deja la pieza Apta y vigente hasta hoy más la vigencia de su artículo; No apto exige observación (422) y la deja No apta. Sirve para cualquier pieza de su almacén, también la que está con un trabajador (es del almacén de su última entrega); sin `almacenes.todos`, una pieza de otro almacén da 404 (AC-06, H11); una en baja da 409. |
| `POST /api/piezas/{id}/estado` | `piezas.inspeccionar` o `piezas.marcar_estado` | Exige una de las dos claves. El servicio exige `piezas.inspeccionar` para No apta y `piezas.marcar_estado` para los demás estados. Marca el estado con `{estado, observacion}`; la observación es obligatoria (422). Responde 200 con `{evento_id, estado_anterior, pieza}`. Si ya está No apta o en baja, 409. |
| `POST /api/piezas/{id}/serie` | `piezas.registrar_serie` | Completa la serie de una pieza que entró con serie pendiente (P-08, I-02). Cuerpo `{numero_serie}` (texto de 1 a 80 caracteres (el largo de la columna), sin espacios al inicio ni al final). Solo se **pone** una serie a una pieza que no la tiene: si ya tiene, 409 `SERIE_YA_REGISTRADA`; si la serie ya existe en otra pieza del mismo artículo, 409 `SERIE_REPETIDA`; una pieza en baja da 409 `CONFLICTO`. Sin `almacenes.todos`, una pieza fuera del alcance del usuario da 404 `NO_ENCONTRADO`, igual que en `GET /api/piezas/{id}` (AC-06). No cambia el estado ni la ubicación de la pieza y no genera movimiento. Deja un renglón de auditoría `pieza.registrar_serie` con el antes (`numero_serie: null`) y el después. Responde 200 con la ficha de la pieza (la de `GET /api/piezas/{id}`, con `serie_pendiente: false`). Cambiar una serie ya registrada no entra en esta etapa. |
| `POST /api/piezas/{id}/ajuste-vigencia` | `piezas.ajustar_vigencia` | Cambia la fecha hasta la que vale la inspección vigente, con `{vigente_hasta, motivo}` (P-07). No cambia el resultado de la inspección. Responde 201 con el ajuste y la pieza. Se rechaza si la pieza está No apta o no tiene una inspección Apta (409 `AJUSTE_NO_PERMITIDO`), si la fecha pasa de la inspección más la vigencia del artículo (422 `VIGENCIA_EXCEDIDA`), si la fecha no cambia (422) o si quien la pide registró esa inspección (403 `AJUSTE_PROPIO`). |

## Puestos y dotación

Los puestos y su dotación recomendada (FEAT-003, D-01 a D-04) son del módulo `catalogo`.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/puestos` | `catalogo.ver` | `{elementos: [{id, nombre, activo, total_articulos}], total}` por nombre; admite `pagina` y `tamano`. Filtro: `activo`. |
| `POST /api/puestos` | `catalogo.administrar` | Crea (201) con `{nombre}`. El nombre no se repite sin importar mayúsculas ni acentos (409). Queda en el registro de cambios. |
| `PATCH /api/puestos/{id}` | `catalogo.administrar` | Cambia `{nombre?, activo?}` (omitido no es `null`). Nombre repetido: 409; puesto inexistente: 404. Un puesto inactivo conserva su dotación pero no se puede dar a un trabajador nuevo. Responde el puesto. |
| `GET /api/puestos/{id}/dotacion` | `catalogo.ver` | La dotación recomendada del puesto (D-01): `{puesto: {id, nombre}, renglones: [{articulo: {id, codigo, nombre, unidad, control}, cantidad, limite: {cantidad, periodo_dias} \| null}]}`. `limite` es el del artículo (`periodo_dias` vacío es "en posesión", L-05) y va `null` si no tiene. Renglones por nombre de artículo. Sin costos. |
| `PUT /api/puestos/{id}/dotacion` | `catalogo.administrar` | Reemplaza toda la dotación con `{renglones: [{articulo_id, cantidad}]}` (lo que no viene se quita; vacía la deja sin dotación). `cantidad` es un entero de 1 a 1000. 422 `DATOS_INVALIDOS` con `detalles: [{campo, mensaje, regla}]` si un artículo no existe o está inactivo o se repite (`regla: "D-01"`) o si la cantidad pasa del límite del artículo (`regla: "D-04"`, `campo: "renglones.N.cantidad"`). Un puesto inexistente es 404. Responde la dotación como el `GET` y queda en el registro de cambios. |

Además, un artículo que está en una dotación no se elimina (409 `CONFLICTO`, `detalles.regla = "D-01"`; se quita de la dotación o se inactiva) y su límite no puede bajar de lo recomendado en alguna dotación (422 en `PATCH /api/articulos/{id}`, `regla: "D-04"`).

Ejemplo de `GET /api/trabajadores/{id}/dotacion` (D-02). `entregada` es, en un retornable, lo que el trabajador tiene ahora; en un consumible, lo consumido desde el inicio de su periodo de contrato vigente (sin vales cancelados). `falta` es `max(recomendada - entregada, 0)`. Los artículos inactivos no se listan.

```json
{
  "puesto": { "id": "01a1…", "nombre": "Soldador" },
  "renglones": [
    { "articulo": { "id": "01a1…", "codigo": "LENTE-CL", "nombre": "Lente claro", "unidad": "pieza", "control": "CANTIDAD" },
      "recomendada": 1, "entregada": 1, "falta": 0 },
    { "articulo": { "id": "01a1…", "codigo": "TAPON-AU", "nombre": "Tapón auditivo", "unidad": "par", "control": "CANTIDAD" },
      "recomendada": 2, "entregada": 0, "falta": 2 }
  ]
}
```

## Almacenes y existencias

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/almacenes?resumen=` | `inventario.ver` | Lista con su red (la forma de la respuesta no cambia; se agregan campos). Cada elemento es una **ficha de almacén** (abajo): `{id, clave, nombre, tipo, estado, padre_id, padre_clave, cerrado_en, hijos: [{id, clave, nombre, estado}]}`. Con `resumen=true` agrega `resumen`; eso solo lo puede pedir quien tiene `almacenes.administrar` (403 `SIN_PERMISO` si no, porque trae existencias de otros almacenes, AC-06). Lista todos, también los cerrados. |
| `POST /api/almacenes` | `almacenes.administrar` | Alta (AL-01, AL-02). Cuerpo `{clave, nombre, tipo, padre_id}`. Responde 201 con la ficha. Detalle abajo. |
| `PATCH /api/almacenes/{id}` | `almacenes.administrar` | Edita `{nombre?, padre_id?, clave?}` (omitido no es `null`; otro campo, 422). Responde la ficha. Detalle abajo. |
| `POST /api/almacenes/{id}/cierre` | `almacenes.administrar` | Inactiva (AL-03). Cuerpo opcional `{motivo?}`. Responde la ficha. Detalle abajo. |
| `POST /api/almacenes/{id}/reapertura` | `almacenes.administrar` | Reactiva el mismo almacén. Cuerpo opcional `{motivo?}`. Responde la ficha. |
| `GET /api/tablero/resumen?almacen_id=` | `tablero.ver` | Tarjetas del Inicio (TB-01). Solo lectura, sin costos. Detalle en la sección «Tablero». |
| `GET /api/tablero/consumo?desde=&hasta=&almacen_id=&categoria_id=&limite=&separar_por_almacen=` | `tablero.ver` | Ranking de lo más usado en un rango (TB-02, TB-03). Detalle en la sección «Tablero». |
| `GET /api/almacenes/{id}/existencias` | `inventario.ver` | `{almacen, elementos, total}`: por artículo con existencia, `cantidad` y `disponible` (en piezas, solo las Aptas; I-05), con `activo` para marcar los inactivos (CF-11). Filtros: `q`, `categoria_id`, `activo`; admite `pagina` y `tamano`. Sin costos. Sin `almacenes.todos`, solo el almacén asignado: otro responde 404 `NO_ENCONTRADO`, igual que uno que no existe (AC-06). |

### Administración de almacenes (FEAT-008)

Reglas AL-01 a AL-05 ([reglas, 7.14](../product/reglas-de-negocio.md)). Todo cambio queda en el registro de cambios (`almacen.crear`, `almacen.editar`, `almacen.inactivar`, `almacen.reactivar`) con el antes y el después. Los cuatro endpoints de escritura piden `almacenes.administrar`: sin él, 403 `SIN_PERMISO`.

**Ficha de almacén** (la respuesta de los cuatro endpoints de escritura y cada elemento de la lista):

```json
{
  "id": "01a1…", "clave": "MID", "nombre": "Midrex", "tipo": "PROYECTO", "estado": "ACTIVO",
  "padre_id": "01a1…", "padre_clave": "CON", "cerrado_en": null,
  "hijos": [{ "id": "01a1…", "clave": "XYZ", "nombre": "Zona nueva", "estado": "ACTIVO" }],
  "resumen": {
    "existencias": { "unidades": 340, "articulos": 18 },
    "piezas_en_resguardo": 4,
    "usuarios": 3,
    "traspasos_en_transito": 0,
    "solicitudes_compra_abiertas": 1,
    "tiene_folios": true,
    "puede_cerrar": false,
    "puede_reabrir": false,
    "bloqueos_cierre": [{ "codigo": "CON_EXISTENCIAS", "mensaje": "Todavía tiene 340 unidades de 18 artículos." }]
  }
}
```

- `cerrado_en` es UTC o `null`. `padre_id` y `padre_clave` son `null` en el central.
- `resumen` solo viene en `GET /api/almacenes?resumen=true`. `existencias` suma las unidades de la ubicación del almacén (cualquier estado de pieza) y cuenta los artículos con cantidad mayor a cero. `piezas_en_resguardo` son las piezas de artículos por pieza que tiene un trabajador por una entrega de ese almacén. `usuarios` son los usuarios **activos** asignados. `traspasos_en_transito` son los traspasos desde o hacia él con algo todavía En tránsito. `solicitudes_compra_abiertas` son las PENDIENTE y EN_COMPRA. `tiene_folios` es `true` si ya emitió algún folio de vale o de solicitud (AL-05).
- `puede_cerrar` (almacén ACTIVO) es `true` si ninguna condición de AL-03 falla; si no, `bloqueos_cierre` trae `{codigo, mensaje}` por cada una, con los mismos códigos del cierre. `puede_reabrir` (almacén CERRADO) es `true` si su padre está activo (o es el central). La pantalla usa estos campos para habilitar o no los botones; el servidor vuelve a validar al ejecutar.

**`POST /api/almacenes`**

- Cuerpo: `clave` (2 a 10 caracteres, letras sin acento y números; el servidor la pasa a mayúsculas), `nombre` (1 a 100), `tipo` (`CENTRAL`, `SUBALMACEN` o `PROYECTO`) y `padre_id` (UUID de un almacén activo; `null` solo si el tipo es `CENTRAL`).
- Crea el almacén **y su ubicación** en la misma transacción. Nace `ACTIVO`. Si todavía no existen, crea también las ubicaciones virtuales del sistema (proveedor, en tránsito, consumido y baja) que los movimientos necesitan: una base de producción vacía no las trae.
- Errores: 409 `CLAVE_REPETIDA`, 409 `NOMBRE_REPETIDO`, 409 `YA_HAY_CENTRAL` (el tipo es `CENTRAL` y ya existe uno), 422 `PADRE_INVALIDO` (no existe, está cerrado, `CENTRAL` con padre o no central sin padre), 422 `DATOS_INVALIDOS` (formato de la clave, tipo desconocido). Dos altas simultáneas con la misma clave o nombre: gana una y la otra recibe el 409 (restricción única de la base).

**`PATCH /api/almacenes/{id}`**

- Cambia lo que viene: `nombre`, `padre_id` y `clave`. El `tipo` no se cambia (422).
- Un almacén `CERRADO` no se edita: 409 `ALMACEN_CERRADO`. Hay que reactivarlo primero.
- `clave`: 409 `CLAVE_CON_FOLIOS` si ya tiene folios (AL-05); 409 `CLAVE_REPETIDA` si choca.
- `padre_id`: 422 `PADRE_INVALIDO` si crearía un ciclo, si es él mismo, si el padre está cerrado, o si es el central (que no lleva padre). EK-06: también si el tipo del padre no cuadra, con el mensaje en `mensaje`: un `PROYECTO` solo depende de un `SUBALMACEN`, un `SUBALMACEN` solo del `CENTRAL`.
- 404 `NO_ENCONTRADO` si el almacén no existe.

**`POST /api/almacenes/{id}/cierre`**

- Pasa a `CERRADO` y escribe `cerrado_en`. 200 con la ficha. Si ya estaba cerrado: 409 `CONFLICTO`.
- Revisa las cuatro condiciones de AL-03. Si falla alguna, 409 sin cambiar nada. El `codigo` es el del primer bloqueo en este orden: `CON_TRASPASOS_EN_TRANSITO`, `CON_EXISTENCIAS`, `CON_HIJOS_ACTIVOS`, `CON_USUARIOS`. El `mensaje` dice en español llano qué falta y `detalles` lista **todos** los bloqueos:

```json
{
  "codigo": "CON_EXISTENCIAS",
  "mensaje": "Midrex todavía tiene 340 unidades de 18 artículos. Regrésalas por traspaso a Contratistas antes de cerrarlo.",
  "detalles": {
    "regla": "AL-03",
    "bloqueos": [
      { "codigo": "CON_EXISTENCIAS", "mensaje": "…", "unidades": 340, "total_articulos": 18,
        "articulos": [{ "articulo_id": "01a1…", "codigo": "DISCO-4", "nombre": "Disco de corte 4 pulgadas", "cantidad": 120 }] },
      { "codigo": "CON_USUARIOS", "mensaje": "…", "total": 3,
        "usuarios": [{ "id": "01a1…", "nombre": "Ana Pérez", "usuario": "alm_mid" }] }
    ]
  }
}
```

  Campos por bloqueo: `CON_EXISTENCIAS`: `unidades`, `total_articulos` y `articulos` (hasta 20, de mayor a menor cantidad); `CON_TRASPASOS_EN_TRANSITO`: `total` y `traspasos` (hasta 20: `{id, folio, estado, origen: {id, clave, nombre}, destino: {id, clave, nombre}}`); `CON_HIJOS_ACTIVOS`: `total` y `hijos` (`{id, clave, nombre}`); `CON_USUARIOS`: `total` y `usuarios` (hasta 20, activos: `{id, nombre, usuario}`). Las piezas en resguardo de trabajadores no bloquean (CP-05).

**`POST /api/almacenes/{id}/reapertura`**

- Pasa a `ACTIVO` y limpia `cerrado_en`. 200 con la ficha. Si ya estaba activo: 409 `CONFLICTO`. Si su padre está cerrado: 409 `PADRE_CERRADO` (hay que reactivar primero al padre).

**Almacén cerrado en el resto de la API (AL-04).** Ver «Almacén cerrado» en [Vales](#vales) y `POST /api/solicitudes-compra`.

## Tablero

Parte de [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md) (TB-01 a TB-03) y de FEAT-012 (valor del inventario). Solo lectura: no escribe nada y nunca trae costos unitarios, CURP ni NSS. `resumen` y `consumo` piden `tablero.ver`; sin él (Compras, RH), 403 `SIN_PERMISO`. `valor` pide `reportes.valor_inventario` y no `tablero.ver` (ver [`GET /api/tablero/valor`](#get-apitablerovaloralmacen_id)). El alcance lo decide el servidor (AC-06, TB-01): con `almacenes.todos`, todos los almacenes o el que indique `almacen_id`; sin él, **solo el almacén asignado** y `almacen_id` se ignora (no es error). Un `almacen_id` que no existe, con `almacenes.todos`, es 404 `NO_ENCONTRADO`; uno cerrado sí se puede pedir. Sin almacén asignado y sin `almacenes.todos`, ambos responden 200 con todo en cero y `alcance.almacen_id` en `null` y `es_todos` en `false`.

### `GET /api/tablero/resumen?almacen_id=`

Las tarjetas de FEAT-008 4.2.2. Respuesta (200):

```json
{
  "alcance": { "almacen_id": null, "nombre": "Todos los almacenes", "es_todos": true, "puede_elegir": true },
  "existencias": { "unidades": 1240, "articulos": 37 },
  "resguardo_equipo_importante": 12,
  "sin_existencia": 3,
  "traspasos_en_transito": 2,
  "entregas_hoy": 18,
  "solicitudes_compra_abiertas": 4,
  "inspecciones_por_vencer": 1,
  "piezas_serie_pendiente": 5,
  "alto_valor_fuera": 3,
  "generado_en": "2026-10-06T16:20:00Z"
}
```

| Campo | Qué cuenta |
|---|---|
| `alcance.almacen_id` | UUID del almacén que se está viendo, o `null` si son todos (o si el usuario no tiene almacén). |
| `alcance.nombre` | «Todos los almacenes», el nombre del almacén (por ejemplo «Midrex») o «Sin almacén asignado». |
| `alcance.es_todos` | `true` solo cuando se ven todos los almacenes. |
| `alcance.puede_elegir` | `true` si el usuario tiene `almacenes.todos`: la interfaz muestra el selector solo en ese caso. El selector se llena con `GET /api/almacenes`. |
| `existencias.unidades` | Suma de `existencia.cantidad` en las ubicaciones de almacén del alcance. No cuenta lo que tienen los trabajadores ni lo que está En tránsito. |
| `existencias.articulos` | Artículos distintos con cantidad mayor a cero en el alcance. |
| `resguardo_equipo_importante` | Piezas de artículos **por pieza** (alturas, eléctrica, alto valor) que están en manos de un trabajador (ubicación de trabajador, estado distinto de `BAJA`) y que son del alcance: se entregaron desde un almacén del alcance (AC-06, C-02). Al tocarla, la interfaz abre `/seguimiento` filtrado por `ubicacion=TRABAJADOR`. |
| `sin_existencia` | Artículos **activos** que alguna vez tuvieron existencia en el alcance y hoy suman cero (tienen fila de `existencia` pero la suma del alcance es 0). Un artículo del catálogo que nunca entró al almacén no cuenta. |
| `traspasos_en_transito` | Traspasos con algo aún En tránsito (`EN_TRANSITO` o `RECIBIDO_CON_DIFERENCIAS`) cuyo origen **o** destino está en el alcance: de ida y de venida. |
| `entregas_hoy` | Vales de ENTREGA no cancelados del alcance (`vale.almacen_id`) creados hoy, del día de México (TB-03). |
| `solicitudes_compra_abiertas` | Solicitudes de compra en estado PENDIENTE o EN_COMPRA del alcance. |
| `inspecciones_por_vencer` | Piezas de artículos que requieren inspección, en estado `APTO`, cuya `inspeccion_vigente_hasta` cae entre hoy y hoy más 7 días (el plazo de E-11; hoy incluido), dentro del alcance de C-02. Las ya vencidas no cuentan. |
| `piezas_serie_pendiente` | Piezas sin número de serie (`numero_serie` nulo, derivado) que no están de baja, dentro del alcance de C-02. Al tocar la tarjeta, la interfaz abre `/seguimiento` con `serie_pendiente=true`. |
| `alto_valor_fuera` | SG-04. Piezas de las categorías «Equipo de alto valor» y «Equipo de alturas» en manos de un trabajador (estado distinto de `BAJA`), dentro del alcance de C-02. Solo se calcula con `resguardo.ver`; sin ese permiso vale `null` y la tarjeta no se muestra. Al tocarla, la interfaz abre `/seguimiento?alto_valor=true&ubicacion=TRABAJADOR`. |
| `generado_en` | Momento del cálculo, UTC. |

Todos los números son enteros. No hay paginación.

### `GET /api/tablero/consumo?desde=&hasta=&almacen_id=&categoria_id=&limite=&separar_por_almacen=`

El ranking de lo más usado (FEAT-008 4.2.3, TB-02), agrupado en el servidor.

| Parámetro | Valor | Por omisión |
|---|---|---|
| `desde`, `hasta` | `AAAA-MM-DD`, fechas de México, ambas inclusivas (el día `hasta` entra completo, TB-03). | Del día 1 del mes en curso a hoy. |
| `almacen_id` | UUID. Solo se respeta con `almacenes.todos`; sin él se usa el del usuario. | Todos (con `almacenes.todos`) o el del usuario. |
| `categoria_id` | UUID de una categoría. | Todas (la interfaz manda «Consumibles de trabajo» por omisión; el servidor no la elige). |
| `limite` | Entero de 1 a 20. | 10 |
| `separar_por_almacen` | `true` o `false`. Solo tiene efecto si el alcance es «todos los almacenes». | `false` |

**Qué cuenta (TB-02).** Lo entregado en el rango, neto de cancelaciones, por artículo: para consumibles, la misma consulta de C-08 (suma los movimientos a CONSUMIDO y resta los que salen de CONSUMIDO); para retornables, las unidades de los movimientos de vales ENTREGA no cancelados. El almacén de un movimiento es el del vale. Sin renglones en cero. Se ordena de mayor a menor `total` y, en empate, por nombre.

Respuesta (200):

```json
{
  "desde": "2026-10-01",
  "hasta": "2026-10-06",
  "almacen": null,
  "categoria": { "id": "01a1…", "nombre": "Consumibles de trabajo" },
  "limite": 10,
  "separar_por_almacen": true,
  "barras": [
    {
      "articulo_id": "01a1…",
      "articulo": "Disco de corte 4 pulgadas",
      "categoria": { "id": "01a1…", "nombre": "Consumibles de trabajo" },
      "unidad": "pieza",
      "total": 120,
      "por_almacen": [
        { "almacen_id": "01a1…", "almacen": "Midrex", "total": 80 },
        { "almacen_id": "01a1…", "almacen": "HYL", "total": 40 }
      ]
    }
  ],
  "otros": { "total": 35, "articulos": 6 },
  "total_general": 155,
  "sin_registros": false
}
```

- `almacen` es `{id, clave, nombre}` del almacén que se usó, o `null` si son todos. `categoria` es `{id, nombre}` o `null` si son todas.
- `barras` trae, a lo más, `limite` artículos. Cada una lleva la `categoria` de su artículo (con «todas las categorías» sirve para distinguirlas) y `unidad`.
- `por_almacen` va vacío (`[]`) salvo con `separar_por_almacen=true` y alcance de todos los almacenes. Entonces lleva un elemento por almacén con consumo, de mayor a menor, y **su suma es el `total` de la barra**.
- `otros` es la suma de los artículos que no entraron en `barras` (`total`) y cuántos son (`articulos`); `{total: 0, articulos: 0}` si no los hay. No tiene desglose.
- `total_general` = suma de las barras más `otros.total`. Coincide con el total del reporte de consumo (`GET /api/reportes/consumo`) del mismo rango, almacén y categoría de consumibles.
- `sin_registros` es `true` si no hubo consumo en el rango (`barras` vacío): la interfaz muestra «No hubo consumo en estas fechas».
- Errores: 422 `DATOS_INVALIDOS` (fecha mal escrita, `desde` posterior a `hasta`, rango de más de 366 días, `limite` fuera de 1 a 20); 404 `NO_ENCONTRADO` (almacén o categoría que no existe); 403 `SIN_PERMISO`.

### `GET /api/tablero/valor?almacen_id=`

**Construido en el código** (`consulta/router_tablero.py`, `service_valor.py`, `repository_valor.py`, `schemas_tablero.py`; pruebas `tests/consulta/test_valor_inventario.py`, reglas VI-01 a VI-07 en sus comentarios; permiso disponible desde la migración `0009_permiso_valor_inventario`). Es [FEAT-012](../features/FEAT-012-valor-del-inventario.md), cuyo brief se escribió el 9 de octubre de 2026 a partir del código: este contrato se escribió leyendo el código.

- **Permiso:** `reportes.valor_inventario` (de inicio Compras, Supervisor y Administrador). No pide `tablero.ver`. Sin él, 403 `SIN_PERMISO`; sin sesión, 401 (VI-01).
- **Alcance (AC-06, VI-02):** el mismo del resto del tablero. Con `almacenes.todos`, todos o el `almacen_id` pedido (uno que no existe es 404 `NO_ENCONTRADO`); sin él, solo el almacén asignado y `almacen_id` se ignora. Sin almacén asignado ni `almacenes.todos`, 200 con todo en `"0.00"` y listas vacías.
- **Qué suma (VI-03):** existencia por el costo actual del catálogo. `en_almacen`: existencias en ubicaciones de almacén del alcance. `en_resguardo`: existencias en manos de trabajadores, atribuidas al almacén del vale de su última entrega (como AC-06). `en_transito`: existencias En tránsito, **solo** en el alcance «todos» (no se atribuye a un almacén; con un almacén va `null`). `total` = la suma de las tres. Incluye los artículos por pieza (cuenta por existencia).
- **Sin costo (VI-04):** un artículo sin `costo_unitario` no suma pesos; se cuenta en `articulos_sin_costo` (artículos distintos) y `unidades_sin_costo`. `GET /api/articulos?sin_costo=true` (`catalogo.ver`, VI-06) lista los activos sin costo para completarlos; no muestra el costo.
- **Nunca un costo (VI-05):** solo totales en pesos, como texto con dos decimales. La respuesta no trae `costo_unitario`, `articulo_id` ni el valor de un artículo.
- `por_categoria`: valor por nombre de categoría, de mayor a menor, hasta 6 y el resto en «Otras»; su suma es `total`. `por_almacen` (VI-07): solo en el alcance «todos» sin `almacen_id`, un elemento por almacén (también cerrados) con `en_almacen`, `en_resguardo` y `total`; si no, `[]`.

Respuesta (200):

```json
{
  "moneda": "MXN",
  "alcance": { "todos": true, "almacen_id": null, "almacen_nombre": null },
  "total": "1284500.00",
  "en_almacen": "903200.00",
  "en_resguardo": "352800.00",
  "en_transito": "28500.00",
  "articulos_sin_costo": 4,
  "unidades_sin_costo": 37,
  "por_categoria": [ { "categoria": "Equipo de alto valor", "valor": "512000.00" }, { "categoria": "Otras", "valor": "18400.00" } ],
  "por_almacen": [ { "almacen_id": "01a1…", "nombre": "Midrex", "en_almacen": "120400.00", "en_resguardo": "64000.00", "total": "184400.00" } ],
  "generado_en": "2026-10-08T16:20:00Z"
}
```

FEAT-013 lo extiende (alcance por conjunto y unidades): ver «Previsto por la iteración 01».

## Vales

El mismo cuerpo sirve para evaluar y para confirmar.

El cuerpo de `POST /api/vales` puede traer `almacen_id`: el almacén en el que se capturó el vale. Si viene y el usuario no tiene `almacenes.todos`, el servidor lo compara con el almacén de la sesión (`AccesoService.exigir_mismo_almacen`) y, si ya no coincide, responde 409 `ALMACEN_CAMBIO` sin guardar nada (AC-13). Quien tiene `almacenes.todos` elige el almacén en cada vale y la comparación no aplica.

```json
{
  "tipo": "ENTREGA",
  "trabajador_id": "01a10a17-…",
  "destino_almacen_id": null,
  "vale_origen_id": null,
  "renglones": [
    { "codigo": "ALT-024", "cantidad": 1, "condicion": null, "observacion": null }
  ]
}
```

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/vales/evaluar` | Sesión | El router exige sesión; el servicio comprueba el permiso correspondiente al tipo. Evalúa sin escribir. Acepta el mismo cuerpo que confirmar (ignora `id_cliente`, `observacion` y `firma`). Con `autorizacion_id` marca como `autorizado` los renglones naranja que esa autorización cubre. |
| `POST /api/vales` | Sesión | El router exige sesión; el servicio comprueba el permiso correspondiente al tipo. Confirma. Agrega `id_cliente`, `observacion`, `autorizacion_id` y `firma`. |
| `GET /api/vales/{id}` | `vales.ver` | Detalle con renglones. Fuera del alcance del usuario (AC-06), 404. |
| `GET /api/vales/{id}/firma` | `vales.ver` | La imagen de la firma del trabajador (PNG), con la misma visibilidad que el vale (AC-06). 404 si el vale no tiene firma en pantalla. Sirve para el detalle y la impresión: `tiene_firma` del detalle dice si existe. |
| `GET /api/vales/por-token/{token}` | `vales.ver` | El vale que abre su QR (mismo detalle). |
| `POST /api/vales/reservar-papel` | Sesión | El router exige sesión; el servicio permite solo ENTREGA y comprueba el permiso de ese tipo. Recibe el mismo cuerpo base de `POST /api/vales` con `firma.modo = PAPEL` y sin foto. Reevalúa el vale, reserva folio y QR durante 30 minutos y devuelve `{id, folio, token, vence_en, ticket, evaluacion}` para imprimir dos copias. El snapshot incluye trabajador, artículo, código de pieza y serie cuando aplica, observación y leyenda de responsabilidad. Repetir el mismo `id_cliente` y cuerpo devuelve la reserva vigente. |
| `POST /api/vales` con `firma.modo = PAPEL` | Sesión | El router exige sesión; el servicio comprueba el permiso correspondiente al tipo. Requiere `reserva_papel_id` y `firma.imagen` (foto del ticket firmado); no acepta trazo digital en ese modo. Confirma solo si la reserva vigente pertenece al usuario y almacén actuales y el cuerpo coincide. Reutiliza el folio y token reservados y enlaza la reserva al vale en la misma transacción. |
| `GET /api/vales?tipo=&almacen_id=&desde=&hasta=&trabajador_id=&usuario_id=` | `vales.ver` | Lista paginada, del más nuevo al más viejo. Sin `almacenes.todos`, solo los del almacén asignado, también si filtra por otro almacén o usuario. `desde` y `hasta` son fechas del centro de México, ambas inclusivas. Con el `usuario_id` de la sesión y las fechas de hoy resuelve "Mis movimientos de hoy" (C-12). |
| `GET /api/traspasos/por-recibir?solo_contar=&almacen_id=` | `traspasos.recibir` | Traspasos con algo En tránsito (estado `EN_TRANSITO` o `RECIBIDO_CON_DIFERENCIAS`) hacia el almacén de la sesión, del más antiguo al más nuevo, con sus renglones y lo ya recibido (forma abajo). Sin `almacenes.todos`, solo los del almacén asignado (un `almacen_id` distinto es 409 `ALMACEN_CAMBIO`); con él, `almacen_id` filtra y sin él trae los de todos los almacenes. Con `solo_contar=true` responde solo `{"total": n}`: es la consulta ligera del contador del inicio (cada 30 s). |
| `POST /api/trabajadores/{id}/no-adeudo` | `no_adeudo.emitir` | Emite el vale de no adeudo (B-04). Cuerpo `{id_cliente, observacion, almacen_id}`; `almacen_id` solo lo indica quien tiene `almacenes.todos` (AC-06). Si el trabajador está Activo, inicia su baja (B-01: queda en Baja en proceso, aunque después responda 409) y para eso exige además `trabajadores.iniciar_baja` (403 si falta; con la baja ya en proceso no se pide). Responde 409 `CON_PENDIENTES` con la lista si los hay; 409 si el trabajador ya está Inactivo. Sin pendientes responde 201 con `{id, folio, token, creado_en, renglones: [], trabajador: {id, numero_empleado, nombre, estado, estado_texto}}` (folio `…-NAD-…`, el trabajador queda Inactivo, B-08; `renglones` va vacío); 200 con el mismo cuerpo si el `id_cliente` ya existía. |
| `POST /api/vales/{id}/cancelacion` | `vales.cancelar` | Cancela con `{motivo, id_cliente, rehacer}` y genera los movimientos inversos (K-01 a K-04). Con `rehacer: true` la respuesta trae además un `borrador` con los renglones del vale original, sin firma ni autorización, para corregirlos y confirmar de nuevo (K-05). Con `vales.cancelar` solo los propios; con `vales.cancelar_todos`, los de cualquiera. Responde 409 `NO_CANCELABLE` si no procede. Forma exacta abajo, en "Cancelación". |

Permiso y campos propios de cada tipo. El permiso se verifica por clave, según el `tipo` del cuerpo, antes de leer nada (403 `SIN_PERMISO`):

| Tipo | Permiso | Campos propios |
|---|---|---|
| ENTRADA | `inventario.entradas` | **Entra siempre al almacén central (Kepler, EK-01)**: no hace falta indicar almacén y, si `almacen_id` o `destino_almacen_id` traen otro, 422 `ENTRADA_SOLO_KEPLER` (también para el Administrador); sin `almacenes.todos`, el usuario debe estar asignado a Kepler; en artículos por pieza, cada renglón lleva `pieza: {codigo, numero_serie, inspeccion: {fecha, resultado, observacion}}` (la inspección inicial es opcional, I-03). No acepta `trabajador_id` ni costos (el cuerpo rechaza campos desconocidos con 422). Firma de sesión (F-03). |
| ENTREGA | `entregas.crear` | `trabajador_id`; `firma` con `modo: "PANTALLA"` e `imagen` (F-02); `condicion` por renglón (`BUENO` por defecto, E-22). `almacen_id` solo para quien tiene `almacenes.todos`. |
| DEVOLUCION | `devoluciones.crear` | `condicion` por renglón (obligatoria, V-04); `observacion` obligatoria si es `DANADO` (V-05); `foto` opcional por renglón `DANADO` (`data:image/…;base64,…`, se guarda como adjunto `FOTO_DANO` ligado al movimiento); `trabajador_id` solo hace falta en renglones por cantidad (una pieza se abona a su titular). Sin firma: firma el almacenista con su sesión (F-08). |
| NO_ADEUDO | `no_adeudo.emitir` | `trabajador_id`; sin renglones. Lo usual es `POST /api/trabajadores/{id}/no-adeudo`; por `POST /api/vales` con pendientes responde 409 `VALE_CAMBIO` con el motivo `B-04`. |
| TRASPASO | `traspasos.operar` | `destino_almacen_id` (obligatorio); renglones por código de pieza, o de artículo con `cantidad`. Sin `trabajador_id`, `vale_origen_id`, `pieza` ni costos (422). Firma de sesión (F-09): no lleva `firma`. El vale queda `EN_TRANSITO`, folio `CLAVE-TRS-000001`. `almacen_id` solo para quien tiene `almacenes.todos`. `evaluar` trae en `motivos` del vale la regla X-03 (verde, amarillo o rojo) y por renglón X-02, X-04, X-09. **Ruta que no es padre-hijo (X-03, FEAT-008):** sin `almacenes.todos`, `evaluar` la marca en rojo y confirmar responde 403 `RUTA_SOLO_ADMINISTRADOR`; con `almacenes.todos`, `evaluar` da amarillo con `pide_observacion: true` (en el vale) y confirmar exige `observacion` en el vale (sin ella, 422 `DATOS_INVALIDOS` con `detalles: [{campo: "observacion", mensaje, regla: "X-03"}]`). Un origen o destino cerrado: 409 `ALMACEN_CERRADO` (AL-04). **Traslado lateral entre dos almacenes de tercer nivel (X-16 a X-20, FEAT-015):** `evaluar` trae `ruta: {clase: HABITUAL \| LATERAL \| NO_HABITUAL \| MISMO, autoriza: NADIE \| ENVIO_PROPIO \| SUPERVISOR_ORIGEN \| ADMINISTRADOR, autorizadores_disponibles}` (`autorizadores_disponibles` solo con `SUPERVISOR_ORIGEN`: cuántos usuarios activos pueden autorizar en el origen, sin contar a quien envía) y en los `motivos` del vale, antes que X-03, X-18 (verde, informa). Quien tiene `autorizaciones.resolver` en el origen: X-16, amarillo, `pide_observacion: true`; sin `observacion`, 422 `DATOS_INVALIDOS` con `detalles: [{campo: "observacion", mensaje, regla: "X-16"}]`; el vale queda con `valido.medio = "ENVIO_PROPIO"` (`autorizo` es quien envió y `autorizacion_id`, `null`) y sus movimientos llevan `X-16` y `X-18`; no se crea ninguna autorización. Quien no lo tiene y no tiene `almacenes.todos`: X-17, naranja, con `autorizable: true` (y `autorizado: true` si el cuerpo trae una `autorizacion_id` de TRASLADO que sirve); `puede_confirmar` es falso y confirmar sin autorización responde 409 `VALE_CAMBIO`. Con `autorizacion_id` (X-19) el vale se crea y la autorización pasa a `USADA` en la misma transacción; 409 `AUTORIZACION_INVALIDA` si no está aprobada, venció, ya se usó, es de otro origen o destino, o no cubre (solo se pueden quitar renglones); en la evaluación eso aparece como `autorizacion_error`. Quien tiene `almacenes.todos` sin `autorizaciones.resolver` hace el lateral por X-03 (amarillo y observación, `autoriza: ADMINISTRADOR`). X-20: aviso amarillo, sin pedir observación, si en el destino no hay ningún usuario activo con `traspasos.recibir` asignado a él. |
| RECEPCION | `traspasos.recibir` | `vale_origen_id` (el traspaso, obligatorio); `renglones`: lo escaneado, por código de pieza o de artículo con `cantidad` (para recibir todo, todos los pendientes de `por-recibir`; sin renglones, 422). Sin `trabajador_id` ni `destino_almacen_id` (422). Firma de sesión (F-09). Folio `CLAVE-REC-000001` del almacén que recibe; al confirmar, el traspaso queda `RECIBIDO` o `RECIBIDO_CON_DIFERENCIAS` (X-13). `evaluar`: X-10 (vale y renglones, rojo), X-12 (renglón, rojo), X-13 (vale, amarillo) y, si la recepción deja algo pendiente sin `observacion` (vacía o en blanco), RG-14 (vale, rojo). Al confirmar esa recepción sin observación responde 422 con `detalles: [{campo: "observacion", mensaje, regla: "RG-14"}]` y no guarda nada; la recepción que completa lo pendiente no la pide. Un `vale_origen_id` inexistente es 404 y el de un vale que no es traspaso, 422. **X-21:** si quien recibe es quien envió el traspaso (cualquier traspaso), `evaluar` trae X-21 en amarillo con `pide_observacion: true` y confirmar sin `observacion` es 422 con `regla: "X-21"`; las reglas de los movimientos de la recepción llevan `X-21`. |
| CANCELACION | `vales.cancelar` | `vale_origen_id` (el vale que se cancela) y `observacion` (el motivo); sin renglones: salen de los del original. Normalmente se usa `POST /api/vales/{id}/cancelacion`; `POST /api/vales` con este tipo hace lo mismo. |

**Enviar y recibir son dos permisos distintos.** `traspasos.operar` es solo para **enviar** (tipo TRASPASO, incluido el traspaso por lista de Excel); `traspasos.recibir` es para **recibir** (tipo RECEPCION y `GET /api/traspasos/por-recibir`). Como `POST /api/vales/evaluar` y `POST /api/vales` solo exigen sesión en el router, el servicio verifica la clave según el `tipo` del cuerpo: `traspasos.operar` para TRASPASO y `traspasos.recibir` para RECEPCION (403 `SIN_PERMISO` si falta). Un rol puede tener uno, el otro o los dos: de inicio el Supervisor trae los dos, el Almacenista trae `traspasos.recibir` (sin `traspasos.operar`) y el Administrador, todos (sección 8.2 de las reglas y `acceso/datos_prueba.py`; el texto anterior de X-01, que decía que el Almacenista no recibe de inicio, estaba atrasado, maestro de la iteración 01, sección 9). La interfaz de la recepción se muestra a quien tiene `traspasos.recibir`, no al rol. `GET /api/traspasos/por-recibir` ya declara su permiso en el router (no es una de las rutas que se verifican en el servicio).

**Pieza con serie pendiente en la ENTREGA (E-29).** Si un renglón entrega una pieza cuyo `numero_serie` es nulo, la evaluación le agrega el motivo `{regla: "E-29", codigo: "SERIE_PENDIENTE", nivel: "AMARILLO", mensaje: "Esta pieza no tiene número de serie registrado."}`. **No bloquea**: `puede_confirmar` no cambia y no pide observación. El renglón trae `pieza.serie_pendiente: true` para que la interfaz ofrezca capturar la serie. Traspaso, recepción y devolución no miran la serie.

**Almacén cerrado (AL-04, FEAT-008).** En cualquier tipo que mueve inventario (ENTRADA, ENTREGA, DEVOLUCION, TRASPASO, RECEPCION y CANCELACION), si el almacén del vale, o el origen o el destino de un traspaso, está `CERRADO`, `evaluar` trae un motivo rojo del vale con la regla `AL-04` y `POST /api/vales` responde 409 `ALMACEN_CERRADO` sin guardar nada. Las lecturas (consulta y reportes) no cambian.

Respuesta de `GET /api/traspasos/por-recibir` (sin costos; `codigo` es lo que se escanea al recibir: el de la pieza, o el del artículo si es por cantidad). `ruta` es `HABITUAL`, `LATERAL` (traslado entre almacenes de tercer nivel: la interfaz lo rotula «Traslado desde Midrex», X-20) o `NO_HABITUAL`; `valido` es quién lo validó (A-04) con la forma de `valido` del detalle del vale: `{autorizacion_id, solicito, autorizo, medio, resuelta_en, motivo}` con `medio` `PIN`, `REMOTA` o `ENVIO_PROPIO` (X-16, sin autorización: `autorizacion_id` y `solicito` van `null`), o `null` si nadie lo validó (ruta habitual).

```json
{
  "total": 1,
  "elementos": [
    {
      "id": "01a1…", "folio": "KEP-TRS-000012", "token": "…", "estado": "RECIBIDO_CON_DIFERENCIAS",
      "origen": { "id": "01a1…", "clave": "KEP", "nombre": "Kepler" },
      "destino": { "id": "01a1…", "clave": "CON", "nombre": "Contratistas" },
      "envio": { "id": "01a1…", "nombre": "Almacenista Kepler" },
      "ruta": "HABITUAL",
      "valido": null,
      "creado_en": "2026-10-05T15:20:00Z",
      "pendiente_total": 3,
      "renglones": [
        { "renglon": 1, "articulo_id": "01a1…", "articulo": "Guante", "marca": "…", "modelo": null, "talla": "M",
          "codigo": "GUA-001", "pieza_id": null, "numero_serie": null,
          "cantidad_enviada": 6, "cantidad_recibida": 4, "cantidad_pendiente": 2 }
      ],
      "recepciones": [ { "id": "01a1…", "folio": "CON-REC-000003", "creado_en": "…", "recibio": { "id": "01a1…", "nombre": "Almacenista Contratistas" } } ]
    }
  ]
}
```

Respuesta de `evaluar`:

```json
{
  "nivel": "ROJO",
  "puede_confirmar": false,
  "pide_observacion": false,
  "renglones": [
    {
      "renglon": 1,
      "codigo": "ALT-024",
      "articulo": { "id": "01a10a2b-…", "nombre": "Arnés poliéster", "marca": "…", "talla": "M", "control": "PIEZA" },
      "pieza": { "id": "01a10a3c-…", "estado": "APTO", "inspeccion_vigente_hasta": "2026-09-30" },
      "titular": null,
      "cantidad": 1,
      "disponible": 1,
      "nivel": "ROJO",
      "motivos": [
        { "regla": "E-06", "nivel": "ROJO", "mensaje": "Inspección vencida el 30/09/2026." }
      ],
      "pide_observacion": false,
      "autorizable": false,
      "requiere_confirmacion": false
    }
  ]
}
```

**Avisos de la dotación (FEAT-003) en la ENTREGA.** Si el trabajador tiene dotación (su periodo vigente está ligado a un puesto con renglones), un renglón fuera de la dotación o que, con lo ya entregado y lo que lleva el vale, supera lo recomendado trae el motivo `{regla: "E-09", nivel: "AMARILLO", mensaje}` y `pide_observacion: true`; la evaluación trae arriba `pide_observacion: true` si algún renglón la pide (un renglón en rojo no la pide). No bloquea: `puede_confirmar` sigue verdadero. Si el renglón además supera el límite (L-02, L-03) o pide autorización, el nivel es NARANJA y los motivos traen los dos (`["L-03", "E-09"]`). Al confirmar con `pide_observacion` verdadero hace falta una observación de texto no vacío en ese renglón (`renglones[].observacion`) o en el vale (`observacion`); si no, 422 `DATOS_INVALIDOS` con `detalles: [{campo: "renglones.N.observacion", mensaje, regla: "E-09"}]` y no se guarda nada. La observación se guarda en el movimiento (la del vale se copia a los renglones E-09 que no traen la suya) y `GET /api/reportes/movimientos` la devuelve en `observacion`. `E-10` (la talla del artículo no coincide con ninguna de las del trabajador) y `E-11` (la inspección de la pieza vence en 7 días o menos) son AMARILLO sin observación (`pide_observacion` no cambia). Un trabajador sin puesto del catálogo o con el puesto sin dotación no genera E-09.

Además de lo anterior, la evaluación trae arriba `motivos` (los que valen para todo el vale: E-02 y E-12), `almacen` y, en una ENTREGA, `trabajador` (la ficha breve: foto, vigencia y resguardo, sin CURP ni NSS). Cada renglón trae también `autorizado` (un naranja que la `autorizacion_id` del cuerpo ya cubre) y, si la autorización indicada no sirve, `autorizacion_error` arriba explica por qué. `titular` dice dónde está una pieza que no está en este almacén (E-03), solo a quien tiene `almacenes.todos`; para los demás va con `tipo` y `id` nulos, sin nombre y con la descripción «no está registrada en tu almacén», y el motivo no nombra el almacén ni al trabajador (AC-06). Una pieza en tránsito desde o hacia el almacén del usuario conserva su explicación. Si la pieza está en un lugar virtual, `titular.nombre` va en español llano («En tránsito a Contratistas»; nunca la clave interna) y `descripcion` explica dónde está. Un trabajador no vigente (E-02) pone en rojo todos los renglones. `nivel` es el más grave de los renglones y de `motivos`; `puede_confirmar` es verdadero sin rojos, con todos los naranjas autorizados y al menos un renglón. En ENTRADA, `pieza.id` va vacío (la pieza aún no existe) y `pieza.pendiente_inspeccion` avisa que entra sin inspección.

La ENTREGA normaliza los renglones antes de evaluar: una pieza repetida se ignora (E-15) y un artículo por cantidad repetido suma (E-16). Cada motivo lleva el ID de su regla: E-01 a E-06, E-09 a E-12, E-19, E-26, E-27, RG-05 y, para el límite, `L-02` (retornables, lo que tiene más lo que pide) o `L-03` (consumibles, lo entregado en los últimos N días más lo que pide) con el detalle "límite 2, tiene 2, pide 1" (L-04). En ENTRADA: E-01, I-02, I-03, I-09.

**DEVOLUCION.** El mismo cuerpo, con `condicion` en cada renglón. Una pieza se escanea (su código o el que devuelve la búsqueda por número de serie, V-14) y se abona a su titular sin credencial (V-01); un artículo por cantidad lleva `trabajador_id` y `cantidad` (V-03). La normalización ignora una pieza repetida y suma un artículo por cantidad repetido **con la misma condición**. Cada renglón trae `titular` (el trabajador al que se abona o, en V-02, dónde está la pieza según el sistema) y `disponible` (lo que ese titular tiene en resguardo del artículo; 1 o 0 en una pieza). `pide_observacion` es verdadero si es `DANADO`. Reglas en la respuesta: V-01 y V-06 (verde, informativas), V-02 (amarillo: nada que devolver, el renglón no genera movimiento), V-03, V-04, V-05 (rojo sin observación; amarillo con ella: la pieza entra No apta, el artículo por cantidad va a Baja y nunca hay cargo), V-07 (amarillo: lo entregó otro almacén; entra al almacén de la sesión), V-12 (rojo, "No es de la empresa"), V-14 (rojo: el código de un artículo por pieza no sirve), RG-05. SM-05: ninguna regla del trabajador (E-02), de límites, de autorización ni de artículo inactivo se evalúa. Si TODOS los renglones son V-02 la evaluación trae un motivo rojo `V-02` arriba y no se puede confirmar; si solo algunos lo son, se confirma con los demás y los V-02 no dejan movimiento. El vale lleva folio `…-DEV-…`, `firma_modo = SESION`, y su `trabajador` es el del abono (nulo si trae piezas de varios titulares; cada renglón del vale ya indica `origen`). Una pieza dañada queda No apta con su evento en el historial de la pieza. Sin costos (F-12).

`requiere_confirmacion` es verdadero cuando la cantidad del renglón alcanza el aviso de cantidad inusual del artículo (E-27); la interfaz pide confirmarla y no decide nada por su cuenta. `evaluar` nunca escribe: el borrador vive en el dispositivo hasta `POST /api/vales` (E-28).

Al confirmar se agrega:

```json
{
  "id_cliente": "b1f6…",
  "observacion": null,
  "autorizacion_id": null,
  "firma": { "modo": "PANTALLA", "imagen": "data:image/png;base64,…", "trazo": [] }
}
```

- Responde 201 con el vale: `{id, folio, token, creado_en, renglones}`; cada renglón trae `{renglon, codigo, articulo, cantidad, nivel, reglas}`. Nunca trae costos (F-12).
- Si el `id_cliente` ya existe y el cuerpo es el MISMO, responde 200 con el vale que se guardó la primera vez (también ante dos confirmaciones simultáneas); si es de otro usuario o de otro tipo, o si el cuerpo es DISTINTO, 409 `CONFLICTO` ("Ese vale ya se guardó antes con otros datos"). La comparación usa una huella SHA-256 del cuerpo (`vale.huella_cuerpo`) que no incluye la imagen ni el trazo de la firma: volver a firmar en un reintento no cambia el vale, que conserva la firma de la primera vez. Los vales anteriores a la columna no tienen huella y se tratan como repetición.
- Si la evaluación cambió o queda un rojo o un naranja sin autorizar, responde 409 `VALE_CAMBIO` con la evaluación nueva en `detalles` y no guarda nada (RG-08, RG-09).
- Una `autorizacion_id` que no sirve (no aprobada, vencida, usada, de otro trabajador o que no cubre los renglones) responde 409 `AUTORIZACION_INVALIDA`; si quien confirma es quien autorizó, 403 `AUTORIZACION_PROPIA`. Una autorización que el vale no necesita no se gasta.
- Una ENTREGA sin `firma.imagen` responde 422 con `detalles[0].campo = "firma"` y `regla = "F-02"`.
- La firma se valida de verdad (F-02): `firma.imagen` debe ser un PNG completo (cabecera, 100x50 a 4000x4000 píxeles, datos de imagen que miden lo declarado, cierre y sumas de comprobación correctas, mínimo 150 bytes) y `firma.trazo` debe traer al menos 10 puntos `{x, y, t}` numéricos y como máximo 20 000 (una lista de trazos, cada uno una lista de puntos, como la manda la interfaz, o una lista plana de puntos). Si no, 422 con `detalles[0].campo` `firma.imagen` o `firma.trazo`. El control impide el atajo trivial de mandar una imagen o un trazo de relleno; no impide que se dibuje cualquier cosa.
- Tamaño: cada `foto` de un renglón pasa de 4 millones de caracteres (~3 MB de imagen) → 422; las fotos de un vale suman como máximo 10 MiB de texto → 422. El cuerpo completo tiene su tope por ruta (abajo).
- Todo ocurre en una transacción: vale, movimientos, existencias, ubicación de las piezas, firma y autorización usada. El folio es `CLAVE-TIPO-CONSECUTIVO` (`KEP-ENT-000123`; los prefijos de cada tipo están en data-model.md).

Detalle del vale (`GET /api/vales/{id}` y `por-token`): `{id, folio, token, tipo, estado, almacen, destino_almacen, trabajador {id, numero_empleado, nombre, puesto, area_obra}, responsable, observacion, firma_modo, tiene_firma, valido, vale_origen_id, vale_origen_folio, cancelacion, dispositivo, creado_en, renglones}`. Cada renglón: `{renglon, articulo, marca, modelo, talla, codigo_articulo, codigo_pieza, numero_serie, cantidad, condicion, nivel, reglas, observacion, origen, destino, saldo_origen, saldo_destino}`. `valido` es el "Validó" de A-04: `{autorizacion_id, solicito, autorizo, medio, resuelta_en, motivo}` o `null`. `cancelacion` solo viene en un vale con `estado = CANCELADO`: `{id, folio, motivo, responsable {id, nombre}, creado_en}` del vale de cancelación que lo canceló (K-02); en los demás es `null`. Sin costos.

### Cancelación (`POST /api/vales/{id}/cancelacion`)

Cuerpo: `{ "motivo": "Capturé el artículo equivocado", "id_cliente": "c4a1…", "rehacer": false }`. `motivo` es obligatorio (sin él, 422; K-01) y queda en `observacion` del vale de cancelación. `id_cliente` lo genera el dispositivo (un doble toque no cancela dos veces). `rehacer` es opcional (`false` por defecto).

Quién (K-01), antes de leer nada más:

- 404 si el vale no existe o está fuera del almacén del usuario (AC-06).
- 403 `SIN_PERMISO` si el vale no es suyo y no tiene `vales.cancelar_todos`: "Solo puedes cancelar los vales que tú hiciste."
- 409 `NO_CANCELABLE` (X-14) si quien lo pide es del almacén de destino de un traspaso y no puede operar todos los almacenes: lo cancela el almacén de origen.

Qué hace, en una sola transacción (RG-09): genera un vale de CANCELACION con su propio folio (`KEP-CAN-000001`, del almacén del vale original; en un traspaso, el de origen) y los movimientos inversos de todos los del original (origen y destino invertidos, misma pieza y cantidad; copian `trabajador_id` y `condicion`, así el reporte de consumo C-08 los resta); regresa las existencias y `pieza.ubicacion_id`; deja el original con `estado = CANCELADO`, y anota en la auditoría `vale.cancelar` (entra a la lista de revisión, K-01). La autorización que usó una entrega cancelada sigue USADA (A-03). No se cancela parcialmente.

Cuándo responde 409 `NO_CANCELABLE`, sin escribir nada. Cada motivo lleva su regla:

| Regla | Motivo |
|---|---|
| K-03 | La pieza ya se movió después de este vale (el mensaje dice dónde está o quién la tiene), o tuvo otros movimientos después. |
| K-03 | Las existencias ya no alcanzan para revertirlo ("se necesitan 10 en el almacén KEP y hay 2"). |
| K-03 | El vale ya está cancelado (el mensaje trae el folio de su cancelación). |
| K-04 | Es una recepción, un vale de no adeudo o una cancelación. |
| X-14 | Es un traspaso que ya se recibió (se cancela solo en tránsito, antes de la recepción). |

`POST /api/vales/evaluar` con `{"tipo": "CANCELACION", "vale_origen_id": "…"}` previsualiza lo mismo sin escribir: un renglón por movimiento del original, en rojo con su regla si no se puede.

Respuesta: 201 (o 200 si el `id_cliente` ya existía: la misma respuesta, sin crear nada más):

```json
{
  "id": "01a1…", "folio": "KEP-CAN-000001", "token": "…", "creado_en": "2026-10-05T16:20:00Z",
  "renglones": [ { "renglon": 1, "codigo": "GUA-001", "articulo": "Guantes", "cantidad": 10, "nivel": "VERDE", "reglas": ["K-02"] } ],
  "vale_cancelado": { "id": "01a0…", "folio": "KEP-ENT-000012", "estado": "CANCELADO" },
  "motivo": "Capturé el artículo equivocado",
  "borrador": null
}
```

Con `"rehacer": true`, `borrador` trae los datos del vale cancelado, con la forma del cuerpo de `POST /api/vales/evaluar`, listo para que la interfaz lo cargue, corrija y confirme como un vale nuevo (K-05):

```json
"borrador": {
  "tipo": "ENTREGA",
  "almacen_id": "01a0…",
  "trabajador_id": "01a1…",
  "destino_almacen_id": null,
  "observacion": null,
  "renglones": [
    { "codigo": "GUA-001", "cantidad": 10, "condicion": "BUENO", "observacion": null, "pieza": null }
  ]
}
```

- Sin `firma`, sin `autorizacion_id` y sin `id_cliente`: el vale nuevo se firma de nuevo, se vuelve a evaluar completo (puede salir naranja o rojo aunque el original no lo fuera) y la interfaz genera su `id_cliente`.
- `codigo` es el de la pieza en los renglones de una pieza, y el del artículo en los de cantidad. `condicion` y `observacion` son las del movimiento original.
- `trabajador_id` va en ENTREGA y DEVOLUCION; `destino_almacen_id`, en TRASPASO; `almacen_id` es el almacén del vale original.
- En una ENTRADA de una pieza, `codigo` es el del artículo y `pieza` trae el `{codigo, numero_serie}` que tenía. Esa pieza sigue registrada (queda en PROVEEDOR) y su código no se puede reutilizar (RG-10): para rehacerla hay que capturar otro código y otra serie.

## Autorizaciones

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/autorizaciones` | Sesión | El router exige sesión; el servicio valida `entregas.crear` para EXCEDENTE/DESPACHO y `traspasos.operar` para TRASLADO. Solicita con `{tipo?, trabajador_id, renglones, motivo}` (`tipo`: `EXCEDENTE` por omisión o `TRASLADO`; ver abajo el traslado). Responde 201 `{id, tipo, estado, vence_en}`. El motivo es obligatorio (A-02); el almacén sale de la sesión; `vence_en` es ahora más 15 minutos (`AUTORIZACION_VIGENCIA_MINUTOS`). De cada renglón del cuerpo el servidor toma SOLO `{codigo, cantidad}`; cualquier otro campo (`articulo`, `limite`, `tiene`, `excedente`, `regla`, `mensaje`, `autorizable`...) se ignora. Con su propia evaluación arma y guarda `{codigo, articulo_id, articulo, cantidad, limite, tiene, excedente, regla, mensaje, autorizable}`, que es lo que lee quien autoriza y lo que responden los `GET`. Un renglón que no sea naranja en esa evaluación (rojo: A-06; verde o amarillo: no necesita autorización) da 422 `RENGLON_NO_AUTORIZABLE` con `detalles: {codigo, regla, nivel, motivos}` y no se guarda nada. |
| `GET /api/autorizaciones/{id}` | Sesión | Estado de una solicitud, con `tipo`, renglones, quién la pidió y quién la resolvió; `trabajador` (`null` en un traslado) y, en un traslado, `origen` y `destino` `{id, clave, nombre}` (`almacen_id` es el origen). La ve quien la pidió y quien tiene `autorizaciones.resolver` en su almacén (con `almacenes.todos`, en todos); para los demás, 404. Si venció, responde `VENCIDA`. El solicitante la consulta cada tres segundos. |
| `GET /api/autorizaciones?estado=PENDIENTE&tipo=` | `autorizaciones.resolver` | Solicitudes por resolver (`estado` por defecto `PENDIENTE`; `tipo` opcional), con `tipo`, trabajador (`null` en un traslado), `origen` y `destino` (traslado), renglones, `excedente_total`, motivo y quién la pide. Sin `almacenes.todos`, solo las de su almacén (AC-06). |
| `POST /api/autorizaciones/{id}/resolucion` | `autorizaciones.resolver` | `{decision}` desde la sesión de quien autoriza (medio REMOTA); o `{decision, usuario, pin}` desde el dispositivo del almacenista (medio PIN). `decision`: `APROBAR` o `RECHAZAR`. En el segundo caso la sesión es la del almacenista (`entregas.crear`) y el permiso `autorizaciones.resolver`, el almacén y el PIN se verifican sobre ese usuario. Errores: 403 `AUTORIZACION_PROPIA` (A-05), 403 `PIN_INCORRECTO`, 429 `DEMASIADOS_INTENTOS`, 409 `AUTORIZACION_RESUELTA`. En un traslado, el permiso para pedir es `traspasos.operar` (con PIN, lo tiene la sesión de quien envía), quien resuelve debe ser supervisor del origen (o tener `almacenes.todos`; para los demás, 404) y `renglones` no se acepta (422 con `regla: "X-19"`): se aprueba o se rechaza completa. |

**Autorización de traslado (FEAT-015, X-17 y X-19).** Cuerpo de `POST /api/autorizaciones` con `tipo: "TRASLADO"`: `{tipo, destino_almacen_id, renglones: [{codigo, cantidad}], motivo, almacen_id?}`, sin `trabajador_id` (422 si lo trae); `almacen_id` solo para quien tiene `almacenes.todos`; el origen es el almacén de la sesión. El servidor evalúa el traspaso como lo evaluaría quien lo pide: un renglón o el vale en rojo es 422 `RENGLON_NO_AUTORIZABLE` (A-06), y también si el traslado no necesita autorización (`detalles.regla: "X-17"`: ruta habitual, o quien pide es supervisor del origen y su envío es la autorización, X-16). Guarda la solicitud `PENDIENTE` con `trabajador_id` nulo, `almacen_id` = origen y en `detalle`: `origen_almacen_id`, `destino_almacen_id` y los renglones evaluados; vence a los 15 minutos. Un destino que no existe es 404. Se usa con `POST /api/vales` (TRASPASO) y `autorizacion_id`, o con `POST /api/importacion/traspasos`. `id_cliente` lo agrega FEAT-014; hoy se ignora. La notificación push a los supervisores del origen llega con el módulo `notificaciones` (FEAT-014): mientras tanto la solicitud se ve en la lista del supervisor.

La autorización aprobada se usa una sola vez (A-03) con `POST /api/vales` y `autorizacion_id`; el vale la valida y la marca usada en su misma transacción. Al solicitar, el servidor evalúa de verdad los renglones (la misma evaluación de la ENTREGA) y rechaza con 422 `RENGLON_NO_AUTORIZABLE` los que están en rojo, aunque quien los pide los marque `autorizable` (A-06, SM-04); `detalles` trae el `codigo`, la `regla` y los `motivos`.

## Solicitudes de compra

La solicitud de compra urgente (reglas SC-01 a SC-11, sección 7.13 de las [reglas](../product/reglas-de-negocio.md)). Todo va bajo `/api/solicitudes-compra`. Permisos: `compras.solicitar` (pedir y cancelar; de inicio Almacenista, Supervisor y Administrador) y `compras.atender` (hacer avanzar la solicitud; de inicio Compras y Administrador). En las dos lecturas, el router solo exige sesión y el servicio verifica cualquiera de los dos permisos (403 `SIN_PERMISO` si no tiene ninguno). El módulo no escribe inventario (SC-11).

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/solicitudes-compra` | `compras.solicitar` | Levanta una solicitud (SC-01, SC-02). Cuerpo abajo. 201 con la solicitud completa; 200 con la misma si el `id_cliente` ya existía con el mismo cuerpo (SC-10). El almacén sale del usuario; con `almacenes.todos` se indica `almacen_id`. Un almacén cerrado no recibe solicitudes nuevas: 409 `ALMACEN_CERRADO` (AL-04). |
| `GET /api/solicitudes-compra` | Sesión | El router exige sesión y el servicio requiere `compras.solicitar` o `compras.atender`. Lista paginada (`{elementos, total}`) de lo que el usuario ve (SC-03): con `compras.atender` o `almacenes.todos`, las de todos los almacenes; si no, las de su almacén (y nada si no tiene almacén). Filtros: `estado`, `urgencia`, `almacen_id` (con alcance restringido, pedir otro almacén no devuelve nada), `q` (folio, descripción, nombre o código del artículo y motivo; sin distinguir mayúsculas ni acentos), `desde` y `hasta` (fechas de México, `AAAA-MM-DD`; el día `hasta` entra completo; un rango invertido da 422), `mias=true` (solo las que pidió el usuario), `pagina` y `tamano`. Con `solo_contar=true` responde `{"total": n}` con los mismos filtros, para el contador del menú (por ejemplo `estado=PENDIENTE`). Orden: primero PENDIENTE, luego EN_COMPRA, COMPRADA y al final lo cerrado; en cada grupo, URGENTE antes que NORMAL y las más antiguas primero (lo cerrado, la más reciente primero). |
| `GET /api/solicitudes-compra/{id}` | Sesión | El router exige sesión y el servicio requiere `compras.solicitar` o `compras.atender`. Devuelve el detalle: la solicitud y su línea de tiempo (`eventos`). Fuera del alcance del usuario, 404. |
| `POST /api/solicitudes-compra/{id}/estado` | `compras.atender` | `{estado, nota?, vale_entrada_id?}`. Transiciones válidas (SC-04): PENDIENTE a EN_COMPRA o RECHAZADA, EN_COMPRA a COMPRADA o RECHAZADA, COMPRADA a INGRESADA. Rechazar exige `nota` (SC-05, 422). `vale_entrada_id` solo con `estado: INGRESADA`, es opcional y debe ser un vale de ENTRADA que exista, no esté cancelado y sea de un almacén en el alcance de quien lo liga (SC-06, 422). Cualquier otra transición: 409 `TRANSICION_INVALIDA`. Responde el detalle. |
| `POST /api/solicitudes-compra/{id}/cancelacion` | `compras.solicitar` | `{nota?}` (el cuerpo es opcional). Solo mientras está PENDIENTE (409 `NO_CANCELABLE` si no) y solo por quien la pidió, por un supervisor de su almacén (`vales.cancelar_todos`) o por quien tiene `almacenes.todos` (403 `SIN_PERMISO` si no; 404 si no la ve). Responde el detalle (SC-07). |

No hay métodos que editen o borren una solicitud ni sus eventos (SC-08).

**Cuerpo de `POST /api/solicitudes-compra`:**

```json
{
  "id_cliente": "6f0c8c0e-2f6e-4f4a-9a53-0b1f4d1b9a10",
  "articulo_id": null,
  "descripcion": "Llave métrica 24 mm",
  "cantidad": 2,
  "motivo": "Mantenimiento de un equipo europeo en Midrex",
  "urgencia": "URGENTE",
  "almacen_id": null
}
```

`id_cliente` (UUID que genera el dispositivo) es obligatorio. Hace falta `articulo_id` (artículo activo del catálogo; con él se toma su nombre y `descripcion` se ignora) o, sin él, `descripcion` (texto libre). `cantidad` es un entero de 1 en adelante; `motivo` es obligatorio; `urgencia` es `URGENTE` (por omisión) o `NORMAL`. `almacen_id` solo lo indica quien tiene `almacenes.todos` (y lo exige); para los demás debe ser el suyo o no venir. El mismo `id_cliente` con el mismo cuerpo (el almacén ya resuelto) devuelve la misma solicitud con 200; con otro cuerpo o de otro usuario, 409 `ID_CLIENTE_EN_USO`.

**Respuesta de la solicitud** (cada elemento de la lista trae lo mismo, sin `eventos`):

```json
{
  "id": "01a10fe7-76c8-76d5-b333-9ff4e3d49f27",
  "folio": "MID-SOL-000001",
  "estado": "PENDIENTE",
  "urgencia": "URGENTE",
  "almacen": { "id": "01a10fe7-4db0-…", "clave": "MID", "nombre": "Midrex" },
  "solicitante": { "id": "01a10fe7-638a-…", "nombre": "Almacenista Midrex" },
  "articulo": null,
  "descripcion": "Llave métrica 24 mm",
  "cantidad": 2,
  "motivo": "Mantenimiento de un equipo europeo en Midrex",
  "nota_compras": null,
  "vale_entrada": null,
  "creada_en": "2026-10-06T06:29:49.894352Z",
  "actualizada_en": "2026-10-06T06:29:49.894352Z",
  "acciones": ["tomar", "rechazar"],
  "eventos": [
    {
      "id": "01a10fe8-7321-…",
      "estado_anterior": null,
      "estado_nuevo": "PENDIENTE",
      "usuario": { "id": "01a10fe7-638a-…", "nombre": "Almacenista Midrex" },
      "nota": null,
      "creado_en": "2026-10-06T06:29:49.894352Z"
    }
  ]
}
```

- `articulo` es `{id, codigo, nombre}` o `null` si el equipo no está en el catálogo; `descripcion` siempre trae un texto (el nombre del artículo, si lo hay).
- `vale_entrada` es `{id, folio}` o `null`; solo lo tiene una solicitud INGRESADA a la que Compras ligó un vale (SC-06), que debe ser una entrada de Kepler (EK-05); el almacén solicitante la recibe luego por traspaso.
- `nota_compras` es la última nota que dejó Compras (por ejemplo, el motivo del rechazo).
- `eventos` va del más antiguo al más reciente; el primero tiene `estado_anterior: null` y `estado_nuevo: "PENDIENTE"`. Cada cambio de estado agrega uno (SC-08).
- `acciones` la calcula el servidor según el permiso del usuario y el estado actual, siempre en este orden: `tomar` (PENDIENTE a EN_COMPRA), `rechazar` (desde PENDIENTE o EN_COMPRA), `comprar` (EN_COMPRA a COMPRADA), `ingresar` (COMPRADA a INGRESADA) y `cancelar`. Con `compras.atender` salen las de Compras; `cancelar` sale solo si está PENDIENTE y el usuario puede cancelarla (SC-07). Una solicitud cerrada (INGRESADA, RECHAZADA, CANCELADA) trae `[]`.

| Estado | Con `compras.atender` | Con `compras.solicitar` (quien la pidió, supervisor de su almacén o `almacenes.todos`) |
|---|---|---|
| PENDIENTE | `tomar`, `rechazar` | `cancelar` |
| EN_COMPRA | `rechazar`, `comprar` | ninguna |
| COMPRADA | `ingresar` | ninguna |
| INGRESADA, RECHAZADA, CANCELADA | ninguna | ninguna |

Errores propios (todos con el ID de la regla en `detalles.regla`): 409 `TRANSICION_INVALIDA` (`detalles`: `{regla: "SC-04", estado_actual, estado_pedido, estados_permitidos}`), 409 `NO_CANCELABLE` (`{regla: "SC-07", estado_actual}`), 409 `ID_CLIENTE_EN_USO` (`{regla: "SC-10"}`), 403 `SIN_PERMISO` al cancelar sin ser quien corresponde (`{regla: "SC-07"}`), y 422 `DATOS_INVALIDOS` con `detalles: [{campo, mensaje, regla}]` cuando falta la nota al rechazar (SC-05), el vale de entrada no sirve (SC-06) o el artículo está inactivo (SC-02).

## Importación

La importación tiene dos **modos** (`modo`, regla I-10): `ALTA` (por omisión, compatible con lo que ya existía) y `REPOSICION`.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/importacion/plantilla` | `inventario.importar` | Descarga un `.xlsx` de ejemplo para el modo del parámetro `modo` (`ALTA` o `REPOSICION`): encabezados que el sistema reconoce, una fila de ejemplo y una hoja de instrucciones. La columna de costo solo viene con `catalogo.costos` y solo en `ALTA`. No trae columna de almacén (EK-03). Sin `modo`, `ALTA`. No lee ni escribe datos. |
| `POST /api/importacion/vista-previa` | `inventario.importar` | Recibe `{modo, filas, columnas}` y devuelve filas válidas, filas con error y artículos que se crearían. No escribe. |
| `POST /api/importacion/archivo` | `inventario.importar` | Recibe un `.xlsx` (multipart, campo `archivo`, y el campo opcional `modo`), lo convierte en las mismas filas y responde `{hoja, encabezados, columnas, primera_fila, filas, vista_previa}`. No escribe ni guarda el archivo. |
| `POST /api/importacion` | `inventario.importar` | Confirma (pide además `inventario.entradas`, porque escribe un vale de entrada; el alta que crea artículos pide además `catalogo.administrar`, I-10, y se revisa por fila): en `ALTA` crea los artículos faltantes; en los dos modos, un vale de entrada a Kepler (EK-01; la columna `almacen` y `almacen_por_defecto` se ignoran con un aviso). 201; con un `id_lote` ya confirmado, 200 con `repetida: true`. |

El router de estas rutas exige `inventario.importar` (AC-30: importar desde Excel se separa de capturar a mano, que pide `inventario.entradas`). El permiso `catalogo.administrar` del alta depende de las filas (solo se pide si alguna crearía un artículo), así que lo revisa el servicio y se reporta por fila (`SIN_PERMISO_CREAR`), no como 403 de la petición.

La tabla se lee en el navegador (pegada desde Excel, o un `.xlsx` leído allá); al servidor llegan filas ya separadas en columnas. Con `POST /archivo` el servidor lee el `.xlsx` y devuelve las filas ya separadas para reenviarlas a los otros dos endpoints.

**Cuerpo** (vista previa y confirmación):

```json
{
  "modo": "ALTA",
  "filas": [["MART-01", "Martillo", "Truper", "Herramienta manual", "12", "Kepler", "", "85.50", "", "pieza"]],
  "columnas": {"codigo": 0, "nombre": 1, "marca": 2, "categoria": 3, "cantidad": 4,
               "almacen": 5, "serie": 6, "costo": 7, "codigo_pieza": 8, "unidad": 9},
  "primera_fila": 2,
  "categoria_por_defecto_id": null,
  "mapa_categorias": {"Cosas raras": "<categoria_id>"},
  "categoria_por_fila": {"5": "<categoria_id>"},
  "almacen_por_defecto": null,
  "id_lote": "<uuid>",
  "confirmar_repetido": false
}
```

- `modo` es `"ALTA"` o `"REPOSICION"`; si falta, `ALTA`. Otro valor da 422.
- `filas` son solo las de datos (máximo 5 000, 30 columnas, 500 caracteres por celda); cada celda es texto, número o vacía. `columnas` da el índice (desde 0) de cada dato y una columna no puede ser dos datos. Sin `columnas`, se acepta `encabezados` (el nombre de cada columna) y el servidor las propone. `codigo` es el del artículo; `codigo_pieza`, el de cada pieza en artículos por pieza (opcional: si falta, el servidor lo genera al confirmar, ver «Código de pieza generado»). `unidad` (opcional, solo `ALTA`; el servidor reconoce los encabezados «unidad», «u.m.» y «medida») es la unidad de un artículo **nuevo** (texto de hasta 20 caracteres; vacía, «pieza»). En `REPOSICION` se ignora con un aviso.
  - **`REPOSICION`:** solo se leen `codigo`, `cantidad`, `almacen` y, en artículos por pieza, `codigo_pieza` y `serie`. `codigo` es obligatorio; sin esa columna, 422. Si vienen `nombre`, `marca`, `categoria` o `costo`, se ignoran con un aviso.
  - **`ALTA`:** son obligatorias `cantidad` y al menos una de `codigo` o `nombre`. Sin código en una fila de un artículo nuevo, el servidor lo genera (`PREFIJO-NNNN`, regla I-10 y sección «Código generado»).
- `primera_fila` es el número que tiene la primera fila de `filas` en la hoja (2 si la hoja traía encabezados; por defecto 1): los errores se reportan con ese número.
- Categoría de un artículo nuevo, de más a menos fuerte: la columna `categoria` del archivo (si existe, o su equivalente en `mapa_categorias`); `categoria_por_fila` (`{número de fila: categoria_id}`, lo que el usuario eligió o aceptó en la vista previa); `categoria_por_defecto_id`. La sugerencia del servidor (I-14) **nunca se aplica sola**: solo cuenta si la interfaz la manda de vuelta en `categoria_por_fila`. Una categoría elegida que no existe o está inactiva da 422. `almacen_por_defecto` (clave o nombre) es el almacén de las filas sin almacén; sin él, Kepler (o el almacén asignado si no se tiene `almacenes.todos`).
- `id_lote` (UUID del cliente) es obligatorio al confirmar y se ignora en la vista previa.
- `confirmar_repetido` (por omisión `false`) se manda en `true` para confirmar un archivo que la vista previa avisó como ya importado (I-12). Se ignora en la vista previa.

**Reglas que revisa el servidor en cada fila** (la misma revisión en la vista previa y al confirmar; cada motivo lleva el ID de su regla):

| Regla | Qué rechaza |
|---|---|
| I-06 | Falta el código o el nombre (de un artículo nuevo); un dato pasa del largo permitido. |
| I-10 | `REPOSICION`: un código que no existe en el catálogo (`ARTICULO_NO_EXISTE`, «Ese artículo no existe: dalo de alta primero»). `ALTA`: una fila que crearía un artículo sin que el usuario tenga `catalogo.administrar` (`SIN_PERMISO_CREAR`). |
| I-01 | Cantidad vacía, no entera o ≤ 0 (en artículos por cantidad); almacén desconocido, cerrado o vacío sin almacén por defecto. |
| I-11 | Cantidad mayor que el tope por fila, 100 000 por omisión (`CANTIDAD_EXCESIVA`; el tope se ajusta por configuración). |
| I-13 | Cantidad con decimales (`0.25`) o con una coma ambigua (`0,25`, `1,5`): `CANTIDAD_NO_ENTERA`, con el mensaje «La cantidad debe ser un número entero. Usa una unidad menor (por ejemplo, 250 gramos en lugar de 0.25 kilos)». Nunca se redondea. La coma solo vale como separador de miles en grupos de tres dígitos (`1,250` es 1250); `12.0` es 12. |
| AC-06 | Sin `almacenes.todos`, un almacén que no es el asignado. |
| CF-02 | Categoría desconocida o vacía en un artículo nuevo (`CATEGORIA_DESCONOCIDA`): se elige una con `categoria_por_fila`, `categoria_por_defecto_id` o `mapa_categorias`. Si la sugerencia (I-14) no coincide con nada, la fila queda «por revisar» con este mismo motivo y no entra hasta elegir una. El artículo nuevo copia la plantilla de su categoría. |
| I-09 | Artículo inactivo. |
| RG-10 | Código de artículo que ya identifica una pieza, un trabajador o un vale; código de pieza igual al de un artículo. (El mismo artículo por cantidad en el mismo almacén ya no es error: se consolida, ver abajo.) |
| I-02 | Código de pieza ya usado (en la base o antes en la tabla, `CODIGO_REPETIDO`); serie repetida del mismo artículo (`SERIE_REPETIDA`, en la base o antes en la tabla). **Ya no son error** la pieza sin código de pieza (el servidor lo genera) ni la pieza sin número de serie (entra con serie pendiente, aviso amarillo `SERIE_PENDIENTE`). Una serie vacía nunca cuenta como repetida. Cada fila de un artículo por pieza es una pieza (cantidad 1). Sin inspección inicial la pieza entra pendiente (I-03, se avisa). |
| RG-05 | Una pieza con cantidad distinta de 1. |
| I-04 / RG-12 | `ALTA`, con `catalogo.costos`: un costo inválido (no es un número ≥ 0) rechaza la fila; el costo solo se guarda en artículos nuevos (en uno que ya existe se avisa que no cambia). Sin `catalogo.costos`: la columna de costo se ignora con un aviso, las filas entran y el costo nunca vuelve en las respuestas (ni en `datos` de una fila con error). `REPOSICION`: el costo nunca cambia. Ningún vale lleva costos. |

**Consolidación (I-06).** En un artículo por cantidad, las filas del mismo artículo y el mismo almacén se suman en una sola; la fila resultante lleva la primera de las filas en `fila`, sus compañeras en `unida_de` y el aviso «Unido: filas 2, 5, 9». Una fila sin código se une con otra del mismo nombre y marca, comparados sin acentos ni mayúsculas ni espacios de más. Lo repetido sí es error en artículos por pieza: un `codigo_pieza` o una serie repetidos (`CODIGO_REPETIDO`, `SERIE_REPETIDA`).

**Otros avisos por fila** (no bloquean): un artículo que ya existe cuyo nombre, marca o categoría del archivo no coincide con el registrado («El nombre del archivo es distinto del registrado; no se cambia»), siempre sin actualizar nada; una pieza sin inspección inicial (I-03); una pieza sin número de serie (`SERIE_PENDIENTE`, amarillo, la fila entra y la serie se completa después con `POST /api/piezas/{id}/serie`); en `ALTA`, un artículo que ya existe cuya `unidad` del archivo es distinta de la registrada («La unidad del archivo es distinta de la registrada; no se cambia»). Una fila cuya descripción dice SERVICIO (`\bSERVICIO\b`, sin acentos ni mayúsculas) se **excluye** con un aviso: no se importa y no cuenta como error; va en `filas_excluidas`.

**Código generado.** En `ALTA`, una fila de un artículo nuevo sin código recibe `PREFIJO-NNNN`: EPB (EPP básico), EPD (EPP de dotación), ALT (Equipo de alturas), HMA (Herramienta manual), HEL (Herramienta eléctrica), EAV (Equipo de alto valor) y CON (Consumibles de trabajo), con un consecutivo por categoría. En la vista previa el código se muestra como provisional (`codigo_generado: true`); el número definitivo se asigna al confirmar, **dentro de la misma transacción** y con la categoría bloqueada, de modo que dos lotes simultáneos nunca reciben el mismo. Una categoría sin prefijo (creada por la empresa) no genera código: la fila pide el suyo (`FALTA_CODIGO`).

**Código de pieza generado.** En `ALTA`, una fila de un artículo por pieza sin `codigo_pieza` recibe `CÓDIGO-DEL-ARTÍCULO-NNN` (por ejemplo `HEL-0003-001`, `HEL-0003-002`): un tercer segmento sobre el código del artículo, con consecutivo por artículo. El código que sí viene en el archivo se respeta tal cual (RG-10). Se genera **al confirmar**, dentro de la misma transacción y con el artículo bloqueado, y es único contra el registro de códigos (`codigo`): si el candidato ya existe, toma el siguiente. En la vista previa la fila trae `codigo_pieza_generado: true` y `codigo_pieza` queda `null` o provisional (el número definitivo se asigna al confirmar). Un artículo nuevo sin código también recibe el suyo al confirmar; el código de pieza se arma sobre ese. Las etiquetas de las piezas con código generado no existen todavía físicamente: la respuesta de la confirmación las lista en `piezas_creadas` para imprimirlas. No hay generador en la entrada manual por vale: ahí se captura el código.

Las filas vacías se ignoran (cuentan en `vacias`). Un artículo que ya existe solo recibe la entrada (su nombre, marca y categoría del archivo no lo cambian). Las filas con error no se importan y se listan con su motivo; las buenas sí entran, sin esperar a las malas.

**Respuesta de la vista previa** (200):

```json
{
  "modo": "ALTA",
  "columnas": {"codigo": 0, "nombre": 1, "...": null},
  "avisos": ["Se ignoró la columna de costo: no tienes permiso para capturar costos."],
  "archivo_repetido": null,
  "resumen": {"total": 6, "validas": 4, "con_error": 1, "vacias": 0,
              "articulos_nuevos": 2, "existentes": 1, "unidos": 1, "excluidas": 1,
              "por_revisar": 0, "piezas": 1, "unidades": 15, "almacenes": 2,
              "series_pendientes": 1},
  "filas_validas": [{"fila": 2, "estado": "NUEVO", "codigo": "MART-01", "codigo_generado": false,
                     "nombre": "Martillo", "marca": "Truper",
                     "categoria": {"id": "...", "nombre": "Herramienta manual"},
                     "categoria_sugerida": null, "motivo_sugerencia": null,
                     "control": "CANTIDAD", "articulo_nuevo": true, "cantidad": 12,
                     "unidad": "pieza",
                     "saldo_antes": 0, "saldo_despues": 12, "unida_de": [],
                     "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"},
                     "codigo_pieza": null, "codigo_pieza_generado": false,
                     "numero_serie": null, "serie_pendiente": false,
                     "costo": "85.50", "avisos": []},
                    {"fila": 4, "estado": "UNIDO", "codigo": "CON-0001", "codigo_generado": true,
                     "nombre": "Disco de corte", "marca": null,
                     "categoria": null,
                     "categoria_sugerida": {"id": "...", "nombre": "Consumibles de trabajo"},
                     "motivo_sugerencia": "La descripción dice «disco»",
                     "control": "CANTIDAD", "articulo_nuevo": true, "cantidad": 30,
                     "saldo_antes": 0, "saldo_despues": 30, "unida_de": [7, 9],
                     "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"},
                     "avisos": ["Unido: filas 4, 7, 9"]}],
  "filas_error": [{"fila": 3, "estado": "ERROR",
                   "datos": {"codigo": "X", "cantidad": "0,25", "...": ""},
                   "motivos": [{"regla": "I-13", "campo": "cantidad",
                                "codigo": "CANTIDAD_NO_ENTERA", "mensaje": "..."}]}],
  "filas_excluidas": [{"fila": 8, "nombre": "Servicio de calibración",
                       "motivo": "Es un servicio, no un artículo."}],
  "articulos_nuevos": [{"codigo": "MART-01", "nombre": "Martillo", "marca": "Truper",
                        "categoria": {"id": "...", "nombre": "..."}, "control": "CANTIDAD",
                        "filas": 1, "costo": "85.50"}],
  "categorias_desconocidas": [{"nombre": "Cosas raras", "filas": [3, 5]}]
}
```

- `estado` de una fila: `NUEVO` (crea el artículo), `EXISTENTE` (suma a uno que ya existe), `UNIDO` (varias filas sumadas en una; `unida_de` lista las demás) o `ERROR` (solo en `filas_error`).
- `saldo_antes` y `saldo_despues` son lo que hay del artículo en ese almacén antes y después de la fila (en un artículo por pieza, el número de piezas). En un artículo nuevo, `saldo_antes` es 0.
- `unidad` es la unidad del artículo: la del archivo en un artículo nuevo (o «pieza» si no la trae) y la registrada en uno existente. Es solo informativa: el servidor no convierte ni redondea (I-13); quien trae kilos con decimales los pasa antes a la unidad menor y la declara en esta columna.
- En una fila de artículo por pieza, `codigo_pieza_generado: true` marca un código provisional (`codigo_pieza` puede ir `null`: se asigna al confirmar) y `serie_pendiente: true` marca que no trae número de serie (con el aviso `SERIE_PENDIENTE`). `resumen.series_pendientes` cuenta esas filas.
- `categoria_sugerida` y `motivo_sugerencia` vienen solo en `ALTA`, en filas de artículo nuevo sin categoría en el archivo (I-14); son `null` si el archivo trae categoría o si ninguna regla coincidió (la fila queda «por revisar» y va en `filas_error` con `CATEGORIA_DESCONOCIDA`, contada en `resumen.por_revisar`).
- **Sugerencia pendiente.** En la vista previa, una fila de artículo nuevo con sugerencia (I-14) y sin categoría elegida vuelve en `filas_validas` con `categoria: null` y `categoria_sugerida` puesta (no como error). Al confirmar, sin esa fila en `categoria_por_fila` no entra (`CATEGORIA_DESCONOCIDA`): la sugerencia nunca se aplica sola. Con `categoria_por_fila`, la fila vuelve con `categoria` puesta. Las filas de `filas_error` que tenían sugerencia la traen en `categoria_sugerida` y `motivo_sugerencia` (opcionales).
- Columnas: `codigo` ya no es obligatorio en el cuerpo; en `ALTA` basta `codigo` o `nombre`, en `REPOSICION` hace falta `codigo` (422 si no). `cantidad` no se exige como columna: sin ella, cada fila de un artículo por cantidad sale con `FALTA_CANTIDAD`.
- Las marcas conocidas del anexo de FEAT-007 aún no se usan; la clave UNSPSC del archivo no es un dato del contrato (el respaldo 15 del diccionario existe en el código pero la API no lo recibe).
- `motivos` trae los motivos que valen para todo el archivo y no para una fila: hoy, `AL-04` (`ALMACEN_CERRADO`) si el origen o el destino está cerrado (al confirmar, 409 `ALMACEN_CERRADO`). `puede_confirmar` es verdadero solo si se puede confirmar tal cual: sin filas en rojo, sin motivos del archivo, con ruta que no es roja, con al menos una fila y sin pasar de 500 renglones.
- `archivo_repetido` es `null` o `{"fecha": "<UTC>"}`, la fecha de la importación anterior con la misma huella (I-12). La interfaz lo muestra como aviso, no como error.
- `costo` (en filas válidas y artículos nuevos) solo aparece con `catalogo.costos` y si la fila lo trae. `codigo` de los motivos: `FALTA_CODIGO`, `FALTA_NOMBRE`, `CODIGO_REPETIDO`, `ARTICULO_REPETIDO`, `ARTICULO_INACTIVO`, `ARTICULO_NO_EXISTE`, `SIN_PERMISO_CREAR`, `CATEGORIA_DESCONOCIDA`, `ALMACEN_DESCONOCIDO`, `ALMACEN_CERRADO`, `ALMACEN_AJENO`, `FALTA_ALMACEN`, `FALTA_CANTIDAD`, `CANTIDAD_INVALIDA`, `CANTIDAD_NO_ENTERA`, `CANTIDAD_EXCESIVA`, `SERIE_REPETIDA`, `COSTO_INVALIDO`, `DEMASIADO_LARGO`. `FALTA_CODIGO_PIEZA` y `FALTA_SERIE` ya no existen como error de la importación de entradas (el código se genera y la serie queda pendiente); la serie pendiente sale como aviso con el motivo `SERIE_PENDIENTE` (amarillo, en `avisos` de la fila, con la regla I-17). (`FALTA_CODIGO_PIEZA` sigue existiendo en la importación de traspasos, donde no se crean piezas.)

**Respuesta de `POST /archivo`** (200): `{hoja, encabezados, columnas, primera_fila, filas, vista_previa}`. `filas` son las de datos (texto, ya separadas en columnas); `columnas` es la relación propuesta por el nombre de cada encabezado (sin acentos ni mayúsculas); `vista_previa` es la de arriba, o `null` si no se encontró la columna del código (en `ALTA`, tampoco la del nombre). El archivo se lee en memoria: solo `.xlsx` sin macros (se rechazan `.xlsm`, `.xls`, `.csv` y lo que no sea un `.xlsx` válido por su contenido), hasta 5 MB, 5 000 filas, 30 columnas, 500 caracteres por celda y 50 MB descomprimido (zip bomb). Una fórmula nunca se ejecuta: se lee el último valor que Excel guardó (o queda vacía). Un archivo malo da 422 `DATOS_INVALIDOS` con un mensaje en español, nunca un 500. Se lee la primera hoja; las filas vacías de arriba se saltan (el primer renglón con datos son los encabezados).

**Confirmación** (`POST /api/importacion`). En `ALTA` crea con `CatalogoService` los artículos que faltan (con su código, generado si hacía falta) y, en los dos modos, con el motor de movimientos, **un vale de ENTRADA a Kepler**, siempre el almacén central (EK-01, EK-02; una columna `almacen` del archivo y `almacen_por_defecto` se ignoran y la respuesta trae un aviso). Con más de 500 renglones se parte en vales de 500. Todo en una sola transacción: si falla cualquier entrada no se guarda nada (RG-09) y el error es el del motor (por ejemplo 409 `VALE_CAMBIO`) o 409 si algo cambió desde la vista previa. Los folios salen del contador del almacén (RG-06). Las filas con error no se importan. Sin ninguna fila válida: 422 con `detalles.filas_error`.

Si la huella del archivo ya está en una importación anterior (I-12) y el cuerpo no trae `confirmar_repetido: true`, no se escribe nada y responde 409 `ARCHIVO_REPETIDO` con `detalles: {regla: "I-12", fecha}`; la interfaz muestra el aviso y reenvía con `confirmar_repetido: true` si la persona decide continuar. Confirmar de nuevo el mismo `id_lote` (idempotencia, abajo) se resuelve antes y no pasa por esta revisión.

```json
{
  "modo": "ALTA", "id_lote": "<uuid>", "repetida": false,
  "resumen": {"filas_importadas": 3, "filas_con_error": 1, "articulos_creados": 2,
              "existentes": 1, "unidos": 1, "excluidas": 0,
              "vales": 2, "piezas": 1, "unidades": 15, "series_pendientes": 1},
  "articulos_creados": [{"id": "...", "codigo": "MART-01", "codigo_generado": false,
                         "nombre": "Martillo", "unidad": "pieza",
                         "categoria": "Herramienta manual", "control": "CANTIDAD"}],
  "piezas_creadas": [{"id": "...", "codigo": "HEL-0003-001", "codigo_generado": true,
                      "articulo": {"id": "...", "codigo": "HEL-0003", "nombre": "Taladro"},
                      "numero_serie": null, "serie_pendiente": true,
                      "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"}}],
  "vales": [{"id": "...", "folio": "KEP-ING-000012",
             "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"},
             "renglones": 2, "piezas": 0, "unidades": 14}],
  "filas_error": [],
  "avisos": []
}
```

`filas_error` tiene la misma forma que en la vista previa. `piezas_creadas` lista **todas** las piezas que entraron (no solo las de código generado), con su código definitivo y `codigo_generado`, para que la interfaz ofrezca imprimir sus etiquetas (`GET /api/etiquetas?tipo=piezas` sigue siendo la fuente de la impresión); va vacía si el lote no trae piezas. **Idempotencia:** el `id_cliente` de cada vale es determinista por (`id_lote`, almacén, parte). Confirmar de nuevo el mismo `id_lote` responde **200** con `repetida: true`, los mismos vales (con sus folios) y `articulos_creados: []` y los mismos `piezas_creadas`, sin crear nada; el `id_lote` de otra persona da 409. Un lote nuevo con las mismas filas no duplica artículos (los existentes solo reciben otra entrada) y rechaza como error las piezas cuyo código o serie ya existen. La interfaz genera un `id_lote` por importación y lo reutiliza si el usuario reintenta.

**Concurrencia entre lotes.** Dos confirmaciones al mismo tiempo (de lotes distintos) con los mismos artículos nuevos o las mismas piezas no duplican nada: el servidor bloquea lo que va a crear (la categoría para el consecutivo de códigos, el código del artículo y el de cada pieza) dentro de la transacción. El que llega segundo ve el artículo ya creado y le suma, o recibe 409 sin guardar nada; las existencias quedan iguales a la suma de los movimientos. Es un criterio de aceptación de US-IMP-001 y US-IMP-002.

**Auditoría.** Cada confirmación deja un renglón `importacion.confirmar`; su `despues` lleva, además del resumen, el `modo` y la `huella` (sha256 en hexadecimal) que usa I-12. No hay tabla ni migración para eso. Con `confirmar_repetido: true` se guarda también `repetido: true`.

**Descarga de filas con error.** La interfaz ofrece las filas con error en un CSV (con acentos para Excel). Toda celda que empiece con `=`, `+`, `-`, `@`, tabulador o retorno de carro se escribe con un apóstrofo al principio, para que Excel no la tome por una fórmula; los datos del archivo son ajenos y no se confía en ellos.

## Importación de traspasos

FEAT-009 («Traspasos por lista de Excel»; reglas TR-01 a TR-10): una lista de Excel con artículos y cantidades, o con piezas, se convierte en **un traspaso** del almacén de origen a un destino. La importación **no escribe vales ni existencias**: confirma llamando al servicio de movimientos con el tipo `TRASPASO`, así que el resultado es el mismo vale que la captura manual (folio `CLAVE-TRS-…`, QR, estado `EN_TRANSITO`, reglas X-01 a X-14 y firma de sesión F-09). Todas las rutas piden `traspasos.operar` (no piden `inventario.entradas`) y respetan el alcance de almacén (AC-06). El router declara el permiso: no hay excepción a la lista de rutas que lo verifican en el servicio.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/importacion/traspasos/plantilla` | `traspasos.operar` | Descarga un `.xlsx` de ejemplo con las columnas `codigo`, `cantidad`, `codigo pieza` y `serie`, una fila de ejemplo y una hoja de instrucciones. No lee ni escribe datos. |
| `POST /api/importacion/traspasos/archivo` | `traspasos.operar` | Recibe un `.xlsx` (multipart: `archivo`, `destino_almacen_id` y, solo con `almacenes.todos`, `almacen_id` como origen), lo separa en columnas y responde `{hoja, encabezados, columnas, primera_fila, filas, vista_previa}`. No escribe ni guarda el archivo. |
| `POST /api/importacion/traspasos/vista-previa` | `traspasos.operar` | Recibe `{filas, columnas, primera_fila, destino_almacen_id, almacen_id?}` y devuelve la vista previa de abajo. No escribe. |
| `POST /api/importacion/traspasos` | `traspasos.operar` | Confirma: crea el vale de traspaso con las filas buenas. 201 con el vale; con un `id_lote` ya confirmado, 200 con `repetida: true`. |

La descarga de la lista de un traspaso, `GET /api/traspasos/{id}/lista?formato=xlsx` (la ve el origen o el destino, X-10: quien tiene `traspasos.operar` en el origen o `traspasos.recibir` en el destino; el servicio verifica cuál según el almacén, así que al construirla también se agrega a la lista de rutas que lo verifican en el servicio, en `AGENTS.md`), es la segunda entrega de TR-10. Mientras no exista en el código no lleva fila en la tabla de rutas, porque la prueba `test_AC_01_los_permisos_del_codigo_coinciden_con_el_contrato_de_api` exige que cada ruta documentada exista; al construirla se agrega su fila a la tabla de arriba.

La **recepción no cambia**: el traspaso importado se recibe con `POST /api/vales` tipo `RECEPCION` y `GET /api/traspasos/por-recibir`, igual que uno capturado a mano. Esas dos rutas piden `traspasos.recibir`, no `traspasos.operar`: quien arma y envía la lista no es necesariamente quien recibe.

**Cuerpo** (vista previa y confirmación; `POST /archivo` manda `destino_almacen_id` y `almacen_id` como campos del formulario):

```json
{
  "filas": [["GUA-001", "6", "", ""], ["ALT-024", "", "ALT-024-0007", "SN-5521"]],
  "columnas": {"codigo": 0, "cantidad": 1, "codigo_pieza": 2, "serie": 3},
  "primera_fila": 2,
  "destino_almacen_id": "01a1…",
  "almacen_id": null,
  "id_lote": "<uuid>",
  "observacion": null,
  "dejar_fuera_errores": false,
  "confirmar_repetido": false
}
```

- `filas`, `columnas` y `primera_fila` se entienden como en la importación de entradas (máximo 5 000 filas, 30 columnas, 500 caracteres por celda; los errores se reportan con el número de la hoja). `codigo` es el del artículo y `codigo_pieza`, el de la pieza. Una fila de artículo por cantidad lleva `codigo` y `cantidad`; una de artículo por pieza lleva `codigo_pieza` (la cantidad es 1; `serie` es opcional y solo ayuda a identificar). **TR-13:** `columnas.nombre` es opcional y de ayuda: no genera aviso de columna ignorada; si el nombre no coincide con el del catálogo para ese código, la fila trae el motivo `{regla: "TR-13", codigo: "NOMBRE_NO_COINCIDE"}` y nivel AMARILLO (no bloquea). La plantilla (`GET /plantilla`) trae las columnas `codigo`, `nombre`, `cantidad`, `codigo pieza` y `serie`. **TR-12:** `POST /archivo` trae `vista_previa` cuando se reconoce la columna del código; la pantalla la muestra sola y solo pide relacionar columnas si faltan las obligatorias.
- `destino_almacen_id` es obligatorio. `almacen_id` es el origen y solo lo manda quien tiene `almacenes.todos`; los demás parten del almacén de la sesión (un `almacen_id` ajeno es 409 `ALMACEN_CAMBIO`). Destino igual al origen: 422 `DATOS_INVALIDOS`.
- `id_lote`, `observacion`, `dejar_fuera_errores` y `confirmar_repetido` solo cuentan al confirmar; la vista previa los ignora. `id_lote` (UUID del cliente) es obligatorio. `observacion` se guarda en el vale y es obligatoria cuando la ruta pide observación (X-03). `dejar_fuera_errores` (por omisión `false`) confirma solo las filas buenas y deja fuera las rojas. `confirmar_repetido` (por omisión `false`) autoriza confirmar un archivo ya importado.

**Respuesta de la vista previa** (200). Es la evaluación del traspaso por fila, con el mismo semáforo del vale:

```json
{
  "origen": {"id": "01a1…", "clave": "KEP", "nombre": "Kepler"},
  "destino": {"id": "01a1…", "clave": "CON", "nombre": "Contratistas"},
  "ruta": {"habitual": true, "nivel": "VERDE", "pide_observacion": false, "mensaje": "Ruta habitual.",
           "clase": "HABITUAL", "autoriza": "NADIE", "autorizadores_disponibles": null, "autorizada": false},
  "motivos": [],
  "puede_confirmar": false,
  "archivo_repetido": null,
  "resumen": {"total": 3, "ok": 1, "avisos": 1, "errores": 1,
              "unidades": 7, "piezas": 1, "excedido": false},
  "filas": [
    {"fila": 2, "codigo": "GUA-001", "articulo": "Guante", "pieza": null,
     "cantidad": 6, "disponible_en_origen": 40, "nivel": "VERDE", "unida_de": [], "motivos": []},
    {"fila": 3, "codigo": "ALT-024", "articulo": "Arnés poliéster",
     "pieza": {"id": "01a1…", "codigo": "ALT-024-0007", "numero_serie": "SN-5521"},
     "cantidad": 1, "disponible_en_origen": 1, "nivel": "AMARILLO", "unida_de": [],
     "motivos": [{"regla": "X-04", "codigo": "PIEZA_NO_APTA", "mensaje": "La pieza no está apta."}]},
    {"fila": 4, "codigo": "TOR-9", "articulo": null, "pieza": null,
     "cantidad": 2, "disponible_en_origen": 0, "nivel": "ROJO", "unida_de": [],
     "motivos": [{"regla": "X-02", "codigo": "SIN_EXISTENCIA_EN_ORIGEN", "mensaje": "No hay existencia en el origen."}]}
  ],
  "avisos": ["Unido: filas 2, 5"]
}
```

- **Traslado lateral (TR-05, X-16 a X-19, FEAT-015).** `ruta` se evalúa una vez para todo el archivo, igual que la evaluación de un vale: `clase` (`HABITUAL`, `LATERAL`, `NO_HABITUAL`, `MISMO`), `autoriza` (`NADIE`, `ENVIO_PROPIO`, `SUPERVISOR_ORIGEN`, `ADMINISTRADOR`) y `autorizadores_disponibles`. Entre dos almacenes de tercer nivel: con `autorizaciones.resolver` en el origen, X-16 (`AMARILLO`, `pide_observacion: true`); sin él, X-17 (`NARANJA`, `puede_confirmar` falso hasta que la `autorizacion_id` sirva). El cuerpo (vista previa y confirmación) acepta `autorizacion_id`: la vista previa dice en `ruta.autorizada` si sirve para las filas que no están en rojo (y `autorizacion_error` el porqué si no); dejar fuera filas con error después de aprobar es quitar renglones. La confirmación sin `observacion` en X-16 es 422 con `regla: "X-16"`; sin autorización en X-17, 409 `VALE_CAMBIO`; con una que no sirve, 409 `AUTORIZACION_INVALIDA`. Los avisos de X-20 llegan en `avisos`. La solicitud de autorización (`POST /api/autorizaciones`, `tipo: "TRASLADO"`) lleva las filas normalizadas que no están en rojo.
- `ruta` es la regla X-03 de la ruta entre origen y destino: `habitual` es verdadero si es padre-hijo (`VERDE`); otra ruta con `almacenes.todos` es `AMARILLO` con `pide_observacion: true`; otra ruta sin `almacenes.todos` es `ROJO` (se puede ver, no confirmar: 403 `RUTA_SOLO_ADMINISTRADOR`). `mensaje` va en español llano.
- `archivo_repetido` es `null` o `{"fecha": "<UTC>"}`: la importación anterior con la misma huella. Es aviso, no error.
- `resumen`: `total` de filas con datos; `ok` (verde), `avisos` (amarillo) y `errores` (rojo) suman `total`; `unidades` y `piezas` son lo que se traspasaría con las filas confirmables; `excedido` es verdadero si pasa de 500 renglones (al confirmar, 422 `TRASPASO_MUY_GRANDE`).
- Cada fila trae `nivel` (el más grave de sus `motivos`), `disponible_en_origen` (lo que el origen tiene del artículo; 1 o 0 en una pieza), `pieza` (solo en artículos por pieza) y `unida_de`: como en la importación de entradas, las filas repetidas de un artículo por cantidad se suman; la primera lleva en `unida_de` a sus compañeras y se avisa en `avisos`. Nada trae costos (F-12).
- `codigo` de los motivos por fila: `ARTICULO_NO_EXISTE`, `CANTIDAD_NO_ENTERA`, `CANTIDAD_INVALIDA`, `SIN_EXISTENCIA_EN_ORIGEN` (X-02), `PIEZA_NO_ESTA_EN_ORIGEN` (X-02), `PIEZA_REPETIDA`, `FALTA_CODIGO_PIEZA` y `SERIE_NO_COINCIDE` (la `serie` del archivo no es la de la pieza; rojos, no se confirman) y `PIEZA_NO_APTA` (X-04, amarillo, no bloquea).

**Respuesta de `POST /archivo`** (200): como la de la importación de entradas, con `vista_previa` (la de arriba) o `null` si no se encontró ni la columna `codigo` ni la `codigo pieza`. Mismas restricciones de archivo (solo `.xlsx` sin macros, 5 MB, 5 000 filas, 30 columnas; un archivo malo da 422 `DATOS_INVALIDOS` en español, nunca un 500).

**Confirmación** (`POST /api/importacion/traspasos`). El servidor vuelve a evaluar el cuerpo con la misma revisión de la vista previa y llama al servicio de movimientos con un vale de tipo `TRASPASO` (renglones por código de pieza, o de artículo con `cantidad`), todo en una transacción (RG-09): el vale, sus movimientos y las existencias se guardan juntos o no se guarda nada. Responde 201:

```json
{
  "id_lote": "<uuid>", "repetida": false,
  "vale": {"id": "01a1…", "folio": "KEP-TRS-000013", "token": "…", "estado": "EN_TRANSITO",
           "origen": {"id": "01a1…", "clave": "KEP", "nombre": "Kepler"},
           "destino": {"id": "01a1…", "clave": "CON", "nombre": "Contratistas"},
           "renglones": 2, "piezas": 1, "unidades": 7},
  "resumen": {"filas_importadas": 2, "filas_dejadas_fuera": 1, "unidades": 7, "piezas": 1},
  "filas_dejadas_fuera": [{"fila": 4, "motivos": [{"regla": "X-02", "codigo": "SIN_EXISTENCIA_EN_ORIGEN", "mensaje": "…"}]}],
  "avisos": []
}
```

**Idempotencia.** El `id_cliente` del vale es determinista a partir de `id_lote` (uuid5). Confirmar de nuevo el mismo `id_lote` responde 200 con `repetida: true` y el mismo vale (mismo folio), sin crear nada; un `id_lote` de otra persona da 409. Un lote nuevo con las mismas filas crea otro traspaso: lo frena el aviso de archivo repetido, no la idempotencia.

**Errores propios** (además de los de la sección Errores):

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 403 | `RUTA_SOLO_ADMINISTRADOR` | La ruta no es padre-hijo y quien confirma no tiene `almacenes.todos` (X-03). Existente. |
| 409 | `ALMACEN_CERRADO` | El origen o el destino está cerrado (AL-04). Existente. |
| 409 | `ARCHIVO_REPETIDO` | La huella del archivo ya está en un traspaso importado y el cuerpo no trae `confirmar_repetido: true`; `detalles.fecha` es la de la importación anterior. Se resuelve reenviando con `confirmar_repetido: true`. Un `id_lote` ya confirmado se resuelve antes y no pasa por esta revisión. |
| 409 | `FILAS_CON_ERROR` | Se confirmó con filas en rojo sin `dejar_fuera_errores: true`; `detalles.filas` las lista con sus motivos y no se guarda nada. Si no queda ninguna fila confirmable, 422 `DATOS_INVALIDOS` con `detalles.filas`. |
| 422 | `TRASPASO_MUY_GRANDE` | Más de 500 renglones: un traspaso no se parte en varios vales; se divide el archivo. |
| 422 | `DATOS_INVALIDOS` | Falta la `observacion` que pide X-03 (`detalles: [{campo: "observacion", mensaje, regla: "X-03"}]`); el destino es igual al origen; falta `destino_almacen_id` o `id_lote`; el archivo no sirve. |

**Auditoría.** Cada confirmación deja un renglón `importacion.traspaso`; su `despues` lleva el resumen, el id y el folio del vale y la `huella` (sha256 en hexadecimal) del archivo, que usa el aviso de archivo repetido. Con `confirmar_repetido: true` se guarda también `repetido: true`. No hay tabla ni migración para eso (ver `data-model.md`).

## Reportes

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/reportes/existencias` | `reportes.existencias` | Por almacén y artículo. Filtros: `almacen_id`, `categoria_id`. |
| `GET /api/reportes/movimientos` | `bitacora.ver` o `reportes.movimientos` | **La bitácora del almacén (SG-05).** Acepta `bitacora.ver` o `reportes.movimientos` (cualquiera; lo declara el router con `requiere_alguno`: 403 `SIN_PERMISO` si no tiene ninguno). Con `almacen_id` incluye lo que **sale** (el vale lo emitió ese almacén o el movimiento sale de sus ubicaciones), lo que **llega** (el vale va hacia él o el movimiento llega a sus ubicaciones, como una recepción) y las **entradas**. Filtros: fechas, almacén, tipo, trabajador, artículo, `usuario_id` (quien hizo el vale, C-11), `pieza` (texto del código o de la serie de la pieza) y `solo_mios=true` (solo lo que hizo el usuario de la sesión). Cada fila trae `vale_id`, `trabajador_id`, `numero_serie` y `direccion` (`ENTRADA`, `SALIDA` o `EN_CAMINO`, respecto al almacén filtrado; `null` sin `almacen_id`) con su `direccion_texto`. Sin `almacenes.todos`, solo el almacén asignado, también al filtrar por usuario; con él, todos los almacenes y usuarios. |
| `GET /api/reportes/usuarios` | `bitacora.ver` o `reportes.movimientos` | Quién ha hecho vales (`bitacora.ver` o `reportes.movimientos`, como la bitácora), para el filtro «quién lo hizo» de la bitácora: `{elementos: [{id, nombre, usuario}]}`. Con `almacenes.todos`, de todos los almacenes; sin él, solo de su almacén (AC-06, C-11). |
| `GET /api/reportes/adeudos` | `reportes.adeudos` | Pendientes por trabajador. Filtro: `solo_no_vigentes`. |
| `GET /api/reportes/consumo` | `reportes.consumo` | Consumo de artículos consumibles (C-08). Filtros: fechas, `almacen_id`, `categoria_id`, `articulo_id`, `trabajador_id`. Responde por artículo el total y el desglose por trabajador, restando las cancelaciones. Sin `almacenes.todos`, solo el almacén asignado. Sin costos (RG-12). |

Todos aceptan `formato=csv` y las listas, `pagina` y `tamano`. Las fechas (`desde`, `hasta`, `AAAA-MM-DD`) son fechas locales de México: el día `hasta` entra completo, hasta las 23:59:59 hora de México. Un `desde` posterior a `hasta` se rechaza (422 `DATOS_INVALIDOS`). Cada respuesta es `{elementos, total, sin_registros, mensaje}`; sin registros, `mensaje` es "No hay registros con esos filtros.".

- **Alcance (AC-06, C-11):** sin `almacenes.todos`, solo el almacén asignado; pedir otro almacén o un usuario de otro almacén no devuelve nada (no es error). Sin almacén asignado ni `almacenes.todos`, nada. Excepción: el de adeudos, que es de la persona, lo ve completo quien tiene `almacenes.todos` o `trabajadores.administrar` (RH, que no tiene almacén); se decide por permiso, no por no tener almacén. Los demás, solo lo que entregó su almacén y, sin almacén, nada. El almacén de un movimiento es el del vale que lo emitió.
- **Movimientos:** un renglón por movimiento, del más reciente al más antiguo: fecha (UTC), folio, tipo, artículo, pieza, cantidad, origen, destino, responsable, trabajador, `autorizado_por` y `motivo` (quien autorizó el vale y el motivo de la autorización, o el motivo de baja del renglón; vacíos si no hubo; ES-26, A-04), `saldo_origen` y `saldo_destino`. `trabajador_id` coincide con el trabajador del vale o el anotado en el renglón. Cada elemento trae también `observacion` (lo que anotó quien hizo el vale en ese renglón, por ejemplo el porqué de E-09; `null` si no hay) en el JSON; el CSV no la incluye.
- **Adeudos:** un renglón por retornable en resguardo (trabajador, artículo, código, serie, cantidad, `desde`, folio y almacén de la última entrega, `vigente`). Los consumibles no cuentan (B-03). `solo_no_vigentes` deja a quienes ya no son vigentes (T-07). Filtro extra: `almacen_id`.
- **Consumo:** un elemento por artículo consumible con `total`, `unidad` y `trabajadores` (mayor a menor). Suma los movimientos a CONSUMIDO y resta los que salen de CONSUMIDO (cancelaciones, K-02); una cancelación se fecha con el vale que cancela, así un vale cancelado no cuenta en ningún periodo. Sin renglones en cero.
- **CSV:** `text/csv; charset=utf-8` con BOM (Excel abre bien los acentos), encabezados en español, fechas en hora de México, todas las filas con los mismos filtros (movimientos y existencias: un renglón por elemento del JSON; adeudos: igual; consumo: un renglón por artículo y trabajador). Una celda de texto que empiece con `=`, `+`, `-` o `@` se antepone con `'`.

## Seguimiento de piezas

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/seguimiento/piezas` | `reportes.existencias` o `resguardo.ver` | Seguimiento de piezas (C-13): todas las piezas dentro del alcance del usuario, cada una con dónde está o quién la tiene, desde cuándo y con qué vale. Filtros: `q`, `articulo_id`, `almacen_id`, `estado`, `ubicacion`, `serie_pendiente`, `alto_valor`, `pagina`, `tamano` y `formato=csv`. Cada pieza trae `alto_valor` y `aviso` (SG-06: alto valor con un trabajador dado de baja o con el contrato vencido, o `null`); `resumen.articulos_por_cantidad` cuenta los artículos de la otra pestaña. Solo lee. |
| `GET /api/seguimiento/cantidad` | `reportes.existencias` o `resguardo.ver` | Pestaña «Por cantidad» (SG-01): artículos de control por cantidad en resguardo de trabajadores. Cada elemento: `trabajador {id, numero_empleado, nombre}`, `articulo {id, codigo, nombre, marca}`, `unidad`, `cantidad`, `desde` (UTC, su entrega más reciente), `vale {id, folio}` (nulo si es de otro almacén, AC-06) y `almacen {id, clave, nombre}` (el del vale). `resumen`: `renglones`, `unidades`, `articulos` y `trabajadores`. Filtros: `q`, `articulo_id`, `almacen_id`, `pagina`, `tamano` y `formato=csv`. Sin `almacenes.todos` solo trae lo entregado con un vale de su almacén y exige `trabajadores.ver`. Solo lee. |

- **Filtros.** `q` busca por nombre o código del artículo, número de serie, código de la pieza y nombre o número del trabajador que la tiene; varias palabras deben coincidir todas, y con menos de dos caracteres no busca (lista vacía y `mensaje` "Escribe al menos dos caracteres para buscar."). `estado`: `APTO`, `NO_APTO`, `EN_MANTENIMIENTO`, `EN_CALIBRACION` o `BAJA`. `ubicacion`: `ALMACEN`, `TRABAJADOR`, `TRANSITO` o `BAJA`. `almacen_id` deja las piezas que están en ese almacén, las que tiene un trabajador por un vale de ese almacén y las que van en tránsito desde o hacia él. `serie_pendiente=true` deja solo las piezas sin número de serie (`false`, solo las que ya la tienen; omitido, todas). Un valor inválido responde 422 `DATOS_INVALIDOS`.
- **Alcance (AC-06, C-02).** Con `almacenes.todos`, todas las piezas. Sin él, solo las del almacén asignado, las que tiene un trabajador (si el rol tiene `trabajadores.ver`) y el tránsito desde o hacia su almacén; pedir el `almacen_id` de otro no devuelve nada (no es error), y sin almacén asignado ni `almacenes.todos` tampoco. `vale` es `null` cuando el vale es de un almacén fuera del alcance. Nunca lleva costos, CURP ni NSS (RG-12, RG-13).
- **Respuesta.** `{elementos, total, sin_registros, mensaje, resumen}`, ordenada por artículo y código de pieza. `resumen` = `{total, en_almacen, en_resguardo, en_transito, no_aptas}` cuenta las piezas del alcance con el texto, el artículo y el almacén del filtro, **sin** aplicar `estado` ni `ubicacion`, para que las tarjetas de la pantalla cambien entre ellos. Cada elemento:

```json
{
  "id": "0192...",
  "codigo": "HER-001",
  "numero_serie": "MP-2041",
  "serie_pendiente": false,
  "articulo": {"id": "0192...", "codigo": "MINIPULIDOR", "nombre": "Minipulidor", "marca": "Bosch"},
  "estado": "APTO",
  "estado_texto": "Apta",
  "inspeccion_vigente": true,
  "inspeccion_vigente_hasta": "2026-12-01",
  "ubicacion": {
    "tipo": "TRABAJADOR",
    "texto": "En resguardo de Juan Pérez",
    "almacen": null,
    "trabajador": {"id": "0192...", "numero_empleado": "EMP-1001", "nombre": "Juan Pérez"}
  },
  "desde": "2026-10-05T16:20:00Z",
  "vale": {"id": "0192...", "folio": "KEP-ENT-000012"}
}
```

  `numero_serie` es `null` y `serie_pendiente` es `true` en una pieza sin serie registrada; el CSV deja la celda de la serie vacía. `ubicacion.tipo` es `ALMACEN` (`almacen` es el almacén; texto "En Kepler"), `TRABAJADOR` (`trabajador` es quien la tiene), `TRANSITO` (`almacen` es el almacén al que va; texto "En tránsito a Contratistas"), `BAJA` ("De baja"), `OTRA` o `NINGUNA` (sin ubicación todavía). `desde` (UTC) es el movimiento que la dejó en esa ubicación; con un trabajador, su entrega más reciente, porque una cancelación que se la regresa no cambia desde cuándo la tiene. `vale` es el vale de ese movimiento.
- **CSV.** `formato=csv` descarga todas las filas del filtro (`seguimiento-piezas-AAAAMMDD.csv`): código de la pieza, serie, código y nombre del artículo, marca, estado, inspección vigente hasta, dónde está, número y nombre del trabajador, desde (hora de México) y folio del vale. Mismas reglas del CSV de los reportes (BOM, neutralización de `=`, `+`, `-` y `@`).
- **Pantalla.** La ficha de cada pieza es `GET /api/piezas/{id}` (C-02): trae su inspección y su historial completo.

## Etiquetas

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/etiquetas?tipo=` | `etiquetas.imprimir` | `{elementos: [{codigo, texto}], total}` (sin paginar) para `tipo` = `credenciales` (códigos de trabajadores no inactivos), `piezas` (las que no están de baja) o `estantes` (artículos activos por cantidad). `etiquetas.imprimir` basta para los tres tipos: una etiqueta solo lleva el código y un texto breve. En `credenciales` cada elemento trae además `nombre`, `numero_empleado` y `puesto` (el del periodo de contrato vigente; se omite si la persona no tiene) para armar la credencial completa: nunca CURP ni NSS (RG-13). Los campos vacíos no se envían. El QR contiene exactamente `codigo`; lo dibuja el navegador, que también arma la credencial (pantalla, hoja carta e imagen PNG). |

## Previsto por la segunda ola

| Feature | Endpoints | Permiso |
|---|---|---|
| FEAT-001 | `GET /api/publico/vales/{token}` sin sesión; `GET /api/reportes/integridad` | Público; `reportes.movimientos` |
| FEAT-002 | **Servidor construido:** `GET /api/almacenes/{id}/reporte-cierre?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`, `GET /api/reportes/valor-inventario`; `POST /api/vales` y `/api/vales/evaluar` admiten `tipo: AJUSTE` (abrir y cerrar sigue en FEAT-008) | `reportes.cierre`; `reportes.valor_inventario`; `inventario.ajustar` |
| FEAT-008 | `POST`, `PATCH /api/almacenes`, `POST /api/almacenes/{id}/cierre` y `/reapertura`, `GET /api/almacenes?resumen=true`, `GET /api/tablero/resumen`, `GET /api/tablero/consumo`; `POST /api/trabajadores` sin `numero_empleado` | `almacenes.administrar`; `tablero.ver`; `trabajadores.administrar` |
| FEAT-003 | **Construido en el servidor** (ver [Puestos y dotación](#puestos-y-dotación)): `GET`, `PUT /api/puestos/{id}/dotacion`, `GET`, `POST`, `PATCH /api/puestos`, `GET /api/trabajadores/{id}/dotacion` | `catalogo.ver`; `catalogo.administrar`; `trabajadores.ver` |
| FEAT-004 | `PUT /api/almacenes/{id}/minimos`; `POST /api/piezas/{id}/estado` admite mantenimiento y calibración | `inventario.minimos`; `piezas.inspeccionar` |

### FEAT-002: ajuste y cierre construidos en el servidor

`POST /api/vales/evaluar` y `POST /api/vales` aceptan `tipo: "AJUSTE"`, `observacion` obligatoria y `renglones: [{codigo, cantidad, observacion?}]`. La confirmación agrega `id_cliente`; la firma es por sesión, sin trabajador, proyecto, destino, vale de origen ni autorización. Permiso `inventario.ajustar`; el almacén es el activo del usuario, o el indicado por quien tiene `almacenes.todos`. Observación vacía o campos ajenos: 422 `DATOS_INVALIDOS` con `CP-03`; una pieza que figure con trabajador, una pieza solicitada con cantidad distinta de uno, artículo por pieza sin identificar la pieza o existencia insuficiente dan evaluación roja y 409 al confirmar. Una cantidad repetida suma; una pieza repetida se ignora. Si la suma supera un millón o la observación unida supera 1000 caracteres, responde 422 sin recortar ni escribir. La respuesta usa el contrato común de vales, folio `CLAVE-AJU-NNNNNN`, responsable y sello; reintentar el mismo `id_cliente` devuelve el mismo vale (200).

`GET /api/almacenes/{id}/reporte-cierre` exige `reportes.cierre`, `desde` y `hasta` (inclusive, hora de México); 422 si faltan o están invertidas, 404 para almacén inexistente o ajeno. Respuesta `{almacen:{id,clave,nombre,estado},desde,hasta,articulos,cuadra,atribucion_cantidades:"FIFO",reglas:["CP-04","CP-05"]}`. Cada artículo trae `articulo_id`, `codigo`, `nombre`, `unidad`, `saldo_inicial`, `recibido_traspasos`, `devuelto_a_almacen`, `otras_entradas`, `consumido`, `entregado_trabajadores`, `regresado`, `faltantes`, `otras_salidas`, `saldo_final`, `devuelto_por_trabajadores`, `cerrado_sin_devolucion`, `en_resguardo`, `trabajadores:[{id,nombre,numero_empleado,cantidad}]`, `diferencia` y `cuadra`. Son cantidades, sin costos ni CURP/NSS. La columna `regresado` incluye salidas por traspaso aún en tránsito: la restricción de cierre AL-03 sigue indicando que deben recibirse o cancelarse antes de cerrar.

El saldo final y el resguardo se reconstruyen al término del rango; el desglose de trabajadores corresponde a las entregas hechas en ese rango, considerando también devoluciones en otros almacenes. La devolución por cantidad se atribuye FIFO; las piezas se identifican exactamente. Una cancelación revierte el lote del movimiento original, no otra entrega elegida por FIFO. Los movimientos inversos netean su columna; una cancelación de una operación anterior al rango puede hacer negativa una columna del rango y el saldo inicial mantiene la igualdad. `cuadra` verifica la clasificación de la bitácora, no certifica un conteo físico.

`atribucion_cantidades: "FIFO"` advierte que el desglose de procedencia de unidades por cantidad es **aproximado**: el vale de devolución no conserva la entrega de origen de cada unidad. La interfaz debe mostrar ese límite; no debe presentar FIFO como trazabilidad física exacta. Los saldos y movimientos propios del almacén sí son lecturas reales de la bitácora.

`GET /api/reportes/valor-inventario` es alias del contrato `GET /api/tablero/valor`, con el mismo permiso `reportes.valor_inventario`, alcance AC-37, agregados por categoría/almacén, artículos sin costo y supresión de totales que revelarían un costo unitario (VI-07/TB-04).

## Previsto por la iteración 01 (aprobado, sin construir)

Fuente: [documento maestro de la iteración 01](../releases/iteration_01/README.md) (secciones 5.3, 5.4 y la tabla de cambios a endpoints existentes) y los briefs [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) a [FEAT-020](../features/FEAT-020-app-android-sin-conexion.md). **Nada de esta sección está construido.** Lo de arriba sigue siendo el contrato del código actual; al construir cada parte, su contrato pasa a la sección que le toca y sale de aquí. Si un brief contradice al maestro, manda el maestro.

### Convenciones que cambian

- **Alcance por conjunto (AC-36 a AC-41, FEAT-013).** Donde arriba dice «el almacén asignado», pasa a ser: las **lecturas** abarcan todos los almacenes del conjunto del usuario (`usuario_almacen`) y un `almacen_id` del conjunto filtra; uno fuera del conjunto se trata como hoy un almacén ajeno (se ignora en el tablero y los reportes, 404 en un detalle). Las **escrituras** se hacen en el almacén activo (`usuario.almacen_id`). Con un solo almacén en el conjunto, nada cambia.
- **Rutas que verifican el permiso en el servicio** (el router solo exige sesión): las ocho de hoy más `POST /api/autorizaciones` (según `tipo`; ya construido con FEAT-015). `POST /api/sincronizacion/lotes` declara `sincronizacion.operar` en el router, pero el permiso de **cada operación** del lote (`entregas.crear`, `devoluciones.crear`, `traspasos.recibir`, `piezas.inspeccionar`, `compras.solicitar`) se verifica en el servicio contra quien la capturó. `POST /api/trabajadores` declara `trabajadores.administrar` y el servicio exige además `proyectos.asignar`.
- **Rutas con `requiere_alguno`**: las cuatro de hoy más `GET /api/bitacora` (`bitacora.ver` o `reportes.movimientos`), `PUT /api/usuarios/{id}/almacenes` (`acceso.usuarios` o `almacenes.asignar_personal`) y `GET /api/proyectos` y `GET /api/proyectos/{id}` (`proyectos.ver` o `proyectos.asignar`).
- **Encabezado `X-App-Version`** (FEAT-020, OF-02): si llega y es menor que `APP_VERSION_MINIMA`, cualquier ruta responde 426 `APP_DESACTUALIZADA`; sin el encabezado (la web) no se revisa. `POST /api/sincronizacion/lotes` acepta el formato de la versión anterior.
- **Encabezado `X-Dispositivo: <id>.<secreto>`** en las rutas de `/api/sincronizacion/*`: identifica al equipo inscrito.
- **Costo deducible (T-2 del maestro):** donde un total en pesos cubre un solo artículo con costo, el valor se responde `null` («No se muestra para no revelar el costo de un artículo») para quien no tiene `catalogo.costos`. Aplica a `GET /api/tablero/proyectos`, al `resumen` de `GET /api/vales/{id}` y a `GET /api/trabajadores/{id}/consumo`.

### Permisos nuevos (maestro 5.3)

`proyectos.ver`, `proyectos.administrar`, `proyectos.asignar` (FEAT-013); `despacho.autonomia` (014); `inspecciones.ver` (016); `deudores.ver` (018); `sincronizacion.operar`, `sincronizacion.administrar` (020). `reportes.valor_inventario` ya está disponible en el código y el Supervisor ya lo trae (migración `0009`); la tabla 8.3 de las reglas está atrasada.

### Errores nuevos

| HTTP | `codigo` | Cuándo | FEAT |
|---|---|---|---|
| 403 | `ALMACEN_NO_ASIGNADO` | `PUT /api/sesion/almacen` a un almacén que no está en su conjunto (AC-39). | 013 |
| 409 | `PROYECTO_CERRADO` | Se edita un proyecto cerrado (PR-03). | 013 |
| 409 | `PROYECTO_CON_VALES` | Se cambia la clave o el almacén de un proyecto que ya usa algún vale (PR-03). | 013 |
| 409 | `ASIGNACION_REPETIDA` | El trabajador ya tiene una asignación activa a ese proyecto (PR-13). | 013 |
| 409 | `CON_PROYECTOS_ACTIVOS` | Bloqueo nuevo de AL-03 al inactivar un almacén; `detalles` trae hasta 20 `{id, clave, nombre, fin_estimado}`. Orden de bloqueos: `CON_TRASPASOS_EN_TRANSITO`, `CON_EXISTENCIAS`, `CON_HIJOS_ACTIVOS`, `CON_PROYECTOS_ACTIVOS`, `CON_USUARIOS` (que cuenta a los usuarios activos que lo tienen en su conjunto). | 013 |
| 422 | `PROYECTO_REQUERIDO` | Falta `proyecto_id` en el alta, el reingreso sin asignación asignable o la ENTREGA de un trabajador con varios proyectos (PR-09, PR-11). | 013 |
| 422 | `PROYECTO_INVALIDO` | El proyecto no existe, está cerrado, venció (al asignar) o no es de una asignación activa del trabajador (al entregar). | 013 |
| 409 | `REQUIERE_APROBACION_DESPACHO` | Se confirma una ENTREGA con EPP que pide aprobación y no trae autorización. `detalles: {regla: "DE-01", renglones: [{renglon, codigo}]}`. | 014 |
| 409 | `APROBACION_INVALIDA` | La autorización de despacho no cubre un renglón. `detalles: {regla: "DE-08", renglones: [{renglon, codigo, causa: RECHAZADO \| NO_INCLUIDO \| CANTIDAD_MAYOR}]}`. | 014 |
| 409 | `AUTORIZACION_RESUELTA` (cambia) | Trae `detalles: {estado, resuelta_por: {id, nombre} \| null, resuelta_en, medio}` (DE-11). | 014 |
| 409 | `PIEZA_EN_TRANSITO` | Inspeccionar una pieza en tránsito (P-17). | 016 |
| 409 | `PIEZA_EN_MANTENIMIENTO` | Inspeccionar una pieza en mantenimiento o calibración (P-17). | 016 |
| 422 | `FECHA_FUTURA` | Inspección inicial de una ENTRADA con fecha posterior a hoy (P-17, I-03). | 016 |
| 426 | `APP_DESACTUALIZADA` | `X-App-Version` menor que `APP_VERSION_MINIMA` (OF-02). | 020 |
| 403 | `DISPOSITIVO_REVOCADO`, `DISPOSITIVO_NO_INSCRITO`, `DISPOSITIVO_DE_OTRO_ALMACEN` | Rutas de sincronización con un equipo revocado, desconocido o de otro almacén. `DISPOSITIVO_REVOCADO` ordena al equipo borrar sus datos. | 020 |
| 422 | `LOTE_INVALIDO` | La forma del lote no sirve (una operación mal formada dentro de un lote bueno es conflicto `FORMA_INVALIDA`, no error del lote). | 020 |
| 409 | `CONFLICTO_YA_RESUELTO` | Se resuelve un conflicto de sincronización ya resuelto. | 020 |

### Traslados entre almacenes de tercer nivel (FEAT-015, X-16 a X-21)

**Construido en el backend el 8 oct 2026** (migración `0010_autorizacion_traslado`): el contrato vigente está en «Vales» (TRASPASO y RECEPCION), «Autorizaciones» e «Importación de traspasos». Queda previsto, por depender de otras features, la notificación push (X-20, FEAT-014), el aviso de PR-12 (FEAT-013) y el alcance por conjunto de almacenes (AC-36). La tabla de abajo se conserva como referencia del brief.

| Endpoint | Cambio |
|---|---|
| `POST /api/vales/evaluar` (TRASPASO) | Trae `ruta: {clase: HABITUAL \| LATERAL \| NO_HABITUAL \| MISMO, autoriza: NADIE \| ENVIO_PROPIO \| SUPERVISOR_ORIGEN \| ADMINISTRADOR, autorizadores_disponibles}` y, en `motivos` del vale, X-03, X-16, X-17, X-18 o X-20. X-16: amarillo con `pide_observacion: true` (quien envía tiene `autorizaciones.resolver` en el origen). X-17: naranja con `autorizable: true` y, con `autorizacion_id`, `autorizado: true`. X-20: avisos amarillos que no bloquean (nadie en el destino con `traspasos.recibir`; destino sin proyectos activos). X-18 se evalúa antes de la ruta no habitual de X-03. |
| `POST /api/vales` (TRASPASO) | Acepta `autorizacion_id`. 422 `DATOS_INVALIDOS` con `regla: "X-16"` sin observación; 409 `AUTORIZACION_INVALIDA` (no aprobada, vencida, usada, de otro origen o destino, o que no cubre: después de aprobada solo se pueden **quitar** renglones); 409 `VALE_CAMBIO` con X-17 sin autorizar. El detalle trae `valido.medio = "ENVIO_PROPIO"` en el envío propio. |
| `POST /api/vales/evaluar` y `POST /api/vales` (RECEPCION) | X-21 en amarillo con `pide_observacion` si quien recibe es quien envió; sin observación, 422 con `regla: "X-21"`. Aplica a todo traspaso. |
| `GET /api/traspasos/por-recibir` | Cada elemento trae `ruta` (`HABITUAL`, `LATERAL`, `NO_HABITUAL`) y `valido`. |
| `POST /api/importacion/traspasos/vista-previa` y `POST /api/importacion/traspasos` | La vista previa trae la `ruta` como la evaluación (TR-05: una vez por archivo); la confirmación acepta `autorizacion_id` (X-19). La solicitud lleva solo las filas que no están en rojo; dejar fuera filas después de aprobar es quitar renglones. |

Sin permisos nuevos. Las solicitudes TRASLADO están en «Autorizaciones», abajo.

### Despacho de EPP con aprobación (FEAT-014, DE-01 a DE-16)

| Endpoint | Permiso | Cambio o contrato |
|---|---|---|
| `POST /api/vales/evaluar` (ENTREGA) | Según el tipo | Arriba: `requiere_aprobacion_despacho` (bool) y `despacho: {modo: CON_APROBACION \| AUTONOMO_ALMACEN \| AUTONOMO_USUARIO \| SUPERVISOR \| NO_APLICA}`. Por renglón: `es_epp`, `requiere_aprobacion` y, con `autorizacion_id`, `aprobacion` (`APROBADO`, `RECHAZADO`, `NO_INCLUIDO`, `CANTIDAD_MAYOR`, `PENDIENTE` o `null`) y `motivo_rechazo`. `puede_confirmar` es falso si falta la aprobación (DE-02); el nivel del semáforo no cambia. Con una aprobación que ya no cubre (DE-13), `autorizacion_error` lo explica. |
| `POST /api/vales` (ENTREGA) | Según el tipo | Nuevos 409 `REQUIERE_APROBACION_DESPACHO` y `APROBACION_INVALIDA`. `AUTORIZACION_INVALIDA` queda para la autorización misma (no aprobada, vencida, usada, de otro almacén, trabajador o proyecto, o de un tipo que no corresponde: DESPACHO, o EXCEDENTE si el despacho no la pide). Quien confirma no puede ser quien aprobó (403 `AUTORIZACION_PROPIA`). Si la autonomía se prendió mientras se esperaba, se confirma sin la autorización y esta no se gasta (DE-16). |
| `GET /api/vales/{id}` | `vales.ver` | Agrega `despacho: {modo: APROBADO \| PROPIO \| AUTONOMO \| null, aprobo: {id, nombre} \| null}`, derivado de `autorizacion_id` y de `movimiento.reglas` (`DE-01`, `DE-07`, `DE-14`). |
| `PATCH /api/almacenes/{id}/autonomia` | `despacho.autonomia` | `{despacho_epp_con_aprobacion: bool, motivo}`. Responde la ficha del almacén. 422 sin motivo; 404 si no existe; si el valor no cambia, 200 sin auditoría. Auditoría `almacen.autonomia` (antes, después, motivo). |
| `PATCH /api/usuarios/{id}/autonomia` | `despacho.autonomia` | `{despacho_autonomo: bool, motivo}`. Responde el usuario. 422 sin motivo; 404 si no existe. Auditoría `usuario.autonomia`. |

### Autorizaciones (FEAT-014 y FEAT-015)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `POST /api/autorizaciones` | Sesión | El router exige sesión; el servicio comprueba `entregas.crear` para EXCEDENTE/DESPACHO y `traspasos.operar` para TRASLADO. Cuerpo: `{tipo: EXCEDENTE (por omisión) \| DESPACHO \| TRASLADO, id_cliente, trabajador_id? (no en TRASLADO), almacen_id?, proyecto_id?, destino_almacen_id? (solo TRASLADO), motivo?, nota? (hasta 255), renglones: [{codigo, cantidad, observacion?}]}` (1 a 100 renglones). El almacén sale de la sesión; de cada renglón el servidor toma solo `codigo`, `cantidad` y `observacion` y evalúa él mismo. `motivo` obligatorio en EXCEDENTE, en TRASLADO y en un DESPACHO con naranjas; en un DESPACHO sin naranjas se guarda «Despacho de EPP». Un DESPACHO lleva **todos** los renglones de EPP y todos los naranjas del vale; los verdes y amarillos de herramienta viajan como contexto. Responde 201 `{id, tipo, estado: PENDIENTE, vence_en, avisados}` (`avisados`: a cuántos supervisores se mandó aviso, sin decir a quiénes); 200 si el `id_cliente` ya existía con el mismo cuerpo; 409 `CONFLICTO` con otro cuerpo. 422 `RENGLON_NO_AUTORIZABLE` con `detalles: {codigo, regla, nivel, motivos}` por un rojo (A-06), por un `tipo` que no corresponde (`regla: "DE-01"`: el despacho no pide aprobación; `regla: "DE-04"`: se mandó EXCEDENTE y el vale pide despacho) o, en EXCEDENTE, por un renglón que no es naranja. Los avisos se mandan después del commit. |
| `GET /api/autorizaciones/{id}` | Sesión (como hoy) | Agrega `tipo`, `renglones` con `clase` (`EPP`, `EXCEDENTE`, `CONTEXTO`), `renglones_resueltos`, `nota`, `proyecto`, `trabajador {id, nombre, numero_empleado, tiene_foto}` (`null` en TRASLADO), `almacen {id, clave, nombre}`, `origen` y `destino` (TRASLADO) y `servidor_ahora` (para calcular lo que falta sin el reloj del dispositivo). La ven quien la pidió y quien tiene `autorizaciones.resolver` con el almacén en su conjunto (AC-40). |
| `GET /api/autorizaciones?estado=&tipo=&almacen_id=` | `autorizaciones.resolver` | De la más antigua a la más nueva, de todos los almacenes del conjunto. Cada elemento agrega `tipo`, `proyecto`, `almacen`, `trabajador.tiene_foto`, `incluye_excedente`, `renglones` con `clase`, `origen`, `destino` y `servidor_ahora`. |
| `POST /api/autorizaciones/{id}/resolucion` | Sesión | El router exige sesión; el servicio comprueba `autorizaciones.resolver` en el usuario de sesión o en el autorizado por PIN. Cuerpo: `{decision?: APROBAR \| RECHAZAR, motivo?, renglones?: [{renglon, decision: APROBAR \| RECHAZAR, motivo?}], usuario?, pin?}`: `decision` (todo) **o** `renglones` (uno por renglón que se resuelve; los de contexto no se mandan). Rechazar pide `motivo` (422 `DATOS_INVALIDOS` con `regla: "DE-06"`). Queda APROBADA si se aprobó al menos un renglón y RECHAZADA si ninguno; al aprobarse, `vence_en` pasa a `resuelta_en` + `AUTORIZACION_VIGENCIA_MINUTOS` (DE-09). Un TRASLADO no acepta `renglones` (422): se aprueba o rechaza completo; con PIN, la sesión de quien envía debe tener `traspasos.operar`. Responde la solicitud con `renglones_resueltos`. Siguen 403 `AUTORIZACION_PROPIA`, 403 `PIN_INCORRECTO`, 429 `DEMASIADOS_INTENTOS` y 409 `AUTORIZACION_RESUELTA` (con detalle). |
| `POST /api/autorizaciones/resolucion-multiple` | `autorizaciones.resolver` | `{resoluciones: [{id, decision: APROBAR \| RECHAZAR, motivo?}]}`, de 1 a 50, solo desde la sesión (sin PIN). Cada una en su propia transacción, con el reintento ante interbloqueo de la individual. Responde 200 `{resultados: [{id, estado, error: {codigo, mensaje} \| null}]}`. Errores por solicitud: `AUTORIZACION_RESUELTA`, `AUTORIZACION_PROPIA`, `NO_ENCONTRADO` y `RENGLON_NO_AUTORIZABLE` con `regla: "DE-12"` (una que incluye excedente no se aprueba en grupo). |
| `POST /api/autorizaciones/{id}/retiro` | Sesión; solo quien la pidió | **Solo si se aprueba la decisión abierta 1 de FEAT-014.** Retira una solicitud PENDIENTE: estado `RETIRADA` y aviso de reemplazo. |

### Notificaciones push (FEAT-014, NT-01 a NT-09; módulo `notificaciones`)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `GET /api/notificaciones/clave-publica` | Sesión | `{clave_publica}` (VAPID, base64url). 404 `NO_ENCONTRADO` («Los avisos no están configurados en este servidor») si faltan las claves; la pantalla esconde «Activar avisos». |
| `POST /api/notificaciones/suscripciones` | `autorizaciones.resolver` (con T-4 del maestro, propuesta, también `traspasos.recibir` con `requiere_alguno`) | `{endpoint, keys: {p256dh, auth}}`, como lo entrega el navegador. Liga la suscripción al usuario y a la familia de la sesión. `endpoint` `https` y de 1000 caracteres como máximo (si no, 422). Responde 201 `{id, creada_en}` (200 si ya existía para esa familia). |
| `DELETE /api/notificaciones/suscripciones/{id}` | Sesión | Revoca una suscripción **propia** (404 si es de otro). 204. |
| `POST /api/notificaciones/prueba` | `autorizaciones.resolver` | Aviso de prueba a las suscripciones de la familia de la sesión. `{enviadas, fallidas}`. 429 `DEMASIADOS_INTENTOS` antes de 10 s. |

Contenido de un aviso (lo lee el service worker; menos de 4 KB; sin costos, CURP, NSS ni foto): `{evento: NUEVA | RESUELTA | PRUEBA, tipo, autorizacion_id, almacen: {clave, nombre}, pendientes, titulo, cuerpo, url, etiqueta, silencioso}`. Con `pendientes` mayor que 1, `url` es `/autorizaciones`. TTL de 15 minutos. Destinatarios: usuarios activos con `autorizaciones.resolver` y el almacén en su conjunto, menos quien la pidió; el Administrador no recibe por omisión (NT-02). El traslado confirmado manda además un aviso informativo al destino (X-20).

### Proyectos y conjunto de almacenes (FEAT-013, PR-01 a PR-14, AC-36 a AC-41, TB-04 a TB-08; módulo `proyectos`)

Ficha de proyecto: `{id, clave, nombre, almacen: {id, clave, nombre}, inicio, fin_estimado, estado, situacion: VIGENTE | POR_INICIAR | FIN_VENCIDO | CERRADO, cerrado_en, motivo_cierre, trabajadores_asignados}`. Fechas de proyecto en hora del centro de México.

| Endpoint | Permiso | Contrato |
|---|---|---|
| `GET /api/proyectos?almacen_id=&situacion=&q=&asignables=` | `proyectos.ver` o `proyectos.asignar` (`requiere_alguno`) | Lista paginada. Con `proyectos.ver`, los de su conjunto (todos con `almacenes.todos`); con `proyectos.asignar` (RH, sin almacén), todos, solo con datos generales, sin consumo ni valor (PR-07). `asignables=true` deja los activos con fin estimado igual o posterior a hoy. |
| `POST /api/proyectos` | `proyectos.administrar` | `{clave, nombre, almacen_id, inicio, fin_estimado}`. 201 con la ficha; si el almacén no es de tipo `PROYECTO`, la ficha trae `aviso` (no es error). 409 `CLAVE_REPETIDA`, 409 `ALMACEN_CERRADO`, 422 `DATOS_INVALIDOS` (formato, `fin_estimado < inicio` con `regla: "PR-02"`), 404 (almacén). Auditoría `proyecto.crear`. |
| `GET /api/proyectos/{id}` | `proyectos.ver` o `proyectos.asignar` | Ficha. Fuera del alcance, 404. |
| `PATCH /api/proyectos/{id}` | `proyectos.administrar` | `{nombre?, inicio?, fin_estimado?, clave?, almacen_id?}`. 409 `PROYECTO_CERRADO`, 409 `PROYECTO_CON_VALES` (clave o almacén). Auditoría `proyecto.editar`. |
| `POST /api/proyectos/{id}/cierre` | `proyectos.administrar` | `{motivo}` (1 a 500). Termina en la misma transacción todas sus asignaciones activas. 200 con la ficha, `asignaciones_terminadas` y `trabajadores_sin_proyecto`. 409 `CONFLICTO` si ya estaba cerrado. Auditoría `proyecto.cerrar`. |
| `POST /api/proyectos/{id}/reapertura` | `proyectos.administrar` | `{fin_estimado?, motivo?}`; `fin_estimado` obligatorio si el anterior ya pasó (422). 409 `CONFLICTO` si ya estaba activo; 409 `ALMACEN_CERRADO`. Las asignaciones no se restauran. |
| `GET /api/trabajadores/{id}/proyectos` | `trabajadores.ver` | Asignaciones activas y terminadas, la más reciente primero. |
| `POST /api/trabajadores/{id}/proyectos` | `proyectos.asignar` | `{proyecto_id, principal?, inicio?, reemplaza_asignacion_id?}`; con `reemplaza_asignacion_id` es un cambio de proyecto (termina una y abre otra, que hereda `principal`). 201 con las asignaciones. 409 `ASIGNACION_REPETIDA`; 422 `PROYECTO_INVALIDO`; 409 si el trabajador está Inactivo. |
| `POST /api/trabajadores/{id}/proyectos/{asignacion_id}/termino` | `proyectos.asignar` | 200 con las asignaciones y `queda_sin_proyecto`. 409 `CONFLICTO` si ya estaba terminada. |
| `POST /api/trabajadores` | `trabajadores.administrar` (y `proyectos.asignar`, en el servicio: 403 sin él) | Acepta `proyecto_id` obligatorio y asignable (422 `PROYECTO_REQUERIDO` o `PROYECTO_INVALIDO`); crea la asignación principal en la misma transacción. `area_obra` deja de pedirse: se llena con el nombre del proyecto. |
| `POST /api/trabajadores/{id}/periodos` | `trabajadores.administrar` | Acepta `proyecto_id`; obligatorio si el trabajador no tiene asignación activa a un proyecto asignable (PR-11). |
| `GET /api/trabajadores`, `GET /api/trabajadores/{id}` | `trabajadores.ver` | Cada trabajador trae `proyectos: [{asignacion_id, proyecto: {id, clave, nombre, almacen}, principal}]`. La lista acepta `proyecto_id` y `sin_proyecto=true`. |
| `POST /api/vales/evaluar`, `POST /api/vales` (ENTREGA) | Según el tipo | Aceptan `proyecto_id`. La evaluación trae `proyecto` (el que se tomará o `null`), `proyectos_del_trabajador` y `pide_proyecto`, y los motivos del vale PR-09 (amarillo, elegir) o PR-10 (amarillo, `pide_observacion`). Al confirmar: 422 `PROYECTO_REQUERIDO`, 422 `PROYECTO_INVALIDO`, 422 `DATOS_INVALIDOS` (observación de PR-10), 409 `VALE_CAMBIO` (el proyecto se cerró o la asignación cambió). Un `proyecto_id` en otro tipo de vale es 422. El detalle del vale trae `proyecto`; la CANCELACION lo hereda. |
| `PUT /api/usuarios/{id}/almacenes` | `acceso.usuarios` o `almacenes.asignar_personal` (`requiere_alguno`; el límite de AC-41 en el servicio) | `{almacenes: [ids], almacen_activo_id}`: deja el conjunto exactamente así. Con `almacenes.asignar_personal` solo agrega o quita almacenes de su propio conjunto (403 si no). 422 si un almacén no existe o está cerrado, si el activo no está en el conjunto, si el usuario tiene `almacenes.todos` o es RH, o está inactivo. 200 con el renglón de personal (`almacenes`, `almacen_activo`). Auditoría `usuario.almacenes`. |
| `PATCH /api/usuarios/{id}/almacen` | `almacenes.asignar_personal` | Sin cambio de forma: deja el conjunto con ese único almacén (o vacío con `null`). |
| `PUT /api/sesion/almacen` | Sesión | `{almacen_id}`: cambia el almacén activo, desde la siguiente petición y en todos sus dispositivos. 200 con la sesión. 403 `ALMACEN_NO_ASIGNADO`, 409 `ALMACEN_CERRADO`, 422 para quien tiene `almacenes.todos`. Un vale capturado en el almacén anterior responde 409 `ALMACEN_CAMBIO`. Auditoría `usuario.almacen_activo`. |
| `GET /api/sesion`, `POST /api/sesion`, `POST /api/sesion/refresh` | Sesión / Público | Agregan `almacenes` (el conjunto) y `almacen_activo`; `almacen` se conserva igual a `almacen_activo`. |
| `GET /api/personal`, `GET /api/usuarios` | Sin cambio | Cada renglón trae `almacenes`; `almacen_id` filtra por pertenecer al conjunto. |
| `GET /api/almacenes?resumen=true` | `almacenes.administrar` | El resumen agrega `proyectos_activos` y `aviso_sin_proyecto` (PR-12: tipo `PROYECTO`, activo, sin proyectos activos); `usuarios` cuenta a quienes lo tienen en su conjunto. |
| `POST /api/almacenes/{id}/cierre` | `almacenes.administrar` | Bloqueo nuevo `CON_PROYECTOS_ACTIVOS`. |
| `GET /api/tablero/resumen` | `tablero.ver` | `alcance` agrega `almacenes` (los del conjunto) y `nombre` «Tus 2 almacenes»; agrega `almacenes_sin_proyecto` (solo con `almacenes.administrar`; `null` sin él) y `proyectos_por_vencer` (activos con fin estimado en los próximos 7 días o ya pasado; con `proyectos.ver`, `null` sin él). Con FEAT-016, además `inspecciones_vencidas` e `inspecciones_sin_registro`. |
| `GET /api/tablero/valor` | `reportes.valor_inventario` | Alcance por conjunto; agrega `unidades_en_almacen`, `unidades_en_resguardo` y `unidades_total` (TB-04). Sigue sin costos unitarios. |
| `GET /api/tablero/proyectos?desde=&hasta=&almacen_id=&proyecto_id=` | `tablero.ver` y `proyectos.ver` | Uso por proyecto (TB-05 a TB-07): `{alcance, rango, proyectos: [{id, clave, nombre, almacen, inicio, fin_estimado, estado, situacion, trabajadores_asignados, retornables_en_resguardo: {unidades, valor}, consumibles_consumidos: {unidades, valor}, total: {unidades, valor}, articulos_sin_costo, por_categoria}], sin_proyecto: {retornables_en_resguardo, consumibles_consumidos}, generado_en}`. Un proyecto entra si **su almacén** está en el conjunto, sin importar quién entregó. El resguardo cuenta para el proyecto de la última entrega de ese artículo (o pieza). `valor` es cantidad por costo actual y va `null` sin `reportes.valor_inventario` (y por T-2). `por_categoria` solo con `proyecto_id` (hasta 6 y «Otras»). Orden por `total.valor` (o unidades). |

### Inspecciones y avisos de vigencia (FEAT-016, P-09 a P-17)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `GET /api/inspecciones/pendientes?estado=&almacen_id=&categoria_id=&q=&ubicacion=&pagina=&tamano=&solo_contar=` | `inspecciones.ver` | `estado`: `VENCIDA`, `POR_VENCER` o `SIN_INSPECCION`. Responde `{conteos: {vencidas, por_vencer, sin_inspeccion, no_aptas, en_mantenimiento, no_aptas_con_trabajador}, elementos: [{pieza: {id, codigo, numero_serie, serie_pendiente, estado}, articulo: {id, codigo, nombre, categoria}, vigente_hasta, dias_restantes, dias_aviso, ubicacion: {tipo, almacen, trabajador, desde, folio, vale_id, destino}, accion: INSPECCIONAR \| PEDIR_DEVOLUCION \| NINGUNA}], total}`; con `solo_contar=true`, solo `conteos`. Alcance por conjunto (AC-37); folio y vale de otro almacén en `null`. Sin costos, CURP ni NSS. Solo lee. |
| `POST /api/inspecciones/lote` | `piezas.inspeccionar` | `{id_lote, piezas: [{id_cliente, codigo, resultado, puntos, observacion?, foto?}]}`, de 1 a 50 (más, 422). Cada pieza en su propia transacción. 200 `{guardadas, rechazadas, repetidas, resultados: [{id_cliente, codigo, estado: GUARDADA \| REPETIDA \| RECHAZADA, inspeccion?, error?: {codigo, mensaje, regla}}]}`. |
| `POST /api/piezas/{id}/inspecciones` | `piezas.inspeccionar` | `puntos` obligatorio con las cinco claves; acepta `id_cliente` y `foto` (PNG, JPEG o WebP, hasta 3 MB; adjunto `FOTO_INSPECCION`). La fecha la pone el servidor (un campo de fecha es 422). Nuevos: 422 con `regla: "P-14"` (Apto con un punto Mal sin observación), 409 `PIEZA_EN_TRANSITO`, 409 `PIEZA_EN_MANTENIMIENTO`. Con un `id_cliente` ya guardado, 200 con la misma inspección. Se hace en el almacén activo (AC-38). |
| `GET /api/piezas/{id}` | `catalogo.ver` | Agrega `vigencia_inspeccion_dias`, `dias_aviso_inspeccion` (resuelto) y su `origen` (`ARTICULO`, `CATEGORIA`, `GENERAL`), `dias_restantes`, `vigencia_si_apta_hoy` e `inspeccion_posible: {puede, motivo, regla}`. El historial trae `puntos` y la foto. |
| Categorías y artículos (`GET`/`POST`/`PATCH`) | Los de hoy | Campo `dias_aviso_inspeccion` (1 a 90 o `null`; fuera de rango, 422 con `regla: "P-10"`). El artículo devuelve el valor resuelto y su origen; la categoría, `articulos_con_aviso_propio`. |
| `POST /api/vales` (ENTRADA) | `inventario.entradas` | Inspección inicial con fecha posterior a hoy: 422 `FECHA_FUTURA`. |
| `GET /api/tablero/resumen` | `tablero.ver` | `inspecciones_por_vencer` con el aviso resuelto de cada artículo (no 7 fijo); nuevos `inspecciones_vencidas` e `inspecciones_sin_registro`. Los tres `null` sin `inspecciones.ver`. |

### Bitácora por vale y PDF (FEAT-017, BT-01 a BT-10)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `GET /api/bitacora?desde=&hasta=&almacen_id=&tipo=&usuario_id=&trabajador_id=&proyecto_id=&articulo_id=&q=&lote_id=&solo_mios=&pagina=&tamano=&formato=` | `bitacora.ver` o `reportes.movimientos` (`requiere_alguno`) | Un elemento por vale, o por lote si varios vales del alcance comparten `lote_id`; del más reciente al más antiguo; paginado por elemento. Mismo alcance que `GET /api/reportes/movimientos`; un filtro fuera del alcance no devuelve nada. `q` busca códigos de artículo/pieza y series. Respuesta `{elementos, total, sin_registros, mensaje}`. Elemento `VALE`: `{clase, id, folio, tipo, tipo_texto, creado_en, almacen, responsable, trabajador, destino, proyecto, vale_origen {id, folio}, cancelacion {id, folio}, renglones, unidades, estado, estado_texto, direccion: ENTRADA \| SALIDA \| EN_CAMINO \| null, direccion_texto, coincidencias, capturado_sin_conexion, capturado_en}`. Elemento `LOTE`: `{clase, lote_id, origen_lote: IMPORTACION \| TRASPASO_EXCEL, creado_en, tipo, almacen, responsable, renglones, unidades, estado_texto, direccion, coincidencias, vales: [{clase, id, folio, estado, renglones, unidades, parte, cancelacion}]}`. `direccion` solo con `almacen_id`. `coincidencias` solo con filtro de artículo, pieza o serie. `formato=csv`: un renglón por vale. Sin costos, CURP ni NSS. |
| `GET /api/vales/{id}/renglones?q=&pagina=&tamano=` | `vales.ver` | Los renglones del detalle, paginados (`tamano` hasta 500), con el mismo alcance y el mismo 404 que el detalle. `q` (2 caracteres mínimo) busca en código de artículo, código de pieza, nombre y serie. `{elementos, total, sin_registros, mensaje}`. |
| `GET /api/vales/{id}` | `vales.ver` | Agrega `lote {id, parte, partes, renglones, unidades}` o `null`, `proyecto`, `resumen` (por categoría `{categoria, renglones, unidades}` y, solo con `reportes.valor_inventario`, `valor` por categoría y `valor_total`; nunca por renglón; T-2), `relacionados [{relacion, id, folio, creado_en, texto}]` (`id` y `folio` nulos fuera del alcance), `capturado_sin_conexion` y `capturado_en`. Con `?renglones=false` no trae los renglones. |
| `POST /api/vales` | Según el tipo | Sigue rechazando `lote_id` (422): el lote lo pone la importación como parámetro interno. |
| `POST /api/importacion`, `POST /api/importacion/traspasos` | Los de hoy | La respuesta agrega `lote_id` (igual al `id_lote`). |

El PDF del vale, del lote y de las etiquetas se arma en el navegador con los datos de estas rutas: no hay endpoint de PDF. `GET /api/reportes/movimientos` y `GET /api/reportes/usuarios` no cambian.

### Deudores, consumo por trabajador y alto valor (FEAT-018, AV-01 a AV-05, DU-01 a DU-09)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `GET /api/deudores?trabajador_id=&almacen_id=&proyecto_id=&categoria_id=&alto_valor=&vigencia=&antiguedad_dias=&q=&pagina=&tamano=&formato=` | `deudores.ver` | Un elemento por trabajador con deuda (retornables en resguardo): `{trabajador {id, numero_empleado, nombre, tiene_foto}, vigente, aviso, proyectos, piezas, unidades, alto_valor, desde, otros_almacenes, renglones}` y arriba `resumen` (las cuatro tarjetas). Con `trabajador_id`, `renglones: [{articulo, pieza, cantidad, desde, vale {id, folio}, proyecto, almacen, alto_valor, requiere_inspeccion}]` (`vale.id` nulo fuera del alcance). Una cosa se le debe al almacén y al proyecto de su entrega más reciente. Alcance (DU-03): con `almacenes.todos`, todo; con `trabajadores.administrar` (RH), todos los trabajadores y deudas; si no, lo que se le debe a su conjunto y, de lo demás, solo el número (`otros_almacenes`). Paginado en la consulta. `formato=csv`: un renglón por cosa debida. Sin costos. |
| `GET /api/deudores/resumen` | `deudores.ver` | Por almacén y por proyecto: trabajadores con deuda, piezas, unidades, alto valor fuera y no vigentes. Mismos filtros y alcance. `formato=csv`. Sin costos. |
| `GET /api/trabajadores/{id}/consumo?desde=&hasta=` | `trabajadores.ver` | `{periodo {desde, hasta, origen}, elementos: [{articulo {id, codigo, nombre}, unidad, cantidad, recomendado, por_proyecto: [{proyecto \| null, cantidad}]}], valor_total, valor_por_proyecto}`. Consumibles entregados por todos los almacenes, netos de cancelaciones; periodo por omisión, su contrato vigente (o el último). `valor_total` y `valor_por_proyecto` solo con `reportes.valor_inventario` (y T-2); nunca por artículo. |
| `GET /api/reportes/consumo` | `reportes.consumo` | Filtro nuevo `proyecto_id`. |
| Categorías (`GET`, `POST`, `PATCH`) | Los de hoy | Aceptan y devuelven `alto_valor` (cambiarlo pide `catalogo.administrar`, auditoría `categoria.editar`). |
| Artículo, pieza, `GET /api/seguimiento/*`, tablero | Los de hoy | Devuelven `alto_valor` (booleano, AV-02: marca de la categoría o costo igual o mayor que `ALTO_VALOR_COSTO_MINIMO`) y `alto_valor_motivo` solo con `catalogo.costos` (AV-05). `alto_valor_fuera` del tablero y el filtro `alto_valor` de Seguimiento cuentan alto valor **o** `requiere_inspeccion`, sin leer el nombre de la categoría (AV-04). La vista previa de la importación puede sugerir «Equipo de alto valor» por costo (AV-03). |
| `GET /api/reportes/adeudos` | `reportes.adeudos` | Sin cambios; la pantalla `/reportes/adeudos` redirige a `/deudores`. |

### Búsqueda y etiquetas (FEAT-019, UX-01 a UX-07)

| Endpoint | Cambio |
|---|---|
| `GET /api/busqueda` | Busca trabajadores por palabras en cualquier orden (cada palabra en el nombre; hasta 5), por número de empleado (contiene) y por código de credencial (empieza con); artículos por nombre (palabras), marca y código; piezas por código, serie y nombre del artículo. Orden por relevancia (exacto, empieza, contiene; luego nombre). `tamano` 10 por omisión y 50 como máximo (más, 422). Campos nuevos sin quitar los existentes: `articulos[].retornable`, `en_almacen` y `con_trabajadores` (solo retornables); `piezas[].ubicacion_texto` (el texto de C-13); `trabajadores[].puesto`, `vigencia {vigente, texto}` y `credencial`. Sin costos, CURP ni NSS. |
| `GET /api/trabajadores?q=` | `q` busca por palabras, igual que la búsqueda. |
| `GET /api/etiquetas` | Filtros opcionales: `articulo_id` y `lote_id` (solo `piezas`), `alta_desde` y `alta_hasta` (solo `credenciales`, fechas de México sobre `trabajador.creado_en`). Un filtro que no corresponde al tipo es 422. Sigue sin paginar y con `etiquetas.imprimir`. |
| `GET /api/escaneo/{codigo}` | Sin cambio. |

### App de Android y sincronización (FEAT-020, OF-01 a OF-30; módulo `sincronizacion`)

| Endpoint | Permiso | Contrato |
|---|---|---|
| `POST /api/dispositivos` | `sincronizacion.operar` | `{nombre, plataforma: ANDROID, version_app, modelo}`. Inscribe el equipo en el almacén activo de quien lo pide y lo registra en el equipo. 201 `{id, secreto}` (el secreto se entrega **una sola vez**; la base guarda su SHA-256). 409 `ALMACEN_CERRADO`. Auditoría `dispositivo.inscribir`. |
| `GET /api/dispositivos` | `sincronizacion.administrar` | Equipos de sus almacenes: nombre, quién lo inscribió y cuándo, usuarios registrados, versión, `ultimo_paquete_en`, `ultima_subida_en` y estado («En uso», «Sin contacto hace 30 h», «Revocado»). |
| `POST /api/dispositivos/{id}/revocacion` | `sincronizacion.administrar` | `{motivo, cerrar_sesiones}`; sin motivo, 422; ya revocado, 409. Con `cerrar_sesiones`, sube `version_sesion` de los usuarios registrados en el equipo. Auditoría `dispositivo.revocar`. |
| `GET /api/sincronizacion/paquete` | `sincronizacion.operar` + `X-Dispositivo` | El paquete del almacén del equipo (OF-13): JSON con `formato`, `generado_en`, `almacen_id`, `dispositivo_id` y las secciones `almacen`, `usuarios_del_equipo`, `categorias`, `articulos` (activos e inactivos), `codigos`, `piezas`, `existencias`, `trabajadores` (los de proyectos del almacén y de sus hijos, más los que tienen pendientes con él), `traspasos_en_transito`, `proyectos` y `parametros`. Comprimido con `gzip`, `ETag` = SHA-256 del contenido; con `If-None-Match` igual, 304. Nunca trae costos, CURP, NSS, contraseñas, PIN ni sus hashes, firmas ni datos de otros almacenes fuera del resguardo de esos trabajadores. Actualiza `ultimo_paquete_en` y registra al usuario en el equipo. 403 `DISPOSITIVO_REVOCADO`, `DISPOSITIVO_NO_INSCRITO`, `DISPOSITIVO_DE_OTRO_ALMACEN`. Las fotos se piden aparte con `GET /api/trabajadores/{id}/foto` (cambian cuando cambia su `sha256`). |
| `POST /api/sincronizacion/lotes` | `sincronizacion.operar` + `X-Dispositivo`; el permiso de cada operación, en el servicio, contra quien la capturó | `{lote_id, formato, enviado_en, operaciones: [{id_cliente, secuencia, tipo: ENTREGA \| DEVOLUCION \| RECEPCION \| INSPECCION \| NO_APTA \| SOLICITUD_COMPRA, responsable_id, capturado_en, paquete_huella, evaluacion_local, cuerpo}]}`, hasta `SINCRONIZACION_LOTE_MAXIMO` (20); el `cuerpo` de un vale es el de `POST /api/vales` con `token`, `proyecto_id`, `observacion` y `firma`. Cada operación en su propia transacción y en orden de `secuencia`, por el servicio del módulo dueño (`movimientos`, `inspecciones`, `solicitudes_compra`). 200 `{resultados: [{id_cliente, resultado: GUARDADO \| GUARDADO_CON_AVISOS \| CONFLICTO, folio?, vale_id?, avisos?, conflicto_id?, motivo?}], servidor_ahora}`. Idempotente por `id_cliente` y `huella_cuerpo` (vales) o por `operacion_recibida` (lo demás): reenviar el mismo lote devuelve lo mismo. El responsable es quien capturó (debe estar registrado en el equipo); el almacén, el del equipo. Errores del lote: 401, 403 (`DISPOSITIVO_*`), 413 `CUERPO_MUY_GRANDE` (límite 12 MB), 422 `LOTE_INVALIDO`. Un equipo revocado manda todas sus operaciones a conflicto `DISPOSITIVO_REVOCADO`. Actualiza `ultima_subida_en`; auditoría `sincronizacion.lote`. |
| `GET /api/sincronizacion/conflictos?estado=&dispositivo_id=&desde=&hasta=` y `GET /api/sincronizacion/conflictos/{id}` | `sincronizacion.administrar` | Conflictos de los equipos de sus almacenes. El detalle trae la operación capturada, la evaluación local, lo que dijo el servidor por renglón y el vale con que chocó. |
| `POST /api/sincronizacion/conflictos/{id}/resolucion` | `sincronizacion.administrar` | `{accion: REINTENTAR \| GUARDAR_SIN_RENGLONES \| GUARDAR_CON_DIFERENCIAS \| DESCARTAR, renglones?, motivo}`; motivo obligatorio. Lo que guarda lo crea `movimientos` como vale nuevo (con la hora de captura y el responsable originales). 409 `CONFLICTO_YA_RESUELTO`; 403 si quien resuelve capturó la operación. Auditoría `sincronizacion.resolver_conflicto`. |
| `PATCH /api/almacenes/{id}` | `almacenes.administrar` | Acepta `hora_descarga` (`HH:MM`, hora de México, o `null`). |
| `GET /api/vales/por-token/{token}` | Como hoy | Si el token no es de un vale pero sí de un conflicto, responde su estado («en revisión», «no se guardó»); si no existe, «pendiente de sincronizar», sin revelar nada más. |

Motivos de conflicto: `EXISTENCIA_INSUFICIENTE`, `PIEZA_EN_OTRA_UBICACION`, `YA_RECIBIDO`, `TRASPASO_CANCELADO`, `CODIGO_DESCONOCIDO`, `TRABAJADOR_NO_EXISTE`, `ALMACEN_CERRADO`, `ID_CLIENTE_OTRO_CUERPO`, `TOKEN_REPETIDO`, `FORMA_INVALIDA`, `USUARIO_NO_REGISTRADO`, `DISPOSITIVO_REVOCADO`, `DEPENDE_DE_CONFLICTO`.


## Implementación FEAT-004: mínimos y estados

- `GET /api/almacenes/{id}/minimos`, permiso `inventario.minimos`, devuelve `[{articulo_id, cantidad}]`.
- `PUT /api/almacenes/{id}/minimos`, mismo permiso, recibe `{minimos: [{articulo_id, cantidad}]}`. Actualiza únicamente los artículos enviados en una transacción y devuelve la lista actual. Cantidad entera de 0 a 100000; `null` elimina su configuración. Máximo 500 artículos únicos; una referencia inexistente o fuera del alcance no se aplica. Se registra `almacen.minimos` con antes/después.
- `GET /api/almacenes/{id}/existencias` agrega filtro `bajo_minimo=true` y campos `minimo: integer|null`, `bajo_minimo: boolean`, `no_disponible: integer`. Incluye artículos sin existencia si tienen un mínimo configurado, para que los agotados también aparezcan. No envía costos.
- `POST /api/piezas/{id}/estado` conserva `NO_APTO` y agrega `EN_MANTENIMIENTO`, `EN_CALIBRACION` y `APTO`, siempre con observación. El router exige `piezas.inspeccionar` o `piezas.marcar_estado`; el servicio exige específicamente el primero para No apta y el segundo para los otros estados. No se marca APTO una pieza No apta: requiere inspección. El regreso de mantenimiento/calibración a APTO por este endpoint solamente se admite si el artículo no requiere inspección; si la requiere responde 422 con P-06.
- La evaluación de entrega y de salida de traspaso agrega avisos E-14 y X-05 si la salida deja disponibles bajo el mínimo. Son amarillos sin observación obligatoria; se reevalúan al confirmar.

## FEAT-019 — búsqueda y etiquetas implementadas

`GET /api/busqueda` conserva permisos por grupo y alcance de piezas (AC-06). Cada grupo usa `pagina` (mínimo 1), `tamano` (omisión 10, máximo 50; excederlo devuelve 422). `q` se divide en hasta cinco palabras; se ignoran palabras de un carácter cuando hay otras. Cada palabra debe coincidir en nombre, código, número o marca según el grupo, sin distinguir acentos/mayúsculas con la colación de MySQL. Credenciales coinciden por prefijo del código registrado. Prioridad: coincidencia exacta, prefijo, resto; luego nombre/código.

Campos aditivos: artículos `retornable`, `en_almacen` y `con_trabajadores` (nulo para consumibles); piezas `ubicacion_texto` además de `ubicacion`; trabajadores `puesto`, `vigencia:{vigente,texto}`, `credencial` cuando coincidió su prefijo. No se envían costos, CURP ni NSS. `GET /api/trabajadores?q=` también aplica palabras independientes.

`GET /api/etiquetas` sigue protegido por `etiquetas.imprimir` y sin paginación. Filtros opcionales: `articulo_id` y `lote_id` solo para `tipo=piezas`; `alta_desde` y `alta_hasta` solo para `tipo=credenciales`. Fechas inclusivas por día de México sobre `trabajador.creado_en`; inactivos excluidos. Filtros de tipo incorrecto o rango invertido: 422 `DATOS_INVALIDOS`. Piezas de baja excluidas; alcance global previo conservado. La pieza agrega `numero_serie` cuando existe; `texto` permanece compatible. El QR siempre conserva exactamente el código registrado.
