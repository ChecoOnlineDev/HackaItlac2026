// Tipos de las solicitudes de compra urgente que ven quienes las piden.
// Fuente: docs/architecture/api-contracts.md, sección "Solicitudes de compra" (reglas SC-01 a SC-11).

export type EstadoSolicitud = "PENDIENTE" | "EN_COMPRA" | "COMPRADA" | "INGRESADA" | "RECHAZADA" | "CANCELADA";
export type Urgencia = "URGENTE" | "NORMAL";
export type AccionSolicitud = "tomar" | "rechazar" | "comprar" | "ingresar" | "cancelar";

export interface SolicitudCompra {
  id: string;
  /** Por ejemplo `MID-SOL-000001` (SC-09). */
  folio: string;
  estado: EstadoSolicitud;
  urgencia: Urgencia;
  almacen: { id: string; clave: string; nombre: string };
  solicitante: { id: string; nombre: string };
  /** `null` si el equipo no está en el catálogo. */
  articulo: { id: string; codigo: string; nombre: string } | null;
  /** Siempre trae un texto (el nombre del artículo, si lo hay). */
  descripcion: string;
  cantidad: number;
  motivo: string;
  /** La última nota de Compras (por ejemplo, por qué se rechazó). */
  nota_compras: string | null;
  vale_entrada: { id: string; folio: string } | null;
  creada_en: string;
  actualizada_en: string;
  /** Lo que el servidor deja hacer a quien consulta. La interfaz solo lo muestra. */
  acciones: AccionSolicitud[];
}

export interface PaginaSolicitudes {
  elementos: SolicitudCompra[];
  total: number;
}

export const TAMANO_SOLICITUDES = 20;
export const LARGO_MAXIMO_TEXTO = 255;
export const CANTIDAD_MAXIMA = 1_000_000;

export const TEXTO_ESTADO: Record<EstadoSolicitud, string> = {
  PENDIENTE: "Pendiente",
  EN_COMPRA: "En compra",
  COMPRADA: "Comprada",
  INGRESADA: "Ingresada al almacén",
  RECHAZADA: "Rechazada",
  CANCELADA: "Cancelada",
};

export const TEXTO_URGENCIA: Record<Urgencia, string> = {
  URGENTE: "Urgente",
  NORMAL: "Normal",
};

/** Opciones del filtro "Estado", en el orden en que Compras las trabaja. */
export const OPCIONES_ESTADO: { valor: EstadoSolicitud; texto: string }[] = (
  ["PENDIENTE", "EN_COMPRA", "COMPRADA", "INGRESADA", "RECHAZADA", "CANCELADA"] as const
).map((valor) => ({ valor, texto: TEXTO_ESTADO[valor] }));

export const OPCIONES_URGENCIA: { valor: Urgencia; texto: string }[] = [
  { valor: "URGENTE", texto: TEXTO_URGENCIA.URGENTE },
  { valor: "NORMAL", texto: TEXTO_URGENCIA.NORMAL },
];

/** Respuestas rápidas de "¿Para qué trabajo?". "Otro" deja el texto libre para escribirlo. */
export const MOTIVOS_RAPIDOS = ["Mantenimiento programado", "Reparación urgente", "Falta de existencia", "Otro"] as const;

/** Un artículo del catálogo elegido para pedirlo. */
export interface ArticuloElegido {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
}

/** "1 unidad" o "2 unidades", para el resumen. */
export function textoCantidad(cantidad: number): string {
  return `${cantidad} ${cantidad === 1 ? "unidad" : "unidades"}`;
}
