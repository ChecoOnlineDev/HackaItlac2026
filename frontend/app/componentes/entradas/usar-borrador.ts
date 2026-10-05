import { useCallback, useEffect, useState } from "react";

import {
  nuevoBorrador,
  nuevoId,
  type ArticuloFichaEntrada,
  type Borrador,
  type PiezaBorrador,
  type RenglonBorrador,
} from "./tipos";

const PREFIJO = "imhotep.entrada.";

function leer(usuarioId: string): Borrador | null {
  try {
    const texto = window.localStorage.getItem(PREFIJO + usuarioId);
    if (!texto) return null;
    const dato = JSON.parse(texto) as Borrador;
    if (typeof dato?.id_cliente !== "string" || !Array.isArray(dato.renglones)) return null;
    return { id_cliente: dato.id_cliente, almacen_id: dato.almacen_id ?? "", renglones: dato.renglones };
  } catch {
    return null;
  }
}

function guardar(usuarioId: string, borrador: Borrador | null) {
  try {
    if (borrador && borrador.renglones.length > 0) window.localStorage.setItem(PREFIJO + usuarioId, JSON.stringify(borrador));
    else window.localStorage.removeItem(PREFIJO + usuarioId);
  } catch {
    // Sin almacenamiento (ventana privada o bloqueado): la pantalla sigue funcionando sin guardar.
  }
}

function renglonDe(ficha: ArticuloFichaEntrada, pieza?: PiezaBorrador): RenglonBorrador {
  return {
    clave: nuevoId(),
    articulo_id: ficha.id,
    codigo: ficha.codigo,
    nombre: ficha.nombre,
    marca: ficha.marca,
    control: ficha.control,
    requiere_inspeccion: ficha.requiere_inspeccion,
    unidad: ficha.unidad,
    cantidad: 1,
    pieza,
  };
}

/**
 * Borrador de la entrada, guardado en este dispositivo: sobrevive a una recarga y a un corte de red.
 * El `id_cliente` es único por entrada; solo se renueva al empezar otra.
 */
export function useBorradorEntrada(usuarioId: string) {
  const [borrador, setBorrador] = useState<Borrador>(() => nuevoBorrador());
  const [recuperado, setRecuperado] = useState(false);
  const [cargado, setCargado] = useState(false);

  // Se lee después del primer pintado para que coincida con lo que genera el servidor de la interfaz.
  useEffect(() => {
    const guardado = leer(usuarioId);
    if (guardado) {
      setBorrador(guardado);
      setRecuperado(guardado.renglones.length > 0);
    }
    setCargado(true);
  }, [usuarioId]);

  useEffect(() => {
    if (cargado) guardar(usuarioId, borrador);
  }, [usuarioId, borrador, cargado]);

  const cambiarAlmacen = useCallback((almacen_id: string) => setBorrador((b) => ({ ...b, almacen_id })), []);

  /** Un artículo por cantidad: suma 1 si ya está. Devuelve la clave del renglón. */
  const agregarCantidad = useCallback((ficha: ArticuloFichaEntrada): string => {
    let clave = "";
    setBorrador((b) => {
      const existente = b.renglones.find((r) => r.articulo_id === ficha.id && !r.pieza);
      if (existente) {
        clave = existente.clave;
        return {
          ...b,
          renglones: b.renglones.map((r) => (r.clave === existente.clave ? { ...r, cantidad: r.cantidad + 1 } : r)),
        };
      }
      const nuevo = renglonDe(ficha);
      clave = nuevo.clave;
      return { ...b, renglones: [...b.renglones, nuevo] };
    });
    return clave;
  }, []);

  const agregarPieza = useCallback((ficha: ArticuloFichaEntrada, pieza: PiezaBorrador): string => {
    const nuevo = renglonDe(ficha, pieza);
    setBorrador((b) => ({ ...b, renglones: [...b.renglones, nuevo] }));
    return nuevo.clave;
  }, []);

  const cambiarCantidad = useCallback((clave: string, cantidad: number) => {
    setBorrador((b) => ({ ...b, renglones: b.renglones.map((r) => (r.clave === clave ? { ...r, cantidad } : r)) }));
  }, []);

  const corregirPieza = useCallback((clave: string, pieza: PiezaBorrador) => {
    setBorrador((b) => ({ ...b, renglones: b.renglones.map((r) => (r.clave === clave ? { ...r, pieza } : r)) }));
  }, []);

  /** Deshace un "+1" de un artículo por cantidad: resta uno o quita el renglón si era el único. */
  const quitarUnoDe = useCallback((articuloId: string) => {
    setBorrador((b) => ({
      ...b,
      renglones: b.renglones.flatMap((r) => {
        if (r.articulo_id !== articuloId || r.pieza) return [r];
        return r.cantidad > 1 ? [{ ...r, cantidad: r.cantidad - 1 }] : [];
      }),
    }));
  }, []);

  const quitar = useCallback((clave: string) => {
    setBorrador((b) => ({ ...b, renglones: b.renglones.filter((r) => r.clave !== clave) }));
  }, []);

  /** Empieza otra entrada: borra los renglones y renueva el identificador. */
  const reiniciar = useCallback(() => {
    setBorrador((b) => nuevoBorrador(b.almacen_id));
    setRecuperado(false);
  }, []);

  return {
    borrador,
    recuperado,
    descartarAviso: () => setRecuperado(false),
    cambiarAlmacen,
    agregarCantidad,
    agregarPieza,
    cambiarCantidad,
    corregirPieza,
    quitar,
    quitarUnoDe,
    reiniciar,
  };
}
