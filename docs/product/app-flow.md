# App Flow — MVP

> Estado Android del 8 de octubre de 2026: los Flujos 31 a 34 siguen planeados. El contenedor empaqueta las pantallas existentes para operar en línea. Sin señal muestra el aviso existente y conserva borradores; no emite vales locales ni ofrece PIN, inscripción o cola. Atrás cierra primero el diálogo abierto, retrocede y pregunta antes de cerrar desde Inicio o Entrar. Un 426 sustituye la interfaz por el aviso de versión nueva. Las descargas existentes abren Compartir y la impresión abre el diálogo Android. Falta la aceptación de sesión en dispositivo real.


Cómo recorre cada rol el sistema: entradas, decisiones, salidas y errores. No describe apariencia (eso está en [ui-ux.md](ui-ux.md)) ni implementación. Los códigos entre paréntesis son reglas de [reglas-de-negocio.md](reglas-de-negocio.md).

## Roles

Son los cinco roles iniciales. Lo que puede cada uno sale de sus permisos (sección 8 de las reglas), y el menú muestra solo eso.

- **Almacenista**: opera su almacén asignado.
- **Supervisor**: autoriza y administra el catálogo; también puede operar un almacén, eligiéndolo.
- **Compras**: inventario, entradas, importación, catálogo, reportes y la cola de solicitudes de compra urgente de todos los almacenes.
- **RH**: trabajadores y bajas.
- **Administrador**: tiene todos los permisos, así que ve todos los menús. Tiene además sus pantallas de administración: Almacenes (`/almacenes`; [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md)), Usuarios (`/usuarios`) y Roles y permisos (`/roles`, `/roles/:id`; [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md)). Solo aparecen con `almacenes.administrar` y `acceso.administrar`.

> **Iteración 01 (aprobada el 8 de octubre de 2026, sin construir).** Lo marcado «Iteración 01» en este documento sale del [documento maestro de la iteración](../releases/iteration_01/README.md) y de sus briefs FEAT-013 a FEAT-020; todavía no está en el código. Cambios por rol:
>
> - **Flujo normal (D-01):** un supervisor en **un** almacén; cada trabajador en **un proyecto** de ese almacén. Lo demás (supervisor con varios almacenes, trabajador con varios proyectos) son casos especiales: las pantallas los muestran solo cuando existen.
> - **Almacenista:** el EPP que entrega pide la aprobación del supervisor del almacén, salvo autonomía (Flujo 6, D-06). Inspecciona el equipo de alturas desde su lista (Flujos 13 y 28, D-10). En la app de Android opera sin conexión dentro de su almacén (Flujos 31 a 34, D-15).
> - **Supervisor:** aprueba el despacho de EPP desde su celular con notificación push (Flujo 25); ve el valor del inventario y el uso por proyecto de sus almacenes (Flujo 22, D-05); ve Deudores (Flujo 27); autoriza los traslados entre almacenes de tercer nivel de su almacén (Flujo 9); resuelve conflictos de sincronización (Flujo 35). Si tiene varios almacenes, cambia su almacén activo (Flujo 29).
> - **RH:** elige el proyecto del trabajador al darlo de alta (Flujo 2, PR-11) y ve Deudores.
> - **Administrador:** da de alta los proyectos (Flujo 24) y es el único que cambia la autonomía de despacho (Flujo 30, D-07).
>
> **Almacén de tercer nivel y proyecto no son lo mismo.** Un **almacén de tercer nivel** (tipo `PROYECTO`: Midrex, HYL, Laminador, Minas) es el **lugar** que se surte desde Contratistas. Un **proyecto** (FEAT-013, D-02) es el **contrato o mantenimiento** que usa ese almacén: tiene nombre, almacén, inicio y fin estimado, y se da de alta antes que sus trabajadores. Un almacén de tercer nivel puede tener varios proyectos o ninguno.

## Navegación global

El Inicio es el **tablero** para quien tiene `tablero.ver`, con los botones de operación **arriba** («Lo que haces hoy», FEAT-008). El menú se arma por permisos y se agrupa por tarea ([ui-ux.md](ui-ux.md), «Grupo de menú plegable»).

```
Entrar
  -> Almacenista   -> Inicio: Lo que haces hoy (Entregar | Devolver | Consultar | Recibir (n) con `traspasos.recibir`, que trae de inicio) + tablero de su almacén
  -> Supervisor    -> Inicio: Lo que haces hoy (Entregar | Devolver | Trasladar | Recibir (n) | Autorizaciones (n) | Consultar) + tablero de su almacén
  -> Compras       -> Inicio: Solicitudes de compra (n) | Entradas pendientes (sin tablero)
  -> RH            -> Inicio: Trabajadores | Altas recientes (sin tablero)
  -> Administrador -> Inicio: Lo que haces hoy + tablero de todos los almacenes con selector
```

Menú (FEAT-011, AC-35: unas 10 entradas; cada entrada aparece solo con su permiso y una sección sin pantallas visibles no se pinta). Cada sección es **una** entrada del menú y sus pantallas son las **pestañas** de una barra compartida; las URLs no cambian. Con una sola pestaña visible, la entrada lleva directo a esa pantalla. Solo «Operación del día» es un grupo plegable con entradas directas.

| Entrada | Pestañas (URL · permiso) |
|---|---|
| **Inicio** | Resumen |
| **Operación del día** | Entregar (`entregas.crear`) · Devolver (`devoluciones.crear`) · Consultar (todos) |
| **Traspasos** | Enviar `/trasladar` (`traspasos.operar`) · Recibir `/recibir` (`traspasos.recibir`) |
| **Inventario** | Existencias `/inventario` (`inventario.ver`) · Bitácora `/reportes/movimientos` (`bitacora.ver` o `reportes.movimientos`) · Piezas y resguardos `/seguimiento` (`reportes.existencias` o `resguardo.ver`) · Dar entrada `/entrada` (`inventario.entradas` o `inventario.importar`) |
| **Catálogo** | Artículos `/catalogo/articulos` · Categorías `/catalogo/categorias` · Puestos `/puestos` (`catalogo.administrar`) · Etiquetas `/etiquetas` (`etiquetas.imprimir`) |
| **Trabajadores** | Trabajadores `/trabajadores` (`trabajadores.ver`) · Alta de trabajador `/trabajadores/nuevo` (`trabajadores.administrar`) |
| **Compras** | Pedir una compra urgente `/compras/nueva` · Mis solicitudes `/compras/mias` (`compras.solicitar`) · Cola de Compras `/compras` (`compras.atender`) |
| **Supervisión** | Autorizaciones `/autorizaciones` (`autorizaciones.resolver`) · Existencias · Adeudos · Consumo `/reportes/...` (su permiso `reportes.*`) |
| **Personas y accesos** | Usuarios `/usuarios` (`acceso.usuarios`) · Roles y permisos `/roles` (`acceso.roles`) · Personal por almacén `/personal` (`almacenes.asignar_personal`) |
| **Almacenes** | `/almacenes` (`almacenes.administrar`) |

**Iteración 01, sin construir: entradas y pestañas nuevas.** Cada una con su permiso; la sección exacta se confirma al construir.

| Entrada | Pestañas o elementos nuevos (URL · permiso) | Brief |
|---|---|---|
| **Operación del día** | Inspecciones `/inspecciones` (`inspecciones.ver`), con contador de vencidas, por vencer y sin inspección | FEAT-016 |
| **Inventario** | La pestaña Bitácora abre `/bitacora` (por vale); `/reportes/movimientos` pasa a ser su pestaña «Detalle por renglón» | FEAT-017 |
| **Supervisión** | Deudores `/deudores` (`deudores.ver`; reemplaza a la pestaña Adeudos, que redirige) · Equipos y Conflictos de sincronización (`sincronizacion.administrar`) | FEAT-018, FEAT-020 |
| **Almacenes** (administración) | Proyectos `/proyectos` (`proyectos.ver`; editar con `proyectos.administrar`) | FEAT-013 |
| Barra superior | Selector «Operando en: Midrex ▾», solo con dos o más almacenes en el conjunto (AC-39) | FEAT-013 |
| Menú de usuario | «Avisos de este equipo»: activar, desactivar y aviso de prueba (`autorizaciones.resolver`; NT-01, NT-09) | FEAT-014 |
| App de Android | Indicador de conexión, «Por sincronizar» y «Preparar este equipo» (`sincronizacion.operar`), solo en la plataforma nativa | FEAT-020 |

«Mis movimientos de hoy» (`/mis-movimientos`) ya no está en el menú: se llega desde Consultar y desde la Bitácora con el filtro «Solo los míos». La barra de pestañas sale solo en la pantalla de cada pestaña, no en sus detalles (`/compras/<id>`, `/roles/<id>`, `/trabajadores/<id>`). Los enlaces anteriores (`/entradas/nueva`, `/importar`) siguen abriendo y redirigen a `/entrada`. Ocultar un módulo a un rol se hace quitándole el permiso en Roles y permisos.

"Consultar" y la búsqueda están disponibles para todos; cada usuario ve solo lo que permiten los permisos de su rol (AC-05).

El interruptor **«Tutorial»** (FEAT-010) está en el pie del menú lateral, en la hoja «Menú» del celular y en el encabezado móvil dentro de los flujos; lo ve cualquier usuario con sesión y se describe en el Flujo 23.

## Flujo 1: Entrar

- **Entrada:** cualquier ruta sin sesión.
- **Pasos:** usuario y contraseña -> inicio del rol.
- **Decisiones:** credenciales válidas; usuario activo.
- **Éxito:** inicio del rol, o la ruta que se intentó abrir.
- **Error:** "Usuario o contraseña incorrectos", sin decir cuál; tras cinco intentos, espera de cinco minutos.
- **Salida:** "Salir" cierra la sesión de este dispositivo y regresa a Entrar; las de los demás dispositivos siguen abiertas.
- **Sesión que se renueva sola:** al vencer el acceso (15 minutos) la aplicación lo renueva sin avisar y repite lo que se estaba haciendo; reabrirla a los 3 días no pide la contraseña. La contraseña se vuelve a pedir si pasan 7 días sin usarla, si se cumplen 30 días desde que se entró, o si la sesión se cerró en otro lado (cambio de contraseña o de PIN, usuario inactivado, «cerrar todas»). En ese caso Entrar dice «Tu sesión venció. Entra de nuevo para continuar donde estabas.» y, al entrar, regresa a la pantalla donde se estaba (AC-14 a AC-24).

## Flujo 2: Alta y reingreso de trabajador (RH)

- **Entrada:** Trabajadores -> Alta.
- **Precondiciones:** sesión de RH.
- **Pasos:**

```
Capturar nombre, puesto, área u obra y periodo (T-03); opcionales: tallas, CURP o NSS
  (el número de empleado NO se captura: lo asigna el servidor, T-10)
Guardar -> el servidor compara
  -> la CURP ya existe -> mostrar a la persona y sus pendientes -> Reingresar (T-02)
  -> sin CURP y el nombre completo coincide con otra persona -> aviso de coincidencia -> Reingresar a esa persona | "Es otra persona" (confirmar_distinta)
  -> no coincide -> alta; la ficha y la confirmación muestran el número asignado (E-000001)
Ligar credencial (T-05)
  -> escanear la credencial de la planta
  -> o generar un QR propio para imprimir
Foto, opcional (T-09): tomarla con la cámara o subir una imagen
Guardar -> con `etiquetas.imprimir` y credencial ligada: imprimir o descargar la credencial (completa o solo QR) -> ficha
       -> si no, ficha del trabajador
```

- **Orden real de la pantalla.** El servidor compara al guardar; la pantalla puede avisar antes, al salir del campo CURP o nombre, con la misma consulta de coincidencias. Solo quien tiene `trabajadores.numero_externo` (el Administrador) ve el campo opcional «Número de empleado propio del centro»; RH no lo ve (T-10).
- **Decisiones:** CURP repetida o nombre completo coincidente (reingreso); periodo con fin anterior al inicio; credencial ya ligada a otra persona.
- **Éxito:** trabajador Activo y vigente; su credencial lo identifica en cualquier almacén.
- **Error:** dato obligatorio faltante marcado en el campo; código de credencial repetido indica de quién es.
- **Cancelación:** salir sin guardar no crea nada.

### Iteración 01, sin construir: el proyecto es obligatorio en el alta (FEAT-013)

- **Precondiciones:** `trabajadores.administrar` **y** `proyectos.asignar` (403 `SIN_PERMISO` si falta el segundo; PR-11). El proyecto ya existe: lo dio de alta el Administrador (Flujo 24, D-02).
- **Cambio en los pasos:**

```
Capturar nombre, puesto, PROYECTO (reemplaza a «área u obra», T-03) y periodo
  -> «Proyecto»: lista de los proyectos asignables (activos, vigentes o por iniciar), agrupados por almacén y con sus fechas (PR-02, PR-07)
       -> un solo proyecto asignable -> ya elegido
       -> ninguno -> no se puede guardar: «No hay proyectos abiertos. Pide al Administrador que dé de alta el proyecto antes de registrar a sus trabajadores.» (PR-11)
Guardar -> en una transacción: trabajador, periodo (con `area_obra` = nombre del proyecto) y asignación principal (PR-11)
Reingreso (T-02) -> pide proyecto si no tiene una asignación activa a un proyecto asignable; si la tiene, se propone esa (PR-11)
```

- **Ficha del trabajador:** sección «Proyectos» con la asignación activa (o «Sin proyecto») y el historial plegado. Con `proyectos.asignar`: «Cambiar de proyecto» (caso normal) y, en un menú secundario, «Agregar otro proyecto» o terminar una asignación. Lo que tiene en resguardo sigue siendo suyo (PR-13).
- **Errores:** 422 `PROYECTO_REQUERIDO` sin proyecto; 422 `PROYECTO_INVALIDO` con uno cerrado, vencido o inexistente; 409 `ASIGNACION_REPETIDA` al repetir una asignación activa (PR-11, PR-13).
- **Lista de trabajadores:** columna «Proyecto» y filtros «Proyecto» y «Sin proyecto», para que RH asigne a los que ya existían antes de desplegar (decisión abierta 1 de FEAT-013).

## Flujo 3: Catálogo (Compras o supervisor)

- **Entrada:** Catálogo -> Categorías | Artículos | Puestos.
- **Pasos:**

```
Categoría -> crear o editar: nombre, tipo y plantilla de reglas (CF-01, CF-02)
Artículo  -> crear: elegir categoría -> el formulario toma la plantilla -> ajustar -> guardar
          -> editar: límite, requisitos especiales y su motivo (CF-06, CF-07)
          -> inactivar: motivo obligatorio (CF-10) | reactivar (CF-13)
          -> eliminar: solo si no tiene movimientos (CF-12)
Puesto    -> crear: nombre -> se abre su dotación | renombrar | inactivar y reactivar
Dotación  -> agregar artículos activos y cantidad recomendada -> resumen de cambios -> guardar (reemplaza la lista; D-01, D-04)
```

- **Puestos (`/puestos`):** lista con búsqueda y filtro Activos, Inactivos o Todos. Quien tiene `catalogo.ver` la ve y abre la dotación; crear, renombrar, inactivar y editar la dotación piden `catalogo.administrar`. Un puesto inactivo conserva su dotación pero no se ofrece en el alta de trabajadores. Un puesto sin dotación no genera avisos al entregar.
- **Alta y reingreso de trabajadores:** el campo "Puesto" es una lista de los puestos activos y manda `puesto_id`. Si no hay puestos, el formulario avisa: con `catalogo.administrar` ofrece el enlace a Puestos ("Primero crea un puesto"); sin él pide a Compras o al supervisor que lo creen. Quien no tiene `catalogo.ver` (Recursos Humanos en los datos iniciales) no puede listar el catálogo: ve el campo de texto de antes y el servidor liga el nombre al puesto si coincide.
- **Ficha del trabajador:** el bloque "Dotación del puesto" muestra cada artículo recomendado con lo entregado, lo recomendado y lo que falta (D-02).

- **Decisiones:** si el artículo ya tiene movimientos, control y retorno aparecen bloqueados con la explicación (CF-05).
- **Éxito:** la siguiente entrega respeta el cambio (CF-08); el cambio queda registrado (CF-15).
- **Error:** código de artículo repetido; categoría inactiva no seleccionable.
- **Cancelación:** salir sin guardar no cambia nada.

## Flujo 4: Entrada de inventario (Compras)

- **Entrada:** «Dar entrada» (`/entrada`), método **Capturar a mano** (permiso `inventario.entradas`). Los enlaces anteriores `/entradas/nueva` y `/importar` redirigen aquí con su método (`?metodo=mano` o `?metodo=excel`).
- **Pasos:**

```
Sin selector de almacén: la pantalla dice «Entra a Kepler» (el nombre sale de la API de almacenes) y «Para llevarlo a otro almacén, usa un traspaso» (EK-01, EK-03)
Agregar renglones (escanear o buscar artículo)
  -> no existe y hay catalogo.administrar: «Crear este artículo» (EK-07) y sigue como renglón nuevo
  -> por cantidad: capturar cantidad
  -> por pieza: capturar o escanear el código de cada pieza, marca y serie (I-02); la serie puede quedar pendiente (E-xx)
       -> requiere inspección: capturar la inspección inicial o dejarla pendiente (I-03)
Confirmar -> vale de entrada con folio
```

- **Decisiones:** artículo inactivo se rechaza (I-09); código de pieza repetido se rechaza. Si lo buscado no existe, quien tiene `catalogo.administrar` ve «Crear este artículo» (nombre, categoría, unidad; la categoría dice si es «Por cantidad» o «Por pieza» y el servidor genera el código): el artículo queda en el catálogo, el renglón se agrega y sigue la misma captura, sin salir de la pantalla (EK-07). Sin el permiso: «Este artículo no existe en el catálogo; pide que lo den de alta».
- **Éxito:** existencias aumentan en Kepler. Para llegar a Contratistas o a un almacén de tercer nivel, la mercancía pasa por traspaso (Trasladar).
- **Error:** el renglón con problema se marca; nada se guarda hasta corregirlo (RG-09).

## Flujo 5: Importación desde Excel (Compras)

- **Entrada:** «Dar entrada» (`/entrada`), método **Desde un Excel** (EK-04). La pantalla ofrece los dos métodos como dos botones grandes y muestra solo los que el rol puede usar; sin ninguno, «Tu rol no puede hacer esto».
- **Precondiciones:** `inventario.importar` y también `inventario.entradas` (confirmar escribe un vale de entrada). El alta que crea artículos pide además `catalogo.administrar` (I-10).
- **Pasos:**

```
Elegir el modo: Alta (carga inicial: crea artículos nuevos y suma a los que ya existen)
                o Reposición (solo suma a artículos que ya existen)
   -> "Descargar plantilla" ofrece el ejemplo de ese modo
Pegar la tabla copiada de Excel, o subir el archivo
   -> con las columnas obligatorias reconocidas, la vista previa aparece sola, con esqueleto de carga (TR-12)
Indicar qué columna es cada dato (solo si no se reconocieron; «Relacionarlas a mano» vuelve a este paso)
   Alta: código (opcional), nombre, marca, categoría, cantidad, unidad (opcional), serie (opcional), costo, código de pieza (opcional)
   Reposición: código, cantidad y, si es por pieza, código de pieza y serie
   Todo entra a Kepler (EK-01): una columna de almacén en el archivo se ignora con un aviso (EK-02)
Vista previa en tabla, paginada de 12 en 12: una fila por renglón del archivo, con su estado
   Nuevo | Existente (suma) | Unido | Error, saldo antes -> después,
   y en el alta la categoría sugerida, que se puede cambiar por fila
   Resumen arriba: nuevos, existentes, unidos, errores y, si los hay, «n piezas sin serie»
   Una pieza sin serie sale en amarillo con «Serie pendiente»; una sin código de pieza, con «Código provisional: se asigna al confirmar»
   Aviso si el archivo ya se importó
Confirmar -> un vale de entrada a Kepler
  -> si entraron piezas: pantalla de resultado con «Imprimir etiquetas de las piezas nuevas»
```

- **Decisiones:**
  - Categoría de un artículo nuevo sin categoría en el archivo: el sistema sugiere una según la descripción y dice por qué; la persona la acepta o la cambia en la fila, y lo que no coincide queda «por revisar» hasta elegir una (I-14).
  - Filas del mismo artículo por cantidad y almacén: se unen en una («Unido: filas 2, 5, 9»); artículo por pieza: cada fila es una pieza, y el código de pieza o la serie repetidos son error (I-06). Una pieza sin serie **no** es error: entra con la serie pendiente y la fila sale en amarillo (I-02, I-17). Una pieza sin código de pieza tampoco: el sistema le asigna `CÓDIGO-DEL-ARTÍCULO-NNN` al confirmar (RG-10).
  - Código que no existe en Reposición: error «Ese artículo no existe: dalo de alta primero» (I-10).
  - Cantidad con decimales o con coma ambigua: error que pide una unidad entera menor; nunca se redondea (I-13). Más de 100 000 por fila: error (I-11).
  - Columna `unidad` (opcional, en Alta): la unidad de un artículo nuevo; si difiere de la de uno existente, aviso y no se cambia. Las cantidades siguen siendo enteras: quien mide en kilos las pasa a gramos en el archivo (I-13).
  - Una descripción con la palabra SERVICIO se excluye con aviso.
  - Archivo ya importado: aviso en la vista previa; para confirmar hay que aceptar expresamente (I-12).
  - Sin `catalogo.administrar`: las filas que crearían un artículo salen como error y las demás entran.
- **Éxito:** catálogo y existencias cargados; resumen de lo creado y de lo sumado, con los folios de los vales. Si entraron piezas, el resultado lista las piezas creadas con su código (los generados, marcados) y ofrece «Imprimir etiquetas de las piezas nuevas», que abre Etiquetas (flujo 16) con esas piezas; un código generado no está pegado en la herramienta hasta imprimir y pegar su etiqueta. Si quedaron piezas con serie pendiente, el resultado lo dice y enlaza al seguimiento filtrado.
- **Error:** las filas con error no se importan y se listan con su motivo (se pueden descargar en CSV); las buenas entran sin esperar a las malas.
- **Cancelación:** hasta "Confirmar" no se guarda nada.
- **Iteración 01, sin construir (FEAT-017, FEAT-019):** los vales de una misma importación comparten `lote_id` (BT-02). El resultado agrega «Ver en la bitácora» (abre `/bitacora?lote_id=` con el lote desplegado) y «Descargar PDF» (del lote, o del vale si fue uno solo; BT-10). «Imprimir etiquetas de las piezas nuevas» sigue siendo la acción principal si se crearon piezas, y Etiquetas las recibe por el lote, no por la dirección (UX-06); si no se crearon piezas, la principal es «Ver en la bitácora».

## Flujo 6: Entrega (almacenista)

- **Entrada:** Inicio -> Entregar; o desde la ficha de un trabajador -> "Entregarle".
- **Precondiciones:** sesión con almacén asignado.
- **Pasos:**

```
Identificar al trabajador: escanear credencial | teclear número | buscar por nombre (E-18)
  -> no encontrado -> mensaje y reintento
  -> no vigente (E-02) -> pantalla en rojo con el motivo -> fin
  -> vigente -> ficha breve: foto, nombre, puesto, vigencia y lo que ya tiene (E-17)
       -> con dotación: "Dotación: faltan 4 de 11" y "Ver dotación" (solo consulta); sin puesto o sin dotación no se muestra nada (D-02)
Escanear artículos, uno tras otro (cada lectura se agrega a un borrador; nada se descuenta hasta confirmar, E-28)
  -> "Dotación sugerida" (solo si hay dotación): hoja con casillas, sin marcar; "Agregar a la entrega" agrega lo marcado
     como renglones normales con la cantidad que falta, por el mismo camino que escanear (nunca se carga sola)
  -> cada lectura se evalúa y aparece como renglón con nivel y motivos
  -> por cantidad: ajustar con + y -, o teclear la cantidad; volver a escanear suma 1 (E-16)
  -> cantidad inusualmente alta: se pide confirmar la cantidad (E-27)
  -> lectura accidental: Quitar el renglón, o Deshacer durante 5 segundos
  -> rojo: se quita el renglón para poder continuar
  -> amarillo: se lee y no detiene (E-09 fuera de la dotación o sobre lo recomendado, E-10 talla, E-11 inspección por vencer, E-29 pieza con serie pendiente: el renglón ofrece «Registrar serie» si la persona tiene `piezas.registrar_serie`)
  -> naranja: Pedir autorización (flujo 7) o quitar el renglón (A-07)
Continuar: sin rojos y con los naranjas autorizados (SM-03)
  -> si algún renglón pide observación (E-09): "¿Por qué se entrega esto?" con respuestas rápidas; obligatoria para confirmar
  -> resumen (con el motivo), leyenda de responsabilidad y firma del trabajador (F-02)
Confirmar
  -> sin observación cuando se pide -> el servidor responde E-09 y el error sale junto al campo
  -> el servidor revalida (RG-08)
       -> algo cambió -> regresa a la lista con el renglón marcado
       -> correcto -> vale emitido: folio y QR -> Imprimir | Nueva entrega
```

- **Éxito:** vale de entrega emitido; bajan las existencias y sube el resguardo del trabajador.
- **Error:** si se pierde la conexión al confirmar, el borrador se conserva en el dispositivo y se reintenta; un mismo vale no se guarda dos veces.
- **Cancelación:** salir con renglones capturados pide confirmación; no se guarda nada.

### Iteración 01, sin construir: proyecto de la entrega y aprobación del despacho de EPP (FEAT-013, FEAT-014)

- **Orden del flujo (D-08, DE-03):** capturar al trabajador → capturar los artículos → **enviar a aprobación** → el supervisor **aprueba** (total o parcial) → quitar lo rechazado → **firma** del trabajador → **confirmar**. La firma nunca va antes de aprobar, para que el trabajador firme solo lo que recibe. Cambia el orden de las notas del track, que ponían la firma antes (incongruencia 5 del maestro).
- **Cuándo se pide la aprobación (DE-01):** toda ENTREGA con al menos un artículo de EPP (categoría de tipo `EPP`) cuando el almacén tiene el despacho con aprobación (`despacho_epp_con_aprobacion`, prendido por omisión), quien captura no tiene la excepción `despacho_autonomo` y no tiene `autorizaciones.resolver` en ese almacén. La herramienta sola, las devoluciones, los traspasos, las recepciones, las cancelaciones, el no adeudo y las entradas nunca la piden.
- **Pasos:**

```
Identificar al trabajador (igual que arriba)
  -> vigente -> ficha breve
       -> proyecto de la entrega (sale del trabajador, no del almacén que entrega; D-13, PR-14):
            una asignación activa a un proyecto activo -> línea «Proyecto: Mantenimiento Midrex (Midrex)»; no se elige nada (PR-08)
            varias -> selector con la principal ya elegida y el motivo amarillo PR-09 «Elige para qué proyecto es esta entrega» (PR-09)
            ninguna -> amarillo PR-10 «Este trabajador no tiene proyecto activo» y observación obligatoria; cuenta como «Sin proyecto» (PR-10)
       -> despacho con aprobación -> línea discreta «El EPP de esta entrega lo aprueba un supervisor» (DE-01)
Escanear artículos (semáforo de siempre; el nivel no cambia, DE-02)
  -> renglón de EPP -> etiqueta «Necesita aprobación» (no es un color del semáforo; DE-02)
  -> naranja -> ya no tiene su propio «Pedir autorización»: va dentro de la misma solicitud (DE-04)
  -> rojo -> se quita como siempre (A-06)
«Enviar a aprobación» (reemplaza a «Continuar» mientras falte la aprobación; DE-02)
  -> hoja: lo que se resuelve arriba (EPP y naranjas), el contexto abajo (herramienta en verde o amarillo), nota opcional;
     «Motivo del excedente» obligatorio solo si hay naranjas (DE-04, DE-05, A-02)
  -> «Enviar al supervisor» -> una sola solicitud DESPACHO por vale, con `id_cliente` (un doble toque no crea dos; DE-04)
                               -> notificación push a los supervisores del almacén (NT-02, Flujo 25)
  -> «El supervisor está aquí» -> usuario y PIN en este dispositivo; resuelve igual que en su celular (A-01)
Esperar (DE-15)
  -> «Esperando aprobación de un supervisor de Midrex», reloj con lo que falta (hora del servidor, RG-11), «Se avisó a 2 supervisores»
  -> «Atender a otro mientras» -> el borrador pasa a «En espera (n)», con contador en el Inicio y en Entregar (hasta 10 por dispositivo)
  -> 5 minutos sin respuesta -> «Nadie ha respondido todavía»: PIN aquí | seguir esperando | quitar el EPP y entregar lo demás (DE-10)
  -> vencida a los 15 minutos -> reenviar | PIN en el mostrador | quitar el EPP (DE-09)
Respuesta (la pantalla consulta cada 3 s y se actualiza sola)
  -> aprobada total o parcial -> aprobados con palomita; rechazados en gris tachado con su motivo y «Quitar» (DE-06)
  -> rechazada toda -> se quitan el EPP y los naranjas; la herramienta de contexto se puede entregar (A-07)
  -> «Continuar a la firma» se habilita cuando ya no queda ningún rechazado
  -> si después de aprobar se agrega EPP o un naranja, se sube una cantidad aprobada o se cambia trabajador, almacén o proyecto:
     «Cambiaste lo que se aprobó: hay que volver a enviar». Quitar renglones, bajar cantidades o tocar el contexto no la invalida (DE-13)
Firma (F-02) -> observación si la pide E-09 o PR-10
Confirmar (la aprobada sirve 15 minutos desde que se aprobó; DE-09)
  -> 409 APROBACION_INVALIDA: un renglón rechazado, no incluido o con más cantidad (DE-08)
  -> 409 REQUIERE_APROBACION_DESPACHO: el Administrador apagó la autonomía mientras se capturaba; el borrador se conserva (DE-16)
  -> 409 VALE_CAMBIO: un renglón aprobado quedó en rojo (se quita sin pedir otra aprobación), o el proyecto se cerró (PR-10, DE-16)
  -> correcto -> vale con folio y QR; lleva el proyecto (E-24) y «Validó: Luis Gómez»
```

- **Sin paso de aprobación (DE-07, DE-14):** si el almacén o el almacenista tienen autonomía, o quien captura es supervisor de ese almacén (o el Administrador), el botón sigue diciendo «Continuar» y los naranjas siguen con «Pedir autorización» de tipo EXCEDENTE (Flujo 7). El supervisor que despacha él mismo queda como «Validó: él mismo (despacho)»; un excedente suyo sigue necesitando a **otro** supervisor (A-05).
- **Éxito:** vale con proyecto (o «Sin proyecto») y, si hubo despacho, con su `autorizacion_id`. El consumo cuenta para el proyecto aunque lo entregue otro almacén: el EPP que Contratistas entrega a un trabajador del proyecto de Midrex lo ve el supervisor de Midrex (D-13, PR-14).
- **Errores de proyecto:** 422 `PROYECTO_REQUERIDO` (varios proyectos sin elegir), 422 `PROYECTO_INVALIDO` (uno que no es del trabajador) y 422 `DATOS_INVALIDOS` con regla PR-10 (sin observación).
- **Sin conexión (app de Android):** el EPP que pide aprobación espera señal (Flujo 33, OF-10).

## Flujo 7: Autorización (almacenista y supervisor)

- **Entrada:** renglón en naranja -> Pedir autorización.
- **Pasos:**

```
Almacenista: escribe el motivo -> envía la solicitud -> queda "En espera"
  -> supervisor presente -> teclea su PIN en ese dispositivo -> autoriza
  -> supervisor en campo -> ve la solicitud en su celular -> Autorizar | Rechazar
Almacenista: la pantalla se actualiza sola
  -> autorizada -> el renglón queda autorizado -> continúa la entrega
  -> rechazada o vencida -> quita el renglón y entrega lo demás (A-07)
```

- **Decisiones:** quien captura no puede autorizarse (A-05); un rojo no se puede enviar a autorización (A-06).
- **Éxito:** queda registrado quién pidió, quién autorizó, cuándo y por qué (A-04).
- **Error:** PIN incorrecto; al quinto intento se bloquea cinco minutos.

### Iteración 01, sin construir: tres tipos, aprobación parcial, resolución múltiple y notificaciones push (FEAT-014, FEAT-015)

- **Tipos de solicitud** (`autorizacion.tipo`; las de hoy quedan como EXCEDENTE):

| Tipo | Quién la pide y cuándo | Quién la resuelve | Cómo |
|---|---|---|---|
| **EXCEDENTE** | El naranja de una entrega que **no** pide aprobación del despacho (flujo de arriba, sin cambios) | `autorizaciones.resolver` en el almacén | Total o, desde ahora, parcial por renglón (DE-06) |
| **DESPACHO** | «Enviar a aprobación» de una entrega con EPP (Flujo 6); incluye todo el EPP y todos los naranjas del vale (DE-04) | `autorizaciones.resolver` en el almacén que entrega | Por renglón: Aprobar o Rechazar, con motivo en cada rechazo (DE-06) |
| **TRASLADO** | El naranja X-17 de un traslado lateral que no envía el supervisor del origen (Flujo 9) | `autorizaciones.resolver` en el almacén de **origen**, o `almacenes.todos` | Completa: no hay aprobación parcial (X-19) |

- **Pasos del supervisor:**

```
Le llega la notificación push (si activó avisos en ese equipo; NT-01) o ve subir el contador de Autorizaciones (NT-08)
  -> título y cuerpo sin costos, CURP, NSS ni foto: «Midrex · EPP por aprobar» / «Para Juan Pérez: 4 artículos de EPP. Lo pide Ana Ruiz.» (NT-03)
  -> varias pendientes del mismo almacén: un solo aviso que se reemplaza, «Midrex · 5 solicitudes por aprobar»; suena una vez por minuto (NT-05)
Toca el aviso -> `/autorizaciones/{id}` (o la lista si es un aviso agrupado); si la sesión venció, entra y regresa ahí (NT-04)
Resuelve una (Flujo 25)
  -> DESPACHO o EXCEDENTE: cada renglón que se resuelve en Aprobar o Rechazar; «Aprobar todo» | «Rechazar todo» | «Aprobar 3 y rechazar 1»
     queda APROBADA si se aprobó al menos un renglón; RECHAZADA si ninguno (DE-06)
  -> TRASLADO: «Autorizar» | «Rechazar» completa (X-19)
O resuelve varias de un jalón (DE-12)
  -> en la lista, marca solicitudes sin excedente -> «Aprobar 12» (o rechazar varias, con un motivo por cada una)
  -> las que dicen «Incluye excedente» no se aprueban en grupo: se abren una por una
  -> cada una en su transacción: «Aprobaste 11. 1 ya la había resuelto Marta Ríos»
A los demás supervisores se les reemplaza el aviso en silencio: «Midrex · Luis Gómez ya la aprobó» (NT-06)
```

- **Decisiones:** gana el primero que resuelve; el segundo recibe 409 `AUTORIZACION_RESUELTA` con quién, cuándo y cómo quedó (DE-11). Quien pidió nunca la resuelve (A-05), salvo las dos excepciones que no crean solicitud: el supervisor que despacha él mismo (DE-07) y el que envía un traslado lateral desde su almacén (X-16). La ven y la resuelven quienes tienen `autorizaciones.resolver` y el almacén de la solicitud en su conjunto, aunque no sea su almacén activo (AC-40). El Administrador no recibe avisos por omisión, pero ve el contador y la lista (NT-02).
- **Vigencia:** la pendiente vence a los 15 minutos de creada; la aprobada sirve 15 minutos **desde que se aprobó**, para dar tiempo a la firma (DE-09). Vencer no manda aviso (NT-06).
- **El push es una ayuda, no el único camino:** el contador del menú y la lista siguen funcionando sin avisos. En iPhone el aviso solo llega con la aplicación instalada en la pantalla de inicio; en Android, Chrome lo recibe sin instalar (NT-08). Los avisos se mandan después de guardar; un fallo al enviar no deshace nada (NT-07).
- **Activar avisos (NT-01, NT-09):** en Autorizaciones y en el menú de usuario, «Activar avisos» (el navegador pide permiso solo al tocarlo) y «Mandar un aviso de prueba». Al salir, la suscripción de ese equipo se revoca. La propuesta T-4 del maestro ofrece también «Activar avisos» a quien tiene `traspasos.recibir`, para el aviso informativo de un traslado lateral (X-20).

## Flujo 8: Devolución (almacenista)

- **Entrada:** Inicio -> Devolver.
- **Pasos:**

```
Escanear
  -> pieza en resguardo -> muestra artículo y titular (V-01) -> elegir condición (V-04)
  -> pieza que no está en resguardo -> aviso con su ubicación (V-02)
  -> código desconocido -> rojo: no es de la empresa, no se recibe (V-12)
  -> credencial de trabajador -> lista de lo que tiene -> elegir artículo y cantidad (V-03)
Condición Dañado -> observación obligatoria, foto opcional (V-05)
Confirmar -> vale de devolución con folio (V-11)
```

- **Decisiones:** la devolución se abona al titular aunque la traiga otra persona (V-01); si el almacén no es el que entregó, se avisa y se recibe (V-07).
- **Éxito:** baja el resguardo del titular y suben las existencias del almacén que recibe.
- **Error:** cantidad mayor a la que tiene el trabajador se rechaza en ese renglón.
- **Cancelación:** como en la entrega.

## Flujo 9: Traspaso, salida (supervisor del almacén de origen)

- **Entrada:** Inicio -> Trasladar. Con `traspasos.operar` (X-01); el almacenista no la tiene.
- **Pasos:**

```
Elegir almacén de destino (se ofrecen las rutas habituales: padre o hijo del almacén, X-03)
  -> otra ruta: solo con `almacenes.todos`; aviso amarillo y observación obligatoria (X-03). Para los demás, ni se ofrece; si el servidor la recibe, la marca en rojo (`RUTA_SOLO_ADMINISTRADOR`)
Escanear o buscar artículos -> solo se ofrece lo que hay en el almacén de origen, con «Disponible: N» (TR-11)
  -> renglones con nivel (X-02, X-04); un código que no hay en el origen se rechaza con X-02
Confirmar -> vale de traspaso con folio y QR; estado En tránsito (X-06)
```

- **Éxito:** las existencias salen del origen y quedan En tránsito (X-01).
- **Error:** pieza que no está en este almacén, o cantidad mayor a la existencia: rojo.

### Iteración 01, sin construir: traslado lateral entre almacenes de tercer nivel (FEAT-015)

Un **traslado lateral** es un traspaso entre dos almacenes de tercer nivel (tipo `PROYECTO`), distintos y activos, compartan o no el mismo subalmacén padre (X-18). Ejemplo: Midrex → HYL. Es una salida para lo que sobra en un almacén y falta en otro; la ruta habitual sigue siendo Kepler → Contratistas → tercer nivel (X-03). No cambia el proyecto de nada: el consumo es del proyecto de la entrega (D-13).

```
Elegir destino: la lista trae tres grupos, decididos por el servidor (`ruta.autoriza`):
  «Rutas habituales» (padre o hijo) | «Entre proyectos» (los demás almacenes de tercer nivel) | «Otras rutas» (solo con `almacenes.todos`)
  -> Entre proyectos, y quien envía tiene `autorizaciones.resolver` en el origen (el supervisor del origen o el Administrador):
       «Tú lo autorizas al enviarlo»: amarillo X-16 y observación obligatoria (para qué se manda) (X-16)
       -> Confirmar -> vale «Validó: Pedro (envío propio)»; entra a la lista de revisión (RG-14). No se crea solicitud
  -> Entre proyectos, y quien envía NO lo tiene (un almacenista al que se le dio `traspasos.operar`):
       «Lo autoriza el supervisor de Midrex»: naranja X-17; no se confirma sin autorización (X-17)
       -> «Pedir autorización» con motivo -> solicitud TRASLADO con origen, destino y renglones (Flujo 7)
          -> push al supervisor del origen; vence a los 15 minutos; o el supervisor da su PIN en el mostrador (A-01)
          -> «En espera de Pedro»: el borrador no se edita mientras espera; «Cancelar la solicitud» lo libera
          -> autorizada -> Confirmar con `autorizacion_id`; el vale dice «Validó: Pedro (desde su celular)» o «(con su PIN)»
          -> rechazada o vencida -> no sale nada; el borrador se conserva y se puede pedir otra
  -> Avisos amarillos que no piden observación: nadie en el destino tiene `traspasos.recibir`; el destino no tiene proyectos activos (X-20, PR-12)
Al confirmar: notificación informativa al destino «HYL · Te enviaron un traslado desde Midrex» (X-20)
```

- **Decisiones:** después de autorizado se pueden **quitar** renglones; agregar uno, subir una cantidad o cambiar el destino deja la autorización sin efecto (409 `AUTORIZACION_INVALIDA`; X-19). Un renglón en rojo no se autoriza (422 `RENGLON_NO_AUTORIZABLE`; A-06). Las demás rutas que no son padre-hijo (Kepler → Midrex, Midrex → Kepler) siguen con X-03 sin cambios. Un rol con `almacenes.todos` y sin `autorizaciones.resolver` hace el lateral por X-03 (X-18).
- **Con una lista de Excel (TR-05):** la ruta se evalúa una vez por archivo; el banner dice «Entre proyectos: tú lo autorizas» (pide la observación) o «Entre proyectos: lo autoriza el supervisor de Midrex» con «Pedir autorización». La solicitud lleva las filas que no están en rojo; «Dejar fuera las filas con error» después de autorizar es quitar renglones y la autorización sigue sirviendo.
- **Cancelar y rehacer (K-05):** el borrador nuevo no hereda la autorización.

### Entrada alternativa: Trasladar con una lista (FEAT-009)

- **Entrada:** en Trasladar, el botón «Trasladar con una lista», junto a «Escanear». Misma precondición y mismo permiso (`traspasos.operar`); no hay permiso nuevo.
- **Pasos:**

```
Elegir almacén de destino (igual que arriba: rutas habituales; la no habitual solo con `almacenes.todos`,
  con aviso amarillo y observación obligatoria, X-03)
  -> el destino es uno solo para todo el archivo
Descargar la plantilla (código, nombre, cantidad, código de pieza, serie), o subir el archivo, o pegar la tabla copiada de Excel
Indicar qué columna es cada dato: solo si no se reconocen solas por el encabezado (TR-12);
   si se reconocen, la vista previa aparece sola, con esqueleto de carga. «Relacionar columnas a mano» sigue disponible
   código, nombre (de ayuda, TR-13), cantidad y, si es por pieza, código de pieza o serie
Vista previa en tabla, de 12 en 12: una fila por renglón del archivo, con su estado
   Correcto | Aviso | Error, artículo, cantidad y lo disponible en el origen
   Resumen arriba: correctas, con aviso, con error
   Aviso si el archivo ya se usó para otro traspaso
   Banner de ruta: habitual, o no habitual con la observación obligatoria
Confirmar -> vale de traspaso con folio CLAVE-TRS y QR; estado En tránsito (X-06)
```

- **Decisiones:**
  - Cada fila pasa por la misma evaluación que un escaneo (X-02, X-04, X-09); el servidor decide el nivel y la pantalla solo lo muestra.
  - Un rojo bloquea **todo** el traspaso (RG-09). Para seguir, se corrige el archivo y se vuelve a subir, o se usa «Dejar fuera las filas con error», que pide confirmar y dice cuántas son y cuáles; las filas dejadas fuera no se envían.
  - Una fila en amarillo avisa y no detiene; por ejemplo, un nombre que no coincide con el del catálogo (TR-13). Las filas del mismo artículo por cantidad se unen en una; un artículo por pieza lleva una fila por pieza.
  - Más de 500 filas: se rechaza el archivo completo con el motivo en español llano.
  - Archivo ya usado: aviso en la vista previa; para confirmar hay que aceptarlo expresamente.
  - Tocar «Confirmar» dos veces, o perder la conexión y reintentar, no duplica el vale (el dispositivo manda su `id_lote`; una repetición devuelve el mismo vale).
- **Éxito:** igual que la captura manual: las existencias salen del origen y quedan En tránsito (X-01); resultado con folio y QR.
- **Error:** destino inválido, un renglón en rojo (sin dejarlo fuera) o un archivo ilegible: no se guarda nada.
- **Cancelación:** hasta «Confirmar» no se guarda nada; el archivo no se conserva en el servidor.
- **Con escaneo:** la lista y el escaneo se pueden combinar antes de confirmar: lo que viene del archivo entra como renglones normales del borrador.

## Flujo 10: Traspaso, recepción (quien tiene `traspasos.recibir` en el almacén de destino)

- **Entrada:** Inicio -> Recibir (n); o escanear el QR del traspaso.
- **Precondiciones:** `traspasos.recibir` (distinto de `traspasos.operar`, que es solo para enviar). Quién recibe en un almacén lo define ese permiso: de inicio lo traen el Supervisor, el Almacenista y el Administrador (tabla 8.2 y AC-31; el texto de X-01 que decía lo contrario estaba atrasado y se corrige en la iteración 01); armar y enviar el traspaso no lo implica. Está construido en el código (`recibir.tsx`, `recibir-detalle.tsx`); falta comprobarlo en el entorno desplegado (lista de verificación de FEAT-015).
- **Pasos:**

```
Abrir el traspaso
  -> Recibir todo
  -> o escanear renglón por renglón (X-11)
  -> o marcar renglones con su casilla y ajustar la cantidad con − y +
  -> en una lista larga: buscar un renglón, filtrar «Pendientes» / «Todos» / «Con diferencia»
     y seguir el avance en el contador «12 de 40 revisados»
Confirmar -> vale de recepción; el traspaso queda Recibido
```

- **Lista larga (traspasos de cientos de renglones, FEAT-009):** el encabezado muestra «12 de 40 revisados» (un renglón está revisado cuando se marcó, se escaneó o se le puso cantidad) y una barra de avance. Un cuadro de búsqueda filtra por código, nombre o serie, y el filtro «Pendientes» oculta lo ya revisado. «Recibir todo» marca todos los renglones **pendientes**, incluidos los que el filtro oculta. Escanear un código marca su renglón y lo lleva a la vista; si el código no es del traspaso, avisa (X-12). La cantidad de cada renglón por cantidad es editable (teclear, o − y +) y no pasa de lo pendiente (X-11). Los renglones con diferencia se resumen arriba con «Falta recibir n» antes de confirmar y piden la observación (RG-14). Estas ayudas son de la interfaz; el servidor evalúa lo mismo que antes.
- **Decisiones:** lo que no se reciba sigue En tránsito y el traspaso queda "Recibido con diferencias" (X-13). Mientras le falte algo, el traspaso sigue en la lista de por recibir y se puede recibir otra vez hasta completarlo; entonces queda Recibido. "Recibir todo" manda todos los renglones pendientes del traspaso.
- **Sin cambios de reglas por FEAT-009:** un traspaso armado con una lista de Excel se recibe con las mismas reglas que uno escaneado (X-10 a X-13, RG-14); el Excel solo arma la salida. Lo que cambia es la pantalla, para listas largas (arriba).
- **Éxito:** las existencias entran al destino, con origen y destino conservados (X-07).
- **Error:** el traspaso es para otro almacén (X-10); lo escaneado no pertenece a este traspaso (X-12); quien no tiene `traspasos.recibir` no ve «Recibir» y el servidor responde 403.
- **Iteración 01, sin construir (FEAT-015):**
  - Un **traslado lateral** se recibe igual que cualquier traspaso (X-10 a X-13 y X-15), con la etiqueta «Traslado desde Midrex» y «Validó: Pedro» en «Por recibir» y en el contador del Inicio (X-20). Si quien recibe tiene los avisos activos, le llega la notificación informativa. El destino no rechaza: recibe lo que llegó o pide al origen cancelarlo (X-14).
  - **Envió y recibió la misma persona** (posible con dos almacenes en el conjunto, AC-36): aviso amarillo «Tú enviaste este traspaso. Explica por qué también lo recibes.», observación obligatoria, marca en el vale de recepción y lista de revisión. Aplica a todo traspaso (X-21).
  - Con varios almacenes en el conjunto, se recibe en el **almacén activo**: para recibir uno que va a otro almacén del conjunto, primero se cambia de almacén (AC-38, Flujo 29).
  - En la app de Android, los traspasos que vinieron en el paquete se reciben sin conexión (Flujo 33, OF-09).

## Flujo 11: Baja y vale de no adeudo (RH o almacenista)

- **Entrada:** RH: ficha del trabajador -> Iniciar baja. Almacenista: ficha del trabajador -> Vale de no adeudo.
- **Pasos:**

```
Iniciar baja -> el trabajador pasa a Baja en proceso (B-01)
Se muestran sus pendientes de todos los almacenes (B-02)
  -> con pendientes -> recibir devoluciones (flujo 8)
  -> sin pendientes -> el almacenista emite el vale de no adeudo (B-04)
Vale emitido -> el trabajador queda Inactivo (B-08)
RH ve "No adeudo emitido" en su consulta (B-09)
```

- **Decisiones:** los consumibles no cuentan (B-03); RH puede cancelar la baja en proceso (B-07).
- **Éxito:** vale de no adeudo con folio; trabajador inactivo hasta su reingreso.
- **Error:** intentar emitir con pendientes muestra la lista de lo que falta.

## Flujo 12: Consultar (todos)

- **Entrada:** Consultar; o el campo de búsqueda.
- **Pasos:**

```
Escanear o escribir
  -> credencial o trabajador -> ficha: vigencia y resguardo (C-01)
  -> pieza -> estado, inspección, quién la tiene e historial (C-02); si no tiene serie, la insignia «Serie pendiente» (E-xx)
  -> artículo -> existencias por almacén y quién lo tiene (C-03)
  -> vale -> detalle (C-04)
  -> texto -> lista de coincidencias: artículos, piezas y trabajadores (C-06)
```

- **Éxito:** respuesta en una sola pantalla, con atajos a la acción siguiente (entregar, devolver, inspeccionar).
- **Vacío:** "No se encontró nada con ese código o texto".
- **Hoy:** Consultar busca texto solo al oprimir Enter.
- **Iteración 01, sin construir (FEAT-019):** la lista aparece mientras se escribe, 300 ms después de la última tecla y con 2 caracteres o más; Enter busca en ese instante (con 1 carácter, solo la identificación exacta); la pistola y la cámara van directo al escaneo, sin lista (UX-01). Una respuesta vieja nunca se pinta y la lista anterior se atenúa mientras llega la nueva (UX-02). Encuentra trabajadores por palabras en cualquier orden («perez juan»), número de empleado y código de credencial; artículos por nombre, marca y código; piezas por código, serie y artículo (UX-03). Cada pieza dice dónde está («En resguardo de Juan Pérez (E-000123)») y cada artículo retornable por cantidad, cuánto hay y cuánto tienen los trabajadores (UX-04). Lo mismo aplica a los buscadores de Entregar, Devolver y Trasladar.

## Flujo 13: Inspección y estado de pieza (almacenista o supervisor)

- **Entrada:** ficha de la pieza -> Inspeccionar | Marcar No apta | Ajustar vigencia.
- **Pasos:**

```
Inspeccionar -> revisar etiquetas, costuras, cintas, herrajes y conectores (P-01)
  -> Apto -> queda vigente hasta la fecha que resulte de su vigencia
  -> No apto -> observación obligatoria -> la pieza ya no se entrega
Marcar No apta -> observación obligatoria (P-03)
Ajustar vigencia (supervisor o administrador) -> nueva fecha y motivo obligatorio -> queda en el historial y en la lista de revisión (P-07)
```

- **Éxito:** el estado y la inspección aparecen en el historial de la pieza; el semáforo los respeta de inmediato.

### Iteración 01, sin construir: flujo de inspección rehecho (FEAT-016)

Lo pidió el track: definir las reglas del equipo de alturas, poder modificar la vigencia, configurar el aviso de «por vencer» y **rehacer el flujo de la pantalla**. Las pueden hacer almacenista y supervisor (`piezas.inspeccionar`), pero el flujo se diseña **para el almacenista**, primero celular (D-10, P-01). La lista de lo que hay que inspeccionar es el Flujo 28.

- **Entrada:** Inspecciones → «Inspeccionar» y escanear la pieza; o «Inspeccionar» desde un renglón de la lista (Flujo 28); o la ficha de la pieza.
- **Precondiciones:** `piezas.inspeccionar`; la pieza está en el almacén activo del usuario (AC-38) y no está en tránsito, en mantenimiento, en calibración ni en baja (P-17).
- **Pasos (una pieza, P-14):**

```
Escanear la pieza -> la ficha trae `inspeccion_posible`; si no se puede, lo dice aquí y no deja seguir (P-17):
  en tránsito «Inspecciónala cuando la reciban» | en mantenimiento o calibración «Regrésala al servicio y luego inspecciónala»
  de otro almacén (404, AC-06) | código de artículo «Escanea el código de la pieza, no el del artículo» (422)
Ficha breve: artículo, código, serie (o «Serie pendiente»), estado, dónde está, «Vale hasta 01/10/2026 (venció hace 5 días)»,
  «Una inspección dura 180 días» y las últimas inspecciones (fecha, resultado y quién) (P-09)
Cinco puntos: etiquetas, costuras, cintas, herrajes y conectores -> cada uno Bien | Mal | No aplica; se contestan los cinco
Resultado: un punto Mal propone No apto, pero decide la persona
Observación: obligatoria si es No apto (P-01) o si es Apto con algún punto Mal («Explica por qué sigue Apta»; P-14)
Foto opcional (una; PNG, JPEG o WebP hasta 3 MB)
Resumen con la fecha que calcula el servidor: «Quedará vigente hasta el 6/04/2027» o «Quedará No apta. No se podrá entregar hasta una nueva inspección.»
Guardar -> la fecha de la inspección es la de hoy del servidor; no se captura (RG-11)
  -> «Inspección guardada» con «Inspeccionar otra»; al volver a la lista, la pieza ya no sale
```

- **Varias piezas (P-16):** «Varias piezas» abre el escáner continuo; cada pieza entra a una lista con su vigencia actual y la que quedará (una repetida suena y no se agrega; una que no se puede inspeccionar entra en rojo con su motivo). «Revisar esta» abre el flujo de una pieza para la que tiene algo mal; «Todas Apto» pide confirmar «Revisé etiquetas, costuras, cintas, herrajes y conectores de estas 11 piezas y están bien». Cada pieza es su propia inspección, en su propia transacción: una rechazada no detiene a las demás («11 guardadas, 1 no se guardó: ALT-0300 va en tránsito»). Hasta 50 por lote; reintentar no duplica (cada pieza lleva su `id_cliente`).
- **Modificar la vigencia, dos cosas distintas (P-09):** el **periodo** del artículo o de la categoría («Una inspección dura 120 días», con `catalogo.administrar`; aplica a las inspecciones nuevas, no recalcula las fechas de las ya inspeccionadas) y la **fecha** de una pieza («Ajustar fecha», con `piezas.ajustar_vigencia`, motivo y sin pasar del tope; quien inspeccionó no ajusta la suya, 403 `AJUSTE_PROPIO`; P-07).
- **Configurar el aviso (P-10):** «Avisar antes de que venza» en la categoría y en el artículo, de 1 a 90 días; el artículo gana a la categoría y la categoría al general (`INSPECCION_AVISO_DIAS`, 7). Junto al campo se ve de dónde sale el valor: «15 (de este artículo)», «10 (de la categoría)» o «7 (general)». Lo usan E-11, la lista, la tarjeta del Inicio, el contador del menú y la app de Android.
- **Errores:** 422 con regla P-01 o P-14 (falta observación o faltan puntos); 409 `PIEZA_EN_TRANSITO` y `PIEZA_EN_MANTENIMIENTO` (P-17).
- **Con varios almacenes en el conjunto:** en una pieza de otro almacén del conjunto el botón dice «Cambiar a HYL e inspeccionar» (T-6 del maestro, AC-38, AC-39).
- **Sin conexión:** la app de Android registra la inspección y la No apta por la cola (Flujo 33, OF-09); su vigencia se cuenta desde la fecha de captura (OF-19).

### Registrar la serie de una pieza (con `piezas.registrar_serie`)

- **Entrada:** ficha de la pieza con la insignia «Serie pendiente» -> «Registrar serie»; o el renglón amarillo de una entrega; o la lista del seguimiento filtrada por «Serie pendiente».
- **Pasos:** escribir o escanear el número de serie del fabricante -> Guardar. El servidor guarda la serie y deja la auditoría `pieza.registrar_serie`.
- **Decisiones:** solo se **pone** la serie a una pieza que no la tiene; si ya tiene, no se ofrece el botón (409 `SERIE_YA_REGISTRADA`). Una serie que ya existe en otra pieza del mismo artículo se rechaza con «Esa serie ya está registrada en otra pieza» (409 `SERIE_REPETIDA`).
- **Éxito:** la ficha ya no muestra la insignia; la pieza deja de avisar en las entregas.
- **Segunda entrega:** completar muchas series de una vez con un Excel (`codigo pieza`, `serie`).

## Flujo 14: Cancelar un vale (quien lo hizo, o el supervisor)

- **Entrada:** detalle del vale -> Cancelar | Cancelar y rehacer; o Consultar -> Mis movimientos de hoy, que lista los vales que hizo el usuario ese día (C-12).
- **Pasos:** escribir el motivo -> confirmar -> vale de cancelación con folio; el original queda marcado como cancelado (K-01, K-02). Con "Cancelar y rehacer" se abre además un borrador con los mismos renglones, sin firma ni autorización, para corregirlo y confirmar de nuevo (K-05).
- **Decisiones:** se cancelan entradas, entregas, devoluciones y traspasos en tránsito (K-04).
- **Éxito:** las existencias y el resguardo regresan a como estaban; los dos vales quedan en el historial.
- **Error:** si lo que movió el vale ya se movió después, o las existencias no alcanzan, no se cancela y se explica por qué (K-03).
- **Iteración 01, sin construir:** la cancelación de una entrega hereda su proyecto, para que el uso se descuente del mismo proyecto, aunque ya esté cerrado (PR-14). «Cancelar y rehacer» una entrega de EPP evalúa el borrador nuevo completo y, si el despacho es con aprobación, se vuelve a enviar: la autorización del vale cancelado sigue usada (K-05, A-03). Un vale capturado sin conexión se cancela después de sincronizarse (OF-09).

## Flujo 15: Reportes (según el rol)

- **Entrada:** Reportes -> Existencias | Movimientos | Adeudos | Consumo.
- **Pasos:** elegir filtros (almacén, periodo, trabajador, artículo y, en movimientos, tipo y usuario) -> tabla -> Descargar CSV.
- **[NUEVO] Bitácora del almacén (SG-05):** «Movimientos» pasa a ser la bitácora de un almacén (con `bitacora.ver` o `reportes.movimientos`). Cada fila dice si fue **Entrada**, **Salida** o **En camino** respecto al almacén que se ve y enlaza al vale y al trabajador. Filtros nuevos: pieza o número de serie, y «Solo los míos». Un traspaso recibido aparece como entrada en el almacén destino y como salida en el de origen.
- **Alcance:** cada usuario ve lo de su almacén, también con el filtro de usuario, que para el almacenista es solo informativo. Quien tiene `almacenes.todos` ve todos los almacenes y filtra por cualquier usuario para rastrear una desaparición (C-11).
- **Vacío:** "No hay registros con esos filtros".
- **Iteración 01, sin construir:** la bitácora pasa a `/bitacora`, con un renglón por vale (Flujo 26, FEAT-017) y la de hoy como pestaña «Detalle por renglón». `/reportes/adeudos` redirige a Deudores (Flujo 27, DU-09). El reporte de consumo gana el filtro de proyecto (C-08, DU-08). Con varios almacenes en el conjunto, los reportes muestran todos los del conjunto (AC-37).

## Flujo 16: Etiquetas (supervisor, Compras y RH)

- **Entrada:** Etiquetas. Permiso `etiquetas.imprimir`, que de inicio tienen Supervisor, Compras y RH (tabla 8.2 de las reglas; el Administrador lo tiene por tener todos).
- **Pasos:** elegir qué imprimir (credenciales, piezas o estantes; en credenciales, la credencial completa o solo el código QR) -> seleccionar -> hoja con QR y texto -> imprimir desde el navegador. Una credencial suelta también se imprime o se descarga como PNG desde la ficha del trabajador.
- **Iteración 01, sin construir (FEAT-019):**

```
Elegir tipo: credencial (completa o solo QR) | pieza | estante
Elegir formato: «9 grandes» (3 × 3) | «18 medianas» (3 × 6, por omisión) | «30 chicas» (3 × 10); la credencial completa siempre en hoja de 8 (UX-05)
Elegir origen o marcar a mano (UX-06): selección manual | piezas de una importación (por su lote) |
  trabajadores dados de alta entre dos fechas | todas las piezas de un artículo
  -> el origen solo preselecciona: se puede quitar o agregar
Opcional: «Empezar en la etiqueta n.º N» para una hoja adhesiva ya usada
Vista previa a escala, «37 etiquetas · 3 hojas carta», con avisos de legibilidad en amarillo (UX-07)
«Descargar PDF» (acción principal) -> un solo archivo con todas, avance por hoja y «Cancelar» -> `etiquetas-piezas-18-20261008-1542.pdf`
«Imprimir» queda como acción secundaria
```

- **Decisiones:** hasta 1000 etiquetas por PDF (con más, se pide dividir); el QR mide 20 mm o más y contiene exactamente el código (RG-10); el código nunca se corta; un código largo que no se leería en tamaño chico se avisa sin impedirlo (UX-07). El PDF se arma en el navegador, también en la app de Android.
- **Pendiente:** hoy `GET /api/etiquetas?tipo=piezas` lista piezas de todos los almacenes sin aplicar AC-06 (incongruencia 7 del maestro; decisión abierta 8 de FEAT-019).

## Flujo 18: Usuarios y roles (administrador)

- **Entrada:** Menú -> Administración -> Usuarios (`/usuarios`) o Roles y permisos (`/roles`); permiso `acceso.administrar` (AC-08).
- **Usuarios:** búsqueda por nombre o usuario a la vista y filtros de rol, almacén y estado en "Filtros". "Nuevo usuario" abre una hoja (nombre, usuario, rol, almacén, contraseña y, si el rol autoriza, PIN opcional). El almacén solo se pide si el rol no tiene `almacenes.todos` (RG-07). "Editar" cambia nombre, rol y almacén; "Contraseña" abre una hoja con confirmación (se cierran las sesiones abiertas y se quitan los bloqueos); "Inactivar" o "Reactivar" piden confirmación. Nadie puede inactivarse a sí mismo desde la pantalla, y el servidor rechaza inactivar o cambiar de rol al último administrador (`ULTIMO_ADMINISTRADOR`, AC-09).
- **Roles:** tarjetas con nombre, descripción, número de usuarios y de permisos; "Nuevo rol" crea uno sin permisos y "Duplicar" copia los permisos de otro. "Ver permisos" abre `/roles/:id`: la matriz de permisos agrupada por módulo, con un interruptor por permiso, su descripción en lenguaje de persona y la clave técnica en segundo plano. Los permisos de información reservada (costos, CURP y NSS) llevan su advertencia. Activar un permiso de acción activa también los de ver que necesita. Los que no se pueden cambiar quedan deshabilitados con su razón: el Administrador siempre lleva `acceso.administrar`, nadie se lo quita a su propio rol, y no se quita un permiso de ver mientras otro lo necesita.
- **Botón por grupo (FEAT-008, 4.5):** cada grupo de la matriz trae un contador («3 de 5 activos») y un botón: «Activar todos» si está vacío o a medias, «Quitar todos» si está completo. Arriba de la matriz, opcionalmente, «Activar todo» y «Quitar todo». El botón **solo mueve los interruptores en pantalla** (no guarda): los cambios se revisan en la barra de abajo y se pueden descartar. Respeta lo que bloquea un interruptor (el permiso protegido se queda como está y el botón avisa cuántos no pudo mover y por qué) y las dependencias (activar enciende el permiso de ver que necesita; quitar un permiso de ver quita los que dependen de él). Al guardar, la confirmación nombra aparte los datos reservados que se agregan («incluye ver costos y datos personales»). La API no cambia: `PUT /api/roles/{id}/permisos` con la lista final.
- **Guardar:** con cambios aparece una barra con "Se agregan 2 permisos y se quitan 1" y qué cambia exactamente (también si el rol recibe o pierde `almacenes.todos` y qué le pasa a sus usuarios). "Guardar cambios" pide confirmación; el cambio aplica en la siguiente acción de cada persona (AC-10) y la sesión de quien se edita su propio rol se actualiza al instante.
- **Estado del rol:** "Inactivar rol" y "Eliminar rol" quedan deshabilitados, con la razón escrita debajo, si el rol es el Administrador, es uno de los cinco iniciales (solo la eliminación) o tiene usuarios (AC-11).
- **Sin permiso:** "Tu rol no puede hacer esto".
- **Iteración 01, sin construir:** «Editar» asigna un **conjunto** de almacenes con uno activo; en el caso normal sigue siendo un solo selector «Almacén», y «Agregar otro almacén» es una opción secundaria (AC-36, AC-41). Con `despacho.autonomia` (solo el Administrador), la columna y el control «Despacha EPP sin aprobación», con motivo obligatorio (Flujo 30, DE-14).

## Flujo 17: Personal por almacén (supervisor y administrador)

- **Entrada:** Menú -> Personas -> Personal del almacén (`/personal`, permiso `almacenes.asignar_personal`; AC-12, AC-13). Antes colgaba del grupo Supervisión; FEAT-008 lo pasa a Personas.
- **Pasos:** buscar por nombre o usuario, o filtrar por almacén o "Sin almacén" -> "Cambiar almacén" en la persona -> elegir el almacén (o "Sin almacén") -> la hoja dice en una frase qué cambiará ("Ana pasará de Kepler a Contratistas") -> Guardar -> aviso de éxito y la lista se actualiza.
- **Quiénes aparecen:** solo quienes operan un almacén (los que no tienen `almacenes.todos`). El servidor decide si el cambio procede; si lo rechaza (422), la hoja muestra su mensaje junto a la lista desplegable.
- **Efecto:** aplica en cuanto la persona vuelve a usar el sistema; no toca vales ni movimientos ya hechos.
- **Vacío:** "No hay personal con ese filtro". Sin el permiso, "Tu rol no puede hacer esto".
- **Iteración 01, sin construir:** con `almacenes.asignar_personal` (sin `acceso.usuarios`), el supervisor solo agrega o quita almacenes **de su propio conjunto** y no toca los almacenes ajenos de esa persona (403); nadie se amplía su propio conjunto así (AC-41).

## Flujo 19: Pedir una compra urgente (almacenista y supervisor)

- **Entrada:** Menú -> Operación -> Pedir compra urgente (`/compras/nueva`, permiso `compras.solicitar`). No es un botón del inicio: el inicio del almacenista sigue con Entregar, Devolver y Consultar. Desde "Compras urgentes" también está el botón "Pedir compra urgente". Al abrir la pantalla se genera el `id_cliente` y se guarda con lo escrito en un borrador del dispositivo (SC-10).
- **Pasos:** (1) ¿Qué hace falta? Se busca un artículo del catálogo por nombre o código (espera 300 ms tras dejar de escribir) o se toca "No está en el catálogo" y se describe con texto libre, por ejemplo "Llave métrica 24 mm" (SC-02). (2) Cantidad, con menos, más y teclado numérico. (3) ¿Para qué trabajo? Respuestas rápidas ("Mantenimiento programado", "Reparación urgente", "Falta de existencia", "Otro") que llenan el motivo, que también se puede escribir. (4) Urgente (elegida) o Normal. (5) Resumen y "Enviar solicitud", deshabilitado hasta tener lo obligatorio. Quien tiene `almacenes.todos` elige además el almacén (obligatorio); los demás piden para el suyo y no lo ven como campo (SC-01).
- **Éxito:** pantalla "Solicitud enviada" con el folio (`MID-SOL-000001`), el estado y el resumen; "Ver mis solicitudes" lleva a `/compras/mias` y "Pedir otra" empieza una nueva con otro `id_cliente`. Se borra el borrador.
- **Doble toque o reintento:** el botón se deshabilita al enviar y el servidor devuelve la misma solicitud si el `id_cliente` ya existía con los mismos datos (SC-10). Sin conexión, la solicitud se conserva y se reintenta con el mismo identificador al volver a tocar "Enviar solicitud".
- **Errores:** los de un dato (422) salen junto al campo; `ID_CLIENTE_EN_USO` (409) avisa que ese envío ya existía con otros datos, renueva el identificador y manda revisar "Compras urgentes"; sin almacén asignado, la pantalla lo dice y no deja enviar.
- **Sin permiso:** "Tu rol no puede hacer esto". Compras (`compras.atender`) atiende, no pide.

### Compras urgentes de mi almacén (`/compras/mias`)

- **Entrada:** Menú -> Operación -> Compras urgentes (permiso `compras.solicitar`). Para el Administrador (`almacenes.todos`) se llama "Solicitudes de compra" y trae todos los almacenes con un filtro de almacén.
- **Pasos:** búsqueda por folio, artículo o motivo; en "Filtros", estado, urgencia y "Solo las que yo pedí" (`mias=true`); lista paginada de 20 en el orden del servidor (SC-03): pendientes primero, urgentes antes y las más antiguas primero. Cada fila lleva folio, qué se pidió, cantidad, urgencia, estado, quién la pidió y cuándo; si Compras dejó una nota (por ejemplo, al rechazar) se lee en la misma fila (SC-05). Tocar una solicitud abre su detalle (`/compras/:id`).
- **Cancelar:** el botón "Cancelar" aparece solo en las pendientes en cuya lista de `acciones` el servidor incluye `cancelar` (la pidió el usuario, o es supervisor de su almacén, o tiene `almacenes.todos`; SC-07). Pide confirmación con una nota opcional. Si Compras ya la tomó (409 `NO_CANCELABLE`), el aviso lo dice y la lista se actualiza.
- **Vacío:** "Todavía no hay solicitudes". Error: mensaje y "Reintentar".

## Flujo 20: Atender las solicitudes de compra (Compras)

La solicitud de compra urgente (reglas SC-01 a SC-11). Quien pide la levanta desde su almacén; este flujo es el de Compras, que ve la de **todos** los almacenes sin ver su inventario (SC-03).

- **Entrada:** Menú -> Solicitudes de compra (`/compras`, permiso `compras.atender`). En el inicio de Compras es un botón con el número de pendientes, y el menú lleva el mismo número; se actualiza solo cada pocos segundos y al actuar sobre una solicitud.
- **La cola:** arriba, tres tarjetas táctiles (Pendientes, En compra y Compradas por ingresar) con su conteo; tocar una filtra la lista y tocarla otra vez quita el filtro. La tarjeta de pendientes dice cuántas son urgentes. Debajo, la búsqueda (folio, artículo, descripción o motivo) siempre a la vista y "Filtros" (estado, urgencia, almacén y periodo, con su contador y sus chips). La lista llega ya ordenada por el servidor: primero lo pendiente, luego lo que está en compra, lo comprado y al final lo cerrado; en cada grupo, las urgentes primero y las más antiguas primero. En computadora y tableta es una tabla (folio, qué se pidió, cantidad, almacén, urgencia y estado, solicitante, fecha y acción); en celular, tarjetas. Una urgente pendiente se distingue por su franja y fondo rojos suaves y su insignia roja.
- **Acción rápida:** en cada renglón, el botón de la acción principal que el servidor ofrece (Tomar, Comprada o Ingresar), con su confirmación. Nada se deduce del rol: los botones salen de `acciones` de la respuesta.
- **El detalle (`/compras/:id`):** folio con sus insignias de estado y urgencia, qué se pidió (con el enlace al artículo del catálogo, si lo hay), cantidad, para qué se necesita, almacén, quién la pidió, fechas en hora de México, la nota de Compras (en una rechazada, "Por qué se rechazó") y el vale de entrada ligado, con enlace a `/vales/:id`. Abajo, la **línea de tiempo**: cada cambio de estado, del más antiguo al más reciente, con quién, cuándo y su nota (SC-08). Las acciones van en un pie fijo en celular y tableta, y al final del contenido en computadora; una es la principal (azul) y las demás, secundarias.
- **Las acciones (SC-04):** Tomar (confirmación breve; pasa a En compra). Rechazar abre una hoja con la nota obligatoria y respuestas rápidas (SC-05). Marcar como comprada abre una hoja con una nota opcional (proveedor, día de llegada). Ingresar a Kepler abre una hoja donde se liga, si se quiere, el vale de ENTRADA con el que se metió lo comprado: se elige de las últimas entradas **de Kepler** o se escribe su folio (SC-06). La hoja avisa que la entrada queda en Kepler y que el almacén que la pidió la recibe después por traspaso (EK-05), y que ingresar no suma existencias por sí solo, porque suben con el vale que se registra en «Dar entrada» (SC-11). Tras cada acción aparece un aviso breve y la pantalla se actualiza sin salir.
- **Quien pide:** abre la misma pantalla `/compras/:id` desde su lista y no ve las acciones de Compras; si está pendiente y es quien la pidió, el supervisor de su almacén o el administrador, ve **Cancelar solicitud** (hoja con nota opcional, SC-07). Una solicitud de otro almacén responde "No encontramos esta solicitud".
- **Errores:** los del servidor se escriben dentro de la misma ventana, junto a lo que falló: un vale que no sirve (422, SC-06) bajo la lista de vales; una solicitud que otra persona ya cambió (409, SC-04) como aviso en la ventana y el detalle se recarga.
- **Vacío y error:** "No hay solicitudes de compra" (con filtros, "No hay solicitudes con ese filtro" y "Quitar filtros"); si no carga, mensaje y Reintentar. Sin el permiso, "Tu rol no puede hacer esto".

## Flujo 21: Administración de almacenes (administrador)

Parte de [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md) (AL-01 a AL-05).

- **Entrada:** Menú -> Administración -> Almacenes (`/almacenes`, permiso `almacenes.administrar`). Sin el permiso, la entrada no existe en el menú y la ruta dice «Tu rol no puede hacer esto».
- **Lista:** una fila por almacén (tabla en computadora y tableta, tarjetas en celular) con clave, nombre, tipo, de cuál depende, estado en una insignia (Activo o Cerrado) y el resumen (existencias, piezas en resguardo, usuarios). Los cerrados salen atenuados. Búsqueda a la vista y estado en «Filtros». Los números salen de `GET /api/almacenes?resumen=true`.
- **Alta:** «Nuevo almacén» abre una hoja con clave, nombre, tipo y «De qué almacén depende» (obligatorio salvo el central; solo se ofrecen los activos). Errores del servidor junto al campo: clave o nombre repetidos, ya hay central, padre inválido. Al guardar, aviso y el almacén aparece en la lista.
- **Editar:** nombre y de qué depende; la clave solo mientras el almacén no tenga folios (si los tiene, el campo sale bloqueado con la razón). Un almacén cerrado no se edita.
- **Inactivar:** el botón está en la ficha del almacén. Una confirmación nombra el almacén y dice en una frase qué pasará. El botón «Inactivar» queda deshabilitado mientras `puede_cerrar` sea falso y, debajo, cada bloqueo se explica con su enlace: existencias (qué artículos y cuántas; «Regrésalas por traspaso a …»), traspasos en tránsito (con los folios), almacenes que dependen de él, y usuarios (quiénes, con enlace a Personal del almacén para reasignarlos). Las piezas en manos de trabajadores no bloquean y se avisan. Si el servidor responde un bloqueo (409), la ventana lo escribe junto al botón y la ficha se actualiza.
- **Reactivar:** «Reactivar» en un almacén cerrado, con confirmación; vuelve a operar con su clave y su historial. Si su padre está cerrado, el botón dice por qué no puede.
- **Vínculos:** desde la ficha, enlaces a sus usuarios (`/personal`), su inventario (`/inventario` filtrado) y sus solicitudes de compra. No se duplican pantallas.
- **Puesta en marcha de la red (base vacía):**

```
1. Administrador -> Almacenes -> Kepler (CENTRAL)
   (o el comando `sembrar-almacenes`, que crea los seis de una vez)
2. Contratistas (SUBALMACEN, depende de Kepler)
3. Asignar personal a cada almacén: un supervisor y los almacenistas (Usuarios y Personal del almacén)
4. Compras carga el inventario de Kepler (Importar inventario, modo Alta, o Entrada de proveedor)
5. Supervisor de Kepler -> Trasladar a Contratistas
6. Al empezar un mantenimiento: Administrador -> Nuevo almacén de tercer nivel (tipo PROYECTO, depende de Contratistas), o reactivar el que ya existe, y su personal
6 bis. [Iteración 01] Administrador -> Proyectos -> Nuevo proyecto en ese almacén, con inicio y fin estimado (Flujo 24); después RH da de alta a sus trabajadores con ese proyecto (Flujo 2)
7. Supervisor de Contratistas -> Trasladar al almacén de tercer nivel
```

- **Cierre de un almacén de tercer nivel:** el supervisor devuelve el sobrante por traspaso a Contratistas, registra faltantes y revisa el reporte de cierre ([FEAT-002](../features/FEAT-002-cierre-de-almacen.md)); el Administrador reasigna a su personal y lo inactiva. La puesta en marcha y el cierre completos, con sus reglas, están en [red-de-almacenes-y-flujo.md](red-de-almacenes-y-flujo.md). En la iteración 01 el cierre del **proyecto** (Flujo 24) es otra acción: termina las asignaciones de sus trabajadores, no toca el almacén.
- **Estados:** esqueleto al cargar; error con «Reintentar».
- **Iteración 01, sin construir:**
  - **Proyectos activos y aviso PR-12:** la lista agrega la columna «Proyectos activos». Un almacén de tercer nivel activo sin ningún proyecto activo muestra «Sin proyectos activos: considera inactivarlo» aquí y en el Inicio del Administrador. El sistema nunca lo inactiva solo; Kepler y Contratistas no generan el aviso (PR-12).
  - **Bloqueo nuevo al inactivar:** `CON_PROYECTOS_ACTIVOS`, con la lista de proyectos y el enlace a `/proyectos?almacen_id=…` para cerrarlos; `CON_USUARIOS` cuenta a quienes tienen el almacén en su conjunto, no solo como activo (AL-03).
  - **Autonomía de despacho:** «El EPP pide aprobación del supervisor», interruptor con motivo, solo con `despacho.autonomia` (Flujo 30, DE-14).
  - **Hora de descarga para equipos sin señal** (`almacen.hora_descarga`): la edita el Administrador; el supervisor la ve (OF-14).

## Flujo 22: Inicio y tablero (almacenista, supervisor y administrador)

Parte de FEAT-008 (TB-01 a TB-03).

- **Entrada:** `/` con sesión. El Inicio depende de los permisos, nunca del nombre del rol.
- **Orden de la pantalla:** primero «Lo que haces hoy» (los botones de operación del rol, grandes), debajo las tarjetas y, al final, la gráfica de lo más usado.
- **Quién ve el tablero:** quien tiene `tablero.ver` (Administrador, Supervisor y Almacenista de inicio). Con `almacenes.todos` (Administrador) ve todos los almacenes y un selector «Viendo: Todos los almacenes» con la lista de almacenes; el rótulo «Viendo: Midrex» avisa que el selector solo cambia lo que se mira, no el almacén en el que se opera. Sin `almacenes.todos`, ve solo su almacén, sin selector. Compras y RH no tienen tablero: su Inicio muestra lo suyo (solicitudes por atender, trabajadores y altas recientes).
- **Tarjetas** (de `GET /api/tablero/resumen`): Existencias, Equipo importante en resguardo, Sin existencia, Traspasos en tránsito, Entregas de hoy, Solicitudes de compra abiertas, Inspecciones por vencer y Piezas con serie pendiente. Cada una dice en una línea qué cuenta. Tocar «Equipo importante en resguardo» abre `/seguimiento` con las piezas en manos de trabajadores; «Traspasos en tránsito», `/recibir`; «Solicitudes de compra abiertas», `/compras` o `/compras/mias` según el permiso. «Piezas con serie pendiente» abre `/seguimiento` con el filtro `serie_pendiente=true`. «Alto valor fuera del almacén» (SG-04, solo con `resguardo.ver`) cuenta las piezas de alto valor y de alturas con un trabajador y abre `/seguimiento?alto_valor=true&ubicacion=TRABAJADOR`. Las demás no navegan.
- **Gráfica «Lo más usado»** (de `GET /api/tablero/consumo`): filtros Almacén (solo con `almacenes.todos`), Periodo (Hoy, 7 días, Este mes, Mes pasado, Elegir fechas; por omisión Este mes) y Categoría (por omisión Consumibles de trabajo); «Limpiar filtros»; interruptor «Separar por almacén» solo con todos los almacenes. Se actualiza al cambiar cualquier filtro, con indicador de carga y sin borrar la anterior hasta que llega la nueva. Cada barra se toca y abre el artículo (`/articulos/:id`).
- **Estados:** sin consumo en el rango, «No hubo consumo en estas fechas»; error con «Reintentar»; sin almacén asignado, el aviso «No tienes un almacén asignado» y las tarjetas en cero.
- **Sin permiso:** quien no tiene `tablero.ver` no ve el tablero y `GET /api/tablero/*` responde 403.

### Iteración 01, sin construir: Inicio del supervisor, almacenes sin proyecto y selector de almacén (FEAT-013, FEAT-014, FEAT-016, FEAT-020)

- **Alcance (AC-36, AC-37, TB-01 cambiada):** el tablero muestra los almacenes del **conjunto** del usuario; lo normal es uno, y entonces todo se ve exactamente como antes, sin selector.
- **Orden del Inicio del supervisor** (`tablero.ver`, `proyectos.ver` y `reportes.valor_inventario`, que el Supervisor recibe de inicio; D-05):

```
«Lo que haces hoy» (como hoy)
Tarjetas de siempre
  + «Valor del inventario»: en almacén, en resguardo de trabajadores y total, en pesos y en unidades (TB-04)
      solo totales y su reparto por categoría y por almacén; nunca el costo unitario (RG-12); sin el permiso, solo unidades
  + «Proyectos por vencer»: activos cuyo fin estimado cae en los próximos 7 días o ya pasó -> `/proyectos` filtrado (TB-08)
  + «Inspecciones»: vencidas · por vencer · sin inspección -> `/inspecciones` en la pestaña más urgente (P-13)
  + [app de Android] «Conflictos de sincronización: n» y «Equipos sin contacto: n» (OF-30)
«Uso por proyecto»: tabla con barras horizontales, no una gráfica nueva (TB-05)
  por proyecto de sus almacenes: retornables en resguardo hoy y consumibles consumidos en el rango, en unidades y en pesos,
  trabajadores asignados, fechas y situación; un renglón «Sin proyecto»; «N artículos sin costo» si los hay
  en celular, una tarjeta por proyecto con su barra
«Lo más usado» (TB-02, como hoy)
```

- **Atribución (TB-06, D-13):** un proyecto entra al uso del supervisor si **su almacén** está en su conjunto, sin importar qué almacén entregó. El EPP que Contratistas entrega a un trabajador del proyecto de Midrex aparece en el uso del supervisor de Midrex, no en el de Contratistas; el vale sigue siendo de Contratistas (bitácora y «Lo más usado»). Lo que un trabajador tiene en resguardo cuenta para el proyecto de la última entrega de ese artículo.
- **Selectores (TB-07):** con más de un almacén, «Todos mis almacenes» o uno; en la tabla de uso, «Todos los proyectos» o uno (con uno, su reparto por categoría). Se rotulan «Viendo: …» y **no** cambian el almacén activo (como TB-01). Con un solo almacén o un solo proyecto, no hay selector. El selector que sí cambia dónde se opera es el de la barra superior (Flujo 29).
- **Inicio del Administrador:** lo de hoy, más las tarjetas «Almacenes sin proyectos» (PR-12; solo con `almacenes.administrar`) y «Proyectos por vencer», y el uso por proyecto de todos los almacenes con selector (TB-08). Tocar «Almacenes sin proyectos» abre `/almacenes` filtrado.
- **Inicio del almacenista:** sin valor ni uso por proyecto (no tiene `reportes.valor_inventario`). Gana el contador «En espera (n)» junto a Entregar, con las solicitudes de despacho aprobadas resaltadas (DE-15), y la tarjeta Inspecciones si tiene `inspecciones.ver` (P-13).
- **Errores:** un `almacen_id` fuera del conjunto se ignora (AC-37). Sin `reportes.valor_inventario`, `valor` viaja en `null` y la pantalla muestra solo unidades. Cuando un grupo tiene un solo artículo con costo, su valor en pesos sale como «—», para no revelar el costo unitario por división (T-2 del maestro).

## Flujo 23: Tutorial guiado de práctica (cualquier usuario con sesión)

Parte de FEAT-010 (TU-01 a TU-10). Es solo de interfaz: no usa la API ni cambia datos.

- **Entrada:** el interruptor «Tutorial». Al encenderlo aparece la lista de recorridos que los permisos de la sesión permiten, y una banda fija «Práctica: nada de esto se guarda». No hay pantalla de bienvenida.
- **Recorridos** (cada uno solo con su permiso, nunca por el nombre del rol):

| Recorrido | Permiso | Pasos que se resaltan |
|---|---|---|
| Entregar | `entregas.crear` | Escanear o escribir el trabajador → «Continuar» → escanear artículos y leer el semáforo → «Continuar» → firma → «Confirmar entrega» → folio de práctica |
| Devolver | `devoluciones.crear` | Escanear la pieza → elegir la condición (Bueno, Desgaste por uso o Dañado) → «Confirmar devolución» → folio de práctica |
| Consultar | ninguno | Escanear o escribir → leer la ficha → atajo a la acción siguiente |
| Recibir un traspaso | `traspasos.recibir` | Abrir el traspaso → «Recibir todo» o marcar por renglón → «Confirmar recepción» |

- **Cada paso:** la pantalla se oscurece y se bloquea; solo el elemento del paso actúa, rodeado por un círculo y una flecha, con un globo de una o dos frases. Un paso de lectura trae «Siguiente»; «Salir» y `Escape` terminan siempre.
- **Escaneo en práctica:** no se enciende la cámara; el globo ofrece «Escanear un ejemplo». El campo de texto acepta los códigos de ejemplo.
- **Datos:** un trabajador y unos artículos ficticios. La confirmación muestra un folio de práctica. No se crea ningún vale, movimiento ni auditoría, no se escribe ningún borrador y «Mis movimientos de hoy» no cambia.
- **Salida:** al salir o al terminar, se quita la banda y la pantalla vuelve a operar con datos reales. El recorrido terminado se marca en el dispositivo (`localStorage`) y puede repetirse.
- **Estados:** si el ancla de un paso no existe en la pantalla, el paso se omite; sin permiso para ningún recorrido, el interruptor muestra «No hay recorridos para tu usuario».
- **Fuera del recorrido:** Trasladar (enviar), Autorización, reportes, RH, Compras y administración.
- **Iteración 01, sin construir:** el recorrido de Entregar simula la espera y una aprobación ficticia del despacho de EPP; no crea ninguna solicitud ni manda avisos (FEAT-014).

## Flujos nuevos de la iteración 01 (sin construir)

Los flujos 24 a 35 salen del [documento maestro de la iteración 01](../releases/iteration_01/README.md) y de los briefs FEAT-013 a FEAT-020. Ninguno está en el código. Si un brief y el maestro no coinciden, manda el maestro.

## Flujo 24: Proyectos (Administrador)

Parte de [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) (PR-01 a PR-07, PR-12). Primero computadora (D-20).

- **Entrada:** Menú → Almacenes → Proyectos (`/proyectos`); o las tarjetas «Proyectos por vencer» y «Almacenes sin proyectos» del Inicio; o el bloqueo `CON_PROYECTOS_ACTIVOS` al inactivar un almacén.
- **Precondiciones:** para ver, `proyectos.ver` (los proyectos de los almacenes de su conjunto; con `almacenes.todos`, todos). Para dar de alta, editar, extender, cerrar y reabrir, `proyectos.administrar` (de inicio, solo el Administrador). RH, con `proyectos.asignar`, ve todos los proyectos con sus datos generales, sin consumo ni valor (PR-07). El almacén del proyecto está activo.
- **Pasos:**

```
Lista: clave, nombre, almacén, inicio, fin estimado, situación (Vigente | Por iniciar | Fin estimado vencido | Cerrado) y trabajadores asignados
  filtros: almacén, situación y búsqueda (espera de 300 ms, UX-01)
«Nuevo proyecto» -> clave (2 a 20 caracteres; el servidor la pasa a mayúsculas), nombre, almacén, inicio y fin estimado (PR-01, PR-02)
  -> el almacén ofrece primero los de tercer nivel y al final Contratistas y Kepler «para personal general»
  -> en un almacén que no es de tercer nivel: se guarda con el aviso «Este proyecto queda en Contratistas: úsalo para personal general»
  -> nace ACTIVO; aparece «Vigente» o «Por iniciar»
Abrir un proyecto -> datos, sus trabajadores (enlace a `/trabajadores?proyecto_id=`) y, con `reportes.valor_inventario`, su uso (TB-05)
«Editar» o «Extender» -> nombre y fechas; clave y almacén solo mientras ningún vale use el proyecto (PR-03)
  -> extender un «Fin estimado vencido» lo vuelve asignable y lo saca de «Proyectos por vencer» (PR-06)
«Cerrar» -> motivo obligatorio -> confirmación: cuántos trabajadores pierden la asignación, cuántos quedan sin proyecto
   y cuántas unidades siguen en resguardo de su gente («Lo que tienen en resguardo sigue siendo su pendiente») (PR-04)
  -> el proyecto queda CERRADO y terminan todas sus asignaciones; contratos, vales y existencias no cambian
  -> si era el último proyecto activo de un almacén de tercer nivel: aviso «Sin proyectos activos: considera inactivarlo» (PR-12)
«Reabrir» -> vuelve a ACTIVO; si su fin estimado ya pasó, pide uno nuevo igual o posterior a hoy (PR-05)
  -> aviso «Las asignaciones no se restauran. RH debe volver a asignar a los trabajadores.»
```

- **Decisiones:** un proyecto que pasa su fin estimado sin cerrarse **sigue operando** (las entregas lo toman), aparece como «Fin estimado vencido» y no se ofrece para asignaciones nuevas hasta que se extienda; el sistema nunca lo cierra solo (PR-06). Los proyectos no se borran (PR-01). El mismo nombre en dos almacenes se permite; la clave los distingue.
- **Éxito:** el proyecto existe antes que sus trabajadores (D-02) y RH puede asignarlos desde el alta (Flujo 2). Cada cambio queda en el registro de cambios con el antes y el después.
- **Error:** 409 `CLAVE_REPETIDA`; 409 `ALMACEN_CERRADO` (en el alta o al reabrir); 422 `DATOS_INVALIDOS` si el fin estimado es anterior al inicio (PR-02) o falta el motivo; 409 `PROYECTO_CON_VALES` al cambiar clave o almacén de un proyecto con vales (PR-03); 409 `PROYECTO_CERRADO` al editar uno cerrado; 403 sin `proyectos.administrar`. Sin `proyectos.ver` ni `proyectos.asignar`, «Tu rol no puede hacer esto».

## Flujo 25: Despacho por aprobar (supervisor, desde el celular)

Parte de [FEAT-014](../features/FEAT-014-despacho-de-epp-con-aprobacion.md) (DE-06, DE-09, DE-11, DE-12; NT-01 a NT-09). Primero celular (D-20). Es la otra mitad del Flujo 6.

- **Entrada:** la notificación push «Midrex · EPP por aprobar» (abre `/autorizaciones/{id}`; si es un aviso agrupado, `/autorizaciones`); o Menú → Supervisión → Autorizaciones con su contador.
- **Precondiciones:** `autorizaciones.resolver` y el almacén de la solicitud en su conjunto (AC-40). Para recibir avisos: haberlos activado en ese equipo (NT-01), con la aplicación servida por HTTPS (el túnel) y, en iPhone, instalada en la pantalla de inicio (NT-08). Sin avisos, todo funciona con el contador y la lista.
- **Pasos:**

```
Primera vez en el celular: tarjeta «Activa los avisos para enterarte aunque no tengas la aplicación abierta»
  -> «Activar avisos» -> el navegador pregunta -> «Avisos activos en este equipo» -> «Mandar un aviso de prueba» (NT-01, NT-09)
Llega el aviso (sin costos, CURP, NSS ni foto; NT-03) -> lo toca (NT-04)
  -> sesión vencida -> entra y regresa a esa solicitud (Flujo 1)
Detalle de la solicitud (`/autorizaciones/:id`)
  -> foto y nombre del trabajador, número, proyecto de la entrega, almacén (si tiene varios), «Lo pide Ana Ruiz hace 1 min», cuánto le queda
  -> renglones que se resuelven (EPP y naranjas), cada uno con Aprobar | Rechazar (todos en Aprobar al abrir)
  -> renglones de contexto (herramienta en verde o amarillo) en gris, sin interruptor
  -> nota del almacenista y observaciones E-09 de los renglones (DE-05)
Resolver (DE-06)
  -> «Aprobar todo» | «Rechazar todo» (pide motivo)
  -> cambia un renglón a Rechazar -> aparece su motivo obligatorio -> el botón dice «Aprobar 3 y rechazar 1»
  -> «Listo: aprobaste 3 de 4» -> regresa a la lista
Lista (`/autorizaciones`): de la más antigua a la más nueva, con tipo (Despacho, Excedente, Traslado), foto, proyecto y contexto (DE-12)
  -> marcar varias sin excedente -> «Aprobar 12» | rechazar varias con un motivo por cada una
  -> las marcadas «Incluye excedente» se abren una por una
```

- **Decisiones:** la aprobación queda APROBADA si se aprobó al menos un renglón y RECHAZADA si ninguno (DE-06). Gana el primero que resuelve (DE-11): a los demás supervisores se les reemplaza el aviso en silencio («Midrex · Luis Gómez ya la aprobó»; NT-06). El sistema no sabe de turnos: los dos supervisores del almacén reciben todo (decisión abierta 3 de FEAT-014). El supervisor que despacha él mismo no se manda solicitud (DE-07).
- **Éxito:** el almacenista ve la respuesta en máximo 3 segundos y sigue a la firma (Flujo 6). Queda quién pidió, quién aprobó cada renglón, cuándo y por qué (A-04).
- **Error:** 409 `AUTORIZACION_RESUELTA` con quién, cuándo y cómo quedó («Ya la aprobó Luis Gómez a las 10:42»); solicitud vencida, «Venció a las 10:55» y no se resuelve (DE-09); 422 con regla DE-06 si un rechazo no trae motivo; 403 `AUTORIZACION_PROPIA` si es quien la pidió (A-05); 404 «Ya no puedes ver esta solicitud» si le quitaron el permiso o el almacén (NT-02). Avisos bloqueados en el navegador: el botón explica cómo permitirlos; el servidor sin claves VAPID esconde «Activar avisos».

## Flujo 26: Bitácora por vale y detalle del vale con PDF

Parte de [FEAT-017](../features/FEAT-017-bitacora-por-vale-y-pdf.md) (BT-01 a BT-10). Primero computadora (D-20); el detalle del vale sigue usable en el celular.

- **Entrada:** Menú → Inventario → Bitácora (`/bitacora`); `/reportes/movimientos` redirige a su pestaña «Detalle por renglón» con sus filtros; desde el resultado de una importación («Ver en la bitácora», `/bitacora?lote_id=`); el detalle del vale, también desde Mis movimientos de hoy, el QR o un enlace.
- **Precondiciones:** `bitacora.ver` o `reportes.movimientos` (BT-01); el detalle pide `vales.ver`. Cada quien ve los vales de su alcance (AC-06; con varios almacenes, su conjunto, AC-37).
- **Pasos:**

```
Pestaña «Por vale» (por omisión): un renglón por vale, el más reciente arriba, últimos 7 días, 25 por página (BT-01)
  columnas: fecha y hora, folio, tipo, entrada o salida (icono y texto), trabajador o destino, proyecto, renglones, unidades, responsable, estado
  -> con un almacén filtrado: Entrada | Salida | En camino respecto a ese almacén (BT-04)
  -> marcas: «Cancelado» con el folio de su cancelación; «Capturado sin conexión» con la hora de captura (BT-04)
  -> lote: los vales de una misma importación (partida en vales de 500) o de un traspaso por Excel salen como un renglón
     «Importación del 8 oct · 3 vales · 1,240 renglones» -> «Ver los 3 vales» lo despliega (BT-02)
Filtrar: búsqueda de pieza o serie a la vista (300 ms) y en «Filtros» periodo, tipo, usuario, trabajador, proyecto, artículo
  y, con varios almacenes, almacén; con filtro de artículo, pieza o serie, cada renglón dice «3 de 500 renglones coinciden» (BT-03)
«Descargar CSV» -> un renglón por vale con los mismos filtros
Pestaña «Detalle por renglón»: la bitácora por movimiento de hoy (SG-05), sin cambios, con su CSV
Abrir un vale (toda la fila) -> `/vales/:id` a todo el ancho desde 1280 px (BT-05)
  encabezado: folio, tipo, estado, fechas, almacén, responsable, trabajador, proyecto, «Validó», firma y QR
  «Parte 2 de 3 de la importación del 8 oct», con los totales del lote y los enlaces a las otras partes
  resumen por categoría (renglones y unidades; valor en pesos por categoría solo con `reportes.valor_inventario`)
  renglones paginados de 50 en 50, con búsqueda (BT-06)
  relacionados: recepciones de un traspaso, el traspaso de una recepción, la cancelación, la solicitud de compra ligada
«Descargar PDF» -> «Armando el PDF…» -> `KEP-ENT-000123.pdf` (BT-07, BT-09)
«Descargar PDF del lote» -> un solo PDF: hoja de resumen del lote y los renglones de cada vale (BT-08)
```

- **Decisiones:** el PDF lleva lo mismo que el vale impreso (E-24), con la firma o «Firmado con la sesión de <responsable>», y **nunca** costos ni valor en pesos, aunque quien lo descarga tenga el permiso (F-12, RG-12), ni CURP, NSS o foto. Se arma en el navegador, también en la app de Android sin conexión; un lote grande avanza por tramos y se puede cancelar (BT-09). Un vale cancelado sale con marca de agua «CANCELADO». Un relacionado fuera del alcance se nombra sin folio ni enlace («Recibido en otro almacén el 8 oct»; BT-06). Los vales no se editan ni se borran desde aquí.
- **Éxito:** una importación de 800 filas es **un** renglón; desde el vale se llega a cada pieza y a su línea de tiempo (SG-03, D-16).
- **Error:** «No hay vales con esos filtros» con «Quitar filtros»; vale fuera del alcance, «No encontramos este vale. Puede que no sea de tu almacén o que ya no exista» (404); PDF que falla, «No se pudo armar el PDF. Revisa la conexión y vuelve a intentar» con «Reintentar» (nunca un PDF a medias); 403 sin permiso.

## Flujo 27: Deudores (supervisor, RH y administrador)

Parte de [FEAT-018](../features/FEAT-018-deudores-resguardo-y-alto-valor.md) (DU-01 a DU-09, AV-01 a AV-05). Primero computadora (D-20).

- **Entrada:** Menú → Supervisión → Deudores (`/deudores`); `/reportes/adeudos` redirige aquí (DU-09); desde la ficha de una pieza en resguardo, «Ver lo que debe».
- **Precondiciones:** `deudores.ver` (de inicio Supervisor, RH y Administrador). Alcance (DU-03): con `almacenes.todos`, todos los almacenes; el supervisor, lo que se le debe a los almacenes de su conjunto; RH (con `trabajadores.administrar`), todos los trabajadores y todas sus deudas, sin acceso a existencias, vales ni Seguimiento.
- **Pasos:**

```
Pestaña «Por trabajador»: cuatro tarjetas que filtran al tocarlas
  «Trabajadores con adeudo» | «Alto valor fuera» | «No vigentes con adeudo» | «Deben desde hace más de 30 días»
  un renglón por trabajador con deuda: nombre, número y foto, proyecto(s), vigencia, cuánto debe, desde cuándo, alto valor y aviso (DU-04)
  -> primero los no vigentes con alto valor, luego la deuda más antigua
  -> no vigente: banda amarilla «Contrato terminado el 30/09/2026. Hay que recuperar lo que tiene o renovar su contrato» (SG-06)
  -> debe también a otros almacenes: «Tiene además 3 artículos de otros almacenes», sin detalle (DU-03)
Abrir un trabajador -> hoja lateral (página completa en celular) con dos pestañas
  «Lo que tiene»: artículo, pieza y serie, cantidad, desde, folio de la entrega, proyecto, almacén al que se le debe e insignia «Alto valor» (DU-05)
  «Consumo»: lo consumido por artículo en su contrato, separado por proyecto (DU-08)
  -> «Ver ficha del trabajador» | «Recibir devolución» (con `devoluciones.crear` en ese almacén; abre Devolver con el trabajador ya identificado)
Filtros: almacén (si ve más de uno), proyecto (con «Sin proyecto»), categoría (con «Alto valor» primero), vigencia y antigüedad;
  búsqueda por nombre, número, credencial, artículo, código o serie con espera de 300 ms (DU-06)
Pestaña «Resumen»: por almacén y por proyecto, trabajadores con adeudo, piezas, unidades, alto valor fuera y no vigentes (DU-07)
«Descargar CSV» en cada pestaña
```

- **Decisiones:** deber es tener en resguardo algo **retornable**; los consumibles, lo que va en tránsito y lo que está en baja no cuentan (DU-01, B-03). La deuda es con el almacén de la entrega más reciente; el consumo, con el proyecto (DU-02, T-3 del maestro). Alto valor: categoría marcada o costo de 10,000 o más, y gana sobre eléctrica (AV-02, AV-03, D-12). La insignia «Alto valor» no revela el costo (AV-05). Solo lee.
- **Éxito:** el supervisor sabe quién le debe a su almacén, qué, desde cuándo y para qué proyecto, con el alto valor a la vista (D-17).
- **Error:** un filtro fuera del alcance no devuelve nada y no es error; sin `deudores.ver`, 403 y «Tu rol no puede hacer esto»; error de carga con «Reintentar».

## Flujo 28: Inspecciones (almacenista y supervisor)

Parte de [FEAT-016](../features/FEAT-016-inspecciones-y-alertas-de-vigencia.md) (P-11 a P-13, P-15). Primero celular (D-20). Inspeccionar una pieza o un lote es el Flujo 13.

- **Entrada:** Menú → Inspecciones (`/inspecciones`), con el contador de pendientes; o la tarjeta «Inspecciones» del Inicio, que abre la pestaña más urgente con piezas; o, en la app de Android, la notificación local del día (P-15).
- **Precondiciones:** `inspecciones.ver` (de inicio Almacenista, Supervisor y Administrador). Quien tiene `piezas.inspeccionar` sin `inspecciones.ver` no ve la lista, pero inspecciona desde el escaneo o la ficha.
- **Pasos:**

```
Tres pestañas, la más urgente primero (P-11):
  «Vencidas» (aptas con la inspección vencida) | «Por vencer» (vencen entre hoy y el aviso resuelto, hoy incluido) | «Sin inspección»
  cada pieza: artículo, código, serie (o «Serie pendiente»), dónde está, fecha de vigencia y días en palabras
  («Vence hoy», «Vence en 3 días», «Venció hace 5 días»)
  -> las No aptas y en mantenimiento no entran en pestañas: se cuentan y enlazan a Seguimiento
  -> «1 pieza No apta está con un trabajador» se anuncia arriba
Acción según dónde está la pieza (P-12):
  en su almacén -> «Inspeccionar» -> Flujo 13 con la pieza cargada; al volver, ya no sale en la lista
  con un trabajador -> «Pedir que la devuelva»: nombre, número, puesto, desde cuándo y folio, «Pídele que la devuelva para inspeccionarla»
                        y atajo a Devolver; no manda mensajes ni guarda nada
  en tránsito -> sin botón, «Inspecciónala cuando la reciban»
  en otro almacén del conjunto -> «Cambiar a HYL e inspeccionar» (AC-39)
Filtros: almacén (si ve más de uno), categoría, texto (código, serie o artículo) y «En el almacén» o «Con trabajadores»
```

- **Decisiones:** los días de aviso son los del artículo, si no los de su categoría, si no el general (P-10). Una pieza vencida con un trabajador sale en Vencidas con quién la tiene (P-04 cambiada); su devolución nunca se bloquea (SM-05). No hay notificación push por vencimiento ni tarea programada en el servidor: el aviso se ve en pantalla y, en la app de Android, como notificación local (P-15). Solo lee.
- **Éxito:** el almacenista sabe cada día qué equipo de alturas inspeccionar y dónde está.
- **Error:** lista vacía por pestaña con su mensaje; error de carga con «Reintentar»; sin `inspecciones.ver`, 403.

## Flujo 29: Cambiar de almacén activo (usuario con dos o más almacenes)

Parte de FEAT-013 (AC-36 a AC-40). Es un caso especial (D-01): con un solo almacén en el conjunto, nada de esto aparece.

- **Entrada:** el selector de la barra superior «Operando en: Midrex ▾».
- **Precondiciones:** dos o más almacenes en su conjunto, asignados por el Administrador (`/usuarios`) o por un supervisor con sus propios almacenes (`/personal`; AC-41). Quien tiene `almacenes.todos` no tiene conjunto: elige almacén en cada operación.
- **Pasos:**

```
Toca «Operando en: Midrex ▾» -> lista de los almacenes de su conjunto que están activos
Elige HYL -> desde la siguiente petición opera en HYL, en todos sus dispositivos (es del usuario, no del dispositivo) (AC-39)
  -> la pantalla de operación se recarga
  -> si había un borrador en Midrex: «Tienes una entrega sin terminar en Midrex. Regresa a Midrex para terminarla.»
```

- **Decisiones:** las **lecturas** (Inicio, reportes, bitácora, Seguimiento, Deudores, autorizaciones pendientes, inspecciones, traspasos por recibir) abarcan todo el conjunto (AC-37); las **escrituras** (entregas, devoluciones, envío y recepción de traspasos, no adeudo, inspecciones, estado de piezas, solicitudes de compra) se hacen en el almacén activo (AC-38). Resolver una autorización no cambia el almacén activo (AC-40). Los selectores «Viendo: …» del Inicio no cambian el almacén activo (TB-07).
- **Éxito:** el cambio queda en el registro de cambios con el almacén anterior y el nuevo.
- **Error:** 403 `ALMACEN_NO_ASIGNADO` (un almacén fuera del conjunto); 409 `ALMACEN_CERRADO`; un vale capturado en el almacén anterior se rechaza al confirmar con 409 `ALMACEN_CAMBIO` y su borrador se conserva, con la opción de volver al almacén anterior (AC-39, AC-13).

## Flujo 30: Autonomía de despacho (Administrador)

Parte de FEAT-014 (DE-07, DE-14, DE-16; D-07). Primero computadora.

- **Entrada:** Almacenes (`/almacenes`), ficha del almacén → «El EPP pide aprobación del supervisor»; o Usuarios (`/usuarios`), ficha del usuario → «Despacha EPP sin aprobación» (solo para quien puede entregar).
- **Precondiciones:** `despacho.autonomia`, que de inicio solo tiene el Administrador (D-07). Por omisión, todo almacén pide aprobación y ningún almacenista tiene la excepción.
- **Pasos:**

```
Ficha del almacén -> apaga «El EPP pide aprobación del supervisor» -> escribe el motivo -> guardar
  o
Ficha del usuario -> prende «Despacha EPP sin aprobación» -> escribe el motivo -> guardar
-> la ficha muestra el valor nuevo; los supervisores ven la etiqueta «Despacho de EPP sin aprobación» en el almacén
-> aplica desde la siguiente evaluación de cada almacenista
```

- **Decisiones:** basta con que uno de los dos interruptores dé autonomía (caso límite 8 de FEAT-014). Un borrador que esperaba aprobación sigue esperando, pero se puede confirmar sin ella si se prendió la autonomía; si se apagó, la confirmación responde 409 `REQUIERE_APROBACION_DESPACHO` y el borrador se conserva para enviarlo (DE-16). Los renglones de EPP despachados con autonomía guardan la regla DE-14 en el movimiento. El almacenista nunca despacha EPP sin aprobación por su cuenta (DE-10).
- **Éxito:** queda la auditoría `almacen.autonomia` o `usuario.autonomia` con quién, cuándo, valor anterior, valor nuevo y motivo. Si el valor no cambió, no se registra nada.
- **Error:** 422 sin motivo; 404 si el almacén o el usuario no existen; 403 sin `despacho.autonomia`.

## Flujo 31: App de Android, inscribir el equipo (almacenista)

Parte de [FEAT-020](../features/FEAT-020-app-android-sin-conexion.md) (OF-01 a OF-04). La app de Android es la **misma interfaz** de `frontend/` empaquetada con Capacitor ([ADR-014](../architecture/decisions/ADR-014-app-android-con-capacitor.md)); en línea se comporta igual que la web (OF-01). Va al final del orden de construcción.

- **Entrada:** en la app, con señal, el aviso «Preparar este equipo para trabajar sin señal» (también en el menú de la app).
- **Precondiciones:** con señal y sesión normal (usuario y contraseña); `sincronizacion.operar` (de inicio, el Almacenista); su almacén activo no está cerrado. La versión de la app no es menor que `APP_VERSION_MINIMA` (si lo es, 426 «Hay una versión nueva de la app»; OF-02). El equipo tiene un WebView equivalente a Chrome 111 o superior.
- **Pasos:**

```
Escribir el nombre del equipo («Zebra 2 Midrex») -> «Preparar»
  -> el servidor inscribe el equipo en el almacén activo de quien lo inscribe y le da un secreto, que la app guarda cifrado (OF-03)
  -> la app crea la base local cifrada, pide crear el PIN local (Flujo 32) y descarga el primer paquete con fotos
  -> «Equipo listo: Midrex. Datos de hace 0 min»
```

- **Decisiones:** un equipo pertenece a **un** almacén; un almacén puede tener varios equipos. Para usarlo en otro almacén se revoca y se inscribe de nuevo, después de subir su cola (OF-03). Un equipo no inscrito solo opera en línea. Kepler no se habilita sin conexión en la primera versión (decisión abierta 6 de FEAT-020).
- **Éxito:** el equipo aparece en «Equipos» del supervisor (Flujo 35) y queda la auditoría `dispositivo.inscribir`.
- **Error:** sin señal, «Necesitas señal para preparar este equipo»; sin el permiso, el aviso no aparece; almacén cerrado (AL-04).

## Flujo 32: App de Android, entrar sin conexión

Parte de FEAT-020 (OF-05 a OF-07).

- **Entrada:** la pantalla «Entrar» de la app cuando no hay señal.
- **Precondiciones:** el equipo está inscrito y el usuario **ya entró con señal en ese equipo** al menos una vez y creó su PIN local (OF-06); su credencial local no ha caducado.
- **Pasos:**

```
Primera vez de cada usuario, con señal: entra con usuario y contraseña
  -> «Crea un PIN de 6 dígitos para entrar a este equipo cuando no haya señal» (dos veces; rechaza 123456, 000000 y parecidos)
  -> el PIN se guarda solo en el equipo; nunca viaja al servidor (OF-06)
Sin señal: la pantalla muestra solo a los usuarios con credencial local en ese equipo (nombre y usuario)
  -> elige su nombre -> PIN local -> entra a su almacén con «Sin conexión · datos de hace 2 h»
Cambio de turno: «Salir» cierra la sesión local; la cola se queda y es del equipo
  -> sin señal se borran las cookies del usuario anterior; nadie opera en línea con la sesión de otro (OF-07)
```

- **Decisiones:** un usuario nuevo o uno que nunca entró en ese equipo no puede entrar sin señal. La credencial local caduca a los 30 días sin entrar con señal en el equipo, o cuando el paquete dice que el usuario está inactivo, perdió `sincronizacion.operar` o cambió de almacén. Revocar el equipo, inactivar al usuario, «cerrar todas» o restablecer su contraseña o PIN borran su credencial en la siguiente conexión, después de subir la cola (OF-05). Nunca se descargan contraseñas ni PIN de supervisor: sin conexión no hay autorización con PIN en el mostrador.
- **Éxito:** cada vale capturado queda a nombre de quien entró (OF-24).
- **Error:** PIN incorrecto: cinco fallos bloquean esa credencial 5 minutos; diez seguidos la borran y hay que entrar otra vez con señal (OF-07).

## Flujo 33: App de Android, operar sin conexión (almacenista)

Parte de FEAT-020 (OF-08 a OF-16). La operación sin conexión es la **excepción**: el almacenista opera en línea casi siempre.

- **Entrada:** se cae la señal en el mostrador (el indicador cambia a «Sin conexión · datos de hace 40 min») o el almacenista entra sin señal (Flujo 32).
- **Precondiciones:** equipo inscrito; datos descargados hace menos de `SINCRONIZACION_HORAS_MAXIMAS` (24 h), medidas con el reloj del equipo que no se puede atrasar (OF-15); el trabajador está en el paquete (asignado a un proyecto del almacén o de sus almacenes hijos, o con pendientes con él; OF-13).
- **Pasos:**

```
Detección: la primera petición que falla por red -> «Sin conexión»; vuelve a «En línea» tras dos respuestas buenas (OF-08)
  -> el vale en captura no se pierde: se vuelve a evaluar con el evaluador local, «Sin señal: revisado con los datos de hace 40 min»
Se puede, por la cola «Por sincronizar» (OF-09):
  entrega de herramienta, y de EPP solo con autonomía, en verde o amarillo -> firma -> «Confirmar» -> comprobante con QR y «Folio pendiente»
  devolución (una pieza fuera del paquete entra «Por verificar», con observación; OF-12)
  recepción de los traspasos que vinieron en el paquete
  inspección y marcar No apta
  solicitud de compra urgente (se encola)
EPP sin autonomía o cualquier naranja -> «Necesita aprobación del supervisor: espera señal» (OF-10)
  -> «Entregar lo demás ahora» | «Guardar para cuando haya señal» (borrador «Espera señal para aprobación»; no hay vale ni firma)
  -> al volver la señal: «Hay 1 entrega esperando aprobación» -> se reevalúa en línea y sigue el Flujo 6
Confirmación en línea que salió sin respuesta -> el mismo vale (mismo `id_cliente`) pasa a la cola como «Confirmación sin respuesta» (OF-11)
No se puede: enviar traspasos, cancelar, no adeudo, altas, entradas, ajustar vigencia, registrar serie, mantenimiento,
  pedir o resolver autorizaciones, ni atender a un trabajador fuera del paquete -> «Necesitas señal para …» (OF-12)
```

- **Decisiones:** el semáforo lo calcula un evaluador local con las mismas reglas, IDs y textos que el servidor, con los datos del paquete más lo hecho sin conexión (OF-16). Una operación de la cola **no se edita ni se borra**: se corrige después de subir, con una cancelación (OF-09). El comprobante se da solo después de guardar la operación en la base local (OF-27).
- **Éxito:** el trabajador se lleva su equipo y un comprobante con «Folio pendiente»; su QR abre `/v/:token`, que dice «Pendiente de sincronizar» hasta que el vale llega al servidor (OF-27).
- **Error:** datos de más de 24 h: solo se consulta, «Tus datos tienen más de 24 horas. Busca señal para seguir operando» (un vale ya en captura se puede terminar); reloj del equipo antes de la última hora del servidor vista: se bloquea hasta sincronizar (OF-15); trabajador fuera del paquete: «Este trabajador no está en los datos de tu almacén. Necesitas señal para entregarle»; sin espacio en el equipo: no hay comprobante.

## Flujo 34: App de Android, sincronizar

Parte de FEAT-020 (OF-14, OF-17 a OF-24).

- **Entrada:** vuelve la señal (automático); o «Actualizar ahora» en el indicador de conexión; o al iniciar sesión o turno; o la hora de descarga del almacén (`almacen.hora_descarga`, aproximada).
- **Precondiciones:** señal y una sesión en línea de un usuario registrado en el equipo (si el usuario local cambió sin señal, la app pide su contraseña; mientras, la cola puede subir con la sesión de otro usuario registrado; OF-24). Equipo inscrito y no revocado.
- **Pasos:**

```
Primero sube la cola, en orden de captura, en lotes de hasta 20 operaciones (o unos 2 MB), un lote a la vez (OF-23)
  -> indicador «Sincronizando 3 de 12»
  -> el servidor revalida cada operación con su fecha, en su propia transacción, y la clasifica (OF-17, OF-18):
       GUARDADO -> la cola muestra el folio («Guardado · MID-ENT-000245»); se puede reimprimir el comprobante con folio
       GUARDADO_CON_AVISOS -> se guardó, pero alguna regla de política ya no se cumple (límite, vigencia, autonomía apagada,
                              proyecto cerrado…); entra a la lista de revisión; nadie la autoriza después del hecho (OF-21)
       CONFLICTO -> «En revisión del supervisor» (Flujo 35); las operaciones que dependen de ella también (OF-18, OF-22)
  -> sin red o error del servidor: reintenta el mismo lote con espera creciente; nunca se duplica (OF-23)
Luego descarga el paquete si tiene más de 30 minutos (siempre con «Actualizar ahora») -> «Datos de hace 0 min» (OF-14)
  -> si quedan operaciones sin subir, sus ajustes locales se reaplican sobre el paquete nuevo
Notificación local si algo quedó en revisión: «2 vales quedaron en revisión del supervisor» (OF-29)
```

- **Decisiones:** `creado_en` es la hora del servidor al sincronizar; la hora del equipo se guarda aparte en `capturado_en` y se muestra junto («Capturado sin conexión el 08/10 14:02»); si difieren más de 10 minutos, «Hora del equipo dudosa» (OF-19). El folio se asigna al sincronizar y sigue consecutivo (RG-06). El responsable es quien capturó, aunque suba otro (OF-24). La operación se guarda en el almacén del equipo aunque el usuario ya tenga otro almacén activo (OF-22). Si dos equipos registraron la misma pieza, gana el primero que sincroniza (OF-20).
- **Éxito:** la cola queda vacía o solo con lo que está en revisión; el Inicio del supervisor ya no cuenta al equipo como «sin contacto» (OF-30).
- **Error:** 426 `APP_DESACTUALIZADA` (la subida de lotes se acepta igual, para que la cola nunca quede atrapada; OF-02); 403 `DISPOSITIVO_REVOCADO`: cada operación va a conflicto y la app borra su base local (OF-24); 401: renovar o pedir contraseña, la cola espera; lote demasiado grande: se parte a la mitad.

## Flujo 35: Conflictos de sincronización y equipos (supervisor)

Parte de FEAT-020 (OF-04, OF-20, OF-22, OF-25, OF-30). Primero computadora (D-20); también se ve en el celular.

- **Entrada:** Menú → Supervisión → Conflictos de sincronización, o Equipos; o las tarjetas del Inicio «Conflictos de sincronización: n» y «Equipos sin contacto: n» (OF-30).
- **Precondiciones:** `sincronizacion.administrar` (de inicio, el Supervisor), de los equipos de sus almacenes. Quien capturó la operación no resuelve su propio conflicto (como A-05).
- **Pasos:**

```
Conflictos: lista con equipo, quién capturó, hora del equipo y de llegada, tipo, trabajador, motivo en español llano y estado
Abrir uno -> el vale capturado completo (renglones, firma, observación), la evaluación local con la edad de sus datos,
  lo que dijo el servidor por renglón y qué otro vale chocó
  («La pieza ALT-003 ya estaba con Pedro Ruiz por MID-ENT-000245, capturado en Zebra 1 a las 20:40»)
Resolver, con motivo obligatorio (OF-25):
  «Reintentar» (ya se arregló la causa) | «Guardar sin los renglones en conflicto» |
  «Guardar como diferencia» (donde ya existe la regla, como X-13) | «Descartar» (no guarda nada)
Equipos: nombre, quién lo inscribió, usuarios registrados, versión, última descarga, última subida y estado
  («En uso», «Sin contacto hace 30 h», «Revocado») (OF-04)
  -> «Revocar» con motivo y, opcional, «Cerrar también las sesiones de sus usuarios» (equipo perdido)
```

- **Decisiones:** nunca se edita un vale guardado (RG-02): resolver crea, si aplica, un vale **nuevo** por `movimientos`, que vuelve a evaluar como siempre. Un conflicto resuelto no se reabre.
- **Éxito:** el conflicto queda RESUELTO o DESCARTADO con quién, cómo, cuándo y por qué, y en la auditoría (`sincronizacion.resolver_conflicto`). Un descartado hace que el QR del comprobante diga «Este vale no se guardó» con el motivo (OF-27). Un equipo revocado borra su base local en su siguiente conexión (OF-05).
- **Error:** el servidor no deja resolver a quien capturó la operación ni a quien no tiene ese almacén; falta el motivo, 422. El código de error exacto y qué pasa si «Reintentar» vuelve a chocar se fijan en api-contracts al construirse.

## Estados transversales

| Estado | Comportamiento |
|---|---|
| No autenticado | Lleva a Entrar y, al entrar, regresa a la ruta pedida. |
| Sin permisos | Pantalla "Tu rol no puede hacer esto", con regreso al inicio. |
| Carga | Las listas muestran un esqueleto; los botones de acción se deshabilitan con indicador. |
| Vacío | Mensaje y acción sugerida ("No hay traspasos por recibir"). |
| Error | Mensaje en lenguaje llano y botón Reintentar. |
| Sin conexión | Banda "Sin conexión". El borrador del vale se conserva en el dispositivo; nada se da por guardado hasta que el servidor responde. **Iteración 01:** en la app de Android con el equipo inscrito, el indicador de conexión de la barra superior dice «Sin conexión · datos de hace 2 h» y se sigue operando por la cola dentro de los límites del Flujo 33; en la web y en un equipo no inscrito, todo sigue como hoy. |
| En espera de aprobación (iteración 01) | Una entrega con EPP enviada a aprobación muestra la espera con su reloj y pasa a «En espera (n)» si el almacenista atiende a otro (Flujo 6, DE-15). |

## Pantallas del MVP

Con FEAT-011 las rutas no cambian, pero varias pantallas comparten la barra de pestañas de su sección del menú (ver «Navegación global»); `/mis-movimientos` ya no está en el menú.

La columna **Clase** dice dónde se diseña y se prueba primero cada pantalla (UX-08 de [FEAT-019](../features/FEAT-019-busqueda-etiquetas-y-diseno-por-dispositivo.md), D-20): **celular** para la operación diaria, **computadora** para lo administrativo. Es parte de la iteración 01 y todavía no está en el código: hoy todas las pantallas usan el mismo marco. Toda pantalla funciona en los dos dispositivos.

| Ruta | Pantalla | Roles iniciales (permiso) | Clase (UX-08) |
|---|---|---|---|
| `/entrar` | Entrar | Todos | Las dos |
| `/` | Inicio según el rol: «Lo que haces hoy» y, con `tablero.ver`, el tablero (flujo 22) | Todos; el tablero, Administrador, supervisor y almacenista | Celular para almacenista y supervisor; computadora para Administrador, Compras y RH |
| `/almacenes` | Administración de almacenes: lista, alta, edición, inactivar y reactivar (flujo 21) | Administrador (`almacenes.administrar`) | Computadora |
| `/entregar` | Entrega | Almacenista, supervisor (`entregas.crear`) | Celular |
| `/devolver` | Devolución | Almacenista, supervisor (`devoluciones.crear`) | Celular |
| `/trasladar` | Traspaso, salida, escaneando o con una lista de Excel (FEAT-009) | Supervisor, administrador (`traspasos.operar`, solo enviar) | Celular; el paso con la lista de Excel, computadora |
| `/recibir`, `/recibir/:id` | Traspasos por recibir y recepción, con búsqueda, filtros y avance para listas largas (flujo 10) | Quien tiene `traspasos.recibir`: de inicio Supervisor, Almacenista y Administrador (tabla 8.2; X-01 se corrige) | Celular |
| `/consultar` | Consulta y búsqueda | Todos | Celular |
| `/trabajadores`, `/trabajadores/nuevo` | Lista y alta | RH (`trabajadores.ver`, `trabajadores.administrar`) | Computadora |
| `/trabajadores/:id` | Ficha del trabajador | RH; ficha reducida para almacenista y supervisor | Celular (dos columnas desde 1024 px) |
| `/articulos/:id`, `/piezas/:id` | Fichas de artículo y de pieza | Almacenista, supervisor, Compras | Celular |
| `/vales/:id` | Detalle de un vale, con la opción de cancelarlo o de cancelarlo y rehacerlo | Almacenista, supervisor, Compras (`vales.ver`) | Computadora (a todo el ancho con FEAT-017); una columna en el celular |
| `/mis-movimientos` | Mis movimientos de hoy | Almacenista, supervisor, Compras | Celular |
| `/seguimiento` | «Quién tiene qué», con dos pestañas (SG-01): **Piezas** (dónde está o quién tiene cada pieza, desde cuándo y con qué vale, C-13) y **Por cantidad** (lo que cada trabajador tiene de artículos sin serie). Acepta `?vista=cantidad`, `?articulo=<id>`, `?q=`, `?alto_valor=true` y `?ubicacion=` | Administrador, supervisor y Compras (`reportes.existencias`) o quien tenga `resguardo.ver` (SG-04, el almacenista); cada quien ve solo lo que le toca (AC-06) | Computadora; tarjetas en el celular |
| `/autorizaciones` | Solicitudes pendientes | Supervisor (`autorizaciones.resolver`) | Celular |
| `/compras/nueva`, `/compras/mias` | Pedir una compra urgente y ver las solicitudes de mi almacén (todas, para el administrador) | Almacenista, supervisor (`compras.solicitar`) | Celular |
| `/personal` | Personal por almacén: asignar y mover usuarios entre almacenes | Supervisor, administrador (`almacenes.asignar_personal`) | Computadora |
| `/usuarios` | Usuarios: alta, edición, rol, almacén, activar o inactivar, restablecer contraseña y PIN | Administrador (`acceso.administrar`) | Computadora |
| `/roles`, `/roles/:id` | Roles y permisos: lista de roles y matriz de permisos de cada uno | Administrador (`acceso.administrar`) | Computadora |
| `/inventario` | Existencias | Compras, supervisor, almacenista | Computadora |
| `/entrada` (`/entradas/nueva` y `/importar` redirigen) | Dar entrada: capturar a mano o desde un Excel, siempre a Kepler | Compras | Computadora |
| `/catalogo/categorias`, `/catalogo/articulos` | Catálogo | Compras, supervisor | Computadora |
| `/puestos` | Puestos y su dotación recomendada | Compras, supervisor (`catalogo.ver`; editar, `catalogo.administrar`) | Computadora |
| `/etiquetas` | Hojas de QR (con FEAT-019, un PDF de 9, 18 o 30 por hoja) | Supervisor, Compras y RH (`etiquetas.imprimir`, tabla 8.2) | Computadora; en el celular descarga el PDF igual |
| `/compras` | Solicitudes de compra: la cola de todos los almacenes, con resumen, búsqueda, filtros y acciones rápidas (SC-03, SC-04) | Compras, administrador (`compras.atender`) | Computadora |
| `/compras/:id` | Detalle de una solicitud de compra, con su línea de tiempo y las acciones que el servidor ofrece (SC-04 a SC-08) | Compras y administrador; también quien la pidió y su supervisor (`compras.solicitar`), solo las de su almacén | Computadora; una columna en el celular |
| `/reportes/existencias`, `/reportes/movimientos`, `/reportes/adeudos`, `/reportes/consumo` | Reportes | Según la sección 8.2 de las reglas | Computadora |
| `/v/:token` | Vale abierto desde su QR | Con sesión en el MVP | Celular |

### Pantallas nuevas de la iteración 01 (sin construir)

| Ruta | Pantalla | Roles iniciales (permiso) | Clase (UX-08) | Flujo y brief |
|---|---|---|---|---|
| `/proyectos` | Proyectos: lista, alta, edición, extender, cerrar y reabrir; ficha con sus trabajadores y su uso | Ver: Almacenista, Supervisor y RH (`proyectos.ver`; RH ve todos con `proyectos.asignar`); administrar: Administrador (`proyectos.administrar`) | Computadora | Flujo 24, FEAT-013 |
| `/autorizaciones/:id` | Detalle de una solicitud (despacho, excedente o traslado): lo que abre la notificación push; Aprobar o Rechazar por renglón y cómo quedó | Supervisor (`autorizaciones.resolver` con el almacén en su conjunto); también quien la pidió, para ver cómo va | Celular | Flujos 7 y 25, FEAT-014 |
| `/bitacora` | Bitácora por vale, con lotes y PDF; pestaña «Detalle por renglón» (la de hoy). `/reportes/movimientos` redirige aquí | Quien tenga `bitacora.ver` o `reportes.movimientos` (los mismos que hoy ven la bitácora) | Computadora | Flujo 26, FEAT-017 |
| `/deudores` | Deudores por trabajador y resumen por almacén y proyecto. `/reportes/adeudos` redirige aquí | Supervisor, RH y Administrador (`deudores.ver`) | Computadora | Flujo 27, FEAT-018 |
| `/inspecciones` | Inspecciones vencidas, por vencer y sin inspección | Almacenista, Supervisor y Administrador (`inspecciones.ver`) | Celular | Flujo 28, FEAT-016 |
| Inspeccionar una pieza o un lote (ruta por definir al construir; archivo propuesto `routes/operacion/inspeccionar.tsx`) | Flujo rehecho de inspección y modo «Varias piezas» | Almacenista y Supervisor (`piezas.inspeccionar`) | Celular | Flujo 13, FEAT-016 |
| Barra superior | Selector del almacén activo «Operando en: …» | Quien tiene dos o más almacenes en su conjunto | Las dos | Flujo 29, FEAT-013 |
| Menú de usuario | «Avisos de este equipo» | Supervisor (`autorizaciones.resolver`) | Las dos | Flujos 7 y 25, FEAT-014 |
| Equipos (ruta por definir) | Equipos inscritos de sus almacenes; revocar | Supervisor (`sincronizacion.administrar`) | Computadora; también se ve en el celular | Flujo 35, FEAT-020 |
| Conflictos de sincronización (ruta por definir) | Lista y detalle de vales que no se pudieron guardar tal cual; resolver | Supervisor (`sincronizacion.administrar`) | Computadora | Flujo 35, FEAT-020 |
| Solo en la app de Android: indicador de conexión, «Por sincronizar» (la cola), «Preparar este equipo», «Crear PIN local» y «Entrar sin señal» | Operación sin conexión del almacenista | Almacenista (`sincronizacion.operar`) | Celular | Flujos 31 a 34, FEAT-020 |

Pantallas que cambian en la iteración 01: `/entregar` (proyecto y paso de aprobación), `/autorizaciones` (tipos, selección múltiple, «Activar avisos»), `/trasladar` y `/recibir` (traslado lateral), `/trabajadores/nuevo` y la ficha (proyecto), `/trabajadores` (columna y filtros de proyecto), `/almacenes` (proyectos activos, aviso PR-12, autonomía y hora de descarga), `/usuarios` y `/personal` (conjunto de almacenes y autonomía), `/` (Inicio del supervisor y del Administrador), `/vales/:id` (detalle a todo el ancho y PDF), `/etiquetas` (PDF), `/piezas/:id` (vigencia y flujo de inspección nuevo), categorías y artículos (días de aviso de inspección y marca «Alto valor»), y todos los buscadores (UX-01).

## Flujos pospuestos

- Comprobante público del vale sin sesión, ticket impreso y firma en papel ([FEAT-001](../features/FEAT-001-vale-como-prueba.md)). Con FEAT-020 importa más: el trabajador que escanea un comprobante capturado sin conexión ve «Entrar» (decisión abierta 5 de FEAT-020).
- Cierre de un almacén de tercer nivel con su reporte de cierre ([FEAT-002](../features/FEAT-002-cierre-de-almacen.md)).
- Cierre sin devolución y equipo dado por perdido.
- Lista de revisión del supervisor.
- ~~Periodo por apertura de un almacén de tercer nivel (ciclos al reactivar)~~: **lo resuelve el proyecto** de la iteración 01 (FEAT-013; maestro, sección 6). El reporte de cierre se pedirá por proyecto, con sus fechas; mientras no se construya, se pide por rango de fechas.
- Retirar una solicitud de despacho pendiente cuando el trabajador se va (decisión abierta 1 de FEAT-014): mientras no se apruebe, la solicitud vence sola.
