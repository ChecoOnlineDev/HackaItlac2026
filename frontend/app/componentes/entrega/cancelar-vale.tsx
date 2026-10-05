import { CircleAlertIcon, WifiOffIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { HojaObservacion } from "~/componentes/dominio/hoja-observacion";
import type { TipoVale } from "~/componentes/dominio/vale-imprimible";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { useSesionActiva } from "~/sesion/sesion";
import { nuevoIdCliente } from "./borrador";
import {
  cargarBorradorParaRehacer,
  hayCapturaSinTerminar,
  rutaDeCaptura,
  sePuedeRehacer,
  type CancelacionApi,
} from "./rehacer";

/** Lo que hace falta saber de un vale para ofrecer su cancelación. */
export interface ValeParaCancelar {
  id: string;
  folio: string;
  tipo: TipoVale;
  estado: string;
}

/** Tipos que nunca se cancelan (K-04): una recepción, un no adeudo y una cancelación. */
const NO_CANCELABLES: readonly TipoVale[] = ["RECEPCION", "NO_ADEUDO", "CANCELACION"];

/** ¿Vale la pena ofrecer "Cancelar"? El servidor decide el resto (K-03: lo que ya se movió después, etc.). */
export function esCancelable(vale: Pick<ValeParaCancelar, "tipo" | "estado">): boolean {
  return vale.estado !== "CANCELADO" && !NO_CANCELABLES.includes(vale.tipo);
}

/** Una frase de lo que regresa a su lugar al cancelar cada tipo de vale (K-02). */
const QUE_SE_REVIERTE: Partial<Record<TipoVale, string>> = {
  ENTREGA: "El equipo y el material vuelven al almacén y dejan de estar en resguardo del trabajador.",
  DEVOLUCION: "Lo que se recibió sale del almacén y vuelve al resguardo del trabajador.",
  ENTRADA: "Lo que entró se descuenta de las existencias del almacén.",
  TRASPASO: "Lo que se envió regresa al almacén de origen.",
};

const RESPUESTAS_RAPIDAS = [
  "Capturé el artículo equivocado",
  "Capturé mal la cantidad",
  "Era otro trabajador",
  "Se hizo dos veces",
];

interface MotivoNoCancelable {
  regla?: string;
  mensaje: string;
}

type Fallo = { tipo: "conexion" | "no_cancelable" | "otro"; mensaje: string; motivos: MotivoNoCancelable[] };

interface PropiedadesCancelarVale {
  /** El vale que se quiere cancelar; `null` mantiene todo cerrado. */
  vale: ValeParaCancelar | null;
  /** `true` para "Cancelar y rehacer" (K-05). */
  rehacer: boolean;
  alCerrar: () => void;
  /** Se llama cuando el servidor ya canceló el vale (y, con rehacer, cuando ya no hay nada más que hacer aquí). */
  alCancelar: (cancelacion: CancelacionApi) => void;
}

/**
 * Cancelar un vale (K-01 a K-05): hoja con el motivo obligatorio, confirmación de una frase que dice qué se
 * revierte y la llamada al servidor. Con `rehacer`, el borrador que responde el servidor se carga en la pantalla
 * de su tipo (entregar o devolver) para corregirlo. Si el servidor responde que no se puede, se muestra su motivo.
 *
 * ```tsx
 * <CancelarVale vale={vale} rehacer={false} alCerrar={() => setVale(null)} alCancelar={recargar} />
 * ```
 */
export function CancelarVale({ vale, rehacer, alCerrar, alCancelar }: PropiedadesCancelarVale) {
  const { sesion } = useSesionActiva();
  const navegar = useNavigate();
  const [paso, setPasoEstado] = useState<"motivo" | "confirmar" | "fallo" | null>(null);
  // El paso también va en una referencia: la hoja avisa que se cierra justo después de guardar el motivo,
  // y en ese instante el estado todavía dice "motivo".
  const pasoRef = useRef<typeof paso>(null);
  const setPaso = (siguiente: typeof paso) => {
    pasoRef.current = siguiente;
    setPasoEstado(siguiente);
  };
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<Fallo | null>(null);
  const enviandoRef = useRef(false);
  /** Un doble toque o un reintento nunca cancelan dos veces: el mismo `id_cliente` en toda la operación. */
  const idCliente = useRef<string>("");

  const idVale = vale?.id ?? null;
  useEffect(() => {
    if (idVale) {
      idCliente.current = nuevoIdCliente();
      pasoRef.current = "motivo";
      setPasoEstado("motivo");
      setMotivo("");
      setFallo(null);
      setEnviando(false);
      enviandoRef.current = false;
    } else {
      pasoRef.current = null;
      setPasoEstado(null);
    }
  }, [idVale, rehacer]);

  if (!vale) return null;

  const tipoRehacer = rehacer && sePuedeRehacer(vale.tipo);
  const cerrar = () => {
    if (enviandoRef.current) return;
    setPaso(null);
    alCerrar();
  };

  const cancelar = async () => {
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setEnviando(true);
    try {
      const r = await apiPost<CancelacionApi>(`/vales/${vale.id}/cancelacion`, {
        motivo,
        id_cliente: idCliente.current,
        rehacer: tipoRehacer,
      });
      if (tipoRehacer && r.borrador) {
        try {
          const ruta = await cargarBorradorParaRehacer(r.borrador, sesion.usuario.id);
          if (ruta) {
            aviso({ titulo: "Vale cancelado", descripcion: `Corrige los renglones y confirma de nuevo. Cancelación ${r.folio}.`, tipo: "exito", duracionMs: 7000 });
            setPaso(null);
            alCancelar(r);
            alCerrar();
            void navegar(ruta);
            return;
          }
        } catch (causa) {
          aviso({
            titulo: "Se canceló el vale, pero no pudimos abrir la captura",
            descripcion: `${mensajeDeError(causa)} Hazlo de nuevo desde ${rutaDeCaptura(vale.tipo) === "/devolver" ? "Devolver" : "Entregar"}.`,
            tipo: "aviso",
            duracionMs: 8000,
          });
          setPaso(null);
          alCancelar(r);
          alCerrar();
          return;
        }
      }
      aviso({
        titulo: "Vale cancelado",
        descripcion: rehacer && !tipoRehacer ? `Cancelación ${r.folio}. Este tipo de vale se vuelve a capturar desde su pantalla.` : `Cancelación ${r.folio}`,
        tipo: "exito",
        duracionMs: 6000,
      });
      setPaso(null);
      alCancelar(r);
      alCerrar();
    } catch (causa) {
      if (esErrorApi(causa) && causa.sinConexion) {
        setFallo({ tipo: "conexion", mensaje: "Sin conexión. No se canceló nada. Inténtalo otra vez en cuanto vuelva; no se cancelará dos veces.", motivos: [] });
      } else if (esErrorApi(causa) && causa.codigo === "NO_CANCELABLE") {
        const lista = Array.isArray(causa.detalles) ? (causa.detalles as unknown as MotivoNoCancelable[]) : [];
        setFallo({ tipo: "no_cancelable", mensaje: causa.message, motivos: lista });
      } else {
        setFallo({ tipo: "otro", mensaje: mensajeDeError(causa), motivos: [] });
      }
      setPaso("fallo");
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  };

  const reemplaza = tipoRehacer && hayCapturaSinTerminar(vale.tipo, sesion.usuario.id);
  const frase = [
    QUE_SE_REVIERTE[vale.tipo] ?? "Lo que movió el vale regresa a donde estaba.",
    tipoRehacer ? "Después se abre la captura con los mismos renglones para corregirlos." : null,
    reemplaza ? "Se reemplazará la captura que tienes sin terminar." : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <HojaObservacion
        abierta={paso === "motivo"}
        alCambiar={(abierta) => {
          if (!abierta && pasoRef.current === "motivo") cerrar();
        }}
        titulo={tipoRehacer ? "Cancelar y rehacer" : "Cancelar vale"}
        motivo={`Escribe por qué cancelas el vale ${vale.folio}. El motivo queda anotado en el historial.`}
        regla="K-01"
        respuestasRapidas={RESPUESTAS_RAPIDAS}
        etiquetaGuardar="Continuar"
        maxLargo={300}
        alGuardar={(texto) => {
          setMotivo(texto);
          setPaso("confirmar");
        }}
      />
      <Confirmacion
        abierta={paso === "confirmar"}
        alCambiar={(abierta) => {
          if (!abierta && pasoRef.current === "confirmar") cerrar();
        }}
        mensaje={`¿Cancelar el vale ${vale.folio}?`}
        detalle={frase}
        etiquetaConfirmar={tipoRehacer ? "Sí, cancelar y rehacer" : "Sí, cancelar vale"}
        etiquetaCancelar="No, volver"
        peligro
        cargando={enviando}
        alConfirmar={() => void cancelar()}
      />
      <Hoja
        abierta={paso === "fallo"}
        alCambiar={(abierta) => {
          if (!abierta && pasoRef.current === "fallo") cerrar();
        }}
        titulo={fallo?.tipo === "conexion" ? "Sin conexión" : "No se pudo cancelar el vale"}
        descripcion={`Vale ${vale.folio}`}
        pie={
          fallo?.tipo === "conexion" ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Boton variante="contorno" onClick={cerrar}>
                Cerrar
              </Boton>
              <Boton variante="normal" cargando={enviando} onClick={() => void cancelar()}>
                Reintentar
              </Boton>
            </div>
          ) : (
            <Boton variante="normal" onClick={cerrar}>
              Entendido
            </Boton>
          )
        }
      >
        {fallo ? (
          <div role="alert" className="flex flex-col gap-3">
            <p className="flex items-start gap-2 text-base font-semibold">
              {fallo.tipo === "conexion" ? (
                <WifiOffIcon aria-hidden="true" className="mt-1 size-5 shrink-0" />
              ) : (
                <CircleAlertIcon aria-hidden="true" className="mt-1 size-5 shrink-0 text-semaforo-rojo" />
              )}
              <span>{fallo.mensaje}</span>
            </p>
            {fallo.motivos.length > 1 ? (
              <ul className="flex flex-col gap-2">
                {fallo.motivos.map((m, i) => (
                  <li key={i} className="rounded-lg border bg-muted p-3 text-base">
                    {m.mensaje}
                    {m.regla ? <span className="ml-1.5 text-xs font-medium whitespace-nowrap text-muted-foreground">({m.regla})</span> : null}
                  </li>
                ))}
              </ul>
            ) : null}
            {fallo.tipo === "no_cancelable" ? (
              <p className="text-base text-muted-foreground">No se movió nada: el vale sigue igual. Si hay un error, se corrige con un movimiento nuevo.</p>
            ) : null}
          </div>
        ) : null}
      </Hoja>
    </>
  );
}
