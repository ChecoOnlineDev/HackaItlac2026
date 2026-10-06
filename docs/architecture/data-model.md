# Modelo de datos

Entidades, relaciones e invariantes del MVP. Es también el entregable del PDF "descripción breve de la estructura de datos". Los nombres van en español, sin acentos ni ñ.

Estado: las 21 tablas existen en la migración inicial `0001_esquema_inicial` (Fase 0). Los modelos están en el `models.py` del módulo dueño de cada tabla.

## Idea central

Todo artículo está siempre en una **ubicación**: un almacén, un trabajador o una ubicación virtual. Toda operación es un **movimiento** de una ubicación a otra, agrupado en un **vale**. Los movimientos no se modifican; las **existencias** son su suma, guardada para consultar rápido ([ADR-001](decisions/ADR-001-bitacora-de-movimientos.md)).

```
categoria 1─N articulo 1─N pieza
                 │           │
almacen ─┐       │           │ ubicación actual
trabajador ─┼─ ubicacion ─── existencia (ubicacion, articulo, cantidad)
virtual ─┘       │
                 └── movimiento N─1 vale
```

## Identificadores

Decisión completa en [ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md).

- Cada tabla tiene un `id` **UUID versión 7**, generado por el servidor. Las excepciones usan su llave natural: `codigo` (el propio código) y las de llave compuesta: `existencia`, `serie_folio` y `rol_permiso`.
- Las personas no ven el UUID. Lo que se lee, se imprime y se escanea es otro dato:

| Entidad | Lo que ve la persona |
|---|---|
| Vale | Folio, por ejemplo `KEP-ENT-000123` |
| Trabajador | Número de empleado y código de su credencial |
| Artículo | Código |
| Pieza | Código y número de serie |
| Almacén | Clave |
| Usuario | Nombre de usuario |

- El **folio** no sale del `id` ni de calcular el máximo más uno. Sale de `serie_folio`, un contador por almacén y tipo de vale que se bloquea y avanza en la misma transacción que guarda el vale. Así no se repite aunque dos personas confirmen a la vez, ni deja huecos si una operación falla.
- `vale.id_cliente` es otro UUID, que genera el dispositivo, para que un reintento no duplique el vale.

## Tablas

### Personas y acceso

| Tabla | Campos | Notas |
|---|---|---|
| `usuario` | `id`, `nombre`, `usuario`, `contrasena_hash`, `pin_hash`, `rol_id`, `almacen_id`, `activo`, `creado_en`, `intentos_fallidos`, `bloqueado_hasta`, `pin_intentos_fallidos`, `pin_bloqueado_hasta`, `version_sesion` | `usuario` es único. Cada usuario tiene un rol. `almacen_id` es su almacén asignado, uno solo por usuario; varios usuarios pueden compartir almacén (RG-07). Puede ir vacío si su rol tiene `almacenes.todos`. `pin_hash` solo en quien puede autorizar. Bloqueo por intentos: cinco contraseñas fallidas seguidas ponen `bloqueado_hasta` cinco minutos adelante (429 `DEMASIADOS_INTENTOS`) y reinician `intentos_fallidos`; un acierto lo reinicia. El PIN tiene su propio contador (`pin_intentos_fallidos`, `pin_bloqueado_hasta`). El conteo bloquea la fila del usuario (`FOR UPDATE`) antes de verificar la clave, así que las ráfagas se atienden de una en una. `version_sesion` (entero, 0 por defecto, migración `0002_version_sesion`) va dentro del token de acceso (`ver`) y de cada fila de `sesion_dispositivo`: el token solo sirve si coincide con la de la base; «cerrar todas», restablecer contraseña o PIN e inactivar o reactivar al usuario la incrementan, y con eso se revocan todos los tokens de acceso y de renovación anteriores. Cerrar la sesión de un solo dispositivo NO la incrementa (revoca esa familia en `sesion_dispositivo`). |
| `sesion_dispositivo` | `id`, `usuario_id`, `familia_id`, `refresh_hash`, `version_sesion`, `creado_en`, `inicio`, `ultimo_uso`, `expira_en`, `vence_absoluto`, `revocada_en`, `motivo_revocacion`, `reemplazada_por`, `agente` | Un token de renovación por fila (AC-14 a AC-24; migración `0005_sesion_dispositivo`). `familia_id` identifica al dispositivo: la crea el inicio de sesión y la comparten todas sus renovaciones; el token de acceso la lleva (`fam`). `refresh_hash` es la huella SHA-256 (hex, única) del token de renovación: el token en claro nunca se guarda. Cada renovación inserta una fila nueva de la familia y deja la anterior con `revocada_en`, `motivo_revocacion = 'rotada'` y `reemplazada_por` (sin llave foránea: las familias se borran completas). La fila sin `revocada_en` es la vigente de la familia; una familia abierta tiene exactamente una. `inicio` y `vence_absoluto` (`inicio` + `REFRESH_TOPE_DIAS`) no cambian al renovar; `expira_en` (ventana de `REFRESH_DIAS`, nunca más allá de `vence_absoluto`) y `ultimo_uso` sí. `version_sesion` es la del usuario al emitir la fila. `motivo_revocacion`: `rotada`, `salida`, `salida_todas`, `salida_otras`, `version` (la versión del usuario cambió), `reutilizacion` (un token ya rotado se usó fuera de la tolerancia), `nueva_entrada` (el mismo navegador volvió a entrar), `vencida`. `agente` es el navegador y sistema resumidos, hasta 120 caracteres; no se guarda la IP. `usuario_id` borra en cascada. Al iniciar sesión se purgan las familias cuyo `vence_absoluto` pasó hace más de un día. |
| `rol` | `id`, `nombre`, `descripcion`, `protegido`, `activo`, `creado_en` | `nombre` único. `protegido` marca al Administrador, que no se elimina ni pierde `acceso.administrar`. |
| `rol_permiso` | `rol_id`, `permiso` | Llave: ambas columnas. `permiso` es una clave del catálogo, como `entregas.crear`. El catálogo vive en el código, no en una tabla (AC-01). |
| `trabajador` | `id`, `numero_empleado`, `nombre`, `curp`, `nss`, `tallas`, `foto_adjunto_id`, `estado`, `creado_en` | `numero_empleado` único; `curp` único si existe. `estado`: ACTIVO, BAJA_EN_PROCESO, INACTIVO. `foto_adjunto_id` va vacío si el trabajador no tiene foto (T-09). |
| `periodo_contrato` | `id`, `trabajador_id`, `puesto`, `puesto_id`, `area_obra`, `referencia`, `inicio`, `fin`, `creado_por`, `creado_en` | Un renglón por contrato o reingreso. El vigente es el más reciente. `puesto` es el texto capturado y `puesto_id` (opcional, FK a `puesto`) lo liga al catálogo; de él sale la dotación. Un texto que no coincide con ningún puesto deja `puesto_id` vacío y el trabajador sin dotación. |

### Lugares

| Tabla | Campos | Notas |
|---|---|---|
| `almacen` | `id`, `clave`, `nombre`, `tipo`, `padre_id`, `estado`, `creado_en`, `cerrado_en` | `clave` única (KEP, CON, MID, HYL, LAM, MIN). `tipo`: CENTRAL, SUBALMACEN, PROYECTO. `padre_id` arma la red: Kepler, Contratistas, áreas. |
| `ubicacion` | `id`, `tipo`, `almacen_id`, `trabajador_id`, `virtual` | Exactamente uno de los tres últimos tiene valor. `virtual`: PROVEEDOR, EN_TRANSITO, CONSUMIDO, BAJA. Se crea una al dar de alta cada almacén y cada trabajador. |

### Catálogo

| Tabla | Campos | Notas |
|---|---|---|
| `categoria` | `id`, `nombre`, `tipo`, `control`, `retornable`, `requiere_inspeccion`, `vigencia_inspeccion_dias`, `requiere_autorizacion`, `motivo_uso_especial`, `limite_cantidad`, `limite_periodo_dias`, `cantidad_aviso`, `activo` | `tipo`: EPP, HERRAMIENTA. Los campos de regla son la plantilla que se copia al artículo (CF-02). |
| `articulo` | `id`, `codigo`, `nombre`, `marca`, `modelo`, `categoria_id`, `control`, `retornable`, `talla`, `unidad`, `costo_unitario`, `requiere_inspeccion`, `vigencia_inspeccion_dias`, `requiere_autorizacion`, `motivo_uso_especial`, `limite_cantidad`, `limite_periodo_dias`, `cantidad_aviso`, `activo`, `motivo_inactivacion`, `creado_en` | `control`: PIEZA, CANTIDAD. Guarda sus propias reglas; las de la categoría solo son el punto de partida. `limite_periodo_dias` vacío significa "en posesión" (L-05). `cantidad_aviso` vacío significa que no hay aviso de cantidad inusual (E-27). |
| `pieza` | `id`, `articulo_id`, `codigo`, `numero_serie`, `estado`, `inspeccion_vigente_hasta`, `ubicacion_id`, `creado_en` | `estado`: APTO, NO_APTO, EN_MANTENIMIENTO, EN_CALIBRACION, BAJA. `ubicacion_id` la actualiza solo el motor. |
| `codigo` | `codigo`, `tipo`, `ref_id` | Registro único de todo lo que se escanea. `tipo`: TRABAJADOR, ARTICULO, PIEZA, VALE. Un trabajador puede tener varios códigos. |
| `puesto` | `id`, `nombre`, `activo`, `creado_en` | `nombre` único sin distinguir mayúsculas ni acentos. Se inactiva, no se borra. |
| `dotacion` | `id`, `puesto_id`, `articulo_id`, `cantidad` | La cantidad recomendada de un artículo en un puesto (D-01). `(puesto_id, articulo_id)` único, `cantidad >= 1`. La cantidad no pasa del `limite_cantidad` del artículo (D-04): lo verifica el servicio, no la base. |

### Bitácora

| Tabla | Campos | Notas |
|---|---|---|
| `vale` | `id`, `id_cliente`, `tipo`, `folio`, `almacen_id`, `trabajador_id`, `periodo_contrato_id`, `destino_almacen_id`, `vale_origen_id`, `estado`, `responsable_id`, `autorizacion_id`, `observacion`, `firma_modo`, `firma_adjunto_id`, `token`, `dispositivo`, `creado_en`, `huella_cuerpo` | `id_cliente`, `folio` y `token` son únicos. `huella_cuerpo` (SHA-256 del cuerpo canónico con el que se confirmó, sin la imagen ni el trazo de la firma; migración `0003_huella_cuerpo`) permite rechazar con 409 un reintento con el mismo `id_cliente` y otro cuerpo; es nula en los vales anteriores y en los que no salen de `POST /api/vales`. `tipo`: ENTRADA, ENTREGA, DEVOLUCION, TRASPASO, RECEPCION, NO_ADEUDO, CANCELACION. `estado`: EMITIDO, EN_TRANSITO, RECIBIDO, RECIBIDO_CON_DIFERENCIAS, CANCELADO. `firma_modo`: PANTALLA cuando firma el trabajador, SESION cuando basta la sesión del responsable. `vale_origen_id` liga una recepción con su traspaso, y una cancelación con el vale que cancela. |
| `movimiento` | `id`, `vale_id`, `renglon`, `articulo_id`, `pieza_id`, `cantidad`, `origen_id`, `destino_id`, `trabajador_id`, `condicion`, `motivo_baja`, `nivel`, `reglas`, `observacion`, `saldo_origen`, `saldo_destino`, `creado_en` | Solo se inserta. `origen_id` y `destino_id` son ubicaciones. `trabajador_id` anota a quién se atribuye un consumo o una devolución. `condicion`: BUENO, DESGASTE, DANADO. `reglas`: IDs de las reglas que aplicaron. |
| `existencia` | `ubicacion_id`, `articulo_id`, `cantidad` | Llave: ambas columnas. Se actualiza en la misma transacción que el movimiento. |
| `serie_folio` | `almacen_id`, `tipo`, `ultimo` | Un consecutivo por almacén y tipo de vale (RG-06). |

### Control

| Tabla | Campos | Notas |
|---|---|---|
| `autorizacion` | `id`, `almacen_id`, `trabajador_id`, `solicitada_por`, `motivo`, `detalle`, `estado`, `resuelta_por`, `medio`, `creado_en`, `resuelta_en`, `vence_en` | `estado`: PENDIENTE, APROBADA, RECHAZADA, VENCIDA, USADA. `medio`: PIN, REMOTA. `detalle`: renglones y regla que la originó. |
| `inspeccion` | `id`, `pieza_id`, `fecha`, `resultado`, `puntos`, `observacion`, `vigente_hasta`, `usuario_id`, `creado_en` | `puntos`: etiquetas, costuras, cintas, herrajes, conectores. |
| `ajuste_vigencia` | `id`, `pieza_id`, `inspeccion_id`, `vigente_hasta_anterior`, `vigente_hasta_nuevo`, `motivo`, `usuario_id`, `creado_en` | Solo se inserta (P-07). Al guardarse, `pieza.inspeccion_vigente_hasta` toma la fecha nueva; la inspección original no cambia. |
| `evento_pieza` | `id`, `pieza_id`, `estado_anterior`, `estado_nuevo`, `observacion`, `usuario_id`, `creado_en` | Cambios de estado que no son inspección. |
| `adjunto` | `id`, `tipo`, `ruta`, `mime`, `tamano`, `sha256`, `vale_id`, `movimiento_id`, `subido_por`, `creado_en` | `tipo`: FIRMA, FOTO_DANO, FOTO_TRABAJADOR. El archivo vive en el volumen, no en la base. |
| `auditoria` | `id`, `usuario_id`, `accion`, `entidad`, `entidad_id`, `antes`, `despues`, `creado_en` | Entradas al sistema, cambios de catálogo, inactivaciones (CF-15). |
| `solicitud_compra` | `id`, `id_cliente`, `huella_cuerpo`, `folio`, `almacen_id`, `solicitante_id`, `articulo_id`, `descripcion`, `cantidad`, `motivo`, `urgencia`, `estado`, `nota_compras`, `vale_entrada_id`, `creada_en`, `actualizada_en` | La solicitud de compra urgente (SC-01 a SC-11, migración `0006_solicitudes_compra`). `id_cliente` y `folio` son únicos. `folio`: `CLAVE-SOL-000001`, del contador del almacén solicitante. `almacen_id` es el del solicitante al pedir. `articulo_id` va vacío si el equipo no está en el catálogo; `descripcion` siempre tiene texto (el nombre del artículo, si lo hay). `urgencia`: URGENTE, NORMAL. `estado`: PENDIENTE, EN_COMPRA, COMPRADA, INGRESADA, RECHAZADA, CANCELADA. `cantidad >= 1` (CHECK). `vale_entrada_id` (FK a `vale`) solo puede tener valor si `estado = INGRESADA` (CHECK `vale_solo_ingresada`); el servicio exige que sea de tipo ENTRADA, no cancelado y dentro del alcance de quien lo liga. `huella_cuerpo` (SHA-256 del cuerpo canónico) rechaza con 409 un reintento con el mismo `id_cliente` y otro cuerpo. No es inventario: no mueve existencias. |
| `solicitud_compra_evento` | `id`, `solicitud_id`, `estado_anterior`, `estado_nuevo`, `usuario_id`, `nota`, `creado_en` | Un renglón por cada cambio de estado, el primero con `estado_anterior` vacío (nace PENDIENTE). Solo se inserta (SC-08): ninguna ruta lo edita o lo borra. |
| `serie_solicitud_compra` | `almacen_id`, `ultimo` | El consecutivo de folios de solicitud por almacén (SC-09). Su fila se bloquea (`FOR UPDATE`) y avanza en la misma transacción que guarda la solicitud: sin huecos ni repetidos. Es aparte de `serie_folio` porque esa tabla es de `movimientos` y su `tipo` es un tipo de vale. |

## Decisiones de implementación

Fijadas al construir las tablas; son parte del contrato para los demás módulos.

- **Cantidades enteras.** `movimiento.cantidad`, `saldo_origen`, `saldo_destino` y `existencia.cantidad` son enteros. Un artículo que se mide en otra unidad (metros, litros) se cuenta en su unidad mínima.
- **Nombres de constraints estables.** `pk_`, `fk_`, `uq_`, `ck_` e `ix_` seguidos de tabla y columnas (por ejemplo `uq_usuario_usuario`, `ck_existencia_cantidad_no_negativa`). El servidor traduce los errores de la base por ese nombre (`app/core/errores_bd.py`). Un CHECK violado llega de MySQL como `OperationalError` (3819), no como `IntegrityError`; por eso los services capturan `DBAPIError`.
- **Enums de dominio** son `StrEnum` guardados como VARCHAR con CHECK (`ck_<tabla>_<columna>`), no como `ENUM` de MySQL.
- **Fechas** `DATETIME(6)` en UTC sin zona; las pone el servidor.
- **Mayúsculas.** La colación es `utf8mb4_0900_ai_ci`: usuarios, códigos y claves son únicos sin distinguir mayúsculas ni acentos.
- **`ubicacion`**: además de que exactamente uno de `almacen_id`, `trabajador_id` y `virtual` tiene valor, `tipo` (ALMACEN, TRABAJADOR, VIRTUAL) debe coincidir con cuál es; cada uno es único (una ubicación por almacén, por trabajador y por tipo virtual).
- **`pieza.ubicacion_id`** puede ir vacía mientras la pieza no tenga su primer movimiento (la entrada). `(articulo_id, numero_serie)` es único.
- **`categoria` y `articulo`**: `requiere_inspeccion` solo con `control = PIEZA` (CHECK); límite, periodo, vigencia y aviso, positivos si existen; un artículo inactivo exige `motivo_inactivacion`; el costo no es negativo.
- **`movimiento`**: `cantidad > 0`, una pieza siempre con cantidad 1, `origen_id` distinto de `destino_id`, `(vale_id, renglon)` único, `nivel` (VERDE, AMARILLO, NARANJA, ROJO). `reglas` es una lista JSON de IDs de regla.
- **`autorizacion`**: `resuelta_por` no puede ser `solicitada_por` (AC-07, A-05).
- **`periodo_contrato`**: `fin >= inicio`.
- **`puesto` y `dotacion`** (migración `0004_puestos_dotacion`): se crean junto con `periodo_contrato.puesto_id`. La migración relaciona los periodos que ya existían con el catálogo por nombre; como el catálogo nace vacío, quedan sin `puesto_id` y sin dotación hasta que se capture el puesto. Un artículo que está en una dotación no se elimina (409) y su límite no baja de lo recomendado (422, D-04).
- **Tallas (E-10).** No se agregó ningún campo: se compara `articulo.talla` con los valores de `trabajador.tallas` (JSON `{prenda: talla}`).
- **Cómo escribe el motor** (módulo `movimientos`; ver `backend/app/modulos/movimientos/README.md`):
  - Una confirmación es una sola transacción en READ COMMITTED que bloquea (`FOR UPDATE`), en este orden, vales, trabajador, `existencia` por `(ubicacion_id, articulo_id)`, `pieza` por `id` y `serie_folio`; vuelve a evaluar y solo entonces escribe.
  - `serie_folio` guarda el último consecutivo por almacén y tipo; su fila se crea en la primera confirmación de ese par. El folio es `CLAVE-PREFIJO-000123`; los prefijos son `ING`, `ENT`, `DEV`, `TRS`, `REC`, `NAD` y `CAN`.
  - Las filas de `existencia` se crean en cero cuando un movimiento llega por primera vez a una ubicación. PROVEEDOR no lleva existencia: sus movimientos dejan `saldo_origen` vacío. `movimiento.saldo_origen` y `saldo_destino` son el saldo de esa ubicación y artículo después del movimiento.
  - `movimiento.creado_en` es el `creado_en` del vale. `reglas` son los IDs de las reglas que dieron motivo al renglón (por ejemplo `["L-02", "E-26"]`); `nivel` es el del renglón: un naranja autorizado queda NARANJA y el vale lleva su `autorizacion_id`. En una entrega, `condicion` es `BUENO` si no se indica (E-22) y `trabajador_id` anota al trabajador también en los retornables.
  - Al confirmar, el vale registra en `codigo` (tipo VALE) su `token`, que es el contenido del QR, y su folio.
  - El límite de consumibles (L-03) suma los movimientos de vales de ENTREGA no cancelados hacia CONSUMIDO con ese trabajador y artículo, creados después de ahora menos N días (una entrega hecha hace exactamente N días ya no cuenta). El de retornables (L-02) usa la existencia del trabajador.
- **Llaves circulares.** `trabajador.foto_adjunto_id` y `vale.firma_adjunto_id` apuntan a `adjunto`, que a su vez apunta a `vale` y `movimiento`; la migración las agrega al final. Al confirmar una entrega, el vale se inserta sin `firma_adjunto_id`, se guarda el adjunto de la firma con su `vale_id` y se completa `firma_adjunto_id`, todo en la misma transacción.
- **Dueños.** `acceso`: usuario, rol, rol_permiso, sesion_dispositivo. `trabajadores`: trabajador, periodo_contrato (lee `puesto` y `dotacion`). `almacenes`: almacen, ubicacion. `catalogo`: categoria, articulo, pieza, codigo, puesto, dotacion. `movimientos`: vale, movimiento, existencia, serie_folio. `autorizaciones`: autorizacion. `solicitudes_compra`: solicitud_compra, solicitud_compra_evento, serie_solicitud_compra (solo LEE `vale`). `inspecciones`: inspeccion, ajuste_vigencia, evento_pieza. `archivos`: adjunto. `auditoria`: auditoria.
- **Lo que no se puede expresar en la base** y queda para los services: que `vale` y `movimiento` no se actualicen (salvo `vale.estado`), que `existencia` sea la suma de los movimientos, que `pieza.ubicacion_id` sea el destino de su último movimiento, que `control` y `retornable` no cambien con movimientos (CF-05), y que siempre exista un usuario activo con `acceso.administrar` (AC-09).

## Qué movimientos genera cada vale

| Vale | Folio | Origen | Destino |
|---|---|---|---|
| ENTRADA | `ING` | PROVEEDOR | Almacén |
| ENTREGA de retornable | `ENT` | Almacén | Trabajador |
| ENTREGA de consumible | `ENT` | Almacén | CONSUMIDO, con el trabajador anotado |
| DEVOLUCION | `DEV` | Trabajador | Almacén |
| DEVOLUCION de artículo por cantidad dañado | `DEV` | Trabajador | BAJA |
| DEVOLUCION de consumible sobrante (pospuesto, V-10) | `DEV` | CONSUMIDO, con el trabajador anotado | Almacén |
| TRASPASO | `TRS` | Almacén de origen | EN_TRANSITO |
| RECEPCION | `REC` | EN_TRANSITO | Almacén de destino |
| NO_ADEUDO | `NAD` | Sin movimientos | — |
| CANCELACION | `CAN` | Los destinos del vale original | Sus orígenes |

El folio tiene la forma `CLAVE-TIPO-CONSECUTIVO`, por ejemplo `KEP-ENT-000123`.

La CANCELACION es genérica: invierte las filas de `movimiento` del vale original (mismo `renglon`, `pieza_id`, `cantidad`, `trabajador_id` y `condicion`; origen y destino cambiados). Su `vale.almacen_id` es el del original (en un traspaso, el de origen), `vale.observacion` es el motivo y `vale.vale_origen_id` apunta al original, que pasa a `estado = CANCELADO`. No hay columna aparte para el motivo ni para el folio de la cancelación del original: salen del vale cuyo `vale_origen_id` es el original y cuyo tipo es CANCELACION.

## Invariantes

1. `existencia.cantidad` es igual a la suma de entradas menos salidas de esa ubicación y artículo en `movimiento`.
2. `existencia.cantidad` nunca es negativa en almacenes, trabajadores ni En tránsito. PROVEEDOR no lleva existencia.
3. En artículos por pieza, cada movimiento lleva `pieza_id` y cantidad 1; en artículos por cantidad, `pieza_id` va vacío.
4. `pieza.ubicacion_id` es el destino de su último movimiento.
5. `movimiento` y `vale` no reciben actualizaciones ni borrados. La única excepción es `vale.estado`, que avanza de EN_TRANSITO a RECIBIDO o a RECIBIDO_CON_DIFERENCIAS, o pasa a CANCELADO cuando existe su vale de cancelación. Un traspaso queda RECIBIDO_CON_DIFERENCIAS mientras le quede algo pendiente (lo enviado menos lo recibido en sus recepciones, que son los vales RECEPCION con su `vale_origen_id`); cada recepción lo recalcula, y al completarse pasa a RECIBIDO. Lo pendiente sigue en la ubicación EN_TRANSITO. El vale RECEPCION queda en estado EMITIDO y sin `destino_almacen_id`: su `almacen_id` es el que recibe.
6. Un valor de `codigo` aparece una sola vez en todo el sistema.
7. `articulo.control` y `articulo.retornable` no cambian si el artículo tiene movimientos (CF-05).
8. Un trabajador con existencias de artículos retornables no puede recibir un vale NO_ADEUDO.
9. Un vale que no se confirmó no deja nada en la base: ni vale, ni movimientos, ni cambios de existencias. El borrador vive en el dispositivo (E-28, RG-09).
10. `inspeccion` y `ajuste_vigencia` solo se insertan. Un ajuste cambia `pieza.inspeccion_vigente_hasta`, no la inspección (P-07).

`uv run python -m app.mantenimiento verificar` (solo lectura) comprueba sobre la base real las invariantes 1 a 6 y 8, el estado de los vales cancelados con su cancelación, y que los folios de cada almacén y tipo sean consecutivos, sin repetidos ni huecos y coincidan con `serie_folio`. Sale con código 0 si todo cuadra y con 1 si no, y lista las diferencias en español. Las invariantes 7, 9 y 10 las garantiza el servicio y no se pueden comprobar después en la base.

## Índices

- `movimiento`: por `(articulo_id, creado_en)`, por `origen_id`, por `(destino_id, creado_en)` (también para el reporte de consumo), por `(trabajador_id, articulo_id, creado_en)` para los límites por periodo, y por `pieza_id` para el historial.
- `vale`: por `(tipo, almacen_id, creado_en)`, por `trabajador_id` y por `(responsable_id, creado_en)` para el filtro por usuario de la bitácora (C-11).
- `pieza`: por `(ubicacion_id, estado)` y por `articulo_id`.
- `periodo_contrato`: por `(trabajador_id, fin)` y por `puesto_id`.
- `solicitud_compra`: por `(almacen_id, estado)`, por `(estado, urgencia, creada_en)` (la cola de Compras) y por `solicitante_id`; `solicitud_compra_evento`: por `(solicitud_id, creado_en)`.
- `dotacion`: por `(puesto_id, articulo_id)` (único) y por `articulo_id`.

## Fechas y horas

Se guardan en UTC y las pone el servidor (RG-11). Se muestran en la hora del centro de México. La vigencia de contrato y de inspección se compara por fecha en esa misma zona.

## Retención

Nada se borra. Un artículo, una categoría, un usuario, un rol o un trabajador se inactivan. Un artículo solo se elimina si no tiene movimientos (CF-12).

## Datos de prueba

El script carga, de forma repetible:

- Los seis almacenes del PDF y las cuatro ubicaciones virtuales.
- Las siete categorías iniciales (sección 5.1 de las reglas).
- Cuatro puestos (Ayudante general, Soldador, Electricista y Rigger) con su dotación, **propuestas de datos de prueba basadas en el PDF** (EPP de la p. 10 más equipo de las p. 7 y 10); los puestos reales los define la empresa. Los cuatro trabajadores de prueba quedan ligados a su puesto. Las cantidades caben en los límites de los artículos sembrados, así que no hubo que ajustar ninguno. La línea base de las pruebas automáticas borra las dotaciones para que las demás pruebas no pidan observación.
- Los quince artículos de la página 7 del PDF y el EPP de la página 10, con sus costos.
- Existencias iniciales de los artículos por cantidad en Kepler y Contratistas, cargadas con un vale de entrada real por almacén (folio `KEP-ING-000001`, `CON-ING-000001`), nunca escribiendo saldos. Es repetible: cada carga lleva un `id_cliente` fijo y no se duplica.
- Piezas de prueba, en Kepler, dadas de alta con **un vale de entrada real** y su inspección inicial (las carga `app/datos_prueba_piezas.py`, que corre al final porque depende de `catalogo`, `movimientos` e `inspecciones`; es repetible y no duplica): ocho de equipo de alturas (`ALT-001` a `ALT-008`: arneses Kevlar y Poliéster, bandola, gancho doble de vida y retráctil) y cinco herramientas por serie (`HER-001` a `HER-005`: minipulidores, detectores de gases y un radio). Entre las de alturas, `ALT-001`, `ALT-002` y `ALT-004` están aptas con inspección vigente, `ALT-003` está **no apta** y `ALT-005` tiene la **inspección vencida**: entra con una inspección inicial de hace 200 días y el servicio de inspecciones le calcula la vigencia (180 días) como a cualquier pieza. El artículo `RADIO` (Radio de comunicación) se crea ahí mismo.
- Los cinco roles iniciales con sus permisos (sección 8.2 de las reglas).
- Tres solicitudes de compra de ejemplo, repetibles (cada una con un `id_cliente` fijo): `MID-SOL-000001`, urgente y PENDIENTE, de una «Llave métrica 24 mm» sin artículo de catálogo, pedida por el almacenista de Midrex; `KEP-SOL-000001`, EN_COMPRA, de 20 respiradores (artículo `RESP-6200`), pedida por el supervisor de Kepler y tomada por Compras; y `KEP-SOL-000002`, INGRESADA, de 10 flexómetros (`FLEXOM`), ligada al vale real `KEP-ING-000001`.
- Un usuario por rol, y un almacenista para cada almacén que se use en la prueba.

## Cambios previstos por la segunda ola

| Feature | Cambio |
|---|---|
| FEAT-001 | `vale.hash`, `vale.hash_anterior`; tabla `cadena_sello`; `adjunto.tipo` TICKET_FIRMADO; `vale.firma_modo` PAPEL |
| FEAT-002 | Vale AJUSTE con movimientos entre almacén y BAJA |
| FEAT-003 | Tablas `puesto` y `dotacion` y `periodo_contrato.puesto_id`: **construidas** (`0004_puestos_dotacion`) |
| FEAT-004 | Tabla `minimo` (`almacen_id`, `articulo_id`, `cantidad`) |
| FEAT-005 | Ninguno: pasó al MVP (T-09) |
| FEAT-006 | Sin tablas nuevas: administra `rol`, `rol_permiso` y `usuario` desde la pantalla, incluida la asignación de personal a almacenes (`usuario.almacen_id`) |
