// Utilidades propias del traspaso por lista. La lectura del texto pegado y la propuesta de columnas son las de
// la importación (se importan sin modificarlas); aquí solo se adaptan a las cuatro columnas del traspaso.

import { COLUMNAS_TRASPASO_VACIAS, MAX_RENGLONES_TRASPASO, type ColumnasTraspaso } from "~/api/traspasos-lista";
import { MAX_BYTES_ARCHIVO, proponerColumnas } from "~/componentes/importacion/tabla";
import type { Tabla } from "~/componentes/importacion/tipos";

export { MAX_BYTES_ARCHIVO };

export const CAMPOS_TRASPASO = ["codigo", "cantidad", "codigo_pieza", "serie"] as const;
export type CampoTraspaso = (typeof CAMPOS_TRASPASO)[number];

export const ETIQUETA_TRASPASO: Record<CampoTraspaso, string> = {
  codigo: "Código del artículo",
  cantidad: "Cantidad",
  codigo_pieza: "Código de la pieza",
  serie: "Número de serie",
};

export const AYUDA_TRASPASO: Record<CampoTraspaso, string> = {
  codigo: "Con él se reconoce el artículo. Solo salen artículos que ya existen.",
  cantidad: "Cuántas unidades salen. Solo números enteros.",
  codigo_pieza: "Solo para artículos por pieza: el código de cada pieza.",
  serie: "Solo para artículos por pieza; ayuda a identificarla.",
};

/** Propone las columnas con las mismas palabras de la importación y se queda con las cuatro del traspaso. */
export function proponerColumnasTraspaso(encabezados: string[]): ColumnasTraspaso {
  const c = proponerColumnas(encabezados);
  return { codigo: c.codigo, cantidad: c.cantidad, codigo_pieza: c.codigo_pieza, serie: c.serie };
}

export function columnasDelServidor(c: Partial<ColumnasTraspaso> | undefined): ColumnasTraspaso {
  return { ...COLUMNAS_TRASPASO_VACIAS, ...(c ?? {}) };
}

/** Revisa el tope propio de 500 filas antes de molestar al servidor; devuelve el motivo o `null`. */
export function motivoDeTopeTabla(tabla: Tabla): string | null {
  const filas = tabla.filas.filter((f) => f.some((c) => c.trim() !== "")).length;
  if (filas > MAX_RENGLONES_TRASPASO) {
    return `La lista tiene ${filas.toLocaleString("es-MX")} filas y un traspaso lleva como máximo ${MAX_RENGLONES_TRASPASO}. Divídela en varios archivos y sube uno por traspaso.`;
  }
  return null;
}

/** Las filas del archivo en lenguaje llano: «4, 9 y 17». */
export function listaDeFilas(filas: number[]): string {
  const ordenadas = [...filas].sort((a, b) => a - b).map(String);
  if (ordenadas.length <= 1) return ordenadas.join("");
  return `${ordenadas.slice(0, -1).join(", ")} y ${ordenadas[ordenadas.length - 1]}`;
}
