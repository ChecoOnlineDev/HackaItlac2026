import { cn } from "cn";
import { ArrowRightIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import type { ResumenTablero } from "~/api/tablero";
import { Card, CardContent } from "~/components/ui/card";

const numero = new Intl.NumberFormat("es-MX");

interface PropiedadesTarjeta {
  titulo: string;
  valor: number;
  /** Qué cuenta, en pocas palabras. */
  detalle: ReactNode;
  /** Si lleva, toda la tarjeta se toca y abre esa pantalla. */
  ruta?: string;
  /** Resalta la cifra cuando pide atención (por ejemplo, artículos sin existencia). */
  atencion?: boolean;
}

/** Tarjeta de indicador: título, cifra grande y una línea que dice qué cuenta. */
export function TarjetaIndicador({ titulo, valor, detalle, ruta, atencion }: PropiedadesTarjeta) {
  const contenido = (
    <Card size="sm" className={cn("h-full", ruta && "transition-colors group-hover/enlace:bg-accent/60")}>
      <CardContent className="flex h-full flex-col gap-1">
        <p className="text-sm font-medium text-muted-foreground">{titulo}</p>
        <p className={cn("text-3xl leading-tight font-bold tabular-nums", atencion && valor > 0 ? "text-destructive" : "text-marino")}>{numero.format(valor)}</p>
        <p className="flex items-end justify-between gap-2 text-sm text-muted-foreground">
          <span>{detalle}</span>
          {ruta ? <ArrowRightIcon aria-hidden="true" className="size-4 shrink-0 text-marino" /> : null}
        </p>
      </CardContent>
    </Card>
  );
  if (!ruta) return contenido;
  return (
    <Link to={ruta} className="group/enlace block min-h-11 rounded-xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
      {contenido}
    </Link>
  );
}

interface PropiedadesTarjetas {
  resumen: ResumenTablero;
  /** Si quien mira puede abrir el seguimiento de piezas (`reportes.existencias`). */
  puedeVerSeguimiento: boolean;
}

/** Los indicadores del tablero (FEAT-008 4.2.2). Todas las cifras las calcula el servidor. */
export function TarjetasIndicadores({ resumen, puedeVerSeguimiento }: PropiedadesTarjetas) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      <TarjetaIndicador
        titulo="Existencias"
        valor={resumen.existencias.unidades}
        detalle={`unidades · ${numero.format(resumen.existencias.articulos)} ${resumen.existencias.articulos === 1 ? "artículo" : "artículos"}`}
      />
      <TarjetaIndicador
        titulo="Equipo importante en resguardo"
        valor={resumen.resguardo_equipo_importante}
        detalle="piezas en manos de trabajadores"
        ruta={puedeVerSeguimiento ? "/seguimiento?ubicacion=TRABAJADOR" : undefined}
      />
      <TarjetaIndicador titulo="Sin existencia" valor={resumen.sin_existencia} detalle="artículos agotados" atencion />
      <TarjetaIndicador titulo="Traspasos en tránsito" valor={resumen.traspasos_en_transito} detalle="enviados y sin recibir" />
      <TarjetaIndicador titulo="Entregas de hoy" valor={resumen.entregas_hoy} detalle="vales de entrega del día" />
      <TarjetaIndicador titulo="Solicitudes de compra abiertas" valor={resumen.solicitudes_compra_abiertas} detalle="pendientes o en compra" />
      {typeof resumen.piezas_serie_pendiente === "number" ? (
        <TarjetaIndicador
          titulo="Piezas con serie pendiente"
          valor={resumen.piezas_serie_pendiente}
          detalle="piezas sin número de serie"
          ruta={puedeVerSeguimiento ? "/seguimiento?serie_pendiente=true" : undefined}
        />
      ) : null}
      <TarjetaIndicador titulo="Inspecciones por vencer" valor={resumen.inspecciones_por_vencer} detalle="en los próximos 7 días" atencion />
    </div>
  );
}
