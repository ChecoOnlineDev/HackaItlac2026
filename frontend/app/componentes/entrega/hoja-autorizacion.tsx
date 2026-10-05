import { LockIcon, SendIcon, ShieldCheckIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiPost } from "~/api/cliente";
import { esErrorApi, formatearEspera, mensajeDeError } from "~/api/errores";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import type { AutorizacionBorrador } from "./borrador";
import type { AutorizacionApi } from "./tipos";

interface PropiedadesHojaAutorizacion {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  trabajadorId: string;
  /** Los renglones naranja que se piden autorizar (todos juntos, en una sola solicitud). */
  renglones: RenglonEvaluado[];
  /** Se llama cuando la solicitud quedó creada (en espera) o ya resuelta por PIN. */
  alSolicitar: (autorizacion: AutorizacionBorrador) => void;
}

interface SolicitudCreada {
  id: string;
  estado: AutorizacionBorrador["estado"];
  vence_en: string;
}

type Modo = "elegir" | "pin";

/** El motivo que dio el servidor para pedir autorización: la regla (L-01...) y su frase. */
function motivoNaranja(renglon: RenglonEvaluado) {
  return renglon.motivos.find((m) => m.nivel === "NARANJA") ?? renglon.motivos[0];
}

/**
 * Hoja de "Pedir autorización" (flujo 7). Pide el motivo y ofrece dos caminos: "El supervisor está
 * aquí" (su usuario y su PIN en este mismo dispositivo) o "Enviar a su celular" (queda en espera y la
 * pantalla de la entrega consulta cada 3 segundos). No decide nada: el servidor valida el PIN, que
 * quien captura no se autorice (A-05) y que un rojo no se pueda enviar (A-06).
 */
export function HojaAutorizacion({ abierta, alCambiar, trabajadorId, renglones, alSolicitar }: PropiedadesHojaAutorizacion) {
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
      setError(null);
      setErrorMotivo(null);
      setPin("");
    }
  }, [abierta]);

  const codigos = renglones.map((r) => r.codigo);

  const crearSolicitud = async (): Promise<SolicitudCreada> => {
    if (solicitud.current) return solicitud.current;
    const creada = await apiPost<SolicitudCreada>("/autorizaciones", {
      trabajador_id: trabajadorId,
      motivo: motivo.trim(),
      renglones: renglones.map((r) => {
        const m = motivoNaranja(r);
        return {
          codigo: r.codigo,
          articulo_id: r.articulo?.id ?? null,
          articulo: r.articulo?.nombre ?? null,
          cantidad: r.cantidad,
          regla: m?.regla ?? "L-01",
          mensaje: m?.mensaje?.slice(0, 255) ?? null,
        };
      }),
    });
    solicitud.current = creada;
    return creada;
  };

  const cerrar = (valor: boolean) => {
    if (!valor && solicitud.current) {
      // Quedó una solicitud creada que nadie resolvió (por ejemplo un PIN que falló): sigue en espera.
      alSolicitar({ id: solicitud.current.id, estado: "PENDIENTE", codigos, vence_en: solicitud.current.vence_en });
      solicitud.current = null;
    }
    alCambiar(valor);
  };

  const validarMotivo = (): boolean => {
    if (!motivo.trim()) {
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
      alSolicitar({ id: creada.id, estado: creada.estado, codigos, vence_en: creada.vence_en });
      alCambiar(false);
    } catch (causa) {
      setError(mensajeDeError(causa));
    } finally {
      setEnviando(null);
    }
  };

  const irAPin = () => {
    if (!validarMotivo()) return;
    setModo("pin");
  };

  const resolver = async (decision: "APROBAR" | "RECHAZAR") => {
    if (!usuario.trim() || !pin) {
      setError("Escribe el usuario y el PIN del supervisor.");
      return;
    }
    setEnviando(decision === "APROBAR" ? "autorizar" : "rechazar");
    setError(null);
    try {
      const creada = await crearSolicitud();
      const resuelta = await apiPost<AutorizacionApi>(`/autorizaciones/${creada.id}/resolucion`, {
        decision,
        usuario: usuario.trim(),
        pin,
      });
      solicitud.current = null;
      setPin("");
      alSolicitar({
        id: resuelta.id,
        estado: resuelta.estado,
        codigos,
        vence_en: resuelta.vence_en,
        resuelta_por: resuelta.resuelta_por?.nombre ?? null,
      });
      alCambiar(false);
    } catch (causa) {
      setPin("");
      if (esErrorApi(causa) && causa.segundosEspera !== null) {
        setEsperaHasta(Date.now() + causa.segundosEspera * 1000);
        setError("Demasiados intentos con el PIN. Espera para volver a intentar.");
      } else {
        setError(mensajeDeError(causa));
      }
    } finally {
      setEnviando(null);
    }
  };

  const bloqueado = segundosRestantes > 0;
  const resumen = renglones.map((r) => `${r.cantidad} × ${r.articulo?.nombre ?? r.codigo}`).join(", ");

  return (
    <Hoja
      abierta={abierta}
      alCambiar={cerrar}
      titulo="Pedir autorización"
      descripcion={resumen ? `Para: ${resumen}.` : "Un supervisor debe autorizar esta entrega."}
    >
      <div className="flex flex-col gap-4">
        <Campo
          etiqueta="Motivo"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={255}
          placeholder="Por qué se necesita más de lo permitido"
          error={errorMotivo}
          autoComplete="off"
          disabled={modo === "pin" || enviando !== null}
        />

        {modo === "elegir" ? (
          <div className="flex flex-col gap-3">
            <Boton variante="normal" onClick={irAPin} disabled={enviando !== null}>
              <ShieldCheckIcon aria-hidden="true" />
              El supervisor está aquí
            </Boton>
            <Boton variante="contorno" onClick={() => void enviarACelular()} cargando={enviando === "remota"} disabled={enviando !== null}>
              <SendIcon aria-hidden="true" />
              Enviar a su celular
            </Boton>
            <p className="text-sm text-muted-foreground">
              Si lo envías a su celular, la entrega queda en espera y se actualiza sola cuando responda.
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
              <p role="alert" className="rounded-lg border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-base font-medium">
                {error}
                {bloqueado ? <span className="mt-1 block text-lg font-bold">Podrás intentar en {formatearEspera(segundosRestantes)}</span> : null}
              </p>
            ) : null}
            <Boton type="submit" variante="normal" cargando={enviando === "autorizar"} disabled={enviando !== null || bloqueado}>
              Autorizar
            </Boton>
            <Boton
              type="button"
              variante="contorno"
              cargando={enviando === "rechazar"}
              disabled={enviando !== null || bloqueado}
              onClick={() => void resolver("RECHAZAR")}
            >
              Rechazar
            </Boton>
            <Boton type="button" variante="texto" disabled={enviando !== null} onClick={() => setModo("elegir")}>
              Atrás
            </Boton>
          </form>
        )}
        {modo === "elegir" && error ? (
          <p role="alert" className="rounded-lg border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-base font-medium">
            {error}
          </p>
        ) : null}
      </div>
    </Hoja>
  );
}
