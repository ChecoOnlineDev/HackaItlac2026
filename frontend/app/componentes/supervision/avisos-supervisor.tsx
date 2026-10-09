import { useEffect, useState } from "react";
import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { activarAvisos, admiteAvisos, cancelarAvisos } from "~/pwa/avisos";
import { esDispositivoApple, yaEstaInstalada } from "~/pwa/registrar";
import { Boton } from "~/componentes/ui/boton";

export function AvisosSupervisor() {
  const [configurados, setConfigurados] = useState(false);
  const [activos, setActivos] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState("");
  useEffect(() => {
    let vivo = true;
    if (!admiteAvisos()) return;
    void apiGet("/notificaciones/clave-publica").then(() => { if (vivo) { setConfigurados(true); void navigator.serviceWorker.getRegistration("/").then(async (r) => { const s = await r?.pushManager.getSubscription(); if (vivo) setActivos(Boolean(s)); }); } }).catch((e) => { if (vivo && (!esErrorApi(e) || e.status !== 404)) setMensaje("No pudimos revisar los avisos. La bandeja sigue actualizándose."); });
    return () => { vivo = false; };
  }, []);
  const ejecutar = async (accion: "activar" | "desactivar" | "probar") => {
    setOcupado(true); setMensaje("");
    try {
      if (accion === "activar") { await activarAvisos(); setActivos(true); setMensaje("Avisos activos en este dispositivo."); }
      else if (accion === "desactivar") { await cancelarAvisos(true); setActivos(false); setMensaje("Avisos desactivados en este dispositivo."); }
      else { const r = await apiPost<{ enviadas: number; fallidas: number }>("/notificaciones/prueba", {}); setMensaje(r.enviadas ? "Se envió la prueba a este dispositivo." : "No se pudo enviar la prueba. La bandeja sigue funcionando."); }
    } catch (e) { setMensaje(mensajeDeError(e)); }
    finally { setOcupado(false); }
  };
  if (!configurados && !mensaje) return null;
  return <section className="flex flex-col gap-2 rounded-xl border p-3">
    {configurados && esDispositivoApple() && !yaEstaInstalada() ? <p className="text-sm">En iPhone o iPad, abre Compartir y elige Agregar a inicio. Abre la aplicación instalada para activar avisos.</p> : configurados ? <div className="flex flex-wrap gap-2">
      <Boton variante="contorno" disabled={ocupado} onClick={() => void ejecutar(activos ? "desactivar" : "activar")}>{activos ? "Desactivar avisos" : "Activar avisos"}</Boton>
      {activos ? <Boton variante="texto" disabled={ocupado} onClick={() => void ejecutar("probar")}>Probar aviso</Boton> : null}
    </div> : null}
    {mensaje ? <p role="status" className="text-sm">{mensaje}</p> : null}
  </section>;
}
