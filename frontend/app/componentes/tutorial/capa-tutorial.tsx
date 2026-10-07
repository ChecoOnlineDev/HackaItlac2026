import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type SyntheticEvent } from "react";
import { createPortal } from "react-dom";

import { Boton } from "~/componentes/ui/boton";
import { useTutorial } from "./proveedor";

interface Caja {
  top: number;
  left: number;
  width: number;
  height: number;
}

const HOLGURA = 6; // aire entre el elemento y el círculo
const FLECHA = 36; // alto reservado para la flecha
const MARGEN = 12;
const ESPERA_ANCLA_MS = 2500;

const FOCALIZABLES =
  'a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

function buscarAncla(ancla: string): HTMLElement | null {
  const candidatos = document.querySelectorAll<HTMLElement>(`[data-tutorial="${CSS.escape(ancla)}"]`);
  for (const el of candidatos) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) return el;
  }
  return null;
}

function aCaja(r: DOMRect): Caja {
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

function igual(a: Caja | null, b: Caja | null) {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height;
}

/** Evita que un clic en la capa cierre diálogos u hojas que escuchan fuera de ellos. */
const noSubir = (e: SyntheticEvent) => e.stopPropagation();

/**
 * Banda de práctica y capa de guía (velo, círculo, flecha y globo) en un portal propio por encima de todo.
 * Va montada una sola vez, en el layout de la aplicación.
 */
export function CapaTutorial() {
  const { activo, paso, recorrido, indicePaso, siguiente, salir } = useTutorial();
  const [raiz, setRaiz] = useState<HTMLElement | null>(null);

  // El portal vive en <body>; si una hoja modal marca el resto como inerte, se le quita.
  useEffect(() => {
    if (!activo) {
      setRaiz(null);
      return;
    }
    const el = document.createElement("div");
    el.dataset.tutorialRaiz = "";
    document.body.appendChild(el);
    const limpiar = () => {
      el.removeAttribute("inert");
      el.removeAttribute("aria-hidden");
    };
    const observador = new MutationObserver(limpiar);
    observador.observe(el, { attributes: true, attributeFilter: ["inert", "aria-hidden"] });
    setRaiz(el);
    return () => {
      observador.disconnect();
      el.remove();
    };
  }, [activo]);

  if (!activo || !raiz) return null;

  return createPortal(
    <>
      <div
        role="status"
        className="pointer-events-none fixed inset-x-0 top-0 z-[70] flex h-6 items-center justify-center bg-marino px-3 text-xs font-semibold text-white"
      >
        Práctica: nada de esto se guarda
      </div>
      {paso && recorrido ? (
        <Guia
          key={`${recorrido.id}-${indicePaso}`}
          ancla={paso.ancla}
          texto={paso.texto}
          modo={paso.modo}
          accion={paso.accionSimulada}
          listo={paso.listo}
          numero={indicePaso + 1}
          total={recorrido.pasos.length}
          alAvanzar={siguiente}
          alSalir={salir}
        />
      ) : null}
    </>,
    raiz,
  );
}

interface PropiedadesGuia {
  ancla: string;
  texto: string;
  modo: "tocar" | "leer";
  accion?: { etiqueta: string; ejecutar: () => void };
  listo?: () => boolean;
  numero: number;
  total: number;
  alAvanzar: () => void;
  alSalir: () => void;
}

function Guia({ ancla, texto, modo, accion, listo, numero, total, alAvanzar, alSalir }: PropiedadesGuia) {
  const [caja, setCaja] = useState<Caja | null>(null);
  const [alto, setAlto] = useState(160);
  const [, setVentana] = useState(0);
  const globo = useRef<HTMLDivElement | null>(null);
  const elemento = useRef<HTMLElement | null>(null);
  const ausenteDesde = useRef<number | null>(null);
  const ultima = useRef({ modo, listo, alAvanzar, alSalir });
  ultima.current = { modo, listo, alAvanzar, alSalir };

  const medir = useCallback(() => {
    let el = elemento.current;
    if (!el || !el.isConnected) {
      el = buscarAncla(ancla);
      elemento.current = el;
      if (el) {
        ausenteDesde.current = null;
        el.scrollIntoView({ block: "center", inline: "nearest" });
      }
    }
    if (!el) {
      ausenteDesde.current ??= Date.now();
      setCaja(null);
      if (Date.now() - ausenteDesde.current > ESPERA_ANCLA_MS) {
        console.warn(`[tutorial] No se encontró el elemento «${ancla}»; se omite el paso.`);
        ausenteDesde.current = Date.now();
        ultima.current.alAvanzar();
      }
      return;
    }
    const nueva = aCaja(el.getBoundingClientRect());
    setCaja((actual) => (igual(actual, nueva) ? actual : nueva));
  }, [ancla]);

  // Sigue al elemento: scroll, tamaño, giro de pantalla, cambios del propio elemento y de la página.
  useEffect(() => {
    medir();
    const alCambiar = () => {
      medir();
      setVentana((n) => n + 1);
    };
    window.addEventListener("scroll", alCambiar, true);
    window.addEventListener("resize", alCambiar);
    window.addEventListener("orientationchange", alCambiar);
    const observador = new ResizeObserver(alCambiar);
    observador.observe(document.documentElement);
    let observado: Element | null = null;
    // Respaldo para cambios de posición que ningún evento avisa (carga de datos, animaciones).
    const intervalo = window.setInterval(() => {
      if (elemento.current && elemento.current !== observado) {
        if (observado) observador.unobserve(observado);
        observado = elemento.current;
        observador.observe(observado);
      }
      medir();
    }, 120);
    return () => {
      window.removeEventListener("scroll", alCambiar, true);
      window.removeEventListener("resize", alCambiar);
      window.removeEventListener("orientationchange", alCambiar);
      observador.disconnect();
      window.clearInterval(intervalo);
    };
  }, [medir]);

  useLayoutEffect(() => {
    if (globo.current && globo.current.offsetHeight !== alto) setAlto(globo.current.offsetHeight);
  });

  // Foco dentro de la capa al empezar cada paso.
  useEffect(() => {
    globo.current?.focus({ preventScroll: true });
  }, []);

  // Bloqueo de teclado, de foco y del avance con un clic en el elemento.
  useEffect(() => {
    const dentroDeGuia = (n: EventTarget | null) =>
      n instanceof Node && (!!globo.current?.contains(n) || !!elemento.current?.contains(n));

    const alTecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "keydown") ultima.current.alSalir();
        return;
      }
      if (e.key === "Tab") {
        if (e.type !== "keydown") return;
        const lista = [
          ...(elemento.current?.matches(FOCALIZABLES) ? [elemento.current] : []),
          ...Array.from(elemento.current?.querySelectorAll<HTMLElement>(FOCALIZABLES) ?? []),
          ...Array.from(globo.current?.querySelectorAll<HTMLElement>(FOCALIZABLES) ?? []),
        ];
        e.preventDefault();
        e.stopPropagation();
        if (lista.length === 0) {
          globo.current?.focus();
          return;
        }
        const i = lista.indexOf(document.activeElement as HTMLElement);
        const destino = e.shiftKey ? lista[(i <= 0 ? lista.length : i) - 1] : lista[(i + 1) % lista.length];
        destino.focus();
        return;
      }
      if (!dentroDeGuia(e.target)) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    const alFoco = (e: FocusEvent) => {
      if (!dentroDeGuia(e.target)) globo.current?.focus({ preventScroll: true });
    };

    const esperas: number[] = [];
    let esperando = false;
    const alClic = (e: MouseEvent | PointerEvent) => {
      const el = elemento.current;
      if (e.type === "pointerup" && !ultima.current.listo) return;
      if (ultima.current.modo !== "tocar" || !el || !(e.target instanceof Node) || !el.contains(e.target)) return;
      // Deja que el elemento haga lo suyo y después avanza (si el paso pide una condición, la espera un momento).
      if (!ultima.current.listo) {
        window.setTimeout(() => ultima.current.alAvanzar(), 0);
        return;
      }
      if (esperando) return;
      esperando = true;
      let intentos = 0;
      const espera = window.setInterval(() => {
        intentos += 1;
        if (ultima.current.listo?.()) {
          window.clearInterval(espera);
          ultima.current.alAvanzar();
        } else if (intentos >= 12) {
          window.clearInterval(espera);
          esperando = false;
        }
      }, 50);
      esperas.push(espera);
    };

    document.addEventListener("keydown", alTecla, true);
    document.addEventListener("keyup", alTecla, true);
    document.addEventListener("focusin", alFoco);
    document.addEventListener("click", alClic, true);
    // Un trazo con el dedo no genera «clic»: en los pasos con condición también se revisa al soltar.
    document.addEventListener("pointerup", alClic, true);
    return () => {
      document.removeEventListener("keydown", alTecla, true);
      document.removeEventListener("keyup", alTecla, true);
      document.removeEventListener("focusin", alFoco);
      document.removeEventListener("click", alClic, true);
      document.removeEventListener("pointerup", alClic, true);
      esperas.forEach((n) => window.clearInterval(n));
    };
  }, []);

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const ancho = Math.min(340, vw - 2 * MARGEN);

  // Colocación del globo: debajo del elemento si cabe, si no arriba, y si no, al pie de la pantalla.
  let top = vh - alto - MARGEN;
  let flecha: "arriba" | "abajo" | null = null;
  let flechaTop = 0;
  let left = (vw - ancho) / 2;
  if (caja) {
    const centro = caja.left + caja.width / 2;
    left = Math.min(Math.max(centro - ancho / 2, MARGEN), vw - ancho - MARGEN);
    if (caja.top + caja.height + HOLGURA + FLECHA + alto + MARGEN <= vh) {
      top = caja.top + caja.height + HOLGURA + FLECHA;
      flecha = "arriba";
      flechaTop = caja.top + caja.height + HOLGURA + 2;
    } else if (caja.top - HOLGURA - FLECHA - alto - MARGEN >= 0) {
      top = caja.top - HOLGURA - FLECHA - alto;
      flecha = "abajo";
      flechaTop = caja.top - HOLGURA - FLECHA + 2;
    } else if (caja.left + caja.width + HOLGURA + MARGEN + ancho + MARGEN <= vw) {
      // Elemento muy alto: el globo va a su derecha (sin flecha) para no taparlo.
      left = caja.left + caja.width + HOLGURA + MARGEN;
      top = Math.min(Math.max(caja.top + caja.height / 2 - alto / 2, MARGEN), vh - alto - MARGEN);
    } else if (caja.left - HOLGURA - MARGEN - ancho - MARGEN >= 0) {
      left = caja.left - HOLGURA - MARGEN - ancho;
      top = Math.min(Math.max(caja.top + caja.height / 2 - alto / 2, MARGEN), vh - alto - MARGEN);
    }
  }
  const flechaLeft = caja ? Math.min(Math.max(caja.left + caja.width / 2 - 16, MARGEN), vw - 32 - MARGEN) : 0;

  const bloque = "pointer-events-auto fixed bg-transparent";
  const redondeo =
    caja && Math.max(caja.width, caja.height) / Math.max(Math.min(caja.width, caja.height), 1) < 1.8 ? 9999 : 20;

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[70]"
      onPointerDown={noSubir}
      onMouseDown={noSubir}
      onClick={noSubir}
      onTouchStart={noSubir}
    >
      {caja ? (
        <>
          {/* Cuatro bloques alrededor del hueco: el toque solo llega al elemento del paso. */}
          <div className={bloque} style={{ top: 0, left: 0, right: 0, height: Math.max(caja.top, 0) }} />
          <div className={bloque} style={{ top: caja.top + caja.height, left: 0, right: 0, bottom: 0 }} />
          <div className={bloque} style={{ top: caja.top, left: 0, width: Math.max(caja.left, 0), height: caja.height }} />
          <div className={bloque} style={{ top: caja.top, left: caja.left + caja.width, right: 0, height: caja.height }} />
          {modo === "leer" ? (
            <div className={bloque} style={{ top: caja.top, left: caja.left, width: caja.width, height: caja.height }} />
          ) : null}
          {/* Velo con hueco y círculo de contorno azul marino. */}
          <div
            aria-hidden="true"
            className="pointer-events-none fixed border-[3px] border-marino motion-safe:transition-all motion-safe:duration-150"
            style={{
              top: caja.top - HOLGURA,
              left: caja.left - HOLGURA,
              width: caja.width + 2 * HOLGURA,
              height: caja.height + 2 * HOLGURA,
              borderRadius: redondeo,
              boxShadow: "0 0 0 3px #fff, 0 0 0 100vmax rgba(0,0,0,0.6)",
            }}
          />
          {flecha ? (
            <div
              aria-hidden="true"
              className="pointer-events-none fixed text-white motion-safe:transition-all motion-safe:duration-150"
              style={{ top: flechaTop, left: flechaLeft }}
            >
              {flecha === "arriba" ? (
                <ArrowUpIcon className="size-8" strokeWidth={3} />
              ) : (
                <ArrowDownIcon className="size-8" strokeWidth={3} />
              )}
            </div>
          ) : null}
        </>
      ) : (
        <div className="pointer-events-auto fixed inset-0 bg-black/60" />
      )}
      <div
        ref={globo}
        tabIndex={-1}
        role="dialog"
        aria-label="Guía de práctica"
        className="pointer-events-auto fixed flex flex-col gap-3 rounded-xl border bg-popover p-4 text-[14px] leading-snug text-popover-foreground shadow-lg outline-none motion-safe:transition-all motion-safe:duration-150"
        style={{ top, left, width: ancho }}
      >
        <p className="text-xs text-muted-foreground">
          Paso {numero} de {total}
        </p>
        <p aria-live="polite">{caja ? texto : "Un momento, buscando dónde tocar…"}</p>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Boton variante="texto" className="h-12" onClick={alSalir}>
            Salir
          </Boton>
          {accion && caja ? (
            <Boton
              variante="secundario"
              className="h-12"
              onClick={() => {
                accion.ejecutar();
                if (modo === "tocar") alAvanzar();
              }}
            >
              {accion.etiqueta}
            </Boton>
          ) : null}
          {modo === "leer" ? (
            <Boton variante="normal" className="h-12" onClick={alAvanzar}>
              Siguiente
            </Boton>
          ) : null}
        </div>
      </div>
    </div>
  );
}
