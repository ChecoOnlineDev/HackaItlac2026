import { XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router";

import { api } from "~/api/cliente";
import { esErrorApi, mensajeDeError, type ErrorApi } from "~/api/errores";
import { nuevoIdCliente } from "~/componentes/entrega/borrador";
import { PasoColumnas } from "~/componentes/importacion/paso-columnas";
import { PasoModo } from "~/componentes/importacion/paso-modo";
import { PasoPegar } from "~/componentes/importacion/paso-pegar";
import { PasoRevision, type ErrorConfirmacion } from "~/componentes/importacion/paso-revision";
import { PasosImportacion } from "~/componentes/importacion/pasos";
import { ResultadoImportacion } from "~/componentes/importacion/resultado-importacion";
import { columnasVacias, descargarTexto, filasConErrorACsv, proponerColumnas } from "~/componentes/importacion/tabla";
import {
  CAMPOS,
  camposDelModo,
  type CategoriaDesconocida,
  type Columnas,
  type FilaError,
  type ImportacionApi,
  type ModoImportacion,
  type OpcionesImportacion,
  type Tabla,
  type VistaPreviaApi,
} from "~/componentes/importacion/tipos";
import { BotonAtrasPaso, usarAtrasDePasos } from "~/componentes/navegacion/atras";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "inventario.entradas" };

// 1 modo, 2 pegar o subir, 3 columnas, 4 revisar y confirmar, 5 resultado.
type Paso = 1 | 2 | 3 | 4 | 5;

const OPCIONES_VACIAS: OpcionesImportacion = { categoriaPorDefectoId: null, mapaCategorias: {}, categoriaPorFila: {}, almacenPorDefecto: null };

/** El cuerpo de la vista previa y de la confirmación: es el mismo, y la confirmación solo agrega `id_lote`. */
function cuerpoDe(modo: ModoImportacion, tabla: Tabla, columnas: Columnas, opciones: OpcionesImportacion, puedeCostos: boolean) {
  const delModo = camposDelModo(modo);
  const alta = modo === "ALTA";
  return {
    modo,
    filas: tabla.filas,
    // En reposición solo se mandan los datos que ese modo lee.
    columnas: Object.fromEntries(CAMPOS.map((c) => [c, !delModo.includes(c) || (c === "costo" && !puedeCostos) ? null : columnas[c]])),
    primera_fila: tabla.primeraFila,
    categoria_por_defecto_id: alta ? opciones.categoriaPorDefectoId : null,
    mapa_categorias: alta ? opciones.mapaCategorias : {},
    // Solo lo que la persona eligió o aceptó viendo la fila: la sugerencia nunca viaja sola (I-14).
    categoria_por_fila: alta ? opciones.categoriaPorFila : {},
    almacen_por_defecto: opciones.almacenPorDefecto,
  };
}

export default function Importar() {
  const { puede } = useSesionActiva();
  const puedeCostos = puede("catalogo.costos");

  const [paso, setPaso] = useState<Paso>(1);
  const [modo, setModo] = useState<ModoImportacion>("ALTA");
  const [texto, setTexto] = useState("");
  const [tabla, setTabla] = useState<Tabla | null>(null);
  const [columnas, setColumnas] = useState<Columnas>(columnasVacias());
  const [opciones, setOpciones] = useState<OpcionesImportacion>(OPCIONES_VACIAS);

  const [vista, setVista] = useState<VistaPreviaApi | null>(null);
  const [desconocidas, setDesconocidas] = useState<CategoriaDesconocida[]>([]);
  const [cargandoVista, setCargandoVista] = useState(false);
  const [errorVista, setErrorVista] = useState<unknown>(null);
  const [intentoVista, setIntentoVista] = useState(0);

  const [confirmando, setConfirmando] = useState(false);
  const confirmandoRef = useRef(false);
  const [pidiendoConfirmacion, setPidiendoConfirmacion] = useState(false);
  const [errorConfirmacion, setErrorConfirmacion] = useState<ErrorConfirmacion | null>(null);
  const [avisoCambio, setAvisoCambio] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ImportacionApi | null>(null);
  // I-12: el archivo ya se había importado. La casilla "Entiendo, importar de nuevo" manda `confirmar_repetido`.
  const [fechaRepetido, setFechaRepetido] = useState<string | null>(null);
  const [repetidoAceptado, setRepetidoAceptado] = useState(false);
  const [cancelando, setCancelando] = useState(false);

  // El `id_lote` se genera una vez por importación y se REUTILIZA al reintentar (así un reintento nunca
  // duplica). Si cambia lo que se va a importar, es otra importación y lleva otro lote.
  const lote = useRef<{ clave: string; id: string } | null>(null);
  const cuerpo = useMemo(() => (tabla ? cuerpoDe(modo, tabla, columnas, opciones, puedeCostos) : null), [modo, tabla, columnas, opciones, puedeCostos]);
  const claveCuerpo = useMemo(() => (cuerpo ? JSON.stringify(cuerpo) : null), [cuerpo]);
  const idLote = () => {
    if (!lote.current || lote.current.clave !== claveCuerpo) lote.current = { clave: claveCuerpo ?? "", id: nuevoIdCliente() };
    return lote.current.id;
  };

  // ------------------------------------------------------------------ vista previa (paso 3)
  useEffect(() => {
    if (paso !== 4 || !cuerpo) return;
    const control = new AbortController();
    setCargandoVista(true);
    const espera = window.setTimeout(() => {
      api<VistaPreviaApi>("/importacion/vista-previa", { metodo: "POST", cuerpo, signal: control.signal })
        .then((r) => {
          setVista(r);
          if (r.categorias_desconocidas.length > 0) {
            setDesconocidas((previas) => {
              const mapa = new Map(previas.map((c) => [c.nombre, c] as const));
              for (const c of r.categorias_desconocidas) mapa.set(c.nombre, c);
              return [...mapa.values()];
            });
          }
          setErrorVista(null);
          setCargandoVista(false);
        })
        .catch((causa: unknown) => {
          if (control.signal.aborted || (causa instanceof DOMException && causa.name === "AbortError")) return;
          setErrorVista(causa);
          setCargandoVista(false);
        });
    }, 200);
    return () => {
      window.clearTimeout(espera);
      control.abort();
    };
  }, [paso, cuerpo, intentoVista]);

  // ------------------------------------------------------------------ acciones
  const hayDatos = tabla !== null && paso !== 5;
  const bloqueo = useBlocker(hayDatos);

  const empezarDeNuevo = useCallback(() => {
    lote.current = null;
    setPaso(1);
    setModo("ALTA");
    setFechaRepetido(null);
    setRepetidoAceptado(false);
    setTexto("");
    setTabla(null);
    setColumnas(columnasVacias());
    setOpciones(OPCIONES_VACIAS);
    setVista(null);
    setDesconocidas([]);
    setErrorVista(null);
    setErrorConfirmacion(null);
    setAvisoCambio(null);
    setResultado(null);
  }, []);

  const cambiarModo = (m: ModoImportacion) => {
    if (m === modo) return;
    // Otro modo es otra importación: lo que se había revisado ya no vale.
    setModo(m);
    setOpciones(OPCIONES_VACIAS);
    setVista(null);
    setDesconocidas([]);
    setFechaRepetido(null);
    setRepetidoAceptado(false);
    setErrorConfirmacion(null);
  };

  const alContinuarConTexto = (t: Tabla) => {
    setTabla(t);
    setColumnas(t.encabezados ? proponerColumnas(t.encabezados) : columnasVacias());
    setOpciones(OPCIONES_VACIAS);
    setVista(null);
    setDesconocidas([]);
    setFechaRepetido(null);
    setRepetidoAceptado(false);
    setPaso(3);
  };
  const alSubirArchivo = (t: Tabla, propuestas: Columnas) => {
    setTabla(t);
    setColumnas(propuestas);
    setOpciones(OPCIONES_VACIAS);
    setVista(null);
    setDesconocidas([]);
    setFechaRepetido(null);
    setRepetidoAceptado(false);
    setPaso(3);
  };

  const descargar = (filas: FilaError[]) => {
    descargarTexto("filas-con-error.csv", filasConErrorACsv(filas));
  };

  const confirmar = async () => {
    if (confirmandoRef.current || !cuerpo) return;
    confirmandoRef.current = true;
    setConfirmando(true);
    setErrorConfirmacion(null);
    setAvisoCambio(null);
    try {
      const r = await api<ImportacionApi>("/importacion", {
        metodo: "POST",
        cuerpo: { ...cuerpo, id_lote: idLote(), confirmar_repetido: repetidoAceptado },
      });
      setResultado(r);
      setPaso(5);
    } catch (causa) {
      atenderError(causa);
    } finally {
      confirmandoRef.current = false;
      setConfirmando(false);
    }
  };

  const atenderError = (causa: unknown) => {
    if (!esErrorApi(causa)) {
      setErrorConfirmacion({ tipo: "otro", mensaje: mensajeDeError(causa) });
      return;
    }
    const e: ErrorApi = causa;
    if (e.status === 409 && e.codigo === "ARCHIVO_REPETIDO") {
      // I-12: nada se guardó; se pide aceptar expresamente y se vuelve a confirmar.
      const fecha = e.detalles?.fecha;
      setFechaRepetido(typeof fecha === "string" ? fecha : "");
      setRepetidoAceptado(false);
      return;
    }
    if (e.sinConexion) {
      setErrorConfirmacion({ tipo: "conexion", mensaje: "Sin conexión. No sabemos si la importación alcanzó a guardarse." });
    } else if (e.status === 409) {
      // Algo cambió desde la vista previa: no se guardó nada; se vuelve a revisar.
      setAvisoCambio(e.message);
      setIntentoVista((n) => n + 1);
    } else {
      setErrorConfirmacion({ tipo: "otro", mensaje: e.message });
      if (e.status === 422) setIntentoVista((n) => n + 1);
    }
  };

  // Los errores de una importación fallida no deben quedarse al cambiar de paso.
  useEffect(() => {
    setErrorConfirmacion(null);
  }, [paso]);

  const filasErrorResultado = resultado ? (resultado.filas_error.length > 0 ? resultado.filas_error : (vista?.filas_error ?? [])) : [];

  // ------------------------------------------------------------------ encabezado
  const volverPaso =
    paso === 2 ? () => setPaso(1) : paso === 3 ? () => setPaso(2) : paso === 4 ? () => (confirmando ? undefined : setPaso(3)) : null;
  usarAtrasDePasos(volverPaso);
  const atras = volverPaso ? <BotonAtrasPaso alVolver={volverPaso} deshabilitado={paso === 4 && confirmando} /> : null;

  return (
    <Pantalla
      titulo="Importar desde Excel"
      descripcion={paso === 5 ? undefined : "Carga artículos y existencias desde una tabla. No se guarda nada hasta que confirmes."}
      acciones={
        tabla && paso !== 5 ? (
          <Boton variante="contorno" disabled={confirmando} onClick={() => setCancelando(true)}>
            <XIcon aria-hidden="true" />
            Cancelar
          </Boton>
        ) : null
      }
    >
      <div className="flex max-w-5xl flex-col gap-6 pb-24 lg:pb-0">
        <PasosImportacion actual={paso} />
        {atras}

        {paso === 1 ? <PasoModo modo={modo} alCambiar={cambiarModo} alContinuar={() => setPaso(2)} /> : null}

        {paso === 2 ? (
          <PasoPegar modo={modo} textoInicial={texto} alCambiarTexto={setTexto} alContinuarConTexto={alContinuarConTexto} alSubirArchivo={alSubirArchivo} />
        ) : null}

        {paso === 3 && tabla ? (
          <PasoColumnas
            modo={modo}
            tabla={tabla}
            columnas={columnas}
            alCambiar={(c) => {
              setColumnas(c);
              setVista(null);
              setDesconocidas([]);
              setOpciones(OPCIONES_VACIAS);
            }}
            puedeCostos={puedeCostos}
            alContinuar={() => setPaso(4)}
          />
        ) : null}

        {paso === 4 ? (
          <PasoRevision
            modo={modo}
            vista={vista}
            desconocidas={desconocidas}
            cargando={cargandoVista}
            error={errorVista}
            alReintentar={() => setIntentoVista((n) => n + 1)}
            opciones={opciones}
            alCambiarOpciones={setOpciones}
            confirmando={confirmando}
            errorConfirmacion={errorConfirmacion}
            avisoCambio={avisoCambio}
            fechaRepetido={fechaRepetido}
            repetidoAceptado={repetidoAceptado}
            alAceptarRepetido={setRepetidoAceptado}
            alConfirmar={() => {
              // Un reintento tras un corte de red va directo: ya se confirmó la intención y el lote es el mismo.
              if (errorConfirmacion?.tipo === "conexion") void confirmar();
              else setPidiendoConfirmacion(true);
            }}
            alDescargarErrores={descargar}
          />
        ) : null}

        {paso === 5 && resultado ? (
          <>
            <ResultadoImportacion resultado={resultado} filasError={filasErrorResultado} alDescargarErrores={descargar} />
            <AccionPrincipal>
              <Boton variante="principal" onClick={empezarDeNuevo}>
                Importar otra tabla
              </Boton>
            </AccionPrincipal>
          </>
        ) : null}
      </div>

      <Confirmacion
        abierta={pidiendoConfirmacion}
        alCambiar={setPidiendoConfirmacion}
        mensaje={`¿Importar ${vista?.resumen.validas ?? 0} ${vista?.resumen.validas === 1 ? "fila" : "filas"}?`}
        detalle={
          vista
            ? [
                modo === "ALTA"
                  ? `Se crearán ${vista.resumen.articulos_nuevos} ${vista.resumen.articulos_nuevos === 1 ? "artículo nuevo" : "artículos nuevos"} y ${vista.resumen.almacenes} ${vista.resumen.almacenes === 1 ? "vale de entrada" : "vales de entrada"} (uno por almacén).`
                  : `Se sumará a artículos que ya existen, con ${vista.resumen.almacenes} ${vista.resumen.almacenes === 1 ? "vale de entrada" : "vales de entrada"} (uno por almacén). No se crea ningún artículo.`,
                vista.resumen.con_error > 0
                  ? `${vista.resumen.con_error === 1 ? "La fila con error no se importa" : `Las ${vista.resumen.con_error} filas con error no se importan`}.`
                  : "",
              ]
                .filter(Boolean)
                .join(" ")
            : undefined
        }
        etiquetaConfirmar="Sí, importar"
        etiquetaCancelar="Seguir revisando"
        alConfirmar={() => {
          setPidiendoConfirmacion(false);
          void confirmar();
        }}
      />
      <Confirmacion
        abierta={cancelando}
        alCambiar={setCancelando}
        mensaje="¿Cancelar la importación?"
        detalle="No se guardó nada. Tendrías que pegar la tabla otra vez."
        etiquetaConfirmar="Sí, cancelar"
        etiquetaCancelar="Seguir aquí"
        peligro
        alConfirmar={() => {
          setCancelando(false);
          empezarDeNuevo();
          aviso({ titulo: "Importación cancelada", descripcion: "No se guardó nada.", tipo: "info" });
        }}
      />
      <Confirmacion
        abierta={bloqueo.state === "blocked"}
        alCambiar={(abierta) => {
          if (!abierta && bloqueo.state === "blocked") bloqueo.reset();
        }}
        mensaje="¿Salir sin importar?"
        detalle="No se guardó nada y se perderá la tabla."
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
