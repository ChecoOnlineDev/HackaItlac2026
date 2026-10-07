/** Dónde se recuerda, por persona y por navegador, qué recorridos del tutorial se terminaron. */
const CLAVE = "imhotep.tutorial.terminados";

type Guardado = Record<string, string[]>;

function leerTodo(): Guardado {
  try {
    const texto = window.localStorage.getItem(CLAVE);
    const dato: unknown = texto ? JSON.parse(texto) : null;
    if (dato && typeof dato === "object" && !Array.isArray(dato)) {
      const salida: Guardado = {};
      for (const [persona, lista] of Object.entries(dato)) {
        if (Array.isArray(lista)) salida[persona] = lista.filter((x): x is string => typeof x === "string");
      }
      return salida;
    }
  } catch {
    // Sin almacenamiento o con datos dañados: todo aparece sin terminar.
  }
  return {};
}

export function leerTerminados(persona: string): string[] {
  return leerTodo()[persona] ?? [];
}

export function guardarTerminado(persona: string, recorridoId: string): string[] {
  const todo = leerTodo();
  const lista = todo[persona] ?? [];
  if (lista.includes(recorridoId)) return lista;
  const nueva = [...lista, recorridoId];
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify({ ...todo, [persona]: nueva }));
  } catch {
    // Sin almacenamiento simplemente no se recuerda.
  }
  return nueva;
}
