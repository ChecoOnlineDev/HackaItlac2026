// Formas de lo que devuelve la API de trabajadores (backend/app/modulos/trabajadores/schemas.py).

export type Situacion = "SIN_PENDIENTES" | "CON_PENDIENTES" | "NO_ADEUDO_EMITIDO";

export interface Vigencia {
  vigente: boolean;
  motivo: string | null;
  regla: string;
}

export interface Pendiente {
  articulo_id: string;
  articulo: string;
  control: string;
  pieza_id: string | null;
  codigo: string;
  numero_serie: string | null;
  cantidad: number;
  entregado_en: string | null;
  vale_id: string | null;
  folio: string | null;
  almacen_id: string | null;
  almacen_clave: string | null;
  almacen: string | null;
  de_periodo_anterior: boolean;
}

export interface ElementoLista {
  id: string;
  numero_empleado: string;
  nombre: string;
  estado: string;
  estado_texto: string;
  puesto: string | null;
  area_obra: string | null;
  periodo_inicio: string | null;
  periodo_fin: string | null;
  vigencia: Vigencia;
  situacion: Situacion;
  situacion_texto: string;
  tiene_foto: boolean;
}

export interface Periodo {
  id: string;
  puesto: string | null;
  area_obra: string | null;
  referencia: string | null;
  inicio: string;
  fin: string;
  creado_en: string;
}

export interface Ficha {
  id: string;
  numero_empleado: string;
  nombre: string;
  estado: string;
  estado_texto: string;
  puesto: string | null;
  area_obra: string | null;
  vigencia: Vigencia;
  tiene_foto: boolean;
  foto_url: string | null;
  resguardo: Pendiente[];
  pendientes: { total: number; de_periodos_anteriores: number; regla: string | null };
  periodo: Periodo | null;
  situacion: Situacion;
  situacion_texto: string;
  tallas: Record<string, string> | null;
  codigos: string[];
  /** Solo existen con `trabajadores.ver_datos_personales`. */
  curp?: string | null;
  nss?: string | null;
}

export interface RespuestaBaja {
  id: string;
  estado: string;
  estado_texto: string;
  pendientes: Pendiente[];
  puede_emitir_no_adeudo: boolean;
  reglas: string[];
}

export interface CodigoLigado {
  codigo: string;
  tipo: string;
  generado: boolean;
}

export interface FotoRespuesta {
  tiene_foto: boolean;
  foto_url: string | null;
}
