/** Tipos de la administración de almacenes (FEAT-008; docs/architecture/api-contracts.md, «Administración de almacenes»). */

export type TipoAlmacen = "CENTRAL" | "SUBALMACEN" | "PROYECTO";
export type EstadoAlmacen = "ACTIVO" | "CERRADO";

export const TEXTO_TIPO: Record<TipoAlmacen, string> = {
  CENTRAL: "Central",
  SUBALMACEN: "Subalmacén",
  PROYECTO: "Proyecto",
};

export const AYUDA_TIPO: Record<TipoAlmacen, string> = {
  CENTRAL: "El almacén principal. Solo puede haber uno y no depende de otro.",
  SUBALMACEN: "Surte a otros almacenes, por ejemplo Contratistas.",
  PROYECTO: "Un área u obra que recibe material, por ejemplo Midrex.",
};

export interface HijoAlmacen {
  id: string;
  clave: string;
  nombre: string;
  estado: EstadoAlmacen;
}

/** Un motivo por el que todavía no se puede inactivar. Los campos de detalle dependen del `codigo`. */
export interface BloqueoCierre {
  codigo: "CON_EXISTENCIAS" | "CON_TRASPASOS_EN_TRANSITO" | "CON_HIJOS_ACTIVOS" | "CON_USUARIOS" | string;
  mensaje: string;
  unidades?: number;
  total_articulos?: number;
  articulos?: { articulo_id: string; codigo: string; nombre: string; cantidad: number }[];
  total?: number;
  traspasos?: { id: string; folio: string; estado: string; origen: { id: string; clave: string; nombre: string }; destino: { id: string; clave: string; nombre: string } }[];
  hijos?: { id: string; clave: string; nombre: string }[];
  usuarios?: { id: string; nombre: string; usuario: string }[];
}

export interface ResumenAlmacen {
  existencias: { unidades: number; articulos: number };
  piezas_en_resguardo: number;
  usuarios: number;
  traspasos_en_transito: number;
  solicitudes_compra_abiertas: number;
  tiene_folios: boolean;
  puede_cerrar: boolean;
  puede_reabrir: boolean;
  bloqueos_cierre: BloqueoCierre[];
}

/** La ficha de un almacén: la respuesta de `GET /api/almacenes?resumen=true` y de las escrituras. */
export interface FichaAlmacen {
  despacho_epp_con_aprobacion?: boolean;
  id: string;
  clave: string;
  nombre: string;
  tipo: TipoAlmacen;
  estado: EstadoAlmacen;
  padre_id: string | null;
  padre_clave: string | null;
  cerrado_en: string | null;
  hijos: HijoAlmacen[];
  resumen?: ResumenAlmacen;
  proyectos_activos?: number;
  aviso?: string | null;
}

export function plural(n: number, uno: string, varios: string): string {
  return `${n.toLocaleString("es-MX")} ${n === 1 ? uno : varios}`;
}

/** «340 unidades de 18 artículos · 4 piezas en resguardo · 3 usuarios». */
export function textoResumen(r: ResumenAlmacen): string {
  const existencias =
    r.existencias.unidades === 0 ? "Sin existencias" : `${plural(r.existencias.unidades, "unidad", "unidades")} de ${plural(r.existencias.articulos, "artículo", "artículos")}`;
  return [existencias, `${plural(r.piezas_en_resguardo, "pieza", "piezas")} en resguardo`, plural(r.usuarios, "usuario", "usuarios")].join(" · ");
}

/** El almacén y todos los que dependen de él, directa o indirectamente (no pueden ser su propio padre). */
export function conDescendientes(id: string, todos: readonly FichaAlmacen[]): Set<string> {
  const resultado = new Set<string>([id]);
  let crecio = true;
  while (crecio) {
    crecio = false;
    for (const a of todos) {
      if (a.padre_id && resultado.has(a.padre_id) && !resultado.has(a.id)) {
        resultado.add(a.id);
        crecio = true;
      }
    }
  }
  return resultado;
}
