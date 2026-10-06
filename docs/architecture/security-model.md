# Modelo de seguridad

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
- El servidor verifica el permiso en cada endpoint. La interfaz solo oculta lo que el rol no permite. Seis rutas lo verifican en el servicio en vez de en el router, porque depende del tipo de vale o del usuario (`POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}` y `POST /api/autorizaciones/{id}/resolucion`); responden 403 igual que las demás.
- Control de acceso por almacén (AC-06): el alcance sale del almacén asignado del usuario. Solo `almacenes.todos` (de inicio, el Administrador) ve y opera todos; sin almacén asignado y sin `almacenes.todos`, el usuario no ve nada. No hay supervisor general: cada almacén tiene sus supervisores, y a ellos llegan sus autorizaciones. Una solicitud de autorización es del almacén donde se pidió: la ven y resuelven quienes tienen `autorizaciones.resolver` en ese almacén (y el Administrador); el supervisor que autoriza con su PIN en otro mostrador también debe ser de ese almacén. Las inspecciones y el ajuste de vigencia aplican solo a piezas del almacén propio (una pieza es del almacén donde está; la que tiene un trabajador, del de su última entrega; H11). El personal que un supervisor ve y asigna es el de su almacén y quien no tiene almacén; mover entre almacenes distintos exige `almacenes.todos`. Fuera de alcance se responde como si no existiera (404).
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
