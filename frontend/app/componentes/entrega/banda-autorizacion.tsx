import { CircleCheckIcon, CircleXIcon, ClockIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import type { AutorizacionBorrador } from "./borrador";

interface PropiedadesBandaAutorizacion {
  autorizacion: AutorizacionBorrador;
  /** Quita los renglones que se pidió autorizar y deja la solicitud (flujo 7, A-07). */
  alQuitarRenglones: () => void;
  deshabilitado?: boolean;
}

/**
 * Estado de la solicitud de autorización: en espera (con indicador), autorizada, rechazada o vencida.
 * La pantalla consulta al servidor cada 3 segundos mientras está en espera.
 */
export function BandaAutorizacion({ autorizacion, alQuitarRenglones, deshabilitado }: PropiedadesBandaAutorizacion) {
  const { estado } = autorizacion;
  const [ahora, setAhora] = useState(Date.now());
  useEffect(() => {
    if (estado !== "PENDIENTE") return;
    const timer = window.setInterval(() => setAhora(Date.now()), 10000);
    return () => clearInterval(timer);
  }, [estado]);

  if (estado === "PENDIENTE") {
    return (
      <section aria-label="Autorización en espera" className="flex flex-col gap-3 rounded-2xl border border-semaforo-naranja bg-semaforo-naranja/10 p-4">
        <p className="flex items-center gap-2 text-base font-semibold">
          <ClockIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-naranja" />
          En espera del supervisor
        </p>
        <Cargando variante="en-linea" texto="Esperando su respuesta…" className="justify-start p-0" />
        <p className="text-sm text-muted-foreground">Solicitud registrada. Vence a las {formatearFechaHora(autorizacion.vence_en).slice(11)}.</p>
        {autorizacion.avisados === 0 ? <p className="text-sm font-semibold">Ningún supervisor tiene los avisos activos: búscalo o llámalo.</p> : null}
        {autorizacion.solicitado_en && ahora - autorizacion.solicitado_en >= 300000 ? <p className="text-sm">El supervisor aún no responde. Puedes buscarlo para que revise con su PIN.</p> : null}
        <Boton variante="contorno" onClick={alQuitarRenglones} disabled={deshabilitado}>
          Quitar renglón y continuar
        </Boton>
      </section>
    );
  }

  if (estado === "APROBADA" || estado === "USADA") {
    return (
      <p role="status" className="flex items-center gap-2 rounded-2xl border border-semaforo-verde bg-semaforo-verde/10 p-3 text-sm font-semibold">
        <CircleCheckIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-verde" />
        Autorizado{autorizacion.resuelta_por ? ` por ${autorizacion.resuelta_por}` : ""}.
      </p>
    );
  }

  return (
    <section
      role="alert"
      aria-label="Autorización no concedida"
      className="flex flex-col gap-3 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4"
    >
      <p className="flex items-center gap-2 text-base font-semibold">
        <CircleXIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-rojo" />
        {estado === "RECHAZADA" ? "El supervisor rechazó la solicitud." : "La solicitud venció sin respuesta."}
      </p>
      <p className="text-base">Quita el renglón para entregar lo demás, o vuelve a pedir la autorización.</p>
      <Boton variante="contorno" onClick={alQuitarRenglones} disabled={deshabilitado}>
        Quitar renglón y continuar
      </Boton>
    </section>
  );
}
