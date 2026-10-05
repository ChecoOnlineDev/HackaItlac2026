# Contratos de API

Endpoints, cuerpos, errores y permisos del MVP. Todo va bajo `/api`, en JSON, con la sesión en una cookie.

Estado: es el contrato acordado para construir. Si al implementar cambia, se actualiza aquí en el mismo cambio.

## Convenciones

- Los `id` son UUID en texto, por ejemplo `01a10a17-3a3b-74ed-89d0-2082afd9941a` ([ADR-006](decisions/ADR-006-identificadores-uuid-y-folio.md)). En los ejemplos se abrevian.
- Las fechas van en ISO 8601; las horas, en UTC.
- Las listas admiten `pagina` y `tamano` y responden `{elementos, total}`.
- Cada endpoint exige un **permiso**; la columna "Permiso" da su clave ([ADR-007](decisions/ADR-007-permisos-por-clave.md)). Qué roles lo tienen de inicio está en la sección 8.2 de las [reglas](../product/reglas-de-negocio.md). "Sesión" significa que basta haber entrado.
- El almacén sale del usuario de la sesión. Quien tiene `almacenes.todos` lo indica con `almacen_id`.
- Los datos reservados no se envían sin su permiso de información: `costo_unitario` pide `catalogo.costos`; `curp` y `nss` piden `trabajadores.ver_datos_personales`.

### Errores

```json
{ "codigo": "SIN_PERMISO", "mensaje": "Tu rol no puede hacer esto.", "detalles": null }
```

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTENTICADO` | No hay sesión o venció. |
| 403 | `SIN_PERMISO` | El rol del usuario no tiene el permiso del endpoint. |
| 404 | `NO_ENCONTRADO` | El recurso no existe. |
| 409 | `VALE_CAMBIO` | Al confirmar, la evaluación ya no es la misma. Incluye la evaluación nueva en `detalles`. |
| 409 | `ALMACEN_CAMBIO` | Al confirmar, el usuario ya no está asignado al almacén en el que capturó el vale. No se guarda; incluye el almacén nuevo y el borrador se conserva (AC-13). |
| 409 | `CODIGO_REPETIDO` | El código ya identifica otra cosa. Incluye en `detalles` su `tipo`, su `ref_id` y una `descripcion` de quién es. |
| 409 | `TRABAJADOR_EXISTE` | Al dar de alta, el número de empleado o la CURP ya existen (T-02). Incluye en `detalles.trabajador` a la persona (`id`, `numero_empleado`, `nombre`, `estado`) y en `detalles.coincide_por` el dato que coincidió, para ofrecer el reingreso. |
| 409 | `CON_PENDIENTES` | No se puede emitir el vale de no adeudo. Incluye los pendientes. |
| 409 | `CON_MOVIMIENTOS` | No se puede eliminar ni cambiar control o retorno. |
| 409 | `NO_CANCELABLE` | El vale no se puede cancelar; incluye el motivo (K-03, K-04). |
| 422 | `DATOS_INVALIDOS` | Falta un dato o tiene forma incorrecta. Incluye el campo. |
| 403 | `PIN_INCORRECTO` | El PIN de autorización no es válido (403 y no 401, para no cerrar la sesión). |
| 429 | `DEMASIADOS_INTENTOS` | Cinco contraseñas o PIN fallidos seguidos: bloqueo de cinco minutos. Incluye `detalles.segundos_espera` y la cabecera `Retry-After`. Se responde ya en el quinto intento fallido. |

## Acceso

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/sesion` | Público | Entra con `{usuario, contrasena}` y deja la cookie de sesión. Responde `{usuario: {id, nombre, usuario}, rol: {id, nombre}, almacen: {id, clave, nombre} o null, permisos: [claves]}`. Credenciales incorrectas o usuario inactivo: 401 con "Usuario o contraseña incorrectos", sin decir cuál falló. |
| `GET /api/sesion` | Sesión | Devuelve la sesión actual con la lista de permisos. La interfaz la usa para mostrar menús y botones. |
| `DELETE /api/sesion` | Sesión | Sale y borra la cookie. Responde 204. |

## Escaneo y búsqueda

Responden solo lo que el usuario puede ver: trabajadores con `trabajadores.ver`, artículos y piezas con `catalogo.ver`, y vales con `vales.ver`.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/escaneo/{codigo}` | Sesión | Identifica un código: `{tipo, id, resumen}`. `tipo`: TRABAJADOR, ARTICULO, PIEZA, VALE o DESCONOCIDO. Lo que el usuario no puede ver llega como DESCONOCIDO. |
| `GET /api/busqueda?q=` | Sesión | Coincidencias en artículos, piezas (por serie) y trabajadores (nombre o número). |

## Trabajadores

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/trabajadores` | `trabajadores.ver` | Lista con vigencia y situación. Filtros: `q` (parte del nombre o del número) y `situacion` (`SIN_PENDIENTES`, `CON_PENDIENTES`, `NO_ADEUDO_EMITIDO`). Nunca trae CURP ni NSS. |
| `POST /api/trabajadores` | `trabajadores.administrar` | Alta (T-03): `{nombre, numero_empleado, puesto, area_obra, inicio, fin}` y opcionales `{referencia, tallas, curp, nss}`. Responde 201 con la ficha. Si el número o la CURP ya existen responde 409 `TRABAJADOR_EXISTE` con la persona, para ofrecer el reingreso. Fin anterior a inicio: 422 con `detalles.campo = "fin"`. |
| `GET /api/trabajadores/{id}` | `trabajadores.ver` | Ficha: datos, `periodo` vigente, `vigencia` `{vigente, motivo, regla}`, `situacion`, `codigos`, `tiene_foto` y `foto_url`, `resguardo` (retornables con código, fecha de entrega, folio y almacén) y `pendientes` `{total, de_periodos_anteriores, regla}`. `curp` y `nss` solo existen en la respuesta con `trabajadores.ver_datos_personales`; sin el permiso la clave no se envía. |
| `POST /api/trabajadores/{id}/periodos` | `trabajadores.administrar` | Reingreso o extensión: `{inicio, fin}` y opcionales `{puesto, area_obra, referencia}` (sin puesto o área se conservan los del periodo anterior). Registra el periodo nuevo, regresa a Activo (T-02) y responde 201 con la ficha. |
| `POST /api/trabajadores/{id}/codigos` | `trabajadores.administrar` | Liga una credencial escaneada con `{codigo}` o, sin `codigo`, genera un código propio para imprimir (T-05). Responde 201 `{codigo, tipo, generado}`. Un código ya usado responde 409 `CODIGO_REPETIDO` diciendo de quién es. |
| `POST /api/trabajadores/{id}/foto` | `trabajadores.administrar` | Sube o reemplaza la foto (T-09). Multipart con el campo `archivo`. Solo acepta imágenes PNG, JPEG o WEBP (por su contenido) y rechaza las que pesan más del tamaño permitido (422). Responde `{tiene_foto, foto_url}`. El cambio queda en el registro de cambios. |
| `GET /api/trabajadores/{id}/foto` | `trabajadores.ver` | Entrega la imagen con su tipo de contenido, solo con sesión. 404 "Sin foto registrada." si no tiene. La ficha indica si el trabajador tiene foto. |
| `POST /api/trabajadores/{id}/baja` | `trabajadores.iniciar_baja` | Inicia la baja (B-01): pasa a Baja en proceso y responde `{id, estado, estado_texto, pendientes, puede_emitir_no_adeudo, reglas}` con los pendientes de todos los almacenes (B-02, sin consumibles, B-03). Si ya estaba en proceso solo repite los pendientes; si está Inactivo, 409. |
| `DELETE /api/trabajadores/{id}/baja` | `trabajadores.administrar` | Cancela la baja en proceso (B-07): vuelve a Activo y responde la ficha. Si la baja no está en proceso, 409. |

La emisión del vale de no adeudo (B-04, B-08) es de `movimientos`, en `POST /api/trabajadores/{id}/no-adeudo` (sección Vales).

## Catálogo

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/categorias` | `catalogo.ver` | Lista. |
| `POST /api/categorias`, `PATCH /api/categorias/{id}` | `catalogo.administrar` | Crea o edita una categoría y su plantilla (CF-01, CF-02). |
| `GET /api/articulos` | `catalogo.ver` | Lista. Filtros: `q`, `categoria_id`, `activo`. |
| `POST /api/articulos` | `catalogo.administrar` | Crea un artículo; toma la plantilla de su categoría si no se indican reglas. El costo solo se acepta con `catalogo.costos`. |
| `GET /api/articulos/{id}` | `catalogo.ver` | Ficha: reglas, existencias por almacén y quién lo tiene (C-03). |
| `PATCH /api/articulos/{id}` | `catalogo.administrar` | Edita datos, límite, aviso de cantidad inusual y requisitos. Rechaza cambios de control o retorno con movimientos (CF-05). |
| `POST /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Inactiva con `{motivo}` (CF-10). |
| `DELETE /api/articulos/{id}/inactivacion` | `catalogo.administrar` | Reactiva (CF-13). |
| `DELETE /api/articulos/{id}` | `catalogo.administrar` | Elimina solo si no tiene movimientos (CF-12). |
| `GET /api/piezas/{id}` | `catalogo.ver` | Ficha: estado, inspección, ubicación e historial (C-02). |
| `POST /api/piezas/{id}/inspecciones` | `piezas.inspeccionar` | Registra una inspección (P-01). |
| `POST /api/piezas/{id}/estado` | `piezas.inspeccionar` | Marca No apta, con observación (P-03). |
| `POST /api/piezas/{id}/ajuste-vigencia` | `piezas.ajustar_vigencia` | Cambia la fecha hasta la que vale la inspección vigente, con `{vigente_hasta, motivo}` (P-07). No cambia el resultado de la inspección. Se rechaza si la pieza está No apta, si la fecha pasa de la inspección más la vigencia del artículo, o si quien la pide registró esa inspección. |

## Almacenes y existencias

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/almacenes` | `inventario.ver` | Lista con su red. |
| `GET /api/almacenes/{id}/existencias` | `inventario.ver` | Existencias y disponibles por artículo. |

## Vales

El mismo cuerpo sirve para evaluar y para confirmar.

```json
{
  "tipo": "ENTREGA",
  "trabajador_id": "01a10a17-…",
  "destino_almacen_id": null,
  "vale_origen_id": null,
  "renglones": [
    { "codigo": "ALT-024", "cantidad": 1, "condicion": null, "observacion": null }
  ]
}
```

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/vales/evaluar` | Según el tipo | Evalúa sin escribir. |
| `POST /api/vales` | Según el tipo | Confirma. Agrega `id_cliente`, `observacion`, `autorizacion_id` y `firma`. |
| `GET /api/vales/{id}` | `vales.ver` | Detalle con renglones. |
| `GET /api/vales/por-token/{token}` | `vales.ver` | El vale que abre su QR. |
| `GET /api/vales?tipo=&almacen_id=&desde=&hasta=&trabajador_id=&usuario_id=` | `vales.ver` | Lista. Sin `almacenes.todos`, solo los del almacén asignado. Con el `usuario_id` de la sesión y las fechas de hoy resuelve "Mis movimientos de hoy" (C-12). |
| `GET /api/traspasos/por-recibir` | `traspasos.operar` | Traspasos en tránsito hacia el almacén de la sesión. |
| `POST /api/trabajadores/{id}/no-adeudo` | `no_adeudo.emitir` | Emite el vale de no adeudo (B-04). Responde 409 `CON_PENDIENTES` si los hay. |
| `POST /api/vales/{id}/cancelacion` | `vales.cancelar` | Cancela con `{motivo, id_cliente, rehacer}` y genera los movimientos inversos (K-01 a K-04). Con `rehacer: true` la respuesta trae además un `borrador` con los renglones del vale original, sin firma ni autorización, para corregirlos y confirmar de nuevo (K-05). Con `vales.cancelar` solo los propios; con `vales.cancelar_todos`, los de cualquiera. Responde 409 `NO_CANCELABLE` si no procede. |

Permiso y campos propios de cada tipo:

| Tipo | Permiso | Campos propios |
|---|---|---|
| ENTRADA | `inventario.entradas` | `almacen_id`; en artículos por pieza, cada renglón lleva `pieza: {codigo, numero_serie, inspeccion}` |
| ENTREGA | `entregas.crear` | `trabajador_id`; `firma` |
| DEVOLUCION | `devoluciones.crear` | `condicion` por renglón; `trabajador_id` solo en renglones por cantidad |
| TRASPASO | `traspasos.operar` | `destino_almacen_id` |
| RECEPCION | `traspasos.operar` | `vale_origen_id`; renglones recibidos |

Respuesta de `evaluar`:

```json
{
  "nivel": "ROJO",
  "puede_confirmar": false,
  "renglones": [
    {
      "renglon": 1,
      "codigo": "ALT-024",
      "articulo": { "id": "01a10a2b-…", "nombre": "Arnés poliéster", "marca": "…", "talla": "M", "control": "PIEZA" },
      "pieza": { "id": "01a10a3c-…", "estado": "APTO", "inspeccion_vigente_hasta": "2026-09-30" },
      "titular": null,
      "cantidad": 1,
      "disponible": 1,
      "nivel": "ROJO",
      "motivos": [
        { "regla": "E-06", "nivel": "ROJO", "mensaje": "Inspección vencida el 30/09/2026." }
      ],
      "pide_observacion": false,
      "autorizable": false,
      "requiere_confirmacion": false
    }
  ]
}
```

`requiere_confirmacion` es verdadero cuando la cantidad del renglón alcanza el aviso de cantidad inusual del artículo (E-27); la interfaz pide confirmarla y no decide nada por su cuenta. `evaluar` nunca escribe: el borrador vive en el dispositivo hasta `POST /api/vales` (E-28).

Al confirmar se agrega:

```json
{
  "id_cliente": "b1f6…",
  "observacion": null,
  "autorizacion_id": null,
  "firma": { "modo": "PANTALLA", "imagen": "data:image/png;base64,…", "trazo": [] }
}
```

- Responde 201 con el vale: `{id, folio, token, creado_en, renglones}`.
- Si el `id_cliente` ya existe, responde 200 con el vale que se guardó la primera vez.
- Si la evaluación cambió, responde 409 `VALE_CAMBIO`.

## Autorizaciones

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/autorizaciones` | `entregas.crear` | Solicita con `{trabajador_id, renglones, motivo}`. Responde `{id, estado, vence_en}`. |
| `GET /api/autorizaciones/{id}` | Sesión | Estado de una solicitud. La ve quien la pidió y quien puede resolverla. El solicitante la consulta cada tres segundos. |
| `GET /api/autorizaciones?estado=PENDIENTE` | `autorizaciones.resolver` | Solicitudes por resolver. |
| `POST /api/autorizaciones/{id}/resolucion` | `autorizaciones.resolver` | `{decision}` desde la sesión de quien autoriza; o `{decision, usuario, pin}` desde el dispositivo del almacenista. En el segundo caso el permiso se verifica sobre ese usuario. |

## Importación

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /api/importacion/vista-previa` | `inventario.entradas` | Recibe `{filas, columnas}` y devuelve filas válidas, filas con error y artículos que se crearían. No escribe. |
| `POST /api/importacion` | `inventario.entradas` | Confirma: crea artículos faltantes y un vale de entrada por almacén. |

La tabla se lee en el navegador; al servidor llegan filas ya separadas en columnas.

## Reportes

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/reportes/existencias` | `reportes.existencias` | Por almacén y artículo. Filtros: `almacen_id`, `categoria_id`. |
| `GET /api/reportes/movimientos` | `reportes.movimientos` | Bitácora. Filtros: fechas, almacén, tipo, trabajador, artículo y `usuario_id` (quien hizo el vale, C-11). Sin `almacenes.todos`, solo el almacén asignado, también al filtrar por usuario; con él, todos los almacenes y usuarios. |
| `GET /api/reportes/adeudos` | `reportes.adeudos` | Pendientes por trabajador. Filtro: `solo_no_vigentes`. |
| `GET /api/reportes/consumo` | `reportes.consumo` | Consumo de artículos consumibles (C-08). Filtros: fechas, `almacen_id`, `categoria_id`, `articulo_id`, `trabajador_id`. Responde por artículo el total y el desglose por trabajador, restando las cancelaciones. Sin `almacenes.todos`, solo el almacén asignado. Sin costos (RG-12). |

Todos aceptan `formato=csv`.

## Etiquetas

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /api/etiquetas?tipo=` | `etiquetas.imprimir` | Lista de `{codigo, texto}` para credenciales, piezas o estantes. Las credenciales piden además `trabajadores.ver`; piezas y estantes, `catalogo.ver`. El QR lo dibuja el navegador. |

## Previsto por la segunda ola

| Feature | Endpoints | Permiso |
|---|---|---|
| FEAT-001 | `GET /api/publico/vales/{token}` sin sesión; `GET /api/reportes/integridad` | Público; `reportes.movimientos` |
| FEAT-002 | `POST /api/almacenes`, `POST /api/almacenes/{id}/cierre`, `GET /api/almacenes/{id}/reporte-cierre`, `GET /api/reportes/valor-inventario` | `almacenes.administrar`; `reportes.valor_inventario` |
| FEAT-003 | `GET`, `PUT /api/puestos/{id}/dotacion` | `catalogo.ver`; `catalogo.administrar` |
| FEAT-004 | `PUT /api/almacenes/{id}/minimos`; `POST /api/piezas/{id}/estado` admite mantenimiento y calibración | `inventario.minimos`; `piezas.inspeccionar` |
| FEAT-006 | `GET /api/permisos`; `GET`, `POST`, `PATCH /api/roles`; `PUT /api/roles/{id}/permisos`; `GET`, `POST`, `PATCH /api/usuarios`; `POST /api/usuarios/{id}/contrasena` | `acceso.administrar` |
| FEAT-006 (asignación de personal) | `GET /api/personal?almacen_id=&sin_almacen=`; `PATCH /api/usuarios/{id}/almacen` con `{almacen_id}` | `almacenes.asignar_personal` |
