export type FormatoEtiqueta = 9 | 18 | 30;
export interface MedidasEtiqueta { columnas: number; filas: number; ancho: number; alto: number; qr: number; margenX: number; margenY: number; separacion: number; nombrePt: number; codigoPt: number; lineas: number }
export const CARTA = { ancho: 215.9, alto: 279.4 };
export const FORMATOS_ETIQUETA: Record<FormatoEtiqueta, MedidasEtiqueta> = {
  9: { columnas: 3, filas: 3, ancho: 65, alto: 86, qr: 45, margenX: 10.45, margenY: 10.7, separacion: 0, nombrePt: 12, codigoPt: 12, lineas: 2 },
  18: { columnas: 3, filas: 6, ancho: 65, alto: 42, qr: 30, margenX: 10.45, margenY: 13.7, separacion: 0, nombrePt: 10, codigoPt: 10, lineas: 3 },
  30: { columnas: 3, filas: 10, ancho: 66.7, alto: 25.4, qr: 21, margenX: 4.65, margenY: 12.7, separacion: 3.2, nombrePt: 8, codigoPt: 9, lineas: 2 },
};

export function posicionEtiqueta(indice: number, formato: FormatoEtiqueta) {
  const m = FORMATOS_ETIQUETA[formato];
  return { x: m.margenX + (indice % m.columnas) * (m.ancho + m.separacion), y: m.margenY + Math.floor(indice / m.columnas) * m.alto };
}

export function hojasEtiquetas(cantidad: number, porHoja: number, inicio: number): number {
  return Math.max(1, Math.ceil((cantidad + inicio - 1) / porHoja));
}
