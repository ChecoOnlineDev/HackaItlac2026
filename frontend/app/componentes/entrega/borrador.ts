// Borrador de un vale en captura. Vive en el dispositivo (localStorage) hasta que el servidor
// confirma el vale: sobrevive a una recarga o a un corte de red y nada se da por guardado antes
// de la respuesta del servidor (E-28, ES-10). Otras pantallas de captura (devolver, trasladar)
// pueden reutilizar `RenglonBorrador`, `nuevoIdCliente`, `leerBorrador` y `guardarBorrador`.

import type { FichaTrabajadorApi, FirmaCapturada, ValeConfirmadoApi } from "./tipos";

/** Un renglón capturado: solo el código, la cantidad y, si se pidió, la observación. */
export interface RenglonBorrador {
  codigo: string;
  cantidad: number;
  observacion?: string;
}

/** La autorización que se pidió para este borrador (A-01 a A-07). */
export interface AutorizacionBorrador {
  id: string;
  estado: "PENDIENTE" | "APROBADA" | "RECHAZADA" | "VENCIDA" | "USADA";
  /** Códigos de los renglones que se pidió autorizar. */
  codigos: string[];
  vence_en: string;
  /** Quién resolvió, si ya se resolvió. */
  resuelta_por?: string | null;
}

export type PasoEntrega = "trabajador" | "articulos" | "firma" | "resultado";

export interface BorradorEntrega {
  version: 1;
  /** Un borrador es de un usuario; otro usuario nunca lo ve. */
  usuarioId: string;
  /** Se fija al empezar y se manda igual al evaluar y al confirmar: un doble toque nunca crea dos vales. */
  idCliente: string;
  paso: PasoEntrega;
  /** Almacén en el que se capturó (AC-13). */
  almacenId: string | null;
  trabajador: FichaTrabajadorApi | null;
  renglones: RenglonBorrador[];
  /** Cantidad ya confirmada por la persona en un renglón con cantidad inusual (E-27), por código. */
  cantidadesConfirmadas: Record<string, number>;
  autorizacion: AutorizacionBorrador | null;
  firma: FirmaCapturada | null;
  /** Solo en el paso `resultado`: el vale que ya emitió el servidor. */
  resultado: ValeConfirmadoApi | null;
  actualizadoEn: number;
}

const CLAVE = "imhotep.borrador.entrega.v1";

export function nuevoBorradorEntrega(usuarioId: string, almacenId: string | null): BorradorEntrega {
  return {
    version: 1,
    usuarioId,
    idCliente: nuevoIdCliente(),
    paso: "trabajador",
    almacenId,
    trabajador: null,
    renglones: [],
    cantidadesConfirmadas: {},
    autorizacion: null,
    firma: null,
    resultado: null,
    actualizadoEn: Date.now(),
  };
}

/** UUID para `id_cliente`. `crypto.randomUUID` solo existe en contextos seguros; hay un respaldo. */
export function nuevoIdCliente(): string {
  const c = typeof crypto === "undefined" ? undefined : crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  const bytes = new Uint8Array(16);
  if (c?.getRandomValues) c.getRandomValues(bytes);
  else for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Clave de comparación de un código: sin espacios y sin distinguir mayúsculas. */
export function claveDeCodigo(codigo: string): string {
  return codigo.trim().toLocaleUpperCase("es-MX");
}

/** El borrador guardado de este usuario, o null (nada guardado, otro usuario o datos dañados). */
export function leerBorrador(usuarioId: string): BorradorEntrega | null {
  try {
    const texto = window.localStorage.getItem(CLAVE);
    if (!texto) return null;
    const dato = JSON.parse(texto) as Partial<BorradorEntrega> | null;
    if (!dato || dato.version !== 1 || dato.usuarioId !== usuarioId) return null;
    if (typeof dato.idCliente !== "string" || !Array.isArray(dato.renglones)) return null;
    // Un vale ya emitido no se retoma: la pantalla vuelve a empezar de cero.
    if (dato.paso === "resultado" || dato.resultado) return null;
    return dato as BorradorEntrega;
  } catch {
    return null;
  }
}

/** Guarda el borrador. Devuelve `false` si el dispositivo no deja guardar (la captura sigue en pantalla). */
export function guardarBorrador(borrador: BorradorEntrega): boolean {
  if (borrador.paso === "resultado") {
    borrarBorrador();
    return true;
  }
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify({ ...borrador, actualizadoEn: Date.now() }));
    return true;
  } catch {
    return false;
  }
}

export function borrarBorrador(): void {
  try {
    window.localStorage.removeItem(CLAVE);
  } catch {
    // Sin almacenamiento no hay nada que borrar.
  }
}

/** ¿Hay algo capturado que se perdería al salir? (trabajador identificado o renglones). */
export function tieneCaptura(borrador: BorradorEntrega | null): boolean {
  if (!borrador || borrador.paso === "resultado") return false;
  return borrador.renglones.length > 0;
}
