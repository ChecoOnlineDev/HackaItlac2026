import { toast } from "~/components/ui/toast";

interface OpcionesAviso {
  titulo: string;
  descripcion?: string;
  tipo?: "exito" | "info" | "aviso" | "error";
  /** Botón dentro del aviso, por ejemplo "Deshacer". */
  accion?: { etiqueta: string; alHacerClic: () => void };
  /** Milisegundos en pantalla. Por omisión 5000. */
  duracionMs?: number;
}

const TIPOS = { exito: "success", info: "info", aviso: "warning", error: "error" } as const;

/**
 * Aviso breve (toast). Ejemplo del renglón agregado:
 * `aviso({ titulo: "Se agregó Casco blanco", accion: { etiqueta: "Deshacer", alHacerClic: quitar } })`
 * Devuelve un id para cerrarlo antes con `cerrarAviso(id)`.
 */
export function aviso({ titulo, descripcion, tipo = "info", accion, duracionMs = 5000 }: OpcionesAviso): string {
  return toast.add({
    title: titulo,
    description: descripcion,
    type: TIPOS[tipo],
    timeout: duracionMs,
    actionProps: accion
      ? {
          children: accion.etiqueta,
          onClick: () => {
            accion.alHacerClic();
          },
        }
      : undefined,
  });
}

export function cerrarAviso(id?: string) {
  toast.close(id);
}
