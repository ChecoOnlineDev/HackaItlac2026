import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "~/components/ui/alert-dialog";
import { Boton } from "./boton";

interface PropiedadesConfirmacion {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Qué va a pasar, en una frase: "¿Entregar 10 pares de guantes?". */
  mensaje: string;
  detalle?: string;
  etiquetaConfirmar?: string;
  etiquetaCancelar?: string;
  /** Pinta el botón de confirmar como acción que no se deshace. */
  peligro?: boolean;
  cargando?: boolean;
  alConfirmar: () => void;
}

/** Modal de una frase y dos botones. Solo para lo que no se puede deshacer. */
export function Confirmacion({
  abierta,
  alCambiar,
  mensaje,
  detalle,
  etiquetaConfirmar = "Sí, confirmar",
  etiquetaCancelar = "Corregir",
  peligro = false,
  cargando = false,
  alConfirmar,
}: PropiedadesConfirmacion) {
  return (
    <AlertDialog open={abierta} onOpenChange={alCambiar}>
      <AlertDialogContent className="data-[size=default]:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-lg font-semibold text-marino">{mensaje}</AlertDialogTitle>
          {detalle ? <AlertDialogDescription className="text-sm">{detalle}</AlertDialogDescription> : null}
        </AlertDialogHeader>
        <AlertDialogFooter className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <AlertDialogCancel render={<Boton variante="contorno" />} disabled={cargando}>
            {etiquetaCancelar}
          </AlertDialogCancel>
          <Boton variante={peligro ? "peligro" : "normal"} cargando={cargando} onClick={alConfirmar}>
            {etiquetaConfirmar}
          </Boton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
