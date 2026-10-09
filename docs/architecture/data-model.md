# Modelo de datos

> FEAT-013 ya incorpora `proyecto` y `asignacion_proyecto` (0011), `usuario_almacen` y `vale.proyecto_id` (0012). Las referencias históricas del vale permanecen al cancelar. `usuario.almacen_id` es el activo; el servicio mantiene su pertenencia al conjunto. La migración conserva la asignación previa de cada usuario y deja los trabajadores existentes sin proyecto.

El CHECK de las fechas de asignación es `fin >= inicio OR terminada_en IS NOT NULL`: una asignación futura cancelada o terminada antes de empezar conserva su inicio previsto y la fecha real de término. Las asignaciones se bloquean junto al trabajador para impedir dos principales activas en altas concurrentes. `usuario_almacen` tiene llave compuesta `(usuario_id, almacen_id)`; en esta implementación la autoría y fecha de sus cambios quedan en la auditoría.

FEAT-014 incorpora en 0014 los campos no nulos `almacen.despacho_epp_con_aprobacion` (por omisión verdadero) y `usuario.despacho_autonomo` (por omisión falso), además de suscripciones push y metadatos de autorización. Su flujo de confirmación y pruebas siguen en integración.

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
| Pieza | Código y número de serie (que puede estar pendiente) |
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
| `trabajador` | `id`, `numero_empleado`, `numero_externo`, `nombre`, `curp`, `nss`, `tallas`, `foto_adjunto_id`, `estado`, `creado_en` | `numero_empleado` único; `curp` único si existe. `estado`: ACTIVO, BAJA_EN_PROCESO, INACTIVO. `foto_adjunto_id` va vacío si el trabajador no tiene foto (T-09). **FEAT-008 (migración `0007`, T-10):** `numero_empleado` lo genera el servidor con el formato `E-000001` desde `serie_empleado`; `numero_externo` (booleano, `false` por omisión) marca el número que se capturó a mano con el permiso `trabajadores.numero_externo`. La migración deja con `numero_externo = true` a los trabajadores que ya existían, que conservan su número (por ejemplo `EMP-1001`). |
| `serie_empleado` | `id`, `ultimo` | **FEAT-008 (migración `0007`, T-10).** Una sola fila (`id = 1`, `CHECK id = 1`) con el último consecutivo del número de empleado. Se bloquea (`FOR UPDATE`) y avanza en la misma transacción que guarda al trabajador: sin huecos ni repetidos (mismo patrón que `serie_folio`, [ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). La migración inicia `ultimo` con el mayor consecutivo que ya exista con forma `E-NNNNNN` (0 si no hay); `numero_empleado` único es la red de seguridad. Dueño: `trabajadores`. |
| `periodo_contrato` | `id`, `trabajador_id`, `puesto`, `puesto_id`, `area_obra`, `referencia`, `inicio`, `fin`, `creado_por`, `creado_en` | Un renglón por contrato o reingreso. El vigente es el más reciente. `puesto` es el texto capturado y `puesto_id` (opcional, FK a `puesto`) lo liga al catálogo; de él sale la dotación. Un texto que no coincide con ningún puesto deja `puesto_id` vacío y el trabajador sin dotación. |

### Lugares

| Tabla | Campos | Notas |
|---|---|---|
| `almacen` | `id`, `clave`, `nombre`, `tipo`, `padre_id`, `estado`, `creado_en`, `cerrado_en` | `clave` única (KEP, CON, MID, HYL, LAM, MIN). `tipo`: CENTRAL, SUBALMACEN, PROYECTO. `padre_id` arma la red: Kepler, Contratistas, áreas. `estado`: ACTIVO, CERRADO. **FEAT-008:** `cerrado_en` (UTC) se escribe al inactivar (`estado = CERRADO`) y se limpia al reactivar; lo escribe solo el módulo `almacenes` (AL-03). Invariantes: un solo `CENTRAL`; un `CENTRAL` no tiene `padre_id` y los demás sí; sin ciclos; el nombre es único. Un almacén `CERRADO` conserva su historial y no recibe ni envía movimientos (AL-04). **Migración `0007`:** agrega `uq_almacen_nombre` (único sin distinguir mayúsculas ni acentos, por la colación; hoy solo `clave` es única) y `uq_almacen_un_central` (columna generada `central_unico` = 1 si `tipo = 'CENTRAL'`, si no `NULL`, con índice único: MySQL no tiene índices parciales). Lo demás (padre válido, sin ciclos, coherencia de `estado` y `cerrado_en`) lo verifica el servicio, porque la base no puede expresarlo. |
| `ubicacion` | `id`, `tipo`, `almacen_id`, `trabajador_id`, `virtual` | Exactamente uno de los tres últimos tiene valor. `virtual`: PROVEEDOR, EN_TRANSITO, CONSUMIDO, BAJA. Se crea una al dar de alta cada almacén y cada trabajador. |

### Catálogo

| Tabla | Campos | Notas |
|---|---|---|
| `categoria` | `id`, `nombre`, `tipo`, `control`, `retornable`, `requiere_inspeccion`, `vigencia_inspeccion_dias`, `requiere_autorizacion`, `motivo_uso_especial`, `limite_cantidad`, `limite_periodo_dias`, `cantidad_aviso`, `activo` | `tipo`: EPP, HERRAMIENTA. Los campos de regla son la plantilla que se copia al artículo (CF-02). |
| `articulo` | `id`, `codigo`, `nombre`, `marca`, `modelo`, `categoria_id`, `control`, `retornable`, `talla`, `unidad`, `costo_unitario`, `requiere_inspeccion`, `vigencia_inspeccion_dias`, `requiere_autorizacion`, `motivo_uso_especial`, `limite_cantidad`, `limite_periodo_dias`, `cantidad_aviso`, `activo`, `motivo_inactivacion`, `creado_en` | `control`: PIEZA, CANTIDAD. Guarda sus propias reglas; las de la categoría solo son el punto de partida. `limite_periodo_dias` vacío significa "en posesión" (L-05). `cantidad_aviso` vacío significa que no hay aviso de cantidad inusual (E-27). |
| `pieza` | `id`, `articulo_id`, `codigo`, `numero_serie`, `estado`, `inspeccion_vigente_hasta`, `ubicacion_id`, `creado_en` | `estado`: APTO, NO_APTO, EN_MANTENIMIENTO, EN_CALIBRACION, BAJA. `ubicacion_id` la actualiza solo el motor. `numero_serie` admite nulo: nulo significa **serie pendiente** (ver «Serie pendiente y código de pieza generado»). |
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
| `autorizacion` | `id`, `tipo`, `almacen_id`, `trabajador_id`, `solicitada_por`, `motivo`, `detalle`, `estado`, `resuelta_por`, `medio`, `creado_en`, `resuelta_en`, `vence_en` | `tipo`: EXCEDENTE (por omisión; las anteriores), DESPACHO (FEAT-014, aún sin uso) o TRASLADO (FEAT-015, X-17). `trabajador_id` es nulo solo en un TRASLADO (`ck_autorizacion_trabajador_segun_tipo`: nulo solo si `tipo = 'TRASLADO'`). `estado`: PENDIENTE, APROBADA, RECHAZADA, VENCIDA, USADA. `medio`: PIN, REMOTA. `detalle`: renglones y regla que la originó; en un TRASLADO también `origen_almacen_id` y `destino_almacen_id` (`almacen_id` es el origen). Migración `0010_autorizacion_traslado`. |
| `inspeccion` | `id`, `pieza_id`, `fecha`, `resultado`, `puntos`, `observacion`, `vigente_hasta`, `usuario_id`, `creado_en` | `puntos`: etiquetas, costuras, cintas, herrajes, conectores. |
| `ajuste_vigencia` | `id`, `pieza_id`, `inspeccion_id`, `vigente_hasta_anterior`, `vigente_hasta_nuevo`, `motivo`, `usuario_id`, `creado_en` | Solo se inserta (P-07). Al guardarse, `pieza.inspeccion_vigente_hasta` toma la fecha nueva; la inspección original no cambia. |
| `evento_pieza` | `id`, `pieza_id`, `estado_anterior`, `estado_nuevo`, `observacion`, `usuario_id`, `creado_en` | Cambios de estado que no son inspección. |
| `adjunto` | `id`, `tipo`, `ruta`, `mime`, `tamano`, `sha256`, `vale_id`, `movimiento_id`, `subido_por`, `creado_en` | `tipo`: FIRMA, FOTO_DANO, FOTO_TRABAJADOR. El archivo vive en el volumen, no en la base. |
| `auditoria` | `id`, `usuario_id`, `accion`, `entidad`, `entidad_id`, `antes`, `despues`, `creado_en` | Entradas al sistema, cambios de catálogo, inactivaciones (CF-15). Acciones de importación: `importacion.confirmar` (entradas por Excel) e `importacion.traspaso` (traspaso por lista de Excel, FEAT-009; su `despues` lleva el resumen, el vale creado y la `huella` sha256 del archivo, con `repetido: true` si se confirmó un archivo ya importado). Registro de serie: `pieza.registrar_serie` (`entidad` = pieza, `antes` = `{numero_serie: null}`, `despues` = `{numero_serie: "…"}`). Sin tabla nueva: el aviso de archivo repetido busca la huella aquí. |
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
- **`pieza.ubicacion_id`** puede ir vacía mientras la pieza no tenga su primer movimiento (la entrada). `(articulo_id, numero_serie)` es único, y como MySQL permite varios nulos en un índice único, varias piezas del mismo artículo pueden tener la serie pendiente a la vez.
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
- **Dueños.** `acceso`: usuario, rol, rol_permiso, sesion_dispositivo. `trabajadores`: trabajador, periodo_contrato, serie_empleado (lee `puesto` y `dotacion`). `almacenes`: almacen, ubicacion. `catalogo`: categoria, articulo, pieza, codigo, puesto, dotacion. `movimientos`: vale, movimiento, existencia, serie_folio. `autorizaciones`: autorizacion. `solicitudes_compra`: solicitud_compra, solicitud_compra_evento, serie_solicitud_compra (solo LEE `vale`). `inspecciones`: inspeccion, ajuste_vigencia, evento_pieza. `archivos`: adjunto. `auditoria`: auditoria.
- **Lo que no se puede expresar en la base** y queda para los services: que `vale` y `movimiento` no se actualicen (salvo `vale.estado`), que `existencia` sea la suma de los movimientos, que `pieza.ubicacion_id` sea el destino de su último movimiento, que `control` y `retornable` no cambien con movimientos (CF-05), y que siempre exista un usuario activo con `acceso.administrar` (AC-09).

### Serie pendiente y código de pieza generado

Decisión en [ADR-010](decisions/ADR-010-codigos-y-series-de-pieza.md). **No hay migración ni columna nueva.**

- **Serie pendiente (E-29, I-02).** `pieza.numero_serie` nulo significa que la pieza entró sin número de serie del fabricante. La condición se **deriva** del dato, igual que la inspección pendiente (I-03) se deriva de `inspeccion_vigente_hasta`: la API la expone como `serie_pendiente` (booleano) y no se guarda aparte ni hay un estado nuevo en `EstadoPieza`. Una cadena vacía o en blanco no se guarda: se normaliza a nulo.
- **Quién escribe la serie.** Al entrar, el módulo `movimientos` crea la pieza dentro del vale de entrada (con o sin serie). Después, solo `POST /api/piezas/{id}/serie` (módulo `catalogo`) puede poner una serie, y únicamente si la pieza no tiene (P-08); cambiar una serie ya registrada no entra en esta etapa. Es una escritura de dato de la pieza, no un movimiento: no cambia existencias ni ubicación (Invariante 5 intacta) y deja la auditoría `pieza.registrar_serie`.
- **Unicidad.** La serie que sí existe sigue siendo única por artículo; el nulo no cuenta como repetido.
- **Código de pieza generado.** `pieza.codigo` ya es único y vive en `codigo` (tipo PIEZA, invariante 6). Si la importación Alta no trae `codigo_pieza`, el servidor lo genera al confirmar con la forma `CÓDIGO-DEL-ARTÍCULO-NNN` (`HEL-0003-001`): el consecutivo es por artículo, se busca el primer `NNN` libre en `codigo` bajo el bloqueo del artículo y el código nace en la misma transacción que la pieza. No se guarda si fue generado o capturado; la respuesta de la importación lo informa.
- **Unidad.** `articulo.unidad` (texto de hasta 20, «pieza» por omisión) ya existe. La importación Alta la lee de una columna opcional `unidad` solo al **crear** un artículo; en uno existente no se modifica. Las cantidades siguen siendo enteras (I-13): quien mide en otra unidad la declara en la unidad menor.

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

Un traspaso creado por la importación de FEAT-009 («Traspasos por lista de Excel») es un vale TRASPASO normal: mismo folio `CLAVE-TRS-…`, mismo QR y estado `EN_TRANSITO`, movimientos y existencias iguales a los de la captura manual. No hay tablas, columnas ni migración nuevas, y la recepción no cambia (`POST /api/vales` tipo RECEPCION).

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
- **Tablero (FEAT-008).** `GET /api/tablero/consumo` agrupa `movimiento` por artículo y almacén del vale en un rango de fechas: se apoya en `vale(tipo, almacen_id, creado_en)` y en `movimiento(destino_id, creado_en)`. Si el plan de ejecución lo pide con mucho historial, se agrega un índice por `(vale_id, articulo_id)`; la decisión se toma midiendo, no antes.

## Fechas y horas

Se guardan en UTC y las pone el servidor (RG-11). Se muestran en la hora del centro de México. La vigencia de contrato y de inspección se compara por fecha en esa misma zona.

## Retención

Nada se borra. Un artículo, una categoría, un usuario, un rol o un trabajador se inactivan. Un artículo solo se elimina si no tiene movimientos (CF-12).

## Datos de prueba

El script carga, de forma repetible:

- Los seis almacenes del PDF y las cuatro ubicaciones virtuales. En producción los almacenes los crea `uv run python -m app.mantenimiento sembrar-almacenes` (solo si no existe ninguno) o la pantalla `/almacenes` (FEAT-008); los trabajadores de prueba conservan su número de empleado (`EMP-1001`…) y quedan marcados como externos.
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
| FEAT-002 | **Servidor construido:** vale AJUSTE, folio `CLAVE-AJU-CONSECUTIVO`, firma SESION, observación y responsable obligatorios; movimientos entre almacén y BAJA, sin trabajador. Migración `0019_ajuste_cierre` amplía los CHECK de `vale.tipo` y `serie_folio.tipo`. Sin tabla de ciclos ni saldos de resumen: el reporte se calcula por almacén y rango obligatorio de fechas del mantenimiento. El saldo final es histórico al final del rango. |
| FEAT-003 | Tablas `puesto` y `dotacion` y `periodo_contrato.puesto_id`: **construidas** (`0004_puestos_dotacion`) |
| FEAT-004 | Tabla `minimo` (`almacen_id`, `articulo_id`, `cantidad`) |
| FEAT-005 | Ninguno: pasó al MVP (T-09) |
| FEAT-006 | Sin tablas nuevas: administra `rol`, `rol_permiso` y `usuario` desde la pantalla, incluida la asignación de personal a almacenes (`usuario.almacen_id`) |
| FEAT-007 / ADR-010 | Sin migración: `pieza.numero_serie` nulo = serie pendiente (derivado), código de pieza generado y columna `unidad` de la importación Alta usan columnas que ya existen. Auditoría nueva: `pieza.registrar_serie`. |
| FEAT-008 | Migración `0007`: tabla `serie_empleado`, `trabajador.numero_externo`, `uq_almacen_nombre` y `uq_almacen_un_central`; `almacen.cerrado_en` empieza a usarse. El tablero lee con consultas agregadas sobre `movimiento`, `existencia`, `vale`, `pieza` y `solicitud_compra`: se revisan los índices por fecha y almacén (ver «Índices») y no hay tablas de resumen. |

## Previsto por la iteración 01 (aprobado, sin construir)

Fuente: [documento maestro de la iteración 01](../releases/iteration_01/README.md) (sección 5.1 y sus tablas adicionales) y los briefs [FEAT-013](../features/FEAT-013-proyectos-y-supervision-por-almacenes.md) a [FEAT-020](../features/FEAT-020-app-android-sin-conexion.md). **Nada de esta sección existe todavía en el código ni en las migraciones** (la última es `0009_permiso_valor_inventario`). Lo de arriba sigue describiendo lo construido; al construirse cada parte, su detalle pasa a las secciones de arriba y sale de aquí. Si un brief contradice al maestro, manda el maestro.

Siguen valiendo las convenciones de «Decisiones de implementación»: UUID v7, enums como `VARCHAR` con `ck_<tabla>_<columna>`, fechas `DATETIME(6)` en UTC, nombres de constraints estables y, donde MySQL no tiene índices parciales, una **columna generada** con índice único (el patrón de `uq_almacen_un_central`).

### Tablas nuevas

| Tabla | Dueño | FEAT | Campos | Constraints e índices (propuestos) |
|---|---|---|---|---|
| `proyecto` | `proyectos` (módulo nuevo) | 013 | `id`, `clave`, `nombre` (100), `almacen_id`, `inicio` (fecha), `fin_estimado` (fecha), `estado`, `cerrado_en` (UTC), `motivo_cierre` (500), `creado_por`, `creado_en` | `uq_proyecto_clave` (2 a 20 caracteres, en mayúsculas). `ck_proyecto_estado` (`ACTIVO`, `CERRADO`). `ck_proyecto_fechas`: `fin_estimado >= inicio`. FK `almacen_id` → `almacen`, `creado_por` → `usuario`. `ix_proyecto_almacen_estado` (`almacen_id`, `estado`). El nombre puede repetirse en almacenes distintos (la clave los distingue). La coherencia de `estado` con `cerrado_en` y `motivo_cierre` la verifica el servicio. No se borra. |
| `asignacion_proyecto` | `proyectos` | 013 | `id`, `trabajador_id`, `proyecto_id`, `inicio` (fecha), `fin` (fecha, nula mientras está activa), `principal` (bool), `creado_por`, `creado_en`, `terminada_en` (UTC), `terminada_por` | Activa = `terminada_en` nula. Columnas generadas para dos únicos: `uq_asignacion_proyecto_activa` (una activa por trabajador y proyecto; 409 `ASIGNACION_REPETIDA`) y `uq_asignacion_proyecto_principal` (una principal activa por trabajador). `ck_asignacion_proyecto_fechas`: `fin >= inicio`. FK a `trabajador`, `proyecto` y `usuario` (`creado_por`, `terminada_por`). `ix_asignacion_proyecto_trabajador` (`trabajador_id`, `terminada_en`) e `ix_asignacion_proyecto_proyecto` (`proyecto_id`, `terminada_en`). Se actualiza **una sola vez**, para terminarla; nunca se borra. |
| `usuario_almacen` | `acceso` | 013 | `usuario_id`, `almacen_id`, `asignado_por` (nulo en lo que crea la migración), `asignado_en` | Llave `(usuario_id, almacen_id)`. FK a `usuario` y `almacen`. `ix_usuario_almacen_almacen` (`almacen_id`). Es el **conjunto** de almacenes del usuario (AC-36). La migración crea un renglón por cada usuario con `usuario.almacen_id`, así nadie pierde ni gana acceso. Si MySQL lo permite, una FK compuesta `usuario(id, almacen_id)` → `usuario_almacen(usuario_id, almacen_id)` garantiza en la base que el almacén activo esté en el conjunto; si no, lo garantiza el servicio. |
| `suscripcion_push` | `notificaciones` (módulo nuevo) | 014 | `id`, `usuario_id`, `familia_id`, `endpoint` (hasta 1000, `https`), `p256dh`, `auth`, `agente` (resumido como en AC-21), `creada_en`, `ultimo_envio`, `ultimo_error`, `revocada_en` | Una suscripción de Web Push por dispositivo. FK `usuario_id` → `usuario`. `familia_id` sin FK (como `sesion_dispositivo.reemplazada_por`: las familias se purgan). Vigente = `revocada_en` nula. Un `endpoint` es único **entre las vigentes**: registrar el mismo `endpoint` toma la fila (la anterior queda revocada); como un `VARCHAR(1000)` no cabe en un índice único de utf8mb4, se propone una columna generada con su huella SHA-256 cuando la fila es vigente, con índice único (si no, lo garantiza el servicio). `ix_suscripcion_push_usuario` (`usuario_id`, `revocada_en`) e `ix_suscripcion_push_familia` (`familia_id`). `ultimo_envio` cuenta el minuto de agrupación (NT-05) en la base. |
| `dispositivo` | `sincronizacion` (módulo nuevo) | 020 | `id`, `usuario_id` (quien lo inscribió), `almacen_id`, `nombre`, `plataforma`, `version_app`, `registrado_en`, `ultimo_paquete_en`, `ultima_subida_en`, `revocado_en`, `revocado_por`, `secreto_hash`, `motivo_revocacion` | Un equipo inscrito para operar sin conexión; pertenece a **un** almacén (OF-03). `ck_dispositivo_plataforma` (`ANDROID`). `uq_dispositivo_secreto_hash` (SHA-256 del secreto del equipo; el secreto nunca se guarda en claro). FK a `usuario` (`usuario_id`, `revocado_por`) y `almacen`. `ix_dispositivo_almacen` (`almacen_id`) e `ix_dispositivo_revocado` (`revocado_en`). Revocado = `revocado_en` no nula; no se borra. |
| `dispositivo_usuario` | `sincronizacion` | 020 | `dispositivo_id`, `usuario_id`, `primera_entrada_en`, `ultima_entrada_en`, `revocado_en` | Llave `(dispositivo_id, usuario_id)`. Los usuarios que entraron con señal en el equipo (turno de día y de noche): a quién se le aceptan vales (OF-24) y a quién se le invalida la credencial local (OF-05). |
| `conflicto_sincronizacion` | `sincronizacion` | 020 | `id`, `dispositivo_id`, `usuario_id` (quien capturó), `id_cliente`, `tipo_operacion`, `cuerpo` (JSON), `motivo`, `detalle` (JSON), `estado`, `resuelto_por`, `resolucion` (JSON), `vale_id`, `creado_en`, `resuelto_en` | Una operación capturada sin conexión que el servidor no pudo guardar tal cual (OF-22). `uq_conflicto_sincronizacion_id_cliente`. `ck_..._tipo_operacion` (`ENTREGA`, `DEVOLUCION`, `RECEPCION`, `INSPECCION`, `NO_APTA`, `SOLICITUD_COMPRA`). `ck_..._estado` (`PENDIENTE`, `RESUELTO`, `DESCARTADO`). `ck_conflicto_sincronizacion_no_resolverse`: `resuelto_por IS NULL OR resuelto_por <> usuario_id` (como `no_autorizarse`, OF-25). FK a `dispositivo`, `usuario` y `vale` (`vale_id`, nulo salvo que la resolución cree un vale). `cuerpo` guarda la firma como referencia a un archivo del volumen, no la imagen. `ix_..._dispositivo_estado` (`dispositivo_id`, `estado`) e `ix_..._estado_creado` (`estado`, `creado_en`). Solo se inserta; su resolución se escribe **una vez** (un conflicto resuelto no se reabre). |
| `operacion_recibida` | `sincronizacion` | 020 | `id_cliente`, `dispositivo_id`, `tipo`, `resultado` (JSON), `creado_en` | Llave natural `id_cliente`. Idempotencia de lo que **no** es vale (inspecciones, marcar No apta, solicitudes de compra) al reenviar un lote: el mismo `id_cliente` responde el `resultado` guardado. FK `dispositivo_id`. Solo se inserta. |

### Columnas nuevas en tablas existentes

| Columna | Dueño | FEAT | Detalle |
|---|---|---|---|
| `usuario.almacen_id` (sin cambio de tipo) | `acceso` | 013 | Pasa a ser el **almacén activo**: el de las escrituras (AC-38). Siempre pertenece al conjunto (`usuario_almacen`); vacío solo si el conjunto está vacío o el rol tiene `almacenes.todos`. |
| `usuario.despacho_autonomo` (bool, no nulo, `false`) | `acceso` | 014 | Excepción por almacenista: despacha EPP sin aprobación (DE-14). |
| `almacen.despacho_epp_con_aprobacion` (bool, no nulo, `true`) | `almacenes` | 014 | Interruptor de autonomía del almacén (DE-14). Los almacenes que ya existen quedan con aprobación. |
| `almacen.hora_descarga` (`TIME`, nula) | `almacenes` | 020 | Hora del centro de México de la descarga diaria del paquete del almacén; nula = sin descarga programada. La edita el Administrador. |
| `autorizacion.tipo` (no nulo) | `autorizaciones` | 015, 014 | **Construido (FEAT-015, migración `0010`).** `ck_autorizacion_tipo`: `EXCEDENTE`, `DESPACHO`, `TRASLADO`. Las que ya existen quedan `EXCEDENTE`. |
| `autorizacion.trabajador_id` | `autorizaciones` | 015 | **Construido (migración `0010`).** Pasa a **aceptar nulo**, con `ck_autorizacion_trabajador_segun_tipo`: nulo solo si `tipo = 'TRASLADO'` (un traslado no tiene trabajador). |
| `autorizacion.renglones_resueltos` (JSON, nulo) | `autorizaciones` | 014 | `[{renglon, codigo, cantidad, decision: APROBADO \| RECHAZADO, motivo}]` (aprobación parcial, DE-06). Nulo en las anteriores: si están APROBADA o USADA, todos sus renglones cuentan como aprobados. |
| `autorizacion.id_cliente` (nulo, único) | `autorizaciones` | 014 | `uq_autorizacion_id_cliente`. Un doble toque no crea dos solicitudes (DE-04). Nulo en las anteriores. |
| `autorizacion.estado` + `RETIRADA` | `autorizaciones` | 014 | **Solo si se aprueba la decisión abierta 1 de FEAT-014** (retirar una solicitud pendiente). Amplía `ck_autorizacion_estado`. |
| `autorizacion.detalle` (sin cambio de columna) | `autorizaciones` | 014, 015 | Gana por renglón `clase` (`EPP`, `EXCEDENTE`, `CONTEXTO`) y `observacion`; arriba, `nota` y `proyecto`. En un TRASLADO, `origen_almacen_id` y `destino_almacen_id` (`almacen_id` es el origen). |
| `vale.proyecto_id` (FK a `proyecto`, nula) | `movimientos` | 013 | El proyecto de la ENTREGA; la CANCELACION de una entrega lo hereda. Se escribe al insertar y no cambia (invariante 5). Los vales anteriores quedan sin proyecto. `ix_vale_proyecto` (`proyecto_id`, `tipo`, `creado_en`). |
| `vale.lote_id` (UUID, nulo, sin FK) | `movimientos` | 017 | Agrupa los vales de una misma importación (partida en vales de 500) o de un mismo traspaso por Excel. Vale el `id_lote` que ya manda el cliente; lo pasa la importación a `MovimientoService.confirmar` como parámetro **interno** (el cuerpo público de `POST /api/vales` lo sigue rechazando). Sin rellenar los anteriores. `ix_vale_lote_id`. |
| `vale.capturado_sin_conexion` (bool, no nulo, `false`), `vale.capturado_en` (UTC, nula), `vale.dispositivo_id` (FK a `dispositivo`, nula) | `movimientos` | 020 | Datos del vale capturado sin conexión. `creado_en` sigue siendo la hora del servidor (al sincronizar); `capturado_en` es la del equipo y no se corrige. **`vale.dispositivo` (el navegador, ya existe) y `vale.dispositivo_id` (el equipo inscrito, nuevo) son cosas distintas.** Propuesto `ck_vale_sin_conexion`: `capturado_sin_conexion` es verdadero si y solo si `capturado_en` y `dispositivo_id` tienen valor. |
| `categoria.alto_valor` (bool, no nulo, `false`) | `catalogo` | 018 | Marca de alto valor (AV-04). La migración la prende **una vez** en «Equipo de alto valor», buscándola por nombre; después nada lee el nombre. El alto valor de un artículo se **calcula al leer** (AV-02: la marca de su categoría o `costo_unitario >= ALTO_VALOR_COSTO_MINIMO`) y no se guarda. |
| `categoria.dias_aviso_inspeccion`, `articulo.dias_aviso_inspeccion` (entero, nulo = hereda) | `catalogo` | 016 | Días de aviso antes de que venza una inspección (P-10). CHECK de 1 a 90. Herencia **en vivo** (artículo, si no categoría, si no `INSPECCION_AVISO_DIAS`), a diferencia de la plantilla de CF-02, que se copia. |
| `inspeccion.id_cliente` (nulo, único) | `inspecciones` | 016 | `uq_inspeccion_id_cliente`. Inspección individual y por lote sin duplicar (P-16). Nulo en las existentes. |
| `adjunto.inspeccion_id` (FK a `inspeccion`, nula) y `adjunto.tipo` + `FOTO_INSPECCION` | `archivos` | 016 | Foto opcional de la inspección (P-14). Amplía el CHECK de `adjunto.tipo`. |
| `reserva_papel` | `movimientos` | 001 | Reserva por 30 minutos de folio, QR y snapshot del ticket antes de emitir una ENTREGA con firma manuscrita. `id_cliente`, `folio` y `token` son únicos; `vale_id` se enlaza al confirmar y no se permite reutilizar la reserva. |

`inspeccion.puntos` (JSON) no cambia de forma: desde FEAT-016 trae las cinco claves (`true` Bien, `false` Mal, `null` No aplica). El supervisor que despacha él mismo (DE-07) y el que envía un traslado lateral (X-16) **no** se guardan como una autorización: `ck_autorizacion_no_autorizarse` sigue igual; se marcan con la regla en `movimiento.reglas` y el vale muestra «Validó: él mismo».

### Migraciones previstas, en el orden de construcción

Números propuestos según el orden de la sección 7 del maestro; si el orden cambia, cada una toma el siguiente número libre. Cada una va arriba y abajo con datos y deja `verificar` en 0.

| # | Migración | FEAT | Qué hace |
|---|---|---|---|
| 1 | `0010_autorizacion_traslado` (**construida**) | 015 | `autorizacion.tipo` (existentes = `EXCEDENTE`) y `autorizacion.trabajador_id` nulo con su CHECK. Sin permisos nuevos. La bajada borra las autorizaciones de traslado (no caben sin trabajador) y deja sin `autorizacion_id` a los vales que las citaban. |
| 2 | `0011_despacho_epp_y_avisos` | 014 | `almacen.despacho_epp_con_aprobacion`, `usuario.despacho_autonomo`, `autorizacion.renglones_resueltos`, `autorizacion.id_cliente` (y `RETIRADA` si se aprueba), tabla `suscripcion_push`; permiso `despacho.autonomia` al rol protegido. |
| 3 | `0012_proyectos_y_conjunto_de_almacenes` | 013 | Tablas `proyecto`, `asignacion_proyecto` y `usuario_almacen` (rellenada desde `usuario.almacen_id`), `vale.proyecto_id` con su índice; permisos `proyectos.ver` (Almacenista, Supervisor, RH), `proyectos.administrar` (Administrador) y `proyectos.asignar` (RH y todo rol con `trabajadores.administrar`). Los trabajadores existentes quedan sin asignación. `reportes.valor_inventario` ya lo da al Supervisor la `0009`. FEAT-013 la llama `0010`; con este orden es la tercera. |
| 4 | `0013_vale_lote` | 017 | `vale.lote_id` e `ix_vale_lote_id`. |
| 5 | `0014_alto_valor_y_deudores` | 018 | `categoria.alto_valor` (y `true` en «Equipo de alto valor»); permiso `deudores.ver` a Supervisor, RH, Administrador y todo rol con `reportes.adeudos`. |
| 6 | `0015_inspecciones_y_avisos` | 016 | `categoria.dias_aviso_inspeccion`, `articulo.dias_aviso_inspeccion`, `inspeccion.id_cliente`, `adjunto.inspeccion_id` y `FOTO_INSPECCION`; permiso `inspecciones.ver` (Almacenista, Supervisor, Administrador). |
| — | — | 019 | Sin migración: usa `vale.lote_id` de FEAT-017. |
| 7 | `0016_sincronizacion` | 020 | Tablas `dispositivo`, `dispositivo_usuario`, `conflicto_sincronizacion` y `operacion_recibida`; `vale.capturado_sin_conexion`, `vale.capturado_en`, `vale.dispositivo_id`; `almacen.hora_descarga`; permisos `sincronizacion.operar` (Almacenista) y `sincronizacion.administrar` (Supervisor). |
| 8 | `0018_vale_papel` | 001 | Crea `reserva_papel`; conserva folio y token mientras se imprime y firma el ticket. |
| 9 | `0019_ajuste_cierre` | 002 | Agrega el tipo de vale `AJUSTE` y los datos de cierre del almacén. |
| 10 | `0020_bitacora_lote` | 017 | Agrega `vale.lote_id` para agrupar operaciones de importación. |

Los permisos son filas de `rol_permiso` (el catálogo vive en el código, AC-01): cada migración solo agrega filas con `INSERT IGNORE`, como la `0009`.

### Invariantes nuevas

11. `usuario.almacen_id`, si tiene valor, pertenece al conjunto del usuario (`usuario_almacen`). Quien tiene `almacenes.todos` no necesita conjunto.
12. `vale.proyecto_id` solo tiene valor en una ENTREGA o en la CANCELACION de una ENTREGA, y la cancelación lleva el mismo proyecto que el vale que cancela. Se escribe al insertar y no cambia aunque el trabajador cambie de proyecto o el proyecto se cierre (PR-14). (La parte «solo ENTREGA o CANCELACION» se puede expresar con un CHECK sobre `tipo`; la de la cancelación, el servicio.)
13. Una asignación activa por trabajador y proyecto, y a lo más una principal activa por trabajador.
14. Todos los vales de un lote (`vale.lote_id`) son del mismo tipo, del mismo almacén y del mismo responsable, y lo comparten desde que se insertan. Las cancelaciones y las recepciones no heredan el lote.
15. Un vale capturado sin conexión tiene `capturado_sin_conexion = true`, `capturado_en` y `dispositivo_id`; uno en línea, ninguno de los tres. Su `almacen_id` es el del **equipo**, no el almacén activo del usuario al sincronizar (OF-22), y su `responsable_id` es quien lo capturó (OF-24). El folio se asigna al sincronizar y sigue consecutivo por almacén y tipo (RG-06).
16. Una autorización `DESPACHO` APROBADA tiene al menos un renglón APROBADO en `renglones_resueltos`; una RECHAZADA, ninguno. Una `TRASLADO` no tiene trabajador.
17. Un vale con renglones de EPP en un despacho con aprobación lleva un `autorizacion_id` de tipo `DESPACHO`, o sus movimientos de EPP llevan la regla `DE-07` (lo despachó un supervisor) o `DE-14` (autonomía).
18. Un `conflicto_sincronizacion` no lo resuelve quien capturó la operación; resolverlo nunca edita un vale guardado: si guarda algo, crea un vale nuevo por `movimientos` y lo anota en `vale_id`.

Las invariantes 1 a 10 no cambian, tampoco para lo sincronizado: solo `movimientos` escribe vales, movimientos, existencias y ubicación de piezas; `sincronizacion` recibe, valida la forma y llama a su servicio. Se propone que `app.mantenimiento verificar` compruebe además 11, 12, 14 y 15.

### Dueños, con la iteración 01

`acceso`: + `usuario_almacen`, `usuario.despacho_autonomo`. `almacenes`: + `almacen.despacho_epp_con_aprobacion`, `almacen.hora_descarga`. **`proyectos`** (nuevo): `proyecto`, `asignacion_proyecto`. **`notificaciones`** (nuevo): `suscripcion_push`. **`sincronizacion`** (nuevo): `dispositivo`, `dispositivo_usuario`, `conflicto_sincronizacion`, `operacion_recibida`. `movimientos`: + `vale.proyecto_id`, `vale.lote_id`, `vale.capturado_sin_conexion`, `vale.capturado_en`, `vale.dispositivo_id`. `autorizaciones`: + `autorizacion.tipo`, `renglones_resueltos`, `id_cliente`. `catalogo`: + `categoria.alto_valor`, `dias_aviso_inspeccion` de categoría y artículo. `inspecciones`: + `inspeccion.id_cliente`. `archivos`: + `adjunto.inspeccion_id`.

### Qué movimientos genera cada vale

**No hay tipos de vale nuevos** ni cambia la tabla de arriba. Cambia solo qué lleva el vale:

- Una ENTREGA lleva `proyecto_id` (o nulo, «Sin proyecto», PR-10); su CANCELACION lo hereda. El proyecto no cambia origen ni destino: la entrega sigue saliendo del almacén que entrega (`vale.almacen_id`), aunque el consumo cuente para el proyecto de otro almacén (PR-14, D-13).
- Un TRASPASO entre dos almacenes de tercer nivel (traslado lateral, X-18) genera los mismos movimientos (almacén de origen → EN_TRANSITO) y su RECEPCION igual (EN_TRANSITO → destino). Con autorización, el vale lleva el `autorizacion_id` de tipo TRASLADO; con envío propio, sus movimientos llevan `X-16` y `X-18` en `reglas`.
- Los vales de una importación o de un traspaso por Excel llevan `lote_id`.
- Un vale sincronizado desde la app de Android genera exactamente los mismos movimientos que en línea, con las columnas de captura sin conexión; resolver un conflicto con «Guardar sin los renglones en conflicto» crea un vale **nuevo** del mismo tipo.

### Índices

Los de las tablas de arriba, más `vale(proyecto_id, tipo, creado_en)` para el uso por proyecto (TB-05) y `vale(lote_id)` para la bitácora por vale (BT-02). La bitácora por vale cuenta renglones y unidades solo de los vales de la página; si el plan de ejecución lo pide, se agrega el índice `movimiento(vale_id, articulo_id)` que ya prevé la sección «Índices». Deudores y la lista de inspecciones pendientes usan la tabla derivada con `row_number()` de Seguimiento; se miden antes de agregar índices.


## Implementación FEAT-004: mínimos por almacén

La migración `0013_minimos` crea `minimo`: clave primaria compuesta (`almacen_id`, `articulo_id`), ambas llaves foráneas, y `cantidad` entera no negativa. No modifica existencias: el mínimo configura una alerta contra la cantidad disponible. No existe fila cuando el artículo no tiene mínimo. Se conserva el estado de la pieza y su ubicación; el cambio de estado usa el evento y la auditoría existentes.
