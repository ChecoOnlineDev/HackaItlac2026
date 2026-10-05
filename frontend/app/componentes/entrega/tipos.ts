// Formas de lo que responde la API en el flujo de captura de vales (entrega y, más adelante, devolución
// y traspaso). Fuente: backend/app/modulos/movimientos/schemas.py y autorizaciones/schemas.py.
// Son tipos de PRESENTACIÓN: nada aquí decide una regla; la interfaz muestra lo que evalúa el servidor.

import type { DatosFichaTrabajador } from "~/componentes/dominio/ficha-trabajador";
import type { MotivoRegla, NivelSemaforo, RenglonEvaluado, Trazo } from "~/componentes/dominio/tipos";
import type { TipoVale } from "~/componentes/dominio/vale-imprimible";

export interface AlmacenResumen {
  id: string;
  clave: string;
  nombre: string;
}

/** Ficha del trabajador (`GET /api/trabajadores/{id}` o la `trabajador` de la evaluación). */
export interface FichaTrabajadorApi extends DatosFichaTrabajador {
  estado?: string;
  estado_texto?: string;
}

/** `POST /api/vales/evaluar`. */
export interface EvaluacionApi {
  nivel: NivelSemaforo;
  puede_confirmar: boolean;
  /** Motivos que valen para todo el vale (por ejemplo E-02 o E-12). */
  motivos: MotivoRegla[];
  almacen: AlmacenResumen;
  trabajador: FichaTrabajadorApi | null;
  /** Si la autorización enviada no sirve, por qué (A-03). */
  autorizacion_error: string | null;
  renglones: RenglonEvaluado[];
}

/** Respuesta de `POST /api/vales` (201, o 200 si el `id_cliente` ya existía). */
export interface ValeConfirmadoApi {
  id: string;
  folio: string;
  token: string;
  creado_en: string;
  renglones: { renglon: number; codigo: string; articulo: string; cantidad: number; nivel: NivelSemaforo; reglas: string[] }[];
}

export type EstadoAutorizacionApi = "PENDIENTE" | "APROBADA" | "RECHAZADA" | "VENCIDA" | "USADA";

export interface PersonaApi {
  id: string;
  nombre: string;
}

/** `GET /api/autorizaciones/{id}` y la respuesta de la resolución. */
export interface AutorizacionApi {
  id: string;
  estado: EstadoAutorizacionApi;
  medio: "PIN" | "REMOTA" | null;
  motivo: string;
  trabajador_id: string;
  almacen_id: string;
  solicitada_por: PersonaApi;
  resuelta_por: PersonaApi | null;
  creado_en: string;
  resuelta_en: string | null;
  vence_en: string;
}

/** Un renglón del vale tal como lo manda el servidor en el detalle. */
export interface RenglonValeApi {
  renglon: number;
  articulo_id: string;
  articulo: string;
  marca: string | null;
  modelo: string | null;
  talla: string | null;
  codigo_articulo: string;
  pieza_id: string | null;
  codigo_pieza: string | null;
  numero_serie: string | null;
  cantidad: number;
  condicion: string | null;
  nivel: NivelSemaforo;
  reglas: string[];
  observacion: string | null;
}

/** `GET /api/vales/{id}` y `GET /api/vales/por-token/{token}`. */
export interface ValeDetalleApi {
  id: string;
  folio: string;
  token: string;
  tipo: TipoVale;
  estado: "EMITIDO" | "EN_TRANSITO" | "RECIBIDO" | "RECIBIDO_CON_DIFERENCIAS" | "CANCELADO";
  almacen: AlmacenResumen;
  destino_almacen: AlmacenResumen | null;
  trabajador: { id: string; numero_empleado: string; nombre: string; puesto: string | null; area_obra: string | null } | null;
  responsable: PersonaApi;
  observacion: string | null;
  firma_modo: "PANTALLA" | "SESION" | null;
  tiene_firma: boolean;
  valido: {
    autorizacion_id: string;
    solicito: PersonaApi | null;
    autorizo: PersonaApi;
    medio: string;
    resuelta_en: string;
    motivo: string;
  } | null;
  vale_origen_id: string | null;
  vale_origen_folio: string | null;
  dispositivo: string | null;
  creado_en: string;
  renglones: RenglonValeApi[];
}

/** Una fila de `GET /api/vales`. */
export interface ValeListaApi {
  id: string;
  folio: string;
  tipo: TipoVale;
  estado: ValeDetalleApi["estado"];
  almacen: AlmacenResumen;
  trabajador: PersonaApi | null;
  numero_empleado: string | null;
  responsable: PersonaApi;
  renglones: number;
  creado_en: string;
}

/** Lo que se firmó en pantalla. */
export interface FirmaCapturada {
  imagen: string;
  trazo: Trazo;
}
