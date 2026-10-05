// Formas de la API de importación. Fuente: backend/app/modulos/importacion/schemas.py y
// docs/architecture/api-contracts.md ("Importación"). Son tipos de PRESENTACIÓN: la revisión de cada fila
// la hace el servidor; la interfaz muestra lo que responde.

export const CAMPOS = ["codigo", "nombre", "marca", "categoria", "cantidad", "almacen", "serie", "costo", "codigo_pieza"] as const;
export type CampoImportacion = (typeof CAMPOS)[number];

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

export interface FilaValida {
  fila: number;
  codigo: string;
  nombre: string;
  marca: string | null;
  categoria: CategoriaRef | null;
  control: string;
  articulo_nuevo: boolean;
  cantidad: number;
  almacen: AlmacenRef;
  codigo_pieza: string | null;
  numero_serie: string | null;
  costo?: string | null;
  avisos: string[];
}

export interface FilaError {
  fila: number;
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
  piezas: number;
  unidades: number;
  almacenes: number;
}

export interface VistaPreviaApi {
  columnas: Columnas;
  avisos: string[];
  resumen: ResumenVistaPrevia;
  filas_validas: FilaValida[];
  filas_error: FilaError[];
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

export interface ImportacionApi {
  id_lote: string;
  repetida: boolean;
  resumen: {
    filas_importadas: number;
    filas_con_error: number;
    articulos_creados: number;
    vales: number;
    piezas: number;
    unidades: number;
  };
  articulos_creados: { id: string; codigo: string; nombre: string; categoria: string; control: string }[];
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
  almacenPorDefecto: string | null;
}
