# Flujos de usuario por rol y guion de la prueba

Propuesta ligada a [FEAT-011](../features/FEAT-011-entrada-por-kepler-trazabilidad-y-menu.md). Describe lo que cada rol hace de principio a fin, con el camino normal y los caminos alternos, y cómo se cubre cada paso de la prueba del PDF. **Complementa a [app-flow.md](app-flow.md)** (que sigue siendo la fuente de las pantallas actuales); aquí se marca con **[NUEVO]** lo que FEAT-011 cambia o agrega, y se ordena por persona, no por pantalla.

Las reglas se citan por su ID de [reglas-de-negocio.md](reglas-de-negocio.md). Los códigos de ejemplo son ilustrativos.

## 1. La red de almacenes

```
Proveedor ──> KEPLER (central) ──> CONTRATISTAS (subalmacén) ──> Midrex · HYL · Laminador · Minas
                entrada solo aquí      aquí empieza la entrega        entrega de herramienta
                [NUEVO]                a trabajadores (EPP)            y devolución al mismo almacén
```

- **Todo movimiento entre almacenes es un traspaso.** Se puede armar escaneando o con una lista de Excel.
- **Solo Kepler recibe de fuera.** Entrada de proveedor e importación van a Kepler **[NUEVO, EK-01]**.
- **Ruta habitual:** Kepler a Contratistas, y Contratistas a cada proyecto; el regreso va por la misma cadena (X-03). Otra ruta solo la hace quien tiene `almacenes.todos`, con observación.
- **El EPP se entrega en Contratistas** y la herramienta especializada en el almacén del proyecto; no es una regla del sistema, se logra por cómo se surten los almacenes (FEAT-011, sección E).

## 2. Quién hace qué

| Rol | Hace | No hace |
|---|---|---|
| **Almacenista** | Entregar, devolver, consultar, inspeccionar, no adeudo, pedir compra urgente, ver «quién tiene qué» de su almacén **[NUEVO]**, recibir traspasos **[NUEVO, configurable]** | Enviar traspasos, autorizar, cambiar límites, ver datos personales |
| **Supervisor** | Todo lo del almacenista, más enviar y recibir traspasos, autorizar excesos con PIN, ver la bitácora de su almacén **[NUEVO]**, reportes de su almacén, asignar personal | Cambiar límites de entrega **[NUEVO]**, administrar roles |
| **Compras** | Dar entrada a Kepler **[NUEVO: solo Kepler]**, importar inventario, catálogo y costos, atender solicitudes de compra | Ver trabajadores, entregar |
| **RH** | Alta, reingreso y baja de trabajadores, datos personales, adeudos, ver el vale de no adeudo **[NUEVO]** | Ver herramientas ni existencias |
| **Administrador** | Todo, y es el único con `almacenes.todos`: elige el almacén en que opera y envía por rutas excepcionales con observación | No es un rol del reto: existe solo para el control de los almacenes |

Quién **recibe** traspasos es un permiso (`traspasos.recibir`) que se cambia en `/roles`: de inicio, Supervisor y Almacenista **[NUEVO, AC-34]**.

## 3. Flujos del Almacenista

### 3.1 Entregar (la prueba del PDF, paso 2)

1. Entra y toca **Entregar** en «Lo que haces hoy».
2. **Trabajador:** escanea la credencial, teclea el número o busca por nombre. Ve la ficha breve (sin CURP ni NSS).
   - *Alterno:* trabajador de baja o contrato vencido, rojo y no avanza (E-02, T-02, T-03).
   - *Alterno:* «No es esta persona», regresa a buscar.
3. **Artículos:** escanea uno tras otro. Cada lectura es un renglón con semáforo; nada se descuenta hasta confirmar (E-28).
   - *Verde:* correcto. *Amarillo:* aviso (por ejemplo, fuera de la dotación del puesto, E-09; se pide el motivo).
   - *Naranja:* excede un límite; pide autorización del supervisor (ver 3.2).
   - *Rojo:* no se puede (sin existencia en este almacén, E-03; pieza no apta o vencida, E-05; pieza ajena). «Continuar» queda deshabilitado hasta quitarlo.
   - Herramienta por cantidad: se suma la cantidad; por pieza: se escanea cada pieza, con su serie.
   - *Alterno:* **Dotación sugerida** carga lo que corresponde al puesto del trabajador.
   - *Alterno:* **Deshacer** durante 5 segundos o **Quitar** un renglón.
4. **Firma:** el trabajador firma con el dedo. Se pide el motivo si hubo aviso.
5. **Confirmar entrega:** sale el vale con folio y QR. *Alterno:* **Imprimir**, **Nueva entrega**.
6. **Después:** lo entregado queda ligado al trabajador. **[NUEVO]** Se ve en Seguimiento (pestaña Por cantidad, o Piezas si lleva serie) y en la ficha del trabajador (SG-01, SG-02).

### 3.2 Pedir autorización (exceder un límite; PDF, paso 3)

1. Un renglón en naranja (por ejemplo, 4 guantes cuando el límite es 3 por semana, L-03).
2. El almacenista toca **Pedir autorización**. Se crea una solicitud para el supervisor.
3. El supervisor la resuelve con su PIN, en su equipo o a distancia (flujo 7). *Caminos:* autoriza, rechaza o vence.
4. Con autorización el renglón pasa a verde y el vale queda firmado también por el supervisor (F-04).

### 3.3 Devolver

1. Toca **Devolver**. Escanea la pieza (muestra artículo y titular) o la credencial (lista lo que el trabajador tiene).
2. Elige la **condición**: Bueno, Desgaste por uso o Dañado. *Dañado* exige observación y admite foto (V-05, V-06); no se cobra.
3. **Confirmar devolución:** vale con folio.
   - *Alterno:* se devuelve en un almacén distinto del de salida: se acepta con aviso (V-07); el titular sigue siendo responsable (V-01).
   - *Alterno:* equipo que no es de la empresa, en rojo «No es de la empresa» (V-12).
   - Los consumibles no regresan (E-21).

### 3.4 Consultar y rastrear

1. **Consultar:** escanea o escribe. Ve ficha de trabajador, pieza, artículo o vale, con atajos a la acción siguiente.
2. **[NUEVO] ¿Quién lo tiene?:** desde Inventario > Piezas y resguardos o la tarjeta «Alto valor fuera del almacén» del inicio. Busca por serie, nombre o artículo; cada fila lleva a la pieza o al trabajador y a su vale (SG-04).
3. **[NUEVO] Línea de tiempo de una pieza:** cada movimiento con quién la entregó, a quién, vale, fecha, condición y almacén (SG-03).

### 3.5 Recibir un traspaso (si tiene `traspasos.recibir`)

1. **Recibir traspaso**, abre el traspaso en camino. Ve su avance.
2. **Recibir todo** o marcar renglón por renglón (con − y +, o escaneando). En listas largas hay búsqueda y filtros (Pendientes, Todos, Con diferencia).
3. **Confirmar recepción.** Lo no marcado queda como diferencia, con observación (X-10 a X-13, RG-14).
4. **[NUEVO]** Queda en la bitácora de este almacén como entrada y en la del emisor como salida (SG-05).

## 4. Flujos del Supervisor

Hace todo lo de 3 y además:

### 4.1 Enviar un traspaso (la prueba del PDF, paso 4)

1. **Traspasos > Enviar.** Elige el **destino** (solo rutas habituales, X-03).
2. **Armar la lista**, de dos maneras:
   - *Escaneando o buscando:* **[NUEVO]** solo aparece lo que hay en el origen, con la cantidad disponible (TR-11).
   - *Con una lista de Excel:* descarga la plantilla, la llena, la sube. **[NUEVO]** La vista previa aparece sola, paginada de 12 en 12 (TR-12).
3. Cada fila sale correcta, con aviso o con error:
   - Rojo: no hay suficiente en el origen o la pieza no está (X-02), código inexistente, almacén cerrado (AL-04).
   - Amarillo: pieza no apta (X-04).
   - Si hay filas en rojo no se guarda nada (RG-09), salvo **Dejar fuera las filas con error**.
4. **Confirmar traspaso.** Sale un vale con folio y QR. La mercancía queda **en tránsito** hasta que el destino la reciba.
   - *Alterno:* ruta distinta de la habitual: lo rechaza el servidor (403), salvo el Administrador.

### 4.2 Autorizar y vigilar

- **Autorizaciones:** resuelve solicitudes con PIN (3.2). Ve las pendientes de su almacén.
- **[NUEVO] Bitácora del almacén:** todo lo que sale, llega y entra, con quién, qué y cuándo; filtros por pieza, serie, trabajador y fechas (SG-05). Ve también los reportes de existencias, movimientos, adeudos y consumo de su almacén.
- **Personal por almacén:** trae a su almacén o libera a quien no tiene uno (AC-12, AC-13).
- **Cancelar un vale** de su almacén (V-xx, flujo 14).

## 5. Flujos de Compras

### 5.1 Dar entrada [NUEVO: solo Kepler]

1. **Inventario > Dar entrada.** No hay selector de almacén: dice «Entra a Kepler» (EK-01, EK-03).
2. Elige el método:
   - **A mano:** escanea o busca, captura cantidades; para piezas, código, marca y serie, y la inspección inicial (I-02, I-03).
   - **Desde Excel:** sube el archivo. Se ve la vista previa paginada, con estados Nuevo, Existente, Unido y Error. *Alta* crea artículos nuevos (pide también `catalogo.administrar`); *Reposición* solo suma a lo que existe.
3. **Confirmar:** un vale de entrada en Kepler. Ofrece imprimir las etiquetas de las piezas nuevas.
4. Para llegar a un proyecto, la mercancía debe **pasar por traspaso** (4.1).

### 5.2 Catálogo y solicitudes

- **Catálogo** (pestañas Artículos, Categorías, Puestos, Etiquetas): define si un artículo es por cantidad o por pieza, sus límites (con `catalogo.limites`) y costos (con `catalogo.costos`).
- **Solicitudes de compra** (flujos 19 y 20): el supervisor o almacenista pide una compra urgente; Compras la toma, la marca comprada y la ingresa. **[NUEVO]** El vale de entrada queda en Kepler y el almacén que la pidió la recibe después por traspaso (EK-05).

## 6. Flujos de RH

### 6.1 Alta de un trabajador (PDF, paso 1)

1. **Trabajadores > Nuevo.** Captura nombre, puesto, contrato y vigencia, y datos personales (CURP, NSS: solo RH los ve, RG-13). Foto opcional.
2. El sistema genera el **número de empleado** (T-10) y ofrece la **credencial** con QR.
   - *Alterno:* reingreso de quien ya estuvo, por CURP: conserva el historial y los adeudos.

### 6.2 Baja y vale de no adeudo (PDF, paso 5)

1. **Iniciar la baja** (RH, supervisor o almacenista). El sistema muestra los **pendientes**: piezas y cantidades que el trabajador todavía tiene (B-01 a B-03).
2. *Con pendientes:* no se emite el no adeudo hasta devolverlos o resolverlos (B-04 a B-09).
3. *Sin pendientes:* se emite el **vale de no adeudo**. **[NUEVO]** RH puede abrirlo (`vales.ver`).
4. El trabajador queda inactivo hasta que RH lo reingrese (T-02).

## 7. Flujos del Administrador

- **Personas y accesos [NUEVO]:** crea usuarios (rol, almacén, contraseña y PIN), cambia el almacén de alguien, restablece contraseña y PIN. Ve la lista «Sin almacén».
- **Roles y permisos:** crea y edita roles, activa permisos por grupo. Cambios aplican en la siguiente petición (AC-10). **[NUEVO]** El Administrador no puede quitarse `almacenes.todos` ni `almacenes.administrar` (AC-26), y volver a correr el seed no pisa lo editado (AC-27). Aquí se decide quién **recibe** traspasos (AC-28).
- **Almacenes:** alta, edición, inactivar y reactivar. **[NUEVO]** El servidor valida que un proyecto dependa de un subalmacén (EK-06).
- **Operar como cualquier almacén:** elige el almacén de origen en Entregar, Devolver y Trasladar.
- **Ruta excepcional:** envía de Kepler a un proyecto con una observación obligatoria; queda auditado (X-03).

## 8. La prueba del PDF paso a paso

| # | Paso del PDF | Quién | Dónde | Reglas | Cómo comprobarlo |
|---|---|---|---|---|---|
| 1 | Registrar un trabajador | RH | 6.1 | T-10, RG-13 | Queda con número de empleado; la credencial se imprime |
| 2 | Surtirle EPP y una herramienta por escaneo | Almacenista (Contratistas) | 3.1 | E-03, E-20, E-21 | Vale con folio; el trabajador tiene la herramienta en resguardo |
| 3 | Exceder un límite | Almacenista + supervisor | 3.2 | L-03, A-xx | Renglón naranja; solicitud; autoriza con PIN; el vale lleva la firma del supervisor |
| 4 | Traspaso entre almacenes | Supervisor (Contratistas a Midrex) y quien reciba | 4.1 y 3.5 | X-02, X-03, X-10 a X-13 | Tránsito, recepción, diferencia anotada; queda en la bitácora de los dos almacenes |
| 5 | Mostrar pendientes al procesar la baja | RH | 6.2 | B-01 a B-09 | Lista de lo que debe; sin pendientes se emite el no adeudo |
| + | Equipo de alturas (arnés, bandola) | Almacenista | 3.1 | I-02, I-03, E-05 | Una pieza no apta o con inspección vencida sale en rojo y no se entrega |

## 9. Guion de demostración (propuesta)

Orden pensado para que cada persona presente su rol y el recorrido se vea de corrido. Se cronometra en los ensayos.

1. **Preparación** (antes): base vacía sembrada con datos de ejemplo; Kepler con la mercancía cargada por **Dar entrada** (Compras); etiquetas QR pegadas en objetos reales; dos celulares y una computadora.
2. **Compras:** da entrada del Excel a Kepler (5.1) y muestra que llega por traspaso al resto.
3. **Supervisor:** envía de Kepler a Contratistas y de Contratistas a Midrex (4.1); el almacenista de Midrex recibe (3.5). Se ve la bitácora de ambos lados.
4. **RH:** registra un trabajador y emite la credencial (6.1).
5. **Almacenista:** entrega EPP y herramienta por escaneo (3.1), excede un límite (3.2) y el supervisor autoriza.
6. **Almacenista:** devuelve una herramienta dañada (3.3) y consulta «quién tiene» un detector de gases (3.4).
7. **RH:** inicia la baja y muestra los pendientes (6.2); se devuelve lo que falta y se emite el no adeudo.
8. **Administrador:** muestra roles y permisos: quita `traspasos.recibir` al almacenista y se ve el cambio al instante (AC-10, AC-34).
9. **Cierre:** el tutorial (FEAT-010) para un almacenista nuevo.

## 10. Caminos de error que conviene tener ensayados

| Situación | Resultado esperado |
|---|---|
| Artículo sin existencia en el origen | Rojo X-02, no se confirma |
| Excel con filas en error | Nada se guarda, salvo «Dejar fuera las filas con error» |
| Mismo Excel dos veces | Aviso «este archivo ya se usó» |
| Más de 500 renglones | Se rechaza y se pide dividir |
| Entrada a un almacén que no es Kepler | El servidor la rechaza **[NUEVO]** |
| Trabajador de baja | Rojo, no se entrega |
| Pieza vencida | Rojo, no se entrega |
| Supervisor sin PIN válido | No se autoriza |
| Rol sin permiso | La opción no aparece y el servidor responde 403 |
| Sin conexión | Banda «Sin conexión»; nada se da por guardado |
