import { useRef, useState } from "react";
import { apiGet } from "~/api/cliente";
import { registrarLoteInspecciones, type DatosInspeccion, type ResultadoLoteInspeccion } from "~/api/inspecciones";
import { mensajeDeError } from "~/api/errores";
import { PUNTOS_INSPECCION, type FichaPieza } from "~/componentes/consulta/tipos";
import { Escaner } from "~/componentes/dominio/escaner";
import { reproducir } from "~/componentes/dominio/sonido";
import { nuevoIdCliente } from "~/componentes/entrega/borrador";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { refrescarContadores } from "~/sesion/contadores";
import { RegistroInspeccion } from "./registro-inspeccion";

interface ElementoLote { pieza: FichaPieza; datos: DatosInspeccion; editada: boolean }
export function LoteInspecciones() {
  const [idLote, setIdLote] = useState(nuevoIdCliente);
  const [piezas, setPiezas] = useState<ElementoLote[]>([]);
  const [leyendo, setLeyendo] = useState(false); const leyendoRef = useRef(false);
  const [guardando, setGuardando] = useState(false); const [enviado, setEnviado] = useState(false); const [confirmando, setConfirmando] = useState(false);
  const [editando, setEditando] = useState<ElementoLote | null>(null);
  const [error, setError] = useState<string | null>(null); const [resultado, setResultado] = useState<ResultadoLoteInspeccion | null>(null);
  async function agregar(codigo: string) {
    if (leyendoRef.current || guardando || enviado) return;
    if (piezas.length >= 50) { setError("Guarda este lote y empieza otro. El máximo es 50 piezas."); return; }
    leyendoRef.current = true; setLeyendo(true); setError(null);
    try {
      const escaneo = await apiGet<{ tipo: string; id: string | null }>(`/escaneo/${encodeURIComponent(codigo)}`);
      if (escaneo.tipo !== "PIEZA" || !escaneo.id) { setError("Escanea el código de la pieza, no el del artículo."); return; }
      if (piezas.some((p) => p.pieza.id === escaneo.id)) { reproducir("aviso"); setError("Esta pieza ya está en el lote."); return; }
      const pieza = await apiGet<FichaPieza>(`/piezas/${escaneo.id}`);
      const puntos = Object.fromEntries(PUNTOS_INSPECCION.map((p) => [p.clave, true])) as DatosInspeccion["puntos"];
      setPiezas((anteriores) => [...anteriores, { pieza, editada: false, datos: { id_cliente: nuevoIdCliente(), resultado: "APTO", puntos } }]); setResultado(null);
    } catch (causa) { setError(mensajeDeError(causa)); } finally { leyendoRef.current = false; setLeyendo(false); }
  }
  async function guardar() {
    if (guardando) return; setGuardando(true); setEnviado(true); setError(null);
    try { setResultado(await registrarLoteInspecciones(idLote, piezas.map((p) => ({ ...p.datos, codigo: p.pieza.codigo })))); setConfirmando(false); refrescarContadores(); }
    catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  return <div className="flex flex-col gap-4"><p>Escanea hasta 50 piezas. Abre las que tengan un problema para registrar sus cinco puntos y observación antes de guardar el lote.</p>
    <Escaner activo={!leyendo && !guardando && !editando && !confirmando && !enviado} onCodigo={(c) => void agregar(c)} etiquetaCampo="Escanear piezas del lote" />
    {error ? <p role="alert" className="text-destructive">{error}</p> : null}
    <ul className="flex flex-col gap-3">{piezas.map((p) => { const res = resultado?.resultados.find((r) => r.id_cliente === p.datos.id_cliente); return <li key={p.pieza.id} className="flex flex-col gap-2 rounded-xl border p-3"><p className="font-semibold">{p.pieza.articulo.nombre} · {p.pieza.codigo}</p><p className="text-sm">{p.pieza.inspeccion_vigente_hasta ?? "Sin inspección"} → {p.datos.resultado === "APTO" ? p.pieza.vigencia_si_apta_hoy ?? "La vigencia se confirma al guardar" : "No apta"}</p>{p.pieza.inspeccion_posible?.puede === false ? <p>{p.pieza.inspeccion_posible.motivo}</p> : null}{res ? <p role="status">{res.estado === "RECHAZADA" ? res.error?.mensaje ?? "No se pudo guardar" : "Inspección guardada"}</p> : null}<div className="flex flex-wrap gap-2"><Boton variante="contorno" disabled={guardando || enviado} onClick={() => setEditando(p)}>{p.editada ? "Editar revisión" : "Tiene un problema"}</Boton><Boton variante="texto" disabled={guardando || enviado} onClick={() => { setPiezas((lista) => lista.filter((a) => a.pieza.id !== p.pieza.id)); setResultado(null); }}>Quitar</Boton></div></li>; })}</ul>
    {resultado ? <p role="status">Guardadas: {resultado.guardadas}. Ya guardadas antes: {resultado.repetidas}. Rechazadas: {resultado.rechazadas}.</p> : null}
    <div className="flex flex-wrap gap-2"><Boton variante="normal" cargando={guardando} disabled={!piezas.length || leyendo || Boolean(resultado && !resultado.rechazadas)} onClick={() => setConfirmando(true)}>{resultado ? "Reintentar las pendientes" : `Guardar ${piezas.length} inspecciones`}</Boton>{resultado ? <Boton variante="contorno" onClick={() => { setPiezas([]); setResultado(null); setIdLote(nuevoIdCliente()); setEnviado(false); }}>Empezar otro lote</Boton> : null}</div>
    <Confirmacion abierta={confirmando} alCambiar={(a) => !guardando && setConfirmando(a)} mensaje={`¿Guardar la revisión de estas ${piezas.length} piezas?`} detalle={error ?? "Confirmo que revisé etiquetas, costuras, cintas, herrajes y conectores. Los puntos no modificados están bien; los problemas registrados conservan su resultado y observación. Cada pieza se guarda por separado."} cargando={guardando} alConfirmar={() => void guardar()} />
    <Hoja abierta={Boolean(editando)} alCambiar={(a) => !a && setEditando(null)} titulo="Revisión de una pieza del lote">{editando ? <RegistroInspeccion key={editando.pieza.id} pieza={editando.pieza} inicial={editando.editada ? editando.datos : undefined} alGuardar={() => {}} alPreparar={(datos) => { setPiezas((lista) => lista.map((p) => p.pieza.id === editando.pieza.id ? { ...p, editada: true, datos: { ...datos, id_cliente: p.datos.id_cliente } } : p)); setEditando(null); }} /> : null}</Hoja>
  </div>;
}
