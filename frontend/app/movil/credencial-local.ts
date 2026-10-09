/**
 * Primitivas de la credencial local de FEAT-020.
 * Solo conserva la derivacion del PIN; nunca conserva el PIN ni lo envia al servidor.
 * La persistencia y el ciclo de vida de la credencial pertenecen a la base local cifrada.
 */

export const ITERACIONES_PIN_LOCAL = 600_000;
export const INTENTOS_PARA_BLOQUEO = 5;
export const INTENTOS_PARA_BORRADO = 10;
export const DURACION_BLOQUEO_MS = 5 * 60 * 1000;

export type DerivacionPin = {
  algoritmo: "PBKDF2-SHA256";
  iteraciones: typeof ITERACIONES_PIN_LOCAL;
  sal: string;
  verificador: string;
};

export type EstadoIntentosPin = {
  fallosConsecutivos: number;
  bloqueadaHasta: number | null;
  debeBorrarCredencial: boolean;
};

const texto = new TextEncoder();

function bytesBase64(bytes: Uint8Array): string {
  let binario = "";
  for (const byte of bytes) binario += String.fromCharCode(byte);
  return btoa(binario);
}

function base64Bytes(valor: string): Uint8Array {
  const binario = atob(valor);
  return Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0));
}

function pinEsValido(pin: string): boolean {
  return /^\d{6}$/.test(pin);
}

function pinTrivial(pin: string, hoy: Date): boolean {
  if (/^(\d)\1{5}$/.test(pin)) return true;
  if (pin === "123456" || pin === "654321") return true;

  const dia = String(hoy.getDate()).padStart(2, "0");
  const mes = String(hoy.getMonth() + 1).padStart(2, "0");
  const anio = String(hoy.getFullYear());
  const anioCorto = anio.slice(-2);
  return new Set([`${dia}${mes}${anioCorto}`, `${anioCorto}${mes}${dia}`, `${mes}${dia}${anioCorto}`]).has(pin);
}

function obtenerCrypto(cryptoApi: Crypto | undefined): Crypto {
  if (!cryptoApi?.subtle || !cryptoApi.getRandomValues) {
    throw new Error("Este equipo no permite proteger la credencial local.");
  }
  return cryptoApi;
}

async function derivar(pin: string, sal: Uint8Array, cryptoApi: Crypto): Promise<Uint8Array> {
  const clave = await cryptoApi.subtle.importKey("raw", texto.encode(pin), "PBKDF2", false, ["deriveBits"]);
  const salEstable = new Uint8Array(sal).buffer as ArrayBuffer;
  const bits = await cryptoApi.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: salEstable, iterations: ITERACIONES_PIN_LOCAL },
    clave,
    256,
  );
  return new Uint8Array(bits);
}

/** Crea el verificador local. El PIN debe venir de una entrada con señal ya autenticada. */
export async function crearDerivacionPinLocal(
  pin: string,
  opciones: { hoy?: Date; crypto?: Crypto } = {},
): Promise<DerivacionPin> {
  const hoy = opciones.hoy ?? new Date();
  if (!pinEsValido(pin)) throw new Error("El PIN local debe tener seis números.");
  if (pinTrivial(pin, hoy)) throw new Error("Elige un PIN local distinto de secuencias y fechas fáciles de adivinar.");

  const cryptoApi = obtenerCrypto(opciones.crypto ?? globalThis.crypto);
  const sal = cryptoApi.getRandomValues(new Uint8Array(16));
  const verificador = await derivar(pin, sal, cryptoApi);
  return {
    algoritmo: "PBKDF2-SHA256",
    iteraciones: ITERACIONES_PIN_LOCAL,
    sal: bytesBase64(sal),
    verificador: bytesBase64(verificador),
  };
}

/** Comprueba un PIN sin revelar ni reconstruir el PIN guardado. */
export async function verificarPinLocal(
  pin: string,
  credencial: DerivacionPin,
  crypto: Crypto | undefined = globalThis.crypto,
): Promise<boolean> {
  if (!pinEsValido(pin) || credencial.algoritmo !== "PBKDF2-SHA256" || credencial.iteraciones !== ITERACIONES_PIN_LOCAL) {
    return false;
  }

  try {
    const calculado = await derivar(pin, base64Bytes(credencial.sal), obtenerCrypto(crypto));
    const esperado = base64Bytes(credencial.verificador);
    if (calculado.length !== esperado.length) return false;
    let diferencia = 0;
    for (let i = 0; i < calculado.length; i += 1) diferencia |= calculado[i] ^ esperado[i];
    return diferencia === 0;
  } catch {
    return false;
  }
}

export function nuevoEstadoIntentosPin(): EstadoIntentosPin {
  return { fallosConsecutivos: 0, bloqueadaHasta: null, debeBorrarCredencial: false };
}

/** Registra un intento fallido; quien persiste este estado debe usar la base local cifrada. */
export function registrarFalloPinLocal(
  estado: EstadoIntentosPin,
  ahora = Date.now(),
): EstadoIntentosPin {
  if (estado.debeBorrarCredencial) return estado;
  if (estado.bloqueadaHasta !== null && ahora < estado.bloqueadaHasta) return estado;

  const fallosConsecutivos = estado.fallosConsecutivos + 1;
  if (fallosConsecutivos >= INTENTOS_PARA_BORRADO) {
    return { fallosConsecutivos, bloqueadaHasta: null, debeBorrarCredencial: true };
  }
  if (fallosConsecutivos % INTENTOS_PARA_BLOQUEO === 0) {
    return { fallosConsecutivos, bloqueadaHasta: ahora + DURACION_BLOQUEO_MS, debeBorrarCredencial: false };
  }
  return { fallosConsecutivos, bloqueadaHasta: null, debeBorrarCredencial: false };
}

export function registrarAciertoPinLocal(): EstadoIntentosPin {
  return nuevoEstadoIntentosPin();
}

export function pinLocalEstaBloqueado(estado: EstadoIntentosPin, ahora = Date.now()): boolean {
  return estado.debeBorrarCredencial || (estado.bloqueadaHasta !== null && ahora < estado.bloqueadaHasta);
}
