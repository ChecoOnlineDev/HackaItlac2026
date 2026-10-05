import { cn } from "cn";
import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { Textarea } from "~/components/ui/textarea";
import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { formatearFecha, hoyMexico, sumarDias } from "~/componentes/dominio/fechas";
import { PUNTOS_INSPECCION, type ClavePunto, type FichaPieza } from "./tipos";

interface PropiedadesHojaPieza {
  pieza: FichaPieza;
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Se llama tras guardar con éxito, para que la ficha se refresque. */
  alGuardar: () => void;
}

function ErrorEnHoja({ mensaje }: { mensaje: string | null }) {
  if (!mensaje) return null;
  return (
    <p role="alert" className="flex items-start gap-2 rounded-xl border-2 border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-semibold">
      <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-rojo" />
      {mensaje}
    </p>
  );
}

function CampoObservacion({
  valor,
  alCambiar,
  etiqueta,
  error,
  obligatoria,
  maxLargo = 1000,
}: {
  valor: string;
  alCambiar: (v: string) => void;
  etiqueta: string;
  error: string | null;
  obligatoria?: boolean;
  maxLargo?: number;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-base font-medium">
        {etiqueta}
        {obligatoria ? "" : " (opcional)"}
      </label>
      <Textarea
        id={id}
        value={valor}
        rows={3}
        maxLength={maxLargo}
        onChange={(e) => alCambiar(e.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        placeholder="Escribe aquí"
        className={cn(
          "min-h-24 w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-base outline-none placeholder:text-muted-foreground",
          "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
          error && "border-destructive",
        )}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------------------ inspeccionar

type Resultado = "APTO" | "NO_APTO" | null;

/** Flujo 13: cinco puntos, Apto o No apto y observación (obligatoria si No apto). P-01. */
export function HojaInspeccion({ pieza, abierta, alCambiar, alGuardar }: PropiedadesHojaPieza) {
  const [puntos, setPuntos] = useState<Partial<Record<ClavePunto, boolean>>>({});
  const [resultado, setResultado] = useState<Resultado>(null);
  const [observacion, setObservacion] = useState("");
  const [intento, setIntento] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (abierta) {
      setPuntos({});
      setResultado(null);
      setObservacion("");
      setIntento(false);
      setError(null);
    }
  }, [abierta]);

  const marcar = (clave: ClavePunto, bien: boolean) => {
    setPuntos((p) => ({ ...p, [clave]: bien }));
    // Un punto con problema sugiere No apto, pero la persona decide.
    if (!bien) setResultado((r) => r ?? "NO_APTO");
  };

  const errorResultado = intento && !resultado ? "Elige si la pieza está Apta o No apta." : null;
  const errorObservacion =
    intento && resultado === "NO_APTO" && !observacion.trim() ? "Escribe qué daño tiene la pieza." : null;

  const guardar = async () => {
    setIntento(true);
    if (!resultado || (resultado === "NO_APTO" && !observacion.trim())) return;
    setEnviando(true);
    setError(null);
    try {
      const cuerpo: Record<string, unknown> = { resultado };
      if (Object.keys(puntos).length > 0) cuerpo.puntos = puntos;
      if (observacion.trim()) cuerpo.observacion = observacion.trim();
      await apiPost(`/piezas/${pieza.id}/inspecciones`, cuerpo);
      alCambiar(false);
      aviso({
        titulo: resultado === "APTO" ? "Inspección guardada: la pieza quedó apta" : "Inspección guardada: la pieza quedó no apta",
        tipo: resultado === "APTO" ? "exito" : "aviso",
      });
      alGuardar();
    } catch (causa) {
      setError(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo="Inspeccionar pieza"
      descripcion={`${pieza.articulo.nombre} · ${pieza.codigo}`}
      pie={
        <Boton variante="principal" cargando={enviando} onClick={guardar}>
          Guardar inspección
        </Boton>
      }
    >
      <div className="flex flex-col gap-5">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-base font-semibold text-marino">Revisa cada punto</legend>
          {PUNTOS_INSPECCION.map((p) => {
            const valor = puntos[p.clave];
            return (
              <div key={p.clave} className="flex flex-col gap-2 rounded-xl border p-3">
                <p className="text-base font-medium">{p.etiqueta}</p>
                <div className="grid grid-cols-2 gap-2">
                  <Boton
                    variante={valor === true ? "normal" : "contorno"}
                    aria-pressed={valor === true}
                    onClick={() => marcar(p.clave, true)}
                  >
                    <CheckIcon aria-hidden="true" />
                    Bien
                  </Boton>
                  <Boton
                    variante={valor === false ? "peligro" : "contorno"}
                    aria-pressed={valor === false}
                    onClick={() => marcar(p.clave, false)}
                  >
                    <XIcon aria-hidden="true" />
                    Con problema
                  </Boton>
                </div>
              </div>
            );
          })}
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-base font-semibold text-marino">Resultado</legend>
          <div className="grid grid-cols-2 gap-2">
            <Boton
              variante={resultado === "APTO" ? "normal" : "contorno"}
              aria-pressed={resultado === "APTO"}
              className="h-12 text-base"
              onClick={() => setResultado("APTO")}
            >
              <CheckIcon aria-hidden="true" />
              Apta
            </Boton>
            <Boton
              variante={resultado === "NO_APTO" ? "peligro" : "contorno"}
              aria-pressed={resultado === "NO_APTO"}
              className="h-12 text-base"
              onClick={() => setResultado("NO_APTO")}
            >
              <XIcon aria-hidden="true" />
              No apta
            </Boton>
          </div>
          {errorResultado ? (
            <p role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              {errorResultado}
            </p>
          ) : null}
        </fieldset>

        <CampoObservacion
          valor={observacion}
          alCambiar={setObservacion}
          etiqueta="Observaciones"
          obligatoria={resultado === "NO_APTO"}
          error={errorObservacion}
        />
        <ErrorEnHoja mensaje={error} />
      </div>
    </Hoja>
  );
}

// ------------------------------------------------------------------------------ marcar No apta

/** P-03: cualquiera con `piezas.inspeccionar` puede marcarla al ver un daño; la observación es obligatoria. */
export function HojaMarcarNoApta({ pieza, abierta, alCambiar, alGuardar }: PropiedadesHojaPieza) {
  const [observacion, setObservacion] = useState("");
  const [intento, setIntento] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (abierta) {
      setObservacion("");
      setIntento(false);
      setError(null);
    }
  }, [abierta]);

  const guardar = async () => {
    setIntento(true);
    if (!observacion.trim()) return;
    setEnviando(true);
    setError(null);
    try {
      await apiPost(`/piezas/${pieza.id}/estado`, { estado: "NO_APTO", observacion: observacion.trim() });
      alCambiar(false);
      aviso({ titulo: "La pieza quedó marcada como no apta", tipo: "aviso" });
      alGuardar();
    } catch (causa) {
      setError(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo="Marcar como no apta"
      descripcion={`${pieza.articulo.nombre} · ${pieza.codigo}`}
      pie={
        <Boton variante="principal" cargando={enviando} onClick={guardar}>
          Marcar como no apta
        </Boton>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="rounded-xl border bg-muted p-3 text-sm">
          Mientras esté no apta no se entrega a nadie. Solo una inspección nueva la regresa a apta.
        </p>
        <CampoObservacion
          valor={observacion}
          alCambiar={setObservacion}
          etiqueta="¿Qué daño tiene?"
          obligatoria
          error={intento && !observacion.trim() ? "Escribe qué daño tiene la pieza." : null}
        />
        <ErrorEnHoja mensaje={error} />
      </div>
    </Hoja>
  );
}

// ------------------------------------------------------------------------------ ajustar vigencia

/** P-07: la fecha nueva y el motivo; antes de guardar se dice en una frase qué va a cambiar. */
export function HojaAjusteVigencia({ pieza, abierta, alCambiar, alGuardar }: PropiedadesHojaPieza) {
  const [fecha, setFecha] = useState("");
  const [motivo, setMotivo] = useState("");
  const [intento, setIntento] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorFecha, setErrorFecha] = useState<string | null>(null);

  const actual = pieza.inspeccion_vigente_hasta;
  const inspeccion = pieza.ultima_inspeccion;
  const dias = pieza.articulo.vigencia_inspeccion_dias;
  const limite = inspeccion && dias ? sumarDias(inspeccion.fecha, dias) : null;

  useEffect(() => {
    if (abierta) {
      setFecha(actual ?? "");
      setMotivo("");
      setIntento(false);
      setConfirmando(false);
      setError(null);
      setErrorFecha(null);
    }
  }, [abierta, actual]);

  const faltaFecha = intento && !fecha ? "Elige la fecha nueva." : null;
  const faltaMotivo = intento && !motivo.trim() ? "Escribe el motivo del cambio." : null;
  const sinCambio = fecha !== "" && fecha === actual;

  const revisar = () => {
    setIntento(true);
    setError(null);
    setErrorFecha(null);
    if (!fecha || !motivo.trim()) return;
    if (sinCambio) {
      setErrorFecha("Es la misma fecha que ya tiene. Elige otra.");
      return;
    }
    setConfirmando(true);
  };

  const guardar = async () => {
    setEnviando(true);
    try {
      await apiPost(`/piezas/${pieza.id}/ajuste-vigencia`, { vigente_hasta: fecha, motivo: motivo.trim() });
      setConfirmando(false);
      alCambiar(false);
      aviso({ titulo: `Listo: la inspección vale hasta el ${formatearFecha(fecha)}`, tipo: "exito" });
      alGuardar();
    } catch (causa) {
      setConfirmando(false);
      if (esErrorApi(causa) && causa.codigo === "VIGENCIA_EXCEDIDA") setErrorFecha(causa.message);
      else setError(mensajeDeError(causa));
    } finally {
      setEnviando(false);
    }
  };

  const frase = actual
    ? `¿Cambiar la vigencia de ${pieza.codigo} del ${formatearFecha(actual)} al ${fecha ? formatearFecha(fecha) : ""}?`
    : `¿Dar a ${pieza.codigo} vigencia hasta el ${fecha ? formatearFecha(fecha) : ""}?`;

  return (
    <>
      <Hoja
        abierta={abierta}
        alCambiar={alCambiar}
        titulo="Ajustar vigencia"
        descripcion={`${pieza.articulo.nombre} · ${pieza.codigo}`}
        pie={
          <Boton variante="principal" cargando={enviando} onClick={revisar}>
            Revisar el cambio
          </Boton>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="rounded-xl border bg-muted p-3 text-sm">
            {actual ? `Hoy la inspección vale hasta el ${formatearFecha(actual)}. ` : "Esta pieza no tiene inspección vigente. "}
            {limite ? `Puede llegar, como máximo, hasta el ${formatearFecha(limite)}. ` : ""}
            Acortarla no tiene límite. El resultado de la inspección no cambia.
          </p>
          <CampoFecha
            etiqueta="Fecha nueva"
            value={fecha}
            min={hoyMexico()}
            max={limite ?? undefined}
            alCambiar={(v) => {
              setFecha(v);
              setErrorFecha(null);
            }}
            error={errorFecha ?? faltaFecha}
          />
          <CampoObservacion
            valor={motivo}
            alCambiar={setMotivo}
            etiqueta="Motivo del cambio"
            obligatoria
            maxLargo={255}
            error={faltaMotivo}
          />
          <ErrorEnHoja mensaje={error} />
        </div>
      </Hoja>
      <Confirmacion
        abierta={confirmando}
        alCambiar={setConfirmando}
        mensaje={frase}
        detalle="Queda en el historial de la pieza con la fecha anterior, la nueva, tu nombre y el motivo."
        etiquetaConfirmar="Sí, cambiar la vigencia"
        cargando={enviando}
        alConfirmar={guardar}
      />
    </>
  );
}
