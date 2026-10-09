import { useEffect, useId, useState } from "react";
import { Link } from "react-router";
import { pedirUsoProyectos, type ProyectoTablero, type TotalUso, type UsoProyecto } from "~/api/tablero";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { fechaCorta } from "~/componentes/personas/formato";
import { Boton } from "~/componentes/ui/boton";
import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { useSesionActiva } from "~/sesion/sesion";
import { ATAJOS_PERIODO, periodoPorOmision, rangoDePeriodo, type ClavePeriodo } from "./periodos";

const numero = new Intl.NumberFormat("es-MX");
const moneda = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

export function UsoProyectos({ almacen }: { almacen: string }) {
  const { puede, sesion } = useSesionActiva();
  const [periodo, setPeriodo] = useState(periodoPorOmision);
  const [proyecto, setProyecto] = useState("");
  const id = useId();
  const valido = Boolean(periodo.desde && periodo.hasta && periodo.desde <= periodo.hasta);
  const clave = JSON.stringify([periodo.desde, periodo.hasta, almacen, sesion.usuario.id]);
  const parametros = { desde: periodo.desde, hasta: periodo.hasta, almacen_id: almacen || undefined };
  const lista = useConsulta((signal) => valido ? pedirUsoProyectos(parametros, signal) : Promise.resolve(null), `${clave}|${valido}`);
  const idDetalle = proyecto || (lista.datos?.proyectos.length === 1 ? lista.datos.proyectos[0].id : "");
  const ficha = useConsulta((signal) => idDetalle && valido ? pedirUsoProyectos({ ...parametros, proyecto_id: idDetalle }, signal) : Promise.resolve(null), `${clave}|${idDetalle}|${valido}`);
  useEffect(() => setProyecto(""), [almacen]);
  const consulta = proyecto ? ficha : lista;
  const datos = consulta.datos;
  const reparto = ficha.datos?.proyectos[0]?.por_categoria;
  const opciones = (lista.datos?.proyectos ?? []).map((p) => ({ valor: p.id, texto: `${p.clave} · ${p.nombre}` }));
  const conPesos = puede("reportes.valor_inventario");
  // Cuando el servidor reserva un importe (T-2), la barra compara unidades de todos.
  const barrasEnPesos = conPesos && Boolean(datos?.proyectos.length) && (datos?.proyectos.every((p) => p.total.valor !== null) ?? false);
  const magnitud = (p: UsoProyecto) => barrasEnPesos ? Number(p.total.valor) : p.total.unidades;
  const maximo = Math.max(...(datos?.proyectos ?? []).map(magnitud), 1);
  function total(t: TotalUso) {
    return <><span className="font-semibold tabular-nums">{numero.format(t.unidades)} unidades</span>{conPesos ? <p className="text-xs text-muted-foreground">{t.valor === null ? "Importe reservado" : moneda.format(Number(t.valor))}</p> : null}</>;
  }
  function barra(p: UsoProyecto) {
    return <div className="mt-2 h-2 rounded-full bg-muted" aria-hidden="true"><div className="h-full rounded-full bg-marino" style={{ width: `${Math.min(100, Math.max(0, magnitud(p) / maximo * 100))}%` }} /></div>;
  }
  function titulo(p: ProyectoTablero) {
    return <><Link to={`/proyectos?proyecto_id=${p.id}`} className="font-semibold underline underline-offset-4">{p.nombre}</Link><p className="text-xs text-muted-foreground">{p.clave} · {p.almacen.nombre}</p><p className="text-xs text-muted-foreground">{fechaCorta(p.inicio)} al {fechaCorta(p.fin_estimado)}{p.estado === "CERRADO" ? " · Cerrado" : p.situacion === "FIN_VENCIDO" ? " · Fin estimado vencido" : ""}</p></>;
  }
  return <Card><CardHeader><CardTitle>Uso por proyecto</CardTitle><p className="text-sm text-muted-foreground">Retornables en resguardo hoy y consumibles consumidos en el periodo, descontando cancelaciones.</p></CardHeader><CardContent className="flex flex-col gap-4">
    <div className="flex flex-wrap gap-2" role="group" aria-label="Periodo de uso">{ATAJOS_PERIODO.map((a) => <Boton key={a.clave} variante={periodo.clave === a.clave ? "normal" : "contorno"} aria-pressed={periodo.clave === a.clave} onClick={() => setPeriodo((p) => a.clave === "fechas" ? { ...p, clave: "fechas" } : { clave: a.clave as ClavePeriodo, ...rangoDePeriodo(a.clave as Exclude<ClavePeriodo, "fechas">) })}>{a.texto}</Boton>)}</div>
    {periodo.clave === "fechas" ? <div className="grid gap-3 sm:grid-cols-2"><CampoFecha etiqueta="Desde" value={periodo.desde} alCambiar={(desde) => setPeriodo({ ...periodo, desde })} /><CampoFecha etiqueta="Hasta" value={periodo.hasta} alCambiar={(hasta) => setPeriodo({ ...periodo, hasta })} error={!valido ? "Elige fechas válidas y ordenadas." : undefined} /></div> : null}
    {opciones.length > 1 ? <div className="flex max-w-lg flex-col gap-1.5"><label htmlFor={id}>Viendo proyecto</label><ListaDesplegable id={id} valor={proyecto} alCambiar={setProyecto} opciones={opciones} vacio="Todos los proyectos" /></div> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : null}
    {!proyecto && ficha.error ? <EstadoError error={ficha.error} alReintentar={ficha.recargar} /> : null}
    {valido && consulta.cargando && !datos ? <Esqueleto tipo="tabla" cantidad={4} /> : null}
    {datos ? <div aria-busy={consulta.cargando} className={consulta.cargando ? "opacity-70" : undefined}>
      <p className="mb-3 text-sm">Viendo: {datos.alcance.nombre} · {fechaCorta(datos.rango.desde)} al {fechaCorta(datos.rango.hasta)}. Barras por {barrasEnPesos ? "pesos" : "unidades"}.</p>
      {conPesos ? <p className="mb-3 text-xs text-muted-foreground">Pesos mexicanos al costo actual del catálogo. Un importe reservado protege el costo de un único artículo.</p> : null}
      {!datos.proyectos.length ? <p className="py-3 text-muted-foreground">No hay proyectos con uso o activos en este alcance.</p> : null}
      <div className="hidden md:block"><Table><TableHeader><TableRow>{["Proyecto", "Trabajadores", "En resguardo hoy", "Consumido en el periodo", "Total"].map((t) => <TableHead key={t}>{t}</TableHead>)}</TableRow></TableHeader><TableBody>{datos.proyectos.map((p) => <TableRow key={p.id}><TableCell className="whitespace-normal">{titulo(p)}{p.articulos_sin_costo ? <p className="text-xs text-muted-foreground">{p.articulos_sin_costo} artículos sin costo</p> : null}</TableCell><TableCell>{p.trabajadores_asignados}</TableCell><TableCell>{total(p.retornables_en_resguardo)}</TableCell><TableCell>{total(p.consumibles_consumidos)}</TableCell><TableCell className="min-w-40">{total(p.total)}{barra(p)}</TableCell></TableRow>)}{!proyecto ? <TableRow><TableHead>Sin proyecto</TableHead><TableCell>—</TableCell><TableCell>{total(datos.sin_proyecto.retornables_en_resguardo)}</TableCell><TableCell>{total(datos.sin_proyecto.consumibles_consumidos)}</TableCell><TableCell>{total(datos.sin_proyecto.total)}</TableCell></TableRow> : null}</TableBody></Table></div>
      <div className="flex flex-col gap-3 md:hidden">{datos.proyectos.map((p) => <div key={p.id} className="rounded-lg border p-4">{titulo(p)}<p className="mt-2 text-sm">{p.trabajadores_asignados} trabajadores asignados</p><dl className="mt-2 grid grid-cols-2 gap-3 text-sm"><div><dt>En resguardo hoy</dt><dd>{total(p.retornables_en_resguardo)}</dd></div><div><dt>Consumido en el periodo</dt><dd>{total(p.consumibles_consumidos)}</dd></div></dl><div className="mt-3 text-sm">Total: {total(p.total)}{barra(p)}</div>{p.articulos_sin_costo ? <p className="mt-2 text-xs">{p.articulos_sin_costo} artículos sin costo</p> : null}</div>)}{!proyecto ? <div className="rounded-lg border p-4"><h3 className="font-semibold">Sin proyecto</h3><dl className="mt-2 grid grid-cols-2 gap-3 text-sm"><div><dt>En resguardo hoy</dt><dd>{total(datos.sin_proyecto.retornables_en_resguardo)}</dd></div><div><dt>Consumido en el periodo</dt><dd>{total(datos.sin_proyecto.consumibles_consumidos)}</dd></div></dl></div> : null}</div>
      {reparto?.length ? <div className="mt-5"><h3 className="mb-3 font-semibold">Reparto por categoría</h3><ul className="flex flex-col gap-3">{reparto.map((c) => <li key={c.categoria?.id ?? "otras"}><span>{c.nombre}</span><div className="text-sm">{total(c.total)}{barra(c)}</div></li>)}</ul></div> : null}
    </div> : null}
  </CardContent></Card>;
}
