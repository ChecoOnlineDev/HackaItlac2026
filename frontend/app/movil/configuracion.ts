/** OF-01: una construcción por servidor, sin credenciales ni rutas en la dirección. */
export function validarOrigenServidor(valor: string | undefined): string {
  if (!valor) throw new Error("Falta VITE_API_ORIGEN para construir la app de Android.");
  const url = new URL(valor);
  if (
    url.protocol !== "https:" || url.username || url.password ||
    url.pathname !== "/" || url.search || url.hash
  ) {
    throw new Error("VITE_API_ORIGEN debe ser un origen HTTPS, sin ruta ni credenciales.");
  }
  return url.origin;
}
