import { cn } from "cn";
import { IdCardIcon, PackageIcon, PrinterIcon, SearchIcon, TagIcon, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Checkbox } from "~/components/ui/checkbox";
import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { HojaEtiquetas, ETIQUETAS_POR_HOJA } from "~/componentes/dominio/hoja-etiquetas";
import type { EtiquetaElemento } from "~/componentes/dominio/tipos";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Input } from "~/components/ui/input";

export const handle: ManejadorRuta = { permiso: "etiquetas.imprimir" };

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

  const [tipo, setTipo] = useState<TipoEtiqueta | null>(disponibles[0]?.tipo ?? null);
  const [elementos, setElementos] = useState<EtiquetaElemento[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busqueda, setBusqueda] = useState("");
  const [elegidos, setElegidos] = useState<ReadonlySet<string>>(new Set());
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (!tipo) return;
    const control = new AbortController();
    setElementos(null);
    setError(null);
    setElegidos(new Set());
    setBusqueda("");
    apiGet<RespuestaEtiquetas>("/etiquetas", { tipo }, control.signal)
      .then((r) => setElementos(r.elementos))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e);
      });
    return () => control.abort();
  }, [tipo, intento]);

  const visibles = useMemo(() => {
    if (!elementos) return [];
    const q = busqueda.trim().toLowerCase();
    return q ? elementos.filter((e) => e.texto.toLowerCase().includes(q) || e.codigo.toLowerCase().includes(q)) : elementos;
  }, [elementos, busqueda]);

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

  const hojas = Math.max(1, Math.ceil(seleccionadas.length / ETIQUETAS_POR_HOJA));

  return (
    <Pantalla titulo="Etiquetas" descripcion="Elige qué imprimir y revisa la hoja antes de mandarla a la impresora.">
      <div className="flex flex-col gap-6 pb-28 lg:pb-0">
        <div role="radiogroup" aria-label="Qué imprimir" className="grid gap-3 sm:grid-cols-3">
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

        {error !== null ? (
          <EstadoError
            error={error}
            alReintentar={esErrorApi(error) && error.sinPermiso ? undefined : () => setIntento((n) => n + 1)}
          />
        ) : elementos === null ? (
          <Cargando variante="en-linea" texto="Cargando la lista" />
        ) : elementos.length === 0 ? (
          <EstadoVacio icono={PrinterIcon} titulo="No hay nada que imprimir" descripcion="Cuando haya elementos de este tipo, aparecerán aquí." />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
            <section aria-label="Elementos" className="flex min-w-0 flex-col gap-3">
              <div className="relative">
                <SearchIcon aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="search"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre o código"
                  aria-label="Buscar por nombre o código"
                  className="h-12 rounded-lg pl-10 text-base md:text-base"
                />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-base" aria-live="polite">
                  <span className="font-semibold">{seleccionadas.length}</span> de {elementos.length} elegidas
                </p>
                <Boton variante="contorno" onClick={alternarTodas} disabled={visibles.length === 0}>
                  {todasVisiblesElegidas ? "Quitar selección" : busqueda.trim() ? "Seleccionar lo que se ve" : "Seleccionar todo"}
                </Boton>
              </div>
              {visibles.length === 0 ? (
                <p className="rounded-xl border p-4 text-base text-muted-foreground">No encontramos nada con “{busqueda.trim()}”.</p>
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
                          <span className="font-mono text-sm text-muted-foreground">{e.codigo}</span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section aria-label="Vista previa de la hoja" className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xl">Vista previa</h2>
                {seleccionadas.length > 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {seleccionadas.length === 1 ? "1 etiqueta" : `${seleccionadas.length} etiquetas`} · {hojas === 1 ? "1 hoja carta" : `${hojas} hojas carta`}
                  </p>
                ) : null}
              </div>
              {seleccionadas.length === 0 ? (
                <EstadoVacio icono={TagIcon} titulo="Elige qué etiquetas imprimir" descripcion="Marca elementos de la lista y aquí verás cómo queda la hoja." />
              ) : (
                <div className="rounded-xl border bg-muted p-3">
                  <HojaEtiquetas etiquetas={seleccionadas} />
                </div>
              )}
            </section>
          </div>
        )}
      </div>

      {elementos && elementos.length > 0 ? (
        <AccionPrincipal nota={seleccionadas.length === 0 ? "Elige al menos una etiqueta para imprimir." : undefined}>
          <Boton variante="principal" disabled={seleccionadas.length === 0} onClick={() => window.print()}>
            <PrinterIcon aria-hidden="true" />
            Imprimir
          </Boton>
        </AccionPrincipal>
      ) : null}
    </Pantalla>
  );
}
