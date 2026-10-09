// Formas de lo que responde la API en Trasladar y Recibir. Fuente: backend/app/modulos/movimientos/
// schemas_traspasos.py. Son tipos de PRESENTACIÓN: la interfaz muestra lo que evalúa el servidor.

import type { AlmacenResumen } from "~/componentes/entrega/tipos";

export interface RenglonPorRecibirApi {
  renglon: number;
  articulo_id: string;
  articulo: string;
  marca: string | null;
  modelo: string | null;
  talla: string | null;
  /** Lo que se escanea al recibirlo: el código de la pieza, o el del artículo si es por cantidad. */
  codigo: string;
  pieza_id: string | null;
  numero_serie: string | null;
  cantidad_enviada: number;
  cantidad_recibida: number;
  cantidad_pendiente: number;
}

export interface RecepcionResumenApi {
  id: string;
  folio: string;
  creado_en: string;
  recibio: { id: string; nombre: string };
}

/** Quién validó el envío (X-16, X-19). `medio`: ENVIO_PROPIO, REMOTA o PIN. */
export interface ValidoTraspasoApi {
  autorizo: { id?: string; nombre: string };
  medio: string | null;
}

export interface TraspasoPorRecibirApi {
  id: string;
  folio: string;
  token: string;
  estado: "EN_TRANSITO" | "RECIBIDO_CON_DIFERENCIAS" | string;
  origen: AlmacenResumen;
  destino: AlmacenResumen;
  envio: { id: string; nombre: string };
  /** FEAT-015: LATERAL es un traslado entre proyectos. Puede faltar en un servidor anterior. */
  ruta?: "HABITUAL" | "LATERAL" | "NO_HABITUAL";
  valido?: ValidoTraspasoApi | null;
  creado_en: string;
  pendiente_total: number;
  renglones: RenglonPorRecibirApi[];
  recepciones: RecepcionResumenApi[];
}

export interface PorRecibirApi {
  total: number;
  elementos: TraspasoPorRecibirApi[];
}

/** Un almacén de `GET /api/almacenes` con su red (quién lo surte y a quién surte). */
export interface AlmacenRedApi extends AlmacenResumen {
  tipo: string;
  estado: string;
  padre_id: string | null;
  padre_clave: string | null;
  hijos: AlmacenResumen[];
}
