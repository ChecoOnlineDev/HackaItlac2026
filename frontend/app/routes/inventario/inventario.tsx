import { cn } from "cn";
import { Boxes, SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { Paginador, Seleccion } from "~/componentes/catalogo/campos";
import {
  TAMANO_PAGINA,
  TEXTO_CONTROL,
  textoRetorno,
  type Almacen,
  type Categoria,
  type Existencias,
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
import { HojaMinimos } from "~/componentes/catalogo/hoja-minimos";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "inventario.ver" };

/** El almacén que se operó por última vez en este dispositivo (lo guarda Entregar). */
function leerAlmacenRecordado(): string | null {
  try {
    return window.localStorage.getItem("imhotep.almacen.operando");
  } catch {
    return null;
  }
}

export default function Inventario() {
  const { sesion, puede } = useSesion();
  const puedeVerArticulo = puede("catalogo.ver");
  // Desde Almacenes (administración) se llega con `?almacen=<id>` ya elegido.
  const [almacenElegido, setAlmacenElegido] = useState<string | null>(() => new URLSearchParams(window.location.search).get("almacen"));
  const [bajoMinimo, setBajoMinimo] = useState(false);
  const [minimosAbiertos, setMinimosAbiertos] = useState(false);
  const [categoria, setCategoria] = useState("");
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [pagina, setPagina] = useState(1);

  const almacenes = useConsulta((signal) => apiGet<Almacen[]>("/almacenes", undefined, signal), "almacenes");
  const categorias = useConsulta(
    (signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal).catch(() => ({ elementos: [], total: 0 })),
    "categorias",
  );

  // La página vuelve a la 1 cuando cambia el texto ya retrasado, no en cada tecla.
  useEffect(() => {
    setPagina(1);
  }, [q]);

  // Solo quien tiene `almacenes.todos` ve el inventario de varios almacenes; los demás, solo el suyo.
  const operaTodos = puede("almacenes.todos");
  const lista = (almacenes.datos ?? []).filter((a) => operaTodos || a.id === sesion?.almacen?.id || sesion?.almacenes?.some((asignado) => asignado.id === a.id));
  // Por omisión, el almacén de quien entra; si opera todos, el último que operó; si no, el primero.
  const recordado = lista.find((a) => a.id === leerAlmacenRecordado())?.id;
  const almacenPorOmision = sesion?.almacen?.id ?? recordado ?? lista[0]?.id ?? "";
  const almacenId = almacenElegido ?? almacenPorOmision;

  const existencias = useConsulta(
    (signal) =>
      almacenId
        ? apiGet<Existencias>(`/almacenes/${almacenId}/existencias`, { q, bajo_minimo: bajoMinimo || undefined, categoria_id: categoria, pagina, tamano: TAMANO_PAGINA }, signal)
        : Promise.resolve(null),
    `${almacenId}|${q}|${categoria}|${pagina}|${bajoMinimo}`,
  );

  const filas = existencias.datos?.elementos ?? [];
  const hayFiltros = q !== "" || categoria !== "" || bajoMinimo;

  const enlace = (id: string, nombre: string) =>
    puedeVerArticulo ? (
      <Link to={`/catalogo/articulos?articulo=${id}`} className="font-semibold underline-offset-4 hover:underline">
        {nombre}
      </Link>
    ) : (
      <span className="font-semibold">{nombre}</span>
    );

  let contenido;
  if (almacenes.error && !almacenes.datos) {
    contenido = <EstadoError error={almacenes.error} alReintentar={almacenes.recargar} />;
  } else if (existencias.error && !existencias.datos) {
    contenido = <EstadoError error={existencias.error} alReintentar={existencias.recargar} />;
  } else if ((almacenes.cargando && !almacenes.datos) || (existencias.cargando && !existencias.datos)) {
    contenido = <Esqueleto tipo="tabla" cantidad={6} />;
  } else if (lista.length === 0) {
    contenido = <EstadoVacio icono={Boxes} titulo="No hay almacenes" descripcion={operaTodos ? "Todavía no se ha dado de alta ningún almacén." : "Todavía no tienes un almacén asignado."} />;
  } else if (filas.length === 0) {
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
              setCategoria("");
              setBajoMinimo(false);
              setPagina(1);
            }}
          >
            Quitar filtros
          </Boton>
        }
      />
    ) : (
      <EstadoVacio
        icono={Boxes}
        titulo="Este almacén no tiene existencias"
        descripcion="Cuando se registre una entrada o llegue un traslado, aparecerán aquí."
      />
    );
  } else {
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", existencias.cargando && "opacity-60")} aria-busy={existencias.cargando}>
        <div className="hidden lg:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Artículo</TableHead>
                <TableHead scope="col">Categoría</TableHead>
                <TableHead scope="col" className="text-right">Existencia</TableHead>
                <TableHead scope="col" className="text-right">Disponible</TableHead>
                <TableHead scope="col" className="text-right">No disponible</TableHead>
                <TableHead scope="col" className="text-right">Mínimo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filas.map((f) => (
                <TableRow key={f.articulo_id} className={cn(!f.activo && "bg-muted/40 text-muted-foreground", f.bajo_minimo && "bg-destructive/5")}>
                  <TableCell className="whitespace-normal">
                    {enlace(f.articulo_id, f.nombre)}
                    <span className="block text-xs text-muted-foreground">
                      {f.codigo}
                      {f.marca ? ` · ${f.marca}` : ""}
                      {f.talla ? ` · Talla ${f.talla}` : ""}
                    </span>
                    {!f.activo ? <Insignia estado="neutra" className="mt-1">Inactivo</Insignia> : null}
                  </TableCell>
                  <TableCell className="whitespace-normal">
                    {f.categoria_nombre}
                    <span className="block text-xs text-muted-foreground">
                      {TEXTO_CONTROL[f.control]} · {textoRetorno(f.retornable)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-semibold">{f.cantidad}</TableCell>
                  <TableCell className={cn("text-right font-semibold", f.bajo_minimo && "text-destructive")}>{f.disponible}{f.bajo_minimo ? <span className="block text-xs">Por debajo del mínimo</span> : null}</TableCell>
                  <TableCell className="text-right">{f.no_disponible ?? "—"}</TableCell>
                  <TableCell className="text-right">{f.minimo ?? "Sin mínimo"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <ul className="grid gap-3 sm:grid-cols-2 lg:hidden">
          {filas.map((f) => (
            <li key={f.articulo_id} className={cn("flex flex-col gap-3 rounded-2xl border bg-card p-4 shadow-xs", !f.activo && "bg-muted/40 text-muted-foreground")}>
              <div className="flex flex-col gap-0.5">
                <span className="text-base">{enlace(f.articulo_id, f.nombre)}</span>
                <span className="text-xs text-muted-foreground">
                  {f.codigo} · {f.categoria_nombre}
                  {f.talla ? ` · Talla ${f.talla}` : ""}
                </span>
                {!f.activo ? <Insignia estado="neutra" className="mt-1 self-start">Inactivo</Insignia> : null}
              </div>
              <dl className="grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-muted/60 px-3 py-2">
                  <dt className="text-xs text-muted-foreground">Existencia</dt>
                  <dd className="text-xl font-semibold tabular-nums text-foreground">{f.cantidad}</dd>
                </div>
                <div className="rounded-xl bg-muted/60 px-3 py-2">
                  <dt className="text-xs text-muted-foreground">Disponible</dt>
                  <dd className={cn("text-xl font-semibold tabular-nums", f.bajo_minimo && "text-destructive")}>{f.disponible}</dd>
                </div>
              </dl>
              <p className={cn("text-sm", f.bajo_minimo && "text-destructive")}>Mínimo: {f.minimo ?? "Sin mínimo"} · No disponible: {f.no_disponible ?? "—"}{f.bajo_minimo ? " · Por debajo del mínimo" : ""}</p>
            </li>
          ))}
        </ul>
        <Paginador pagina={pagina} tamano={TAMANO_PAGINA} total={existencias.datos?.total ?? 0} alCambiar={setPagina} ocupado={existencias.cargando} />
      </div>
    );
  }

  const almacenActual = lista.find((a) => a.id === almacenId);
  const almacenCambiado = almacenElegido !== null && almacenElegido !== almacenPorOmision;
  const activos = (categoria ? 1 : 0) + (almacenCambiado ? 1 : 0);

  return (
    <Pantalla acciones={puede("inventario.minimos") && almacenId ? <Boton variante="contorno" onClick={() => setMinimosAbiertos(true)}>Configurar mínimos</Boton> : null} titulo="Inventario" descripcion={almacenActual ? `Lo que hay en ${almacenActual.nombre}.` : "Lo que hay en cada almacén."}>
      <div className="flex items-center gap-2">
        <CampoBusqueda
          etiqueta="Buscar artículo"
          placeholder="Buscar artículo"
          value={texto}
          alCambiar={(v) => {
            setTexto(v);
          }}
        />
        <HojaFiltros
          valores={{ almacen: almacenId, categoria }}
          activos={activos}
          alAplicar={(v) => {
            setAlmacenElegido(v.almacen);
            setCategoria(v.categoria);
            setPagina(1);
          }}
          alLimpiar={() => {
            setAlmacenElegido(null);
            setCategoria("");
              setBajoMinimo(false);
            setPagina(1);
          }}
        >
          {(b, cambiar) => (
            <>
              <Seleccion
                etiqueta="Almacén"
                opciones={lista.map((a) => ({ valor: a.id, texto: a.nombre }))}
                value={b.almacen}
                alCambiar={(v) => cambiar({ almacen: v })}
                disabled={lista.length === 0}
              />
              {categorias.datos && categorias.datos.elementos.length > 0 ? (
                <Seleccion
                  etiqueta="Categoría"
                  vacio="Todas las categorías"
                  opciones={categorias.datos.elementos.map((c) => ({ valor: c.id, texto: c.nombre }))}
                  value={b.categoria}
                  alCambiar={(v) => cambiar({ categoria: v })}
                />
              ) : null}
            </>
          )}
        </HojaFiltros>
      </div>
      <p className="text-xs text-muted-foreground">
        <strong className="font-semibold text-foreground">Existencia:</strong> todo lo que hay.{" "}
        <strong className="font-semibold text-foreground">Disponible:</strong> lo que se puede entregar hoy (sin piezas no aptas ni en mantenimiento).
      </p>
      <Boton variante={bajoMinimo ? "normal" : "contorno"} aria-pressed={bajoMinimo} onClick={() => { setBajoMinimo((v) => !v); setPagina(1); }}>Por debajo del mínimo</Boton>
      {contenido}
      {minimosAbiertos ? <HojaMinimos almacenId={almacenId} alCerrar={() => setMinimosAbiertos(false)} alGuardar={existencias.recargar} /> : null}
    </Pantalla>
  );
}
