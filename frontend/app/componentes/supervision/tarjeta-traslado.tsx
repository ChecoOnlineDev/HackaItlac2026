import { cn } from "cn";
import { ArrowRightIcon, CheckIcon, ClockIcon, TruckIcon, XIcon } from "lucide-react";
import { useState } from "react";

import { api } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { instanteUtc } from "~/componentes/consulta/formato";
import type { SolicitudTraslado } from "~/componentes/consulta/tipos";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { HojaObservacion } from "~/componentes/dominio/hoja-observacion";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { venceEn, type SolicitudCerrada } from "./use-solicitudes";

function restante(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function textoCierre(estado: SolicitudCerrada["estado"], por: string | null): string {
  switch (estado) {
    case "VENCIDA":
      return "Esta solicitud venció. Ya no se puede autorizar; quien la pidió debe pedirla otra vez.";
    case "APROBADA":
      return por ? `${por} ya la autorizó.` : "Ya la autorizaron.";
    case "RECHAZADA":
      return por ? `${por} ya la rechazó.` : "Ya la rechazaron.";
    case "USADA":
      return "Ya se usó en un traslado.";
    default:
      return "Esta solicitud ya no está pendiente.";
  }
}

interface PropiedadesTarjetaTraslado {
  solicitud: SolicitudTraslado;
  /** Hora actual en milisegundos; la pantalla la renueva cada segundo. */
  ahora: number;
  nueva?: boolean;
  cierre?: SolicitudCerrada;
  alResolver: () => void;
  alRefrescar: () => void;
  alDescartar?: () => void;
  /** La pidió quien mira: no puede autorizarla él mismo (A-05). */
  esPropia?: boolean;
}

/**
 * Tarjeta de un traslado entre proyectos (X-17, X-19): de dónde sale, a dónde va, qué lleva y quién lo pide.
 * Se aprueba o se rechaza completa; no hay aprobación por renglón.
 */
export function TarjetaTraslado({ solicitud, ahora, nueva, cierre, alResolver, alRefrescar, alDescartar, esPropia }: PropiedadesTarjetaTraslado) {
  const [autorizando, setAutorizando] = useState(false);
  const [rechazando, setRechazando] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const msRestantes = venceEn(solicitud) - ahora;
  const vencida = cierre ? cierre.estado === "VENCIDA" : msRestantes <= 0;
  const cerrada = Boolean(cierre) || vencida;
  const articulos = solicitud.renglones.map((r) => `${r.cantidad} × ${r.articulo ?? r.codigo}`).join(", ");

  const resolver = async (accion: "APROBAR" | "RECHAZAR", motivo?: string) => {
    setEnviando(true);
    try {
      await api(`/autorizaciones/${solicitud.id}/resolucion`, {
        metodo: "POST",
        cuerpo: motivo ? { decision: accion, motivo } : { decision: accion },
      });
      aviso({
        titulo: accion === "APROBAR" ? "Traslado autorizado" : "Traslado rechazado",
        descripcion: `De ${solicitud.origen.nombre} a ${solicitud.destino.nombre}`,
        tipo: accion === "APROBAR" ? "exito" : "info",
      });
      setAutorizando(false);
      setRechazando(false);
      alResolver();
    } catch (causa) {
      setAutorizando(false);
      setRechazando(false);
      aviso({ titulo: mensajeDeError(causa), tipo: "error", duracionMs: 8000 });
      // Ya resuelta, vencida o fuera de alcance: se refresca para mostrar cómo quedó.
      if (esErrorApi(causa) && (causa.status === 409 || causa.status === 404)) alRefrescar();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <article
      aria-label={`Traslado de ${solicitud.origen.nombre} a ${solicitud.destino.nombre}`}
      className={cn(
        "flex flex-col gap-4 rounded-2xl border bg-card p-4 shadow-xs transition-colors",
        cerrada ? "border-border bg-muted/60 opacity-70" : "border-semaforo-naranja",
        nueva && !cerrada && "ring-2 ring-semaforo-naranja/30",
      )}
    >
      <div className="flex items-start gap-3">
        <TruckIcon aria-hidden="true" className="mt-1 size-6 shrink-0 text-marino" />
        <div className="flex min-w-0 flex-1 flex-col">
          <p className="text-sm font-semibold text-muted-foreground">Traslado entre proyectos</p>
          <p className="flex flex-wrap items-center gap-1.5 text-lg leading-tight font-semibold text-marino">
            {solicitud.origen.nombre}
            <ArrowRightIcon aria-label="hacia" className="size-5 shrink-0" />
            {solicitud.destino.nombre}
          </p>
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

      <ul className="flex flex-col gap-2" aria-label="Lo que se traslada">
        {solicitud.renglones.map((r, i) => (
          <li key={`${r.codigo}-${i}`} className="flex flex-col gap-0.5 rounded-xl border bg-background p-3">
            <p className="text-base font-semibold">
              {r.cantidad} × {r.articulo ?? r.codigo}
            </p>
            {r.mensaje ? <p className="text-sm text-muted-foreground">{r.mensaje}</p> : null}
            <p className="text-xs text-muted-foreground">Regla {r.regla}</p>
          </li>
        ))}
      </ul>

      <div className="flex flex-col gap-1">
        <p className="text-sm">
          <span className="font-semibold">Motivo: </span>
          {solicitud.motivo}
        </p>
        <p className="text-sm text-muted-foreground">
          Lo pide {solicitud.solicitada_por.nombre} · {formatearFechaHora(instanteUtc(solicitud.creado_en))}
        </p>
      </div>

      {cerrada ? (
        <div className="flex flex-col gap-2">
          <p role="status" className="rounded-xl border bg-background p-3 text-sm font-semibold">
            {textoCierre(cierre?.estado ?? "VENCIDA", cierre?.por ?? null)}
          </p>
          {alDescartar ? (
            <Boton variante="contorno" onClick={alDescartar}>
              Quitar de la lista
            </Boton>
          ) : null}
        </div>
      ) : esPropia ? (
        <p role="status" className="rounded-xl border bg-background p-3 text-sm font-semibold">
          La pediste tú. Debe autorizarla otro supervisor.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Boton variante="principal" onClick={() => setAutorizando(true)} disabled={enviando}>
            <CheckIcon aria-hidden="true" />
            Autorizar
          </Boton>
          <Boton variante="contorno" className="h-12 text-base font-semibold" onClick={() => setRechazando(true)} disabled={enviando}>
            <XIcon aria-hidden="true" />
            Rechazar
          </Boton>
        </div>
      )}

      <Confirmacion
        abierta={autorizando}
        alCambiar={(a) => {
          if (!a && !enviando) setAutorizando(false);
        }}
        mensaje={`¿Autorizar que salga de ${solicitud.origen.nombre} hacia ${solicitud.destino.nombre}: ${articulos}?`}
        detalle="Se autoriza completo. Quien lo pidió podrá terminar el envío."
        etiquetaConfirmar="Sí, autorizar"
        etiquetaCancelar="Volver"
        cargando={enviando}
        alConfirmar={() => resolver("APROBAR")}
      />
      <HojaObservacion
        abierta={rechazando}
        alCambiar={(a) => {
          if (!enviando) setRechazando(a);
        }}
        titulo="Rechazar el traslado"
        motivo={`No sale nada de ${solicitud.origen.nombre}. Quien lo pidió verá que no se autorizó. Puedes decirle por qué.`}
        obligatoria={false}
        respuestasRapidas={["Hace falta aquí", "Mejor por Contratistas", "Cantidad equivocada"]}
        etiquetaGuardar="Rechazar el traslado"
        alGuardar={(texto) => void resolver("RECHAZAR", texto || undefined)}
      />
    </article>
  );
}
