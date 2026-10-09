# Modelo de seguridad

> Estado Android del 8 de octubre de 2026: existe el contenedor en línea con SPA local y API HTTPS fija. El complemento HTTP nativo conserva cookies en Android y elimina Set-Cookie de respuestas entregadas a JavaScript; CapacitorCookies y el registro del puente están desactivados. Fotos y firmas protegidas pasan por el cliente autenticado. Las exportaciones quedan en caché privada y se limpian al abrir o compartir si tienen más de una hora; las copias recibidas por otras aplicaciones quedan bajo su control. La prueba real de entrada, renovación, cierre/revocación, document.cookie, respuestas del puente y FormData sigue pendiente. Las medidas de SQLite cifrada, PIN local, revocación de equipos y cola descritas en la iteración son diseño futuro. El APK debug requiere firma de publicación para distribuir en producción.


Quién puede hacer qué, qué puede salir mal y con qué se controla. Es también el entregable del PDF "controles de acceso".

## Actores

| Actor | Confianza |
|---|---|
| Almacenista | Opera su almacén. Puede equivocarse o coludirse con un trabajador. |
| Supervisor | Autoriza excepciones y administra el catálogo. |
| Compras | Ve costos y carga inventario. |
| RH | Ve datos personales. |
| Administrador | Tiene todos los permisos y es el único que ve todos los almacenes. Administra usuarios, roles y permisos desde las pantallas Usuarios y Roles y permisos (FEAT-006). |
| Trabajador | No tiene cuenta. Puede intentar sacar equipo sin derecho o devolver equipo ajeno. |
| Externo | Cualquiera en Internet: el sistema está publicado. |

## Qué se protege

- **La bitácora.** Si se puede alterar, deja de servir como prueba.
- **Los datos personales** de los trabajadores: CURP, NSS, firma.
- **Los costos**, que no deben llegar al trabajador (RG-12).
- **Las existencias**, que deben coincidir con la realidad.

## Control de acceso

- El acceso se decide por permisos con clave, no por el nombre del rol ([ADR-007](decisions/ADR-007-permisos-por-clave.md)). El catálogo de permisos y lo que trae cada rol inicial están en la sección 8 de las [reglas de negocio](../product/reglas-de-negocio.md).
- El servidor verifica el permiso en cada endpoint. La interfaz solo oculta lo que el rol no permite. Ocho rutas lo verifican en el servicio en vez de en el router, porque depende del tipo de vale o del usuario, o porque aceptan uno de dos permisos (`POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}`, `POST /api/autorizaciones/{id}/resolucion`, y las dos lecturas de `/api/solicitudes-compra`, que piden `compras.solicitar` o `compras.atender`); responden 403 igual que las demás.
- Control de acceso por almacén (AC-06): el alcance sale del almacén asignado del usuario. Solo `almacenes.todos` (de inicio, el Administrador) ve y opera todos; sin almacén asignado y sin `almacenes.todos`, el usuario no ve nada. No hay supervisor general: cada almacén tiene sus supervisores, y a ellos llegan sus autorizaciones. Una solicitud de autorización es del almacén donde se pidió: la ven y resuelven quienes tienen `autorizaciones.resolver` en ese almacén (y el Administrador); el supervisor que autoriza con su PIN en otro mostrador también debe ser de ese almacén. Las inspecciones y el ajuste de vigencia aplican solo a piezas del almacén propio (una pieza es del almacén donde está; la que tiene un trabajador, del de su última entrega; H11). El personal que un supervisor ve y asigna es el de su almacén y quien no tiene almacén; mover entre almacenes distintos exige `almacenes.todos`. Fuera de alcance se responde como si no existiera (404).
- Las solicitudes de compra urgentes (SC-03) son la única excepción al alcance por almacén: quien tiene `compras.atender` (Compras) ve las de todos los almacenes, porque una solicitud no es inventario y no revela existencias ni piezas; quien solo tiene `compras.solicitar` ve las de su almacén. El módulo no escribe inventario (SC-11) y sus eventos solo se insertan (SC-08).
- Los datos reservados piden un permiso de información; sin él, el dato no se envía (AC-05).
- Hay cuatro cosas que ningún rol puede hacer, porque no son permisos (AC-07): editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale.
- Una prueba por permiso comprueba que el endpoint responde con él y da 403 sin él; otra compara los roles iniciales contra las reglas.
- El alcance por almacén (AC-06) es el mismo en todo lo que muestra un vale: el detalle, el listado y el escaneo (`GET /api/escaneo/{codigo}`). Un vale es visible si el almacén del usuario es el de origen o el de destino de un traspaso (el receptor ve el vale que le llega), o si tiene `almacenes.todos`; si no, el escaneo lo trata como desconocido.
- **Qué ve cada rol de otros almacenes.** Solo quien tiene `almacenes.todos` (el Administrador) ve las piezas y las existencias de todos los almacenes. Los demás roles ven únicamente su almacén asignado; sin almacén ni `almacenes.todos`, nada. Eso vale para el escaneo, la búsqueda, la ficha y el historial de una pieza (404 si es ajena), las existencias de un artículo y del inventario, los reportes y los mensajes de la evaluación: E-03 y X-02 no dicen dónde está una pieza ajena ni quién la tiene. Excepción: lo que tiene un trabajador (su resguardo) se ve completo para quien opera su devolución o su baja, porque el trabajador es una ubicación y no un almacén; no incluye el inventario del almacén de origen.
- Los reportes que son de personas, como el de adeudos, se deciden por permiso y no por «no tener almacén»: lo ven completo `almacenes.todos` y `trabajadores.administrar` (RH); el resto, solo lo de su almacén, y sin almacén nada.

## Amenazas y controles

| Amenaza | Control |
|---|---|
| Alterar o borrar un vale para ocultar un faltante. | Los movimientos solo se insertan; no hay endpoint que los edite. Respaldo periódico (`scripts/respaldo.*`) y `app.mantenimiento verificar`, que descubre existencias que no cuadran con la bitácora. El sello encadenado llega con FEAT-001. |
| Registrar una devolución sin recibir el equipo. | Cada vale lleva al responsable por su sesión; el cierre de almacén (FEAT-002) descubre lo que el sistema dice que hay y no aparece. |
| Sacar equipo con contrato vencido. | La vigencia se evalúa en el servidor con su propia fecha (E-02). |
| Presentar la credencial de otro. | El almacenista ve los datos del trabajador y su foto (T-09). |
| Devolver equipo de otra compañía. | Un código desconocido se rechaza (V-12). |
| Autorizarse a sí mismo un excedente. | Quien captura no puede autorizar (A-05). |
| Darse permisos de más, o dejar un rol que exponga datos. | Solo quien tiene `acceso.administrar` cambia roles, y cada cambio queda en el registro de cambios. Los roles se editan desde la pantalla Roles y permisos; el rol Administrador está protegido (no pierde `acceso.administrar`) y los cinco roles iniciales no se eliminan ni se renombran. |
| Dejar al sistema sin administrador. | El rol Administrador no pierde `acceso.administrar`, y no se inactiva al último usuario que lo tiene (AC-09). |
| Adivinar una contraseña o un PIN. | Argon2; bloqueo de cinco minutos tras cinco intentos; mensaje de error genérico. El conteo bloquea la fila del usuario (`FOR UPDATE`) ANTES de verificar la clave: peticiones simultáneas se atienden una por una y no hay más de cinco intentos reales por ventana. Un interbloqueo o una espera de bloqueo vencida de MySQL (errores 1213 y 1205) se reintenta tres veces con una pausa corta y, si persiste, responde 503, nunca 500. |
| Robo de sesión. | Dos cookies `HttpOnly` y `SameSite=Lax` (más `Secure` bajo HTTPS) por dispositivo: un token de acceso de 15 minutos y un token de renovación opaco de 7 días que solo viaja a `/api/sesion` y del que la base guarda únicamente la huella SHA-256. El de renovación se **rota** en cada uso; usar uno ya rotado fuera de 10 segundos cierra la sesión de ese dispositivo. La sesión tiene un tope absoluto de 30 días. El token de acceso lleva la versión de sesión del usuario (`usuario.version_sesion`) y la familia del dispositivo, y se comprueba contra la base en cada petición: cerrar sesión revoca ese dispositivo al instante; restablecer la contraseña o el PIN, inactivar o reactivar al usuario, o «cerrar todas» suben la versión y revocan todos los dispositivos, aunque alguien haya copiado un token. Detalle y decisiones en [Sesión por dispositivo](#sesión-por-dispositivo). |
| Configuración débil en el servidor (clave de sesión de ejemplo, cookie sin `Secure`, documentación pública). | `ENTORNO=produccion`: la aplicación NO arranca con una clave de sesión de ejemplo o de menos de 32 caracteres, sin `COOKIE_SEGURA=true`, o con `CARGAR_DATOS_PRUEBA=true` y `CLAVE_DATOS_PRUEBA` vacía; además apaga `/api/docs`, `/api/redoc` y `/api/openapi.json`. En `desarrollo` solo avisa en el registro. Las cabeceras `X-Forwarded-*` solo se aceptan de las redes de `FORWARDED_ALLOW_IPS` (nunca `*`). |
| Agotar la memoria o el ancho de banda con un cuerpo enorme. | Un middleware ASGI puro (`app/limite_cuerpo.py`) responde 413 `CUERPO_MUY_GRANDE` antes de leer el cuerpo si `Content-Length` pasa del límite de la ruta, y cuenta los bytes del flujo cuando no hay `Content-Length`. Límites: 1 MB de JSON, 12 MB al crear o evaluar un vale, 3 MB la foto de un trabajador, 6 MB la importación; además, 3 MB por foto de daño y 10 MB de fotos por vale, y un máximo de puntos en el trazo de la firma. |
| Mentirle al supervisor al pedir una autorización (artículo, límite o excedente falsos). | Del cliente el servidor toma solo `codigo` y `cantidad`; lo que lee quien autoriza (artículo, límite, lo que tiene, excedente, regla y mensaje) sale de la evaluación del servidor, y solo un renglón naranja se puede autorizar (A-02, A-06). |
| Reintentar un vale con otros datos usando el mismo `id_cliente` para que parezca que se guardó lo nuevo. | El vale guarda una huella SHA-256 de su cuerpo; el mismo `id_cliente` con otro cuerpo responde 409 en vez de devolver el vale original. |
| Peticiones falsas desde otro sitio. | Un solo origen y `SameSite=Lax`. |
| Inyección de SQL o de código en pantalla. | Consultas por ORM; React escapa el texto; ningún HTML llega de los datos. |
| Subir un archivo dañino como firma o foto. | Se validan tipo y tamaño; se guarda con nombre generado, fuera de la carpeta pública. |
| Dar por firmada una entrega con una imagen o un trazo de relleno (F-02). | La firma debe ser un PNG completo (cabecera, dimensiones entre 100x50 y 4000x4000, datos de imagen que miden lo declarado, cierre y sumas de comprobación correctas) y traer un trazo de 10 a 20 000 puntos `{x, y, t}`. ALCANCE REAL: es un control de integridad del archivo; no impide que se dibuje cualquier cosa ni que alguien con el equipo mande un PNG válido hecho a mano. Impide el atajo trivial (nueve bytes, imagen vacía, trazo vacío). La evidencia de la firma es el conjunto: usuario, dispositivo, hora, trazo y archivo ligados al vale (F-05). |
| Ver un vale ajeno adivinando su dirección. | El token del vale tiene 128 bits aleatorios; en el MVP además pide sesión. |
| Datos de negocio o de sesión guardados en el dispositivo por la aplicación instalable. | El service worker (`/sw.js`, escrito a mano) solo guarda `/offline.html`, un icono y los archivos con huella de `/assets/*` (código y fuente de la interfaz, iguales para todos). Ignora todo `/api/*`, los métodos distintos de GET y otros orígenes: nunca guarda respuestas de la API, vales, personas ni cookies. Las navegaciones van siempre a la red. Se sirve con `Cache-Control: no-cache` y `Service-Worker-Allowed: /`; la CSP solo añade `manifest-src 'self'` y `worker-src 'self'`. Al cambiar su `VERSION` se borran los cachés viejos. |
| Que una caché compartida o del navegador guarde respuestas de la API. | Toda respuesta de `/api/*` lleva `Cache-Control: no-store` (S-07), salvo las firmas y fotos, que conservan su propia política `private, no-cache`. La CSP de la interfaz permite workers solo de `'self'` (sin `blob:`: el escáner usa el detector nativo del navegador y no crea workers en memoria). |
| Fuga de secretos. | `.env` fuera del repositorio; `.env.example` sin valores reales. |
| Acceso directo a la base de datos. | MySQL no se publica por el túnel y solo escucha en la máquina local. |
| Pérdida de datos. | Respaldo de la base y de los archivos con `scripts/respaldo.sh` o `respaldo.ps1`; restauración probada en otra base con `restaurar.*`; las existencias se pueden verificar y reconstruir desde la bitácora. |

## Sesión por dispositivo

Reglas AC-14 a AC-24 ([reglas de negocio](../product/reglas-de-negocio.md)). Contratos en [api-contracts.md](api-contracts.md); tabla `sesion_dispositivo` en [data-model.md](data-model.md).

**Cómo funciona.**

1. `POST /api/sesion` valida usuario y contraseña (con el bloqueo de intentos de siempre) y abre una *familia*: un dispositivo. Deja dos cookies: `sesion` (token de acceso, JWT firmado, `ACCESO_MINUTOS`) y `sesion_renovar` (token de renovación, 48 bytes aleatorios, `Path=/api/sesion`). La base guarda una fila con la huella del segundo.
2. El token de acceso lleva solo `sub` (usuario), `ver` (versión de sesión), `fam` (familia), `iat` y `exp`. Rol, permisos y almacén se leen de la base en cada petición (AC-23). En cada petición el servidor además comprueba que el usuario esté activo, que `ver` coincida con `usuario.version_sesion` y que la familia no esté revocada (una consulta por índice).
3. Cuando el acceso vence, la interfaz recibe 401, llama a `POST /api/sesion/refresh` (una sola vez aunque varias peticiones fallen a la vez) y repite la petición. La renovación valida el token de renovación, lo **rota** (el viejo queda revocado y encadenado al nuevo; hay otros `REFRESH_DIAS` días desde ahora, sin pasar de `inicio + REFRESH_TOPE_DIAS`) y entrega un acceso nuevo.
4. Un token de renovación ya rotado: dentro de `REFRESH_TOLERANCIA_SEGUNDOS` (10) se atiende como carrera legítima y devuelve solo un token de acceso nuevo, sin tocar la cookie de renovación (la que ya trae la primera respuesta); después se toma por reutilización y **se revoca toda la familia** (el dueño legítimo también pierde su sesión en ese dispositivo y entra de nuevo con su contraseña). Un token vencido, revocado, inexistente, de un usuario inactivo o de una versión de sesión vieja responde 401 `SESION_VENCIDA` y borra las cookies.
5. `DELETE /api/sesion` revoca la familia de ESE dispositivo; `DELETE /api/sesion/otras` las demás; `DELETE /api/sesion/todas` todas y sube `version_sesion`. Restablecer contraseña o PIN e inactivar o reactivar suben la versión (como antes), con lo que ningún token de renovación de esas sesiones sirve.

**Decisiones.**

| Decisión | Por qué | Qué se aceptó |
|---|---|---|
| Acceso de **15 minutos**. | Es la ventana en que un token de acceso copiado sirve si el servidor no lo revoca. Como cerrar sesión y la versión se comprueban en cada petición, en la práctica la ventana solo importa si hay un fallo de revocación; más corto sube las renovaciones sin ganar casi nada y más largo alarga la exposición. | Una renovación cada 15 minutos por dispositivo en uso. |
| Renovación de **7 días**, que se renueva con el uso. | El almacén opera por turnos y días de descanso: quien no entra un fin de semana o unas vacaciones cortas no debe teclear la contraseña al volver (decisión del usuario: al menos 7 días). La ventana deslizante evita que quien usa la aplicación todos los días la pierda a media operación. | Un dispositivo desatendido y sin cerrar sigue abierto hasta 7 días desde su último uso. |
| Tope absoluto de **30 días**. | Una sesión que se renueva sin fin equivale a una contraseña que nunca se vuelve a pedir: con un dispositivo robado y usado a diario, el atacante nunca saldría. El tope fuerza una prueba de identidad por lo menos una vez al mes. | Una vez al mes se pide la contraseña, aunque se use a diario. |
| Token de renovación **opaco y guardado solo como huella** (SHA-256). | No es un JWT: no se puede leer, extender ni falsificar. Si se filtra la tabla, las huellas no sirven para entrar (el token tiene 384 bits de entropía; no hace falta Argon2 en un secreto de esa entropía). | Hay que consultar la base en cada renovación (que de todos modos hace falta para rotar y revocar). |
| **Rotación** con detección de reutilización. | Un token de renovación robado y usado antes que el dueño deja al dueño con un token ya rotado: su siguiente renovación revoca la familia y lo obliga a entrar, lo que delata el robo (queda `sesion.reutilizacion` en el registro de cambios) y corta al atacante. | El dueño legítimo también pierde la sesión de ese dispositivo si su token se reutilizó. |
| **Tolerancia de 10 segundos.** | Dos pestañas o un reintento de red pueden presentar el mismo token casi a la vez. Sin tolerancia, esa carrera tumbaría la sesión de gente honesta. En ese plazo solo se da un token de acceso nuevo; no se rota otra vez ni se toca la cookie de renovación, para no pisar la que otra respuesta ya entregó. | Si la respuesta de una rotación se pierde en la red y el cliente reintenta pasados los 10 segundos, la familia se revoca y se pide la contraseña. Un token robado y usado dentro de los 10 segundos posteriores al uso legítimo recibe un token de acceso (15 minutos), pero no uno de renovación. |
| Sesión **por dispositivo**; la versión (`version_sesion`) se conserva para revocar todo. | Cada almacenista usa su propia cuenta y dispositivo (RG-07); cerrar sesión en el mostrador no debe tumbar la del celular. La versión sigue siendo el interruptor de emergencia: contraseña, PIN, inactivar y reactivar cierran todos los dispositivos. | Hay una tabla más y una consulta más por petición. |
| La IP **no se guarda**; el agente se resume y se recorta (120 caracteres). | Basta con que la persona reconozca su dispositivo («Chrome en Windows»). | No se puede decir desde dónde se entró. |

**Riesgo de equipos compartidos.** Un equipo compartido (la computadora del mostrador, un celular que se presta) con la sesión sin cerrar sigue abierto hasta 7 días desde el último uso (30 como máximo si se usa a diario), no solo 15 minutos: quien llegue después opera con la cuenta de la persona anterior, y cada vale lleva su nombre. Controles: cada persona usa su propia cuenta (RG-07); «Salir» cierra de verdad (el token de acceso copiado y el de renovación dejan de servir al instante); quien sospeche puede cerrar todas sus sesiones o pedir que se restablezca su contraseña (cierra todas); las autorizaciones piden además el PIN (A-05). Si el centro quisiera menos exposición, se baja `REFRESH_DIAS` (por ejemplo a 1 para turnos de 24 horas) sin cambiar código; los tres valores están en `.env` (`ACCESO_MINUTOS`, `REFRESH_DIAS`, `REFRESH_TOPE_DIAS`).

**Qué falta (a propósito).** No hay cierre automático por inactividad en la pantalla ni un aviso al dueño cuando se detecta una reutilización; el rastro queda en el registro de cambios. No hay lista de IP ni geolocalización. `SESION_HORAS` quedó obsoleta: si sigue en el `.env`, se ignora.

## Datos personales

- Se guarda lo mínimo: nombre, número de empleado, puesto y periodo. CURP y NSS son opcionales.
- La firma es dato personal: se guarda como archivo en el volumen, ligado a su vale.
- El almacenista no ve CURP, NSS ni sueldo; el sistema no guarda sueldos (RG-13).
- La huella dactilar no se usa.
- Para operar con datos reales, la empresa debe entregar su aviso de privacidad al trabajador.

## Respaldos y recuperación

Lo que existe hoy:

- **Respaldo.** `scripts/respaldo.sh` (bash) y `scripts/respaldo.ps1` (PowerShell) generan, con la misma marca de fecha, un `bd-MARCA.sql.gz` (volcado de MySQL con `mysqldump --single-transaction --routines --triggers`, ejecutado dentro del contenedor de la base) y un `archivos-MARCA.tar.gz` (firmas y fotos). Van a `respaldos/` o a `RESPALDOS_DIR`; la carpeta está en `.gitignore`. `RESPALDOS_CONSERVAR=N` conserva solo los N más recientes. Ninguna contraseña aparece en la línea de comandos ni en el registro: `mysqldump` lee la clave de root del entorno del propio contenedor.
- **Restauración.** `scripts/restaurar.sh` y `restaurar.ps1` restauran los dos archivos. Piden confirmación explícita antes de sobrescribir la base de producción (hay que escribir su nombre). Con `--base OTRA` restauran en una base distinta, sin tocar producción, que es como se prueba. Se probó respaldando una base y restaurándola en otra: los conteos de vales, movimientos y existencias coincidieron y `verificar` dio 0 en ambas.
- **Verificación.** `python -m app.mantenimiento verificar` (solo lectura) comprueba las invariantes de [data-model.md](data-model.md) sobre la base real y sale con código 1 si encuentra diferencias. Conviene correrlo después de cada restauración.
- **Reconstrucción de existencias.** `python -m app.mantenimiento reconstruir-existencias` calcula lo que valdrían las existencias desde la bitácora. Con `--simular` no escribe. Con `--aplicar` las reescribe, y es **la única operación que escribe `existencia` fuera del motor de `movimientos`**: se permite porque es una recuperación (la bitácora es la verdad y las existencias son su suma guardada, ADR-001), solo existe por línea de comandos, exige escribir una frase de confirmación en una terminal interactiva, se niega si la bitácora arrojaría una existencia negativa y deja un renglón en `auditoria`. Nunca toca vales ni movimientos.
- **Programación.** El respaldo diario se programa con el Programador de tareas de Windows o con cron; los pasos están en [despliegue-local-cloudflare.md](despliegue-local-cloudflare.md).

Lo que falta: el respaldo se lanza a mano o con la tarea programada del equipo, y las copias quedan en la misma máquina; copiarlas a otro equipo o a la nube es decisión de operación. No hay verificación periódica automática de la consistencia.

## Riesgos aceptados en el MVP

- Sin sello contra alteración hasta FEAT-001: la inmutabilidad de vales y movimientos la garantiza solo el código (no hay endpoint que los edite y los servicios no los actualizan), no la base de datos. Quien tenga acceso directo a MySQL podría modificar un registro sin dejar rastro; `verificar` detecta los cambios que rompen las invariantes (por ejemplo, existencias que ya no suman), pero no una edición que las deje cuadradas.
- Sin segundo factor de autenticación.
- Un administrador con credenciales robadas puede cambiar roles y permisos: por eso el cambio queda en el registro de cambios y exige el permiso `acceso.administrar`; no hay segundo factor (ver arriba).

## Previsto por la iteración 01 (aprobado, sin construir)

Fuente: [documento maestro de la iteración 01](../releases/iteration_01/README.md), [ADR-012](decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md) a [ADR-015](decisions/ADR-015-operacion-sin-conexion-del-almacenista.md) y los briefs FEAT-013 a FEAT-020. **Nada de esto está construido**; lo de arriba describe el sistema de hoy. Al construirse, cada punto pasa a su sección.

### Control de acceso

- **Alcance por un conjunto de almacenes (AC-36 a AC-41, ADR-012).** El alcance deja de ser «el suyo o todos»: cada usuario tiene un conjunto (`usuario_almacen`) y un almacén activo (`usuario.almacen_id`, siempre dentro del conjunto). Las lecturas abarcan el conjunto; las escrituras, solo el activo. El conjunto, el activo, el rol y los permisos se siguen leyendo de la base en cada petición (AC-23): quitar un almacén del conjunto corta el acceso desde la siguiente petición. Un supervisor con `almacenes.asignar_personal` solo reparte almacenes de su propio conjunto y nunca amplía el suyo (AC-41). El almacén activo es del usuario, no del dispositivo: un vale capturado en el anterior se rechaza con 409 `ALMACEN_CAMBIO`.
- **Un solo helper de alcance.** `AccesoService.alcance_del_usuario(usuario)` en `acceso` (dueño de `usuario_almacen`; `core` no importa módulos), con `en_alcance` y `exigir_mismo_almacen` reescritos sobre él. Los servicios migran uno por uno, cada uno con una prueba de un usuario de dos almacenes; una prueba de búsqueda en el código falla si queda una lectura directa de `usuario.almacen_id` fuera de `acceso` y `movimientos`. Mientras dure la migración, una lectura directa solo es correcta para conjuntos de un almacén: es el riesgo principal de esta feature.
- **Rutas que verifican el permiso en el servicio.** A las ocho de hoy se suma `POST /api/autorizaciones` (el router pide sesión; el servicio exige `entregas.crear` para EXCEDENTE y DESPACHO y `traspasos.operar` para TRASLADO). `POST /api/sincronizacion/lotes` declara `sincronizacion.operar` en el router, pero el permiso de **cada operación** del lote se verifica en el servicio contra el usuario que la capturó. `POST /api/trabajadores` exige además `proyectos.asignar` en el servicio. A las cuatro de `requiere_alguno` se suman `GET /api/bitacora`, `PUT /api/usuarios/{id}/almacenes` y `GET /api/proyectos` (y su ficha). Todas responden 403 igual que las demás.
- **Autonomía del despacho como permiso de alto impacto.** `despacho.autonomia` (de inicio, solo el Administrador; D-07) apaga la aprobación del EPP de un almacén o de un almacenista. Cada cambio pide motivo y queda en `auditoria` (`almacen.autonomia`, `usuario.autonomia`) con el antes y el después. Como cualquier permiso, se podría dar desde `/roles`; si debe quedar protegido como AC-32 es una decisión abierta de FEAT-014.

### Autorizarse a sí mismo: dos excepciones que no son autorizaciones guardadas

AC-07 y A-05 siguen: nadie resuelve una solicitud que él mismo pidió, y `ck_autorizacion_no_autorizarse` no cambia. Las dos excepciones del maestro **no crean ninguna solicitud**: es la autoridad de quien captura, no una autorización propia.

- **DE-07.** El supervisor (o el Administrador) que despacha EPP en un almacén donde tiene `autorizaciones.resolver` no pide aprobación del despacho; sus movimientos de EPP llevan `DE-07` y el vale dice «Validó: él mismo». Un excedente (naranja) en ese vale **sigue necesitando a otro supervisor**.
- **X-16.** El supervisor del almacén de origen que envía un traslado lateral entre almacenes de tercer nivel: su envío es la autorización, con observación obligatoria, las reglas `X-16` y `X-18` en los movimientos y entrada a la lista de revisión.
- Relacionado: **X-21** permite que quien envió un traspaso lo reciba (un supervisor con los dos almacenes en su conjunto), con observación obligatoria, marca en el vale y revisión. Un conflicto de sincronización tampoco lo resuelve quien capturó la operación (`ck_conflicto_sincronizacion_no_resolverse`, OF-25).

### Costos y valor

- **El supervisor ve dinero** por primera vez: el valor del inventario de su conjunto y el uso por proyecto (D-05, TB-04, TB-05), siempre como **totales**, nunca un costo unitario (RG-12). (El código ya le da `reportes.valor_inventario` desde la migración `0009`.)
- **Costo deducible de un total (T-2).** Un total en pesos que cubre un solo artículo revela su costo al dividirlo entre las unidades. Donde un grupo tiene un solo artículo con costo, el valor se responde `null` («No se muestra para no revelar el costo de un artículo») a quien no tiene `catalogo.costos`: uso por proyecto, resumen del vale (BT-05) y consumo por trabajador (DU-08). Una prueba revisa que ninguna respuesta del tablero traiga `costo_unitario`.
- **El PDF nunca lleva pesos** (BT-07), aunque quien lo descarga tenga `reportes.valor_inventario` o `catalogo.costos`.
- **`alto_valor` es un booleano** que ven todos los que ven el artículo (AV-05): dice, como mucho, que el costo pasa del tope general (`ALTO_VALOR_COSTO_MINIMO`), y se acepta (D-12). Si la marca vino «por su costo» o «por su categoría» solo se dice con `catalogo.costos`.

### Notificaciones push (Web Push, ADR-013, FEAT-014)

| Amenaza | Control |
|---|---|
| El aviso se ve en la pantalla bloqueada del celular. | El contenido no lleva costos, CURP, NSS ni foto (NT-03): almacén, para quién, cuántos artículos y quién lo pide. El cuerpo viaja cifrado de punta a punta (RFC 8291): el servicio de push del navegador no lo lee. |
| Que un dispositivo que ya cerró sesión siga recibiendo avisos. | Cada suscripción (`suscripcion_push`) es **por dispositivo** y queda ligada al usuario y a la familia de su sesión (`familia_id`). Al salir, la aplicación la revoca; si no pudo (sin red), el servidor no envía a una familia cerrada o vencida ni a una versión de sesión vieja y la marca revocada al intentar. Un 404 o 410 del servicio de push también la revoca. «Cerrar todas» y restablecer contraseña o PIN dejan sin avisos hasta volver a entrar. |
| Que reciba avisos quien ya no debe. | Los destinatarios se calculan al enviar: usuarios activos con `autorizaciones.resolver` y el almacén en su conjunto, menos quien pidió. Registrar una suscripción pide ese permiso. Al tocar un aviso viejo, la solicitud responde 404 si ya no la puede ver. |
| Pedir permisos de notificación sin que el usuario lo decida. | El navegador pide el permiso solo al tocar «Activar avisos», nunca al cargar. |
| Robo de la clave VAPID privada (cualquiera podría mandar avisos a las suscripciones). | `VAPID_CLAVE_PRIVADA` vive en `.env` (secreto; `.env.example` solo la nombra), junto con `VAPID_CLAVE_PUBLICA` y `VAPID_CONTACTO`. Cambiarla invalida todas las suscripciones, que se vuelven a registrar solas al abrir la aplicación. Sin las claves, los avisos quedan apagados y lo demás funciona. |
| Que una regla dependa de que el aviso llegue. | Ninguna depende: el contador, la lista y el PIN en el mostrador siguen (NT-08). Se manda **después del commit** con `BackgroundTasks`, sin reintentos; un fallo queda en `ultimo_error` y no deshace nada. |
| Conexiones salientes nuevas. | El servidor necesita salir por HTTPS a los servicios de push (Google, Mozilla, Apple, Microsoft). Web Push exige contexto seguro: funciona por el túnel o en `localhost`, no por la IP local sin HTTPS. |

**El service worker deja de ser solo de instalación.** `/sw.js` gana los manejadores `push`, `notificationclick` y `pushsubscriptionchange` (y sube su `VERSION`). Sigue sin guardar nada de `/api/*`, vales, personas ni cookies: el aviso llega con su propio contenido mínimo y al tocarlo abre la pantalla, que pide los datos con sesión.

### App de Android del almacenista (ADR-014, ADR-015, FEAT-020)

Solo la app de Android, en un equipo inscrito, por quien tiene `sincronizacion.operar`, opera sin conexión. La web y la PWA siguen «primero en línea» (ADR-004).

| Amenaza | Control |
|---|---|
| La sesión desde la app. La interfaz se carga desde `https://localhost` y la API está en otro dominio: con `fetch` del WebView las cookies `SameSite=Lax` no viajan y haría falta CORS con credenciales. | Las peticiones se hacen por la capa nativa (`CapacitorHttp`), con el almacén de cookies nativo de Android: no hay CORS ni «sitio». El modelo del servidor **no cambia**: mismas dos cookies `HttpOnly`, rotación, detección de reutilización y tope de 30 días. `CapacitorCookies` queda **desactivado** salvo que la prueba de concepto lo necesite, porque podría exponer las cookies `HttpOnly` a JavaScript por `document.cookie`. La prueba de concepto (primer paso de la construcción) comprueba que `document.cookie` no muestre ningún token. Las alternativas (cargar la interfaz desde el servidor, o un token `Bearer` cifrado) cambian el modelo y piden otro ADR. |
| Robo o pérdida del equipo con datos del almacén. | Base local SQLite **cifrada** (SQLCipher) con una frase aleatoria protegida por el **Android Keystore**, que no es el PIN de nadie. El paquete trae lo mínimo: sin costos, CURP, NSS, contraseñas, PIN ni sus hashes, tokens ni datos de otros almacenes fuera del resguardo de los trabajadores del paquete. Lo más sensible en el equipo son nombres, fotos reducidas y las firmas de la cola. |
| Entrar al equipo sin señal con la cuenta de otro. | **Credencial local** por usuario y equipo: un PIN de 6 dígitos que se crea tras entrar **con señal** y contraseña, distinto del PIN de supervisor y sin secuencias triviales; se guarda solo en el equipo como derivación **PBKDF2-SHA256** con sal y al menos 600 000 iteraciones, y nunca viaja. Cinco fallos la bloquean 5 minutos; diez la borran. Caduca a los 30 días sin entrar con señal en el equipo, o si el paquete dice que el usuario está inactivo, perdió el permiso o cambió de almacén. Al cambiar de usuario sin señal se borran las cookies del anterior. Bloqueo por inactividad a los 10 minutos: propuesta abierta. |
| Que un usuario con sesión se haga pasar por cualquier equipo de su almacén. | Cada equipo inscrito recibe un **secreto** de 32 bytes, guardado cifrado en el equipo; el servidor guarda solo su huella SHA-256 (`dispositivo.secreto_hash`). Las rutas de sincronización piden `X-Dispositivo: <id>.<secreto>`, y el equipo debe existir, no estar revocado y ser de un almacén del usuario. |
| Equipo perdido, robado o de alguien dado de baja. | **Borrado remoto en la siguiente conexión** (OF-05): revocar el equipo borra toda su base local; inactivar al usuario, «cerrar todas» o restablecer su contraseña o PIN borran su credencial local. Antes de borrar, la app presenta la cola: nunca se borra una operación sin haberla presentado. Al revocar se pueden cerrar las sesiones de todos sus usuarios (sube `version_sesion`). Un lote de un equipo revocado no toca el inventario: todo va a conflictos. |
| Operar mucho tiempo con datos viejos o atrasando el reloj. | **Ventana sin conexión de 24 h** (`SINCRONIZACION_HORAS_MAXIMAS`) desde la última descarga exitosa, medida con el reloj **monótono** del equipo; un reloj anterior a la última hora del servidor vista bloquea hasta sincronizar. Pasado el plazo solo se consulta. |
| Un equipo que miente (folios, existencias, saldos, permisos, horas). | **El servidor no confía en el equipo:** revalida todo con su fecha y las filas bloqueadas; del cuerpo toma solo lo que toma en línea (códigos y cantidades); verifica que el responsable esté registrado en el equipo; nunca acepta del equipo un folio, una existencia ni un saldo. `creado_en` es la hora del servidor; `capturado_en` (la del equipo) se guarda aparte y se marca «Hora del equipo dudosa» si difiere más de 10 minutos. Lo que ya no cumple una regla de política se guarda con aviso y va a revisión; lo que rompería una invariante va a conflicto para un supervisor que no lo capturó. |
| Saltarse aprobaciones sin señal. | Sin conexión no hay autorizaciones ni PIN en el mostrador (los PIN no bajan al equipo): el EPP sin autonomía y cualquier naranja **esperan la señal** (OF-10). |
| Una app vieja con reglas viejas. | `X-App-Version` en cada petición; menor que `APP_VERSION_MINIMA`, 426 `APP_DESACTUALIZADA` (la subida de lotes acepta el formato anterior para no atrapar la cola). |
| Perder o filtrar la llave de firma del APK. | La llave y sus contraseñas son secretos: fuera del repositorio, guardadas con los respaldos. Perderla impide actualizar la app instalada sin desinstalarla (y desinstalar borra la cola). La app se distribuye por MDM o instalación directa, sin tienda. |
| El trabajador escanea un comprobante que aún no sube. | El token del QR lo genera el equipo (128 bits aleatorios, como el del servidor); `GET /api/vales/por-token/{token}` dice «pendiente de sincronizar» sin revelar nada más. `/v/:token` sigue pidiendo sesión (decisión abierta de FEAT-020). |

Riesgos aceptados nuevos: la entrega del push no está garantizada (el respaldo es el contador); una cola se pierde si la app se desinstala o se borran sus datos (aviso permanente, MDM y vigilancia de equipos sin subir, OF-30); el evaluador local en TypeScript puede divergir del de Python (casos compartidos con pytest y vitest; el servidor decide).
