/** Medidas de la credencial: tamaño tarjeta CR80 (ISO/IEC 7810 ID-1), en milímetros. */
export const ANCHO_MM = 85.6;
export const ALTO_MM = 54;

/**
 * Lo que lleva una credencial. NUNCA trae CURP, NSS ni otro dato reservado (RG-13): el servidor no
 * los manda en `GET /api/etiquetas` y la tarjeta no tiene dónde ponerlos.
 */
export interface DatosCredencial {
  /** Código registrado del trabajador (por ejemplo `TRB-1001`); el QR lo contiene exactamente (RG-10). */
  codigo: string;
  nombre: string;
  puesto?: string | null;
  numero_empleado: string;
}

/**
 * Tamaño del nombre en mm según su largo (Poppins es ancha) y renglones que se reservan: el nombre
 * va completo, sin cortarse; si es largo, baja el tamaño y usa tres renglones. Lo comparten la
 * pantalla y el PNG.
 */
export function ajustarNombre(nombre: string): { tamano: number; interlinea: number; lineas: number } {
  const largo = nombre.trim().length;
  if (largo <= 16) return { tamano: 4.8, interlinea: 5.6, lineas: 2 };
  if (largo <= 26) return { tamano: 4.1, interlinea: 4.8, lineas: 2 };
  return { tamano: 3.4, interlinea: 4, lineas: 3 };
}
