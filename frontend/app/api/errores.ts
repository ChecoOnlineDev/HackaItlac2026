/** Cuerpo de error de la API: `{codigo, mensaje, detalles}`. */
export interface CuerpoError {
  codigo: string;
  mensaje: string;
  detalles: Record<string, unknown> | null;
}

/** Códigos que genera el cliente cuando no hubo respuesta del servidor. */
export const CODIGO_SIN_CONEXION = "SIN_CONEXION";
export const CODIGO_RESPUESTA_INVALIDA = "RESPUESTA_INVALIDA";

export const CODIGO_CUERPO_MUY_GRANDE = "CUERPO_MUY_GRANDE";
export const CODIGO_SERVICIO_NO_DISPONIBLE = "SERVICIO_NO_DISPONIBLE";
export const CODIGO_DEMASIADOS_INTENTOS = "DEMASIADOS_INTENTOS";

function megas(bytes: unknown): string | null {
  if (typeof bytes !== "number" || bytes <= 0) return null;
  const m = bytes / (1024 * 1024);
  return m >= 10 || Number.isInteger(m) ? m.toFixed(0) : m.toFixed(1);
}

/**
 * Textos en español llano para los errores de capacidad. Valen igual si el mensaje del servidor no
 * llegó (por ejemplo, lo cortó un intermediario) y así nunca se ve texto técnico.
 */
export function mensajeLlano(status: number, codigo: string, mensaje: string, detalles: Record<string, unknown> | null): string {
  if (status === 413 || codigo === CODIGO_CUERPO_MUY_GRANDE) {
    const tope = megas(detalles?.limite_bytes);
    return `La foto o el archivo pesa demasiado. Elige uno más ligero o toma la foto otra vez.${tope ? ` Lo máximo es ${tope} MB.` : ""}`;
  }
  if (status === 503 || codigo === CODIGO_SERVICIO_NO_DISPONIBLE) {
    return "El sistema está ocupado en este momento. Espera unos segundos y vuelve a intentarlo.";
  }
  if (status === 502 || status === 504) {
    return "El sistema no respondió a tiempo. Espera unos segundos y vuelve a intentarlo.";
  }
  if (status === 429 || codigo === CODIGO_DEMASIADOS_INTENTOS) {
    const espera = detalles?.segundos_espera;
    if (typeof espera === "number" && espera > 0) {
      const minutos = Math.max(1, Math.ceil(espera / 60));
      return `Hubo demasiados intentos. Espera ${minutos} ${minutos === 1 ? "minuto" : "minutos"} para volver a intentar.`;
    }
    return mensaje || "Hubo demasiados intentos. Espera unos minutos para volver a intentar.";
  }
  return mensaje;
}

/**
 * Error de la API. `mensaje` ya está en español llano y se muestra tal cual al usuario.
 * `codigo` sirve para decidir qué hacer (por ejemplo `VALE_CAMBIO`), nunca para mostrarse.
 */
export class ErrorApi extends Error {
  readonly status: number;
  readonly codigo: string;
  readonly detalles: Record<string, unknown> | null;

  constructor(status: number, cuerpo: CuerpoError) {
    super(mensajeLlano(status, cuerpo.codigo, cuerpo.mensaje, cuerpo.detalles));
    this.name = "ErrorApi";
    this.status = status;
    this.codigo = cuerpo.codigo;
    this.detalles = cuerpo.detalles;
  }

  get sinConexion(): boolean {
    return this.codigo === CODIGO_SIN_CONEXION;
  }

  /** `true` si volver a intentar lo mismo puede funcionar: sin conexión o el sistema ocupado. */
  get reintentable(): boolean {
    return this.sinConexion || this.status === 502 || this.status === 503 || this.status === 504;
  }

  /** `true` si el archivo o la foto enviada pesa más de lo permitido (hay que elegir otro). */
  get archivoMuyPesado(): boolean {
    return this.status === 413;
  }

  get noAutenticado(): boolean {
    return this.status === 401;
  }

  get sinPermiso(): boolean {
    return this.status === 403 && this.codigo === "SIN_PERMISO";
  }

  /** Segundos de espera de un bloqueo temporal (429), o null si no aplica. */
  get segundosEspera(): number | null {
    if (this.status !== 429) return null;
    const valor = this.detalles?.segundos_espera;
    return typeof valor === "number" ? valor : null;
  }

  /** Campo del formulario al que se refiere el error (422), si el servidor lo indica. */
  get campo(): string | null {
    const valor = this.detalles?.campo;
    return typeof valor === "string" ? valor : null;
  }
}

export function esErrorApi(valor: unknown): valor is ErrorApi {
  return valor instanceof ErrorApi;
}

/** Mensaje para mostrar de cualquier error, sin términos técnicos. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.message;
  return "Algo salió mal. Inténtalo de nuevo.";
}

/** "4:59" a partir de segundos, para el bloqueo temporal. */
export function formatearEspera(segundos: number): string {
  const s = Math.max(0, Math.ceil(segundos));
  const minutos = Math.floor(s / 60);
  const resto = String(s % 60).padStart(2, "0");
  return `${minutos}:${resto}`;
}
