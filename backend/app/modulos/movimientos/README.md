# Módulo `movimientos`: el motor de vales

Dueño de `vale`, `movimiento`, `existencia` y `serie_folio`, y el único que cambia
`pieza.ubicacion_id`. Evalúa el semáforo, confirma vales, asigna folios y consulta vales. El motor
es **genérico**: no conoce las reglas de ningún tipo de vale. Cada tipo vive en su archivo de
`tipos/` y le da sus ganchos al motor.

## Archivos

| Archivo | Qué es |
|---|---|
| `evaluador.py` | Funciones **puras** (sin base de datos): una por regla (`regla_e06_inspeccion`, `regla_limite`...), los hechos (`Hechos*`), `Motivo`, `peor_nivel` (SM-01) y los evaluadores de renglón de ENTREGA y ENTRADA (orden SM-06). |
| `cargador.py` | `Cargador`: reúne de la base los hechos (identifica códigos, trabajador y su ficha, existencias, cuenta del límite, dónde está una pieza). No escribe. |
| `contexto.py` | Tipos que el motor y los tipos se pasan: `ContextoVale`, `Evaluacion`, `RenglonEvaluado`, `PlanBloqueo`, `MovimientoNuevo`, `DatosVale`. |
| `tipos/base.py` | El contrato: `ManejadorTipo` (y `TipoPendiente`, el stub). |
| `tipos/__init__.py` | La tabla `TIPOS`: un manejador por `TipoVale`. |
| `tipos/entrada.py`, `tipos/entrega.py`, `tipos/traspaso.py`, `tipos/recepcion.py` | Los tipos completos. |
| `evaluador_traspasos.py`, `repository_traspasos.py`, `schemas_traspasos.py` | Lo propio de los traspasos: reglas puras (X-02 a X-04, X-09, X-10, X-12, X-13), consultas de lo enviado y lo recibido, y el contrato de `por-recibir`. |
| `tipos/cancelacion.py`, `tipos/cancelacion_reglas.py`, `schemas_cancelacion.py` | La CANCELACION: genérica (ver abajo, "La cancelación"), sus reglas puras (K-03, K-04, X-14) y su respuesta (`CancelacionOut`, `BorradorOut`). |
| `tipos/devolucion.py`, `no_adeudo.py` | Stubs (`TipoPendiente`): todo responde 501 `TIPO_NO_IMPLEMENTADO`. |
| `service.py` | `MovimientoService`: permisos por tipo, `evaluar`, `confirmar`, consultas. Controla commit y rollback. |
| `repository.py` | Consultas, bloqueos `FOR UPDATE` e inserciones. Nunca hace commit. |
| `router.py`, `schemas.py`, `exceptions.py` | HTTP, contratos y errores de dominio. |
| `verificador.py` | Punto de extensión de A-06 que usa el router de `autorizaciones`. |
| `datos_prueba.py` | Carga las existencias iniciales con vales de ENTRADA reales. |

## Cómo corre una confirmación (`POST /api/vales`)

`MovimientoService.confirmar`:

1. **Permiso por clave** del tipo (`manejador.permiso`) y `manejador.validar_cuerpo(cuerpo, confirmar=True)`
   (campos propios; la ENTREGA exige la firma aquí, F-02). Sin tocar la base.
2. **Idempotencia**: si el `id_cliente` ya existe, responde 200 con ese vale. La misma comprobación
   se repite después de bloquear (una confirmación simultánea con el mismo `id_cliente` gana la
   primera) y el índice único `uq_vale_id_cliente` es la red de seguridad.
3. **Una transacción en READ COMMITTED.** Se hace commit de lo que leyó la autenticación y se
   abre una transacción nueva en READ COMMITTED: en REPEATABLE READ esa lectura fija una foto
   y, tras esperar un bloqueo, las lecturas no verían lo que la otra confirmación guardó. (En las
   pruebas la sesión va dentro de una transacción externa y no se toca el nivel.)
4. **Bloqueos en orden canónico** (`PlanBloqueo`, ver abajo) y `expire_all()`: todo se vuelve a leer.
5. **Volver a evaluar** con `manejador.evaluar`. Un rojo, o un naranja sin autorización válida,
   responde 409 `VALE_CAMBIO` con la evaluación nueva en `detalles` y no escribe nada (RG-08, RG-09).
6. **Autorización** (A-03): `AutorizacionService.validar_para_vale` sobre los renglones naranja.
7. **Folio** de `serie_folio` (`CLAVE-TIPO-000123`), el vale, los movimientos con saldos, las
   existencias y `pieza.ubicacion_id` con el mismo delta, la firma (`adjunto` FIRMA), la
   autorización `USADA`, los códigos del vale (token y folio, RG-10) y `manejador.al_confirmar`.
8. **Commit** (o rollback de todo: ni vale, ni movimientos, ni folio quemado, ni autorización usada).

### Orden canónico de bloqueos

Todos los tipos lo siguen; así dos confirmaciones nunca se interbloquean (si MySQL aun así
detecta un interbloqueo, el motor repite la confirmación hasta 3 veces):

1. vales (`PlanBloqueo.vales`, por id)
2. el trabajador (`PlanBloqueo.trabajador_id`): serializa límites y autorizaciones por trabajador
3. existencias por `(ubicacion_id, articulo_id)` (`PlanBloqueo.existencias`). Las que no existen
   se crean en cero con `INSERT ... ON DUPLICATE KEY UPDATE`, que toma el bloqueo sin la carrera
   de dos inserciones.
4. piezas por `id` (`PlanBloqueo.piezas`)
5. `serie_folio` del almacén y tipo (el motor lo toma solo)

## El contrato `ManejadorTipo` (`tipos/base.py`)

Atributos de clase: `tipo` (`TipoVale`), `permiso` (clave), `requiere_firma`, `firma_modo`.

| Gancho | Para qué | Lo implementa |
|---|---|---|
| `validar_cuerpo(cuerpo, *, confirmar)` | Campos propios, antes de leer la base | opcional |
| `almacen_operativo(servicio, usuario, cuerpo)` | Qué almacén opera el vale | opcional |
| `normalizar_renglones(ctx, cuerpo)` | E-15 y E-16 (pieza repetida se ignora, cantidad repetida suma) | opcional |
| `evaluar(ctx, cuerpo) -> Evaluacion` | El semáforo. **No escribe.** Usa `ctx.cargador` y funciones puras | obligatorio |
| `bloqueos(ctx, cuerpo) -> PlanBloqueo` | Qué filas bloquear | obligatorio |
| `datos_vale(ctx, cuerpo, evaluacion) -> DatosVale` | Trabajador, periodo, destino, `vale_origen_id`, estado inicial, `firma_modo` | obligatorio |
| `construir_movimientos(ctx, cuerpo, evaluacion) -> list[MovimientoNuevo]` | Los movimientos (origen y destino son ubicaciones). Puede crear entidades propias con `flush` (la ENTRADA crea sus piezas) | obligatorio |
| `al_confirmar(ctx, cuerpo, evaluacion, vale, movimientos)` | Efectos propios con el vale ya insertado (inspección inicial, `vale.estado` del original, dejar Inactivo al trabajador) | opcional |
| `por_recibir(servicio, usuario, solo_contar, almacen_id)`, `emitir_no_adeudo`, `cancelar` | Las operaciones de sus endpoints propios | solo RECEPCION, NO_ADEUDO y CANCELACION |

### Ejemplo: enchufar un tipo

```python
# tipos/devolucion.py  (reemplaza el stub; no se toca service.py ni router.py)
class DevolucionTipo(ManejadorTipo):
    tipo = TipoVale.DEVOLUCION
    permiso = P.DEVOLUCIONES_CREAR
    firma_modo = FirmaModo.SESION

    def evaluar(self, ctx, cuerpo):
        evaluacion = Evaluacion()
        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = ctx.cargador.identificar(renglon.codigo)
            motivos = ...  # funciones puras: regla_v01(...), regla_v12(...), con su ID de regla
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=motivos,
                    articulo_id=...,
                    pieza_id=...,
                )
            )
        return evaluacion

    def bloqueos(self, ctx, cuerpo):
        plan = PlanBloqueo(trabajador_id=cuerpo.trabajador_id)
        plan.existencias |= {
            (ubicacion_trabajador_id, articulo_id),
            (ctx.ubicacion_almacen.id, articulo_id),
        }
        return plan

    def datos_vale(self, ctx, cuerpo, evaluacion):
        return DatosVale(trabajador_id=cuerpo.trabajador_id, firma_modo=FirmaModo.SESION)

    def construir_movimientos(self, ctx, cuerpo, evaluacion):
        return [
            MovimientoNuevo(
                renglon=r.renglon,
                articulo_id=r.articulo_id,
                pieza_id=r.pieza_id,
                cantidad=r.cantidad,
                origen_id=...,
                destino_id=ctx.ubicacion_almacen.id,
                condicion=...,
                nivel=r.nivel,
                reglas=motivos_ids(r),
            )
            for r in evaluacion.renglones
        ]
```

La tabla `TIPOS` (`tipos/__init__.py`) ya apunta a la clase del archivo; basta con sustituir el
stub. Las funciones puras de reglas del tipo nuevo van en su archivo de `tipos/` (o en
`evaluador_<tipo>.py`), reutilizando `Motivo`, `Nivel` y `peor_nivel` de `evaluador.py`.

Reglas del motor que el tipo debe respetar: cada motivo lleva el **ID de su regla**; un
`RenglonEvaluado` con rojo no se confirma; solo los naranja se autorizan (`autorizable`); el vale
nunca lleva costos; todo lo que escriba el tipo va con `flush` (el commit es del motor).

## Qué falta (para los siguientes agentes)

Solo llenan el archivo de su tipo (y sus pruebas). Pueden agregar un `evaluador_<tipo>.py` y
sus esquemas en un archivo propio si el cuerpo necesita campos nuevos.

| Tipo | Permiso | Movimientos | Reglas | Ganchos especiales |
|---|---|---|---|---|
| **DEVOLUCION** (`tipos/devolucion.py`) | `devoluciones.crear` | trabajador -> almacén; artículo por cantidad dañado -> BAJA (V-05); pieza dañada entra como No apta (`CatalogoService.actualizar_estado_pieza`) | V-01 a V-07, V-11 a V-14, F-08, **SM-05: nunca se bloquea por E-02** (trabajador no vigente) | `bloqueos`: trabajador, existencias y piezas. La condición (`Condicion`) es obligatoria |
| **NO_ADEUDO** (`tipos/no_adeudo.py`) | `no_adeudo.emitir` | ninguno | B-04, B-08, invariante 8 | `construir_movimientos` devuelve `[]`; `al_confirmar` llama `TrabajadorService.marcar_inactivo`; `emitir_no_adeudo(servicio, usuario, trabajador_id, datos)`; 409 `CON_PENDIENTES` si hay pendientes |

TRASPASO y RECEPCION (fase 5) ya están hechos. Cómo funcionan:

- **TRASPASO** (`tipos/traspaso.py`): almacén de la sesión -> EN_TRANSITO; `datos_vale` pone `estado=EN_TRANSITO` y `destino_almacen_id`. `evaluar` trae X-03 en los motivos del vale (verde, amarillo o rojo) y X-02, X-04, X-09 por renglón. Bloquea las existencias (origen, EN_TRANSITO) y las piezas.
- **RECEPCION** (`tipos/recepcion.py`): EN_TRANSITO -> almacén de la sesión, `vale_origen_id` = el traspaso. Bloquea primero el traspaso (`PlanBloqueo.vales`): dos recepciones del mismo traspaso se turnan y la segunda vuelve a evaluar con lo que la primera recibió (X-12 si ya no hay pendiente). `al_confirmar` recalcula lo pendiente (enviado menos recibido en todas las recepciones) y deja el traspaso en RECIBIDO o RECIBIDO_CON_DIFERENCIAS (X-13). Un traspaso con diferencias se puede recibir otra vez hasta completarse. Una recepción sin renglones se rechaza; para "recibir todo" se mandan todos los pendientes.
- **`por_recibir`**: traspasos EN_TRANSITO o con diferencias hacia el almacén de la sesión; `solo_contar=true` solo cuenta (consulta ligera para el contador del inicio). Con `almacenes.todos`, `almacen_id` filtra y sin él trae todos.
- Cambio al motor (aditivo): `por_recibir` y `traspasos_por_recibir` reciben `solo_contar` y `almacen_id`, y el router los toma como parámetros de consulta.

El límite de consumo (L-03) ignora los vales con `estado = CANCELADO` (la CANCELACION ya está
implementada; ver abajo). Una recepción nunca se cancela (K-04). `por-recibir` y la RECEPCION
ignoran los traspasos `CANCELADO` (rojo X-14 en la evaluación).

## La cancelación (`tipos/cancelacion.py`)

Es el único tipo **genérico**: no conoce las reglas de ningún otro tipo. Trabaja con las filas de
`movimiento` del vale original y las invierte (K-02); el contrato HTTP está en `api-contracts.md`,
"Cancelación".

- `almacen_operativo` es el primer gancho que corre y hace las comprobaciones de quién cancela:
  404 (no existe o fuera de alcance), K-01 (403 si no es suyo y no tiene `vales.cancelar_todos`) y
  X-14 (el almacén de destino de un traspaso no lo cancela). Devuelve el almacén del vale original.
- `evaluar` arma un renglón por movimiento del original (el inverso) con las reglas de
  `cancelacion_reglas.py`. Con las filas ya bloqueadas (`ctx.bloqueado`) un rojo lanza 409
  `NO_CANCELABLE` (no `VALE_CAMBIO`); sin bloquear (`POST /api/vales/evaluar`) devuelve el semáforo.
- K-03 para una pieza: debe seguir en el destino del movimiento y ningún otro vale puede haberla
  movido después (`repository.hay_movimiento_posterior_de_pieza`, por fecha y `id` UUID v7). Para un
  artículo por cantidad: la existencia del destino original debe alcanzar (se acumula por renglón).
  Las existencias por cantidad son fungibles: no se rastrea de qué entrega salió cada unidad.
- `bloqueos`: el vale original, su trabajador, las existencias de origen y destino de cada
  movimiento (PROVEEDOR no lleva) y sus piezas. Dos cancelaciones simultáneas del mismo vale se
  serializan en el bloqueo del vale: la segunda ve `CANCELADO` y responde K-03.
- `al_confirmar` pone el original en `CANCELADO` y registra la auditoría `vale.cancelar` (K-01:
  entra a la lista de revisión).
- `cancelar` (endpoint) arma un `ConfirmarIn` con `vale_origen_id` y `observacion = motivo` y llama
  a `servicio.confirmar`: folio, idempotencia por `id_cliente`, transacción y bloqueos son los del
  motor. Con `rehacer` agrega el `borrador` (K-05).
- Cambios aditivos al motor, por esta tarea: `NoCancelable` en `exceptions.py`; `cancelacion_de` y
  `hay_movimiento_posterior_de_pieza` en `repository.py`; `ValeDetalleOut.cancelacion` (el original
  CANCELADO muestra folio y motivo de su cancelación) en `schemas.py`/`service.detalle`; el endpoint
  responde 201 o 200 (repetido) en `router.py`.

### Qué no revierte una cancelación

La cancelación solo invierte movimientos (existencias, resguardo, `pieza.ubicacion_id`) y marca el
original. Los efectos propios de un tipo que no son un movimiento **no se revierten**:

| Tipo cancelado | Lo que se queda como estaba después de cancelar |
|---|---|
| ENTRADA | La pieza creada sigue en el catálogo (queda en PROVEEDOR, sin ubicación en un almacén) con su código y su serie: un código identifica una sola cosa (RG-10). La inspección inicial registrada queda en su historial. |
| ENTREGA | La autorización que usó queda USADA y no se libera (A-03). |
| DEVOLUCION | Una pieza devuelta dañada quedó No apta (V-05): la cancelación la devuelve al trabajador pero **no la rehabilita**; si de verdad no estaba dañada, se inspecciona. Lo que se dio de baja (artículos por cantidad dañados, BAJA) sí regresa al trabajador. |
| TRASPASO | Sin efectos propios: la existencia regresa al almacén de origen. |
| Todos | La firma del original y su "Validó" no se tocan; los ve el vale original, que sigue visible. |

## Integración con otros módulos

- **autorizaciones**: `validar_para_vale` y `marcar_usada` corren en la transacción del vale;
  `datos_valido` arma el "Validó" (A-04). `verificador.crear_verificador(session, usuario)` lo
  toma el router de `autorizaciones` para rechazar los rojos al solicitar (A-06).
- **inspecciones**: la ENTRADA llama `InspeccionService(session).registrar_inicial(pieza_id, *,
  fecha, resultado, observacion, usuario_id)` (solo flush) por `entrada.servicio_inspecciones`,
  el punto de enchufe que las pruebas sustituyen por un doble.
- **catalogo**: `registrar_pieza` (la pieza y su código), `identificar_codigo`, `obtener_articulo`.
- **trabajadores**: `ficha_breve` (vigencia, resguardo, E-12), `periodo_vigente`.
- **consulta** puede usar `MovimientoService.detalle(vale)`, `obtener`, `obtener_por_token` y
  `listar`, o leer las tablas directamente (solo lectura).
