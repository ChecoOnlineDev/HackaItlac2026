import {
  BriefcaseBusiness,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  FileBarChart,
  FileClock,
  FolderTree,
  History,
  Inbox,
  KeyRound,
  MapPinned,
  Package,
  PackageCheck,
  PackagePlus,
  Printer,
  ReceiptText,
  Search,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Undo2,
  UserCog,
  UserPlus,
  UserRoundCog,
  Users,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

import type { Permiso } from "~/api/tipos";

/**
 * El menú SE ARMA DE LOS PERMISOS de la sesión, nunca del nombre del rol.
 * Un elemento sin `permisosAlguno` lo ve cualquiera con sesión.
 *
 * Cada elemento es una pantalla (con su URL de siempre). Las pantallas se juntan en `seccion`: en el menú
 * cada sección es UNA entrada, y sus pantallas son las pestañas de la barra compartida (FEAT-011, AC-35).
 */
export interface ElementoMenu {
  id: string;
  titulo: string;
  /** Texto corto de la pestaña dentro de su sección (si no, `titulo`). */
  pestana?: string;
  /** Cómo se llama la entrada del menú cuando es la única pantalla visible de su sección (si no, el de la sección). */
  tituloSolo?: string;
  ruta: string;
  icono: LucideIcon;
  /** Basta con tener uno. Sin lista: todos. */
  permisosAlguno?: readonly Permiso[];
  /** Sección del menú a la que pertenece (id de `SECCIONES`); `null`: no está en el menú (se llega por un enlace). */
  seccion: string | null;
  /**
   * Dónde aparece en el inicio:
   * - `flujo`: botón grande de una operación del almacén.
   * - `siempre`: botón del inicio de cualquiera que tenga el permiso.
   * - `gestion`: solo en el inicio de quien no opera un almacén (Compras, RH...); los demás lo encuentran en el menú.
   */
  inicio: "flujo" | "siempre" | "gestion";
  /** Cuenta que muestra el botón (traspasos por recibir, solicitudes por autorizar). */
  contador?: "porRecibir" | "porAutorizar" | "porComprar";
}

export const MENU: readonly ElementoMenu[] = [
  { id: "entregar", titulo: "Entregar", ruta: "/entregar", icono: PackageCheck, permisosAlguno: ["entregas.crear"], seccion: "operacion", inicio: "flujo" },
  { id: "devolver", titulo: "Devolver", ruta: "/devolver", icono: Undo2, permisosAlguno: ["devoluciones.crear"], seccion: "operacion", inicio: "flujo" },
  { id: "consultar", titulo: "Consultar", tituloSolo: "Consultar", ruta: "/consultar", icono: Search, seccion: "operacion", inicio: "flujo" },
  { id: "trasladar", titulo: "Enviar traspasos", pestana: "Enviar", tituloSolo: "Enviar traspasos", ruta: "/trasladar", icono: Truck, permisosAlguno: ["traspasos.operar"], seccion: "traspasos", inicio: "flujo" },
  { id: "recibir", titulo: "Recibir traspasos", pestana: "Recibir", tituloSolo: "Recibir traspasos", ruta: "/recibir", icono: Inbox, permisosAlguno: ["traspasos.recibir"], seccion: "traspasos", inicio: "flujo", contador: "porRecibir" },
  { id: "inventario", titulo: "Existencias", ruta: "/inventario", icono: Boxes, permisosAlguno: ["inventario.ver"], seccion: "inventario", inicio: "gestion" },
  { id: "rep-movimientos", titulo: "Bitácora", ruta: "/reportes/movimientos", icono: FileClock, permisosAlguno: ["bitacora.ver", "reportes.movimientos"], seccion: "inventario", inicio: "gestion" },
  { id: "seguimiento", titulo: "Piezas y resguardos", ruta: "/seguimiento", icono: MapPinned, permisosAlguno: ["reportes.existencias", "resguardo.ver"], seccion: "inventario", inicio: "siempre" },
  { id: "entrada", titulo: "Dar entrada", ruta: "/entrada", icono: PackagePlus, permisosAlguno: ["inventario.entradas", "inventario.importar"], seccion: "inventario", inicio: "gestion" },
  { id: "articulos", titulo: "Artículos", ruta: "/catalogo/articulos", icono: Package, permisosAlguno: ["catalogo.administrar"], seccion: "catalogo", inicio: "gestion" },
  { id: "categorias", titulo: "Categorías", ruta: "/catalogo/categorias", icono: FolderTree, permisosAlguno: ["catalogo.administrar"], seccion: "catalogo", inicio: "gestion" },
  { id: "puestos", titulo: "Puestos", ruta: "/puestos", icono: BriefcaseBusiness, permisosAlguno: ["catalogo.administrar"], seccion: "catalogo", inicio: "gestion" },
  { id: "etiquetas", titulo: "Etiquetas", tituloSolo: "Etiquetas", ruta: "/etiquetas", icono: Printer, permisosAlguno: ["etiquetas.imprimir"], seccion: "catalogo", inicio: "gestion" },
  { id: "trabajadores", titulo: "Trabajadores", ruta: "/trabajadores", icono: Users, permisosAlguno: ["trabajadores.ver"], seccion: "trabajadores", inicio: "gestion" },
  { id: "alta-trabajador", titulo: "Alta de trabajador", ruta: "/trabajadores/nuevo", icono: UserPlus, permisosAlguno: ["trabajadores.administrar"], seccion: "trabajadores", inicio: "gestion" },
  { id: "pedir-compra", titulo: "Pedir una compra urgente", ruta: "/compras/nueva", icono: ShoppingCart, permisosAlguno: ["compras.solicitar"], seccion: "compras", inicio: "gestion" },
  { id: "compras-mias", titulo: "Mis solicitudes", ruta: "/compras/mias", icono: ReceiptText, permisosAlguno: ["compras.solicitar"], seccion: "compras", inicio: "gestion" },
  { id: "solicitudes-compra", titulo: "Cola de Compras", ruta: "/compras", icono: ClipboardList, permisosAlguno: ["compras.atender"], seccion: "compras", inicio: "gestion", contador: "porComprar" },
  { id: "autorizaciones", titulo: "Autorizaciones", ruta: "/autorizaciones", icono: ShieldCheck, permisosAlguno: ["autorizaciones.resolver"], seccion: "supervision", inicio: "siempre", contador: "porAutorizar" },
  { id: "rep-existencias", titulo: "Reporte de existencias", pestana: "Existencias", tituloSolo: "Reporte de existencias", ruta: "/reportes/existencias", icono: ClipboardList, permisosAlguno: ["reportes.existencias"], seccion: "supervision", inicio: "gestion" },
  { id: "rep-adeudos", titulo: "Reporte de adeudos", pestana: "Adeudos", tituloSolo: "Reporte de adeudos", ruta: "/reportes/adeudos", icono: FileBarChart, permisosAlguno: ["reportes.adeudos"], seccion: "supervision", inicio: "gestion" },
  { id: "rep-consumo", titulo: "Reporte de consumo", pestana: "Consumo", tituloSolo: "Reporte de consumo", ruta: "/reportes/consumo", icono: FileBarChart, permisosAlguno: ["reportes.consumo"], seccion: "supervision", inicio: "gestion" },
  { id: "usuarios", titulo: "Usuarios", ruta: "/usuarios", icono: UserRoundCog, permisosAlguno: ["acceso.usuarios"], seccion: "personas", inicio: "gestion" },
  { id: "roles", titulo: "Roles y permisos", ruta: "/roles", icono: KeyRound, permisosAlguno: ["acceso.roles"], seccion: "personas", inicio: "gestion" },
  { id: "personal", titulo: "Personal por almacén", ruta: "/personal", icono: UserCog, permisosAlguno: ["almacenes.asignar_personal"], seccion: "personas", inicio: "gestion" },
  { id: "almacenes", titulo: "Almacenes", ruta: "/almacenes", icono: Warehouse, permisosAlguno: ["almacenes.administrar"], seccion: "almacenes", inicio: "gestion" },
  // «Mis movimientos de hoy» ya no está en el menú: se llega desde Consultar y desde la Bitácora («Solo los míos»).
  { id: "mis-movimientos", titulo: "Mis movimientos de hoy", ruta: "/mis-movimientos", icono: History, permisosAlguno: ["vales.ver"], seccion: null, inicio: "gestion" },
];

/**
 * Las secciones del menú, en orden. «Inicio» no es una sección: es una entrada fija.
 * - `grupo`: la entrada se pliega y muestra sus pantallas como opciones (solo «Operación del día»).
 * - Las demás son un enlace; con dos o más pantallas visibles, estas son las pestañas de una barra compartida.
 */
export interface SeccionMenu {
  /** Identificador estable (sirve para recordar si está abierta y para `aria-controls`). */
  id: string;
  titulo: string;
  icono: LucideIcon;
  /** Se pinta como grupo plegable con sus pantallas, en lugar de enlace con pestañas. */
  grupo: boolean;
}

export const SECCIONES: readonly SeccionMenu[] = [
  { id: "operacion", titulo: "Operación del día", icono: ClipboardCheck, grupo: true },
  { id: "traspasos", titulo: "Traspasos", icono: Truck, grupo: false },
  { id: "inventario", titulo: "Inventario", icono: Boxes, grupo: false },
  { id: "catalogo", titulo: "Catálogo", icono: FolderTree, grupo: false },
  { id: "trabajadores", titulo: "Trabajadores", icono: Users, grupo: false },
  { id: "compras", titulo: "Compras", icono: ShoppingCart, grupo: false },
  { id: "supervision", titulo: "Supervisión", icono: ShieldCheck, grupo: false },
  { id: "personas", titulo: "Personas y accesos", icono: KeyRound, grupo: false },
  { id: "almacenes", titulo: "Almacenes", icono: Warehouse, grupo: false },
];

export function menuPermitido(puedeAlguno: (permisos: readonly Permiso[]) => boolean): ElementoMenu[] {
  return MENU.filter((e) => !e.permisosAlguno || puedeAlguno(e.permisosAlguno));
}

const sinBarraFinal = (pathname: string) => (pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname);

/**
 * Qué pantalla del menú corresponde a la ruta actual. Cuenta también la subruta (`/trabajadores/<id>` marca
 * "Trabajadores"); si varias coinciden gana la más específica (`/trabajadores/nuevo` marca "Alta de trabajador").
 * "Inicio" (`/`) no está en la lista: se marca solo en `/` exacto.
 */
export function idActivo(elementos: readonly ElementoMenu[], pathname: string): string | null {
  const ruta = sinBarraFinal(pathname);
  let mejor: ElementoMenu | null = null;
  for (const e of elementos) {
    if (ruta === e.ruta || ruta.startsWith(`${e.ruta}/`)) {
      if (!mejor || e.ruta.length > mejor.ruta.length) mejor = e;
    }
  }
  return mejor?.id ?? null;
}

/** Una entrada del menú ya armada con lo que permiten los permisos. */
export interface EntradaMenu {
  id: string;
  titulo: string;
  icono: LucideIcon;
  /** A dónde lleva: la primera pantalla visible de la sección. */
  ruta: string;
  /** `true`: se pinta como grupo plegable con sus `elementos` como opciones. */
  grupo: boolean;
  /** Pantallas visibles de la sección (pestañas o, en un grupo, opciones). */
  elementos: ElementoMenu[];
  /** Las cuentas que suma la entrada (traspasos por recibir, etc.). */
  contadores: NonNullable<ElementoMenu["contador"]>[];
}

/**
 * Arma el menú: una entrada por sección con al menos una pantalla visible (una sección sin pantallas visibles no se pinta).
 * Una sección con una sola pantalla visible es una entrada simple que lleva directo a ella.
 */
export function armarMenu(permitidos: readonly ElementoMenu[]): EntradaMenu[] {
  const entradas: EntradaMenu[] = [];
  for (const s of SECCIONES) {
    const elementos = permitidos.filter((e) => e.seccion === s.id);
    if (elementos.length === 0) continue;
    const unico = elementos.length === 1 ? elementos[0] : null;
    entradas.push({
      id: s.id,
      titulo: unico ? (unico.tituloSolo ?? s.titulo) : s.titulo,
      icono: s.icono,
      ruta: elementos[0].ruta,
      grupo: s.grupo && elementos.length > 1,
      elementos,
      contadores: elementos.flatMap((e) => (e.contador ? [e.contador] : [])),
    });
  }
  return entradas;
}

/** La entrada del menú que contiene la pantalla activa, o null (en Inicio o en una ruta sin entrada). */
export function idEntradaActiva(entradas: readonly EntradaMenu[], activoId: string | null): string | null {
  if (!activoId) return null;
  return entradas.find((e) => e.elementos.some((el) => el.id === activoId))?.id ?? null;
}

/**
 * Las pestañas de la barra compartida para una ruta. La barra sale solo en la pantalla misma de una pestaña
 * (no en sus detalles) y solo si la sección tiene dos o más pestañas visibles. Cada URL sigue siendo la de siempre.
 */
export function pestanasDe(
  permitidos: readonly ElementoMenu[],
  pathname: string,
): { seccion: SeccionMenu; pestanas: ElementoMenu[]; activa: string | null } | null {
  const ruta = sinBarraFinal(pathname);
  const pantalla = MENU.find((e) => e.seccion && e.ruta === ruta);
  if (!pantalla) return null;
  const seccion = SECCIONES.find((s) => s.id === pantalla.seccion);
  if (!seccion || seccion.grupo) return null;
  const pestanas = permitidos.filter((e) => e.seccion === seccion.id);
  if (pestanas.length < 2) return null;
  return { seccion, pestanas, activa: pestanas.some((p) => p.id === pantalla.id) ? pantalla.id : null };
}

/** Botones del inicio según los permisos. */
export function elementosDeInicio(permitidos: readonly ElementoMenu[]): ElementoMenu[] {
  const operaAlmacen = permitidos.some((e) => e.inicio === "flujo" && e.id !== "consultar");
  return permitidos.filter(
    (e) => e.inicio === "flujo" || e.inicio === "siempre" || (e.inicio === "gestion" && !operaAlmacen),
  );
}
