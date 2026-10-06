import { CircleAlertIcon, InfoIcon, RotateCcwIcon, ScanLineIcon, WifiOffIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker, useNavigate, useSearchParams } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError, type ErrorApi } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import {
  borrarBorradorDevolucion,
  guardarBorradorDevolucion,
  leerBorradorDevolucion,
  nuevoBorradorDevolucion,
  nuevoRenglonDevolucion,
  tieneCapturaDevolucion,
  type BorradorDevolucion,
  type RenglonDevolucionBorrador,
  type TrabajadorDevolucion,
} from "~/componentes/devolucion/borrador";
import { reducirFoto } from "~/componentes/devolucion/foto";
import { HojaCantidad } from "~/componentes/devolucion/hoja-cantidad";
import { PanelResguardo } from "~/componentes/devolucion/panel-resguardo";
import { RenglonDevolucion } from "~/componentes/devolucion/renglon-devolucion";
import { Escaner, type OrigenLectura } from "~/componentes/dominio/escaner";
import { HojaObservacion } from "~/componentes/dominio/hoja-observacion";
import { TEXTO_NIVEL } from "~/componentes/dominio/renglon-semaforo";
import { reproducir } from "~/componentes/dominio/sonido";
import type { Condicion, RenglonEvaluado } from "~/componentes/dominio/tipos";
import { claveDeCodigo } from "~/componentes/entrega/borrador";
import { HojaBusquedaArticulos, type CoincidenciaArticulo } from "~/componentes/entrega/hoja-busqueda-articulos";
import { ResultadoEntrega } from "~/componentes/entrega/resultado-entrega";
import { SelectorAlmacen } from "~/componentes/entrega/selector-almacen";
import type { AlmacenResumen, EvaluacionApi, ValeConfirmadoApi } from "~/componentes/entrega/tipos";
import { useEvaluacion, type CuerpoEvaluar } from "~/componentes/entrega/use-evaluacion";
import { BotonAtrasPaso, usarAtrasDePasos } from "~/componentes/navegacion/atras";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import type { Ficha, Pendiente } from "~/componentes/personas/tipos";
import { aviso, cerrarAviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "devoluciones.crear" };

// El almacén que opera quien tiene `almacenes.todos` se recuerda con la misma clave que usa la entrega.
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

interface EscaneoApi {
  tipo: "TRABAJADOR" | "ARTICULO" | "PIEZA" | "VALE" | "DESCONOCIDO";
  id: string | null;
  resumen?: { nombre?: string; control?: string } | null;
}
interface BusquedaApi {
  articulos: { elementos: { codigo: string; nombre: string; marca: string | null; control: string }[] };
  piezas: { elementos: { codigo: string; articulo: string; numero_serie: string | null; ubicacion: string | null }[] };
  trabajadores: { elementos: { numero_empleado: string; nombre: string; estado_texto: string }[] };
}

type ErrorEnvio = { tipo: "conexion" | "otro"; mensaje: string } | null;

const RESPUESTAS_DANO = ["Se rompió", "Ya no funciona", "Golpe o caída", "Costuras o cintas dañadas"];

function aTrabajador(ficha: Ficha): TrabajadorDevolucion {
  return {
    id: ficha.id,
    numero_empleado: ficha.numero_empleado,
    nombre: ficha.nombre,
    puesto: ficha.puesto,
    area_obra: ficha.area_obra,
  };
}

/** Une los renglones que el servidor también uniría: mismo código y misma condición (por cantidad). */
function unirIguales(renglones: RenglonDevolucionBorrador[]): RenglonDevolucionBorrador[] {
  const salida: RenglonDevolucionBorrador[] = [];
  for (const r of renglones) {
    const igual = salida.find((x) => claveDeCodigo(x.codigo) === claveDeCodigo(r.codigo) && x.condicion === r.condicion);
    if (!igual) {
      salida.push(r);
      continue;
    }
    igual.cantidad += r.cantidad;
    igual.observacion = [igual.observacion, r.observacion].filter(Boolean).join("; ") || undefined;
    igual.foto = igual.foto ?? r.foto;
  }
  return salida;
}

export default function Devolver() {
  const { sesion, puede, recargar } = useSesionActiva();
  const navegar = useNavigate();
  const [parametros, setParametros] = useSearchParams();
  const enLinea = useEnLinea();
  const usuarioId = sesion.usuario.id;
  const operaTodos = puede("almacenes.todos");

  // ------------------------------------------------------------------ borrador (persistente)
  const [inicial] = useState(() => {
    const guardado = leerBorradorDevolucion(usuarioId);
    const almacen = sesion.almacen?.id ?? (operaTodos ? leerAlmacenRecordado() : null);
    const base = guardado ?? nuevoBorradorDevolucion(usuarioId, almacen);
    return { borrador: base, retomado: Boolean(guardado) && !base.resultado && base.renglones.length > 0 };
  });
  const [borrador, setBorrador] = useState<BorradorDevolucion>(inicial.borrador);
  const [retomado, setRetomado] = useState(inicial.retomado);
  const borradorRef = useRef(borrador);
  borradorRef.current = borrador;

  useEffect(() => {
    guardarBorradorDevolucion(borrador);
  }, [borrador]);

  // Al salir de la pantalla ya con el vale emitido, el borrador no se conserva.
  useEffect(
    () => () => {
      if (borradorRef.current.resultado) borrarBorradorDevolucion();
    },
    [],
  );

  const actualizar = useCallback((cambio: (b: BorradorDevolucion) => BorradorDevolucion) => setBorrador(cambio), []);

  // ------------------------------------------------------------------ estado de pantalla
  const [notas, setNotas] = useState<Record<string, string>>({});
  const [avisoCambio, setAvisoCambio] = useState<string | null>(null);
  const [almacenCambio, setAlmacenCambio] = useState<{ mensaje: string; almacen: AlmacenResumen | null } | null>(null);
  const [errorEnvio, setErrorEnvio] = useState<ErrorEnvio>(null);
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const [observando, setObservando] = useState<string | null>(null);
  const [descartando, setDescartando] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [mensajeLectura, setMensajeLectura] = useState<string | null>(null);
  const [resultadosBusqueda, setResultadosBusqueda] = useState<{ texto: string; items: CoincidenciaArticulo[] } | null>(null);
  const [cantidadDe, setCantidadDe] = useState<Pendiente | null>(null);
  const sonidoPendiente = useRef<Set<string>>(new Set());
  const anunciados = useRef<Set<string>>(new Set(inicial.borrador.renglones.map((r) => r.uid)));

  // ------------------------------------------------------------------ resguardo del trabajador
  const [fichaTrabajador, setFichaTrabajador] = useState<Ficha | null>(null);
  const [cargandoFicha, setCargandoFicha] = useState(false);
  const [errorFicha, setErrorFicha] = useState<unknown>(null);
  const [intentoFicha, setIntentoFicha] = useState(0);
  const trabajadorId = borrador.trabajador?.id ?? null;

  useEffect(() => {
    if (!trabajadorId) {
      setFichaTrabajador(null);
      return;
    }
    if (fichaTrabajador?.id === trabajadorId && intentoFicha === 0) return;
    const control = new AbortController();
    setCargandoFicha(true);
    setErrorFicha(null);
    apiGet<Ficha>(`/trabajadores/${trabajadorId}`, undefined, control.signal)
      .then((f) => {
        setFichaTrabajador(f);
        setCargandoFicha(false);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted || (causa instanceof DOMException && causa.name === "AbortError")) return;
        setErrorFicha(causa);
        setCargandoFicha(false);
      });
    return () => control.abort();
    // `fichaTrabajador` solo se lee para no pedirla dos veces al identificar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trabajadorId, intentoFicha]);

  // ------------------------------------------------------------------ evaluación
  const cuerpo = useMemo<CuerpoEvaluar | null>(() => {
    if (borrador.resultado || borrador.renglones.length === 0) return null;
    if (operaTodos && !borrador.almacenId) return null;
    return {
      tipo: "DEVOLUCION",
      almacen_id: borrador.almacenId,
      trabajador_id: borrador.trabajador?.id,
      id_cliente: borrador.idCliente,
      renglones: borrador.renglones.map((r) => ({
        codigo: r.codigo,
        cantidad: r.cantidad,
        condicion: r.condicion ?? undefined,
        observacion: r.observacion || undefined,
      })),
    };
  }, [borrador.resultado, borrador.renglones, borrador.almacenId, borrador.trabajador, borrador.idCliente, operaTodos]);

  const ev = useEvaluacion(cuerpo);
  const evaluacion: EvaluacionApi | null = cuerpo ? ev.evaluacion : null;

  /** A cada renglón de la captura, lo que el servidor evaluó para él (en el mismo orden por código). */
  const evaluadoDe = useMemo(() => {
    const porCodigo = new Map<string, RenglonEvaluado[]>();
    for (const r of evaluacion?.renglones ?? []) {
      const clave = claveDeCodigo(r.codigo);
      porCodigo.set(clave, [...(porCodigo.get(clave) ?? []), r]);
    }
    const usados = new Map<string, number>();
    const mapa = new Map<string, RenglonEvaluado>();
    for (const l of borrador.renglones) {
      const clave = claveDeCodigo(l.codigo);
      const n = usados.get(clave) ?? 0;
      const r = porCodigo.get(clave)?.[n];
      if (r) {
        mapa.set(l.uid, r);
        usados.set(clave, n + 1);
      }
    }
    return mapa;
  }, [evaluacion, borrador.renglones]);
  const evaluadoDeRef = useRef(evaluadoDe);
  evaluadoDeRef.current = evaluadoDe;

  const sinEvaluar = borrador.renglones.filter((l) => !evaluadoDe.has(l.uid));

  // El servidor junta lo repetido: si un renglón ya no aparece en la evaluación, se quita.
  useEffect(() => {
    if (!ev.actual || !evaluacion || sinEvaluar.length === 0) return;
    const sobran = new Set(sinEvaluar.map((l) => l.uid));
    actualizar((b) => ({ ...b, renglones: b.renglones.filter((r) => !sobran.has(r.uid)) }));
  }, [ev.actual, evaluacion, sinEvaluar, actualizar]);

  // Sonido y aviso "Se agregó… Deshacer" de cada lectura nueva, cuando el servidor ya la evaluó.
  useEffect(() => {
    if (!ev.actual) return;
    for (const l of borrador.renglones) {
      const r = evaluadoDe.get(l.uid);
      if (!r) continue;
      if (sonidoPendiente.current.has(l.uid)) {
        sonidoPendiente.current.delete(l.uid);
        reproducir(r.nivel === "ROJO" ? "bloqueo" : r.nivel === "VERDE" ? "ok" : "aviso");
      }
      if (!anunciados.current.has(l.uid)) {
        anunciados.current.add(l.uid);
        const uid = l.uid;
        // Un código que el servidor no reconoce (rojo) no se "agregó": la fila roja ya lo dice.
        if (r.nivel === "ROJO") continue;
        aviso({
          titulo: `Se agregó ${r.articulo?.nombre ?? l.codigo}`,
          tipo: "info",
          duracionMs: 5000,
          accion: { etiqueta: "Deshacer", alHacerClic: () => actualizar((b) => ({ ...b, renglones: b.renglones.filter((x) => x.uid !== uid) })) },
        });
      }
    }
  }, [ev.actual, evaluadoDe, borrador.renglones, actualizar]);

  // Los avisos "Se agregó… Deshacer" no sobreviven al vale terminado ni a salir de la pantalla.
  const terminada = Boolean(borrador.resultado);
  useEffect(() => {
    if (terminada) cerrarAviso();
  }, [terminada]);
  useEffect(() => () => cerrarAviso(), []);

  // Un error de almacén al evaluar se atiende igual que al confirmar.
  const errorEvaluacion: ErrorApi | null = cuerpo ? ev.error : null;
  useEffect(() => {
    if (errorEvaluacion?.codigo === "ALMACEN_CAMBIO") {
      const almacen = (errorEvaluacion.detalles?.almacen as AlmacenResumen | null | undefined) ?? null;
      setAlmacenCambio({ mensaje: errorEvaluacion.message, almacen });
    }
  }, [errorEvaluacion]);

  // ------------------------------------------------------------------ salir con captura
  const hayCaptura = tieneCapturaDevolucion(borrador);
  const bloqueo = useBlocker(hayCaptura);

  // ------------------------------------------------------------------ cambios del borrador
  const hayCantidades = () => [...evaluadoDeRef.current.values()].some((r) => r.articulo?.control === "CANTIDAD");

  const agregarCodigo = useCallback(
    (codigo: string) => {
      const limpio = codigo.trim();
      if (!limpio) return;
      const clave = claveDeCodigo(limpio);
      setNotas({});
      setAvisoCambio(null);
      const existente = borradorRef.current.renglones.find((r) => claveDeCodigo(r.codigo) === clave);
      if (existente) {
        // Una pieza o un código repetido se ignora (E-15), con sonido.
        reproducir("aviso");
        aviso({ titulo: "Ya está en la lista", descripcion: limpio, tipo: "aviso", duracionMs: 2500 });
        return;
      }
      const nuevo = nuevoRenglonDevolucion(limpio);
      sonidoPendiente.current.add(nuevo.uid);
      actualizar((b) => ({ ...b, renglones: [...b.renglones, nuevo] }));
    },
    [actualizar],
  );

  const agregarCantidad = useCallback(
    (codigo: string, cantidad: number, condicion: Condicion | null) => {
      setNotas({});
      setAvisoCambio(null);
      const nuevo = nuevoRenglonDevolucion(codigo, cantidad, condicion);
      sonidoPendiente.current.add(nuevo.uid);
      actualizar((b) => ({ ...b, renglones: unirIguales([...b.renglones.map((r) => ({ ...r })), nuevo]) }));
      if (condicion === "DANADO") setObservando(nuevo.uid);
    },
    [actualizar],
  );

  const identificarTrabajador = useCallback(
    async (id: string) => {
      const ficha = await apiGet<Ficha>(`/trabajadores/${id}`);
      const actual = borradorRef.current.trabajador;
      if (actual && actual.id !== ficha.id && hayCantidades()) {
        reproducir("aviso");
        aviso({
          titulo: "Termina primero esta devolución",
          descripcion: `Ya hay artículos de ${actual.nombre}. Una devolución por cantidad es de una sola persona.`,
          tipo: "aviso",
          duracionMs: 6000,
        });
        return;
      }
      setFichaTrabajador(ficha);
      reproducir("ok");
      actualizar((b) => ({ ...b, trabajador: aTrabajador(ficha) }));
    },
    [actualizar],
  );

  const alLeer = useCallback(
    async (codigo: string, origen: OrigenLectura) => {
      const limpio = codigo.trim();
      if (!limpio) return;
      setMensajeLectura(null);
      setBuscando(true);
      try {
        const escaneo = await apiGet<EscaneoApi>(`/escaneo/${encodeURIComponent(limpio)}`);
        if (escaneo.tipo === "TRABAJADOR" && escaneo.id) {
          await identificarTrabajador(escaneo.id);
          return;
        }
        if (escaneo.tipo === "ARTICULO" && escaneo.resumen?.control === "CANTIDAD") {
          const actual = borradorRef.current.trabajador;
          if (!actual) {
            reproducir("aviso");
            setMensajeLectura(`Para devolver ${escaneo.resumen.nombre ?? "este artículo"}, primero escanea la credencial del trabajador.`);
            return;
          }
          const pendiente = fichaTrabajador?.resguardo.find((p) => p.pieza_id === null && claveDeCodigo(p.codigo) === claveDeCodigo(limpio));
          if (pendiente) setCantidadDe(pendiente);
          else agregarCantidad(limpio, 1, null);
          return;
        }
        if (escaneo.tipo === "DESCONOCIDO" && origen === "teclado" && limpio.length >= 2) {
          // Etiqueta ilegible (V-14): se busca por número de serie, nombre o número de empleado.
          const b = await apiGet<BusquedaApi>("/busqueda", { q: limpio });
          const items: CoincidenciaArticulo[] = [
            ...b.piezas.elementos.map((p) => ({
              codigo: p.codigo,
              nombre: p.articulo,
              detalle: `${p.numero_serie ? `Serie ${p.numero_serie}` : `Pieza ${p.codigo}`}${p.ubicacion ? ` · ${p.ubicacion}` : ""}`,
            })),
            ...b.trabajadores.elementos.map((t) => ({
              codigo: t.numero_empleado,
              nombre: t.nombre,
              detalle: `Trabajador · N.º ${t.numero_empleado} · ${t.estado_texto}`,
            })),
            ...b.articulos.elementos
              .filter((a) => a.control === "CANTIDAD")
              .map((a) => ({
                codigo: a.codigo,
                nombre: a.nombre,
                detalle: [a.marca, a.codigo].filter(Boolean).join(" · "),
              })),
          ];
          if (items.length > 0) {
            setResultadosBusqueda({ texto: limpio, items });
            return;
          }
        }
        // Una pieza, un artículo por pieza o un código desconocido entran como renglón: el servidor
        // dice qué es (pieza en resguardo, "No es de la empresa", etc.).
        agregarCodigo(limpio);
      } catch (causa) {
        if (esErrorApi(causa) && causa.sinConexion) {
          // Sin conexión no se puede saber qué es: se guarda en el borrador y se revisa al volver.
          agregarCodigo(limpio);
          return;
        }
        reproducir("aviso");
        aviso({ titulo: "No pudimos leer el código", descripcion: mensajeDeError(causa), tipo: "error" });
      } finally {
        setBuscando(false);
      }
    },
    [agregarCodigo, agregarCantidad, identificarTrabajador, fichaTrabajador],
  );

  // El trabajador puede llegar por la dirección (desde el no adeudo): `/devolver?trabajador=…`.
  const trabajadorPedido = parametros.get("trabajador");
  useEffect(() => {
    if (!trabajadorPedido) return;
    const limpiar = () => {
      const copia = new URLSearchParams(parametros);
      copia.delete("trabajador");
      setParametros(copia, { replace: true });
    };
    // Si lo que quedó guardado es una devolución ya terminada, esta empieza de nuevo.
    if (borradorRef.current.resultado) {
      borrarBorradorDevolucion();
      anunciados.current = new Set();
      setBorrador(nuevoBorradorDevolucion(usuarioId, borradorRef.current.almacenId));
    }
    apiGet<Ficha>(`/trabajadores/${trabajadorPedido}`)
      .then((ficha) => {
        const b = borradorRef.current;
        if (b.trabajador && b.trabajador.id !== ficha.id && b.renglones.length > 0) {
          aviso({ titulo: "Ya tienes una devolución en curso", descripcion: "Termínala o empieza de nuevo para recibir a otra persona.", tipo: "aviso" });
          return;
        }
        setFichaTrabajador(ficha);
        actualizar((x) => ({ ...x, trabajador: aTrabajador(ficha) }));
      })
      .catch((causa: unknown) => aviso({ titulo: "No pudimos abrir al trabajador", descripcion: mensajeDeError(causa), tipo: "error" }))
      .finally(limpiar);
    // Solo al abrir con ese parámetro.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trabajadorPedido]);

  const quitar = (uid: string) => {
    setNotas({});
    actualizar((b) => ({ ...b, renglones: b.renglones.filter((r) => r.uid !== uid) }));
  };

  const cambiarCantidad = (uid: string, cantidad: number) => {
    setNotas({});
    actualizar((b) => ({ ...b, renglones: b.renglones.map((r) => (r.uid === uid ? { ...r, cantidad } : r)) }));
  };

  const cambiarCondicion = (uid: string, condicion: Condicion) => {
    setNotas({});
    sonidoPendiente.current.add(uid);
    actualizar((b) => ({
      ...b,
      renglones: unirIguales(
        b.renglones.map((r) => {
          if (r.uid !== uid) return { ...r };
          // La foto y la observación son del daño: al dejar de ser Dañado se quitan.
          return condicion === "DANADO" ? { ...r, condicion } : { ...r, condicion, foto: undefined, observacion: undefined };
        }),
      ),
    }));
    if (condicion === "DANADO") setObservando(uid);
  };

  const guardarObservacion = (uid: string, texto: string) => {
    actualizar((b) => ({ ...b, renglones: b.renglones.map((r) => (r.uid === uid ? { ...r, observacion: texto } : r)) }));
  };

  const cambiarFoto = async (uid: string, archivo: File | null) => {
    const foto = archivo ? await reducirFoto(archivo) : undefined;
    actualizar((b) => ({ ...b, renglones: b.renglones.map((r) => (r.uid === uid ? { ...r, foto } : r)) }));
  };

  const elegirAlmacen = (almacen: AlmacenResumen) => {
    recordarAlmacen(almacen.id);
    actualizar((b) => ({ ...b, almacenId: almacen.id }));
  };

  const cambiarTrabajador = () => {
    if (hayCantidades()) {
      aviso({
        titulo: "Termina primero esta devolución",
        descripcion: "Ya hay artículos por cantidad de esta persona. Quítalos si quieres recibir a otra.",
        tipo: "aviso",
        duracionMs: 6000,
      });
      return;
    }
    setFichaTrabajador(null);
    actualizar((b) => ({ ...b, trabajador: null }));
  };

  const empezarDeNuevo = () => {
    borrarBorradorDevolucion();
    sonidoPendiente.current = new Set();
    anunciados.current = new Set();
    setNotas({});
    setAvisoCambio(null);
    setAlmacenCambio(null);
    setErrorEnvio(null);
    setRetomado(false);
    setMensajeLectura(null);
    setFichaTrabajador(null);
    setBorrador(nuevoBorradorDevolucion(usuarioId, borradorRef.current.almacenId));
  };

  // ------------------------------------------------------------------ confirmar
  const confirmar = async () => {
    if (enviandoRef.current) return;
    const b = borradorRef.current;
    if (b.renglones.length === 0) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    setAvisoCambio(null);
    try {
      // F-08: el almacenista firma con su sesión; no se pide firma al trabajador.
      const vale = await apiPost<ValeConfirmadoApi>("/vales", {
        tipo: "DEVOLUCION",
        almacen_id: b.almacenId,
        trabajador_id: b.trabajador?.id,
        id_cliente: b.idCliente,
        renglones: b.renglones.map((r) => ({
          codigo: r.codigo,
          cantidad: r.cantidad,
          condicion: r.condicion ?? undefined,
          observacion: r.observacion || undefined,
          foto: r.condicion === "DANADO" ? r.foto : undefined,
        })),
      });
      reproducir("ok");
      actualizar((x) => ({ ...x, resultado: vale, renglones: x.renglones.map((r) => ({ ...r, foto: undefined })) }));
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
      setErrorEnvio({ tipo: "conexion", mensaje: "Sin conexión. La devolución está guardada en este dispositivo." });
      return;
    }
    if (causa.reintentable) {
      // El sistema estaba ocupado: lo capturado sigue aquí y reintentar no duplica el vale.
      setErrorEnvio({ tipo: "conexion", mensaje: causa.message });
      return;
    }
    if (causa.codigo === "VALE_CAMBIO" && causa.detalles) {
      const nueva = causa.detalles as unknown as EvaluacionApi;
      const marcas: Record<string, string> = {};
      const porCodigo = new Map<string, number>();
      for (const l of borradorRef.current.renglones) {
        const clave = claveDeCodigo(l.codigo);
        const n = porCodigo.get(clave) ?? 0;
        porCodigo.set(clave, n + 1);
        const r = nueva.renglones.filter((x) => claveDeCodigo(x.codigo) === clave)[n];
        if (r && r.nivel === "ROJO") marcas[l.uid] = "Esto cambió mientras capturabas. Revísalo.";
      }
      ev.adoptar(nueva);
      setNotas(marcas);
      setAvisoCambio(causa.message);
      return;
    }
    if (causa.codigo === "ALMACEN_CAMBIO") {
      const almacen = (causa.detalles?.almacen as AlmacenResumen | null | undefined) ?? null;
      setAlmacenCambio({ mensaje: causa.message, almacen });
      return;
    }
    setErrorEnvio({ tipo: "otro", mensaje: causa.message });
  };

  const continuarEnAlmacenActual = async () => {
    const nuevo = almacenCambio?.almacen;
    if (!nuevo) return;
    await recargar();
    setAlmacenCambio(null);
    actualizar((b) => ({ ...b, almacenId: nuevo.id }));
  };

  // ------------------------------------------------------------------ lo que se pinta
  const evaluados = borrador.renglones.flatMap((l) => {
    const r = evaluadoDe.get(l.uid);
    return r ? [{ local: l, evaluado: r }] : [];
  });
  const almacenNombre = evaluacion?.almacen.nombre ?? sesion.almacen?.nombre ?? null;
  const faltaAlmacen = operaTodos && !borrador.almacenId;

  const razonParaNoConfirmar = (): string | null => {
    if (borrador.renglones.length === 0) return "Escanea una pieza o la credencial del trabajador para empezar.";
    if (faltaAlmacen) return "Elige el almacén que operas.";
    if (errorEvaluacion && !ev.actual) {
      return errorEvaluacion.sinConexion ? "Sin conexión: no podemos revisar la lista todavía." : "No pudimos revisar la lista.";
    }
    if (!evaluacion || !ev.actual || ev.evaluando || sinEvaluar.length > 0) return "Revisando la lista…";
    const tiene = (regla: string) => (r: RenglonEvaluado) => r.motivos.some((m) => m.regla === regla && m.nivel === "ROJO");
    if (evaluados.some((x) => tiene("V-04")(x.evaluado))) return "Elige cómo regresa cada artículo.";
    const sinNota = evaluados.find((x) => tiene("V-05")(x.evaluado));
    if (sinNota) return `Anota qué le pasó a ${sinNota.evaluado.articulo?.nombre ?? sinNota.local.codigo}.`;
    const rojos = evaluados.filter((x) => x.evaluado.nivel === "ROJO").length;
    if (rojos > 0) return `Quita ${rojos === 1 ? "lo que está en rojo" : `los ${rojos} renglones en rojo`} para continuar.`;
    if (!evaluacion.puede_confirmar) return evaluacion.motivos[0]?.mensaje ?? "Revisa la lista para continuar.";
    return null;
  };

  const atrasDePaso = () => {
    if (!enviando) void navegar("/");
  };
  usarAtrasDePasos(borrador.resultado ? null : atrasDePaso);

  const encabezado = (
    <div className="flex flex-col gap-3">
      {!borrador.resultado ? <BotonAtrasPaso alVolver={atrasDePaso} deshabilitado={enviando} /> : null}
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase" aria-live="polite">
        {borrador.resultado ? "Devolución terminada" : "Recibe lo que regresa"}
      </p>
    </div>
  );

  const bandas = (
    <div className="flex flex-col gap-3">
      {retomado ? (
        <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border bg-muted p-3 text-sm">
          <span className="flex items-center gap-2">
            <InfoIcon aria-hidden="true" className="size-5 shrink-0 text-marino" />
            Retomaste una devolución que no terminaste.
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

  const selector = operaTodos ? (
    <SelectorAlmacen valor={borrador.almacenId} alCambiar={elegirAlmacen} deshabilitado={borrador.renglones.length > 0} />
  ) : almacenNombre ? (
    <p className="text-sm text-muted-foreground">
      Almacén que recibe: <span className="font-semibold text-foreground">{almacenNombre}</span>
    </p>
  ) : null;

  let contenido: React.ReactNode;
  let accion: React.ReactNode;

  if (borrador.resultado) {
    contenido = <ResultadoEntrega vale={borrador.resultado} titulo="Devolución guardada" nombreVale="Vale de devolución" />;
    accion = (
      <AccionPrincipal>
        <Boton variante="principal" onClick={empezarDeNuevo}>
          Nueva devolución
        </Boton>
      </AccionPrincipal>
    );
  } else {
    const campoDeObservacion = observando ? borrador.renglones.find((r) => r.uid === observando) : undefined;
    const evaluadoObservado = campoDeObservacion ? evaluadoDe.get(campoDeObservacion.uid) : undefined;
    const razon = razonParaNoConfirmar();
    const reintento = errorEnvio?.tipo === "conexion";
    const listo = razon === null;
    const motivosVale = evaluacion?.motivos ?? [];
    const valeRojo = motivosVale.some((m) => m.nivel === "ROJO");

    const maximoDe = (l: RenglonDevolucionBorrador, r: RenglonEvaluado | undefined) => {
      if (!r || r.disponible === null) return undefined;
      const otros = borrador.renglones.filter((x) => x.uid !== l.uid && claveDeCodigo(x.codigo) === claveDeCodigo(l.codigo)).reduce((s, x) => s + x.cantidad, 0);
      return Math.max(1, r.disponible - otros);
    };
    const agregadoDe = (p: Pendiente) =>
      borrador.renglones.filter((r) => claveDeCodigo(r.codigo) === claveDeCodigo(p.codigo)).reduce((s, r) => s + r.cantidad, 0);
    const codigosAgregados = new Set(borrador.renglones.map((r) => claveDeCodigo(r.codigo)));

    contenido = (
      <div className="flex flex-col gap-4">
        {selector}
        {bandas}
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

            {errorEnvio ? (
              <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
                <p className="flex items-start gap-2 text-base font-semibold">
                  {errorEnvio.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
                  {errorEnvio.mensaje}
                </p>
                {errorEnvio.tipo === "conexion" ? <p className="text-base">Toca “Reintentar” cuando haya conexión o el sistema responda. No se guardará dos veces.</p> : null}
              </section>
            ) : null}

            {borrador.trabajador ? (
              <PanelResguardo
                trabajador={borrador.trabajador}
                ficha={fichaTrabajador}
                cargando={cargandoFicha}
                error={errorFicha}
                alReintentar={() => setIntentoFicha((n) => n + 1)}
                agregadoDe={agregadoDe}
                codigosAgregados={codigosAgregados}
                alElegirPieza={(p) => agregarCodigo(p.codigo)}
                alElegirCantidad={setCantidadDe}
                alCambiarTrabajador={cambiarTrabajador}
                deshabilitado={enviando}
              />
            ) : null}

            {motivosVale.length > 0 ? (
              <ul
                className={
                  valeRojo
                    ? "flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3"
                    : "flex flex-col gap-1 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3"
                }
              >
                {motivosVale.map((m, i) => (
                  <li key={`${m.regla}-${i}`} className="text-base">
                    <span className="sr-only">{m.nivel === "ROJO" ? "No se puede recibir" : TEXTO_NIVEL[m.nivel]}: </span>
                    {m.mensaje} <span className="text-xs font-medium whitespace-nowrap text-muted-foreground">({m.regla})</span>
                  </li>
                ))}
              </ul>
            ) : null}

            {borrador.renglones.length > 0 ? (
              <section aria-label="Lo que recibes" className="flex flex-col gap-3">
                <h2 className="text-base font-semibold text-marino">Lo que recibes</h2>
                <ul className="flex flex-col gap-3">
                  {borrador.renglones.map((l) => {
                    const r = evaluadoDe.get(l.uid) ?? null;
                    return (
                      <li key={l.uid} className="animate-in fade-in slide-in-from-top-2 duration-150 motion-reduce:animate-none">
                        <RenglonDevolucion
                          local={l}
                          evaluado={r}
                          cantidadMaxima={maximoDe(l, r ?? undefined)}
                          nota={notas[l.uid]}
                          deshabilitado={enviando}
                          alCondicion={(c) => cambiarCondicion(l.uid, c)}
                          alCantidad={(n) => cambiarCantidad(l.uid, n)}
                          alQuitar={() => quitar(l.uid)}
                          alObservacion={() => setObservando(l.uid)}
                          alFoto={(archivo) => cambiarFoto(l.uid, archivo)}
                        />
                      </li>
                    );
                  })}
                </ul>
              </section>
            ) : !borrador.trabajador ? (
              <p className="flex items-start gap-2 rounded-2xl border border-dashed p-6 text-sm text-muted-foreground">
                <ScanLineIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                Todavía no recibes nada. Escanea la pieza que regresa (se abona a quien la tenía) o la credencial del trabajador para elegir de su lista.
              </p>
            ) : (
              <p className="rounded-2xl border border-dashed p-4 text-center text-sm text-muted-foreground">
                Todavía no recibes nada. Toca “Devolver” en lo que regresa o escanea la pieza.
              </p>
            )}
          </div>

          <div className="order-1 flex flex-col gap-3 md:sticky md:top-4 md:order-2">
            <Escaner
              activo={!observando && !cantidadDe && !resultadosBusqueda && !descartando && !enviando}
              sonidoAlLeer={false}
              onCodigo={(codigo, origen) => void alLeer(codigo, origen)}
              onRepetido={() => reproducir("aviso")}
              etiquetaCampo="Escribir código, serie o nombre"
              placeholderCampo="Código, serie o nombre"
            />
            {buscando ? <Cargando variante="en-linea" texto="Buscando…" /> : null}
            {mensajeLectura ? (
              <p role="alert" className="flex items-start gap-2 rounded-xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm font-medium">
                <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-amarillo" />
                {mensajeLectura}
              </p>
            ) : null}
          </div>
        </div>

        <HojaObservacion
          abierta={observando !== null && campoDeObservacion !== undefined}
          alCambiar={(abierta) => {
            if (!abierta) setObservando(null);
          }}
          titulo="¿Qué le pasó?"
          motivo={
            evaluadoObservado?.motivos.find((m) => m.regla === "V-05")?.mensaje ?? "Si regresa dañado, anota qué le pasó."
          }
          regla="V-05"
          valorInicial={campoDeObservacion?.observacion ?? ""}
          respuestasRapidas={RESPUESTAS_DANO}
          alGuardar={(texto) => {
            if (observando) guardarObservacion(observando, texto);
            setObservando(null);
          }}
        />

        {cantidadDe ? (
          <HojaCantidad
            abierta
            alCambiar={(abierta) => {
              if (!abierta) setCantidadDe(null);
            }}
            articulo={cantidadDe.articulo}
            disponible={Math.max(1, cantidadDe.cantidad - agregadoDe(cantidadDe))}
            alAgregar={(cantidad, condicion) => agregarCantidad(cantidadDe.codigo, cantidad, condicion)}
          />
        ) : null}
      </div>
    );
    accion = (
      <AccionPrincipal nota={razon}>
        <Boton variante="principal" cargando={enviando} disabled={!listo && !reintento} onClick={() => void confirmar()}>
          {reintento ? "Reintentar" : "Confirmar devolución"}
        </Boton>
      </AccionPrincipal>
    );
  }

  return (
    <Pantalla titulo="Devolver">
      {encabezado}
      {!enLinea && !borrador.resultado ? (
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
        mensaje="¿Salir sin terminar la devolución?"
        detalle="Lo que capturaste no se guardará."
        etiquetaConfirmar="Sí, salir"
        etiquetaCancelar="Seguir aquí"
        peligro
        alConfirmar={() => {
          borrarBorradorDevolucion();
          if (bloqueo.state === "blocked") bloqueo.proceed();
        }}
      />
      <Confirmacion
        abierta={descartando}
        alCambiar={setDescartando}
        mensaje="¿Empezar una devolución nueva?"
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
            // Se vuelve a identificar lo elegido por su código: pieza, trabajador o artículo por cantidad.
            void alLeer(c.codigo, "pistola");
          }}
        />
      ) : null}
    </Pantalla>
  );
}
