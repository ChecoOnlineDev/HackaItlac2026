import { CircleCheckIcon, PrinterIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";
import { FolioQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { ValeImprimible } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import type { ValeConfirmadoApi, ValeDetalleApi } from "./tipos";
import { aValeImprimible } from "./vale-adaptador";

interface PropiedadesResultadoEntrega {
  vale: ValeConfirmadoApi;
  /** La firma que se acaba de capturar, para el vale impreso (el servidor no la devuelve). */
  firmaImagen?: string | null;
  /** Qué se guardó, para el título y el pie del QR. Por omisión una entrega. */
  titulo?: string;
  nombreVale?: string;
}

/**
 * Resultado de una entrega ya guardada por el servidor: folio en grande, QR del vale, "Imprimir" y
 * debajo el vale tal como saldrá en papel. "Nueva entrega" va en la acción principal de la pantalla.
 */
export function ResultadoEntrega({ vale, firmaImagen, titulo = "Entrega guardada", nombreVale = "Vale de entrega" }: PropiedadesResultadoEntrega) {
  const [detalle, setDetalle] = useState<ValeDetalleApi | null>(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    let vivo = true;
    apiGet<ValeDetalleApi>(`/vales/${vale.id}`)
      .then((d) => {
        if (vivo) setDetalle(d);
      })
      .catch(() => {
        if (vivo) setFallo(true);
      });
    return () => {
      vivo = false;
    };
  }, [vale.id]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_1fr] lg:items-start">
      <section aria-label={titulo} className="flex flex-col items-center gap-4 rounded-xl border bg-card p-6">
        <p role="status" className="flex items-center gap-2 text-base font-semibold text-semaforo-verde">
          <CircleCheckIcon aria-hidden="true" className="size-6" strokeWidth={3} />
          <span className="text-foreground">{titulo}</span>
        </p>
        <FolioQR folio={vale.folio} valor={urlDeVale(vale.token)} texto={`${nombreVale} · ${formatearFechaHora(vale.creado_en)}`} />
        <Boton variante="normal" className="w-full" onClick={() => window.print()} disabled={!detalle}>
          <PrinterIcon aria-hidden="true" />
          Imprimir
        </Boton>
        {fallo ? <p className="text-sm text-muted-foreground">No pudimos preparar el vale para imprimir. Ábrelo desde “Mis movimientos de hoy”.</p> : null}
      </section>

      <div className="min-w-0">
        {detalle ? (
          <ValeImprimible vale={aValeImprimible(detalle, firmaImagen)} botonImprimir={false} />
        ) : fallo ? null : (
          <Cargando variante="en-linea" texto="Preparando el vale…" />
        )}
      </div>
    </div>
  );
}
