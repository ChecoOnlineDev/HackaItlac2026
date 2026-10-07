import { hoyMexico, sumarDias } from "~/componentes/dominio/fechas";

export type ClavePeriodo = "hoy" | "siete" | "mes" | "pasado" | "fechas";

export const ATAJOS_PERIODO: { clave: ClavePeriodo; texto: string }[] = [
  { clave: "hoy", texto: "Hoy" },
  { clave: "siete", texto: "7 días" },
  { clave: "mes", texto: "Este mes" },
  { clave: "pasado", texto: "Mes pasado" },
  { clave: "fechas", texto: "Elegir fechas" },
];

export interface Periodo {
  clave: ClavePeriodo;
  desde: string;
  hasta: string;
}

/** Fechas `YYYY-MM-DD` de un atajo, con el día de hoy en México. «fechas» conserva las que ya había. */
export function rangoDePeriodo(clave: Exclude<ClavePeriodo, "fechas">, hoy: string = hoyMexico()): { desde: string; hasta: string } {
  switch (clave) {
    case "hoy":
      return { desde: hoy, hasta: hoy };
    case "siete":
      return { desde: sumarDias(hoy, -6), hasta: hoy };
    case "mes":
      return { desde: `${hoy.slice(0, 8)}01`, hasta: hoy };
    case "pasado": {
      const ultimo = sumarDias(`${hoy.slice(0, 8)}01`, -1);
      return { desde: `${ultimo.slice(0, 8)}01`, hasta: ultimo };
    }
  }
}

export function periodoPorOmision(): Periodo {
  return { clave: "mes", ...rangoDePeriodo("mes") };
}

export function esPeriodoPorOmision(p: Periodo): boolean {
  const base = periodoPorOmision();
  return p.clave === "mes" && p.desde === base.desde && p.hasta === base.hasta;
}
