# App Flow — MVP

Cómo recorre cada rol el sistema: entradas, decisiones, salidas y errores. No describe apariencia (eso está en [ui-ux.md](ui-ux.md)) ni implementación. Los códigos entre paréntesis son reglas de [reglas-de-negocio.md](reglas-de-negocio.md).

## Roles

Son los cinco roles iniciales. Lo que puede cada uno sale de sus permisos (sección 8 de las reglas), y el menú muestra solo eso.

- **Almacenista**: opera su almacén asignado.
- **Supervisor**: autoriza y administra el catálogo; también puede operar un almacén, eligiéndolo.
- **Compras**: inventario, entradas, importación, catálogo y reportes.
- **RH**: trabajadores y bajas.
- **Administrador**: tiene todos los permisos, así que ve todos los menús. Tiene además sus pantallas de administración: Personal por almacén (`/personal`), Usuarios (`/usuarios`) y Roles y permisos (`/roles`, `/roles/:id`; [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md)). Solo aparecen con `acceso.administrar`.

## Navegación global

```
Entrar
  -> Almacenista   -> Inicio de almacén: Entregar | Devolver | Trasladar | Recibir (n) | Consultar
  -> Supervisor    -> Autorizaciones (n) | Personal | Operar un almacén | Catálogo | Reportes
  -> Compras       -> Inventario | Entradas | Importar | Catálogo | Etiquetas | Reportes
  -> RH            -> Trabajadores | Alta | Bajas
  -> Administrador -> todos los menús anteriores | Administración: Usuarios | Roles y permisos
```

"Consultar" y la búsqueda están disponibles para todos; cada usuario ve solo lo que permiten los permisos de su rol (AC-05).

## Flujo 1: Entrar

- **Entrada:** cualquier ruta sin sesión.
- **Pasos:** usuario y contraseña -> inicio del rol.
- **Decisiones:** credenciales válidas; usuario activo.
- **Éxito:** inicio del rol, o la ruta que se intentó abrir.
- **Error:** "Usuario o contraseña incorrectos", sin decir cuál; tras cinco intentos, espera de cinco minutos.
- **Salida:** "Salir" cierra la sesión y regresa a Entrar.

## Flujo 2: Alta y reingreso de trabajador (RH)

- **Entrada:** Trabajadores -> Alta.
- **Precondiciones:** sesión de RH.
- **Pasos:**

```
Capturar número de empleado
  -> ya existe -> mostrar a la persona y sus pendientes -> Reingresar (T-02)
  -> no existe -> capturar nombre, puesto, área u obra y periodo (T-03)
Ligar credencial (T-05)
  -> escanear la credencial de la planta
  -> o generar un QR propio para imprimir
Foto, opcional (T-09): tomarla con la cámara o subir una imagen
Guardar -> con `etiquetas.imprimir` y credencial ligada: imprimir o descargar la credencial (completa o solo QR) -> ficha
       -> si no, ficha del trabajador
```

- **Decisiones:** número repetido; periodo con fin anterior al inicio; credencial ya ligada a otra persona.
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
  -> por pieza: capturar o escanear el código de cada pieza, marca y serie (I-02)
       -> requiere inspección: capturar la inspección inicial o dejarla pendiente (I-03)
Confirmar -> vale de entrada con folio
```

- **Decisiones:** artículo inactivo se rechaza (I-09); código de pieza repetido se rechaza.
- **Éxito:** existencias aumentan en el almacén elegido.
- **Error:** el renglón con problema se marca; nada se guarda hasta corregirlo (RG-09).

## Flujo 5: Importación desde Excel (Compras)

- **Entrada:** Importar.
- **Pasos:**

```
Pegar la tabla copiada de Excel, o subir el archivo
Indicar qué columna es cada dato: código, nombre, marca, categoría, cantidad, almacén, serie, costo
Vista previa: filas válidas, filas con error y artículos nuevos que se crearán
Confirmar -> un vale de entrada por almacén
```

- **Decisiones:** categoría desconocida: se elige una para esas filas; artículo por pieza: cada fila es una pieza.
- **Éxito:** catálogo y existencias cargados; resumen de lo creado.
- **Error:** las filas con error no se importan y se listan con su motivo; el resto sí.
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
  -> amarillo: se lee y no detiene (E-09 fuera de la dotación o sobre lo recomendado, E-10 talla, E-11 inspección por vencer)
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

## Flujo 9: Traspaso, salida (almacenista de origen)

- **Entrada:** Inicio -> Trasladar.
- **Pasos:**

```
Elegir almacén de destino (se sugieren las rutas habituales, X-03)
Escanear artículos -> renglones con nivel (X-02, X-04)
Confirmar -> vale de traspaso con folio y QR; estado En tránsito (X-06)
```

- **Éxito:** las existencias salen del origen y quedan En tránsito (X-01).
- **Error:** pieza que no está en este almacén, o cantidad mayor a la existencia: rojo.

## Flujo 10: Traspaso, recepción (almacenista de destino)

- **Entrada:** Inicio -> Recibir (n); o escanear el QR del traspaso.
- **Pasos:**

```
Abrir el traspaso
  -> Recibir todo
  -> o escanear renglón por renglón (X-11)
Confirmar -> vale de recepción; el traspaso queda Recibido
```

- **Decisiones:** lo que no se reciba sigue En tránsito y el traspaso queda "Recibido con diferencias" (X-13). Mientras le falte algo, el traspaso sigue en la lista de por recibir y se puede recibir otra vez hasta completarlo; entonces queda Recibido. "Recibir todo" manda todos los renglones pendientes del traspaso.
- **Éxito:** las existencias entran al destino, con origen y destino conservados (X-07).
- **Error:** el traspaso es para otro almacén (X-10); lo escaneado no pertenece a este traspaso (X-12).

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
  -> pieza -> estado, inspección, quién la tiene e historial (C-02)
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
- **Guardar:** con cambios aparece una barra con "Se agregan 2 permisos y se quitan 1" y qué cambia exactamente (también si el rol recibe o pierde `almacenes.todos` y qué le pasa a sus usuarios). "Guardar cambios" pide confirmación; el cambio aplica en la siguiente acción de cada persona (AC-10) y la sesión de quien se edita su propio rol se actualiza al instante.
- **Estado del rol:** "Inactivar rol" y "Eliminar rol" quedan deshabilitados, con la razón escrita debajo, si el rol es el Administrador, es uno de los cinco iniciales (solo la eliminación) o tiene usuarios (AC-11).
- **Sin permiso:** "Tu rol no puede hacer esto".

## Flujo 17: Personal por almacén (supervisor y administrador)

- **Entrada:** Menú -> Supervisión -> Personal (`/personal`, permiso `almacenes.asignar_personal`; AC-12, AC-13).
- **Pasos:** buscar por nombre o usuario, o filtrar por almacén o "Sin almacén" -> "Cambiar almacén" en la persona -> elegir el almacén (o "Sin almacén") -> la hoja dice en una frase qué cambiará ("Ana pasará de Kepler a Contratistas") -> Guardar -> aviso de éxito y la lista se actualiza.
- **Quiénes aparecen:** solo quienes operan un almacén (los que no tienen `almacenes.todos`). El servidor decide si el cambio procede; si lo rechaza (422), la hoja muestra su mensaje junto a la lista desplegable.
- **Efecto:** aplica en cuanto la persona vuelve a usar el sistema; no toca vales ni movimientos ya hechos.
- **Vacío:** "No hay personal con ese filtro". Sin el permiso, "Tu rol no puede hacer esto".

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
| `/` | Inicio según el rol | Todos |
| `/entregar` | Entrega | Almacenista, supervisor |
| `/devolver` | Devolución | Almacenista, supervisor |
| `/trasladar` | Traspaso, salida | Almacenista, supervisor |
| `/recibir`, `/recibir/:id` | Traspasos por recibir y recepción | Almacenista, supervisor |
| `/consultar` | Consulta y búsqueda | Todos |
| `/trabajadores`, `/trabajadores/nuevo`, `/trabajadores/:id` | Lista, alta y ficha | RH; ficha reducida para almacenista y supervisor |
| `/articulos/:id`, `/piezas/:id` | Fichas de artículo y de pieza | Almacenista, supervisor, Compras |
| `/vales/:id` | Detalle de un vale, con la opción de cancelarlo o de cancelarlo y rehacerlo | Almacenista, supervisor, Compras |
| `/mis-movimientos` | Mis movimientos de hoy | Almacenista, supervisor, Compras |
| `/seguimiento` | Seguimiento de piezas: todas las piezas de un artículo, dónde está o quién tiene cada una, desde cuándo y con qué vale (C-13). Acepta `?articulo=<id>` y `?q=` | Administrador, supervisor y Compras (`reportes.existencias`); cada quien ve solo lo que le toca (AC-06) |
| `/autorizaciones` | Solicitudes pendientes | Supervisor |
| `/personal` | Personal por almacén: asignar y mover usuarios entre almacenes | Supervisor, administrador (`almacenes.asignar_personal`) |
| `/usuarios` | Usuarios: alta, edición, rol, almacén, activar o inactivar, restablecer contraseña y PIN | Administrador (`acceso.administrar`) |
| `/roles`, `/roles/:id` | Roles y permisos: lista de roles y matriz de permisos de cada uno | Administrador (`acceso.administrar`) |
| `/inventario` | Existencias | Compras, supervisor, almacenista |
| `/entradas/nueva`, `/importar` | Entrada e importación | Compras |
| `/catalogo/categorias`, `/catalogo/articulos` | Catálogo | Compras, supervisor |
| `/puestos` | Puestos y su dotación recomendada | Compras, supervisor (`catalogo.ver`; editar, `catalogo.administrar`) |
| `/etiquetas` | Hojas de QR | Compras, RH |
| `/reportes/existencias`, `/reportes/movimientos`, `/reportes/adeudos`, `/reportes/consumo` | Reportes | Según la sección 8.2 de las reglas |
| `/v/:token` | Vale abierto desde su QR | Con sesión en el MVP |

## Flujos pospuestos

- Comprobante público del vale sin sesión, ticket impreso y firma en papel ([FEAT-001](../features/FEAT-001-vale-como-prueba.md)).
- Cierre de almacén de proyecto ([FEAT-002](../features/FEAT-002-cierre-de-almacen.md)).
- Cierre sin devolución y equipo dado por perdido.
- Lista de revisión del supervisor.
- Solicitud de compra.
- Tablero general por almacén.
