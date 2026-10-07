import { Bar, BarChart, Cell, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router";

import type { ConsumoTablero } from "~/api/tablero";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "~/components/ui/chart";

const COLOR_PRINCIPAL = "var(--primary)";
const COLOR_OTROS = "#9ca3af";
/** Un color por almacén; el nombre va siempre en la leyenda y en el detalle, el color nunca va solo. */
const COLORES_ALMACEN = ["#0054a6", "#d97706", "#0f766e", "#7c3aed", "#be123c", "#4d7c0f", "#475569", "#0e7490"];

const ALTO_FILA = 52;
const ANCHO_ETIQUETA = 150;
const MAX_LETRAS = 22;
const numero = new Intl.NumberFormat("es-MX");

interface Fila {
  clave: string;
  articuloId: string | null;
  nombre: string;
  completo: string;
  unidad: string;
  total: number;
  [serie: string]: string | number | null;
}

function recortar(texto: string): string {
  return texto.length > MAX_LETRAS ? `${texto.slice(0, MAX_LETRAS - 1)}…` : texto;
}

interface PropiedadesGrafica {
  datos: ConsumoTablero;
}

/**
 * Barras horizontales de lo más usado (recharts por `components/ui/chart`, ADR-009). Cada barra lleva su
 * nombre y su número escritos al lado (no solo en el detalle) y el nombre abre el artículo.
 * Solo dibuja lo que entrega el servidor: ya viene ordenado, con «Otros» agrupado.
 */
export default function GraficaConsumo({ datos }: PropiedadesGrafica) {
  const navegar = useNavigate();
  const separado = datos.separar_por_almacen && datos.barras.some((b) => b.por_almacen.length > 0);

  // Series por almacén, en orden alfabético y estable.
  const almacenes = separado
    ? [...new Map(datos.barras.flatMap((b) => b.por_almacen).map((a) => [a.almacen_id, a.almacen])).entries()].sort((a, b) => a[1].localeCompare(b[1], "es"))
    : [];
  const claveAlmacen = new Map(almacenes.map(([id], i) => [id, `a${i}`]));

  const filas: Fila[] = datos.barras.map((b) => {
    const fila: Fila = { clave: b.articulo_id, articuloId: b.articulo_id, nombre: recortar(b.articulo), completo: b.articulo, unidad: b.unidad, total: b.total };
    for (const a of b.por_almacen) fila[claveAlmacen.get(a.almacen_id) ?? "a?"] = a.total;
    return fila;
  });
  if (datos.otros.total > 0) {
    const etiqueta = `Otros (${datos.otros.articulos} ${datos.otros.articulos === 1 ? "artículo" : "artículos"})`;
    filas.push({ clave: "otros", articuloId: null, nombre: etiqueta, completo: etiqueta, unidad: "", total: datos.otros.total, otros: datos.otros.total });
  }

  const config: ChartConfig = separado
    ? {
        ...Object.fromEntries(almacenes.map(([, nombre], i) => [`a${i}`, { label: nombre, color: COLORES_ALMACEN[i % COLORES_ALMACEN.length] }])),
        otros: { label: "Otros", color: COLOR_OTROS },
      }
    : { total: { label: "Unidades", color: COLOR_PRINCIPAL } };

  const alto = filas.length * ALTO_FILA + 16 + (separado ? 44 : 0);

  // Etiqueta de cada barra: nombre (enlace al artículo) y debajo su total con la unidad.
  const Etiqueta = ({ x, y, payload }: { x?: number | string; y?: number | string; payload?: { index?: number } }) => {
    const fila = filas[payload?.index ?? -1];
    if (!fila) return null;
    const px = Number(x ?? 0);
    const py = Number(y ?? 0);
    const texto = (
      <>
        <text x={px - 4} y={py - 4} textAnchor="end" className="fill-foreground text-[13px] font-medium">
          {fila.nombre}
        </text>
        <text x={px - 4} y={py + 13} textAnchor="end" className="fill-marino text-[13px] font-bold">
          {`${numero.format(fila.total)}${fila.unidad ? ` ${fila.unidad}` : ""}`}
        </text>
      </>
    );
    if (!fila.articuloId) return <g>{texto}</g>;
    const ruta = `/articulos/${fila.articuloId}`;
    return (
      <a
        href={ruta}
        aria-label={`${fila.completo}: ${numero.format(fila.total)}${fila.unidad ? ` ${fila.unidad}` : ""}. Abrir el artículo`}
        className="cursor-pointer underline-offset-2 outline-none hover:underline focus-visible:underline"
        onClick={(e) => {
          e.preventDefault();
          void navegar(ruta);
        }}
      >
        <title>{fila.completo}</title>
        {texto}
      </a>
    );
  };

  const alTocarBarra = (fila: Fila | undefined) => {
    if (fila?.articuloId) void navegar(`/articulos/${fila.articuloId}`);
  };

  return (
    <ChartContainer config={config} className="aspect-auto w-full" style={{ height: alto }} initialDimension={{ width: 320, height: alto }}>
      <BarChart accessibilityLayer={false} data={filas} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 0 }} barCategoryGap="22%">
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="clave" width={ANCHO_ETIQUETA} tickLine={false} axisLine={false} interval={0} tick={Etiqueta as never} />
        <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent labelFormatter={(_, p) => p?.[0]?.payload?.completo ?? ""} hideIndicator={!separado} />} />
        {separado ? (
          <>
            <ChartLegend content={<ChartLegendContent />} />
            {almacenes.map(([id], i) => (
              <Bar key={id} dataKey={`a${i}`} stackId="u" fill={`var(--color-a${i})`} cursor="pointer" onClick={(_, idx) => alTocarBarra(filas[idx])} />
            ))}
            <Bar dataKey="otros" stackId="u" fill="var(--color-otros)" radius={[0, 4, 4, 0]} />
          </>
        ) : (
          <Bar dataKey="total" radius={4} cursor="pointer" onClick={(_, idx) => alTocarBarra(filas[idx])}>
            {filas.map((f) => (
              <Cell key={f.clave} fill={f.articuloId ? "var(--color-total)" : COLOR_OTROS} />
            ))}
          </Bar>
        )}
      </BarChart>
    </ChartContainer>
  );
}
