# ADR-012: El proyecto como entidad propia y el alcance por un conjunto de almacenes

## Estado

Aceptada (8 de octubre de 2026), sin construir. La pide la [iteración 01](../../releases/iteration_01/README.md) (D-01 a D-05 y D-13) y la detalla [FEAT-013](../../features/FEAT-013-proyectos-y-supervision-por-almacenes.md). Cambia AC-06 y AC-12 ([reglas](../../product/reglas-de-negocio.md), sección 8) y resuelve el «periodo por apertura» que FEAT-008 dejó pospuesto.

## Contexto

Hasta ahora el sistema tenía dos simplificaciones que la plática del 8 de octubre de 2026 rompe:

1. **«Proyecto» era un almacén.** Los almacenes de tercer nivel (Midrex, HYL, Laminador, Minas; tipo `PROYECTO`) hacían de proyecto, y el trabajador solo tenía un texto libre, `periodo_contrato.area_obra`. No había fechas de proyecto, ni lista de quién trabaja en él, ni forma de contar su consumo. Además, el EPP sale de Contratistas: contado por el almacén que entrega, el consumo de un mantenimiento de Midrex aparecía como de Contratistas.
2. **Un usuario tenía un solo almacén o todos.** AC-06 decía «ve el suyo o todos» y `usuario.almacen_id` era a la vez el alcance de lectura y el almacén donde se opera. La plática pide que un supervisor pueda llevar varios almacenes y saltar entre ellos (D-04), aunque lo normal sea uno (D-01).

FEAT-008 había pospuesto el «periodo por apertura»: cada vez que un almacén de proyecto se reactiva, un ciclo con su apertura y su cierre, con una tabla `almacen_ciclo` y cada vale ligado a su ciclo. Mientras tanto, el reporte de cierre se pedía por rango de fechas a mano.

## Fuerzas y restricciones

- **Flujo normal primero (D-01).** Un supervisor en un almacén y un trabajador en un proyecto. Lo demás se soporta sin complicar ese caso: ni una pantalla debe cambiar para quien tiene un solo almacén.
- **El consumo es del proyecto, no del almacén que entrega (D-13).**
- **Los almacenes de tercer nivel se conservan (D-02).** Siguen siendo lugares físicos con existencias, folios y personal.
- **AC-06 se aplica en unos 20 servicios** y lo prueban decenas de archivos; un cambio de alcance mal hecho abre o cierra datos sin aviso.
- **AC-23:** el rol, los permisos y el almacén se leen de la base en cada petición; los tokens no llevan nada de eso.
- **Movimientos y vales no se modifican** (ADR-001): lo que se ligue al vale tiene que escribirse al insertarlo.
- **Solo el módulo `movimientos` escribe vales.**
- Hackathon: poco tiempo, y la app sin conexión del almacenista (FEAT-020) va al final y depende de este alcance.

## Alternativas consideradas

### Parte 1: qué es un proyecto

1. **Usar el almacén tipo `PROYECTO` como proyecto.** Sin tablas nuevas: el trabajador apuntaría a un almacén. Pero un almacén se reactiva para el siguiente mantenimiento con la misma clave (decisión de FEAT-008), así que dos mantenimientos de Midrex serían el mismo «proyecto»; no hay fechas propias; Contratistas no puede tener «personal general» sin volverse proyecto; y el reporte por proyecto seguiría necesitando el periodo por apertura.
2. **Seguir con el texto `area_obra`.** Cero cambios de modelo. Pero un texto libre no se puede sumar con confianza («Midrex», «MIDREX», «Mtto Midrex»), no tiene almacén, ni fechas, ni estado, y no permite que el supervisor vea «sus» proyectos.
3. **Entidad nueva `proyecto`**, con clave, nombre, almacén, inicio, fin estimado y estado, más `asignacion_proyecto` (el trabajador en un proyecto) y `vale.proyecto_id` (el proyecto de cada entrega).

### Parte 2: cómo tener varios almacenes

1. **Reemplazar `usuario.almacen_id` por una tabla y quitar la columna.** Modelo limpio, pero rompe de golpe todo lo que hoy lee la columna (unos 20 servicios y la interfaz) y obliga a decidir en cada escritura «¿en cuál de sus almacenes?».
2. **Tabla de conjunto y almacén activo por dispositivo**, guardado en `sesion_dispositivo`. Un supervisor podría operar Midrex en el celular y HYL en la tableta a la vez. Pero la sesión deja de ser solo sesión: el alcance de una petición dependería de qué dispositivo la manda, la renovación del token tendría que copiar el almacén activo, AC-23 tendría que leer una cosa del usuario y otra del dispositivo, y las pruebas se duplican. La app sin conexión (FEAT-020) tendría que sincronizar un estado más.
3. **Tabla de conjunto y almacén activo por usuario**, conservando `usuario.almacen_id` como el almacén activo, que siempre pertenece al conjunto.

## Decisión

**Parte 1: la alternativa 3.** El proyecto es una entidad propia del módulo nuevo `proyectos`:

- `proyecto` (`id`, `clave`, `nombre`, `almacen_id`, `inicio`, `fin_estimado`, `estado` ACTIVO o CERRADO, `cerrado_en`, `motivo_cierre`, `creado_por`, `creado_en`). Puede pertenecer a cualquier almacén activo; lo normal es uno de tercer nivel.
- `asignacion_proyecto` (`id`, `trabajador_id`, `proyecto_id`, `inicio`, `fin`, `principal`, `creado_por`, `creado_en`, `terminada_en`, `terminada_por`). Lo normal es una activa por trabajador.
- `vale.proyecto_id`, que escribe `movimientos` al insertar la ENTREGA (y la CANCELACION, que lo hereda) y que no cambia nunca.
- Los almacenes de tercer nivel se conservan; un almacén puede tener varios proyectos a lo largo del tiempo, y uno sin proyectos activos genera un aviso (PR-12), nunca un cierre automático.

**Parte 2: la alternativa 3.** Tabla `usuario_almacen` (`usuario_id`, `almacen_id`, `asignado_por`, `asignado_en`) del módulo `acceso`, y `usuario.almacen_id` se conserva como **almacén activo**:

- Las **lecturas** abarcan todo el conjunto; las **escrituras** se hacen en el almacén activo (AC-37, AC-38).
- El activo se cambia con `PUT /api/sesion/almacen`, solo a un almacén del conjunto, y aplica desde la siguiente petición en todos los dispositivos del usuario (AC-39).
- `almacenes.todos` no cambia: no necesita conjunto.
- El alcance se calcula en un solo lugar, `AccesoService.alcance_del_usuario(usuario)`, que devuelve `(todos, almacenes, activo)`. Vive en `acceso` porque es el dueño de `usuario_almacen` y `core` no importa módulos. `en_alcance` y `exigir_mismo_almacen` se reescriben sobre él y los servicios migran uno por uno.

## Justificación

- **Parte 1.** Solo la entidad nueva separa el lugar (almacén, que se reactiva y conserva su historial) del trabajo (proyecto, con fechas y gente). Permite el personal general de Contratistas sin inventar almacenes, y deja que el consumo se cuente por el proyecto del trabajador aunque entregue otro almacén (D-13). Como el vale guarda el proyecto al insertarse, el historial no cambia si el trabajador cambia de proyecto o el proyecto se cierra, en línea con ADR-001.
- **Parte 2, por qué conservar la columna.** Para el caso normal (un almacén) la columna sigue diciendo lo mismo que hoy, así que el código que la lee sigue siendo correcto mientras se migra. La migración solo copia cada `usuario.almacen_id` a `usuario_almacen`: nadie pierde ni gana acceso.
- **Parte 2, por qué por usuario y no por dispositivo.** Es más simple: el alcance de una petición depende solo del usuario, que AC-23 ya lee de la base en cada petición; la sesión por dispositivo (AC-14 a AC-24) no cambia; las pruebas no se multiplican por dispositivo. El caso que lo justificaría (un supervisor operando dos almacenes a la vez en dos equipos) no es el flujo normal ni apareció en la plática. El riesgo de que un equipo «se mueva» de almacén por un cambio en otro ya está cubierto: un vale capturado en el almacén anterior se rechaza con 409 `ALMACEN_CAMBIO` y su borrador se conserva (AC-13).
- **Resuelve el periodo por apertura.** El ciclo que pedía `almacen_ciclo` es, en la práctica, el proyecto: tiene inicio, fin estimado y cierre, y cada entrega queda ligada a él. El reporte de un mantenimiento se pide por proyecto, con sus fechas, sin tabla de ciclos. Si el mismo almacén de Midrex vuelve a abrirse, el mantenimiento nuevo es otro proyecto en el mismo almacén.

## Consecuencias positivas

- El supervisor ve el uso y el valor por proyecto, incluido lo que entregó Contratistas a su gente (TB-05, TB-06).
- RH asigna a los trabajadores a un proyecto real en el alta, y la entrega lo toma sola en el caso normal (PR-08).
- Un supervisor puede llevar varios almacenes sin dos cuentas, y con un solo almacén nada cambia en pantalla.
- El alcance queda en un solo helper, más fácil de probar que la lógica repartida de hoy.
- Se cierra un pendiente de FEAT-008 (periodo por apertura) sin una tabla de ciclos.

## Consecuencias negativas

- Tres tablas y una columna nuevas, un módulo nuevo y tres permisos nuevos (`proyectos.ver`, `proyectos.administrar`, `proyectos.asignar`).
- Migrar AC-06 toca muchos servicios y pruebas; mientras dure, conviven el helper y lecturas directas de `usuario.almacen_id`, que solo son correctas para conjuntos de un almacén.
- Los trabajadores que ya existen quedan sin proyecto hasta que RH los asigne, y sus entregas piden observación (PR-10).
- El resguardo por artículos por cantidad se atribuye al proyecto de la última entrega (TB-06): es una regla, no un dato exacto.
- Con el almacén activo por usuario, un supervisor no puede operar dos almacenes a la vez en dos equipos.
- Hay dos atribuciones conviviendo: el almacén que entregó (bitácora, «Lo más usado») y el proyecto del trabajador (uso por proyecto). La interfaz debe decir en cada vista qué cuenta.

## Señales para reevaluar

- **Un supervisor necesita operar dos almacenes a la vez en dos equipos** (por ejemplo, celular en Midrex y tableta en HYL en el mismo turno) y los 409 `ALMACEN_CAMBIO` se vuelven frecuentes: pasar el almacén activo a `sesion_dispositivo`, dejando el conjunto en `usuario_almacen`.
- **Los conjuntos de más de un almacén se vuelven lo normal**, no la excepción: revisar si las pantallas deben dejar de optimizarse para un almacén.
- **Se pide el costo histórico** del uso por proyecto: guardar el costo en el movimiento (otro ADR).
- **El resguardo por proyecto no cuadra** con lo que reportan los supervisores: ligar cada unidad en resguardo a su vale de entrega en vez de usar la última entrega.
- **Hace falta presupuesto o topes por proyecto**: el proyecto ya es entidad y puede crecer, pero sería otra feature.
