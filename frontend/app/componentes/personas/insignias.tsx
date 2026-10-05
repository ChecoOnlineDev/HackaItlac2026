import { CircleCheckIcon, CircleXIcon, FileCheck2Icon, PackageOpenIcon } from "lucide-react";

import { Insignia } from "~/componentes/ui/insignia";
import type { Situacion, Vigencia } from "./tipos";

// El semáforo (verde/amarillo/naranja/rojo) es solo para renglones y piezas: aquí van insignias
// neutras con icono y texto, para que nada dependa del color.

export function InsigniaSituacion({ situacion, texto }: { situacion: Situacion; texto: string }) {
  const Icono =
    situacion === "CON_PENDIENTES" ? PackageOpenIcon : situacion === "NO_ADEUDO_EMITIDO" ? FileCheck2Icon : CircleCheckIcon;
  return (
    <Insignia estado={situacion === "CON_PENDIENTES" ? "info" : "neutra"}>
      <Icono aria-hidden="true" className="size-4 shrink-0" />
      {texto}
    </Insignia>
  );
}

export function InsigniaVigencia({ vigencia }: { vigencia: Vigencia }) {
  return (
    <Insignia estado="neutra" className={vigencia.vigente ? undefined : "border-semaforo-rojo bg-semaforo-rojo/10"}>
      {vigencia.vigente ? (
        <CircleCheckIcon aria-hidden="true" className="size-4 shrink-0" />
      ) : (
        <CircleXIcon aria-hidden="true" className="size-4 shrink-0 text-semaforo-rojo" />
      )}
      {vigencia.vigente ? "Vigente" : "No vigente"}
    </Insignia>
  );
}
