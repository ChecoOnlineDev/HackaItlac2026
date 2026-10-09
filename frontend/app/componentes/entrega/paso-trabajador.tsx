import { EscanerBusqueda } from "~/componentes/dominio/escaner-busqueda";
import { SearchXIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiGet } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import type { OrigenLectura } from "~/componentes/dominio/escaner";
import { FichaTrabajador } from "~/componentes/dominio/ficha-trabajador";
import { reproducir } from "~/componentes/dominio/sonido";
import { Cargando } from "~/componentes/ui/cargando";
import { HojaDotacion } from "./hoja-dotacion";
import { resumenDeDotacion, type FichaTrabajadorApi } from "./tipos";
import { useDotacion } from "./use-dotacion";

interface EscaneoApi {
  tipo: "TRABAJADOR" | "ARTICULO" | "PIEZA" | "VALE" | "DESCONOCIDO";
  id: string | null;
}

interface CandidatoApi {
  id: string;
  numero_empleado: string;
  nombre: string;
  estado_texto: string;
}

interface BusquedaApi {
  trabajadores: { elementos: CandidatoApi[]; total: number };
}

interface PropiedadesPasoTrabajador {
  /** Trabajador ya identificado, o null. */
  trabajador: FichaTrabajadorApi | null;
  alIdentificar: (ficha: FichaTrabajadorApi) => void;
  /** Apaga el escáner (por ejemplo mientras no se ha elegido almacén). */
  activo?: boolean;
  /** `data-tutorial` del escáner y de la ficha (FEAT-010). */
  anclas?: { escaner: string; ficha: string };
}

/**
 * Paso 1 de la entrega: identificar al trabajador con la credencial (cámara o pistola), su número de
 * empleado o su nombre. Al identificarlo aparece su ficha; si no es vigente, toda en rojo (E-02).
 */
export function PasoTrabajador({ trabajador, alIdentificar, activo = true, anclas }: PropiedadesPasoTrabajador) {
  const [buscando, setBuscando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [candidatos, setCandidatos] = useState<CandidatoApi[] | null>(null);
  const [textoBuscado, setTextoBuscado] = useState("");
  const [viendoDotacion, setViendoDotacion] = useState(false);
  const dotacion = useDotacion(trabajador?.id ?? null);
  const secuencia = useRef(0);
  const vivo = useRef(true);
  useEffect(() => {
    vivo.current = true;
    return () => {
      vivo.current = false;
    };
  }, []);

  const cargarFicha = useCallback(
    async (id: string) => {
      const ficha = await apiGet<FichaTrabajadorApi>(`/trabajadores/${id}`);
      if (!vivo.current) return;
      setCandidatos(null);
      setMensaje(null);
      if (!ficha.vigencia.vigente) reproducir("bloqueo");
      alIdentificar(ficha);
    },
    [alIdentificar],
  );

  const alCodigo = useCallback(
    async (codigo: string, origen: OrigenLectura) => {
      const mia = ++secuencia.current;
      setBuscando(true);
      setMensaje(null);
      setCandidatos(null);
      try {
        const escaneo = await apiGet<EscaneoApi>(`/escaneo/${encodeURIComponent(codigo)}`);
        if (mia !== secuencia.current) return;
        if (escaneo.tipo === "TRABAJADOR" && escaneo.id) {
          await cargarFicha(escaneo.id);
          return;
        }
        if (escaneo.tipo !== "DESCONOCIDO") {
          reproducir("aviso");
          setMensaje("Ese código no es de un trabajador. Escanea su credencial o escribe su número.");
          return;
        }
        if (origen === "teclado" && codigo.length >= 2) {
          const busqueda = await apiGet<BusquedaApi>("/busqueda", { q: codigo });
          if (mia !== secuencia.current) return;
          const lista = busqueda.trabajadores.elementos;
          if (lista.length > 0) {
            setTextoBuscado(codigo);
            setCandidatos(lista);
            return;
          }
        }
        reproducir("aviso");
        setMensaje(`No encontramos a ningún trabajador con “${codigo}”. Revisa el número o vuelve a escanear.`);
      } catch (causa) {
        if (mia !== secuencia.current) return;
        reproducir("aviso");
        setMensaje(esErrorApi(causa) && causa.sinConexion ? "Sin conexión. Inténtalo otra vez en cuanto vuelva." : mensajeDeError(causa));
      } finally {
        if (mia === secuencia.current && vivo.current) setBuscando(false);
      }
    },
    [cargarFicha],
  );

  const elegir = async (candidato: CandidatoApi) => {
    const mia = ++secuencia.current;
    setBuscando(true);
    setMensaje(null);
    try {
      await cargarFicha(candidato.id);
    } catch (causa) {
      if (mia === secuencia.current) setMensaje(mensajeDeError(causa));
    } finally {
      if (mia === secuencia.current && vivo.current) setBuscando(false);
    }
  };

  // La acción "No es esta persona" vive en el pie fijo de la pantalla, junto a "Continuar": nunca queda fuera de alcance.
  if (trabajador) {
    return (
      <div className="flex flex-col gap-3">
        <h2>Confirma que es la persona correcta</h2>
        <FichaTrabajador
          trabajador={trabajador}
          ancla={anclas?.ficha}
          variante="completa"
          dotacion={resumenDeDotacion(dotacion)}
          alVerDotacion={() => setViendoDotacion(true)}
        />
        {dotacion ? <HojaDotacion abierta={viendoDotacion} alCambiar={setViendoDotacion} dotacion={dotacion} modo="consulta" /> : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg">Escanea la credencial del trabajador</h2>
        <p className="text-sm text-muted-foreground">Si no la tiene a la mano, escribe su número o su nombre.</p>
      </div>
      <EscanerBusqueda
        grupo="trabajadores"
        ancla={anclas?.escaner}
        activo={activo && !buscando}
        onCodigo={(codigo, origen) => void alCodigo(codigo, origen)}
        etiquetaCampo="Escribir número o nombre"
        placeholderCampo="EMP-1001 o Juan"
      />
      {buscando ? <Cargando variante="en-linea" texto="Buscando al trabajador…" /> : null}
      {mensaje ? (
        <p role="alert" className="flex items-start gap-2 rounded-xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm font-medium">
          <SearchXIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-amarillo" />
          {mensaje}
        </p>
      ) : null}
      {candidatos ? (
        <section aria-label="Trabajadores encontrados" className="flex flex-col gap-2">
          <h2 className="text-base">¿Cuál es? Resultados para “{textoBuscado}”</h2>
          <ul className="flex flex-col gap-2">
            {candidatos.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => void elegir(c)}
                  className="flex min-h-12 w-full flex-col items-start rounded-2xl border bg-card px-4 py-2 text-left shadow-xs hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="text-base font-semibold">{c.nombre}</span>
                  <span className="text-sm text-muted-foreground">
                    N.º {c.numero_empleado} · {c.estado_texto}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
