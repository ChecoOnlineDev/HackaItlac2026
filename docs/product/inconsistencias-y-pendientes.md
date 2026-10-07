# Inconsistencias detectadas y posibles soluciones

> **Estado:** documento de trabajo para iterar. **No cambia nada del proyecto**: no hay código modificado ni reglas alteradas. Cada punto describe qué se encontró, dónde, qué efecto tiene y una **posible solución** apoyada en la lógica que ya está aplicada. Nada de lo propuesto está decidido hasta que lo apruebe el usuario; lo que sí está decidido va marcado como **Decidido**.
> **Cómo leerlo:** la gravedad es *Alta* (puede dar un resultado equivocado o bloquear la operación), *Media* (confunde o estorba) o *Baja* (documentos o detalles). Las referencias a reglas (X-01, RG-10…) son las de [reglas-de-negocio.md](reglas-de-negocio.md).

## 1. Resumen

| # | Tema | Gravedad | Solución propuesta en una línea |
|---|---|---|---|
| 1 | Quién recibe un traspaso en un almacén de proyecto | Alta | Permiso de recibir separado de enviar |
| 2 | Piezas sin código de pieza ni serie | Alta | **Decidido:** código automático y serie pendiente |
| 3 | El administrador ve «Pedir compra urgente» | Media | Quitarlo del menú del administrador |
| 4 | Plantilla de traslados entre almacenes | Media | Columnas de origen y destino para verificar |
| 5 | Filtros del inventario | Media | Filtros por existencia, tipo, control, marca y estado |
| 6 | Origen de los límites y de la dotación | Media | Documentar qué es del reto y qué es valor inicial nuestro |
| 7 | Almacén vacío sin explicación | Baja | Mensaje de estado vacío |
| 8 | Historias de traspasos dicen «almacenista» | Media | Corregir las historias a «supervisor» |
| 9 | `README` dice que FEAT-008 no está construido | Baja | Actualizar la frase |
| 10 | Menú con ocho grupos contra un criterio de siete | Baja | Ajustar el criterio |
| 11 | Mínimos de stock sin construir | Media | Dejar claro que el tablero no los muestra |
| 12 | Datos del Excel de compras incompletos | Media | Completar o aceptar marca genérica |
| 13 | Decimales rechazados | Media | **Decidido:** unidad entera menor con columna `unidad` |
| 14 | Desplegable de almacén al entregar equipo | Media | Reproducir con sesión de administrador |
| 15 | Pruebas que fallan desde antes | Media | Aislar qué prueba contamina |
| 16 | Dos categorías de EPP muy parecidas | Baja | Mantener o juntar |
| 17 | Versión de Docker anterior a los últimos cambios | Baja | Reconstruir |
| 18 | Archivos y documentos sin subir | Baja | Commit y push |

---

## 2. Inconsistencias de lógica de negocio

### 2.1 Quién recibe un traspaso en un almacén de proyecto — Alta

- **Qué se encontró.** El reto dice que a los almacenes de proyecto se asignan almacenistas (turnos de 24 horas) que quedan «responsables» de lo recibido (plática, min 32-33; regla X-08 «quien recibe queda como responsable»). Pero X-01 reserva enviar **y recibir** traspasos al Supervisor, con un solo permiso, `traspasos.operar`. El Almacenista no lo tiene (reglas, sección 8).
- **Dónde.** `reglas-de-negocio.md` X-01 y X-08; `red-de-almacenes-y-flujo.md` secciones 10 y 12.1 (mejora 2); permiso `traspasos.operar` en `acceso/permisos.py`.
- **Efecto.** De noche, o sin el supervisor, nadie puede recibir el material de un traspaso que ya está En tránsito. Mientras tanto la existencia no cuenta para ningún almacén.
- **Posible solución (consistente con lo ya hecho).** Separar el permiso: dejar `traspasos.operar` para **enviar** y crear `traspasos.recibir` para **recibir**, que se asigna al Supervisor y se puede asignar al Almacenista del proyecto desde Roles y permisos (FEAT-006). Así no se compara el nombre del rol (regla de AGENTS.md) y se respeta X-10 (solo el destino recibe). Cambios: sección 8 de reglas, X-01, el contrato de `por-recibir` y la ruta `recibir-detalle`.
- **Decidido (7 oct 2026).** Se aprobó la separación: `traspasos.recibir` (Supervisor y Administrador; se puede dar al Almacenista). Reglas al día en X-01, X-08, X-10 y la sección 8; sin construir.

### 2.2 Piezas sin código de pieza ni serie — Alta

- **Qué se encontró.** El Excel de piezas (`importacion_equipo_por_pieza_kepler.xlsx`, 137 filas de 23 artículos) no trae código de pieza ni serie. En la vista previa da 137 errores («Falta el código de la pieza», «Falta el número de serie»). La regla I-02 exige ambos: «cada pieza entra con su código único, marca y número de serie del fabricante».
- **Aclaración sobre el Excel original.** Las claves numéricas del Excel de compras no son identificadores de pieza: son claves de clasificación de producto que se repiten (una sola aparece en 160 filas). No sirven como código de pieza.
- **Efecto.** Las herramientas eléctricas, el equipo de alturas y el de alto valor no pueden entrar por importación, que es justo el equipo más controlado.
- **Posible solución.**
  1. **Código de pieza automático.** Igual que ya se genera el código de artículo (`PREFIJO-NNNN`), generar el de pieza cuando el archivo no lo trae, por ejemplo `HEL-0003-001`. RG-10 ya acepta cualquier código «tal como viene», así que uno numérico o alfanumérico es válido; el formato es solo una convención.
  2. **Serie.** No se puede inventar: es la del fabricante. Opción A (cambia I-02): la pieza entra con la serie «pendiente» y no se puede entregar hasta registrarla, igual que la pieza sin inspección inicial (I-03). Opción B (no cambia reglas): alguien llena las series en el Excel antes de importar.
- **Riesgo.** Cambiar un código después de imprimir el QR obliga a reimprimir la etiqueta; el código identifica una sola cosa (RG-10).
- **Decidido:** la pieza **entra con serie pendiente** (opción A) y el código de pieza se genera automáticamente. El detalle y el orden de construcción están en [plan-de-implementacion.md](plan-de-implementacion.md), secciones 3 y 4.

### 2.3 El administrador ve «Pedir compra urgente» — Media

- **Qué se encontró.** SC-01 da `compras.solicitar` a Almacenista, Supervisor y Administrador. El administrador lo tiene porque tiene todos los permisos, pero la solicitud nace en el almacén del solicitante: sin almacén asignado, el administrador tiene que elegir uno. Además, la solicitud la **atiende Compras**; el módulo existe para recibir las peticiones de los supervisores de los almacenes, sobre todo de proyecto.
- **Dónde.** `reglas-de-negocio.md` SC-01 y SC-03; menú del administrador (grupo Operación).
- **Efecto.** Una entrada del menú que casi nunca debe usar y que confunde: no queda claro a quién le llega.
- **Posible solución.** Quitarla del menú del administrador sin quitarle el permiso: mostrar «Pedir compra urgente» solo a quien tiene almacén asignado (el menú ya se filtra por permisos y datos de sesión). El administrador conserva la cola y el seguimiento de solicitudes. Alternativa: quitar `compras.solicitar` al rol Administrador desde Roles y permisos.
- **Decisión pendiente.** Escoger entre ocultar en el menú o quitar el permiso.

### 2.4 Plantilla de traslados entre almacenes — Media

- **Qué se propone.** Una plantilla de Excel para traslados con el código del almacén que envía, el del que recibe y las cantidades.
- **Cómo encaja.** FEAT-009 ya define la plantilla del traspaso con `codigo`, `cantidad`, `codigo pieza` y `serie`; el destino se elige en pantalla (TR-02), porque un traspaso es **un vale con un solo origen y un solo destino**, y la ruta (X-03) se evalúa una sola vez.
- **Posible solución.** Agregar a la plantilla las columnas `almacen_origen` y `almacen_destino`. Dos formas, de menor a mayor cambio:
  1. **Verificar** (recomendada para el MVP): las columnas deben coincidir con el origen y el destino elegidos en pantalla; si no, error por fila. Evita mandar el archivo equivocado al almacén equivocado y no cambia ninguna regla.
  2. **Dividir:** un archivo con varios destinos genera un vale por destino. Es más cómodo, pero rompe «un archivo es un vale» (TR-07) y exige evaluar X-03 por cada destino.
- **Decisión pendiente.** Elegir 1 o 2.

### 2.5 Origen de los límites y de la dotación — Media

- **Qué se encontró.** Hubo la duda de dónde salen los límites por trabajador y qué es la dotación.
- **Qué es del reto.** El bloqueo por límite sale del PDF (función 6: «si se supera, bloquear hasta que un supervisor la autorice»); los ejemplos, de la plática: tres guantes por semana (min 36) y que no se acumulen tres arneses o detectores (min 10). La dotación es la lista de equipo recomendada por puesto (PDF p.3 y p.7): al identificar al trabajador se muestra qué le falta; fuera de la dotación **avisa** en amarillo (D-03), mientras que el límite **bloquea** en naranja (L-04).
- **Qué es nuestro.** Los números concretos de las categorías (1 en posesión, 3 por 7 días, 5 en consumibles) son valores iniciales nuestros, no del reto. Los puestos y su dotación de prueba también son propuesta.
- **Posible solución.** Documentar en la sección 4 de las reglas qué es del reto y qué es valor inicial editable, y avisar en la pantalla de categorías que son valores de partida. No cambia lógica.

### 2.6 Dos categorías de EPP muy parecidas — Baja

- **Qué se encontró.** «EPP básico» (retornable, límite 1 en posesión) y «EPP de dotación» (consumible, 3 por semana) solo se distinguen porque una se devuelve y la otra no. En el Excel de compras quedaron 2 y 17 artículos. La frontera es difusa: el calzado es dotación, el casco es básico.
- **Posible solución.** Mantener las dos (conserva la diferencia entre lo que regresa y lo que no) o juntarlas en «EPP» y decidir retorno por artículo. Se puede ajustar editando solo `categorias_iniciales.py`.
- **Decisión pendiente.** Mantener o juntar, con la opinión de quien opera el almacén.

---

## 3. Inconsistencias de interfaz y de uso

### 3.1 Filtros del inventario — Media

- **Qué se encontró.** La pantalla de inventario filtra por almacén, categoría y texto. En un almacén sin existencias (como Contratistas hoy) no explica por qué está vacío.
- **Posible solución.** Agregar filtros que ya tienen sustento en los datos: con o sin existencia, tipo (EPP o herramienta), control (por pieza o por cantidad), marca, y estado de las piezas (aptas, no aptas, en mantenimiento). Reutilizar el patrón de hoja de filtros que ya usa la pantalla.

### 3.2 Almacén vacío sin explicación — Baja

- **Posible solución.** Estado vacío con texto claro: «Este almacén no tiene existencias todavía», con un enlace a la entrada de proveedor o a recibir traspaso, según el permiso.

### 3.3 Desplegable de almacén al entregar equipo — Media

- **Qué se encontró.** Se reportó un desfase del desplegable de «Almacén que opera» al entregar equipo desde la cuenta de administrador. No se pudo reproducir: falta una sesión de administrador en el navegador para verlo, y el código del selector y del componente de lista no muestra una causa evidente.
- **Posible solución.** Reproducirlo con la sesión de administrador, capturar la lista abierta y revisar cómo se posiciona la lista contra contenedores con desplazamiento.

---

## 4. Inconsistencias entre documentos

| # | Qué dice | Qué debería decir | Dónde |
|---|---|---|---|
| 8 | «Como almacenista del almacén de origen, quiero enviar…» y «Como almacenista del almacén de destino, quiero recibir…» | «Como supervisor…», porque X-01 reserva el traspaso al supervisor | `stories/fase-5-traspasos.md` líneas 9 y 32 (US-TRS-001 y 002) |
| 9 | FEAT-008 «sin construir» | FEAT-008 está construido y en el remoto | `README.md` línea 25 |
| 10 | «Ninguno ve más de 7 grupos» de menú | El administrador ve ocho grupos más Inicio; el criterio no se cumple con la tabla del propio brief | `FEAT-008` línea 303 |
| 11 | El tablero y las historias mencionan alertas de mínimo | X-05 (aviso de salida por debajo del mínimo) **no está implementada**; el tablero no puede mostrar «bajo mínimo» hasta FEAT-004 | `reglas-de-negocio.md` X-05; `traspaso.py` |

**Posible solución.** Corregir los cuatro textos en un solo cambio de documentación; ninguno afecta al código. Para el 10, o se ajusta el criterio a «los grupos que su permiso permite» o se agrupan Consulta y Personas.

---

## 5. Datos y carga de inventario

### 5.1 Datos incompletos en el Excel de compras — Media

- **Qué se encontró.** De los 323 artículos por cantidad, 72 quedaron sin marca (no coincidían con la lista conocida), y de las 137 piezas, 62. Algunos costos unitarios parecen compras agrupadas (línea de vida a 20 594, llave de impacto a 10 868).
- **Posible solución.** Aceptar «sin marca» (el campo es opcional en el alta) o usar una marca genérica solo si el usuario lo decide; revisar los costos altos con Compras. No inventar datos.

### 5.2 Decimales rechazados — Media

- **Qué se encontró.** Tres filas (clavo 0.25, alambre 60.12, bolsa 25.15) se rechazan por ser decimales (I-13), y una fila es un servicio, que no es artículo.
- **Posible solución.** Convertirlas a una unidad entera menor (gramos, centímetros, piezas) y dejar la unidad en el artículo; el servicio se excluye. No se redondea en silencio.
- **Decidido:** convertir a unidad entera menor, declarándola en una columna `unidad` de la importación (sin conversión automática). Detalle en [plan-de-implementacion.md](plan-de-implementacion.md), sección 5; falta confirmar con Compras la unidad original de las tres filas.

---

## 6. Calidad y operación

### 6.1 Pruebas que fallan desde antes — Media

- **Qué se encontró.** En la suite completa del backend fallan 16 pruebas de sesiones y renovación (`tests/test_sesiones.py` y `tests/seguridad/test_refresh.py`). Pasan solas y con las pruebas de importación, así que otro archivo anterior las contamina. Las mismas 16 fallan en el último commit anterior a estos cambios.
- **Posible solución.** Buscar la prueba que deja el estado sucio (probablemente reloj o sesiones sin limpiar), corregirla y volver a correr todo.
- **Relacionado.** Dos archivos `test_visibilidad_almacenes.py` (en `consulta/` y en `movimientos/`) tienen el mismo nombre y rompen la recolección de la suite completa; renombrar uno.

### 6.2 Versión de Docker anterior a los últimos cambios — Baja

- **Qué se encontró.** La aplicación en `http://127.0.0.1:21040` se construyó antes del rediseño de la ficha de almacén, la vista previa paginada y los últimos ajustes.
- **Posible solución.** `docker compose up -d --build` antes de cualquier prueba en navegador.

### 6.3 Archivos y documentos sin subir — Baja

- **Qué se encontró.** Los documentos de FEAT-009 y los de este análisis están sin commit. `docs/recursos/plantilla-alta.xlsx` es una descarga del usuario y no se sube.
- **Posible solución.** Commit y push de los documentos cuando el usuario lo indique.

---

## 7. Orden sugerido de decisión

1. **Alta:** 2.1 (quién recibe) y 2.2 (código y serie de las piezas). Bloquean datos reales.
2. **Alcance:** aprobar FEAT-009 y «Dejar fuera las filas con error».
3. **Media:** 2.3, 2.4, 3.1 y 2.5, que mejoran el uso diario.
4. **Baja:** corregir los cuatro textos (sección 4) y reconstruir Docker.
5. **Verificación:** probar en navegador con cada rol y resolver 3.3 y 6.1.
