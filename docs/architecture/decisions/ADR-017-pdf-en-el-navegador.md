# ADR-017: PDF armado en el navegador

Estado: aceptada para FEAT-017 y FEAT-019, dependencias aprobadas por el usuario el 9 de octubre de 2026.

El mismo documento debe poder descargarse desde web y compartirse desde el contenedor Android. Se usa `jspdf` y `jspdf-autotable`, importados sólo al tocar la acción de PDF. La fuente Poppins Regular TTF y su licencia OFL se sirven como archivos locales bajo `/fuentes`; se cargan al generar el documento. Esta decisión no agrega una ruta de PDF en el servidor.

La API sigue siendo la autoridad de permisos y alcance. El cliente proyecta únicamente campos imprimibles de encabezados, categorías y renglones; nunca serializa los DTO completos ni valores en pesos. Recupera renglones de 500 en 500, cede ejecución entre tramos, informa avance y acepta cancelación. Una petición fallida impide guardar un archivo incompleto. Android reutiliza el adaptador existente de archivos temporales y compartir.

Se conserva impresión del navegador. Se requiere comprobar visualmente un documento generado y medir 500 renglones en equipo Android de gama media y 5000 en computadora. La existencia del generador y sus pruebas de proyección no acredita las metas de tiempo; si Poppins impide cumplirlas, el brief permite documentar el uso de Helvetica.

El vínculo `vale.lote_id` es insertado junto con el vale y permanece fuera del formato canónico v1 del sello para no invalidar vales históricos. El sello v1 garantiza su contenido original definido; no garantiza el vínculo administrativo de lote.
