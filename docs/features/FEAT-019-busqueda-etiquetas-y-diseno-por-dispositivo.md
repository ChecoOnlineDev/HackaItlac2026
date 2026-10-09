# FEAT-019: Búsqueda con espera, etiquetas en PDF, diseño por dispositivo y estética

Estado: **aprobada por el usuario el 8 de octubre de 2026, sin construir.** Sale de las decisiones D-18 a D-21 del [documento maestro de la iteración 01](../releases/iteration_01/README.md) y usa las reglas **UX-01 a UX-12** (sección 4 del maestro). Amplía C-06 (qué encuentra la búsqueda), cambia el contrato de `GET /api/busqueda` y de `GET /api/etiquetas`, y cambia varios patrones de [ui-ux.md](../product/ui-ux.md) (ver «Documentos globales que podrían actualizarse»). Va en el paso 6 del orden de construcción del maestro. Las decisiones que dependen del usuario están en «Decisiones abiertas».

## Problema u oportunidad

La plática del 8 de octubre y la revisión del código encontraron cuatro problemas:

1. **Los buscadores no se comportan igual.** [ui-ux.md](../product/ui-ux.md) dice que «todas las búsquedas usan `useRetraso` (300 ms)», pero no es así:
   - Consultar, Entregar, Devolver y Trasladar buscan **solo al oprimir Enter** dentro del escáner (`routes/consulta/consultar.tsx`, `routes/operacion/entregar.tsx`, `devolver.tsx`, `trasladar.tsx`, `componentes/entrega/paso-trabajador.tsx`): mientras se escribe no aparece nada.
   - Recibir y el detalle de un traspaso esperan **200 ms** (`routes/operacion/recibir.tsx:79`, `recibir-detalle.tsx:290`).
   - Etiquetas y Almacenes filtran la lista ya cargada a cada tecla, sin espera.
   - El mínimo de dos caracteres se repite a mano en ocho archivos con nombres distintos (`MINIMO`, `MINIMO_BUSQUEDA`, `buscable = q.length >= 2`).
2. **La búsqueda no encuentra lo que el mostrador pide.** `GET /api/busqueda` busca al trabajador con `nombre LIKE '%texto%'`: «pérez juan» no encuentra a «Juan Pérez López». No busca por **código de credencial** ni por **marca**. Una pieza dice «Juan Pérez (EMP-1001)» y no «En resguardo de Juan Pérez», como sí lo dice Seguimiento (C-13), y un artículo por cantidad retornable no dice cuántos tienen los trabajadores.
3. **Las etiquetas solo se imprimen.** La pantalla Etiquetas arma una hoja de 18 en HTML y llama a `window.print()` (`routes/inventario/etiquetas.tsx`, `componentes/dominio/hoja-etiquetas.tsx`). No hay un PDF que se pueda guardar, mandar o imprimir después, ni hojas de 9 o de 30. Las piezas de una importación grande pierden la selección: el enlace manda los códigos en la dirección y, pasados 6000 caracteres, abre la lista sin nada elegido (`componentes/importacion/resultado-importacion.tsx:30`).
4. **El diseño no distingue el mostrador de la oficina.**
   - El marco de la aplicación limita todo el contenido a 1152 px (`max-w-6xl` en `componentes/navegacion/armazon-escritorio.tsx:139`), aun en las tablas administrativas.
   - En pantallas de celular hay enlaces de 40 px (`routes/consulta/pieza.tsx:92` y `:145`, `routes/operacion/recibir-detalle.tsx:84`, `componentes/consulta/bloques.tsx:31`).
   - La estética tiene inconsistencias visibles; están en la sección D.

## Objetivo

- Que buscar se sienta igual en toda la aplicación: espera breve, nunca un resultado viejo y encuentra a la persona o la herramienta como la nombra el almacén.
- Que las etiquetas salgan en un solo PDF con el tamaño que pide cada uso.
- Que la operación diaria se diseñe y se pruebe en el celular del mostrador, y lo administrativo en la computadora, sin que ninguna de las dos se rompa en el otro dispositivo.

## Historia de usuario

- Como almacenista, quiero escribir «perez» o parte del número del trabajador y ver la lista mientras escribo, para encontrarlo aunque su credencial no se lea.
- Como almacenista, quiero que al buscar una herramienta me diga quién la tiene o en qué almacén está, para no abrir su ficha.
- Como Compras, quiero descargar en un PDF las etiquetas de las 300 piezas que acabo de importar, en hojas de 30, para imprimirlas en hojas adhesivas.
- Como RH, quiero sacar en un PDF las credenciales de los trabajadores que di de alta esta semana.
- Como supervisor, quiero aprobar y recibir desde el celular sin tablas que se salgan de la pantalla, y revisar la bitácora en la computadora con la tabla a todo el ancho.

Todavía no hay historias en `docs/stories/`: se escriben al empezar la construcción.

## Alcance incluido

### A. Búsqueda (UX-01 a UX-04)

| ID | Regla | Origen |
|---|---|---|
| UX-01 | **Cuándo se busca.** Todo buscador busca **300 ms después de la última tecla**. La búsqueda automática pide **2 caracteres o más** (sin contar espacios al inicio y al final). **Enter** busca de inmediato, sin esperar. Con 1 carácter, Enter intenta solo la identificación exacta (`GET /api/escaneo/{codigo}`), para que un número de empleado propio corto («7») o un código de un carácter se encuentren. Lo que llega de la **pistola** o de la **cámara** es una lectura, no una búsqueda: va directo al escaneo, sin espera y sin lista. | D-18; decisión de este brief |
| UX-02 | **Una búsqueda a la vez y estados claros.** Al empezar una búsqueda se cancela la anterior. Una respuesta que llega para un texto que ya no es el del campo se descarta y nunca se pinta. Estados visibles: menos de 2 caracteres, «Escribe al menos 2 letras o números»; esperando respuesta, «Buscando…»; sin coincidencias, «No encontramos nada con "<texto>"» con una acción; error, el mensaje en español llano con «Reintentar»; sin conexión, «Sin conexión. Escanea el código o inténtalo cuando vuelva la señal». Mientras llega la respuesta nueva, la lista anterior se queda **atenuada y no se puede tocar**, para que nadie elija un resultado del texto anterior. | D-18; decisión de este brief |
| UX-03 | **Qué encuentra.** Amplía C-06. **Trabajadores:** por nombre y apellidos por **palabras, en cualquier orden y en cualquier parte** del nombre («perez juan» encuentra a «Juan Pérez López»), sin distinguir acentos ni mayúsculas; por número de empleado (contiene); y por código de credencial (empieza con). **Artículos:** por nombre (por palabras), marca y código. **Piezas:** por código de pieza, número de serie y nombre de su artículo. Una pieza con serie pendiente no se encuentra por serie, solo por su código (I-02, E-18). El orden es: coincidencia exacta del código o del número, luego lo que empieza con el texto, luego lo que lo contiene; dentro de cada grupo, por nombre. Cada grupo respeta los permisos y el alcance como hoy (AC-05, AC-06, C-02). | D-18; C-06 |
| UX-04 | **Qué dice cada resultado y cuánto trae.** Una **pieza** dice dónde está o quién la tiene con el mismo texto de Seguimiento (C-13): «En resguardo de Juan Pérez (E-000123)», «En Kepler», «En tránsito a Contratistas», más su estado si no está apta. Un **artículo retornable por cantidad** dice cuánto hay en el almacén del usuario y cuánto tienen los trabajadores («3 en Midrex · 5 con trabajadores»); esta última cifra se ve completa, como en C-03. Un **artículo consumible** dice solo lo que hay. Un **trabajador** dice su número, su puesto y su vigencia en una insignia con icono y texto, y, si coincidió por la credencial, «Credencial <código>». Ningún resultado trae costos, CURP ni NSS. El servidor devuelve **10 por grupo** por omisión, **8** en las hojas de elección dentro de un flujo, y **50 como máximo** (`tamano`). «Ver más» pide la página siguiente; nunca hay una petición por letra. | D-18; AC-06, C-03, C-13 |

#### Detalle, acción por acción

| Lo que hace la persona | Lo que pasa |
|---|---|
| Escribe una letra | No se busca. Debajo del campo: «Escribe al menos 2 letras o números». |
| Escribe la segunda letra y sigue escribiendo | Cada tecla reinicia la espera de 300 ms. No sale ninguna petición mientras escribe con ritmo normal. |
| Deja de escribir 300 ms | Se manda una petición con el texto completo. Aparece «Buscando…» en una línea bajo el campo (con `aria-live="polite"`) y la lista anterior, si la hay, se atenúa. |
| Escribe otra letra mientras la petición va en camino | La petición anterior se cancela (`AbortController`). Si su respuesta llega de todos modos, se descarta porque su texto no es el del campo. |
| Oprime Enter | Se cancela la espera y se busca en ese instante. En los buscadores con escáner, Enter primero intenta identificar el código exacto: si es un trabajador, una pieza, un artículo o un vale, abre o agrega eso como hoy; si no, muestra la lista de coincidencias. |
| Borra todo el texto | Se cancela lo pendiente y la lista vuelve a su estado inicial: la lista completa en las pantallas con tabla, o vacía en Consultar. |
| Toca «Borrar» (la equis del campo) | Lo mismo que borrar el texto, y el foco se queda en el campo. |
| Dispara la pistola con el foco **fuera** de un campo | El escáner captura la ráfaga como hoy (`componentes/dominio/escaner.tsx`) y la entrega como lectura; el buscador no se entera. |
| Dispara la pistola con el foco **dentro** del campo | Las teclas llegan en ráfaga (menos de 30 ms entre teclas) y terminan en Enter antes de que se cumplan los 300 ms. Así no sale ninguna búsqueda a medias. Enter se trata como lectura: identificación exacta; si no es un código conocido, se muestra la lista como con un Enter escrito a mano. El campo se limpia después de una lectura de pistola para la siguiente. |
| Lee con la cámara | La lectura va directo a la identificación exacta, sin pasar por el campo de texto. |
| Elige un resultado | En una pantalla de flujo (Entregar, Devolver, Trasladar) el resultado se agrega como si se hubiera escaneado su código. En Consultar abre la ficha. En una tabla, la tabla ya está filtrada. |
| Sale de la pantalla con una búsqueda en camino | La petición se cancela al desmontarse el componente. |
| Pierde la señal | Se muestra el estado sin conexión; el texto se conserva y Enter o «Reintentar» vuelven a intentarlo. |

#### Componente común

Todos los buscadores usan las mismas dos piezas. Ninguna pantalla vuelve a escribir su propia espera, su mínimo ni su cancelación.

- **`useBusquedaDiferida`** (gancho nuevo, `frontend/app/componentes/ui/busqueda-diferida.ts`):
  - Recibe el texto, la función que pide (con `AbortSignal`), el mínimo (2 por omisión) y la espera (300 ms por omisión).
  - Devuelve `{estado, resultado, textoDelResultado, buscarYa, limpiar}`. `estado` es uno de `inactivo`, `corto`, `buscando`, `listo`, `vacio`, `error` y `sin_conexion`.
  - `buscarYa` es lo que llama Enter. `textoDelResultado` permite descartar lo viejo (UX-02).
  - Internamente reutiliza `useRetraso` y la cancelación de `useConsulta` (`componentes/catalogo/usar-consulta.ts`). `useRetraso` se mueve a `componentes/ui/` para que no viva en el catálogo.
- **`CampoBusqueda`** (ya existe en `frontend/app/componentes/ui/campo-busqueda.tsx`) se amplía:
  - recibe el `estado` del gancho y pinta la línea de estado bajo el campo;
  - agrega el botón «Borrar» de 44 px;
  - envía con Enter (`alEnviar`);
  - distingue la ráfaga de la pistola con la misma regla del escáner (`MAXIMO_ENTRE_TECLAS_MS`), sin copiarla.
- Un **filtro sobre una lista que ya está en la pantalla** (Etiquetas, Almacenes, Recibir, el detalle de un traspaso) también espera 300 ms. Compara sin acentos ni mayúsculas con la misma función `normalizar` y no llama al servidor.
- En el modo práctica del tutorial (`frontend/app/api/practica.ts`) la búsqueda local sigue las mismas reglas: palabras en cualquier orden, sin acentos ni mayúsculas.

#### Inventario de buscadores que migran

| Pantalla | Ruta | Archivo | Hoy | Cambia a |
|---|---|---|---|---|
| Consultar | `/consultar` | `routes/consulta/consultar.tsx` | Solo con Enter; mínimo 2 a mano | Lista mientras se escribe (UX-01), Enter y lectura exacta; resultados con UX-04 |
| Entregar, paso del trabajador | `/entregar` | `componentes/entrega/paso-trabajador.tsx` | Solo con Enter | Lista de trabajadores mientras se escribe; elegir uno abre su ficha de confirmación |
| Entregar, paso de artículos | `/entregar` | `routes/operacion/entregar.tsx`, `componentes/entrega/hoja-busqueda-articulos.tsx` | Solo con Enter; hoja «¿Cuál es?» | Sugerencias bajo el campo (8) mientras se escribe; Enter conserva la hoja |
| Devolver | `/devolver` | `routes/operacion/devolver.tsx` | Solo con Enter | Igual que Entregar; las piezas muestran quién las tiene (UX-04) |
| Trasladar (enviar) | `/trasladar` | `routes/operacion/trasladar.tsx` | Solo con Enter; con `almacen_id` (TR-11) | Lista mientras se escribe; conserva `almacen_id` y `disponible` |
| Recibir | `/recibir` | `routes/operacion/recibir.tsx` | Filtro local de 200 ms | Filtro local de 300 ms |
| Detalle de un traspaso | `/recibir/:id` | `routes/operacion/recibir-detalle.tsx` | Filtro local de 200 ms | Filtro local de 300 ms; la pistola en el campo marca el renglón |
| Existencias | `/inventario` | `routes/inventario/inventario.tsx` | `useRetraso` | `useBusquedaDiferida` |
| Piezas y resguardos | `/seguimiento` | `routes/consulta/seguimiento.tsx`, `componentes/seguimiento/pestana-cantidad.tsx` | `useRetraso`, mínimo a mano | `useBusquedaDiferida` |
| Dar entrada, capturar a mano | `/entrada` | `componentes/entradas/buscador-articulos.tsx` | `useRetraso`, mínimo a mano | `useBusquedaDiferida`; conserva «Crear este artículo» (EK-07) |
| Artículos | `/catalogo/articulos` | `routes/inventario/articulos.tsx` | `useRetraso` | `useBusquedaDiferida` |
| Puestos y su dotación | `/puestos` | `routes/inventario/puestos.tsx`, `componentes/puestos/hoja-dotacion.tsx` | `useRetraso`, mínimo a mano | `useBusquedaDiferida` |
| Etiquetas | `/etiquetas` | `routes/inventario/etiquetas.tsx` | Filtro local sin espera | Filtro local de 300 ms, sin acentos |
| Trabajadores | `/trabajadores` | `routes/personas/trabajadores.tsx` | `useRetraso` sobre `GET /api/trabajadores?q=` | `useBusquedaDiferida`; `q` busca por palabras (UX-03) |
| Usuarios | `/usuarios` | `routes/acceso/usuarios.tsx` | `useRetraso` | `useBusquedaDiferida` |
| Personal por almacén | `/personal` | `routes/supervision/personal.tsx` | `useRetraso` | `useBusquedaDiferida` |
| Almacenes | `/almacenes` | `routes/acceso/almacenes.tsx` | Filtro local sin espera | Filtro local de 300 ms |
| Pedir una compra urgente | `/compras/nueva` | `componentes/compras/solicitar/buscador-articulo.tsx` | `useRetraso`, mínimo a mano | `useBusquedaDiferida` |
| Mis solicitudes y cola de Compras | `/compras/mias`, `/compras` | `routes/compras/mias.tsx`, `routes/compras/index.tsx` | `useRetraso` | `useBusquedaDiferida` |
| Filtros de trabajador y artículo de los reportes | `/reportes/*` | `componentes/reportes/selector-busqueda.tsx` | `useRetraso`, mínimo a mano | `useBusquedaDiferida` |
| Pantallas nuevas de la iteración (Proyectos, Deudores, Bitácora por vale, Inspecciones) | Las define su FEAT | FEAT-013, 016, 017 y 018 | No existen | Nacen con `useBusquedaDiferida` y `CampoBusqueda` |

#### En el servidor

- `GET /api/busqueda` parte el texto en palabras (hasta 5; se ignoran las de una letra si hay otras). Exige que **cada palabra** aparezca en el nombre: un `LIKE '%palabra%'` por palabra, unidos con «y». El número de empleado, el código y la serie se comparan contra el texto completo.
- La colación de la base (`utf8mb4_0900_ai_ci`, `docker-compose.yml`) ya ignora acentos y mayúsculas. La prueba lo verifica con «perez» contra «Pérez» para que un cambio de colación no lo rompa en silencio.
- El código de credencial se busca en la tabla `codigo` (tipo TRABAJADOR) con «empieza con», que usa su llave primaria.
- La marca se agrega a la condición de artículos. `tamano` de esta ruta se limita a 50 (hoy vale el máximo general de 200, `core/paginacion.py`).
- **Sin índices nuevos en esta feature.** `%palabra%` no usa un índice, pero sobre unos miles de trabajadores y piezas responde en milisegundos. Si con 20 000 piezas el tiempo de respuesta pasa de 300 ms en la prueba de carga, se propone un índice de texto completo (`FULLTEXT` con el analizador `ngram` de MySQL) en un ADR aparte.
- `GET /api/escaneo/{codigo}` no cambia: ya acepta un carácter.

### B. Etiquetas en PDF (UX-05 a UX-07)

| ID | Regla | Origen |
|---|---|---|
| UX-05 | **Un solo PDF.** La pantalla Etiquetas descarga **un archivo PDF** con todas las etiquetas elegidas, en hoja carta, con tres tamaños: **9 grandes (3 × 3)**, **18 medianas (3 × 6)** y **30 chicas (3 × 10)**. La credencial completa (CR80) sigue en su hoja de 8 (2 × 4), también en PDF. Cada etiqueta lleva el QR, que contiene **exactamente** el código registrado (RG-10), y debajo o al lado el texto legible: nombre, código y, si la tiene, la serie. El QR mide **20 mm o más** con su margen blanco, y cada módulo (cuadrito) del QR mide **0.5 mm o más**, para que lo lean la pistola y la cámara. El PDF se arma en el navegador, sin pasar por el servidor, para que funcione también en la app de Android. La vista previa en pantalla usa las mismas medidas que el PDF. «Imprimir» queda como acción secundaria. | D-19 |
| UX-06 | **Tipos y orígenes.** Tipos: **credencial** de trabajador (completa o solo el QR), **pieza** y **estante** (artículo por cantidad, I-07). Orígenes: **selección manual** de la lista; **piezas creadas en una importación** (con código generado por I-15 o traído en el archivo); **trabajadores dados de alta en un rango de fechas**; y **todas las piezas de un artículo**. Se puede empezar en la etiqueta n.º N de la primera hoja, para aprovechar una hoja adhesiva ya usada en parte. El permiso sigue siendo `etiquetas.imprimir`, sin cambio. | D-19; I-07, I-15 |
| UX-07 | **Límites y casos difíciles.** Un PDF lleva **hasta 1000 etiquetas**. Con más, la pantalla pide dividir la selección. Mientras se arma, se ve el avance («Armando hoja 3 de 28») y se puede cancelar. Un nombre largo se corta con «…» al llegar a su número de renglones. El código **nunca** se corta: si no cabe, baja de tamaño hasta 7 pt y, si aún no cabe, pasa a dos renglones. Un código con caracteres especiales (acentos, «Ñ», «/», espacios) se escribe tal cual en el QR y en el texto. Si un código es tan largo que su QR quedaría con módulos de menos de 0.5 mm en el tamaño elegido, la pantalla avisa antes de descargar («3 etiquetas tienen un código largo que puede no leerse en tamaño chico; usa 18 por hoja») sin impedirlo. | D-19; RG-10 |

#### Formatos

Hoja carta: 215.9 × 279.4 mm. Las medidas son las del contenido; el margen de la hoja va aparte.

| Formato | Cuadrícula | Celda (aprox.) | QR | Texto | Uso |
|---|---|---|---|---|---|
| Grande | 3 × 3 = 9 | 65 × 86 mm | 45 mm, arriba y al centro | Debajo del QR: nombre en 2 renglones (12 pt), código (12 pt, negrita) y serie (10 pt) | Estantes y equipo grande, legible a distancia |
| Mediana | 3 × 6 = 18 | 65 × 42 mm (las 6 filas ocupan el alto útil de la hoja) | 30 mm, a la izquierda | A la derecha: nombre en 3 renglones (10 pt), código (10 pt, negrita) y serie (8 pt) | La de hoy, para piezas y estantes |
| Chica | 3 × 10 = 30 | 66.7 × 25.4 mm (1 × 2⅝ in, el formato común de hojas adhesivas de 30) | 21 mm, a la izquierda | A la derecha: nombre en 2 renglones (8 pt) y código (9 pt, negrita) | Herramienta chica y piezas de importación en hojas adhesivas |
| Credencial completa | 2 × 4 = 8 | 85.6 × 54 mm (CR80) | Como hoy (`TarjetaCredencial`) | Como hoy | Credencial del trabajador |

- Las guías de corte son líneas punteadas grises fuera del margen blanco del QR, en los tres formatos de etiqueta. En el formato chico no hay guías: lo corta la hoja adhesiva.
- Texto de cada tipo:
  - **Pieza:** nombre del artículo (con «· talla M» si la tiene), código de pieza y «Serie <número>». Si la serie está pendiente, no se imprime nada en su lugar: la etiqueta dura más que el pendiente.
  - **Estante:** nombre del artículo y su código.
  - **Credencial, solo QR:** nombre del trabajador, código de la credencial y «N.º <número de empleado>» si el número es distinto del código. Nunca CURP ni NSS (RG-13).
- Fuente: Poppins, la de la aplicación. Ver «Decisiones abiertas», punto 2.
- Nombre del archivo: `etiquetas-<tipo>-<formato>-AAAAMMDD-HHmm.pdf`, con la hora del centro de México (por ejemplo `etiquetas-piezas-30-20261008-1542.pdf`). Credenciales completas: `credenciales-AAAAMMDD-HHmm.pdf`.

#### Orígenes

| Origen | Cómo se llega | Qué pide al servidor |
|---|---|---|
| Selección manual | Etiquetas → tipo → marcar en la lista | `GET /api/etiquetas?tipo=` (como hoy) |
| Piezas de una importación | Resultado de la importación → «Imprimir etiquetas de las piezas nuevas» | `GET /api/etiquetas?tipo=piezas&lote_id=` (el lote de la importación, `vale.lote_id` de FEAT-017). Ya no se mandan los códigos en la dirección. Hasta que exista el lote, los códigos viajan en el estado de la navegación, no en la URL, y se acaba el tope de 6000 caracteres. Opcional: «Solo las de código generado». |
| Trabajadores dados de alta en un rango | Etiquetas → Credenciales → «Dados de alta entre…» con el selector de rango de fechas de los reportes | `GET /api/etiquetas?tipo=credenciales&alta_desde=&alta_hasta=` (fechas de México sobre `trabajador.creado_en`) |
| Todas las piezas de un artículo | Ficha del artículo por pieza → «Etiquetas de sus piezas», o Etiquetas → Piezas → filtro de artículo | `GET /api/etiquetas?tipo=piezas&articulo_id=` |

El origen solo **preselecciona**: la persona puede quitar o agregar antes de descargar.

#### Detalle, acción por acción

1. **Entra a Etiquetas.** Ve los tres tipos como hoy. En Credenciales, además, «Credencial completa» o «Solo el código QR».
2. **Elige el formato.** Hay tres botones de alternancia con un dibujo de la cuadrícula y su nombre: «9 grandes», «18 medianas», «30 chicas». El de omisión es 18 para piezas y estantes. Con credencial completa no hay selector: siempre son 8.
3. **Elige el origen o marca a mano.** Si llegó desde una importación o desde una ficha, la selección ya viene marcada y una línea dice de dónde («37 piezas de la importación del 8 de octubre»).
4. **Opcional: «Empezar en la etiqueta n.º».** Es un campo numérico de 1 a 9, 18 o 30 según el formato. La vista previa deja en blanco las primeras posiciones.
5. **Revisa la vista previa.** Es la primera hoja a escala, con «37 etiquetas · 3 hojas carta». Se pueden ver las siguientes con «Hoja anterior» y «Hoja siguiente». Si hay avisos de legibilidad (UX-07), salen arriba en amarillo con su texto.
6. **Toca «Descargar PDF».** Es la acción principal, en el pie fijo en celular y al final del contenido en computadora. El botón muestra el avance y «Cancelar». Al terminar, el navegador descarga el archivo y sale el aviso «Se descargó etiquetas-piezas-18-20261008-1542.pdf».
7. **Opcional: «Imprimir».** Es la acción secundaria: imprime la misma hoja desde el navegador, como hoy.

#### Cómo se arma el PDF

- Con **jsPDF**, la misma dependencia que la descarga del vale en PDF de FEAT-017. Se carga solo al tocar «Descargar PDF» (`import()` dinámico), para no hacer más pesada la primera carga. Agregarla requiere aprobación (ver «Decisiones abiertas»).
- El QR se dibuja **como vector**, con rectángulos negros sobre blanco. Los módulos contiguos de cada fila se unen en un solo rectángulo, para que el archivo no pese de más. Así queda nítido a cualquier tamaño de impresión. La matriz del QR se calcula con la misma librería que ya dibuja los QR en pantalla (`qrcode.react`). Si no expone la matriz, se dibuja el QR en un lienzo a 600 ppp y se inserta como imagen en blanco y negro, sin suavizado. No se agrega otra librería de QR.
- Se arma **una hoja a la vez** y se le devuelve el control a la pantalla entre hojas. Así la interfaz no se congela y se puede cancelar.
- Las medidas de los tres formatos viven en un solo archivo (`componentes/dominio/etiquetas-medidas.ts`), que usan la vista previa en HTML y el PDF.

### C. Diseño por dispositivo (UX-08 a UX-10)

| ID | Regla | Origen |
|---|---|---|
| UX-08 | **Cada pantalla tiene una clase y los anchos son fijos.** Cada ruta es **primero celular** o **primero computadora** (tabla de abajo); una pantalla nueva declara su clase al crearse. Se declara en el `handle` de la ruta (`dispositivo: "celular" \| "computadora"`), y `Pantalla` toma de ahí su ancho. Anchos: celular, menos de 768 px; tableta, de 768 a 1023 px; computadora, 1024 px o más (menú lateral, como hoy); ancha, 1280 px o más; muy ancha, 1536 px o más. Lo de celular se centra a **720 px como máximo** en pantallas grandes. Lo de computadora usa el ancho disponible hasta **1600 px**: el marco deja de limitar a 1152 px. | D-20 |
| UX-09 | **Primero celular.** Se diseña y se prueba a **360 × 640** y **412 × 915** px, la pantalla de los equipos de mano del mostrador, y además en horizontal a 640 × 360. Todo lo que se toca mide **44 px o más** (la acción principal 48 px y a todo el ancho; un renglón de un solo toque, 48 px). La acción principal va **fija abajo** (`AccionPrincipal`) y el teclado del celular no la tapa. No hay tablas anchas: las listas son tarjetas de una columna. La página nunca se desliza de lado. El escáner y el título caben sin desplazarse a 360 × 640. Los campos numéricos abren el teclado numérico (`inputmode="numeric"`). | D-20 |
| UX-10 | **Primero computadora, y que no se rompa en el celular.** Se diseña y se prueba a **1366 × 768** y **1920 × 1080**. Las tablas son densas: filas de 40 px, texto de 14 px, encabezado fijo al desplazarse, números a la derecha con cifras de ancho fijo (`tabular-nums`) y columnas secundarias que aparecen desde 1280 o 1536 px (como ya hace la cola de Compras). Los filtros: desde 1280 px, hasta tres filtros principales quedan **visibles en una barra superior**, junto a la búsqueda, y el resto en la hoja «Filtros»; por debajo de 1280 px, todos van en la hoja, como hoy. En el celular la pantalla **sigue funcionando**: la tabla pasa a tarjetas o, si es una tabla de detalle, se desliza de lado **solo dentro de su contenedor**; ninguna acción queda fuera de alcance; la página no se desliza de lado. | D-20 |

#### Clasificación de las rutas

Todas las rutas de `frontend/app/routes.ts`, más las pantallas nuevas de la iteración.

| Ruta | Pantalla | Clase | Nota |
|---|---|---|---|
| `/entrar` | Entrar | Las dos | Formulario de 720 px que funciona igual en los dos |
| `/` | Inicio | Según el rol | Almacenista y supervisor: celular («Lo que haces hoy» arriba). Administrador, Compras y RH: computadora |
| `/entregar` | Entregar | Celular | |
| `/devolver` | Devolver | Celular | |
| `/trasladar` | Trasladar (enviar) | Celular | El paso «Trasladar con una lista» (Excel) es de computadora dentro de la misma ruta: su vista previa sigue UX-10 |
| `/recibir`, `/recibir/:id` | Recibir traspaso | Celular | |
| `/autorizaciones` | Autorizaciones | Celular | También las solicitudes de despacho y de traslado (FEAT-014, FEAT-015) |
| `/consultar` | Consultar | Celular | |
| `/articulos/:id` | Ficha de artículo | Celular | La tabla «Quién lo tiene» ya se reduce en celular (SG-02) |
| `/piezas/:id` | Ficha de pieza | Celular | |
| `/trabajadores/:id` | Ficha del trabajador | Celular | RH la usa en computadora: a partir de 1024 px, dos columnas |
| `/mis-movimientos` | Mis movimientos de hoy | Celular | |
| `/compras/nueva` | Pedir una compra urgente | Celular | |
| `/compras/mias` | Mis solicitudes | Celular | La tabla de 768 px o más se conserva |
| `/v/:token` | Vale abierto desde su QR | Celular | Se abre con la cámara del teléfono |
| `/inventario` | Existencias | Computadora | Tarjetas en celular (ya existen) |
| `/reportes/movimientos` | Bitácora | Computadora | La bitácora por vale de FEAT-017 la reemplaza |
| `/seguimiento` | Piezas y resguardos | Computadora | El almacenista la abre en el celular (`resguardo.ver`): tarjetas, como hoy |
| `/entrada` | Dar entrada | Computadora | |
| `/catalogo/articulos`, `/catalogo/categorias` | Catálogo | Computadora | |
| `/puestos` | Puestos | Computadora | |
| `/etiquetas` | Etiquetas | Computadora | En celular descarga el PDF igual (UX-05) |
| `/trabajadores`, `/trabajadores/nuevo` | Lista y alta de trabajadores | Computadora | El alta debe poder tomar la foto con la cámara del celular |
| `/compras`, `/compras/:id` | Cola de Compras y detalle | Computadora | El detalle lo abre también quien pidió, desde el celular: una columna |
| `/reportes/existencias`, `/reportes/adeudos`, `/reportes/consumo` | Reportes | Computadora | |
| `/usuarios`, `/roles`, `/roles/:id` | Usuarios, roles y permisos | Computadora | |
| `/personal` | Personal por almacén | Computadora | |
| `/almacenes` | Almacenes | Computadora | |
| `/vales/:id` | Detalle de un vale | Computadora | A todo el ancho (D-16, FEAT-017). Desde el resultado de una entrega se abre en el celular: una columna |
| `/entradas/nueva`, `/importar` | Enlaces anteriores | No aplica | Redirigen a `/entrada` |
| `*` | No encontrada | Las dos | |
| `/dev/componentes` | Galería de componentes | No aplica | Solo fuera de producción |
| Rutas de FEAT-013 | Proyectos | Computadora | Las rutas las define FEAT-013 |
| Rutas de FEAT-016 | Inspecciones pendientes e inspección en lote | Celular | Diseñada para el almacenista (D-10) |
| Rutas de FEAT-018 | Deudores | Computadora | |
| Rutas de FEAT-020 | Equipos inscritos y conflictos de sincronización | Computadora | Las resuelve el supervisor |

#### Consideraciones

- La clase dice **dónde se diseña primero y dónde se prueba con más cuidado**. No prohíbe el otro dispositivo: toda pantalla funciona en los dos.
- La tableta (768 a 1023 px) usa el diseño de celular con dos columnas donde quepa (ui-ux, «Tableta»), sin menú lateral.
- Las pantallas de celular conservan la jerarquía de «Pensado para el mostrador»: texto de 16 px para los datos y alto contraste.

### D. Estética (UX-11 y UX-12)

| ID | Regla | Origen |
|---|---|---|
| UX-11 | **Plan de mejoras visuales.** Las mejoras de la lista de abajo se planean y se construyen como cambios chicos, uno por área, sin cambiar reglas ni flujos. Cada una se revisa con capturas antes y después a los tamaños de UX-09 y UX-10. No hay tema oscuro (excluido en [mvp-scope.md](../product/mvp-scope.md)) ni ilustraciones (excluidas en ui-ux): los estados vacíos usan un icono de trazo. | D-21 |
| UX-12 | **Consistencia visual que se puede verificar.** (1) Fechas, horas, números y moneda salen de **un solo módulo de formato** en español de México y con la hora del centro de México. (2) Los números en tablas y tarjetas van a la derecha y con `tabular-nums`. (3) Los encabezados siguen la escala de ui-ux: `h1` de 20 o 24 px; `h2` de 16 px, semibold, azul marino. (4) Una insignia de estado lleva siempre icono y texto. El semáforo (SM-02) se usa solo para el nivel de un renglón o de una pieza, y cada nivel lleva siempre su icono y su texto de la tabla. Un mismo estado tiene el mismo color en todas las pantallas. (5) Toda lista tiene esqueleto al cargar, vacío con icono, frase y acción, y error con «Reintentar». (6) El texto cumple contraste AA (4.5 a 1) y los iconos y bordes que dan información, 3 a 1. (7) Lo que se imprime o se descarga sale en blanco y negro legible, sin menús ni botones. | D-21; SM-02, ui-ux |

#### Lista de mejoras (UX-11), por área

Cada punto cita dónde se ve hoy.

**Toda la aplicación**

1. **Ancho del marco.** `max-w-6xl` (1152 px) en `componentes/navegacion/armazon-escritorio.tsx:139` pasa a depender de la clase de la pantalla (UX-08).
2. **Formato único.** Hoy hay dos módulos de fechas que hacen lo mismo:
   - `componentes/dominio/fechas.ts` (`formatearFecha`, `hoyMexico`);
   - `componentes/personas/formato.ts` (`fechaCorta`, `fechaHoraMx`, `hoyMx`).

   La moneda se formatea en tres lugares por separado:
   - `routes/consulta/articulo.tsx:182`;
   - `componentes/catalogo/tipos.ts:148`;
   - `componentes/tablero/pestana-valor.tsx:7`.

   Se juntan en `componentes/dominio/formato.ts`, con fecha, fecha y hora, «hace cuánto», número entero y moneda MXN (UX-12, punto 1).
3. **Encabezados `h2`.** Hay al menos seis variantes. Se dejan en la escala de ui-ux (16 px, semibold, marino). Ejemplos:
   - `text-xl` en `routes/inventario/etiquetas.tsx:192`;
   - `text-lg font-bold` en `routes/personas/trabajador-ficha.tsx:40` y `trabajador-nuevo.tsx:35`;
   - `text-lg font-semibold` en `componentes/catalogo/detalle-articulo.tsx:44` y `componentes/traspasos-lista/paso-archivo.tsx:98`;
   - `text-lg` en `componentes/entrega/paso-trabajador.tsx:146`.
4. **Estados vacíos con acción.** De unos 39 `EstadoVacio`, menos de la mitad ofrece una acción. Además hay vacíos escritos como párrafo suelto, sin icono ni acción:
   - «No encontramos nada con…» en `routes/inventario/etiquetas.tsx:168` (debe ofrecer «Borrar búsqueda»);
   - «Todavía no tiene ninguna inspección» en `routes/consulta/pieza.tsx:172`;
   - «No hay detalle por trabajador» en `routes/supervision/rep-consumo.tsx:33`.
5. **Esqueletos.**
   - Etiquetas carga la lista con el indicador en línea (`<Cargando>`), y no con el esqueleto de lista que pide ui-ux.
   - Entregar, Devolver y Trasladar usan `<Cargando>` en lugares donde la forma del contenido ya se conoce, como la ficha del trabajador y los renglones: ahí va el esqueleto.
6. **Contraste del amarillo.** El amarillo del semáforo (`#CA8A04`) da cerca de 2.9 a 1 sobre blanco. No llega a 3 a 1 como icono y tampoco alcanza para el icono blanco sobre el círculo amarillo de `componentes/dominio/renglon-semaforo.tsx:153`. Se propone conservar `#CA8A04` para la franja y el fondo al 10 %, y usar un tono más oscuro (`#A16207`, unos 4.9 a 1) para el icono y el texto en amarillo. Requiere cambiar la tabla del semáforo en ui-ux (ver «Decisiones abiertas»).

**Operación (celular)**

7. **Objetivos táctiles de 44 px.** Hay enlaces de 40 px en pantallas de celular:
   - `routes/consulta/pieza.tsx:92` y `:145`;
   - `routes/operacion/recibir-detalle.tsx:84`;
   - `componentes/consulta/bloques.tsx:31`;
   - `componentes/consulta/linea-de-tiempo.tsx:41`.
8. **Motivos de un traspaso.** `componentes/traspasos/motivos-vale.tsx` pinta el naranja con el triángulo y el texto «Aviso», y con el borde amarillo. Va contra la tabla del semáforo: el naranja es el candado y «Requiere autorización». Se alinea con `RenglonSemaforo`.
9. **Resultados de búsqueda.** Los resultados de Consultar y de las hojas «¿Cuál es?» de Entregar y Devolver se igualan:
   - la misma tarjeta de 48 px;
   - nombre en semibold;
   - una línea de apoyo con código, serie y dónde está (UX-04);
   - un icono por tipo: persona, herramienta o caja.

**Administración (computadora)**

10. **Columnas numéricas.** Van a la derecha con `tabular-nums` en las tablas que aún no lo hacen. Por ejemplo, la columna «Resumen» de `routes/acceso/almacenes.tsx` (existencias y usuarios) no tiene ni alineación ni cifras de ancho fijo.
11. **Encabezado de pantalla uniforme.** Título, una línea de apoyo, acción principal arriba a la derecha y, debajo, una sola barra con la búsqueda, los filtros visibles (UX-10) y «Descargar». Los reportes, Usuarios, Almacenes y la cola de Compras ya se acercan; Etiquetas e Inventario no.
12. **Insignias de compras.** Las dos familias de insignias de compras no coinciden:
   - Pendiente es azul en `componentes/compras/solicitar/insignias.tsx:13` y gris en `componentes/compras/atender/insignias.tsx:17`;
   - Urgente es azul marino en una y rojo de error en la otra.

   Así, la misma solicitud se ve distinta en «Mis solicitudes» y en la cola de Compras. Se deja una sola familia (ver «Decisiones abiertas»).

**Impresión y etiquetas**

13. **Alto de la hoja de 18.** La hoja de 18 de hoy usa celdas de 36 mm: las 6 filas suman 216 mm de 255 mm útiles y dejan unos 4 cm sin usar al pie. Las celdas pasan a 42 mm, con un QR más grande (sección B).
14. **Nombre del archivo.** El PDF del vale (FEAT-017) y el de las etiquetas comparten fuente, márgenes y estilo de nombre de archivo.

## Casos límite

| Situación | Qué pasa | Regla |
|---|---|---|
| Se escribe «a» y se espera | No sale ninguna petición; «Escribe al menos 2 letras o números». | UX-01 |
| Número de empleado propio de un carácter («7») y Enter | Se identifica exacto por `GET /api/escaneo/7`; si existe, abre al trabajador. No hay lista de texto. | UX-01 |
| La pistola dispara con el foco en el campo de búsqueda | La ráfaga y su Enter llegan antes de los 300 ms: no sale ninguna búsqueda a medias. Se identifica el código exacto y el campo se limpia. | UX-01 |
| La respuesta de «jua» llega después de la de «juan» | Se descarta: su texto no es el del campo. Se queda la lista de «juan». | UX-02 |
| La red es lenta (3 s por respuesta) | La lista anterior se queda atenuada y no se puede tocar. Se lee «Buscando…». Nada se elige por error. | UX-02 |
| «perez juan» con el trabajador registrado como «Juan Pérez López» | Lo encuentra: cada palabra está en el nombre, sin importar orden ni acentos. | UX-03 |
| Se busca la serie de una pieza con serie pendiente | No aparece por serie (no tiene). Aparece si se busca su código o el nombre del artículo. | UX-03, E-18 |
| Almacenista de Midrex busca una pieza que está en Kepler | No aparece, igual que hoy: está fuera de su alcance. La que tiene un trabajador sí aparece, con quién la tiene. | UX-03, AC-06 |
| Artículo retornable por cantidad (flexómetro) | El resultado dice «3 en Midrex · 5 con trabajadores»; sin costos. | UX-04 |
| «guantes» coincide con 300 artículos | Llegan 10, en orden de relevancia, con «Ver más» y el total. Nunca 300 de un jalón. | UX-04 |
| Una sola etiqueta | Un PDF de una hoja con una etiqueta en la posición 1 (o en la n.º N elegida). Las demás posiciones quedan en blanco. | UX-05, UX-06 |
| 500 etiquetas en formato de 18 | 28 hojas. Se ve el avance por hoja, la pantalla responde y se puede cancelar. El archivo se descarga al terminar. | UX-07 |
| 1200 etiquetas elegidas | No se arma. «Puedes descargar hasta 1000 etiquetas en un PDF. Quita 200 o descárgalas en dos partes.» | UX-07 |
| Nombre de artículo de 150 caracteres | Se corta con «…» en su número de renglones. El código y la serie se ven completos. | UX-07 |
| Código «ARNÉS/ALT-Ñ 01» | El QR contiene exactamente esa cadena y el texto la muestra igual. La pistola la lee tal cual. | UX-07, RG-10 |
| Código de 64 caracteres en formato de 30 | El QR quedaría con módulos de menos de 0.5 mm: aviso amarillo antes de descargar, sugiriendo 18 por hoja. Se puede descargar igual. | UX-07 |
| Importación de 900 piezas | El enlace del resultado lleva el lote, no los códigos. Las 900 llegan elegidas sin pasar por la URL. | UX-06 |
| Rango de alta sin trabajadores | Estado vacío: «Nadie se dio de alta entre esas fechas», con «Cambiar fechas». | UX-06 |
| Trabajador inactivo dado de alta dentro del rango | No aparece: las credenciales son de trabajadores no inactivos, como hoy. | UX-06 |
| Una tabla de computadora abierta en 360 px | Pasa a tarjetas, o se desliza de lado solo dentro de su contenedor; la página no. | UX-10 |
| El teclado del celular abierto en Entregar | La acción principal sigue a la vista sobre el teclado o queda accesible al cerrarlo, nunca tapada sin salida. | UX-09 |
| Celular en horizontal (640 × 360) | Entregar pone los renglones a la izquierda y la firma a la derecha (ui-ux). El pie fijo no tapa más de un tercio de la pantalla. | UX-09 |

## Fuera de alcance

- Impresión directa a impresoras térmicas (sigue excluida en [mvp-scope.md](../product/mvp-scope.md)), etiquetas en rollo, tamaños A4 u oficio y diseño libre de etiquetas.
- Copias de una misma etiqueta en un PDF. Se imprime dos veces o se elige un formato más grande.
- Código de barras lineal: solo QR.
- Búsqueda por voz, búsqueda difusa con errores de dedo («peres» por «pérez») e índice de texto completo (solo si lo pide la prueba de carga, en un ADR aparte).
- Tema oscuro, personalización de colores, ilustraciones y pantallas de bienvenida (excluidos en ui-ux y mvp-scope).
- Cambiar las reglas de alcance de las etiquetas (ver «Riesgos»).

## Criterios de aceptación

- Dado cualquier buscador de la tabla «Inventario de buscadores», cuando la persona escribe «juan» de corrido, entonces sale **una** petición, 300 ms después de la última tecla, y no una por letra (UX-01, UX-04).
- Dado un buscador con el texto «j», cuando se espera, entonces no hay petición y se lee «Escribe al menos 2 letras o números»; y cuando se oprime Enter, entonces solo se intenta la identificación exacta (UX-01).
- Dado el campo de búsqueda con foco, cuando la pistola lee un código de pieza, entonces la pieza se identifica sin que salga una búsqueda de texto a medias, y el campo queda limpio (UX-01).
- Dadas dos búsquedas seguidas, «jua» y «juan», cuando la respuesta de «jua» llega al final, entonces la pantalla muestra solo la de «juan» (UX-02).
- Dada una respuesta lenta, mientras llega, entonces la lista anterior está atenuada, no se puede tocar y se lee «Buscando…» (UX-02).
- Dado el trabajador «Juan Pérez López», cuando se busca «perez juan», «PEREZ» o una parte de su código de credencial, entonces aparece (UX-03).
- Dado un artículo con marca «Truper», cuando se busca «truper», entonces aparece (UX-03).
- Dada una pieza con serie pendiente, cuando se busca un texto que no es su código ni el nombre de su artículo, entonces no aparece; y cuando se busca su código, entonces sí (UX-03, E-18).
- Dado un almacenista sin `almacenes.todos`, cuando busca una pieza que está en otro almacén, entonces no aparece; y cuando la pieza la tiene un trabajador, entonces aparece con «En resguardo de <nombre>» (UX-03, UX-04, AC-06).
- Dado un artículo retornable por cantidad, cuando aparece en los resultados, entonces dice cuánto hay en el almacén del usuario y cuánto tienen los trabajadores, sin costo (UX-04).
- Dada una petición a `GET /api/busqueda` con `tamano=200`, entonces el servidor responde 422, porque el máximo de esa ruta es 50 (UX-04).
- Dadas 37 piezas elegidas en formato de 18, cuando se toca «Descargar PDF», entonces se descarga un solo archivo de 3 hojas carta. Cada QR mide 20 mm o más y contiene exactamente el código, con el nombre, el código y la serie legibles (UX-05).
- Dado el PDF de 30 por hoja impreso en papel común, cuando se lee cada etiqueta con la pistola y con la cámara de un celular, entonces todas se leen (UX-05).
- Dada la importación de 900 piezas, cuando se toca «Imprimir etiquetas de las piezas nuevas», entonces Etiquetas abre con las 900 elegidas (UX-06).
- Dado RH con `etiquetas.imprimir`, cuando elige «Dados de alta entre el 1 y el 8 de octubre», entonces quedan elegidas las credenciales de esas altas y nada más (UX-06).
- Dada la ficha de un artículo por pieza, cuando se toca «Etiquetas de sus piezas», entonces Etiquetas abre con todas sus piezas que no están de baja (UX-06).
- Dado «Empezar en la etiqueta n.º 7» en formato de 30, entonces la primera hoja del PDF deja las posiciones 1 a 6 en blanco (UX-06).
- Dadas 500 etiquetas, cuando se descarga el PDF, entonces la pantalla muestra el avance, responde y se puede cancelar, y el archivo pesa menos de 5 MB (UX-07).
- Dadas 1200 etiquetas elegidas, entonces «Descargar PDF» está deshabilitado con la nota del límite (UX-07).
- Dado un usuario sin `etiquetas.imprimir`, entonces no ve Etiquetas, y `GET /api/etiquetas` con cualquiera de los filtros nuevos responde 403 `SIN_PERMISO` (UX-06).
- Dada cada ruta «primero celular», a 360 × 640 y 412 × 915, entonces no hay desplazamiento horizontal de la página, todo lo que se toca mide 44 px o más y la acción principal está fija abajo (UX-08, UX-09).
- Dada cada ruta «primero computadora», a 1920 × 1080, entonces el contenido usa hasta 1600 px; y a 360 × 640, entonces se puede completar su tarea sin desplazamiento horizontal de la página (UX-08, UX-10).
- Dada cualquier pantalla con fechas o moneda, entonces salen en formato es-MX y con la hora del centro de México, del mismo módulo de formato (UX-12).
- Dada la misma solicitud de compra en «Mis solicitudes» y en la cola de Compras, entonces su insignia de estado y de urgencia se ven iguales (UX-12).
- Dado el semáforo amarillo, entonces su icono y su texto alcanzan 3 a 1 y 4.5 a 1 de contraste contra su fondo (UX-12).

## Módulos relacionados conocidos

- **Backend:**
  - `consulta`: `repository.py` (`buscar_articulos`, `buscar_piezas`, `buscar_trabajadores`), `service.py` (`buscar`), `router.py` (`GET /api/busqueda`) y `schemas.py` (`BusquedaArticuloItem`, `BusquedaPiezaItem`, `BusquedaTrabajadorItem`).
  - `catalogo`: `router.py` y `service.py` (`listar_etiquetas`), y el repositorio de etiquetas (`piezas`, `estantes`, `credenciales`).
  - `core/paginacion.py`: tope por ruta.
- **Frontend, búsqueda:**
  - `componentes/ui/campo-busqueda.tsx` y `componentes/catalogo/usar-consulta.ts` (`useRetraso`, `useConsulta`);
  - `componentes/dominio/escaner.tsx`;
  - todas las pantallas del inventario de buscadores;
  - `api/practica.ts`.
- **Frontend, etiquetas:** `routes/inventario/etiquetas.tsx`, `componentes/dominio/hoja-etiquetas.tsx`, `credencial.tsx`, `credencial-medidas.ts`, `credencial-png.ts`, `codigo-qr.tsx`, `estilo-impresion.tsx` y `componentes/importacion/resultado-importacion.tsx`.
- **Frontend, diseño:**
  - `componentes/pantalla.tsx`, `componentes/navegacion/armazon-escritorio.tsx` y `armazon-movil.tsx`;
  - `componentes/reportes/marco-reporte.tsx` y `componentes/ui/hoja-filtros.tsx`;
  - `app.css` (tokens de color);
  - los módulos de formato que se juntan: `componentes/dominio/fechas.ts`, `componentes/personas/formato.ts` y los formateadores de moneda citados.
- **FEAT-017:** comparte jsPDF, la fuente y el estilo de nombre de archivo, y aporta `vale.lote_id`.
- **FEAT-020:** descarga de archivos dentro de la app de Android.

## Cambios de datos o API esperados

- **Sin migraciones.** No hay tablas ni columnas nuevas. El origen «piezas de una importación» usa `vale.lote_id`, que crea FEAT-017.
- **`GET /api/busqueda`:**
  - busca por palabras, por marca y por código de credencial;
  - ordena por relevancia (UX-03);
  - `tamano` por omisión 10 y máximo 50.
  - Campos nuevos, sin quitar los existentes:

    | Grupo | Campos nuevos |
    |---|---|
    | `articulos` | `retornable`, `en_almacen` (lo del almacén del usuario, o de todos con `almacenes.todos`) y `con_trabajadores` (solo en retornables) |
    | `piezas` | `ubicacion_texto`, con el texto de C-13 |
    | `trabajadores` | `puesto`, `vigencia` `{vigente, texto}` y `credencial` (el código que coincidió, si fue por credencial) |

  - `ubicacion` se conserva por compatibilidad.
- **`GET /api/escaneo/{codigo}`:** sin cambio.
- **`GET /api/etiquetas`:** filtros opcionales nuevos, que se pueden combinar con `tipo`:
  - `articulo_id` (solo `piezas`);
  - `lote_id` (solo `piezas`);
  - `alta_desde` y `alta_hasta` (solo `credenciales`; fechas de México sobre `trabajador.creado_en`).

  Un filtro que no corresponde al tipo es 422. Sigue sin paginar y con `etiquetas.imprimir`.
- **`GET /api/trabajadores?q=`:** `q` busca por palabras, igual que UX-03.
- Se actualiza [api-contracts.md](../architecture/api-contracts.md) (Escaneo y búsqueda, Trabajadores y Etiquetas) en el mismo cambio.

## Restricciones y compatibilidad

- Las reglas viven en el servidor. La interfaz solo decide **cuándo** preguntar (espera, mínimo, Enter). **Qué** coincide y qué se puede ver lo decide `GET /api/busqueda`.
- El escáner (`Escaner`) no cambia su detección de la pistola ni su ventana de repetidos de 1.5 s. El buscador reutiliza su regla de ráfaga.
- Las pantallas que hoy pasan `almacen_id` (Trasladar, TR-11) lo siguen pasando.
- El QR sigue conteniendo exactamente el código registrado (RG-10). Ninguna etiqueta lleva costos, CURP ni NSS (RG-12, RG-13).
- La credencial en PNG y su hoja de 8 no cambian de diseño: solo se agrega su descarga en PDF.
- jsPDF se carga bajo demanda: la primera carga de la aplicación no crece.
- Los textos nuevos van en español llano.

## Riesgos

- **Descarga en la app de Android.** En el WebView de Capacitor, un enlace de descarga a un archivo armado en el navegador no siempre guarda el archivo. Hace falta guardar con el sistema de archivos del teléfono y ofrecer «Compartir», con los complementos que defina FEAT-020. Mientras tanto, en la app se ofrece «Compartir PDF» o se avisa que la descarga se hace desde la computadora. De inicio, el almacenista no tiene `etiquetas.imprimir`, así que el impacto es bajo.
- **Fuente en el PDF.** jsPDF necesita la fuente en TTF y el proyecto trae Poppins solo en WOFF (`@fontsource/poppins`). Hay que incluir los TTF (licencia OFL) en `frontend/public/` o usar Helvetica, que trae jsPDF. Se decide junto con FEAT-017.
- **Peso del PDF.** Un QR dibujado módulo por módulo pesa mucho. Unir módulos por fila lo baja; la prueba de 500 etiquetas fija el tope de 5 MB.
- **Búsqueda por palabras más lenta.** Varios `LIKE '%…%'` unidos con «y» recorren la tabla. Con los volúmenes del reto no se nota; la prueba de carga decide si hace falta el índice de texto completo.
- **Alcance de las etiquetas.** `GET /api/etiquetas?tipo=piezas` lista las piezas de **todos** los almacenes sin aplicar AC-06. Esta feature no lo cambia, pero el filtro por artículo hace más visible que un usuario de un almacén imprima etiquetas de piezas de otro. Ver «Decisiones abiertas».
- **Muchos archivos tocados.** La migración de buscadores toca unas veinte pantallas. Se hace por pantalla, con su prueba, y no en un solo cambio grande.
- **Cambiar el amarillo.** Ajustar el tono del icono amarillo toca un color reservado del semáforo. Se cambia en ui-ux y en `app.css` a la vez, y se revisan las capturas del tutorial (FEAT-010).

## Validaciones requeridas

- `uv run pytest`, `uv run ruff check .`, `pnpm typecheck` y `pnpm build`.
- Una prueba por regla del servidor, con el ID en el nombre:
  - `test_ux03_busca_por_palabras_en_cualquier_orden`;
  - `test_ux03_sin_acentos_ni_mayusculas`;
  - `test_ux03_por_codigo_de_credencial`;
  - `test_ux03_por_marca`;
  - `test_ux03_serie_pendiente_no_por_serie`;
  - `test_ux03_respeta_alcance`;
  - `test_ux04_texto_de_ubicacion_y_cantidades`;
  - `test_ux04_tamano_maximo`;
  - `test_ux06_etiquetas_por_articulo`, `test_ux06_etiquetas_por_lote` y `test_ux06_credenciales_por_rango_de_alta`;
  - `test_ux06_filtro_que_no_corresponde_al_tipo`.
- Prueba del gancho `useBusquedaDiferida` (espera, mínimo, Enter, cancelación y descarte de respuestas viejas), si el frontend ya tiene pruebas; si no, recorrido manual documentado.
- PDF: abrir el de 1, 37 y 500 etiquetas en cada formato. Imprimir en papel carta común una hoja de cada formato y leer **todas** las etiquetas con la pistola y con la cámara del celular. Anotar las que fallen.
- Recorrido de cada ruta de la tabla de clasificación a 360 × 640, 412 × 915, 1366 × 768 y 1920 × 1080, con capturas antes y después de las mejoras de UX-11.
- Revisión de contraste del semáforo y de las insignias con una herramienta de contraste.
- La prueba de integración del guion del PDF sigue pasando.

## Documentos globales que podrían actualizarse

- [reglas-de-negocio.md](../product/reglas-de-negocio.md):
  - C-06 (amplía qué encuentra);
  - nota en E-18 (la credencial también se encuentra por parte de su código);
  - una sección corta con UX-01 a UX-07, que son reglas de servidor y de comportamiento.
- [api-contracts.md](../architecture/api-contracts.md): `GET /api/busqueda`, `GET /api/trabajadores` y `GET /api/etiquetas`.
- [ui-ux.md](../product/ui-ux.md):
  - «Objetivos táctiles» (44 px en pantallas de celular);
  - «Navegación» y «Navegación por ancho» (clases y anchos de UX-08);
  - «Hoja de filtros» y «Patrón de reporte» (filtros visibles desde 1280 px);
  - «Impresión» y «Reportes y etiquetas» (PDF, formatos y orígenes);
  - el semáforo (tono del icono amarillo);
  - las insignias de compras (una sola familia);
  - la frase «todas las búsquedas usan `useRetraso`» (pasa a `useBusquedaDiferida`).
- [app-flow.md](../product/app-flow.md):
  - Flujo 12 (Consultar con lista mientras se escribe);
  - Flujo 16 (Etiquetas: formato, origen, PDF);
  - «Pantallas del MVP», con la clase de cada ruta.
- Un ADR nuevo, compartido con FEAT-017, si se aprueba jsPDF: «PDF armado en el navegador».

## Decisiones abiertas

1. **Dependencia jsPDF.** Se propone la misma que FEAT-017, cargada bajo demanda. Requiere tu aprobación (AGENTS.md, «Agregar dependencias»).
2. **Fuente del PDF.** Se propone Poppins en TTF dentro de `frontend/public/` (unos 300 KB por dos pesos), para que el PDF se vea como la aplicación. La alternativa es Helvetica, sin peso extra.
3. **Formato de 30 igual a las hojas adhesivas comerciales.** Se propone la geometría de 1 × 2⅝ in, con los márgenes exactos de esas hojas, para imprimir directo en adhesivo. Falta confirmar con el track qué hojas compran, si es que compran.
4. **Amarillo del semáforo.** Se propone `#A16207` para el icono y el texto, y `#CA8A04` para la franja y el fondo. Cambia la tabla de ui-ux.
5. **Insignias de compras.** ¿Cuál familia se queda? Se propone la de la cola de Compras: Pendiente en gris, Urgente con rayo en rojo de error. Es la que distingue lo urgente con más fuerza.
6. **Filtros visibles en computadora.** Se propone mostrarlos en una barra superior desde 1280 px. Cambia el «Patrón de reporte», que hoy los pone en la hoja en todos los tamaños.
7. **«Dados de alta en un rango».** Se propone `trabajador.creado_en` (el alta en el sistema). Un reingreso no cuenta como alta. ¿Debe contar el inicio de un periodo nuevo?
8. **Alcance de las etiquetas de piezas.** Hoy no se limita al almacén del usuario. ¿Se deja así, porque una etiqueta solo lleva código y nombre, o se aplica AC-06 como en la búsqueda?

## Orden de construcción sugerido

1. **Servidor de búsqueda (UX-03, UX-04)**, con sus pruebas. No cambia la interfaz y deja listo el contrato.
2. **`useBusquedaDiferida` y `CampoBusqueda` (UX-01, UX-02)**, y migrar primero Consultar, Entregar y Devolver: es lo que se ve en la demostración.
3. **Resto del inventario de buscadores**, una pantalla por cambio.
4. **Etiquetas en PDF (UX-05 a UX-07)**, después de que FEAT-017 decida jsPDF y la fuente, y después de `vale.lote_id`.
5. **Clases y anchos (UX-08 a UX-10)**: el `handle` de cada ruta, el ancho del marco y la barra de filtros.
6. **Mejoras estéticas (UX-11, UX-12)**: primero el módulo de formato, los encabezados y los estados vacíos; al final el contraste y las insignias, que dependen de las decisiones 4 y 5.
