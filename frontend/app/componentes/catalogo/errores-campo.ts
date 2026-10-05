import { esErrorApi } from "~/api/errores";

/**
 * Errores de un formulario por campo. El servidor manda el campo en `detalles` (un objeto o una lista);
 * lo que no se puede ligar a un campo se devuelve en `general`.
 */
export function erroresPorCampo(causa: unknown): { campos: Record<string, string>; general: string | null } {
  const campos: Record<string, string> = {};
  if (!esErrorApi(causa)) return { campos, general: "Algo salió mal. Inténtalo de nuevo." };
  const detalles: unknown = causa.detalles;
  if (Array.isArray(detalles)) {
    for (const d of detalles as { campo?: string; mensaje?: string; regla?: string }[]) {
      if (!d.campo) continue;
      // Los mensajes con regla ya vienen en español llano; los demás son avisos genéricos de forma.
      campos[d.campo] ??= d.regla && d.mensaje ? d.mensaje : "Revisa este dato.";
    }
    if (Object.keys(campos).length > 0) return { campos, general: null };
  }
  if (causa.campo) {
    campos[causa.campo] = causa.message;
    return { campos, general: null };
  }
  return { campos, general: causa.message };
}
