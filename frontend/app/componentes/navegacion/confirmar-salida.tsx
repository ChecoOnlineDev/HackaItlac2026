import { useState } from "react";
import { useNavigate } from "react-router";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "~/components/ui/alert-dialog";
import { Boton } from "~/componentes/ui/boton";
import { useSesionActiva } from "~/sesion/sesion";
import { DispositivosSesion } from "./dispositivos-sesion";

/**
 * Pregunta antes de cerrar la sesión de ESTE dispositivo; si se confirma, sale y regresa a Entrar.
 * Un enlace discreto abre la lista de dispositivos con sesión abierta (AC-20, AC-21).
 */
export function ConfirmarSalida({ abierta, alCambiar }: { abierta: boolean; alCambiar: (abierta: boolean) => void }) {
  const { cerrarSesion } = useSesionActiva();
  const navigate = useNavigate();
  const [saliendo, setSaliendo] = useState(false);
  const [verDispositivos, setVerDispositivos] = useState(false);

  const salir = async () => {
    setSaliendo(true);
    await cerrarSesion();
    navigate("/entrar", { replace: true });
  };

  return (
    <>
      <AlertDialog open={abierta} onOpenChange={alCambiar}>
        <AlertDialogContent className="data-[size=default]:max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-lg font-semibold text-marino">¿Cerrar tu sesión?</AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              Los borradores sin confirmar se quedan en este dispositivo. Tu sesión en otros dispositivos sigue abierta.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <AlertDialogCancel render={<Boton variante="contorno" />} disabled={saliendo}>
              Quedarme
            </AlertDialogCancel>
            <Boton variante="normal" cargando={saliendo} onClick={salir}>
              Sí, salir
            </Boton>
          </AlertDialogFooter>
          <Boton
            variante="texto"
            className="justify-self-center text-sm text-muted-foreground"
            disabled={saliendo}
            onClick={() => {
              alCambiar(false);
              setVerDispositivos(true);
            }}
          >
            Ver dispositivos con sesión abierta
          </Boton>
        </AlertDialogContent>
      </AlertDialog>
      <DispositivosSesion abierta={verDispositivos} alCambiar={setVerDispositivos} />
    </>
  );
}
