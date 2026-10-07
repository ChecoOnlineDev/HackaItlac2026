import { CircleAlertIcon } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { Input } from "~/components/ui/input";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";

interface Propiedades {
  piezaId: string;
  codigo: string;
  articulo: string;
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Se llama tras guardar (o si la pieza ya tenía serie) para refrescar la pantalla. */
  alGuardar: () => void;
}

/** Mensaje claro para los errores de «Registrar serie» (P-08, I-02). */
function textoDeError(causa: unknown): string {
  if (esErrorApi(causa)) {
    if (causa.codigo === "SERIE_YA_REGISTRADA") return "Esta pieza ya tiene un número de serie. Cambiarlo no se puede desde aquí.";
    if (causa.codigo === "SERIE_REPETIDA") {
      const otra = causa.detalles?.pieza as { codigo?: string } | undefined;
      return otra?.codigo
        ? `Esa serie ya está registrada en otra pieza de este artículo (${otra.codigo}). Revisa que la hayas escrito bien.`
        : "Esa serie ya está registrada en otra pieza de este artículo. Revisa que la hayas escrito bien.";
    }
  }
  return mensajeDeError(causa);
}

/** Hoja con un campo para poner el número de serie a una pieza que entró sin él (`POST /api/piezas/{id}/serie`). */
export function HojaRegistrarSerie({ piezaId, codigo, articulo, abierta, alCambiar, alGuardar }: Propiedades) {
  const id = useId();
  const [serie, setSerie] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (abierta) {
      setSerie("");
      setError(null);
    }
  }, [abierta]);

  const guardar = async () => {
    const limpia = serie.trim();
    if (!limpia) {
      setError("Escribe el número de serie.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await apiPost(`/piezas/${piezaId}/serie`, { numero_serie: limpia });
      alCambiar(false);
      aviso({ titulo: "Serie registrada", tipo: "exito" });
      alGuardar();
    } catch (causa) {
      setError(textoDeError(causa));
      // Si ya tenía serie, la pantalla estaba desactualizada: se refresca.
      if (esErrorApi(causa) && causa.codigo === "SERIE_YA_REGISTRADA") alGuardar();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo="Registrar serie"
      descripcion={`${articulo} · ${codigo}`}
      pie={
        <Boton variante="principal" cargando={enviando} onClick={guardar}>
          Guardar
        </Boton>
      }
    >
      <form
        className="flex flex-col gap-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          void guardar();
        }}
      >
        <label htmlFor={id} className="text-base font-medium">
          Número de serie del fabricante
        </label>
        <Input
          id={id}
          value={serie}
          maxLength={100}
          autoComplete="off"
          autoCapitalize="characters"
          enterKeyHint="done"
          onChange={(e) => setSerie(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          placeholder="Escríbelo o escanéalo"
          className="h-12 rounded-xl text-base"
        />
        {error ? (
          <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {error}
          </p>
        ) : null}
      </form>
    </Hoja>
  );
}
