# Escenarios de la planta

Situaciones que pueden vivir los usuarios, contadas de principio a fin. Salen de la plática del patrocinador y del PDF. Sirven para tres cosas: comprobar que el plan aguanta la realidad, ensayar la demostración y preparar las respuestas del pitch.

Cada escenario dice qué pasa en el sistema, qué reglas e historias lo cubren, y con qué alcance:

- **MVP**: lo cubren las fases 0 a 7.
- **Ola 2**: llega con una feature que ya tiene brief.
- **Pospuesto**: está previsto, sin brief todavía.
- **No cubierto**: hueco del plan; se resume en la última sección.

Los nombres son de ejemplo. Juan y Pedro son trabajadores; Oscar atiende Kepler; Marta y Raúl, el contenedor de Midrex; el ingeniero Martínez es supervisor; Ana está en RH y Luis en Compras.

---

## 1. Arranque del mantenimiento

### ES-01 · Cuarenta trabajadores nuevos el primer día

**Situación.** Lunes, 6:00. Arranca un paro de veinte días y cuarenta trabajadores recién contratados hacen fila en Kepler por su equipo básico: casco, lentes, guantes, calzado, overol y respirador.

**Qué pasa.**

1. RH los dio de alta el viernes, cada uno con su periodo de contrato.
2. Oscar escanea la credencial, escanea los artículos y el trabajador firma en la pantalla. Sale el vale con folio.
3. Toca "Nueva entrega" y sigue con el siguiente.

A quien todavía no trae la credencial de la planta se le busca por su número de empleado.

**Reglas e historias.** T-03, T-05, E-18, E-20, E-21, F-02; US-TRB-001, US-ENT-001, US-ENT-003.

**Cobertura.** MVP. Con FEAT-003 el sistema muestra además la dotación del puesto ("Dotación: faltan 4 de 11") y Oscar la agrega a la entrega con "Dotación sugerida" o solo escanea lo que falta.

**Qué vigilar.** La meta es menos de un minuto por trabajador. Es la entrega que conviene cronometrar en el ensayo.

### ES-02 · Regresa alguien que debía un casco

**Situación.** Pedro trabajó en el paro del año pasado y se fue sin devolver su casco. Lo vuelven a contratar.

**Qué pasa.**

1. Ana captura su número de empleado; el sistema lo reconoce, le muestra el casco pendiente y ofrece el reingreso.
2. En Kepler, al escanear su credencial, Oscar ve el casco en su resguardo y el aviso de que trae pendientes de un periodo anterior.
3. Si le quiere dar otro casco, el límite en posesión lo pone en naranja: o devuelve el anterior, o lo autoriza un supervisor con su motivo.

**Reglas e historias.** T-02, E-12, L-02, E-07, B-05; US-TRB-002, US-LIM-001.

**Cobertura.** MVP. Es justo lo que el patrocinador quiere evitar: que alguien acumule cascos de un contrato a otro.

### ES-03 · Se abre el contenedor de Midrex y llega una pieza de menos

**Situación.** Contratistas arma la herramienta del paro de Midrex y la manda al contenedor. Al recibir, a Marta le falta un minipulidor.

**Qué pasa.**

1. El almacenista de Contratistas escanea lo que envía y confirma. El traspaso queda En tránsito y su vale impreso, con QR, viaja con la carga.
2. Marta escanea ese QR, marca lo que sí llegó y confirma. Desde ese momento ella responde por lo recibido.
3. El minipulidor que falta sigue En tránsito y el traspaso queda "Recibido con diferencias".

**Reglas e historias.** X-01, X-06, X-08, X-10, X-11, X-13; US-TRS-001, US-TRS-002.

**Cobertura.** MVP para enviar, recibir y dejar visible la diferencia. Darlo por faltante llega con FEAT-002.

---

## 2. El día a día en el mostrador

### ES-04 · Un arnés con la inspección vencida

**Situación.** Juan pide arnés, bandola y gancho para un trabajo en alturas. El arnés que toma Marta tiene la inspección vencida desde la semana pasada.

**Qué pasa.**

1. Al escanearlo, el renglón queda en rojo: "Inspección vencida el 28/09/2026". No aparece el botón para pedir autorización.
2. Marta tiene dos caminos: tomar otro arnés, o inspeccionar ese ahí mismo. Revisa etiquetas, costuras, cintas, herrajes y conectores, y registra el resultado.
3. Si lo marca Apto, lo vuelve a escanear y sale verde. Si lo marca No apto, lo aparta y ya no se puede entregar.

**Reglas e historias.** E-06, SM-04, P-01, P-03; US-ENT-002, US-INS-001.

**Cobertura.** MVP. Es el caso especial que pide el PDF.

### ES-05 · El cuarto par de guantes de la semana

**Situación.** Juan ya recibió tres pares de guantes esta semana, que es el límite. Pide otro porque se le llenaron de grasa.

**Qué pasa.**

1. El renglón queda en naranja: "límite 3 en 7 días, lleva 3, pide 1".
2. Marta escribe el motivo y envía la solicitud.
3. El ingeniero Martínez, que anda en el área, la ve en su celular con todos los datos y toca "Autorizar". La pantalla de Marta se actualiza sola y la entrega continúa.
4. El vale guarda quién autorizó y por qué.

Si nadie responde en quince minutos, la solicitud vence; Marta quita ese renglón y entrega lo demás.

**Reglas e historias.** L-03, L-04, E-07, A-01 a A-04, A-07; US-LIM-001, US-AUT-001.

**Cobertura.** MVP.

**Qué vigilar.** Puede responder cualquier usuario con el permiso de autorizar, no un supervisor en particular. Aun así, un límite estricto sobre equipo de seguridad puede dejar a alguien sin protección: ver los huecos.

### ES-06 · Un marro y dos cinceles, que no llevan etiqueta

**Situación.** Juan pide un marro y dos cinceles. A ninguno se le puede pegar un QR.

**Qué pasa.**

1. En el estante de los marros hay una etiqueta con el QR del producto. Marta la escanea: un marro.
2. Escanea dos veces la del estante de los cinceles, o una vez y toca "+".
3. Si la etiqueta del estante no se lee, busca "cincel" por nombre.
4. Lo escaneado es un borrador: si se equivoca de estante, quita el renglón o toca "Deshacer" en los primeros 5 segundos. Las existencias solo bajan al confirmar el vale.

**Reglas e historias.** I-07, E-16, E-18, E-28; US-ETQ-001, US-ENT-001.

**Cobertura.** MVP. Es la pregunta que el patrocinador planteó como reto en la plática.

### ES-07 · Se despegó la etiqueta del arnés

**Situación.** Juan devuelve un arnés cuya etiqueta ya no se lee.

**Qué pasa.**

1. Marta escanea la credencial de Juan y ve lo que tiene en resguardo; ahí está el arnés con su número de serie.
2. Compara la serie grabada en el arnés con la de la pantalla y lo recibe desde la lista.
3. Después reimprime la etiqueta desde Etiquetas.

**Reglas e historias.** V-14, E-18, C-01, I-02; US-DEV-001, US-ETQ-001.

**Cobertura.** MVP.

### ES-08 · Olvidó la credencial

**Situación.** Juan llega sin su credencial.

**Qué pasa.**

1. Marta teclea su número de empleado o lo busca por nombre.
2. Aparece su ficha: nombre, puesto y vigencia. Marta confirma que es él.
3. La entrega sigue igual.

**Reglas e historias.** E-17, E-18; US-ENT-001.

**Cobertura.** MVP. La ficha muestra la foto del trabajador, que es lo que de verdad confirma quién es; si no tiene, avisa y la entrega continúa.

### ES-09 · Pide herramienta alguien que ya no trabaja aquí

**Situación.** Un trabajador cuyo contrato terminó el viernes, y que ahora está con otra contratista, se presenta en el contenedor: "yo estoy registrado en su sistema".

**Qué pasa.**

1. Al escanear su credencial, la ficha sale en rojo: "ya no forma parte de la plantilla", con la fecha en que terminó su contrato.
2. No se le puede agregar ningún artículo.
3. Si trae algo que devolver, sí se le recibe.

**Reglas e historias.** E-02, T-07, SM-05; US-TRB-002.

**Cobertura.** MVP.

### ES-10 · Se cae la red a media entrega

**Situación.** Marta ya escaneó cinco artículos y, al confirmar, el celular se queda sin señal.

**Qué pasa.**

1. Aparece la banda "Sin conexión". El borrador no se pierde.
2. Al volver la señal, toca "Reintentar".
3. Aunque el primer intento sí hubiera llegado al servidor, el vale no se duplica.

**Reglas e historias.** RG-08, RG-09; [ADR-004](../architecture/decisions/ADR-004-primero-en-linea.md).

**Cobertura.** MVP para cortes breves. Un corte largo no está cubierto: ver los huecos.

### ES-11 · Diez pares en lugar de uno

**Situación.** Marta entrega un par de guantes, pero se le va el dedo y confirma diez.

**Qué pasa.**

1. Abre el vale y toca "Cancelar", con el motivo "error de captura".
2. Se genera un vale de cancelación: los diez pares regresan a existencias y el consumo de Juan vuelve a como estaba.
3. Captura de nuevo la entrega correcta. Con "Cancelar y rehacer" se abre un borrador con los mismos renglones y solo corrige la cantidad; el trabajador firma el vale nuevo. Los tres vales quedan en el historial.

**Reglas e historias.** K-01 a K-05, C-12, RG-02; US-CAN-001.

**Cobertura.** MVP.

### ES-12 · Cambio de turno en el contenedor

**Situación.** A las 18:00 Marta entrega el contenedor a Raúl, del turno de noche.

**Qué pasa.**

1. Cada almacenista trabaja con su propia cuenta y su propio dispositivo: Marta cubre el día y Raúl la noche, y ninguno conoce la contraseña del otro.
2. Cada vale lleva como responsable a quien lo hizo.
3. El reporte de movimientos, filtrado por almacén, fechas y usuario, muestra qué hizo cada uno.

**Reglas e historias.** RG-03, RG-07; US-ACC-001, US-REP-001.

**Cobertura.** MVP para saber quién hizo cada movimiento. La entrega formal del turno, con conteo y firma de los dos, no está cubierta: ver los huecos.

---

## 3. Equipo que se mueve, se daña o no aparece

### ES-13 · "¿Quién tiene el detector?"

**Situación.** Una cuadrilla va a entrar a un espacio confinado y no hay detector de gases en el contenedor de Midrex. Marta, la almacenista, necesita saber dónde están.

**Qué pasa.**

1. Escribe "detector" en la búsqueda.
2. Ve solo lo de su almacén y lo que tienen los trabajadores: ninguno en Midrex y uno en resguardo de Pedro desde el martes. No ve qué hay en Kepler ni en otros almacenes (AC-06).
3. Le pide a Pedro que lo devuelva, o pide por teléfono a Kepler que le envíen uno por traspaso. Quien tiene `almacenes.todos` (el Administrador) sí ve los detectores de todos los almacenes.

Si Pedro se lo prestó a Juan sin pasar por el almacén, el sistema sigue diciendo Pedro: él lo sacó y él responde. Si Juan lo devuelve, se abona a Pedro.

**Reglas e historias.** C-03, C-06, V-01, AC-06; US-CON-001, US-DEV-001.

**Cobertura.** MVP. Distinguir "en calibración" de "No apto" llega con FEAT-004.

### ES-14 · Devuelve un detector que no es el nuestro

**Situación.** Pedro perdió su detector, tomó uno de otra compañía y lo trae a devolver.

**Qué pasa.**

1. Marta lo escanea y el código no existe. Rojo: "No es de la empresa". No se recibe.
2. Si le pegaron encima una etiqueta nuestra, Marta compara la serie grabada con la de la pantalla, y no coincide.
3. El detector de Pedro sigue pendiente a su nombre.

**Reglas e historias.** V-12, V-14, I-02; US-DEV-001.

**Cobertura.** MVP.

### ES-15 · El minipulidor regresa con el cable roto

**Situación.** Juan devuelve un minipulidor con el cable pelado.

**Qué pasa.**

1. Marta lo escanea y elige "Dañado". El sistema pide una observación y deja tomar una foto.
2. El minipulidor entra al almacén como No apto: ya no se puede entregar.
3. A Juan no se le carga nada; queda la observación.
4. Cuando regresa de reparación, una inspección con resultado Apto lo vuelve a poner disponible.

**Reglas e historias.** V-04, V-05, V-06, P-03; US-DEV-001, US-INS-001.

**Cobertura.** MVP. Marcarlo "En mantenimiento" mientras está fuera llega con FEAT-004.

### ES-16 · El tecle que se quedó instalado

**Situación.** La planta pide dejar un tecle sosteniendo una tubería. Juan, que lo sacó, ya no lo puede devolver.

**Qué pasa**, cuando exista el cierre sin devolución:

1. Marta registra el cierre con el motivo "quedó instalado" y anota quién lo indicó.
2. El tecle sale del resguardo de Juan sin dejarle pendiente.
3. Queda en la lista de revisión, para que la empresa lo cobre al cliente.

**Reglas e historias.** V-09.

**Cobertura.** Pospuesto. En el MVP el tecle seguiría como pendiente de Juan y le impediría el vale de no adeudo: ver los huecos.

### ES-17 · "Me lo robaron"

**Situación.** A Pedro le robaron una extensión en el área.

**Qué pasa.**

1. No hay nada que escanear. La extensión sigue en su resguardo.
2. Al pedir su vale de no adeudo, aparece como pendiente y el vale no se emite.
3. Ana ve "Con pendientes" y la empresa decide qué hacer con el finiquito.

**Reglas e historias.** B-04, B-05, B-09, V-13; US-BAJ-001.

**Cobertura.** MVP en lo esencial: el pendiente queda a su nombre. Anotar el reporte de robo, y que un supervisor lo dé por perdido, está pospuesto.

### ES-18 · No hay arneses en Midrex, pero sí en Contratistas

**Situación.** Marta se queda sin arneses talla M.

**Qué pasa.**

1. Abre el artículo y ve las existencias por almacén: cero en Midrex, cinco en Contratistas.
2. Llama a Contratistas, y de allá envían un traspaso.
3. Marta lo recibe con el QR.

**Reglas e historias.** C-03, E-04, X-01; US-CON-001, US-TRS-001, US-TRS-002.

**Cobertura.** MVP para ver dónde hay y para el traspaso. La petición se hace por teléfono: ver los huecos. Con FEAT-004, Luis ve antes que el artículo bajó del mínimo.

---

## 4. Cierre

### ES-19 · Baja en Kepler con un arnés pendiente en Midrex

**Situación.** Termina el contrato de Juan. Llega a Kepler con su casco y su respirador a pedir el vale de no adeudo, pero se le olvidó devolver un arnés en Midrex.

**Qué pasa.**

1. Oscar abre su ficha y toca "Vale de no adeudo". Juan pasa a Baja en proceso.
2. La lista muestra tres pendientes: casco, respirador y un arnés entregado en Midrex.
3. Oscar recibe el casco y el respirador. El arnés lo puede recibir ahí mismo si Juan lo trae, con el aviso de que entra a Kepler; si no, Juan regresa a la planta.
4. Con todo en cero se emite el vale y Juan queda inactivo. Ana ve "No adeudo emitido" y lo finiquita.

**Reglas e historias.** B-01 a B-04, B-08, B-09, V-07; US-BAJ-001, US-DEV-001.

**Cobertura.** MVP. Es el último paso de la prueba del PDF.

### ES-20 · Se fue sin pasar por el almacén

**Situación.** Un trabajador deja de presentarse y nunca devuelve su equipo.

**Qué pasa.**

1. Su contrato vence y deja de ser vigente: ya no puede recibir nada.
2. Aparece en el reporte de adeudos con el filtro "solo no vigentes", con lo que debe y desde cuándo.
3. Si un día lo recontratan, sus pendientes siguen ahí.

**Reglas e historias.** T-07, B-05, C-05; US-REP-001, US-TRB-002.

**Cobertura.** MVP.

### ES-21 · Se termina el paro y se cierra el contenedor

**Situación.** Acaba el mantenimiento de Midrex. Hay que regresar todo a Contratistas y saber qué faltó.

**Qué pasa.**

1. Los trabajadores devuelven su herramienta en el contenedor.
2. Marta envía por traspaso todo lo que queda.
3. El reporte de cierre muestra, por artículo, lo que llegó, lo consumido, lo regresado y lo que sigue con trabajadores, con su nombre.
4. Lo que el sistema dice que está en el contenedor y no aparece se registra como faltante, con observación.
5. Con las existencias en cero, el supervisor cierra el almacén.

**Reglas e historias.** CP-01 a CP-05, X-01.

**Cobertura.** Ola 2 (FEAT-002). En el MVP se hace el traspaso de regreso y se ve, en los reportes de existencias y de adeudos, qué quedó y quién lo tiene; no hay registro de faltantes ni cierre.

### ES-22 · La Comisión Mixta pide prueba de que se entregó el EPP

**Situación.** Un trabajador dice que nunca le dieron camisola. La Comisión Mixta de Seguridad pide evidencia.

**Qué pasa.**

1. Se abre la ficha del trabajador, o el reporte de movimientos filtrado por él.
2. Aparece la entrega con fecha, folio y responsable.
3. El vale muestra su firma.

**Reglas e historias.** C-01, C-05, E-21, F-02; US-CON-001, US-REP-001.

**Cobertura.** MVP para encontrar el vale firmado. El comprobante sellado llega con FEAT-001; el reporte de EPP por trabajador está pospuesto.

---

## 5. Administración

### ES-23 · Una herramienta pasa a ser de uso especial

**Situación.** Tras un incidente, la empresa decide que cierta herramienta solo salga con autorización.

**Qué pasa.**

1. Luis o el supervisor abren el artículo, activan "autorización del supervisor" y escriben el motivo: "Solo personal capacitado".
2. Desde la siguiente entrega, el renglón sale en naranja con ese motivo.
3. Las que ya están con trabajadores no se recogen.

Si quisieran exigirle inspección a un artículo que se controla por cantidad, no se puede: la inspección es por pieza. Se crea el artículo por pieza y se inactiva el anterior.

**Reglas e historias.** CF-05 a CF-08, E-26; US-CAT-002, US-ESP-001.

**Cobertura.** MVP.

### ES-24 · Un modelo se descontinúa

**Situación.** La empresa deja de usar un modelo de minipulidor.

**Qué pasa.**

1. Luis lo inactiva con el motivo "Descontinuado".
2. Ya no se puede entregar ni darle entrada.
3. Los que están con trabajadores se devuelven normal, y lo que queda en los contenedores se traslada a Kepler.
4. Su historial sigue completo.

**Reglas e historias.** CF-10 a CF-13, E-19, I-09, X-09; US-CAT-003.

**Cobertura.** MVP.

### ES-25 · El almacenista necesita ver un dato de RH

**Situación.** La empresa decide que el almacenista de Kepler debe ver el NSS para llenar un formato.

**Qué pasa.**

1. El administrador abre el rol Almacenista y activa "ver datos personales del trabajador". La pantalla le muestra qué gana el rol.
2. Desde la siguiente consulta, la ficha incluye CURP y NSS.
3. El cambio queda en el registro de cambios.

Si solo debe verlo el almacenista de Kepler, se duplica el rol y se le asigna a él.

**Reglas e historias.** AC-05, AC-08, AC-10.

**Cobertura.** Ola 2 (FEAT-006). En el MVP el permiso ya existe y el servidor lo respeta, pero el cambio se hace editando el script de datos.

### ES-26 · Mil pares de guantes en un mes

**Situación.** Finanzas pregunta por qué se compraron mil pares de guantes.

**Qué pasa.**

1. Luis abre el reporte de consumo, filtra por el artículo y por el mes, y ve el total y quiénes más consumieron.
2. Para el detalle, abre el reporte de movimientos y ve cada entrega: a quién, en qué almacén, quién la hizo, y las autorizaciones con su motivo.
3. Con eso ajusta el límite del artículo.

**Reglas e historias.** C-05, E-21, L-01, A-04; US-REP-001, US-CAT-002.

**Cobertura.** MVP, con el reporte de consumo y el de movimientos.

### ES-27 · "Ese vale lo manipularon"

**Situación.** Un trabajador desconoce una entrega: dice que él no firmó eso.

**Qué pasa.**

1. Se abre el vale: firma, fecha y hora, responsable y dispositivo.
2. El comprobante indica "Íntegro": el contenido no cambió desde que se emitió.
3. El trabajador tiene su copia desde ese día, y coincide.

**Reglas e historias.** F-05, F-06, F-07, F-10.

**Cobertura.** Ola 2 (FEAT-001). En el MVP el vale tiene firma y el sistema no ofrece forma de editarlo, pero aún no lleva sello ni copia para el trabajador.

### ES-28 · Desaparece una herramienta

**Situación.** En Midrex falta un detector de gases que el sistema ubica en ese almacén. Nadie recuerda quién lo vio por última vez.

**Qué pasa.**

1. El ingeniero Martínez, que tiene `almacenes.todos`, abre el reporte de movimientos y filtra por el artículo, el almacén y los últimos días.
2. Ve cada vale que movió el detector, con su responsable. En la ficha de la pieza está su historial completo.
3. Filtra por usuario para ver qué más hizo cada persona en esos días y a quién preguntar.

Marta, almacenista de Midrex, puede usar el mismo filtro, pero solo sobre su almacén y como dato informativo.

**Reglas e historias.** C-02, C-11, AC-06; US-REP-001, US-CON-001.

**Cobertura.** MVP. Registrar el faltante con una observación llega con FEAT-002.

---

## 6. Huecos que revelan los escenarios

| Hueco | Escenario | Qué pasa hoy en el plan | Recomendación |
|---|---|---|---|
| Equipo que quedó instalado | ES-16 | En el MVP sigue como pendiente e impide el vale de no adeudo. | Es lo primero a construir de lo pospuesto (V-09): es barato y la baja depende de ello. |
| Corte largo de red | ES-10 | No se puede capturar, y un vale hecho en papel no se puede registrar después porque falta la firma en pantalla. | Con la firma en papel de FEAT-001 se captura al volver la red, adjuntando la foto del vale. Si los cortes largos son frecuentes, es la señal para el modo sin conexión. |
| Diferencia de un traspaso | ES-03 | Lo no recibido queda En tránsito sin fecha de cierre. | Se resuelve con el faltante de FEAT-002. |
| Un límite que deja sin EPP | ES-05 | Si nadie autoriza, el trabajador se queda sin el equipo. | No es de código: límites holgados en equipo de seguridad y más de una persona con permiso de autorizar. |
| Entrega de turno | ES-12 | Se sabe quién hizo cada movimiento, pero no hay conteo ni firma al cambiar de turno. | Pospuesto, anotado en el alcance. |
| Solicitud de surtido | ES-18 | Se pide por teléfono. | Pospuesto. El PDF la dibuja en la página 6, pero no la exige. |
| Etiqueta ilegible | ES-07 | Las reglas solo hablaban de escanear. | Resuelto en la versión 4 de las reglas: V-14 y E-18. |
| Extender un contrato | ES-02 | No estaba dicho. | Resuelto: T-02. |

---

## 7. Para la demostración y el pitch

- **La prueba del PDF** es la suma de ES-01, ES-04, ES-05, ES-03 y ES-19, en ese orden.
- **El reto que planteó el patrocinador** es ES-06: la herramienta sin etiqueta.
- **Su primera frase en la plática** es ES-13: buscar quién tiene algo.
- **Sus dolores**, para la parte de preguntas: ES-02 (adeudos que se acumulan), ES-14 (equipo cambiado), ES-21 (quién perdió qué), ES-26 (consumo excesivo) y ES-27 (el vale como prueba).
