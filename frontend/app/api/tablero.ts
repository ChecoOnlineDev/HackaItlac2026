import { apiGet } from "./cliente";

// Tablero de inicio (FEAT-008, TB-01 a TB-03). Fuente: docs/architecture/api-contracts.md, sección «Tablero».

export interface AlcanceTablero {
  almacen_id: string | null;
  nombre: string;
  es_todos: boolean;
  /** Solo con `almacenes.todos`: la interfaz muestra el selector de almacén. */
  puede_elegir: boolean;
  almacenes?: { id: string; clave: string; nombre: string }[];
}

export interface ResumenTablero {
  alcance: AlcanceTablero;
  existencias: { unidades: number; articulos: number };
  resguardo_equipo_importante: number;
  sin_existencia: number;
  traspasos_en_transito: number;
  entregas_hoy: number;
  solicitudes_compra_abiertas: number;
  inspecciones_por_vencer: number | null;
  inspecciones_vencidas?: number | null;
  inspecciones_sin_registro?: number | null;
  /** Puede faltar si el servidor es anterior a ADR-010. */
  piezas_serie_pendiente?: number;
  /** SG-04: solo llega con `resguardo.ver`; sin ese permiso es `null`. */
  alto_valor_fuera?: number | null;
  almacenes_sin_proyecto?: { id: string; clave: string; nombre: string }[] | null;
  proyectos_por_vencer?: { id: string; clave: string; nombre: string; almacen: { id: string; clave: string; nombre: string }; fin_estimado: string }[] | null;
  inventario_unidades?: { en_almacen: number; en_resguardo: number; total: number };
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

// Valor del inventario (GET /api/tablero/valor, permiso `reportes.valor_inventario`). Los importes llegan como texto decimal.
export interface ValorPorCategoria {
  categoria: string;
  valor: string;
  unidades?: number;
}

export interface ValorPorAlmacen {
  almacen_id: string;
  nombre: string;
  en_almacen: string;
  en_resguardo: string;
  total: string;
  unidades_en_almacen?: number;
  unidades_en_resguardo?: number;
  unidades_total?: number;
}

export interface ValorTablero {
  moneda: "MXN";
  alcance: { todos: boolean; almacen_id: string | null; almacen_nombre: string | null };
  total: string;
  en_almacen: string;
  en_resguardo: string;
  en_transito: string | null;
  articulos_sin_costo: number;
  unidades_sin_costo: number;
  por_categoria: ValorPorCategoria[];
  /** Vacío si no aplica (un solo almacén). */
  por_almacen: ValorPorAlmacen[];
  generado_en: string;
  unidades_en_almacen?: number;
  unidades_en_resguardo?: number;
  unidades_total?: number;
}

export interface TotalUso { unidades: number; valor: string | null }
export interface UsoProyecto {
  retornables_en_resguardo: TotalUso;
  consumibles_consumidos: TotalUso;
  total: TotalUso;
  articulos_sin_costo: number;
}
export interface ProyectoTablero extends UsoProyecto {
  id: string; clave: string; nombre: string;
  almacen: { id: string; clave: string; nombre: string };
  inicio: string; fin_estimado: string; estado: string; situacion: string;
  trabajadores_asignados: number;
  por_categoria: (UsoProyecto & { categoria: { id: string; nombre: string } | null; nombre: string })[] | null;
}
export interface UsoProyectosTablero {
  alcance: AlcanceTablero;
  rango: { desde: string; hasta: string };
  proyectos: ProyectoTablero[];
  sin_proyecto: UsoProyecto;
  generado_en: string;
}
export const pedirUsoProyectos = (parametros: { desde: string; hasta: string; almacen_id?: string; proyecto_id?: string }, signal?: AbortSignal) => apiGet<UsoProyectosTablero>("/tablero/proyectos", parametros, signal);

export const pedirValorTablero = (almacenId: string, signal?: AbortSignal) =>
  apiGet<ValorTablero>("/tablero/valor", { almacen_id: almacenId || undefined }, signal);
