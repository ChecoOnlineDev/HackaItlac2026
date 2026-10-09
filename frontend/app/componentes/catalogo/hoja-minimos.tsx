import { useState } from "react";
import { api, apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { Campo } from "~/componentes/ui/campo";
import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { EstadoError } from "~/componentes/ui/estado-error";
import { aviso } from "~/componentes/ui/aviso";
import { useConsulta } from "./usar-consulta";

export function HojaMinimos({ almacenId, alCerrar, alGuardar }: { almacenId: string; alCerrar: () => void; alGuardar: () => void }) {
  const [articulo, setArticulo] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const catalogo = useConsulta(async (signal) => {
    const resultado = await apiGet<Pagina<{ id: string; codigo: string; nombre: string }>>("/articulos", { activo: true, tamano: 200 }, signal);
    for (let pagina = 2; resultado.elementos.length < resultado.total; pagina++) {
      const siguiente = await apiGet<typeof resultado>("/articulos", { activo: true, tamano: 200, pagina }, signal);
      if (!siguiente.elementos.length) break;
      resultado.elementos.push(...siguiente.elementos);
    }
    return resultado;
  }, "articulos-minimos");
  const minimos = useConsulta((signal) => apiGet<{ articulo_id: string; cantidad: number }[]>(`/almacenes/${almacenId}/minimos`, undefined, signal), almacenId);
  function elegir(id: string) { setArticulo(id); setCantidad(String(minimos.datos?.find((m) => m.articulo_id === id)?.cantidad ?? "")); setError(null); }
  async function guardar(borrar = false) {
    if (!articulo || guardando) return;
    const numero = Number(cantidad);
    if (!borrar && (!cantidad.trim() || !Number.isInteger(numero) || numero < 0 || numero > 100000)) { setError("Escribe un número entero entre 0 y 100000."); return; }
    setGuardando(true); setError(null);
    try {
      await api(`/almacenes/${almacenId}/minimos`, { metodo: "PUT", cuerpo: { minimos: [{ articulo_id: articulo, cantidad: borrar ? null : numero }] } });
      aviso({ titulo: borrar ? "Mínimo eliminado." : "Mínimo guardado.", tipo: "exito" });
      alGuardar(); alCerrar();
    } catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  return <Hoja abierta alCambiar={(a) => !a && !guardando && alCerrar()} titulo="Mínimo de inventario" descripcion="El aviso aparece cuando lo disponible queda por debajo de esta cantidad." pie={<div className="flex flex-wrap gap-2"><Boton variante="normal" cargando={guardando} disabled={!articulo || !cantidad || Boolean(catalogo.error || minimos.error)} onClick={() => void guardar()}>Guardar mínimo</Boton><Boton variante="contorno" disabled={guardando || !minimos.datos?.some((m) => m.articulo_id === articulo)} onClick={() => void guardar(true)}>Quitar mínimo</Boton></div>}>
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5"><label htmlFor="articulo-minimo">Artículo</label><ListaDesplegable id="articulo-minimo" valor={articulo} alCambiar={elegir} deshabilitado={guardando || catalogo.cargando || minimos.cargando} opciones={(catalogo.datos?.elementos ?? []).map((a) => ({ valor: a.id, texto: `${a.nombre} (${a.codigo})` }))} /></div>
      <Campo etiqueta="Cantidad mínima disponible" type="number" inputMode="numeric" min={0} max={100000} step={1} value={cantidad} disabled={guardando} onChange={(e) => { setCantidad(e.target.value); setError(null); }} error={error} ayuda="Quitar el mínimo elimina el aviso de este artículo, sin cambiar las existencias." />
      {catalogo.error ? <EstadoError error={catalogo.error} alReintentar={catalogo.recargar} /> : null}
      {minimos.error ? <EstadoError error={minimos.error} alReintentar={minimos.recargar} /> : null}
    </div>
  </Hoja>;
}
