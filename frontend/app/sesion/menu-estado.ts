import { useCallback, useEffect, useState } from "react";

/** Dónde se recuerda, por persona y por navegador, qué grupos del menú están abiertos. */
const CLAVE = "imhotep.menu.grupos";

type Recordados = Record<string, boolean>;

function leer(): Recordados {
  try {
    const texto = window.localStorage.getItem(CLAVE);
    const dato: unknown = texto ? JSON.parse(texto) : null;
    if (dato && typeof dato === "object" && !Array.isArray(dato)) {
      return Object.fromEntries(Object.entries(dato).filter(([, v]) => typeof v === "boolean")) as Recordados;
    }
  } catch {
    // Sin almacenamiento o con datos dañados: se abre solo el grupo de la sección actual.
  }
  return {};
}

function guardar(valor: Recordados) {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(valor));
  } catch {
    // Sin almacenamiento simplemente no se recuerda.
  }
}

/**
 * Qué grupos del menú están abiertos. El grupo de la sección actual siempre se abre al llegar a ella;
 * lo que la persona abre o cierra a mano se recuerda en el navegador (con `try/catch`: si falla, no pasa nada).
 */
export function useGruposAbiertos(grupoActivo: string | null) {
  const [recordados, setRecordados] = useState<Recordados>(leer);

  // Al entrar a una sección, su grupo se abre (aunque estuviera cerrado la vez anterior).
  useEffect(() => {
    if (!grupoActivo) return;
    setRecordados((actual) => {
      if (actual[grupoActivo]) return actual;
      const nuevo = { ...actual, [grupoActivo]: true };
      guardar(nuevo);
      return nuevo;
    });
  }, [grupoActivo]);

  const abierto = useCallback((id: string) => recordados[id] ?? id === grupoActivo, [recordados, grupoActivo]);

  const alternar = useCallback(
    (id: string) => {
      setRecordados((actual) => {
        const estaba = actual[id] ?? id === grupoActivo;
        const nuevo = { ...actual, [id]: !estaba };
        guardar(nuevo);
        return nuevo;
      });
    },
    [grupoActivo],
  );

  return { abierto, alternar };
}
