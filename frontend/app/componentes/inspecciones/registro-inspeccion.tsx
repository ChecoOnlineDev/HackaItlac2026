import { useEffect, useRef, useState } from "react";
import { registrarInspeccion, type DatosInspeccion, type PuntosInspeccion } from "~/api/inspecciones";
import { mensajeDeError } from "~/api/errores";
import { ToggleGroup, ToggleGroupItem } from "~/components/ui/toggle-group";
import { Textarea } from "~/components/ui/textarea";
import { PUNTOS_INSPECCION, type ClavePunto, type FichaPieza } from "~/componentes/consulta/tipos";
import { nuevoIdCliente } from "~/componentes/entrega/borrador";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { aviso } from "~/componentes/ui/aviso";

export function RegistroInspeccion({ pieza, alGuardar, alPreparar, inicial }: { pieza: FichaPieza; alGuardar: () => void; alPreparar?: (datos: DatosInspeccion) => void; inicial?: DatosInspeccion }) {
  const [puntos, setPuntos] = useState<Partial<PuntosInspeccion>>(inicial?.puntos ?? {});
  const [resultado, setResultado] = useState<"APTO" | "NO_APTO" | "">(inicial?.resultado ?? "");
  const [observacion, setObservacion] = useState(inicial?.observacion ?? "");
  const [foto, setFoto] = useState<string | undefined>(inicial?.foto);
  const [leyendoFoto, setLeyendoFoto] = useState(false);
  const lectorRef = useRef<FileReader | null>(null);
  useEffect(() => () => { lectorRef.current?.abort(); }, []);
  const [idCliente] = useState(() => inicial?.id_cliente ?? nuevoIdCliente());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const completos = PUNTOS_INSPECCION.every((p) => p.clave in puntos);
  const mal = Object.values(puntos).some((valor) => valor === false);
  function marcar(clave: ClavePunto, valor: string) {
    if (!valor) return;
    setPuntos((p) => ({ ...p, [clave]: valor === "bien" ? true : valor === "mal" ? false : null }));
    if (valor === "mal") setResultado((r) => r || "NO_APTO");
  }
  async function guardar() {
    if (guardando || leyendoFoto) return;
    if (!completos || !resultado) { setError("Contesta los cinco puntos y elige el resultado."); return; }
    if ((resultado === "NO_APTO" || mal) && !observacion.trim()) { setError("Explica el daño o por qué la consideras apta con un punto mal."); return; }
    setGuardando(true); setError(null);
    try {
      const datos = { id_cliente: idCliente, resultado, puntos: puntos as PuntosInspeccion, observacion: observacion.trim() || undefined, foto };
      if (alPreparar) { alPreparar(datos); return; }
      await registrarInspeccion(pieza.id, datos);
      aviso({ titulo: "Inspección guardada.", tipo: "exito" }); alGuardar();
    } catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  return <div className="flex flex-col gap-5">
    <div className="flex flex-col gap-1"><p className="font-semibold">{pieza.articulo.nombre} · {pieza.codigo}</p><p className="text-sm text-muted-foreground">{pieza.numero_serie || "Serie pendiente"} · {pieza.ubicacion?.texto ?? "Ubicación no indicada"}</p><p className="text-sm">Una inspección dura {pieza.vigencia_inspeccion_dias ?? pieza.articulo.vigencia_inspeccion_dias ?? "—"} días. Vigencia actual: {pieza.inspeccion_vigente_hasta ? formatearFecha(pieza.inspeccion_vigente_hasta) : "Sin inspección"}.</p></div>
    {pieza.historial.filter((h) => h.tipo === "INSPECCION").length ? <details><summary>Últimas inspecciones</summary><ul className="mt-2 flex flex-col gap-2">{pieza.historial.filter((h) => h.tipo === "INSPECCION").slice(0, 3).map((h, i) => <li key={`${h.fecha}-${i}`} className="text-sm">{formatearFecha(h.fecha)} · {h.resultado ?? h.titulo} · {h.usuario ?? "Usuario no indicado"}</li>)}</ul></details> : null}
    {pieza.inspeccion_posible?.puede === false ? <p role="alert">{pieza.inspeccion_posible.motivo}</p> : null}
    <fieldset className="flex flex-col gap-3" disabled={guardando || pieza.inspeccion_posible?.puede === false}><legend className="mb-2 font-semibold">Revisa los cinco puntos</legend>
      {PUNTOS_INSPECCION.map((p) => <div className="flex flex-col gap-2 rounded-xl border p-3" key={p.clave}><p id={`punto-${p.clave}`}>{p.etiqueta}</p><ToggleGroup aria-labelledby={`punto-${p.clave}`} value={p.clave in puntos ? [puntos[p.clave] === true ? "bien" : puntos[p.clave] === false ? "mal" : "no-aplica"] : []} onValueChange={(v) => marcar(p.clave, v[0] ?? "")} variant="outline"><ToggleGroupItem value="bien">Bien</ToggleGroupItem><ToggleGroupItem value="mal">Mal</ToggleGroupItem><ToggleGroupItem value="no-aplica">No aplica</ToggleGroupItem></ToggleGroup></div>)}
    </fieldset>
    <fieldset disabled={guardando || pieza.inspeccion_posible?.puede === false}><legend className="mb-2 font-semibold">Resultado</legend><ToggleGroup value={resultado ? [resultado] : []} onValueChange={(v) => setResultado((v[0] as "APTO" | "NO_APTO") || "")} variant="outline"><ToggleGroupItem value="APTO">Apta</ToggleGroupItem><ToggleGroupItem value="NO_APTO">No apta</ToggleGroupItem></ToggleGroup></fieldset>
    <div className="flex flex-col gap-1.5"><label htmlFor="observacion-inspeccion">Observaciones{resultado === "NO_APTO" || mal ? " (obligatorias)" : " (opcional)"}</label><Textarea id="observacion-inspeccion" value={observacion} onChange={(e) => setObservacion(e.target.value)} maxLength={1000} disabled={guardando} /></div>
    <div className="flex flex-col gap-2"><label htmlFor="foto-inspeccion">Foto de la inspección (opcional)</label><input id="foto-inspeccion" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" disabled={guardando || leyendoFoto} onChange={(e) => {
      const archivo = e.target.files?.[0]; setFoto(undefined); setError(null);
      if (!archivo) return;
      if (archivo.size > 3 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(archivo.type)) { setError("Elige una foto JPG, PNG o WebP de hasta 3 MB."); e.target.value = ""; return; }
      setLeyendoFoto(true);
      const lector = new FileReader(); lectorRef.current = lector; lector.onload = () => { setFoto(String(lector.result)); setLeyendoFoto(false); }; lector.onerror = () => { setError("No pudimos leer la foto. Elige otra."); setLeyendoFoto(false); }; lector.readAsDataURL(archivo);
    }} />{foto ? <img src={foto} alt="Foto elegida para la inspección" className="max-h-48 rounded-xl object-contain" /> : null}</div>
    {resultado === "APTO" && pieza.vigencia_si_apta_hoy ? <p className="font-semibold">Quedará vigente hasta {formatearFecha(pieza.vigencia_si_apta_hoy)}.</p> : null}
    {error ? <p role="alert" className="text-destructive">{error}</p> : null}
    <Boton variante="normal" cargando={guardando} disabled={leyendoFoto || !completos || !resultado || pieza.inspeccion_posible?.puede === false} onClick={() => void guardar()}>{alPreparar ? "Preparar revisión para el lote" : "Guardar inspección"}</Boton>
  </div>;
}
