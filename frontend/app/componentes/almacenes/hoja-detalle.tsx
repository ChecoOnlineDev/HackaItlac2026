import { BanIcon, PencilIcon, RotateCcwIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { fechaHoraMx } from "~/componentes/personas/formato";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { TEXTO_TIPO, plural, type BloqueoCierre, type FichaAlmacen } from "./tipos";

interface Propiedades {
  /** La ficha que se muestra; `null` mantiene la hoja cerrada. */
  almacen: FichaAlmacen | null;
  alCerrar: () => void;
  alEditar: (almacen: FichaAlmacen) => void;
  /** Cambió el estado del almacén: la lista se vuelve a pedir. */
  alCambiar: () => void;
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="flex flex-col rounded-xl border bg-card p-3">
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="text-base font-semibold text-marino tabular-nums">{valor}</dd>
    </div>
  );
}

const ENLACE = "inline-flex min-h-11 items-center rounded-xl px-3 text-sm font-medium text-primary underline-offset-4 hover:bg-accent/60 hover:underline";

/** Un motivo por el que no se puede inactivar, con lo que falta y a dónde ir para resolverlo. */
function Bloqueo({ bloqueo, almacenId }: { bloqueo: BloqueoCierre; almacenId: string }) {
  const extra = (() => {
    switch (bloqueo.codigo) {
      case "CON_EXISTENCIAS": {
        const articulos = bloqueo.articulos ?? [];
        const faltan = (bloqueo.total_articulos ?? articulos.length) - articulos.length;
        return articulos.length > 0 ? (
          <>
            <ul className="list-disc pl-5 text-sm">
              {articulos.map((a) => (
                <li key={a.articulo_id}>
                  {a.nombre} ({a.codigo}): {a.cantidad.toLocaleString("es-MX")}
                </li>
              ))}
            </ul>
            {faltan > 0 ? <p className="text-sm">y {plural(faltan, "artículo más", "artículos más")}.</p> : null}
            <Link to={`/inventario?almacen=${almacenId}`} className={ENLACE}>
              Ver su inventario
            </Link>
          </>
        ) : null;
      }
      case "CON_TRASPASOS_EN_TRANSITO":
        return bloqueo.traspasos && bloqueo.traspasos.length > 0 ? (
          <ul className="list-disc pl-5 text-sm">
            {bloqueo.traspasos.map((t) => (
              <li key={t.id}>
                {t.folio}: de {t.origen.nombre} a {t.destino.nombre}
              </li>
            ))}
          </ul>
        ) : null;
      case "CON_HIJOS_ACTIVOS":
        return bloqueo.hijos && bloqueo.hijos.length > 0 ? (
          <p className="text-sm">Dependen de él: {bloqueo.hijos.map((h) => h.nombre).join(", ")}.</p>
        ) : null;
      case "CON_USUARIOS":
        return (
          <>
            {bloqueo.usuarios && bloqueo.usuarios.length > 0 ? (
              <ul className="list-disc pl-5 text-sm">
                {bloqueo.usuarios.map((u) => (
                  <li key={u.id}>
                    {u.nombre} ({u.usuario})
                  </li>
                ))}
              </ul>
            ) : null}
            <Link to={`/personal?almacen=${almacenId}`} className={ENLACE}>
              Reasignarlos en Personal del almacén
            </Link>
          </>
        );
      default:
        return null;
    }
  })();
  return (
    <li className="flex flex-col gap-1 rounded-xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3">
      <p className="text-sm font-medium">{bloqueo.mensaje}</p>
      {extra}
    </li>
  );
}

/** La ficha de un almacén: su resumen, a dónde ir desde él y las acciones de inactivar, reactivar y editar. */
export function HojaDetalleAlmacen({ almacen, alCerrar, alEditar, alCambiar }: Propiedades) {
  const [confirmando, setConfirmando] = useState<"inactivar" | "reactivar" | null>(null);
  const [ocupado, setOcupado] = useState(false);
  // Lo que el servidor dijo en el último intento de inactivar: trae más detalle que la lista.
  const [bloqueosServidor, setBloqueosServidor] = useState<BloqueoCierre[] | null>(null);

  const id = almacen?.id ?? null;
  useEffect(() => {
    setBloqueosServidor(null);
    setConfirmando(null);
  }, [id]);

  const resumen = almacen?.resumen;
  const activo = almacen?.estado === "ACTIVO";
  const bloqueos = resumen?.puede_cerrar ? [] : (bloqueosServidor ?? resumen?.bloqueos_cierre ?? []);
  const puedeCerrar = activo && resumen?.puede_cerrar === true;

  async function inactivar() {
    if (!almacen) return;
    setOcupado(true);
    try {
      await apiPost(`/almacenes/${almacen.id}/cierre`, {});
      aviso({ titulo: `${almacen.nombre} quedó inactivo`, descripcion: "Su historial y sus reportes se conservan.", tipo: "exito" });
      alCambiar();
    } catch (causa) {
      const lista = esErrorApi(causa) ? (causa.detalles?.bloqueos as BloqueoCierre[] | undefined) : undefined;
      if (lista && lista.length > 0) {
        setBloqueosServidor(lista);
        aviso({ titulo: "Todavía no se puede inactivar", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
        alCambiar();
      } else {
        aviso({ titulo: "No se pudo inactivar", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
      }
    } finally {
      setOcupado(false);
      setConfirmando(null);
    }
  }

  async function reactivar() {
    if (!almacen) return;
    setOcupado(true);
    try {
      await apiPost(`/almacenes/${almacen.id}/reapertura`, {});
      aviso({ titulo: `${almacen.nombre} ya puede operar otra vez`, tipo: "exito" });
      alCambiar();
    } catch (causa) {
      aviso({ titulo: "No se pudo reactivar", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
      if (esErrorApi(causa)) alCambiar();
    } finally {
      setOcupado(false);
      setConfirmando(null);
    }
  }

  const padreCerrado = almacen && !activo && resumen?.puede_reabrir === false;

  return (
    <>
      <Hoja
        abierta={almacen !== null}
        alCambiar={(a) => !a && !ocupado && alCerrar()}
        titulo={almacen ? `${almacen.nombre} (${almacen.clave})` : "Almacén"}
        descripcion={
          almacen
            ? almacen.padre_clave
              ? `${TEXTO_TIPO[almacen.tipo]}. Depende de ${almacen.padre_clave}.`
              : `${TEXTO_TIPO[almacen.tipo]}. No depende de otro almacén.`
            : undefined
        }
        pie={
          almacen ? (
            <>
              {activo ? (
                <>
                  <Boton variante="contorno" onClick={() => alEditar(almacen)}>
                    <PencilIcon aria-hidden="true" />
                    Editar
                  </Boton>
                  <Boton variante="peligro" disabled={!puedeCerrar || !resumen} onClick={() => setConfirmando("inactivar")}>
                    <BanIcon aria-hidden="true" />
                    Inactivar almacén
                  </Boton>
                </>
              ) : (
                <Boton variante="normal" disabled={resumen?.puede_reabrir === false} onClick={() => setConfirmando("reactivar")}>
                  <RotateCcwIcon aria-hidden="true" />
                  Reactivar almacén
                </Boton>
              )}
            </>
          ) : undefined
        }
      >
        {almacen ? (
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap items-center gap-2">
              <Insignia estado={activo ? "info" : "neutra"}>{activo ? "Activo" : "Cerrado"}</Insignia>
              <Insignia estado="neutra">{TEXTO_TIPO[almacen.tipo]}</Insignia>
              {almacen.cerrado_en ? <span className="text-sm text-muted-foreground">Cerrado el {fechaHoraMx(almacen.cerrado_en)}</span> : null}
            </div>

            {resumen ? (
              <dl className="grid grid-cols-2 gap-2">
                <Dato
                  etiqueta="Existencias"
                  valor={
                    resumen.existencias.unidades === 0
                      ? "Sin existencias"
                      : `${resumen.existencias.unidades.toLocaleString("es-MX")} (${plural(resumen.existencias.articulos, "artículo", "artículos")})`
                  }
                />
                <Dato etiqueta="Piezas en resguardo" valor={resumen.piezas_en_resguardo.toLocaleString("es-MX")} />
                <Dato etiqueta="Usuarios activos" valor={resumen.usuarios.toLocaleString("es-MX")} />
                <Dato etiqueta="Traspasos en camino" valor={resumen.traspasos_en_transito.toLocaleString("es-MX")} />
                <Dato etiqueta="Compras urgentes abiertas" valor={resumen.solicitudes_compra_abiertas.toLocaleString("es-MX")} />
              </dl>
            ) : null}

            {almacen.hijos.length > 0 ? (
              <section aria-labelledby="almacen-hijos" className="flex flex-col gap-1">
                <h3 id="almacen-hijos" className="text-sm font-semibold text-marino">
                  Almacenes que dependen de este
                </h3>
                <ul className="flex flex-wrap gap-2">
                  {almacen.hijos.map((h) => (
                    <li key={h.id}>
                      <Insignia estado={h.estado === "ACTIVO" ? "info" : "neutra"}>
                        {h.nombre}
                        {h.estado === "CERRADO" ? " (cerrado)" : ""}
                      </Insignia>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <nav aria-label={`Lo que tiene ${almacen.nombre}`} className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold text-marino">Ir a</h3>
              <div className="flex flex-wrap gap-x-1">
                <Link to={`/personal?almacen=${almacen.id}`} className={ENLACE}>
                  Su personal
                </Link>
                <Link to="/usuarios" className={ENLACE}>
                  Usuarios
                </Link>
                <Link to={`/inventario?almacen=${almacen.id}`} className={ENLACE}>
                  Su inventario
                </Link>
                <Link to={`/compras?almacen=${almacen.id}`} className={ENLACE}>
                  Sus compras urgentes
                </Link>
              </div>
            </nav>

            {activo && resumen ? (
              <section aria-labelledby="almacen-cierre" className="flex flex-col gap-2">
                <h3 id="almacen-cierre" className="text-sm font-semibold text-marino">
                  Inactivar este almacén
                </h3>
                {bloqueos.length === 0 ? (
                  <p className="text-sm">
                    Se puede inactivar: no tiene existencias, traspasos en camino, almacenes que dependan de él ni usuarios asignados.
                    {resumen.piezas_en_resguardo > 0
                      ? ` Las ${plural(resumen.piezas_en_resguardo, "pieza", "piezas")} que siguen con trabajadores no lo impiden.`
                      : ""}
                  </p>
                ) : (
                  <>
                    <p className="text-sm text-muted-foreground">Falta resolver esto para poder inactivarlo:</p>
                    <ul className="flex flex-col gap-2">
                      {bloqueos.map((b) => (
                        <Bloqueo key={b.codigo} bloqueo={b} almacenId={almacen.id} />
                      ))}
                    </ul>
                  </>
                )}
              </section>
            ) : null}

            {padreCerrado ? (
              <p role="status" className="rounded-xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm font-medium">
                No se puede reactivar porque el almacén del que depende ({almacen.padre_clave}) está cerrado. Reactívalo primero.
              </p>
            ) : null}
            {!activo ? (
              <p className="text-sm text-muted-foreground">
                Un almacén cerrado no recibe ni envía material y no se edita, pero su historial y sus reportes siguen a la vista.
              </p>
            ) : null}
          </div>
        ) : null}
      </Hoja>

      <Confirmacion
        abierta={confirmando === "inactivar"}
        alCambiar={(a) => !ocupado && !a && setConfirmando(null)}
        mensaje={`¿Inactivar ${almacen?.nombre ?? "el almacén"}?`}
        detalle="Dejará de recibir y enviar material y no se podrán hacer solicitudes de compra nuevas. No se borra nada: su historial y sus reportes se conservan y lo puedes reactivar cuando quieras."
        etiquetaConfirmar="Sí, inactivar"
        etiquetaCancelar="Volver"
        peligro
        cargando={ocupado}
        alConfirmar={inactivar}
      />
      <Confirmacion
        abierta={confirmando === "reactivar"}
        alCambiar={(a) => !ocupado && !a && setConfirmando(null)}
        mensaje={`¿Reactivar ${almacen?.nombre ?? "el almacén"}?`}
        detalle="Vuelve a operar con su misma clave y su historial."
        etiquetaConfirmar="Sí, reactivar"
        etiquetaCancelar="Volver"
        cargando={ocupado}
        alConfirmar={reactivar}
      />
    </>
  );
}
