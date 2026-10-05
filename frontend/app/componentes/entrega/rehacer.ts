// "Cancelar y rehacer" (K-05): el servidor devuelve un `borrador` con los renglones del vale cancelado,
// sin firma ni autorización. Aquí se carga como un borrador NUEVO (con `id_cliente` nuevo) en el flujo de su
// tipo, para corregirlo, volver a firmar y confirmar. Solo la entrega y la devolución tienen pantalla de
// captura de este tipo; con los demás tipos solo se cancela.

import { apiGet } from "~/api/cliente";
import {
  guardarBorradorDevolucion,
  leerBorradorDevolucion,
  nuevoBorradorDevolucion,
  nuevoRenglonDevolucion,
  tieneCapturaDevolucion,
  type TrabajadorDevolucion,
} from "~/componentes/devolucion/borrador";
import type { Condicion } from "~/componentes/dominio/tipos";
import type { TipoVale } from "~/componentes/dominio/vale-imprimible";
import { guardarBorrador, leerBorrador, nuevoBorradorEntrega, tieneCaptura } from "./borrador";
import type { FichaTrabajadorApi, ValeConfirmadoApi } from "./tipos";

/** El `borrador` de `POST /api/vales/{id}/cancelacion` con `rehacer: true`. */
export interface BorradorRehacerApi {
  tipo: TipoVale;
  almacen_id: string;
  trabajador_id: string | null;
  destino_almacen_id: string | null;
  observacion: string | null;
  renglones: {
    codigo: string;
    cantidad: number;
    condicion: Condicion | null;
    observacion: string | null;
    pieza?: { codigo: string; numero_serie: string | null } | null;
  }[];
}

/** `POST /api/vales/{id}/cancelacion`: el vale de cancelación y el vale que cancela. */
export interface CancelacionApi extends ValeConfirmadoApi {
  vale_cancelado: { id: string; folio: string; estado: string };
  motivo: string;
  borrador: BorradorRehacerApi | null;
}

/** ¿Este tipo de vale se vuelve a capturar desde su pantalla? */
export function sePuedeRehacer(tipo: TipoVale): boolean {
  return tipo === "ENTREGA" || tipo === "DEVOLUCION";
}

/** La pantalla donde se corrige un vale de este tipo, o null si no hay. */
export function rutaDeCaptura(tipo: TipoVale): "/entregar" | "/devolver" | null {
  return tipo === "ENTREGA" ? "/entregar" : tipo === "DEVOLUCION" ? "/devolver" : null;
}

/** ¿Ya hay una captura sin terminar de este tipo que se reemplazaría? */
export function hayCapturaSinTerminar(tipo: TipoVale, usuarioId: string): boolean {
  if (tipo === "ENTREGA") return tieneCaptura(leerBorrador(usuarioId));
  if (tipo === "DEVOLUCION") return tieneCapturaDevolucion(leerBorradorDevolucion(usuarioId));
  return false;
}

/**
 * Guarda el borrador del vale cancelado como un borrador nuevo del flujo de su tipo y dice a qué pantalla ir.
 * Devuelve `null` si el tipo no tiene pantalla de captura. Puede lanzar `ErrorApi` (al pedir la ficha).
 */
export async function cargarBorradorParaRehacer(
  borrador: BorradorRehacerApi,
  usuarioId: string,
): Promise<"/entregar" | "/devolver" | null> {
  if (borrador.tipo === "ENTREGA") {
    if (!borrador.trabajador_id) return null;
    const ficha = await apiGet<FichaTrabajadorApi>(`/trabajadores/${borrador.trabajador_id}`);
    const base = nuevoBorradorEntrega(usuarioId, borrador.almacen_id);
    guardarBorrador({
      ...base,
      paso: "articulos",
      trabajador: ficha,
      renglones: borrador.renglones.map((r) => ({
        codigo: r.codigo,
        cantidad: r.cantidad,
        observacion: r.observacion ?? undefined,
      })),
    });
    return "/entregar";
  }
  if (borrador.tipo === "DEVOLUCION") {
    let trabajador: TrabajadorDevolucion | null = null;
    if (borrador.trabajador_id) {
      const ficha = await apiGet<TrabajadorDevolucion>(`/trabajadores/${borrador.trabajador_id}`);
      trabajador = {
        id: ficha.id,
        numero_empleado: ficha.numero_empleado,
        nombre: ficha.nombre,
        puesto: ficha.puesto,
        area_obra: ficha.area_obra,
      };
    }
    const base = nuevoBorradorDevolucion(usuarioId, borrador.almacen_id);
    guardarBorradorDevolucion({
      ...base,
      trabajador,
      renglones: borrador.renglones.map((r) => ({
        ...nuevoRenglonDevolucion(r.codigo, r.cantidad, r.condicion),
        observacion: r.observacion ?? undefined,
      })),
    });
    return "/devolver";
  }
  return null;
}
