import { cn } from "cn";
import { CameraIcon, CameraOffIcon, CheckIcon, CornerDownLeftIcon, InfoIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";

import { practicaActiva } from "~/api/practica";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { prepararSonido, reproducir } from "./sonido";

// ---------------------------------------------------------------------------------------------
// BarcodeDetector todavía no está en las definiciones de TypeScript.
interface CodigoDetectado {
  rawValue: string;
}
interface DetectorDeCodigos {
  detect(fuente: HTMLVideoElement): Promise<CodigoDetectado[]>;
}
interface ConstructorDetector {
  new (opciones?: { formats?: string[] }): DetectorDeCodigos;
  getSupportedFormats?: () => Promise<string[]>;
}
function constructorDetector(): ConstructorDetector | null {
  if (typeof window === "undefined") return null;
  const c = (window as unknown as { BarcodeDetector?: ConstructorDetector }).BarcodeDetector;
  return c ?? null;
}

/** QR y los códigos de barras comunes en almacén. */
const FORMATOS = ["qr_code", "code_128", "code_39", "ean_13", "ean_8", "upc_a", "upc_e", "itf", "codabar", "data_matrix"];

// ---------------------------------------------------------------------------------------------

/** Con qué entrada llegó el código. Las tres entregan lo mismo. */
export type OrigenLectura = "camara" | "pistola" | "teclado";

/** Evento con el que el tutorial entrega un código de ejemplo a un escáner con `ancla`. */
export const EVENTO_ESCANEO_SIMULADO = "tutorial:escanear";

/** Mismo código leído en menos de este tiempo: se ignora. */
export const VENTANA_REPETIDO_MS = 1500;

/** Tras una lectura aceptada de la cámara o la pistola, el escáner ignora lecturas automáticas
 * durante este tiempo, para no registrar de más. El campo de texto no se bloquea. */
export const PAUSA_TRAS_LECTURA_MS = 2000;

/** Entre una tecla y la siguiente de una pistola pasan menos de ~30 ms; una persona tarda más de 100. */
export const MAXIMO_ENTRE_TECLAS_MS = 60;
const LARGO_MINIMO_PISTOLA = 3;

export interface ManejadorEscaner {
  limpiarCampo: () => void;
  abrirCamara: () => void;
  cerrarCamara: () => void;
  /** Lleva el cursor al campo "Escribir código o buscar". */
  enfocarCampo: () => void;
}

export interface PropiedadesEscaner {
  /** Recibe cada código leído, venga de la cámara, la pistola o el teclado. */
  onCodigo: (codigo: string, origen: OrigenLectura) => void;
  alCambiarTexto?: (texto: string) => void;
  /** Se avisa cuando se ignora una lectura repetida (menos de 1.5 s). La cámara avisa una vez por vista. */
  onRepetido?: (codigo: string, origen: OrigenLectura) => void;
  /** `false` apaga la pistola y la cámara (por ejemplo mientras hay una hoja abierta). Por omisión `true`. */
  activo?: boolean;
  /** Abre la cámara desde el principio. Por omisión cerrada hasta tocar "Escanear". */
  camaraInicial?: boolean;
  /** Suena y vibra un "ok" al leer. Ponlo en `false` si la pantalla reproduce el resultado del servidor. */
  sonidoAlLeer?: boolean;
  /** Mantiene la pantalla encendida mientras el escáner está abierto. Por omisión `true`. */
  mantenerPantalla?: boolean;
  etiquetaCampo?: string;
  placeholderCampo?: string;
  className?: string;
  /**
   * Valor de `data-tutorial` de este escáner (FEAT-010). El tutorial puede «escanear un ejemplo»
   * mandando el evento `tutorial:escanear` con `{ ancla, codigo }`.
   */
  ancla?: string;
  /**
   * Mensaje que la pantalla quiere mostrar junto al campo tras una lectura (por ejemplo un código que no
   * corresponde). Cambia `n` para mostrarlo de nuevo; se oculta solo a los 5 s. Opcional.
   */
  retroalimentacion?: { tipo: "error" | "ok"; texto: string; n: number } | null;
  ref?: Ref<ManejadorEscaner>;
}

type EstadoCamara = "cerrada" | "abriendo" | "abierta";

function esCampoDeTexto(destino: EventTarget | null): boolean {
  if (!(destino instanceof HTMLElement)) return false;
  if (destino.isContentEditable) return true;
  const etiqueta = destino.tagName;
  return etiqueta === "INPUT" || etiqueta === "TEXTAREA" || etiqueta === "SELECT";
}

/**
 * Escáner con tres entradas que entregan lo mismo, un código: cámara (se abre al tocar "Escanear" y
 * queda abierta), pistola (captura el teclado cuando no hay un campo con foco) y teclado (campo
 * "Escribir código o buscar"). No decide qué es el código: la pantalla lo manda al servidor.
 *
 * ```tsx
 * <Escaner onCodigo={(codigo) => agregar(codigo)} onRepetido={() => reproducir("aviso")} />
 * ```
 */
export function Escaner({
  onCodigo,
  alCambiarTexto,
  onRepetido,
  activo = true,
  camaraInicial = false,
  sonidoAlLeer = true,
  mantenerPantalla = true,
  etiquetaCampo = "Escribir código o buscar",
  placeholderCampo = "Código, número o nombre",
  className,
  ancla,
  retroalimentacion = null,
  ref,
}: PropiedadesEscaner) {
  const [soportaCamara, setSoportaCamara] = useState<boolean | null>(null);
  const [camara, setCamara] = useState<EstadoCamara>("cerrada");
  const [quiereCamara, setQuiereCamara] = useState(camaraInicial);
  const [errorCamara, setErrorCamara] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const tecleoCampo = useRef({ ultima: 0, caracteres: 0, suma: 0 });
  const [ultimo, setUltimo] = useState<{ codigo: string; n: number } | null>(null);

  const [mensajeVisible, setMensajeVisible] = useState(false);
  const mensajeN = retroalimentacion?.n;
  useEffect(() => {
    if (mensajeN === undefined) {
      setMensajeVisible(false);
      return;
    }
    setMensajeVisible(true);
    const t = window.setTimeout(() => setMensajeVisible(false), 5000);
    return () => window.clearTimeout(t);
  }, [mensajeN]);

  const video = useRef<HTMLVideoElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const ultimaLectura = useRef<{ codigo: string; t: number; avisado: boolean } | null>(null);
  const bloqueadoHasta = useRef(0);
  const finDePausa = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Mientras dura la pausa tras una lectura, se avisa que la lectura fue correcta y se guarda.
  const [enPausa, setEnPausa] = useState(false);

  // Siempre se usa la última versión de los callbacks sin reiniciar la cámara ni los oyentes.
  const alCodigo = useRef(onCodigo);
  const alRepetido = useRef(onRepetido);
  const sonar = useRef(sonidoAlLeer);
  useEffect(() => {
    alCodigo.current = onCodigo;
    alRepetido.current = onRepetido;
    sonar.current = sonidoAlLeer;
  });

  useEffect(() => {
    const disponible = constructorDetector() !== null && Boolean(navigator.mediaDevices?.getUserMedia);
    setSoportaCamara(disponible);
  }, []);

  /** Punto único de entrada: quita repetidos, avisa y entrega el código. */
  const procesar = useCallback((bruto: string, origen: OrigenLectura) => {
    const codigo = bruto.trim();
    if (!codigo) return;
    const ahora = performance.now();
    const previa = ultimaLectura.current;
    // Pausa de seguridad tras cada lectura automática. Si el mismo código sigue a la vista, se
    // sigue contando como visto para que no se lea otra vez al terminar la pausa.
    if (origen !== "teclado" && ahora < bloqueadoHasta.current) {
      if (previa && previa.codigo === codigo) previa.t = ahora;
      return;
    }
    if (previa && previa.codigo === codigo && ahora - previa.t < VENTANA_REPETIDO_MS) {
      if (origen === "camara") {
        // Mientras el código siga a la vista no se vuelve a leer; se avisa una sola vez.
        previa.t = ahora;
        if (!previa.avisado) {
          previa.avisado = true;
          alRepetido.current?.(codigo, origen);
        }
      } else {
        alRepetido.current?.(codigo, origen);
      }
      return;
    }
    ultimaLectura.current = { codigo, t: ahora, avisado: false };
    if (origen !== "teclado") {
      bloqueadoHasta.current = ahora + PAUSA_TRAS_LECTURA_MS;
      setEnPausa(true);
      if (finDePausa.current) clearTimeout(finDePausa.current);
      finDePausa.current = setTimeout(() => setEnPausa(false), PAUSA_TRAS_LECTURA_MS);
    }
    if (sonar.current) reproducir("ok");
    setUltimo((u) => ({ codigo, n: (u?.n ?? 0) + 1 }));
    alCodigo.current(codigo, origen);
  }, []);

  useEffect(
    () => () => {
      if (finDePausa.current) clearTimeout(finDePausa.current);
    },
    [],
  );

  // Se prepara el audio con el primer toque o tecla (los navegadores no dejan sonar antes).
  useEffect(() => {
    const preparar = () => prepararSonido();
    window.addEventListener("pointerdown", preparar, { once: true, capture: true });
    window.addEventListener("keydown", preparar, { once: true, capture: true });
    return () => {
      window.removeEventListener("pointerdown", preparar, { capture: true });
      window.removeEventListener("keydown", preparar, { capture: true });
    };
  }, []);

  // ------------------------------------------------------------------ escaneo simulado del tutorial (TU-06)
  useEffect(() => {
    if (!ancla) return;
    const alSimular = (e: Event) => {
      const d = (e as CustomEvent<{ ancla: string; codigo: string }>).detail;
      if (d?.ancla === ancla && d.codigo) procesar(d.codigo, "teclado");
    };
    window.addEventListener(EVENTO_ESCANEO_SIMULADO, alSimular);
    return () => window.removeEventListener(EVENTO_ESCANEO_SIMULADO, alSimular);
  }, [ancla, procesar]);

  // ------------------------------------------------------------------ pistola
  useEffect(() => {
    if (!activo) return;
    let buffer = "";
    let ultimaTecla = 0;
    let sumaIntervalos = 0;

    const limpiar = () => {
      buffer = "";
      sumaIntervalos = 0;
    };

    const alTeclear = (e: KeyboardEvent) => {
      if (e.isComposing || e.ctrlKey || e.altKey || e.metaKey) return;
      // Si hay un campo con foco, escribe ahí; no se captura nada.
      if (esCampoDeTexto(e.target)) {
        limpiar();
        return;
      }
      const ahora = performance.now();

      if (e.key === "Enter" || e.key === "Tab") {
        const promedio = buffer.length > 1 ? sumaIntervalos / (buffer.length - 1) : Infinity;
        const esRafaga = buffer.length >= LARGO_MINIMO_PISTOLA && promedio <= MAXIMO_ENTRE_TECLAS_MS;
        if (esRafaga) {
          e.preventDefault();
          e.stopPropagation();
          const codigo = buffer;
          limpiar();
          procesar(codigo, "pistola");
        } else {
          limpiar();
        }
        return;
      }

      if (e.key.length !== 1) return; // Shift, flechas, etc.
      const intervalo = ahora - ultimaTecla;
      if (buffer && intervalo > MAXIMO_ENTRE_TECLAS_MS * 2) limpiar(); // tecleo humano: se descarta
      if (buffer) sumaIntervalos += intervalo;
      buffer += e.key;
      ultimaTecla = ahora;
    };

    window.addEventListener("keydown", alTeclear, true);
    return () => window.removeEventListener("keydown", alTeclear, true);
  }, [activo, procesar]);

  // ------------------------------------------------------------------ pantalla encendida
  useEffect(() => {
    if (!activo || !mantenerPantalla) return;
    type Cerrojo = { release: () => Promise<void> };
    let cerrojo: Cerrojo | null = null;
    let cancelado = false;
    const pedir = async () => {
      try {
        const wl = (navigator as unknown as { wakeLock?: { request: (t: "screen") => Promise<Cerrojo> } }).wakeLock;
        if (!wl || document.visibilityState !== "visible") return;
        const nuevo = await wl.request("screen");
        if (cancelado) void nuevo.release().catch(() => {});
        else cerrojo = nuevo;
      } catch {
        // Sin Wake Lock o sin permiso: la pantalla se apaga como siempre.
      }
    };
    const alCambiarVisibilidad = () => {
      if (document.visibilityState === "visible") void pedir();
    };
    void pedir();
    document.addEventListener("visibilitychange", alCambiarVisibilidad);
    return () => {
      cancelado = true;
      document.removeEventListener("visibilitychange", alCambiarVisibilidad);
      void cerrojo?.release().catch(() => {});
    };
  }, [activo, mantenerPantalla]);

  // ------------------------------------------------------------------ cámara
  // En práctica (TU-06) la cámara nunca se enciende.
  const camaraEncendida = quiereCamara && activo && soportaCamara === true && !practicaActiva();
  useEffect(() => {
    if (!camaraEncendida) {
      setCamara("cerrada");
      return;
    }
    let cancelado = false;
    let flujo: MediaStream | null = null;
    let cuadro = 0;
    setCamara("abriendo");
    setErrorCamara(null);

    const detener = () => {
      cancelado = true;
      cancelAnimationFrame(cuadro);
      flujo?.getTracks().forEach((pista) => pista.stop());
      if (video.current) video.current.srcObject = null;
    };

    void (async () => {
      try {
        flujo = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        if (cancelado) {
          flujo.getTracks().forEach((pista) => pista.stop());
          return;
        }
        const elemento = video.current;
        if (!elemento) return;
        elemento.srcObject = flujo;
        await elemento.play().catch(() => {});

        const Detector = constructorDetector()!;
        let formatos = FORMATOS;
        try {
          const aceptados = await Detector.getSupportedFormats?.();
          if (aceptados?.length) formatos = FORMATOS.filter((f) => aceptados.includes(f));
        } catch {
          // Se usa la lista completa.
        }
        const detector = new Detector({ formats: formatos.length ? formatos : undefined });
        if (cancelado) return;
        setCamara("abierta");

        let ocupado = false;
        let ultimoCuadro = 0;
        const ciclo = (t: number) => {
          if (cancelado) return;
          cuadro = requestAnimationFrame(ciclo);
          if (ocupado || t - ultimoCuadro < 100 || elemento.readyState < 2) return;
          ocupado = true;
          ultimoCuadro = t;
          detector
            .detect(elemento)
            .then((codigos) => {
              if (cancelado) return;
              for (const c of codigos) if (c.rawValue) procesar(c.rawValue, "camara");
            })
            .catch(() => {})
            .finally(() => {
              ocupado = false;
            });
        };
        cuadro = requestAnimationFrame(ciclo);
      } catch (error) {
        if (cancelado) return;
        const nombre = error instanceof DOMException ? error.name : "";
        setErrorCamara(
          nombre === "NotAllowedError" || nombre === "SecurityError"
            ? "No se pudo usar la cámara. Permite el acceso en tu navegador y vuelve a intentarlo."
            : nombre === "NotFoundError" || nombre === "OverconstrainedError"
              ? "Este equipo no tiene cámara disponible."
              : "No pudimos abrir la cámara. Cierra otras aplicaciones que la usen e inténtalo de nuevo.",
        );
        setQuiereCamara(false);
        setCamara("cerrada");
      }
    })();

    return detener;
  }, [camaraEncendida, procesar]);

  useImperativeHandle(
    ref,
    () => ({
      limpiarCampo: () => { setTexto(""); alCambiarTexto?.(""); },
      abrirCamara: () => setQuiereCamara(true),
      cerrarCamara: () => setQuiereCamara(false),
      enfocarCampo: () => campo.current?.focus(),
    }),
    [],
  );

  const enviarTexto = (e: React.SyntheticEvent) => {
    e.preventDefault();
    const valor = texto.trim();
    if (!valor) return;
    setTexto("");
    alCambiarTexto?.("");
    const t = tecleoCampo.current;
    const pistola = t.caracteres >= LARGO_MINIMO_PISTOLA && t.suma / (t.caracteres - 1) <= MAXIMO_ENTRE_TECLAS_MS && performance.now() - t.ultima < 300;
    tecleoCampo.current = { ultima: 0, caracteres: 0, suma: 0 };
    procesar(valor, pistola ? "pistola" : "teclado");
  };

  const sinSoporte = soportaCamara === false;
  const camaraVisible = camaraEncendida;

  return (
    <div className={cn("flex flex-col gap-3", className)} data-slot="escaner" data-tutorial={ancla}>
      <div className="flex flex-col gap-3">
        {camaraVisible ? (
          <div className="relative overflow-hidden rounded-2xl border-2 border-primary bg-black">
            <video
              ref={video}
              playsInline
              muted
              autoPlay
              aria-label="Vista de la cámara"
              className="aspect-[4/3] max-h-[60dvh] w-full object-cover"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-[18%] rounded-2xl border-4 border-white/90 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"
            />
            {camara === "abriendo" ? (
              <p role="status" className="absolute inset-x-0 bottom-3 text-center text-sm font-semibold text-white">
                Abriendo la cámara…
              </p>
            ) : enPausa ? (
              <p
                role="status"
                className="absolute inset-x-3 bottom-3 flex items-center justify-center gap-2 rounded-xl bg-marino px-3 py-2 text-center text-sm font-semibold text-white"
              >
                <CheckIcon aria-hidden="true" strokeWidth={3} className="size-4 shrink-0" />
                Lectura correcta. Guardando…
              </p>
            ) : (
              <p className="absolute inset-x-0 bottom-3 text-center text-sm font-semibold text-white drop-shadow">
                Apunta al código; se lee solo.
              </p>
            )}
          </div>
        ) : null}

        <Boton
          variante={camaraVisible ? "contorno" : "normal"}
          className="w-full"
          disabled={sinSoporte || !activo}
          onClick={() => {
            prepararSonido();
            setQuiereCamara((v) => !v);
          }}
          aria-pressed={camaraVisible}
        >
          {camaraVisible ? (
            <>
              <XIcon aria-hidden="true" />
              Cerrar cámara
            </>
          ) : (
            <>
              {sinSoporte ? <CameraOffIcon aria-hidden="true" /> : <CameraIcon aria-hidden="true" />}
              Escanear
            </>
          )}
        </Boton>

        {sinSoporte ? (
          <p role="status" className="flex items-start gap-2 rounded-xl bg-muted p-3 text-sm text-muted-foreground">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-marino" />
            <span>Este navegador no abre la cámara. Usa la pistola lectora o escribe el código.</span>
          </p>
        ) : null}
        {errorCamara ? (
          <p role="alert" className="flex items-start gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-semaforo-amarillo" />
            <span>{errorCamara}</span>
          </p>
        ) : null}
      </div>

      <form onSubmit={enviarTexto} className="flex items-end gap-2">
        <Campo
          ref={campo}
          etiqueta={etiquetaCampo}
          claseContenedor="flex-1"
          value={texto}
          onKeyDown={(e) => {
            if (e.key.length !== 1 || e.ctrlKey || e.altKey || e.metaKey || e.nativeEvent.isComposing) return;
            const ahora = performance.now();
            const t = tecleoCampo.current;
            const intervalo = ahora - t.ultima;
            tecleoCampo.current = !t.caracteres || intervalo > MAXIMO_ENTRE_TECLAS_MS * 2 ? { ultima: ahora, caracteres: 1, suma: 0 } : { ultima: ahora, caracteres: t.caracteres + 1, suma: t.suma + intervalo };
          }}
          onChange={(e) => { setTexto(e.target.value); alCambiarTexto?.(e.target.value); }}
          placeholder={placeholderCampo}
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="send"
          disabled={!activo}
        />
        <Boton type="submit" variante="secundario" className="h-11" disabled={!activo || !texto.trim()} aria-label="Enviar código">
          <CornerDownLeftIcon aria-hidden="true" />
          <span className="max-sm:sr-only">Agregar</span>
        </Boton>
      </form>

      {retroalimentacion && mensajeVisible ? (
        <p
          role={retroalimentacion.tipo === "error" ? "alert" : "status"}
          className={cn(
            "flex items-start gap-2 rounded-2xl border-2 p-3 text-base font-semibold",
            retroalimentacion.tipo === "error"
              ? "border-semaforo-rojo bg-semaforo-rojo/10"
              : "border-semaforo-verde bg-semaforo-verde/10",
          )}
        >
          {retroalimentacion.tipo === "error" ? (
            <XIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-rojo" />
          ) : null}
          <span>{retroalimentacion.texto}</span>
        </p>
      ) : null}

      {enPausa ? (
        <p
          role="status"
          className="flex items-center gap-2 rounded-xl border border-primary bg-accent px-3 py-1.5 text-sm font-semibold text-marino"
        >
          <CheckIcon aria-hidden="true" strokeWidth={3} className="size-4 shrink-0" />
          Lectura correcta. Guardando…
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">Con pistola lectora: apunta y dispara, sin tocar ningún campo.</p>
      )}

      {/* Anuncia la última lectura a los lectores de pantalla. */}
      <p className="sr-only" role="status" aria-live="polite">
        {ultimo ? `Leído ${ultimo.codigo}` : ""}
      </p>
    </div>
  );
}
