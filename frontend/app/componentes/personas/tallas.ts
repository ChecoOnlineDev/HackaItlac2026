/** Tallas que captura RH. La clave va al servidor; la etiqueta es lo que ve la persona. */
export const TALLAS = [
  { clave: "camisa", etiqueta: "Camisa" },
  { clave: "pantalon", etiqueta: "Pantalón" },
  { clave: "calzado", etiqueta: "Calzado" },
  { clave: "guantes", etiqueta: "Guantes" },
] as const;

export function etiquetaTalla(clave: string): string {
  return TALLAS.find((t) => t.clave === clave)?.etiqueta ?? clave.charAt(0).toUpperCase() + clave.slice(1);
}
