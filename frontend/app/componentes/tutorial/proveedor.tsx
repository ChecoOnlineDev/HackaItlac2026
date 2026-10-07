import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { activarPractica, desactivarPractica } from "~/api/practica";
import type { Permiso } from "~/api/tipos";
import { useSesion } from "~/sesion/sesion";
import { guardarTerminado, leerTerminados } from "./progreso";
import { recorridos } from "./recorridos";
import type { Paso, Recorrido } from "./tipos";

interface ValorTutorial {
  /** Interruptor encendido: hay banda de práctica y no se llama al servidor. */
  activo: boolean;
  recorrido: Recorrido | null;
  paso: Paso | null;
  /** Posición del paso actual (desde 0). */
  indicePaso: number;
  /** Recorridos que la sesión permite (por permiso, nunca por rol). */
  recorridosDisponibles: Recorrido[];
  /** Ids de recorridos terminados por esta persona en este dispositivo. */
  terminados: string[];
  encender: () => void;
  apagar: () => void;
  iniciar: (recorridoId: string) => void;
  siguiente: () => void;
  salir: () => void;
}

const Contexto = createContext<ValorTutorial | null>(null);

export function ProveedorTutorial({ children }: { children: ReactNode }) {
  const { sesion, puede } = useSesion();
  const navigate = useNavigate();
  const persona = sesion?.usuario.id ?? "";

  const [activo, setActivo] = useState(false);
  const [recorridoId, setRecorridoId] = useState<string | null>(null);
  const [indicePaso, setIndicePaso] = useState(0);
  const [terminados, setTerminados] = useState<string[]>([]);

  useEffect(() => {
    setTerminados(persona ? leerTerminados(persona) : []);
  }, [persona]);

  const recorridosDisponibles = useMemo(
    () => recorridos.filter((r) => !r.permiso || puede(r.permiso as Permiso)),
    [puede],
  );
  const recorrido = useMemo(
    () => recorridosDisponibles.find((r) => r.id === recorridoId) ?? null,
    [recorridosDisponibles, recorridoId],
  );
  const paso = recorrido?.pasos[indicePaso] ?? null;

  const apagarSinNavegar = useCallback(() => {
    setRecorridoId(null);
    setIndicePaso(0);
    setActivo(false);
    desactivarPractica();
  }, []);

  const encender = useCallback(() => {
    activarPractica();
    setActivo(true);
  }, []);

  const apagar = useCallback(() => {
    const habiaRecorrido = recorridoId !== null;
    apagarSinNavegar();
    if (habiaRecorrido) navigate("/");
  }, [apagarSinNavegar, navigate, recorridoId]);

  const iniciar = useCallback((id: string) => {
    activarPractica();
    setActivo(true);
    setRecorridoId(id);
    setIndicePaso(0);
  }, []);

  const siguiente = useCallback(() => {
    if (!recorrido) return;
    if (indicePaso + 1 < recorrido.pasos.length) {
      setIndicePaso(indicePaso + 1);
      return;
    }
    if (persona) setTerminados(guardarTerminado(persona, recorrido.id));
    apagarSinNavegar();
    navigate("/");
  }, [apagarSinNavegar, indicePaso, navigate, persona, recorrido]);

  // Si la sesión cambia y el recorrido deja de estar permitido, se sale.
  useEffect(() => {
    if (recorridoId && !recorrido) apagarSinNavegar();
  }, [recorrido, recorridoId, apagarSinNavegar]);

  // Si el paso trae pantalla propia, se navega a ella antes de buscar el ancla.
  const ruta = paso?.ruta;
  useEffect(() => {
    if (ruta && window.location.pathname !== ruta) navigate(ruta);
  }, [ruta, navigate, recorridoId, indicePaso]);

  // Al cerrar sesión o desmontar, la práctica nunca se queda encendida.
  const apagarRef = useRef(apagarSinNavegar);
  apagarRef.current = apagarSinNavegar;
  useEffect(() => {
    if (!persona) return;
    return () => apagarRef.current();
  }, [persona]);

  const valor = useMemo<ValorTutorial>(
    () => ({
      activo,
      recorrido,
      paso,
      indicePaso,
      recorridosDisponibles,
      terminados,
      encender,
      apagar,
      iniciar,
      siguiente,
      salir: apagar,
    }),
    [activo, recorrido, paso, indicePaso, recorridosDisponibles, terminados, encender, apagar, iniciar, siguiente],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useTutorial(): ValorTutorial {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useTutorial debe usarse dentro de ProveedorTutorial");
  return valor;
}
