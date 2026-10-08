import { FileSpreadsheetIcon, PencilLineIcon } from "lucide-react";
import { useSearchParams } from "react-router";

import { EntradaManual } from "~/componentes/entradas/entrada-manual";
import { ImportarExcel } from "~/componentes/importacion/importar-excel";
import { SinPermiso } from "~/componentes/navegacion/sin-permiso";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { cn } from "cn";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permisosAlguno: ["inventario.entradas", "inventario.importar"] };

type Metodo = "mano" | "excel";

const METODOS: { id: Metodo; titulo: string; ayuda: string; icono: typeof PencilLineIcon }[] = [
  { id: "mano", titulo: "Capturar a mano", ayuda: "Escanea o busca cada artículo", icono: PencilLineIcon },
  { id: "excel", titulo: "Desde un Excel", ayuda: "Sube o pega una tabla", icono: FileSpreadsheetIcon },
];

/**
 * «Dar entrada» (EK-04): una sola pantalla con dos métodos. Todo entra al almacén central (EK-01).
 * A mano pide `inventario.entradas`. El Excel pide `inventario.importar` y además `inventario.entradas`, porque al
 * confirmar escribe un vale de entrada; el alta de artículos nuevos sigue pidiendo `catalogo.administrar`
 * (lo revisa el servidor por fila).
 */
export default function DarEntrada() {
  const { puede } = useSesionActiva();
  const [params, setParams] = useSearchParams();

  const permitidos: Record<Metodo, boolean> = {
    mano: puede("inventario.entradas"),
    excel: puede("inventario.importar") && puede("inventario.entradas"),
  };
  const disponibles = METODOS.filter((m) => permitidos[m.id]);
  if (disponibles.length === 0) return <SinPermiso />;

  const pedido = params.get("metodo");
  const metodo: Metodo = disponibles.some((m) => m.id === pedido) ? (pedido as Metodo) : disponibles[0].id;

  return (
    <Pantalla titulo="Dar entrada" descripcion="Registra lo que llega del proveedor.">
      <div className="flex flex-col gap-6">
        {disponibles.length > 1 ? (
          <div role="group" aria-label="Cómo quieres dar la entrada" className="grid max-w-[720px] grid-cols-1 gap-3 sm:grid-cols-2">
            {disponibles.map((m) => {
              const activo = m.id === metodo;
              return (
                <button
                  key={m.id}
                  type="button"
                  aria-pressed={activo}
                  onClick={() => setParams({ metodo: m.id }, { replace: true })}
                  className={cn(
                    "flex min-h-16 items-center gap-3 rounded-2xl border-2 p-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                    activo ? "border-primary bg-accent" : "border-border bg-card hover:bg-muted",
                  )}
                >
                  <m.icono aria-hidden="true" className="size-6 shrink-0 text-marino" />
                  <span className="flex flex-col">
                    <span className="text-base font-semibold">{m.titulo}</span>
                    <span className="text-sm text-muted-foreground">{m.ayuda}</span>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        {metodo === "mano" ? <EntradaManual /> : null}
        {/* El Excel se queda montado al cambiar de método para no perder la tabla ya cargada. */}
        {permitidos.excel ? (
          <div hidden={metodo !== "excel"}>
            <ImportarExcel />
          </div>
        ) : null}
      </div>
    </Pantalla>
  );
}
