import {
  BriefcaseBusiness,
  Boxes,
  ClipboardList,
  FolderTree,
  History,
  Inbox,
  KeyRound,
  MapPinned,
  UserRoundCog,
  PackageCheck,
  PackagePlus,
  Package,
  Printer,
  ReceiptText,
  Search,
  ShoppingCart,
  UserCog,
  ShieldCheck,
  Truck,
  Undo2,
  Upload,
  UserPlus,
  Users,
  FileBarChart,
  type LucideIcon,
} from "lucide-react";

import type { Permiso } from "~/api/tipos";

/**
 * El menú SE ARMA DE LOS PERMISOS de la sesión, nunca del nombre del rol.
 * Un elemento sin `permisosAlguno` lo ve cualquiera con sesión.
 */
export interface ElementoMenu {
  id: string;
  titulo: string;
  ruta: string;
  icono: LucideIcon;
  /** Basta con tener uno. Sin lista: todos. */
  permisosAlguno?: readonly Permiso[];
  grupo: string;
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
  { id: "entregar", titulo: "Entregar", ruta: "/entregar", icono: PackageCheck, permisosAlguno: ["entregas.crear"], grupo: "Operación", inicio: "flujo" },
  { id: "devolver", titulo: "Devolver", ruta: "/devolver", icono: Undo2, permisosAlguno: ["devoluciones.crear"], grupo: "Operación", inicio: "flujo" },
  { id: "trasladar", titulo: "Trasladar", ruta: "/trasladar", icono: Truck, permisosAlguno: ["traspasos.operar"], grupo: "Operación", inicio: "flujo" },
  { id: "recibir", titulo: "Recibir", ruta: "/recibir", icono: Inbox, permisosAlguno: ["traspasos.operar"], grupo: "Operación", inicio: "flujo", contador: "porRecibir" },
  { id: "pedir-compra", titulo: "Pedir compra urgente", ruta: "/compras/nueva", icono: ShoppingCart, permisosAlguno: ["compras.solicitar"], grupo: "Operación", inicio: "gestion" },
  { id: "compras-mias", titulo: "Compras urgentes", ruta: "/compras/mias", icono: ReceiptText, permisosAlguno: ["compras.solicitar"], grupo: "Operación", inicio: "gestion" },
  { id: "consultar", titulo: "Consultar", ruta: "/consultar", icono: Search, grupo: "Consulta", inicio: "flujo" },
  { id: "mis-movimientos", titulo: "Mis movimientos de hoy", ruta: "/mis-movimientos", icono: History, permisosAlguno: ["vales.ver"], grupo: "Consulta", inicio: "gestion" },
  { id: "solicitudes-compra", titulo: "Solicitudes de compra", ruta: "/compras", icono: ShoppingCart, permisosAlguno: ["compras.atender"], grupo: "Inventario y catálogo", inicio: "gestion", contador: "porComprar" },
  { id: "autorizaciones", titulo: "Autorizaciones", ruta: "/autorizaciones", icono: ShieldCheck, permisosAlguno: ["autorizaciones.resolver"], grupo: "Supervisión", inicio: "siempre", contador: "porAutorizar" },
  { id: "seguimiento", titulo: "Seguimiento de piezas", ruta: "/seguimiento", icono: MapPinned, permisosAlguno: ["reportes.existencias"], grupo: "Supervisión", inicio: "siempre" },
  { id: "personal", titulo: "Personal", ruta: "/personal", icono: UserCog, permisosAlguno: ["almacenes.asignar_personal"], grupo: "Supervisión", inicio: "gestion" },
  { id: "trabajadores", titulo: "Trabajadores", ruta: "/trabajadores", icono: Users, permisosAlguno: ["trabajadores.ver"], grupo: "Personas", inicio: "gestion" },
  { id: "alta-trabajador", titulo: "Alta de trabajador", ruta: "/trabajadores/nuevo", icono: UserPlus, permisosAlguno: ["trabajadores.administrar"], grupo: "Personas", inicio: "gestion" },
  { id: "inventario", titulo: "Inventario", ruta: "/inventario", icono: Boxes, permisosAlguno: ["inventario.ver"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "entradas", titulo: "Entradas", ruta: "/entradas/nueva", icono: PackagePlus, permisosAlguno: ["inventario.entradas"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "importar", titulo: "Importar", ruta: "/importar", icono: Upload, permisosAlguno: ["inventario.entradas"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "categorias", titulo: "Categorías", ruta: "/catalogo/categorias", icono: FolderTree, permisosAlguno: ["catalogo.administrar"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "articulos", titulo: "Artículos", ruta: "/catalogo/articulos", icono: Package, permisosAlguno: ["catalogo.administrar"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "puestos", titulo: "Puestos", ruta: "/puestos", icono: BriefcaseBusiness, permisosAlguno: ["catalogo.administrar"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "etiquetas", titulo: "Etiquetas", ruta: "/etiquetas", icono: Printer, permisosAlguno: ["etiquetas.imprimir"], grupo: "Inventario y catálogo", inicio: "gestion" },
  { id: "rep-existencias", titulo: "Existencias", ruta: "/reportes/existencias", icono: ClipboardList, permisosAlguno: ["reportes.existencias"], grupo: "Reportes", inicio: "gestion" },
  { id: "rep-movimientos", titulo: "Movimientos", ruta: "/reportes/movimientos", icono: FileBarChart, permisosAlguno: ["reportes.movimientos"], grupo: "Reportes", inicio: "gestion" },
  { id: "rep-adeudos", titulo: "Adeudos", ruta: "/reportes/adeudos", icono: FileBarChart, permisosAlguno: ["reportes.adeudos"], grupo: "Reportes", inicio: "gestion" },
  { id: "rep-consumo", titulo: "Consumo", ruta: "/reportes/consumo", icono: FileBarChart, permisosAlguno: ["reportes.consumo"], grupo: "Reportes", inicio: "gestion" },
  { id: "usuarios", titulo: "Usuarios", ruta: "/usuarios", icono: UserRoundCog, permisosAlguno: ["acceso.administrar"], grupo: "Administración", inicio: "gestion" },
  { id: "roles", titulo: "Roles y permisos", ruta: "/roles", icono: KeyRound, permisosAlguno: ["acceso.administrar"], grupo: "Administración", inicio: "gestion" },
];

const ORDEN_GRUPOS = ["Operación", "Consulta", "Supervisión", "Personas", "Inventario y catálogo", "Reportes", "Administración"];

export function menuPermitido(puedeAlguno: (permisos: readonly Permiso[]) => boolean): ElementoMenu[] {
  return MENU.filter((e) => !e.permisosAlguno || puedeAlguno(e.permisosAlguno));
}

/**
 * Qué opción del menú corresponde a la ruta actual. Cuenta también la subruta (`/trabajadores/<id>` marca
 * "Trabajadores"); si varias coinciden gana la más específica (`/trabajadores/nuevo` marca "Alta de trabajador").
 * "Inicio" (`/`) no está en la lista: se marca solo en `/` exacto.
 */
export function idActivo(elementos: readonly ElementoMenu[], pathname: string): string | null {
  const ruta = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  let mejor: ElementoMenu | null = null;
  for (const e of elementos) {
    if (ruta === e.ruta || ruta.startsWith(`${e.ruta}/`)) {
      if (!mejor || e.ruta.length > mejor.ruta.length) mejor = e;
    }
  }
  return mejor?.id ?? null;
}

export function agruparMenu(elementos: readonly ElementoMenu[]): { grupo: string; elementos: ElementoMenu[] }[] {
  return ORDEN_GRUPOS.map((grupo) => ({
    grupo,
    elementos: elementos.filter((e) => e.grupo === grupo),
  })).filter((g) => g.elementos.length > 0);
}

/** Botones del inicio según los permisos. */
export function elementosDeInicio(permitidos: readonly ElementoMenu[]): ElementoMenu[] {
  const operaAlmacen = permitidos.some((e) => e.inicio === "flujo" && e.id !== "consultar");
  return permitidos.filter(
    (e) => e.inicio === "flujo" || e.inicio === "siempre" || (e.inicio === "gestion" && !operaAlmacen),
  );
}
