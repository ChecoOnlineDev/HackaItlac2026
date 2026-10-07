# FEAT-008: Administración de almacenes, tablero de inicio y menú reorganizado

> **Estado:** propuesta para revisión. Nada de esto está construido. Antes de escribir código hay que aprobar este brief y actualizar los documentos de la sección 12.
> **Flujo de la red de almacenes:** el recorrido de alta, surtido, entrega de EPP y cierre está en [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md); las preguntas abiertas de ese flujo pueden cambiar este brief.
> **Relación con otros briefs:** extiende a [FEAT-002](FEAT-002-cierre-de-almacen.md) (cierre de almacén y valor del inventario). Si algo de aquí se solapa con FEAT-002, manda este documento y FEAT-002 se ajusta en el mismo cambio.

## 1. Problema u oportunidad

1. **En producción no hay almacenes.** Los seis almacenes (Kepler, Contratistas, Midrex, HYL, Laminador y Minas) solo existen en el script de datos de prueba (`backend/app/modulos/almacenes/datos_prueba.py`). Ninguna migración los siembra y la API solo tiene lecturas (`GET /api/almacenes` y `GET /api/almacenes/{id}/existencias`). Sin ese script, una base nueva no tiene dónde recibir inventario, y no hay forma de crear un almacén desde la aplicación.
2. **El campo `cerrado_en` está muerto.** El modelo ya tiene los estados `ACTIVO` y `CERRADO`, pero ningún código los cambia.
3. **El Inicio es solo una cuadrícula de botones.** Nadie ve cómo está el inventario de un vistazo: ni cuántas piezas importantes están en manos de trabajadores, ni qué se consume más.
4. **El menú tiene demasiadas opciones sueltas** (27 entradas posibles según el rol) y carga de más a quien solo quiere entregar o devolver.
5. **El número de empleado lo escribe RH**, y eso invita a errores y duplicados.

## 2. Objetivo

- Que un administrador pueda **dar de alta, activar e inactivar almacenes** desde la aplicación, y que todo lo ligado a un almacén (usuarios, personal, inventario, folios, solicitudes) quede coherente.
- Que cada persona vea **un resumen gráfico de lo que le toca**: el administrador, todo el inventario con filtro por almacén; el almacenista y el supervisor, solo su almacén.
- Que el menú sea **corto y por tarea**, con Operación agrupada y plegable.
- Que el número de empleado **se genere solo**.
- Que armar un rol en **Roles y permisos** sea rápido: un botón por grupo que active o quite todos los permisos de ese bloque.

## 3. Historias de usuario

- Como **administrador**, quiero crear un almacén y decir de cuál depende, para que un proyecto nuevo pueda recibir y entregar material.
- Como **administrador**, quiero inactivar un almacén que ya no opera y volver a activarlo si hace falta, para no borrar su historial.
- Como **administrador**, quiero ver el estado general de todos los almacenes y filtrar por uno, para saber dónde están las existencias y las piezas importantes.
- Como **administrador**, quiero ver qué artículo se consumió más en un rango de fechas y en qué almacén, para decidir qué comprar.
- Como **almacenista o supervisor**, quiero ver qué tengo en mi almacén al entrar, sin ver el de los demás, para trabajar rápido.
- Como **administrador**, quiero activar o quitar de una vez todos los permisos de un grupo al armar un rol, para no mover los interruptores uno por uno.
- Como **personal de RH**, quiero dar de alta a un trabajador sin inventar su número de empleado, para no equivocarme.

## 4. Alcance incluido

### 4.1 Administración de almacenes

| Pieza | Qué hace |
|---|---|
| **Pantalla Almacenes** (`/almacenes`, grupo Administración) | Lista todos los almacenes con clave, nombre, tipo, depende de, estado y un resumen (existencias y piezas en resguardo). Solo para quien tiene `almacenes.administrar`. |
| **Alta** | Formulario: clave (única, hasta 10 caracteres, en mayúsculas), nombre, tipo (`CENTRAL`, `SUBALMACEN` o `PROYECTO`) y **de qué almacén depende** (obligatorio salvo para el central). El servidor crea el almacén **y su ubicación** en la misma transacción. |
| **Editar** | Nombre y de qué almacén depende. La clave **no se cambia** una vez que el almacén tiene folios, porque forma parte de ellos (`KEP-ENT-000123`). |
| **Inactivar** | Pasa a `CERRADO` y registra `cerrado_en`. Solo con las condiciones de la sección 4.1.2. No borra nada. |
| **Reactivar** | Vuelve a `ACTIVO` y limpia `cerrado_en`. Queda en la auditoría. **Decidido:** un proyecto que vuelve se reactiva (mismo almacén y misma clave); no se crea otro. |
| **Vínculos** | Desde la ficha del almacén se ven y se gestionan sus usuarios (ya existe `/usuarios` y `/personal`), su inventario y sus solicitudes de compra. No se duplican pantallas: se enlazan. |

#### 4.1.1 Reglas de la jerarquía (propuestas)

- Hay **un solo almacén central**. Los demás dependen de otro.
- El flujo habitual es Central → Contratistas → áreas o proyectos (Midrex, HYL, Laminador, Minas). Un destino de traspaso es "habitual" si uno es padre del otro (regla de traspasos ya existente).
- Un almacén no puede depender de sí mismo ni de uno de sus descendientes.
- La clave y el nombre son únicos entre los almacenes.

#### 4.1.2 Condiciones para inactivar

Un almacén solo se inactiva si se cumplen **las dos** condiciones de FEAT-002:

1. **Todas sus existencias están en cero.** Si queda algo, primero se regresa por traspaso al almacén del que depende.
2. **No hay traspasos en tránsito** desde ni hacia él.

Además:
- No se inactiva un almacén con **hijos activos**: primero se inactivan o se reasignan.
- Si tiene **usuarios asignados**, la pantalla avisa cuántos son. No bloquea, pero esos usuarios ya no pueden operar. Mi propuesta es **bloquear** hasta reasignarlos, porque dejar usuarios sin almacén activo les quita el acceso sin aviso. Se decide en la sección 10.
- Las piezas en resguardo de trabajadores **no impiden** inactivar (CP-05): una pieza es del almacén de su última entrega y su historial se conserva.
- Un almacén inactivo **sigue apareciendo en los reportes** y en el historial, pero no recibe ni envía movimientos.

#### 4.1.3 Qué debe hacer un almacén `CERRADO`

Hoy solo se rechaza en traspasos, en el alta de usuarios y en la importación. Este brief lo extiende a **todo lo que mueve inventario**: entregas, devoluciones, entradas, traspasos (origen y destino) y solicitudes de compra nuevas. El error es el mismo en todos: «Ese almacén está cerrado.» Las lecturas (consultas, reportes) siguen funcionando.

#### 4.1.4 Qué se crea junto con el almacén

| Cosa | Cuándo |
|---|---|
| `almacen` | En el alta. |
| `ubicacion` del almacén | En el alta, en la misma transacción (`UbicacionRepository.crear_de_almacen`). |
| `serie_folio` y `serie_solicitud_compra` | **Verificar** si se crean al primer vale (perezoso) o hay que crearlas en el alta. Si son perezosas, no se hace nada. |
| Usuarios y personal | No se crean solos: se asignan después desde `/usuarios` y `/personal`. |
| Inventario | Llega después, por entrada de proveedor o por la importación de Excel (FEAT-007), eligiendo ese almacén. |

#### 4.1.5 Primer arranque en producción

Un mecanismo para que una base nueva no quede vacía:

- **Pantalla de alta** (lo de arriba) como camino normal.
- **Opcional:** un comando `uv run python -m app.mantenimiento sembrar-almacenes` que cree los seis almacenes iniciales **solo si no existe ninguno**, para no depender de las pantallas el primer día. Es seguro de repetir. Se decide en la sección 10.

### 4.2 Tablero de inicio

El Inicio pasa a ser un **resumen** con tarjetas y gráficas. Los botones de operación no desaparecen: pasan a un bloque "Lo que haces hoy" arriba o a un lado, según el rol.

#### 4.2.1 Quién ve qué

| Rol (por permiso, nunca por nombre) | Qué ve en el Inicio |
|---|---|
| **Administrador** (`almacenes.todos`) | Resumen de **todos los almacenes** con selector para filtrar por uno. |
| **Supervisor y almacenista** | Resumen **solo de su almacén**. Sin selector y sin la vista general. |
| **Compras** | Sin tablero. Su Inicio muestra solicitudes por atender y entradas pendientes. |
| **Recursos Humanos** | Sin tablero. Su Inicio muestra trabajadores y altas recientes. |

El alcance sale de AC-06: lo decide el **servidor** con el almacén de la sesión y el permiso `almacenes.todos`. La interfaz solo muestra lo que el servidor devuelve.

#### 4.2.2 Tarjetas (indicadores)

Todas se calculan en el servidor con los datos que ya existen. Cada una dice en pocas palabras qué cuenta.

| Tarjeta | Qué cuenta |
|---|---|
| **Existencias** | Unidades totales en el almacén (o en todos), y cuántos artículos distintos. |
| **Equipo importante en resguardo** | Piezas de las categorías por pieza (alturas, eléctrica, alto valor) que están en manos de trabajadores. Al tocarla, abre Seguimiento de piezas ya filtrado. |
| **Sin existencia** | Artículos con cantidad cero. |
| **Traspasos en tránsito** | Enviados y no recibidos, de ida y de venida. |
| **Entregas de hoy** | Vales de entrega del día en la hora de México. |
| **Solicitudes de compra abiertas** | Pendientes y en compra de ese almacén. |
| **Inspecciones por vencer** | Piezas con inspección que vence en el plazo ya definido por la regla (7 días). |

Las que dependen de reglas aún no construidas (mínimos y alertas de FEAT-004, valor del inventario de FEAT-002) **no entran** en este brief.

#### 4.2.3 Gráfica principal: lo más usado

Una **gráfica de barras horizontales** con los 10 artículos más usados.

**Qué es "usado":** unidades **entregadas** en el rango. Para los consumibles es lo que sale del almacén y se consume; para las herramientas y el EPP retornable, cada entrega cuenta una vez. Se muestran **separados** por categoría para no mezclar 800 discos con 3 taladros: el filtro de categoría los distingue, y por omisión se muestran los consumibles.

**Filtros** (máximo tres, para no abrumar):

| Filtro | Valores | Por omisión |
|---|---|---|
| **Almacén** | Todos o uno. Solo el administrador lo ve. | Todos (administrador) o el suyo (los demás). |
| **Periodo** | Atajos: Hoy, 7 días, Este mes, Mes pasado, y "Elegir fechas". | Este mes |
| **Categoría** | Todas o una. | Consumibles de trabajo |

- La gráfica **se actualiza al cambiar cualquier filtro**, con un indicador de carga y sin borrar la anterior hasta que llega la nueva.
- Un botón **«Limpiar filtros»** vuelve a los valores por omisión.
- Cada barra es tocable: lleva al detalle del artículo con los mismos filtros.
- Una barra solo con texto y número visible, además del color (accesibilidad).
- Con el administrador en "Todos los almacenes", un interruptor **«Separar por almacén»** reparte cada barra por colores. Es el único control extra y es opcional.

**Estados vacíos y de error:** sin movimientos en el rango, «No hubo consumo en estas fechas». Si falla la carga, el aviso de siempre con «Reintentar».

#### 4.2.4 Gráfica secundaria (opcional en la primera entrega)

Consumo por día en el rango, como línea o barras finas, para ver picos. Se deja fuera si el tiempo no alcanza.

### 4.3 Menú reorganizado

#### 4.3.1 Estructura propuesta

Un **grupo plegable por tarea**, con el grupo de la sección actual abierto. En celular, el mismo orden dentro de la hoja del menú.

| Grupo | Entradas | Quién lo ve |
|---|---|---|
| **Inicio** (fijo) | Resumen | Administrador, supervisor, almacenista |
| **Operación** (plegable) | Entregar · Devolver · Trasladar · Recibir traspaso · Pedir compra urgente · Mis compras urgentes | Según permiso: almacenista y supervisor |
| **Consulta** | Consultar · Mis movimientos de hoy | Almacenista, supervisor y Compras |
| **Personas** | Trabajadores · Alta de trabajador · Personal del almacén | RH, supervisor, almacenista (según permiso) |
| **Inventario** | Inventario · Entradas de proveedor · Importar Excel · Categorías · Artículos · Puestos · Etiquetas | Compras, supervisor y administrador (según permiso) |
| **Compras** | Solicitudes de compra | Compras |
| **Supervisión** | Autorizaciones · Seguimiento de piezas | Supervisor y administrador |
| **Reportes** | Existencias · Movimientos · Adeudos · Consumo | Supervisor, Compras y administrador (según permiso) |
| **Administración** | Almacenes · Usuarios · Roles y permisos | Solo administrador |

**Ocultar módulos por rol se hace desde Roles y permisos** (FEAT-006, ya construido): quitar un permiso a un rol esconde las entradas del menú que lo piden. No hace falta código para ajustar quién ve qué. Límite: cuando varias entradas comparten un permiso (por ejemplo Categorías, Artículos y Puestos piden `catalogo.administrar`), se esconden o se muestran juntas; si hace falta separarlas, se divide el permiso. Consultar no pide ningún permiso y la ven todos.

Cada entrada **se muestra solo si el usuario tiene su permiso**; el menú se arma con los permisos que ya entrega la sesión (`frontend/app/sesion/menu.ts`), nunca por el nombre del rol. Un grupo sin entradas visibles no se pinta.

#### 4.3.2 Nombres más claros

| Hoy | Propuesto | Por qué |
|---|---|---|
| Entradas | **Entrada de proveedor** | Es lo que llega de una compra o un proveedor. |
| Recibir | **Recibir traspaso** | Es aceptar lo que otro almacén envió. |
| Compras urgentes | **Mis compras urgentes** | Distingue de la cola de Compras. |
| Importar | **Importar inventario** | Dice qué se importa. |

#### 4.3.3 Qué cambia en el código

- `menu.ts`: el elemento del menú gana un campo `grupo` jerárquico y una marca de "plegable". Ya existe `grupo`; hace falta añadir el comportamiento.
- `armazon-escritorio.tsx` y `menu-hoja.tsx`: pintar los grupos como secciones plegables (el `Sidebar` de shadcn ya soporta grupos colapsables). El estado abierto/cerrado se recuerda por persona en el navegador, con respaldo si el almacenamiento falla.
- Táctil de 44 px, foco visible y `aria-expanded` en cada grupo.

### 4.4 Número de empleado automático

- El servidor **genera** el número de empleado al dar de alta: un consecutivo propio, con formato `E-000001`, que no se repite aunque se borren registros de trabajo.
- RH **ya no lo escribe**. El formulario deja de pedirlo y, al guardar, muestra el número asignado.
- **Reingreso (T-02):** hoy se detecta con el número de empleado repetido. Pasa a detectarse por **CURP** (único si existe) o por nombre y fecha de ingreso, con el aviso de siempre. Hay que decidir el criterio (sección 10).
- **Importación de trabajadores o carga histórica:** si el centro ya tiene números propios, el alta puede aceptar uno **solo con un permiso de administración** y marcarlo como externo. Se decide en la sección 10.
- Se mantiene el **código de la credencial** (`TRB-XXXXXXXX`): es lo que lleva el QR y lo que se escanea para identificar al trabajador. **No es el número de empleado.** El número de empleado es de RH y se imprime en la credencial; el código del QR es para el escáner.

### 4.5 Roles y permisos: botón por grupo

Mejora a la pantalla de un rol (`/roles/:id`, FEAT-006). Hoy cada permiso es un interruptor y hay que moverlos uno por uno. La matriz ya agrupa los permisos por módulo; cada grupo gana un botón.

| Pieza | Qué hace |
|---|---|
| **Botón «Activar todos» por grupo** | Enciende todos los permisos de ese grupo que se puedan encender en ese momento. |
| **Botón «Quitar todos»** | Cuando el grupo ya está completo, el mismo botón pasa a quitar todos. Si el grupo está a medias, ofrece «Activar todos». |
| **Contador del grupo** | «3 de 5 activos», para ver de un vistazo qué falta. |
| **Un solo botón para todo el rol** | Opcional: «Activar todo» y «Quitar todo» arriba de la matriz. |

**Reglas**
- El botón **solo mueve los interruptores en pantalla**; no guarda. Los cambios siguen la confirmación de siempre («se agregan N permisos y se quitan M»), así que se pueden revisar y descartar con «Descartar cambios».
- **Respeta lo que hoy bloquea un interruptor.** Un permiso que no se puede mover (por ejemplo `acceso.administrar` del rol Administrador, que está protegido) se queda como está, y el botón avisa cuántos no pudo mover y por qué.
- **Respeta las dependencias.** Activar un permiso que necesita uno de «ver» enciende también ese de «ver»; quitar uno de «ver» quita los que dependen de él. El servidor sigue validando lo mismo al guardar (422 si falta una dependencia).
- **Datos reservados.** Los permisos de información (costos, CURP, NSS) están dentro de sus grupos. Al activar un grupo que los incluye, la confirmación de guardar los **nombra aparte** («incluye ver costos y datos personales») para que no pasen sin ser vistos.
- Nada cambia en el servidor para los permisos: la API sigue siendo `PUT /api/roles/{id}/permisos` con la lista final. Es un cambio de interfaz.
- Queda en el registro de cambios igual que hoy, con los permisos agregados y quitados.

## 5. Fuera de alcance

- Mínimos y alertas de stock (FEAT-004) y valor del inventario (FEAT-002).
- Ubicación dentro del almacén (estante, anaquel).
- Gráficas arbitrarias combinables a gusto del usuario o un generador de reportes.
- Exportar el tablero a PDF.
- Permisos por subconjunto de almacenes: sigue siendo "el suyo o todos" (AC-06).
- Cambiar la clave de un almacén que ya tiene folios.
- Borrar un almacén. Solo se inactiva.
- Notificaciones y alertas automáticas por correo.
- **Periodo por apertura (ciclos de un almacén de proyecto):** al reactivar el mismo almacén, cada apertura tendría su propio ciclo con fecha de apertura y de cierre. **Decidido: después del MVP.** Mientras tanto, el reporte de cierre (FEAT-002) se pide por rango de fechas. Ver [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md), sección 12.2.

## 6. Permisos

| Permiso | Estado | Cambio |
|---|---|---|
| `almacenes.administrar` | Declarado para el Supervisor, pendiente | **Pasa al Administrador solamente**. El supervisor no crea ni inactiva almacenes (hoy la tabla 8.3 se lo asignaba; se corrige en la sección 8). |
| `almacenes.todos` | Existe | Sin cambio. Marca quién ve todos los almacenes. |
| `tablero.ver` | Pospuesto, solo administrador | **Se activa y se reparte:** administrador, supervisor y almacenista. El alcance lo da `almacenes.todos`: con él, todos y con selector; sin él, solo el almacén asignado. Compras y RH **no** lo tienen. |

Cada endpoint declara su permiso y el servicio aplica el alcance de AC-06. **Nunca se compara el nombre del rol.** Las rutas del menú y del Inicio se esconden o se muestran según los permisos que ya entrega la sesión.

## 7. Cambios de datos o API esperados

### 7.1 Datos

- **Sin tablas nuevas** para almacenes. Se usan los campos ya existentes (`estado`, `cerrado_en`, `padre_id`).
- **Número de empleado:** una tabla de contador, por ejemplo `serie_empleado` (una fila), o reutilizar el patrón de `serie_folio`. Requiere **migración de Alembic** y actualizar `data-model.md`. Los trabajadores existentes **conservan** su número actual.
- **Auditoría:** acciones nuevas `almacen.crear`, `almacen.editar`, `almacen.inactivar` y `almacen.reactivar`, con el antes y el después.

### 7.2 API

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/almacenes` | `almacenes.administrar` | Crea el almacén y su ubicación. Errores: `CLAVE_REPETIDA`, `NOMBRE_REPETIDO`, `PADRE_INVALIDO`, `YA_HAY_CENTRAL`. |
| `PATCH /api/almacenes/{id}` | `almacenes.administrar` | Edita nombre y de quién depende. |
| `POST /api/almacenes/{id}/cierre` | `almacenes.administrar` | Inactiva con las condiciones de 4.1.2. Errores: `CON_EXISTENCIAS`, `CON_TRASPASOS_EN_TRANSITO`, `CON_HIJOS_ACTIVOS`, `CON_USUARIOS`. Cada uno trae el detalle de qué falta. |
| `POST /api/almacenes/{id}/reapertura` | `almacenes.administrar` | Reactiva. |
| `GET /api/almacenes` | `inventario.ver` (ya existe) | Se amplía: incluye `cerrado_en` y un resumen opcional (`?resumen=true`). |
| `GET /api/tablero/resumen?almacen_id=` | `tablero.ver` | Las tarjetas de 4.2.2. Sin `almacenes.todos` ignora `almacen_id` y usa el de la sesión. |
| `GET /api/tablero/consumo?desde=&hasta=&almacen_id=&categoria_id=&limite=` | `tablero.ver` | El ranking de 4.2.3, **agrupado en el servidor** (por artículo y, si se pide, por almacén). Hoy el reporte de consumo da el total por artículo, pero hay que llamarlo una vez por almacén y no cubre las herramientas retornables. Este endpoint se construye sobre la misma consulta. |
| `POST /api/trabajadores` | `trabajadores.administrar` | Ya no recibe `numero_empleado`; lo devuelve generado. |

Todo cambio en el contrato se documenta en `api-contracts.md` en el mismo cambio.

## 8. Reglas de negocio nuevas (IDs tentativos)

| ID | Regla |
|---|---|
| **AL-01** | Solo `almacenes.administrar` crea, edita, inactiva y reactiva almacenes. |
| **AL-02** | Hay un solo almacén central. Los demás dependen de otro, sin ciclos. La clave y el nombre son únicos. |
| **AL-03** | Un almacén se inactiva solo con existencias en cero, sin traspasos en tránsito y sin hijos activos. Los usuarios asignados lo bloquean hasta reasignarlos (decisión pendiente, sección 10). |
| **AL-04** | Un almacén `CERRADO` no recibe ni envía movimientos ni solicitudes nuevas. Conserva su historial y aparece en los reportes. |
| **AL-05** | La clave de un almacén con folios no se cambia. |
| **TB-01** | El tablero respeta AC-06: sin `almacenes.todos`, solo el almacén de la sesión. |
| **TB-02** | «Usado» es lo entregado en el rango, neto de cancelaciones, y se separa por categoría. |
| **TB-03** | Las fechas del rango se interpretan en la hora del centro de México. |
| **T-10** | El número de empleado lo genera el servidor y no se repite (ajusta T-01 y T-02). |

Se ajusta también la tabla 8.3: `almacenes.administrar` pasa de Supervisor a Administrador.

## 9. Criterios de aceptación

**Almacenes**
- Dado un administrador, cuando crea el almacén `PRY` dependiente de Contratistas, entonces aparece en la lista, tiene su ubicación y se puede asignar personal y recibir una entrada.
- Dado un almacén con existencias, cuando se intenta inactivar, entonces el servidor responde `CON_EXISTENCIAS` y dice cuántas unidades y de qué artículos.
- Dado un almacén inactivo, cuando alguien intenta entregar desde él, entonces recibe «Ese almacén está cerrado.»
- Dado un almacén inactivo, entonces su historial y sus reportes siguen visibles.
- Dado un supervisor, cuando abre `/almacenes`, entonces no existe para él (404 o ausente en el menú) y `POST /api/almacenes` responde 403.
- Dado un almacén recién creado, cuando se importa un Excel de alta hacia él, entonces el vale de entrada sale con el folio `PRY-ENT-000001`.

**Tablero**
- Dado el administrador en "Todos", entonces ve las tarjetas con el total de todos los almacenes, y al elegir Midrex todo se recalcula solo para Midrex.
- Dado un almacenista de Midrex, entonces su Inicio muestra solo datos de Midrex, sin selector, y `GET /api/tablero/resumen?almacen_id=<otro>` devuelve los datos de Midrex (ignora el parámetro).
- Dado Compras o RH, entonces no ven el tablero y `GET /api/tablero/resumen` responde 403.
- Dado el filtro Midrex, Este mes y Consumibles, entonces la gráfica muestra el consumible más usado ahí, y al cambiar el almacén o el periodo se actualiza sin recargar la pantalla.
- Dado un rango sin movimientos, entonces se muestra el estado vacío y no una gráfica vacía.
- La suma de la gráfica coincide con el reporte de consumo del mismo rango y almacén.

**Menú**
- Cada rol ve solo los grupos y las entradas que su permiso permite, y ninguno ve más de 7 grupos.
- Operación se abre y se cierra con el teclado y el dedo, y recuerda su estado entre visitas.

**Roles y permisos**
- Dado un rol con un grupo a medias, cuando el administrador toca «Activar todos» en ese grupo, entonces todos los interruptores del grupo quedan encendidos y nada se guarda hasta confirmar.
- Dado un grupo completo, entonces el mismo botón dice «Quitar todos» y los apaga.
- Dado el rol Administrador, entonces el botón no quita `acceso.administrar` y avisa que lo dejó como estaba.
- Dado un grupo que incluye `catalogo.costos`, cuando se guarda, entonces la confirmación lo nombra aparte.
- Dado un permiso que depende de uno de «ver», cuando se activa, entonces el de «ver» se enciende también.

**Número de empleado**
- Dado RH, cuando da de alta a un trabajador, entonces el formulario no pide número de empleado y la ficha muestra el asignado, único y consecutivo.

## 10. Decisiones pendientes (necesito tu respuesta)

| # | Pregunta | Mi recomendación |
|---|---|---|
| 1 | **Inactivar con usuarios asignados:** ¿bloquear hasta reasignarlos o solo avisar? | Bloquear. |
| 2 | **Sembrar los seis almacenes** con un comando de mantenimiento para el primer arranque, además de la pantalla. | Sí, solo si no hay ninguno. |
| 3 | **Tipos de almacén:** hoy son `CENTRAL`, `SUBALMACEN` y `PROYECTO`. ¿Se conservan los tres? | Sí. Contratistas es `SUBALMACEN`; Midrex, HYL, Laminador y Minas son `PROYECTO`. |
| 4 | **Gráficas:** ¿se usa una librería nueva (hay que aprobarla y escribir un ADR) o barras hechas con HTML y CSS, sin dependencias? | Sin dependencias para la primera entrega: barras horizontales con CSS y SVG. Una librería solo si luego se piden gráficas más complejas. |
| 5 | **Reingreso de un trabajador** al ya no tener número de empleado capturado: ¿por CURP, o por nombre y fecha? | Por CURP cuando exista; si no, por nombre completo con aviso de coincidencia. |
| 6 | **Números de empleado propios del centro:** ¿se aceptan al dar de alta solo con permiso de administración? | Sí, marcados como externos. |
| 7 | **Qué cuenta como «usado» para las herramientas:** ¿entregas o unidades? | Entregas (cada entrega una vez), separadas de los consumibles. |
| 8 | **Contratistas:** ¿maneja herramienta o solo EPP? | **Resuelta con la plática** (min 35): maneja las dos cosas. Ver [red-de-almacenes-y-flujo.md](../product/red-de-almacenes-y-flujo.md). |
| 9 | **Ubicación de los botones de operación en el Inicio** del almacenista: ¿arriba del tablero o a un lado? | Arriba y grandes: es lo que más usa. |

## 11. Riesgos

| Riesgo | Cómo se atiende |
|---|---|
| El administrador cambia el selector y cree que **opera** en ese almacén. | El selector del tablero **no** cambia el almacén de operación. Se rotula «Viendo: Midrex» con un aviso y las acciones de operación no dependen de él. |
| Inactivar un almacén **sin querer**. | Confirmación con el nombre y el resumen de lo que pasará; el botón no se activa hasta cumplir las condiciones. |
| Rangos largos con **demasiados artículos** vuelven ilegible la gráfica. | Solo los 10 principales, con el resto agrupado en «Otros». |
| El «consumo» no coincide con lo que alguien espera (compras contra entregas). | Cada tarjeta y la gráfica dicen en una línea qué cuentan. |
| El **cálculo del tablero es lento** con mucho historial. | Consultas agregadas con índices por fecha y almacén; revisar el plan de ejecución. Si hace falta, un resumen diario precalculado. |
| Mover el menú **desorienta** a quien ya lo usa. | Mismos nombres siempre que se pueda, y el cambio se anota en la guía por rol. |
| La **concurrencia** al crear dos almacenes con la misma clave. | Restricción única en base de datos y manejo del error. |

## 12. Documentos que se actualizan en el mismo cambio

| Documento | Qué cambia |
|---|---|
| `docs/product/mvp-scope.md` | El tablero sale de «Pospuesto». Es una ampliación de alcance y **requiere tu aprobación explícita**. |
| `docs/product/reglas-de-negocio.md` | Reglas AL-01 a AL-05, TB-01 a TB-03 y T-10; ajuste de T-01 y T-02; permisos `almacenes.administrar` y `tablero.ver` en la sección 8 y la tabla 8.3. |
| `docs/architecture/data-model.md` | Contador del número de empleado y `cerrado_en`. |
| `docs/architecture/api-contracts.md` | Endpoints de la sección 7.2. |
| `docs/product/app-flow.md` | Rutas `/almacenes` y el Inicio por rol. |
| `docs/product/ui-ux.md` | Patrones: grupo de menú plegable, tarjetas de indicadores, gráfica de barras con filtros y botón por grupo en la matriz de permisos. |
| `docs/architecture/decisions/` | Un ADR **solo si** se elige una librería de gráficas. |
| `docs/guia-por-rol.md` | Menú nuevo y tablero. |
| `docs/features/FEAT-002-cierre-de-almacen.md` | Referencia a este brief para el cierre y el valor del inventario. |

## 13. Plan de trabajo por etapas

Cada etapa se prueba y se puede entregar sola.

**Etapa 0: aprobación.** Responder las decisiones de la sección 10 y aprobar el cambio de alcance. Actualizar los documentos de la sección 12.

**Etapa 1: administración de almacenes (backend).**
1. Servicio y repositorio: crear, editar, inactivar y reactivar, con las reglas AL-01 a AL-05 y auditoría.
2. Endpoints de 7.2 con su permiso.
3. Extender el rechazo de almacén `CERRADO` a entregas, devoluciones, entradas y solicitudes de compra (4.1.3).
4. Verificar si `serie_folio` es perezosa.
5. Comando de mantenimiento para sembrar (si se aprueba).
6. Pruebas: una por regla con su ID en el nombre, una de permisos por endpoint y una de concurrencia en el alta.

**Etapa 2: administración de almacenes (interfaz).**
1. Pantalla `/almacenes` con lista, alta, edición y la acción de inactivar con confirmación.
2. Enlaces a usuarios, personal e inventario del almacén.
3. Entrada «Almacenes» en el grupo Administración, solo con el permiso.

**Etapa 3: tablero (backend).**
1. Endpoint `GET /api/tablero/resumen` y `GET /api/tablero/consumo`, construidos sobre las consultas existentes de `consulta`, con alcance AC-06 en el servicio.
2. Activar y repartir `tablero.ver`.
3. Pruebas: el alcance por usuario, que la suma coincide con el reporte de consumo y que Compras y RH reciben 403.

**Etapa 4: tablero (interfaz).**
1. Tarjetas y gráfica de barras con filtros (sin dependencias nuevas, salvo decisión contraria).
2. Selector de almacén solo para `almacenes.todos`, con «Viendo: …».
3. Estados de carga, vacío y error; accesible y táctil.
4. El Inicio por rol: tablero más «Lo que haces hoy».

**Etapa 5: menú.**
1. Grupos plegables en escritorio y celular, con el estado recordado.
2. Nombres nuevos y reordenamiento de la sección 4.3.
3. Prueba de que cada rol ve solo lo suyo.
4. Botón por grupo en la matriz de permisos de `/roles/:id` (sección 4.5), con pruebas de interfaz de las dependencias y los permisos protegidos.

**Etapa 6: número de empleado automático.**
1. Migración del contador y servicio de alta sin número capturado.
2. Reingreso por el criterio elegido.
3. Formulario de alta de RH sin ese campo.
4. Pruebas de unicidad bajo concurrencia.

**Etapa 7: cierre.** Guía por rol, changelog y el reporte final de `docs/templates/reporte.md`.

## 14. Validaciones requeridas

- `uv run pytest`, `uv run ruff check .` y `uv run ruff format --check .`.
- `pnpm typecheck` y `pnpm build`.
- Prueba manual en el navegador con cada rol de datos de prueba: administrador, supervisor, almacenista, Compras y RH.
- Probar en celular (menú plegable y tarjetas) y con teclado.
- Revisar que ningún dato reservado (costos, CURP, NSS) se cuele en el tablero.
- Otra persona o agente revisa el cambio antes de darlo por terminado.

## 15. Módulos relacionados conocidos

`almacenes`, `acceso` (permisos y usuarios), `movimientos` (rechazo de almacén cerrado y folios), `consulta` (consultas del tablero), `trabajadores` (número de empleado), `solicitudes_compra`, `importacion` (ya rechaza almacén cerrado) y `auditoria`.
