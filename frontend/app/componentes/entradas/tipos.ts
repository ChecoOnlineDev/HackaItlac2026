// Tipos de la pantalla de entrada de inventario. Fuente: backend/app/modulos/movimientos/schemas.py
// y tipos/entrada.py. Ningún dato aquí lleva costos: el costo vive en el catálogo (I-04, RG-12).

import type { MotivoRegla, NivelSemaforo, RenglonEvaluado } from "~/componentes/dominio/tipos";

export type ResultadoInspeccion = "APTO" | "NO_APTO";

/** Inspección inicial capturada junto con una pieza que entra (I-03). */
export interface InspeccionBorrador {
  resultado: ResultadoInspeccion;
  observacion: string;
}

export interface PiezaBorrador {
  codigo: string;
  numero_serie: string;
  /** `null` si la inspección queda pendiente. */
  inspeccion: InspeccionBorrador | null;
}

/** Un renglón del borrador: lo que la persona capturó. La revisión de reglas la hace el servidor. */
export interface RenglonBorrador {
  /** Identifica el renglón mientras se captura. */
  clave: string;
  articulo_id: string;
  /** Código del artículo, el que recibe el servidor. */
  codigo: string;
  /** Para mostrar si no hay conexión para revisar el renglón. */
  nombre: string;
  marca: string | null;
  control: "PIEZA" | "CANTIDAD";
  requiere_inspeccion: boolean;
  unidad: string;
  cantidad: number;
  /** Solo en artículos por pieza. */
  pieza?: PiezaBorrador;
}

export interface Borrador {
  /** Un solo identificador por entrada: confirmar dos veces nunca crea dos vales. */
  id_cliente: string;
  almacen_id: string;
  renglones: RenglonBorrador[];
}

/** Lo que devuelve `POST /api/vales/evaluar` para una entrada. */
export interface RenglonEvaluadoEntrada extends Omit<RenglonEvaluado, "pieza"> {
  pieza: {
    id: string | null;
    codigo: string;
    numero_serie: string | null;
    estado: string | null;
    pendiente_inspeccion: boolean;
  } | null;
}

export interface EvaluacionEntrada {
  nivel: NivelSemaforo;
  puede_confirmar: boolean;
  motivos: MotivoRegla[];
  almacen: { id: string; clave: string; nombre: string };
  renglones: RenglonEvaluadoEntrada[];
}

export interface ArticuloFichaEntrada {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  control: "PIEZA" | "CANTIDAD";
  unidad: string;
  activo: boolean;
  requiere_inspeccion: boolean;
}

export interface ValeConfirmado {
  id: string;
  folio: string;
  token: string;
  creado_en: string;
}

/** Identificador aleatorio; no depende de que la página sea segura (HTTPS). */
export function nuevoId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function nuevoBorrador(almacenId = ""): Borrador {
  return { id_cliente: nuevoId(), almacen_id: almacenId, renglones: [] };
}

/** Cuerpo de `evaluar` y de `confirmar` (confirmar agrega `id_cliente`). */
export function cuerpoDeEntrada(b: Borrador, puedeElegirAlmacen: boolean) {
  return {
    tipo: "ENTRADA" as const,
    almacen_id: puedeElegirAlmacen && b.almacen_id ? b.almacen_id : undefined,
    renglones: b.renglones.map((r) => ({
      codigo: r.codigo,
      cantidad: r.cantidad,
      ...(r.pieza
        ? {
            pieza: {
              codigo: r.pieza.codigo.trim(),
              numero_serie: r.pieza.numero_serie.trim() || null,
              inspeccion: r.pieza.inspeccion
                ? { resultado: r.pieza.inspeccion.resultado, observacion: r.pieza.inspeccion.observacion.trim() || null }
                : null,
            },
          }
        : {}),
    })),
  };
}
