// Formas de lo que devuelve la API de consulta. Fuente: backend/app/modulos/consulta/schemas.py,
// backend/app/modulos/catalogo/schemas.py (ficha de artículo) y backend/app/modulos/inspecciones/schemas.py.

export interface Ubicacion {
  /** ALMACEN, TRABAJADOR o VIRTUAL. */
  tipo: string;
  texto: string;
  almacen_id: string | null;
  almacen_clave: string | null;
  trabajador_id: string | null;
  numero_empleado: string | null;
  virtual: string | null;
}

// ------------------------------------------------------------------------------ escaneo

export interface ResumenTrabajador {
  numero_empleado: string;
  nombre: string;
  estado: string;
  estado_texto: string;
  vigente: boolean;
  motivo_no_vigente: string | null;
  puesto: string | null;
  area_obra: string | null;
  vigente_hasta: string | null;
  pendientes: number;
}

export interface ResumenArticulo {
  codigo: string;
  nombre: string;
  marca: string | null;
  categoria: string;
  control: string;
  retornable: boolean;
  unidad: string;
  activo: boolean;
  existencia_total: number;
}

export interface ResumenPieza {
  codigo: string;
  numero_serie: string | null;
  articulo_id: string;
  articulo: string;
  estado: string;
  estado_texto: string;
  inspeccion_vigente_hasta: string | null;
  inspeccion_vigente: boolean;
  ubicacion: Ubicacion | null;
}

export interface ResumenVale {
  folio: string;
  tipo: string;
  tipo_texto: string;
  estado: string;
  fecha: string;
  almacen_clave: string;
  trabajador: string | null;
  responsable: string;
}

export type Escaneo =
  | { tipo: "TRABAJADOR"; id: string; resumen: ResumenTrabajador }
  | { tipo: "ARTICULO"; id: string; resumen: ResumenArticulo }
  | { tipo: "PIEZA"; id: string; resumen: ResumenPieza }
  | { tipo: "VALE"; id: string; resumen: ResumenVale }
  | { tipo: "DESCONOCIDO"; id: null; resumen: { mensaje: string } };

// ----------------------------------------------------------------------------- búsqueda

export interface BusquedaArticulo {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  categoria: string;
  control: string;
  activo: boolean;
}

export interface BusquedaPieza {
  id: string;
  codigo: string;
  numero_serie: string | null;
  articulo_id: string;
  articulo: string;
  estado: string;
  estado_texto: string;
  ubicacion: string | null;
}

export interface BusquedaTrabajador {
  id: string;
  numero_empleado: string;
  nombre: string;
  estado: string;
  estado_texto: string;
}

interface Grupo<T> {
  elementos: T[];
  total: number;
}

export interface Busqueda {
  q: string;
  articulos: Grupo<BusquedaArticulo>;
  piezas: Grupo<BusquedaPieza>;
  trabajadores: Grupo<BusquedaTrabajador>;
  sin_resultados: boolean;
  mensaje: string | null;
}

// ------------------------------------------------------------------------ ficha de pieza

export interface ArticuloDePieza {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  modelo: string | null;
  talla: string | null;
  unidad: string;
  requiere_inspeccion: boolean;
  vigencia_inspeccion_dias: number | null;
}

export interface UltimaInspeccion {
  id: string;
  fecha: string;
  resultado: string;
  resultado_texto: string;
  vigente_hasta: string | null;
  observacion: string | null;
  usuario: string;
}

export type TipoHistorial = "MOVIMIENTO" | "INSPECCION" | "CAMBIO_ESTADO" | "AJUSTE_VIGENCIA";

export interface HechoHistorial {
  tipo: TipoHistorial;
  /** UTC; llega sin la `Z`, por eso se normaliza con `instanteUtc`. */
  fecha: string;
  titulo: string;
  detalle: string | null;
  usuario: string | null;
  vale_id: string | null;
  folio: string | null;
  tipo_vale: string | null;
  origen: string | null;
  destino: string | null;
  responsable: string | null;
  condicion: string | null;
  resultado: string | null;
  vigente_hasta: string | null;
  vigente_hasta_anterior: string | null;
  estado_anterior: string | null;
  estado_nuevo: string | null;
  observacion: string | null;
}

export interface FichaPieza {
  id: string;
  codigo: string;
  numero_serie: string | null;
  estado: string;
  estado_texto: string;
  articulo: ArticuloDePieza;
  inspeccion_vigente_hasta: string | null;
  inspeccion_vigente: boolean;
  ultima_inspeccion: UltimaInspeccion | null;
  ubicacion: Ubicacion | null;
  historial: HechoHistorial[];
}

// --------------------------------------------------------------------- ficha de artículo

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

export interface FichaArticulo {
  id: string;
  codigo: string;
  nombre: string;
  marca: string | null;
  modelo: string | null;
  categoria_id: string;
  categoria_nombre: string;
  control: string;
  retornable: boolean;
  talla: string | null;
  unidad: string;
  requiere_inspeccion: boolean;
  requiere_autorizacion: boolean;
  activo: boolean;
  motivo_inactivacion: string | null;
  /** Solo viene con `catalogo.costos`. */
  costo_unitario?: string | number | null;
  vigencia_inspeccion_dias: number | null;
  motivo_uso_especial: string | null;
  limite_cantidad: number | null;
  limite_periodo_dias: number | null;
  cantidad_aviso: number | null;
  tiene_movimientos: boolean;
  existencias: ExistenciaAlmacen[];
  en_posesion: Poseedor[];
}

// ------------------------------------------------------------------------- inspecciones

export const PUNTOS_INSPECCION = [
  { clave: "etiquetas", etiqueta: "Etiquetas legibles" },
  { clave: "costuras", etiqueta: "Costuras sin daño" },
  { clave: "cintas", etiqueta: "Cintas sin cortes ni desgaste" },
  { clave: "herrajes", etiqueta: "Herrajes sin golpes ni óxido" },
  { clave: "conectores", etiqueta: "Conectores y seguros funcionando" },
] as const;

export type ClavePunto = (typeof PUNTOS_INSPECCION)[number]["clave"];

// ----------------------------------------------------------------------- autorizaciones

export interface RenglonSolicitud {
  codigo: string;
  articulo_id: string | null;
  articulo: string | null;
  cantidad: number;
  limite: number | null;
  tiene: number | null;
  excedente: number | null;
  regla: string;
  mensaje: string | null;
  autorizable: boolean;
}

export type EstadoSolicitud = "PENDIENTE" | "APROBADA" | "RECHAZADA" | "VENCIDA" | "USADA";

export interface Solicitud {
  id: string;
  estado: EstadoSolicitud;
  almacen_id: string;
  trabajador: { id: string; nombre: string; numero_empleado: string };
  solicitada_por: { id: string; nombre: string };
  motivo: string;
  renglones: RenglonSolicitud[];
  excedente_total: number;
  creado_en: string;
  vence_en: string;
}

/** `GET /api/autorizaciones/{id}`: para saber cómo terminó una solicitud que dejó de estar pendiente. */
export interface EstadoAutorizacion {
  id: string;
  estado: EstadoSolicitud;
  resuelta_por: { id: string; nombre: string } | null;
}
