# Track 3 — Reto IMHOTEP: control de herramientas y equipo de protección personal

## Fuente y método

Transcripción y organización del contenido visible en `HackaItlacTrack3_2026.pdf`, documento escaneado de 10 páginas. Se revisó visualmente cada página porque el PDF no contiene una capa de texto legible. Se conservan requisitos, ejemplos, pasos, campos de formularios, porcentajes, precios y mensajes de las infografías. Los datos de las páginas 5 y 10 se presentan como ejemplos y cotizaciones mostrados en el material.

## Propuesta de trabajo para los equipos participantes

### El desafío

Desarrollar un prototipo web que permita saber qué herramientas y equipo de protección personal (EPP) hay en cada almacén, qué artículos tiene asignados cada trabajador y qué debe devolver cuando termina su relación laboral.

El sistema deberá permitir capturar entregas y devoluciones mediante QR o código de barras, usando un celular o una pistola lectora. La captura debe ser rápida: identificar al trabajador, escanear los artículos, revisar las reglas de entrega y generar un vale con folio y responsable.

### Operación que deberá representar el prototipo

IMHOTEP cuenta con un almacén central en Kepler y un almacén en la colonia de Contratistas, dentro de Mittal. Este último surte a los almacenes de área de Midrex, HYL, Laminador y Minas. El prototipo debe registrar existencias y traspasos sin perder el historial de origen y destino.

### Funciones indispensables para la demostración

1. Acceso con usuario y contraseña, con perfiles de almacenista, supervisor, Compras y Recursos Humanos.
2. Catálogo de trabajadores, artículos y almacenes.
3. Identificación del trabajador y lectura de QR o código de barras del artículo.
4. Registro de entregas, devoluciones y traspasos, con fecha, cantidad, almacén y usuario responsable.
5. Consulta de existencias por almacén y de artículos asignados a cada trabajador.
6. Límite de entrega por artículo: si se supera, bloquear la operación hasta que un supervisor la autorice.
7. Al iniciar la baja de un trabajador, mostrar sus herramientas y equipos pendientes de devolución.
8. Reportes de existencias, movimientos y adeudos.

### Caso especial: equipo para trabajo en alturas

El arnés, la bandola y el gancho doble de vida deberán identificarse por pieza, con un código único. Antes de entregarlos, el sistema deberá mostrar su estado e inspección; si el equipo está marcado como no apto, deberá impedir la entrega. Los consumibles, como guantes o discos, podrán capturarse por producto y cantidad.

### Prueba que presentará cada equipo

Durante la demostración se entregarán datos de ejemplo. El equipo deberá registrar un trabajador, surtirle EPP y una herramienta mediante escaneo, intentar una entrega que exceda el límite, registrar un traspaso entre almacenes y mostrar los artículos pendientes al procesar su baja. Así podremos comprobar el funcionamiento completo, no solo las pantallas.

### Entregables

- Prototipo funcional accesible desde celular y computadora.
- Usuarios de prueba para cada perfil.
- Código fuente e instrucciones para instalar o desplegar el sistema.
- Descripción breve de la estructura de datos, respaldos y controles de acceso.
- Guía corta para el almacenista: entregar, devolver, trasladar y consultar.

### Evaluación sugerida

| Criterio | Peso |
|---|---:|
| Funcionamiento de entregas, devoluciones, traspasos y existencias | 35 % |
| Captura rápida con QR o código de barras | 20 % |
| Reglas de entrega, autorizaciones y baja de trabajadores | 15 % |
| Facilidad de uso en celular y computadora | 15 % |
| Seguridad, trazabilidad y posibilidad de implementación | 15 % |

## Infografía: proceso de contratación y entrega de vale de EPP

**Título:** Proceso de contratación y entrega de vale de EPP.  
**Lema:** Personas seguras, proyectos fuertes.

La infografía incluye además: “Nuestro talento también mantiene en movimiento a México” y “Mantenimiento industrial para un México más fuerte”.

### Pasos del proceso

1. **Solicitud de personal**
   - Área solicitante: puesto, obra y fecha.
   - Se genera la necesidad de personal para el proyecto.

2. **Selección y documentos**
   - Recursos Humanos (RH): identificación oficial, CURP, RFC, NSS, comprobante de domicilio y datos bancarios.
   - Se revisa la documentación completa del candidato.

3. **Alta y contrato**
   - RH: contrato firmado, alta IMSS antes de iniciar labores y expediente del trabajador.
   - Se formaliza la relación laboral conforme a la ley.

4. **Inducción de seguridad**
   - Seguridad: riesgos del puesto, uso y cuidado del EPP y evidencia de capacitación.
   - El trabajador conoce los riesgos y las medidas de control.

5. **Definir EPP por puesto y talla**
   - Seguridad y supervisor: casco, lentes, guantes, botas, chaleco, protección auditiva y respiratoria según riesgo.
   - Se determina el EPP necesario de acuerdo con la evaluación de riesgos.

6. **Preparar vale de EPP**
   - Almacén registra folio, fecha, trabajador, obra, artículo, cantidad, talla y estado.
   - Se genera el vale con la información requerida.

7. **Entrega física y revisión**
   - Trabajador y almacén comprueban que los artículos correspondan al vale y verifican tallas y estado.
   - Se entregan los artículos y se revisa que estén completos y en buen estado.

8. **Firmas y archivo**
   - El trabajador recibe y se compromete al uso del EPP.
   - Almacén entrega; supervisor valida.
   - Se guarda copia del vale en el expediente y el registro de inventario.
   - Se formaliza la entrega y se conserva el respaldo.

9. **Reposición y devolución**
   - Registrar daño, desgaste, pérdida o baja.
   - Generar nuevo movimiento en el vale de EPP.
   - Se mantiene el control del EPP durante toda la relación laboral.

### Ejemplo de vale de EPP

Campos del formato: folio, fecha, trabajador, NSS, puesto, obra; tabla con EPP, cantidad, talla y estado; y firmas o espacios para “Entregó”, “Recibió” y “Validó”.

Mensajes de la infografía:

- “No iniciar actividades sin alta e inducción; EPP según evaluación de riesgos.”
- “Cuidarnos hoy mantiene la industria de mañana.”
- “Mantenimiento industrial IMHOTEP México.”
- “Personas | Seguridad | Productividad | Continuidad.”
- “Un entorno seguro, hace grandes proyectos.”

## Entrega y control de herramientas y equipo para trabajo en alturas

### Flujo de entrega y devolución de herramientas

1. **Solicitud autorizada:** el supervisor indica trabajador, obra, tarea y periodo de uso.
2. **Preparación de herramientas en almacén:** se preparan las herramientas solicitadas. Los ejemplos ilustrados son minipulidor, martillo de bola, cincel, llaves mixtas, flexómetro, extensiones eléctricas y discos de corte.
3. **Revisión de herramientas:** verificar inventario; revisar código o serie, cantidad y estado; comprobar guardas y cable del minipulidor; verificar que las extensiones eléctricas estén íntegras; asegurar que los discos sean compatibles y no tengan daño; retirar piezas defectuosas. La ilustración señala “Guarda” y “Cable en buen estado”.
4. **Selección y revisión de equipo de alturas:** seleccionar arnés de Kevlar o poliéster según la tarea; incluir bandola y gancho doble de vida; revisar etiquetas, costuras, cintas, herrajes, conectores e historial de inspección; retirar equipo dañado. La ilustración identifica arnés de Kevlar, arnés de poliéster, bandola y gancho doble de vida.
5. **Entrega e instrucción:** el trabajador verifica herramientas y equipo, recibe instrucciones de uso, anclaje y reporte de daños, y debe contar con autorización de seguridad para trabajo en alturas. Mensaje destacado: “Uso correcto, anclaje, reporte de daños”.
6. **Vale y firmas:** registrar folio, fecha, trabajador, obra, descripción, cantidad, identificación (código o serie), estado y fecha prevista de devolución. Firman almacén, trabajador y supervisor.
7. **Devolución y cierre:** contar e inspeccionar herramientas y equipo; registrar consumo de discos, devoluciones, daño o pérdida; actualizar inventario.

Advertencia del material: “Sin inspección, capacitación y autorización, no usar el equipo de alturas”. También aparece el lema “La seguridad también se entrega”.

### Vale de resguardo de herramientas y equipo

El formato mostrado contiene:

- Folio, fecha, trabajador, obra y fecha de devolución.
- Tabla con artículo, ID/serie, cantidad, estado al salir y estado al volver.
- Firmas: entregó (Almacén), recibió (Trabajador) y revisó devolución (Supervisor).

## Ejemplos de formatos de entrega

### Entrega de herramienta y EPP al trabajador

El ejemplo muestra estos datos:

- Nombre del trabajador: Juan Pérez García.
- Número de empleado: 12345.
- Área/contrato: Mantenimiento.
- Fecha de entrega: 15/09/2026.
- Supervisor: Oscar Salas.
- Observaciones: equipo para trabajos dentro de Mittal.

Texto de conformidad: el trabajador recibe de conformidad el equipo, se compromete a darle buen uso, cuidarlo y regresarlo al finalizar el contrato o cuando se le solicite. El mal uso o la pérdida del equipo será responsabilidad del trabajador.

| No. | Concepto | Tipo | Cantidad | Entregado |
|---:|---|---|---:|---|
| 1 | Arnés Kevlar | EPP | 1 | Sí |
| 2 | Arnés Poliéster | EPP | 1 | Sí |
| 3 | Bandola | EPP | 1 | Sí |
| 4 | Minipulidor | Herramienta | 1 | Sí |
| 5 | Flexómetro | Herramienta | 1 | Sí |
| 6 | Detector de gases | Herramienta | 1 | Sí |
| 7 | Retráctil 3 mts | EPP | 1 | Sí |
| 8 | Marro bola | Herramienta | 1 | Sí |
| 9 | Cincel | Herramienta | 1 | Sí |
| 10 | Extensión eléctrica | Herramienta | 1 | Sí |
| 11 | Reflector o lámpara | Herramienta | 1 | Sí |
| 12 | Peto | EPP | 1 | Sí |
| 13 | Polainas | EPP | 1 | Sí |
| 14 | Discos de corte 9 pulgadas | Herramienta | 1 | Sí |
| 15 | Discos de corte 4 1/2 pulgadas | Herramienta | 1 | Sí |

Espacios de firma en el formato: Entrega (nombre y firma), Recibe trabajador (nombre y firma), Vo. Bo. supervisor (nombre y firma). Los nombres visibles son Oscar Salas, Juan Pérez García y R. Martínez. Lema: “Seguridad hoy, trabajo mañana”.

### Vale de equipo de ejemplo

- Número: 0001.
- Fecha: 15/09/2026.
- Nombre: Juan Pérez García.
- Número de empleado: 12345.
- Área: Mantenimiento.
- Contrato/orden: LC-2026-001.
- Motivo: Entrega de herramienta y EPP.
- Lista: arnés Kevlar, arnés Poliéster, bandola, minipulidor, flexómetro, detector de gases, retráctil 3 mts, marro bola, cincel, extensión eléctrica, reflector o lámpara, peto, polainas, discos de corte 9 pulgadas y discos de corte 4 1/2 pulgadas; cantidad 1 cada uno.
- Firmas: Recibe (Trabajador) Juan Pérez García y Entrega (Almacén/Responsable) Oscar Salas.
- Folio: 0001.

Avisos del vale: “Este vale es personal e intransferible”; “El equipo es propiedad de la empresa”; “Debe devolverse en buen estado”; “Cualquier daño o pérdida será responsabilidad del trabajador”; “Reporta inmediatamente cualquier anomalía”. También incluye “Cuidamos nuestra herramienta, cuidamos nuestro trabajo y nuestra vida”, “IMHOTEP Mantenimiento Industrial” y “¡Apasionados por el servicio!”.

## Red de almacenes IMHOTEP

### Nodos y responsabilidades

- **Almacén central — Kepler:** recepción, resguardo, control de existencias y surtido a Contratistas.
- **Almacén colonia de Contratistas — dentro de Mittal:** recepción desde Kepler, resguardo y control, surtido a las áreas y registro de movimientos.
- **Almacenes de área:** Midrex, HYL, Laminador y Minas. El almacén de Contratistas surte a estas cuatro áreas.

La infografía señala: “Un buen flujo de materiales hace la diferencia”; “Control de materiales para una operación continua”; “Conecta, surte y mantiene operación en las áreas”; “De Contratistas a las áreas: material en tiempo y forma”; “Contratistas surte a Midrex, HYL, Laminador y Minas”.

### Control de movimientos

Flujo ilustrado: solicitud del área → surtido → vale o traspaso → recepción firmada → actualización de existencias.

Registrar folio, fecha, origen, destino, artículo, cantidad, responsable y saldo. En devoluciones y sobrantes, registrar el retorno al almacén de origen. Lema: “Material controlado, operación más fuerte”.

## Equipo y herramienta para un trabajador dentro de Mittal

La parte inicial del título de esta página está cortada en el escaneo; el texto legible termina en “de equipo y herramienta para 1 trabajador dentro de Mittal”. La lámina enumera:

| No. | Artículo | Clasificación |
|---:|---|---|
| 1 | Arnés Kevlar | EPP |
| 2 | Arnés Poliéster | EPP |
| 3 | Bandola | EPP |
| 4 | Minipulidor | Herramienta |
| 5 | Flexómetro | Herramienta |
| 6 | Detector de gases | Herramienta |
| 7 | Retráctil 3 mts | EPP |
| 8 | Marro bola | Herramienta |
| 9 | Cincel | Herramienta |
| 10 | Extensión eléctrica | Herramienta |
| 11 | Reflector o lámpara | Herramienta |
| 12 | Peto | EPP |
| 13 | Polainas | EPP |
| 14 | Discos de corte 9 pulgadas | Herramienta |
| 15 | Discos de corte 4 1/2 pulgadas | Herramienta |

Mensajes de seguridad: “Uso obligatorio de EPP y herramienta autorizada dentro de Mittal”; “Revisa tu equipo antes de usarlo”; “Utiliza el EPP todo el tiempo”; “Reporta cualquier condición insegura”; “Seguridad es responsabilidad de todos”.

## Entrega rápida de EPP y equipo de alturas con QR

**Subtítulo:** Celular o pistola lectora; mismo vale digital.

### Medios de escaneo

- **Celular: cámara.** Usar la cámara del celular; es fácil y rápido, para campo o almacén; escanear QR desde el celular.
- **Pistola: lector USB/Bluetooth.** Conectada a PC o tableta; captura rápida y continua; leer QR con pistola lectora.
- **Mismo vale digital:** un solo sistema, misma información, celular o pistola, en tiempo real. “Diferentes formas de escanear, una sola captura”.

### Flujo de captura por escaneo

1. **Abrir nuevo vale:** elegir entrega, trabajador, área/obra, fecha y responsable. Como opción, escanear el QR del gafete del trabajador.
2. **Leer QR de cada artículo:** usar cámara del celular o pistola conectada a PC/tableta; repetir el escaneo por artículo o ID individual.
3. **Carga automática:** el sistema obtiene código, descripción, tipo, talla, número de serie/ID y almacén. La cantidad es editable para consumibles, como guantes.
4. **Validar antes de entregar:** revisar existencias, talla y estado. Para arnés Kevlar o poliéster, bandola y gancho doble de vida, verificar inspección vigente e identificación individual. Si falla la validación, bloquear entrega y separar el equipo.
5. **Confirmar entrega:** el trabajador revisa artículos; registrar cantidad y estado; firmas de quien entrega y quien recibe.
6. **Guardar y emitir comprobante:** generar folio consecutivo, fecha/hora, lista de artículos, responsable y QR del vale para consulta. Se emite el vale digital de entrega.
7. **Escanear al devolver o reponer:** leer QR del artículo; registrar devolución, daño o reposición; actualizar existencias y resguardo. “Equipo de regreso a control”.

### Ejemplo de pantalla y artículos

Ejemplo en pantalla: escanear QR → arnés poliéster; ID ALT-024; talla M; inspección vigente; botón “Agregar al vale”.

Artículos ilustrados que pueden escanearse: guantes, lentes, casco, arnés, bandola y gancho doble de vida. Nota: QR individual para equipo reutilizable; QR de producto y cantidad para consumibles.

Lema: “Control + seguridad + trazabilidad”.

## Entrega de EPP y equipo para trabajo en alturas

### Flujo ilustrado

1. **Solicitud autorizada:** supervisor indica trabajador, área, tarea y fecha.
2. **Selección de EPP:** casco, lentes, guantes, calzado y protección auditiva o respiratoria según riesgo. Verificar talla.
3. **Selección de equipo de alturas:** arnés de Kevlar o poliéster, bandola y gancho doble de vida según tarea.
4. **Inspección previa:** comprobar etiquetas, costuras, cintas, herrajes, conectores, estado e historial. Retirar equipo dañado.
5. **Entrega e instrucción:** trabajador revisa artículos, ajuste, uso correcto y puntos de anclaje; comprobar capacitación y autorización.
6. **Vale con QR:** anotar folio, fecha, nombre, obra, artículos, ID/serie, cantidades y estado; firmas de quien entrega, quien recibe y supervisor. El QR del vale vincula al registro digital.
7. **Seguimiento y devolución:** escanear QR para consultar el vale una vez vinculado; registrar inspecciones, reposición, daños y devolución.

### Datos del vale

Folio, fecha, trabajador y área/obra. Tabla con artículo, ID/serie, talla, cantidad y estado. Firmas: entregó, recibió y validó.

Advertencia: “No usar equipo de alturas sin inspección, capacitación y autorización”.

## Costo de EPP por trabajador

La lámina indica que los costos totales incluyen IVA al 16 %, mientras que los precios unitarios y costos de la tabla están expresados sin IVA. Se muestran dos opciones:

| Equipo | Cantidad | Opción 1: unitario sin IVA | Opción 1: costo sin IVA | Opción 2: unitario sin IVA | Opción 2: costo sin IVA |
|---|---:|---:|---:|---:|---:|
| Lente claro | 1 | $12.00 | $12.00 | $12.00 | $12.00 |
| Tapón auditivo (par) | 2 | $6.02 | $12.04 | $6.02 | $12.04 |
| Respirador 3M 6200 | 1 | $269.35 | $269.35 | $269.35 | $269.35 |
| Filtro 7093 (par = 2 piezas), opción 1 | 2 | $172.93 | $345.86 | — | — |
| Filtro 2097 (par = 2 piezas), opción 2 | 2 | — | — | $115.58 | $231.16 |
| Cachucha MSA | 1 | $178.00 | $178.00 | $178.00 | $178.00 |
| Camisola mezclilla | 1 | $255.00 | $255.00 | $255.00 | $255.00 |
| Logo frontal | 1 | $28.00 | $28.00 | $28.00 | $28.00 |
| Logo contratista | 1 | $48.00 | $48.00 | $48.00 | $48.00 |
| Guantes dieléctricos clase 0 (1000 V), 1 par | 1 par | $1,250.00 | $1,250.00 | $1,250.00 | $1,250.00 |
| Guante protector de carnaza/piel, 1 par | 1 par | $800.00 | $800.00 | $800.00 | $800.00 |
| Zapato metatarsal 755 MT (par) | 1 par | $695.00 | $695.00 | $695.00 | $695.00 |

| Resumen | Opción 1: filtro 7093 | Opción 2: filtro 2097 |
|---|---:|---:|
| Total sin IVA | $3,892.25 | $3,777.55 |
| IVA 16 % | $622.76 | $604.41 |
| Total con IVA | $4,515.01 | $4,381.96 |

La lámina indica que la diferencia por trabajador con filtro 7093 es **$133.05 más**. Nota: los precios unitarios provienen de las facturas anexas y de la cotización de guantes eléctricos. “Par = 2 piezas”.

## Referencia por página

- **Página 1:** reto, operación del prototipo y ocho funciones indispensables.
- **Página 2:** equipo para trabajo en alturas, prueba de demostración, entregables y evaluación.
- **Página 3:** proceso de contratación y entrega de vale de EPP.
- **Página 4:** flujo de solicitud, revisión, entrega y devolución de herramientas y equipo de alturas; vale de resguardo.
- **Página 5:** ejemplo lleno de entrega y vale foliado de equipo.
- **Página 6:** red de almacenes y registro de movimientos.
- **Página 7:** listado de EPP y herramientas autorizados para un trabajador dentro de Mittal.
- **Página 8:** entrega digital rápida mediante QR con celular o pistola lectora.
- **Página 9:** flujo de entrega, inspección y seguimiento de equipo de alturas con QR.
- **Página 10:** comparación de costos de EPP por trabajador con filtros 7093 y 2097.

## Observaciones de transcripción

- Las diez páginas son escaneos; el texto se revisó visualmente.
- La primera parte del título de la página 7 quedó fuera del área visible del escaneo. No se completó por inferencia.
- La página 10 aclara que los precios se basan en facturas anexas y cotización de guantes eléctricos, pero esas facturas/cotización no forman parte de las diez páginas recibidas.
- El documento no especifica fecha límite del reto ni tecnologías obligatorias.
