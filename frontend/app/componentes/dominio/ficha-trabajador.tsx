import { cn } from "cn";
import { CheckIcon, ChevronDownIcon, ImageOffIcon, XIcon } from "lucide-react";

import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import { formatearFecha } from "./fechas";

/** Un artículo que el trabajador tiene en resguardo (`PendienteOut` del servidor). */
export interface ResguardoItem {
  articulo: string;
  codigo: string;
  numero_serie?: string | null;
  cantidad: number;
  entregado_en?: string | null;
  folio?: string | null;
  almacen?: string | null;
  de_periodo_anterior?: boolean;
}

/**
 * Lo que necesita la ficha. Es la ficha breve de `GET /api/trabajadores/{id}` (`FichaBreveOut`):
 * nunca trae CURP ni NSS. `periodo` solo viene en la ficha completa; si no está, no se muestra fecha.
 */
export interface DatosFichaTrabajador {
  id: string;
  numero_empleado: string;
  nombre: string;
  puesto: string | null;
  area_obra: string | null;
  vigencia: { vigente: boolean; motivo: string | null; regla?: string };
  tiene_foto: boolean;
  foto_url: string | null;
  resguardo: ResguardoItem[];
  periodo?: { inicio: string; fin: string } | null;
}

interface PropiedadesFichaTrabajador {
  trabajador: DatosFichaTrabajador;
  /** `completa`: foto grande y resguardo. `reducida`: una línea para el paso 2 de la entrega. */
  variante?: "completa" | "reducida";
  /**
   * Resumen de la dotación del puesto (FEAT-003), solo en la variante `completa`. Sin dotación, `null` y no se
   * muestra nada. Es una sugerencia: no bloquea ni avisa.
   */
  dotacion?: { faltan: number; total: number } | null;
  /** Abre la lista de la dotación ("Ver dotación"). */
  alVerDotacion?: () => void;
  className?: string;
  /** Valor de `data-tutorial` (FEAT-010). */
  ancla?: string;
}

function textoResguardo(n: number): string {
  return n === 0 ? "Sin nada en resguardo" : n === 1 ? "1 artículo en resguardo" : `${n} artículos en resguardo`;
}

/**
 * Ficha breve del trabajador. Si no es vigente, TODA la ficha va en rojo con el motivo (icono y texto).
 * Sin foto, un aviso "Sin foto registrada" que no bloquea nada.
 *
 * ```tsx
 * <FichaTrabajador trabajador={ficha} variante="completa" />
 * ```
 */
export function FichaTrabajador({ trabajador, variante = "completa", dotacion = null, alVerDotacion, className, ancla }: PropiedadesFichaTrabajador) {
  const { vigencia, periodo } = trabajador;
  const vigente = vigencia.vigente;
  const subtitulo = [trabajador.puesto, trabajador.area_obra].filter(Boolean).join(" · ");
  const motivo = vigencia.motivo ?? "El trabajador no está vigente.";
  const textoVigencia = vigente
    ? periodo?.fin
      ? `Vigente hasta el ${formatearFecha(periodo.fin)}`
      : "Vigente"
    : "No vigente";
  const fotoUrl = trabajador.tiene_foto ? trabajador.foto_url : null;
  const sinFoto = !trabajador.tiene_foto;

  const estadoVigencia = (
    <p
      className={cn(
        "inline-flex w-fit items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
        vigente ? "bg-semaforo-verde/10 text-semaforo-verde" : "bg-semaforo-rojo/10 text-semaforo-rojo",
      )}
    >
      {vigente ? (
        <CheckIcon aria-hidden="true" className="size-3.5" strokeWidth={3} />
      ) : (
        <XIcon aria-hidden="true" className="size-3.5" strokeWidth={3} />
      )}
      {textoVigencia}
    </p>
  );

  const avisoSinFoto = sinFoto ? (
    <p className="inline-flex w-fit items-center gap-1 rounded-full bg-semaforo-amarillo/10 px-2 py-0.5 text-xs font-semibold text-foreground">
      <ImageOffIcon aria-hidden="true" className="size-3.5 text-semaforo-amarillo" />
      Sin foto registrada
    </p>
  ) : null;

  const contenedor = cn(
    "overflow-hidden rounded-2xl border shadow-xs",
    vigente ? "border-border bg-card" : "border-semaforo-rojo bg-semaforo-rojo/5",
    className,
  );

  const bandaRoja = !vigente ? (
    <div role="alert" className="flex items-start gap-2 bg-semaforo-rojo px-3 py-2 text-white">
      <XIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" strokeWidth={3} />
      <p className="text-sm leading-snug font-semibold">
        No se puede entregar. <span className="font-medium">{motivo}</span>
      </p>
    </div>
  ) : null;

  const cabecera = (
    <div className="flex items-center gap-3 p-3">
      <Avatar nombre={trabajador.nombre} fotoUrl={fotoUrl} tamano="md" />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="text-base leading-tight font-semibold wrap-break-word">{trabajador.nombre}</p>
        <p className="text-sm leading-snug text-muted-foreground">
          N.º {trabajador.numero_empleado}
          {subtitulo ? ` · ${subtitulo}` : ""}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
          {estadoVigencia}
          {avisoSinFoto}
          <span className="text-xs text-muted-foreground">{textoResguardo(trabajador.resguardo.length)}</span>
        </div>
      </div>
    </div>
  );

  if (variante === "reducida") {
    return (
      <section aria-label={`Trabajador ${trabajador.nombre}`} className={contenedor} data-tutorial={ancla}>
        {bandaRoja}
        {cabecera}
      </section>
    );
  }

  return (
    <section aria-label={`Trabajador ${trabajador.nombre}`} className={contenedor} data-tutorial={ancla}>
      {bandaRoja}
      {cabecera}
      {dotacion && vigente ? (
        <div className="flex items-center justify-between gap-2 border-t px-3 py-1">
          <p className="text-sm">
            <span className="font-semibold">Dotación: </span>
            {dotacion.faltan === 0 ? "completa" : `faltan ${dotacion.faltan} de ${dotacion.total}`}
          </p>
          {alVerDotacion ? (
            <Boton variante="texto" className="px-2 text-primary" onClick={alVerDotacion}>
              Ver dotación
            </Boton>
          ) : null}
        </div>
      ) : null}
      {trabajador.resguardo.length > 0 ? (
        <details className="group border-t">
          <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-2 px-3 text-sm font-medium text-primary [&::-webkit-details-marker]:hidden">
            Ver lo que tiene en resguardo
            <ChevronDownIcon aria-hidden="true" className="size-4 transition-transform group-open:rotate-180" />
          </summary>
          <ul className="flex flex-col divide-y border-t">
            {trabajador.resguardo.map((r, i) => (
              <li key={`${r.codigo}-${i}`} className="flex flex-col gap-0.5 px-3 py-2 text-sm">
                <span className="font-medium">
                  {r.cantidad > 1 ? `${r.cantidad} × ` : ""}
                  {r.articulo}
                </span>
                <span className="text-xs text-muted-foreground">
                  {r.codigo}
                  {r.numero_serie ? ` · Serie ${r.numero_serie}` : ""}
                  {r.folio ? ` · Vale ${r.folio}` : ""}
                  {r.de_periodo_anterior ? " · De un periodo anterior" : ""}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
