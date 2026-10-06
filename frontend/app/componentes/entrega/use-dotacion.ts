import { useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { DotacionApi } from "./tipos";

/**
 * La dotación del trabajador, solo para sugerir (FEAT-003). Si no hay trabajador, no tiene puesto o no
 * tiene dotación, devuelve `null`: no se muestra nada ni se generan avisos. Un error al consultarla
 * tampoco estorba la entrega. `refrescar` vuelve a pedirla (por ejemplo al entrar al paso de artículos).
 */
export function useDotacion(trabajadorId: string | null, refrescar: string | number = 0): DotacionApi | null {
  const [estado, setEstado] = useState<{ id: string | null; dotacion: DotacionApi | null }>({ id: null, dotacion: null });

  useEffect(() => {
    if (!trabajadorId) return;
    const control = new AbortController();
    apiGet<DotacionApi>(`/trabajadores/${trabajadorId}/dotacion`, undefined, control.signal)
      .then((d) => setEstado({ id: trabajadorId, dotacion: d.renglones.length > 0 ? d : null }))
      .catch(() => {
        if (!control.signal.aborted) setEstado({ id: trabajadorId, dotacion: null });
      });
    return () => control.abort();
  }, [trabajadorId, refrescar]);

  return trabajadorId !== null && estado.id === trabajadorId ? estado.dotacion : null;
}
