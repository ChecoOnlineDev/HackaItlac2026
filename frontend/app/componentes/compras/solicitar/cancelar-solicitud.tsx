import { useEffect, useId, useState } from "react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "~/components/ui/alert-dialog";
import { Label } from "~/components/ui/label";
import { Textarea } from "~/components/ui/textarea";
import { Boton } from "~/componentes/ui/boton";
import type { SolicitudCompra } from "./tipos";

interface Propiedades {
  /** La solicitud que se quiere cancelar; `null` cierra la ventana. */
  solicitud: SolicitudCompra | null;
  cargando?: boolean;
  /** Lo que respondió el servidor si no se pudo cancelar. */
  error?: string | null;
  alCerrar: () => void;
  alConfirmar: (nota: string) => void;
}

/** Confirmación para cancelar una solicitud pendiente (SC-07), con una nota opcional. Cancelar no se deshace. */
export function CancelarSolicitud({ solicitud, cargando = false, error, alCerrar, alConfirmar }: Propiedades) {
  const [nota, setNota] = useState("");
  // Se recuerda la última para que el título no se vacíe mientras la ventana se cierra.
  const [mostrada, setMostrada] = useState<SolicitudCompra | null>(solicitud);
  const id = useId();

  // Cada vez que se abre para otra solicitud, la nota empieza vacía.
  useEffect(() => {
    if (solicitud) {
      setNota("");
      setMostrada(solicitud);
    }
  }, [solicitud]);

  return (
    <AlertDialog open={solicitud !== null} onOpenChange={(abierta) => (!abierta && !cargando ? alCerrar() : undefined)}>
      <AlertDialogContent className="data-[size=default]:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-lg font-semibold text-marino">
            ¿Cancelar la solicitud {mostrada?.folio}?
          </AlertDialogTitle>
          <AlertDialogDescription className="text-sm">
            Compras ya no la verá como pendiente. Si la cancelas por error, tendrás que pedirla otra vez.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={id} className="text-sm font-medium text-foreground">
            Nota (opcional)
          </Label>
          <Textarea
            id={id}
            value={nota}
            maxLength={500}
            placeholder="Por ejemplo: ya llegó la herramienta"
            disabled={cargando}
            onChange={(e) => setNota(e.target.value)}
          />
        </div>
        {error ? (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {error}
          </p>
        ) : null}
        <AlertDialogFooter className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <AlertDialogCancel render={<Boton variante="contorno" />} disabled={cargando}>
            Conservarla
          </AlertDialogCancel>
          <Boton variante="peligro" cargando={cargando} onClick={() => alConfirmar(nota.trim())}>
            Sí, cancelarla
          </Boton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
