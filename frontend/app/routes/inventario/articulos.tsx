import { cn } from "cn";
import { Package, PlusIcon, SearchIcon, XIcon } from "lucide-react";
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
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "catalogo.ver" };

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
  const sinCosto = params.get("sin_costo") === "true";

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
          sin_costo: sinCosto ? true : undefined,
          activo: estado === "activos" ? true : estado === "inactivos" ? false : undefined,
          pagina,
          tamano: TAMANO_PAGINA,
        },
        signal,
      ),
    `${q}|${categoriaFiltro}|${estado}|${pagina}|${sinCosto}`,
  );

  const todasCategorias = categorias.datos?.elementos ?? [];
  const articulos = lista.datos?.elementos ?? [];
  const hayFiltros = q !== "" || categoriaFiltro !== "" || sinCosto || estado !== "activos";

  function cambiarFiltro(parcial: { categoria?: string; articulo?: string | null; sinCosto?: boolean }) {
    const nuevos = new URLSearchParams(params);
    if (parcial.categoria !== undefined) {
      if (parcial.categoria) nuevos.set("categoria", parcial.categoria);
      else nuevos.delete("categoria");
      setPagina(1);
    }
    if (parcial.sinCosto !== undefined) {
      if (parcial.sinCosto) nuevos.set("sin_costo", "true");
      else nuevos.delete("sin_costo");
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
              cambiarFiltro({ categoria: "", sinCosto: false });
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
        <div className="hidden lg:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Artículo</TableHead>
                <TableHead scope="col">Código</TableHead>
                <TableHead scope="col">Categoría</TableHead>
                <TableHead scope="col">Control</TableHead>
                {puedeCostos ? <TableHead scope="col" className="text-right">Costo</TableHead> : null}
                <TableHead scope="col">Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {articulos.map((a) => (
                <TableRow key={a.id} className={cn(!a.activo && "bg-muted/40 text-muted-foreground")}>
                  <TableHead scope="row" className="whitespace-normal">
                    <button
                      type="button"
                      onClick={() => cambiarFiltro({ articulo: a.id })}
                      className="min-h-10 text-left font-semibold text-foreground underline-offset-4 hover:underline"
                    >
                      {a.nombre}
                      {a.marca ? <span className="block text-xs font-normal text-muted-foreground">{a.marca}</span> : null}
                    </button>
                  </TableHead>
                  <TableCell>{a.codigo}</TableCell>
                  <TableCell>{a.categoria_nombre}</TableCell>
                  <TableCell>
                    {TEXTO_CONTROL[a.control]}
                    <span className="block text-xs text-muted-foreground">{textoRetorno(a.retornable)}</span>
                  </TableCell>
                  {puedeCostos ? <TableCell className="text-right">{textoCosto(a.costo_unitario)}</TableCell> : null}
                  <TableCell>
                    <Insignia estado="neutra">{a.activo ? "Activo" : "Inactivo"}</Insignia>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular y tableta: tarjetas */}
        <ul className="grid gap-3 sm:grid-cols-2 lg:hidden">
          {articulos.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                onClick={() => cambiarFiltro({ articulo: a.id })}
                className={cn(
                  "flex h-full min-h-12 w-full flex-col gap-1.5 rounded-2xl border bg-card p-4 text-left shadow-xs transition-colors hover:bg-muted/40",
                  !a.activo && "bg-muted/40 text-muted-foreground",
                )}
              >
                <span className="flex flex-wrap items-start justify-between gap-2">
                  <span className="text-base font-semibold text-foreground">{a.nombre}</span>
                  {!a.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
                </span>
                <span className="text-sm">
                  {a.codigo} · {a.categoria_nombre}
                </span>
                <span className="text-xs text-muted-foreground">
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
      descripcion="Toca un artículo para ver sus reglas y existencias."
      acciones={botonNuevo}
    >
      <div className="flex items-center gap-2">
        <CampoBusqueda
          etiqueta="Buscar artículo"
          placeholder="Buscar artículo"
          value={texto}
          alCambiar={(v) => {
            setTexto(v);
            setPagina(1);
          }}
        />
        <HojaFiltros
          valores={{ categoria: categoriaFiltro, estado }}
          activos={(categoriaFiltro ? 1 : 0) + (estado !== "activos" ? 1 : 0)}
          alAplicar={(v) => {
            setEstado(v.estado);
            cambiarFiltro({ categoria: v.categoria });
            setPagina(1);
          }}
          alLimpiar={() => {
            setEstado("activos");
            cambiarFiltro({ categoria: "" });
            setPagina(1);
          }}
        >
          {(b, cambiar) => (
            <>
              <Seleccion
                etiqueta="Categoría"
                vacio="Todas las categorías"
                opciones={todasCategorias.map((c) => ({ valor: c.id, texto: c.nombre }))}
                value={b.categoria}
                alCambiar={(v) => cambiar({ categoria: v })}
              />
              <Seleccion etiqueta="Estado" opciones={OPCIONES_ESTADO} value={b.estado} alCambiar={(v) => cambiar({ estado: v })} />
            </>
          )}
        </HojaFiltros>
      </div>
      {sinCosto ? (
        <div className="flex flex-col gap-1.5">
          <div>
            <button
              type="button"
              onClick={() => cambiarFiltro({ sinCosto: false })}
              aria-label="Quitar el filtro «Sin costo registrado»"
              className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border bg-accent px-4 text-sm font-medium text-marino focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              Sin costo registrado
              <XIcon aria-hidden="true" className="size-4" />
            </button>
          </div>
          <p className="text-sm text-muted-foreground">Estos artículos no suman al valor del inventario hasta que se les registre un costo.</p>
        </div>
      ) : null}
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
