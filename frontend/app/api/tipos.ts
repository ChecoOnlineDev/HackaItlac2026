// Tipos de lo que devuelve la API. Fuente: docs/architecture/api-contracts.md.
// Al agregar un endpoint nuevo, sus tipos van aquí o junto a la pantalla que lo usa.

/** Catálogo fijo de permisos (docs/product/reglas-de-negocio.md, sección 8). */
export const PERMISOS = [
  "acceso.administrar",
  "trabajadores.ver",
  "trabajadores.ver_datos_personales",
  "trabajadores.administrar",
  "trabajadores.iniciar_baja",
  "catalogo.ver",
  "catalogo.administrar",
  "catalogo.costos",
  "inventario.ver",
  "inventario.entradas",
  "entregas.crear",
  "devoluciones.crear",
  "traspasos.operar",
  "no_adeudo.emitir",
  "vales.ver",
  "vales.cancelar",
  "vales.cancelar_todos",
  "autorizaciones.resolver",
  "piezas.inspeccionar",
  "piezas.ajustar_vigencia",
  "reportes.existencias",
  "reportes.movimientos",
  "reportes.adeudos",
  "reportes.consumo",
  "almacenes.todos",
  "almacenes.asignar_personal",
  "almacenes.administrar",
  "etiquetas.imprimir",
] as const;

export type Permiso = (typeof PERMISOS)[number];

export interface UsuarioSesion {
  id: string;
  nombre: string;
  usuario: string;
}

export interface RolSesion {
  id: string;
  nombre: string;
}

export interface AlmacenSesion {
  id: string;
  clave: string;
  nombre: string;
}

/** Respuesta de `GET /api/sesion` y `POST /api/sesion`. */
export interface Sesion {
  usuario: UsuarioSesion;
  rol: RolSesion;
  /** Es null para quien opera todos los almacenes (`almacenes.todos`) o no opera ninguno. */
  almacen: AlmacenSesion | null;
  /** Claves de permiso. La interfaz arma menús y botones con esto, nunca con el nombre del rol. */
  permisos: string[];
}

/** Lista paginada estándar: `{elementos, total}`. */
export interface Pagina<T> {
  elementos: T[];
  total: number;
}
