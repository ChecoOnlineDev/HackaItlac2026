// Formas de datos que usan los componentes de dominio. Fuente: docs/architecture/api-contracts.md
// (Vales: respuesta de `evaluar`) y backend/app/modulos/trabajadores/schemas.py (ficha).
// Son tipos de PRESENTACIÓN: los componentes no llaman a la API ni deciden nada.

/** Los cuatro niveles del semáforo (reglas de negocio, sección 3). */
export type NivelSemaforo = "VERDE" | "AMARILLO" | "NARANJA" | "ROJO";

/** Un motivo de la evaluación, con el ID de la regla que lo produjo (por ejemplo `E-06`). */
export interface MotivoRegla {
  regla: string;
  nivel: NivelSemaforo;
  mensaje: string;
}

export interface ArticuloEvaluado {
  id: string;
  nombre: string;
  marca?: string | null;
  talla?: string | null;
  control: "PIEZA" | "CANTIDAD";
  // Campos que el servidor también manda (`ArticuloEvaluadoOut`).
  codigo?: string;
  modelo?: string | null;
  unidad?: string;
  retornable?: boolean;
  activo?: boolean;
}

export interface PiezaEvaluada {
  /** Va vacío en una pieza que todavía no existe (renglón de entrada). */
  id?: string | null;
  estado?: string | null;
  inspeccion_vigente_hasta?: string | null;
  numero_serie?: string | null;
  /** `true` si la pieza no tiene serie (E-29); el aviso amarillo llega en `motivos`. */
  serie_pendiente?: boolean;
}

/** Quien tiene la pieza ahora. El servidor puede mandar solo el nombre o un objeto. */
export type TitularPieza = string | { nombre: string; tipo?: string | null } | null;

/** Un renglón de la respuesta de `POST /api/vales/evaluar`. */
export interface RenglonEvaluado {
  renglon: number;
  codigo: string;
  /** Es null cuando el código no existe (renglón rojo). */
  articulo: ArticuloEvaluado | null;
  pieza: PiezaEvaluada | null;
  titular: TitularPieza;
  cantidad: number;
  disponible: number | null;
  nivel: NivelSemaforo;
  motivos: MotivoRegla[];
  pide_observacion: boolean;
  autorizable: boolean;
  requiere_confirmacion: boolean;
  /** Un naranja que la `autorizacion_id` enviada ya cubre. */
  autorizado?: boolean;
}

/** Condición de un renglón recibido o devuelto. */
export type Condicion = "BUENO" | "DESGASTE" | "DANADO";

/** Lo que el servidor guarda de una firma: `{modo, imagen, trazo}` (api-contracts.md, Vales). */
export interface PuntoTrazo {
  x: number;
  y: number;
  /** Milisegundos desde que empezó la firma. */
  t: number;
}
/** Una lista de trazos; cada trazo es una lista de puntos. */
export type Trazo = PuntoTrazo[][];

/** Una credencial, pieza o estante para imprimir. Forma de `GET /api/etiquetas`. */
export interface EtiquetaElemento {
  codigo: string;
  texto: string;
  /** Solo en credenciales: con esto se arma la tarjeta. Nunca CURP ni NSS (RG-13). */
  nombre?: string;
  numero_empleado?: string;
  puesto?: string;
}
