import { formatearFechaHora } from "~/componentes/dominio/fechas";

/** "hace 5 minutos", "hace 3 horas", "hace 2 días" a partir de un instante ISO (UTC). */
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

/** "enviado hace 3 horas (05/10/2026 14:32)". */
export function desdeCuando(iso: string): string {
  return `${haceCuanto(iso)} (${formatearFechaHora(iso)})`;
}

/** El token de un vale a partir de lo que lee el escáner: la dirección del QR (`…/v/<token>`). */
export function tokenDeLectura(lectura: string): string | null {
  const texto = lectura.trim();
  const direccion = /\/v\/([A-Za-z0-9_-]{16,})\/?(?:[?#].*)?$/.exec(texto);
  if (direccion) return direccion[1];
  // Un token escrito a mano, sin la dirección.
  return /^[A-Za-z0-9_-]{22}$/.test(texto) ? texto : null;
}

/** "3 renglones" / "1 renglón". */
export function textoRenglones(n: number): string {
  return `${n} ${n === 1 ? "renglón" : "renglones"}`;
}
