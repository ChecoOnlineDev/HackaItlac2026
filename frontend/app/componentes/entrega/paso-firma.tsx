import { EraserIcon } from "lucide-react";
import { useState } from "react";

import { FirmaPad } from "~/componentes/dominio/firma-pad";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import { LEYENDA_RESPONSABILIDAD } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import type { FirmaCapturada } from "./tipos";

interface PropiedadesPasoFirma {
  renglones: RenglonEvaluado[];
  firma: FirmaCapturada | null;
  alCambiarFirma: (firma: FirmaCapturada | null) => void;
  /** Bloquea la firma mientras se envía. */
  deshabilitado?: boolean;
}

/**
 * Paso 3 de la entrega: resumen de artículos, la leyenda de responsabilidad (F-02) y el recuadro de firma.
 * En horizontal (tableta o computadora) el resumen queda a la izquierda y la firma a la derecha.
 * Si la firma ya estaba guardada en el dispositivo (recarga o corte), se muestra su imagen con "Borrar".
 */
export function PasoFirma({ renglones, firma, alCambiarFirma, deshabilitado }: PropiedadesPasoFirma) {
  // Una firma que ya venía guardada no se puede volver a dibujar sobre el recuadro: se muestra su imagen.
  const [restaurada, setRestaurada] = useState(firma !== null);
  const total = renglones.reduce((suma, r) => suma + r.cantidad, 0);
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:items-start">
      <section aria-labelledby="resumen-entrega" className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 id="resumen-entrega" className="text-lg">
            Lo que recibe ({total})
          </h2>
          <ul className="flex flex-col divide-y rounded-2xl border bg-card">
            {renglones.map((r) => (
              <li key={r.codigo} className="flex items-baseline justify-between gap-3 px-3 py-2">
                <span className="min-w-0">
                  <span className="block font-semibold wrap-break-word">{r.articulo?.nombre ?? r.codigo}</span>
                  <span className="block text-sm text-muted-foreground">
                    {r.codigo}
                    {r.pieza?.numero_serie ? ` · Serie ${r.pieza.numero_serie}` : ""}
                  </span>
                </span>
                <span className="text-lg font-semibold tabular-nums">{r.cantidad}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="rounded-xl bg-muted p-4 text-sm leading-relaxed">{LEYENDA_RESPONSABILIDAD}</p>
      </section>

      <section aria-label="Firma del trabajador" className="flex flex-col gap-2">
        {restaurada && firma ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-base font-semibold">Firma del trabajador</p>
              <Boton variante="contorno" onClick={() => {
                  setRestaurada(false);
                  alCambiarFirma(null);
                }} disabled={deshabilitado}>
                <EraserIcon aria-hidden="true" />
                Borrar
              </Boton>
            </div>
            <div className="w-full max-w-[640px] overflow-hidden rounded-xl border-2 border-foreground bg-white">
              <img src={firma.imagen} alt="Firma capturada" className="block aspect-[2/1] w-full object-contain" />
            </div>
          </div>
        ) : (
          <FirmaPad
            deshabilitado={deshabilitado}
            onCambio={(vacia, imagen, trazo) => alCambiarFirma(vacia || !imagen ? null : { imagen, trazo })}
          />
        )}
      </section>
    </div>
  );
}
