// Cliente de «Trasladar con una lista» (FEAT-009). Fuente: docs/architecture/api-contracts.md, sección
// «Importación de traspasos». Son tipos de PRESENTACIÓN: la evaluación de cada fila la hace el servidor.

import { api, descargarArchivo } from "./cliente";
import { ErrorApi } from "./errores";

/** Un renglón se cuenta por artículo, o por pieza cuando el artículo se controla por pieza (TR-07). */
export const MAX_RENGLONES_TRASPASO = 500;

export type NivelFilaTraspaso = "VERDE" | "AMARILLO" | "ROJO";

export interface AlmacenRefTraspaso {
  id: string;
  clave: string;
  nombre: string;
}

export interface MotivoFilaTraspaso {
  regla: string;
  codigo: string;
  mensaje: string;
}

export interface FilaTraspasoApi {
  fila: number;
  codigo: string | null;
  articulo: string | null;
  pieza: { id: string; codigo: string; numero_serie: string | null } | null;
  cantidad: number;
  disponible_en_origen: number;
  nivel: NivelFilaTraspaso;
  unida_de?: number[];
  motivos: MotivoFilaTraspaso[];
}

export interface VistaPreviaTraspasoApi {
  origen: AlmacenRefTraspaso;
  destino: AlmacenRefTraspaso;
  ruta: { habitual: boolean; nivel: NivelFilaTraspaso; pide_observacion: boolean; mensaje: string };
  archivo_repetido: { fecha: string } | null;
  resumen: { total: number; ok: number; avisos: number; errores: number; unidades: number; piezas: number; excedido: boolean };
  filas: FilaTraspasoApi[];
  avisos: string[];
}

/** Índice (desde 0) de la columna de cada dato; `null` si no viene. */
export interface ColumnasTraspaso {
  codigo: number | null;
  /** Solo de ayuda (TR-13): el servidor la compara con el catálogo y avisa si no coincide. */
  nombre: number | null;
  cantidad: number | null;
  codigo_pieza: number | null;
  serie: number | null;
}

export const COLUMNAS_TRASPASO_VACIAS: ColumnasTraspaso = { codigo: null, nombre: null, cantidad: null, codigo_pieza: null, serie: null };

export interface ArchivoTraspasoApi {
  hoja: string | null;
  encabezados: string[];
  columnas: Partial<ColumnasTraspaso>;
  primera_fila: number;
  filas: string[][];
  vista_previa: VistaPreviaTraspasoApi | null;
}

export interface CuerpoVistaPreviaTraspaso {
  filas: string[][];
  columnas: ColumnasTraspaso;
  primera_fila: number;
  destino_almacen_id: string;
  almacen_id: string | null;
}

export interface CuerpoConfirmarTraspaso extends CuerpoVistaPreviaTraspaso {
  id_lote: string;
  observacion: string | null;
  dejar_fuera_errores: boolean;
  confirmar_repetido: boolean;
}

export interface TraspasoImportadoApi {
  id_lote: string;
  repetida: boolean;
  vale: {
    id: string;
    folio: string;
    token: string;
    estado: string;
    creado_en?: string;
    origen: AlmacenRefTraspaso;
    destino: AlmacenRefTraspaso;
    renglones: number;
    piezas: number;
    unidades: number;
  };
  resumen: { filas_importadas: number; filas_dejadas_fuera: number; unidades: number; piezas: number };
  filas_dejadas_fuera: { fila: number; motivos: MotivoFilaTraspaso[] }[];
  avisos: string[];
}

const RUTA = "/importacion/traspasos";

export function descargarPlantillaTraspaso(): Promise<void> {
  return descargarArchivo(`${RUTA}/plantilla`, undefined, "plantilla-traspaso.xlsx");
}

export function leerArchivoTraspaso(archivo: File, destinoId: string, almacenId: string | null, signal?: AbortSignal) {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo);
  cuerpo.append("destino_almacen_id", destinoId);
  if (almacenId) cuerpo.append("almacen_id", almacenId);
  return api<ArchivoTraspasoApi>(`${RUTA}/archivo`, { metodo: "POST", cuerpo, signal });
}

export function vistaPreviaTraspaso(cuerpo: CuerpoVistaPreviaTraspaso, signal?: AbortSignal) {
  return api<VistaPreviaTraspasoApi>(`${RUTA}/vista-previa`, { metodo: "POST", cuerpo, signal });
}

export function confirmarTraspasoPorLista(cuerpo: CuerpoConfirmarTraspaso) {
  return api<TraspasoImportadoApi>(RUTA, { metodo: "POST", cuerpo });
}

/** El servidor puede no tener todavía estas rutas (se construyen en paralelo): se dice con claridad. */
export function mensajeTraspasoLista(causa: unknown, fallback: string): string {
  if (causa instanceof ErrorApi && (causa.status === 404 || causa.status === 405)) {
    return "Esta función todavía no está disponible en el servidor. Inténtalo más tarde o traslada escaneando.";
  }
  return causa instanceof Error && causa.message ? causa.message : fallback;
}
