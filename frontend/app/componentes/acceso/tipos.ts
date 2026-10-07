/** Tipos de los endpoints de usuarios, roles y permisos (docs/architecture/api-contracts.md). */

export interface PermisoInfo {
  clave: string;
  descripcion: string;
  modulo: string;
  es_de_informacion: boolean;
  mvp: boolean;
  llega_con: string;
  /** Permisos de ver que este necesita. */
  requiere: string[];
}

export interface RolAcceso {
  id: string;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
  protegido: boolean;
  inicial: boolean;
  total_usuarios: number;
  total_permisos: number;
  permisos: string[];
}

export interface UsuarioAcceso {
  id: string;
  nombre: string;
  usuario: string;
  rol: { id: string; nombre: string };
  almacen: { id: string; clave: string; nombre: string } | null;
  activo: boolean;
  tiene_pin: boolean;
  creado_en: string;
}

export interface AlmacenAcceso {
  id: string;
  clave: string;
  nombre: string;
  estado: string;
}

export const TAMANO_PAGINA_USUARIOS = 20;

/** Los permisos que deciden qué pide el formulario de un usuario. */
export const PERMISO_TODOS_LOS_ALMACENES = "almacenes.todos";
export const PERMISO_AUTORIZA = "autorizaciones.resolver";
export const PERMISO_ADMINISTRAR = "acceso.administrar";

/** Cómo se agrupan los módulos del catálogo en la matriz, con nombres de persona. */
const GRUPOS: { id: string; titulo: string; modulos: string[] }[] = [
  { id: "operacion", titulo: "Operación del almacén", modulos: ["entregas", "devoluciones", "traspasos", "no_adeudo"] },
  { id: "vales", titulo: "Vales", modulos: ["vales"] },
  { id: "autorizaciones", titulo: "Autorizaciones", modulos: ["autorizaciones"] },
  { id: "piezas", titulo: "Piezas", modulos: ["piezas"] },
  { id: "trabajadores", titulo: "Trabajadores", modulos: ["trabajadores"] },
  { id: "catalogo", titulo: "Catálogo", modulos: ["catalogo"] },
  { id: "inventario", titulo: "Inventario", modulos: ["inventario"] },
  { id: "reportes", titulo: "Reportes", modulos: ["reportes"] },
  { id: "almacenes", titulo: "Almacenes", modulos: ["almacenes"] },
  { id: "etiquetas", titulo: "Etiquetas", modulos: ["etiquetas"] },
  { id: "acceso", titulo: "Acceso", modulos: ["acceso"] },
  { id: "otros", titulo: "Otros", modulos: ["revision", "tablero"] },
];

export interface GrupoPermisos {
  id: string;
  titulo: string;
  permisos: PermisoInfo[];
}

/** Agrupa el catálogo por módulo en el orden de la pantalla; no deja grupos vacíos. */
export function agruparPermisos(catalogo: readonly PermisoInfo[]): GrupoPermisos[] {
  const conocidos = new Set(GRUPOS.flatMap((g) => g.modulos));
  const grupos = GRUPOS.map((g) => ({
    id: g.id,
    titulo: g.titulo,
    permisos: catalogo.filter((p) => g.modulos.includes(p.modulo)),
  }));
  const sueltos = catalogo.filter((p) => !conocidos.has(p.modulo));
  if (sueltos.length > 0) {
    const otros = grupos.find((g) => g.id === "otros");
    if (otros) otros.permisos.push(...sueltos);
  }
  return grupos.filter((g) => g.permisos.length > 0);
}

/** Lo que un permiso de información deja ver, en palabras de persona. */
export const AVISO_RESERVADO: Record<string, string> = {
  "catalogo.costos": "Quien lo tenga verá y podrá capturar los costos de artículos y piezas.",
  "trabajadores.ver_datos_personales": "Quien lo tenga verá la CURP y el NSS de los trabajadores.",
  "reportes.valor_inventario": "Quien lo tenga verá cuánto vale el inventario.",
};

/** Lo que deja ver un permiso de información, en pocas palabras, para nombrarlo en la confirmación de guardar. */
export const FRASE_RESERVADO: Record<string, string> = {
  "catalogo.costos": "ver costos",
  "trabajadores.ver_datos_personales": "ver CURP y NSS (datos personales)",
  "reportes.valor_inventario": "ver el valor del inventario",
};

export function textoPermisos(n: number): string {
  return n === 1 ? "1 permiso" : `${n} permisos`;
}

export function textoUsuarios(n: number): string {
  return n === 0 ? "Sin usuarios" : n === 1 ? "1 usuario" : `${n} usuarios`;
}
