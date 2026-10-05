import { cn } from "cn";
import { BriefcaseIcon, CheckIcon, ImageOffIcon, PackageIcon, XIcon } from "lucide-react";

import { Avatar } from "~/componentes/ui/avatar";
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
  className?: string;
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
export function FichaTrabajador({ trabajador, variante = "completa", className }: PropiedadesFichaTrabajador) {
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
        "flex items-center gap-1.5 text-sm font-bold",
        vigente ? "text-semaforo-verde" : "text-semaforo-rojo",
      )}
    >
      {vigente ? (
        <CheckIcon aria-hidden="true" className="size-4" strokeWidth={3} />
      ) : (
        <XIcon aria-hidden="true" className="size-4" strokeWidth={3} />
      )}
      <span className="text-foreground">{textoVigencia}</span>
    </p>
  );

  const avisoSinFoto = sinFoto ? (
    <p className="inline-flex w-fit items-center gap-1.5 rounded-full border border-semaforo-amarillo bg-semaforo-amarillo/10 px-2.5 py-0.5 text-sm font-semibold">
      <ImageOffIcon aria-hidden="true" className="size-4 text-semaforo-amarillo" />
      Sin foto registrada
    </p>
  ) : null;

  const contenedor = cn(
    "overflow-hidden rounded-xl border-2",
    vigente ? "border-border bg-card" : "border-semaforo-rojo bg-semaforo-rojo/10",
    className,
  );

  const bandaRoja = !vigente ? (
    <div role="alert" className="flex items-start gap-2 bg-semaforo-rojo px-4 py-2 text-white">
      <XIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" strokeWidth={3} />
      <p className="text-base leading-snug font-bold">
        No se puede entregar. <span className="font-semibold">{motivo}</span>
        {vigencia.regla ? <span className="ml-1.5 text-xs font-medium whitespace-nowrap opacity-90">({vigencia.regla})</span> : null}
      </p>
    </div>
  ) : null;

  if (variante === "reducida") {
    return (
      <section aria-label={`Trabajador ${trabajador.nombre}`} className={contenedor}>
        {bandaRoja}
        <div className="flex items-center gap-3 p-3">
          <Avatar nombre={trabajador.nombre} fotoUrl={fotoUrl} tamano="md" />
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="truncate text-xl leading-tight font-bold">{trabajador.nombre}</p>
            <p className="truncate text-sm text-muted-foreground">
              N.º {trabajador.numero_empleado}
              {subtitulo ? ` · ${subtitulo}` : ""}
            </p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              {estadoVigencia}
              <span className="text-sm text-muted-foreground">{textoResguardo(trabajador.resguardo.length)}</span>
            </div>
          </div>
        </div>
        {avisoSinFoto ? <div className="px-3 pb-3">{avisoSinFoto}</div> : null}
      </section>
    );
  }

  return (
    <section aria-label={`Trabajador ${trabajador.nombre}`} className={contenedor}>
      {bandaRoja}
      <div className="flex flex-col gap-4 p-4">
        <div className="flex items-start gap-4">
          <Avatar nombre={trabajador.nombre} fotoUrl={fotoUrl} tamano="lg" />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <p className="text-xl leading-tight font-bold wrap-break-word">{trabajador.nombre}</p>
            <p className="text-base text-muted-foreground">Número {trabajador.numero_empleado}</p>
            {subtitulo ? (
              <p className="flex items-center gap-1.5 text-base">
                <BriefcaseIcon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
                {subtitulo}
              </p>
            ) : null}
            {estadoVigencia}
            {avisoSinFoto}
          </div>
        </div>

        <div className="flex flex-col gap-2 border-t pt-3">
          <h3 className="flex items-center gap-2 text-base">
            <PackageIcon aria-hidden="true" className="size-5" />
            En resguardo
          </h3>
          {trabajador.resguardo.length === 0 ? (
            <p className="text-base text-muted-foreground">No tiene nada en resguardo.</p>
          ) : (
            <ul className="flex flex-col divide-y rounded-lg border bg-background">
              {trabajador.resguardo.map((r, i) => (
                <li key={`${r.codigo}-${i}`} className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 py-2">
                  <span className="font-semibold">
                    {r.cantidad > 1 ? `${r.cantidad} × ` : ""}
                    {r.articulo}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {r.codigo}
                    {r.numero_serie ? ` · Serie ${r.numero_serie}` : ""}
                    {r.folio ? ` · Vale ${r.folio}` : ""}
                    {r.de_periodo_anterior ? " · De un periodo anterior" : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
