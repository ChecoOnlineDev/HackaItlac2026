import { cn } from "cn";
import { DownloadIcon, MapPinnedIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiGet, descargarCsv } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista, NotaAlcance, textoDeOpcion, useAlcance } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useEtiqueta } from "~/componentes/reportes/listas";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { TablaPiezas, TarjetasPiezas } from "~/componentes/seguimiento/lista";
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

export const handle: ManejadorRuta = { permiso: "reportes.existencias" };

const CLAVES = ["q", "articulo", "almacen", "estado", "ubicacion"] as const;
const MINIMO_BUSQUEDA = 2;

/** Qué tarjeta del resumen corresponde a los filtros de la dirección. */
function tarjetaActiva(ubicacion: string, estado: string): ClaveResumen {
  if (ubicacion === "ALMACEN" || ubicacion === "TRABAJADOR" || ubicacion === "TRANSITO") return ubicacion;
  if (estado === "NO_APTO" && !ubicacion) return "NO_APTO";
  return "total";
}

export default function SeguimientoDePiezas() {
  const { puede } = useSesion();
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);

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
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaSeguimiento>("/seguimiento/piezas", { ...parametros, pagina, tamano: TAMANO_SEGUIMIENTO }, signal),
    JSON.stringify([parametros, pagina]),
  );
  const { datos, cargando, error } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;

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
    quitarTodos();
  }

  const chips: { clave: (typeof CLAVES)[number]; texto: string }[] = [];
  if (valores.articulo) chips.push({ clave: "articulo", texto: `Artículo: ${articuloPrimero ?? nombreArticulo ?? "elegido"}` });
  if (alcance.todos && valores.almacen) {
    chips.push({ clave: "almacen", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen) ?? "elegido"}` });
  }
  if (valores.estado) chips.push({ clave: "estado", texto: `Estado: ${textoDeOpcion(OPCIONES_ESTADO.map(({ valor, texto }) => ({ valor, texto })), valores.estado) ?? valores.estado}` });
  if (valores.ubicacion) chips.push({ clave: "ubicacion", texto: `Lugar: ${textoDeOpcion(OPCIONES_UBICACION, valores.ubicacion) ?? valores.ubicacion}` });
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
        descripcion={hayFiltros ? "Prueba con otra palabra o quita algún filtro." : "Todavía no hay piezas que mostrar."}
        accion={
          hayFiltros ? (
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
    <Pantalla titulo="Seguimiento de piezas" descripcion="Dónde está cada pieza y quién la tiene: busca un artículo y ve todas sus piezas.">
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
            valores={{ estado: valores.estado, ubicacion: valores.ubicacion, almacen: valores.almacen }}
            activos={[valores.estado, valores.ubicacion, alcance.todos ? valores.almacen : ""].filter(Boolean).length}
            alAplicar={(v) => cambiar({ estado: v.estado, ubicacion: v.ubicacion, almacen: alcance.todos ? v.almacen : null })}
            alLimpiar={() => cambiar({ estado: null, ubicacion: null, almacen: null })}
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
    </Pantalla>
  );
}
