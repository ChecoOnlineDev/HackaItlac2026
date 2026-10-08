import { cn } from "cn";
import { DownloadIcon, PackageIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiGet, descargarCsv } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { FiltroLista, NotaAlcance, textoDeOpcion, useAlcance } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro } from "~/componentes/reportes/listas";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Boton } from "~/componentes/ui/boton";
import { aviso } from "~/componentes/ui/aviso";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { useSesion } from "~/sesion/sesion";
import { TablaCantidad, TarjetasCantidad } from "./lista-cantidad";
import { TAMANO_SEGUIMIENTO, type PaginaCantidad } from "./tipos";

const CLAVES = ["q", "articulo", "almacen"] as const;
const MINIMO_BUSQUEDA = 2;
const numero = new Intl.NumberFormat("es-MX");

function Cifra({ valor, titulo }: { valor: number; titulo: string }) {
  return (
    <li className="flex min-h-16 flex-col items-start justify-center gap-0.5 rounded-2xl border bg-card px-4 py-2.5 shadow-xs sm:min-h-20 sm:py-3">
      <span className="text-xl leading-none font-semibold text-marino tabular-nums sm:text-2xl">{numero.format(valor)}</span>
      <span className="text-sm text-muted-foreground">{titulo}</span>
    </li>
  );
}

/**
 * SG-01: pestaña «Por cantidad». Lo que no se controla pieza por pieza (guantes, flexómetros...) y
 * está en resguardo de un trabajador: cuánto, desde cuándo y con qué vale.
 */
export function PestanaCantidad() {
  const { puede } = useSesion();
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const { valores, pagina, cambiar, cambiarPagina } = useFiltrosUrl(CLAVES);

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
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaCantidad>("/seguimiento/cantidad", { ...parametros, pagina, tamano: TAMANO_SEGUIMIENTO }, signal),
    JSON.stringify([parametros, pagina]),
  );
  const { datos, cargando, error } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;

  const [descargando, setDescargando] = useState(false);
  async function descargar() {
    setDescargando(true);
    try {
      await descargarCsv("/seguimiento/cantidad", parametros, "seguimiento-por-cantidad.csv");
    } catch (causa) {
      aviso({ titulo: "No se pudo descargar el archivo", descripcion: mensajeDeError(causa), tipo: "error" });
    } finally {
      setDescargando(false);
    }
  }

  const chips: { clave: (typeof CLAVES)[number]; texto: string }[] = [];
  if (alcance.todos && valores.almacen) {
    chips.push({ clave: "almacen", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen) ?? "elegido"}` });
  }
  const hayFiltros = chips.length > 0 || buscaConTexto !== "";

  function limpiar() {
    setTexto("");
    qEnUrl.current = "";
    cambiar({ q: null, articulo: null, almacen: null });
  }

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
        icono={PackageIcon}
        titulo="Nadie tiene artículos por cantidad"
        descripcion={hayFiltros ? "Prueba con otra palabra o quita algún filtro." : "Cuando se entregue algo por cantidad, como guantes o flexómetros, aparecerá aquí con el trabajador."}
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
    const comunes = { renglones: elementos, puedeVerTrabajador: puede("trabajadores.ver"), puedeVerArticulo: puede("catalogo.ver"), puedeVerVale: puede("vales.ver") };
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", cargando && "opacity-60")} aria-busy={cargando}>
        <div className="w-0 min-w-full">
          <TablaCantidad {...comunes} />
        </div>
        <TarjetasCantidad {...comunes} />
        <Paginador pagina={pagina} tamano={TAMANO_SEGUIMIENTO} total={total} alCambiar={cambiarPagina} ocupado={cargando} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <CampoBusqueda
          etiqueta="Buscar por artículo o trabajador"
          placeholder="Buscar artículo o trabajador"
          value={texto}
          alCambiar={setTexto}
          claseContenedor="min-w-64"
          className="h-12 rounded-xl text-base"
        />
        {alcance.todos && almacenes.disponible ? (
          <HojaFiltros
            valores={{ almacen: valores.almacen }}
            activos={valores.almacen ? 1 : 0}
            alAplicar={(v) => cambiar({ almacen: v.almacen || null })}
            alLimpiar={() => cambiar({ almacen: null })}
          >
            {(borrador, cambiarBorrador) => (
              <FiltroLista
                etiqueta="Almacén que entregó"
                vacio="Todos los almacenes"
                valor={borrador.almacen}
                opciones={almacenes.opciones}
                alCambiar={(v) => cambiarBorrador({ almacen: v })}
              />
            )}
          </HojaFiltros>
        ) : null}
        <Boton variante="contorno" cargando={descargando} disabled={!datos || total === 0 || Boolean(error)} onClick={descargar}>
          {descargando ? null : <DownloadIcon aria-hidden="true" />}
          Descargar CSV
        </Boton>
      </div>

      {texto.trim().length === 1 ? <p className="text-sm text-muted-foreground">Escribe al menos dos caracteres para buscar.</p> : null}

      {datos ? (
        <ul aria-label="Resumen por cantidad" className={cn("grid grid-cols-3 gap-3 transition-opacity", cargando && "opacity-60")}>
          <Cifra valor={datos.resumen.unidades} titulo="Unidades en resguardo" />
          <Cifra valor={datos.resumen.articulos} titulo={datos.resumen.articulos === 1 ? "artículo por cantidad" : "artículos por cantidad"} />
          <Cifra valor={datos.resumen.trabajadores} titulo={datos.resumen.trabajadores === 1 ? "trabajador" : "trabajadores"} />
        </ul>
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
        </ul>
      ) : null}

      <div className="flex flex-col gap-1 text-xs text-muted-foreground">
        <NotaAlcance almacen={alcance.almacen} />
        <p>Muestra lo que cada trabajador tiene en resguardo y se controla por cantidad. Las herramientas con serie están en la pestaña Piezas.</p>
      </div>

      <p className="text-sm font-semibold" aria-live="polite">
        {datos && !error ? `${total} ${total === 1 ? "renglón" : "renglones"}` : " "}
      </p>

      {contenido}
    </div>
  );
}
