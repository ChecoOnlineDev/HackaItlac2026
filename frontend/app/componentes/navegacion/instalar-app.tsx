import { DownloadIcon, ShareIcon } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Boton } from "~/componentes/ui/boton";
import {
  esDispositivoApple,
  instalarAplicacion,
  puedeInstalar,
  suscribirInstalacion,
  yaEstaInstalada,
} from "~/pwa/registrar";

/**
 * Ofrece instalar la aplicación en el dispositivo. No muestra nada si ya está instalada o si el
 * navegador no lo permite. En iPhone y iPad explica cómo agregarla a la pantalla de inicio.
 */
export function InstalarApp({ className }: { className?: string }) {
  const disponible = useSyncExternalStore(suscribirInstalacion, puedeInstalar, () => false);
  // Se decide tras montar para que el primer dibujado coincida con el del servidor.
  const [montado, setMontado] = useState(false);
  useEffect(() => setMontado(true), []);

  if (!montado || yaEstaInstalada()) return null;

  if (disponible) {
    return (
      <Boton variante="contorno" className={className} onClick={() => void instalarAplicacion()}>
        <DownloadIcon aria-hidden="true" />
        Instalar aplicación
      </Boton>
    );
  }

  if (esDispositivoApple()) {
    return (
      <p className={`flex items-start gap-2 text-sm text-muted-foreground ${className ?? ""}`}>
        <ShareIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        Para instalarla, toca Compartir y luego «Agregar a inicio».
      </p>
    );
  }

  return null;
}
