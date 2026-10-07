// Respuesta táctil al escanear en una recepción: vibración corta, sin sonido obligatorio.

/** Vibra donde el dispositivo lo permita; si no, no pasa nada. */
export function vibrar(patron: number | number[]): void {
  try {
    if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") navigator.vibrate(patron);
  } catch {
    // Sin vibración la pantalla igual muestra el resultado.
  }
}

export const vibrarOk = () => vibrar(40);
export const vibrarError = () => vibrar([90, 50, 90]);
