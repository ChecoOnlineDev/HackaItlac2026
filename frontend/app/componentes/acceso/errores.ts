import { esErrorApi } from "~/api/errores";

/**
 * Errores de un formulario de acceso, por campo. El servidor manda en 422 una lista `{campo, mensaje}`;
 * si su mensaje coincide con el del error entero, lo escribió una regla y ya viene en español llano.
 * Los avisos de forma (campo vacío, tipo incorrecto) se cambian por un texto genérico.
 */
export function erroresDeAcceso(causa: unknown): { campos: Record<string, string>; general: string | null } {
  const campos: Record<string, string> = {};
  if (!esErrorApi(causa)) return { campos, general: "Algo salió mal. Inténtalo de nuevo." };
  const detalles: unknown = causa.detalles;
  if (Array.isArray(detalles)) {
    for (const d of detalles as { campo?: string; mensaje?: string }[]) {
      if (!d.campo) continue;
      campos[d.campo] ??= d.mensaje && d.mensaje === causa.message ? d.mensaje : "Revisa este dato.";
    }
    if (Object.keys(campos).length > 0) return { campos, general: null };
  }
  return { campos, general: causa.message };
}
