import { useState } from "react";
import { Link } from "react-router";
import { consumoTrabajador } from "~/api/deudores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { FiltroPeriodo } from "~/componentes/reportes/filtros-comunes";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";

export function ConsumoDelTrabajador({ id }: { id: string }) {
  const { puede } = useSesion();
  const [rango, setRango] = useState({ desde: "", hasta: "" });
  const consulta = useConsulta((signal) => consumoTrabajador(id, rango, signal), JSON.stringify([id, rango]));
  return <section className="flex flex-col gap-3"><h2 className="text-lg font-bold text-marino">Consumo</h2>
    <p className="text-sm">Consumibles entregados durante el contrato. Las entregas canceladas se descuentan.</p>
    <FiltroPeriodo desde={rango.desde} hasta={rango.hasta} alCambiar={(v) => setRango({ desde: v.desde ?? "", hasta: v.hasta ?? "" })} />
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : consulta.cargando ? <Esqueleto tipo="lista" cantidad={2} /> : consulta.datos ? <>
      <p className="text-sm">Del {consulta.datos.periodo.desde} al {consulta.datos.periodo.hasta}</p>
      {consulta.datos.elementos.length ? <ul className="flex flex-col gap-3">{consulta.datos.elementos.map((r) => <li key={r.articulo.id} className="rounded-xl border p-4"><p className="font-semibold">{puede("catalogo.ver") ? <Link className="underline" to={`/articulos/${r.articulo.id}`}>{r.articulo.nombre}</Link> : r.articulo.nombre} · {r.cantidad} {r.unidad}</p>{r.recomendado !== null ? <p className="text-sm">Dotación recomendada: {r.recomendado}</p> : null}{r.por_proyecto.map((p) => <p key={p.proyecto?.id ?? "sin"} className="text-sm">{p.proyecto?.nombre ?? "Sin proyecto"}: {p.cantidad}</p>)}</li>)}</ul> : <EstadoVacio titulo="Sin consumo en este periodo" />}
      {consulta.datos.valor_total != null ? <p className="font-semibold">Valor total: {Number(consulta.datos.valor_total).toLocaleString("es-MX", { style: "currency", currency: "MXN" })}</p> : null}
      {consulta.datos.valor_por_proyecto?.map((p) => p.valor === null ? null : <p key={p.proyecto?.id ?? "sin"} className="text-sm">{p.proyecto?.nombre ?? "Sin proyecto"}: {Number(p.valor).toLocaleString("es-MX", { style: "currency", currency: "MXN" })}</p>)}
      {consulta.datos.aviso_valor ? <p className="text-sm text-muted-foreground">{consulta.datos.aviso_valor}</p> : null}
    </> : null}
  </section>;
}
