import { ArrowLeftIcon, ArrowRightIcon, CircleAlertIcon, ListChecksIcon, SquareXIcon, TriangleAlertIcon, WifiOffIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Escaner } from "~/componentes/dominio/escaner";
import { HojaObservacion } from "~/componentes/dominio/hoja-observacion";
import { reproducir } from "~/componentes/dominio/sonido";
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
import { desdeCuando, textoRenglones, tokenDeLectura } from "~/componentes/traspasos/formato";
import { MotivosDelVale } from "~/componentes/traspasos/motivos-vale";
import { RenglonRecepcion } from "~/componentes/traspasos/renglon-recepcion";
import { ResultadoTraspaso } from "~/componentes/traspasos/resultado-traspaso";
import type { PorRecibirApi, RenglonPorRecibirApi, TraspasoPorRecibirApi } from "~/componentes/traspasos/tipos";
import { useEvaluar, type CuerpoTraspaso } from "~/componentes/traspasos/use-evaluar";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { refrescarContadores } from "~/sesion/contadores";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "traspasos.operar" };

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
  const [abriendo, setAbriendo] = useState(false);
  const sonidoPendiente = useRef<Set<string>>(new Set());

  // Solo cuentan las marcas de renglones que todavía tienen algo pendiente.
  const lineas = traspaso.renglones;
  const lineaDe = useCallback(
    (codigo: string) => lineas.find((l) => claveDeCodigo(l.codigo) === claveDeCodigo(codigo) || (l.numero_serie && claveDeCodigo(l.numero_serie) === claveDeCodigo(codigo))),
    [lineas],
  );
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
  const ev = useEvaluar(cuerpo);
  const evaluacion: EvaluacionApi | null = ev.evaluacion;
  const evaluadoDe = useCallback(
    (codigo: string) => evaluacion?.renglones.find((r) => claveDeCodigo(r.codigo) === claveDeCodigo(codigo)),
    [evaluacion],
  );

  // Sonido de lo que no es del traspaso, cuando el servidor lo evalúa.
  useEffect(() => {
    if (!ev.actual || sonidoPendiente.current.size === 0) return;
    for (const clave of [...sonidoPendiente.current]) {
      const r = evaluacion?.renglones.find((x) => claveDeCodigo(x.codigo) === clave);
      if (!r) continue;
      sonidoPendiente.current.delete(clave);
      reproducir(r.nivel === "ROJO" ? "bloqueo" : "ok");
    }
  }, [ev.actual, evaluacion]);

  const errorAlmacen = ev.error?.codigo === "ALMACEN_CAMBIO" ? ev.error : null;

  // ------------------------------------------------------------------ cambios del borrador
  const cambiar = useCallback((cambio: (b: BorradorRecepcion) => BorradorRecepcion) => {
    setAvisoCambio(null);
    setBorrador(cambio);
  }, []);
  const marcar = (l: RenglonPorRecibirApi, cantidad: number) => {
    const clave = claveDeCodigo(l.codigo);
    cambiar((b) => {
      const copia = { ...b.marcas };
      if (cantidad > 0) copia[clave] = Math.min(cantidad, l.cantidad_pendiente);
      else delete copia[clave];
      return { ...b, marcas: copia };
    });
  };
  const recibirTodo = () => {
    cambiar((b) => ({ ...b, marcas: Object.fromEntries(pendientes.map((l) => [claveDeCodigo(l.codigo), l.cantidad_pendiente])) }));
    reproducir("ok");
  };
  const quitarMarcas = () => cambiar((b) => ({ ...b, marcas: {}, extras: [] }));
  const quitarExtra = (codigo: string) => cambiar((b) => ({ ...b, extras: b.extras.filter((c) => claveDeCodigo(c) !== claveDeCodigo(codigo)) }));

  const alLeer = async (lectura: string) => {
    const token = tokenDeLectura(lectura);
    if (token) {
      if (token === traspaso.token) {
        reproducir("aviso");
        aviso({ titulo: "Ese es el código del traspaso", descripcion: "Escanea cada pieza o artículo que llegó.", tipo: "aviso" });
        return;
      }
      if (totalMarcado > 0 || hayExtras) {
        reproducir("aviso");
        aviso({ titulo: "Termina esta recepción antes de abrir otro traspaso", tipo: "aviso" });
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
    const linea = lineaDe(codigo);
    if (!linea) {
      if (borrador.extras.some((c) => claveDeCodigo(c) === claveDeCodigo(codigo))) {
        reproducir("aviso");
        aviso({ titulo: "Ya lo leíste", descripcion: codigo, tipo: "aviso", duracionMs: 2500 });
        return;
      }
      // Lo que no es del traspaso lo evalúa el servidor y lo marca en rojo (X-12).
      sonidoPendiente.current.add(claveDeCodigo(codigo));
      cambiar((b) => ({ ...b, extras: [...b.extras, codigo] }));
      return;
    }
    const clave = claveDeCodigo(linea.codigo);
    const actual = marcas[clave] ?? 0;
    if (linea.cantidad_pendiente <= 0) {
      reproducir("aviso");
      aviso({ titulo: "Ya se recibió", descripcion: linea.articulo, tipo: "aviso", duracionMs: 2500 });
    } else if (linea.pieza_id !== null && actual > 0) {
      reproducir("aviso");
      aviso({ titulo: "Ya está marcada", descripcion: linea.articulo, tipo: "aviso", duracionMs: 2500 });
    } else if (actual >= linea.cantidad_pendiente) {
      reproducir("aviso");
      aviso({ titulo: "Ya marcaste todo lo que se envió", descripcion: linea.articulo, tipo: "aviso", duracionMs: 2500 });
    } else {
      reproducir("ok");
      marcar(linea, actual + 1);
    }
  };

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
      const observacion = faltaron > 0 ? observacionRef.current : null;
      const vale = await apiPost<ValeConfirmadoApi>("/vales", { ...cuerpo, id_cliente: b.idCliente, ...(observacion ? { observacion } : {}) });
      reproducir("ok");
      borrarBorradorRecepcion();
      alRecibir({ vale, traspasoFolio: traspaso.folio, faltaron });
    } catch (causa) {
      reproducir("bloqueo");
      if (!esErrorApi(causa)) {
        setErrorEnvio({ tipo: "otro", mensaje: mensajeDeError(causa) });
      } else if (causa.sinConexion) {
        setErrorEnvio({ tipo: "conexion", mensaje: "Sin conexión. Lo que marcaste está guardado en este dispositivo." });
      } else if (causa.codigo === "VALE_CAMBIO" && causa.detalles) {
        ev.adoptar(causa.detalles as unknown as EvaluacionApi);
        setAvisoCambio(causa.message);
        void alRecargar();
      } else if (causa.codigo === "ALMACEN_CAMBIO") {
        setErrorEnvio({ tipo: "almacen", mensaje: causa.message });
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
        </p>
        <p className="flex flex-wrap items-center gap-1.5 text-base font-semibold">
          {traspaso.origen.nombre}
          <ArrowRightIcon aria-label="hacia" className="size-5 shrink-0" />
          {traspaso.destino.nombre}
        </p>
        <p className="text-sm text-muted-foreground">
          Lo envió {traspaso.envio.nombre}, {desdeCuando(traspaso.creado_en)} · {textoRenglones(lineas.length)}
        </p>
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

      <MotivosDelVale motivos={(evaluacion?.motivos ?? []).filter((m) => m.regla !== "X-13" && m.regla !== "RG-14")} />

      {errorEnvio && errorEnvio.tipo !== "almacen" ? (
        <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            {errorEnvio.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
            {errorEnvio.mensaje}
          </p>
          {errorEnvio.tipo === "conexion" ? <p className="text-base">Cuando vuelva la conexión, toca “Reintentar”. No se guardará dos veces.</p> : null}
        </section>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
        <div className="order-2 flex min-w-0 flex-col gap-4 md:order-1">
          <div className="flex flex-wrap gap-2">
            <Boton variante="secundario" onClick={recibirTodo} disabled={enviando || pendientes.length === 0}>
              <ListChecksIcon aria-hidden="true" />
              Recibir todo
            </Boton>
            <Boton variante="contorno" onClick={quitarMarcas} disabled={enviando || (totalMarcado === 0 && !hayExtras)}>
              <SquareXIcon aria-hidden="true" />
              Quitar marcas
            </Boton>
          </div>

          <ul aria-label="Renglones del traspaso" className="flex flex-col gap-3">
            {lineas.map((l) => {
              const clave = claveDeCodigo(l.codigo);
              const r = evaluadoDe(l.codigo);
              return (
                <li key={`${l.renglon}-${l.codigo}`}>
                  <RenglonRecepcion
                    renglon={l}
                    marcado={marcas[clave] ?? 0}
                    alMarcar={(c) => marcar(l, c)}
                    nivel={r && (marcas[clave] ?? 0) > 0 && r.nivel !== "VERDE" ? r.nivel : undefined}
                    motivos={r && (marcas[clave] ?? 0) > 0 ? r.motivos.filter((m) => m.nivel !== "VERDE") : []}
                    deshabilitado={enviando}
                  />
                </li>
              );
            })}
          </ul>

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
                                {m.mensaje} <span className="text-xs font-medium whitespace-nowrap text-muted-foreground">({m.regla})</span>
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
            onCodigo={(codigo) => void alLeer(codigo)}
            onRepetido={() => reproducir("aviso")}
            etiquetaCampo="Escribir código"
            placeholderCampo="Código o serie"
          />
          <p className="text-sm text-muted-foreground">Escanea cada pieza o artículo que llegó: se marca solo. También puedes tocar su casilla.</p>
        </div>
      </div>

      <AccionPrincipal nota={razon}>
        <Boton variante="principal" cargando={enviando} disabled={razon !== null && !reintento} onClick={pedirConfirmacion}>
          {reintento ? "Reintentar" : faltantes.length > 0 && totalMarcado > 0 ? "Confirmar recepción con diferencias" : "Confirmar recepción"}
        </Boton>
      </AccionPrincipal>

      <HojaObservacion
        abierta={confirmandoDiferencias}
        alCambiar={setConfirmandoDiferencias}
        titulo="Recepción con diferencias"
        motivo={`Faltan ${textoRenglones(faltantes.length)}. Seguirán en camino y el traspaso quedará como “Recibido con diferencias”. Anota qué pasó con lo que falta.`}
        regla="RG-14"
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
