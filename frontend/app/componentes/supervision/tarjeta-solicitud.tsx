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
import { Hoja } from "~/componentes/ui/hoja";
import { ResolucionRenglones, decisionesCompletas, type DecisionRenglon } from "./resolucion-renglones";
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
  /** La pidió quien mira: no puede autorizarla él mismo (A-05). */
  esPropia?: boolean;
}

/** Tarjeta del supervisor: trabajador, artículo, cuánto excede, motivo y quién la pide. */
export function TarjetaSolicitud({ solicitud, ahora, nueva, cierre, puedeVerTrabajador, alResolver, alRefrescar, alDescartar, esPropia }: PropiedadesTarjeta) {
  const [decision, setDecision] = useState<"APROBAR" | "RECHAZAR" | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [decisiones, setDecisiones] = useState<DecisionRenglon[]>([]);
  const renglones = solicitud.renglones.map((r, i) => ({ ...r, renglon: r.renglon ?? i + 1 }));
  const abrirResolucion = (valor: "APROBAR" | "RECHAZAR") => {
    setDecisiones(renglones.filter((r) => r.clase !== "CONTEXTO").map((r) => ({ renglon: r.renglon, decision: valor, motivo: "" })));
    setDecision(valor);
  };

  const msRestantes = venceEn(solicitud) - ahora;
  const vencida = cierre ? cierre.estado === "VENCIDA" : msRestantes <= 0;
  const cerrada = Boolean(cierre) || vencida;
  const articulos = solicitud.renglones.map((r) => r.articulo ?? r.codigo).join(", ");

  const resolver = async () => {
    if (!decision) return;
    setEnviando(true);
    try {
      const resuelta = await api<{ estado: string }>(`/autorizaciones/${solicitud.id}/resolucion`, { metodo: "POST", cuerpo: { renglones: decisiones.map((d) => ({ ...d, motivo: d.decision === "RECHAZAR" ? d.motivo?.trim() : undefined })) } });
      aviso({
        titulo: resuelta.estado === "APROBADA" ? "Decisiones guardadas: entrega aprobada" : "Solicitud rechazada",
        descripcion: `${solicitud.trabajador.nombre}: ${articulos}`,
        tipo: resuelta.estado === "APROBADA" ? "exito" : "info",
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
        "flex flex-col gap-4 rounded-2xl border bg-card p-4 shadow-xs transition-colors",
        cerrada ? "border-border bg-muted/60 opacity-70" : "border-semaforo-naranja",
        nueva && !cerrada && "ring-2 ring-semaforo-naranja/30",
      )}
    >
      <div className="flex items-start gap-3">
        <Avatar nombre={solicitud.trabajador.nombre} fotoUrl={puedeVerTrabajador && solicitud.trabajador.tiene_foto ? `/api/trabajadores/${solicitud.trabajador.id}/foto` : undefined} tamano="md" />
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

      {solicitud.almacen ? <p className="text-sm font-semibold">{solicitud.almacen.clave} · {solicitud.almacen.nombre}</p> : null}
      {solicitud.proyecto ? <p className="text-sm">Proyecto {solicitud.proyecto.clave} · {solicitud.proyecto.nombre}</p> : null}
      {solicitud.nota ? <p className="rounded-xl border p-3 text-sm">{solicitud.nota}</p> : null}
      <ul className="flex flex-col gap-2">
        {solicitud.renglones.map((r, i) => (
          <li key={`${r.codigo}-${i}`} className="flex flex-col gap-0.5 rounded-xl border bg-background p-3">
            <p className="flex items-center gap-2 text-base font-semibold">
              <LockIcon aria-hidden="true" className="size-5 shrink-0 text-semaforo-naranja" />
              {r.articulo ?? r.codigo}
            </p>
            {r.limite !== null && r.tiene !== null ? (
              <p className="text-sm">
                Límite {r.limite}, tiene {r.tiene}, pide {r.cantidad}
                {r.excedente ? <span className="font-semibold"> · Se pasa por {r.excedente}</span> : null}
              </p>
            ) : (
              <p className="text-sm">Pide {r.cantidad}.</p>
            )}
            {r.mensaje && (r.limite === null || r.tiene === null) ? <p className="text-sm text-muted-foreground">{r.mensaje}</p> : null}
            <p className="text-xs text-muted-foreground">{r.clase === "CONTEXTO" ? "Solo como contexto" : r.clase === "EPP" ? "Equipo de protección" : "Requiere autorización"}{r.incluye_excedente ? " · También excede su límite" : ""}</p>
            {r.observacion ? <p className="text-sm">{r.observacion}</p> : null}
            {solicitud.renglones_resueltos?.filter((d) => d.codigo === r.codigo).map((d) => <p key={d.renglon} className="text-sm font-semibold">{d.decision === "APROBADO" ? "Aprobado" : `Rechazado: ${d.motivo ?? ""}`}</p>)}
          </li>
        ))}
      </ul>

      <div className="flex flex-col gap-1">
        <p className="text-sm">
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
      ) : esPropia ? (
        <p role="status" className="rounded-xl border bg-background p-3 text-sm font-semibold">
          La pediste tú. Debe autorizarla otro supervisor.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Boton variante="principal" onClick={() => abrirResolucion("APROBAR")} disabled={enviando}>
            <CheckIcon aria-hidden="true" />
            Autorizar
          </Boton>
          <Boton variante="contorno" className="h-12 text-base font-semibold" onClick={() => abrirResolucion("RECHAZAR")} disabled={enviando}>
            <XIcon aria-hidden="true" />
            Rechazar
          </Boton>
        </div>
      )}

      <Hoja abierta={decision !== null} alCambiar={(a) => { if (!a && !enviando) setDecision(null); }}
        titulo="Resolver solicitud" descripcion={`Revisa lo que se entregará a ${solicitud.trabajador.nombre}.`}
        pie={<Boton variante="principal" cargando={enviando} disabled={enviando || !decisionesCompletas(renglones, decisiones)} onClick={() => void resolver()}>Guardar decisiones</Boton>}>
        <ResolucionRenglones renglones={renglones} decisiones={decisiones} alCambiar={setDecisiones} bloqueado={enviando} />
      </Hoja>
    </article>
  );
}
