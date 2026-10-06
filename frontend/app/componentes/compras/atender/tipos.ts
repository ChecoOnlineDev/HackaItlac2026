// Tipos de la solicitud de compra urgente. Fuente: docs/architecture/api-contracts.md, "Solicitudes de compra".

export type EstadoSolicitud = "PENDIENTE" | "EN_COMPRA" | "COMPRADA" | "INGRESADA" | "RECHAZADA" | "CANCELADA";
export type UrgenciaSolicitud = "URGENTE" | "NORMAL";

/** Lo que el servidor dice que el usuario puede hacer con esta solicitud. La interfaz no lo deduce. */
export type AccionSolicitud = "tomar" | "rechazar" | "comprar" | "ingresar" | "cancelar";

export interface EventoSolicitud {
  id?: string;
  estado_anterior: EstadoSolicitud | null;
  estado_nuevo: EstadoSolicitud;
  usuario: { id?: string; nombre: string };
  nota: string | null;
  /** Instante en UTC. */
  creado_en: string;
}

export interface SolicitudCompra {
  id: string;
  folio: string;
  estado: EstadoSolicitud;
  urgencia: UrgenciaSolicitud;
  almacen: { id: string; clave: string; nombre: string };
  solicitante: { id: string; nombre: string };
  articulo: { id: string; codigo: string; nombre: string } | null;
  descripcion: string;
  cantidad: number;
  motivo: string;
  nota_compras: string | null;
  vale_entrada: { id: string; folio: string } | null;
  creada_en: string;
  actualizada_en: string;
  acciones: AccionSolicitud[];
  /** Solo el detalle trae la línea de tiempo (más antiguo primero). */
  eventos?: EventoSolicitud[];
}

export const TEXTO_ESTADO: Record<EstadoSolicitud, string> = {
  PENDIENTE: "Pendiente",
  EN_COMPRA: "En compra",
  COMPRADA: "Comprada",
  INGRESADA: "Ingresada",
  RECHAZADA: "Rechazada",
  CANCELADA: "Cancelada",
};

export const TEXTO_URGENCIA: Record<UrgenciaSolicitud, string> = {
  URGENTE: "Urgente",
  NORMAL: "Normal",
};

/** Cuerpo de `POST /api/solicitudes-compra/{id}/estado`. */
export interface CambioEstado {
  estado: Exclude<EstadoSolicitud, "PENDIENTE" | "CANCELADA">;
  nota?: string;
  vale_entrada_id?: string;
}

/** Qué estado pide cada acción de Compras (SC-04). `cancelar` es otro endpoint. */
export const ESTADO_DE_ACCION: Record<Exclude<AccionSolicitud, "cancelar">, CambioEstado["estado"]> = {
  tomar: "EN_COMPRA",
  rechazar: "RECHAZADA",
  comprar: "COMPRADA",
  ingresar: "INGRESADA",
};

export const TEXTO_ACCION: Record<AccionSolicitud, string> = {
  tomar: "Tomar",
  rechazar: "Rechazar",
  comprar: "Marcar como comprada",
  ingresar: "Ingresar al almacén",
  cancelar: "Cancelar solicitud",
};

export const TAMANO_COLA = 20;

/** Un vale de la lista de `GET /api/vales` (solo lo que usa el selector de la entrada). */
export interface ValeEntradaLista {
  id: string;
  folio: string;
  estado: string;
  almacen: { id: string; clave: string; nombre: string };
  renglones: number;
  creado_en: string;
}
