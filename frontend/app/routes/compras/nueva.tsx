import { useEffect, useRef, useState } from "react";

import { apiPost } from "~/api/cliente";
import { ErrorApi, esErrorApi, mensajeDeError } from "~/api/errores";
import { erroresPorCampo } from "~/componentes/catalogo/errores-campo";
import { useBorradorCompra } from "~/componentes/compras/solicitar/borrador";
import { Bloque, ChipsMotivo, ControlCantidad, OpcionesUrgencia } from "~/componentes/compras/solicitar/controles";
import { QueHaceFalta } from "~/componentes/compras/solicitar/que-hace-falta";
import { ResultadoSolicitud } from "~/componentes/compras/solicitar/resultado-solicitud";
import { ResumenSolicitud } from "~/componentes/compras/solicitar/resumen";
import { LARGO_MAXIMO_TEXTO, MOTIVOS_RAPIDOS, type SolicitudCompra } from "~/componentes/compras/solicitar/tipos";
import { almacenRecordado, recordarAlmacen, useAlmacenesParaPedir } from "~/componentes/compras/solicitar/usar-almacenes";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "compras.solicitar" };

const ID_MOTIVO = "motivo-compra";
const RAPIDOS_FIJOS: readonly string[] = MOTIVOS_RAPIDOS.filter((m) => m !== "Otro");

/** Campos que puede señalar el servidor, ligados al bloque donde se escriben. */
type CampoError = "que" | "cantidad" | "motivo" | "almacen";
const CAMPO_DE_SERVIDOR: Record<string, CampoError> = {
  articulo_id: "que",
  descripcion: "que",
  cantidad: "cantidad",
  motivo: "motivo",
  almacen_id: "almacen",
};

export default function PedirCompraUrgente() {
  const { sesion, puede } = useSesionActiva();
  const puedeElegirAlmacen = puede("almacenes.todos");
  const b = useBorradorCompra(sesion.usuario.id);
  const { borrador } = b;
  const almacenes = useAlmacenesParaPedir(puedeElegirAlmacen);

  const [errores, setErrores] = useState<Partial<Record<CampoError, string>>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [sinConexion, setSinConexion] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<SolicitudCompra | null>(null);
  const enviandoRef = useRef(false);

  // Quien opera todos los almacenes empieza con el último que operó en este dispositivo, si sigue activo.
  useEffect(() => {
    if (!puedeElegirAlmacen || !b.cargado || borrador.almacenId || almacenes.opciones.length === 0) return;
    const recordado = almacenRecordado();
    if (recordado && almacenes.opciones.some((o) => o.valor === recordado)) b.cambiar({ almacenId: recordado });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [almacenes.opciones, b.cargado, borrador.almacenId, puedeElegirAlmacen]);

  /** Un cambio en el formulario borra el aviso del campo y los de la última vez que se envió. */
  function editar(parcial: Parameters<typeof b.cambiar>[0], campo?: CampoError) {
    b.cambiar(parcial);
    if (campo) setErrores((e) => ({ ...e, [campo]: undefined }));
    setErrorGeneral(null);
  }

  const descripcion = borrador.descripcion.trim();
  const motivo = borrador.motivo.trim();
  const tieneQue = borrador.sinCatalogo ? descripcion !== "" : borrador.articulo !== null;
  const tieneAlmacen = puedeElegirAlmacen ? borrador.almacenId !== "" : sesion.almacen !== null;
  const completo = tieneQue && motivo !== "" && borrador.cantidad >= 1 && tieneAlmacen;

  const faltan: string[] = [];
  if (!tieneAlmacen && puedeElegirAlmacen) faltan.push("elegir el almacén");
  if (!tieneQue) faltan.push(borrador.sinCatalogo ? "describir lo que hace falta" : "elegir qué hace falta");
  if (motivo === "") faltan.push("decir para qué trabajo es");

  async function enviar() {
    if (enviandoRef.current || !completo) return;
    enviandoRef.current = true;
    setEnviando(true);
    setErrores({});
    setErrorGeneral(null);
    setSinConexion(false);
    try {
      // El mismo `id_cliente` en cada intento: si el primero sí llegó, el servidor devuelve esa misma solicitud.
      const solicitud = await apiPost<SolicitudCompra>("/solicitudes-compra", {
        id_cliente: borrador.idCliente,
        articulo_id: borrador.sinCatalogo ? undefined : borrador.articulo?.id,
        descripcion: borrador.sinCatalogo ? descripcion : undefined,
        cantidad: borrador.cantidad,
        motivo,
        urgencia: borrador.urgencia,
        almacen_id: puedeElegirAlmacen ? borrador.almacenId : undefined,
      });
      setResultado(solicitud);
      b.reiniciar();
    } catch (causa) {
      if (causa instanceof ErrorApi && causa.sinConexion) {
        setSinConexion(true);
      } else if (esErrorApi(causa) && causa.codigo === "ID_CLIENTE_EN_USO") {
        // Ese envío ya existía con otros datos: el siguiente intento lleva un identificador nuevo.
        b.renovarId();
        setErrorGeneral(
          "Ese envío ya se había guardado con otros datos. Revisa “Compras urgentes”: si tu solicitud no aparece, vuelve a tocar “Enviar solicitud”.",
        );
      } else if (esErrorApi(causa) && causa.status === 422) {
        const { campos, general } = erroresPorCampo(causa);
        const porBloque: Partial<Record<CampoError, string>> = {};
        for (const [campo, mensaje] of Object.entries(campos)) {
          const bloque = CAMPO_DE_SERVIDOR[campo];
          if (bloque) porBloque[bloque] ??= mensaje.replace(/^Value error, /, "");
        }
        setErrores(porBloque);
        if (Object.keys(porBloque).length === 0) setErrorGeneral(general ?? mensajeDeError(causa));
      } else {
        setErrorGeneral(mensajeDeError(causa));
      }
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  function pedirOtra() {
    setResultado(null);
    setErrores({});
    setErrorGeneral(null);
    setSinConexion(false);
  }

  if (resultado) {
    return (
      <Pantalla titulo="Pedir una compra urgente" ancho="formulario">
        <ResultadoSolicitud solicitud={resultado} alPedirOtra={pedirOtra} />
      </Pantalla>
    );
  }

  const nombreAlmacen = puedeElegirAlmacen
    ? (almacenes.opciones.find((o) => o.valor === borrador.almacenId)?.texto ?? null)
    : sesion.almacen
      ? `${sesion.almacen.nombre} (${sesion.almacen.clave})`
      : null;
  const que = borrador.sinCatalogo ? descripcion : (borrador.articulo?.nombre ?? "");

  return (
    <Pantalla
      titulo="Pedir una compra urgente"
      descripcion="Si falta un equipo o una herramienta que el almacén no tiene, avisa a Compras desde aquí."
      ancho="formulario"
    >
      <div className="flex flex-col gap-6 pb-40 lg:pb-0">
        {b.recuperado ? (
          <p role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border bg-accent p-3 text-sm">
            <span>Recuperamos la solicitud que dejaste sin terminar.</span>
            <Boton variante="texto" className="h-10 px-3" onClick={b.descartarAviso}>
              Entendido
            </Boton>
          </p>
        ) : null}

        {puedeElegirAlmacen ? (
          <Bloque id="bloque-almacen" titulo="Almacén" ayuda="La solicitud se hace a nombre de este almacén.">
            {almacenes.error ? (
              <EstadoError error={almacenes.error} alReintentar={almacenes.recargar} className="p-4" />
            ) : (
              <ListaDesplegable
                valor={borrador.almacenId}
                alCambiar={(v) => {
                  if (v) recordarAlmacen(v);
                  editar({ almacenId: v }, "almacen");
                }}
                opciones={almacenes.opciones}
                marcador={almacenes.cargando ? "Cargando almacenes…" : "Elige un almacén"}
                deshabilitado={enviando || almacenes.cargando}
                invalido={Boolean(errores.almacen)}
              />
            )}
            {errores.almacen ? (
              <p role="alert" className="text-sm font-medium text-destructive">
                {errores.almacen}
              </p>
            ) : null}
          </Bloque>
        ) : sesion.almacen ? (
          <p className="text-base">
            Se pide para tu almacén: <span className="font-semibold">{sesion.almacen.nombre} ({sesion.almacen.clave})</span>.
          </p>
        ) : (
          <p role="alert" className="rounded-2xl border border-semaforo-amarillo p-3 text-sm font-semibold">
            Todavía no tienes un almacén asignado. Pide a tu supervisor que te lo asigne para poder hacer solicitudes.
          </p>
        )}

        <Bloque id="bloque-que" titulo="¿Qué hace falta?">
          <QueHaceFalta
            sinCatalogo={borrador.sinCatalogo}
            articulo={borrador.articulo}
            descripcion={borrador.descripcion}
            deshabilitado={enviando}
            error={errores.que}
            alCambiar={(parcial) => editar(parcial, "que")}
          />
        </Bloque>

        <Bloque id="bloque-cantidad" titulo="¿Cuántas se necesitan?">
          <ControlCantidad
            valor={borrador.cantidad}
            alCambiar={(cantidad) => editar({ cantidad }, "cantidad")}
            deshabilitado={enviando}
            descripcion={que || undefined}
            error={errores.cantidad}
          />
        </Bloque>

        <Bloque id="bloque-motivo" titulo="¿Para qué trabajo?" ayuda="Dile a Compras para qué área o trabajo se necesita.">
          <ChipsMotivo
            motivo={borrador.motivo}
            otro={borrador.motivoOtro}
            deshabilitado={enviando}
            alElegir={(texto, otro) => {
              editar({ motivo: texto, motivoOtro: otro }, "motivo");
              if (otro) window.setTimeout(() => document.getElementById(ID_MOTIVO)?.focus(), 0);
            }}
          />
          <Campo
            id={ID_MOTIVO}
            etiqueta="Motivo"
            placeholder="Por ejemplo: Mantenimiento del laminador nuevo"
            value={borrador.motivo}
            maxLength={LARGO_MAXIMO_TEXTO}
            disabled={enviando}
            error={errores.motivo}
            autoComplete="off"
            onChange={(e) => {
              const texto = e.target.value;
              editar({ motivo: texto, motivoOtro: texto.trim() !== "" && !RAPIDOS_FIJOS.includes(texto) }, "motivo");
            }}
          />
        </Bloque>

        <Bloque id="bloque-urgencia" titulo="¿Qué tan urgente es?">
          <OpcionesUrgencia valor={borrador.urgencia} alCambiar={(urgencia) => editar({ urgencia })} deshabilitado={enviando} />
        </Bloque>

        <Bloque id="bloque-resumen" titulo="Tu solicitud">
          <ResumenSolicitud
            que={que}
            codigo={borrador.sinCatalogo ? null : borrador.articulo?.codigo}
            cantidad={borrador.cantidad}
            motivo={motivo}
            urgencia={borrador.urgencia}
            almacen={nombreAlmacen}
          />
        </Bloque>

        {errorGeneral ? (
          <p role="alert" className="rounded-2xl border border-semaforo-rojo p-3 text-sm font-semibold">
            {errorGeneral}
          </p>
        ) : null}
        {sinConexion ? (
          <p role="status" className="rounded-2xl border border-semaforo-amarillo p-3 text-sm font-semibold">
            Sin conexión. Tu solicitud está guardada en este dispositivo: cuando vuelva la señal, toca “Enviar solicitud” otra vez. No se duplicará.
          </p>
        ) : null}

        <AccionPrincipal nota={completo ? "Todo listo para enviar." : faltan.length > 0 ? `Falta ${faltan.join(" y ")}.` : undefined}>
          <Boton variante="principal" cargando={enviando} disabled={!completo} onClick={() => void enviar()}>
            Enviar solicitud
          </Boton>
        </AccionPrincipal>
      </div>
    </Pantalla>
  );
}
