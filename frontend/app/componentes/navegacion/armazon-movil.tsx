import { ArrowLeftIcon } from "lucide-react";
import { Outlet, useLocation, useNavigate } from "react-router";

import { InterruptorTutorialCompacto } from "~/componentes/tutorial/interruptor-tutorial";
import { Boton } from "~/componentes/ui/boton";
import { useSesionActiva } from "~/sesion/sesion";
import { useManejadorAtras } from "./atras";

/** Navegación de celular y tableta: sin menú lateral; dentro de un flujo solo "Atrás" y la acción principal. */
export function ArmazonMovil({ contenido }: { contenido?: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { sesion } = useSesionActiva();
  const enInicio = pathname === "/";
  const manejadorPantalla = useManejadorAtras();

  const atras = () => {
    if (manejadorPantalla?.current) {
      manejadorPantalla.current();
      return;
    }
    const indice = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (indice > 0) navigate(-1);
    else navigate("/");
  };

  return (
    <div className="flex min-h-dvh flex-col">
      {enInicio ? null : (
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background/95 px-2 backdrop-blur">
          <Boton variante="texto" onClick={atras} className="text-marino">
            <ArrowLeftIcon aria-hidden="true" />
            Atrás
          </Boton>
          <span className="ml-auto" />
          <InterruptorTutorialCompacto />
          <span className="pr-2 text-right text-sm leading-tight text-muted-foreground">
            {sesion.almacen?.nombre ?? sesion.usuario.nombre}
          </span>
        </header>
      )}
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pt-4 pb-40">{contenido ?? <Outlet />}</main>
    </div>
  );
}
