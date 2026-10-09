import { ShieldCheckIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { esTraslado } from "~/componentes/consulta/tipos";
import { TarjetaTraslado } from "~/componentes/supervision/tarjeta-traslado";
import { AvisosSupervisor } from "~/componentes/supervision/avisos-supervisor";
import { TarjetaSolicitud } from "~/componentes/supervision/tarjeta-solicitud";
import { useSolicitudes } from "~/componentes/supervision/use-solicitudes";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { apiPost } from "~/api/cliente";
import { aviso } from "~/componentes/ui/aviso";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { mensajeDeError } from "~/api/errores";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "autorizaciones.resolver" };

export default function Autorizaciones() {
  const { puede, sesion } = useSesion();
  const [almacenId, setAlmacenId] = useState("");
  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set());
  const [lote, setLote] = useState<"APROBAR" | "RECHAZAR" | null>(null);
  const [motivo, setMotivo] = useState("");
  const [guardandoLote, setGuardandoLote] = useState(false);
  const { pendientes, cerradas, cargando, error, nuevas, recargar, resuelta, descartar } = useSolicitudes(almacenId || undefined);

  useEffect(() => {
    const visibles = new Set(pendientes.map((s) => s.id));
    setSeleccionadas((anteriores) => {
      const vigentes = new Set([...anteriores].filter((id) => visibles.has(id)));
      return vigentes.size === anteriores.size ? anteriores : vigentes;
    });
  }, [pendientes]);

  // Un reloj para las cuentas regresivas y para atenuar las que vencen sin esperar al servidor.
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const puedeVerTrabajador = puede("trabajadores.ver");
  const sinNada = pendientes.length === 0 && cerradas.length === 0;
  const total = pendientes.length;

  const resolverLote = async () => {
    if (!lote || (lote === "RECHAZAR" && !motivo.trim())) return;
    setGuardandoLote(true);
    try {
      const r = await apiPost<{ resultados: { id: string; estado: string | null; error: { mensaje?: string } | null }[] }>("/autorizaciones/resolucion-multiple", {
        resoluciones: [...seleccionadas].map((id) => ({ id, decision: lote, motivo: lote === "RECHAZAR" ? motivo.trim() : undefined })),
      });
      for (const item of r.resultados) {
        if (item.error) aviso({ titulo: item.error.mensaje ?? "No se pudo resolver una solicitud. Ábrela para revisarla.", tipo: "error", duracionMs: 8000 });
        else resuelta(item.id);
      }
      setSeleccionadas(new Set(r.resultados.filter((x) => x.error).map((x) => x.id)));
      setLote(null);
      await recargar();
    } catch (causa) { aviso({ titulo: mensajeDeError(causa), tipo: "error" }); }
    finally { setGuardandoLote(false); }
  };

  return (
    <Pantalla
      titulo="Autorizaciones"
      descripcion={total > 0 ? `${total === 1 ? "Hay 1 solicitud" : `Hay ${total} solicitudes`} por autorizar. La lista se actualiza sola.` : "Aquí llegan las solicitudes de los almacenistas. La lista se actualiza sola."}
      ancho="formulario"
    >
      <AvisosSupervisor />
      {(sesion?.almacenes?.length ?? 0) > 1 ? <div className="flex flex-col gap-1.5"><label htmlFor="almacen-autorizaciones" className="text-sm font-semibold">Almacén</label><ListaDesplegable id="almacen-autorizaciones" valor={almacenId} alCambiar={(v) => { setAlmacenId(v); setSeleccionadas(new Set()); }} opciones={[{ valor: "", texto: "Todos mis almacenes" }, ...(sesion?.almacenes ?? []).map((a) => ({ valor: a.id, texto: `${a.clave} · ${a.nombre}` }))]} /></div> : null}
      {pendientes.some((s) => !esTraslado(s)) ? <section className="flex flex-col gap-3 rounded-xl border p-3">
        <p className="font-semibold">Resolver varias solicitudes</p>
        <div className="flex flex-col gap-2">{pendientes.filter((s) => !esTraslado(s) && s.solicitada_por.id !== sesion?.usuario.id).map((s) => <label key={s.id} className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
          <input type="checkbox" checked={seleccionadas.has(s.id)} disabled={guardandoLote || (!seleccionadas.has(s.id) && seleccionadas.size >= 50)} onChange={(e) => setSeleccionadas((previas) => { const siguientes = new Set(previas); if (e.target.checked) siguientes.add(s.id); else siguientes.delete(s.id); return siguientes; })} />
          {!esTraslado(s) ? s.trabajador.nombre : ""}{(!esTraslado(s) && s.incluye_excedente) ? " · Tiene excedente: revísala por separado" : ""}
        </label>)}</div>
        {seleccionadas.size ? <div className="flex flex-wrap gap-2"><Boton disabled={guardandoLote} onClick={() => setLote("APROBAR")}>Aprobar {seleccionadas.size}</Boton><Boton variante="contorno" disabled={guardandoLote} onClick={() => { setMotivo(""); setLote("RECHAZAR"); }}>Rechazar {seleccionadas.size}</Boton></div> : null}
      </section> : null}
      <Hoja abierta={lote !== null} alCambiar={(a) => { if (!a && !guardandoLote) setLote(null); }} titulo={lote === "APROBAR" ? "Aprobar solicitudes seleccionadas" : "Rechazar solicitudes seleccionadas"}
        pie={<Boton cargando={guardandoLote} disabled={guardandoLote || (lote === "RECHAZAR" && !motivo.trim())} onClick={() => void resolverLote()}>Confirmar {seleccionadas.size} solicitudes</Boton>}>
        <p className="mb-3 text-sm">Cada solicitud se revisa por separado. Las que tengan excedentes deben abrirse y revisarse individualmente.</p>
        {lote === "RECHAZAR" ? <Campo etiqueta="Motivo del rechazo para las seleccionadas" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} required /> : null}
      </Hoja>
      {cargando ? <Esqueleto tipo="tarjeta" cantidad={2} className="[&>div]:grid-cols-1" /> : null}

      {!cargando && error && sinNada ? <EstadoError error={error} alReintentar={() => void recargar()} /> : null}

      {!cargando && error && !sinNada ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
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
          {pendientes.map((s) =>
            esTraslado(s) ? (
              <TarjetaTraslado
                key={s.id}
                solicitud={s}
                ahora={ahora}
                nueva={nuevas.has(s.id)}
                esPropia={s.solicitada_por.id === sesion?.usuario.id}
                alResolver={() => resuelta(s.id)}
                alRefrescar={() => void recargar()}
              />
            ) : (
              <TarjetaSolicitud
                key={s.id}
                solicitud={s}
                ahora={ahora}
                nueva={nuevas.has(s.id)}
                esPropia={s.solicitada_por.id === sesion?.usuario.id}
                puedeVerTrabajador={puedeVerTrabajador}
                alResolver={() => resuelta(s.id)}
                alRefrescar={() => void recargar()}
              />
            ),
          )}
          {cerradas.map((c) =>
            esTraslado(c.solicitud) ? (
              <TarjetaTraslado
                key={c.solicitud.id}
                solicitud={c.solicitud}
                ahora={ahora}
                cierre={c}
                alResolver={() => descartar(c.solicitud.id)}
                alRefrescar={() => void recargar()}
                alDescartar={() => descartar(c.solicitud.id)}
              />
            ) : (
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
            ),
          )}
        </div>
      ) : null}
    </Pantalla>
  );
}
