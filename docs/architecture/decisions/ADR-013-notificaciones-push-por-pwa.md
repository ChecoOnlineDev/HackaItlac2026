# ADR-013: Las notificaciones al supervisor son Web Push desde la PWA, con la consulta periódica como respaldo

## Estado

Aceptada (8 de octubre de 2026, decisión D-14 de la [iteración 01](../../releases/iteration_01/README.md)). Sin construir. La construye [FEAT-014](../../features/FEAT-014-despacho-de-epp-con-aprobacion.md) (reglas NT-01 a NT-09). Cambia lo que decían [trd.md](../trd.md) (sección 17: «notificaciones push» fuera de alcance; `pywebpush` retirado por no usarse) y la fila de [mvp-scope.md](../../product/mvp-scope.md) que excluía las notificaciones push.

## Contexto

En la plática del 8 de octubre el track pidió que toda entrega de EPP se mande como solicitud al supervisor del almacén y que al supervisor **le llegue una notificación push**, entre a la aplicación y vea la solicitud (pedido 5 del maestro). El supervisor está en planta, casi nunca frente a una pantalla, y tiene el celular en la bolsa.

Hoy el supervisor solo se entera si tiene la aplicación abierta: el contador del menú pregunta cada 5 segundos y la pantalla del almacenista consulta su solicitud cada 3 segundos ([contadores.ts](../../../frontend/app/sesion/contadores.ts), [trd.md](../trd.md) sección 8). Si el supervisor no la abre, la solicitud vence a los 15 minutos y el trabajador se queda esperando en el mostrador.

La aplicación ya es una PWA instalable: tiene manifiesto y un service worker escrito a mano (`frontend/public/sw.js`) que hoy solo cumple el requisito de instalación y guarda los archivos estáticos. Se publica por HTTPS con el túnel de Cloudflare. El almacenista tendrá además una app de Android hecha con Capacitor ([ADR-014](ADR-014-app-android-con-capacitor.md)), pero el usuario decidió que **el supervisor no tiene app nativa** (D-14).

## Fuerzas y restricciones

- **El supervisor usa su propio celular**, Android o iPhone, y no siempre instala nada.
- **Un solo desplegable** ([ADR-002](ADR-002-un-solo-desplegable.md)), sin servicios externos de pago, sin colas ni procesos aparte. El equipo es pequeño y el tiempo, corto.
- **Las reglas viven en el servidor.** Ninguna regla puede depender de que el aviso llegue: si no llega, el flujo sigue con el contador, la lista o el PIN en el mostrador.
- **Datos personales.** El aviso se ve en la pantalla bloqueada: no puede llevar costos (RG-12), CURP ni NSS (RG-13).
- **Volumen bajo.** Decenas de usuarios; en el peor caso, el arranque de un mantenimiento con 40 solicitudes en minutos para dos supervisores por almacén.
- **Excluido del alcance:** correo, SMS, WhatsApp y avisos que mande una tarea programada del servidor (mvp-scope).
- **Dispositivos del almacén:** equipos Zebra que pueden no tener servicios de Google (pregunta 3 de la sección 10 del maestro). No reciben push, pero el push es para el supervisor.

## Alternativas consideradas

1. **Web Push con VAPID desde la PWA existente.** El servidor firma cada envío con un par de claves propio (VAPID) y lo manda cifrado al servicio de push del navegador (Google para Chrome, Mozilla, Apple, Microsoft), que lo entrega al dispositivo aunque la aplicación esté cerrada. El service worker lo muestra y, al tocarlo, abre la solicitud.
   - A favor: usa lo que ya existe (PWA, service worker, HTTPS); no hay cuenta ni contrato con un proveedor; no hay costo por mensaje; Android con Chrome lo recibe sin instalar la aplicación; el contenido va cifrado de punta a punta.
   - En contra: en iPhone solo llega con la PWA **instalada en la pantalla de inicio** y con iOS 16.4 o superior; la entrega no está garantizada; los navegadores exigen que cada push muestre un aviso visible (no hay push «invisible»); hace falta un service worker con manejadores nuevos y una dependencia (o cifrado propio).
2. **App nativa para el supervisor con Firebase Cloud Messaging (FCM).** Por ejemplo, la misma interfaz con Capacitor y su complemento de notificaciones.
   - A favor: entrega más confiable en Android; control de canales y prioridad.
   - En contra: el usuario la descartó (D-14); en iPhone pide cuenta de desarrollador de Apple y publicación (excluido); hay que dar de alta un proyecto de Firebase y guardar sus credenciales; otra app que instalar y mantener; los Zebra sin servicios de Google tampoco la recibirían.
3. **Solo consulta periódica** (lo de hoy: contador cada 5 segundos y lista).
   - A favor: ya existe, cero dependencias, funciona en cualquier navegador.
   - En contra: solo funciona con la aplicación abierta y en primer plano; no cumple lo que pidió el track. WebSockets o Server-Sent Events tienen el mismo límite (necesitan la aplicación abierta) y además piden conexiones largas a través del túnel.
4. **SMS o WhatsApp.**
   - A favor: llega a cualquier celular sin instalar nada.
   - En contra: excluido del alcance; costo por mensaje y contrato con un proveedor (o la aprobación de plantillas de WhatsApp Business); hay que guardar el número de celular de cada supervisor, que es otro dato personal; el mensaje sale del sistema y no se puede «cerrar» cuando otro supervisor ya resolvió.

## Decisión

La alternativa 1, **Web Push con VAPID desde la PWA**, con la **consulta periódica como respaldo** que ya existe. En concreto:

- **Quién recibe:** los usuarios con `autorizaciones.resolver` en el almacén de la solicitud, menos quien la pidió (NT-02). El mismo canal sirve para despachos, excedentes y traslados.
- **Suscripción:** se pide permiso solo con un toque explícito («Activar avisos»), nunca al cargar. Cada suscripción se guarda en `suscripcion_push`, ligada al usuario y a la sesión de ese dispositivo (`familia_id`); se revoca al salir y el servidor no envía a una sesión cerrada (NT-01).
- **Envío sin colas ni workers:** después del commit, con `BackgroundTasks` de FastAPI, dentro del mismo proceso, uno tras otro, con un tiempo de espera corto por envío. Sin reintentos. Un fallo no afecta la solicitud; un 404 o 410 del servicio de push revoca la suscripción (NT-07).
- **Caducidad:** cada aviso caduca a los 15 minutos (la vigencia de la solicitud) y se manda con urgencia alta.
- **Agrupación y cierre:** una etiqueta por almacén; el aviso nuevo reemplaza al anterior y solo el primero de cada minuto suena. Al resolverse una solicitud, los demás reciben un aviso de **reemplazo** silencioso con la misma etiqueta (no un push invisible, que los navegadores no permiten) (NT-05, NT-06).
- **Contenido:** almacén, trabajador, cuántos artículos y quién lo pide; sin costos, CURP, NSS ni foto (NT-03).
- **Claves:** `VAPID_CLAVE_PUBLICA`, `VAPID_CLAVE_PRIVADA` y `VAPID_CONTACTO` en `.env`. Sin ellas los avisos quedan apagados y todo lo demás funciona.
- **Librería:** `pywebpush` (cifrado del contenido según RFC 8291 y firma VAPID), **pendiente de aprobar** como dependencia. Si no se aprueba, el token VAPID se firma con PyJWT y `cryptography` (ya instalados), se cifra con `cryptography` y se envía con `httpx`.
- **Respaldo:** el contador del menú, la lista de Autorizaciones y el PIN en el mostrador no cambian y ninguna regla depende de que el aviso llegue (NT-08).

## Justificación

Es la única opción que cumple lo que pidió el track (el aviso llega con la aplicación cerrada) sin app nativa, sin proveedor de pago, sin datos personales nuevos y sin procesos aparte. Reutiliza la PWA, el service worker y el HTTPS que ya existen. El caso que más importa, el supervisor con Android, funciona sin instalar nada; el de iPhone funciona instalando la PWA, que ya es posible. Como el push no está garantizado en ninguna plataforma, la consulta periódica se queda como el canal seguro y las reglas no dependen del aviso.

`BackgroundTasks` basta para el volumen del reto: unos pocos envíos por solicitud a dos o tres supervisores. Una cola con un proceso aparte agregaría un servicio al Compose, su monitoreo y su recuperación, para un beneficio (reintentos) que la caducidad de 15 minutos y el respaldo vuelven innecesario.

## Consecuencias positivas

- El supervisor se entera en su celular aunque la aplicación esté cerrada, y un toque lo lleva a la solicitud.
- Sin costo por mensaje, sin cuentas en proveedores, sin números de celular guardados.
- El contenido va cifrado: el servicio de push del navegador no lo puede leer.
- Un aviso se puede reemplazar y agrupar: el supervisor no recibe 40 avisos sueltos en el arranque de un mantenimiento, y el que ya no aplica se actualiza solo.
- Si los avisos fallan o no están configurados, el sistema sigue igual que hoy.

## Consecuencias negativas

- **iPhone:** solo con la PWA instalada en la pantalla de inicio y con iOS 16.4 o superior. Hay que explicarlo en pantalla y en la guía; quien no la instala depende del contador.
- **Android:** Chrome lo recibe sin instalar, pero el ahorro de batería del sistema puede retrasarlo; algunos navegadores (como Brave) traen los avisos apagados.
- **App de Android de Capacitor (FEAT-020):** su WebView no recibe Web Push. No afecta, porque los avisos son para el supervisor, que usa la PWA; pero un supervisor que abriera la app del almacenista no los recibiría.
- **Equipos sin servicios de Google** (los Zebra, si no los traen): Chrome no recibe push en ellos. No afecta por la misma razón.
- **Entrega no garantizada:** sin señal, con el celular apagado más de 15 minutos o con el permiso negado, el aviso no llega. No hay acuse de lectura ni reintentos.
- **HTTPS obligatorio:** solo funciona por el túnel de Cloudflare (o `localhost` en desarrollo), no por la IP de la red local.
- **Conexiones salientes:** el servidor debe poder conectarse a los servicios de push de Google, Mozilla, Apple y Microsoft. Una red que bloquee la salida deja los avisos sin funcionar (todo lo demás sigue).
- **Envíos perdidos al reiniciar:** si el proceso se reinicia justo después de guardar la solicitud, los avisos de esa solicitud no salen; la solicitud sí queda y aparece en el contador.
- **Aviso visible obligatorio:** cada push debe mostrar algo. Cerrar un aviso en los demás equipos se hace con un reemplazo silencioso, no desapareciéndolo sin rastro.
- **Secreto nuevo:** la clave VAPID privada vive en `.env`. Si cambia, todas las suscripciones dejan de servir hasta que cada dispositivo se vuelva a registrar (lo hace solo al abrir la aplicación).
- **Una dependencia más** (`pywebpush` con `py-vapid` y `http-ece`), o más código propio de cifrado si no se aprueba.
- El service worker deja de ser solo de instalación y estáticos: gana los manejadores `push`, `notificationclick` y `pushsubscriptionchange`, y hay que probarlo en cada plataforma.

## Señales para reevaluar

- **Volumen alto:** más de unas decenas de envíos por minuto, o envíos que hacen lentas las respuestas del servidor. Entonces, una cola con un proceso aparte.
- **Necesidad de reintentos o acuse:** si los supervisores pierden solicitudes porque el aviso no llegó y el respaldo no basta. Entonces, reintentos con cola, o un canal adicional (SMS) con su aprobación de alcance.
- **Avisos programados:** si se pide avisar sin un evento del usuario (vencimientos, inspecciones por vencer, recordatorios). Hoy están excluidos; pedirían una tarea programada.
- **Muchos supervisores con iPhone sin instalar la PWA**, o Apple cambia sus condiciones. Entonces, reconsiderar una app nativa.
- **Varios procesos o servidores** de la aplicación: `BackgroundTasks` sigue sirviendo (la agrupación por minuto de NT-05 ya se cuenta en la base, con `suscripcion_push.ultimo_envio`), pero dos procesos podrían mandar el primer aviso sonoro casi a la vez; si molesta, hace falta un bloqueo o una cola.
