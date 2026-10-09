import { useCallback, useEffect, useState } from "react";
import { apiGet } from "~/api/cliente";
import { practicaActiva } from "~/api/practica";
import { aviso } from "~/componentes/ui/aviso";
import { reproducir } from "~/componentes/dominio/sonido";
import type { BorradorEntrega } from "./borrador";
import type { AutorizacionApi } from "./tipos";

const CLAVE = "imhotep.borrador.entregas.en-espera.v1";
export const CAMBIO_ESPERAS = "imhotep:entregas-en-espera";
export function leerEntregasEnEspera(usuarioId: string): BorradorEntrega[] {
  if (practicaActiva()) return [];
  try {
    const datos: unknown = JSON.parse(localStorage.getItem(CLAVE) ?? "[]");
    return Array.isArray(datos) ? datos.filter((b): b is BorradorEntrega => b && b.version === 1 && b.usuarioId === usuarioId && typeof b.idCliente === "string" && b.autorizacion && Array.isArray(b.renglones)).slice(0, 10) : [];
  } catch { return []; }
}
export function guardarEntregasEnEspera(borradores: BorradorEntrega[]): boolean {
  if (practicaActiva()) return true;
  if (borradores.length > 10) return false;
  try { localStorage.setItem(CLAVE, JSON.stringify(borradores)); window.dispatchEvent(new Event(CAMBIO_ESPERAS)); return true; }
  catch { return false; }
}

/** La cola pertenece al usuario y dispositivo; el servidor sigue decidiendo cada estado. */
export function useEntregasEnEspera(usuarioId: string) {
  const [borradores, setBorradores] = useState(() => leerEntregasEnEspera(usuarioId));
  const recargar = useCallback(() => setBorradores(leerEntregasEnEspera(usuarioId)), [usuarioId]);
  useEffect(() => {
    recargar();
    window.addEventListener(CAMBIO_ESPERAS, recargar);
    return () => window.removeEventListener(CAMBIO_ESPERAS, recargar);
  }, [recargar]);
  useEffect(() => {
    const control = new AbortController();
    let consultando = false;
    const consultar = async () => {
      if (consultando || document.visibilityState !== "visible") return;
      consultando = true;
      try {
        for (const borrador of leerEntregasEnEspera(usuarioId)) {
          if (control.signal.aborted) return;
          if (borrador.autorizacion?.estado !== "PENDIENTE") continue;
          try {
            const respuesta = await apiGet<AutorizacionApi>(`/autorizaciones/${borrador.autorizacion.id}`, undefined, control.signal);
            if (control.signal.aborted || respuesta.estado === "PENDIENTE") continue;
            // Volver a leer evita reinsertar un borrador que ya se abrió o descartó.
            const actuales = leerEntregasEnEspera(usuarioId);
            if (!actuales.some((b) => b.idCliente === borrador.idCliente)) continue;
            guardarEntregasEnEspera(actuales.map((b) => b.idCliente === borrador.idCliente ? { ...b, autorizacion: { ...b.autorizacion!, estado: respuesta.estado, vence_en: respuesta.vence_en, resuelta_por: respuesta.resuelta_por?.nombre, renglones_resueltos: respuesta.renglones_resueltos } } : b));
            reproducir(respuesta.estado === "APROBADA" ? "ok" : "aviso");
            if (respuesta.estado === "APROBADA") navigator.vibrate?.(100);
            aviso({ titulo: respuesta.estado === "APROBADA" ? "Una entrega en espera fue aprobada" : "Una entrega en espera recibió respuesta", descripcion: borrador.trabajador?.nombre, tipo: "info" });
          } catch { /* Una falla de red conserva el borrador; se vuelve a consultar. */ }
        }
      } finally { consultando = false; }
    };
    void consultar();
    const timer = window.setInterval(() => void consultar(), 3000);
    const volver = () => void consultar();
    document.addEventListener("visibilitychange", volver);
    return () => { control.abort(); clearInterval(timer); document.removeEventListener("visibilitychange", volver); };
  }, [usuarioId]);
  return { borradores, recargar };
}
