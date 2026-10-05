/** "2026-10-05" -> "05/10/2026" (sin pasar por zonas horarias). */
export function fechaCorta(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [a, m, d] = valor.slice(0, 10).split("-");
  return a && m && d ? `${d}/${m}/${a}` : valor;
}

/** Fecha y hora UTC del servidor, mostrada en la hora del centro de México. */
export function fechaHoraMx(valor: string | null | undefined): string {
  if (!valor) return "—";
  const conZona = /(Z|[+-]\d\d:?\d\d)$/.test(valor) ? valor : `${valor}Z`;
  const fecha = new Date(conZona);
  if (Number.isNaN(fecha.getTime())) return valor;
  return new Intl.DateTimeFormat("es-MX", {
    timeZone: "America/Mexico_City",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(fecha);
}

/** Hoy en la hora del centro de México, como "AAAA-MM-DD". */
export function hoyMx(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City" }).format(new Date());
}

/** "05/10/2026 al 05/10/2027". */
export function formatearPeriodo(inicio: string | null, fin: string | null): string {
  if (!inicio && !fin) return "Sin periodo";
  return `${fechaCorta(inicio)} al ${fechaCorta(fin)}`;
}
