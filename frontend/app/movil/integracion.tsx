import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import { registerPlugin, type PluginListenerHandle } from "@capacitor/core";
import { toast } from "~/components/ui/toast";
import { marcarConexion } from "~/api/red";
import { EstadoError } from "~/componentes/ui/estado-error";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "~/components/ui/alert-dialog";
import { esAppNativa } from "./plataforma";

const Impresion = registerPlugin<{ imprimir: () => Promise<void> }>("Impresion");

/** Solo funciones del contenedor Android. La captura sigue usando el servidor. */
export function IntegracionNativa({ children }: { children: ReactNode }) {
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const [salir, setSalir] = useState(false);
  const [desactualizada, setDesactualizada] = useState(false);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    if (!esAppNativa()) return;
    const actualizar = () => setDesactualizada(true);
    window.addEventListener("imhotep:actualizar-app", actualizar);
    const imprimirWeb = window.print;
    window.print = () => {
      void Impresion.imprimir().catch(() => {
        toast.add({ title: "No pudimos abrir la impresión. Inténtalo de nuevo.", type: "error" });
      });
    };
    let vigente = true;
    const oyentes: PluginListenerHandle[] = [];
    const conservar = (oyente: PluginListenerHandle) => {
      if (vigente) oyentes.push(oyente);
      else void oyente.remove();
    };
    void (async () => {
      const { Network } = await import("@capacitor/network");
      conservar(await Network.addListener("networkStatusChange", ({ connected }) => {
        if (vigente) marcarConexion(connected);
      }));
      const estado = await Network.getStatus();
      if (vigente) marcarConexion(estado.connected);
      const { limpiarCompartidos } = await import("./archivos");
      // Limpiar exportaciones es mantenimiento; un fallo no debe impedir entrar u operar.
      await limpiarCompartidos().catch(() => undefined);
    })().catch(() => { if (vigente) setFallo(true); });
    return () => {
      vigente = false;
      window.removeEventListener("imhotep:actualizar-app", actualizar);
      window.print = imprimirWeb;
      oyentes.forEach((oyente) => void oyente.remove());
    };
  }, []);

  useEffect(() => {
    if (!esAppNativa()) return;
    let vigente = true;
    let oyente: PluginListenerHandle | undefined;
    void import("@capacitor/app").then(async ({ App }) => {
      const nuevo = await App.addListener("backButton", () => {
        if (!vigente) return;
        // Un diálogo abierto conserva su foco: el primer Atrás pide cerrarlo.
        if (document.querySelector('[role="dialog"], [role="alertdialog"]')) {
          document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
          return;
        }
        if (pathname === "/" || pathname === "/entrar") setSalir(true);
        else if (Number(window.history.state?.idx ?? 0) > 0) navegar(-1);
        else navegar("/", { replace: true });
      });
      if (vigente) oyente = nuevo;
      else await nuevo.remove();
    }).catch(() => { if (vigente) setFallo(true); });
    return () => { vigente = false; void oyente?.remove(); };
  }, [pathname, navegar]);

  if (desactualizada || fallo) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md items-center p-6">
        <EstadoError mensaje={desactualizada
          ? "Hay una versión nueva de la app. Pídela a tu supervisor o al área de sistemas para seguir."
          : "No pudimos iniciar las funciones de este equipo."}
          {...(fallo ? { alReintentar: () => window.location.reload() } : {})} />
      </main>
    );
  }
  return <>
    {children}
    <AlertDialog open={salir} onOpenChange={setSalir}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>¿Cerrar IMHOTEP?</AlertDialogTitle>
          <AlertDialogDescription>Puedes volver a abrir la app para continuar.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel size="toque">Seguir aquí</AlertDialogCancel>
          <AlertDialogAction size="toque" onClick={() => {
            void import("@capacitor/app").then(({ App }) => App.exitApp());
          }}>Cerrar app</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </>;
}
