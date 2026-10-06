import { useEffect, useMemo, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { useSesion } from "~/sesion/sesion";

export interface OpcionLista {
  valor: string;
  texto: string;
  /** Clave corta, por ejemplo `KEP` (solo en almacenes). */
  clave?: string;
}

/**
 * Almacenes para el filtro. Solo se piden si quien mira puede ver todos los almacenes
 * (`almacenes.todos`) y consultar existencias (`inventario.ver`); los demás solo ven el suyo.
 */
export function useAlmacenesFiltro() {
  const { puede } = useSesion();
  const permitido = puede("almacenes.todos") && puede("inventario.ver");
  const consulta = useConsulta(
    (signal) =>
      permitido
        ? apiGet<{ id: string; clave: string; nombre: string; estado: string }[]>("/almacenes", undefined, signal)
        : Promise.resolve([]),
    `almacenes|${permitido}`,
  );
  const opciones = useMemo<OpcionLista[]>(
    () => (consulta.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre === a.clave ? a.nombre : `${a.nombre} (${a.clave})`, clave: a.clave })),
    [consulta.datos],
  );
  // Si falla la lista no estorba: el reporte sigue funcionando con el almacén del usuario o todos.
  return { opciones, disponible: permitido && !consulta.error && opciones.length > 0 };
}

/** Categorías para el filtro (`catalogo.ver`). */
export function useCategoriasFiltro() {
  const { puede } = useSesion();
  const permitido = puede("catalogo.ver");
  const consulta = useConsulta(
    (signal) =>
      permitido
        ? apiGet<Pagina<{ id: string; nombre: string }>>("/categorias", { tamano: 200 }, signal)
        : Promise.resolve({ elementos: [], total: 0 }),
    `categorias|${permitido}`,
  );
  const opciones = useMemo<OpcionLista[]>(
    () => (consulta.datos?.elementos ?? []).map((c) => ({ valor: c.id, texto: c.nombre })),
    [consulta.datos],
  );
  return { opciones, disponible: permitido && !consulta.error && opciones.length > 0 };
}

/**
 * Usuarios para el filtro "Quién lo hizo": quienes han hecho vales (`GET /api/reportes/usuarios`).
 * Con `almacenes.todos` vienen de todos los almacenes; si no, solo los del almacén de quien mira.
 */
export function useUsuariosFiltro() {
  const { sesion } = useSesion();
  const consulta = useConsulta(
    (signal) => apiGet<{ elementos: { id: string; nombre: string }[] }>("/reportes/usuarios", undefined, signal),
    "usuarios-vales",
  );
  const opciones = useMemo<OpcionLista[]>(
    () =>
      (consulta.datos?.elementos ?? [])
        .map((u) => ({ valor: u.id, texto: u.id === sesion?.usuario.id ? `${u.nombre} (tú)` : u.nombre }))
        .sort((a, b) => a.texto.localeCompare(b.texto, "es")),
    [consulta.datos, sesion],
  );
  return { opciones, soloYo: false };
}

// ---------------------------------------------------------------------------------------------
// Nombre de un trabajador o artículo elegido en el filtro. Al elegirlo ya se conoce; si la
// dirección se abre en otro lado, se vuelve a pedir.

type TipoEtiqueta = "trabajador" | "articulo";
const cache = new Map<string, string>();

export function recordarEtiqueta(tipo: TipoEtiqueta, id: string, texto: string) {
  cache.set(`${tipo}:${id}`, texto);
}

export function useEtiqueta(tipo: TipoEtiqueta, id: string): string | null {
  const [, forzar] = useState(0);
  const clave = `${tipo}:${id}`;
  const conocida = id ? (cache.get(clave) ?? null) : null;

  useEffect(() => {
    if (!id || cache.has(clave)) return;
    const control = new AbortController();
    const ruta = tipo === "trabajador" ? `/trabajadores/${id}` : `/articulos/${id}`;
    apiGet<{ nombre: string; numero_empleado?: string }>(ruta, undefined, control.signal)
      .then((r) => {
        cache.set(clave, r.numero_empleado ? `${r.nombre} (${r.numero_empleado})` : r.nombre);
        forzar((n) => n + 1);
      })
      .catch(() => {
        // Sin permiso o sin conexión: el chip dice solo "elegido".
      });
    return () => control.abort();
  }, [id, clave, tipo]);

  return conocida;
}
