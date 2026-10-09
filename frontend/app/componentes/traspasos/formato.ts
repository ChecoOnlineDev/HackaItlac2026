import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { haceCuanto } from "~/componentes/dominio/formato";

/** "hace 5 minutos", "hace 3 horas", "hace 2 días" a partir de un instante ISO (UTC). */
export { haceCuanto } from "~/componentes/dominio/formato";

/** Cómo se validó un envío, en español llano: `ENVIO_PROPIO`, `REMOTA` (desde el celular del supervisor) o `PIN`. */
export function textoMedioValido(medio: string | null | undefined): string | null {
  switch (medio) {
    case "ENVIO_PROPIO":
      return "envío propio";
    case "REMOTA":
      return "desde su celular";
    case "PIN":
      return "con su PIN";
    default:
      return null;
  }
}

/** "Pedro (envío propio)": quién validó el envío y cómo. */
export function textoValido(valido: { autorizo: { nombre: string }; medio: string | null }): string {
  const medio = textoMedioValido(valido.medio);
  return medio ? `${valido.autorizo.nombre} (${medio})` : valido.autorizo.nombre;
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
