// Fechas del dominio. En la base todo va en UTC; se muestra en la hora del centro de México.

export const ZONA_MEXICO = "America/Mexico_City";
const moneda = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const entero = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 0 });
export const formatearMoneda = (valor: string | number): string => moneda.format(Number(valor));
export const formatearEntero = (valor: number): string => entero.format(valor);

const formatoFechaHora = new Intl.DateTimeFormat("es-MX", {
  timeZone: ZONA_MEXICO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** "05/10/2026 14:32" a partir de un instante ISO (UTC). */
export function formatearFechaHora(iso: string): string {
  const conZona = /(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`;
  const fecha = new Date(conZona);
  if (Number.isNaN(fecha.getTime())) return iso;
  const partes = Object.fromEntries(formatoFechaHora.formatToParts(fecha).map((p) => [p.type, p.value]));
  return `${partes.day}/${partes.month}/${partes.year} ${partes.hour}:${partes.minute}`;
}

/** "05/10/2026" a partir de una fecha `YYYY-MM-DD` (o de un instante ISO, en hora de México). */
export function formatearFecha(valor: string): string {
  const solo = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor);
  if (solo) return `${solo[3]}/${solo[2]}/${solo[1]}`;
  return formatearFechaHora(valor).slice(0, 10);
}

const formatoDia = new Intl.DateTimeFormat("en-CA", {
  timeZone: ZONA_MEXICO,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Hoy en México como `YYYY-MM-DD`, sin importar la zona del dispositivo. */
export function hoyMexico(ahora: Date = new Date()): string {
  return formatoDia.format(ahora);
}

/** Convierte `YYYY-MM-DD` en una fecha local a mediodía (para el calendario). */
export function aFechaLocal(valor: string): Date {
  const [a, m, d] = valor.split("-").map(Number);
  return new Date(a, m - 1, d, 12);
}

/** Convierte la fecha local que elige el calendario en `YYYY-MM-DD`. */
export function aTextoFecha(fecha: Date): string {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

/** Suma (o resta) días a una fecha `YYYY-MM-DD`. */
export function sumarDias(valor: string, dias: number): string {
  const f = aFechaLocal(valor);
  f.setDate(f.getDate() + dias);
  return aTextoFecha(f);
}

export function haceCuanto(iso: string, ahora: number = Date.now()): string {
  const antes = new Date(iso).getTime();
  if (Number.isNaN(antes)) return "";
  const minutos = Math.max(0, Math.floor((ahora - antes) / 60_000));
  if (minutos < 1) return "hace un momento";
  if (minutos < 60) return `hace ${minutos} ${minutos === 1 ? "minuto" : "minutos"}`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} ${horas === 1 ? "hora" : "horas"}`;
  const dias = Math.floor(horas / 24);
  return `hace ${dias} ${dias === 1 ? "día" : "días"}`;
}

