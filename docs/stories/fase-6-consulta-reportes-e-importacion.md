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

## US-IMP-001: Importar inventario desde Excel

Como Compras, quiero cargar el inventario pegando una tabla de Excel, para no capturar cientos de artículos uno por uno.

**Criterios de aceptación**

- Pega una tabla copiada de Excel o sube el archivo.
- Indica qué columna corresponde a cada dato; el sistema propone la relación a partir del nombre de la columna.
- La vista previa separa filas válidas, filas con error (con su motivo) y artículos nuevos que se crearán.
- Nada se guarda hasta confirmar.
- Al confirmar se crean los artículos que falten, con la plantilla de su categoría, y un vale de entrada por almacén.
- En artículos por pieza, cada fila es una pieza con su código.
- Las filas con error no se importan y se pueden descargar.
- Repetir la misma importación no duplica artículos y avisa de las piezas que ya existen.

**Reglas:** I-01, I-02, I-06, CF-02, RG-09, RG-10.

**Fuera de alcance:** importar trabajadores; fijar existencias a un valor (ajuste); guardar relaciones de columnas.

**Casos límite:** una categoría que no existe: se elige una para esas filas; cantidades vacías o con texto: error en la fila; columnas en otro orden o con otros nombres.

**Evidencia:** importación ensayada con un Excel preparado por alguien que no conoce el sistema.
