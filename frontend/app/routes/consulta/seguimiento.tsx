import { cn } from "cn";
import { DownloadIcon, MapPinnedIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";

import { apiGet, descargarCsv } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Checkbox } from "~/components/ui/checkbox";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista, NotaAlcance, textoDeOpcion, useAlcance } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useEtiqueta } from "~/componentes/reportes/listas";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { TablaPiezas, TarjetasPiezas } from "~/componentes/seguimiento/lista";
import { PestanaCantidad } from "~/componentes/seguimiento/pestana-cantidad";
import { ResumenSeguimientoTarjetas, type ClaveResumen } from "~/componentes/seguimiento/resumen";
import {
  OPCIONES_ESTADO,
  OPCIONES_UBICACION,
  TAMANO_SEGUIMIENTO,
  type PaginaSeguimiento,
} from "~/componentes/seguimiento/tipos";
import { Boton } from "~/componentes/ui/boton";
import { aviso } from "~/componentes/ui/aviso";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { useSesion } from "~/sesion/sesion";

// SG-04: «quién tiene qué» también se ve con `resguardo.ver`.
export const handle: ManejadorRuta = { permisosAlguno: ["reportes.existencias", "resguardo.ver"] };

const CLAVES = ["q", "articulo", "almacen", "estado", "ubicacion", "serie_pendiente", "alto_valor"] as const;
const MINIMO_BUSQUEDA = 2;

/** Qué tarjeta del resumen corresponde a los filtros de la dirección. */
function tarjetaActiva(ubicacion: string, estado: string): ClaveResumen {
  if (ubicacion === "ALMACEN" || ubicacion === "TRABAJADOR" || ubicacion === "TRANSITO") return ubicacion;
  if (estado === "NO_APTO" && !ubicacion) return "NO_APTO";
  return "total";
}

/** SG-01: Seguimiento tiene dos pestañas, Piezas (con serie) y Por cantidad. La elegida va en `?vista=`. */
export default function Seguimiento() {
  const [params, setParams] = useSearchParams();
  const vista = params.get("vista") === "cantidad" ? "cantidad" : "piezas";

  function elegir(nueva: string) {
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (nueva === "cantidad") nuevos.set("vista", "cantidad");
        else nuevos.delete("vista");
        nuevos.delete("pagina");
        return nuevos;
      },
      { replace: true },
    );
  }

  return (
    <Pantalla titulo="Quién tiene qué" descripcion="Dónde está cada pieza y quién tiene cada herramienta o equipo de protección en resguardo.">
      <div className="flex flex-col gap-4">
        <Tabs value={vista} onValueChange={(v) => elegir(String(v))}>
          <TabsList aria-label="Qué mostrar" className="h-auto! w-full sm:w-fit">
            <TabsTrigger value="piezas" className="min-h-11 flex-1 px-4 text-base sm:flex-none">
              Piezas
            </TabsTrigger>
            <TabsTrigger value="cantidad" className="min-h-11 flex-1 px-4 text-base sm:flex-none">
              Por cantidad
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <p className="text-sm text-muted-foreground">
          {vista === "piezas"
            ? "Piezas: cada herramienta o equipo con serie, una por una, con dónde está y quién la tiene."
            : "Por cantidad: lo que se entrega sin serie, como guantes o flexómetros, y cuánto tiene cada trabajador."}
        </p>
        {vista === "piezas" ? <PestanaPiezas alVerCantidad={() => elegir("cantidad")} /> : <PestanaCantidad />}
      </div>
    </Pantalla>
  );
}

function PestanaPiezas({ alVerCantidad }: { alVerCantidad: () => void }) {
  const { puede } = useSesion();
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const { valores, pagina, cambiar, cambiarPagina } = useFiltrosUrl(CLAVES);

  // El texto se guarda aparte para escribir sin trabas; se aplica a la dirección al dejar de escribir.
  const [texto, setTexto] = useState(valores.q);
  const q = useRetraso(texto.trim());
  const buscaConTexto = q.length >= MINIMO_BUSQUEDA ? q : "";
  const qEnUrl = useRef(valores.q);
  useEffect(() => {
    if (buscaConTexto !== qEnUrl.current) {
      qEnUrl.current = buscaConTexto;
      cambiar({ q: buscaConTexto });
    }
    // `cambiar` es estable; solo importa el texto ya retrasado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buscaConTexto]);

  const parametros = {
    q: buscaConTexto,
    articulo_id: valores.articulo,
    almacen_id: alcance.todos ? valores.almacen : "",
    estado: valores.estado,
    ubicacion: valores.ubicacion,
    serie_pendiente: valores.serie_pendiente === "true" ? true : undefined,
    alto_valor: valores.alto_valor === "true" ? true : undefined,
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaSeguimiento>("/seguimiento/piezas", { ...parametros, pagina, tamano: TAMANO_SEGUIMIENTO }, signal),
    JSON.stringify([parametros, pagina]),
  );
  const { datos, cargando, error } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;
  const porCantidad = datos?.resumen.articulos_por_cantidad ?? 0;

  const nombreArticulo = useEtiqueta("articulo", valores.articulo);
  const articuloPrimero = elementos.find((e) => e.articulo.id === valores.articulo)?.articulo.nombre ?? null;

  const [descargando, setDescargando] = useState(false);
  async function descargar() {
    setDescargando(true);
    try {
      await descargarCsv("/seguimiento/piezas", parametros, "seguimiento-piezas.csv");
    } catch (causa) {
      aviso({ titulo: "No se pudo descargar el archivo", descripcion: mensajeDeError(causa), tipo: "error" });
    } finally {
      setDescargando(false);
    }
  }

  function elegirTarjeta(clave: ClaveResumen) {
    const activa = tarjetaActiva(valores.ubicacion, valores.estado);
    if (clave === "total") cambiar({ ubicacion: null, estado: null });
    else if (clave === "NO_APTO") cambiar({ estado: activa === "NO_APTO" ? null : "NO_APTO", ubicacion: null });
    else cambiar({ ubicacion: activa === clave ? null : clave });
  }

  function limpiar() {
    setTexto("");
    qEnUrl.current = "";
    cambiar({ q: null, articulo: null, almacen: null, estado: null, ubicacion: null, serie_pendiente: null, alto_valor: null });
  }

  const chips: { clave: (typeof CLAVES)[number]; texto: string }[] = [];
  if (valores.articulo) chips.push({ clave: "articulo", texto: `Artículo: ${articuloPrimero ?? nombreArticulo ?? "elegido"}` });
  if (alcance.todos && valores.almacen) {
    chips.push({ clave: "almacen", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen) ?? "elegido"}` });
  }
  if (valores.estado) chips.push({ clave: "estado", texto: `Estado: ${textoDeOpcion(OPCIONES_ESTADO.map(({ valor, texto }) => ({ valor, texto })), valores.estado) ?? valores.estado}` });
  if (valores.ubicacion) chips.push({ clave: "ubicacion", texto: `Lugar: ${textoDeOpcion(OPCIONES_UBICACION, valores.ubicacion) ?? valores.ubicacion}` });
  if (valores.serie_pendiente === "true") chips.push({ clave: "serie_pendiente", texto: "Con serie pendiente" });
  if (valores.alto_valor === "true") chips.push({ clave: "alto_valor", texto: "Alto valor y alturas" });
  const hayFiltros = chips.length > 0 || buscaConTexto !== "";

  let contenido;
  if (error) {
    contenido = <EstadoError error={error} alReintentar={consulta.recargar} />;
  } else if (cargando && !datos) {
    contenido = (
      <>
        <div className="hidden md:block">
          <Esqueleto tipo="tabla" cantidad={6} />
        </div>
        <div className="md:hidden">
          <Esqueleto tipo="lista" cantidad={5} />
        </div>
      </>
    );
  } else if (total === 0 && !cargando) {
    contenido = (
      <EstadoVacio
        icono={MapPinnedIcon}
        titulo="No hay piezas con ese filtro"
        descripcion={
          porCantidad > 0
            ? `Esta pestaña solo cuenta piezas con serie. Hay ${porCantidad} ${porCantidad === 1 ? "artículo" : "artículos"} por cantidad en resguardo: míralos en la pestaña Por cantidad.`
            : hayFiltros
              ? "Prueba con otra palabra o quita algún filtro."
              : "Todavía no hay piezas que mostrar."
        }
        accion={
          porCantidad > 0 ? (
            <Boton variante="normal" onClick={alVerCantidad}>
              Ver lo que se entregó por cantidad
            </Boton>
          ) : hayFiltros ? (
            <Boton variante="contorno" onClick={limpiar}>
              Quitar filtros
            </Boton>
          ) : undefined
        }
      />
    );
  } else {
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", cargando && "opacity-60")} aria-busy={cargando}>
        {/* `w-0 min-w-full`: la tabla ancha se desplaza dentro de su caja y no ensancha la página. */}
        <div className="w-0 min-w-full">
          <TablaPiezas piezas={elementos} puedeAbrir={puede("catalogo.ver")} puedeVerVale={puede("vales.ver")} />
        </div>
        <TarjetasPiezas piezas={elementos} puedeAbrir={puede("catalogo.ver")} puedeVerVale={puede("vales.ver")} />
        <Paginador pagina={pagina} tamano={TAMANO_SEGUIMIENTO} total={total} alCambiar={cambiarPagina} ocupado={cargando} />
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <CampoBusqueda
            etiqueta="Buscar piezas por artículo, serie, código o trabajador"
            placeholder="Buscar artículo, serie o trabajador"
            value={texto}
            alCambiar={setTexto}
            claseContenedor="min-w-64"
            className="h-12 rounded-xl text-base"
          />
          <HojaFiltros
            valores={{ estado: valores.estado, ubicacion: valores.ubicacion, almacen: valores.almacen, serie_pendiente: valores.serie_pendiente }}
            activos={[valores.estado, valores.ubicacion, alcance.todos ? valores.almacen : "", valores.serie_pendiente].filter(Boolean).length}
            alAplicar={(v) => cambiar({ estado: v.estado, ubicacion: v.ubicacion, almacen: alcance.todos ? v.almacen : null, serie_pendiente: v.serie_pendiente === "true" ? "true" : null })}
            alLimpiar={() => cambiar({ estado: null, ubicacion: null, almacen: null, serie_pendiente: null })}
          >
            {(borrador, cambiarBorrador) => (
              <>
                {alcance.todos && almacenes.disponible ? (
                  <FiltroLista
                    etiqueta="Almacén"
                    vacio="Todos los almacenes"
                    valor={borrador.almacen}
                    opciones={almacenes.opciones}
                    alCambiar={(v) => cambiarBorrador({ almacen: v })}
                  />
                ) : null}
                <FiltroLista
                  etiqueta="Estado de la pieza"
                  vacio="Todos los estados"
                  valor={borrador.estado}
                  opciones={OPCIONES_ESTADO}
                  alCambiar={(v) => cambiarBorrador({ estado: v })}
                />
                <FiltroLista
                  etiqueta="Dónde está"
                  vacio="Cualquier lugar"
                  valor={borrador.ubicacion}
                  opciones={OPCIONES_UBICACION}
                  alCambiar={(v) => cambiarBorrador({ ubicacion: v })}
                />
                <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border bg-card px-3 text-base font-medium">
                  <Checkbox
                    checked={borrador.serie_pendiente === "true"}
                    onCheckedChange={(v) => cambiarBorrador({ serie_pendiente: v === true ? "true" : "" })}
                  />
                  Con serie pendiente
                </label>
              </>
            )}
          </HojaFiltros>
          <Boton
            variante="contorno"
            cargando={descargando}
            disabled={!datos || total === 0 || Boolean(error)}
            onClick={descargar}
          >
            {descargando ? null : <DownloadIcon aria-hidden="true" />}
            Descargar CSV
          </Boton>
        </div>

        {texto.trim().length === 1 ? (
          <p className="text-sm text-muted-foreground">Escribe al menos dos caracteres para buscar.</p>
        ) : null}

        <ResumenSeguimientoTarjetas
          resumen={datos?.resumen ?? null}
          activa={tarjetaActiva(valores.ubicacion, valores.estado)}
          alElegir={elegirTarjeta}
          cargando={cargando && Boolean(datos)}
        />

        {porCantidad > 0 && total > 0 ? (
          <p className="text-sm text-muted-foreground">
            Además hay {porCantidad} {porCantidad === 1 ? "artículo" : "artículos"} por cantidad en resguardo.{" "}
            <button type="button" onClick={alVerCantidad} className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2">
              Verlos
            </button>
          </p>
        ) : null}

        {chips.length > 0 ? (
          <ul aria-label="Filtros activos" className="flex flex-wrap items-center gap-2">
            {chips.map((f) => (
              <li key={f.clave}>
                <button
                  type="button"
                  onClick={() => cambiar({ [f.clave]: null })}
                  aria-label={`Quitar filtro: ${f.texto}`}
                  className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-primary/30 bg-accent px-3 text-xs font-semibold text-marino hover:bg-accent/70"
                >
                  {f.texto}
                  <XIcon aria-hidden="true" className="size-3.5" />
                </button>
              </li>
            ))}
            <li>
              <Boton variante="texto" className="h-10 px-3 text-xs" onClick={limpiar}>
                Quitar todos
              </Boton>
            </li>
          </ul>
        ) : null}

        <div className="flex flex-col gap-1 text-xs text-muted-foreground">
          <NotaAlcance almacen={alcance.almacen} />
          <p>Toca una pieza para ver su ficha, su inspección y todo su historial.</p>
        </div>

        <p className="text-sm font-semibold" aria-live="polite">
          {datos && !error ? `${total} ${total === 1 ? "pieza" : "piezas"}` : " "}
        </p>

        {contenido}
      </div>
    </>
  );
}
