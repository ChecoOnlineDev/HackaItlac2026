import { cn } from "cn";
import { Package, PlusIcon, SearchIcon } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { Paginador, Seleccion } from "~/componentes/catalogo/campos";
import { DetalleArticulo } from "~/componentes/catalogo/detalle-articulo";
import { HojaArticulo } from "~/componentes/catalogo/hoja-articulo";
import {
  TAMANO_PAGINA,
  TEXTO_CONTROL,
  textoCosto,
  textoRetorno,
  type ArticuloLista,
  type Categoria,
} from "~/componentes/catalogo/tipos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "catalogo.ver" };

const OPCIONES_ESTADO = [
  { valor: "activos", texto: "Activos" },
  { valor: "inactivos", texto: "Inactivos" },
  { valor: "todos", texto: "Todos" },
];

export default function Articulos() {
  const { puede } = useSesion();
  const puedeEditar = puede("catalogo.administrar");
  const puedeCostos = puede("catalogo.costos");
  const [params, setParams] = useSearchParams();
  const articuloAbierto = params.get("articulo");
  const categoriaFiltro = params.get("categoria") ?? "";

  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [estado, setEstado] = useState("activos");
  const [pagina, setPagina] = useState(1);
  const [alta, setAlta] = useState(false);

  const categorias = useConsulta((signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal), "categorias");
  const lista = useConsulta(
    (signal) =>
      apiGet<Pagina<ArticuloLista>>(
        "/articulos",
        {
          q,
          categoria_id: categoriaFiltro,
          activo: estado === "activos" ? true : estado === "inactivos" ? false : undefined,
          pagina,
          tamano: TAMANO_PAGINA,
        },
        signal,
      ),
    `${q}|${categoriaFiltro}|${estado}|${pagina}`,
  );

  const todasCategorias = categorias.datos?.elementos ?? [];
  const articulos = lista.datos?.elementos ?? [];
  const hayFiltros = q !== "" || categoriaFiltro !== "" || estado !== "activos";

  function cambiarFiltro(parcial: { categoria?: string; articulo?: string | null }) {
    const nuevos = new URLSearchParams(params);
    if (parcial.categoria !== undefined) {
      if (parcial.categoria) nuevos.set("categoria", parcial.categoria);
      else nuevos.delete("categoria");
      setPagina(1);
    }
    if (parcial.articulo !== undefined) {
      if (parcial.articulo) nuevos.set("articulo", parcial.articulo);
      else nuevos.delete("articulo");
    }
    setParams(nuevos, { replace: parcial.articulo === undefined });
  }

  if (articuloAbierto) {
    return (
      <Pantalla titulo="Artículo" ancho="formulario">
        <DetalleArticulo
          articuloId={articuloAbierto}
          categorias={todasCategorias}
          puedeEditar={puedeEditar}
          puedeCostos={puedeCostos}
          alVolver={() => cambiarFiltro({ articulo: null })}
          alCambiar={lista.recargar}
        />
      </Pantalla>
    );
  }

  const botonNuevo = puedeEditar ? (
    <Boton variante="normal" onClick={() => setAlta(true)} disabled={categorias.datos === null}>
      <PlusIcon aria-hidden="true" />
      Nuevo artículo
    </Boton>
  ) : null;

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={6} />;
  } else if (articulos.length === 0) {
    contenido = hayFiltros ? (
      <EstadoVacio
        icono={SearchIcon}
        titulo="No hay artículos con esos filtros"
        descripcion="Prueba con otra palabra o quita los filtros."
        accion={
          <Boton
            variante="contorno"
            onClick={() => {
              setTexto("");
              setEstado("activos");
              cambiarFiltro({ categoria: "" });
            }}
          >
            Quitar filtros
          </Boton>
        }
      />
    ) : (
      <EstadoVacio
        icono={Package}
        titulo="Todavía no hay artículos"
        descripcion={puedeEditar ? "Da de alta el primero: elige su categoría y toma sus reglas." : "Compras o el supervisor los dan de alta."}
        accion={botonNuevo}
      />
    );
  } else {
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", lista.cargando && "opacity-60")} aria-busy={lista.cargando}>
        {/* Computadora: tabla */}
        <div className="hidden overflow-hidden rounded-xl border lg:block">
          <Table className="w-full text-left">
            <TableHeader className="bg-muted text-sm">
              <TableRow>
                <TableHead scope="col" className="p-3 font-semibold">Artículo</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Código</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Categoría</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Control</TableHead>
                {puedeCostos ? <TableHead scope="col" className="p-3 text-right font-semibold">Costo</TableHead> : null}
                <TableHead scope="col" className="p-3 font-semibold">Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {articulos.map((a) => (
                <TableRow key={a.id} className={cn("border-t", !a.activo && "bg-muted/40 text-muted-foreground")}>
                  <TableHead scope="row" className="p-3 font-semibold">
                    <button
                      type="button"
                      onClick={() => cambiarFiltro({ articulo: a.id })}
                      className="min-h-12 text-left underline-offset-4 hover:underline"
                    >
                      {a.nombre}
                      {a.marca ? <span className="block text-sm font-normal text-muted-foreground">{a.marca}</span> : null}
                    </button>
                  </TableHead>
                  <TableCell className="p-3">{a.codigo}</TableCell>
                  <TableCell className="p-3">{a.categoria_nombre}</TableCell>
                  <TableCell className="p-3">
                    {TEXTO_CONTROL[a.control]}
                    <br />
                    <span className="text-sm">{textoRetorno(a.retornable)}</span>
                  </TableCell>
                  {puedeCostos ? <TableCell className="p-3 text-right">{textoCosto(a.costo_unitario)}</TableCell> : null}
                  <TableCell className="p-3">
                    <Insignia estado="neutra">{a.activo ? "Activo" : "Inactivo"}</Insignia>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular y tableta: tarjetas */}
        <ul className="flex flex-col gap-3 lg:hidden">
          {articulos.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                onClick={() => cambiarFiltro({ articulo: a.id })}
                className={cn(
                  "flex min-h-12 w-full flex-col gap-2 rounded-xl border p-4 text-left",
                  !a.activo && "bg-muted/40 text-muted-foreground",
                )}
              >
                <span className="flex flex-wrap items-start justify-between gap-2">
                  <span className="text-lg font-bold text-foreground">{a.nombre}</span>
                  {!a.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
                </span>
                <span>
                  {a.codigo} · {a.categoria_nombre}
                </span>
                <span>
                  {TEXTO_CONTROL[a.control]} · {textoRetorno(a.retornable)}
                  {puedeCostos ? ` · ${textoCosto(a.costo_unitario)}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <Paginador pagina={pagina} tamano={TAMANO_PAGINA} total={lista.datos?.total ?? 0} alCambiar={setPagina} ocupado={lista.cargando} />
      </div>
    );
  }

  return (
    <Pantalla
      titulo="Artículos"
      descripcion="Catálogo de herramientas y equipo de protección. Toca un artículo para ver sus reglas y existencias."
      acciones={botonNuevo}
    >
      <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr]">
        <Campo
          etiqueta="Buscar"
          type="search"
          placeholder="Nombre, marca o código"
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value);
            setPagina(1);
          }}
        />
        <Seleccion
          etiqueta="Categoría"
          vacio="Todas las categorías"
          opciones={todasCategorias.map((c) => ({ valor: c.id, texto: c.nombre }))}
          value={categoriaFiltro}
          alCambiar={(v) => cambiarFiltro({ categoria: v })}
        />
        <Seleccion
          etiqueta="Estado"
          opciones={OPCIONES_ESTADO}
          value={estado}
          alCambiar={(v) => {
            setEstado(v);
            setPagina(1);
          }}
        />
      </div>
      {contenido}
      <HojaArticulo
        abierta={alta}
        alCambiar={setAlta}
        articulo={null}
        categorias={todasCategorias}
        puedeCostos={puedeCostos}
        categoriaInicial={categoriaFiltro}
        alGuardar={(creado) => {
          lista.recargar();
          cambiarFiltro({ articulo: creado.id });
        }}
      />
    </Pantalla>
  );
}
