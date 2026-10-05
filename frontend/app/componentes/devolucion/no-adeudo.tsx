import { CircleCheckIcon, FileCheck2Icon } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router";

import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { FolioQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { nuevoIdCliente } from "~/componentes/entrega/borrador";
import type { ValeConfirmadoApi } from "~/componentes/entrega/tipos";
import { ListaPendientes } from "~/componentes/personas/pendientes";
import type { Pendiente } from "~/componentes/personas/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { useSesion } from "~/sesion/sesion";

/** `POST /api/trabajadores/{id}/no-adeudo`: el vale y cómo queda el trabajador (Inactivo, B-08). */
interface NoAdeudoApi extends ValeConfirmadoApi {
  trabajador: { id: string; numero_empleado: string; nombre: string; estado: string; estado_texto: string };
}

interface TrabajadorNoAdeudo {
  id: string;
  nombre: string;
  estado: string;
}

const NOTA_CONSUMIBLES = "Los consumibles (guantes, lentes, tapones…) no cuentan: solo lo que tiene que devolver.";

/** El botón "Emitir vale de no adeudo". Puede ponerse en más de un lugar de la pantalla; las ventanas van una sola vez. */
export function BotonNoAdeudo({ alAbrir, className }: { alAbrir: () => void; className?: string }) {
  return (
    <Boton variante="contorno" className={className} onClick={alAbrir}>
      <FileCheck2Icon aria-hidden="true" />
      Emitir vale de no adeudo
    </Boton>
  );
}

/**
 * "Emitir vale de no adeudo" (B-04, B-08): confirma en una frase, pide el vale al servidor y muestra el
 * resultado. Si el trabajador todavía debe equipo, el servidor responde la lista de lo que falta y aquí se
 * muestra con un "Recibir devolución" que abre Devolver con el trabajador ya identificado. Sin pendientes se
 * emite el vale (folio y QR) y el trabajador queda Inactivo.
 *
 * Devuelve `abrir` (para los botones) y `ventanas` (la confirmación y los resultados, que se pintan una sola
 * vez: al emitirse, el trabajador cambia de estado y el botón cambia de lugar, pero las ventanas siguen).
 */
export function useAccionNoAdeudo(trabajador: TrabajadorNoAdeudo | null, alCambiar: () => void) {
  const { puede } = useSesion();
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);
  const idCliente = useRef("");
  const [pendientes, setPendientes] = useState<Pendiente[] | null>(null);
  const [vale, setVale] = useState<NoAdeudoApi | null>(null);
  const [fallo, setFallo] = useState<{ sinConexion: boolean; mensaje: string } | null>(null);

  const abrir = () => {
    // Un doble toque o un reintento usan el mismo `id_cliente`: nunca se emiten dos vales.
    if (!idCliente.current) idCliente.current = nuevoIdCliente();
    setFallo(null);
    setConfirmando(true);
  };

  const emitir = async () => {
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setEnviando(true);
    setFallo(null);
    try {
      if (!trabajador) return;
      const r = await apiPost<NoAdeudoApi>(`/trabajadores/${trabajador.id}/no-adeudo`, { id_cliente: idCliente.current });
      idCliente.current = "";
      setConfirmando(false);
      setVale(r);
      alCambiar();
    } catch (causa) {
      if (esErrorApi(causa) && causa.codigo === "CON_PENDIENTES") {
        // El servidor ya dejó la baja en proceso; la lista dice qué falta.
        const lista = (causa.detalles?.pendientes as Pendiente[] | undefined) ?? [];
        idCliente.current = "";
        setConfirmando(false);
        setPendientes(lista);
        alCambiar();
      } else if (esErrorApi(causa) && causa.sinConexion) {
        setFallo({ sinConexion: true, mensaje: "Sin conexión. No se emitió nada. Inténtalo otra vez cuando vuelva; no se emitirá dos veces." });
      } else {
        setFallo({ sinConexion: false, mensaje: mensajeDeError(causa) });
      }
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  };

  const activo = trabajador?.estado === "ACTIVO";
  const n = pendientes?.length ?? 0;
  const nombre = trabajador?.nombre ?? "el trabajador";

  const ventanas = (
    <>
      <Confirmacion
        abierta={confirmando}
        alCambiar={(abierta) => {
          if (!abierta && !enviando) setConfirmando(false);
        }}
        mensaje={`¿Emitir el vale de no adeudo de ${nombre}?`}
        detalle={
          fallo?.mensaje ??
          `${activo ? "Se iniciará su baja. " : ""}Si no debe nada, quedará Inactivo y no podrá recibir equipo hasta que lo reingresen. Si debe algo, te diremos qué falta. ${NOTA_CONSUMIBLES}`
        }
        etiquetaConfirmar={fallo?.sinConexion ? "Reintentar" : "Sí, emitir el vale"}
        etiquetaCancelar="No, volver"
        cargando={enviando}
        alConfirmar={() => void emitir()}
      />

      <Hoja
        abierta={pendientes !== null}
        alCambiar={(abierta) => {
          if (!abierta) setPendientes(null);
        }}
        titulo="Todavía debe devolver"
        descripcion={`${nombre} tiene ${n} ${n === 1 ? "pendiente" : "pendientes"}, de todos los almacenes. El vale de no adeudo se emite cuando no deba nada.`}
        pie={
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Boton variante="contorno" onClick={() => setPendientes(null)}>
              Cerrar
            </Boton>
            {puede("devoluciones.crear") ? (
              <Boton variante="normal" nativeButton={false} render={<Link to={`/devolver?trabajador=${trabajador?.id ?? ""}`} />}>
                Recibir devolución
              </Boton>
            ) : null}
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">{NOTA_CONSUMIBLES}</p>
          {pendientes ? <ListaPendientes pendientes={pendientes} /> : null}
        </div>
      </Hoja>

      <Hoja
        abierta={vale !== null}
        alCambiar={(abierta) => {
          if (!abierta) setVale(null);
        }}
        titulo="Vale de no adeudo emitido"
        pie={
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Boton variante="contorno" onClick={() => setVale(null)}>
              Cerrar
            </Boton>
            {vale ? (
              <Boton variante="normal" nativeButton={false} render={<Link to={`/vales/${vale.id}`} />}>
                Ver e imprimir el vale
              </Boton>
            ) : null}
          </div>
        }
      >
        {vale ? (
          <div className="flex flex-col items-center gap-4">
            <p role="status" className="flex items-center gap-2 text-base font-semibold">
              <CircleCheckIcon aria-hidden="true" className="size-6 text-semaforo-verde" strokeWidth={3} />
              Vale emitido
            </p>
            <FolioQR folio={vale.folio} valor={urlDeVale(vale.token)} texto={`Constancia de no adeudo · ${formatearFechaHora(vale.creado_en)}`} />
            <p className="text-center text-base">
              {vale.trabajador.nombre} quedó <span className="font-semibold">{vale.trabajador.estado_texto}</span>. Recursos Humanos lo verá como “No adeudo emitido”.
            </p>
          </div>
        ) : null}
      </Hoja>
    </>
  );

  return { abrir, ventanas };
}
