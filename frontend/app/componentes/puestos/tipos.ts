// Formas de lo que devuelve la API de puestos y dotación (docs/architecture/api-contracts.md, "Puestos y dotación").

export interface Puesto {
  id: string;
  nombre: string;
  activo: boolean;
  /** Artículos distintos en su dotación. */
  total_articulos: number;
}

export interface ArticuloDotacion {
  id: string;
  codigo: string;
  nombre: string;
  unidad: string;
  control: string;
}

export interface LimiteArticulo {
  cantidad: number;
  /** Vacío significa "en posesión". */
  periodo_dias: number | null;
}

export interface RenglonDotacion {
  articulo: ArticuloDotacion;
  cantidad: number;
  limite: LimiteArticulo | null;
}

export interface Dotacion {
  puesto: { id: string; nombre: string };
  renglones: RenglonDotacion[];
}

/** Lo que le falta a un trabajador de la dotación de su puesto (`GET /api/trabajadores/{id}/dotacion`). */
export interface RenglonDotacionTrabajador {
  articulo: ArticuloDotacion;
  recomendada: number;
  entregada: number;
  falta: number;
}

export interface DotacionTrabajador {
  puesto: { id: string; nombre: string } | null;
  renglones: RenglonDotacionTrabajador[];
}

/** "Límite: 4 cada 30 días", "Límite: 1 en posesión" o "Este artículo no tiene límite". */
export function textoLimiteDotacion(limite: LimiteArticulo | null): string {
  if (!limite) return "Este artículo no tiene límite";
  if (!limite.periodo_dias) return `Límite: ${limite.cantidad} en posesión`;
  return `Límite: ${limite.cantidad} cada ${limite.periodo_dias === 1 ? "1 día" : `${limite.periodo_dias} días`}`;
}

export function textoArticulos(total: number): string {
  if (total === 0) return "Sin dotación";
  return total === 1 ? "1 artículo" : `${total} artículos`;
}

/** Texto en minúsculas y sin acentos, para buscar sin que importen. */
export function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}
