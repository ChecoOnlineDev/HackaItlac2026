import { Capacitor } from "@capacitor/core";
import { validarOrigenServidor } from "./configuracion";

export const esAppNativa = () => Capacitor.isNativePlatform();

export function origenApi(): string {
  return esAppNativa() ? validarOrigenServidor(import.meta.env.VITE_API_ORIGEN) : "";
}

let version: Promise<string> | undefined;
/** OF-02: usa versionName del APK, no un dato que pueda quedar distinto en Vite. */
export async function versionApp(): Promise<string | null> {
  if (!esAppNativa()) return null;
  version ??= import("@capacitor/app").then(async ({ App }) => (await App.getInfo()).version);
  return version;
}
