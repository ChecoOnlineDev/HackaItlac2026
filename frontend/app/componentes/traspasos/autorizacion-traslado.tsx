import { CircleCheckIcon, CircleXIcon, ClockIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";
import { instanteUtc } from "~/componentes/consulta/formato";
import { reproducir } from "~/componentes/dominio/sonido";
import type { AutorizacionBorrador } from "~/componentes/entrega/borrador";
import type { AutorizacionApi } from "~/componentes/entrega/tipos";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";

/** Cada cuánto se pregunta al servidor mientras la solicitud espera (flujo 7, A-01). */
const CONSULTA_MS = 3000;

/**
 * Sigue una solicitud de traslado pendiente: consulta al servidor cada 3 segundos y avisa cuando se resuelve.
 * Devuelve cuántos milisegundos faltan para que venza, contados con la hora del servidor cuando la trae.
 */
export function useSeguirAutorizacion(
  autorizacion: AutorizacionBorrador | null,
  alResolver: (id: string, estado: AutorizacionBorrador["estado"], por: string | null) => void,
): number | null {
  const [desfaseMs, setDesfaseMs] = useState(0);
  const [ahora, setAhora] = useState(() => Date.now());
  const pendiente = autorizacion?.estado === "PENDIENTE";
  const id = autorizacion?.id;

  useEffect(() => {
    if (!pendiente || !id) return;
    let activo = true;
    const control = new AbortController();
    const consultar = async () => {
      try {
        const r = await apiGet<AutorizacionApi>(`/autorizaciones/${id}`, undefined, control.signal);
        if (!activo) return;
        if (r.servidor_ahora) setDesfaseMs(new Date(instanteUtc(r.servidor_ahora)).getTime() - Date.now());
        if (r.estado === "PENDIENTE") return;
        alResolver(id, r.estado, r.resuelta_por?.nombre ?? null);
        if (r.estado === "APROBADA") {
          reproducir("ok");
          aviso({ titulo: "El supervisor autorizó", tipo: "exito" });
        } else {
          reproducir("bloqueo");
        }
      } catch {
        // Sin conexión o error pasajero: se vuelve a intentar en 3 segundos.
      }
    };
    const intervalo = window.setInterval(() => void consultar(), CONSULTA_MS);
    return () => {
      activo = false;
      window.clearInterval(intervalo);
      control.abort();
    };
  }, [pendiente, id, alResolver]);

  useEffect(() => {
    if (!pendiente) return;
    const intervalo = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(intervalo);
  }, [pendiente]);

  if (!autorizacion || !pendiente) return null;
  return new Date(instanteUtc(autorizacion.vence_en)).getTime() - (ahora + desfaseMs);
}

function reloj(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface PropiedadesBandaTraslado {
  autorizacion: AutorizacionBorrador;
  /** Cuánto falta para que venza, de `useSeguirAutorizacion`. */
  restanteMs: number | null;
  /** Almacén del que sale el traslado: su supervisor es quien autoriza. */
  origenNombre: string | null;
  /** Deja de esperar y libera el borrador para editarlo. */
  alCancelar: () => void;
  /** Quita la autorización que no sirvió para pedir otra. */
  alPedirOtra: () => void;
  deshabilitado?: boolean;
}

/**
 * Estado de la autorización de un traslado entre proyectos (X-17, X-19): en espera con cuenta regresiva,
 * autorizada, rechazada o vencida. No decide nada: muestra lo que responde el servidor.
 */
export function BandaAutorizacionTraslado({ autorizacion, restanteMs, origenNombre, alCancelar, alPedirOtra, deshabilitado }: PropiedadesBandaTraslado) {
  const supervisor = origenNombre ? `el supervisor de ${origenNombre}` : "el supervisor";

  if (autorizacion.estado === "PENDIENTE") {
    const vencida = restanteMs !== null && restanteMs <= 0;
    return (
      <section aria-label="Autorización en espera" className="flex flex-col gap-3 rounded-2xl border border-semaforo-naranja bg-semaforo-naranja/10 p-4">
        <p className="flex items-center gap-2 text-base font-semibold">
          <ClockIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-naranja" />
          En espera de {supervisor}
        </p>
        <Cargando variante="en-linea" texto="Esperando su respuesta…" className="justify-start p-0" />
        <p className="text-sm text-muted-foreground" aria-live="off">
          {vencida ? "El tiempo se acabó. Estamos confirmando con el sistema…" : restanteMs !== null ? `Vence en ${reloj(restanteMs)}.` : "Le llegó un aviso para que la autorice."} Mientras espera no puedes
          cambiar la lista.
        </p>
        <Boton variante="contorno" onClick={alCancelar} disabled={deshabilitado}>
          Cancelar la solicitud
        </Boton>
      </section>
    );
  }

  if (autorizacion.estado === "APROBADA" || autorizacion.estado === "USADA") {
    return (
      <section aria-label="Traslado autorizado" className="flex flex-col gap-1 rounded-2xl border border-semaforo-verde bg-semaforo-verde/10 p-3">
        <p role="status" className="flex items-center gap-2 text-base font-semibold">
          <CircleCheckIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-verde" />
          Autorizado{autorizacion.resuelta_por ? ` por ${autorizacion.resuelta_por}` : ""}.
        </p>
        <p className="text-sm text-muted-foreground">Puedes quitar artículos, pero no agregar ni subir cantidades. Si hace falta, pide otra autorización.</p>
      </section>
    );
  }

  return (
    <section role="alert" aria-label="Autorización no concedida" className="flex flex-col gap-3 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
      <p className="flex items-center gap-2 text-base font-semibold">
        <CircleXIcon aria-hidden="true" className="size-6 shrink-0 text-semaforo-rojo" />
        {autorizacion.estado === "RECHAZADA"
          ? `${autorizacion.resuelta_por ?? "El supervisor"} no autorizó el traslado.`
          : "La solicitud venció sin respuesta."}
      </p>
      <p className="text-base">No se envió nada y tu lista sigue aquí. Puedes pedir otra autorización o pedirle al supervisor que escriba su PIN.</p>
      <Boton variante="contorno" onClick={alPedirOtra} disabled={deshabilitado}>
        Pedir otra autorización
      </Boton>
    </section>
  );
}
