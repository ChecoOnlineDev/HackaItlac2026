# Guía por rol: quién hace qué y por qué

Esta guía cuenta, rol por rol, cómo se recorre el sistema de control de herramientas y EPP (Reto IMHOTEP). Cada rol se lee como un recorrido continuo, de principio a fin; después hay un recorrido de punta a punta que une a todos (el guion del PDF del reto). Sirve para quien va a probar, demostrar o presentar el sistema.

Cómo leerla: si solo quieres probar el flujo completo, ve a la sección 2 (con qué usuario entrar) y luego a la sección 9 (el recorrido entre roles). Si quieres entender un rol, lee su sección completa. Las pantallas del almacenista, con más detalle, están en la [guía del almacenista](guia-almacenista.md).

Los códigos entre paréntesis (por ejemplo E-06 o AC-12) son reglas de [reglas-de-negocio.md](product/reglas-de-negocio.md). Los identificadores US-... son historias de [stories/](stories/). Cuando una historia dice «Propuesta», no existe todavía en los documentos: la escribí aquí para completar el rol.

---

## 1. Por qué hay cinco roles y por qué hay que probar con uno de cada uno

El sistema decide qué puede hacer cada persona por sus **permisos**, no por el nombre de su rol (AC-04). Un rol es un conjunto de permisos con nombre, y cada usuario tiene un solo rol (AC-02). El sistema nace con cinco roles (AC-03): el **Administrador**, que tiene todos los permisos, y los cuatro perfiles que pide el PDF del reto: **Almacenista, Supervisor, Compras y Recursos Humanos**.

Hay que tener un usuario de cada uno para probar el flujo completo porque **cada paso lo hace un rol distinto, a propósito**. Ninguna persona puede hacer todo el recorrido sola:

- Solo Recursos Humanos da de alta al trabajador.
- Solo Compras da de alta inventario y ve costos.
- Solo el almacén entrega, devuelve y traslada.
- Solo el Supervisor autoriza una excepción, y nunca puede autorizar la que él mismo capturó (A-05).

Esa separación es el control: quien registra no es quien autoriza, y quien compra no es quien entrega. Además, el traspaso exige **dos almacenistas de dos almacenes distintos** (uno envía y otro recibe, X-10), así que para la prueba completa se usan al menos dos cuentas de almacén.

---

## 2. Roles y usuarios de prueba

Los usuarios de prueba los carga el script de datos de prueba (`backend/app/modulos/acceso/datos_prueba.py`). **No se escriben aquí las contraseñas.** La contraseña de todos es el valor `CLAVE_DATOS_PRUEBA` del archivo `.env` de la raíz del repositorio. El PIN, que solo existe para el Administrador y el Supervisor, es el valor `PIN_DATOS_PRUEBA` del mismo archivo.

| Rol | Usuario de prueba | Almacén asignado | PIN | Para qué se usa en la prueba |
|---|---|---|---|---|
| Administrador | `admin` | Ninguno; opera todos | Sí | Ver todo el menú; en la práctica, no hay pantallas propias de administración (sección 4) |
| Supervisor | `supervisor` | Ninguno; opera todos | Sí | Autorizar excedentes, administrar el catálogo, ver reportes de todos los almacenes |
| Compras | `compras` | Ninguno; ve todos | No | Cargar inventario, catálogo, costos, etiquetas |
| Recursos Humanos | `rh` | Ninguno | No | Alta, reingreso y baja de trabajadores; ver adeudos |
| Almacenista Kepler | `almacenista` | Kepler (KEP) | No | Entregar, devolver, emitir no adeudo |
| Almacenista Contratistas | `alm_con` | Contratistas (CON) | No | Recibir el traspaso desde Kepler |
| Almacenista Midrex | `alm_mid` | Midrex (MID) | No | Operar el almacén de Midrex |
| Almacenista HYL | `alm_hyl` | HYL | No | Operar el almacén de HYL |
| Almacenista Laminador | `alm_lam` | Laminador (LAM) | No | Operar el almacén de Laminador |
| Almacenista Minas | `alm_min` | Minas (MIN) | No | Operar el almacén de Minas |

**Quién opera todos los almacenes y quién solo el suyo.** Cada usuario opera su almacén asignado y ve solo los movimientos de ese almacén, salvo que su rol tenga el permiso `almacenes.todos` (AC-06, RG-07). De inicio lo tienen el **Supervisor, Compras y el Administrador**; ellos eligen el almacén al operar. El **Almacenista** y **Recursos Humanos** no lo tienen: el almacenista opera solo su almacén (y un almacenista opera un solo almacén a la vez), y RH no opera ningún almacén. No existen subconjuntos de almacenes por usuario: se ve el propio o todos.

Los almacenes de prueba son: Kepler (central), Contratistas (depende de Kepler) y cuatro de proyecto (Midrex, HYL, Laminador y Minas) que dependen de Contratistas. Un almacén puede tener varios almacenistas (operan las 24 horas), cada uno con su propia cuenta.

---

## 3. Qué puede y qué no puede cada rol

Resumen en lenguaje de persona, según la tabla 8.2 de las reglas (entre paréntesis, la clave del permiso, una sola vez).

| Capacidad | Admin | Supervisor | Almacenista | Compras | RH |
|---|:-:|:-:|:-:|:-:|:-:|
| Entregar y pedir autorización (`entregas.crear`) | Sí | Sí | Sí | No | No |
| Recibir devoluciones (`devoluciones.crear`) | Sí | Sí | Sí | No | No |
| Enviar y recibir traspasos (`traspasos.operar`) | Sí | Sí | Sí | No | No |
| Emitir el vale de no adeudo (`no_adeudo.emitir`) | Sí | Sí | Sí | No | No |
| Autorizar o rechazar excedentes (`autorizaciones.resolver`) | Sí | Sí | No | No | No |
| Inspeccionar una pieza o marcarla No apta (`piezas.inspeccionar`) | Sí | Sí | Sí | No | No |
| Ajustar la vigencia de una inspección (`piezas.ajustar_vigencia`) | Sí | Sí | No | No | No |
| Registrar entradas e importar inventario (`inventario.entradas`) | Sí | No | No | Sí | No |
| Ver existencias de todos los almacenes (`inventario.ver`) | Sí | Sí | Sí | Sí | No |
| Ver categorías, artículos y piezas (`catalogo.ver`) | Sí | Sí | Sí | Sí | No |
| Crear y editar categorías y artículos (`catalogo.administrar`) | Sí | Sí | No | Sí | No |
| Ver y capturar costos (`catalogo.costos`) | Sí | No | No | Sí | No |
| Ver la ficha básica del trabajador (`trabajadores.ver`) | Sí | Sí | Sí | No | Sí |
| Ver CURP y NSS (`trabajadores.ver_datos_personales`) | Sí | No | No | No | Sí |
| Dar de alta, reingresar, credencial y cancelar baja (`trabajadores.administrar`) | Sí | No | No | No | Sí |
| Iniciar la baja (`trabajadores.iniciar_baja`) | Sí | Sí | Sí | No | Sí |
| Consultar vales (`vales.ver`) | Sí | Sí | Sí | Sí | No |
| Cancelar los vales propios (`vales.cancelar`) | Sí | Sí | Sí | Sí | No |
| Cancelar los vales de cualquiera (`vales.cancelar_todos`) | Sí | Sí | No | No | No |
| Reporte de existencias y de movimientos | Sí | Sí | Sí | Sí | No |
| Reporte de adeudos | Sí | Sí | Sí | No | Sí |
| Reporte de consumo | Sí | Sí | No | Sí | No |
| Operar cualquier almacén (`almacenes.todos`) | Sí | Sí | No | Sí | No |
| Asignar personal a almacenes (`almacenes.asignar_personal`) | Sí | Sí | No | No | No |
| Imprimir hojas de QR y credenciales (`etiquetas.imprimir`) | Sí | Sí | No | Sí | Sí |
| Administrar roles, permisos y usuarios (`acceso.administrar`) | Sí | No | No | No | No |

Cuatro cosas **ningún rol** puede hacer, ni el Administrador, porque no son permisos (AC-07): editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale.

Todo permiso de acción incluye ver su propio módulo: quien puede entregar ve la ficha básica del trabajador y las existencias.

---

## 4. Administrador

**Perfil.** Es quien configura el sistema y decide qué puede hacer cada rol. Tiene todos los permisos, así que ve todos los menús y puede hacer cualquier operación, pero no es quien opera el día a día.

**Qué ve al entrar.** Todo el menú: Operación (Entregar, Devolver, Trasladar, Recibir), Consulta, Supervisión (Autorizaciones), Personas, Inventario y catálogo, y Reportes. Como no opera un almacén fijo, en las operaciones elige el almacén.

**Qué existe y qué no (verificado).**

| Parte | Estado |
|---|---|
| Todas las pantallas operativas | Sí, por tener todos los permisos |
| Alta, edición, desactivación de usuarios y restablecer contraseña | Existe en el servidor (`/api/usuarios`), **sin pantalla** |
| Asignar o mover personal entre almacenes | Existe en el servidor (`/api/personal` y `PATCH /api/usuarios/{id}/almacen`), **sin pantalla** |
| Crear roles y activar o quitar permisos desde pantalla | **Pospuesto** (parte pendiente de FEAT-006). Los cinco roles se cargan con el script de datos de prueba |
| Tablero general por almacén | Pospuesto |

**Funcionalidades clave.**
- Administrar usuarios (alta, cambio de rol, baja lógica, restablecer contraseña y PIN) por el servidor.
- Asignar personal a almacenes (también lo puede hacer el Supervisor).
- Hacer cualquier operación del sistema cuando hace falta (por ejemplo, ajustar la vigencia de una inspección).
- Garantizar que siempre exista al menos un administrador activo (AC-09).

**Flujo principal (puesta en marcha de un equipo nuevo).**
1. Se carga el script de datos de prueba: queda cada rol con sus permisos y un usuario por rol.
2. El Administrador entra con `admin` y su contraseña; el menú le muestra todo.
3. Crea al usuario nuevo (por el servidor): nombre, usuario, contraseña, rol y, si el rol no opera todos los almacenes, su almacén. Si el rol puede autorizar, también un PIN distinto de la contraseña.
4. Si después hay que mover a un almacenista de un almacén a otro, se cambia su almacén (también lo puede hacer el Supervisor). El cambio aplica en su siguiente petición y queda registrado con el almacén anterior y el nuevo (AC-13).
5. Si alguien olvida su contraseña, se restablece (y, si se manda, también el PIN); eso reinicia los bloqueos.
6. Para dejar de dar acceso a alguien, se inactiva su usuario; sus vales anteriores se conservan.

**Casos límite.**
| Situación | Qué hace el sistema |
|---|---|
| Intentar quitar al último administrador activo | Lo rechaza (AC-09) |
| Alta de un rol que opera un almacén sin indicar su almacén | Lo rechaza |
| Dar almacén a un rol que ya opera todos | Lo rechaza |
| Inactivar un rol con usuarios asignados | No se permite hasta reasignarlos (AC-11) |
| El Administrador intenta autorizar su propia solicitud | No puede (A-05) |

**Historias de usuario.**
- Como usuario del sistema, quiero entrar y ver solo lo que permite mi rol, para trabajar sin acceso a lo que no me toca (**US-ACC-001**).
- Como administrador, quiero dar de alta usuarios y asignarles rol y almacén, para que cada persona tenga su propia cuenta (FEAT-006; en el servidor, sin pantalla).
- Como administrador, quiero crear roles y activar o quitar permisos desde una matriz, para ajustar el sistema sin un programador (**FEAT-006**, pospuesta).
- Como administrador, quiero ver un tablero con una pestaña por almacén, para vigilar la operación (pospuesta, sin brief).
- *Propuesta:* Como administrador, quiero ver un registro de los cambios de permisos y de almacén, para saber quién cambió qué (AC-10, AC-13 lo garantizan en el servidor; no hay pantalla).

**Por qué tiene este flujo.** El PDF pide perfiles con permisos distintos, y el equipo decidió que los roles son datos y no código (ADR-007), para que cambiar lo que puede un rol no requiera programar. El Administrador es el único con `acceso.administrar` para que nadie más se dé permisos a sí mismo. En el MVP solo se entrega la base (permisos por clave, verificados en el servidor en cada endpoint), y se acepta como riesgo que usuarios y roles se manejen por script o por el servidor, sin pantalla.

---

## 5. Almacenista

**Perfil.** Está en el mostrador del almacén (celular o tableta, con cámara o pistola lectora). Necesita entregar, devolver y trasladar en segundos, y saber qué debe cada trabajador, sin capacitación previa. Opera **un solo almacén**, el que tiene asignado. Los almacenes trabajan las 24 horas con varios almacenistas, cada uno con su cuenta.

**Qué ve al entrar.** Arriba, el nombre de su almacén y su usuario; abajo, cinco botones grandes: **Entregar, Devolver, Trasladar, Recibir** (con un número cuando hay traspasos en camino) y **Consultar**. Con **Menú** llega a lo demás: Mis movimientos de hoy, Trabajadores, Inventario, Categorías, Artículos y los reportes de existencias, movimientos y adeudos. No ve costos, CURP, NSS, ni entradas de inventario, ni autorizaciones.

**Funcionalidades clave.**
- Entregar por escaneo con semáforo (verde, amarillo, naranja, rojo) y firma del trabajador en pantalla.
- Pedir autorización al supervisor cuando un renglón sale naranja.
- Devolver por escaneo, con la condición de regreso.
- Enviar y recibir traspasos entre almacenes.
- Inspeccionar piezas y marcarlas como No aptas.
- Iniciar la baja y emitir el vale de no adeudo.
- Consultar quién tiene qué; cancelar un vale propio mal capturado.

**Flujo principal: entregar.**
1. Entra con su usuario y contraseña; ve su inicio.
2. Toca **Entregar**.
3. Escanea la credencial del trabajador (o escribe su número o nombre). Aparece su ficha: foto, nombre, número, puesto, vigencia y lo que ya tiene. Compara la foto con la persona.
4. Si el trabajador no está vigente (contrato vencido, en baja o inactivo), la ficha sale en rojo con el motivo y no se le puede entregar nada (E-02). Fin.
5. Escanea los artículos, uno tras otro. Cada lectura es un renglón con su color y sus motivos. Escanear no mueve nada del inventario (E-28).
6. Resuelve cada renglón: verde sigue; amarillo se lee y, si lo pide, se escribe una observación; naranja se **pide autorización** (flujo siguiente) o se quita; rojo se quita porque no hay forma de entregarlo.
7. Cuando no queda rojo ni naranja sin autorizar, toca **Continuar** (SM-03).
8. El trabajador firma con el dedo y el almacenista toca **Confirmar entrega**.
9. El servidor revalida todo (RG-08). Si algo cambió, regresa a la lista con el renglón marcado; si todo cuadra, emite el vale con folio y QR (por ejemplo `KEP-ENT-000123`). Ahí bajan las existencias y sube el resguardo del trabajador.
10. Imprime el vale o toca **Nueva entrega**.

**Otros flujos frecuentes.**

*Pedir autorización (renglón naranja).* Toca **Pedir autorización**, escribe el motivo y elige: «El supervisor está aquí» (el supervisor teclea su usuario y su PIN en ese celular) o «Enviar a su celular» (la solicitud le llega y la pantalla del almacenista se actualiza sola). Si se autoriza, sigue la entrega y el vale muestra quién validó (A-04). Si se rechaza o vence, quita el renglón y entrega lo demás (A-07).

*Devolver.* **Devolver**, escanea la pieza (la abona a su titular aunque la traiga otra persona, V-01) o la credencial para elegir material por cantidad (V-03). Elige la condición: Bueno, Desgaste por uso o Dañado (observación obligatoria; la pieza queda No apta; nunca hay cargo al trabajador, V-05). Confirma y sale el vale de devolución.

*Trasladar y recibir.* **Trasladar**: elige el almacén de destino, escanea, confirma; el material queda En tránsito (X-01, X-06). **Recibir** (en el almacén de destino): abre el traspaso o escanea su QR, marca lo que llegó y confirma; lo no recibido sigue en camino (X-13).

*Baja del trabajador.* En la ficha, **Vale de no adeudo**: el trabajador pasa a Baja en proceso, el sistema lista sus pendientes de todos los almacenes, el almacenista recibe las devoluciones y, con todo en cero, emite el vale; el trabajador queda Inactivo (B-01 a B-04, B-08).

*Inspeccionar.* En la ficha de la pieza, **Inspeccionar** (Apto o No apto) o **Marcar No apta** con observación (P-01, P-03).

*Cancelar un error.* **Mis movimientos de hoy** → el vale → **Cancelar vale** (o **Cancelar y rehacer**) con motivo (K-01, K-05).

**Casos límite y qué hace el sistema.**

| Situación | Qué hace el sistema | Regla |
|---|---|---|
| Arnés No apto o sin inspección vigente | Rojo; no se puede entregar ni con autorización | E-05, E-06, SM-04 |
| Cantidad mayor al límite del artículo | Naranja; pide autorización | E-07, L-04 |
| Cantidad inusualmente alta | Amarillo; pide confirmar la cantidad | E-27 |
| Pieza que está con otro trabajador o en otro almacén | Rojo; muestra dónde está | E-03 |
| Código desconocido | Rojo | E-01 |
| Devolución de un código ajeno a la empresa | Rojo; no se recibe | V-12 |
| Devolver una pieza que no está a nombre de nadie | Amarillo; no hay movimiento | V-02 |
| Intentar autorizarse a sí mismo | No se permite | A-05 |
| Emitir no adeudo con pendientes | Muestra lo que falta y no lo emite | B-02 |
| Cancelar un vale cuyo contenido ya cambió de lugar | No se cancela y explica por qué | K-03 |
| Se va la red | Banda «Sin conexión»; el borrador se conserva; no se puede confirmar hasta tener red | Alcance |
| Cinco intentos de contraseña fallidos | Bloqueo de cinco minutos | US-ACC-001 |

**Historias de usuario.**
- Como almacenista, quiero entregar equipo escaneando la credencial y los artículos, para registrar la entrega en segundos y sin escribir (**US-ENT-001**).
- Como almacenista, quiero que el sistema me impida entregar equipo de alturas no apto o sin inspección vigente, para que nadie trabaje con equipo inseguro (**US-ENT-002**).
- Como almacenista, quiero registrar la inspección de una pieza y marcarla no apta si veo un daño (**US-INS-001**).
- Como almacenista, quiero que el trabajador firme en la pantalla y que la entrega quede en un vale con folio (**US-ENT-003**).
- Como almacenista, quiero recibir una devolución escaneando el equipo (**US-DEV-001**).
- Como almacenista de Kepler, quiero ver lo que un trabajador tiene pendiente y emitir su vale de no adeudo (**US-BAJ-001**).
- Como almacenista del almacén de origen, quiero enviar artículos a otro almacén escaneándolos (**US-TRS-001**); como almacenista del destino, quiero recibirlos escaneando su QR (**US-TRS-002**).
- Como usuario de cualquier rol, quiero escanear o escribir y ver quién tiene un artículo (**US-CON-001**).
- Como almacenista, quiero cancelar un vale que capturé mal sin perder el historial (**US-CAN-001**).
- Como almacenista, quiero ver los reportes de existencias, movimientos y adeudos de mi almacén (**US-REP-001**).
- *Propuesta:* Como almacenista, quiero ver mis traspasos en camino con un contador, para no olvidar recibirlos.

**Por qué tiene este flujo.**
- *Problema que resuelve.* Hoy el almacén se lleva en libreta, se pierde y nadie sabe quién tiene qué (PRD, sección 2). Escanear la credencial y los artículos convierte cada salida en un vale foliado y firmado, sin escribir (objetivos O1 a O3).
- *Reglas que lo respaldan.* El semáforo bloquea solo lo que el PDF o la seguridad exigen; lo demás se resuelve con observación. Un rojo de seguridad no lo autoriza nadie en el mostrador (SM-04), y una devolución nunca se bloquea porque recuperar el equipo es prioritario (SM-05). Nada se descuenta hasta confirmar, y el vale se guarda completo o no se guarda (E-28, RG-09).
- *Por qué no lo hacen otros.* Compras y RH no entregan porque quien compra o contrata no debe ser quien entrega. El almacenista no autoriza excedentes ni ve costos, CURP o NSS: el control de excepciones queda en otra persona (A-05) y los datos reservados solo en quien los necesita (RG-12, RG-13).

---

## 6. Supervisor

**Perfil.** Responsable de la operación en campo. Necesita autorizar excepciones sin ir al almacén y revisar lo irregular cuando tenga tiempo. Usa sobre todo el celular.

**Qué ve al entrar.** Su inicio muestra **Autorizaciones** con un contador de solicitudes por resolver, y los botones de operación de almacén (Entregar, Devolver, Trasladar, Recibir, Consultar). En el menú tiene además Trabajadores, Inventario, Categorías, Artículos, Etiquetas y los cuatro reportes (existencias, movimientos, adeudos y consumo). No ve Entradas ni Importar (son de Compras), ni costos, ni CURP y NSS.

**Funcionalidades clave.**
- Autorizar o rechazar excedentes y entregas restringidas, desde su celular o con su PIN en el mostrador.
- Operar cualquier almacén (elige cuál).
- Administrar el catálogo (categorías, artículos, requisitos, límites, inactivar).
- Ajustar la vigencia de una inspección, con motivo.
- Cancelar los vales de cualquiera.
- Asignar y mover personal entre almacenes (por el servidor; sin pantalla todavía).
- Imprimir credenciales y hojas de QR.
- Reportes de todos los almacenes, incluido el de consumo, y rastrear quién tocó un equipo.

**Flujo principal: autorizar un excedente.**
1. Un almacenista pide una autorización desde un renglón naranja; la solicitud llega con el motivo.
2. Si el supervisor está en el almacén, el almacenista le pasa el celular; el supervisor escribe su usuario y su **PIN** (distinto de su contraseña) y la solicitud queda autorizada al momento.
3. Si está en campo, abre **Autorizaciones** en su celular y ve la lista de solicitudes pendientes, cada una con quién la pidió, qué artículo, cuánto, el motivo y el detalle del excedente (por ejemplo, «límite 2, tiene 2, pide 1»).
4. Toca **Autorizar** o **Rechazar**.
5. La pantalla del almacenista se actualiza sola y sigue con la entrega.
6. La autorización vale solo para ese vale y se usa una sola vez; no cambia el límite del artículo (A-03). El vale muestra al supervisor como «Validó» (A-04).

**Otros flujos frecuentes.**
- *Catálogo.* Categorías → plantilla de reglas; Artículos → crear con la plantilla de su categoría y ajustar límite, requisitos especiales (inspección vigente, autorización en cada entrega) y su motivo; inactivar con motivo obligatorio o reactivar (CF-01 a CF-13). El costo lo captura solo Compras.
- *Ajustar la vigencia de una inspección.* En la ficha de la pieza, **Ajustar vigencia**, nueva fecha y motivo obligatorio; queda en el historial (P-07).
- *Rastrear una desaparición.* Reporte de Movimientos filtrado por usuario, artículo, almacén y periodo, más el historial de la pieza (C-11).
- *Cancelar el vale de otro.* Abre el vale y lo cancela con motivo (K-01).
- *Operar un almacén.* Elige el almacén y usa Entregar, Devolver, Trasladar y Recibir como un almacenista.
- *Asignar personal a un almacén.* Por el servidor (`/api/personal`); aplica en la siguiente petición del usuario (AC-12, AC-13).

**Casos límite y qué hace el sistema.**

| Situación | Qué hace el sistema | Regla |
|---|---|---|
| El supervisor quiere autorizar su propio vale | No puede | A-05 |
| Le piden autorizar una pieza no apta o sin inspección | No se manda a autorización; solo una inspección la resuelve | SM-04, A-06 |
| PIN incorrecto cinco veces | Bloqueo de cinco minutos | Parámetros generales (5 intentos, 5 minutos) |
| La solicitud vence sin respuesta | El almacenista quita el renglón y entrega lo demás | A-07 |
| Cambiar el control o retorno de un artículo que ya tiene movimientos | Aparece bloqueado, con explicación | CF-05 |
| Eliminar un artículo con movimientos | No se permite; se inactiva | CF-12 |

**Historias de usuario.**
- Como supervisor, quiero que el sistema detenga las entregas que superan el límite de un artículo, para controlar el consumo excesivo (**US-LIM-001**).
- Como supervisor, quiero autorizar o rechazar un excedente desde mi celular o con mi PIN, para no detener la operación (**US-AUT-001**).
- Como responsable del catálogo, quiero marcar artículos para que cada entrega pida autorización (**US-ESP-001**), crear categorías (**US-CAT-001**), administrar artículos (**US-CAT-002**) e inactivar y reactivar (**US-CAT-003**).
- Como supervisor, Compras o RH, quiero reportes de existencias, movimientos y adeudos (**US-REP-001**), y como supervisor o Compras, el de consumo (**US-REP-002**).
- Como supervisor, quiero cancelar vales de cualquiera (**US-CAN-001**, parte de supervisor).
- *Propuesta:* Como supervisor, quiero ver la lista de revisión de excepciones y diferencias (C-10; pospuesta en el alcance).
- *Propuesta:* Como supervisor, quiero dar una pieza por perdida o de baja definitiva (P-05; pospuesta).

**Por qué tiene este flujo.** El PDF exige que un excedente de límite se bloquee hasta que el supervisor lo autorice (función 6). El supervisor no tiene que estar en el almacén: autoriza desde su celular o con su PIN. El control es doble: A-05 impide que quien captura se autorice y SM-04 impide que nadie, ni el supervisor, autorice un rojo de seguridad. Por eso también el PIN es distinto de la contraseña: el PIN autoriza en un dispositivo ajeno y no debe abrir sesión. Y es el único rol operativo con permiso de cancelar vales ajenos y de ajustar vigencias, porque son decisiones que corrigen o relajan un control y deben quedar en alguien de mayor responsabilidad.

---

## 7. Compras

**Perfil.** Responsable de abastecer, mantener el catálogo y saber cuánto vale lo que hay. Trabaja en computadora y no opera el mostrador.

**Qué ve al entrar.** Como no opera un almacén, su inicio muestra directamente: Mis movimientos de hoy, Inventario, Entradas, Importar, Categorías, Artículos, Etiquetas y los reportes de Existencias, Movimientos y Consumo, además de Consultar. No ve Entregar, Devolver, Trasladar ni Recibir, ni Trabajadores, ni Adeudos, ni Autorizaciones.

**Funcionalidades clave.**
- Registrar entradas de inventario (almacén, artículos y piezas con su código, marca y serie).
- Importar inventario desde una tabla de Excel con vista previa.
- Administrar el catálogo, incluido el **costo** (solo Compras lo ve y captura).
- Ver existencias de todos los almacenes.
- Imprimir hojas de QR de piezas, estantes y credenciales.
- Reportes de existencias, movimientos y consumo.

**Flujo principal: dar de alta inventario.**
1. Entra con `compras` y su contraseña.
2. Si el artículo no existe, entra a **Artículos** y lo crea: elige la categoría, el formulario toma la plantilla de reglas, ajusta límite y requisitos, y captura el costo (solo Compras puede). Guarda.
3. Entra a **Entradas** → nueva entrada. Elige el almacén (Kepler por defecto, porque las compras entran por Kepler, I-01).
4. Agrega renglones escaneando o buscando el artículo. Por cantidad: captura la cantidad. Por pieza: captura o escanea el código de cada pieza, su marca y su serie (I-02).
5. Si la pieza requiere inspección, captura la inspección inicial o la deja pendiente (queda sin poder entregarse, I-03).
6. Confirma. El sistema emite un vale de entrada con folio y suben las existencias del almacén elegido.
7. Entra a **Etiquetas** para imprimir los QR de las piezas nuevas y de los estantes, desde el navegador.

**Otros flujos frecuentes.**
- *Importación.* Importar → pegar la tabla o subir el archivo → indicar qué columna es cada dato → vista previa (filas válidas, con error y artículos nuevos) → confirmar; se crea un vale de entrada por almacén. Las filas con error no se importan y se listan con su motivo (I-06).
- *Revisar faltantes.* Reportes de Existencias y de Consumo (cuánto se consume por artículo, periodo, almacén y trabajador).
- *Imprimir credenciales.* Etiquetas → credenciales, completa o solo QR; también desde la ficha del trabajador cuando su rol la puede abrir (ver incongruencia 6 de la sección 11).
- *Cancelar una entrada propia.* Mis movimientos de hoy → el vale → Cancelar, con motivo (K-04).

**Casos límite.**

| Situación | Qué hace el sistema | Regla |
|---|---|---|
| Entrada de un artículo inactivo | Se rechaza | I-09 |
| Código de pieza repetido | Se rechaza | I-02 |
| Un renglón con problema | Se marca; no se guarda nada hasta corregirlo | RG-09 |
| Fila de importación con categoría desconocida | Se elige una categoría para esas filas | Flujo 5 |
| Cancelar una entrada cuyo contenido ya se entregó | No se cancela | K-03 |

**Historias de usuario.**
- Como Compras, quiero registrar lo que entra a un almacén, para que haya existencias que entregar (**US-INV-001**).
- Como Compras, quiero cargar el inventario pegando una tabla de Excel (**US-IMP-001**).
- Como Compras o RH, quiero imprimir hojas de QR para piezas, estantes y credenciales (**US-ETQ-001**).
- Como responsable del catálogo, quiero crear categorías y artículos (**US-CAT-001**, **US-CAT-002**, **US-CAT-003**).
- Como supervisor o Compras, quiero saber cuántos consumibles se consumen (**US-REP-002**).
- *Propuesta:* Como Compras, quiero ver el valor del inventario por almacén (FEAT-002, `reportes.valor_inventario`, segunda ola).
- *Propuesta:* Como Compras, quiero fijar mínimos por almacén y recibir la alerta en rojo (FEAT-004, I-05, segunda ola).

**Por qué tiene este flujo.** El inventario nace solo con una entrada: nadie edita saldos (RG-01), así que hay trazabilidad desde el primer día. El costo solo lo ve Compras (RG-12) porque es información reservada; por eso el vale nunca lleva costos. El PRD pide que la empresa conozca cuánto vale lo que tiene y que el catálogo se cambie sin programador (O7). Compras no entrega ni autoriza: la compra y la salida las hacen personas distintas.

---

## 8. Recursos Humanos

**Perfil.** Contrata y finiquita trabajadores. Necesita registrar a cada persona, saber si tiene pendientes antes de finiquitarla y proteger los datos personales. Usa computadora o celular. De inicio **no ve el inventario**.

**Qué ve al entrar.** Como no opera un almacén, su inicio muestra: Trabajadores, Alta de trabajador, Etiquetas, Reporte de Adeudos y Consultar. No ve existencias, catálogo ni vales.

**Funcionalidades clave.**
- Alta y reingreso de trabajadores con su periodo de contrato.
- Ligar la credencial de la planta, o generar un QR propio.
- Foto opcional tomada con la cámara.
- Ver CURP y NSS (solo RH).
- Iniciar y cancelar una baja; ver «Con pendientes» o «No adeudo emitido».
- Imprimir o descargar la credencial (completa o solo QR).
- Reporte de adeudos.

**Flujo principal: dar de alta a un trabajador.**
1. Entra con `rh` y su contraseña; va a **Alta de trabajador**.
2. Escribe el número de empleado.
3. Si ya existe, el sistema muestra a la persona y sus pendientes y ofrece **Reingresar** (T-02). Si no existe, captura nombre, puesto, área u obra y periodo del contrato (inicio y fin, T-03); opcional, tallas, CURP o NSS.
4. Liga la credencial: escanea la de la planta o genera un QR propio para imprimir (T-05).
5. Opcionalmente toma la foto con la cámara o sube una imagen (T-09).
6. Guarda: el trabajador queda Activo y vigente (T-07). Se abre su ficha.
7. Como tiene permiso de etiquetas y la credencial está ligada, puede imprimirla o descargarla en PNG (completa o solo QR).

**Otros flujos frecuentes.**
- *Reingreso.* Mismo número de empleado: se registra el nuevo periodo, la persona se reactiva y conserva historial y pendientes (T-02, US-TRB-002).
- *Baja.* Ficha → **Iniciar baja**: el trabajador pasa a Baja en proceso y el sistema muestra sus pendientes de todos los almacenes. Cuando el almacén emite el vale de no adeudo, RH ve «No adeudo emitido» y puede finiquitar (B-09). RH puede cancelar una baja en proceso (B-07).
- *Consultar situación.* Ficha o reporte de Adeudos (T-08).

**Casos límite.**

| Situación | Qué hace el sistema | Regla |
|---|---|---|
| Número de empleado repetido | Muestra a la persona y ofrece reingreso | T-02 |
| Fin de periodo anterior al inicio | Lo rechaza con el campo marcado | Flujo 2 |
| Credencial ya ligada a otra persona | Lo rechaza y dice de quién es | Flujo 2 |
| Sin foto | Aviso «Sin foto registrada»; no impide entregar | T-09 |
| Salir sin guardar | No se crea nada | Flujo 2 |
| Finiquitar con pendientes | RH ve «Con pendientes» | B-09 |

**Historias de usuario.**
- Como RH, quiero registrar a un trabajador con su periodo de contrato y ligar su credencial (**US-TRB-001**).
- Como RH, quiero reingresar a un trabajador con un nuevo periodo (**US-TRB-002**).
- Como RH, quiero imprimir hojas de QR y la credencial del trabajador (**US-ETQ-001**).
- Como RH, quiero ver el reporte de adeudos (**US-REP-001**).
- *Propuesta:* Como RH, quiero saber desde mi celular, antes de finiquitar, si el trabajador tiene pendientes (T-08, B-09; cubierto por la ficha y el reporte).
- *Propuesta (pospuesta):* Como RH, quiero importar trabajadores desde Excel.

**Por qué tiene este flujo.** El problema que plantea el reto es que los trabajadores se van sin devolver y regresan en otro contrato acumulando pendientes. RH es quien conoce el contrato, por eso es el único que da de alta, reingresa y ve CURP y NSS (RG-13); el almacenista solo ve nombre, número, puesto, área, vigencia y foto. A cambio, RH no ve el inventario. La regla B-09 (no se finiquita sin vale de no adeudo) cierra el ciclo: RH decide la baja, pero no puede ignorar lo que el trabajador debe.

---

## 9. Recorrido de punta a punta: el guion del PDF

Es la prueba que describe el PDF (p. 2) y que el [alcance del MVP](product/mvp-scope.md) llama flujo principal. Cada paso dice con qué usuario de prueba hacerlo. Antes de empezar: base con datos de prueba cargados y `.env` con `CLAVE_DATOS_PRUEBA` y `PIN_DATOS_PRUEBA`.

| Paso | Quién (usuario) | Qué hace | Qué responde el sistema | Regla |
|---|---|---|---|---|
| 0 | `compras` | Si hace falta, da de alta o confirma existencias en Kepler: un arnés por pieza, EPP y una herramienta | Vale de entrada con folio; suben las existencias de Kepler | I-01, I-02 |
| 1 | `rh` | Da de alta a un trabajador nuevo con periodo vigente, liga su credencial, toma foto, imprime la credencial | Trabajador Activo y vigente; credencial lista para escanear | T-03, T-05, T-07 |
| 2 | `almacenista` (Kepler) | Entrega EPP y una herramienta escaneando credencial y artículos; el trabajador firma | Renglones verdes; vale de entrega con folio `KEP-ENT-...` y QR; baja el inventario y sube el resguardo | E-20, E-28, F-02, RG-06 |
| 3 | `almacenista` (Kepler) | Intenta entregar un arnés marcado No apto (o sin inspección vigente) | Renglón **rojo**; no se puede entregar ni pedir autorización | E-05, E-06, SM-04, A-06 |
| 4 | `almacenista` (Kepler) | Intenta una entrega que excede el límite de un artículo y pide autorización con un motivo | Renglón **naranja**; la entrega queda bloqueada hasta que el supervisor responda | E-07, L-04, A-02 |
| 5 | `supervisor` | Autoriza con su PIN en el celular del almacenista, o desde **Autorizaciones** en su propio celular | La autorización queda ligada a ese vale; el renglón pasa a autorizado; el vale muestra «Validó» | A-01, A-03, A-04 |
| 6 | `almacenista` (Kepler) | Termina la entrega con la firma del trabajador | Vale emitido con el excedente autorizado | SM-03, F-02 |
| 7 | `almacenista` (Kepler) | **Trasladar** a Contratistas (ruta habitual) escaneando los artículos | Vale de traspaso con folio y QR; el material queda En tránsito y sale de Kepler | X-01, X-03, X-06 |
| 8 | `alm_con` | **Recibir**: abre el traspaso o escanea su QR, marca lo recibido y confirma | Existencias entran a Contratistas; el traspaso queda Recibido; si falta algo, queda «con diferencias» | X-10, X-11, X-13 |
| 9 | `rh` | Abre la ficha del trabajador y toca **Iniciar baja** (o lo hace el almacenista al pedir su no adeudo) | El trabajador pasa a Baja en proceso y ya no recibe entregas | B-01 |
| 10 | `almacenista` (Kepler) | Ve los pendientes de todos los almacenes e intenta **Emitir vale de no adeudo** | Lista de pendientes (retornables en resguardo); no lo emite mientras haya algo | B-02, B-03 |
| 11 | `almacenista` (Kepler) | Recibe las devoluciones por escaneo, con su condición | Baja el resguardo; vales de devolución | V-01, V-04 |
| 12 | `almacenista` (Kepler) | Con todo en cero, emite el vale de no adeudo | Vale con folio; trabajador Inactivo | B-04, B-08 |
| 13 | `rh` | Abre la ficha o el reporte de adeudos | Ve «No adeudo emitido» y puede finiquitar | B-09 |

Para el paso 3 hay que tener un arnés en Kepler con la inspección vencida o marcada No apta; el almacenista puede marcarla desde su ficha (P-03). Para el paso 4 hay que usar un artículo con límite configurado (el supervisor o Compras lo fijan en el catálogo).

**Por qué son estos usuarios.** Cada paso cae en un permiso que solo tiene el rol indicado: dar de alta trabajadores (RH), cargar inventario (Compras), entregar y trasladar (almacén), autorizar (Supervisor, y nunca quien capturó). El traspaso necesita dos almacenistas de almacenes distintos (`almacenista` en Kepler, `alm_con` en Contratistas). Si se prueba todo con `admin`, el recorrido funciona pero **no se demuestra el control de roles**, y la autorización seguiría necesitando a otra persona (A-05).

---

## 10. Qué NO existe todavía

Para no confundir a quien pruebe. Fuente: [mvp-scope.md](product/mvp-scope.md).

**Excluido explícitamente:**
- Modo sin conexión y sincronización. La app instalable (PWA) no lo cambia: sin red no se opera; el borrador se conserva en el dispositivo.
- Aplicación nativa, lectura de huella o biometría.
- Notificaciones push, correo, SMS o WhatsApp.
- Integración con nómina, torniquetes o sistemas de la planta.
- Descuentos, cargos o finiquitos; la empresa no cobra el daño.
- Órdenes de compra, proveedores y facturas.
- Firma electrónica avanzada y constancias NOM-151.
- Impresión directa a impresoras térmicas (se imprime desde el navegador).
- **Matriz editable de roles y permisos desde la pantalla.** Los cinco roles se cargan con el script.
- **Pantalla de usuarios y de personal por almacén.** El servidor ya los atiende, pero la interfaz no los tiene.
- Niveles del semáforo configurables, límites sumados por categoría, rutas de traspaso obligatorias.
- Tema oscuro, varios idiomas, personalización visual.
- Ubicación dentro del almacén (estante o pasillo): llega hasta el almacén o el trabajador.

**Pospuesto (sin brief):** lista de revisión del supervisor, cierre sin devolución y equipo perdido, reporte de EPP por trabajador, subconjuntos de almacenes por usuario, habilitaciones del trabajador, solicitud de compra, carta de aceptación en el alta, importación de trabajadores desde Excel, tablero general, entrega de turno entre almacenistas, solicitud de surtido entre almacenes y aviso de falta de cobertura de turnos.

**Segunda ola (con brief, aún no construida según el alcance):** vale como prueba (comprobante público por QR, ticket y firma en papel), cierre de almacén de proyecto y valor del inventario, dotación por puesto, mínimos y estados de pieza.

---

## 11. Incongruencias detectadas

Las anoto sin decidir cuál manda; conviene que alguien del equipo lo confirme.

1. **Quién imprime etiquetas.** `app-flow.md` (flujo 16 y tabla de pantallas) y US-ETQ-001 dicen «Compras» o «Compras y RH», pero el código y la tabla 8.2 dan `etiquetas.imprimir` también al Supervisor (y al Administrador). El menú de la interfaz se arma por permiso, así que el Supervisor ve **Etiquetas**.
2. **Administrador sin pantallas propias.** El PRD dice que «en el MVP solo carga los datos iniciales» y `app-flow.md` que no tiene pantallas propias; en cambio `mvp-scope.md` y el contrato de la API describen que usuarios (`/api/usuarios`) y personal (`/api/personal`) ya están integrados en el servidor. Ninguna ruta de la interfaz (`routes.ts`) los usa. La regla AC-08 habla de «desde la pantalla».
3. **Reporte de consumo.** El PRD lo lista en capacidades como **Futuro** (junto con «EPP entregado por trabajador»), pero el alcance del MVP lo incluye, existe la historia US-REP-002 y el menú y los permisos ya lo tienen.
4. **Dónde se emite el no adeudo.** US-BAJ-001 dice «almacenista de Kepler»; la regla B-04 dice «el almacén» y la tabla 8.2 da `no_adeudo.emitir` a cualquier Almacenista y Supervisor, sin limitarlo a Kepler. En esta guía lo uso en Kepler por ser el ejemplo del PDF.
5. **Quién inicia la baja.** B-01 dice RH o el almacenista; la tabla 8.2 también le da `trabajadores.iniciar_baja` al Supervisor y al Administrador. El flujo 11 de `app-flow.md` solo nombra a RH y al almacenista.
6. **Vales para Compras.** La tabla 8.2 y `app-flow.md` dan a Compras `vales.ver` y `vales.cancelar` (para sus entradas), pero la ficha del trabajador (`trabajadores.ver`) no le llega. No pude verificar en el código qué ve Compras al escanear una credencial en **Consultar**.
7. **Estado del PRD y del alcance.** `docs/README.md` marca el PRD y el alcance como «Por aprobar», mientras que gran parte de lo descrito ya está construido; no es una contradicción de contenido, solo de estado.

**Datos que no pude verificar:** el comportamiento exacto de **Consultar** para Compras, y la **lista exacta de artículos con límite** y de piezas con inspección vencida en los datos de prueba (por eso los pasos 3 y 4 del recorrido indican cómo preparar el caso). Tampoco probé el flujo en la interfaz: esta guía se escribió leyendo documentos y código.
