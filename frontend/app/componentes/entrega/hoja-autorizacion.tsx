import { LockIcon, SendIcon, ShieldCheckIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, formatearEspera, mensajeDeError } from "~/api/errores";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { nuevoIdCliente, type AutorizacionBorrador } from "./borrador";
import { ResolucionRenglones, decisionesCompletas, type DecisionRenglon, type RenglonParaResolver } from "~/componentes/supervision/resolucion-renglones";
import type { AutorizacionApi } from "./tipos";

/** Lo que se pide autorizar en un traslado entre proyectos (X-17): el destino y lo que sale. */
export interface SolicitudTrasladoHoja {
  destinoId: string;
  /** Se manda igual si se reintenta, para no crear dos solicitudes. */
  idCliente: string;
  renglones: { codigo: string; cantidad: number; nombre?: string | null }[];
  /** Nombre del almacén de origen, para decir de quién es el supervisor. */
  origenNombre?: string | null;
}

interface PropiedadesHojaAutorizacion {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Solo en una entrega. */
  trabajadorId?: string;
  proyectoId?: string;
  despacho?: boolean;
  observaciones?: Record<string, string>;
  autorizacionExistente?: AutorizacionBorrador | null;
  alReevaluar?: () => void;
  /** Si viene, la hoja pide autorizar un traslado en vez de un excedente de entrega. */
  traslado?: SolicitudTrasladoHoja;
  /** Almacén que se está operando; quien opera todos los almacenes debe indicarlo (RG-07). */
  almacenId?: string | null;
  /** Los renglones naranja que se piden autorizar (todos juntos, en una sola solicitud). */
  renglones?: RenglonEvaluado[];
  /** Se llama cuando la solicitud quedó creada (en espera) o ya resuelta por PIN. */
  alSolicitar: (autorizacion: AutorizacionBorrador) => void;
}

interface SolicitudCreada {
  id: string;
  estado: AutorizacionBorrador["estado"];
  vence_en: string;
  avisados?: number;
  tipo?: "DESPACHO" | "EXCEDENTE" | "TRASLADO";
}

type Modo = "elegir" | "pin";

/**
 * Hoja de "Pedir autorización" (flujo 7). Pide el motivo y ofrece dos caminos: "El supervisor está
 * aquí" (su usuario y su PIN en este mismo dispositivo) o "Enviar a su celular" (queda en espera y la
 * pantalla de la entrega consulta cada 3 segundos). No decide nada: el servidor valida el PIN, que
 * quien captura no se autorice (A-05) y que un rojo no se pueda enviar (A-06).
 */
export function HojaAutorizacion({ abierta, alCambiar, trabajadorId, proyectoId, despacho = false, observaciones = {}, autorizacionExistente, alReevaluar, traslado, almacenId, renglones = [], alSolicitar }: PropiedadesHojaAutorizacion) {
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState<string | null>(null);
  const [modo, setModo] = useState<Modo>("elegir");
  const [usuario, setUsuario] = useState("");
  const [pin, setPin] = useState("");
  const [enviando, setEnviando] = useState<"remota" | "autorizar" | "rechazar" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [esperaHasta, setEsperaHasta] = useState<number | null>(null);
  const [, repintar] = useState(0);
  // Si el PIN falla, la solicitud ya existe: se reintenta la resolución, no se crea otra.
  const solicitud = useRef<SolicitudCreada | null>(null);
  const idSolicitud = useRef(nuevoIdCliente());
  const cuerpoSolicitud = useRef<string | null>(null);
  const [decisiones, setDecisiones] = useState<DecisionRenglon[]>([]);
  const [motivoRechazo, setMotivoRechazo] = useState("");
  const [renglonesServidor, setRenglonesServidor] = useState<RenglonParaResolver[] | null>(null);
  const porResolver = renglonesServidor ?? renglones.map((r) => ({ renglon: r.renglon, codigo: r.codigo, articulo: r.articulo?.nombre, cantidad: r.cantidad,
    clase: r.requiere_aprobacion ? "EPP" : r.nivel === "NARANJA" ? "EXCEDENTE" : "CONTEXTO", observacion: observaciones[r.codigo] }));
  const pideMotivo = Boolean(traslado) || !despacho || renglones.some((r) => r.nivel === "NARANJA");

  const segundosRestantes = esperaHasta ? Math.max(0, Math.ceil((esperaHasta - Date.now()) / 1000)) : 0;
  useEffect(() => {
    if (!esperaHasta) return;
    const id = window.setInterval(() => {
      repintar((n) => n + 1);
      if (Date.now() >= esperaHasta) setEsperaHasta(null);
    }, 1000);
    return () => window.clearInterval(id);
  }, [esperaHasta]);

  useEffect(() => {
    if (abierta) {
      setModo("elegir");
      setRenglonesServidor(null);
      if (autorizacionExistente?.estado === "PENDIENTE") solicitud.current = { ...autorizacionExistente };
      setError(null);
      setErrorMotivo(null);
      setPin("");
      setMotivoRechazo("");
      setDecisiones(renglones.filter((r) => r.requiere_aprobacion || r.nivel === "NARANJA").map((r) => ({ renglon: r.renglon, decision: "APROBAR" })));
    }
  }, [abierta]);

  const codigos = traslado ? traslado.renglones.map((r) => r.codigo) : renglones.map((r) => r.codigo);

  const crearSolicitud = async (): Promise<SolicitudCreada> => {
    if (solicitud.current) return solicitud.current;
    const huella = JSON.stringify({ traslado, trabajadorId, almacenId, proyectoId, despacho, motivo: motivo.trim(), renglones: renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad, observacion: observaciones[r.codigo] })) });
    if (cuerpoSolicitud.current && cuerpoSolicitud.current !== huella) idSolicitud.current = nuevoIdCliente();
    cuerpoSolicitud.current = huella;
    if (traslado) {
      // X-17: el servidor vuelve a evaluar el traslado; aquí solo se mandan códigos y cantidades.
      const creada = await apiPost<SolicitudCreada>("/autorizaciones", {
        tipo: "TRASLADO",
        id_cliente: traslado.idCliente,
        almacen_id: almacenId ?? undefined,
        destino_almacen_id: traslado.destinoId,
        motivo: motivo.trim(),
        renglones: traslado.renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad })),
      });
      solicitud.current = creada;
      return creada;
    }
    const creada = await apiPost<SolicitudCreada>("/autorizaciones", {
      tipo: despacho ? "DESPACHO" : "EXCEDENTE",
      id_cliente: idSolicitud.current,
      trabajador_id: trabajadorId,
      proyecto_id: proyectoId,
      almacen_id: almacenId ?? undefined,
      motivo: pideMotivo ? motivo.trim() : undefined,
      nota: !pideMotivo ? motivo.trim() || undefined : undefined,
      renglones: renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad, observacion: observaciones[r.codigo] || undefined })),
    });
    solicitud.current = creada;
    return creada;
  };

  const cerrar = (valor: boolean) => {
    if (!valor && solicitud.current) {
      // Quedó una solicitud creada que nadie resolvió (por ejemplo un PIN que falló): sigue en espera.
      alSolicitar({ id: solicitud.current.id, estado: solicitud.current.estado, codigos, vence_en: solicitud.current.vence_en, avisados: solicitud.current.avisados, tipo: solicitud.current.tipo, solicitado_en: Date.now() });
      idSolicitud.current = nuevoIdCliente();
      solicitud.current = null;
    }
    alCambiar(valor);
  };

  const validarMotivo = (): boolean => {
    if (pideMotivo && !motivo.trim()) {
      setErrorMotivo("Escribe el motivo para pedir la autorización.");
      return false;
    }
    setErrorMotivo(null);
    return true;
  };

  const enviarACelular = async () => {
    if (!validarMotivo()) return;
    setEnviando("remota");
    setError(null);
    try {
      const creada = await crearSolicitud();
      solicitud.current = null;
      idSolicitud.current = nuevoIdCliente();
      alSolicitar({ id: creada.id, estado: creada.estado, codigos, vence_en: creada.vence_en, avisados: creada.avisados, tipo: creada.tipo, solicitado_en: Date.now() });
      alCambiar(false);
    } catch (causa) {
      setError(mensajeDeError(causa));
      alReevaluar?.();
    } finally {
      setEnviando(null);
    }
  };

  const irAPin = async () => {
    if (!validarMotivo()) return;
    setError(null); setEnviando("autorizar");
    try {
      const creada = await crearSolicitud();
      if (!traslado) {
        const detalle = await apiGet<{ renglones: (RenglonParaResolver & { renglon: number | null })[] }>(`/autorizaciones/${creada.id}`);
        const filas = detalle.renglones.map((r, i) => ({ ...r, renglon: r.renglon ?? i + 1 }));
        setRenglonesServidor(filas);
        setDecisiones(filas.filter((r) => r.clase !== "CONTEXTO").map((r) => ({ renglon: r.renglon, decision: "APROBAR" })));
      }
      setModo("pin");
    } catch (causa) { setError(mensajeDeError(causa));
      alReevaluar?.(); }
    finally { setEnviando(null); }
  };

  const resolver = async (decision: "APROBAR" | "RECHAZAR") => {
    if (!usuario.trim() || !pin) {
      setError("Escribe el usuario y el PIN del supervisor.");
      return;
    }
    if (traslado && decision === "RECHAZAR" && !motivoRechazo.trim()) { setError("Escribe el motivo del rechazo."); return; }
    if (!traslado && !decisionesCompletas(porResolver, decisiones)) { setError("Decide cada renglón y escribe el motivo de cada rechazo."); return; }
    setEnviando(decision === "APROBAR" ? "autorizar" : "rechazar");
    setError(null);
    try {
      const creada = await crearSolicitud();
      const resuelta = await apiPost<AutorizacionApi>(`/autorizaciones/${creada.id}/resolucion`, {
        ...(traslado ? { decision, motivo: decision === "RECHAZAR" ? motivoRechazo.trim() : undefined } : { renglones: decisiones }),
        usuario: usuario.trim(),
        pin,
      });
      solicitud.current = null;
      idSolicitud.current = nuevoIdCliente();
      setPin("");
      alSolicitar({
        id: resuelta.id,
        estado: resuelta.estado,
        codigos,
        vence_en: resuelta.vence_en,
        resuelta_por: resuelta.resuelta_por?.nombre ?? null,
        avisados: creada.avisados, tipo: creada.tipo, renglones_resueltos: resuelta.renglones_resueltos, solicitado_en: Date.now(),
      });
      alCambiar(false);
    } catch (causa) {
      setPin("");
      if (esErrorApi(causa) && causa.segundosEspera !== null) {
        setEsperaHasta(Date.now() + causa.segundosEspera * 1000);
        setError("Demasiados intentos con el PIN. Espera para volver a intentar.");
      } else {
        setError(mensajeDeError(causa));
        alReevaluar?.();
      }
    } finally {
      setEnviando(null);
    }
  };

  const bloqueado = segundosRestantes > 0;
  const resumen = traslado
    ? traslado.renglones.map((r) => `${r.cantidad} × ${r.nombre ?? r.codigo}`).join(", ")
    : renglones.map((r) => `${r.cantidad} × ${r.articulo?.nombre ?? r.codigo}`).join(", ");

  return (
    <Hoja
      abierta={abierta}
      alCambiar={cerrar}
      titulo="Pedir autorización"
      descripcion={
        resumen
          ? `Para: ${resumen}.`
          : traslado
            ? "El supervisor del almacén de origen debe autorizar este traslado."
            : "Un supervisor debe autorizar esta entrega."
      }
    >
      <div className="flex flex-col gap-4">
        <Campo
          etiqueta={pideMotivo ? "Motivo" : "Nota (opcional)"}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={255}
          placeholder={traslado ? "Ej. Sobra aquí y hace falta allá" : "Ej. Trabajo especial"}
          error={errorMotivo}
          autoComplete="off"
          disabled={modo === "pin" || enviando !== null}
        />

        {modo === "elegir" ? (
          <div className="flex flex-col gap-3">
            <Boton variante="normal" onClick={() => void irAPin()} disabled={enviando !== null}>
              <ShieldCheckIcon aria-hidden="true" />
              El supervisor está aquí
            </Boton>
            <Boton variante="contorno" onClick={() => void enviarACelular()} cargando={enviando === "remota"} disabled={enviando !== null}>
              <SendIcon aria-hidden="true" />
              Enviar a su celular
            </Boton>
            <p className="text-sm text-muted-foreground">
              {traslado
                ? "Si lo envías a su celular, el traslado queda en espera y se actualiza solo cuando responda."
                : "Si lo envías a su celular, la entrega queda en espera y se actualiza sola cuando responda."}
            </p>
          </div>
        ) : (
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void resolver("APROBAR");
            }}
          >
            <p className="flex items-center gap-2 text-base font-semibold">
              <LockIcon aria-hidden="true" className="size-5 text-semaforo-naranja" />
              El supervisor escribe aquí su usuario y su PIN
            </p>
            <Campo
              etiqueta="Usuario del supervisor"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              autoComplete="off"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              disabled={enviando !== null}
            />
            <Campo
              etiqueta="PIN"
              type="password"
              inputMode="numeric"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              autoComplete="off"
              disabled={enviando !== null || bloqueado}
            />
            {error ? (
              <p role="alert" className="rounded-xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-medium">
                {error}
                {bloqueado ? <span className="mt-1 block text-base font-semibold">Podrás intentar en {formatearEspera(segundosRestantes)}</span> : null}
              </p>
            ) : null}
            {!traslado ? <ResolucionRenglones renglones={porResolver} decisiones={decisiones} alCambiar={setDecisiones} bloqueado={enviando !== null} /> : <Campo etiqueta="Motivo si rechazas" value={motivoRechazo} onChange={(e) => setMotivoRechazo(e.target.value)} maxLength={500} disabled={enviando !== null} />}
            <Boton type="submit" variante="normal" cargando={enviando === "autorizar"} disabled={enviando !== null || bloqueado}>
              {traslado ? "Autorizar" : "Guardar decisiones"}
            </Boton>
            {traslado ? <Boton
              type="button"
              variante="contorno"
              cargando={enviando === "rechazar"}
              disabled={enviando !== null || bloqueado}
              onClick={() => void resolver("RECHAZAR")}
            >
              Rechazar
            </Boton> : null}
            <Boton type="button" variante="texto" disabled={enviando !== null} onClick={() => setModo("elegir")}>
              Atrás
            </Boton>
          </form>
        )}
        {modo === "elegir" && error ? (
          <p role="alert" className="rounded-xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-medium">
            {error}
          </p>
        ) : null}
      </div>
    </Hoja>
  );
}
