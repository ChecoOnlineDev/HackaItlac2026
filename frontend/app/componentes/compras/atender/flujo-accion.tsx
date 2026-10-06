import { cn } from "cn";
import { CircleAlertIcon, InfoIcon } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router";

import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { Textarea } from "~/components/ui/textarea";
import { refrescarContadores } from "~/sesion/contadores";
import { useSesion } from "~/sesion/sesion";
import { SelectorVale } from "./selector-vale";
import { ESTADO_DE_ACCION, TEXTO_ESTADO, type AccionSolicitud, type EstadoSolicitud, type SolicitudCompra } from "./tipos";

const MAX_NOTA = 500;

const AVISO_EXITO: Record<AccionSolicitud, string> = {
  tomar: "Solicitud tomada",
  rechazar: "Solicitud rechazada",
  comprar: "Marcada como comprada",
  ingresar: "Solicitud ingresada",
  cancelar: "Solicitud cancelada",
};

const RESPUESTAS_RECHAZO = [
  "Ya hay existencia en otro almacén",
  "Es una solicitud repetida",
  "Falta información para comprarla",
  "No hay presupuesto",
];

interface ErroresFlujo {
  general: string | null;
  nota: string | null;
  vale: string | null;
}

const SIN_ERRORES: ErroresFlujo = { general: null, nota: null, vale: null };

/** Reparte el error del servidor: el de cada campo junto a su control y el resto, arriba del pie. */
function repartirError(causa: unknown): ErroresFlujo {
  if (!esErrorApi(causa)) return { ...SIN_ERRORES, general: mensajeDeError(causa) };
  const detalles: unknown = causa.detalles;
  if (causa.codigo === "TRANSICION_INVALIDA" && detalles && !Array.isArray(detalles)) {
    // El servidor nombra los estados con su clave; aquí se dicen con palabras de Compras.
    const d = detalles as { estado_actual?: string; estado_pedido?: string };
    const actual = TEXTO_ESTADO[d.estado_actual as EstadoSolicitud];
    const pedido = TEXTO_ESTADO[d.estado_pedido as EstadoSolicitud];
    if (actual && pedido) {
      return {
        ...SIN_ERRORES,
        general: `Alguien más ya cambió esta solicitud: ahora está ${actual.toLowerCase()} y no puede pasar a ${pedido.toLowerCase()}. Actualiza para ver cómo quedó.`,
      };
    }
  }
  if (causa.status === 422 && Array.isArray(detalles)) {
    const salida: ErroresFlujo = { ...SIN_ERRORES };
    for (const d of detalles as { campo?: string; mensaje?: string }[]) {
      const texto = d.mensaje ?? causa.message;
      if (d.campo?.includes("vale_entrada")) salida.vale = texto;
      else if (d.campo?.includes("nota")) salida.nota = texto;
      else salida.general = texto;
    }
    if (!salida.general && !salida.nota && !salida.vale) salida.general = causa.message;
    return salida;
  }
  return { ...SIN_ERRORES, general: causa.message };
}

function ErrorGeneral({ texto }: { texto: string | null }) {
  if (!texto) return null;
  return (
    <p role="alert" className="flex items-start gap-1.5 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm font-medium text-destructive">
      <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      {texto}
    </p>
  );
}

interface PropiedadesCampoNota {
  valor: string;
  alCambiar: (texto: string) => void;
  etiqueta: string;
  marcador?: string;
  error?: string | null;
  rapidas?: string[];
}

function CampoNota({ valor, alCambiar, etiqueta, marcador = "Escribe aquí", error, rapidas }: PropiedadesCampoNota) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={`${id}-nota`} className="text-sm font-medium text-foreground">
        {etiqueta}
      </label>
      <Textarea
        id={`${id}-nota`}
        value={valor}
        maxLength={MAX_NOTA}
        rows={4}
        onChange={(e) => alCambiar(e.target.value)}
        placeholder={marcador}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={cn(
          "min-h-28 w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-base outline-none placeholder:text-muted-foreground",
          "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
          error && "border-destructive",
        )}
      />
      <p className="text-right text-xs text-muted-foreground">
        {valor.length} de {MAX_NOTA}
      </p>
      {error ? (
        <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
      {rapidas && rapidas.length > 0 ? (
        <div className="flex flex-wrap gap-2 pt-1">
          {rapidas.map((r) => (
            <Boton key={r} variante="contorno" className="h-10 px-3 text-sm" onClick={() => alCambiar(r)}>
              {r}
            </Boton>
          ))}
        </div>
      ) : null}
    </div>
  );
}

interface PropiedadesFlujo {
  /** La solicitud sobre la que se actúa; con `accion` en `null` no se muestra nada. */
  solicitud: SolicitudCompra | null;
  accion: AccionSolicitud | null;
  alCerrar: () => void;
  /** El servidor aceptó el cambio y devolvió la solicitud al día. */
  alTerminar: (solicitud: SolicitudCompra) => void;
  /** El servidor dijo que la solicitud ya no está como la pantalla la tenía (409): hay que recargar. */
  alDesactualizar?: () => void;
}

/**
 * Lo que sigue cuando se toca una acción de la solicitud: una confirmación (tomar) o una hoja con su nota
 * (rechazar, comprar, ingresar, cancelar). Hace la llamada al servidor, avisa y entrega la solicitud al día.
 * Los errores del servidor (409, 422) se escriben dentro de la misma ventana, junto a lo que falló.
 *
 * ```tsx
 * <FlujoAccion solicitud={s} accion={accion} alCerrar={() => setAccion(null)} alTerminar={setS} />
 * ```
 */
export function FlujoAccion({ solicitud, accion, alCerrar, alTerminar, alDesactualizar }: PropiedadesFlujo) {
  const { puede } = useSesion();
  const [nota, setNota] = useState("");
  const [valeId, setValeId] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [errores, setErrores] = useState<ErroresFlujo>(SIN_ERRORES);
  const enviandoRef = useRef(false);

  const idSolicitud = solicitud?.id ?? null;
  useEffect(() => {
    // Cada vez que se abre una acción empieza limpia.
    setNota("");
    setValeId("");
    setErrores(SIN_ERRORES);
    setEnviando(false);
    enviandoRef.current = false;
  }, [idSolicitud, accion]);

  if (!solicitud || !accion) return null;

  const cambiarNota = (texto: string) => {
    setNota(texto);
    if (errores.nota) setErrores((e) => ({ ...e, nota: null }));
  };

  const cerrar = () => {
    if (enviandoRef.current) return;
    alCerrar();
  };

  async function enviar() {
    if (!solicitud || !accion || enviandoRef.current) return;
    if (accion === "rechazar" && !nota.trim()) {
      setErrores({ ...SIN_ERRORES, nota: "Escribe por qué la rechazas para continuar." });
      return;
    }
    enviandoRef.current = true;
    setEnviando(true);
    setErrores(SIN_ERRORES);
    try {
      const texto = nota.trim() || undefined;
      const respuesta =
        accion === "cancelar"
          ? await apiPost<SolicitudCompra>(`/solicitudes-compra/${solicitud.id}/cancelacion`, texto ? { nota: texto } : {})
          : await apiPost<SolicitudCompra>(`/solicitudes-compra/${solicitud.id}/estado`, {
              estado: ESTADO_DE_ACCION[accion],
              nota: texto,
              vale_entrada_id: accion === "ingresar" && valeId ? valeId : undefined,
            });
      aviso({ titulo: AVISO_EXITO[accion], descripcion: solicitud.folio, tipo: "exito", duracionMs: 4000 });
      refrescarContadores();
      alTerminar(respuesta);
      alCerrar();
    } catch (causa) {
      setErrores(repartirError(causa));
      if (esErrorApi(causa) && (causa.status === 409 || causa.status === 404)) alDesactualizar?.();
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  const resumen = `${solicitud.folio} · ${solicitud.cantidad} × ${solicitud.descripcion}`;

  if (accion === "tomar") {
    return (
      <Confirmacion
        abierta
        alCambiar={(abierta) => {
          if (!abierta) cerrar();
        }}
        mensaje={`¿Tomar la solicitud ${solicitud.folio}?`}
        detalle={errores.general ?? "Pasa a En compra y quien la pidió verá que ya la estás atendiendo."}
        etiquetaConfirmar="Sí, tomar"
        etiquetaCancelar="No, volver"
        cargando={enviando}
        alConfirmar={() => void enviar()}
      />
    );
  }

  const ficha = {
    rechazar: {
      titulo: "Rechazar solicitud",
      confirmar: "Rechazar solicitud",
      volver: "Volver",
      peligro: true,
    },
    comprar: {
      titulo: "Marcar como comprada",
      confirmar: "Marcar como comprada",
      volver: "Volver",
      peligro: false,
    },
    ingresar: {
      titulo: "Ingresar al almacén",
      confirmar: "Ingresar",
      volver: "Volver",
      peligro: false,
    },
    cancelar: {
      titulo: "Cancelar solicitud",
      confirmar: "Sí, cancelar solicitud",
      volver: "No, volver",
      peligro: true,
    },
  }[accion];

  return (
    <Hoja
      abierta
      alCambiar={(abierta) => {
        if (!abierta) cerrar();
      }}
      titulo={ficha.titulo}
      descripcion={resumen}
      pie={
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Boton variante="contorno" disabled={enviando} onClick={cerrar}>
            {ficha.volver}
          </Boton>
          <Boton variante={ficha.peligro ? "peligro" : "normal"} cargando={enviando} onClick={() => void enviar()}>
            {ficha.confirmar}
          </Boton>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {accion === "rechazar" ? (
          <CampoNota
            etiqueta="¿Por qué la rechazas?"
            marcador="Quien la pidió lo leerá en su solicitud"
            valor={nota}
            alCambiar={cambiarNota}
            error={errores.nota}
            rapidas={RESPUESTAS_RECHAZO}
          />
        ) : null}

        {accion === "comprar" ? (
          <>
            <p className="flex items-start gap-2 rounded-xl border bg-muted p-3 text-sm">
              <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
              <span>Avisa que ya se compró. Cuando llegue, la ingresas al almacén.</span>
            </p>
            <CampoNota
              etiqueta="Nota (opcional)"
              marcador="Por ejemplo: proveedor o día en que llega"
              valor={nota}
              alCambiar={cambiarNota}
              error={errores.nota}
            />
          </>
        ) : null}

        {accion === "ingresar" ? (
          <>
            <p className="flex items-start gap-2 rounded-xl border bg-muted p-3 text-sm">
              <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
              <span>
                Esto no suma existencias por sí solo: suben con el vale de entrada.{" "}
                {puede("inventario.entradas") ? (
                  <>
                    Si aún no lo registras, hazlo en{" "}
                    <Link to="/entradas/nueva" className="font-semibold text-primary underline underline-offset-2">
                      Entradas
                    </Link>
                    .
                  </>
                ) : null}
              </span>
            </p>
            <SelectorVale valor={valeId} alElegir={(id) => setValeId(id)} error={errores.vale} />
            <CampoNota
              etiqueta="Nota (opcional)"
              marcador="Por ejemplo: llegó completo"
              valor={nota}
              alCambiar={cambiarNota}
              error={errores.nota}
            />
          </>
        ) : null}

        {accion === "cancelar" ? (
          <>
            <p className="flex items-start gap-2 rounded-xl border bg-muted p-3 text-sm">
              <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
              <span>Solo se puede cancelar mientras Compras no la toma. Después de cancelarla ya no se puede reabrir.</span>
            </p>
            <CampoNota
              etiqueta="Nota (opcional)"
              marcador="Por ejemplo: ya se consiguió prestada"
              valor={nota}
              alCambiar={cambiarNota}
              error={errores.nota}
            />
          </>
        ) : null}

        <ErrorGeneral texto={errores.general} />
      </div>
    </Hoja>
  );
}
