# Preguntas para los dueños del track

Para las reuniones de retroalimentación del hackathon. Cada pregunta dice **por qué la hacemos** (de dónde sale la duda) y **qué supuesto usamos hoy**, para que la respuesta se pueda aplicar sin volver a preguntar. Están ordenadas por qué tanto cambian el sistema. Si solo hay tiempo para pocas, hacer las de prioridad **alta**.

Nota sobre las fuentes: el PDF oficial es un escaneo sin texto; las citas vienen de su transcripción (`info_track/track-3-imhotep.md`), de la conferencia (`info_track/transcripcion_track.md`) y de las anotaciones (`info_track/anotaciones-exposicion.md`).

## Contradicciones y huecos que encontramos

| # | Qué dice una fuente | Qué dice otra o qué falta |
|---|---|---|
| 1 | El EPP básico se entrega en el **almacén central de Kepler** al contratar (anotaciones, línea 11; conferencia, línea 15). Nuestra lectura de la operación real: Kepler es el punto de partida de la mercancía y la entrega a trabajadores empieza en Contratistas. | «En el remanente de contratistas se queda el equipo de seguridad y las herramientas… se le dan a cada uno de los trabajadores» (conferencia, línea 169), sin decir quién ni en qué almacén. |
| 2 | La herramienta se pide a los almacenes «de abajo»: Midrex, HYL, Laminador (conferencia, línea 15). | Esa misma línea 169 dice que en Contratistas «se quedan… las herramientas». |
| 3 | Los vales del PDF llevan **fecha prevista de devolución** y **NSS**. | Nuestras reglas no ponen plazo de préstamo (E-25: dura lo que dure el contrato) y reservan el NSS a RH (RG-13). En la conferencia el docente dijo que el plazo «podía modificarse después». |
| 4 | El profesor prefirió usar el **número de empleado de la planta** para la credencial (conferencia, min 57). | El sistema genera su propio número (T-10); el de la planta es un campo opcional solo para el Administrador. |
| 5 | El PDF pide cuatro perfiles: almacenista, supervisor, Compras y RH. | La conferencia habla de tres departamentos: Compras, almacenes y RH (línea 261). No se pide un Administrador; lo agregamos nosotros. |
| 6 | La tabla de costos del PDF (12 conceptos, $4,515.01 y $4,381.96) no tiene columna de tipo. | Otra lámina sí separa EPP de herramienta, pero tampoco dice en qué almacén se entrega cada cosa. |
| 7 | El **Excel de compras** (`docs/recursos/comprasejer2026.xlsx`, 350 renglones) trae una «clave». | La clave **no identifica un artículo**: hay 89 claves distintas para 350 renglones, y una sola (`31162800`) se repite en 160. Ver la sección de artículos por cantidad y por pieza. |

## Preguntas

### Dónde se entrega cada cosa (alta)

1. **EPP básico al contratar.** Nuestra lectura de la operación real es que Kepler es el punto de partida de la mercancía y que **la operación con trabajadores empieza en Contratistas**, donde se entrega el EPP. ¿Es correcto, o el trabajador nuevo acude a Kepler a recoger su equipo básico, como dicen las anotaciones? *Por qué:* contradicción 1. *Hoy:* el sistema deja entregar en cualquier almacén que tenga existencia; la intención del equipo es EPP en Contratistas.
2. **Reposición del EPP.** Cuando un EPP de consumo se acaba o se desgasta (guantes, lentes, cachucha), ¿quién lo repone, en qué almacén y contra qué (se entrega el usado o no)? ¿Con qué frecuencia? *Hoy:* una entrega nueva de un consumible, sin devolución, sujeta al límite por periodo (por ejemplo, 3 guantes por semana).
3. **Herramienta y equipo de alturas.** ¿Se entregan en el almacén del proyecto (Midrex, HYL, Laminador, Minas), en Contratistas o en ambos? *Por qué:* contradicción 2. *Hoy:* herramienta en el proyecto; alturas en Contratistas o Kepler.
4. **«Se le dan a cada uno de los trabajadores».** Frase de la línea 169 de la conferencia: ¿quién entrega y en qué almacén?
5. **Devolución.** Entendemos que se devuelve al almacén donde se tomó. Si el trabajador cambia de proyecto, ¿se acepta en otro almacén? *Hoy:* se acepta con aviso (V-07) y el titular sigue siendo responsable (V-01).

### Cómo se mueve el inventario entre almacenes (alta)

6. **Entrada de material.** ¿Todo lo que compra la empresa entra **solo por Kepler** y los demás almacenes lo reciben por traspaso? *Hoy (decisión del equipo):* sí, también la carga inicial.
7. **Compras urgentes.** Cuando un supervisor pide una compra urgente, ¿el material llega a Kepler y luego se traspasa, o se entrega directo al proyecto que lo pidió?
8. **Ruta de traspasos.** ¿Kepler envía **solo a Contratistas** y Contratistas a los proyectos, sin saltos, y el regreso va por la misma cadena? ¿Hay casos de excepción reales (por ejemplo, una urgencia de Kepler a un proyecto)? *Hoy:* solo el Administrador puede saltarse la ruta, con una nota obligatoria.
9. **Quién recibe un traspaso.** ¿Lo firma el supervisor del almacén o el almacenista en turno? Con almacenes de 24 horas y varios almacenistas, ¿quién queda como responsable de lo recibido? *Hoy:* es un permiso que se puede dar al supervisor, al almacenista o a ambos.
10. **Diferencias al recibir.** Si llega menos de lo enviado, ¿qué debe pasar con lo que falta: se reclama al almacén que envió, se cancela, se espera? *Hoy:* lo no recibido queda «en tránsito» y se anota la diferencia.

### Qué es una pieza y qué es una cantidad (alta)

11. **Qué se identifica por pieza.** ¿Qué artículos deben llevar código único y número de serie? El PDF menciona arnés, bandola y gancho de vida; la conferencia menciona herramienta de alto valor, como el detector de gases «de 30 mil». ¿Hay un monto o una lista que lo defina (por ejemplo, todo lo que cueste más de X)? *Hoy:* lo decide la categoría del artículo: alturas, eléctrica y alto valor son por pieza; el resto, por cantidad.
12. **El Excel de compras.** ¿Trae el listado oficial de artículos que usaremos? Entonces, ¿qué es la «clave»? Se repite en muchos renglones y algunos traen dos claves juntas (por ejemplo, `27112838 / 31191506`). ¿Hay un catálogo con código único por artículo?
13. **Series.** ¿Quién conoce el número de serie de las piezas de alto valor y cuándo se captura: al comprar, al recibir o al entregar?
14. **Estados de una pieza.** La conferencia menciona dañado, funcional, en calibración y en mantenimiento. ¿Hay más? ¿Quién cambia el estado y quién lo autoriza?
15. **Rigor del seguimiento.** Entendemos que lo de alto valor (detector de gases, minipulidor) se sigue **pieza por pieza, con serie**. ¿El equipo de alturas (arnés, bandola, gancho) también, o basta con identificarlo por tipo? Y para lo que es por cantidad (flexómetro, marro, cincel, guantes): ¿basta con saber **a quién se le entregó cuántos y cuándo**, sin identificar cada unidad? *Hoy:* el vale guarda a quién se entregó cada cantidad, pero no hay una pantalla que lo muestre.

### Dudas sobre el Excel de compras (alta)

El archivo `docs/recursos/comprasejer2026.xlsx` es lo único que tenemos de la empresa con artículos reales. Lo analizamos y nos quedan estas dudas:

16. **¿Qué es la «clave»?** Son 8 dígitos y parecen un código de clasificación de producto, no de artículo: la misma clave (`31162800`) la comparten una llave mixta, una pija, un silicón y una cuerda de rapel. ¿Quién la asigna y para qué se usa?
17. **¿Existe un código único por artículo?** Algunos renglones traen uno dentro de la descripción, por ejemplo `(RR077)` y `(RS062)` (17 renglones), y otros un prefijo `/T/` o `/SP/` (6 renglones). ¿Qué significan esos códigos y esos prefijos? ¿Son códigos internos de la empresa que debamos usar como identificador?
18. **Renglones con dos claves** (por ejemplo `27112838 / 31191506`). ¿Es el mismo artículo con dos claves, o dos artículos mezclados?
19. **¿Qué representa el archivo?** Dice «cantidad total acumulada» y «precio unitario promedio». ¿Es el historial de compras de un periodo (no la existencia actual)? ¿Es la lista que debemos cargar como inventario inicial en Kepler?
20. **¿Cuál es la unidad?** Tres renglones traen cantidades con decimales. ¿Son metros, kilos o litros? ¿Qué unidad usa cada artículo?
21. **¿Falta información?** El archivo no trae categoría, tipo (EPP, herramienta), marca, talla, serie ni almacén. ¿Existe una versión con esos datos, o nos toca clasificar los 350 renglones?
22. **Los artículos del reto no aparecen** por nombre (detector de gases, minipulidor, arnés Kevlar). ¿Los traerán los datos de ejemplo del organizador?

### Reglas de entrega y límites (media)

23. **Límites.** ¿Los topes que usamos (por ejemplo, 3 guantes por semana, lentes y cachucha por periodo) los fija la empresa o los inventamos? Si son reales, ¿nos pueden dar la lista?
24. **Dotación por puesto.** El PDF da un total de EPP por trabajador. ¿Es el mismo para todos los puestos, o cada puesto tiene el suyo?
25. **Plazo de préstamo.** El docente dijo que podía modificarse. ¿Debe haber una fecha de devolución en el vale, o basta con que dure el contrato?
26. **Equipo dañado o perdido.** No se cobra al trabajador. ¿Cómo se registra una pérdida, y qué pasa con el equipo que se instala en la planta y no regresa?

### Personas, perfiles y vale (media)

27. **Perfiles.** ¿Quién es el supervisor: de cada almacén o de cada proyecto? ¿Existe un supervisor general o alguien que vea todos los almacenes? Nosotros usamos un Administrador solo para tener control de todos los almacenes.
28. **Qué ve cada perfil.** ¿RH necesita abrir el vale de no adeudo, o solo saber si el trabajador debe algo? ¿El almacenista puede ver los datos personales del trabajador?
29. **Número de empleado.** ¿Usamos el de la planta? ¿Cuál es su formato, y quién lo emite?
30. **Vale.** ¿Debe incluir el NSS y la firma de «Validó» del supervisor? ¿Cuántas copias, y el trabajador conserva una impresa o digital?

### Presentación y evaluación (alta, para mañana)

31. **Tiempos.** ¿Cuánto dura la presentación y la ronda de preguntas? *Hoy:* planeamos 7 minutos por persona y 7 conjuntos, pero eso es nuestro, no del reto.
32. **Datos de la prueba.** ¿Cuándo y en qué formato entregarán los datos de ejemplo (trabajador, EPP, herramienta, límites, traspaso)? ¿Es un Excel? ¿Podemos probar con él antes?
33. **Qué se evalúa en vivo.** ¿La prueba se hace en el servidor que entregamos o en el que ustedes indiquen? ¿Con celulares propios o del equipo?
34. **Conexión.** ¿Habrá internet estable en la demostración? Nuestro sistema no funciona sin conexión.

## Ejemplo de plantilla de traspaso

Un archivo de Excel es **un traspaso**: un origen y un destino que se eligen en pantalla, no en el archivo. El ejemplo supone un traspaso de **Contratistas a Midrex**. Los códigos y los nombres son ilustrativos.

| codigo | nombre | cantidad | codigo pieza | serie |
|---|---|---|---|---|
| FLE-001 | Flexómetro 8 m | 6 | | |
| MAR-001 | Marro de bola | 4 | | |
| CIN-001 | Cincel | 10 | | |
| EXT-001 | Extensión eléctrica 15 m | 5 | | |
| DET-001 | Detector de gases | | DET-001-0003 | GAS-88214 |
| DET-001 | Detector de gases | | DET-001-0004 | GAS-88219 |
| ARN-001 | Arnés de poliéster | | ARN-001-0012 | AR-5521 |

Cómo se lee:

- **`codigo`** es el identificador del artículo. Se llena siempre.
- **`cantidad`** se llena solo para artículos **por cantidad** (los intercambiables). Debe ser un número entero.
- **`codigo pieza`** y **`serie`** se llenan solo para artículos **por pieza**, un renglón por cada pieza. La cantidad se deja vacía porque cada pieza vale uno.
- **`nombre`** es solo de referencia para quien arma el archivo. Hoy el sistema lo ignora con un aviso y en la vista previa muestra el nombre del catálogo. **Propuesta:** reconocerlo como columna de ayuda, sin aviso, y comparar con el catálogo para detectar un código mal escrito.
- Reglas: máximo 500 renglones por archivo; si un artículo por cantidad aparece en varias filas, se suman; una pieza repetida es error; solo se mueve lo que existe en el almacén de origen.

Al cargar el archivo se mostrará la vista previa en tabla, paginada de 12 en 12, con el estado de cada fila: correcta, aviso o error. Si hay filas en error, no se guarda nada, salvo que la persona elija «Dejar fuera las filas con error».

## Artículos por cantidad y por pieza

La diferencia es **si cada unidad se distingue de las demás**.

| | Por cantidad | Por pieza |
|---|---|---|
| Qué es | Unidades intercambiables: da igual cuál te toque | Una unidad única que hay que poder seguir |
| Ejemplos | Guantes, lentes, discos de corte, flexómetros, marros, cinceles | Detector de gases, minipulidor, arnés, bandola, gancho de vida |
| Cómo se cuenta | Un número: «hay 40» | Cada una tiene su código y su serie |
| Qué se sabe de ella | Cuántas hay en cada lugar | Dónde está, quién la tiene, su estado, su última inspección y todo su historial |
| En el vale | «3 guantes» | «Detector GAS-88214» |
| Seguimiento | Se ve en la existencia del almacén y en el resguardo del trabajador | Se sigue pieza por pieza en Seguimiento |
| Si se pierde | Se descuenta una cantidad | Se sabe exactamente cuál fue |

**Qué hace hoy el sistema.** La categoría del artículo decide si es por cantidad o por pieza. Alturas, eléctrica y alto valor son por pieza; la herramienta manual (flexómetro, marro, cincel) es por cantidad. Por eso Seguimiento de piezas sale en cero cuando solo se entregaron herramientas manuales: ese seguimiento cuenta piezas, y lo entregado por cantidad se ve en el resguardo del trabajador.

**Qué dice el Excel original de compras** (`docs/recursos/comprasejer2026.xlsx`, 350 renglones, columnas: clave, descripción, cantidad total acumulada, precio unitario promedio e importe):

- **No distingue por cantidad de por pieza.** No tiene tipo, serie, categoría ni almacén. Es un reporte de compras acumuladas.
- **La clave no sirve como identificador:** 89 claves distintas para 350 renglones. La clave `31162800` aparece en **160** renglones (es una familia de producto, no un artículo) y dos renglones traen dos claves juntas.
- **110 renglones tienen cantidad 1** y 200 tienen 3 o menos. Los de cantidad 1 y precio alto son candidatos a ser piezas únicas: dos bombas neumáticas para grasa de unos 15,000 pesos, y una línea de vida horizontal de cable de unos 20,000.
- Los artículos más caros (llaves de impacto, soplete de corte, taladros) están en cantidades de 1 a 10 y **no se puede saber** si cada uno debe llevar serie.
- 3 renglones tienen cantidad no entera, probablemente metros o kilos.
- **Tiene dos tipos de códigos dentro de la descripción:** 17 renglones empiezan con un código como `(RR077)` y 6 con un prefijo `/T/` o `/SP/`. Podrían ser códigos internos de la empresa; hay que preguntarlo (pregunta 17).
- Las 350 descripciones son distintas entre sí, así que **la descripción es hoy lo único que identifica un artículo.**
- Cosas que el reto menciona, como el detector de gases, el minipulidor y el arnés, **no aparecen** por esos nombres en este Excel.

**Consistencia que conviene aclarar** (preguntas 11, 12 y 16 a 22): definir con el track qué umbral o lista convierte un artículo en pieza, y confirmar si el Excel de compras es la fuente oficial de artículos. Sin eso, la decisión de qué lleva serie la tomamos nosotros.
