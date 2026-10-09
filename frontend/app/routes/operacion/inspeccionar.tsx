import { LoteInspecciones } from "~/componentes/inspecciones/lote-inspecciones";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { FichaPieza } from "~/componentes/consulta/tipos";
import { Escaner } from "~/componentes/dominio/escaner";
import { RegistroInspeccion } from "~/componentes/inspecciones/registro-inspeccion";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { refrescarContadores } from "~/sesion/contadores";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "piezas.inspeccionar" };
export default function Inspeccionar() {
  const [parametros, setParametros] = useSearchParams();
  const [varias, setVarias] = useState(false);
  const id = parametros.get("pieza");
  const [buscando, setBuscando] = useState(false); const [error, setError] = useState<string | null>(null);
  const [guardada, setGuardada] = useState(false);
  const ficha = useConsulta((signal) => id ? apiGet<FichaPieza>(`/piezas/${id}`, undefined, signal) : Promise.resolve(null), id ?? "sin-pieza");
  async function escanear(codigo: string) {
    if (buscando) return; setBuscando(true); setError(null); setGuardada(false);
    try { const resultado = await apiGet<{ tipo: string; id: string | null }>(`/escaneo/${encodeURIComponent(codigo)}`); if (resultado.tipo !== "PIEZA" || !resultado.id) { setError("Escanea el código de la pieza, no el del artículo."); return; } setParametros({ pieza: resultado.id }); }
    catch (causa) { setError(mensajeDeError(causa)); } finally { setBuscando(false); }
  }
  if (varias) return <Pantalla titulo="Inspeccionar varias piezas" ancho="formulario"><Boton variante="texto" onClick={() => setVarias(false)}>Volver a una pieza</Boton><LoteInspecciones /></Pantalla>;
  return <Pantalla titulo="Inspeccionar pieza" ancho="formulario" descripcion="Revisa el equipo y registra el resultado de hoy.">
    <Boton variante="texto" nativeButton={false} render={<Link to="/inspecciones" />}>Volver a pendientes</Boton>
    {!id ? <Boton variante="contorno" onClick={() => setVarias(true)}>Varias piezas</Boton> : null}
    {!id || guardada ? <Escaner activo={!buscando} onCodigo={(c) => void escanear(c)} etiquetaCampo="Código de la pieza" /> : <Boton variante="contorno" onClick={() => { setParametros({}); setGuardada(false); }}>Escanear otra pieza</Boton>}
    {error ? <p role="alert" className="text-destructive">{error}</p> : null}
    {id && ficha.cargando ? <Esqueleto tipo="tarjeta" cantidad={2} /> : null}
    {ficha.error ? <EstadoError error={ficha.error} alReintentar={ficha.recargar} /> : null}
    {guardada ? <p role="status" className="font-semibold">Inspección guardada. Puedes escanear la siguiente pieza.</p> : ficha.datos ? <RegistroInspeccion key={ficha.datos.id} pieza={ficha.datos} alGuardar={() => { setGuardada(true); refrescarContadores(); }} /> : null}
  </Pantalla>;
}
