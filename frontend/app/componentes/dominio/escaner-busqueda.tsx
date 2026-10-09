import { PackageIcon, SearchXIcon, UserRoundIcon, WrenchIcon } from "lucide-react";
import { useRef, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { Busqueda } from "~/componentes/consulta/tipos";
import { useBusquedaDiferida } from "~/componentes/ui/busqueda-diferida";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Boton } from "~/componentes/ui/boton";
import { Escaner, type ManejadorEscaner, type PropiedadesEscaner } from "./escaner";

/** El escaneo exacto sigue en el flujo; estas sugerencias solo preguntan al servidor qué coincide. */
export function EscanerBusqueda({ grupo = "articulos", almacenId, onCodigo, alCambiarTexto, ...props }: PropiedadesEscaner & { grupo?: "articulos" | "trabajadores" | "todos"; almacenId?: string | null }) {
  const [texto, setTexto] = useState("");
  const escaner = useRef<ManejadorEscaner>(null);
  const busqueda = useBusquedaDiferida(texto, (q, signal) => apiGet<Busqueda>("/busqueda", { q, tamano: 8, almacen_id: almacenId || undefined }, signal), { clave: almacenId ?? "" });
  const datos = busqueda.resultado;
  const candidatos = [
    ...(grupo !== "trabajadores" ? (datos?.articulos.elementos ?? []).map((a) => ({ codigo: a.codigo, nombre: a.nombre, detalle: [a.codigo, a.marca, a.en_almacen != null ? `${a.en_almacen} en almacén` : null, a.con_trabajadores != null ? `${a.con_trabajadores} con trabajadores` : null].filter(Boolean).join(" · "), icono: PackageIcon })) : []),
    ...(grupo !== "trabajadores" ? (datos?.piezas.elementos ?? []).map((p) => ({ codigo: p.codigo, nombre: p.articulo, detalle: [p.codigo, p.numero_serie ? `Serie ${p.numero_serie}` : null, p.ubicacion_texto ?? p.ubicacion, p.estado !== "APTO" ? p.estado_texto : null].filter(Boolean).join(" · "), icono: WrenchIcon })) : []),
    ...(grupo !== "articulos" ? (datos?.trabajadores.elementos ?? []).map((t) => ({ codigo: t.credencial ?? t.numero_empleado, nombre: t.nombre, detalle: [`N.º ${t.numero_empleado}`, t.puesto, t.vigencia?.texto ?? t.estado_texto, t.credencial ? `Credencial ${t.credencial}` : null].filter(Boolean).join(" · "), icono: UserRoundIcon })) : []),
  ];
  const limpiar = () => { setTexto(""); busqueda.limpiar(); escaner.current?.limpiarCampo(); };
  return <div className="flex min-w-0 flex-col gap-3">
    <Escaner {...props} ref={escaner} alCambiarTexto={(q) => { setTexto(q); alCambiarTexto?.(q); }} onCodigo={(codigo, origen) => { limpiar(); onCodigo(codigo, origen); }} />
    {busqueda.estado === "corto" ? <p role="status" className="text-sm text-muted-foreground">Escribe al menos 2 letras o números.</p> : null}
    {busqueda.estado === "buscando" ? <p role="status" className="text-sm text-muted-foreground">Buscando…</p> : null}
    {busqueda.estado === "sin_conexion" ? <p role="status" className="text-sm text-muted-foreground">Sin conexión. Escanea el código o inténtalo cuando vuelva la señal.</p> : null}
    {busqueda.error ? <EstadoError error={busqueda.error} alReintentar={busqueda.buscarYa} /> : null}
    {datos && texto.trim().length >= 2 ? <div inert={busqueda.estado === "buscando" || props.activo === false} className={busqueda.estado === "buscando" ? "opacity-50" : undefined}>
      {candidatos.length ? <ul className="divide-y rounded-xl border bg-card">{candidatos.map((c) => <li key={c.codigo}><button type="button" className="flex min-h-12 w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring" onClick={() => { limpiar(); onCodigo(c.codigo, "teclado"); }}><c.icono aria-hidden="true" className="size-5 shrink-0 text-marino" /><span className="flex min-w-0 flex-col"><span className="font-semibold wrap-break-word">{c.nombre}</span><span className="text-sm text-muted-foreground wrap-break-word">{c.detalle}</span></span></button></li>)}</ul> : <EstadoVacio icono={SearchXIcon} titulo="No encontramos coincidencias" descripcion={`Prueba con otra parte de “${busqueda.textoDelResultado}”.`} accion={<Boton variante="contorno" onClick={limpiar}>Borrar búsqueda</Boton>} />}
    </div> : null}
  </div>;
}
