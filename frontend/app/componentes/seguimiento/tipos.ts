// Tipos del seguimiento de piezas (C-13). Fuente: backend/app/modulos/consulta/schemas_seguimiento.py
// y docs/architecture/api-contracts.md. Nada de esto trae costos, CURP ni NSS.

export type TipoUbicacion = "ALMACEN" | "TRABAJADOR" | "TRANSITO" | "BAJA" | "OTRA" | "NINGUNA";

export interface DondeEsta {
  tipo: TipoUbicacion;
  /** Ya viene en español llano: "En resguardo de Juan Pérez", "En Kepler", "En tránsito a Contratistas". */
  texto: string;
  almacen: { id: string; clave: string; nombre: string } | null;
  trabajador: { id: string; numero_empleado: string; nombre: string } | null;
}

export interface PiezaSeguimiento {
  id: string;
  codigo: string;
  numero_serie: string | null;
  serie_pendiente?: boolean;
  articulo: { id: string; codigo: string; nombre: string; marca: string | null };
  estado: string;
  estado_texto: string;
  inspeccion_vigente: boolean;
  inspeccion_vigente_hasta: string | null;
  ubicacion: DondeEsta;
  /** Desde cuándo está ahí (UTC). */
  desde: string | null;
  /** Null si el vale es de un almacén fuera del alcance del usuario. */
  vale: { id: string; folio: string } | null;
}

export interface ResumenSeguimiento {
  total: number;
  en_almacen: number;
  en_resguardo: number;
  en_transito: number;
  no_aptas: number;
}

export interface PaginaSeguimiento {
  elementos: PiezaSeguimiento[];
  total: number;
  sin_registros: boolean;
  mensaje: string | null;
  resumen: ResumenSeguimiento;
}

export const TAMANO_SEGUIMIENTO = 20;

export const OPCIONES_ESTADO = [
  { valor: "APTO", texto: "Apta" },
  { valor: "NO_APTO", texto: "No apta" },
  { valor: "EN_MANTENIMIENTO", texto: "En mantenimiento" },
  { valor: "EN_CALIBRACION", texto: "En calibración" },
  { valor: "BAJA", texto: "De baja" },
];

export const OPCIONES_UBICACION = [
  { valor: "ALMACEN", texto: "En un almacén" },
  { valor: "TRABAJADOR", texto: "En resguardo de un trabajador" },
  { valor: "TRANSITO", texto: "En tránsito" },
  { valor: "BAJA", texto: "De baja" },
];
