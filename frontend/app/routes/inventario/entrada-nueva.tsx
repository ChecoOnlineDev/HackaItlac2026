import { PackagePlusIcon, PencilIcon, TrashIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiGet, apiPost } from "~/api/cliente";
import { ErrorApi, esErrorApi, mensajeDeError } from "~/api/errores";
import { useEnLinea } from "~/api/red";
import { Seleccion } from "~/componentes/catalogo/campos";
import { Escaner } from "~/componentes/dominio/escaner";
import { RenglonSemaforo } from "~/componentes/dominio/renglon-semaforo";
import type { RenglonEvaluado } from "~/componentes/dominio/tipos";
import { BuscadorArticulos } from "~/componentes/entradas/buscador-articulos";
import { CapturaPieza } from "~/componentes/entradas/captura-pieza";
import { ResultadoEntrada } from "~/componentes/entradas/resultado-entrada";
import {
  cuerpoDeEntrada,
  type ArticuloFichaEntrada,
  type EvaluacionEntrada,
  type PiezaBorrador,
  type RenglonBorrador,
  type RenglonEvaluadoEntrada,
  type ValeConfirmado,
} from "~/componentes/entradas/tipos";
import { useBorradorEntrada } from "~/componentes/entradas/usar-borrador";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { useAlmacenesFiltro } from "~/componentes/reportes/listas";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "inventario.entradas" };

/** Los niveles del semáforo, con las palabras de una entrada. */
const TEXTOS_ENTRADA = {
  VERDE: "Listo",
  AMARILLO: "Aviso",
  NARANJA: "Requiere autorización",
  ROJO: "Corrígelo para guardar",
} as const;

interface EscaneoOut {
  tipo: "TRABAJADOR" | "ARTICULO" | "PIEZA" | "VALE" | "DESCONOCIDO";
  id: string | null;
}

interface Capturando {
  ficha: ArticuloFichaEntrada;
  /** Si se corrige una pieza ya agregada. */
  clave?: string;
  inicial?: PiezaBorrador;
}

interface EvaluacionGuardada {
  firma: string;
  datos: EvaluacionEntrada;
  /** Clave de cada renglón del borrador, en el orden en que se mandó. */
  claves: string[];
}

export default function EntradaNueva() {
  const { sesion, puede } = useSesionActiva();
  const puedeElegirAlmacen = puede("almacenes.todos");
  const enLinea = useEnLinea();
  const almacenes = useAlmacenesFiltro();
  const b = useBorradorEntrada(sesion.usuario.id);
  const { borrador } = b;

  const [capturando, setCapturando] = useState<Capturando | null>(null);
  const [codigoLeido, setCodigoLeido] = useState<{ valor: string; n: number } | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [descartar, setDescartar] = useState(false);

  const [evaluacion, setEvaluacion] = useState<EvaluacionGuardada | null>(null);
  const [evaluando, setEvaluando] = useState(false);
  const [errorEvaluacion, setErrorEvaluacion] = useState<unknown>(null);
  const [version, setVersion] = useState(0);

  const [enviando, setEnviando] = useState(false);
  const [errorConfirmacion, setErrorConfirmacion] = useState<string | null>(null);
  const [esperandoRed, setEsperandoRed] = useState(false);
  const [resultado, setResultado] = useState<{ vale: ValeConfirmado; almacen: string } | null>(null);
  const enviandoRef = useRef(false);

  // Kepler por defecto (I-01): las compras entran por ahí.
  useEffect(() => {
    if (!puedeElegirAlmacen || borrador.almacen_id || almacenes.opciones.length === 0) return;
    const kepler = almacenes.opciones.find((o) => o.clave === "KEP") ?? almacenes.opciones[0];
    b.cambiarAlmacen(kepler.valor);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [almacenes.opciones, borrador.almacen_id, puedeElegirAlmacen]);

  const cuerpo = useMemo(() => cuerpoDeEntrada(borrador, puedeElegirAlmacen), [borrador, puedeElegirAlmacen]);
  const firma = JSON.stringify(cuerpo);
  const clavesActuales = useMemo(() => borrador.renglones.map((r) => r.clave), [borrador.renglones]);

  // ---------------------------------------------------------------- evaluar (el servidor decide)
  useEffect(() => {
    if (borrador.renglones.length === 0) {
      setEvaluacion(null);
      setEvaluando(false);
      setErrorEvaluacion(null);
      return;
    }
    const control = new AbortController();
    const claves = clavesActuales;
    setEvaluando(true);
    const espera = window.setTimeout(() => {
      apiPost<EvaluacionEntrada>("/vales/evaluar", cuerpo, control.signal)
        .then((datos) => {
          if (control.signal.aborted) return;
          setEvaluacion({ firma, datos, claves });
          setErrorEvaluacion(null);
          setEvaluando(false);
        })
        .catch((causa: unknown) => {
          if (control.signal.aborted) return;
          setErrorEvaluacion(causa);
          setEvaluando(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(espera);
      control.abort();
    };
    // `firma` resume el cuerpo; al volver la conexión se revisa otra vez.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firma, enLinea, version]);

  const fresca = evaluacion?.firma === firma;
  const puedeConfirmar = Boolean(
    evaluacion && fresca && evaluacion.datos.puede_confirmar && !evaluando && !errorEvaluacion && borrador.renglones.length > 0,
  );

  // ---------------------------------------------------------------- agregar artículos
  const elegirArticulo = useCallback(
    async (articuloId: string) => {
      setBuscando(true);
      try {
        const ficha = await apiGet<ArticuloFichaEntrada>(`/articulos/${articuloId}`);
        if (ficha.control === "PIEZA" && ficha.activo) {
          setCapturando({ ficha });
          return;
        }
        // Un artículo inactivo se agrega igual: el servidor lo marca en rojo y dice por qué (I-09).
        b.agregarCantidad(ficha);
        aviso({
          titulo: `Se agregó ${ficha.nombre}`,
          tipo: "info",
          accion: { etiqueta: "Deshacer", alHacerClic: () => b.quitarUnoDe(ficha.id) },
        });
      } catch (causa) {
        aviso({ titulo: "No pudimos abrir el artículo", descripcion: mensajeDeError(causa), tipo: "error" });
      } finally {
        setBuscando(false);
      }
    },
    [b],
  );

  const alCodigo = useCallback(
    async (codigo: string) => {
      if (capturando) {
        setCodigoLeido((previo) => ({ valor: codigo, n: (previo?.n ?? 0) + 1 }));
        return;
      }
      setBuscando(true);
      try {
        const lectura = await apiGet<EscaneoOut>(`/escaneo/${encodeURIComponent(codigo)}`);
        if (lectura.tipo === "ARTICULO" && lectura.id) {
          await elegirArticulo(lectura.id);
        } else if (lectura.tipo === "PIEZA") {
          aviso({
            titulo: "Ese código ya es de una pieza",
            descripcion: "Para dar entrada, escanea el código del artículo.",
            tipo: "aviso",
          });
        } else {
          aviso({
            titulo: "No encontramos ese código",
            descripcion: "Revisa que sea de un artículo del catálogo o búscalo por nombre.",
            tipo: "aviso",
          });
        }
      } catch (causa) {
        aviso({ titulo: "No pudimos leer el código", descripcion: mensajeDeError(causa), tipo: "error" });
      } finally {
        setBuscando(false);
      }
    },
    [capturando, elegirArticulo],
  );

  function guardarPieza(pieza: PiezaBorrador, otra: boolean) {
    if (!capturando) return;
    if (capturando.clave) {
      b.corregirPieza(capturando.clave, pieza);
      setCapturando(null);
      return;
    }
    const clave = b.agregarPieza(capturando.ficha, pieza);
    aviso({
      titulo: `Se agregó ${capturando.ficha.nombre} ${pieza.codigo}`,
      tipo: "info",
      accion: { etiqueta: "Deshacer", alHacerClic: () => b.quitar(clave) },
    });
    if (!otra) setCapturando(null);
  }

  function corregir(r: RenglonBorrador) {
    if (!r.pieza) return;
    setCapturando({
      ficha: { id: r.articulo_id, codigo: r.codigo, nombre: r.nombre, marca: r.marca, control: "PIEZA", unidad: r.unidad, activo: true, requiere_inspeccion: r.requiere_inspeccion },
      clave: r.clave,
      inicial: r.pieza,
    });
  }

  // ---------------------------------------------------------------- confirmar
  const confirmar = useCallback(async () => {
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrorConfirmacion(null);
    try {
      const vale = await apiPost<ValeConfirmado>("/vales", { ...cuerpo, id_cliente: borrador.id_cliente });
      setEsperandoRed(false);
      setResultado({ vale, almacen: evaluacion?.datos.almacen.nombre ?? "" });
      b.reiniciar();
      setEvaluacion(null);
    } catch (causa) {
      if (causa instanceof ErrorApi && causa.sinConexion) {
        // Se conserva todo en este dispositivo y se reintenta solo con el mismo identificador.
        setEsperandoRed(true);
      } else {
        setEsperandoRed(false);
        setErrorConfirmacion(mensajeDeError(causa));
        // Si el vale cambió o hay un renglón con problema, se vuelve a revisar y se marca.
        if (esErrorApi(causa)) setVersion((v) => v + 1);
      }
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cuerpo, borrador.id_cliente, evaluacion]);

  // Con la entrada ya mandada y sin respuesta, se reintenta sola: al volver la conexión y cada 6 segundos.
  const confirmarRef = useRef(confirmar);
  useEffect(() => {
    confirmarRef.current = confirmar;
  });
  useEffect(() => {
    if (!esperandoRed) return;
    const reintentar = () => void confirmarRef.current();
    const id = window.setInterval(reintentar, 6000);
    window.addEventListener("online", reintentar);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("online", reintentar);
    };
  }, [esperandoRed]);

  function nuevaEntrada() {
    setResultado(null);
    setErrorConfirmacion(null);
    setCapturando(null);
  }

  // ---------------------------------------------------------------- pantalla
  if (resultado) {
    return (
      <Pantalla titulo="Nueva entrada" ancho="formulario">
        <ResultadoEntrada vale={resultado.vale} almacen={resultado.almacen} alNuevaEntrada={nuevaEntrada} />
      </Pantalla>
    );
  }

  const evaluadoPorClave = new Map<string, RenglonEvaluadoEntrada>();
  if (evaluacion) evaluacion.datos.renglones.forEach((r, i) => evaluacion.claves[i] && evaluadoPorClave.set(evaluacion.claves[i], r));

  const nota = !enLinea
    ? "Sin conexión: tu entrada está guardada en este dispositivo."
    : borrador.renglones.length === 0
      ? "Agrega al menos un artículo."
      : errorEvaluacion
        ? "No pudimos revisar la entrada."
        : evaluando || !fresca
          ? "Revisando la entrada…"
          : puedeConfirmar
            ? "Todo listo para guardar."
            : "Corrige los renglones marcados para poder guardar.";

  const bloqueado = enviando;

  return (
    <Pantalla titulo="Nueva entrada" descripcion="Registra lo que llega al almacén." ancho="formulario">
      <div className="flex flex-col gap-6 pb-32 lg:pb-0">
        {b.recuperado ? (
          <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-accent p-3 text-base">
            <span>Recuperamos la entrada que dejaste sin terminar.</span>
            <Boton variante="texto" className="h-10 px-3" onClick={b.descartarAviso}>
              Entendido
            </Boton>
          </p>
        ) : null}

        {puedeElegirAlmacen && almacenes.disponible ? (
          <Seleccion
            etiqueta="Almacén al que entra"
            value={borrador.almacen_id}
            opciones={almacenes.opciones}
            disabled={bloqueado}
            onChange={(e) => b.cambiarAlmacen(e.target.value)}
            ayuda="Las compras entran por Kepler."
          />
        ) : !puedeElegirAlmacen && sesion.almacen ? (
          <p className="text-base">
            Entra a tu almacén: <span className="font-semibold">{sesion.almacen.nombre} ({sesion.almacen.clave})</span>.
          </p>
        ) : null}

        <Escaner
          onCodigo={(codigo) => void alCodigo(codigo)}
          onRepetido={() => aviso({ titulo: "Ya lo leíste", tipo: "info", duracionMs: 1500 })}
          activo={!bloqueado}
          etiquetaCampo="Escribir código"
          placeholderCampo={capturando ? "Código de la pieza" : "Código del artículo"}
        />
        {buscando ? (
          <p role="status" className="text-muted-foreground">
            Buscando…
          </p>
        ) : null}

        {capturando ? (
          <CapturaPieza
            key={`${capturando.clave ?? "nueva"}-${capturando.ficha.id}`}
            articulo={capturando.ficha}
            inicial={capturando.inicial}
            codigoLeido={codigoLeido}
            alGuardar={guardarPieza}
            alCancelar={() => setCapturando(null)}
          />
        ) : (
          <BuscadorArticulos deshabilitado={bloqueado} alElegir={(id) => void elegirArticulo(id)} />
        )}

        <section aria-labelledby="renglones-entrada" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="renglones-entrada" className="text-lg font-bold text-marino">
              Lo que entra
              {borrador.renglones.length > 0 ? <span className="font-normal text-muted-foreground"> ({borrador.renglones.length})</span> : null}
            </h2>
            {borrador.renglones.length > 0 ? (
              <Boton variante="texto" className="h-10 px-3" disabled={bloqueado} onClick={() => setDescartar(true)}>
                <TrashIcon aria-hidden="true" />
                Vaciar entrada
              </Boton>
            ) : null}
          </div>

          {errorEvaluacion ? (
            <EstadoError
              error={errorEvaluacion}
              alReintentar={() => setVersion((v) => v + 1)}
              className="p-4"
            />
          ) : null}

          {borrador.renglones.length === 0 ? (
            <EstadoVacio
              icono={PackagePlusIcon}
              titulo="Todavía no hay nada en esta entrada"
              descripcion="Escanea el código de un artículo o búscalo por nombre."
            />
          ) : (
            <ul className="flex flex-col gap-3" aria-label="Renglones de la entrada">
              {borrador.renglones.map((r) => {
                const evaluado = evaluadoPorClave.get(r.clave);
                return (
                  <li key={r.clave} className="flex flex-col gap-2 animate-in fade-in slide-in-from-top-2 duration-150 motion-reduce:animate-none">
                    {evaluado ? (
                      <RenglonSemaforo
                        renglon={
                          {
                            ...evaluado,
                            cantidad: r.cantidad,
                            codigo: r.pieza ? r.pieza.codigo : evaluado.codigo,
                          } as unknown as RenglonEvaluado
                        }
                        textos={TEXTOS_ENTRADA}
                        cantidadMaxima={1_000_000}
                        deshabilitado={bloqueado}
                        onCantidad={(n) => b.cambiarCantidad(r.clave, n)}
                        onQuitar={() => b.quitar(r.clave)}
                      />
                    ) : (
                      <div className="flex flex-col gap-1 rounded-xl border p-3">
                        <p className="text-lg leading-tight font-semibold">{r.nombre}</p>
                        <p className="text-sm text-muted-foreground">
                          {r.pieza ? `Pieza ${r.pieza.codigo}` : r.codigo} · Cantidad {r.cantidad}
                        </p>
                        <p className="text-sm" role="status">
                          {errorEvaluacion || !enLinea ? "Guardado en este dispositivo; falta revisarlo." : "Revisando…"}
                        </p>
                        <div>
                          <Boton variante="texto" disabled={bloqueado} onClick={() => b.quitar(r.clave)}>
                            <TrashIcon aria-hidden="true" />
                            Quitar
                          </Boton>
                        </div>
                      </div>
                    )}
                    {r.pieza ? (
                      <div className="flex flex-wrap items-center gap-3 px-1 text-sm">
                        <span className="text-muted-foreground">
                          {r.pieza.numero_serie ? `Serie ${r.pieza.numero_serie}` : "Sin número de serie"}
                          {r.requiere_inspeccion
                            ? ` · Inspección: ${r.pieza.inspeccion ? (r.pieza.inspeccion.resultado === "APTO" ? "Apta" : "No apta") : "pendiente"}`
                            : ""}
                        </span>
                        <Boton variante="contorno" className="h-10 px-3 text-sm" disabled={bloqueado} onClick={() => corregir(r)}>
                          <PencilIcon aria-hidden="true" />
                          Corregir datos
                        </Boton>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {errorConfirmacion ? (
          <p role="alert" className="rounded-xl border-2 border-semaforo-rojo p-3 text-base font-semibold">
            {errorConfirmacion}
          </p>
        ) : null}
        {esperandoRed ? (
          <p role="status" className="rounded-xl border-2 border-semaforo-amarillo p-3 text-base font-semibold">
            Sin conexión. Tu entrada está guardada y se enviará sola cuando vuelva la conexión. No la captures otra vez.
          </p>
        ) : null}

        <AccionPrincipal nota={nota}>
          <Boton variante="principal" cargando={enviando} disabled={!puedeConfirmar && !esperandoRed} onClick={() => void confirmar()}>
            Confirmar entrada
          </Boton>
        </AccionPrincipal>
      </div>

      <Confirmacion
        abierta={descartar}
        alCambiar={setDescartar}
        mensaje="¿Vaciar esta entrada?"
        detalle="Se quitan todos los renglones que capturaste."
        etiquetaConfirmar="Sí, vaciar"
        etiquetaCancelar="Conservar"
        peligro
        alConfirmar={() => {
          b.reiniciar();
          setCapturando(null);
        }}
      />
    </Pantalla>
  );
}
