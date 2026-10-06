import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

/**
 * Mapa de rutas (docs/product/app-flow.md, "Pantallas del MVP"). Ya están todas registradas:
 * quien construya una pantalla edita SOLO su archivo en `routes/<area>/`, no este mapa ni los layouts.
 * Cada pantalla se carga por separado (un archivo por ruta) la primera vez que se abre.
 */
export default [
  route("entrar", "routes/entrar.tsx"),

  // Todo lo que sigue exige sesión; el layout aplica la guardia y el menú según permisos.
  layout("routes/_app.tsx", [
    index("routes/inicio.tsx"),
    // operacion
    route("entregar", "routes/operacion/entregar.tsx"),
    route("devolver", "routes/operacion/devolver.tsx"),
    route("trasladar", "routes/operacion/trasladar.tsx"),
    route("recibir", "routes/operacion/recibir.tsx"),
    route("recibir/:id", "routes/operacion/recibir-detalle.tsx"),
    // consulta
    route("consultar", "routes/consulta/consultar.tsx"),
    route("articulos/:id", "routes/consulta/articulo.tsx"),
    route("piezas/:id", "routes/consulta/pieza.tsx"),
    route("vales/:id", "routes/consulta/vale.tsx"),
    route("v/:token", "routes/consulta/vale-qr.tsx"),
    route("mis-movimientos", "routes/consulta/mis-movimientos.tsx"),
    route("seguimiento", "routes/consulta/seguimiento.tsx"),
    // personas
    route("trabajadores", "routes/personas/trabajadores.tsx"),
    route("trabajadores/nuevo", "routes/personas/trabajador-nuevo.tsx"),
    route("trabajadores/:id", "routes/personas/trabajador-ficha.tsx"),
    // inventario
    route("inventario", "routes/inventario/inventario.tsx"),
    route("entradas/nueva", "routes/inventario/entrada-nueva.tsx"),
    route("importar", "routes/inventario/importar.tsx"),
    route("catalogo/categorias", "routes/inventario/categorias.tsx"),
    route("catalogo/articulos", "routes/inventario/articulos.tsx"),
    route("puestos", "routes/inventario/puestos.tsx"),
    route("etiquetas", "routes/inventario/etiquetas.tsx"),
    // supervision
    route("autorizaciones", "routes/supervision/autorizaciones.tsx"),
    route("personal", "routes/supervision/personal.tsx"),
    route("reportes/existencias", "routes/supervision/rep-existencias.tsx"),
    route("reportes/movimientos", "routes/supervision/rep-movimientos.tsx"),
    route("reportes/adeudos", "routes/supervision/rep-adeudos.tsx"),
    route("reportes/consumo", "routes/supervision/rep-consumo.tsx"),
    // administración (acceso.administrar)
    route("usuarios", "routes/acceso/usuarios.tsx"),
    route("roles", "routes/acceso/roles.tsx"),
    route("roles/:id", "routes/acceso/rol.tsx"),
    route("*", "routes/no-encontrada.tsx"),
  ]),

  // Galería de componentes: solo existe fuera de producción.
  ...(process.env.NODE_ENV !== "production" ? [route("dev/componentes", "routes/dev/componentes.tsx")] : []),
] satisfies RouteConfig;
