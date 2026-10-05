import { cn } from "cn";
import { CheckIcon, ClockIcon, LockIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { api } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import type { Solicitud } from "~/componentes/consulta/tipos";
import { Avatar } from "~/componentes/ui/avatar";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { instanteUtc } from "~/componentes/consulta/formato";
import { venceEn, type SolicitudCerrada } from "./use-solicitudes";

function restante(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function textoCierre(c: SolicitudCerrada): string {
  switch (c.estado) {
    case "VENCIDA":
      return "Esta solicitud venció. Ya no se puede autorizar; el almacenista debe pedirla otra vez.";
    case "APROBADA":
      return c.por ? `${c.por} ya la autorizó.` : "Ya la autorizaron.";
    case "RECHAZADA":
      return c.por ? `${c.por} ya la rechazó.` : "Ya la rechazaron.";
    case "USADA":
      return "Ya se usó en un vale.";
    default:
      return "Esta solicitud ya no está pendiente.";
  }
}

interface PropiedadesTarjeta {
  solicitud: Solicitud;
  /** Hora actual en milisegundos; la pantalla la renueva cada segundo. */
  ahora: number;
  /** Llegó hace un momento: se resalta. */
  nueva?: boolean;
  /** Si ya dejó de estar pendiente, cómo terminó. */
  cierre?: SolicitudCerrada;
  puedeVerTrabajador: boolean;
  /** Se llama después de resolverla (o de que el servidor diga que ya no está pendiente) para refrescar. */
  alResolver: () => void;
  /** Refrescar la lista sin darla por resuelta aquí. */
  alRefrescar: () => void;
  alDescartar?: () => void;
}

/** Tarjeta del supervisor: trabajador, artículo, cuánto excede, motivo y quién la pide. */
export function TarjetaSolicitud({ solicitud, ahora, nueva, cierre, puedeVerTrabajador, alResolver, alRefrescar, alDescartar }: PropiedadesTarjeta) {
  const [decision, setDecision] = useState<"APROBAR" | "RECHAZAR" | null>(null);
  const [enviando, setEnviando] = useState(false);

  const msRestantes = venceEn(solicitud) - ahora;
  const vencida = cierre ? cierre.estado === "VENCIDA" : msRestantes <= 0;
  const cerrada = Boolean(cierre) || vencida;
  const articulos = solicitud.renglones.map((r) => r.articulo ?? r.codigo).join(", ");

  const resolver = async () => {
    if (!decision) return;
    setEnviando(true);
    try {
      await api(`/autorizaciones/${solicitud.id}/resolucion`, { metodo: "POST", cuerpo: { decision } });
      aviso({
        titulo: decision === "APROBAR" ? "Autorizada" : "Rechazada",
        descripcion: `${solicitud.trabajador.nombre}: ${articulos}`,
        tipo: decision === "APROBAR" ? "exito" : "info",
      });
      setDecision(null);
      alResolver();
    } catch (causa) {
      setDecision(null);
      aviso({ titulo: mensajeDeError(causa), tipo: "error", duracionMs: 8000 });
      // Ya resuelta, vencida o fuera de alcance: se refresca para mostrar cómo quedó.
      if (esErrorApi(causa) && (causa.status === 409 || causa.status === 404)) alRefrescar();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <article
      aria-label={`Solicitud de ${solicitud.trabajador.nombre}`}
      className={cn(
        "flex flex-col gap-4 rounded-xl border-2 bg-card p-4 transition-colors",
        cerrada ? "border-border bg-muted/60 opacity-70" : "border-semaforo-naranja",
        nueva && !cerrada && "ring-4 ring-semaforo-naranja/30",
      )}
    >
      <div className="flex items-start gap-3">
        <Avatar nombre={solicitud.trabajador.nombre} tamano="md" />
        <div className="flex min-w-0 flex-1 flex-col">
          {puedeVerTrabajador ? (
            <Link to={`/trabajadores/${solicitud.trabajador.id}`} className="text-lg leading-tight font-semibold text-marino underline-offset-2 hover:underline">
              {solicitud.trabajador.nombre}
            </Link>
          ) : (
            <p className="text-lg leading-tight font-semibold text-marino">{solicitud.trabajador.nombre}</p>
          )}
          <p className="text-sm text-muted-foreground">Número {solicitud.trabajador.numero_empleado}</p>
        </div>
      </div>

      <p
        className={cn(
          "flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm font-semibold",
          cerrada ? "border-border bg-background" : msRestantes < 60_000 ? "border-semaforo-rojo bg-semaforo-rojo/10" : "border-border bg-background",
        )}
      >
        <ClockIcon aria-hidden="true" className="size-4" />
        {cierre && cierre.estado !== "VENCIDA" ? "Ya resuelta" : cerrada ? "Venció" : `Vence en ${restante(msRestantes)}`}
      </p>

      <ul className="flex flex-col gap-2">
        {solicitud.renglones.map((r, i) => (
          <li key={`${r.codigo}-${i}`} className="flex flex-col gap-0.5 rounded-xl border bg-background p-3">
            <p className="flex items-center gap-2 text-base font-semibold">
              <LockIcon aria-hidden="true" className="size-5 shrink-0 text-semaforo-naranja" />
              {r.articulo ?? r.codigo}
            </p>
            {r.limite !== null && r.tiene !== null ? (
              <p className="text-base">
                Límite {r.limite}, tiene {r.tiene}, pide {r.cantidad}
                {r.excedente ? <span className="font-semibold"> · Se pasa por {r.excedente}</span> : null}
              </p>
            ) : (
              <p className="text-base">Pide {r.cantidad}.</p>
            )}
            {r.mensaje && (r.limite === null || r.tiene === null) ? <p className="text-sm text-muted-foreground">{r.mensaje}</p> : null}
            <p className="text-xs text-muted-foreground">Regla {r.regla}</p>
          </li>
        ))}
      </ul>

      <div className="flex flex-col gap-1">
        <p className="text-base">
          <span className="font-semibold">Motivo: </span>
          {solicitud.motivo}
        </p>
        <p className="text-sm text-muted-foreground">
          La pide {solicitud.solicitada_por.nombre} · {formatearFechaHora(instanteUtc(solicitud.creado_en))}
        </p>
      </div>

      {cerrada ? (
        <div className="flex flex-col gap-2">
          <p role="status" className="rounded-xl border bg-background p-3 text-sm font-semibold">
            {cierre ? textoCierre(cierre) : textoCierre({ solicitud, estado: "VENCIDA", por: null })}
          </p>
          {alDescartar ? (
            <Boton variante="contorno" onClick={alDescartar}>
              Quitar de la lista
            </Boton>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Boton variante="principal" onClick={() => setDecision("APROBAR")} disabled={enviando}>
            <CheckIcon aria-hidden="true" />
            Autorizar
          </Boton>
          <Boton variante="contorno" className="h-12 text-base font-semibold" onClick={() => setDecision("RECHAZAR")} disabled={enviando}>
            <XIcon aria-hidden="true" />
            Rechazar
          </Boton>
        </div>
      )}

      <Confirmacion
        abierta={decision !== null}
        alCambiar={(a) => {
          if (!a && !enviando) setDecision(null);
        }}
        mensaje={
          decision === "APROBAR"
            ? `¿Autorizar que se entregue ${articulos} a ${solicitud.trabajador.nombre}?`
            : `¿Rechazar la solicitud de ${solicitud.trabajador.nombre}?`
        }
        detalle={decision === "APROBAR" ? "El almacenista podrá terminar la entrega." : "El almacenista verá que no se autorizó."}
        etiquetaConfirmar={decision === "APROBAR" ? "Sí, autorizar" : "Sí, rechazar"}
        etiquetaCancelar="Volver"
        peligro={decision === "RECHAZAR"}
        cargando={enviando}
        alConfirmar={resolver}
      />
    </article>
  );
}
