// Tipos de los reportes. Fuente: backend/app/modulos/consulta/schemas.py y docs/architecture/api-contracts.md.
// Ningún reporte trae costos (RG-12).

/** Respuesta de un reporte: lista paginada con el aviso de "sin registros". */
export interface PaginaReporte<T> {
  elementos: T[];
  total: number;
  sin_registros: boolean;
  mensaje: string | null;
}

export interface ExistenciaReporte {
  almacen_id: string;
  almacen_clave: string;
  almacen: string;
  articulo_id: string;
  codigo: string;
  articulo: string;
  categoria: string;
  unidad: string;
  activo: boolean;
  cantidad: number;
  disponible: number;
}

export interface MovimientoReporte {
  id: string;
  fecha: string;
  vale_id: string;
  folio: string;
  tipo: string;
  tipo_texto: string;
  articulo_id: string;
  codigo_articulo: string;
  articulo: string;
  pieza: string | null;
  cantidad: number;
  origen: string;
  destino: string;
  responsable: string;
  trabajador: string | null;
  autorizado_por: string | null;
  motivo: string | null;
  saldo_origen: number | null;
  saldo_destino: number | null;
}

export interface AdeudoReporte {
  trabajador_id: string;
  numero_empleado: string;
  trabajador: string;
  estado: string;
  estado_texto: string;
  vigente: boolean;
  motivo_no_vigente: string | null;
  articulo_id: string;
  codigo: string;
  articulo: string;
  numero_serie: string | null;
  cantidad: number;
  desde: string | null;
  folio: string | null;
  almacen_clave: string | null;
  almacen: string | null;
}

export interface ConsumoTrabajador {
  trabajador_id: string | null;
  numero_empleado: string | null;
  trabajador: string;
  cantidad: number;
}

export interface ConsumoReporte {
  articulo_id: string;
  codigo: string;
  articulo: string;
  categoria: string;
  unidad: string;
  total: number;
  trabajadores: ConsumoTrabajador[];
}

/** Opciones del filtro "Tipo de movimiento". El texto es el que usa el servidor en el CSV. */
export const TIPOS_DE_MOVIMIENTO: { valor: string; texto: string }[] = [
  { valor: "ENTREGA", texto: "Entrega" },
  { valor: "DEVOLUCION", texto: "Devolución" },
  { valor: "TRASPASO", texto: "Traspaso" },
  { valor: "RECEPCION", texto: "Recepción" },
  { valor: "ENTRADA", texto: "Entrada" },
  { valor: "NO_ADEUDO", texto: "No adeudo" },
  { valor: "CANCELACION", texto: "Cancelación" },
];

export const TAMANO_REPORTE = 20;

/** Un filtro activo, que se muestra como chip y se quita con un toque. */
export interface FiltroActivo {
  clave: string;
  texto: string;
}

/**
 * Las fechas de la base son UTC. Si el servidor las manda sin la `Z` final, el navegador las
 * tomaría como hora local y se mostrarían corridas; aquí se aclara que son UTC.
 */
export function comoUtc(iso: string): string {
  return /(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
}

/** "pieza" -> "piezas", "par" -> "pares"; con 1 queda igual. */
export function unidadConNumero(unidad: string, n: number): string {
  if (n === 1 || !unidad) return unidad;
  return /[aeiouáéíóú]$/i.test(unidad) ? `${unidad}s` : `${unidad}es`;
}
