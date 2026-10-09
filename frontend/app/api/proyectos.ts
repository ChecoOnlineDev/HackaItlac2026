import { apiGet, apiPatch, apiPost } from "./cliente";
import type { Pagina } from "./tipos";

export interface Proyecto {
  id: string;
  clave: string;
  nombre: string;
  almacen: { id: string; clave: string; nombre: string };
  inicio: string;
  fin_estimado: string;
  estado: "ACTIVO" | "CERRADO";
  situacion: "VIGENTE" | "POR_INICIAR" | "FIN_VENCIDO" | "CERRADO";
  asignable: boolean;
  trabajadores_asignados: number;
  cerrado_en: string | null;
  motivo_cierre: string | null;
  creado_en: string;
  aviso?: string | null;
}
export interface AsignacionProyecto {
  id: string;
  asignacion_id: string;
  proyecto: Proyecto;
  principal: boolean;
  inicio: string;
  fin: string | null;
  creado_en: string;
  terminada_en: string | null;
}
export interface DatosProyecto { clave: string; nombre: string; almacen_id: string; inicio: string; fin_estimado: string }
export const SITUACIONES = { VIGENTE: "Vigente", POR_INICIAR: "Por iniciar", FIN_VENCIDO: "Fin estimado vencido", CERRADO: "Cerrado" };
export const listarProyectos = (parametros: Record<string, string | number | boolean | undefined> = {}, signal?: AbortSignal) => apiGet<Pagina<Proyecto>>("/proyectos", parametros, signal);
export const crearProyecto = (datos: DatosProyecto) => apiPost<Proyecto>("/proyectos", datos);
export const editarProyecto = (id: string, datos: Partial<DatosProyecto>) => apiPatch<Proyecto>(`/proyectos/${id}`, datos);
export const cerrarProyecto = (id: string, motivo: string) => apiPost<Proyecto & { asignaciones_terminadas: number; trabajadores_sin_proyecto: number }>(`/proyectos/${id}/cierre`, { motivo });
export const reabrirProyecto = (id: string, fin_estimado: string) => apiPost<Proyecto>(`/proyectos/${id}/reapertura`, { fin_estimado });
export const proyectosDeTrabajador = (id: string, signal?: AbortSignal) => apiGet<AsignacionProyecto[]>(`/trabajadores/${id}/proyectos`, undefined, signal);
export const asignarProyecto = (id: string, proyecto_id: string, reemplaza_asignacion_id?: string) => apiPost<AsignacionProyecto[]>(`/trabajadores/${id}/proyectos`, { proyecto_id, reemplaza_asignacion_id });
export const terminarProyecto = (id: string, asignacion: string) => apiPost<{ asignaciones: AsignacionProyecto[]; queda_sin_proyecto: boolean }>(`/trabajadores/${id}/proyectos/${asignacion}/termino`);
