/** Cuerpo de error de la API: `{codigo, mensaje, detalles}`. */
export interface CuerpoError {
  codigo: string;
  mensaje: string;
  detalles: Record<string, unknown> | null;
}

/** Códigos que genera el cliente cuando no hubo respuesta del servidor. */
export const CODIGO_SIN_CONEXION = "SIN_CONEXION";
export const CODIGO_RESPUESTA_INVALIDA = "RESPUESTA_INVALIDA";

/**
 * Error de la API. `mensaje` ya está en español llano y se muestra tal cual al usuario.
 * `codigo` sirve para decidir qué hacer (por ejemplo `VALE_CAMBIO`), nunca para mostrarse.
 */
export class ErrorApi extends Error {
  readonly status: number;
  readonly codigo: string;
  readonly detalles: Record<string, unknown> | null;

  constructor(status: number, cuerpo: CuerpoError) {
    super(cuerpo.mensaje);
    this.name = "ErrorApi";
    this.status = status;
    this.codigo = cuerpo.codigo;
    this.detalles = cuerpo.detalles;
  }

  get sinConexion(): boolean {
    return this.codigo === CODIGO_SIN_CONEXION;
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
