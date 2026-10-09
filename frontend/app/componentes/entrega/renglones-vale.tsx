import { Link } from "react-router";
import type { RenglonValeApi } from "./tipos";

const textoNivel = {VERDE:"Sin avisos",AMARILLO:"Atención",NARANJA:"Requiere autorización",ROJO:"No permitido"};
export function RenglonesVale({filas, puedeVerPieza}:{filas:RenglonValeApi[];puedeVerPieza:boolean}) {
  const pieza = (r:RenglonValeApi) => r.pieza_id && puedeVerPieza ? <Link className="underline" to={`/piezas/${r.pieza_id}`}>{r.codigo_pieza} · {r.numero_serie ?? "Serie pendiente"}</Link> : r.numero_serie ?? "—";
  const ubicacion = (r:RenglonValeApi,campo:"origen"|"destino") => (r as RenglonValeApi & {origen?:{nombre:string};destino?:{nombre:string}})[campo]?.nombre ?? "—";
  return <>
    <div className="hidden md:block overflow-auto rounded-xl border"><table className="w-full text-left text-sm"><thead><tr>{["#","Código","Artículo y marca","Pieza o serie","Cantidad","Condición","Avisos","Observación","De","A"].map((h)=><th key={h} className="p-3">{h}</th>)}</tr></thead><tbody>{filas.map((r)=><tr key={r.renglon} className="border-b"><td className="p-3">{r.renglon}</td><td>{r.codigo_articulo}</td><td>{r.articulo}{r.marca ? ` · ${r.marca}` : ""}</td><td>{pieza(r)}</td><td>{r.cantidad}</td><td>{r.condicion ?? "—"}</td><td>{textoNivel[r.nivel]} · {r.reglas.join(", ")}</td><td>{r.observacion ?? "—"}</td><td>{ubicacion(r,"origen")}</td><td>{ubicacion(r,"destino")}</td></tr>)}</tbody></table></div>
    <div className="md:hidden grid gap-3">{filas.map((r)=><article key={r.renglon} className="rounded-xl border p-4"><h3 className="font-semibold">{r.renglon}. {r.articulo} {r.marca}</h3><p className="text-sm">{r.codigo_articulo} · {r.cantidad} unidades</p><p>{pieza(r)}</p><dl className="grid grid-cols-2 gap-1 mt-2 text-sm"><dt>Condición</dt><dd>{r.condicion ?? "—"}</dd><dt>Avisos</dt><dd>{textoNivel[r.nivel]} · {r.reglas.join(", ")}</dd><dt>De</dt><dd>{ubicacion(r,"origen")}</dd><dt>A</dt><dd>{ubicacion(r,"destino")}</dd></dl>{r.observacion ? <p className="mt-2 text-sm">{r.observacion}</p> : null}</article>)}</div>
    {!filas.length ? <p className="py-4">No hay renglones con esa búsqueda.</p> : null}
  </>;
}
