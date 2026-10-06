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
| Robo de sesión. | Cookie `HttpOnly`, `Secure` y `SameSite=Lax`; la sesión vence. El token lleva la versión de sesión del usuario (`usuario.version_sesion`) y solo sirve si coincide con la de la base: cerrar sesión, restablecer la contraseña o el PIN e inactivar o reactivar al usuario la incrementan y revocan los tokens anteriores, aunque alguien los haya copiado. Cerrar sesión cierra la sesión en TODOS los dispositivos de ese usuario (decisión aceptada: es lo más simple y más seguro; si se quisiera por dispositivo habría que guardar sesiones). |
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
