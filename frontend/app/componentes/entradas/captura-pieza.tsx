import { cn } from "cn";
import { CheckIcon } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { Textarea } from "~/components/ui/textarea";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import type { ArticuloFichaEntrada, InspeccionBorrador, PiezaBorrador, ResultadoInspeccion } from "./tipos";

type EleccionInspeccion = ResultadoInspeccion | "PENDIENTE";

const OPCIONES: { valor: EleccionInspeccion; texto: string }[] = [
  { valor: "APTO", texto: "Apta" },
  { valor: "NO_APTO", texto: "No apta" },
  { valor: "PENDIENTE", texto: "Dejar pendiente" },
];

interface Propiedades {
  articulo: Pick<ArticuloFichaEntrada, "nombre" | "marca" | "requiere_inspeccion">;
  /** Datos con los que abre, al corregir una pieza ya agregada. */
  inicial?: PiezaBorrador;
  /** Código leído por la cámara o la pistola mientras esta captura está abierta. */
  codigoLeido?: { valor: string; n: number } | null;
  alGuardar: (pieza: PiezaBorrador, capturarOtra: boolean) => void;
  alCancelar: () => void;
}

/**
 * Captura de una pieza que entra (I-02, I-03): su código único, su número de serie y, si el artículo
 * requiere inspección, la inspección inicial (Apta o No apta con observación) o dejarla pendiente.
 * Solo reúne los datos; el servidor decide si son válidos (código repetido, serie en uso...).
 */
export function CapturaPieza({ articulo, inicial, codigoLeido, alGuardar, alCancelar }: Propiedades) {
  const id = useId();
  const refCodigo = useRef<HTMLInputElement>(null);
  const refTarjeta = useRef<HTMLElement>(null);
  const [codigo, setCodigo] = useState(inicial?.codigo ?? "");
  const [serie, setSerie] = useState(inicial?.numero_serie ?? "");
  const [eleccion, setEleccion] = useState<EleccionInspeccion>(inicial?.inspeccion?.resultado ?? "PENDIENTE");
  const [observacion, setObservacion] = useState(inicial?.inspeccion?.observacion ?? "");
  const [intento, setIntento] = useState(false);
  const editando = Boolean(inicial);

  useEffect(() => {
    refTarjeta.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    refCodigo.current?.focus({ preventScroll: true });
  }, []);

  // Lo que lee la cámara o la pistola llena el código de la pieza.
  useEffect(() => {
    if (codigoLeido) setCodigo(codigoLeido.valor);
  }, [codigoLeido]);

  const errorCodigo = intento && !codigo.trim() ? "Escribe o escanea el código de la pieza." : null;
  const errorObservacion =
    intento && eleccion === "NO_APTO" && !observacion.trim() ? "Escribe por qué no es apta." : null;

  function guardar(otra: boolean) {
    setIntento(true);
    if (!codigo.trim()) return;
    if (eleccion === "NO_APTO" && !observacion.trim()) return;
    const inspeccion: InspeccionBorrador | null =
      articulo.requiere_inspeccion && eleccion !== "PENDIENTE"
        ? { resultado: eleccion, observacion: observacion.trim() }
        : null;
    alGuardar({ codigo: codigo.trim(), numero_serie: serie.trim(), inspeccion }, otra);
    if (otra) {
      setCodigo("");
      setSerie("");
      setObservacion("");
      setEleccion("PENDIENTE");
      setIntento(false);
      refCodigo.current?.focus();
    }
  }

  return (
    <section
      ref={refTarjeta}
      aria-labelledby={`${id}-titulo`}
      className="flex flex-col gap-4 rounded-xl border-2 border-primary p-4"
    >
      <header className="flex flex-col">
        <h2 id={`${id}-titulo`} className="text-lg font-bold text-marino">
          {editando ? "Corregir la pieza" : "Pieza que entra"}
        </h2>
        <p className="text-base">
          {articulo.nombre}
          {articulo.marca ? <span className="text-muted-foreground"> · Marca {articulo.marca}</span> : null}
        </p>
      </header>

      <Campo
        ref={refCodigo}
        etiqueta="Código de la pieza"
        value={codigo}
        onChange={(e) => setCodigo(e.target.value)}
        error={errorCodigo}
        ayuda="Escanéalo con la cámara o la pistola, o escríbelo. Cada pieza lleva un código distinto."
        autoComplete="off"
        autoCapitalize="characters"
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            guardar(false);
          }
        }}
      />
      <Campo
        etiqueta="Número de serie del fabricante"
        value={serie}
        onChange={(e) => setSerie(e.target.value)}
        autoComplete="off"
      />

      {articulo.requiere_inspeccion ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-base font-medium">Inspección inicial</legend>
          <div role="radiogroup" aria-label="Inspección inicial" className="flex flex-wrap gap-2">
            {OPCIONES.map((o) => {
              const activa = eleccion === o.valor;
              return (
                <Boton
                  key={o.valor}
                  role="radio"
                  aria-checked={activa}
                  variante={activa ? "normal" : "contorno"}
                  className={cn(activa && "ring-2 ring-primary ring-offset-2")}
                  onClick={() => setEleccion(o.valor)}
                >
                  {activa ? <CheckIcon aria-hidden="true" strokeWidth={3} /> : null}
                  {o.texto}
                </Boton>
              );
            })}
          </div>
          <p className="text-sm text-muted-foreground">
            {eleccion === "PENDIENTE"
              ? "Sin inspección, la pieza queda pendiente y no se puede entregar."
              : "La inspección se anota con la fecha de hoy."}
          </p>
          {eleccion === "NO_APTO" ? (
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`${id}-obs`} className="text-base font-medium">
                ¿Por qué no es apta?
              </label>
              <Textarea
                id={`${id}-obs`}
                value={observacion}
                maxLength={300}
                rows={3}
                onChange={(e) => setObservacion(e.target.value)}
                aria-invalid={errorObservacion ? true : undefined}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-base outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive"
              />
              {errorObservacion ? (
                <p role="alert" className="text-sm font-medium text-destructive">
                  {errorObservacion}
                </p>
              ) : null}
            </div>
          ) : null}
        </fieldset>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <Boton variante="normal" onClick={() => guardar(false)}>
          {editando ? "Guardar cambios" : "Agregar pieza"}
        </Boton>
        {!editando ? (
          <Boton variante="secundario" onClick={() => guardar(true)}>
            Agregar y capturar otra
          </Boton>
        ) : null}
        <Boton variante="texto" onClick={alCancelar}>
          Cancelar
        </Boton>
      </div>
    </section>
  );
}
