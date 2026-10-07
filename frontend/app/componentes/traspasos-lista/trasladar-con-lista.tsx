import { ArrowLeftIcon, CircleAlertIcon, InfoIcon, TriangleAlertIcon, WifiOffIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker } from "react-router";

import { Checkbox } from "~/components/ui/checkbox";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import {
  COLUMNAS_TRASPASO_VACIAS,
  confirmarTraspasoPorLista,
  mensajeTraspasoLista,
  vistaPreviaTraspaso,
  type ColumnasTraspaso,
  type TraspasoImportadoApi,
  type VistaPreviaTraspasoApi,
} from "~/api/traspasos-lista";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { reproducir } from "~/componentes/dominio/sonido";
import { EsqueletoTablaVista } from "~/componentes/importacion/tabla-vista-previa";
import type { Tabla } from "~/componentes/importacion/tipos";
import { SelectorAlmacen } from "~/componentes/entrega/selector-almacen";
import type { AlmacenResumen, ValeConfirmadoApi } from "~/componentes/entrega/tipos";
import { AccionPrincipal, Pantalla } from "~/componentes/pantalla";
import { ObservacionRuta } from "~/componentes/traspasos/observacion-ruta";
import { ResultadoTraspaso } from "~/componentes/traspasos/resultado-traspaso";
import { SelectorDestino } from "~/componentes/traspasos/selector-destino";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { IndicadorPasos } from "~/componentes/ui/indicador-pasos";
import { listaDeFilas } from "./lectura";
import { PasoArchivo } from "./paso-archivo";
import { PasoColumnasTraspaso } from "./paso-columnas";
import { TablaVistaTraspaso } from "./tabla-vista";

type Paso = "destino" | "archivo" | "columnas" | "revision" | "resultado";
const PASOS: { paso: Paso; nombre: string }[] = [
  { paso: "destino", nombre: "Destino" },
  { paso: "archivo", nombre: "Subir o pegar la lista" },
  { paso: "columnas", nombre: "Relacionar columnas" },
  { paso: "revision", nombre: "Revisar y confirmar" },
];

const plural = (n: number, uno: string, varios: string) => `${n} ${n === 1 ? uno : varios}`;

interface PropiedadesTrasladarConLista {
  operaTodos: boolean;
  /** Almacén de origen ya conocido (el de la sesión, o el último que eligió quien opera varios). */
  almacenInicialId: string | null;
  /** Nombre del almacén de la sesión, cuando no se puede elegir. */
  almacenNombre: string | null;
  /** Vuelve a Trasladar con escáner. */
  alSalir: () => void;
}

/**
 * «Trasladar con una lista» (FEAT-009): destino, archivo, columnas y vista previa en tabla; al confirmar se crea
 * UN traspaso. La interfaz solo muestra lo que evalúa el servidor; no decide ninguna regla.
 */
export function TrasladarConLista({ operaTodos, almacenInicialId, almacenNombre, alSalir }: PropiedadesTrasladarConLista) {
  const [paso, setPaso] = useState<Paso>("destino");
  const [almacenId, setAlmacenId] = useState<string | null>(almacenInicialId);
  const [destino, setDestino] = useState<AlmacenResumen | null>(null);
  const [tabla, setTabla] = useState<Tabla | null>(null);
  const [columnas, setColumnas] = useState<ColumnasTraspaso>(COLUMNAS_TRASPASO_VACIAS);
  const [textoPegado, setTextoPegado] = useState("");

  const [vista, setVista] = useState<VistaPreviaTraspasoApi | null>(null);
  const [cargandoVista, setCargandoVista] = useState(false);
  const [errorVista, setErrorVista] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);

  const [observacion, setObservacion] = useState("");
  const [errorObservacion, setErrorObservacion] = useState<string | null>(null);
  const [repetidoAceptado, setRepetidoAceptado] = useState(false);
  const [repetidoServidor, setRepetidoServidor] = useState<string | null>(null);
  const [dejarFuera, setDejarFuera] = useState(false);
  const [confirmandoDejarFuera, setConfirmandoDejarFuera] = useState(false);

  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const [errorEnvio, setErrorEnvio] = useState<{ tipo: "conexion" | "otro"; mensaje: string } | null>(null);
  const [resultado, setResultado] = useState<TraspasoImportadoApi | null>(null);
  // Un lote por archivo: tocar «Confirmar» dos veces o reintentar sin conexión no duplica el vale.
  const idLote = useRef<string>(crypto.randomUUID());

  const bloqueo = useBlocker(!resultado && (paso === "columnas" || paso === "revision"));

  // ------------------------------------------------------------------ vista previa
  useEffect(() => {
    if (paso !== "revision" || !tabla || !destino) return;
    const control = new AbortController();
    setCargandoVista(true);
    setErrorVista(null);
    vistaPreviaTraspaso(
      {
        filas: tabla.filas,
        columnas,
        primera_fila: tabla.primeraFila,
        destino_almacen_id: destino.id,
        almacen_id: operaTodos ? almacenId : null,
      },
      control.signal,
    )
      .then((v) => {
        setVista(v);
        setCargandoVista(false);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted) return;
        setVista(null);
        setErrorVista(mensajeTraspasoLista(causa, "No pudimos revisar la lista."));
        setCargandoVista(false);
      });
    return () => control.abort();
  }, [paso, tabla, columnas, destino, almacenId, operaTodos, recarga]);

  // Si ya no hay filas con error, «dejarlas fuera» deja de tener sentido.
  useEffect(() => {
    if (vista && vista.resumen.errores === 0 && dejarFuera) setDejarFuera(false);
  }, [vista, dejarFuera]);

  const nuevoArchivo = useCallback(() => {
    idLote.current = crypto.randomUUID();
    setVista(null);
    setDejarFuera(false);
    setRepetidoAceptado(false);
    setRepetidoServidor(null);
    setErrorEnvio(null);
    setErrorObservacion(null);
  }, []);

  const volver = () => {
    if (paso === "destino") alSalir();
    else if (paso === "archivo") setPaso("destino");
    else if (paso === "columnas") setPaso("archivo");
    else if (paso === "revision") setPaso("columnas");
  };

  // ------------------------------------------------------------------ confirmar
  const filasConError = vista?.filas.filter((f) => f.nivel === "ROJO").map((f) => f.fila) ?? [];
  const confirmables = vista ? vista.resumen.ok + vista.resumen.avisos : 0;
  const repetidoFecha = vista?.archivo_repetido?.fecha ?? repetidoServidor;

  const razonParaNoConfirmar = (): string | null => {
    if (cargandoVista || !vista) return "Revisando la lista…";
    if (vista.resumen.excedido) return "La lista pasa de 500 renglones. Divídela en varios archivos.";
    if (vista.ruta.nivel === "ROJO") return vista.ruta.mensaje;
    if (vista.resumen.errores > 0 && !dejarFuera) {
      return `${plural(vista.resumen.errores, "fila tiene", "filas tienen")} error. Corrige el archivo o deja fuera esas filas.`;
    }
    if (confirmables === 0) return "No queda ninguna fila para enviar.";
    if (vista.ruta.pide_observacion && !observacion.trim()) return "Escribe por qué se envía por esta ruta para continuar.";
    if (repetidoFecha && !repetidoAceptado) return "Marca que entiendes que este archivo ya se usó para continuar.";
    return null;
  };

  const confirmar = async () => {
    if (enviandoRef.current || !tabla || !destino || !vista) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    setErrorObservacion(null);
    try {
      const r = await confirmarTraspasoPorLista({
        filas: tabla.filas,
        columnas,
        primera_fila: tabla.primeraFila,
        destino_almacen_id: destino.id,
        almacen_id: operaTodos ? almacenId : null,
        id_lote: idLote.current,
        observacion: vista.ruta.pide_observacion ? observacion.trim() : null,
        dejar_fuera_errores: dejarFuera,
        confirmar_repetido: repetidoAceptado,
      });
      reproducir("ok");
      setResultado(r);
      setPaso("resultado");
    } catch (causa) {
      reproducir("bloqueo");
      atenderError(causa);
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  };

  const atenderError = (causa: unknown) => {
    if (!esErrorApi(causa)) {
      setErrorEnvio({ tipo: "otro", mensaje: mensajeDeError(causa) });
      return;
    }
    if (causa.sinConexion || causa.reintentable) {
      setErrorEnvio({ tipo: "conexion", mensaje: causa.sinConexion ? "Sin conexión. Tu lista sigue aquí." : causa.message });
      return;
    }
    if (causa.codigo === "ARCHIVO_REPETIDO") {
      const fecha = typeof causa.detalles?.fecha === "string" ? causa.detalles.fecha : "";
      setRepetidoServidor(fecha || "ya");
      setErrorEnvio({ tipo: "otro", mensaje: "Este archivo ya se usó en otro traspaso. Marca que lo entiendes para enviarlo de todos modos." });
      return;
    }
    if (causa.codigo === "FILAS_CON_ERROR") {
      setRecarga((n) => n + 1);
      setErrorEnvio({ tipo: "otro", mensaje: "Hay filas con error. Revisa la lista de nuevo." });
      return;
    }
    if (causa.codigo === "TRASPASO_MUY_GRANDE") {
      setErrorEnvio({ tipo: "otro", mensaje: "La lista pasa de 500 renglones. Divídela en varios archivos y sube uno por traspaso." });
      return;
    }
    if (causa.codigo === "RUTA_SOLO_ADMINISTRADOR") {
      setErrorEnvio({
        tipo: "otro",
        mensaje: "Esta ruta no es la habitual y solo la puede hacer un administrador. Elige otro destino: el almacén del que depende este, o uno que dependa de él.",
      });
      return;
    }
    const detalle = Array.isArray(causa.detalles) ? (causa.detalles as { campo?: string; mensaje?: string }[]) : [];
    const deObservacion = detalle.find((d) => d.campo === "observacion");
    if (causa.status === 422 && deObservacion) {
      setErrorObservacion(deObservacion.mensaje ?? "Escribe por qué se envía por esta ruta.");
      return;
    }
    setErrorEnvio({ tipo: "otro", mensaje: mensajeTraspasoLista(causa, causa.message) });
  };

  // ------------------------------------------------------------------ lo que se pinta
  const indicePaso = PASOS.findIndex((p) => p.paso === paso);
  const razon = paso === "revision" ? razonParaNoConfirmar() : null;
  const reintento = errorEnvio?.tipo === "conexion";

  let contenido: React.ReactNode;
  if (paso === "resultado" && resultado) {
    const vale: ValeConfirmadoApi = {
      id: resultado.vale.id,
      folio: resultado.vale.folio,
      token: resultado.vale.token,
      creado_en: resultado.vale.creado_en ?? new Date().toISOString(),
      renglones: [],
    };
    const fuera = resultado.filas_dejadas_fuera;
    contenido = (
      <>
        <ResultadoTraspaso
          vale={vale}
          titulo="Traspaso guardado"
          texto={`Traspaso a ${resultado.vale.destino.nombre}`}
          nota={
            <div className="flex flex-col gap-2 text-center">
              <p>
                Salieron {plural(resultado.resumen.unidades, "unidad", "unidades")} en {plural(resultado.vale.renglones, "renglón", "renglones")}. Lo enviado está en camino: quien reciba escanea el vale para abrir su recepción.
              </p>
              {resultado.repetida ? <p className="font-semibold">Este traspaso ya se había guardado; no se duplicó.</p> : null}
              {fuera.length > 0 ? (
                <p className="font-semibold">
                  Se dejaron fuera {plural(fuera.length, "fila", "filas")}: {listaDeFilas(fuera.map((f) => f.fila))}.
                </p>
              ) : null}
            </div>
          }
        />
      </>
    );
  } else if (paso === "destino") {
    contenido = (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">Todo el archivo va a un solo almacén. Si la ruta no es la habitual, la pantalla de revisión te pedirá el motivo.</p>
        {operaTodos ? (
          <SelectorAlmacen
            valor={almacenId}
            alCambiar={(a) => {
              setAlmacenId(a.id);
              setDestino((d) => (d?.id === a.id ? null : d));
            }}
          />
        ) : almacenNombre ? (
          <p className="text-sm text-muted-foreground">
            Sale de: <span className="font-semibold text-foreground">{almacenNombre}</span>
          </p>
        ) : null}
        <SelectorDestino origenId={almacenId} valor={destino?.id ?? null} soloHabituales={!operaTodos} alCambiar={setDestino} />
        <AccionPrincipal nota={!destino ? "Elige a qué almacén se envía." : null}>
          <Boton variante="principal" disabled={!destino || (operaTodos && !almacenId)} onClick={() => setPaso("archivo")}>
            Continuar
          </Boton>
        </AccionPrincipal>
      </div>
    );
  } else if (paso === "archivo" && destino) {
    contenido = (
      <PasoArchivo
        destinoId={destino.id}
        almacenId={operaTodos ? almacenId : null}
        textoInicial={textoPegado}
        alCambiarTexto={setTextoPegado}
        alTener={(t, c) => {
          nuevoArchivo();
          setTabla(t);
          setColumnas(c);
          setPaso("columnas");
        }}
      />
    );
  } else if (paso === "columnas" && tabla) {
    contenido = <PasoColumnasTraspaso tabla={tabla} columnas={columnas} alCambiar={setColumnas} alContinuar={() => { setVista(null); setPaso("revision"); }} />;
  } else if (paso === "revision") {
    contenido = (
      <div className="flex flex-col gap-4">
        {cargandoVista && !vista ? <EsqueletoTablaVista columnas={6} /> : null}
        {errorVista ? (
          <section role="alert" className="flex flex-col gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
            <p className="flex items-start gap-2 text-base font-semibold">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              {errorVista}
            </p>
            <div className="flex flex-wrap gap-2">
              <Boton variante="secundario" onClick={() => setRecarga((n) => n + 1)}>
                Reintentar
              </Boton>
              <Boton variante="contorno" onClick={() => setPaso("archivo")}>
                Subir otro archivo
              </Boton>
            </div>
          </section>
        ) : null}

        {vista ? (
          <>
            {vista.ruta.habitual ? (
              <p role="status" className="flex items-center gap-2 rounded-2xl border bg-muted p-3 text-sm">
                <InfoIcon aria-hidden="true" className="size-5 shrink-0 text-marino" />
                Ruta habitual: {vista.origen.nombre} a {vista.destino.nombre}
              </p>
            ) : vista.ruta.nivel === "ROJO" ? (
              <p role="alert" className="flex items-start gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-semibold">
                <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-rojo" />
                {vista.ruta.mensaje}
              </p>
            ) : (
              <>
                <p role="status" className="flex items-center gap-2 text-sm font-semibold">
                  <TriangleAlertIcon aria-hidden="true" className="size-5 shrink-0 text-semaforo-amarillo" />
                  Ruta no habitual: {vista.origen.nombre} a {vista.destino.nombre}
                </p>
                {vista.ruta.pide_observacion ? (
                  <ObservacionRuta
                    valor={observacion}
                    alCambiar={(t) => {
                      setErrorObservacion(null);
                      setObservacion(t);
                    }}
                    error={errorObservacion}
                    deshabilitado={enviando}
                  />
                ) : null}
              </>
            )}

            {repetidoFecha ? (
              <section className="flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
                <p className="flex items-start gap-2 text-base font-semibold">
                  <TriangleAlertIcon aria-hidden="true" strokeWidth={2.5} className="mt-0.5 size-5 shrink-0 text-semaforo-amarillo" />
                  {vista.archivo_repetido ? `Este archivo ya se usó el ${formatearFechaHora(vista.archivo_repetido.fecha)}.` : "Este archivo ya se usó en otro traspaso."}
                </p>
                <label className="flex min-h-12 cursor-pointer items-center gap-3 text-base font-medium">
                  <Checkbox checked={repetidoAceptado} onCheckedChange={(m) => setRepetidoAceptado(m)} className="size-6 rounded-md [&_svg]:size-4" />
                  Entiendo, enviarlo de todos modos
                </label>
              </section>
            ) : null}

            {vista.avisos.length > 0 ? (
              <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                {vista.avisos.map((a, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-marino" />
                    {a}
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="text-base">
              <span className="font-semibold">{plural(vista.resumen.unidades, "unidad", "unidades")}</span>
              {vista.resumen.piezas > 0 ? ` (${plural(vista.resumen.piezas, "pieza", "piezas")})` : ""} saldrían de {vista.origen.nombre} hacia {vista.destino.nombre}.
            </p>

            {vista.resumen.errores > 0 ? (
              dejarFuera ? (
                <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">
                  <span className="flex items-start gap-2 font-medium">
                    <TriangleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-amarillo" />
                    Se dejan fuera {plural(filasConError.length, "fila", "filas")}: {listaDeFilas(filasConError)}. No se enviarán.
                  </span>
                  <Boton variante="texto" onClick={() => setDejarFuera(false)}>
                    Deshacer
                  </Boton>
                </p>
              ) : (
                <Boton variante="secundario" className="self-start" onClick={() => setConfirmandoDejarFuera(true)}>
                  Dejar fuera las filas con error
                </Boton>
              )
            ) : null}

            {vista.resumen.excedido ? (
              <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
                <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                La lista pasa de 500 renglones. Divídela en varios archivos y sube uno por traspaso.
              </p>
            ) : null}

            <TablaVistaTraspaso vista={vista} dejarFuera={dejarFuera} />
          </>
        ) : null}

        {errorEnvio ? (
          <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
            <p className="flex items-start gap-2 text-base font-semibold">
              {errorEnvio.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
              {errorEnvio.mensaje}
            </p>
            {reintento ? <p className="text-base">Toca “Reintentar” cuando haya conexión. No se guardará dos veces.</p> : null}
          </section>
        ) : null}

        <AccionPrincipal nota={razon}>
          <Boton variante="principal" cargando={enviando} disabled={razon !== null && !reintento} onClick={() => void confirmar()}>
            {reintento ? "Reintentar" : `Confirmar: salen ${plural(confirmables, "artículo", "artículos")} a ${destino?.nombre ?? "otro almacén"}`}
          </Boton>
        </AccionPrincipal>
      </div>
    );
  } else {
    contenido = null;
  }

  return (
    <Pantalla titulo="Trasladar con una lista" descripcion={paso === "resultado" ? undefined : "Arma un traspaso con una lista de Excel."}>
      {paso !== "resultado" ? (
        <div className="flex flex-col gap-3">
          <Boton variante="texto" className="self-start" onClick={volver}>
            <ArrowLeftIcon aria-hidden="true" />
            {paso === "destino" ? "Volver a escanear" : "Atrás"}
          </Boton>
          <IndicadorPasos actual={indicePaso + 1} total={PASOS.length} nombre={PASOS[indicePaso]?.nombre ?? ""} />
        </div>
      ) : null}
      {contenido}
      {paso === "resultado" ? (
        <AccionPrincipal>
          <Boton variante="principal" onClick={alSalir}>
            Nuevo traspaso
          </Boton>
        </AccionPrincipal>
      ) : null}

      <Confirmacion
        abierta={confirmandoDejarFuera}
        alCambiar={setConfirmandoDejarFuera}
        mensaje={`Se dejan fuera ${plural(filasConError.length, "fila", "filas")}: ${listaDeFilas(filasConError)}`}
        detalle="No se enviarán. El traspaso se guarda con el resto y queda anotado cuántas y cuáles filas se dejaron fuera."
        etiquetaConfirmar="Sí, dejarlas fuera"
        etiquetaCancelar="Corregir el archivo"
        peligro
        alConfirmar={() => {
          setConfirmandoDejarFuera(false);
          setDejarFuera(true);
        }}
      />
      <Confirmacion
        abierta={bloqueo.state === "blocked"}
        alCambiar={(abierta) => {
          if (!abierta && bloqueo.state === "blocked") bloqueo.reset();
        }}
        mensaje="¿Salir sin terminar el traspaso?"
        detalle="La lista que subiste no se guardará."
        etiquetaConfirmar="Sí, salir"
        etiquetaCancelar="Seguir aquí"
        peligro
        alConfirmar={() => {
          if (bloqueo.state === "blocked") bloqueo.proceed();
        }}
      />
    </Pantalla>
  );
}
