import { apiGet } from "./cliente";

// Tablero de inicio (FEAT-008, TB-01 a TB-03). Fuente: docs/architecture/api-contracts.md, sección «Tablero».

export interface AlcanceTablero {
  almacen_id: string | null;
  nombre: string;
  es_todos: boolean;
  /** Solo con `almacenes.todos`: la interfaz muestra el selector de almacén. */
  puede_elegir: boolean;
}

export interface ResumenTablero {
  alcance: AlcanceTablero;
  existencias: { unidades: number; articulos: number };
  resguardo_equipo_importante: number;
  sin_existencia: number;
  traspasos_en_transito: number;
  entregas_hoy: number;
  solicitudes_compra_abiertas: number;
  inspecciones_por_vencer: number;
  generado_en: string;
}

export interface BarraConsumo {
  articulo_id: string;
  articulo: string;
  categoria: { id: string; nombre: string };
  unidad: string;
  total: number;
  /** Vacío salvo con `separar_por_almacen` y alcance de todos los almacenes. */
  por_almacen: { almacen_id: string; almacen: string; total: number }[];
}

export interface ConsumoTablero {
  desde: string;
  hasta: string;
  almacen: { id: string; clave: string; nombre: string } | null;
  categoria: { id: string; nombre: string } | null;
  limite: number;
  separar_por_almacen: boolean;
  barras: BarraConsumo[];
  otros: { total: number; articulos: number };
  total_general: number;
  sin_registros: boolean;
}

export interface ParametrosConsumo {
  desde: string;
  hasta: string;
  almacen_id?: string;
  categoria_id?: string;
  separar_por_almacen?: boolean;
  limite?: number;
}

export const pedirResumenTablero = (almacenId: string, signal?: AbortSignal) =>
  apiGet<ResumenTablero>("/tablero/resumen", { almacen_id: almacenId || undefined }, signal);

export const pedirConsumoTablero = (p: ParametrosConsumo, signal?: AbortSignal) =>
  apiGet<ConsumoTablero>(
    "/tablero/consumo",
    {
      desde: p.desde,
      hasta: p.hasta,
      almacen_id: p.almacen_id || undefined,
      categoria_id: p.categoria_id || undefined,
      separar_por_almacen: p.separar_por_almacen ? true : undefined,
      limite: p.limite ?? 10,
    },
    signal,
  );
