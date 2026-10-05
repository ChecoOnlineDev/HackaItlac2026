import { useState } from "react";
import { useNavigate } from "react-router";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { useSesionActiva } from "~/sesion/sesion";

/** Pregunta antes de cerrar la sesión; si se confirma, sale y regresa a Entrar. */
export function ConfirmarSalida({ abierta, alCambiar }: { abierta: boolean; alCambiar: (abierta: boolean) => void }) {
  const { cerrarSesion } = useSesionActiva();
  const navigate = useNavigate();
  const [saliendo, setSaliendo] = useState(false);

  const salir = async () => {
    setSaliendo(true);
    await cerrarSesion();
    navigate("/entrar", { replace: true });
  };

  return (
    <Confirmacion
      abierta={abierta}
      alCambiar={alCambiar}
      mensaje="¿Cerrar tu sesión?"
      detalle="Los borradores sin confirmar se quedan en este dispositivo."
      etiquetaConfirmar="Sí, salir"
      etiquetaCancelar="Quedarme"
      cargando={saliendo}
      alConfirmar={salir}
    />
  );
}
