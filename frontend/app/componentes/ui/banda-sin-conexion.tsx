import { WifiOffIcon } from "lucide-react";

import { useEnLinea } from "~/api/red";

/** Banda global "Sin conexión"; se muestra sola cuando el navegador o la API pierden la red. */
export function BandaSinConexion() {
  const enLinea = useEnLinea();
  if (enLinea) return null;
  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[60] flex items-center justify-center gap-2 bg-foreground px-4 py-2 text-center text-sm font-semibold text-background"
    >
      <WifiOffIcon aria-hidden="true" className="size-4 shrink-0" />
      Sin conexión. Lo que capturaste se conserva en este dispositivo.
    </div>
  );
}
