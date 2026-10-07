import { CircleAlertIcon, ClipboardListIcon, InfoIcon, RotateCcwIcon, UserRoundIcon, WifiOffIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker, useNavigate } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError, type ErrorApi } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import { ConfirmarCantidad } from "~/componentes/dominio/confirmar-cantidad";
import { Escaner, type OrigenLectura } from "~/componentes/dominio/escaner";
import { FichaTrabajador } from "~/componentes/dominio/ficha-trabajador";
import { ListaRenglones } from "~/componentes/dominio/lista-renglones";
import { TEXTO_NIVEL } from "~/componentes/dominio/renglon-semaforo";
import { reproducir } from "~/componentes/dominio/sonido";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import {
  borrarBorrador,
  claveDeCodigo,
  guardarBorrador,
  leerBorrador,
  nuevoBorradorEntrega,
  tieneCaptura,
  type AutorizacionBorrador,
  type BorradorEntrega,
  type PasoEntrega,
} from "~/componentes/entrega/borrador";
import { BandaAutorizacion } from "~/componentes/entrega/banda-autorizacion";
import { HojaAutorizacion } from "~/componentes/entrega/hoja-autorizacion";
import { HojaBusquedaArticulos, type CoincidenciaArticulo } from "~/componentes/entrega/hoja-busqueda-articulos";
import { HojaDotacion, type DotacionElegida } from "~/componentes/entrega/hoja-dotacion";
import { ObservacionEntrega } from "~/componentes/entrega/observacion-entrega";
import { PasoFirma } from "~/componentes/entrega/paso-firma";
import { PasoTrabajador } from "~/componentes/entrega/paso-trabajador";
import { BotonAtrasPaso, usarAtrasDePasos } from "~/componentes/navegacion/atras";
import { IndicadorPasos } from "~/componentes/ui/indicador-pasos";
import { ResultadoEntrega } from "~/componentes/entrega/resultado-entrega";
import { SelectorAlmacen } from "~/componentes/entrega/selector-almacen";
import type {
  AlmacenResumen,
  AutorizacionApi,
  EvaluacionApi,
  FichaTrabajadorApi,
  FirmaCapturada,
  ValeConfirmadoApi,
} from "~/componentes/entrega/tipos";
import { useDotacion } from "~/componentes/entrega/use-dotacion";
import { useEvaluacion, type CuerpoEvaluar } from "~/componentes/entrega/use-evaluacion";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "entregas.crear" };

const CLAVE_ALMACEN = "imhotep.almacen.operando";

function leerAlmacenRecordado(): string | null {
  try {
    return window.localStorage.getItem(CLAVE_ALMACEN);
  } catch {
    return null;
  }
}
function recordarAlmacen(id: string) {
  try {
    window.localStorage.setItem(CLAVE_ALMACEN, id);
  } catch {
    // Sin almacenamiento, simplemente no se recuerda.
  }
}

const NOMBRE_PASO: Record<PasoEntrega, string> = {
  trabajador: "Trabajador",
  articulos: "Artículos",
  firma: "Firma",
  resultado: "Listo",
};
const NUMERO_PASO: Record<PasoEntrega, number> = { trabajador: 1, articulos: 2, firma: 3, resultado: 3 };

interface EscaneoApi {
  tipo: "TRABAJADOR" | "ARTICULO" | "PIEZA" | "VALE" | "DESCONOCIDO";
}
interface BusquedaApi {
  articulos: { elementos: { codigo: string; nombre: string; marca: string | null }[] };
  piezas: { elementos: { codigo: string; articulo: string; numero_serie: string | null }[] };
}

/** "par" -> "pares de"; para la frase de confirmación de una cantidad inusual. */
function unidadEnPlural(unidad?: string): string | undefined {
  if (!unidad) return undefined;
  const base = unidad.trim().toLocaleLowerCase("es-MX");
  if (!base) return undefined;
  const plural = /[aeiouáéíó]$/.test(base) ? `${base}s` : `${base}es`;
  return `${plural} de`;
}

type ErrorEnvio = { tipo: "conexion" | "otro"; mensaje: string } | null;

export default function Entregar() {
  const { sesion, puede, recargar } = useSesionActiva();
  const navegar = useNavigate();
  const enLinea = useEnLinea();
  const usuarioId = sesion.usuario.id;
  const operaTodos = puede("almacenes.todos");

  // ------------------------------------------------------------------ borrador (persistente)
  const [inicial] = useState(() => {
    const guardado = leerBorrador(usuarioId);
    const almacen = sesion.almacen?.id ?? (operaTodos ? leerAlmacenRecordado() : null);
    const base = guardado ?? nuevoBorradorEntrega(usuarioId, almacen);
    return { borrador: base, retomado: Boolean(guardado) && base.paso !== "resultado" && base.trabajador !== null };
  });
  const [borrador, setBorrador] = useState<BorradorEntrega>(inicial.borrador);
  const [retomado, setRetomado] = useState(inicial.retomado);
  const borradorRef = useRef(borrador);
  borradorRef.current = borrador;

  useEffect(() => {
    guardarBorrador(borrador);
  }, [borrador]);

  // Al salir de la pantalla ya con el vale emitido, el borrador no se conserva.
  useEffect(
    () => () => {
      if (borradorRef.current.paso === "resultado") borrarBorrador();
    },
    [],
  );

  const actualizar = useCallback((cambio: (b: BorradorEntrega) => BorradorEntrega) => setBorrador(cambio), []);

  // ------------------------------------------------------------------ estado de pantalla
  const [notas, setNotas] = useState<Record<string, string>>({});
  const [avisoCambio, setAvisoCambio] = useState<string | null>(null);
  const [almacenCambio, setAlmacenCambio] = useState<{ mensaje: string; almacen: AlmacenResumen | null } | null>(null);
  const [errorEnvio, setErrorEnvio] = useState<ErrorEnvio>(null);
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const [errorObservacion, setErrorObservacion] = useState<string | null>(null);
  const [eligiendoDotacion, setEligiendoDotacion] = useState(false);
  const [pidiendoAutorizacion, setPidiendoAutorizacion] = useState(false);
  const [descartando, setDescartando] = useState(false);
  const [resultadosBusqueda, setResultadosBusqueda] = useState<{ texto: string; items: CoincidenciaArticulo[] } | null>(null);
  const [buscandoArticulo, setBuscandoArticulo] = useState(false);
  const [descartadasCantidad, setDescartadasCantidad] = useState<ReadonlySet<string>>(new Set());
  const sonidoPendiente = useRef<Set<string>>(new Set());

  // ------------------------------------------------------------------ evaluación
  const autorizacion = borrador.autorizacion;
  const cuerpo = useMemo<CuerpoEvaluar | null>(() => {
    if (borrador.paso !== "articulos" && borrador.paso !== "firma") return null;
    if (!borrador.trabajador || borrador.renglones.length === 0) return null;
    if (operaTodos && !borrador.almacenId) return null;
    return {
      tipo: "ENTREGA",
      almacen_id: borrador.almacenId,
      trabajador_id: borrador.trabajador.id,
      id_cliente: borrador.idCliente,
      autorizacion_id: autorizacion?.estado === "APROBADA" ? autorizacion.id : undefined,
      renglones: borrador.renglones.map((r) => ({
        codigo: r.codigo,
        cantidad: r.cantidad,
        observacion: r.observacion || undefined,
      })),
    };
  }, [borrador.paso, borrador.trabajador, borrador.renglones, borrador.almacenId, borrador.idCliente, autorizacion, operaTodos]);

  const ev = useEvaluacion(cuerpo);
  const evaluacion: EvaluacionApi | null = cuerpo ? ev.evaluacion : null;

  const mapaEvaluados = useMemo(
    () => new Map((evaluacion?.renglones ?? []).map((r) => [claveDeCodigo(r.codigo), r] as const)),
    [evaluacion],
  );

  /** Renglones tal como los evalúa el servidor, con la cantidad que se ve ahora en el borrador. */
  const evaluados = useMemo<RenglonEvaluado[]>(
    () =>
      borrador.renglones.flatMap((b) => {
        const r = mapaEvaluados.get(claveDeCodigo(b.codigo));
        return r ? [{ ...r, cantidad: b.cantidad }] : [];
      }),
    [borrador.renglones, mapaEvaluados],
  );
  const sinEvaluar = borrador.renglones.filter((b) => !mapaEvaluados.has(claveDeCodigo(b.codigo)));

  // El servidor junta lo repetido (E-15, E-16): si un renglón del borrador ya no aparece, se quita.
  useEffect(() => {
    if (!ev.actual || !evaluacion || sinEvaluar.length === 0) return;
    const sobran = new Set(sinEvaluar.map((b) => claveDeCodigo(b.codigo)));
    actualizar((b) => ({ ...b, renglones: b.renglones.filter((r) => !sobran.has(claveDeCodigo(r.codigo))) }));
  }, [ev.actual, evaluacion, sinEvaluar, actualizar]);

  // Sonido del resultado de cada lectura nueva: listo, aviso o bloqueo.
  useEffect(() => {
    if (!ev.actual || sonidoPendiente.current.size === 0) return;
    for (const clave of [...sonidoPendiente.current]) {
      const r = mapaEvaluados.get(clave);
      if (!r) continue;
      sonidoPendiente.current.delete(clave);
      reproducir(r.nivel === "ROJO" ? "bloqueo" : r.nivel === "VERDE" ? "ok" : "aviso");
    }
  }, [ev.actual, mapaEvaluados]);

  // Un error de almacén al evaluar se atiende igual que al confirmar.
  const errorEvaluacion: ErrorApi | null = cuerpo ? ev.error : null;
  useEffect(() => {
    if (errorEvaluacion?.codigo === "ALMACEN_CAMBIO") {
      const almacen = (errorEvaluacion.detalles?.almacen as AlmacenResumen | null | undefined) ?? null;
      setAlmacenCambio({ mensaje: errorEvaluacion.message, almacen });
    }
  }, [errorEvaluacion]);

  // ------------------------------------------------------------------ autorización a distancia
  useEffect(() => {
    if (!autorizacion || autorizacion.estado !== "PENDIENTE") return;
    let activo = true;
    const control = new AbortController();
    const consultar = async () => {
      try {
        const r = await apiGet<AutorizacionApi>(`/autorizaciones/${autorizacion.id}`, undefined, control.signal);
        if (!activo || r.estado === "PENDIENTE") return;
        actualizar((b) =>
          b.autorizacion?.id === autorizacion.id
            ? { ...b, autorizacion: { ...b.autorizacion, estado: r.estado, resuelta_por: r.resuelta_por?.nombre ?? null } }
            : b,
        );
        if (r.estado === "APROBADA") {
          reproducir("ok");
          aviso({ titulo: "El supervisor autorizó", tipo: "exito" });
        } else {
          reproducir("bloqueo");
        }
      } catch {
        // Sin conexión o error pasajero: se vuelve a intentar en 3 segundos.
      }
    };
    const id = window.setInterval(() => void consultar(), 3000);
    return () => {
      activo = false;
      window.clearInterval(id);
      control.abort();
    };
  }, [autorizacion?.id, autorizacion?.estado, actualizar]);

  // ------------------------------------------------------------------ salir con captura
  const hayCaptura = tieneCaptura(borrador);
  const bloqueo = useBlocker(hayCaptura);

  // ------------------------------------------------------------------ cambios del borrador
  const irA = (paso: PasoEntrega) => {
    setErrorEnvio(null);
    actualizar((b) => ({ ...b, paso }));
  };

  const agregarCodigo = useCallback(
    (codigo: string) => {
      const limpio = codigo.trim();
      if (!limpio) return;
      const clave = claveDeCodigo(limpio);
      const existente = borradorRef.current.renglones.find((r) => claveDeCodigo(r.codigo) === clave);
      setNotas({});
      setAvisoCambio(null);
      if (existente) {
        const evaluado = mapaEvaluados.get(clave);
        if (evaluado?.articulo?.control === "CANTIDAD") {
          sonidoPendiente.current.add(clave);
          actualizar((b) => ({
            ...b,
            renglones: b.renglones.map((r) => (claveDeCodigo(r.codigo) === clave ? { ...r, cantidad: r.cantidad + 1 } : r)),
            cantidadesConfirmadas: Object.fromEntries(Object.entries(b.cantidadesConfirmadas).filter(([k]) => k !== clave)),
          }));
        } else {
          // E-15: una pieza repetida se ignora, con sonido.
          reproducir("aviso");
          aviso({ titulo: "Ya está en la lista", descripcion: evaluado?.articulo?.nombre ?? limpio, tipo: "aviso", duracionMs: 2500 });
        }
        return;
      }
      sonidoPendiente.current.add(clave);
      actualizar((b) => ({ ...b, renglones: [...b.renglones, { codigo: limpio, cantidad: 1 }] }));
    },
    [mapaEvaluados, actualizar],
  );

  const alLeerArticulo = useCallback(
    async (codigo: string, origen: OrigenLectura) => {
      if (origen !== "teclado") {
        agregarCodigo(codigo);
        return;
      }
      // Lo que se teclea puede ser un código o un nombre: si el servidor no lo reconoce, se busca.
      setBuscandoArticulo(true);
      try {
        const escaneo = await apiGet<EscaneoApi>(`/escaneo/${encodeURIComponent(codigo)}`);
        if (escaneo.tipo === "DESCONOCIDO" && codigo.length >= 2) {
          const b = await apiGet<BusquedaApi>("/busqueda", { q: codigo });
          const items: CoincidenciaArticulo[] = [
            ...b.articulos.elementos.map((a) => ({
              codigo: a.codigo,
              nombre: a.nombre,
              detalle: [a.marca, a.codigo].filter(Boolean).join(" · "),
            })),
            ...b.piezas.elementos.map((p) => ({
              codigo: p.codigo,
              nombre: p.articulo,
              detalle: `Pieza ${p.codigo}${p.numero_serie ? ` · Serie ${p.numero_serie}` : ""}`,
            })),
          ];
          if (items.length > 0) {
            setResultadosBusqueda({ texto: codigo, items });
            return;
          }
        }
        agregarCodigo(codigo);
      } catch (causa) {
        reproducir("aviso");
        aviso({ titulo: "No pudimos buscar", descripcion: mensajeDeError(causa), tipo: "error" });
      } finally {
        setBuscandoArticulo(false);
      }
    },
    [agregarCodigo],
  );

  const quitar = useCallback(
    (r: RenglonEvaluado) => {
      const clave = claveDeCodigo(r.codigo);
      setNotas({});
      actualizar((b) => ({ ...b, renglones: b.renglones.filter((x) => claveDeCodigo(x.codigo) !== clave) }));
    },
    [actualizar],
  );

  const cambiarCantidad = (r: RenglonEvaluado, cantidad: number) => {
    const clave = claveDeCodigo(r.codigo);
    setNotas({});
    actualizar((b) => ({
      ...b,
      renglones: b.renglones.map((x) => (claveDeCodigo(x.codigo) === clave ? { ...x, cantidad } : x)),
      cantidadesConfirmadas: Object.fromEntries(Object.entries(b.cantidadesConfirmadas).filter(([k]) => k !== clave)),
    }));
  };

  const cambiarObservacion = (texto: string) => {
    setErrorObservacion(null);
    actualizar((b) => ({ ...b, observacion: texto }));
  };

  /** "Dotación sugerida": agrega lo elegido como renglones normales; el servidor evalúa cada uno (E-09 a E-11). */
  const agregarDeDotacion = (elegidos: DotacionElegida[]) => {
    setNotas({});
    setAvisoCambio(null);
    const existentes = new Set(borradorRef.current.renglones.map((r) => claveDeCodigo(r.codigo)));
    const nuevos = elegidos.filter((e) => !existentes.has(claveDeCodigo(e.codigo)));
    if (nuevos.length === 0) return;
    for (const e of nuevos) sonidoPendiente.current.add(claveDeCodigo(e.codigo));
    actualizar((b) => ({ ...b, renglones: [...b.renglones, ...nuevos.map((e) => ({ codigo: e.codigo, cantidad: e.cantidad }))] }));
  };

  const elegirAlmacen = (almacen: AlmacenResumen) => {
    recordarAlmacen(almacen.id);
    actualizar((b) => ({ ...b, almacenId: almacen.id, autorizacion: b.almacenId === almacen.id ? b.autorizacion : null }));
  };

  const quitarRenglonesDeAutorizacion = () => {
    const codigos = new Set((borrador.autorizacion?.codigos ?? []).map(claveDeCodigo));
    setNotas({});
    actualizar((b) => ({
      ...b,
      renglones: b.renglones.filter((r) => !codigos.has(claveDeCodigo(r.codigo))),
      autorizacion: null,
    }));
  };

  const empezarDeNuevo = () => {
    borrarBorrador();
    sonidoPendiente.current = new Set();
    setNotas({});
    setAvisoCambio(null);
    setAlmacenCambio(null);
    setErrorEnvio(null);
    setErrorObservacion(null);
    setRetomado(false);
    setDescartadasCantidad(new Set());
    setBorrador(nuevoBorradorEntrega(usuarioId, borradorRef.current.almacenId));
  };

  // ------------------------------------------------------------------ confirmar
  const confirmar = async () => {
    if (enviandoRef.current) return;
    const b = borradorRef.current;
    if (!b.trabajador || !b.firma) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    setErrorObservacion(null);
    setAvisoCambio(null);
    const observacion = evaluacion?.pide_observacion ? b.observacion?.trim() : undefined;
    try {
      const vale = await apiPost<ValeConfirmadoApi>("/vales", {
        tipo: "ENTREGA",
        almacen_id: b.almacenId,
        trabajador_id: b.trabajador.id,
        id_cliente: b.idCliente,
        autorizacion_id: b.autorizacion?.estado === "APROBADA" ? b.autorizacion.id : undefined,
        observacion: observacion || undefined,
        renglones: b.renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad, observacion: r.observacion || undefined })),
        firma: { modo: "PANTALLA", imagen: b.firma.imagen, trazo: b.firma.trazo },
      });
      reproducir("ok");
      actualizar((x) => ({ ...x, paso: "resultado", resultado: vale }));
    } catch (causa) {
      reproducir("bloqueo");
      atenderErrorAlConfirmar(causa);
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  };

  const atenderErrorAlConfirmar = (causa: unknown) => {
    if (!esErrorApi(causa)) {
      setErrorEnvio({ tipo: "otro", mensaje: mensajeDeError(causa) });
      return;
    }
    if (causa.sinConexion) {
      setErrorEnvio({ tipo: "conexion", mensaje: "Sin conexión. La entrega y la firma están guardadas en este dispositivo." });
      return;
    }
    if (causa.reintentable) {
      // El sistema estaba ocupado: lo capturado sigue aquí y reintentar no duplica el vale.
      setErrorEnvio({ tipo: "conexion", mensaje: causa.message });
      return;
    }
    if (causa.status === 422 && JSON.stringify(causa.detalles ?? "").includes("E-09")) {
      // El servidor exige el motivo de una entrega fuera de lo recomendado: el error va junto al campo.
      setErrorObservacion(causa.message);
      return;
    }
    if (causa.codigo === "VALE_CAMBIO" && causa.detalles) {
      const nueva = causa.detalles as unknown as EvaluacionApi;
      const marcas: Record<string, string> = {};
      for (const r of nueva.renglones) {
        if (r.nivel === "ROJO" || (r.nivel === "NARANJA" && !r.autorizado)) {
          marcas[claveDeCodigo(r.codigo)] = "Esto cambió mientras capturabas. Revísalo.";
        }
      }
      ev.adoptar(nueva);
      setNotas(marcas);
      setAvisoCambio(causa.message);
      reproducir("bloqueo");
      actualizar((x) => ({ ...x, paso: "articulos" }));
      return;
    }
    if (causa.codigo === "ALMACEN_CAMBIO") {
      const almacen = (causa.detalles?.almacen as AlmacenResumen | null | undefined) ?? null;
      setAlmacenCambio({ mensaje: causa.message, almacen });
      actualizar((x) => ({ ...x, paso: "articulos" }));
      return;
    }
    if (causa.codigo === "AUTORIZACION_INVALIDA" || causa.codigo === "AUTORIZACION_PROPIA") {
      setAvisoCambio(causa.message);
      actualizar((x) => ({ ...x, paso: "articulos" }));
      return;
    }
    setErrorEnvio({ tipo: "otro", mensaje: causa.message });
  };

  const continuarEnAlmacenActual = async () => {
    const nuevo = almacenCambio?.almacen;
    if (!nuevo) return;
    await recargar();
    setAlmacenCambio(null);
    actualizar((b) => ({ ...b, almacenId: nuevo.id, autorizacion: null }));
  };

  // ------------------------------------------------------------------ lo que se pinta
  // La evaluación trae la ficha al día; el periodo (fecha de vigencia) solo viene en la ficha completa.
  const trabajador: FichaTrabajadorApi | null = evaluacion?.trabajador
    ? { ...evaluacion.trabajador, periodo: borrador.trabajador?.periodo }
    : borrador.trabajador;
  const almacenNombre = evaluacion?.almacen.nombre ?? sesion.almacen?.nombre ?? null;
  const dotacion = useDotacion(borrador.trabajador?.id ?? null, borrador.paso);
  const faltanDotacion = dotacion ? dotacion.renglones.filter((r) => r.falta > 0).length : 0;
  const yaEnLista = useMemo(
    () =>
      new Set([
        ...borrador.renglones.map((r) => claveDeCodigo(r.codigo)),
        ...evaluados.flatMap((r) => (r.articulo?.codigo ? [claveDeCodigo(r.articulo.codigo)] : [])),
      ]),
    [borrador.renglones, evaluados],
  );
  const pideObservacion = Boolean(evaluacion?.pide_observacion) || evaluados.some((r) => r.pide_observacion);
  const motivosDeObservacion = evaluados.flatMap((r) =>
    r.pide_observacion ? r.motivos.filter((m) => m.regla === "E-09").map((m) => m.mensaje) : [],
  );
  const faltaObservacion = pideObservacion && !(borrador.observacion ?? "").trim();
  const naranjasPorAutorizar = evaluados.filter((r) => r.nivel === "NARANJA" && !r.autorizado);
  const naranjasAutorizables = naranjasPorAutorizar.filter((r) => r.autorizable);
  const autorizacionPendiente = autorizacion?.estado === "PENDIENTE";

  const porConfirmar = useMemo(
    () =>
      evaluados.find((r) => {
        if (!r.requiere_confirmacion) return false;
        const clave = claveDeCodigo(r.codigo);
        return borrador.cantidadesConfirmadas[clave] !== r.cantidad && !descartadasCantidad.has(`${clave}:${r.cantidad}`);
      }),
    [evaluados, borrador.cantidadesConfirmadas, descartadasCantidad],
  );

  const razonParaNoContinuar = (): string | null => {
    if (borrador.renglones.length === 0) return "Escanea al menos un artículo para continuar.";
    if (errorEvaluacion && !ev.actual) {
      return errorEvaluacion.sinConexion ? "Sin conexión: no podemos revisar la lista todavía." : "No pudimos revisar la lista.";
    }
    if (!evaluacion || !ev.actual || ev.evaluando) return "Revisando la lista…";
    const rojos = evaluados.filter((r) => r.nivel === "ROJO").length;
    if (rojos > 0) return `Quita ${rojos === 1 ? "el artículo en rojo" : `los ${rojos} artículos en rojo`} para continuar.`;
    if (naranjasPorAutorizar.length > 0) {
      const n = naranjasPorAutorizar.length;
      return autorizacionPendiente
        ? "Esperando la respuesta del supervisor."
        : `${n === 1 ? "Un artículo requiere" : `${n} artículos requieren`} autorización. Pídela o quita el renglón.`;
    }
    const cantidadSinConfirmar = evaluados.find(
      (r) => r.requiere_confirmacion && borrador.cantidadesConfirmadas[claveDeCodigo(r.codigo)] !== r.cantidad,
    );
    if (cantidadSinConfirmar) return `Confirma la cantidad de ${cantidadSinConfirmar.articulo?.nombre ?? cantidadSinConfirmar.codigo}.`;
    if (!evaluacion.puede_confirmar) {
      return evaluacion.autorizacion_error ?? evaluacion.motivos[0]?.mensaje ?? "Revisa la lista para continuar.";
    }
    return null;
  };

  // ------------------------------------------------------------------ paso 1
  const vigente = trabajador?.vigencia.vigente ?? false;
  const faltaAlmacen = operaTodos && !borrador.almacenId;

  const bandas = (
    <div className="flex flex-col gap-3">
      {retomado ? (
        <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border bg-muted p-3 text-sm">
          <span className="flex items-center gap-2">
            <InfoIcon aria-hidden="true" className="size-5 shrink-0 text-marino" />
            Retomaste una entrega que no terminaste.
          </span>
          <Boton variante="texto" onClick={() => setDescartando(true)}>
            <RotateCcwIcon aria-hidden="true" />
            Empezar de nuevo
          </Boton>
        </p>
      ) : null}
      {almacenCambio ? (
        <section role="alert" className="flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-6 shrink-0 text-semaforo-amarillo" />
            <span>
              Te cambiaron de almacén. <span className="font-semibold">{almacenCambio.mensaje}</span>
            </span>
          </p>
          <p className="text-base">Tu captura sigue aquí; no se perdió nada.</p>
          <div className="flex flex-wrap gap-2">
            {almacenCambio.almacen ? (
              <Boton variante="normal" onClick={() => void continuarEnAlmacenActual()}>
                Continuar en {almacenCambio.almacen.nombre}
              </Boton>
            ) : (
              <p className="text-base font-semibold">Pide que te asignen un almacén para continuar.</p>
            )}
            <Boton variante="contorno" onClick={() => setDescartando(true)}>
              Descartar la captura
            </Boton>
          </div>
        </section>
      ) : null}
      {avisoCambio ? (
        <p role="alert" className="flex items-start gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-semibold">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-rojo" />
          {avisoCambio}
        </p>
      ) : null}
    </div>
  );

  const atrasDePaso = () => {
    if (enviando) return;
    if (borrador.paso === "trabajador") void navegar("/");
    else if (borrador.paso === "articulos") irA("trabajador");
    else irA("articulos");
  };
  usarAtrasDePasos(borrador.paso === "resultado" ? null : atrasDePaso);

  const encabezado = (
    <div className="flex flex-col gap-3">
      {borrador.paso !== "resultado" ? <BotonAtrasPaso alVolver={atrasDePaso} deshabilitado={enviando} /> : null}
      {borrador.paso === "resultado" ? (
        <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase" aria-live="polite">
          Entrega terminada
        </p>
      ) : (
        <IndicadorPasos actual={NUMERO_PASO[borrador.paso]} total={3} nombre={NOMBRE_PASO[borrador.paso]} />
      )}
    </div>
  );

  const selector = operaTodos ? (
    <SelectorAlmacen valor={borrador.almacenId} alCambiar={elegirAlmacen} deshabilitado={borrador.renglones.length > 0 && borrador.paso !== "trabajador"} />
  ) : almacenNombre ? (
    <p className="text-sm text-muted-foreground">
      Almacén: <span className="font-semibold text-foreground">{almacenNombre}</span>
    </p>
  ) : null;

  let contenido: React.ReactNode;
  let accion: React.ReactNode = null;

  if (borrador.paso === "trabajador") {
    const razon = !trabajador
      ? "Identifica al trabajador para continuar."
      : !vigente
        ? `No se puede entregar: ${(trabajador.vigencia.motivo ?? "el trabajador no está vigente").replace(/\.+$/, "")}.`
        : faltaAlmacen
          ? "Elige el almacén que operas."
          : null;
    contenido = (
      <div className="flex flex-col gap-4">
        {selector}
        <PasoTrabajador
          trabajador={borrador.trabajador}
          alIdentificar={(f) =>
            actualizar((b) => ({ ...b, trabajador: f, autorizacion: b.trabajador?.id === f.id ? b.autorizacion : null }))
          }
        />
      </div>
    );
    accion = (
      <AccionPrincipal nota={razon}>
        <Boton variante="principal" disabled={razon !== null} onClick={() => irA("articulos")}>
          Continuar
        </Boton>
        {borrador.trabajador ? (
          <Boton variante="texto" onClick={() => actualizar((b) => ({ ...b, trabajador: null, autorizacion: null }))}>
            <UserRoundIcon aria-hidden="true" />
            No es esta persona
          </Boton>
        ) : null}
      </AccionPrincipal>
    );
  } else if (borrador.paso === "articulos") {
    const razon = razonParaNoContinuar();
    const claseSinEvaluar = "rounded-2xl border border-dashed bg-muted p-3 text-sm";
    contenido = (
      <div className="flex flex-col gap-4">
        {selector}
        {bandas}
        {trabajador ? <FichaTrabajador trabajador={trabajador} variante="reducida" /> : null}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
          <div className="order-2 flex min-w-0 flex-col gap-4 md:order-1">
            {errorEvaluacion && errorEvaluacion.codigo !== "ALMACEN_CAMBIO" ? (
              <section role="alert" className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
                <p className="flex items-start gap-2 text-base font-semibold">
                  {errorEvaluacion.sinConexion ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
                  {errorEvaluacion.sinConexion ? "Sin conexión. Tu captura está guardada en este dispositivo." : errorEvaluacion.message}
                </p>
                <Boton variante="secundario" className="self-start" onClick={ev.reintentar}>
                  Reintentar
                </Boton>
              </section>
            ) : null}

            {evaluacion?.motivos.length ? (
              <ul className="flex flex-col gap-1 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
                {evaluacion.motivos.map((m, i) => (
                  <li key={`${m.regla}-${i}`} className="text-base">
                    <span className="sr-only">{TEXTO_NIVEL[m.nivel]}: </span>
                    {m.mensaje}
                  </li>
                ))}
              </ul>
            ) : null}

            {autorizacion ? (
              <BandaAutorizacion autorizacion={autorizacion} alQuitarRenglones={quitarRenglonesDeAutorizacion} deshabilitado={enviando} />
            ) : null}
            {evaluacion?.autorizacion_error && autorizacion?.estado === "APROBADA" ? (
              <p role="alert" className="rounded-2xl border border-semaforo-naranja bg-semaforo-naranja/10 p-3 text-sm font-semibold">
                {evaluacion.autorizacion_error}
              </p>
            ) : null}

            <ListaRenglones
              key={String(inicial.retomado && !evaluacion)}
              renglones={evaluados}
              claveDe={(r) => claveDeCodigo(r.codigo)}
              anunciarAgregados={true}
              onQuitar={quitar}
              onCantidad={cambiarCantidad}
              onPedirAutorizacion={() => setPidiendoAutorizacion(true)}
              onInspeccionar={puede("piezas.inspeccionar") ? (r) => r.pieza?.id && navegar(`/piezas/${r.pieza.id}`) : undefined}
              estadoAutorizacion={(r) =>
                r.autorizado
                  ? "autorizado"
                  : autorizacionPendiente && autorizacion?.codigos.some((c) => claveDeCodigo(c) === claveDeCodigo(r.codigo))
                    ? "en_espera"
                    : null
              }
              notas={notas}
              deshabilitado={enviando}
              vacio={
                sinEvaluar.length === 0 ? (
                  <p className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                    Todavía no hay artículos. Escanea el primero o escribe su código.
                  </p>
                ) : null
              }
            />
            {sinEvaluar.length > 0 ? (
              <ul aria-label="Artículos por revisar" className="flex flex-col gap-2">
                {sinEvaluar.map((b) => (
                  <li key={b.codigo} className={claseSinEvaluar}>
                    <Cargando variante="en-linea" texto={`Revisando ${b.codigo}…`} className="justify-start p-0" />
                  </li>
                ))}
              </ul>
            ) : null}

            {porConfirmar === undefined && evaluados.some((r) => r.requiere_confirmacion && borrador.cantidadesConfirmadas[claveDeCodigo(r.codigo)] !== r.cantidad) ? (
              <p className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">
                <span>Hay una cantidad más alta de lo normal sin confirmar.</span>
                <Boton
                  variante="secundario"
                  onClick={() => setDescartadasCantidad(new Set())}
                >
                  Revisar cantidad
                </Boton>
              </p>
            ) : null}
          </div>

          <div className="order-1 flex flex-col gap-3 md:sticky md:top-4 md:order-2">
            <Escaner
              activo={!pidiendoAutorizacion && !eligiendoDotacion && !porConfirmar && !resultadosBusqueda && !descartando && !enviando}
              sonidoAlLeer={false}
              onCodigo={(codigo, origen) => void alLeerArticulo(codigo, origen)}
              onRepetido={() => reproducir("aviso")}
              etiquetaCampo="Escribir código o nombre"
              placeholderCampo="Código, serie o nombre"
            />
            {buscandoArticulo ? <Cargando variante="en-linea" texto="Buscando…" /> : null}
            {dotacion ? (
              <>
                {faltanDotacion > 0 ? (
                  <p className="rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm font-semibold" aria-live="polite">
                    Te faltan {faltanDotacion} {faltanDotacion === 1 ? "artículo" : "artículos"} de la dotación.
                  </p>
                ) : null}
                <Boton variante="contorno" onClick={() => setEligiendoDotacion(true)}>
                  <ClipboardListIcon aria-hidden="true" />
                  Dotación sugerida
                </Boton>
              </>
            ) : null}
          </div>
        </div>

        {dotacion ? (
          <HojaDotacion
            abierta={eligiendoDotacion}
            alCambiar={setEligiendoDotacion}
            dotacion={dotacion}
            modo="seleccion"
            yaEnLista={yaEnLista}
            alAgregar={agregarDeDotacion}
          />
        ) : null}

        {porConfirmar ? (
        <ConfirmarCantidad
          abierta={!pidiendoAutorizacion && !eligiendoDotacion}
          alCambiar={() => {}}
          cantidad={porConfirmar.cantidad}
          articulo={(porConfirmar.articulo?.nombre ?? porConfirmar.codigo).toLocaleLowerCase("es-MX")}
          unidad={unidadEnPlural(porConfirmar.articulo?.unidad)}
          alConfirmar={() => {
            const clave = claveDeCodigo(porConfirmar.codigo);
            actualizar((b) => ({ ...b, cantidadesConfirmadas: { ...b.cantidadesConfirmadas, [clave]: porConfirmar.cantidad } }));
          }}
          alCorregir={() => {
            const marca = `${claveDeCodigo(porConfirmar.codigo)}:${porConfirmar.cantidad}`;
            setDescartadasCantidad((previas) => new Set([...previas, marca]));
          }}
        />
        ) : null}

        {borrador.trabajador ? (
          <HojaAutorizacion
            abierta={pidiendoAutorizacion}
            alCambiar={setPidiendoAutorizacion}
            trabajadorId={borrador.trabajador.id}
            almacenId={borrador.almacenId}
            renglones={naranjasAutorizables}
            alSolicitar={(nueva: AutorizacionBorrador) => {
              actualizar((b) => ({ ...b, autorizacion: nueva }));
              if (nueva.estado === "APROBADA") {
                reproducir("ok");
                aviso({ titulo: "Autorizado", tipo: "exito" });
              } else if (nueva.estado === "PENDIENTE") {
                aviso({ titulo: "Solicitud enviada", descripcion: "Esperando al supervisor.", tipo: "info" });
              }
            }}
          />
        ) : null}
      </div>
    );
    accion = (
      <AccionPrincipal nota={razon}>
        <Boton variante="principal" disabled={razon !== null} onClick={() => irA("firma")}>
          Continuar
        </Boton>
      </AccionPrincipal>
    );
  } else if (borrador.paso === "firma") {
    const listo = Boolean(borrador.firma) && ev.actual && Boolean(evaluacion?.puede_confirmar) && !faltaObservacion;
    const reintento = errorEnvio?.tipo === "conexion";
    const razon = !borrador.firma
      ? "Pide al trabajador que firme para confirmar."
      : !ev.actual || ev.evaluando
        ? "Revisando la lista…"
        : !evaluacion?.puede_confirmar
          ? "La lista cambió. Regresa para revisarla."
          : faltaObservacion
            ? "Anota por qué se entrega esto para confirmar."
            : null;
    contenido = (
      <div className="flex flex-col gap-4">
        {trabajador ? <FichaTrabajador trabajador={trabajador} variante="reducida" /> : null}
        {errorEnvio ? (
          <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
            <p className="flex items-start gap-2 text-base font-semibold">
              {errorEnvio.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
              {errorEnvio.mensaje}
            </p>
            {errorEnvio.tipo === "conexion" ? <p className="text-base">Toca “Reintentar” cuando haya conexión o el sistema responda. No se guardará dos veces.</p> : null}
          </section>
        ) : null}
        {pideObservacion ? (
          <ObservacionEntrega
            valor={borrador.observacion ?? ""}
            alCambiar={cambiarObservacion}
            motivos={motivosDeObservacion}
            error={errorObservacion}
            deshabilitado={enviando}
          />
        ) : null}
        <PasoFirma
          observacion={pideObservacion ? borrador.observacion : undefined}
          renglones={evaluados}
          firma={borrador.firma}
          alCambiarFirma={(f: FirmaCapturada | null) => actualizar((b) => ({ ...b, firma: f }))}
          deshabilitado={enviando}
        />
      </div>
    );
    accion = (
      <AccionPrincipal nota={razon}>
        <Boton variante="principal" cargando={enviando} disabled={!listo && !reintento} onClick={() => void confirmar()}>
          {reintento ? "Reintentar" : "Confirmar entrega"}
        </Boton>
      </AccionPrincipal>
    );
  } else {
    contenido = borrador.resultado ? (
      <ResultadoEntrega vale={borrador.resultado} firmaImagen={borrador.firma?.imagen} />
    ) : (
      <Cargando variante="en-linea" />
    );
    accion = (
      <AccionPrincipal>
        <Boton variante="principal" onClick={empezarDeNuevo}>
          Nueva entrega
        </Boton>
      </AccionPrincipal>
    );
  }

  return (
    <Pantalla titulo="Entregar">
      {encabezado}
      {!enLinea && borrador.paso !== "resultado" ? (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <WifiOffIcon aria-hidden="true" className="size-4" />
          Lo que captures se guarda en este dispositivo hasta que vuelva la conexión.
        </p>
      ) : null}
      {contenido}
      {accion}

      <Confirmacion
        abierta={bloqueo.state === "blocked"}
        alCambiar={(abierta) => {
          if (!abierta && bloqueo.state === "blocked") bloqueo.reset();
        }}
        mensaje="¿Salir sin terminar la entrega?"
        detalle="Lo que capturaste no se guardará."
        etiquetaConfirmar="Sí, salir"
        etiquetaCancelar="Seguir aquí"
        peligro
        alConfirmar={() => {
          borrarBorrador();
          if (bloqueo.state === "blocked") bloqueo.proceed();
        }}
      />
      <Confirmacion
        abierta={descartando}
        alCambiar={setDescartando}
        mensaje="¿Empezar una entrega nueva?"
        detalle="Se descartará lo que capturaste hasta ahora."
        etiquetaConfirmar="Sí, empezar de nuevo"
        etiquetaCancelar="Seguir con esta"
        peligro
        alConfirmar={() => {
          setDescartando(false);
          empezarDeNuevo();
        }}
      />
      {resultadosBusqueda ? (
        <HojaBusquedaArticulos
          abierta
          alCambiar={(abierta) => {
            if (!abierta) setResultadosBusqueda(null);
          }}
          texto={resultadosBusqueda.texto}
          coincidencias={resultadosBusqueda.items}
          alElegir={(c) => {
            setResultadosBusqueda(null);
            agregarCodigo(c.codigo);
          }}
        />
      ) : null}
    </Pantalla>
  );
}
