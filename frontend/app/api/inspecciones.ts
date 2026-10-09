import { apiGet, apiPost } from "./cliente";
import type { ClavePunto } from "~/componentes/consulta/tipos";

export type EstadoPendiente = "VENCIDA" | "POR_VENCER" | "SIN_INSPECCION";
export interface ConteosInspecciones {
  vencidas: number; por_vencer: number; sin_inspeccion: number; no_aptas: number; en_mantenimiento: number; no_aptas_con_trabajador: number;
}
export interface PendienteInspeccion {
  pieza: { id: string; codigo: string; numero_serie: string | null; serie_pendiente: boolean; estado: string };
  articulo: { id: string; codigo: string; nombre: string; categoria: string };
  vigente_hasta: string | null; dias_restantes: number | null; dias_aviso: number;
  ubicacion: { tipo: string; almacen: { id: string; clave: string; nombre: string } | null; trabajador: { id: string; nombre: string; numero_empleado: string; puesto?: string | null } | null; desde: string | null; folio: string | null; vale_id: string | null; destino: { id: string; nombre: string } | null };
  accion: "INSPECCIONAR" | "PEDIR_DEVOLUCION" | "NINGUNA";
}
export interface PendientesInspeccion { conteos: ConteosInspecciones; elementos: PendienteInspeccion[]; total: number }
export type PuntosInspeccion = Record<ClavePunto, boolean | null>;
export interface DatosInspeccion { id_cliente: string; resultado: "APTO" | "NO_APTO"; puntos: PuntosInspeccion; observacion?: string; foto?: string }
export const consultarPendientes = (parametros: Record<string, string | number | boolean | undefined>, signal?: AbortSignal) => apiGet<PendientesInspeccion>("/inspecciones/pendientes", parametros, signal);
export const registrarInspeccion = (id: string, datos: DatosInspeccion) => apiPost(`/piezas/${id}/inspecciones`, datos);
export interface ResultadoLoteInspeccion { guardadas: number; rechazadas: number; repetidas: number; resultados: { id_cliente: string; codigo: string; estado: "GUARDADA" | "REPETIDA" | "RECHAZADA"; error?: { codigo: string; mensaje: string; regla?: string } }[] }
export const registrarLoteInspecciones = (id_lote: string, piezas: (DatosInspeccion & { codigo: string })[]) => apiPost<ResultadoLoteInspeccion>("/inspecciones/lote", { id_lote, piezas });
export function textoVigencia(dias: number | null) {
  if (dias === null) return "Sin inspección vigente";
  if (dias === 0) return "Vence hoy";
  if (dias > 0) return `Vence en ${dias} ${dias === 1 ? "día" : "días"}`;
  return `Venció hace ${Math.abs(dias)} ${dias === -1 ? "día" : "días"}`;
}
