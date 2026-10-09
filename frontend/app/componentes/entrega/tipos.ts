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
export interface ProyectoResumen {
  id: string;
  clave: string;
  nombre: string;
}

/** Ficha del trabajador (`GET /api/trabajadores/{id}` o la `trabajador` de la evaluación). */
export interface FichaTrabajadorApi extends DatosFichaTrabajador {
  estado?: string;
  estado_texto?: string;
}

/** Quién autoriza un traspaso según el servidor (FEAT-015, X-16 a X-19). La pantalla solo lo muestra. */
export type AutorizaTraspaso = "NADIE" | "ENVIO_PROPIO" | "SUPERVISOR_ORIGEN" | "ADMINISTRADOR";

/** La ruta de un traspaso, evaluada por el servidor. */
export interface RutaEvaluadaApi {
  clase: "HABITUAL" | "LATERAL" | "NO_HABITUAL" | "MISMO";
  autoriza: AutorizaTraspaso;
  /** Cuántas personas pueden autorizar, sin contar a quien envía. */
  autorizadores_disponibles: number;
}

/** `POST /api/vales/evaluar`. */
export interface EvaluacionApi {
  /** Solo en un traspaso. */
  ruta?: RutaEvaluadaApi;
  nivel: NivelSemaforo;
  puede_confirmar: boolean;
  /** Motivos que valen para todo el vale (por ejemplo E-02 o E-12). */
  motivos: MotivoRegla[];
  almacen: AlmacenResumen;
  trabajador: FichaTrabajadorApi | null;
  proyecto?: ProyectoResumen | null;
  proyectos_del_trabajador?: ProyectoResumen[];
  pide_proyecto?: boolean;
  requiere_aprobacion_despacho?: boolean;
  despacho?: { modo: "CON_APROBACION" | "AUTONOMO_ALMACEN" | "AUTONOMO_USUARIO" | "SUPERVISOR" | "NO_APLICA" };
  /** Algún renglón pide observación (E-09): hace falta anotarla en el vale antes de confirmar. */
  pide_observacion?: boolean;
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
  tipo?: "EXCEDENTE" | "DESPACHO" | "TRASLADO";
  /** Nulo en un traslado. */
  trabajador_id: string | null;
  almacen_id: string;
  solicitada_por: PersonaApi;
  resuelta_por: PersonaApi | null;
  creado_en: string;
  resuelta_en: string | null;
  vence_en: string;
  /** La hora del servidor, para la cuenta regresiva sin fiarse del reloj del dispositivo. */
  servidor_ahora?: string;
  avisados?: number;
  renglones_resueltos?: { renglon: number; codigo: string; cantidad: number; decision: "APROBADO" | "RECHAZADO"; motivo: string | null }[] | null;
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
  despacho?: { modo: "APROBADO" | "PROPIO" | "AUTONOMO" | null; aprobo: PersonaApi | null } | null;
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
  firma_modo: "PANTALLA" | "SESION" | "PAPEL" | null;
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
  /** Solo en un vale cancelado: la cancelación que lo canceló (K-02). */
  cancelacion?: { id: string; folio: string; motivo: string | null; responsable: PersonaApi; creado_en: string } | null;
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

/** Un artículo de la dotación de un trabajador (`GET /api/trabajadores/{id}/dotacion`). */
export interface RenglonDotacionApi {
  articulo: { id: string; codigo: string; nombre: string; unidad: string; control: "PIEZA" | "CANTIDAD" };
  recomendada: number;
  entregada: number;
  falta: number;
}

/** Sin puesto del catálogo o con el puesto sin dotación, `renglones` va vacío. */
export interface DotacionApi {
  puesto: { id: string; nombre: string } | null;
  renglones: RenglonDotacionApi[];
}

/** Cuántos artículos de la dotación le faltan al trabajador, para la línea de la ficha. */
export function resumenDeDotacion(dotacion: DotacionApi | null): { faltan: number; total: number } | null {
  if (!dotacion || dotacion.renglones.length === 0) return null;
  return { faltan: dotacion.renglones.filter((r) => r.falta > 0).length, total: dotacion.renglones.length };
}
