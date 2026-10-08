# Contratos de API

Endpoints, cuerpos, errores y permisos del MVP. Todo va bajo `/api`, en JSON, con la sesión en una cookie.

Estado: es el contrato acordado para construir. Si al implementar cambia, se actualiza aquí en el mismo cambio.

## Convenciones

- Los `id` son UUID en texto, por ejemplo `01a10a17-3a3b-74ed-89d0-2082afd9941a` ([ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). En los ejemplos se abrevian.
- Las fechas van en ISO 8601; las horas, en UTC.
- Las listas admiten `pagina` y `tamano` y responden `{elementos, total}`.
- Cada endpoint exige un **permiso**; la columna "Permiso" da su clave ([ADR-007](decisions/ADR-007-permisos-por-clave.md)). Qué roles lo tienen de inicio está en la sección 8.2 de las [reglas](../product/reglas-de-negocio.md). "Sesión" significa que basta haber entrado. Ocho rutas (las que dicen "Según el tipo" o "Solicitar o atender", y algunas de las que dicen "Sesión") solo exigen sesión en el router y verifican el permiso en el servicio, porque depende del tipo de vale o del usuario, o porque aceptan uno de dos permisos: `POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}`, `POST /api/autorizaciones/{id}/resolucion`, `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}` (`compras.solicitar` o `compras.atender`). Otras cuatro rutas aceptan uno de dos permisos y lo declaran en el router con `requiere_alguno`: `GET /api/reportes/movimientos` y `GET /api/reportes/usuarios` (`bitacora.ver` o `reportes.movimientos`), `GET /api/seguimiento/piezas` y `GET /api/seguimiento/cantidad` (`reportes.existencias` o `resguardo.ver`). Sin el permiso, todas responden 403 `SIN_PERMISO` igual que las demás.
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
| 409 | `AUTORIZACION_INVALIDA` | La autorización no sirve para este vale: no está aprobada, venció, ya se usó, es de otro almacén o trabajador, o no cubre los renglones ni la cantidad (A-03). |
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
| `POST /api/articulos` | `catalogo.administrar` | Crea (201) un artículo; si indica un límite, 403 sin `catalogo.limites` (AC-30 de FEAT-011); control, retorno y reglas salen de la plantilla de su categoría si no se indican (un campo de regla en `null` significa "sin esa regla"). El código no puede repetir el de ningún artículo, pieza o credencial (409 `CODIGO_REPETIDO`) y queda registrado como su QR de producto o de estante (I-07). El costo solo se acepta con `catalogo.costos`; sin él, 403. |
| `GET /api/articulos/{id}` | `catalogo.ver` | Ficha: reglas, `tiene_movimientos` (control y retorno bloqueados), `existencias` por almacén (`cantidad` y `disponible`, que no cuenta piezas No aptas, en mantenimiento ni en calibración) y `en_posesion` (quién lo tiene, con `cantidad`, `desde`, `folio` y `vale_id`, y en artículos por pieza `piezas` con `id`, `codigo` y `numero_serie` de cada una; folio y vale en `null` si el vale es de otro almacén) (C-03, SG-02). Sin `almacenes.todos`, `existencias` trae solo el almacén del usuario (AC-06); `en_posesion` es el resguardo de los trabajadores y se ve completo. El costo, solo con `catalogo.costos`. |
| `PATCH /api/articulos/{id}` | `catalogo.administrar` | Edita datos, límite (cambiarlo pide además `catalogo.limites`: 403), aviso de cantidad inusual y requisitos; solo cambia lo que viene (omitido no es `null`). No cambia el código ni la inactivación (422 si se envían). Rechaza cambios de control o retorno con movimientos (409 `CON_MOVIMIENTOS`, CF-05). Activar la inspección deja sus piezas sin inspección vigente (CF-09). Cambiar el costo pide `catalogo.costos`. |
| `POST /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Inactiva con `{motivo}` (CF-10). Responde el artículo. 409 si ya estaba inactivo. |
| `DELETE /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Reactiva (CF-13). Responde el artículo. 409 si ya estaba activo. |
| `DELETE /api/articulos/{id}` | `catalogo.administrar` | Elimina solo si no tiene movimientos (CF-12); responde 204, o 409 `CON_MOVIMIENTOS`. Libera su código. |
| `GET /api/piezas/{id}` | `catalogo.ver` | Ficha (C-02): artículo, `numero_serie` (nulo si está pendiente), `serie_pendiente` (booleano derivado: `true` si `numero_serie` es nulo), estado, `inspeccion_vigente_hasta` e `inspeccion_vigente`, `ultima_inspeccion`, `ubicacion` (almacén, trabajador o virtual) e `historial`: movimientos, inspecciones, cambios de estado y ajustes de vigencia en una sola lista, del más reciente al más antiguo (`tipo`, `fecha` UTC, `titulo`, `detalle`, `usuario` y los campos propios de cada tipo). Sin costos. Sin `almacenes.todos`, una pieza fuera del alcance (no está en su almacén, ni la tiene un trabajador, ni va en tránsito desde o hacia él) responde 404 `NO_ENCONTRADO`, igual que una que no existe; de su historial, los movimientos de un vale de otro almacén solo se muestran si pasan por un trabajador, con el almacén como «Otro almacén» y sin `folio`, `vale_id` ni responsable (AC-06). |
| `POST /api/piezas/{id}/inspecciones` | `piezas.inspeccionar` | Registra una inspección (P-01) con `{resultado, puntos?, observacion?}`; `puntos` admite `etiquetas`, `costuras`, `cintas`, `herrajes` y `conectores` (booleanos). Responde 201 con la inspección y `pieza: {id, estado, inspeccion_vigente_hasta}`. Apto deja la pieza Apta y vigente hasta hoy más la vigencia de su artículo; No apto exige observación (422) y la deja No apta. Sirve para cualquier pieza de su almacén, también la que está con un trabajador (es del almacén de su última entrega); sin `almacenes.todos`, una pieza de otro almacén da 404 (AC-06, H11); una en baja da 409. |
| `POST /api/piezas/{id}/estado` | `piezas.inspeccionar` | Marca No apta con `{estado: "NO_APTO", observacion}` (P-03); la observación es obligatoria (422). Responde 200 con `{evento_id, estado_anterior, pieza}`. Si ya está No apta o en baja, 409. |
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

Parte de [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md) (TB-01 a TB-03). Solo lectura: no escribe nada y nunca trae costos, CURP ni NSS. Los dos endpoints piden `tablero.ver`; sin él (Compras, RH), 403 `SIN_PERMISO`. El alcance lo decide el servidor (AC-06, TB-01): con `almacenes.todos`, todos los almacenes o el que indique `almacen_id`; sin él, **solo el almacén asignado** y `almacen_id` se ignora (no es error). Un `almacen_id` que no existe, con `almacenes.todos`, es 404 `NO_ENCONTRADO`; uno cerrado sí se puede pedir. Sin almacén asignado y sin `almacenes.todos`, ambos responden 200 con todo en cero y `alcance.almacen_id` en `null` y `es_todos` en `false`.

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
| `POST /api/vales/evaluar` | Según el tipo | Evalúa sin escribir. Acepta el mismo cuerpo que confirmar (ignora `id_cliente`, `observacion` y `firma`). Con `autorizacion_id` marca como `autorizado` los renglones naranja que esa autorización cubre. |
| `POST /api/vales` | Según el tipo | Confirma. Agrega `id_cliente`, `observacion`, `autorizacion_id` y `firma`. |
| `GET /api/vales/{id}` | `vales.ver` | Detalle con renglones. Fuera del alcance del usuario (AC-06), 404. |
| `GET /api/vales/{id}/firma` | `vales.ver` | La imagen de la firma del trabajador (PNG), con la misma visibilidad que el vale (AC-06). 404 si el vale no tiene firma en pantalla. Sirve para el detalle y la impresión: `tiene_firma` del detalle dice si existe. |
| `GET /api/vales/por-token/{token}` | `vales.ver` | El vale que abre su QR (mismo detalle). |
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
| TRASPASO | `traspasos.operar` | `destino_almacen_id` (obligatorio); renglones por código de pieza, o de artículo con `cantidad`. Sin `trabajador_id`, `vale_origen_id`, `pieza` ni costos (422). Firma de sesión (F-09): no lleva `firma`. El vale queda `EN_TRANSITO`, folio `CLAVE-TRS-000001`. `almacen_id` solo para quien tiene `almacenes.todos`. `evaluar` trae en `motivos` del vale la regla X-03 (verde, amarillo o rojo) y por renglón X-02, X-04, X-09. **Ruta que no es padre-hijo (X-03, FEAT-008):** sin `almacenes.todos`, `evaluar` la marca en rojo y confirmar responde 403 `RUTA_SOLO_ADMINISTRADOR`; con `almacenes.todos`, `evaluar` da amarillo con `pide_observacion: true` (en el vale) y confirmar exige `observacion` en el vale (sin ella, 422 `DATOS_INVALIDOS` con `detalles: [{campo: "observacion", mensaje, regla: "X-03"}]`). Un origen o destino cerrado: 409 `ALMACEN_CERRADO` (AL-04). |
| RECEPCION | `traspasos.recibir` | `vale_origen_id` (el traspaso, obligatorio); `renglones`: lo escaneado, por código de pieza o de artículo con `cantidad` (para recibir todo, todos los pendientes de `por-recibir`; sin renglones, 422). Sin `trabajador_id` ni `destino_almacen_id` (422). Firma de sesión (F-09). Folio `CLAVE-REC-000001` del almacén que recibe; al confirmar, el traspaso queda `RECIBIDO` o `RECIBIDO_CON_DIFERENCIAS` (X-13). `evaluar`: X-10 (vale y renglones, rojo), X-12 (renglón, rojo), X-13 (vale, amarillo) y, si la recepción deja algo pendiente sin `observacion` (vacía o en blanco), RG-14 (vale, rojo). Al confirmar esa recepción sin observación responde 422 con `detalles: [{campo: "observacion", mensaje, regla: "RG-14"}]` y no guarda nada; la recepción que completa lo pendiente no la pide. Un `vale_origen_id` inexistente es 404 y el de un vale que no es traspaso, 422. |
| CANCELACION | `vales.cancelar` | `vale_origen_id` (el vale que se cancela) y `observacion` (el motivo); sin renglones: salen de los del original. Normalmente se usa `POST /api/vales/{id}/cancelacion`; `POST /api/vales` con este tipo hace lo mismo. |

**Enviar y recibir son dos permisos distintos.** `traspasos.operar` es solo para **enviar** (tipo TRASPASO, incluido el traspaso por lista de Excel); `traspasos.recibir` es para **recibir** (tipo RECEPCION y `GET /api/traspasos/por-recibir`). Como `POST /api/vales/evaluar` y `POST /api/vales` solo exigen sesión en el router, el servicio verifica la clave según el `tipo` del cuerpo: `traspasos.operar` para TRASPASO y `traspasos.recibir` para RECEPCION (403 `SIN_PERMISO` si falta). Un rol puede tener uno, el otro o los dos: de inicio el Supervisor trae los dos y el Administrador, todos; el Almacenista no recibe de inicio, pero un administrador puede darle `traspasos.recibir` desde Roles y permisos (sección 8.2 de las reglas). La interfaz de la recepción se muestra a quien tiene `traspasos.recibir`, no al rol. `GET /api/traspasos/por-recibir` ya declara su permiso en el router (no es una de las rutas que se verifican en el servicio).

**Pieza con serie pendiente en la ENTREGA (E-29).** Si un renglón entrega una pieza cuyo `numero_serie` es nulo, la evaluación le agrega el motivo `{regla: "E-29", codigo: "SERIE_PENDIENTE", nivel: "AMARILLO", mensaje: "Esta pieza no tiene número de serie registrado."}`. **No bloquea**: `puede_confirmar` no cambia y no pide observación. El renglón trae `pieza.serie_pendiente: true` para que la interfaz ofrezca capturar la serie. Traspaso, recepción y devolución no miran la serie.

**Almacén cerrado (AL-04, FEAT-008).** En cualquier tipo que mueve inventario (ENTRADA, ENTREGA, DEVOLUCION, TRASPASO, RECEPCION y CANCELACION), si el almacén del vale, o el origen o el destino de un traspaso, está `CERRADO`, `evaluar` trae un motivo rojo del vale con la regla `AL-04` y `POST /api/vales` responde 409 `ALMACEN_CERRADO` sin guardar nada. Las lecturas (consulta y reportes) no cambian.

Respuesta de `GET /api/traspasos/por-recibir` (sin costos; `codigo` es lo que se escanea al recibir: el de la pieza, o el del artículo si es por cantidad):

```json
{
  "total": 1,
  "elementos": [
    {
      "id": "01a1…", "folio": "KEP-TRS-000012", "token": "…", "estado": "RECIBIDO_CON_DIFERENCIAS",
      "origen": { "id": "01a1…", "clave": "KEP", "nombre": "Kepler" },
      "destino": { "id": "01a1…", "clave": "CON", "nombre": "Contratistas" },
      "envio": { "id": "01a1…", "nombre": "Almacenista Kepler" },
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
| `POST /api/autorizaciones` | `entregas.crear` | Solicita con `{trabajador_id, renglones, motivo}`. Responde 201 `{id, estado, vence_en}`. El motivo es obligatorio (A-02); el almacén sale de la sesión; `vence_en` es ahora más 15 minutos (`AUTORIZACION_VIGENCIA_MINUTOS`). De cada renglón del cuerpo el servidor toma SOLO `{codigo, cantidad}`; cualquier otro campo (`articulo`, `limite`, `tiene`, `excedente`, `regla`, `mensaje`, `autorizable`...) se ignora. Con su propia evaluación arma y guarda `{codigo, articulo_id, articulo, cantidad, limite, tiene, excedente, regla, mensaje, autorizable}`, que es lo que lee quien autoriza y lo que responden los `GET`. Un renglón que no sea naranja en esa evaluación (rojo: A-06; verde o amarillo: no necesita autorización) da 422 `RENGLON_NO_AUTORIZABLE` con `detalles: {codigo, regla, nivel, motivos}` y no se guarda nada. |
| `GET /api/autorizaciones/{id}` | Sesión | Estado de una solicitud, con renglones, quién la pidió y quién la resolvió. La ve quien la pidió y quien tiene `autorizaciones.resolver` en su almacén (con `almacenes.todos`, en todos); para los demás, 404. Si venció, responde `VENCIDA`. El solicitante la consulta cada tres segundos. |
| `GET /api/autorizaciones?estado=PENDIENTE` | `autorizaciones.resolver` | Solicitudes por resolver (`estado` por defecto `PENDIENTE`), con trabajador, renglones, `excedente_total`, motivo y quién la pide. Sin `almacenes.todos`, solo las de su almacén (AC-06). |
| `POST /api/autorizaciones/{id}/resolucion` | `autorizaciones.resolver` | `{decision}` desde la sesión de quien autoriza (medio REMOTA); o `{decision, usuario, pin}` desde el dispositivo del almacenista (medio PIN). `decision`: `APROBAR` o `RECHAZAR`. En el segundo caso la sesión es la del almacenista (`entregas.crear`) y el permiso `autorizaciones.resolver`, el almacén y el PIN se verifican sobre ese usuario. Errores: 403 `AUTORIZACION_PROPIA` (A-05), 403 `PIN_INCORRECTO`, 429 `DEMASIADOS_INTENTOS`, 409 `AUTORIZACION_RESUELTA`. |

La autorización aprobada se usa una sola vez (A-03) con `POST /api/vales` y `autorizacion_id`; el vale la valida y la marca usada en su misma transacción. Al solicitar, el servidor evalúa de verdad los renglones (la misma evaluación de la ENTREGA) y rechaza con 422 `RENGLON_NO_AUTORIZABLE` los que están en rojo, aunque quien los pide los marque `autorizable` (A-06, SM-04); `detalles` trae el `codigo`, la `regla` y los `motivos`.

## Solicitudes de compra

La solicitud de compra urgente (reglas SC-01 a SC-11, sección 7.13 de las [reglas](../product/reglas-de-negocio.md)). Todo va bajo `/api/solicitudes-compra`. Permisos: `compras.solicitar` (pedir y cancelar; de inicio Almacenista, Supervisor y Administrador) y `compras.atender` (hacer avanzar la solicitud; de inicio Compras y Administrador). Las dos lecturas aceptan cualquiera de los dos permisos: la columna dice «Solicitar o atender», el router solo exige sesión y el servicio verifica cualquiera de los dos (403 `SIN_PERMISO` si no tiene ninguno). El módulo no escribe inventario (SC-11).

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/solicitudes-compra` | `compras.solicitar` | Levanta una solicitud (SC-01, SC-02). Cuerpo abajo. 201 con la solicitud completa; 200 con la misma si el `id_cliente` ya existía con el mismo cuerpo (SC-10). El almacén sale del usuario; con `almacenes.todos` se indica `almacen_id`. Un almacén cerrado no recibe solicitudes nuevas: 409 `ALMACEN_CERRADO` (AL-04). |
| `GET /api/solicitudes-compra` | Solicitar o atender | Lista paginada (`{elementos, total}`) de lo que el usuario ve (SC-03): con `compras.atender` o `almacenes.todos`, las de todos los almacenes; si no, las de su almacén (y nada si no tiene almacén). Filtros: `estado`, `urgencia`, `almacen_id` (con alcance restringido, pedir otro almacén no devuelve nada), `q` (folio, descripción, nombre o código del artículo y motivo; sin distinguir mayúsculas ni acentos), `desde` y `hasta` (fechas de México, `AAAA-MM-DD`; el día `hasta` entra completo; un rango invertido da 422), `mias=true` (solo las que pidió el usuario), `pagina` y `tamano`. Con `solo_contar=true` responde `{"total": n}` con los mismos filtros, para el contador del menú (por ejemplo `estado=PENDIENTE`). Orden: primero PENDIENTE, luego EN_COMPRA, COMPRADA y al final lo cerrado; en cada grupo, URGENTE antes que NORMAL y las más antiguas primero (lo cerrado, la más reciente primero). |
| `GET /api/solicitudes-compra/{id}` | Solicitar o atender | El detalle: la solicitud y su línea de tiempo (`eventos`). Fuera del alcance del usuario, 404. |
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
  "ruta": {"habitual": true, "nivel": "VERDE", "pide_observacion": false, "mensaje": "Ruta habitual."},
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
| FEAT-002 | `GET /api/almacenes/{id}/reporte-cierre`, `GET /api/reportes/valor-inventario` (abrir y cerrar almacenes pasó a FEAT-008: ver [Almacenes y existencias](#almacenes-y-existencias)) | `almacenes.administrar`; `reportes.valor_inventario` |
| FEAT-008 | `POST`, `PATCH /api/almacenes`, `POST /api/almacenes/{id}/cierre` y `/reapertura`, `GET /api/almacenes?resumen=true`, `GET /api/tablero/resumen`, `GET /api/tablero/consumo`; `POST /api/trabajadores` sin `numero_empleado` | `almacenes.administrar`; `tablero.ver`; `trabajadores.administrar` |
| FEAT-003 | **Construido en el servidor** (ver [Puestos y dotación](#puestos-y-dotación)): `GET`, `PUT /api/puestos/{id}/dotacion`, `GET`, `POST`, `PATCH /api/puestos`, `GET /api/trabajadores/{id}/dotacion` | `catalogo.ver`; `catalogo.administrar`; `trabajadores.ver` |
| FEAT-004 | `PUT /api/almacenes/{id}/minimos`; `POST /api/piezas/{id}/estado` admite mantenimiento y calibración | `inventario.minimos`; `piezas.inspeccionar` |
