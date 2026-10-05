import { ShieldCheckIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { TarjetaSolicitud } from "~/componentes/supervision/tarjeta-solicitud";
import { useSolicitudes } from "~/componentes/supervision/use-solicitudes";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { mensajeDeError } from "~/api/errores";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "autorizaciones.resolver" };

export default function Autorizaciones() {
  const { puede } = useSesion();
  const { pendientes, cerradas, cargando, error, nuevas, recargar, resuelta, descartar } = useSolicitudes();

  // Un reloj para las cuentas regresivas y para atenuar las que vencen sin esperar al servidor.
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const puedeVerTrabajador = puede("trabajadores.ver");
  const sinNada = pendientes.length === 0 && cerradas.length === 0;
  const total = pendientes.length;

  return (
    <Pantalla
      titulo="Autorizaciones"
      descripcion={total > 0 ? `${total === 1 ? "Hay 1 solicitud" : `Hay ${total} solicitudes`} por autorizar. La lista se actualiza sola.` : "Aquí llegan las solicitudes de los almacenistas. La lista se actualiza sola."}
      ancho="formulario"
    >
      {cargando ? <Esqueleto tipo="tarjeta" cantidad={2} className="[&>div]:grid-cols-1" /> : null}

      {!cargando && error && sinNada ? <EstadoError error={error} alReintentar={() => void recargar()} /> : null}

      {!cargando && error && !sinNada ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border-2 border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
          <p className="text-base font-semibold">No pudimos actualizar la lista. {mensajeDeError(error)}</p>
          <Boton variante="contorno" onClick={() => void recargar()}>
            Reintentar
          </Boton>
        </div>
      ) : null}

      {!cargando && !error && sinNada ? (
        <EstadoVacio
          icono={ShieldCheckIcon}
          titulo="No hay nada por autorizar"
          descripcion="Cuando un almacenista pida una autorización, aparecerá aquí sin que tengas que recargar."
        />
      ) : null}

      {!cargando && !sinNada ? (
        <div className="flex flex-col gap-4" aria-live="polite">
          {pendientes.map((s) => (
            <TarjetaSolicitud
              key={s.id}
              solicitud={s}
              ahora={ahora}
              nueva={nuevas.has(s.id)}
              puedeVerTrabajador={puedeVerTrabajador}
              alResolver={() => resuelta(s.id)}
              alRefrescar={() => void recargar()}
            />
          ))}
          {cerradas.map((c) => (
            <TarjetaSolicitud
              key={c.solicitud.id}
              solicitud={c.solicitud}
              ahora={ahora}
              cierre={c}
              puedeVerTrabajador={puedeVerTrabajador}
              alResolver={() => descartar(c.solicitud.id)}
              alRefrescar={() => void recargar()}
              alDescartar={() => descartar(c.solicitud.id)}
            />
          ))}
        </div>
      ) : null}
    </Pantalla>
  );
}
