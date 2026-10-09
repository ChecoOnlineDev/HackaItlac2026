# ADR-015: Operación sin conexión del almacenista, limitada a su almacén

## Estado

Aceptada (8 de octubre de 2026), por decisión del usuario (D-15 del [documento maestro de la iteración 01](../../releases/iteration_01/README.md)).

**Reemplaza parcialmente a [ADR-004](ADR-004-primero-en-linea.md).** La web, la PWA y todos los roles siguen «primero en línea», tolerantes a cortes breves, como dice ADR-004. Solo la **app de Android del almacenista** ([ADR-014](ADR-014-app-android-con-capacitor.md)), en un equipo inscrito, opera sin conexión, y solo lo que dice [FEAT-020](../../features/FEAT-020-app-android-sin-conexion.md).

## Contexto

ADR-004 decidió no sincronizar en el MVP: el PDF no lo pedía, los conflictos son caros y la señal de reevaluación era «en operación real los cortes son largos y frecuentes». En la plática del 8 de octubre de 2026 el track confirmó esa señal: en los contenedores de área y en partes de la planta la red se cae, y el almacenista no puede detener la entrega de herramienta ni la recepción de devoluciones cada vez que pasa.

Al mismo tiempo, la misma plática endureció el control: toda entrega de EPP necesita la aprobación del supervisor salvo que el Administrador dé autonomía (D-06, D-07), y el sistema debe saber en todo momento dónde está cada pieza, sobre todo las de alto valor. Operar sin conexión no puede saltarse esos controles.

Lo que ya existe facilita el camino que ADR-004 dejó preparado: la bitácora solo inserta ([ADR-001](ADR-001-bitacora-de-movimientos.md)), cada vale trae un `id_cliente` generado por el dispositivo y una huella de su cuerpo para reintentos sin duplicar ([ADR-006](ADR-006-identificadores-uuid-y-folio.md)), el folio sale de un contador en la transacción del servidor y el motor vuelve a evaluar con las filas bloqueadas antes de escribir ([ADR-008](ADR-008-bloqueos-del-motor-de-vales.md)).

## Fuerzas y restricciones

- **Una pieza física está en una sola mano** (RG-05). Dos registros que se contradicen sobre la misma pieza no son dos entregas reales: uno de los dos está atrasado o equivocado.
- **Las invariantes de la bitácora no se negocian:** existencias nunca negativas (RG-04), una pieza en una sola ubicación, vales y movimientos que no se editan ni se borran (RG-02), folios consecutivos sin huecos (RG-06), solo `movimientos` escribe.
- **Las reglas viven en el servidor.** El equipo puede evaluar para operar, pero la decisión final es del servidor.
- **Las aprobaciones necesitan red.** El supervisor aprueba desde su celular o con su PIN; el PIN no puede bajar al equipo del almacenista.
- **El paquete debe caber en un celular y en una señal débil**, y no debe llevar costos ni datos personales reservados (RG-12, RG-13, AC-05).
- **El supervisor casi no tiene tiempo** (F-04): lo que le llegue debe ser poco y claro.
- **Va al final del orden de construcción** y compite por tiempo con todo lo demás.

## Alternativas consideradas

1. **Sin conexión total, con resolución automática de conflictos.** Toda la operación (también traspasos, cancelaciones, autorizaciones) funciona sin red, y el servidor resuelve los choques con una política fija (por ejemplo, «gana el último» o «gana el que tenga la hora más vieja»).
2. **Cola con evaluación local limitada al almacén, y conflictos para el supervisor.** Solo el almacenista, solo en su almacén y con los trabajadores de sus proyectos; solo lo que no pide aprobación; el equipo evalúa con las mismas reglas y encola; el servidor revalida al sincronizar y guarda, guarda con avisos o manda a conflictos lo que rompería una invariante, para que lo resuelva una persona.
3. **Nada:** seguir con ADR-004 y llevar un punto de acceso a la planta.

## Decisión

**La alternativa 2.**

- Opera sin conexión **solo** la app de Android, **solo** quien tiene `sincronizacion.operar` en un equipo inscrito, **solo** con los datos del almacén del equipo (catálogo, piezas y existencias del almacén; trabajadores de sus proyectos y de los de sus almacenes hijos, y los que tienen pendientes con él), por un máximo de `SINCRONIZACION_HORAS_MAXIMAS` (24 h) desde la última descarga.
- **Se puede:** devolver, entregar lo que no pide aprobación (herramienta, y EPP con autonomía, en verde o amarillo), recibir traspasos ya descargados, inspeccionar y marcar No apta, y encolar solicitudes de compra.
- **No se puede:** nada que pida aprobación (EPP sin autonomía, renglones naranja), enviar traspasos, cancelar, emitir no adeudo, altas, importación, ajustes de vigencia ni series. Lo que pide aprobación **espera la señal**.
- El equipo evalúa con un evaluador local que replica el subconjunto de reglas, con casos de prueba compartidos con el servidor.
- La cola sube por lotes, en orden de captura, cada operación en su propia transacción, por el servicio de `movimientos` (único que escribe). El servidor **revalida** y clasifica: **guardado**, **guardado con avisos** (reglas de política que hoy no se cumplirían: van a la lista de revisión) o **conflicto** (lo que rompería una invariante: va a `conflicto_sincronizacion` para un supervisor).
- **Nunca hay resolución automática** que descarte o modifique un registro: la decide un supervisor que no capturó la operación, y resolver nunca edita un vale guardado.
- El vale guarda la hora del servidor (`creado_en`) y la del equipo (`capturado_en`) por separado; el folio se asigna al sincronizar.
- Excepciones explícitas a RG-08, RG-09 y RG-11 para lo capturado sin conexión (OF-17 a OF-22); en línea no cambian.

## Justificación

- **Los conflictos son registros atrasados, no entregas dobles.** Como una pieza física solo puede estar en una mano, dos equipos que la registran a la vez no entregaron dos piezas: uno escaneó mal o registró algo que ya no era cierto. Por eso basta con guardar el primero que llega y mostrarle el segundo a una persona que puede averiguar qué pasó (OF-20). Una política automática (alternativa 1) tendría que adivinar cuál de los dos es real, y cualquier regla fija («gana el último», «gana la hora más vieja») se equivoca en algún caso y además depende del reloj del equipo, que no es confiable.
- **Lo que ya pasó físicamente se registra, no se rechaza.** Si el equipo entregó algo con datos atrasados (el límite ya se había cubierto en otro almacén, el trabajador ya estaba en baja), el material ya está con el trabajador. Rechazar el vale dejaría la bitácora diciendo que sigue en el almacén, que es peor para «saber en todo momento dónde está cada pieza». Se guarda con aviso y se revisa; nadie «autoriza» después del hecho.
- **Limitar al almacén reduce el paquete y los conflictos.** Un almacén de área tiene cientos de trabajadores, no miles; su paquete pesa menos de 100 KB comprimido. Y casi todo choque posible ocurre dentro del mismo almacén, entre sus propios equipos, donde el supervisor conoce a la gente y el material.
- **Las aprobaciones no se debilitan.** Lo que pide aprobación espera la señal; sin conexión no hay PIN ni aprobación remota. El control que pidió el track en la misma plática queda intacto.
- **Encaja con lo que ya existe.** La bitácora de solo inserción, el `id_cliente`, la huella del cuerpo, el contador de folios y la revaluación con bloqueos ya hacen casi todo lo que la sincronización necesita; la alternativa 2 solo agrega la clasificación del resultado y la cola de conflictos.
- **La alternativa 3 no responde a la plática.** Un punto de acceso no cubre los contenedores ni los turnos de noche, y el track lo pidió explícitamente.

## Consecuencias positivas

- El almacenista no se detiene por un corte de señal en lo que más se hace: entregar herramienta, recibir devoluciones y recibir traspasos.
- Las invariantes de la bitácora se conservan: ninguna operación sincronizada rompe RG-02, RG-04, RG-05 ni RG-06; `verificar` sigue dando 0.
- Lo atrasado queda marcado (`capturado_sin_conexion`, `capturado_en`, `dispositivo_id`) y lo dudoso queda en la lista de revisión o en conflictos, con su regla.
- El servidor sigue siendo la única fuente de verdad; el equipo nunca le impone un folio, un saldo ni una existencia.
- La web y los demás roles no cambian.

## Consecuencias negativas

- **Dos implementaciones del subconjunto de reglas** (Python y TypeScript) que pueden divergir; se mitiga con casos compartidos, pero exige disciplina en cada cambio de regla.
- **Trabajo nuevo para el supervisor:** resolver conflictos. Se espera que sean pocos, pero alguien tiene que verlos (contador en su Inicio).
- **Los folios ya no siguen el orden de captura** para lo capturado sin conexión, y un vale puede aparecer en la bitácora horas después de la entrega.
- **Datos de hasta 24 horas** para evaluar: un límite o una vigencia pueden evaluarse con información vieja; se compensa con la revaluación y la revisión.
- **Riesgo de pérdida** si el equipo se desinstala o se borra con cola pendiente; se mitiga con avisos, MDM y la vigilancia de equipos sin subir, pero no se elimina.
- Más superficie de seguridad: datos del almacén y firmas en el equipo (base cifrada, borrado remoto, credencial local).
- Más tablas, endpoints, un módulo nuevo (`sincronizacion`) y pruebas de integración de sincronización.

## Señales para reevaluar

- Los conflictos son frecuentes (más de unos pocos por semana por almacén): el paquete está demasiado viejo o los equipos de un mismo almacén chocan seguido; se acorta la ventana, se descarga más seguido o se limita qué se opera sin conexión.
- Los evaluadores divergen en producción (vales guardados con avisos que el equipo había visto verdes sin un cambio real de datos).
- El supervisor no alcanza a resolver los conflictos.
- La señal mejora en la planta y casi no se opera sin conexión: se puede retirar la función sin tocar la web.
- El track pide operar sin conexión otras cosas (traspasos, autorizaciones, otros roles) o en otros almacenes completos: eso ya es la alternativa 1 y pide otro ADR.
