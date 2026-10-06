import {
  CODIGO_RESPUESTA_INVALIDA,
  CODIGO_SIN_CONEXION,
  ErrorApi,
  type CuerpoError,
} from "./errores";
import { marcarConexion } from "./red";
import type { Sesion } from "./tipos";

export const BASE_API = "/api";

type Parametros = Record<string, string | number | boolean | null | undefined>;

export interface OpcionesApi {
  /** Método HTTP. Por omisión GET. */
  metodo?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  /** Cuerpo JSON, o FormData para subir archivos. */
  cuerpo?: unknown;
  /** Parámetros de consulta; los nulos y vacíos se omiten. */
  parametros?: Parametros;
  signal?: AbortSignal;
  /** No tratar el 401 como sesión vencida (lo usa la pantalla Entrar y el arranque). */
  sinRedirigir?: boolean;
  /** No intentar renovar la sesión ante un 401 (el inicio de sesión y la propia renovación). */
  sinRenovar?: boolean;
}

type ManejadorSesionVencida = () => void;
type ManejadorSesionRenovada = (sesion: Sesion) => void;
let alVencerSesion: ManejadorSesionVencida | null = null;
let alRenovarSesion: ManejadorSesionRenovada | null = null;

/** La sesión (SesionProvider) registra aquí qué hacer cuando la sesión venció del todo. */
export function registrarManejadorSesionVencida(fn: ManejadorSesionVencida | null) {
  alVencerSesion = fn;
}

/** Y aquí qué hacer cuando se renovó sola (llegan los permisos al día). */
export function registrarManejadorSesionRenovada(fn: ManejadorSesionRenovada | null) {
  alRenovarSesion = fn;
}

/** Código con el que el servidor dice que ya no hay forma de renovar: hay que volver a entrar. */
export const CODIGO_SESION_VENCIDA = "SESION_VENCIDA";

type ResultadoRenovacion = { tipo: "renovada" } | { tipo: "vencida" } | { tipo: "fallo"; error: ErrorApi };

/** La renovación en curso: las peticiones que fallan a la vez comparten UNA sola (single-flight). */
let renovacionEnCurso: Promise<ResultadoRenovacion> | null = null;
/** Cuándo terminó la última renovación buena (ms). Una petición que salió antes no vuelve a renovar. */
let ultimaRenovacionOk = 0;

async function renovarUnaVez(): Promise<ResultadoRenovacion> {
  try {
    const sesion = await api<Sesion>("/sesion/refresh", {
      metodo: "POST",
      sinRedirigir: true,
      sinRenovar: true,
    });
    ultimaRenovacionOk = Date.now();
    alRenovarSesion?.(sesion);
    return { tipo: "renovada" };
  } catch (causa) {
    // 401: ya no hay renovación posible. Sin conexión o error del servidor: no se sabe, y no se
    // cierra la sesión por eso (se vuelve a intentar con la siguiente petición).
    if (causa instanceof ErrorApi && causa.status === 401) return { tipo: "vencida" };
    if (causa instanceof ErrorApi) return { tipo: "fallo", error: causa };
    throw causa;
  }
}

function renovarSesion(): Promise<ResultadoRenovacion> {
  if (!renovacionEnCurso) {
    renovacionEnCurso = renovarUnaVez().finally(() => {
      renovacionEnCurso = null;
    });
  }
  return renovacionEnCurso;
}

export function construirUrl(ruta: string, parametros?: Parametros): string {
  const url = ruta.startsWith("/api") ? ruta : `${BASE_API}${ruta.startsWith("/") ? "" : "/"}${ruta}`;
  if (!parametros) return url;
  const consulta = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor === null || valor === undefined || valor === "") continue;
    consulta.set(clave, String(valor));
  }
  const texto = consulta.toString();
  return texto ? `${url}?${texto}` : url;
}

async function pedir(ruta: string, opciones: OpcionesApi, yaRenovo = false): Promise<Response> {
  const { metodo = "GET", cuerpo, parametros, signal } = opciones;
  const salio = Date.now();
  const encabezados: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (cuerpo instanceof FormData) {
    body = cuerpo;
  } else if (cuerpo !== undefined) {
    encabezados["Content-Type"] = "application/json";
    body = JSON.stringify(cuerpo);
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta, parametros), {
      method: metodo,
      credentials: "include",
      headers: encabezados,
      body,
      signal,
    });
  } catch (causa) {
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    marcarConexion(false);
    throw new ErrorApi(0, {
      codigo: CODIGO_SIN_CONEXION,
      mensaje: "Sin conexión",
      detalles: null,
    });
  }
  marcarConexion(true);

  if (!respuesta.ok) {
    const error = await leerError(respuesta);
    if (respuesta.status === 401) {
      // El token de acceso dura poco: ante un 401 se intenta UNA renovación y se repite la
      // petición. Si tampoco así, la sesión venció y se pide la contraseña.
      if (!opciones.sinRenovar && !yaRenovo && error.codigo !== CODIGO_SESION_VENCIDA) {
        if (salio > ultimaRenovacionOk) {
          const resultado = await renovarSesion();
          if (resultado.tipo === "fallo") throw resultado.error;
          if (resultado.tipo === "renovada") return pedir(ruta, opciones, true);
        } else {
          // Salió antes de que se renovara la sesión: basta con repetirla con el token nuevo.
          return pedir(ruta, opciones, true);
        }
      }
      if (!opciones.sinRedirigir) alVencerSesion?.();
    }
    throw error;
  }
  return respuesta;
}

async function leerError(respuesta: Response): Promise<ErrorApi> {
  let cuerpo: CuerpoError | null = null;
  try {
    const datos = (await respuesta.json()) as Partial<CuerpoError>;
    if (datos && typeof datos.mensaje === "string") {
      cuerpo = {
        codigo: datos.codigo ?? "ERROR",
        mensaje: datos.mensaje,
        detalles: datos.detalles ?? null,
      };
    }
  } catch {
    // El cuerpo no era JSON: se usa un mensaje genérico.
  }
  return new ErrorApi(
    respuesta.status,
    cuerpo ?? {
      codigo: CODIGO_RESPUESTA_INVALIDA,
      mensaje: "No pudimos completar la operación. Inténtalo de nuevo.",
      detalles: null,
    },
  );
}

/**
 * Llama a la API y devuelve el JSON. Lanza `ErrorApi` si falla.
 * Ejemplo: `const sesion = await api<Sesion>("/sesion")`.
 */
export async function api<T = unknown>(ruta: string, opciones: OpcionesApi = {}): Promise<T> {
  const respuesta = await pedir(ruta, opciones);
  if (respuesta.status === 204) return undefined as T;
  try {
    return (await respuesta.json()) as T;
  } catch {
    throw new ErrorApi(respuesta.status, {
      codigo: CODIGO_RESPUESTA_INVALIDA,
      mensaje: "No pudimos leer la respuesta. Inténtalo de nuevo.",
      detalles: null,
    });
  }
}

/** Atajos. */
export const apiGet = <T>(ruta: string, parametros?: Parametros, signal?: AbortSignal) =>
  api<T>(ruta, { parametros, signal });
export const apiPost = <T>(ruta: string, cuerpo?: unknown, signal?: AbortSignal) =>
  api<T>(ruta, { metodo: "POST", cuerpo, signal });
export const apiPatch = <T>(ruta: string, cuerpo?: unknown) =>
  api<T>(ruta, { metodo: "PATCH", cuerpo });
export const apiDelete = <T>(ruta: string) => api<T>(ruta, { metodo: "DELETE" });

/**
 * Descarga un archivo que entrega la API (un CSV, una plantilla de Excel…).
 * Ejemplo: `await descargarArchivo("/importacion/plantilla", { modo: "ALTA" }, "plantilla.xlsx")`.
 */
export async function descargarArchivo(
  ruta: string,
  parametros?: Parametros,
  nombreSugerido = "archivo",
): Promise<void> {
  const respuesta = await pedir(ruta, { parametros });
  const blob = await respuesta.blob();
  const disposicion = respuesta.headers.get("Content-Disposition") ?? "";
  const coincide = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposicion);
  const nombre = coincide ? decodeURIComponent(coincide[1]) : nombreSugerido;
  const enlace = document.createElement("a");
  const url = URL.createObjectURL(blob);
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

/**
 * Descarga un CSV que entrega la API.
 * Ejemplo: `await descargarCsv("/reportes/existencias", { almacen_id }, "existencias.csv")`.
 */
export function descargarCsv(ruta: string, parametros?: Parametros, nombreSugerido = "reporte.csv"): Promise<void> {
  return descargarArchivo(ruta, { ...parametros, formato: "csv" }, nombreSugerido);
}
