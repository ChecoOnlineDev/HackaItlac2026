import { BanIcon, RotateCcwIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { BotonPdfVale } from "~/componentes/dominio/boton-pdf-vale";
import type { CabeceraPdf } from "~/componentes/dominio/pdf-vale";

import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Campo } from "~/componentes/ui/campo";
import { ValeImprimible } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesionActiva } from "~/sesion/sesion";
import { CancelarVale, esCancelable } from "./cancelar-vale";
import { sePuedeRehacer } from "./rehacer";
import type { ValeDetalleApi } from "./tipos";
import type { RenglonValeApi } from "./tipos";
import { RenglonesVale } from "./renglones-vale";
import { aValeImprimible } from "./vale-adaptador";

interface PropiedadesDetalleVale {
  /** `GET /api/vales/{id}` o `GET /api/vales/por-token/{token}`. */
  ruta: string;
}

/**
 * Detalle real de un vale (folio, renglones, responsable, QR) con "Imprimir". Quien puede cancelar ve
 * "Cancelar vale" y, en entregas y devoluciones, "Cancelar y rehacer" (K-05). Un vale cancelado muestra la
 * banda "Cancelado" con el motivo y el folio de su cancelación.
 */
export function DetalleVale({ ruta }: PropiedadesDetalleVale) {
  const { puede, sesion } = useSesionActiva();
  const { datos, cargando, error, recargar } = useConsulta((signal) => apiGet<CabeceraPdf & {relacionados?: {id: string|null;folio: string|null;texto: string}[]}>(ruta, { renglones: false }, signal), ruta);
  const [parametros] = useSearchParams(); const [texto, setTexto] = useState(parametros.get("q") ?? "");
  const [pagina, setPagina] = useState(1);
  const q = useRetraso(texto, 300);
  const filas = useConsulta((signal) => datos ? apiGet<{elementos: RenglonValeApi[];total: number}>(`/vales/${datos.id}/renglones`, {q,pagina,tamano:50}, signal) : Promise.resolve(null), `${datos?.id}|${q}|${pagina}`);
  const [impresion, setImpresion] = useState<ValeDetalleApi | null>(null);
  const [imprimiendo, setImprimiendo] = useState(false); const [errorImpresion, setErrorImpresion] = useState(false);
  useEffect(() => {setTexto(parametros.get("q") ?? "");setPagina(1);setImpresion(null);},[ruta,parametros.get("q")]);
  const [cancelando, setCancelando] = useState<{ rehacer: boolean } | null>(null);

  if (error) {
    const noExiste = esErrorApi(error) && error.status === 404;
    return (
      <EstadoError
        error={noExiste ? undefined : error}
        mensaje={noExiste ? "No encontramos ese vale. Revisa el código o el enlace." : undefined}
        alReintentar={noExiste ? undefined : recargar}
      />
    );
  }
  if (cargando && !datos) return <Cargando variante="en-linea" texto="Abriendo el vale…" />;
  if (!datos) return null;

  // `vales.cancelar` cubre los propios; `vales.cancelar_todos`, los de cualquiera (K-01). El servidor lo vuelve a verificar.
  const esPropio = datos.responsable.id === sesion.usuario.id;
  const puedeCancelar = puede("vales.cancelar_todos") || (puede("vales.cancelar") && esPropio);
  const mostrarCancelar = puedeCancelar && esCancelable(datos);
  return (
    <>
      <div className="print:hidden flex flex-wrap items-center gap-3 mb-4"><BotonPdfVale id={datos.id} />{datos.lote ? <BotonPdfVale id={datos.id} lote /> : null}<Boton variante="contorno" disabled={imprimiendo} onClick={() => { setImprimiendo(true); setErrorImpresion(false); void apiGet<ValeDetalleApi>(ruta).then((v) => { setImpresion(v); setTimeout(() => window.print(), 0); }).catch(() => setErrorImpresion(true)).finally(() => setImprimiendo(false)); }}>Imprimir</Boton>{errorImpresion ? <p role="alert">No pudimos preparar la impresión. Vuelve a intentar.</p> : null}</div>
      <div className="print:hidden"><ValeImprimible
        botonImprimir={false}
        vale={aValeImprimible({...datos, renglones: []})}
        acciones={
          mostrarCancelar ? (
            <div className="flex flex-wrap items-center gap-3">
              <Boton variante="contorno" onClick={() => setCancelando({ rehacer: false })}>
                <BanIcon aria-hidden="true" />
                Cancelar vale
              </Boton>
              {sePuedeRehacer(datos.tipo) ? (
                <Boton variante="contorno" onClick={() => setCancelando({ rehacer: true })}>
                  <RotateCcwIcon aria-hidden="true" />
                  Cancelar y rehacer
                </Boton>
              ) : null}
            </div>
          ) : null
        }
      /></div>
      {impresion ? <div className="hidden print:block"><ValeImprimible botonImprimir={false} vale={aValeImprimible(impresion)} /></div> : null}
      <div className="print:hidden flex flex-col gap-4 mt-5">
        {datos.lote ? <section className="rounded-xl border p-4"><p className="font-semibold">Parte {datos.lote.parte} de {datos.lote.partes} · {datos.lote.renglones} renglones · {datos.lote.unidades} unidades</p><div className="flex flex-wrap gap-3">{datos.lote.vales.map((v) => <Link key={v.id} to={`/vales/${v.id}`} className="underline">{v.folio}</Link>)}</div></section> : null}
        {datos.resumen ? <section className="rounded-xl border p-4"><h2 className="font-semibold">Resumen por categoría</h2><div className="grid gap-3 sm:grid-cols-3">{datos.resumen.categorias.map((c) => <div key={c.categoria.nombre}><p>{c.categoria.nombre}</p><p>{c.renglones} renglones · {c.unidades} unidades</p>{"valor" in c ? <p>{c.valor === null ? "No se muestra para no revelar el costo de un artículo" : `$${c.valor}`}</p> : null}</div>)}</div>{"valor_total" in datos.resumen ? <p className="mt-3">{datos.resumen.valor_total === null ? "Total no mostrado para proteger los costos individuales" : `Valor total: $${datos.resumen.valor_total}`}</p> : null}</section> : null}
        <Campo etiqueta="Buscar código, artículo o serie" value={texto} onChange={(e) => {setTexto(e.target.value);setPagina(1);}} />
        {filas.error ? <EstadoError error={filas.error} alReintentar={filas.recargar} /> : filas.cargando && !filas.datos ? <Cargando /> : filas.datos ? <><RenglonesVale filas={filas.datos.elementos} puedeVerPieza={puede("catalogo.ver")} /><div className="flex gap-3"><Boton variante="contorno" disabled={pagina === 1} onClick={() => setPagina((p) => p-1)}>Anterior</Boton><span>Página {pagina} · {filas.datos.total} renglones</span><Boton variante="contorno" disabled={pagina*50 >= filas.datos.total} onClick={() => setPagina((p) => p+1)}>Siguiente</Boton></div></> : null}
        {datos.relacionados?.length ? <section><h2 className="font-semibold">Vales relacionados</h2>{datos.relacionados.map((r,i) => <p key={r.id ?? i}>{r.id ? <Link className="underline" to={`/vales/${r.id}`}>{r.texto} · {r.folio}</Link> : r.texto}</p>)}</section> : null}
      </div>
      <CancelarVale
        vale={cancelando ? { id: datos.id, folio: datos.folio, tipo: datos.tipo, estado: datos.estado } : null}
        rehacer={cancelando?.rehacer ?? false}
        alCerrar={() => setCancelando(null)}
        alCancelar={recargar}
      />
    </>
  );
}
