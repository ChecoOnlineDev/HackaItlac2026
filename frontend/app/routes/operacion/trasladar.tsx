import { CircleAlertIcon, InfoIcon, RotateCcwIcon, WifiOffIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError, type ErrorApi } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import { Escaner, type OrigenLectura } from "~/componentes/dominio/escaner";
import { ListaRenglones } from "~/componentes/dominio/lista-renglones";
import { reproducir } from "~/componentes/dominio/sonido";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import { HojaBusquedaArticulos, type CoincidenciaArticulo } from "~/componentes/entrega/hoja-busqueda-articulos";
import { SelectorAlmacen } from "~/componentes/entrega/selector-almacen";
import type { AlmacenResumen, EvaluacionApi, ValeConfirmadoApi } from "~/componentes/entrega/tipos";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import {
  borrarBorradorTraslado,
  claveDeCodigo,
  guardarBorradorTraslado,
  leerBorradorTraslado,
  nuevoBorradorTraslado,
  type BorradorTraslado,
} from "~/componentes/traspasos/borradores";
import { MotivosDelVale } from "~/componentes/traspasos/motivos-vale";
import { ResultadoTraspaso } from "~/componentes/traspasos/resultado-traspaso";
import { SelectorDestino } from "~/componentes/traspasos/selector-destino";
import { useEvaluar, type CuerpoTraspaso } from "~/componentes/traspasos/use-evaluar";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "traspasos.operar" };

// La misma clave que Entregar: quien opera varios almacenes recuerda el último que eligió.
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
}
interface BusquedaApi {
  articulos: { elementos: { codigo: string; nombre: string; marca: string | null }[] };
  piezas: { elementos: { codigo: string; articulo: string; numero_serie: string | null }[] };
}

type ErrorEnvio = { tipo: "conexion" | "otro"; mensaje: string } | null;

const TEXTOS_NIVEL = { ROJO: "No se puede enviar" } as const;

export default function Trasladar() {
  const { sesion, puede, recargar } = useSesionActiva();
  const enLinea = useEnLinea();
  const usuarioId = sesion.usuario.id;
  const operaTodos = puede("almacenes.todos");

  // ------------------------------------------------------------------ borrador (persistente)
  const [inicial] = useState(() => {
    const guardado = leerBorradorTraslado(usuarioId);
    const almacen = sesion.almacen?.id ?? (operaTodos ? leerAlmacenRecordado() : null);
    const base = guardado ?? nuevoBorradorTraslado(usuarioId, almacen);
    return { borrador: base, retomado: Boolean(guardado) && base.resultado === null && base.renglones.length > 0 };
  });
  const [borrador, setBorrador] = useState<BorradorTraslado>(inicial.borrador);
  const [retomado, setRetomado] = useState(inicial.retomado);
  const borradorRef = useRef(borrador);
  borradorRef.current = borrador;

  useEffect(() => {
    guardarBorradorTraslado(borrador);
  }, [borrador]);

  // Al salir de la pantalla ya con el traspaso emitido, el borrador no se conserva.
  useEffect(
    () => () => {
      if (borradorRef.current.resultado) borrarBorradorTraslado();
    },
    [],
  );

  const actualizar = useCallback((cambio: (b: BorradorTraslado) => BorradorTraslado) => setBorrador(cambio), []);

  // ------------------------------------------------------------------ estado de pantalla
  const [notas, setNotas] = useState<Record<string, string>>({});
  const [avisoCambio, setAvisoCambio] = useState<string | null>(null);
  const [almacenCambio, setAlmacenCambio] = useState<{ mensaje: string; almacen: AlmacenResumen | null } | null>(null);
  const [errorEnvio, setErrorEnvio] = useState<ErrorEnvio>(null);
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const [descartando, setDescartando] = useState(false);
  const [resultadosBusqueda, setResultadosBusqueda] = useState<{ texto: string; items: CoincidenciaArticulo[] } | null>(null);
  const [buscandoArticulo, setBuscandoArticulo] = useState(false);
  const sonidoPendiente = useRef<Set<string>>(new Set());

  // ------------------------------------------------------------------ evaluación
  const resultado: ValeConfirmadoApi | null = borrador.resultado;
  const cuerpo = useMemo<CuerpoTraspaso | null>(() => {
    if (resultado) return null;
    if (!borrador.destinoId) return null;
    if (operaTodos && !borrador.almacenId) return null;
    return {
      tipo: "TRASPASO",
      almacen_id: borrador.almacenId,
      destino_almacen_id: borrador.destinoId,
      id_cliente: borrador.idCliente,
      renglones: borrador.renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad })),
    };
  }, [resultado, borrador.destinoId, borrador.almacenId, borrador.idCliente, borrador.renglones, operaTodos]);

  const ev = useEvaluar(cuerpo);
  const evaluacion: EvaluacionApi | null = cuerpo ? ev.evaluacion : null;

  const mapaEvaluados = useMemo(
    () => new Map((evaluacion?.renglones ?? []).map((r) => [claveDeCodigo(r.codigo), r] as const)),
    [evaluacion],
  );
  const evaluados = useMemo<RenglonEvaluado[]>(
    () =>
      borrador.renglones.flatMap((b) => {
        const r = mapaEvaluados.get(claveDeCodigo(b.codigo));
        if (!r) return [];
        return [{ ...r, cantidad: b.cantidad }];
      }),
    [borrador.renglones, mapaEvaluados],
  );
  const sinEvaluar = borrador.renglones.filter((b) => !mapaEvaluados.has(claveDeCodigo(b.codigo)));

  // El servidor junta lo repetido: si un renglón del borrador ya no aparece, se quita.
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

  // ------------------------------------------------------------------ salir con captura
  const hayCaptura = !resultado && borrador.renglones.length > 0;
  const bloqueo = useBlocker(hayCaptura);

  // ------------------------------------------------------------------ cambios del borrador
  const agregarCodigo = useCallback(
    (codigo: string) => {
      const limpio = codigo.trim();
      if (!limpio) return;
      const clave = claveDeCodigo(limpio);
      const existente = borradorRef.current.renglones.find((r) => claveDeCodigo(r.codigo) === clave);
      setNotas({});
      setAvisoCambio(null);
      if (existente) {
        if (mapaEvaluados.get(clave)?.articulo?.control === "CANTIDAD") {
          sonidoPendiente.current.add(clave);
          actualizar((b) => ({
            ...b,
            renglones: b.renglones.map((r) => (claveDeCodigo(r.codigo) === clave ? { ...r, cantidad: r.cantidad + 1 } : r)),
          }));
        } else {
          // Una pieza repetida se ignora, con sonido (como E-15).
          reproducir("aviso");
          aviso({ titulo: "Ya está en la lista", descripcion: mapaEvaluados.get(clave)?.articulo?.nombre ?? limpio, tipo: "aviso", duracionMs: 2500 });
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
    actualizar((b) => ({ ...b, renglones: b.renglones.map((x) => (claveDeCodigo(x.codigo) === clave ? { ...x, cantidad } : x)) }));
  };

  const elegirAlmacen = (almacen: AlmacenResumen) => {
    recordarAlmacen(almacen.id);
    // El destino no puede ser el mismo almacén: si coincide, se vuelve a elegir.
    actualizar((b) => ({
      ...b,
      almacenId: almacen.id,
      destinoId: b.destinoId === almacen.id ? null : b.destinoId,
      destinoNombre: b.destinoId === almacen.id ? null : b.destinoNombre,
    }));
  };

  const empezarDeNuevo = () => {
    borrarBorradorTraslado();
    sonidoPendiente.current = new Set();
    setNotas({});
    setAvisoCambio(null);
    setAlmacenCambio(null);
    setErrorEnvio(null);
    setRetomado(false);
    setBorrador(nuevoBorradorTraslado(usuarioId, borradorRef.current.almacenId));
  };

  // ------------------------------------------------------------------ confirmar
  const confirmar = async () => {
    if (enviandoRef.current) return;
    const b = borradorRef.current;
    if (!b.destinoId) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    setAvisoCambio(null);
    try {
      const vale = await apiPost<ValeConfirmadoApi>("/vales", {
        tipo: "TRASPASO",
        almacen_id: b.almacenId,
        destino_almacen_id: b.destinoId,
        id_cliente: b.idCliente,
        renglones: b.renglones.map((r) => ({ codigo: r.codigo, cantidad: r.cantidad })),
      });
      reproducir("ok");
      actualizar((x) => ({ ...x, resultado: vale }));
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
      setErrorEnvio({ tipo: "conexion", mensaje: "Sin conexión. El traspaso está guardado en este dispositivo." });
      return;
    }
    if (causa.reintentable) {
      setErrorEnvio({ tipo: "conexion", mensaje: causa.message });
      return;
    }
    if (causa.codigo === "VALE_CAMBIO" && causa.detalles) {
      const nueva = causa.detalles as unknown as EvaluacionApi;
      const marcas: Record<string, string> = {};
      for (const r of nueva.renglones) {
        if (r.nivel === "ROJO") marcas[claveDeCodigo(r.codigo)] = "Esto cambió mientras capturabas. Revísalo.";
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
    actualizar((b) => ({ ...b, almacenId: nuevo.id, destinoId: b.destinoId === nuevo.id ? null : b.destinoId }));
  };

  // ------------------------------------------------------------------ lo que se pinta
  const almacenNombre = evaluacion?.almacen.nombre ?? sesion.almacen?.nombre ?? null;

  const razonParaNoContinuar = (): string | null => {
    if (operaTodos && !borrador.almacenId) return "Elige el almacén que operas.";
    if (!borrador.destinoId) return "Elige a qué almacén se envía.";
    if (borrador.renglones.length === 0) return "Escanea al menos un artículo para continuar.";
    if (errorEvaluacion && !ev.actual) {
      return errorEvaluacion.sinConexion ? "Sin conexión: no podemos revisar la lista todavía." : "No pudimos revisar la lista.";
    }
    if (!evaluacion || !ev.actual || ev.evaluando) return "Revisando la lista…";
    const rojos = evaluados.filter((r) => r.nivel === "ROJO").length;
    if (rojos > 0) return `Quita ${rojos === 1 ? "el artículo en rojo" : `los ${rojos} artículos en rojo`} para continuar.`;
    if (!evaluacion.puede_confirmar) return evaluacion.motivos.find((m) => m.nivel === "ROJO")?.mensaje ?? "Revisa la lista para continuar.";
    return null;
  };

  const selectores = (
    <div className="flex flex-col gap-4">
      {operaTodos ? (
        <SelectorAlmacen valor={borrador.almacenId} alCambiar={elegirAlmacen} deshabilitado={borrador.renglones.length > 0} />
      ) : almacenNombre ? (
        <p className="text-sm text-muted-foreground">
          Sale de: <span className="font-semibold text-foreground">{almacenNombre}</span>
        </p>
      ) : null}
      <SelectorDestino
        origenId={borrador.almacenId}
        valor={borrador.destinoId}
        alCambiar={(a) => actualizar((b) => ({ ...b, destinoId: a.id, destinoNombre: a.nombre }))}
      />
    </div>
  );

  const bandas = (
    <div className="flex flex-col gap-3">
      {retomado ? (
        <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border bg-muted p-3 text-sm">
          <span className="flex items-center gap-2">
            <InfoIcon aria-hidden="true" className="size-5 shrink-0 text-marino" />
            Retomaste un traspaso que no terminaste.
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

  let contenido: React.ReactNode;
  let accion: React.ReactNode = null;

  if (!resultado) {
    const razon = razonParaNoContinuar();
    const reintento = errorEnvio?.tipo === "conexion";
    contenido = (
      <div className="flex flex-col gap-4">
        {selectores}
        {bandas}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
          <div className="order-2 flex min-w-0 flex-col gap-4 md:order-1">
            {errorEvaluacion && errorEvaluacion.codigo !== "ALMACEN_CAMBIO" ? (
              <section role="alert" className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
                <p className="flex items-start gap-2 text-base font-semibold">
                  {errorEvaluacion.sinConexion ? (
                    <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                  ) : (
                    <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                  )}
                  {errorEvaluacion.sinConexion ? "Sin conexión. Tu captura está guardada en este dispositivo." : errorEvaluacion.message}
                </p>
                <Boton variante="secundario" className="self-start" onClick={ev.reintentar}>
                  Reintentar
                </Boton>
              </section>
            ) : null}

            <MotivosDelVale motivos={evaluacion?.motivos ?? []} />

            {errorEnvio ? (
              <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
                <p className="flex items-start gap-2 text-base font-semibold">
                  {errorEnvio.tipo === "conexion" ? (
                    <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                  ) : (
                    <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                  )}
                  {errorEnvio.mensaje}
                </p>
                {errorEnvio.tipo === "conexion" ? <p className="text-base">Toca “Reintentar” cuando haya conexión o el sistema responda. No se guardará dos veces.</p> : null}
              </section>
            ) : null}

            <ListaRenglones
              key={String(inicial.retomado && !evaluacion)}
              renglones={evaluados}
              claveDe={(r) => claveDeCodigo(r.codigo)}
              anunciarAgregados={true}
              onQuitar={quitar}
              onCantidad={cambiarCantidad}
              notas={notas}
              textos={TEXTOS_NIVEL}
              deshabilitado={enviando}
              vacio={
                sinEvaluar.length === 0 ? (
                  <p className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                    {borrador.destinoId ? "Todavía no hay artículos. Escanea el primero o escribe su código." : "Elige primero a qué almacén se envía."}
                  </p>
                ) : null
              }
            />
            {sinEvaluar.length > 0 ? (
              <ul aria-label="Artículos por revisar" className="flex flex-col gap-2">
                {sinEvaluar.map((b) => (
                  <li key={b.codigo} className="rounded-2xl border border-dashed bg-muted p-3 text-sm">
                    <Cargando variante="en-linea" texto={`Revisando ${b.codigo}…`} className="justify-start p-0" />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <div className="order-1 flex flex-col gap-3 md:sticky md:top-4 md:order-2">
            <Escaner
              activo={!descartando && !resultadosBusqueda && !enviando && Boolean(borrador.destinoId)}
              sonidoAlLeer={false}
              onCodigo={(codigo, origen) => void alLeerArticulo(codigo, origen)}
              onRepetido={() => reproducir("aviso")}
              etiquetaCampo="Escribir código o nombre"
              placeholderCampo="Código, serie o nombre"
            />
            {buscandoArticulo ? <Cargando variante="en-linea" texto="Buscando…" /> : null}
          </div>
        </div>
      </div>
    );
    accion = (
      <AccionPrincipal nota={razon}>
        <Boton variante="principal" cargando={enviando} disabled={razon !== null && !reintento} onClick={() => void confirmar()}>
          {reintento ? "Reintentar" : "Confirmar traspaso"}
        </Boton>
      </AccionPrincipal>
    );
  } else {
    contenido = (
      <ResultadoTraspaso
        vale={resultado}
        titulo="Traspaso guardado"
        texto={`Traspaso a ${borrador.destinoNombre ?? "otro almacén"}`}
        nota={<p className="text-center">Lo enviado está en camino. El vale viaja con la carga: quien reciba lo escanea para abrir su recepción.</p>}
      />
    );
    accion = (
      <AccionPrincipal>
        <Boton variante="principal" onClick={empezarDeNuevo}>
          Nuevo traspaso
        </Boton>
      </AccionPrincipal>
    );
  }

  return (
    <Pantalla titulo="Trasladar" descripcion={resultado ? undefined : "Envía material a otro almacén."}>
      {!enLinea && !resultado ? (
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
        mensaje="¿Salir sin terminar el traspaso?"
        detalle="Lo que capturaste no se guardará."
        etiquetaConfirmar="Sí, salir"
        etiquetaCancelar="Seguir aquí"
        peligro
        alConfirmar={() => {
          borrarBorradorTraslado();
          if (bloqueo.state === "blocked") bloqueo.proceed();
        }}
      />
      <Confirmacion
        abierta={descartando}
        alCambiar={setDescartando}
        mensaje="¿Empezar un traspaso nuevo?"
        detalle="Se descartará lo que capturaste hasta ahora."
        etiquetaConfirmar="Sí, empezar de nuevo"
        etiquetaCancelar="Seguir con este"
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
