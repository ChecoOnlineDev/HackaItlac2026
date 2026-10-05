import { cn } from "cn";
import { Boxes, InfoIcon, SearchIcon } from "lucide-react";
import { useState } from "react";
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
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "inventario.ver" };

export default function Inventario() {
  const { sesion, puede } = useSesion();
  const puedeVerArticulo = puede("catalogo.ver");
  const [almacenElegido, setAlmacenElegido] = useState<string | null>(null);
  const [categoria, setCategoria] = useState("");
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [pagina, setPagina] = useState(1);

  const almacenes = useConsulta((signal) => apiGet<Almacen[]>("/almacenes", undefined, signal), "almacenes");
  const categorias = useConsulta(
    (signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal).catch(() => ({ elementos: [], total: 0 })),
    "categorias",
  );

  const lista = almacenes.datos ?? [];
  // Por omisión, el almacén de quien entra; si opera todos o ninguno, el primero de la lista.
  const almacenId = almacenElegido ?? sesion?.almacen?.id ?? lista[0]?.id ?? "";

  const existencias = useConsulta(
    (signal) =>
      almacenId
        ? apiGet<Existencias>(`/almacenes/${almacenId}/existencias`, { q, categoria_id: categoria, pagina, tamano: TAMANO_PAGINA }, signal)
        : Promise.resolve(null),
    `${almacenId}|${q}|${categoria}|${pagina}`,
  );

  const filas = existencias.datos?.elementos ?? [];
  const hayFiltros = q !== "" || categoria !== "";

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
    contenido = <EstadoVacio icono={Boxes} titulo="No hay almacenes" descripcion="Todavía no se ha dado de alta ningún almacén." />;
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
        <div className="hidden overflow-hidden rounded-xl border lg:block">
          <Table className="w-full text-left">
            <TableHeader className="bg-muted text-sm">
              <TableRow>
                <TableHead scope="col" className="p-3 font-semibold">Artículo</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Categoría</TableHead>
                <TableHead scope="col" className="p-3 text-right font-semibold">Existencia</TableHead>
                <TableHead scope="col" className="p-3 text-right font-semibold">Disponible</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filas.map((f) => (
                <TableRow key={f.articulo_id} className={cn("border-t", !f.activo && "bg-muted/40 text-muted-foreground")}>
                  <TableHead scope="row" className="p-3">
                    {enlace(f.articulo_id, f.nombre)}
                    <span className="block text-sm font-normal text-muted-foreground">
                      {f.codigo}
                      {f.marca ? ` · ${f.marca}` : ""}
                      {f.talla ? ` · Talla ${f.talla}` : ""}
                    </span>
                    {!f.activo ? <Insignia estado="neutra" className="mt-1">Inactivo</Insignia> : null}
                  </TableHead>
                  <TableCell className="p-3">
                    {f.categoria_nombre}
                    <span className="block text-sm text-muted-foreground">
                      {TEXTO_CONTROL[f.control]} · {textoRetorno(f.retornable)}
                    </span>
                  </TableCell>
                  <TableCell className="p-3 text-right text-lg font-semibold">{f.cantidad}</TableCell>
                  <TableCell className="p-3 text-right text-lg font-semibold">{f.disponible}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <ul className="flex flex-col gap-3 lg:hidden">
          {filas.map((f) => (
            <li key={f.articulo_id} className={cn("flex flex-col gap-3 rounded-xl border p-4", !f.activo && "bg-muted/40 text-muted-foreground")}>
              <div className="flex flex-col gap-1">
                <span className="text-lg">{enlace(f.articulo_id, f.nombre)}</span>
                <span className="text-sm text-muted-foreground">
                  {f.codigo} · {f.categoria_nombre}
                  {f.talla ? ` · Talla ${f.talla}` : ""}
                </span>
                {!f.activo ? <Insignia estado="neutra" className="self-start">Inactivo</Insignia> : null}
              </div>
              <dl className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-muted p-3">
                  <dt className="text-sm">Existencia</dt>
                  <dd className="text-2xl font-bold text-foreground">{f.cantidad}</dd>
                </div>
                <div className="rounded-lg bg-muted p-3">
                  <dt className="text-sm">Disponible</dt>
                  <dd className="text-2xl font-bold text-foreground">{f.disponible}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
        <Paginador pagina={pagina} tamano={TAMANO_PAGINA} total={existencias.datos?.total ?? 0} alCambiar={setPagina} ocupado={existencias.cargando} />
      </div>
    );
  }

  return (
    <Pantalla titulo="Inventario" descripcion="Lo que hay en cada almacén.">
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_2fr]">
        <Seleccion
          etiqueta="Almacén"
          opciones={lista.map((a) => ({ valor: a.id, texto: a.nombre }))}
          value={almacenId}
          alCambiar={(v) => {
            setAlmacenElegido(v);
            setPagina(1);
          }}
          disabled={lista.length === 0}
        />
        {categorias.datos && categorias.datos.elementos.length > 0 ? (
          <Seleccion
            etiqueta="Categoría"
            vacio="Todas las categorías"
            opciones={categorias.datos.elementos.map((c) => ({ valor: c.id, texto: c.nombre }))}
            value={categoria}
            alCambiar={(v) => {
              setCategoria(v);
              setPagina(1);
            }}
          />
        ) : (
          <div />
        )}
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
      </div>
      <p className="flex items-start gap-2 rounded-xl border bg-accent p-3 text-marino">
        <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <span>
          <strong>Existencia</strong> es todo lo que hay en el almacén. <strong>Disponible</strong> es lo que se puede entregar hoy: no cuenta las piezas no aptas ni las que están en mantenimiento.
        </span>
      </p>
      {contenido}
    </Pantalla>
  );
}
