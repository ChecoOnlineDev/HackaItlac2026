// Borrador de una devolución en captura. Vive en el dispositivo (localStorage) con su PROPIA clave,
// distinta de la de la entrega: sobrevive a una recarga o a un corte de red y nada se da por guardado
// antes de la respuesta del servidor (E-28, ES-10). Reutiliza `nuevoIdCliente` del borrador de la entrega.

import type { Condicion } from "~/componentes/dominio/tipos";
import { nuevoIdCliente } from "~/componentes/entrega/borrador";
import type { ValeConfirmadoApi } from "~/componentes/entrega/tipos";

/** Lo que hace falta del trabajador identificado; su resguardo se pide al servidor cada vez. */
export interface TrabajadorDevolucion {
  id: string;
  numero_empleado: string;
  nombre: string;
  puesto: string | null;
  area_obra: string | null;
}

export interface RenglonDevolucionBorrador {
  /** Identificador local del renglón (no es del servidor). */
  uid: string;
  codigo: string;
  cantidad: number;
  /** Se elige siempre (V-04); al escanear una pieza queda en `null` hasta que la persona la toque. */
  condicion: Condicion | null;
  /** Obligatoria si es Dañado (V-05). */
  observacion?: string;
  /** Foto del daño como `data:image/jpeg;base64,…`, reducida en el navegador. */
  foto?: string;
}

export interface BorradorDevolucion {
  version: 1;
  /** Un borrador es de un usuario; otro usuario nunca lo ve. */
  usuarioId: string;
  /** Se fija al empezar y se manda igual al evaluar y al confirmar: un doble toque nunca crea dos vales. */
  idCliente: string;
  almacenId: string | null;
  /** Solo hace falta para lo que se devuelve por cantidad; una pieza se abona a su titular. */
  trabajador: TrabajadorDevolucion | null;
  renglones: RenglonDevolucionBorrador[];
  /** Solo después de confirmar: el vale que ya emitió el servidor. */
  resultado: ValeConfirmadoApi | null;
  actualizadoEn: number;
}

const CLAVE = "imhotep.borrador.devolucion.v1";

export function nuevoBorradorDevolucion(usuarioId: string, almacenId: string | null): BorradorDevolucion {
  return {
    version: 1,
    usuarioId,
    idCliente: nuevoIdCliente(),
    almacenId,
    trabajador: null,
    renglones: [],
    resultado: null,
    actualizadoEn: Date.now(),
  };
}

export function nuevoRenglonDevolucion(
  codigo: string,
  cantidad = 1,
  condicion: Condicion | null = null,
): RenglonDevolucionBorrador {
  return { uid: nuevoIdCliente(), codigo, cantidad, condicion };
}

export function leerBorradorDevolucion(usuarioId: string): BorradorDevolucion | null {
  try {
    const texto = window.localStorage.getItem(CLAVE);
    if (!texto) return null;
    const dato = JSON.parse(texto) as Partial<BorradorDevolucion> | null;
    if (!dato || dato.version !== 1 || dato.usuarioId !== usuarioId) return null;
    if (typeof dato.idCliente !== "string" || !Array.isArray(dato.renglones)) return null;
    return dato as BorradorDevolucion;
  } catch {
    return null;
  }
}

/** Guarda el borrador. Devuelve `false` si el dispositivo no deja guardar todo (la captura sigue en pantalla). */
export function guardarBorradorDevolucion(borrador: BorradorDevolucion): boolean {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify({ ...borrador, actualizadoEn: Date.now() }));
    return true;
  } catch {
    // Puede faltar espacio por las fotos: se intenta de nuevo sin ellas para no perder lo demás.
    try {
      const sinFotos = { ...borrador, renglones: borrador.renglones.map((r) => ({ ...r, foto: undefined })) };
      window.localStorage.setItem(CLAVE, JSON.stringify({ ...sinFotos, actualizadoEn: Date.now() }));
    } catch {
      // Sin almacenamiento, la captura sigue en pantalla.
    }
    return false;
  }
}

export function borrarBorradorDevolucion(): void {
  try {
    window.localStorage.removeItem(CLAVE);
  } catch {
    // Sin almacenamiento no hay nada que borrar.
  }
}

/** ¿Hay algo capturado que se perdería al salir? */
export function tieneCapturaDevolucion(borrador: BorradorDevolucion | null): boolean {
  if (!borrador || borrador.resultado) return false;
  return borrador.renglones.length > 0;
}
