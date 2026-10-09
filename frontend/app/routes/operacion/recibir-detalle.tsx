import { ArrowLeftIcon, ArrowRightIcon, CircleAlertIcon, ListChecksIcon, SquareXIcon, TriangleAlertIcon, WifiOffIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Escaner } from "~/componentes/dominio/escaner";
import { HojaObservacion } from "~/componentes/dominio/hoja-observacion";
import type { MotivoRegla, NivelSemaforo } from "~/componentes/dominio/tipos";
import type { EvaluacionApi, ValeConfirmadoApi, ValeDetalleApi } from "~/componentes/entrega/tipos";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import {
  borrarBorradorRecepcion,
  claveDeCodigo,
  guardarBorradorRecepcion,
  leerBorradorRecepcion,
  nuevoBorradorRecepcion,
  type BorradorRecepcion,
} from "~/componentes/traspasos/borradores";
import { idDeTraspasoPorToken } from "~/componentes/traspasos/buscar-traspaso";
import { desdeCuando, textoRenglones, textoValido, tokenDeLectura } from "~/componentes/traspasos/formato";
import { MotivosDelVale } from "~/componentes/traspasos/motivos-vale";
import { ObservacionRuta } from "~/componentes/traspasos/observacion-ruta";
import { RenglonRecepcion } from "~/componentes/traspasos/renglon-recepcion";
import { vibrarError, vibrarOk } from "~/componentes/traspasos/retroalimentacion";
import { ResultadoTraspaso } from "~/componentes/traspasos/resultado-traspaso";
import type { PorRecibirApi, RenglonPorRecibirApi, TraspasoPorRecibirApi } from "~/componentes/traspasos/tipos";
import { useEvaluar, type CuerpoTraspaso } from "~/componentes/traspasos/use-evaluar";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { refrescarContadores } from "~/sesion/contadores";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "traspasos.recibir" };

/** Renglones que se dibujan de una vez; el resto se carga al pedirlo. */
const TRAMO = 60;

/** Minúsculas y sin acentos, para buscar sin importar cómo se escribió. */
function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-MX").trim();
}

/** Lo que se sabe del traspaso: en camino hacia este almacén, o solo el vale (de otro almacén o ya recibido). */
type Cargado = { modo: "en-camino"; traspaso: TraspasoPorRecibirApi } | { modo: "otro"; vale: ValeDetalleApi | null };

interface Recibido {
  vale: ValeConfirmadoApi;
  traspasoFolio: string;
  /** Renglones que quedaron sin llegar al confirmar. */
  faltaron: number;
}

export default function RecibirDetalle() {
  const { id = "" } = useParams();
  const { sesion, puede, recargar: recargarSesion } = useSesionActiva();
  const navegar = useNavigate();
  const enLinea = useEnLinea();
  const usuarioId = sesion.usuario.id;
  const operaTodos = puede("almacenes.todos");

  const carga = useConsulta<Cargado>(async (signal) => {
    const lista = await apiGet<PorRecibirApi>("/traspasos/por-recibir", undefined, signal);
    const traspaso = lista.elementos.find((t) => t.id === id);
    if (traspaso) return { modo: "en-camino", traspaso };
    try {
      return { modo: "otro", vale: await apiGet<ValeDetalleApi>(`/vales/${encodeURIComponent(id)}`, undefined, signal) };
    } catch (causa) {
      // Un traspaso de otro almacén no se puede abrir: el servidor dice por qué al evaluar la recepción (X-10).
      if (esErrorApi(causa) && (causa.status === 404 || causa.status === 403)) return { modo: "otro", vale: null };
      throw causa;
    }
  }, id);

  const [recibido, setRecibido] = useState<Recibido | null>(null);

  const volver = (
    <Link to="/recibir" className="inline-flex min-h-10 items-center gap-2 self-start text-base font-semibold text-primary">
      <ArrowLeftIcon aria-hidden="true" className="size-5" />
      Volver a la lista
    </Link>
  );

  if (carga.error) {
    const noExiste = esErrorApi(carga.error) && carga.error.status === 404;
    return (
      <Pantalla titulo="Recibir traspaso">
        {volver}
        <EstadoError
          error={noExiste ? undefined : carga.error}
          mensaje={noExiste ? "No encontramos ese traspaso. Revisa el código o la lista de traspasos." : undefined}
          alReintentar={noExiste ? undefined : carga.recargar}
        />
      </Pantalla>
    );
  }
  if (!carga.datos) {
    return (
      <Pantalla titulo="Recibir traspaso">
        {volver}
        <Esqueleto tipo="lista" cantidad={3} />
      </Pantalla>
    );
  }

  if (recibido) {
    const completo = recibido.faltaron === 0;
    return (
      <Pantalla titulo="Recibir traspaso">
        <ResultadoTraspaso
          ancla="recibir-resultado"
          vale={recibido.vale}
          titulo="Recepción guardada"
          texto={`Recepción del traspaso ${recibido.traspasoFolio}`}
          nota={
            completo ? (
              <p className="text-center">Se recibió todo el traspaso. Ya quedó en el inventario de este almacén.</p>
            ) : (
              <p role="status" className="flex items-start gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
                <TriangleAlertIcon aria-hidden="true" className="mt-1 size-4 shrink-0 text-semaforo-amarillo" strokeWidth={3} />
                <span>
                  <strong>Recibido con diferencias.</strong> Lo que no marcaste ({textoRenglones(recibido.faltaron)}) sigue en camino. El traspaso seguirá en la lista hasta que llegue.
                </span>
              </p>
            )
          }
        />
        <AccionPrincipal>
          <Boton
            variante="principal"
            onClick={() => {
              if (completo) void navegar("/recibir");
              else {
                setRecibido(null);
                carga.recargar();
              }
            }}
          >
            {completo ? "Volver a la lista" : "Seguir con este traspaso"}
          </Boton>
          {completo ? null : (
            <Boton variante="contorno" onClick={() => void navegar("/recibir")}>
              Volver a la lista
            </Boton>
          )}
        </AccionPrincipal>
      </Pantalla>
    );
  }

  const datos = carga.datos;
  return datos.modo === "en-camino" ? (
    <Recepcion
      key={datos.traspaso.id + datos.traspaso.recepciones.length}
      traspaso={datos.traspaso}
      usuarioId={usuarioId}
      operaTodos={operaTodos}
      almacenSesionId={sesion.almacen?.id ?? null}
      enLinea={enLinea}
      volver={volver}
      alRecibir={(r) => {
        setRecibido(r);
        refrescarContadores();
      }}
      alRecargar={async (conSesion) => {
        if (conSesion) await recargarSesion();
        carga.recargar();
        refrescarContadores();
      }}
    />
  ) : (
    <OtroAlmacen id={id} vale={datos.vale} operaTodos={operaTodos} almacenSesionId={sesion.almacen?.id ?? null} volver={volver} />
  );
}

// ---------------------------------------------------------------------------------------------
// Un traspaso que no está en camino hacia este almacén: se muestra lo que dice el servidor (X-10, X-12).

function OtroAlmacen({ id, vale, operaTodos, almacenSesionId, volver }: { id: string; vale: ValeDetalleApi | null; operaTodos: boolean; almacenSesionId: string | null; volver: React.ReactNode }) {
  const esTraspaso = vale === null || (vale.tipo === "TRASPASO" && vale.destino_almacen);
  const cuerpo = useMemo<CuerpoTraspaso | null>(() => {
    if (!esTraspaso) return null;
    return {
      tipo: "RECEPCION",
      almacen_id: operaTodos ? (vale?.destino_almacen?.id ?? null) : almacenSesionId,
      vale_origen_id: id,
      id_cliente: "00000000-0000-4000-8000-000000000000",
      renglones: (vale?.renglones ?? []).map((r) => ({ codigo: r.codigo_pieza ?? r.codigo_articulo, cantidad: r.cantidad })),
    };
  }, [esTraspaso, operaTodos, almacenSesionId, vale, id]);
  const ev = useEvaluar(cuerpo);
  const noExiste = ev.error?.status === 404;

  const renglones: RenglonPorRecibirApi[] = (vale?.renglones ?? []).map((r) => ({
    renglon: r.renglon,
    articulo_id: r.articulo_id,
    articulo: r.articulo,
    marca: r.marca,
    modelo: r.modelo,
    talla: r.talla,
    codigo: r.codigo_pieza ?? r.codigo_articulo,
    pieza_id: r.pieza_id,
    numero_serie: r.numero_serie,
    cantidad_enviada: r.cantidad,
    cantidad_recibida: 0,
    cantidad_pendiente: r.cantidad,
  }));

  return (
    <Pantalla titulo="Recibir traspaso" descripcion={vale?.folio}>
      {volver}
      {!esTraspaso ? (
        <EstadoError mensaje="Ese vale no es un traspaso." />
      ) : noExiste ? (
        <EstadoError mensaje="No encontramos ese traspaso. Revisa el código o la lista de traspasos." />
      ) : (
        <>
          {vale?.destino_almacen ? (
            <p className="flex flex-wrap items-center gap-2 text-base font-semibold">
              {vale.almacen.nombre}
              <ArrowRightIcon aria-label="hacia" className="size-5" />
              {vale.destino_almacen.nombre}
            </p>
          ) : null}
          {ev.error ? (
            <EstadoError error={ev.error} alReintentar={ev.reintentar} />
          ) : ev.evaluacion ? (
            <MotivosDelVale motivos={ev.evaluacion.motivos} />
          ) : (
            <Esqueleto tipo="renglon" />
          )}
          <p className="text-sm text-muted-foreground">Este traspaso no está disponible para que lo recibas desde este almacén.</p>
          {renglones.length > 0 ? (
            <ul className="flex flex-col gap-3">
              {renglones.map((r) => (
                <li key={r.renglon}>
                  <RenglonRecepcion renglon={r} marcado={0} soloLectura />
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </Pantalla>
  );
}

// ---------------------------------------------------------------------------------------------
// La recepción de un traspaso en camino hacia este almacén.

interface PropiedadesRecepcion {
  traspaso: TraspasoPorRecibirApi;
  usuarioId: string;
  operaTodos: boolean;
  almacenSesionId: string | null;
  enLinea: boolean;
  volver: React.ReactNode;
  alRecibir: (r: Recibido) => void;
  alRecargar: (conSesion?: boolean) => Promise<void>;
}

function Recepcion({ traspaso, usuarioId, operaTodos, almacenSesionId, enLinea, volver, alRecibir, alRecargar }: PropiedadesRecepcion) {
  const navegar = useNavigate();
  const [borrador, setBorrador] = useState<BorradorRecepcion>(
    () => leerBorradorRecepcion(usuarioId, traspaso.id) ?? nuevoBorradorRecepcion(usuarioId, traspaso.id),
  );
  const borradorRef = useRef(borrador);
  borradorRef.current = borrador;
  useEffect(() => {
    guardarBorradorRecepcion(borrador);
  }, [borrador]);

  const [errorEnvio, setErrorEnvio] = useState<{ tipo: "conexion" | "almacen" | "otro"; mensaje: string } | null>(null);
  const [avisoCambio, setAvisoCambio] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const [confirmandoDiferencias, setConfirmandoDiferencias] = useState(false);
  // RG-14: con diferencias la observación es obligatoria. Se pide en la hoja y se conserva para un reintento.
  const observacionRef = useRef<string | null>(null);
  // X-21: si quien recibe es quien envió, el servidor pide explicar por qué. Esta es esa explicación.
  const [observacionMisma, setObservacionMisma] = useState("");
  const [errorObservacionMisma, setErrorObservacionMisma] = useState<string | null>(null);
  const [abriendo, setAbriendo] = useState(false);

  // Búsqueda, filtro y carga incremental: con 100 a 500 renglones solo se dibuja un tramo.
  const [busqueda, setBusqueda] = useState("");
  const buscar = useRetraso(busqueda, 200);
  const [filtro, setFiltro] = useState<"todos" | "pendientes" | "marcados">("todos");
  const [limite, setLimite] = useState(TRAMO);
  const [destello, setDestello] = useState<{ renglon: number; n: number } | null>(null);
  const [mensajeEscaner, setMensajeEscaner] = useState<{ tipo: "error" | "ok"; texto: string; n: number } | null>(null);
  const [confirmandoTodo, setConfirmandoTodo] = useState(false);
  const contadorLecturas = useRef(0);

  // Búsqueda por mapa: cada código o serie apunta a su renglón sin recorrer la lista.
  const lineas = traspaso.renglones;
  const mapaCodigos = useMemo(() => {
    const m = new Map<string, RenglonPorRecibirApi>();
    for (const l of lineas) {
      m.set(claveDeCodigo(l.codigo), l);
      if (l.numero_serie) m.set(claveDeCodigo(l.numero_serie), l);
    }
    return m;
  }, [lineas]);
  const mapaRef = useRef(mapaCodigos);
  mapaRef.current = mapaCodigos;
  const textos = useMemo(
    () => lineas.map((l) => normalizar(`${l.articulo} ${l.marca ?? ""} ${l.modelo ?? ""} ${l.codigo} ${l.numero_serie ?? ""}`)),
    [lineas],
  );

  // Solo cuentan las marcas de renglones que todavía tienen algo pendiente.
  const marcas = useMemo(() => {
    const salida: Record<string, number> = {};
    for (const l of lineas) {
      const m = borrador.marcas[claveDeCodigo(l.codigo)] ?? 0;
      if (m > 0 && l.cantidad_pendiente > 0) salida[claveDeCodigo(l.codigo)] = Math.min(m, l.cantidad_pendiente);
    }
    return salida;
  }, [borrador.marcas, lineas]);

  const totalMarcado = Object.keys(marcas).length;
  const hayExtras = borrador.extras.length > 0;
  const pendientes = lineas.filter((l) => l.cantidad_pendiente > 0);
  const faltantes = pendientes.filter((l) => (marcas[claveDeCodigo(l.codigo)] ?? 0) < l.cantidad_pendiente);
  const unidadesQueFaltan = faltantes.reduce((s, l) => s + l.cantidad_pendiente - (marcas[claveDeCodigo(l.codigo)] ?? 0), 0);

  const textoBuscado = normalizar(buscar);
  const visibles = useMemo(
    () =>
      lineas.filter((l, i) => {
        const marcada = (marcas[claveDeCodigo(l.codigo)] ?? 0) > 0;
        if (filtro === "pendientes" && (marcada || l.cantidad_pendiente <= 0)) return false;
        if (filtro === "marcados" && !marcada) return false;
        return !textoBuscado || textos[i].includes(textoBuscado);
      }),
    [lineas, marcas, filtro, textoBuscado, textos],
  );
  const tramo = useMemo(() => visibles.slice(0, limite), [visibles, limite]);
  const porcentaje = pendientes.length > 0 ? Math.round((totalMarcado / pendientes.length) * 100) : 100;

  // ------------------------------------------------------------------ evaluación
  const cuerpo = useMemo<CuerpoTraspaso>(
    () => ({
      tipo: "RECEPCION",
      almacen_id: operaTodos ? traspaso.destino.id : almacenSesionId,
      vale_origen_id: traspaso.id,
      id_cliente: borrador.idCliente,
      renglones: [
        ...lineas.filter((l) => marcas[claveDeCodigo(l.codigo)]).map((l) => ({ codigo: l.codigo, cantidad: marcas[claveDeCodigo(l.codigo)] })),
        ...borrador.extras.map((codigo) => ({ codigo, cantidad: 1 })),
      ],
    }),
    [operaTodos, traspaso.destino.id, traspaso.id, almacenSesionId, borrador.idCliente, lineas, marcas, borrador.extras],
  );
  // Con listas largas el cuerpo es grande: se espera más para no reenviarlo en cada marca de una ráfaga.
  const ev = useEvaluar(cuerpo, lineas.length > 40 ? 450 : 150);
  const evaluacion: EvaluacionApi | null = ev.evaluacion;
  const esMismaPersona = Boolean(evaluacion?.motivos.some((m) => m.regla === "X-21"));
  const mapaEvaluado = useMemo(() => {
    const m = new Map<string, EvaluacionApi["renglones"][number]>();
    for (const r of evaluacion?.renglones ?? []) m.set(claveDeCodigo(r.codigo), r);
    return m;
  }, [evaluacion]);
  const evaluadoDe = useCallback((codigo: string) => mapaEvaluado.get(claveDeCodigo(codigo)), [mapaEvaluado]);

  // Lo que dijo el servidor de cada renglón, con las mismas referencias si no cambió (así el renglón no se redibuja).
  const cacheEstado = useRef(new Map<string, { firma: string; nivel: NivelSemaforo | undefined; motivos: MotivoRegla[] }>());
  const estadoDe = useMemo(() => {
    const salida = new Map<string, { nivel: NivelSemaforo | undefined; motivos: MotivoRegla[] }>();
    for (const l of lineas) {
      const clave = claveDeCodigo(l.codigo);
      const r = (marcas[clave] ?? 0) > 0 ? mapaEvaluado.get(clave) : undefined;
      const nivel = r && r.nivel !== "VERDE" ? r.nivel : undefined;
      const motivos = r ? r.motivos.filter((m) => m.nivel !== "VERDE") : [];
      if (!nivel && motivos.length === 0) continue;
      const firma = JSON.stringify([nivel, motivos.map((m) => [m.nivel, m.mensaje])]);
      const previo = cacheEstado.current.get(clave);
      if (previo && previo.firma === firma) salida.set(clave, previo);
      else {
        const nuevo = { firma, nivel, motivos };
        cacheEstado.current.set(clave, nuevo);
        salida.set(clave, nuevo);
      }
    }
    return salida;
  }, [lineas, marcas, mapaEvaluado]);

  const errorAlmacen = ev.error?.codigo === "ALMACEN_CAMBIO" ? ev.error : null;

  // ------------------------------------------------------------------ cambios del borrador
  const cambiar = useCallback((cambio: (b: BorradorRecepcion) => BorradorRecepcion) => {
    setAvisoCambio(null);
    setBorrador(cambio);
  }, []);
  /** Estable: lo usan todos los renglones (React.memo). La clave es la del código del renglón. */
  const marcar = useCallback(
    (clave: string, cantidad: number) => {
    const l = mapaRef.current.get(clave);
    if (!l) return;
    cambiar((b) => {
      const copia = { ...b.marcas };
      if (cantidad > 0) copia[clave] = Math.min(cantidad, l.cantidad_pendiente);
      else delete copia[clave];
      return { ...b, marcas: copia };
    });
    },
    [cambiar],
  );
  const recibirTodo = () => {
    cambiar((b) => ({ ...b, marcas: Object.fromEntries(pendientes.map((l) => [claveDeCodigo(l.codigo), l.cantidad_pendiente])) }));
    vibrarOk();
  };
  const pedirRecibirTodo = () => {
    if (pendientes.length > 10) setConfirmandoTodo(true);
    else recibirTodo();
  };
  const quitarMarcas = () => cambiar((b) => ({ ...b, marcas: {}, extras: [] }));
  const quitarExtra = (codigo: string) => cambiar((b) => ({ ...b, extras: b.extras.filter((c) => claveDeCodigo(c) !== claveDeCodigo(codigo)) }));

  const decir = (tipo: "error" | "ok", texto: string) => {
    contadorLecturas.current += 1;
    setMensajeEscaner({ tipo, texto, n: contadorLecturas.current });
  };
  const alLeer = async (lectura: string) => {
    const token = tokenDeLectura(lectura);
    if (token) {
      if (token === traspaso.token) {
        vibrarError();
        decir("error", "Ese es el código del traspaso. Escanea cada pieza o artículo que llegó.");
        return;
      }
      if (totalMarcado > 0 || hayExtras) {
        vibrarError();
        decir("error", "Termina esta recepción antes de abrir otro traspaso.");
        return;
      }
      setAbriendo(true);
      try {
        const otro = await idDeTraspasoPorToken(token, null);
        if (otro) void navegar(`/recibir/${otro}`);
        else aviso({ titulo: "Ese vale no es un traspaso", tipo: "aviso" });
      } catch (causa) {
        aviso({ titulo: "No pudimos abrir el traspaso", descripcion: mensajeDeError(causa), tipo: "error" });
      } finally {
        setAbriendo(false);
      }
      return;
    }

    const codigo = lectura.trim();
    const linea = mapaCodigos.get(claveDeCodigo(codigo));
    if (!linea) {
      vibrarError();
      if (borrador.extras.some((c) => claveDeCodigo(c) === claveDeCodigo(codigo))) {
        decir("error", `Ya leíste ${codigo}, y no es de este traspaso.`);
        return;
      }
      // Lo que no es del traspaso lo evalúa el servidor y lo marca en rojo (X-12).
      decir("error", `${codigo} no es de este traspaso. No se recibe; quedó en la lista de abajo.`);
      cambiar((b) => ({ ...b, extras: [...b.extras, codigo] }));
      return;
    }
    const clave = claveDeCodigo(linea.codigo);
    const actual = marcas[clave] ?? 0;
    if (linea.cantidad_pendiente <= 0) {
      vibrarError();
      decir("error", `${linea.articulo} ya se recibió completo.`);
    } else if (linea.pieza_id !== null && actual > 0) {
      vibrarError();
      decir("error", `${linea.articulo} ya está marcada.`);
    } else if (actual >= linea.cantidad_pendiente) {
      vibrarError();
      decir("error", `Ya marcaste todo lo que se envió de ${linea.articulo}.`);
    } else {
      vibrarOk();
      decir("ok", `Marcado: ${linea.articulo}`);
      marcar(clave, actual + 1);
      // Se asegura que el renglón se vea (sin búsqueda que lo oculte ni fuera del tramo dibujado) y se le da un destello.
      if (busqueda) setBusqueda("");
      if (filtro === "pendientes") setFiltro("todos");
      setLimite((n) => Math.max(n, lineas.indexOf(linea) + 1));
      setDestello((d) => ({ renglon: linea.renglon, n: (d?.n ?? 0) + 1 }));
    }
  };

  // Lleva la vista al renglón recién escaneado.
  useEffect(() => {
    if (!destello) return;
    const id = window.setTimeout(() => {
      const el = document.getElementById(`rec-${destello.renglon}`);
      if (!el) return;
      let suave = true;
      try {
        suave = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      } catch {
        suave = true;
      }
      el.scrollIntoView({ block: "center", behavior: suave ? "smooth" : "auto" });
    }, 40);
    return () => window.clearTimeout(id);
  }, [destello]);

  // ------------------------------------------------------------------ confirmar
  const confirmar = async () => {
    if (enviandoRef.current) return;
    const b = borradorRef.current;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    setAvisoCambio(null);
    const faltaron = faltantes.length;
    try {
      const partes = [esMismaPersona ? observacionMisma.trim() : "", faltaron > 0 ? (observacionRef.current ?? "") : ""].filter(Boolean);
      const observacion = partes.length > 0 ? partes.join(" · ") : null;
      const vale = await apiPost<ValeConfirmadoApi>("/vales", { ...cuerpo, id_cliente: b.idCliente, ...(observacion ? { observacion } : {}) });
      vibrarOk();
      borrarBorradorRecepcion();
      alRecibir({ vale, traspasoFolio: traspaso.folio, faltaron });
    } catch (causa) {
      vibrarError();
      if (!esErrorApi(causa)) {
        setErrorEnvio({ tipo: "otro", mensaje: mensajeDeError(causa) });
      } else if (causa.sinConexion) {
        setErrorEnvio({ tipo: "conexion", mensaje: "Sin conexión. Lo que marcaste está guardado en este dispositivo." });
      } else if (causa.reintentable) {
        setErrorEnvio({ tipo: "conexion", mensaje: causa.message });
      } else if (causa.codigo === "VALE_CAMBIO" && causa.detalles) {
        ev.adoptar(causa.detalles as unknown as EvaluacionApi);
        setAvisoCambio(causa.message);
        void alRecargar();
      } else if (causa.codigo === "ALMACEN_CAMBIO") {
        setErrorEnvio({ tipo: "almacen", mensaje: causa.message });
      } else if (causa.status === 422 && causa.detalles?.regla === "X-21") {
        setErrorObservacionMisma(causa.message || "Explica por qué también recibes este traspaso.");
      } else {
        setErrorEnvio({ tipo: "otro", mensaje: causa.message });
      }
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  };

  const pedirConfirmacion = () => {
    // Un reintento tras un corte de red va directo: la intención ya estaba confirmada y la recepción es la misma.
    if (errorEnvio?.tipo !== "conexion" && faltantes.length > 0) setConfirmandoDiferencias(true);
    else void confirmar();
  };

  // ------------------------------------------------------------------ razones
  const rojos = evaluacion?.renglones.filter((r) => r.nivel === "ROJO").length ?? 0;
  const reintento = errorEnvio?.tipo === "conexion";
  const razon = ((): string | null => {
    if (totalMarcado === 0 && !hayExtras) return "Marca lo que llegó o toca “Recibir todo”.";
    if (ev.error && !ev.actual) return ev.error.sinConexion ? "Sin conexión: no podemos revisar todavía." : "No pudimos revisar la recepción.";
    if (!evaluacion || !ev.actual || ev.evaluando) return "Revisando la recepción…";
    if (rojos > 0) return `Quita ${rojos === 1 ? "el código en rojo" : `los ${rojos} códigos en rojo`} para continuar.`;
    if (esMismaPersona && !observacionMisma.trim()) return "Explica por qué también recibes este traspaso para continuar.";
    // Solo falta la observación (RG-14): se pide al confirmar, en la hoja de diferencias.
    const soloFaltaObservacion = evaluacion.motivos.filter((m) => m.nivel === "ROJO").every((m) => m.regla === "RG-14");
    if (!evaluacion.puede_confirmar && !soloFaltaObservacion) return evaluacion.motivos.find((m) => m.nivel === "ROJO")?.mensaje ?? "Revisa la recepción para continuar.";
    if (totalMarcado === 0) return "Marca lo que llegó o toca “Recibir todo”.";
    return null;
  })();

  const conDiferencias = traspaso.estado === "RECIBIDO_CON_DIFERENCIAS";

  return (
    <Pantalla titulo="Recibir traspaso" descripcion={`Marca lo que llegó y confirma la recepción.`}>
      {volver}

      <section aria-label="Datos del traspaso" className="flex flex-col gap-1 rounded-2xl border bg-card p-4">
        <p className="flex flex-wrap items-center gap-2">
          <span className="text-lg font-semibold tracking-wide text-marino">{traspaso.folio}</span>
          {conDiferencias ? <Insignia estado="amarillo">Recibido en parte</Insignia> : <Insignia estado="info">En camino</Insignia>}
          {traspaso.ruta === "LATERAL" ? <Insignia estado="neutra">Traslado desde {traspaso.origen.nombre}</Insignia> : null}
        </p>
        <p className="flex flex-wrap items-center gap-1.5 text-base font-semibold">
          {traspaso.origen.nombre}
          <ArrowRightIcon aria-label="hacia" className="size-5 shrink-0" />
          {traspaso.destino.nombre}
        </p>
        <p className="text-sm text-muted-foreground">
          Lo envió {traspaso.envio.nombre}, {desdeCuando(traspaso.creado_en)} · {textoRenglones(lineas.length)}
        </p>
        {traspaso.valido ? <p className="text-sm text-muted-foreground">Validó: {textoValido(traspaso.valido)}</p> : null}
        {traspaso.recepciones.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            Ya recibido antes: {traspaso.recepciones.map((r) => `${r.folio} (${r.recibio.nombre})`).join(", ")}.
          </p>
        ) : null}
      </section>

      {!enLinea ? (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <WifiOffIcon aria-hidden="true" className="size-4" />
          Lo que marques se guarda en este dispositivo hasta que vuelva la conexión.
        </p>
      ) : null}

      {errorAlmacen ? (
        <section role="alert" className="flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-6 shrink-0 text-semaforo-amarillo" />
            Te cambiaron de almacén. {errorAlmacen.message}
          </p>
          <Boton variante="normal" className="self-start" onClick={() => void alRecargar(true)}>
            Continuar
          </Boton>
        </section>
      ) : null}

      {avisoCambio ? (
        <p role="alert" className="flex items-start gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-semibold">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-rojo" />
          {avisoCambio} Revisa lo que falta por recibir.
        </p>
      ) : null}

      {ev.error && !errorAlmacen ? (
        <section role="alert" className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            {ev.error.sinConexion ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
            {ev.error.sinConexion ? "Sin conexión. Lo que marcaste está guardado en este dispositivo." : ev.error.message}
          </p>
          <Boton variante="secundario" className="self-start" onClick={ev.reintentar}>
            Reintentar
          </Boton>
        </section>
      ) : null}

      <MotivosDelVale sinRegla motivos={(evaluacion?.motivos ?? []).filter((m) => m.regla !== "X-13" && m.regla !== "RG-14")} />

      {esMismaPersona ? (
        <ObservacionRuta
          titulo="¿Por qué también lo recibes tú?"
          descripcion="Tú enviaste este traspaso. Anota por qué lo recibes también; queda en el vale y en la revisión."
          respuestas={["Soy el único en el almacén", "El otro turno no estaba", "Otro motivo"]}
          valor={observacionMisma}
          alCambiar={(texto) => {
            setErrorObservacionMisma(null);
            setObservacionMisma(texto);
          }}
          error={errorObservacionMisma}
          deshabilitado={enviando}
        />
      ) : null}

      {errorEnvio && errorEnvio.tipo !== "almacen" ? (
        <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            {errorEnvio.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
            {errorEnvio.mensaje}
          </p>
          {errorEnvio.tipo === "conexion" ? <p className="text-base">Toca “Reintentar” cuando haya conexión o el sistema responda. No se guardará dos veces.</p> : null}
        </section>
      ) : null}

      {pendientes.length > 0 ? (
        <div className="sticky top-12 z-20 -mx-1 flex flex-col gap-1.5 rounded-2xl border bg-background/95 px-3 py-2 shadow-sm backdrop-blur lg:top-0">
          <p aria-live="polite" role="status" className="text-base font-semibold">
            Recibidos {totalMarcado} de {pendientes.length}
            {hayExtras ? <span className="font-normal text-muted-foreground"> · {hayExtras ? borrador.extras.length : 0} código(s) que no son de este traspaso</span> : null}
          </p>
          <div role="progressbar" aria-label="Avance de la recepción" aria-valuemin={0} aria-valuemax={pendientes.length} aria-valuenow={totalMarcado} className="h-2.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-semaforo-verde transition-[width] duration-200 motion-reduce:transition-none" style={{ width: `${porcentaje}%` }} />
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
        <div className="order-2 flex min-w-0 flex-col gap-4 md:order-1">
          <div className="flex flex-wrap gap-2">
            <Boton variante="secundario" data-tutorial="recibir-todo" onClick={pedirRecibirTodo} disabled={enviando || pendientes.length === 0}>
              <ListChecksIcon aria-hidden="true" />
              Recibir todo
            </Boton>
            <Boton variante="contorno" onClick={quitarMarcas} disabled={enviando || (totalMarcado === 0 && !hayExtras)}>
              <SquareXIcon aria-hidden="true" />
              Quitar marcas
            </Boton>
          </div>

          {lineas.length > 8 ? (
            <div className="flex flex-col gap-2">
              <CampoBusqueda etiqueta="Buscar en los renglones por nombre, código o serie" placeholder="Buscar por nombre, código o serie" value={busqueda} alCambiar={setBusqueda} />
              <div role="group" aria-label="Filtrar renglones" className="flex flex-wrap gap-2">
                {(
                  [
                    ["todos", `Todos (${lineas.length})`],
                    ["pendientes", `Pendientes (${pendientes.length - totalMarcado})`],
                    ["marcados", `Marcados (${totalMarcado})`],
                  ] as const
                ).map(([valor, texto]) => (
                  <Boton
                    key={valor}
                    variante={filtro === valor ? "normal" : "contorno"}
                    aria-pressed={filtro === valor}
                    className="min-h-11"
                    onClick={() => {
                      setFiltro(valor);
                      setLimite(TRAMO);
                    }}
                  >
                    {texto}
                  </Boton>
                ))}
              </div>
            </div>
          ) : null}

          {visibles.length === 0 ? (
            <p className="rounded-2xl border border-dashed p-4 text-base text-muted-foreground">
              {buscar || filtro !== "todos" ? "Ningún renglón coincide. Cambia la búsqueda o el filtro." : "Este traspaso no tiene renglones."}
            </p>
          ) : null}

          <ul aria-label="Renglones del traspaso" className="flex flex-col gap-3">
            {tramo.map((l) => {
              const clave = claveDeCodigo(l.codigo);
              const estado = estadoDe.get(clave);
              return (
                <li key={`${l.renglon}-${l.codigo}`} id={`rec-${l.renglon}`} className="scroll-mt-40">
                  <RenglonRecepcion
                    renglon={l}
                    clave={clave}
                    marcado={marcas[clave] ?? 0}
                    alMarcar={marcar}
                    nivel={estado?.nivel}
                    motivos={estado?.motivos}
                    deshabilitado={enviando}
                    destello={destello?.renglon === l.renglon ? destello.n : 0}
                  />
                </li>
              );
            })}
          </ul>

          {visibles.length > tramo.length ? (
            <Boton variante="contorno" className="min-h-11 self-center" onClick={() => setLimite((n) => n + TRAMO)}>
              Mostrar más ({visibles.length - tramo.length} restantes)
            </Boton>
          ) : null}

          {hayExtras ? (
            <section aria-label="Códigos que no son de este traspaso" className="flex flex-col gap-2">
              <h2 className="text-base font-semibold">Códigos que no son de este traspaso</h2>
              <ul className="flex flex-col gap-3">
                {borrador.extras.map((codigo) => {
                  const r = evaluadoDe(codigo);
                  return (
                    <li key={codigo} className="flex flex-col gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/5 p-3">
                      <p className="text-base font-semibold">{r?.articulo?.nombre ?? codigo}</p>
                      <p className="text-sm text-muted-foreground">Código {codigo}</p>
                      {r ? (
                        <ul className="flex flex-col gap-1">
                          {r.motivos.map((m, i) => (
                            <li key={`${m.regla}-${i}`} className="flex items-start gap-2 text-base">
                              <XIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-rojo" />
                              <span>
                                <span className="sr-only">No se puede recibir: </span>
                                {m.mensaje}
                              </span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-muted-foreground">Revisando…</p>
                      )}
                      <Boton variante="contorno" className="self-start" onClick={() => quitarExtra(codigo)} disabled={enviando}>
                        Quitar
                      </Boton>
                    </li>
                  );
                })}
              </ul>
            </section>
          ) : null}

          {totalMarcado > 0 && faltantes.length > 0 ? (
            <section role="status" aria-label="Diferencias" className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
              <p className="flex items-start gap-2 text-base font-semibold">
                <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-amarillo" />
                <span>
                  Hay diferencias: faltan {textoRenglones(faltantes.length)} ({unidadesQueFaltan} {unidadesQueFaltan === 1 ? "pieza o unidad" : "piezas o unidades"}).
                </span>
              </p>
              <p className="text-base">
                Si confirmas así, lo que no marcaste sigue en camino y el traspaso queda como “Recibido con diferencias”. Después puedes recibir lo que falte.
              </p>
              <ul className="list-disc pl-6 text-base">
                {faltantes.map((l) => (
                  <li key={`${l.renglon}-${l.codigo}`}>
                    {l.articulo}
                    {l.pieza_id ? ` (${l.codigo})` : ` — faltan ${l.cantidad_pendiente - (marcas[claveDeCodigo(l.codigo)] ?? 0)}`}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <div className="order-1 flex flex-col gap-2 md:sticky md:top-4 md:order-2">
          <Escaner
            activo={!confirmandoDiferencias && !enviando && !abriendo}
            sonidoAlLeer={false}
            retroalimentacion={mensajeEscaner}
            onCodigo={(codigo) => void alLeer(codigo)}
            onRepetido={() => vibrarError()}
            etiquetaCampo="Escribir código"
            placeholderCampo="Código o serie"
          />
          <p className="text-sm text-muted-foreground">Escanea cada pieza o artículo que llegó: se marca solo. También puedes tocar su casilla.</p>
        </div>
      </div>

      <AccionPrincipal nota={razon}>
        <Boton variante="principal" data-tutorial="recibir-confirmar" cargando={enviando} disabled={razon !== null && !reintento} onClick={pedirConfirmacion}>
          {reintento ? "Reintentar" : faltantes.length > 0 && totalMarcado > 0 ? "Confirmar recepción con diferencias" : "Confirmar recepción"}
        </Boton>
      </AccionPrincipal>

      <Confirmacion
        abierta={confirmandoTodo}
        alCambiar={setConfirmandoTodo}
        mensaje={`¿Marcar ${textoRenglones(pendientes.length)} como recibidos?`}
        detalle="Se marca como llegado todo lo que falta por recibir, con su cantidad completa. Después puedes quitar o cambiar lo que no llegó."
        etiquetaConfirmar="Sí, recibir todo"
        ancla="recibir-todo-confirmar"
        alConfirmar={() => {
          setConfirmandoTodo(false);
          recibirTodo();
        }}
      />

      <HojaObservacion
        abierta={confirmandoDiferencias}
        alCambiar={setConfirmandoDiferencias}
        titulo="Recepción con diferencias"
        motivo={`Faltan ${textoRenglones(faltantes.length)}. Seguirán en camino y el traspaso quedará como “Recibido con diferencias”. Anota qué pasó con lo que falta.`}
        valorInicial={observacionRef.current ?? ""}
        respuestasRapidas={["Faltó en el contenedor", "Llegó dañado", "Se quedó en el origen", "Lo recibirá otro turno"]}
        etiquetaGuardar="Confirmar recepción con diferencias"
        alGuardar={(texto) => {
          observacionRef.current = texto;
          void confirmar();
        }}
      />
    </Pantalla>
  );
}
