import { HashIcon, ClipboardCheckIcon, MapPinIcon, PackageCheckIcon, TriangleAlertIcon, Undo2Icon, CalendarClockIcon } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";

import { Bloque } from "~/componentes/consulta/bloque";
import { Dato, Seccion, VolverAConsultar } from "~/componentes/consulta/bloques";
import { BandaEstadoPieza, leerEstadoPieza } from "~/componentes/consulta/estado-pieza";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { InsigniaSeriePendiente } from "~/componentes/dominio/insignia-serie-pendiente";
import { HojaRegistrarSerie } from "~/componentes/consulta/hoja-registrar-serie";
import { HojaAjusteVigencia, HojaInspeccion, HojaMarcarNoApta } from "~/componentes/consulta/hojas-pieza";
import { AvisoResguardo } from "~/componentes/seguimiento/aviso-resguardo";
import { LineaDeTiempo } from "~/componentes/consulta/linea-de-tiempo";
import type { FichaPieza } from "~/componentes/consulta/tipos";
import { useCarga } from "~/componentes/consulta/use-carga";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";
import { HojaEstadoPieza } from "~/componentes/consulta/hoja-estado-pieza";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "catalogo.ver" };

type Panel = null | "inspeccion" | "no-apta" | "vigencia" | "serie" | "estado";

export default function FichaPiezaPantalla() {
  const { id } = useParams();
  const { puede } = useSesion();
  const { datos: pieza, error, cargando, recargar } = useCarga<FichaPieza>(id ? `/piezas/${id}` : null);
  const [panel, setPanel] = useState<Panel>(null);

  const puedeInspeccionar = puede("piezas.inspeccionar");
  const puedeAjustar = puede("piezas.ajustar_vigencia");
  const puedeRegistrarSerie = puede("piezas.registrar_serie");
  const puedeEntregar = puede("entregas.crear");
  const puedeDevolver = puede("devoluciones.crear");

  if (cargando) {
    return (
      <Pantalla titulo="Ficha de pieza" ancho="formulario">
        <VolverAConsultar />
        <Esqueleto tipo="tarjeta" cantidad={2} />
        <Esqueleto tipo="lista" cantidad={3} />
      </Pantalla>
    );
  }

  if (error || !pieza) {
    return (
      <Pantalla titulo="Ficha de pieza" ancho="formulario">
        <VolverAConsultar />
        <EstadoError error={error ?? undefined} alReintentar={recargar} />
      </Pantalla>
    );
  }

  const lectura = leerEstadoPieza({ ...pieza, requiere_inspeccion: pieza.articulo.requiere_inspeccion });
  const enBaja = pieza.estado === "BAJA";
  const conTrabajador = pieza.ubicacion?.tipo === "TRABAJADOR";
  const inspeccion = pieza.ultima_inspeccion;
  const seriePendiente = pieza.serie_pendiente ?? !pieza.numero_serie;

  return (
    <Pantalla
      titulo={pieza.articulo.nombre}
      descripcion={`Pieza ${pieza.codigo}${pieza.numero_serie ? ` · Serie ${pieza.numero_serie}` : ""}`}
      ancho="formulario"
    >
      <VolverAConsultar />

      <BandaEstadoPieza lectura={lectura} />

      {seriePendiente && !enBaja ? (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
          <InsigniaSeriePendiente />
          <p className="min-w-0 flex-1 text-sm">Esta pieza no tiene número de serie registrado. Se puede entregar, pero conviene completarlo.</p>
          {puedeRegistrarSerie ? (
            <Boton variante="secundario" className="h-11" onClick={() => setPanel("serie")}>
              <HashIcon aria-hidden="true" />
              Registrar serie
            </Boton>
          ) : null}
        </div>
      ) : null}

      {pieza.aviso && !enBaja ? <AvisoResguardo texto={pieza.aviso} /> : null}

      <Bloque titulo="Dónde está" icono={MapPinIcon}>
        {pieza.ubicacion ? (
          <p className="text-base font-semibold">
            {conTrabajador && pieza.ubicacion.trabajador_id && puede("trabajadores.ver") ? (
              <Link to={`/trabajadores/${pieza.ubicacion.trabajador_id}`} className="inline-flex min-h-10 items-center text-primary underline underline-offset-2">
                {pieza.ubicacion.texto}
              </Link>
            ) : (
              pieza.ubicacion.texto
            )}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">No se sabe dónde está.</p>
        )}
        <p className="text-sm text-muted-foreground">
          {conTrabajador ? "La tiene un trabajador en resguardo." : pieza.ubicacion?.tipo === "ALMACEN" ? "Está en el almacén." : ""}
        </p>
      </Bloque>

      <div className="flex flex-wrap gap-2">
        {puede("piezas.marcar_estado") && !enBaja ? <Boton variante="contorno" onClick={() => setPanel("estado")}>Mantenimiento o calibración</Boton> : null}
        {puedeInspeccionar && !enBaja ? (
          <Boton variante="normal" nativeButton={false} render={<Link to={`/inspeccionar?pieza=${pieza.id}`} />}>
            <ClipboardCheckIcon aria-hidden="true" />
            Inspeccionar
          </Boton>
        ) : null}
        {puedeInspeccionar && !enBaja && pieza.estado !== "NO_APTO" ? (
          <Boton variante="contorno" onClick={() => setPanel("no-apta")}>
            <TriangleAlertIcon aria-hidden="true" />
            Marcar como no apta
          </Boton>
        ) : null}
        {puedeAjustar && !enBaja && pieza.articulo.requiere_inspeccion ? (
          <Boton variante="contorno" onClick={() => setPanel("vigencia")}>
            <CalendarClockIcon aria-hidden="true" />
            Ajustar vigencia
          </Boton>
        ) : null}
        {puedeEntregar && pieza.ubicacion?.tipo === "ALMACEN" && lectura.nivel !== "rojo" && !enBaja ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to="/entregar" />}>
            <PackageCheckIcon aria-hidden="true" />
            Entregar
          </Boton>
        ) : null}
        {puedeDevolver && conTrabajador ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to="/devolver" />}>
            <Undo2Icon aria-hidden="true" />
            Devolver
          </Boton>
        ) : null}
      </div>

      <Seccion titulo="Datos de la pieza">
        <dl className="grid grid-cols-1 gap-3 rounded-2xl border bg-card p-4 shadow-xs sm:grid-cols-2">
          <Dato
            etiqueta="Artículo"
            valor={
              <Link to={`/articulos/${pieza.articulo.id}`} className="inline-flex min-h-10 items-center text-primary underline underline-offset-2">
                {pieza.articulo.nombre}
              </Link>
            }
          />
          <Dato etiqueta="Estado" valor={pieza.estado_texto} />
          <Dato etiqueta="Código" valor={pieza.codigo} />
          <Dato etiqueta="Número de serie" valor={pieza.numero_serie ? pieza.numero_serie : <InsigniaSeriePendiente />} />
          {pieza.articulo.marca ? <Dato etiqueta="Marca" valor={pieza.articulo.marca} /> : null}
          {pieza.articulo.talla ? <Dato etiqueta="Talla" valor={pieza.articulo.talla} /> : null}
          {pieza.articulo.requiere_inspeccion && pieza.articulo.vigencia_inspeccion_dias ? (
            <Dato etiqueta="Una inspección dura" valor={`${pieza.articulo.vigencia_inspeccion_dias} días`} />
          ) : null}
        </dl>
      </Seccion>

      {pieza.articulo.requiere_inspeccion ? (
        <Seccion titulo="Última inspección">
          {inspeccion ? (
            <dl className="grid grid-cols-1 gap-3 rounded-2xl border bg-card p-4 shadow-xs sm:grid-cols-2">
              <Dato etiqueta="Resultado" valor={inspeccion.resultado_texto} />
              <Dato etiqueta="Fecha" valor={formatearFecha(inspeccion.fecha)} />
              <Dato etiqueta="Hecha por" valor={inspeccion.usuario} />
              {inspeccion.vigente_hasta ? <Dato etiqueta="Vale hasta" valor={formatearFecha(inspeccion.vigente_hasta)} /> : null}
              {inspeccion.observacion ? <Dato etiqueta="Observación" valor={inspeccion.observacion} /> : null}
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">Todavía no tiene ninguna inspección.</p>
          )}
        </Seccion>
      ) : null}

      <Seccion titulo="Línea de tiempo">
        <LineaDeTiempo historial={pieza.historial} puedeVerVales={puede("vales.ver")} puedeVerTrabajadores={puede("trabajadores.ver")} />
      </Seccion>

      <HojaInspeccion pieza={pieza} abierta={panel === "inspeccion"} alCambiar={(a) => setPanel(a ? "inspeccion" : null)} alGuardar={recargar} />
      <HojaEstadoPieza pieza={pieza} abierta={panel === "estado"} alCambiar={(a) => setPanel(a ? "estado" : null)} alGuardar={recargar} />
      <HojaMarcarNoApta pieza={pieza} abierta={panel === "no-apta"} alCambiar={(a) => setPanel(a ? "no-apta" : null)} alGuardar={recargar} />
      {puedeRegistrarSerie ? (
        <HojaRegistrarSerie
          piezaId={pieza.id}
          codigo={pieza.codigo}
          articulo={pieza.articulo.nombre}
          abierta={panel === "serie"}
          alCambiar={(a) => setPanel(a ? "serie" : null)}
          alGuardar={recargar}
        />
      ) : null}
      <HojaAjusteVigencia pieza={pieza} abierta={panel === "vigencia"} alCambiar={(a) => setPanel(a ? "vigencia" : null)} alGuardar={recargar} />
    </Pantalla>
  );
}
