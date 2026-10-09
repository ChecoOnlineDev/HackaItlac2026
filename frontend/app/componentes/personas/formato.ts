import { formatearFecha, formatearFechaHora, hoyMexico } from "~/componentes/dominio/formato";
export const fechaCorta = (valor: string | null | undefined): string => valor ? formatearFecha(valor) : "\u2014";
export const fechaHoraMx = (valor: string | null | undefined): string => valor ? formatearFechaHora(valor) : "\u2014";
export const hoyMx = hoyMexico;

/** "05/10/2026 al 05/10/2027". */
export function formatearPeriodo(inicio: string | null, fin: string | null): string {
  if (!inicio && !fin) return "Sin periodo";
  return `${fechaCorta(inicio)} al ${fechaCorta(fin)}`;
}
