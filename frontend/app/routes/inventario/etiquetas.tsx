import { cn } from "cn";
import { DownloadIcon, IdCardIcon, PackageIcon, PrinterIcon, TagIcon, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";

import { Checkbox } from "~/components/ui/checkbox";
import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { CREDENCIALES_POR_HOJA, HojaCredenciales, SelectorModoCredencial, type ModoCredencial } from "~/componentes/dominio/credencial";
import { HojaEtiquetas } from "~/componentes/dominio/hoja-etiquetas";
import type { EtiquetaElemento } from "~/componentes/dominio/tipos";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Campo } from "~/componentes/ui/campo";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { coincideBusqueda, useRetraso } from "~/componentes/ui/busqueda-diferida";
import { hojasEtiquetas, type FormatoEtiqueta } from "~/componentes/dominio/etiquetas-medidas";
import { esAppNativa } from "~/movil/plataforma";

export const handle: ManejadorRuta = { permiso: "etiquetas.imprimir", dispositivo: "computadora" };

type TipoEtiqueta = "credenciales" | "piezas" | "estantes";

interface RespuestaEtiquetas extends Pagina<EtiquetaElemento> {}

const TIPOS: { tipo: TipoEtiqueta; nombre: string; ayuda: string; icono: LucideIcon }[] = [
  { tipo: "credenciales", nombre: "Credenciales", ayuda: "Un QR por trabajador", icono: IdCardIcon },
  { tipo: "piezas", nombre: "Piezas", ayuda: "Un QR por herramienta o equipo", icono: TagIcon },
  { tipo: "estantes", nombre: "Estantes", ayuda: "Un QR por artículo de cantidad", icono: PackageIcon },
];

export default function Etiquetas() {
  // `etiquetas.imprimir` basta para los tres tipos (la ruta ya lo exige; el servidor lo verifica).
  const disponibles = TIPOS;

  // Al llegar desde la importación: `?tipo=piezas&codigos=A,B` abre ese tipo con esas piezas ya elegidas.
  const [params] = useSearchParams();
  const ubicacion = useLocation();
  const tipoInicial = TIPOS.find((t) => t.tipo === params.get("tipo"))?.tipo ?? disponibles[0]?.tipo ?? null;
  const [codigosInicial] = useState<ReadonlySet<string>>(() => {
    const codigos = (ubicacion.state as { codigos?: unknown } | null)?.codigos;
    return new Set(Array.isArray(codigos) ? codigos.filter((c): c is string => typeof c === "string") : (params.get("codigos") ?? "").split(",").filter(Boolean));
  });
  const [tipo, setTipo] = useState<TipoEtiqueta | null>(tipoInicial);
  const [elementos, setElementos] = useState<EtiquetaElemento[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busqueda, setBusqueda] = useState("");
  const [elegidos, setElegidos] = useState<ReadonlySet<string>>(new Set());
  const [intento, setIntento] = useState(0);
  // Solo en credenciales: la tarjeta completa o únicamente el código QR.
  const [modo, setModo] = useState<ModoCredencial>("completa");
  const [formato, setFormato] = useState<FormatoEtiqueta>(18);
  const [inicio, setInicio] = useState(1);
  const [altaDesde, setAltaDesde] = useState("");
  const [altaHasta, setAltaHasta] = useState("");
  const [progreso, setProgreso] = useState<{ hoja: number; total: number } | null>(null);
  const [errorPdf, setErrorPdf] = useState<unknown>(null);
  const [advertenciaQr, setAdvertenciaQr] = useState(false);
  const cancelarPdf = useRef<AbortController | null>(null);
  const busquedaAplicada = useRetraso(busqueda);
  const articuloId = tipo === "piezas" ? params.get("articulo_id") : null;
  const loteId = tipo === "piezas" ? params.get("lote_id") : null;
  useEffect(() => () => cancelarPdf.current?.abort(), []);
  useEffect(() => { setAdvertenciaQr(false); }, [formato, elegidos, modo]);

  useEffect(() => {
    if (!tipo) return;
    const control = new AbortController();
    setElementos(null);
    setError(null);
    setElegidos(new Set());
    setBusqueda("");
    apiGet<RespuestaEtiquetas>("/etiquetas", { tipo, articulo_id: articuloId || undefined, lote_id: loteId || undefined, alta_desde: tipo === "credenciales" ? altaDesde || undefined : undefined, alta_hasta: tipo === "credenciales" ? altaHasta || undefined : undefined }, control.signal)
      .then((r) => {
        if (control.signal.aborted) return;
        setElementos(r.elementos);
        // Solo el tipo pedido por la dirección preselecciona.
        if (tipo === tipoInicial && codigosInicial.size > 0) setElegidos(new Set(r.elementos.filter((e) => codigosInicial.has(e.codigo)).map((e) => e.codigo)));
        else if (articuloId || loteId || altaDesde || altaHasta) setElegidos(new Set(r.elementos.map((e) => e.codigo)));
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e);
      });
    return () => control.abort();
  }, [tipo, intento, articuloId, loteId, altaDesde, altaHasta]);

  const visibles = useMemo(() => {
    if (!elementos) return [];
    return busquedaAplicada.trim() ? elementos.filter((e) => coincideBusqueda(`${e.texto} ${e.codigo}`, busquedaAplicada)) : elementos;
  }, [elementos, busquedaAplicada]);

  const seleccionadas = useMemo(() => (elementos ?? []).filter((e) => elegidos.has(e.codigo)), [elementos, elegidos]);
  const todasVisiblesElegidas = visibles.length > 0 && visibles.every((e) => elegidos.has(e.codigo));

  const alternar = useCallback((codigo: string) => {
    setElegidos((prev) => {
      const copia = new Set(prev);
      if (copia.has(codigo)) copia.delete(codigo);
      else copia.add(codigo);
      return copia;
    });
  }, []);

  const alternarTodas = () => {
    setElegidos((prev) => {
      const copia = new Set(prev);
      if (todasVisiblesElegidas) for (const e of visibles) copia.delete(e.codigo);
      else for (const e of visibles) copia.add(e.codigo);
      return copia;
    });
  };

  if (disponibles.length === 0) {
    return (
      <Pantalla titulo="Etiquetas" descripcion="Hojas de códigos QR para imprimir.">
        <EstadoVacio icono={PrinterIcon} titulo="No tienes permiso para imprimir etiquetas de ningún tipo" descripcion="Pide acceso a quien administra el sistema." />
      </Pantalla>
    );
  }

  const tarjetas = tipo === "credenciales" && modo === "completa";
  const porHoja = tarjetas ? CREDENCIALES_POR_HOJA : formato;
  const inicioValido = Math.max(1, Math.min(inicio, porHoja));
  const hojas = hojasEtiquetas(seleccionadas.length, porHoja, inicioValido);
  const descargar = async () => {
    const actual = new AbortController();
    cancelarPdf.current = actual;
    setErrorPdf(null);
    setProgreso({ hoja: 0, total: hojas });
    try {
      const { descargarEtiquetasPdf, qrMuyPequeno } = await import("~/componentes/dominio/pdf-etiquetas");
      if (!tarjetas && !advertenciaQr && seleccionadas.some((e) => qrMuyPequeno(e.codigo, formato))) {
        setAdvertenciaQr(true);
        return;
      }
      await descargarEtiquetasPdf(seleccionadas, { tipo: tipo!, formato, completas: tarjetas, inicio: inicioValido, signal: actual.signal, progreso: (hoja, total) => setProgreso({ hoja, total }) });
    } catch (causa) {
      if (!actual.signal.aborted) setErrorPdf(causa);
    } finally { if (cancelarPdf.current === actual) setProgreso(null); }
  };
  const datosTarjetas = seleccionadas.flatMap((e) =>
    e.nombre && e.numero_empleado ? [{ codigo: e.codigo, nombre: e.nombre, puesto: e.puesto, numero_empleado: e.numero_empleado }] : [],
  );

  return (
    <Pantalla titulo="Etiquetas" descripcion="Elige qué imprimir y revisa la hoja antes de mandarla a la impresora.">
      <div className="flex flex-col gap-6 pb-28 lg:pb-0">
        <div role="radiogroup" aria-label="Tipo de etiqueta" className="grid gap-3 sm:grid-cols-3">
          {disponibles.map(({ tipo: t, nombre, ayuda, icono: Icono }) => {
            const activo = tipo === t;
            return (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={activo}
                onClick={() => setTipo(t)}
                className={cn(
                  "flex min-h-14 items-center gap-3 rounded-xl border-2 p-3 text-left transition-colors duration-150",
                  activo ? "border-primary bg-accent" : "border-border bg-card hover:bg-muted",
                )}
              >
                <Icono aria-hidden="true" className="size-6 shrink-0 text-marino" />
                <span className="flex flex-col">
                  <span className="text-lg leading-tight font-semibold">{nombre}</span>
                  <span className="text-sm text-muted-foreground">{ayuda}</span>
                </span>
              </button>
            );
          })}
        </div>

        {tipo === "credenciales" ? <SelectorModoCredencial modo={modo} alCambiar={setModo} /> : null}
        <div className="flex flex-wrap items-end gap-3">
          {!tarjetas ? <label className="flex flex-col gap-1 text-sm font-medium">Formato<select className="min-h-11 rounded-lg border bg-background px-3" value={formato} onChange={(e) => { setFormato(Number(e.target.value) as FormatoEtiqueta); setInicio(1); }}><option value={9}>9 por hoja · QR grande</option><option value={18}>18 por hoja</option><option value={30}>30 por hoja</option></select></label> : null}
          <Campo etiqueta="Empezar en la etiqueta n.º" type="number" inputMode="numeric" min={1} max={porHoja} value={inicioValido} onChange={(e) => setInicio(Number(e.target.value) || 1)} claseContenedor="w-48" />
          {tipo === "credenciales" ? <><Campo etiqueta="Dados de alta desde" type="date" value={altaDesde} onChange={(e) => setAltaDesde(e.target.value)} /><Campo etiqueta="Hasta" type="date" value={altaHasta} min={altaDesde || undefined} onChange={(e) => setAltaHasta(e.target.value)} /></> : null}
        </div>

        {error !== null ? (
          <EstadoError
            error={error}
            alReintentar={esErrorApi(error) && error.sinPermiso ? undefined : () => setIntento((n) => n + 1)}
          />
        ) : elementos === null ? (
          <Esqueleto tipo="lista" />
        ) : elementos.length === 0 ? (
          <EstadoVacio icono={PrinterIcon} titulo="No hay nada que imprimir" descripcion="Cuando haya elementos de este tipo, aparecerán aquí." />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
            <section aria-label="Elementos" className="flex min-w-0 flex-col gap-3">
              <CampoBusqueda
                etiqueta="Buscar por nombre o código"
                value={busqueda}
                alCambiar={setBusqueda}
                placeholder="Buscar por nombre o código"
              />
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-base" aria-live="polite">
                  <span className="font-semibold">{seleccionadas.length}</span> de {elementos.length} elegidas
                </p>
                <Boton variante="contorno" onClick={alternarTodas} disabled={visibles.length === 0}>
                  {todasVisiblesElegidas ? "Quitar selección" : busqueda.trim() ? "Seleccionar lo que se ve" : "Seleccionar todo"}
                </Boton>
              </div>
              {visibles.length === 0 ? (
                <EstadoVacio icono={TagIcon} titulo={`No encontramos nada con “${busquedaAplicada.trim()}”`} accion={<Boton variante="contorno" onClick={() => setBusqueda("")}>Borrar búsqueda</Boton>} />
              ) : (
                <ul className="max-h-[60dvh] divide-y overflow-y-auto rounded-xl border">
                  {visibles.map((e) => (
                    <li key={e.codigo}>
                      <label className="flex min-h-14 cursor-pointer items-center gap-3 px-3 py-2 hover:bg-muted has-[:focus-visible]:bg-muted">
                        <Checkbox
                          checked={elegidos.has(e.codigo)}
                          onCheckedChange={() => alternar(e.codigo)}
                          className="size-6 rounded-md [&_svg]:size-4"
                        />
                        <span className="flex min-w-0 flex-col">
                          <span className="text-base leading-snug font-semibold wrap-break-word">{e.texto}</span>
                          <span className="tabular-nums text-sm text-muted-foreground">{e.codigo}</span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section aria-label="Vista previa de la hoja" className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-marino">Vista previa · primera hoja</h2>
                {seleccionadas.length > 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {seleccionadas.length === 1 ? (tarjetas ? "1 credencial" : "1 etiqueta") : `${seleccionadas.length} ${tarjetas ? "credenciales" : "etiquetas"}`} ·{" "}
                    {hojas === 1 ? "1 hoja carta" : `${hojas} hojas carta`}
                  </p>
                ) : null}
              </div>
              {seleccionadas.length === 0 ? (
                <EstadoVacio icono={TagIcon} titulo="Elige qué etiquetas imprimir" descripcion="Marca elementos de la lista y aquí verás cómo queda la hoja." />
              ) : (
                <div className="rounded-xl border bg-muted p-3">
                  {tarjetas ? <HojaCredenciales credenciales={datosTarjetas} inicio={inicioValido} /> : <HojaEtiquetas etiquetas={seleccionadas} formato={formato} inicio={inicioValido} />}
                </div>
              )}
            </section>
          </div>
        )}
      </div>

      {elementos && elementos.length > 0 ? (
        <AccionPrincipal nota={seleccionadas.length > 1000 ? `Puedes descargar hasta 1000 etiquetas en un PDF. Quita ${seleccionadas.length - 1000} o descárgalas en dos partes.` : progreso ? `Armando hoja ${progreso.hoja} de ${progreso.total}…` : seleccionadas.length === 0 ? "Elige al menos una etiqueta para imprimir." : undefined}>
          {errorPdf ? <EstadoError error={errorPdf} /> : null}
          {advertenciaQr ? <p role="status" className="rounded-lg border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">Los códigos largos quedan pequeños en este formato. Puedes elegir 18 por hoja para ampliarlos o descargar de todos modos y comprobar la lectura al imprimir.</p> : null}
          {progreso ? <Boton variante="contorno" onClick={() => cancelarPdf.current?.abort()}>Cancelar</Boton> : null}
          <Boton variante="principal" disabled={seleccionadas.length === 0 || seleccionadas.length > 1000 || progreso !== null} onClick={() => void descargar()}>
            <DownloadIcon aria-hidden="true" />
            {advertenciaQr ? "Descargar de todos modos" : esAppNativa() ? "Compartir PDF" : "Descargar PDF"}
          </Boton>
        </AccionPrincipal>
      ) : null}
    </Pantalla>
  );
}
