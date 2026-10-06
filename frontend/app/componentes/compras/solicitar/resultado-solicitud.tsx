import { CircleCheckIcon, ListChecksIcon, PlusIcon } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link } from "react-router";

import { Boton } from "~/componentes/ui/boton";
import { InsigniaEstadoCompra } from "./insignias";
import { ResumenSolicitud } from "./resumen";
import type { SolicitudCompra } from "./tipos";

interface Propiedades {
  solicitud: SolicitudCompra;
  alPedirOtra: () => void;
}

/** La solicitud ya quedó registrada: folio en grande, resumen y a dónde ir. */
export function ResultadoSolicitud({ solicitud, alPedirOtra }: Propiedades) {
  const titulo = useRef<HTMLHeadingElement>(null);
  // La pantalla anterior era larga: se lleva la vista y el foco al aviso para que se lea desde arriba.
  useEffect(() => {
    titulo.current?.focus();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="solicitud-enviada" className="flex flex-col items-center gap-4 rounded-2xl border border-semaforo-verde p-6 text-center">
        <h2
          id="solicitud-enviada"
          ref={titulo}
          tabIndex={-1}
          className="flex scroll-mt-20 items-center gap-2 text-lg font-semibold text-marino outline-none"
        >
          <CircleCheckIcon aria-hidden="true" className="size-7 text-semaforo-verde" strokeWidth={3} />
          Solicitud enviada
        </h2>
        <div className="flex flex-col items-center gap-1">
          <p className="text-sm text-muted-foreground">Folio</p>
          <p className="text-2xl font-bold tracking-tight text-marino tabular-nums">{solicitud.folio}</p>
          <InsigniaEstadoCompra estado={solicitud.estado} className="mt-1" />
        </div>
        <p className="max-w-sm text-sm text-muted-foreground">
          Compras la va a revisar. Puedes ver cómo avanza en “Compras urgentes”, y cancelarla mientras siga pendiente.
        </p>
      </section>

      <ResumenSolicitud
        que={solicitud.articulo?.nombre ?? solicitud.descripcion}
        codigo={solicitud.articulo?.codigo}
        cantidad={solicitud.cantidad}
        motivo={solicitud.motivo}
        urgencia={solicitud.urgencia}
        almacen={`${solicitud.almacen.nombre} (${solicitud.almacen.clave})`}
      />

      <div className="flex flex-col gap-3">
        <Boton variante="principal" render={<Link to="/compras/mias" />} nativeButton={false}>
          <ListChecksIcon aria-hidden="true" />
          Ver mis solicitudes
        </Boton>
        <Boton variante="contorno" onClick={alPedirOtra}>
          <PlusIcon aria-hidden="true" />
          Pedir otra
        </Boton>
      </div>
    </div>
  );
}
