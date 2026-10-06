import { CircleCheckIcon, DownloadIcon, InfoIcon, TriangleAlertIcon } from "lucide-react";
import { Link } from "react-router";

import { Boton } from "~/componentes/ui/boton";
import type { FilaError, ImportacionApi } from "./tipos";

interface PropiedadesResultadoImportacion {
  resultado: ImportacionApi;
  /** Las filas que no entraron: las de la respuesta o, si el lote ya estaba guardado, las de la revisión. */
  filasError: FilaError[];
  alDescargarErrores: (filas: FilaError[]) => void;
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: number }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-2xl border p-3">
      <dt className="text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className="text-xl font-semibold tabular-nums">{valor.toLocaleString("es-MX")}</dd>
    </div>
  );
}

/** Resultado de una importación ya guardada por el servidor: lo creado, los vales de entrada con su folio y las filas que no entraron. */
export function ResultadoImportacion({ resultado, filasError, alDescargarErrores }: PropiedadesResultadoImportacion) {
  const { resumen } = resultado;
  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Importación guardada" className="flex flex-col gap-3 rounded-2xl border border-semaforo-verde p-5">
        <p role="status" className="flex items-center gap-2 text-lg font-semibold">
          <CircleCheckIcon aria-hidden="true" className="size-7 text-semaforo-verde" strokeWidth={3} />
          {resultado.repetida ? "Esta importación ya estaba guardada" : "Importación guardada"}
        </p>
        {resultado.repetida ? (
          <p className="flex items-start gap-2 text-base">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
            Ya se había guardado antes con los mismos vales. No se duplicó nada.
          </p>
        ) : null}
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Dato etiqueta="Filas importadas" valor={resumen.filas_importadas} />
          {resultado.repetida ? null : <Dato etiqueta="Artículos nuevos" valor={resumen.articulos_creados} />}
          {resultado.repetida || resumen.existentes === undefined ? null : <Dato etiqueta="Artículos que ya existían (sumados)" valor={resumen.existentes} />}
          {resultado.repetida || !resumen.unidos ? null : <Dato etiqueta="Filas unidas" valor={resumen.unidos} />}
          {resultado.repetida || !resumen.excluidas ? null : <Dato etiqueta="Filas excluidas" valor={resumen.excluidas} />}
          <Dato etiqueta="Vales de entrada" valor={resumen.vales} />
          <Dato etiqueta="Piezas" valor={resumen.piezas} />
          <Dato etiqueta="Unidades" valor={resumen.unidades} />
          {resultado.repetida ? null : <Dato etiqueta="Filas con error (no entraron)" valor={resumen.filas_con_error} />}
        </dl>
      </section>

      {resultado.avisos.length > 0 ? (
        <ul aria-label="Avisos" className="flex flex-col gap-2">
          {resultado.avisos.map((a, i) => (
            <li key={i} className="flex items-start gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">
              <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-amarillo" />
              <span>
                <span className="sr-only">Aviso: </span>
                {a}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      <section aria-labelledby="vales-titulo" className="flex flex-col gap-3">
        <h2 id="vales-titulo" className="text-lg font-semibold">
          Vales de entrada
        </h2>
        <ul className="flex flex-col gap-2">
          {resultado.vales.map((v) => (
            <li key={v.id}>
              <Link
                to={`/vales/${v.id}`}
                className="flex min-h-12 flex-col justify-center rounded-2xl border bg-card p-3 transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >
                <span className="text-base font-semibold tracking-wide text-marino">{v.folio}</span>
                <span className="text-sm text-muted-foreground">
                  {v.almacen.nombre} · {v.renglones} {v.renglones === 1 ? "renglón" : "renglones"} · {v.piezas} {v.piezas === 1 ? "pieza" : "piezas"} · {v.unidades} {v.unidades === 1 ? "unidad" : "unidades"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">Cada vale queda en el historial. Ábrelo para verlo o imprimirlo.</p>
      </section>

      {resultado.articulos_creados.length > 0 ? (
        <details className="rounded-2xl border p-3">
          <summary className="flex min-h-12 cursor-pointer items-center text-base font-semibold">Artículos nuevos creados ({resultado.articulos_creados.length})</summary>
          <ul className="mt-2 flex flex-col divide-y">
            {resultado.articulos_creados.map((a) => (
              <li key={a.id} className="flex flex-col py-2 text-base">
                <span className="font-semibold">
                  {a.nombre} <span className="font-normal text-muted-foreground">· {a.codigo}</span>
                </span>
                <span className="text-muted-foreground">
                  {a.categoria} · {a.control === "PIEZA" ? "Por pieza" : "Por cantidad"}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {filasError.length > 0 ? (
        <section aria-labelledby="sin-entrar-titulo" className="flex flex-col gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/5 p-4">
          <h2 id="sin-entrar-titulo" className="text-lg font-semibold">
            {filasError.length} {filasError.length === 1 ? "fila no entró" : "filas no entraron"}
          </h2>
          <p className="text-base">Descárgalas, corrígelas en Excel y vuelve a importarlas.</p>
          <Boton variante="contorno" className="self-start" onClick={() => alDescargarErrores(filasError)}>
            <DownloadIcon aria-hidden="true" />
            Descargar filas con error
          </Boton>
        </section>
      ) : null}
    </div>
  );
}
