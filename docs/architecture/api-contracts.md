# Contratos de API

Endpoints, cuerpos, errores y permisos del MVP. Todo va bajo `/api`, en JSON, con la sesión en una cookie.

Estado: es el contrato acordado para construir. Si al implementar cambia, se actualiza aquí en el mismo cambio.

## Convenciones

- Los `id` son UUID en texto, por ejemplo `01a10a17-3a3b-74ed-89d0-2082afd9941a` ([ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). En los ejemplos se abrevian.
- Las fechas van en ISO 8601; las horas, en UTC.
- Las listas admiten `pagina` y `tamano` y responden `{elementos, total}`.
- Cada endpoint exige un **permiso**; la columna "Permiso" da su clave ([ADR-007](decisions/ADR-007-permisos-por-clave.md)). Qué roles lo tienen de inicio está en la sección 8.2 de las [reglas](../product/reglas-de-negocio.md). "Sesión" significa que basta haber entrado. Ocho rutas (las que dicen "Sesión", "Según el tipo" o "Solicitar o atender" en la columna Permiso) solo exigen sesión en el router y verifican el permiso en el servicio, porque depende del tipo de vale o del usuario, o porque aceptan uno de dos permisos: `POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}`, `POST /api/autorizaciones/{id}/resolucion`, `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}` (`compras.solicitar` o `compras.atender`); sin el permiso responden 403 `SIN_PERMISO` igual que las demás.
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
| 409 | `ROL_PROTEGIDO` | El rol Administrador no pierde `acceso.administrar`, no se inactiva ni se elimina; los cinco roles iniciales no se eliminan ni cambian de nombre (AC-09). |
| 409 | `ROL_EN_USO` | Un rol con usuarios asignados no se inactiva ni se elimina (AC-11). |
| 409 | `AUTO_BLOQUEO` | Quien administra intenta quitarle `acceso.administrar` a su propio rol o inactivarlo (AC-09). |
| 409 | `CODIGO_REPETIDO` | El código ya identifica otra cosa. Incluye en `detalles` su `tipo`, su `ref_id` y una `descripcion` de quién es. |
| 409 | `TRABAJADOR_EXISTE` | Al dar de alta, el número de empleado o la CURP ya existen (T-02). Incluye en `detalles.trabajador` a la persona (`id`, `numero_empleado`, `nombre`, `estado`) y en `detalles.coincide_por` el dato que coincidió, para ofrecer el reingreso. Si coincidió la CURP y quien da de alta no tiene `trabajadores.ver_datos_personales`, solo dice que ya existe (`detalles` solo trae `regla`), sin `coincide_por` ni la persona (AC-05). |
| 409 | `CON_PENDIENTES` | No se puede emitir el vale de no adeudo. `detalles` trae `{regla: "B-04", pendientes}`: cada pendiente con `articulo`, `codigo`, `numero_serie`, `cantidad`, `entregado_en`, `folio` y almacén (`almacen_clave`, `almacen`); sin costos. |
| 409 | `CON_MOVIMIENTOS` | No se puede eliminar ni cambiar control o retorno. |
| 409 | `NO_CANCELABLE` | El vale no se puede cancelar (K-03, K-04, X-14). `mensaje` explica por qué en español llano y `detalles` trae, por cada motivo, `{regla, mensaje}` (y `renglon` y `codigo` si es de un renglón). No se escribe nada. |
| 409 | `TRANSICION_INVALIDA` | La solicitud de compra no puede pasar a ese estado desde el que tiene (SC-04). `detalles`: `{regla, estado_actual, estado_pedido, estados_permitidos}`. |
| 409 | `ID_CLIENTE_EN_USO` | El `id_cliente` de una solicitud de compra ya se usó con otro cuerpo o por otro usuario (SC-10). |
| 403 | `AUTORIZACION_PROPIA` | Quien pidió la autorización intenta autorizarla (A-05, AC-07). |
| 409 | `AUTORIZACION_RESUELTA` | La solicitud ya se resolvió o venció; no se resuelve de nuevo. |
| 409 | `AUTORIZACION_INVALIDA` | La autorización no sirve para este vale: no está aprobada, venció, ya se usó, es de otro almacén o trabajador, o no cubre los renglones ni la cantidad (A-03). |
| 403 | `AJUSTE_PROPIO` | Quien registró la inspección intenta ajustar su vigencia (P-07). |
| 409 | `AJUSTE_NO_PERMITIDO` | La pieza está No apta o no tiene inspección Apta: no hay vigencia que ajustar (P-07). |
| 422 | `VIGENCIA_EXCEDIDA` | La fecha pasa de la inspección más la vigencia del artículo (P-07). |
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
| `GET /api/usuarios?q=&rol_id=&almacen_id=&sin_almacen=&activo=` | `acceso.administrar` | `{elementos, total}`: lo del personal más `tiene_pin` y `creado_en`; sin límite de roles. |
| `GET /api/usuarios/{id}` | `acceso.administrar` | Un usuario. |
| `POST /api/usuarios` | `acceso.administrar` | Alta con `{nombre, usuario, contrasena, rol_id, almacen_id, pin}`. `almacen_id` es obligatorio si el rol no tiene `almacenes.todos` y va vacío si lo tiene (RG-07). `pin` (4 a 8 dígitos, distinto de la contraseña) solo si el rol tiene `autorizaciones.resolver`. Responde 201. 409 `USUARIO_EXISTE`. |
| `PATCH /api/usuarios/{id}` | `acceso.administrar` | Solo `nombre`, `rol_id`, `activo` y `almacen_id`; cualquier otro campo es 422. Cambiar a un rol con `almacenes.todos` quita el almacén; volver a uno que no lo tiene exige indicarlo. 409 `ULTIMO_ADMINISTRADOR` (AC-09). |
| `POST /api/usuarios/{id}/contrasena` | `acceso.administrar` | `{contrasena, pin}` (`pin` opcional). Restablece la contraseña y, si se manda, el PIN, y reinicia los bloqueos. |

## Roles y permisos

Parte de [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md) (AC-08 a AC-11). Todo pide `acceso.administrar`. Un cambio aplica en la siguiente petición de los usuarios del rol (el rol y sus permisos se leen de la base en cada petición) y queda en el registro de cambios con el valor anterior y el nuevo.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/permisos` | `acceso.administrar` | El catálogo fijo de permisos: `[{clave, descripcion, modulo, es_de_informacion, mvp, llega_con, requiere: [claves]}]`. `modulo` es la parte de la clave antes del punto. `requiere` lista los permisos de ver que ese permiso de acción necesita (la interfaz los activa juntos). `es_de_informacion` marca los datos reservados (costos, CURP y NSS). El catálogo no se edita desde la pantalla (AC-01). |
| `GET /api/roles` | `acceso.administrar` | `[{id, nombre, descripcion, activo, protegido, inicial, total_usuarios, total_permisos, permisos: [claves]}]`. `inicial` marca los cinco roles con los que nace el sistema; `protegido`, al Administrador. |
| `GET /api/roles/{id}` | `acceso.administrar` | Un rol, con la misma forma. 404 si no existe. |
| `POST /api/roles` | `acceso.administrar` | `{nombre, descripcion, permisos: [claves]}` (`permisos` puede ir vacío: un rol sin permisos no ve ningún módulo). Responde 201 con el detalle. 409 `ROL_EXISTE` si el nombre ya se usa; 422 si una clave no existe o falta un permiso de ver que necesita otro. |
| `PATCH /api/roles/{id}` | `acceso.administrar` | Solo `nombre`, `descripcion` y `activo`; otro campo es 422. Los roles iniciales no cambian de nombre (409 `ROL_PROTEGIDO`). Inactivar: 409 `ROL_PROTEGIDO` si es el Administrador y 409 `ROL_EN_USO` si tiene usuarios asignados (AC-11). 409 `AUTO_BLOQUEO` si inactivaría el rol del propio actor con `acceso.administrar`. |
| `PUT /api/roles/{id}/permisos` | `acceso.administrar` | `{permisos: [claves]}`: deja al rol exactamente con esa lista (agrega y quita la diferencia). Responde el detalle. 422 si una clave no existe o falta un permiso de ver. Quitar `acceso.administrar`: 409 `ROL_PROTEGIDO` si es el Administrador, 409 `AUTO_BLOQUEO` si es el rol de quien lo hace, 409 `ULTIMO_ADMINISTRADOR` si no quedaría un administrador activo (AC-09). Si el rol recibe `almacenes.todos`, sus usuarios dejan el almacén asignado (RG-07) y cada uno queda en el registro de cambios; si lo pierde, sus usuarios quedan sin almacén hasta que alguien con `almacenes.asignar_personal` se lo asigne. |
| `DELETE /api/roles/{id}` | `acceso.administrar` | Responde 204. 409 `ROL_PROTEGIDO` si es el Administrador o uno de los cinco iniciales; 409 `ROL_EN_USO` si tiene usuarios, aunque estén inactivos (AC-11). |

## Escaneo y búsqueda

Responden solo lo que el usuario puede ver: trabajadores con `trabajadores.ver`, artículos y piezas con `catalogo.ver`, y vales con `vales.ver`.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/escaneo/{codigo}` | Sesión | Identifica un código: `{tipo, id, resumen}`. `tipo`: TRABAJADOR, ARTICULO, PIEZA, VALE o DESCONOCIDO. Lo que el usuario no puede ver llega como DESCONOCIDO (`id` en `null`); un vale solo se identifica dentro del alcance del usuario (AC-06): su almacén es el de origen o el de destino de un traspaso, o tiene `almacenes.todos` (la misma regla que `GET /api/vales/{id}`). Lo mismo vale para una pieza: sin `almacenes.todos` solo se identifica la que está en su almacén, la que tiene un trabajador (con `trabajadores.ver`) o la que va en tránsito desde o hacia su almacén; cualquier otra es DESCONOCIDO, idéntica a un código que no existe. En un artículo, `existencia_total` es lo que hay en el almacén del usuario (todos los almacenes, solo con `almacenes.todos`; 0 sin almacén asignado). Reconoce el código de una credencial, artículo o pieza, el QR (token) o el folio de un vale y el número de empleado tecleado. `resumen` es breve y nunca trae costos, CURP ni NSS. |
| `GET /api/busqueda?q=` | Sesión | Coincidencias en artículos (nombre o código), piezas (serie, código o nombre del artículo, con quién las tiene) y trabajadores (nombre o número). Responde `{q, articulos, piezas, trabajadores, sin_resultados, mensaje}`; cada grupo es `{elementos, total}` y admite `pagina` y `tamano`. Un grupo sin permiso llega vacío. Menos de dos caracteres no busca y lo dice en `mensaje`. Los artículos son catálogo y se ven siempre; las piezas se limitan al alcance del usuario como en el escaneo (AC-06). |

## Trabajadores

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/trabajadores` | `trabajadores.ver` | Lista con vigencia y situación (cada elemento trae `puesto` y `puesto_id`). Filtros: `q` (parte del nombre o del número) y `situacion` (`SIN_PENDIENTES`, `CON_PENDIENTES`, `NO_ADEUDO_EMITIDO`). Nunca trae CURP ni NSS. |
| `POST /api/trabajadores` | `trabajadores.administrar` | Alta (T-03): `{nombre, numero_empleado, area_obra, inicio, fin}`, el puesto como `puesto_id` (del catálogo) o como texto `puesto` (al menos uno; con los dos manda `puesto_id`) y opcionales `{referencia, tallas, curp, nss}`. Con `puesto_id`, el texto del periodo queda con el nombre del puesto; un `puesto_id` que no existe o está inactivo es 422 (`detalles.campo = "puesto_id"`). Con solo texto se busca el puesto por nombre (sin importar mayúsculas ni acentos): si existe se liga y, si no, el periodo queda sin `puesto_id` (sin dotación). Responde 201 con la ficha. Si el número o la CURP ya existen responde 409 `TRABAJADOR_EXISTE` con la persona, para ofrecer el reingreso. Fin anterior a inicio: 422 con `detalles.campo = "fin"`. |
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
| `POST /api/categorias`, `PATCH /api/categorias/{id}` | `catalogo.administrar` | Crea (201) o edita una categoría y su plantilla (CF-01, CF-02). El nombre no se repite (409). Una plantilla con inspección en control por cantidad se rechaza (422, CF-06). Editar la plantilla no cambia los artículos que ya existen. |
| `GET /api/articulos` | `catalogo.ver` | Lista. Filtros: `q` (nombre, código, marca o modelo), `categoria_id`, `activo`; sin `activo` trae activos e inactivos, y la pantalla manda `activo=true` por defecto (CF-10). `costo_unitario` solo con `catalogo.costos`: sin el permiso la clave no aparece. |
| `POST /api/articulos` | `catalogo.administrar` | Crea (201) un artículo; control, retorno y reglas salen de la plantilla de su categoría si no se indican (un campo de regla en `null` significa "sin esa regla"). El código no puede repetir el de ningún artículo, pieza o credencial (409 `CODIGO_REPETIDO`) y queda registrado como su QR de producto o de estante (I-07). El costo solo se acepta con `catalogo.costos`; sin él, 403. |
| `GET /api/articulos/{id}` | `catalogo.ver` | Ficha: reglas, `tiene_movimientos` (control y retorno bloqueados), `existencias` por almacén (`cantidad` y `disponible`, que no cuenta piezas No aptas, en mantenimiento ni en calibración) y `en_posesion` (quién lo tiene, con su cantidad) (C-03). Sin `almacenes.todos`, `existencias` trae solo el almacén del usuario (AC-06); `en_posesion` es el resguardo de los trabajadores y se ve completo. El costo, solo con `catalogo.costos`. |
| `PATCH /api/articulos/{id}` | `catalogo.administrar` | Edita datos, límite, aviso de cantidad inusual y requisitos; solo cambia lo que viene (omitido no es `null`). No cambia el código ni la inactivación (422 si se envían). Rechaza cambios de control o retorno con movimientos (409 `CON_MOVIMIENTOS`, CF-05). Activar la inspección deja sus piezas sin inspección vigente (CF-09). Cambiar el costo pide `catalogo.costos`. |
| `POST /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Inactiva con `{motivo}` (CF-10). Responde el artículo. 409 si ya estaba inactivo. |
| `DELETE /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Reactiva (CF-13). Responde el artículo. 409 si ya estaba activo. |
| `DELETE /api/articulos/{id}` | `catalogo.administrar` | Elimina solo si no tiene movimientos (CF-12); responde 204, o 409 `CON_MOVIMIENTOS`. Libera su código. |
| `GET /api/piezas/{id}` | `catalogo.ver` | Ficha (C-02): artículo, estado, `inspeccion_vigente_hasta` e `inspeccion_vigente`, `ultima_inspeccion`, `ubicacion` (almacén, trabajador o virtual) e `historial`: movimientos, inspecciones, cambios de estado y ajustes de vigencia en una sola lista, del más reciente al más antiguo (`tipo`, `fecha` UTC, `titulo`, `detalle`, `usuario` y los campos propios de cada tipo). Sin costos. Sin `almacenes.todos`, una pieza fuera del alcance (no está en su almacén, ni la tiene un trabajador, ni va en tránsito desde o hacia él) responde 404 `NO_ENCONTRADO`, igual que una que no existe; de su historial, los movimientos de un vale de otro almacén solo se muestran si pasan por un trabajador, con el almacén como «Otro almacén» y sin `folio`, `vale_id` ni responsable (AC-06). |
| `POST /api/piezas/{id}/inspecciones` | `piezas.inspeccionar` | Registra una inspección (P-01) con `{resultado, puntos?, observacion?}`; `puntos` admite `etiquetas`, `costuras`, `cintas`, `herrajes` y `conectores` (booleanos). Responde 201 con la inspección y `pieza: {id, estado, inspeccion_vigente_hasta}`. Apto deja la pieza Apta y vigente hasta hoy más la vigencia de su artículo; No apto exige observación (422) y la deja No apta. Sirve para cualquier pieza de su almacén, también la que está con un trabajador (es del almacén de su última entrega); sin `almacenes.todos`, una pieza de otro almacén da 404 (AC-06, H11); una en baja da 409. |
| `POST /api/piezas/{id}/estado` | `piezas.inspeccionar` | Marca No apta con `{estado: "NO_APTO", observacion}` (P-03); la observación es obligatoria (422). Responde 200 con `{evento_id, estado_anterior, pieza}`. Si ya está No apta o en baja, 409. |
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
| `GET /api/almacenes` | `inventario.ver` | Lista con su red: `{id, clave, nombre, tipo, estado, padre_id, padre_clave, hijos: [{id, clave, nombre}]}`. |
| `GET /api/almacenes/{id}/existencias` | `inventario.ver` | `{almacen, elementos, total}`: por artículo con existencia, `cantidad` y `disponible` (en piezas, solo las Aptas; I-05), con `activo` para marcar los inactivos (CF-11). Filtros: `q`, `categoria_id`, `activo`; admite `pagina` y `tamano`. Sin costos. Sin `almacenes.todos`, solo el almacén asignado: otro responde 404 `NO_ENCONTRADO`, igual que uno que no existe (AC-06). |

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
| `GET /api/traspasos/por-recibir?solo_contar=&almacen_id=` | `traspasos.operar` | Traspasos con algo En tránsito (estado `EN_TRANSITO` o `RECIBIDO_CON_DIFERENCIAS`) hacia el almacén de la sesión, del más antiguo al más nuevo, con sus renglones y lo ya recibido (forma abajo). Sin `almacenes.todos`, solo los del almacén asignado (un `almacen_id` distinto es 409 `ALMACEN_CAMBIO`); con él, `almacen_id` filtra y sin él trae los de todos los almacenes. Con `solo_contar=true` responde solo `{"total": n}`: es la consulta ligera del contador del inicio (cada 30 s). |
| `POST /api/trabajadores/{id}/no-adeudo` | `no_adeudo.emitir` | Emite el vale de no adeudo (B-04). Cuerpo `{id_cliente, observacion, almacen_id}`; `almacen_id` solo lo indica quien tiene `almacenes.todos` (AC-06). Si el trabajador está Activo, inicia su baja (B-01: queda en Baja en proceso, aunque después responda 409) y para eso exige además `trabajadores.iniciar_baja` (403 si falta; con la baja ya en proceso no se pide). Responde 409 `CON_PENDIENTES` con la lista si los hay; 409 si el trabajador ya está Inactivo. Sin pendientes responde 201 con `{id, folio, token, creado_en, renglones: [], trabajador: {id, numero_empleado, nombre, estado, estado_texto}}` (folio `…-NAD-…`, el trabajador queda Inactivo, B-08; `renglones` va vacío); 200 con el mismo cuerpo si el `id_cliente` ya existía. |
| `POST /api/vales/{id}/cancelacion` | `vales.cancelar` | Cancela con `{motivo, id_cliente, rehacer}` y genera los movimientos inversos (K-01 a K-04). Con `rehacer: true` la respuesta trae además un `borrador` con los renglones del vale original, sin firma ni autorización, para corregirlos y confirmar de nuevo (K-05). Con `vales.cancelar` solo los propios; con `vales.cancelar_todos`, los de cualquiera. Responde 409 `NO_CANCELABLE` si no procede. Forma exacta abajo, en "Cancelación". |

Permiso y campos propios de cada tipo. El permiso se verifica por clave, según el `tipo` del cuerpo, antes de leer nada (403 `SIN_PERMISO`):

| Tipo | Permiso | Campos propios |
|---|---|---|
| ENTRADA | `inventario.entradas` | `almacen_id` (o `destino_almacen_id`; sin él, quien opera todos los almacenes entra por Kepler, I-01); en artículos por pieza, cada renglón lleva `pieza: {codigo, numero_serie, inspeccion: {fecha, resultado, observacion}}` (la inspección inicial es opcional, I-03). No acepta `trabajador_id` ni costos (el cuerpo rechaza campos desconocidos con 422). Firma de sesión (F-03). |
| ENTREGA | `entregas.crear` | `trabajador_id`; `firma` con `modo: "PANTALLA"` e `imagen` (F-02); `condicion` por renglón (`BUENO` por defecto, E-22). `almacen_id` solo para quien tiene `almacenes.todos`. |
| DEVOLUCION | `devoluciones.crear` | `condicion` por renglón (obligatoria, V-04); `observacion` obligatoria si es `DANADO` (V-05); `foto` opcional por renglón `DANADO` (`data:image/…;base64,…`, se guarda como adjunto `FOTO_DANO` ligado al movimiento); `trabajador_id` solo hace falta en renglones por cantidad (una pieza se abona a su titular). Sin firma: firma el almacenista con su sesión (F-08). |
| NO_ADEUDO | `no_adeudo.emitir` | `trabajador_id`; sin renglones. Lo usual es `POST /api/trabajadores/{id}/no-adeudo`; por `POST /api/vales` con pendientes responde 409 `VALE_CAMBIO` con el motivo `B-04`. |
| TRASPASO | `traspasos.operar` | `destino_almacen_id` (obligatorio); renglones por código de pieza, o de artículo con `cantidad`. Sin `trabajador_id`, `vale_origen_id`, `pieza` ni costos (422). Firma de sesión (F-09): no lleva `firma`. El vale queda `EN_TRANSITO`, folio `CLAVE-TRS-000001`. `almacen_id` solo para quien tiene `almacenes.todos`. `evaluar` trae en `motivos` del vale la regla X-03 (verde, amarillo o rojo) y por renglón X-02, X-04, X-09. |
| RECEPCION | `traspasos.operar` | `vale_origen_id` (el traspaso, obligatorio); `renglones`: lo escaneado, por código de pieza o de artículo con `cantidad` (para recibir todo, todos los pendientes de `por-recibir`; sin renglones, 422). Sin `trabajador_id` ni `destino_almacen_id` (422). Firma de sesión (F-09). Folio `CLAVE-REC-000001` del almacén que recibe; al confirmar, el traspaso queda `RECIBIDO` o `RECIBIDO_CON_DIFERENCIAS` (X-13). `evaluar`: X-10 (vale y renglones, rojo), X-12 (renglón, rojo), X-13 (vale, amarillo) y, si la recepción deja algo pendiente sin `observacion` (vacía o en blanco), RG-14 (vale, rojo). Al confirmar esa recepción sin observación responde 422 con `detalles: [{campo: "observacion", mensaje, regla: "RG-14"}]` y no guarda nada; la recepción que completa lo pendiente no la pide. Un `vale_origen_id` inexistente es 404 y el de un vale que no es traspaso, 422. |
| CANCELACION | `vales.cancelar` | `vale_origen_id` (el vale que se cancela) y `observacion` (el motivo); sin renglones: salen de los del original. Normalmente se usa `POST /api/vales/{id}/cancelacion`; `POST /api/vales` con este tipo hace lo mismo. |

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
| `POST /api/solicitudes-compra` | `compras.solicitar` | Levanta una solicitud (SC-01, SC-02). Cuerpo abajo. 201 con la solicitud completa; 200 con la misma si el `id_cliente` ya existía con el mismo cuerpo (SC-10). El almacén sale del usuario; con `almacenes.todos` se indica `almacen_id`. |
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
- `vale_entrada` es `{id, folio}` o `null`; solo lo tiene una solicitud INGRESADA a la que Compras ligó un vale (SC-06).
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

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/importacion/vista-previa` | `inventario.entradas` | Recibe `{filas, columnas}` y devuelve filas válidas, filas con error y artículos que se crearían. No escribe. |
| `POST /api/importacion/archivo` | `inventario.entradas` | Recibe un `.xlsx` (multipart, campo `archivo`), lo convierte en las mismas filas y responde `{hoja, encabezados, columnas, primera_fila, filas, vista_previa}`. No escribe ni guarda el archivo. |
| `POST /api/importacion` | `inventario.entradas` | Confirma: crea artículos faltantes y un vale de entrada por almacén. 201; con un `id_lote` ya confirmado, 200 con `repetida: true`. |

La tabla se lee en el navegador (pegada desde Excel, o un `.xlsx` leído allá); al servidor llegan filas ya separadas en columnas. Con `POST /archivo` el servidor lee el `.xlsx` y devuelve las filas ya separadas para reenviarlas a los otros dos endpoints.

**Cuerpo** (vista previa y confirmación):

```json
{
  "filas": [["MART-01", "Martillo", "Truper", "Herramienta manual", "12", "Kepler", "", "85.50", ""]],
  "columnas": {"codigo": 0, "nombre": 1, "marca": 2, "categoria": 3, "cantidad": 4,
               "almacen": 5, "serie": 6, "costo": 7, "codigo_pieza": 8},
  "primera_fila": 2,
  "categoria_por_defecto_id": null,
  "mapa_categorias": {"Cosas raras": "<categoria_id>"},
  "almacen_por_defecto": null,
  "id_lote": "<uuid>"
}
```

- `filas` son solo las de datos (máximo 5 000, 30 columnas, 500 caracteres por celda); cada celda es texto, número o vacía. `columnas` da el índice (desde 0) de cada dato; solo `codigo` es obligatorio y una columna no puede ser dos datos. Sin `columnas`, se acepta `encabezados` (el nombre de cada columna) y el servidor las propone; sin la del código, 422. `codigo` es el del artículo; `codigo_pieza`, el de cada pieza en artículos por pieza.
- `primera_fila` es el número que tiene la primera fila de `filas` en la hoja (2 si la hoja traía encabezados; por defecto 1): los errores se reportan con ese número.
- `categoria_por_defecto_id` y `mapa_categorias` ({nombre de categoría en el archivo: `categoria_id`}) dan la categoría de los artículos nuevos cuya categoría no existe o viene vacía. Una categoría elegida que no existe o está inactiva da 422. `almacen_por_defecto` (clave o nombre) es el almacén de las filas sin almacén; sin él, Kepler (o el almacén asignado si no se tiene `almacenes.todos`).
- `id_lote` (UUID del cliente) es obligatorio al confirmar y se ignora en la vista previa.

**Reglas que revisa el servidor en cada fila** (la misma revisión en la vista previa y al confirmar; cada motivo lleva el ID de su regla):

| Regla | Qué rechaza |
|---|---|
| I-06 | Falta el código o el nombre (de un artículo nuevo); un dato pasa del largo permitido. |
| I-01 | Cantidad vacía, no entera o ≤ 0 (en artículos por cantidad); almacén desconocido, cerrado o vacío sin almacén por defecto. |
| AC-06 | Sin `almacenes.todos`, un almacén que no es el asignado. |
| CF-02 | Categoría desconocida o vacía en un artículo nuevo (`CATEGORIA_DESCONOCIDA`): se elige una con `categoria_por_defecto_id` o `mapa_categorias`. El artículo nuevo copia la plantilla de su categoría. |
| I-09 | Artículo inactivo. |
| RG-10 | Código de artículo que ya identifica una pieza, un trabajador o un vale; el mismo artículo por cantidad dos veces en el mismo almacén de la tabla (otro almacén es otra fila); código de pieza igual al de un artículo. |
| I-02 | Pieza sin código de pieza o sin número de serie; código de pieza ya usado (en la base o antes en la tabla); serie repetida del mismo artículo. Cada fila de un artículo por pieza es una pieza (cantidad 1). Sin inspección inicial la pieza entra pendiente (I-03, se avisa). |
| RG-05 | Una pieza con cantidad distinta de 1. |
| I-04 / RG-12 | Con `catalogo.costos`: un costo inválido (no es un número ≥ 0) rechaza la fila; el costo solo se guarda en artículos nuevos (en uno que ya existe se avisa que no cambia). Sin `catalogo.costos`: la columna de costo se ignora con un aviso, las filas entran y el costo nunca vuelve en las respuestas (ni en `datos` de una fila con error). Ningún vale lleva costos. |

Las filas vacías se ignoran (cuentan en `vacias`). Un artículo que ya existe solo recibe la entrada (su nombre, marca y categoría del archivo no lo cambian). Las filas con error no se importan y se listan con su motivo; las buenas sí entran.

**Respuesta de la vista previa** (200):

```json
{
  "columnas": {"codigo": 0, "nombre": 1, "...": null},
  "avisos": ["Se ignoró la columna de costo: no tienes permiso para capturar costos."],
  "resumen": {"total": 4, "validas": 3, "con_error": 1, "vacias": 0,
              "articulos_nuevos": 2, "piezas": 1, "unidades": 15, "almacenes": 2},
  "filas_validas": [{"fila": 2, "codigo": "MART-01", "nombre": "Martillo", "marca": "Truper",
                     "categoria": {"id": "...", "nombre": "Herramienta manual"},
                     "control": "CANTIDAD", "articulo_nuevo": true, "cantidad": 12,
                     "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"},
                     "codigo_pieza": null, "numero_serie": null,
                     "costo": "85.50", "avisos": []}],
  "filas_error": [{"fila": 3, "datos": {"codigo": "X", "cantidad": "mucho", "...": ""},
                   "motivos": [{"regla": "I-01", "campo": "cantidad",
                                "codigo": "CANTIDAD_INVALIDA", "mensaje": "..."}]}],
  "articulos_nuevos": [{"codigo": "MART-01", "nombre": "Martillo", "marca": "Truper",
                        "categoria": {"id": "...", "nombre": "..."}, "control": "CANTIDAD",
                        "filas": 1, "costo": "85.50"}],
  "categorias_desconocidas": [{"nombre": "Cosas raras", "filas": [3, 5]}]
}
```

`costo` (en filas válidas y artículos nuevos) solo aparece con `catalogo.costos` y si la fila lo trae. `codigo` de los motivos: `FALTA_CODIGO`, `FALTA_NOMBRE`, `CODIGO_REPETIDO`, `ARTICULO_REPETIDO`, `ARTICULO_INACTIVO`, `CATEGORIA_DESCONOCIDA`, `ALMACEN_DESCONOCIDO`, `ALMACEN_CERRADO`, `ALMACEN_AJENO`, `FALTA_ALMACEN`, `FALTA_CANTIDAD`, `CANTIDAD_INVALIDA`, `FALTA_CODIGO_PIEZA`, `FALTA_SERIE`, `SERIE_REPETIDA`, `COSTO_INVALIDO`, `DEMASIADO_LARGO`.

**Respuesta de `POST /archivo`** (200): `{hoja, encabezados, columnas, primera_fila, filas, vista_previa}`. `filas` son las de datos (texto, ya separadas en columnas); `columnas` es la relación propuesta por el nombre de cada encabezado (sin acentos ni mayúsculas); `vista_previa` es la de arriba, o `null` si no se encontró la columna del código. El archivo se lee en memoria: solo `.xlsx` sin macros (se rechazan `.xlsm`, `.xls`, `.csv` y lo que no sea un `.xlsx` válido por su contenido), hasta 5 MB, 5 000 filas, 30 columnas, 500 caracteres por celda y 50 MB descomprimido (zip bomb). Una fórmula nunca se ejecuta: se lee el último valor que Excel guardó (o queda vacía). Un archivo malo da 422 `DATOS_INVALIDOS` con un mensaje en español, nunca un 500. Se lee la primera hoja; las filas vacías de arriba se saltan (el primer renglón con datos son los encabezados).

**Confirmación** (`POST /api/importacion`). Crea con `CatalogoService` los artículos que faltan y, con el motor de movimientos, **un vale de ENTRADA por almacén** (un almacén con más de 500 renglones se parte en vales de 500). Todo en una sola transacción: si falla cualquier entrada no se guarda nada (RG-09) y el error es el del motor (por ejemplo 409 `VALE_CAMBIO`) o 409 si algo cambió desde la vista previa. Los folios salen del contador del almacén (RG-06). Las filas con error no se importan. Sin ninguna fila válida: 422 con `detalles.filas_error`.

```json
{
  "id_lote": "<uuid>", "repetida": false,
  "resumen": {"filas_importadas": 3, "filas_con_error": 1, "articulos_creados": 2,
              "vales": 2, "piezas": 1, "unidades": 15},
  "articulos_creados": [{"id": "...", "codigo": "MART-01", "nombre": "Martillo",
                         "categoria": "Herramienta manual", "control": "CANTIDAD"}],
  "vales": [{"id": "...", "folio": "KEP-ING-000012",
             "almacen": {"id": "...", "clave": "KEP", "nombre": "Kepler"},
             "renglones": 2, "piezas": 0, "unidades": 14}],
  "filas_error": [],
  "avisos": []
}
```

`filas_error` tiene la misma forma que en la vista previa. **Idempotencia:** el `id_cliente` de cada vale es determinista por (`id_lote`, almacén, parte). Confirmar de nuevo el mismo `id_lote` responde **200** con `repetida: true`, los mismos vales (con sus folios) y `articulos_creados: []`, sin crear nada; el `id_lote` de otra persona da 409. Un lote nuevo con las mismas filas no duplica artículos (los existentes solo reciben otra entrada) y rechaza como error las piezas cuyo código o serie ya existen. La interfaz genera un `id_lote` por importación y lo reutiliza si el usuario reintenta. Cada confirmación deja un renglón de auditoría `importacion.confirmar`.

## Reportes

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/reportes/existencias` | `reportes.existencias` | Por almacén y artículo. Filtros: `almacen_id`, `categoria_id`. |
| `GET /api/reportes/movimientos` | `reportes.movimientos` | Bitácora. Filtros: fechas, almacén, tipo, trabajador, artículo y `usuario_id` (quien hizo el vale, C-11). Sin `almacenes.todos`, solo el almacén asignado, también al filtrar por usuario; con él, todos los almacenes y usuarios. |
| `GET /api/reportes/usuarios` | `reportes.movimientos` | Quién ha hecho vales, para el filtro «quién lo hizo» de la bitácora: `{elementos: [{id, nombre, usuario}]}`. Con `almacenes.todos`, de todos los almacenes; sin él, solo de su almacén (AC-06, C-11). |
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
| `GET /api/seguimiento/piezas` | `reportes.existencias` | Seguimiento de piezas (C-13): todas las piezas dentro del alcance del usuario, cada una con dónde está o quién la tiene, desde cuándo y con qué vale. Filtros: `q`, `articulo_id`, `almacen_id`, `estado`, `ubicacion`, `pagina`, `tamano` y `formato=csv`. Solo lee. |

- **Filtros.** `q` busca por nombre o código del artículo, número de serie, código de la pieza y nombre o número del trabajador que la tiene; varias palabras deben coincidir todas, y con menos de dos caracteres no busca (lista vacía y `mensaje` "Escribe al menos dos caracteres para buscar."). `estado`: `APTO`, `NO_APTO`, `EN_MANTENIMIENTO`, `EN_CALIBRACION` o `BAJA`. `ubicacion`: `ALMACEN`, `TRABAJADOR`, `TRANSITO` o `BAJA`. `almacen_id` deja las piezas que están en ese almacén, las que tiene un trabajador por un vale de ese almacén y las que van en tránsito desde o hacia él. Un valor inválido responde 422 `DATOS_INVALIDOS`.
- **Alcance (AC-06, C-02).** Con `almacenes.todos`, todas las piezas. Sin él, solo las del almacén asignado, las que tiene un trabajador (si el rol tiene `trabajadores.ver`) y el tránsito desde o hacia su almacén; pedir el `almacen_id` de otro no devuelve nada (no es error), y sin almacén asignado ni `almacenes.todos` tampoco. `vale` es `null` cuando el vale es de un almacén fuera del alcance. Nunca lleva costos, CURP ni NSS (RG-12, RG-13).
- **Respuesta.** `{elementos, total, sin_registros, mensaje, resumen}`, ordenada por artículo y código de pieza. `resumen` = `{total, en_almacen, en_resguardo, en_transito, no_aptas}` cuenta las piezas del alcance con el texto, el artículo y el almacén del filtro, **sin** aplicar `estado` ni `ubicacion`, para que las tarjetas de la pantalla cambien entre ellos. Cada elemento:

```json
{
  "id": "0192...",
  "codigo": "HER-001",
  "numero_serie": "MP-2041",
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

  `ubicacion.tipo` es `ALMACEN` (`almacen` es el almacén; texto "En Kepler"), `TRABAJADOR` (`trabajador` es quien la tiene), `TRANSITO` (`almacen` es el almacén al que va; texto "En tránsito a Contratistas"), `BAJA` ("De baja"), `OTRA` o `NINGUNA` (sin ubicación todavía). `desde` (UTC) es el movimiento que la dejó en esa ubicación; con un trabajador, su entrega más reciente, porque una cancelación que se la regresa no cambia desde cuándo la tiene. `vale` es el vale de ese movimiento.
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
| FEAT-002 | `POST /api/almacenes`, `POST /api/almacenes/{id}/cierre`, `GET /api/almacenes/{id}/reporte-cierre`, `GET /api/reportes/valor-inventario` | `almacenes.administrar`; `reportes.valor_inventario` |
| FEAT-003 | **Construido en el servidor** (ver [Puestos y dotación](#puestos-y-dotación)): `GET`, `PUT /api/puestos/{id}/dotacion`, `GET`, `POST`, `PATCH /api/puestos`, `GET /api/trabajadores/{id}/dotacion` | `catalogo.ver`; `catalogo.administrar`; `trabajadores.ver` |
| FEAT-004 | `PUT /api/almacenes/{id}/minimos`; `POST /api/piezas/{id}/estado` admite mantenimiento y calibración | `inventario.minimos`; `piezas.inspeccionar` |
