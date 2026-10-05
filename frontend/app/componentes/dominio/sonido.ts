// Respuesta inmediata de cada lectura: un sonido distinto para correcta, aviso y bloqueo, y vibración
// donde exista. Los sonidos se generan con Web Audio (sin archivos). La pantalla de operación llama a
// `reproducir` con el resultado que da el servidor.

export type TipoSonido = "ok" | "aviso" | "bloqueo";

interface Nota {
  /** Frecuencia en Hz. */
  f: number;
  /** Segundos desde el inicio. */
  inicio: number;
  duracion: number;
  onda: OscillatorType;
}

const NOTAS: Record<TipoSonido, Nota[]> = {
  // Un pitido agudo y corto.
  ok: [{ f: 988, inicio: 0, duracion: 0.09, onda: "sine" }],
  // Dos pitidos medios.
  aviso: [
    { f: 587, inicio: 0, duracion: 0.1, onda: "triangle" },
    { f: 587, inicio: 0.16, duracion: 0.1, onda: "triangle" },
  ],
  // Un zumbido grave y largo.
  bloqueo: [{ f: 196, inicio: 0, duracion: 0.38, onda: "sawtooth" }],
};

const VIBRACION: Record<TipoSonido, number | number[]> = {
  ok: 40,
  aviso: [60, 60, 60],
  bloqueo: 250,
};

let contexto: AudioContext | null = null;
let silenciado = false;

function obtenerContexto(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (contexto) return contexto;
  const Constructor =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Constructor) return null;
  try {
    contexto = new Constructor();
  } catch {
    contexto = null;
  }
  return contexto;
}

/**
 * Los navegadores solo dejan sonar tras un gesto del usuario. Llamarla en el primer toque o tecla
 * deja el audio listo para las lecturas de la pistola, que no tocan la pantalla.
 */
export function prepararSonido(): void {
  const ctx = obtenerContexto();
  if (ctx && ctx.state === "suspended") void ctx.resume().catch(() => {});
}

/** Apaga o enciende el sonido (la vibración sigue). */
export function silenciarSonido(valor: boolean): void {
  silenciado = valor;
}

/**
 * Suena y vibra según el resultado: `ok` (correcto), `aviso` (amarillo, lectura repetida) o
 * `bloqueo` (rojo, no se puede). Nunca lanza error: si el navegador no puede, no pasa nada.
 */
export function reproducir(tipo: TipoSonido): void {
  try {
    // Los navegadores bloquean la vibración (y avisan en la consola) antes del primer toque.
    const huboToque = typeof navigator !== "undefined" && (navigator.userActivation?.hasBeenActive ?? true);
    if (huboToque && typeof navigator.vibrate === "function") {
      navigator.vibrate(VIBRACION[tipo]);
    }
  } catch {
    // Sin vibración en este dispositivo.
  }
  if (silenciado) return;
  const ctx = obtenerContexto();
  if (!ctx) return;
  try {
    if (ctx.state === "suspended") void ctx.resume().catch(() => {});
    const base = ctx.currentTime;
    for (const nota of NOTAS[tipo]) {
      const oscilador = ctx.createOscillator();
      const ganancia = ctx.createGain();
      oscilador.type = nota.onda;
      oscilador.frequency.value = nota.f;
      const t0 = base + nota.inicio;
      // Entrada y salida suaves para que no truene.
      ganancia.gain.setValueAtTime(0.0001, t0);
      ganancia.gain.exponentialRampToValueAtTime(0.25, t0 + 0.01);
      ganancia.gain.exponentialRampToValueAtTime(0.0001, t0 + nota.duracion);
      oscilador.connect(ganancia).connect(ctx.destination);
      oscilador.start(t0);
      oscilador.stop(t0 + nota.duracion + 0.02);
    }
  } catch {
    // Sin audio en este navegador.
  }
}
