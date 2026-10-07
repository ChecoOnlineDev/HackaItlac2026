# App Flow — MVP

Cómo recorre cada rol el sistema: entradas, decisiones, salidas y errores. No describe apariencia (eso está en [ui-ux.md](ui-ux.md)) ni implementación. Los códigos entre paréntesis son reglas de [reglas-de-negocio.md](reglas-de-negocio.md).

## Roles

Son los cinco roles iniciales. Lo que puede cada uno sale de sus permisos (sección 8 de las reglas), y el menú muestra solo eso.

- **Almacenista**: opera su almacén asignado.
- **Supervisor**: autoriza y administra el catálogo; también puede operar un almacén, eligiéndolo.
- **Compras**: inventario, entradas, importación, catálogo, reportes y la cola de solicitudes de compra urgente de todos los almacenes.
- **RH**: trabajadores y bajas.
- **Administrador**: tiene todos los permisos, así que ve todos los menús. Tiene además sus pantallas de administración: Almacenes (`/almacenes`; [FEAT-008](../features/FEAT-008-administracion-de-almacenes-y-tablero.md)), Usuarios (`/usuarios`) y Roles y permisos (`/roles`, `/roles/:id`; [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md)). Solo aparecen con `almacenes.administrar` y `acceso.administrar`.

## Navegación global

El Inicio es el **tablero** para quien tiene `tablero.ver`, con los botones de operación **arriba** («Lo que haces hoy», FEAT-008). El menú se arma por permisos y se agrupa por tarea ([ui-ux.md](ui-ux.md), «Grupo de menú plegable»).

```
Entrar
  -> Almacenista   -> Inicio: Lo que haces hoy (Entregar | Devolver | Consultar) + tablero de su almacén
  -> Supervisor    -> Inicio: Lo que haces hoy (Entregar | Devolver | Trasladar | Recibir (n) | Autorizaciones (n) | Consultar) + tablero de su almacén
  -> Compras       -> Inicio: Solicitudes de compra (n) | Entradas pendientes (sin tablero)
  -> RH            -> Inicio: Trabajadores | Altas recientes (sin tablero)
  -> Administrador -> Inicio: Lo que haces hoy + tablero de todos los almacenes con selector
```

Menú (un grupo plegable por tarea; cada entrada aparece solo con su permiso y un grupo sin entradas visibles no se pinta; el grupo de la sección actual va abierto):

| Grupo | Entradas |
|---|---|
| **Inicio** | Resumen |
| **Operación** | Entregar · Devolver · Trasladar · Recibir traspaso · Pedir compra urgente · Mis compras urgentes |
| **Consulta** | Consultar · Mis movimientos de hoy |
| **Personas** | Trabajadores · Alta de trabajador · Personal del almacén |
| **Inventario** | Inventario · Entradas de proveedor · Importar inventario · Categorías · Artículos · Puestos · Etiquetas |
| **Compras** | Solicitudes de compra |
| **Supervisión** | Autorizaciones · Seguimiento de piezas |
| **Reportes** | Existencias · Movimientos · Adeudos · Consumo |
| **Administración** | Almacenes · Usuarios · Roles y permisos |

Los nombres nuevos (decididos en FEAT-008): «Entrada de proveedor» (antes Entradas), «Recibir traspaso» (antes Recibir), «Mis compras urgentes» (antes Compras urgentes) e «Importar inventario» (antes Importar). Las rutas no cambian. Ocultar un módulo a un rol se hace quitándole el permiso en Roles y permisos; las entradas que comparten un permiso (por ejemplo Categorías, Artículos y Puestos, `catalogo.administrar`) se ocultan juntas.

"Consultar" y la búsqueda están disponibles para todos; cada usuario ve solo lo que permiten los permisos de su rol (AC-05).

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

- **Entrada:** Entradas -> Nueva.
- **Pasos:**

```
Elegir almacén (Kepler por defecto)
Agregar renglones (escanear o buscar artículo)
  -> por cantidad: capturar cantidad
  -> por pieza: capturar o escanear el código de cada pieza, marca y serie (I-02); la serie puede quedar pendiente (E-xx)
       -> requiere inspección: capturar la inspección inicial o dejarla pendiente (I-03)
Confirmar -> vale de entrada con folio
```

- **Decisiones:** artículo inactivo se rechaza (I-09); código de pieza repetido se rechaza.
- **Éxito:** existencias aumentan en el almacén elegido.
- **Error:** el renglón con problema se marca; nada se guarda hasta corregirlo (RG-09).

## Flujo 5: Importación desde Excel (Compras)

- **Entrada:** Importar.
- **Precondiciones:** `inventario.entradas`. El alta que crea artículos pide además `catalogo.administrar` (I-10).
- **Pasos:**

```
Elegir el modo: Alta (carga inicial: crea artículos nuevos y suma a los que ya existen)
                o Reposición (solo suma a artículos que ya existen)
   -> "Descargar plantilla" ofrece el ejemplo de ese modo
Pegar la tabla copiada de Excel, o subir el archivo
Indicar qué columna es cada dato
   Alta: código (opcional), nombre, marca, categoría, cantidad, unidad (opcional), almacén, serie (opcional), costo, código de pieza (opcional)
   Reposición: código, cantidad, almacén y, si es por pieza, código de pieza y serie
Vista previa en tabla: una fila por renglón del archivo, con su estado
   Nuevo | Existente (suma) | Unido | Error, saldo antes -> después,
   y en el alta la categoría sugerida, que se puede cambiar por fila
   Resumen arriba: nuevos, existentes, unidos, errores y, si los hay, «n piezas sin serie»
   Una pieza sin serie sale en amarillo con «Serie pendiente»; una sin código de pieza, con «Código provisional: se asigna al confirmar»
   Aviso si el archivo ya se importó
Confirmar -> un vale de entrada por almacén
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
Escanear artículos -> renglones con nivel (X-02, X-04)
Confirmar -> vale de traspaso con folio y QR; estado En tránsito (X-06)
```

- **Éxito:** las existencias salen del origen y quedan En tránsito (X-01).
- **Error:** pieza que no está en este almacén, o cantidad mayor a la existencia: rojo.

### Entrada alternativa: Trasladar con una lista (FEAT-009)

- **Entrada:** en Trasladar, el botón «Trasladar con una lista», junto a «Escanear». Misma precondición y mismo permiso (`traspasos.operar`); no hay permiso nuevo.
- **Pasos:**

```
Elegir almacén de destino (igual que arriba: rutas habituales; la no habitual solo con `almacenes.todos`,
  con aviso amarillo y observación obligatoria, X-03)
  -> el destino es uno solo para todo el archivo
Descargar la plantilla, o subir el archivo, o pegar la tabla copiada de Excel
Indicar qué columna es cada dato (se proponen solas por el encabezado; se pueden cambiar)
   código, cantidad y, si es por pieza, código de pieza o serie
Vista previa en tabla: una fila por renglón del archivo, con su estado
   Correcto | Aviso | Error, artículo, cantidad y lo disponible en el origen
   Resumen arriba: correctas, con aviso, con error
   Aviso si el archivo ya se usó para otro traspaso
   Banner de ruta: habitual, o no habitual con la observación obligatoria
Confirmar -> vale de traspaso con folio CLAVE-TRS y QR; estado En tránsito (X-06)
```

- **Decisiones:**
  - Cada fila pasa por la misma evaluación que un escaneo (X-02, X-04, X-09); el servidor decide el nivel y la pantalla solo lo muestra.
  - Un rojo bloquea **todo** el traspaso (RG-09). Para seguir, se corrige el archivo y se vuelve a subir, o se usa «Dejar fuera las filas con error», que pide confirmar y dice cuántas son y cuáles; las filas dejadas fuera no se envían.
  - Una fila en amarillo avisa y no detiene. Las filas del mismo artículo por cantidad se unen en una; un artículo por pieza lleva una fila por pieza.
  - Más de 500 filas: se rechaza el archivo completo con el motivo en español llano.
  - Archivo ya usado: aviso en la vista previa; para confirmar hay que aceptarlo expresamente.
  - Tocar «Confirmar» dos veces, o perder la conexión y reintentar, no duplica el vale (el dispositivo manda su `id_lote`; una repetición devuelve el mismo vale).
- **Éxito:** igual que la captura manual: las existencias salen del origen y quedan En tránsito (X-01); resultado con folio y QR.
- **Error:** destino inválido, un renglón en rojo (sin dejarlo fuera) o un archivo ilegible: no se guarda nada.
- **Cancelación:** hasta «Confirmar» no se guarda nada; el archivo no se conserva en el servidor.
- **Con escaneo:** la lista y el escaneo se pueden combinar antes de confirmar: lo que viene del archivo entra como renglones normales del borrador.

## Flujo 10: Traspaso, recepción (supervisor del almacén de destino)

- **Entrada:** Inicio -> Recibir (n); o escanear el QR del traspaso.
- **Precondiciones:** `traspasos.recibir` (distinto de `traspasos.operar`, que es solo para enviar). Quién recibe en un almacén lo define ese permiso: un supervisor, un almacenista del destino o quien el administrador decida; armar y enviar el traspaso no lo implica.
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

## Flujo 15: Reportes (según el rol)

- **Entrada:** Reportes -> Existencias | Movimientos | Adeudos | Consumo.
- **Pasos:** elegir filtros (almacén, periodo, trabajador, artículo y, en movimientos, tipo y usuario) -> tabla -> Descargar CSV.
- **Alcance:** cada usuario ve lo de su almacén, también con el filtro de usuario, que para el almacenista es solo informativo. Quien tiene `almacenes.todos` ve todos los almacenes y filtra por cualquier usuario para rastrear una desaparición (C-11).
- **Vacío:** "No hay registros con esos filtros".

## Flujo 16: Etiquetas (Compras)

- **Entrada:** Etiquetas.
- **Pasos:** elegir qué imprimir (credenciales, piezas o estantes; en credenciales, la credencial completa o solo el código QR) -> seleccionar -> hoja con QR y texto -> imprimir desde el navegador. Una credencial suelta también se imprime o se descarga como PNG desde la ficha del trabajador.

## Flujo 18: Usuarios y roles (administrador)

- **Entrada:** Menú -> Administración -> Usuarios (`/usuarios`) o Roles y permisos (`/roles`); permiso `acceso.administrar` (AC-08).
- **Usuarios:** búsqueda por nombre o usuario a la vista y filtros de rol, almacén y estado en "Filtros". "Nuevo usuario" abre una hoja (nombre, usuario, rol, almacén, contraseña y, si el rol autoriza, PIN opcional). El almacén solo se pide si el rol no tiene `almacenes.todos` (RG-07). "Editar" cambia nombre, rol y almacén; "Contraseña" abre una hoja con confirmación (se cierran las sesiones abiertas y se quitan los bloqueos); "Inactivar" o "Reactivar" piden confirmación. Nadie puede inactivarse a sí mismo desde la pantalla, y el servidor rechaza inactivar o cambiar de rol al último administrador (`ULTIMO_ADMINISTRADOR`, AC-09).
- **Roles:** tarjetas con nombre, descripción, número de usuarios y de permisos; "Nuevo rol" crea uno sin permisos y "Duplicar" copia los permisos de otro. "Ver permisos" abre `/roles/:id`: la matriz de permisos agrupada por módulo, con un interruptor por permiso, su descripción en lenguaje de persona y la clave técnica en segundo plano. Los permisos de información reservada (costos, CURP y NSS) llevan su advertencia. Activar un permiso de acción activa también los de ver que necesita. Los que no se pueden cambiar quedan deshabilitados con su razón: el Administrador siempre lleva `acceso.administrar`, nadie se lo quita a su propio rol, y no se quita un permiso de ver mientras otro lo necesita.
- **Botón por grupo (FEAT-008, 4.5):** cada grupo de la matriz trae un contador («3 de 5 activos») y un botón: «Activar todos» si está vacío o a medias, «Quitar todos» si está completo. Arriba de la matriz, opcionalmente, «Activar todo» y «Quitar todo». El botón **solo mueve los interruptores en pantalla** (no guarda): los cambios se revisan en la barra de abajo y se pueden descartar. Respeta lo que bloquea un interruptor (el permiso protegido se queda como está y el botón avisa cuántos no pudo mover y por qué) y las dependencias (activar enciende el permiso de ver que necesita; quitar un permiso de ver quita los que dependen de él). Al guardar, la confirmación nombra aparte los datos reservados que se agregan («incluye ver costos y datos personales»). La API no cambia: `PUT /api/roles/{id}/permisos` con la lista final.
- **Guardar:** con cambios aparece una barra con "Se agregan 2 permisos y se quitan 1" y qué cambia exactamente (también si el rol recibe o pierde `almacenes.todos` y qué le pasa a sus usuarios). "Guardar cambios" pide confirmación; el cambio aplica en la siguiente acción de cada persona (AC-10) y la sesión de quien se edita su propio rol se actualiza al instante.
- **Estado del rol:** "Inactivar rol" y "Eliminar rol" quedan deshabilitados, con la razón escrita debajo, si el rol es el Administrador, es uno de los cinco iniciales (solo la eliminación) o tiene usuarios (AC-11).
- **Sin permiso:** "Tu rol no puede hacer esto".

## Flujo 17: Personal por almacén (supervisor y administrador)

- **Entrada:** Menú -> Personas -> Personal del almacén (`/personal`, permiso `almacenes.asignar_personal`; AC-12, AC-13). Antes colgaba del grupo Supervisión; FEAT-008 lo pasa a Personas.
- **Pasos:** buscar por nombre o usuario, o filtrar por almacén o "Sin almacén" -> "Cambiar almacén" en la persona -> elegir el almacén (o "Sin almacén") -> la hoja dice en una frase qué cambiará ("Ana pasará de Kepler a Contratistas") -> Guardar -> aviso de éxito y la lista se actualiza.
- **Quiénes aparecen:** solo quienes operan un almacén (los que no tienen `almacenes.todos`). El servidor decide si el cambio procede; si lo rechaza (422), la hoja muestra su mensaje junto a la lista desplegable.
- **Efecto:** aplica en cuanto la persona vuelve a usar el sistema; no toca vales ni movimientos ya hechos.
- **Vacío:** "No hay personal con ese filtro". Sin el permiso, "Tu rol no puede hacer esto".

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
- **Las acciones (SC-04):** Tomar (confirmación breve; pasa a En compra). Rechazar abre una hoja con la nota obligatoria y respuestas rápidas (SC-05). Marcar como comprada abre una hoja con una nota opcional (proveedor, día de llegada). Ingresar al almacén abre una hoja donde se liga, si se quiere, el vale de ENTRADA con el que se metió lo comprado: se elige de las últimas entradas o se escribe su folio (SC-06); la hoja avisa que ingresar no suma existencias por sí solo, porque suben con el vale que se registra en Entradas (SC-11). Tras cada acción aparece un aviso breve y la pantalla se actualiza sin salir.
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
6. Al empezar un mantenimiento: Administrador -> Nuevo almacén (PROYECTO, depende de Contratistas) y su personal
7. Supervisor de Contratistas -> Trasladar al proyecto
```

- **Cierre de un proyecto:** el supervisor devuelve el sobrante por traspaso a Contratistas, registra faltantes y revisa el reporte de cierre ([FEAT-002](../features/FEAT-002-cierre-de-almacen.md)); el Administrador reasigna a su personal y lo inactiva. La puesta en marcha y el cierre completos, con sus reglas, están en [red-de-almacenes-y-flujo.md](red-de-almacenes-y-flujo.md).
- **Estados:** esqueleto al cargar; error con «Reintentar».

## Flujo 22: Inicio y tablero (almacenista, supervisor y administrador)

Parte de FEAT-008 (TB-01 a TB-03).

- **Entrada:** `/` con sesión. El Inicio depende de los permisos, nunca del nombre del rol.
- **Orden de la pantalla:** primero «Lo que haces hoy» (los botones de operación del rol, grandes), debajo las tarjetas y, al final, la gráfica de lo más usado.
- **Quién ve el tablero:** quien tiene `tablero.ver` (Administrador, Supervisor y Almacenista de inicio). Con `almacenes.todos` (Administrador) ve todos los almacenes y un selector «Viendo: Todos los almacenes» con la lista de almacenes; el rótulo «Viendo: Midrex» avisa que el selector solo cambia lo que se mira, no el almacén en el que se opera. Sin `almacenes.todos`, ve solo su almacén, sin selector. Compras y RH no tienen tablero: su Inicio muestra lo suyo (solicitudes por atender, trabajadores y altas recientes).
- **Tarjetas** (de `GET /api/tablero/resumen`): Existencias, Equipo importante en resguardo, Sin existencia, Traspasos en tránsito, Entregas de hoy, Solicitudes de compra abiertas, Inspecciones por vencer y Piezas con serie pendiente. Cada una dice en una línea qué cuenta. Tocar «Equipo importante en resguardo» abre `/seguimiento` con las piezas en manos de trabajadores; «Traspasos en tránsito», `/recibir`; «Solicitudes de compra abiertas», `/compras` o `/compras/mias` según el permiso. «Piezas con serie pendiente» abre `/seguimiento` con el filtro `serie_pendiente=true`. Las demás no navegan.
- **Gráfica «Lo más usado»** (de `GET /api/tablero/consumo`): filtros Almacén (solo con `almacenes.todos`), Periodo (Hoy, 7 días, Este mes, Mes pasado, Elegir fechas; por omisión Este mes) y Categoría (por omisión Consumibles de trabajo); «Limpiar filtros»; interruptor «Separar por almacén» solo con todos los almacenes. Se actualiza al cambiar cualquier filtro, con indicador de carga y sin borrar la anterior hasta que llega la nueva. Cada barra se toca y abre el artículo (`/articulos/:id`).
- **Estados:** sin consumo en el rango, «No hubo consumo en estas fechas»; error con «Reintentar»; sin almacén asignado, el aviso «No tienes un almacén asignado» y las tarjetas en cero.
- **Sin permiso:** quien no tiene `tablero.ver` no ve el tablero y `GET /api/tablero/*` responde 403.

## Estados transversales

| Estado | Comportamiento |
|---|---|
| No autenticado | Lleva a Entrar y, al entrar, regresa a la ruta pedida. |
| Sin permisos | Pantalla "Tu rol no puede hacer esto", con regreso al inicio. |
| Carga | Las listas muestran un esqueleto; los botones de acción se deshabilitan con indicador. |
| Vacío | Mensaje y acción sugerida ("No hay traspasos por recibir"). |
| Error | Mensaje en lenguaje llano y botón Reintentar. |
| Sin conexión | Banda "Sin conexión". El borrador del vale se conserva en el dispositivo; nada se da por guardado hasta que el servidor responde. |

## Pantallas del MVP

| Ruta | Pantalla | Roles iniciales |
|---|---|---|
| `/entrar` | Entrar | Todos |
| `/` | Inicio según el rol: «Lo que haces hoy» y, con `tablero.ver`, el tablero (flujo 22) | Todos; el tablero, Administrador, supervisor y almacenista |
| `/almacenes` | Administración de almacenes: lista, alta, edición, inactivar y reactivar (flujo 21) | Administrador (`almacenes.administrar`) |
| `/entregar` | Entrega | Almacenista, supervisor |
| `/devolver` | Devolución | Almacenista, supervisor |
| `/trasladar` | Traspaso, salida, escaneando o con una lista de Excel (FEAT-009) | Supervisor, administrador (`traspasos.operar`, solo enviar) |
| `/recibir`, `/recibir/:id` | Traspasos por recibir y recepción, con búsqueda, filtros y avance para listas largas (flujo 10) | Quien tiene `traspasos.recibir`: de inicio supervisor y administrador; el almacenista si se le da |
| `/consultar` | Consulta y búsqueda | Todos |
| `/trabajadores`, `/trabajadores/nuevo`, `/trabajadores/:id` | Lista, alta y ficha | RH; ficha reducida para almacenista y supervisor |
| `/articulos/:id`, `/piezas/:id` | Fichas de artículo y de pieza | Almacenista, supervisor, Compras |
| `/vales/:id` | Detalle de un vale, con la opción de cancelarlo o de cancelarlo y rehacerlo | Almacenista, supervisor, Compras |
| `/mis-movimientos` | Mis movimientos de hoy | Almacenista, supervisor, Compras |
| `/seguimiento` | Seguimiento de piezas: todas las piezas de un artículo, dónde está o quién tiene cada una, desde cuándo y con qué vale (C-13). Acepta `?articulo=<id>` y `?q=` | Administrador, supervisor y Compras (`reportes.existencias`); cada quien ve solo lo que le toca (AC-06) |
| `/autorizaciones` | Solicitudes pendientes | Supervisor |
| `/compras/nueva`, `/compras/mias` | Pedir una compra urgente y ver las solicitudes de mi almacén (todas, para el administrador) | Almacenista, supervisor (`compras.solicitar`) |
| `/personal` | Personal por almacén: asignar y mover usuarios entre almacenes | Supervisor, administrador (`almacenes.asignar_personal`) |
| `/usuarios` | Usuarios: alta, edición, rol, almacén, activar o inactivar, restablecer contraseña y PIN | Administrador (`acceso.administrar`) |
| `/roles`, `/roles/:id` | Roles y permisos: lista de roles y matriz de permisos de cada uno | Administrador (`acceso.administrar`) |
| `/inventario` | Existencias | Compras, supervisor, almacenista |
| `/entradas/nueva`, `/importar` | Entrada e importación | Compras |
| `/catalogo/categorias`, `/catalogo/articulos` | Catálogo | Compras, supervisor |
| `/puestos` | Puestos y su dotación recomendada | Compras, supervisor (`catalogo.ver`; editar, `catalogo.administrar`) |
| `/etiquetas` | Hojas de QR | Compras, RH |
| `/compras` | Solicitudes de compra: la cola de todos los almacenes, con resumen, búsqueda, filtros y acciones rápidas (SC-03, SC-04) | Compras, administrador (`compras.atender`) |
| `/compras/:id` | Detalle de una solicitud de compra, con su línea de tiempo y las acciones que el servidor ofrece (SC-04 a SC-08) | Compras y administrador; también quien la pidió y su supervisor (`compras.solicitar`), solo las de su almacén |
| `/reportes/existencias`, `/reportes/movimientos`, `/reportes/adeudos`, `/reportes/consumo` | Reportes | Según la sección 8.2 de las reglas |
| `/v/:token` | Vale abierto desde su QR | Con sesión en el MVP |

## Flujos pospuestos

- Comprobante público del vale sin sesión, ticket impreso y firma en papel ([FEAT-001](../features/FEAT-001-vale-como-prueba.md)).
- Cierre de almacén de proyecto ([FEAT-002](../features/FEAT-002-cierre-de-almacen.md)).
- Cierre sin devolución y equipo dado por perdido.
- Lista de revisión del supervisor.
- Periodo por apertura de un almacén de proyecto (ciclos al reactivar): mientras tanto el reporte de cierre se pide por rango de fechas.
