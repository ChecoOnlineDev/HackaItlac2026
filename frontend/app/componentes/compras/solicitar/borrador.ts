import { useCallback, useEffect, useState } from "react";

import { practicaActiva } from "~/api/practica";
import { nuevoId } from "~/componentes/entradas/tipos";
import type { ArticuloElegido, Urgencia } from "./tipos";

/**
 * Lo que se va capturando al pedir una compra. Se guarda en este dispositivo para que una recarga o un corte
 * de red no pierdan lo escrito, y lleva el `id_cliente` de la solicitud (SC-10): un doble toque o un reintento
 * con el mismo identificador nunca crea dos solicitudes. El nombre empieza con `imhotep.borrador.` para que se
 * borre al cerrar la sesión.
 */
export interface BorradorCompra {
  version: 1;
  /** Un borrador es de un usuario; otro usuario nunca lo ve. */
  usuarioId: string;
  idCliente: string;
  /** `true` si el equipo no está en el catálogo y se describe con texto libre. */
  sinCatalogo: boolean;
  articulo: ArticuloElegido | null;
  descripcion: string;
  cantidad: number;
  motivo: string;
  /** Marca "Otro" en las respuestas rápidas aunque todavía no haya texto. */
  motivoOtro: boolean;
  urgencia: Urgencia;
  /** Solo quien opera todos los almacenes lo elige. */
  almacenId: string;
}

const CLAVE = "imhotep.borrador.compra.v1";

export function nuevoBorradorCompra(usuarioId: string, almacenId = ""): BorradorCompra {
  return {
    version: 1,
    usuarioId,
    idCliente: nuevoId(),
    sinCatalogo: false,
    articulo: null,
    descripcion: "",
    cantidad: 1,
    motivo: "",
    motivoOtro: false,
    urgencia: "URGENTE",
    almacenId,
  };
}

function leer(usuarioId: string): BorradorCompra | null {
  if (practicaActiva()) return null; // TU-07
  try {
    const texto = window.localStorage.getItem(CLAVE);
    if (!texto) return null;
    const dato = JSON.parse(texto) as Partial<BorradorCompra> | null;
    if (!dato || dato.version !== 1 || dato.usuarioId !== usuarioId) return null;
    if (typeof dato.idCliente !== "string" || typeof dato.cantidad !== "number") return null;
    return { ...nuevoBorradorCompra(usuarioId), ...dato } as BorradorCompra;
  } catch {
    return null;
  }
}

function guardar(borrador: BorradorCompra) {
  if (practicaActiva()) return; // TU-07
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(borrador));
  } catch {
    // Sin almacenamiento (ventana privada o bloqueado): la pantalla sigue funcionando sin guardar.
  }
}

export function borrarBorradorCompra() {
  if (practicaActiva()) return; // TU-07
  try {
    window.localStorage.removeItem(CLAVE);
  } catch {
    // Nada que borrar.
  }
}

/** Borrador de la solicitud: sobrevive a una recarga; `reiniciar` empieza otra con un identificador nuevo. */
export function useBorradorCompra(usuarioId: string) {
  const [borrador, setBorrador] = useState<BorradorCompra>(() => nuevoBorradorCompra(usuarioId));
  const [cargado, setCargado] = useState(false);
  const [recuperado, setRecuperado] = useState(false);

  // Se lee después del primer pintado para que coincida con lo que genera el servidor de la interfaz.
  useEffect(() => {
    const guardado = leer(usuarioId);
    if (guardado) {
      setBorrador(guardado);
      setRecuperado(Boolean(guardado.articulo || guardado.descripcion || guardado.motivo));
    }
    setCargado(true);
  }, [usuarioId]);

  useEffect(() => {
    if (cargado) guardar(borrador);
  }, [borrador, cargado]);

  const cambiar = useCallback((parcial: Partial<BorradorCompra>) => setBorrador((b) => ({ ...b, ...parcial })), []);

  /** Termina una solicitud enviada: se borra lo guardado y la siguiente lleva otro identificador. */
  const reiniciar = useCallback(() => {
    borrarBorradorCompra();
    setBorrador((b) => nuevoBorradorCompra(usuarioId, b.almacenId));
    setRecuperado(false);
  }, [usuarioId]);

  /** Cambia solo el identificador (cuando el servidor dice que ya lo usó otra solicitud con otros datos). */
  const renovarId = useCallback(() => setBorrador((b) => ({ ...b, idCliente: nuevoId() })), []);

  return { borrador, cargado, recuperado, descartarAviso: () => setRecuperado(false), cambiar, reiniciar, renovarId };
}
