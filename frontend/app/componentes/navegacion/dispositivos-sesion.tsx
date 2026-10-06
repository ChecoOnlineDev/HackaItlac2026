import { useCallback, useEffect, useState } from "react";

import { api } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { Dispositivo, Dispositivos } from "~/api/tipos";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { aviso } from "~/componentes/ui/aviso";
import { useSesionActiva } from "~/sesion/sesion";

/** Las sesiones abiertas de la persona, con «Cerrar las demás» y «Cerrar en todos» (AC-20, AC-21). */
export function DispositivosSesion({ abierta, alCambiar }: { abierta: boolean; alCambiar: (abierta: boolean) => void }) {
  const { cerrarTodas } = useSesionActiva();
  const [lista, setLista] = useState<Dispositivo[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cerrando, setCerrando] = useState<"otras" | "todas" | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const respuesta = await api<Dispositivos>("/sesion/dispositivos");
      setLista(respuesta.dispositivos);
    } catch (causa) {
      setError(causa);
    }
  }, []);

  useEffect(() => {
    if (!abierta) return;
    setLista(null);
    void cargar();
  }, [abierta, cargar]);

  const cerrarOtras = async () => {
    setCerrando("otras");
    try {
      const { cerradas } = await api<{ cerradas: number }>("/sesion/otras", { metodo: "DELETE" });
      aviso({
        tipo: "exito",
        titulo: cerradas === 1 ? "Se cerró 1 sesión" : `Se cerraron ${cerradas} sesiones`,
      });
      await cargar();
    } catch (causa) {
      aviso({ tipo: "error", titulo: mensajeDeError(causa) });
    } finally {
      setCerrando(null);
    }
  };

  const cerrarEnTodos = async () => {
    setCerrando("todas");
    try {
      await cerrarTodas();
    } catch (causa) {
      setCerrando(null);
      aviso({ tipo: "error", titulo: mensajeDeError(causa) });
    }
  };

  const hayOtras = (lista?.length ?? 0) > 1;

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo="Dispositivos con sesión abierta"
      descripcion="Tu sesión se renueva sola mientras la uses. Cierra las que no reconozcas."
      pie={
        <div className="grid grid-cols-1 gap-3">
          <Boton variante="contorno" disabled={!hayOtras || cerrando !== null} cargando={cerrando === "otras"} onClick={cerrarOtras}>
            Cerrar las demás
          </Boton>
          <Boton variante="peligro" disabled={cerrando !== null} cargando={cerrando === "todas"} onClick={cerrarEnTodos}>
            Cerrar todas, también esta
          </Boton>
        </div>
      }
    >
      {error ? (
        <EstadoError error={error} alReintentar={() => void cargar()} />
      ) : lista === null ? (
        <Cargando variante="en-linea" texto="Buscando tus sesiones" />
      ) : (
        <ul className="flex flex-col gap-3">
          {lista.map((d) => (
            <li key={d.id} className="flex flex-col gap-1 rounded-xl border p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold text-foreground">{d.agente ?? "Dispositivo desconocido"}</p>
                {d.actual ? <Insignia estado="info">Este dispositivo</Insignia> : null}
              </div>
              <p className="text-sm text-muted-foreground">Entraste el {formatearFechaHora(d.inicio)}</p>
              <p className="text-sm text-muted-foreground">Último uso: {formatearFechaHora(d.ultimo_uso)}</p>
            </li>
          ))}
        </ul>
      )}
    </Hoja>
  );
}
