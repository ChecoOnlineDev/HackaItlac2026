import { hoyMexico, aFechaLocal } from "~/componentes/dominio/fechas";

/** Los instantes de algunos endpoints llegan en UTC sin la `Z`: se les agrega para no leerlos como hora local. */
export function instanteUtc(iso: string): string {
  return /(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
}

/** Días que faltan para una fecha `YYYY-MM-DD` (negativo si ya pasó), contados desde hoy en México. */
export function diasHasta(fecha: string): number {
  const a = aFechaLocal(hoyMexico());
  const b = aFechaLocal(fecha);
  return Math.round((b.getTime() - a.getTime()) / 86_400_000);
}

export function textoDias(dias: number): string {
  if (dias === 0) return "vence hoy";
  if (dias === 1) return "falta 1 día";
  if (dias > 1) return `faltan ${dias} días`;
  if (dias === -1) return "venció hace 1 día";
  return `venció hace ${-dias} días`;
}

const ESTADOS_PIEZA: Record<string, string> = {
  APTO: "Apta",
  NO_APTO: "No apta",
  EN_MANTENIMIENTO: "En mantenimiento",
  EN_CALIBRACION: "En calibración",
  BAJA: "De baja",
};

export function textoEstadoPieza(estado: string): string {
  return ESTADOS_PIEZA[estado] ?? estado;
}

/** "Quién la tiene" en una frase. */
export function textoControl(control: string): string {
  return control === "PIEZA" ? "Se controla por pieza" : "Se controla por cantidad";
}
