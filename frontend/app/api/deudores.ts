import { apiGet } from "./cliente";

export interface RenglonDeuda {
  articulo: { id: string; codigo: string; nombre: string; marca: string | null };
  pieza: { id: string; codigo: string; numero_serie: string | null; serie_pendiente: boolean } | null;
  cantidad: number; desde: string | null;
  vale: { id: string | null; folio: string | null };
  proyecto: { id: string; nombre: string; estado: string } | null;
  almacen: { id: string; clave: string; nombre: string; estado: string };
  alto_valor: boolean; requiere_inspeccion: boolean;
}
export interface Deudor {
  trabajador: { id: string; nombre: string; numero_empleado: string; tiene_foto: boolean };
  vigente: boolean; aviso: string | null;
  proyectos: { id: string; nombre: string; estado: string }[];
  piezas: number; unidades: number; alto_valor: number; desde: string | null;
  otros_almacenes: number; renglones: RenglonDeuda[] | null;
}
export interface ListaDeudores {
  elementos: Deudor[]; total: number; sin_registros: boolean; mensaje: string | null;
  resumen: { trabajadores_con_adeudo: number; alto_valor_fuera: number; no_vigentes_con_adeudo: number; mas_de_30_dias: number };
}
export interface ResumenDeudores {
  almacenes: { almacen_id: string; almacen_clave: string; almacen_nombre: string; trabajadores: number; piezas: number; unidades: number; alto_valor: number; no_vigentes: number }[];
  proyectos: { proyecto_id: string | null; proyecto_nombre: string | null; trabajadores: number; piezas: number; unidades: number; alto_valor: number; no_vigentes: number }[];
}
export interface ConsumoTrabajador {
  periodo: { desde: string; hasta: string; origen: string };
  elementos: { articulo: { id: string; codigo: string; nombre: string }; unidad: string; cantidad: number; recomendado: number | null; por_proyecto: { proyecto: { id: string; nombre: string } | null; cantidad: number }[] }[];
  valor_total?: string | null;
  valor_por_proyecto?: { proyecto: { id: string; nombre: string } | null; valor: string | null }[];
  aviso_valor?: string;
}
export type FiltrosDeudores = Record<string, string | number | boolean | undefined>;
export const listarDeudores = (filtros: FiltrosDeudores, signal?: AbortSignal) => apiGet<ListaDeudores>("/deudores", filtros, signal);
export const resumenDeudores = (filtros: FiltrosDeudores, signal?: AbortSignal) => apiGet<ResumenDeudores>("/deudores/resumen", filtros, signal);
export const consumoTrabajador = (id: string, filtros: FiltrosDeudores, signal?: AbortSignal) => apiGet<ConsumoTrabajador>(`/trabajadores/${id}/consumo`, filtros, signal);
