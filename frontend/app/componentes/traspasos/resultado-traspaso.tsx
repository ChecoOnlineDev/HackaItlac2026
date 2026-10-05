import { CircleCheckIcon, PrinterIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { apiGet } from "~/api/cliente";
import { FolioQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { ValeImprimible } from "~/componentes/dominio/vale-imprimible";
import { aValeImprimible } from "~/componentes/entrega/vale-adaptador";
import type { ValeConfirmadoApi, ValeDetalleApi } from "~/componentes/entrega/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";

interface PropiedadesResultadoTraspaso {
  vale: ValeConfirmadoApi;
  /** "Traspaso guardado", "Recepción guardada". */
  titulo: string;
  /** Bajo el folio: "Traspaso a Contratistas". */
  texto: string;
  /** Lo que sigue (por ejemplo "Lo que no marcaste sigue en camino"). */
  nota?: ReactNode;
}

/**
 * Resultado de un traspaso o una recepción ya guardados por el servidor: folio en grande, QR, "Imprimir" y
 * debajo el vale tal como saldrá en papel (el vale viaja con la carga). "Nuevo traspaso" va en la acción
 * principal de la pantalla.
 */
export function ResultadoTraspaso({ vale, titulo, texto, nota }: PropiedadesResultadoTraspaso) {
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
      <section aria-label={titulo} className="flex flex-col items-center gap-4 rounded-2xl border bg-card p-6 print:hidden">
        <p role="status" className="flex items-center gap-2 text-base font-semibold text-semaforo-verde">
          <CircleCheckIcon aria-hidden="true" className="size-6" strokeWidth={3} />
          <span className="text-foreground">{titulo}</span>
        </p>
        <FolioQR folio={vale.folio} valor={urlDeVale(vale.token)} texto={`${texto} · ${formatearFechaHora(vale.creado_en)}`} />
        {nota ? <div className="w-full text-base">{nota}</div> : null}
        <Boton variante="normal" className="w-full" onClick={() => window.print()} disabled={!detalle}>
          <PrinterIcon aria-hidden="true" />
          Imprimir
        </Boton>
        {fallo ? <p className="text-sm text-muted-foreground">No pudimos preparar el vale para imprimir. Ábrelo desde “Mis movimientos de hoy”.</p> : null}
      </section>

      <div className="min-w-0">
        {detalle ? <ValeImprimible vale={aValeImprimible(detalle)} botonImprimir={false} /> : fallo ? null : <Cargando variante="en-linea" texto="Preparando el vale…" />}
      </div>
    </div>
  );
}
