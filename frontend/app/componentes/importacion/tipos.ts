// Formas de la API de importación. Fuente: backend/app/modulos/importacion/schemas.py y
// docs/architecture/api-contracts.md ("Importación"). Son tipos de PRESENTACIÓN: la revisión de cada fila
// la hace el servidor; la interfaz muestra lo que responde.

export const CAMPOS = ["codigo", "nombre", "marca", "categoria", "cantidad", "almacen", "serie", "costo", "codigo_pieza", "unidad"] as const;
export type CampoImportacion = (typeof CAMPOS)[number];

/** Los dos modos de la importación (regla I-10): `ALTA` crea y suma; `REPOSICION` solo suma a lo que ya existe. */
export type ModoImportacion = "ALTA" | "REPOSICION";

/** Los datos que se leen en la reposición: el resto de las columnas se ignora (I-10). */
export const CAMPOS_REPOSICION: readonly CampoImportacion[] = ["codigo", "cantidad", "serie", "codigo_pieza"];

/**
 * EK-03: todo entra a Kepler, así que «almacén» ya no es una columna que se relacione. Si el archivo la trae, se
 * manda igual y el servidor la ignora con un aviso.
 */
export const CAMPOS_RELACIONABLES: readonly CampoImportacion[] = CAMPOS.filter((c) => c !== "almacen");

export function camposDelModo(modo: ModoImportacion): readonly CampoImportacion[] {
  return modo === "REPOSICION" ? CAMPOS_REPOSICION : CAMPOS;
}

/** Índice (desde 0) de la columna de cada dato; `null` si no viene. */
export type Columnas = Record<CampoImportacion, number | null>;

export interface Motivo {
  regla: string;
  campo: string | null;
  codigo: string;
  mensaje: string;
}

export interface CategoriaRef {
  id: string;
  nombre: string;
}
export interface AlmacenRef {
  id: string;
  clave: string;
  nombre: string;
}

/** Estado de una fila en la vista previa. `ERROR` solo viene en `filas_error`. */
export type EstadoFila = "NUEVO" | "EXISTENTE" | "UNIDO" | "ERROR";

export interface FilaValida {
  fila: number;
  estado: EstadoFila;
  codigo: string;
  /** El código lo asigna el servidor al confirmar; el que se ve es provisional. */
  codigo_generado?: boolean;
  nombre: string;
  marca: string | null;
  categoria: CategoriaRef | null;
  /** Solo en el alta, en artículos nuevos sin categoría en el archivo. Es una sugerencia: no se aplica sola (I-14). */
  categoria_sugerida?: CategoriaRef | null;
  motivo_sugerencia?: string | null;
  control: string;
  articulo_nuevo: boolean;
  cantidad: number;
  saldo_antes: number;
  saldo_despues: number;
  /** Las demás filas que se sumaron en esta (estado `UNIDO`). */
  unida_de?: number[];
  almacen: AlmacenRef;
  codigo_pieza: string | null;
  /** El código de la pieza lo asigna el servidor al confirmar; el que se ve es provisional. */
  codigo_pieza_generado?: boolean;
  numero_serie: string | null;
  /** La pieza no trae número de serie: entra igual y se registra después (aviso, no bloquea). */
  serie_pendiente?: boolean;
  /** Unidad del artículo: la del archivo en uno nuevo, la registrada en uno existente. */
  unidad?: string | null;
  costo?: string | null;
  avisos: string[];
}

export interface FilaError {
  fila: number;
  estado?: EstadoFila;
  datos: Record<string, string>;
  motivos: Motivo[];
}

export interface ArticuloNuevo {
  codigo: string;
  nombre: string;
  marca: string | null;
  categoria: CategoriaRef;
  control: string;
  filas: number;
  costo?: string | null;
}

/** Una fila que no es un artículo (dice SERVICIO): no se importa y no cuenta como error. */
export interface FilaExcluida {
  fila: number;
  nombre: string;
  motivo: string;
}

export interface CategoriaDesconocida {
  nombre: string;
  filas: number[];
}

export interface ResumenVistaPrevia {
  total: number;
  validas: number;
  con_error: number;
  vacias: number;
  articulos_nuevos: number;
  existentes: number;
  unidos: number;
  excluidas: number;
  /** Filas de artículo nuevo que esperan que se elija su categoría. */
  por_revisar: number;
  piezas: number;
  unidades: number;
  almacenes: number;
  /** Piezas que entrarían sin número de serie. */
  series_pendientes?: number;
}

export interface VistaPreviaApi {
  modo: ModoImportacion;
  columnas: Columnas;
  avisos: string[];
  /** La importación anterior con el mismo archivo (I-12); es un aviso, no un error. */
  archivo_repetido: { fecha: string } | null;
  resumen: ResumenVistaPrevia;
  filas_validas: FilaValida[];
  filas_error: FilaError[];
  filas_excluidas: FilaExcluida[];
  articulos_nuevos: ArticuloNuevo[];
  categorias_desconocidas: CategoriaDesconocida[];
}

/** Respuesta de `POST /api/importacion/archivo`. */
export interface ArchivoApi {
  hoja: string | null;
  encabezados: string[];
  columnas: Columnas;
  primera_fila: number;
  filas: string[][];
  vista_previa: VistaPreviaApi | null;
}

export interface ValeImportado {
  id: string;
  folio: string;
  almacen: AlmacenRef;
  renglones: number;
  piezas: number;
  unidades: number;
}

export interface PiezaCreada {
  id: string;
  codigo: string;
  codigo_generado: boolean;
  articulo: { id: string; codigo: string; nombre: string };
  numero_serie: string | null;
  serie_pendiente: boolean;
  almacen: AlmacenRef;
}

export interface ImportacionApi {
  modo: ModoImportacion;
  id_lote: string;
  repetida: boolean;
  resumen: {
    filas_importadas: number;
    filas_con_error: number;
    articulos_creados: number;
    existentes: number;
    unidos: number;
    excluidas: number;
    vales: number;
    piezas: number;
    unidades: number;
    series_pendientes?: number;
  };
  articulos_creados: { id: string; codigo: string; nombre: string; categoria: string; control: string }[];
  /** Todas las piezas que entraron, con su código definitivo (para imprimir sus etiquetas). */
  piezas_creadas?: PiezaCreada[];
  vales: ValeImportado[];
  filas_error: FilaError[];
  avisos: string[];
}

/** La tabla que se va a importar, ya separada en columnas (de lo pegado o de un `.xlsx`). */
export interface Tabla {
  origen: "pegado" | "archivo";
  /** Nombre del archivo, si se subió uno. */
  archivo?: string;
  /** Encabezados, o `null` si la tabla no los trae. */
  encabezados: string[] | null;
  /** Filas de datos, sin encabezados. */
  filas: string[][];
  /** Número que tiene la primera fila de datos en la hoja (2 si traía encabezados). */
  primeraFila: number;
}

/** Lo que se manda a la vista previa y a la confirmación. */
export interface OpcionesImportacion {
  categoriaPorDefectoId: string | null;
  mapaCategorias: Record<string, string>;
  /** `{número de fila: categoria_id}`: solo lo que la persona eligió o aceptó viendo la fila. */
  categoriaPorFila: Record<string, string>;
}
