// Borradores de Trasladar y de Recibir. Viven en el dispositivo (localStorage, claves propias) hasta que el
// servidor confirma: sobreviven a una recarga o a un corte de red y nada se da por guardado antes de la
// respuesta del servidor (E-28, ES-10). Comparten helpers con el borrador de la entrega.

import { nuevoIdCliente, type RenglonBorrador } from "~/componentes/entrega/borrador";
import type { ValeConfirmadoApi } from "~/componentes/entrega/tipos";

export { claveDeCodigo, nuevoIdCliente } from "~/componentes/entrega/borrador";

function leer<T>(clave: string): T | null {
  try {
    const texto = window.localStorage.getItem(clave);
    return texto ? (JSON.parse(texto) as T) : null;
  } catch {
    return null;
  }
}
function guardar(clave: string, valor: unknown): boolean {
  try {
    window.localStorage.setItem(clave, JSON.stringify(valor));
    return true;
  } catch {
    return false;
  }
}
function borrar(clave: string) {
  try {
    window.localStorage.removeItem(clave);
  } catch {
    // Sin almacenamiento no hay nada que borrar.
  }
}

// ------------------------------------------------------------------------------ trasladar

const CLAVE_TRASLADO = "imhotep.borrador.traspaso.v1";

export interface BorradorTraslado {
  version: 1;
  /** Un borrador es de un usuario; otro usuario nunca lo ve. */
  usuarioId: string;
  /** Se manda igual al evaluar y al confirmar: un doble toque nunca crea dos traspasos. */
  idCliente: string;
  almacenId: string | null;
  destinoId: string | null;
  /** Nombre del destino, para el resultado. */
  destinoNombre: string | null;
  renglones: RenglonBorrador[];
  /** El traspaso que ya emitió el servidor; con él, la pantalla muestra el resultado. */
  resultado: ValeConfirmadoApi | null;
  actualizadoEn: number;
}

export function nuevoBorradorTraslado(usuarioId: string, almacenId: string | null): BorradorTraslado {
  return {
    version: 1,
    usuarioId,
    idCliente: nuevoIdCliente(),
    almacenId,
    destinoId: null,
    destinoNombre: null,
    renglones: [],
    resultado: null,
    actualizadoEn: Date.now(),
  };
}

export function leerBorradorTraslado(usuarioId: string): BorradorTraslado | null {
  const dato = leer<Partial<BorradorTraslado>>(CLAVE_TRASLADO);
  if (!dato || dato.version !== 1 || dato.usuarioId !== usuarioId) return null;
  if (typeof dato.idCliente !== "string" || !Array.isArray(dato.renglones)) return null;
  if (dato.resultado) return null; // un traspaso ya emitido no se retoma
  return dato as BorradorTraslado;
}
export const guardarBorradorTraslado = (b: BorradorTraslado) => {
  if (b.resultado) {
    borrar(CLAVE_TRASLADO);
    return true;
  }
  return guardar(CLAVE_TRASLADO, { ...b, actualizadoEn: Date.now() });
};
export const borrarBorradorTraslado = () => borrar(CLAVE_TRASLADO);

// ------------------------------------------------------------------------------- recibir

const CLAVE_RECEPCION = "imhotep.borrador.recepcion.v1";

export interface BorradorRecepcion {
  version: 1;
  usuarioId: string;
  /** El traspaso que se está recibiendo. */
  traspasoId: string;
  /** Una recepción nueva cada vez: se renueva al confirmar para poder recibir lo que falte después. */
  idCliente: string;
  /** Lo marcado como recibido ahora, por código: cuántas piezas o unidades. */
  marcas: Record<string, number>;
  /** Códigos leídos que no están en el traspaso: el servidor dice por qué no (X-12). */
  extras: string[];
  actualizadoEn: number;
}

export function nuevoBorradorRecepcion(usuarioId: string, traspasoId: string): BorradorRecepcion {
  return { version: 1, usuarioId, traspasoId, idCliente: nuevoIdCliente(), marcas: {}, extras: [], actualizadoEn: Date.now() };
}

/** El borrador guardado de este usuario para este traspaso, o null. */
export function leerBorradorRecepcion(usuarioId: string, traspasoId: string): BorradorRecepcion | null {
  const dato = leer<Partial<BorradorRecepcion>>(CLAVE_RECEPCION);
  if (!dato || dato.version !== 1 || dato.usuarioId !== usuarioId || dato.traspasoId !== traspasoId) return null;
  if (typeof dato.idCliente !== "string" || typeof dato.marcas !== "object" || !Array.isArray(dato.extras)) return null;
  return dato as BorradorRecepcion;
}
export const guardarBorradorRecepcion = (b: BorradorRecepcion) => guardar(CLAVE_RECEPCION, { ...b, actualizadoEn: Date.now() });
export const borrarBorradorRecepcion = () => borrar(CLAVE_RECEPCION);
