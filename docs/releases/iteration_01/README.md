# Iteración 01: ajustes de la plática del 8 de octubre de 2026

Documento maestro de la iteración. Reúne lo que pidieron los dueños del track en la segunda plática ([ajustes_01.pdf](ajustes_01.pdf)), las decisiones que tomó el usuario al revisarlo y el reparto de identificadores, tablas y endpoints que usan los briefs. **Si un brief contradice este documento, manda este documento** hasta que se corrija uno de los dos en el mismo cambio.

Estado: **aprobado por el usuario el 8 de octubre de 2026. Al 9 de octubre se integraron localmente FEAT-001, 002, 004, 013 a 019 y partes de FEAT-020; quedan criterios, regresión integral y pruebas físicas. FEAT-020 aún no opera sin conexión.** Amplía el alcance del MVP (sección 6).

La última sesión de Claude Code dejó briefs, ADR y cambios locales; la captura adjunta documenta aquella sesión, no demuestra por sí sola que una feature funcione. El trabajo retomado integró el rediseño visual y continuó la implementación funcional. El estado, las pruebas, los faltantes y las limitaciones vigentes están en [reporte-integracion-features.md](reporte-integracion-features.md) y [reporte-capacitor.md](reporte-capacitor.md).

Rama de trabajo: `android/capacitor`. La app de Android **no es un proyecto aparte**: es la misma interfaz de `frontend/` empaquetada con Capacitor ([ADR-014](../../architecture/decisions/ADR-014-app-android-con-capacitor.md)); su carpeta nativa vive en `frontend/android/`.

---

## 1. Lo que pidió el track (transcripción de las notas)

Hoja 1 (encabezado «Midrex ← etc.»: aplica a los almacenes de tercer nivel):

1. Traslados entre almacenes de **tercer nivel** permitidos siempre y cuando **autorice el supervisor**.
2. Definir bien las reglas de negocio del **equipo de alturas**, entre ellas las inspecciones. ¿Quién hace las inspecciones: almacenista o supervisor?
3. Poder **modificar la vigencia** de la inspección.
4. **Alertas** en equipo que requiera inspección previa: cuando a cierto equipo de alturas esté por vencer su inspección (por ejemplo, en 10 días), poder **configurar una alerta**. Considerar cómo se podría visibilizar. **Rehacer el flujo de la pantalla.**

Hoja 2:

5. **Corregir el flujo de captura.** Para entregar cualquier equipo de EPP se requiere mandar una solicitud al supervisor de ese almacén. Ver posibles situaciones problemáticas. El almacenista no tiene autonomía para despachar a cualquiera. Flujo anotado: captura del trabajador → captura del EPP o herramienta → firma → confirmo solicitud → se envía al supervisor → llega notificación push → entra a la app → ventana de la solicitud de despacho del almacenista.
6. Es muy importante saber **en todo momento la ubicación de todas las piezas**, sobre todo las de **alto valor**.
7. Definir bien qué es **EPP de dotación**, **EPP básico**, **herramienta eléctrica** y **equipo de alto valor**. Una herramienta puede ser eléctrica y de alto valor; en ese caso da igual que sea eléctrica: **cuenta solo como alto valor**.

## 2. Decisiones del usuario (8 de octubre de 2026)

| # | Tema | Decisión |
|---|---|---|
| D-01 | **Flujo normal** | Un supervisor asignado a **un** almacén; cada trabajador o contratista asignado a **un** proyecto, que pertenece a un almacén. Todo lo demás (supervisor con varios almacenes, trabajador con varios proyectos, almacén con varios proyectos) son **casos especiales** que el sistema soporta, pero las pantallas se optimizan para el caso normal. |
| D-02 | **Proyecto** | Es una entidad nueva, distinta del almacén: nombre, almacén al que pertenece y periodo (inicio y fin estimado). Se da de alta **antes** que los trabajadores que trabajarán en él. Los almacenes de tercer nivel (tipo `PROYECTO`) **se conservan**. |
| D-03 | **Almacén sin proyecto** | Cuando un almacén de tercer nivel no tiene ningún proyecto activo, el sistema **avisa y sugiere inactivarlo**. Nunca lo inactiva solo. |
| D-04 | **Supervisor** | Se asigna a **almacenes** (lo normal, uno). Ve los proyectos de esos almacenes. Puede saltar entre sus almacenes y sus proyectos. |
| D-05 | **Valor del inventario** | Además de Compras, el **Supervisor** ve el valor del inventario de sus almacenes y el **uso por proyecto**, **en pesos y en unidades**. Nunca el costo unitario de un artículo. |
| D-06 | **Despacho de EPP** | Es requisito del flujo principal: toda entrega de **artículos de tipo EPP** necesita la aprobación del supervisor del almacén, con **notificación push**. La herramienta y las devoluciones no la piden. |
| D-07 | **Autonomía** | Un **interruptor por almacén** y una **excepción por almacenista** permiten despachar EPP sin aprobación. Por ahora **solo el Administrador** los cambia. |
| D-08 | **Orden del flujo** | Se aprueba **antes** de firmar: capturar → solicitar → aprobar → firmar → confirmar. Así el trabajador firma solo lo que de verdad recibe. (Cambia el orden de las notas del track, que ponían la firma antes de la solicitud.) |
| D-09 | **Traslado entre almacenes de tercer nivel** | Lo autoriza el supervisor del **almacén de origen**; el destino confirma lo que recibió. Si quien envía **es** el supervisor del origen, su envío **es** la autorización. |
| D-10 | **Inspecciones** | Las pueden hacer almacenista y supervisor, pero el flujo se diseña **para el almacenista**. |
| D-11 | **Aviso de inspección por vencer** | Configurable: un valor **general**, que la **categoría** puede cambiar y el **artículo** también. |
| D-12 | **Alto valor** | Un artículo es de alto valor si su categoría está marcada como de alto valor **o** si su costo unitario es de **10,000 o más** (tope editable). La marca de la categoría es editable. Alto valor gana sobre eléctrica. |
| D-13 | **Proyecto de la entrega** | Sale del proyecto vigente del trabajador. Si tiene más de uno, aparece un selector. El consumo es **del proyecto**, no del almacén que entregó: el EPP que Contratistas entrega a un trabajador del proyecto de Midrex cuenta para ese proyecto y lo ve el supervisor de Midrex. |
| D-14 | **Notificaciones** | Por **PWA** (Web Push), sin app nativa para el supervisor. |
| D-15 | **App del almacenista** | App de **Android con Capacitor**, la misma interfaz React, con **operación sin conexión** limitada a su almacén y a los trabajadores de sus proyectos. Descarga los datos al iniciar turno, a una hora configurable, cada vez que hay señal y con un botón. Sincroniza por lotes. Va **al final** del orden de construcción. |
| D-16 | **Bitácora** | Es el centro para saber dónde está cada cosa. Muestra **un renglón por vale** (no uno por movimiento); al abrirlo se ve el detalle a todo el ancho en computadora y se descarga en PDF. |
| D-17 | **Deudores** | Sección propia: quién le debe a cada almacén, qué, desde cuándo y para qué proyecto; filtro por categoría (por ejemplo, alto valor). El Administrador ve todo; el supervisor, sus almacenes. |
| D-18 | **Buscadores** | Esperan **300 ms** después de la última tecla antes de buscar. Buscan trabajadores por nombre, apellido, código de credencial y número de empleado, y herramienta por nombre, código y serie. |
| D-19 | **QR en PDF** | Un solo PDF descargable con varias etiquetas por hoja (9 o más). |
| D-20 | **Diseño por dispositivo** | La operación diaria (entregar, devolver, trasladar, recibir, aprobar, inspeccionar, consultar) es **primero celular**. Lo administrativo (importación, bitácora, vales, trabajadores, usuarios, roles, almacenes, proyectos, reportes, deudores, etiquetas, catálogo) es **primero computadora**. |
| D-21 | **Lo que va sí o sí** | Lo del PDF del track y los traspasos completamente funcionales. Se agregan a la planeación mejoras estéticas. |

## 3. Mapa de documentos de la iteración

| Documento | Qué resuelve | Pedido |
|---|---|---|
| [ADR-012](../../architecture/decisions/ADR-012-proyectos-y-varios-almacenes-por-usuario.md) | El proyecto como entidad y el alcance por un conjunto de almacenes | D-01 a D-05, D-13 |
| [ADR-013](../../architecture/decisions/ADR-013-notificaciones-push-por-pwa.md) | Notificaciones push por Web Push | D-06, D-14 |
| [ADR-014](../../architecture/decisions/ADR-014-app-android-con-capacitor.md) | Capacitor y no Flutter, mismo repositorio | D-15 |
| [ADR-015](../../architecture/decisions/ADR-015-operacion-sin-conexion-del-almacenista.md) | Operación sin conexión; reemplaza en parte a ADR-004 | D-15 |
| [FEAT-012](../../features/FEAT-012-valor-del-inventario.md) | Valor del inventario (ya construido; documento escrito a partir del código) | Base de D-05 |
| [FIX-001](../../fixes/FIX-001-etiquetas-de-piezas-sin-alcance.md) | Las etiquetas de piezas no respetan el alcance por almacén | Hallazgo de FEAT-019 |
| [FEAT-013](../../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) | Proyectos, asignación, supervisor con varios almacenes, uso y valor por proyecto | D-01 a D-05, D-13 |
| [FEAT-014](../../features/FEAT-014-despacho-de-epp-con-aprobacion.md) | Despacho de EPP con aprobación, autonomía y notificaciones | Track 5; D-06 a D-08, D-14 |
| [FEAT-015](../../features/FEAT-015-traslados-entre-almacenes-de-tercer-nivel.md) | Traslado entre almacenes de tercer nivel con autorización | Track 1; D-09 |
| [FEAT-016](../../features/FEAT-016-inspecciones-y-alertas-de-vigencia.md) | Inspecciones de alturas, avisos configurables y pantalla nueva | Track 2 a 4; D-10, D-11 |
| [FEAT-017](../../features/FEAT-017-bitacora-por-vale-y-pdf.md) | Bitácora por vale, detalle del vale y PDF | D-16 |
| [FEAT-018](../../features/FEAT-018-deudores-resguardo-y-alto-valor.md) | Deudores, resguardo por proyecto, consumo por trabajador y definición de categorías | Track 6 y 7; D-12, D-17 |
| [FEAT-019](../../features/FEAT-019-busqueda-etiquetas-y-diseno-por-dispositivo.md) | Búsqueda con espera, QR en PDF, diseño por dispositivo y estética | D-18 a D-20 |
| [FEAT-020](../../features/FEAT-020-app-android-sin-conexion.md) | App de Android del almacenista y operación sin conexión | D-15 |

FEAT-012 es el **valor del inventario** que ya está en el código (`GET /api/tablero/valor`, permiso `reportes.valor_inventario`, reglas VI-01 a VI-07). Su documento se escribió el 9 de octubre de 2026 a partir del código: [FEAT-012](../../features/FEAT-012-valor-del-inventario.md).

## 4. Reparto de identificadores de reglas

Para que dos briefs no usen el mismo ID. Cada regla se escribe completa en su FEAT y en [reglas-de-negocio.md](../../product/reglas-de-negocio.md).

| Prefijo e IDs | Tema | Brief |
|---|---|---|
| PR-01 a PR-14 | Proyectos | FEAT-013 |
| AC-36 a AC-41 | Alcance por un conjunto de almacenes y almacén activo | FEAT-013 |
| TB-04 a TB-08 | Inicio del supervisor: valor y uso por proyecto | FEAT-013 |
| DE-01 a DE-16 | Despacho de EPP con aprobación y autonomía | FEAT-014 |
| NT-01 a NT-09 | Notificaciones push | FEAT-014 |
| X-16 a X-21 | Traslado entre almacenes de tercer nivel | FEAT-015 |
| P-09 a P-17 | Inspecciones y avisos de vigencia | FEAT-016 |
| BT-01 a BT-10 | Bitácora por vale, detalle y PDF | FEAT-017 |
| AV-01 a AV-05 | Alto valor y definición de categorías | FEAT-018 |
| DU-01 a DU-09 | Deudores, resguardo y consumo por trabajador | FEAT-018 |
| UX-01 a UX-12 | Búsqueda, etiquetas, diseño por dispositivo y estética | FEAT-019 |
| OF-01 a OF-30 | App de Android y operación sin conexión | FEAT-020 |

Reglas existentes que **cambian**: RG-07, RG-15, AC-06, AC-07 y A-05 (excepción para autorizarse a sí mismo en DE-07 y X-16), AC-12, AC-13, A-01, A-03 (igual o menor cantidad y aprobación parcial), F-04, T-02, T-03, E-11, E-24 (el vale imprime el proyecto de la entrega), X-01 (estaba atrasada: el Almacenista sí trae `traspasos.recibir`), X-03, AL-03 (`CON_PROYECTOS_ACTIVOS`; `CON_USUARIOS` cuenta el conjunto), TB-01, P-01, P-04, C-05, C-06, C-08 (filtro por proyecto), C-09, I-14 (alto valor por costo), SG-04, SG-06, 5.1 (definiciones), 5.4 (parámetros) y la sección 8 (permisos). Al escribir las reglas salieron además: SM-03, A-02 y A-07 (FEAT-014), I-03 (FEAT-016), E-18 (FEAT-019), C-04 y SG-05 (FEAT-017, la bitácora por renglón queda como «Detalle por renglón»), TR-05 (ruta lateral, FEAT-015) y una nota en RG-12 (T-2 y AV-05). Las reglas RG-08, RG-09 y RG-11 **no cambian** para la operación en línea; para los vales capturados sin conexión tienen la excepción de OF-17 a OF-22.

## 5. Modelo de datos y API de la iteración

Resumen; el detalle de cada tabla y endpoint está en su FEAT y, al construirse, en [data-model.md](../../architecture/data-model.md) y [api-contracts.md](../../architecture/api-contracts.md).

### 5.1 Tablas y columnas nuevas

| Tabla o columna | Dueño | FEAT | Qué guarda |
|---|---|---|---|
| `proyecto` (`id`, `clave`, `nombre`, `almacen_id`, `inicio`, `fin_estimado`, `estado`, `cerrado_en`, `motivo_cierre`, `creado_por`, `creado_en`) | `proyectos` (módulo nuevo) | 013 | El proyecto o contrato. `estado`: ACTIVO, CERRADO. |
| `asignacion_proyecto` (`id`, `trabajador_id`, `proyecto_id`, `inicio`, `fin`, `principal`, `creado_por`, `creado_en`, `terminada_en`, `terminada_por`) | `proyectos` | 013 | El trabajador en un proyecto. Lo normal es una activa; `principal` marca la que se propone primero. |
| `usuario_almacen` (`usuario_id`, `almacen_id`, `asignado_por`, `asignado_en`) | `acceso` | 013 | El conjunto de almacenes de un usuario. `usuario.almacen_id` **se conserva** como el almacén activo, que siempre pertenece al conjunto. |
| `vale.proyecto_id` | `movimientos` | 013 | El proyecto de una ENTREGA (nulo en los demás tipos y en entregas sin proyecto). Se escribe al insertar; no se actualiza. |
| `vale.lote_id` | `movimientos` | 017 | Agrupa los vales de una misma importación o traspaso por Excel. |
| `almacen.despacho_epp_con_aprobacion` (bool, `true` por omisión) | `almacenes` | 014 | Interruptor de autonomía del almacén. |
| `usuario.despacho_autonomo` (bool, `false` por omisión) | `acceso` | 014 | Excepción por almacenista. |
| `autorizacion.tipo` (EXCEDENTE, DESPACHO, TRASLADO) y `autorizacion.renglones_resueltos` (JSON) | `autorizaciones` | 014, 015 | Qué se autoriza y qué renglones se aprobaron o rechazaron (aprobación parcial). Las existentes quedan como EXCEDENTE. |
| `suscripcion_push` (`id`, `usuario_id`, `familia_id`, `endpoint`, `p256dh`, `auth`, `agente`, `creada_en`, `ultimo_envio`, `ultimo_error`, `revocada_en`) | `notificaciones` (módulo nuevo) | 014 | Una suscripción de Web Push por dispositivo. |
| `categoria.alto_valor` (bool) | `catalogo` | 018 | Marca de alto valor de la categoría. Se siembra `true` en «Equipo de alto valor». |
| `categoria.dias_aviso_inspeccion` y `articulo.dias_aviso_inspeccion` (enteros, nulos = heredar) | `catalogo` | 016 | Días de aviso antes de que venza una inspección. |
| `dispositivo` (`id`, `usuario_id`, `almacen_id`, `nombre`, `plataforma`, `version_app`, `registrado_en`, `ultimo_paquete_en`, `ultima_subida_en`, `revocado_en`, `revocado_por`) | `sincronizacion` (módulo nuevo) | 020 | Un equipo inscrito para operar sin conexión. |
| `vale.capturado_sin_conexion` (bool), `vale.capturado_en`, `vale.dispositivo_id` | `movimientos` | 020 | Datos del vale capturado sin conexión. `creado_en` sigue siendo la hora del servidor al sincronizar. |
| `conflicto_sincronizacion` (`id`, `dispositivo_id`, `usuario_id`, `id_cliente`, `tipo_vale`, `cuerpo`, `motivo`, `detalle`, `estado`, `resuelto_por`, `resolucion`, `vale_id`, `creado_en`, `resuelto_en`) | `sincronizacion` | 020 | Un vale capturado sin conexión que el servidor no pudo guardar tal cual. Lo resuelve un supervisor. |

Columnas que salieron al escribir los briefs:

| Columna | FEAT | Por qué |
|---|---|---|
| `autorizacion.id_cliente` (único, nulo en las anteriores) | 014 | Que un doble toque no cree dos solicitudes de despacho (DE-04) |
| `autorizacion.trabajador_id` pasa a aceptar nulo | 015 | Una autorización TRASLADO no tiene trabajador |
| `autorizacion.estado` agrega RETIRADA (si se aprueba la decisión abierta 1 de FEAT-014) | 014 | El almacenista retira una solicitud cuando el trabajador se fue |
| `inspeccion.id_cliente` | 016 | Inspección por lote sin duplicar (P-16) |
| `adjunto.inspeccion_id` y `adjunto.tipo` FOTO_INSPECCION | 016 | Foto opcional de la inspección (P-14) |

| `almacen.hora_descarga` (hora local, nula = sin descarga programada) | 020 | Hora de la descarga diaria del paquete del almacén; la edita el Administrador |
| `dispositivo_usuario` (`dispositivo_id`, `usuario_id`, `primera_entrada_en`, `ultima_entrada_en`, `revocado_en`) | 020 | Varios usuarios en un equipo (turno de día y de noche): a quién se le aceptan vales y a quién se le invalida la credencial local |
| `dispositivo.secreto_hash` y `dispositivo.motivo_revocacion` | 020 | El equipo se autentica al subir lotes; motivo de la revocación |
| `operacion_recibida` (`id_cliente`, `dispositivo_id`, `tipo`, `resultado`, `creado_en`) | 020 | Idempotencia de lo que no es vale (inspecciones, marcar No apta, solicitudes) al reenviar un lote |
| `conflicto_sincronizacion.tipo_operacion` (en lugar de `tipo_vale`) | 020 | Un conflicto también puede ser de una inspección, un No apta o una solicitud de compra |

`vale.dispositivo` (el navegador, ya existe) y `vale.dispositivo_id` (equipo inscrito, nuevo) son cosas distintas: el texto de los documentos lo aclara cada vez.

El supervisor que despacha él mismo (DE-07) y el que envía un traslado lateral (X-16) **no** se guardan como una autorización: el CHECK `no_autorizarse` lo impide y así debe seguir. Se marcan con la regla en `movimiento.reglas` y el vale muestra «Validó: él mismo».

Parámetros generales nuevos (variables de `.env`, documentados en `.env.example`): `INSPECCION_AVISO_DIAS` (7), `ALTO_VALOR_COSTO_MINIMO` (10000), `VAPID_CLAVE_PUBLICA`, `VAPID_CLAVE_PRIVADA`, `VAPID_CONTACTO`, `SINCRONIZACION_HORAS_MAXIMAS` (24), `SINCRONIZACION_LOTE_MAXIMO` (20) y `APP_VERSION_MINIMA`. La hora de descarga diaria es por almacén (`almacen.hora_descarga`, FEAT-020).

### 5.2 Módulos nuevos

Los doce módulos de [AGENTS.md](../../../AGENTS.md) pasan a quince: `proyectos` (FEAT-013), `notificaciones` (FEAT-014) y `sincronizacion` (FEAT-020). Cada uno sigue Router → Service → Repository → Model, y su `router.py` se monta en `main.py` al crearse. **Solo `movimientos` escribe vales y existencias**, también los que llegan por sincronización: `sincronizacion` recibe, valida la forma y llama al servicio de movimientos.

### 5.3 Permisos nuevos

| Permiso | Qué permite | Roles iniciales | FEAT |
|---|---|---|---|
| `proyectos.ver` | Ver los proyectos de sus almacenes; quien además tiene `proyectos.asignar` (RH, que no tiene almacén) los ve todos (PR-07) | A, S, R (y Administrador) | 013 |
| `proyectos.administrar` | Dar de alta, editar, extender y cerrar proyectos | Solo Administrador | 013 |
| `proyectos.asignar` | Asignar trabajadores a proyectos y cambiarlos | R (y Administrador) | 013 |
| `despacho.autonomia` | Prender y apagar el interruptor de autonomía de un almacén y de un almacenista | Solo Administrador | 014 |
| `inspecciones.ver` | Lista de inspecciones vencidas y por vencer de sus almacenes | A, S | 016 |
| `deudores.ver` | Sección Deudores | S, R (y Administrador) | 018 |
| `sincronizacion.operar` | Inscribir un equipo y operar sin conexión | A | 020 |
| `sincronizacion.administrar` | Ver equipos inscritos, revocarlos y resolver conflictos de sincronización | S (de su almacén) | 020 |

Roles iniciales: el **Supervisor** ya tiene `reportes.valor_inventario` en el código (migración `0009` y datos de prueba), junto con Compras y el Administrador; D-05 solo pide documentarlo y usarlo en su Inicio. El permiso deja de estar «no disponible» en la tabla 8.3 (el código ya lo trae disponible desde la migración `0009_permiso_valor_inventario`; el documento está atrasado).

### 5.4 Endpoints nuevos o que cambian

| Endpoint | FEAT |
|---|---|
| `GET/POST /api/proyectos`, `GET/PATCH /api/proyectos/{id}`, `POST /api/proyectos/{id}/cierre`, `POST /api/proyectos/{id}/reapertura` | 013 |
| `GET/POST /api/trabajadores/{id}/proyectos`, `POST /api/trabajadores/{id}/proyectos/{asignacion_id}/termino`; `POST /api/trabajadores` acepta `proyecto_id` | 013 |
| `PUT /api/usuarios/{id}/almacenes` (conjunto), `PUT /api/sesion/almacen` (almacén activo); `GET /api/sesion` devuelve `almacenes` y `almacen_activo` | 013 |
| `GET /api/tablero/proyectos` (uso y valor por proyecto); `GET /api/tablero/resumen` agrega `almacenes_sin_proyecto` y `proyectos_por_vencer` | 013 |
| `POST /api/vales/evaluar` y `POST /api/vales` aceptan `proyecto_id` en la ENTREGA; la evaluación trae `proyectos_del_trabajador` y `requiere_aprobacion_despacho` | 013, 014 |
| `POST /api/autorizaciones` acepta `tipo` (DESPACHO, TRASLADO); `POST /api/autorizaciones/{id}/resolucion` acepta `renglones` (aprobación parcial); `POST /api/autorizaciones/resolucion-multiple` | 014, 015 |
| `PATCH /api/almacenes/{id}/autonomia`, `PATCH /api/usuarios/{id}/autonomia` | 014 |
| `GET /api/notificaciones/clave-publica`, `POST /api/notificaciones/suscripciones`, `DELETE /api/notificaciones/suscripciones/{id}`, `POST /api/notificaciones/prueba` | 014 |
| `GET /api/inspecciones/pendientes`, `POST /api/inspecciones/lote` | 016 |
| `GET /api/bitacora` (un renglón por vale o por lote) y `GET /api/vales/{id}/renglones` (paginado) | 017 |
| `GET /api/deudores`, `GET /api/deudores/resumen`, `GET /api/trabajadores/{id}/consumo` | 018 |
| `GET /api/sincronizacion/paquete`, `POST /api/sincronizacion/lotes`, `POST /api/dispositivos`, `GET /api/dispositivos`, `POST /api/dispositivos/{id}/revocacion`, `GET/POST /api/sincronizacion/conflictos` | 020 |

Cambios a endpoints existentes que salieron al escribir los briefs:

| Endpoint | Cambio | FEAT |
|---|---|---|
| `GET /api/trabajadores` | Filtros `proyecto_id` y `sin_proyecto` | 013 |
| `GET /api/tablero/valor` | Campos `unidades_*`; su contrato actual ya está en api-contracts y su brief es FEAT-012 | 013 |
| `GET /api/almacenes?resumen=true` | `proyectos_activos` y `aviso_sin_proyecto` | 013 |
| `POST /api/autorizaciones` | El router pide solo sesión y el servicio verifica según `tipo` (`entregas.crear` para EXCEDENTE y DESPACHO, `traspasos.operar` para TRASLADO); entra a la lista de excepciones de AGENTS.md | 014, 015 |
| `POST /api/autorizaciones/{id}/retiro` | Retirar una solicitud pendiente (decisión abierta de FEAT-014) | 014 |
| `POST /api/importacion/traspasos` | Acepta `autorizacion_id` para la ruta lateral | 015 |
| `GET /api/traspasos/por-recibir` | Trae `ruta` y `valido` | 015 |
| `GET /api/piezas/{id}`, categorías y artículos | `dias_aviso_inspeccion` y la vigencia resuelta; errores nuevos al inspeccionar (P-17) | 016 |
| `GET /api/tablero/resumen` | `inspecciones_vencidas` e `inspecciones_sin_registro` | 016 |
| `GET /api/vales/{id}` | `lote`, `resumen`, `relacionados` y `renglones=false` | 017 |
| Respuesta de la importación | `lote_id` | 017 |
| `GET /api/reportes/consumo` | Filtro `proyecto_id` | 018 |
| Categorías, artículos, seguimiento y tablero | `alto_valor` (AV-02) en lugar del nombre de la categoría | 018 |

Al construirse, [AGENTS.md](../../../AGENTS.md) actualiza su lista de rutas que verifican el permiso en el servicio (`POST /api/autorizaciones`) y de las que aceptan uno de dos permisos (`GET /api/bitacora`, `PUT /api/usuarios/{id}/almacenes`, `GET /api/proyectos`), y su lista de módulos.

## 6. Cambio de alcance (aprobado por el usuario el 8 de octubre de 2026)

Salen de «Excluido» o de «Pospuesto» en [mvp-scope.md](../../product/mvp-scope.md):

| Antes | Ahora |
|---|---|
| Excluido: modo sin conexión y sincronización | **Incluido, al final** y limitado: solo en la app de Android del almacenista, solo su almacén, solo las funciones de FEAT-020 |
| Excluido: aplicación nativa | **Incluida**: app de Android con Capacitor que empaqueta la misma interfaz. Sin iPhone y sin tienda de aplicaciones |
| Excluido: notificaciones push | **Incluidas**: Web Push para las solicitudes de despacho, de traslado y de excedentes. Sin correo, SMS ni WhatsApp |
| Pospuesto: que un usuario vea un subconjunto de almacenes | **Incluido**: conjunto de almacenes por usuario (AC-36) |
| Pospuesto: periodo por apertura de un almacén de proyecto | **Lo resuelve el proyecto**: el reporte de cierre se pide por proyecto (sus fechas) |
| Fuera de alcance de la Fase 3: autorizar varias solicitudes a la vez | **Incluido** para despachos (DE-12) |
| Excluido: más gráficas que «Lo más usado» | Se mantiene, salvo el uso por proyecto del Inicio del supervisor (TB-05), que es una tabla con barras, no una gráfica nueva |

Siguen excluidos: iPhone nativo, tienda de aplicaciones, impresión directa a impresoras térmicas, notificaciones por tarea programada en el servidor (el aviso de inspección se ve en pantalla y, en la app de Android, como notificación local; P-15) y biometría.

## 7. Orden de construcción

1. **Lo del PDF del track y traspasos completamente funcionales:** FEAT-015 y la verificación de punta a punta de enviar, recibir, traspaso por Excel y recepción por lista (sección 9).
2. **FEAT-014:** despacho de EPP con aprobación, interruptor de autonomía y notificaciones push.
3. **FEAT-013:** proyectos, alta del trabajador con proyecto, proyecto en el vale, alerta de almacén sin proyecto, conjunto de almacenes por usuario e Inicio del supervisor con valor y uso por proyecto.
4. **FEAT-017 y FEAT-018:** bitácora por vale con PDF, y deudores con resguardo por proyecto y consumo.
5. **FEAT-016:** inspecciones y avisos configurables.
6. **FEAT-019:** búsqueda con espera, QR en PDF, diseño por dispositivo y estética.
7. **Casos especiales en pantalla:** supervisor con varios almacenes y trabajador con varios proyectos (el modelo de datos ya los soporta desde el paso 3).
8. **FEAT-020:** app de Android y operación sin conexión.

FEAT-013 y FEAT-014 tocan los dos la evaluación de la ENTREGA; si se construyen en paralelo, FEAT-013 entra primero a `movimientos` y FEAT-014 se rebasa sobre ella.

## 8. Situaciones límite que cruzan varias features

| Situación | Qué pasa | Reglas |
|---|---|---|
| Arranque de un mantenimiento: 40 contratistas piden su dotación a la vez | El almacenista arma cada entrega y la manda; el supervisor recibe una notificación agrupada y aprueba varias de un jalón | DE-12, NT-05 |
| Turno de noche, el supervisor de noche no responde | La solicitud vence a los 15 minutos; el almacenista puede reenviarla, llamar al supervisor para que dé su PIN en el mostrador o, si el Administrador prendió la autonomía, despachar | DE-09, DE-10, A-01 |
| Los dos supervisores (día y noche) reciben la misma solicitud | Resuelve el primero; al otro se le cierra la notificación y la pantalla dice quién la resolvió | NT-06, DE-11 |
| El supervisor despacha él mismo | Su captura cuenta como aprobación del despacho; un excedente de límite sigue necesitando a otro supervisor | DE-07, A-05 |
| Trabajador vigente sin proyecto activo (su proyecto ya cerró) | La entrega sale en amarillo con observación y cuenta como «Sin proyecto» | PR-10 |
| Trabajador en dos proyectos del mismo almacén | El almacenista elige el proyecto en la entrega | PR-09 |
| Supervisor con dos almacenes | Ve los dos en el Inicio y en reportes; opera en su almacén activo y lo cambia con el selector | AC-36 a AC-39 |
| Proyecto que pasa su fin estimado sin cerrarse | Sigue operando y aparece como «Fin estimado vencido» para que el Administrador lo extienda o lo cierre | PR-06 |
| Último proyecto de un almacén de tercer nivel se cierra | Aviso «Sin proyectos activos: considera inactivarlo» en Almacenes y en el Inicio del Administrador | PR-12 |
| Se pierde la señal en el mostrador | En la app de Android, lo que no pide aprobación sigue por la cola; el EPP de un almacén sin autonomía espera a que vuelva la señal | OF-08 a OF-12 |
| Dos equipos sin conexión del mismo almacén registran la misma pieza | El primero que sincroniza se guarda; el segundo va a conflictos para el supervisor | OF-20 |

## 9. Incongruencias encontradas al revisar

1. **FEAT-012 sin documento (resuelto).** El código tiene el valor del inventario (`service_valor.py`, reglas VI-01 a VI-07 en sus comentarios, migración `0009`) pero no hay `docs/features/FEAT-012-*.md`. La tabla 8.2 de las reglas sigue diciendo que `reportes.valor_inventario` está «no disponible» (AC-31). **Resuelto el 9 de octubre de 2026:** [FEAT-012](../../features/FEAT-012-valor-del-inventario.md) ya está escrito a partir del código y las reglas VI-01 a VI-07 están en las reglas de negocio.
2. **Estado de los traspasos.** [docs/README.md](../../README.md) y [mvp-scope.md](../../product/mvp-scope.md) dicen que FEAT-009 (traspasos por Excel) y `traspasos.recibir` están «sin construir», pero el código sí los tiene: `importacion/router_traspasos.py` con sus pruebas (`test_traspaso_lista.py`), `trasladar-con-lista.tsx` y `recibir-detalle.tsx` con filtro y progreso (commit `ed7ce82`). Falta TR-10 (descargar la lista). Está construido en el código, pero no se ha probado funcionando en el entorno desplegado: la lista de verificación de FEAT-015 lo cierra. Además, X-01 dice que el Almacenista no trae `traspasos.recibir` de inicio, mientras que la tabla 8.2, AC-31 y el script de datos de prueba sí se lo dan.
3. **Búsquedas.** [ui-ux.md](../../product/ui-ux.md) dice que todas las búsquedas esperan 300 ms (`useRetraso`), pero Consultar, Entregar, Devolver y Trasladar buscan solo con Enter, y Recibir usa 200 ms. FEAT-019 lo unifica.
4. **Etiquetas de piezas fuera del alcance.** `GET /api/etiquetas?tipo=piezas` lista piezas de todos los almacenes sin aplicar AC-06. Es un error del código actual: [FIX-001](../../fixes/FIX-001-etiquetas-de-piezas-sin-alcance.md).
5. **Aviso de inspección fijo.** E-11 usa la constante `DIAS_AVISO_INSPECCION = 7` en `movimientos/evaluador.py`. FEAT-016 la vuelve configurable.
6. **Inspecciones en tránsito.** Hoy se puede inspeccionar una pieza en tránsito o en mantenimiento; P-17 lo rechaza. Es un cambio de comportamiento.
7. **Alto valor por nombre.** `consulta/repository_seguimiento.py` identifica el alto valor por el **nombre** de la categoría (`CATEGORIAS_ALTO_VALOR`). Si alguien renombra la categoría, la tarjeta del Inicio deja de contar. FEAT-018 lo cambia por la marca `categoria.alto_valor` y el costo mínimo (AV-01).
8. **El principio del supervisor sin tiempo.** Las reglas dicen que el supervisor casi no tiene tiempo y que no valida cada vale (plática del 3 de octubre, min 42; F-04). La plática del 8 de octubre pide aprobar todo el EPP. Manda la plática nueva; el interruptor de autonomía (D-07) conserva la salida para los almacenes donde no haga falta.
9. **Firma antes de aprobar.** Las notas del track ponen la firma antes de mandar la solicitud. Se cambió el orden (D-08) para que la firma cubra solo lo aprobado.

## 10. Decisiones transversales tomadas al escribir los briefs

Propuestas; quedan firmes cuando el usuario revise las «Decisiones abiertas» de cada brief.

| # | Tema | Propuesta | Dónde |
|---|---|---|---|
| T-1 | **Qué es un proyecto «vigente»** | Para **entregar**, cuenta cualquier proyecto ACTIVO del trabajador, aunque haya pasado su fin estimado (PR-06, PR-08). Para **asignar** a un trabajador se ofrecen los ACTIVOS vigentes o por iniciar, no los vencidos. | FEAT-013, PR-02 |
| T-2 | **El costo que se deduce de un total** | Un total en pesos que cubre un solo artículo revela su costo unitario al dividirlo entre las unidades (RG-12). Donde un grupo tiene un solo artículo con costo, el valor en pesos se muestra como «—» para quien no tiene `catalogo.costos`. Aplica al Inicio del supervisor (TB-04 a TB-08), al resumen del vale (BT-05) y al consumo (DU-08). | FEAT-013, 017, 018 |
| T-3 | **Deuda contra consumo** | El consumo cuenta para el **proyecto** (D-13); la deuda es con el **almacén** que entregó (DU-02, AC-06). El supervisor de Midrex ve lo que sus trabajadores deben a Contratistas solo como número, sin el detalle del otro almacén. | FEAT-018 |
| T-4 | **Push al almacén que recibe** | La notificación informativa de un traslado (X-20) solo llega a quien activó avisos, que hoy es quien tiene `autorizaciones.resolver`. Para que llegue al almacenista que recibe de noche, NT-01 ofrece «Activar avisos» también a quien tiene `traspasos.recibir`. Con eso `POST /api/notificaciones/suscripciones` acepta `autorizaciones.resolver` o `traspasos.recibir` (`requiere_alguno`). | FEAT-014, 015 |
| T-5 | **Tope de alto valor** | `ALTO_VALOR_COSTO_MINIMO` vive en `.env`: cambiarlo exige reiniciar y no tiene pantalla. Basta para el MVP; una pantalla de ajustes generales queda pospuesta. | FEAT-018 |
| T-6 | **Inspeccionar en otro almacén del conjunto** | La lista de inspecciones abarca todo el conjunto (AC-37), pero inspeccionar es una escritura en el almacén activo (AC-38): la pantalla ofrece cambiar de almacén. | FEAT-016 |
| T-7 | **Prueba del guion del PDF** | Al construir FEAT-014, la prueba de integración del guion incluye el paso de aprobación del despacho (o corre en un almacén con autonomía), en el mismo cambio. | FEAT-014 |

## 11. Dependencias aprobadas

**Aprobadas por el usuario el 9 de octubre de 2026.** AGENTS.md prohíbe agregar dependencias que la tarea no pida; estas las piden los briefs de la iteración y ya tienen el visto bueno, así que la tarea que construya cada feature las instala sin volver a preguntar. Las del contenedor de Capacitor (`@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, `@capacitor/network`, `@capacitor/filesystem`, `@capacitor/share`) y `vitest` ya están instaladas. Faltan por instalar, cuando se construya su feature: `pywebpush`, `jspdf`, `jspdf-autotable`, la fuente en TTF, `@capacitor-community/sqlite`, `@capacitor/local-notifications` y el complemento de tareas en segundo plano. La columna «Alternativa» queda solo como referencia de lo que se descartó.

| Dependencia | Para qué | Alternativa descartada | FEAT |
|---|---|---|---|
| `pywebpush` (backend) | Firmar y cifrar las notificaciones Web Push | Hacerlo con `cryptography`, PyJWT y `httpx`, que ya están | 014 |
| `jspdf` y `jspdf-autotable` (frontend) | PDF del vale, del lote y de las etiquetas, también sin conexión en Android | `fpdf2` en el servidor (no funciona sin conexión) | 017, 019 |
| Fuente Poppins en TTF (archivo, no paquete) | jsPDF no lee WOFF | Usar la fuente Helvetica que trae jsPDF | 017, 019 |
| `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, `@capacitor-community/sqlite`, `@capacitor/network`, `@capacitor/local-notifications`, `@capacitor/filesystem`, `@capacitor/share` y un complemento de tareas en segundo plano | App de Android, base local cifrada, conexión, notificaciones locales, guardar y compartir el PDF | Ninguna: son la app | 020 |
| `vitest` (desarrollo, frontend) | Correr en TypeScript los mismos casos de prueba del evaluador que corre pytest (OF-16) | Probar el evaluador local solo a mano | 020 |

## 11 bis. Notas de FEAT-020 que afectan a otros documentos

- **WebView mínimo.** Tailwind CSS 4 pide un motor equivalente a Chrome 111 o superior. Es el requisito real de los equipos del almacén, más estricto que «Android 7 con WebView reciente» (pregunta 4 de la sección 12).
- **Kepler sin operación sin conexión en la primera versión:** ahí entra el inventario y no hay problema de señal.
- **El paquete de Contratistas** incluye a los trabajadores de los proyectos de sus almacenes hijos, porque Contratistas les entrega el EPP (D-13).
- **Sesión en la app.** La primera prueba de construcción de FEAT-020 es una prueba de concepto de la sesión con cookies en un equipo real: es el riesgo técnico más grande. `CapacitorCookies` queda desactivado salvo que haga falta, porque podría exponer las cookies `HttpOnly`.
- **`POST /api/sincronizacion/lotes`** verifica el permiso de cada operación en el servicio: entra a la lista de excepciones de AGENTS.md y de security-model.
- **`/v/:token` hoy exige sesión.** El trabajador sin cuenta no ve «Pendiente de sincronizar». Es una decisión abierta de FEAT-020, ligada a FEAT-001 (vale como prueba).
- **El responsable del vale sincronizado es quien lo capturó**, aunque la cola la suba otro usuario del equipo: la revisión de repetidos de `movimientos` compara contra quien capturó.

## 12. Preguntas que quedan para el track

1. ¿El EPP que se entrega **al contratar** (antes de que el trabajador entre a un mantenimiento) también pide aprobación, o solo el de un proyecto? Por ahora: también (D-06).
2. ¿Hay un tiempo máximo de espera aceptable en el mostrador? Por ahora: 15 minutos, igual que las autorizaciones.
3. ¿Los equipos Zebra del almacén tienen servicios de Google? Sin ellos funciona la app de Android, pero no las notificaciones dentro de ella (no se necesitan: las notificaciones son para el supervisor).
4. ¿Qué versión de Android y de Android System WebView traen los equipos del almacén? Capacitor necesita Android 7 o superior con un WebView reciente (ADR-014).
