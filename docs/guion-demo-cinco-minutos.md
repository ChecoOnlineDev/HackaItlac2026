# Demostración de IMHOTEP en cinco minutos

La presentación debe demostrar que se sabe qué hay, dónde está, quién lo tiene y por qué una entrega se permite o se bloquea. El hilo es un trabajador desde su alta hasta su devolución y baja. La prioridad es el flujo indispensable del PDF; las mejoras de la iteración 01 se explican como pendientes, sin presentarlas como funciones disponibles.

Fecha de revisión: 8 de octubre de 2026. Este documento propone la exposición y los próximos ajustes; no cambia las reglas vigentes ni la aplicación.

## Guion para decir y mostrar

Duración objetivo: 4 minutos 40 segundos, con 20 segundos de margen. Las acciones y los cambios de cuenta están incluidos en cada tramo. Ensayar con cronómetro: el tiempo depende de la captura y de la respuesta del sistema.

| Tiempo | Mostrar | Decir |
|---|---|---|
| 0:00 a 0:20 | Acceso y red de almacenes, con una vista breve de los perfiles. | «IMHOTEP necesita saber qué equipo hay en cada almacén, quién lo tiene y qué debe devolver. Conectamos Kepler, Contratistas y los almacenes de área mediante movimientos que conservan su historia. RH, Compras, almacén y supervisión tienen permisos distintos.» |
| 0:20 a 0:50 | RH registra a un trabajador con puesto, área, contrato vigente y credencial. | «RH registra al trabajador y su periodo de contrato. El puesto permite consultar su dotación recomendada. Almacén ve su identidad y vigencia, pero sus datos personales reservados requieren otro permiso. Si el contrato está vencido, el sistema impide nuevas entregas.» |
| 0:50 a 1:40 | Cuenta de almacén: escanear la credencial, EPP por cantidad y una herramienta por pieza; confirmar con firma y abrir el vale. | «Identificamos al trabajador y escaneamos los artículos. Los guantes se cuentan; esta herramienta tiene un código único. El almacén sale de la cuenta del operador. El sistema muestra existencias, recomendaciones y restricciones. Escanear prepara el vale; al confirmar se valida otra vez, se actualiza el inventario y queda un folio con trabajador, responsable y artículos.» |
| 1:40 a 2:20 | Pedir una cantidad que supera el límite; mostrar naranja; supervisor autoriza con motivo; confirmar. | «El límite se aplica por artículo y trabajador. En consumibles cuenta lo entregado durante el periodo configurado; en retornables cuenta lo que conserva. Aquí lo superamos: la entrega se detiene hasta que un supervisor autorice. La autorización deja nombre y motivo, tiene vigencia y se usa una sola vez.» |
| 2:20 a 2:55 | Escanear un equipo no apto y otro con inspección vencida; mostrar motivos; quitarlos del borrador. | «En alturas, cada pieza tiene estado e inspección. Una pieza no apta o sin inspección vigente queda en rojo: el supervisor no puede saltarse ese bloqueo. Hay que apartarla y resolver su revisión. Si la inspección sigue vigente, pero vence en siete días o menos, aparece un aviso amarillo.» |
| 2:55 a 3:35 | Supervisor envía un traspaso de Kepler a Contratistas; destino recibe; comprobar saldo. | «El traspaso tiene salida y recepción. Mientras viaja, el equipo está en tránsito; no aparece disponible en ambos almacenes. Al recibirlo se registra lo que realmente llegó. La red continúa de Contratistas a Midrex, HYL, Laminador y Minas, conservando origen, destino y responsables.» |
| 3:35 a 4:15 | Iniciar baja, mostrar pendiente, devolver la herramienta y emitir no adeudo. | «Al iniciar la baja, aparecen los equipos retornables pendientes. Los consumibles no generan esa deuda. Escaneamos la herramienta, registramos su condición y la devolvemos. Solo cuando no quedan pendientes se puede emitir el vale de no adeudo. El historial permanece.» |
| 4:15 a 4:40 | Existencias por almacén, ficha del trabajador y bitácora con el folio de la entrega. | «Podemos consultar existencias, resguardos y movimientos: qué salió, de dónde, hacia dónde y quién lo registró. Nuestro valor es una captura sencilla, con control de seguridad y trazabilidad. Las siguientes mejoras son QR desde la ficha, alertas más útiles y aprobación de EPP; después, operación sin conexión.» |

### Video inicial opcional

Si el video forma parte de los cinco minutos, sustituye los primeros 20 segundos; no se suma al guion. Usar tres tomas: almacén, trabajador con herramienta y escaneo real. Voz sugerida: «Una herramienta puede estar en almacén, en tránsito o con un trabajador. IMHOTEP conecta cada entrega con su responsable, evita entregar equipo no apto y muestra lo pendiente al terminar el contrato».

El video abre el problema; la demostración debe realizar operaciones con datos, especialmente si el jurado los proporciona. Evitar un recorrido de pantallas sin confirmar movimientos.

## Preparación para la demostración

1. Tener cuentas de RH, Compras, almacenista de Kepler, supervisor de Kepler y receptor de Contratistas en sesiones separadas. No usar al Administrador para todo: ocultaría la separación de permisos. El receptor puede ser supervisor o almacenista con `traspasos.recibir`.
2. Preparar catálogo, existencias, puesto con dotación y etiquetas legibles. Mostrar brevemente que Compras carga inventario en Kepler; no dedicar el tiempo central a importar un Excel.
3. Elegir un consumible con límite conocido y una herramienta retornable identificada por pieza. Preparar una pieza no apta, una vencida y, si se quiere mostrar el aviso, una que venza dentro de siete días. Comprobar las fechas el día de la exposición.
4. Ensayar una entrega que cruce el límite teniendo en cuenta lo que ya se entregó. No suponer que todo artículo trae límite: debe estar configurado.
5. Dejar listo un traspaso pequeño, con stock suficiente. Mostrar salida y recepción. Para cinco minutos basta Kepler a Contratistas; explicar el siguiente nivel con la red.
6. Usar datos ficticios y mantener contraseñas, PIN, CURP y NSS fuera de la grabación. Probar la cámara en el dispositivo y entorno de la exposición; tener códigos impresos y captura manual como respaldo.
7. Reservar el tiempo final para mostrar pendientes, devolución y saldo. Si sobra tiempo, abrir el historial de una pieza. Si falta, reducir la introducción, sin quitar la prueba de límite o de baja.

## Cobertura del PDF

| Función indispensable | Evidencia en la exposición |
|---|---|
| Acceso y cuatro perfiles | Sesiones y menús de RH, Compras, almacén y supervisor. |
| Catálogo de trabajadores, artículos y almacenes | Alta del trabajador; artículo existente con reglas; red de almacenes. |
| Identificación y lectura | Credencial del trabajador y lectura de un producto y una pieza. |
| Entregas, devoluciones y traspasos | Vales confirmados; salida y recepción del traspaso. |
| Existencias y asignaciones | Saldo del almacén y resguardo del trabajador después de operar. |
| Límite y autorización | Intento bloqueado, aprobación del supervisor y confirmación posterior. |
| Baja con pendientes | Lista previa a devolver y no adeudo posterior. |
| Reportes | Existencias, bitácora y pendientes o adeudos. |
| Caso especial de alturas | Código único, estado e inspección; rojo no autorizable. |

El guion cubre las operaciones indispensables de las páginas 1 y 2. Las infografías también describen contratación, inducción y autorización de seguridad: no afirmar que el software certifica capacitación o autorización de trabajo en alturas. Las habilitaciones del trabajador están pospuestas en el alcance actual.

## Reglas para responder al jurado

| Pregunta o caso | Respuesta operativa | Referencia |
|---|---|---|
| ¿Quién registra al trabajador? | RH, mediante su permiso de administración. Supervisor y almacenista pueden operar con trabajadores según sus permisos; el trabajador registrado no es por ello una cuenta del sistema. | T-01 a T-10, sección 8 |
| ¿De qué almacén se entrega? | Del asignado a la cuenta. Solo quien tiene `almacenes.todos` puede elegir otro dentro del flujo actual. El conjunto de almacenes y almacén activo pertenece a FEAT-013 pendiente. | RG-07, AC-06 |
| ¿Recomendación y límite son lo mismo? | No. Fuera de dotación o por encima de lo recomendado: aviso amarillo y observación. Por encima del límite: naranja y autorización. Sin límite configurado, esa regla no aplica. | D-01 a D-04, E-09, L-01 a L-05 |
| ¿Existe un límite global por trabajador? | El límite actual es por artículo y trabajador. No hay un tope que sume todo su equipo ni límites sumados por categoría. | L-01, alcance |
| ¿Qué se cuenta para el límite? | Retornables: lo que conserva más el vale. Consumibles con periodo: lo entregado en los últimos N días más el vale; sin periodo, solo la cantidad solicitada en el vale. Los renglones repetidos también se acumulan. Devolver un retornable libera su saldo en posesión. | L-02, L-03, L-04 |
| ¿Qué ocurre si vence hoy? | La inspección vale hasta terminar la fecha; hoy avisa en amarillo. Si ya venció o falta, bloquea en rojo. Estado no apto bloquea aunque una fecha anterior siga vigente. | E-05, E-06, E-11 |
| ¿Una autorización permite entregar un arnés no apto? | No. La excepción de consumo no levanta un bloqueo de seguridad. Registrar una inspección debe reflejar la revisión física real, no servir como atajo. | SM-04, A-06, P-01 a P-03 |
| ¿Qué pasa con una inspección capturada mal? | Revisar el historial y usar el flujo permitido de corrección o nueva inspección. El ajuste de vigencia existente tiene límites y permisos; no permite convertir una falla física en aprobación. No prometer edición libre de una inspección. | P-07, servicio de inspecciones |
| ¿Y si no hay stock o la pieza está en otro almacén? | No se entrega desde este almacén. Se consigue mediante un traspaso; confirmar vuelve a comprobar existencias para evitar saldos negativos. | E-03, E-04, RG-04, RG-08 |
| ¿Todo lo que dice «Disponible» puede entregarse? | La consulta actual cuenta piezas aptas, pero la entrega verifica además la inspección vigente. La evaluación del vale es la comprobación final; conviene alinear ese contador como mejora. | E-05, E-06, consulta de existencias |
| ¿El contrato vencido impide devolver? | No. Impide nuevas entregas, pero recuperar lo que tiene el trabajador sigue permitido. | E-02, SM-05 |
| ¿Qué pasa si regresa dañado? | Se registra condición y observación. Una pieza queda no apta; por cantidad, el daño va a Baja. No se calcula un cargo al trabajador. | V-04 a V-06 |
| ¿Puede devolver otra persona? | Una pieza se abona a su titular, aunque la traiga otra persona. Una pieza desconocida no se recibe como si liquidara el pendiente. | V-01, V-12 |
| ¿Qué pasa si se equivocan en un vale? | Se conserva el historial y se corrige mediante cancelación con movimientos inversos; no se borran movimientos ni se editan saldos directamente. | RG-01, RG-02 |
| ¿Se sabe dónde está físicamente todo? | Se conoce la última ubicación registrada: almacén, tránsito o trabajador. Un préstamo entre compañeros fuera del sistema no cambia esa ubicación. No hay geolocalización ni ubicación por pasillo. | C-02, C-03, alcance |
| ¿Se permite Midrex a HYL? | Hoy es ruta no habitual: solo quien tiene `almacenes.todos`, con observación. La autorización específica del supervisor de origen para traslados laterales sigue pendiente en FEAT-015. | X-03, X-16 a X-19 pendientes |

## Qué existe y qué falta

La presencia en el código no sustituye una prueba en el despliegue. Hay documentos que aún dicen «interfaz pendiente» para dotación, pero la pantalla de Entregar ya contiene la hoja de sugerencias.

| Tema | Estado observado | Consecuencia para presentar |
|---|---|---|
| Entrega, devolución, traspaso y baja | Código y prueba integral del guion del PDF presentes. | Ensayar la operación completa en el entorno de exposición. |
| Dotación por puesto | Servidor y hoja de sugerencias en Entregar presentes. | Mostrar faltantes del puesto; no afirmar asignación automática según riesgos del área. |
| No apto y vencimiento | Reglas E-05 y E-06 presentes en el evaluador. | Mostrar rojo y motivo. |
| Inspección próxima a vencer | E-11 y contador en Inicio, ambos con siete días fijos. | Hay aviso básico; no afirmar que faltan todas las alertas. |
| Lista de inspecciones y aviso configurable | FEAT-016 aprobada, pendiente. | Proponer lista accionable con ubicación, vencidas y por vencer. |
| Autorización de excedentes o artículos restringidos | Servicio de autorizaciones presente, resolución remota o con PIN. | Mostrar una excepción real; no confundirla con aprobación universal de EPP. |
| Aprobación de toda entrega de EPP y push | FEAT-014 pendiente; módulo de notificaciones previsto. | Explicar como siguiente mejora. |
| Búsqueda | Consulta actual por nombre o código; piezas también por serie. | La búsqueda por palabras, marca y relevancia ampliada sigue propuesta en FEAT-019. |
| QR en ficha y descarga de etiquetas | Ficha de artículo sin acción de etiqueta. Pantalla Etiquetas imprime desde el navegador. | Falta el acceso directo solicitado; no presentar esa descarga PDF o PNG de artículos como terminada. |
| Bitácora | Reporte por movimientos y seguimiento de piezas y cantidades presentes. | El agrupado por vale y PDF de FEAT-017 sigue pendiente. |
| Valor del inventario | Servicio de totales por ubicación y reporte de valor presentes. | Respetar permiso y alcance. Uso por proyecto del nuevo modelo sigue pendiente. |
| Android sin conexión | Contenedor Android en línea; sincronización de FEAT-020 pendiente. | Presentarlo después del flujo en línea, sin prometer operación offline disponible. |

## Ajustes propuestos en orden

### Primero asegurar el recorrido indispensable

Demostrar el guion entero con datos del jurado, en celular y computadora. Verificar permisos reales, firma, mensajes, aprobación de excedentes, no aptos, contrato vencido, falta de existencias, recepción y baja con pendientes. Mantener la corrección de seguridad en el servidor y los motivos visibles en lenguaje sencillo.

### QR desde la ficha del equipo y búsqueda

Prioridad visible solicitada: abrir el detalle y resolver la etiqueta allí mismo, sin volver a buscar el artículo en otra pantalla.

- **Por cantidad:** botón «Generar etiqueta QR», vista previa del artículo ya elegido y acciones «Descargar PNG» y «Descargar PDF». El QR contiene exactamente el código del producto; sirve también para identificar el estante.
- **Por pieza:** desde la ficha del artículo, botón «Etiquetas de sus piezas», con selección de unidades; desde la ficha de una pieza, «Generar etiqueta QR» para esa unidad. El QR de un arnés identifica esa pieza, nunca únicamente el modelo.
- Mostrar nombre, código y serie si existe. No mostrar costos ni datos personales. Generar una etiqueta no crea inventario ni cambia la ubicación.
- Reutilizar la composición de etiquetas para impresión individual y por lote, con selección ya resuelta. Mantener `etiquetas.imprimir` y validar el alcance; no otorgar ese permiso al almacenista sin una decisión sobre roles. La ficha exige `catalogo.ver`: el script de roles iniciales sí se lo da al almacenista, aunque algunos textos de roles dicen lo contrario. No trae `etiquetas.imprimir`. Verificar los permisos de la cuenta real, porque los roles son configurables.
- Evitar duplicar la búsqueda: nombre, código, marca y serie donde corresponda; priorizar coincidencia exacta; permitir palabras en distinto orden; mostrar ubicación y cantidades dentro del alcance. El escáner debe identificar el código exacto sin esperar la búsqueda de texto.
- Criterios para aceptar el cambio: desde cada ficha se descarga la etiqueta correcta sin buscar de nuevo; PDF y PNG son legibles; escanearlos devuelve el mismo código; el usuario sin permiso no puede generar la etiqueta; otra pieza del mismo modelo conserva su identificador distinto.

Esto concreta FEAT-019. PNG individual y generación dentro de la ficha son propuestas de esta revisión; deben quedar en el brief antes de construir. Si se requieren nuevos endpoints, permisos o dependencias, actualizar sus documentos junto al cambio. No se han agregado ahora.

### Dotación recomendada que se entienda

Usar lo construido por puesto, sin crear un motor nuevo por área para esta demostración. Preparar una dotación común validada por la empresa: casco, lentes, guantes adecuados y calzado; protección auditiva donde aplique. Respirador y filtros, equipo dieléctrico, alturas y complementos dependen de la tarea y de la evaluación de riesgos. La lista del PDF es un ejemplo, no una obligación de dar todo a todos.

«Máscara de gas» no debe agregarse indiscriminadamente: el ejemplo del PDF distingue respirador y filtros. Para explicarlo: «Tenemos una recomendación por puesto; Seguridad define los artículos adecuados y almacén verifica tallas, existencias y restricciones».

Preparar puestos con la base repetida y sus complementos usando el catálogo existente. La sugerencia presenta qué corresponde, qué se ha entregado y qué falta; cada selección pasa por el evaluador. No seleccionar ni entregar automáticamente todo. Mantener diferencia entre aviso por recomendación y bloqueo por límite.

Casos a revisar antes de cargar la dotación: guantes o calzado contados como par frente a pieza; talla correcta; artículos inactivos; recomendaciones mayores que el límite. Para consumibles, «falta» actualmente compara lo entregado desde el inicio del contrato; no representa por sí solo la reposición semanal ni desgaste. Un nuevo cálculo de reposición requiere definir y documentar la regla antes de implementarla.

### Después completar supervisión y alertas

Seguir las dependencias de la iteración 01: FEAT-013 para proyectos y alcance, FEAT-014 para aprobación de EPP y push, FEAT-015 para laterales y FEAT-016 para inspecciones. Conservar la cola de autorizaciones como respaldo: una notificación no equivale a aprobación.

La lista de inspecciones debe llevar a la pieza y decir dónde está, cuándo vence y qué acción puede ejecutar el usuario. Una inspección vencida estando el equipo con un trabajador también debe ser visible; no limitar el aviso al siguiente intento de entrega. No introducir envíos programados por correo o WhatsApp: están fuera del alcance.

Después mejorar agrupación de bitácora, PDF y deudores. La sincronización offline queda al final, una vez estable el flujo en línea.

## Valor del sistema y preguntas de validación

Frase de cierre: «El sistema reduce la incertidumbre: sabemos qué podemos entregar, qué está con cada trabajador y qué debe regresar, con evidencia de cada movimiento».

Interpretación de «encuesta de valor»: incluir tanto indicadores de inventario como preguntas para validar utilidad con el personal. No se han consultado saldos reales ni se atribuyen ahorros medidos.

### Indicadores que conviene mostrar

| Pregunta | Medida que responde |
|---|---|
| ¿Cuánto tengo por almacén? | Unidades por artículo; separar existencia física, disponibilidad, resguardo y tránsito. No sumar dos veces lo enviado y lo recibido. |
| ¿Cuántos productos diferentes tengo? | Número de artículos distintos con stock, separado de las unidades. Diez guantes y tres arneses no son trece productos diferentes. |
| ¿Quién tiene el equipo? | Trabajador, artículo o pieza, cantidad, último vale y ubicación registrada. |
| ¿Qué debe regresar? | Resguardo retornable pendiente por trabajador; excluir consumo como deuda. |
| ¿Qué necesita atención? | Equipo no apto, inspección vencida o próxima a vencer; distinguir el aviso actual de la lista pendiente. |
| ¿Cuánto vale? | Valor calculado con el costo registrado y dentro del permiso y alcance; señalar artículos sin costo. No es una valuación contable de depreciación. |

Mostrar unidades y artículos por almacén aporta valor sin enseñar costos. Los totales en pesos necesitan revisión de permisos; las nuevas restricciones contra deducir un costo unitario desde un total pequeño forman parte de la iteración pendiente.

### Encuesta breve después de usar el flujo

1. Antes de probarlo, ¿cuántos minutos tardabas en saber quién tenía una herramienta? Después, ¿cuánto tardaste? Cronometrar ambos intentos con una tarea comparable.
2. ¿Pudiste completar entrega y devolución sin ayuda? Sí / Con una indicación / Con varias indicaciones / No.
3. ¿Entendiste por qué la entrega se bloqueó y qué podías hacer? Escala de 1 a 5 y comentario.
4. ¿Qué consulta usas más? Existencias por almacén / Equipo con trabajadores / Pendientes de baja / Movimientos / Valor del inventario.
5. ¿Generar el QR desde la ficha evitaría volver a buscar el artículo? Sí / No; describir el paso que sobra.
6. ¿Qué falta para usarlo en un turno real? Una respuesta abierta, anotando rol y almacén, sin datos personales del trabajador.

No prometer porcentajes de ahorro, eliminación de pérdidas ni cumplimiento normativo sin medirlos. Para el hackathon, el resultado comprobable es completar las operaciones y explicar sus restricciones.

## Evidencia y límites de la revisión

- Fuente principal: [PDF del reto](HackaItlacTrack3_2026.pdf), páginas 1, 2, 3, 8 y 10 revisadas visualmente; [transcripción del material](info_track/track-3-imhotep.md) para el contexto completo.
- Reglas: [catálogo de reglas](product/reglas-de-negocio.md), [alcance](product/mvp-scope.md), [arquitectura](architecture/overview.md) y [plan de la iteración 01](releases/iteration_01/README.md).
- Código contrastado: `backend/app/modulos/movimientos/evaluador.py`, `backend/app/modulos/inspecciones/service.py`, servicios de consulta y autorizaciones; ficha de artículo, Etiquetas y dotación de Entregar en el frontend.
- Pruebas existentes revisadas: `backend/tests/test_guion_pdf.py` y `backend/tests/test_guion_extremos.py`. La ejecución de verificación y sus límites se registran en el [reporte de esta revisión](releases/reporte-preparacion-demo.md).
- La exposición no sustituye los entregables del reto: acceso web, usuarios de prueba, código e instalación, descripción de datos y respaldos, y guía de almacén. Revisar [checklist del MVP](releases/mvp-checklist.md) antes de presentar.
