// Tipos y textos del catálogo. Fuente: docs/architecture/api-contracts.md y los esquemas del servidor.

export type TipoCategoria = "EPP" | "HERRAMIENTA";
export type Control = "PIEZA" | "CANTIDAD";

/** Las reglas que comparten la plantilla de una categoría y un artículo (CF-02). */
export interface Reglas {
  requiere_inspeccion: boolean;
  vigencia_inspeccion_dias: number | null;
  requiere_autorizacion: boolean;
  motivo_uso_especial: string | null;
  limite_cantidad: number | null;
  /** Vacío significa "en posesión". */
  limite_periodo_dias: number | null;
  cantidad_aviso: number | null;
}

export interface Categoria extends Reglas {
  id: string;
  nombre: string;
  tipo: TipoCategoria;
  control: Control;
  retornable: boolean;
  activo: boolean;
}

export interface ArticuloLista {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  modelo: string | null;
  categoria_id: string;
  categoria_nombre: string;
  control: Control;
  retornable: boolean;
  talla: string | null;
  unidad: string;
  requiere_inspeccion: boolean;
  requiere_autorizacion: boolean;
  activo: boolean;
  /** Solo viene con el permiso de costos. */
  costo_unitario?: string | number | null;
}

export interface Articulo extends ArticuloLista, Reglas {
  motivo_inactivacion: string | null;
  creado_en: string;
}

export interface ExistenciaAlmacen {
  almacen_id: string;
  clave: string;
  nombre: string;
  cantidad: number;
  disponible: number;
}

export interface Poseedor {
  trabajador_id: string;
  numero_empleado: string;
  nombre: string;
  cantidad: number;
}

export interface ArticuloFicha extends Articulo {
  tiene_movimientos: boolean;
  existencias: ExistenciaAlmacen[];
  en_posesion: Poseedor[];
}

export interface AlmacenResumen {
  id: string;
  clave: string;
  nombre: string;
}

export interface Almacen extends AlmacenResumen {
  tipo: string;
  estado: string;
}

export interface ExistenciaInventario {
  articulo_id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  talla: string | null;
  unidad: string;
  control: Control;
  retornable: boolean;
  categoria_id: string;
  categoria_nombre: string;
  activo: boolean;
  cantidad: number;
  disponible: number;
}

export interface Existencias {
  almacen: AlmacenResumen;
  elementos: ExistenciaInventario[];
  total: number;
}

export const TAMANO_PAGINA = 20;

export const TEXTO_TIPO: Record<TipoCategoria, string> = { EPP: "EPP", HERRAMIENTA: "Herramienta" };
export const TEXTO_CONTROL: Record<Control, string> = { PIEZA: "Por pieza", CANTIDAD: "Por cantidad" };

export function textoRetorno(retornable: boolean): string {
  return retornable ? "Retornable" : "Consumible";
}

function dias(n: number): string {
  return n === 1 ? "1 día" : `${n} días`;
}

/** Frase corta del límite: "Máximo 2 cada 30 días" o "Máximo 1 en posesión". */
export function textoLimite(r: Pick<Reglas, "limite_cantidad" | "limite_periodo_dias">): string | null {
  if (r.limite_cantidad === null || r.limite_cantidad === undefined) return null;
  return r.limite_periodo_dias
    ? `Máximo ${r.limite_cantidad} cada ${dias(r.limite_periodo_dias)}`
    : `Máximo ${r.limite_cantidad} en posesión`;
}

/** Resumen de la plantilla en frases cortas, para la lista de categorías. */
export function resumenReglas(r: Reglas): string[] {
  const partes: string[] = [];
  if (r.requiere_inspeccion) {
    partes.push(
      r.vigencia_inspeccion_dias
        ? `Inspección vigente (${dias(r.vigencia_inspeccion_dias)})`
        : "Inspección vigente",
    );
  }
  if (r.requiere_autorizacion) partes.push("Pide autorización del supervisor");
  const limite = textoLimite(r);
  if (limite) partes.push(limite);
  if (r.cantidad_aviso) partes.push(`Avisa desde ${r.cantidad_aviso} piezas`);
  return partes;
}

/** Texto del costo con dos decimales. */
export function textoCosto(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "Sin costo";
  const n = Number(valor);
  if (Number.isNaN(n)) return "Sin costo";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(n);
}

export function nombreConMarca(a: { nombre: string; marca: string | null; modelo?: string | null }): string {
  return [a.nombre, a.marca, a.modelo].filter(Boolean).join(" · ");
}
