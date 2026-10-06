# Historias de la Fase 6 — Consulta, reportes e importación

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-CON-001: Consultar por escaneo o por texto

Como usuario de cualquier rol, quiero escanear o escribir y ver de inmediato quién tiene un artículo o qué tiene un trabajador, para responder sin revisar papeles.

**Criterios de aceptación**

- Escanear una credencial muestra al trabajador, su vigencia y su resguardo.
- Escanear una pieza muestra su estado, su inspección, quién la tiene y su historial completo: movimientos, inspecciones y cambios de estado.
- Abrir un artículo muestra sus existencias por almacén y qué trabajadores lo tienen.
- Escanear el QR de un vale lo abre.
- Escribir texto busca en nombre de artículo, número de serie y nombre o número de trabajador. Por ejemplo, "detector" lista los detectores y quién tiene cada uno.
- Cada usuario ve solo lo que permiten los permisos de su rol. Con los roles iniciales: sin costos fuera de Compras, sin CURP ni NSS fuera de RH, y RH no ve el inventario.
- Cada ficha ofrece la acción siguiente que el rol permite: entregarle, devolver o inspeccionar.
- Sin resultados, muestra "No se encontró nada con ese código o texto".

**Reglas:** C-01 a C-04, C-06, RG-12, RG-13.

**Fuera de alcance:** verificación de integridad del vale (FEAT-001); búsqueda por fechas.

**Casos límite:** un texto de menos de dos caracteres no busca; muchos resultados se paginan.

**Evidencia:** búsqueda cronometrada: menos de diez segundos de la pregunta a la respuesta.

---

## US-REP-001: Reportes de existencias, movimientos y adeudos

Como supervisor, Compras o RH, quiero reportes de existencias, movimientos y adeudos, para dar seguimiento sin pedirle datos al almacén.

**Criterios de aceptación**

- Existencias: por almacén y artículo, con filtros por almacén y categoría.
- Movimientos: fecha, folio, tipo, artículo, cantidad, origen, destino, responsable y saldo; con filtros por periodo (rango de fechas), almacén, tipo, trabajador, artículo y usuario.
- Adeudos: por trabajador, lo que tiene pendiente, desde cuándo y de qué almacén; con filtro "solo no vigentes".
- El almacenista solo ve los movimientos de su almacén. También ve el filtro de usuario, dentro de su almacén, como dato informativo.
- Quien tiene `almacenes.todos` ve los movimientos de todos los almacenes y filtra por cualquier usuario.
- Dado un equipo que desapareció, cuando se filtra por su artículo, su almacén y un periodo, entonces se listan los vales que lo movieron con su responsable.
- Cada reporte se descarga en CSV.
- Ningún reporte muestra costos fuera de Compras.
- Sin registros, muestra "No hay registros con esos filtros".

**Reglas:** C-05, C-11, RG-03, RG-12, sección 8.

**Fuera de alcance:** gráficas; EPP por trabajador (C-07); valor del inventario (FEAT-002).

**Casos límite:** rango de fechas invertido se rechaza; el CSV conserva acentos al abrirse en Excel.

**Evidencia:** los reportes después de correr el guion completo.

---

## US-REP-002: Reporte de consumo

Como supervisor o Compras, quiero saber cuántos consumibles se consumen, por artículo, periodo, almacén y trabajador, para entender el gasto y ajustar los límites.

**Criterios de aceptación**

- Lista, por artículo consumible, el total consumido en el periodo, con su unidad.
- Cada artículo se abre para ver el consumo por trabajador, de mayor a menor.
- Filtros: periodo (rango de fechas), almacén, categoría, artículo y trabajador.
- El total resta lo que se cancela: un vale cancelado no cuenta.
- Quien tiene `almacenes.todos` ve todos los almacenes; los demás, solo el suyo.
- No muestra costos (RG-12).
- Se descarga en CSV con los mismos filtros.
- Sin registros, muestra "No hay registros con esos filtros".

**Reglas:** C-08, E-21, K-02, RG-12, sección 8.

**Fuera de alcance:** gráficas; consumo valuado en dinero; devolución de consumible sobrante (V-10).

**Casos límite:** un rango de fechas invertido se rechaza; un trabajador sin consumo en el periodo no aparece.

**Evidencia:** prueba: entregar diez guantes a un trabajador y cinco a otro, cancelar uno de los vales y comparar el total.

---

## US-IMP-001: Importar inventario desde Excel (alta y carga inicial)

Como Compras, quiero cargar el inventario pegando una tabla de Excel, para no capturar cientos de artículos uno por uno.

Es el modo `ALTA` de la importación (I-10): crea los artículos nuevos y suma a los que ya existen. El modo `REPOSICION` está en US-IMP-002.

**Criterios de aceptación**

- Pega una tabla copiada de Excel o sube el archivo; también puede descargar una plantilla de ejemplo para el alta.
- Indica qué columna corresponde a cada dato; el sistema propone la relación a partir del nombre de la columna. La columna del código es opcional si hay nombre.
- La vista previa es una tabla con una fila por renglón del archivo y un estado: **Nuevo**, **Existente (suma)**, **Unido** o **Error**; muestra el saldo antes y después, y un resumen arriba con cuántos hay de cada uno.
- Nada se guarda hasta confirmar.
- Al confirmar se crean los artículos que falten, con la plantilla de su categoría, y un vale de entrada por almacén.
- En artículos por pieza, cada fila es una pieza con su código y su serie.
- Dado un artículo por cantidad que aparece en las filas 2, 5 y 9 para el mismo almacén, cuando se ve la vista previa, entonces sale una sola fila «Unido: filas 2, 5, 9» con la suma; en cambio, un código de pieza o una serie repetidos son error.
- Dado un artículo nuevo sin categoría en el archivo, entonces la vista previa sugiere una según la descripción, con su motivo («La descripción dice «arnés»»), editable por fila; ninguna sugerencia se aplica sin que la persona la vea, y las filas que no coinciden quedan «por revisar» y no entran hasta elegir una categoría. Si el archivo trae categoría, esa manda.
- Dado un artículo nuevo sin código, entonces recibe `PREFIJO-NNNN` (por ejemplo `ALT-0001`), consecutivo por categoría, asignado al confirmar.
- Dada una fila cuya descripción dice SERVICIO, entonces se excluye con un aviso y no cuenta como error.
- Dada una cantidad `0.25` o `0,25`, entonces la fila es un error que pide usar una unidad entera menor, y nunca se redondea; `1,250` vale 1250.
- Dada una cantidad mayor que 100 000, entonces la fila es un error (I-11).
- Dado un artículo que ya existe cuyo nombre, marca o categoría del archivo es distinto, entonces la fila avisa y no cambia nada del artículo.
- Dado un archivo que ya se importó, entonces la vista previa avisa y la confirmación pide una confirmación expresa (`confirmar_repetido`); no es un error (I-12).
- Sin `catalogo.administrar`, las filas que crearían un artículo salen como error («no tienes permiso para dar de alta artículos») y las de artículos que ya existen entran.
- Las filas buenas entran sin esperar a las malas. Las filas con error no se importan y se pueden descargar; en esa descarga, una celda que empieza con `=`, `+`, `-`, `@`, tabulador o retorno de carro se neutraliza con un apóstrofo.
- Repetir la misma importación (mismo `id_lote`) no duplica nada y avisa de las piezas que ya existen.
- Dados dos lotes que se confirman al mismo tiempo con los mismos artículos nuevos, entonces no se duplica ningún artículo ni pieza y las existencias coinciden con la suma de los movimientos.

**Reglas:** I-01, I-02, I-04, I-06, I-10 a I-14, CF-02, RG-09, RG-10, RG-12, sección 8 (`inventario.entradas`, `catalogo.administrar`, `catalogo.costos`).

**Fuera de alcance:** importar trabajadores; fijar existencias a un valor (ajuste); guardar relaciones de columnas; actualizar nombre, marca, categoría o costo de un artículo que ya existe; generar códigos para categorías sin prefijo.

**Casos límite:** una categoría que no existe: se elige una para esas filas; cantidades vacías o con texto: error en la fila; columnas en otro orden o con otros nombres; una fila sin código que coincide en nombre y marca con un artículo existente: suma a ese artículo.

**Evidencia:** importación ensayada con un Excel preparado por alguien que no conoce el sistema; una prueba por cada regla I-10 a I-14 (con su ID en el nombre); una prueba de concurrencia entre dos lotes.

---

## US-IMP-002: Reponer existencias desde Excel

Como Compras, quiero sumar al inventario lo que llegó de artículos que ya están en el catálogo, para reponer existencias sin riesgo de crear artículos duplicados por un error de captura.

Es el modo `REPOSICION` de la importación (I-10): solo suma a artículos que ya existen y nunca crea.

**Criterios de aceptación**

- Elige el modo «Reposición» y puede descargar su plantilla: `codigo`, `cantidad`, `almacen` y, si el artículo es por pieza, `codigo_pieza` y `serie`.
- Dado un código que no existe en el catálogo, entonces esa fila es un error «Ese artículo no existe: dalo de alta primero» (`ARTICULO_NO_EXISTE`), no se crea nada y las demás filas sí entran.
- Dadas columnas de nombre, marca, categoría o costo en el archivo, entonces se ignoran con un aviso; el costo del artículo no cambia aunque la persona tenga `catalogo.costos`.
- La vista previa muestra, por fila, el estado **Existente (suma)** o **Unido** o **Error**, y el saldo antes y después en ese almacén; el resumen de arriba cuenta cada uno. No hay estado «Nuevo» ni sugerencia de categoría.
- Las filas del mismo artículo y el mismo almacén se unen («Unido: filas 3, 8»); un código de pieza o una serie repetidos son error.
- Valen la cantidad entera (I-13), el tope por fila (I-11), el aviso de archivo ya importado (I-12) y la neutralización de la descarga de errores, igual que en el alta.
- Se exige `inventario.entradas` y no hace falta `catalogo.administrar`, porque nunca crea artículos.
- Al confirmar, un vale de entrada por almacén y las existencias suben exactamente en lo importado; nada se guarda antes.
- Dados dos lotes que se confirman al mismo tiempo sobre el mismo artículo, entonces las existencias coinciden con la suma de los movimientos.

**Reglas:** I-01, I-02, I-04, I-06, I-09 a I-13, RG-05, RG-09, RG-10, sección 8 (`inventario.entradas`).

**Fuera de alcance:** crear artículos (es el alta, US-IMP-001); cambiar costo, nombre, marca o categoría; restar o fijar existencias.

**Casos límite:** artículo inactivo (`ARTICULO_INACTIVO`, I-09); artículo por pieza sin `codigo_pieza` o sin serie; almacén que no es el asignado (AC-06); una cantidad con decimales.

**Evidencia:** una prueba por cada regla I-10 a I-13 con su ID en el nombre; prueba de que un código desconocido no crea artículo; prueba de concurrencia entre dos lotes; ensayo con un archivo de reposición real.
