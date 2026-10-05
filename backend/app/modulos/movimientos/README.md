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
| `tipos/devolucion.py`, `cancelacion.py`, `no_adeudo.py` | Stubs (`TipoPendiente`): todo responde 501 `TIPO_NO_IMPLEMENTADO`. |
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
| **CANCELACION** (`tipos/cancelacion.py`) | `vales.cancelar` / `vales.cancelar_todos` | inversos de los del original | K-01 a K-05, X-14 | `bloqueos.vales`; `al_confirmar` pone el original en CANCELADO; `cancelar(servicio, usuario, vale_id, datos)` arma el cuerpo y llama a `servicio.confirmar(usuario, cuerpo, ...)`. Con `rehacer` devuelve el borrador |
| **NO_ADEUDO** (`tipos/no_adeudo.py`) | `no_adeudo.emitir` | ninguno | B-04, B-08, invariante 8 | `construir_movimientos` devuelve `[]`; `al_confirmar` llama `TrabajadorService.marcar_inactivo`; `emitir_no_adeudo(servicio, usuario, trabajador_id, datos)`; 409 `CON_PENDIENTES` si hay pendientes |

TRASPASO y RECEPCION (fase 5) ya están hechos. Cómo funcionan:

- **TRASPASO** (`tipos/traspaso.py`): almacén de la sesión -> EN_TRANSITO; `datos_vale` pone `estado=EN_TRANSITO` y `destino_almacen_id`. `evaluar` trae X-03 en los motivos del vale (verde, amarillo o rojo) y X-02, X-04, X-09 por renglón. Bloquea las existencias (origen, EN_TRANSITO) y las piezas.
- **RECEPCION** (`tipos/recepcion.py`): EN_TRANSITO -> almacén de la sesión, `vale_origen_id` = el traspaso. Bloquea primero el traspaso (`PlanBloqueo.vales`): dos recepciones del mismo traspaso se turnan y la segunda vuelve a evaluar con lo que la primera recibió (X-12 si ya no hay pendiente). `al_confirmar` recalcula lo pendiente (enviado menos recibido en todas las recepciones) y deja el traspaso en RECIBIDO o RECIBIDO_CON_DIFERENCIAS (X-13). Un traspaso con diferencias se puede recibir otra vez hasta completarse. Una recepción sin renglones se rechaza; para "recibir todo" se mandan todos los pendientes.
- **`por_recibir`**: traspasos EN_TRANSITO o con diferencias hacia el almacén de la sesión; `solo_contar=true` solo cuenta (consulta ligera para el contador del inicio). Con `almacenes.todos`, `almacen_id` filtra y sin él trae todos.
- Cambio al motor (aditivo): `por_recibir` y `traspasos_por_recibir` reciben `solo_contar` y `almacen_id`, y el router los toma como parámetros de consulta.

Nota para quien implemente CANCELACION: el límite de consumo (L-03) ya ignora los vales con
`estado = CANCELADO`. Una recepción nunca se cancela (K-04). `por-recibir` y la RECEPCION ignoran los traspasos
`CANCELADO` (rojo X-14 en la evaluación). Si un traspaso con recepciones parciales se puede
cancelar lo decide CANCELACION; la RECEPCION no lo impide.

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
