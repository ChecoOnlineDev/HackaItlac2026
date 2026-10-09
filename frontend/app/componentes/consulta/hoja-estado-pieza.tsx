import { useEffect, useState } from "react";
import { apiPost } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { aviso } from "~/componentes/ui/aviso";
import type { FichaPieza } from "./tipos";

export function HojaEstadoPieza({ pieza, abierta, alCambiar, alGuardar }: { pieza: FichaPieza; abierta: boolean; alCambiar: (abierta: boolean) => void; alGuardar: () => void }) {
  const [estado, setEstado] = useState("EN_MANTENIMIENTO");
  const [observacion, setObservacion] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (abierta) { setEstado(pieza.estado === "EN_MANTENIMIENTO" ? (!pieza.articulo.requiere_inspeccion ? "APTO" : "NO_APTO") : "EN_MANTENIMIENTO"); setObservacion(""); setError(null); } }, [abierta, pieza.estado, pieza.articulo.requiere_inspeccion]);
  async function guardar() {
    if (guardando) return;
    if (!observacion.trim()) { setError("Escribe el motivo del cambio."); return; }
    setGuardando(true); setError(null);
    try {
      await apiPost(`/piezas/${pieza.id}/estado`, { estado, observacion: observacion.trim() });
      aviso({ titulo: "Estado de la pieza guardado.", tipo: "exito" }); alCambiar(false); alGuardar();
    } catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  const opciones = [{ valor: "EN_MANTENIMIENTO", texto: "En mantenimiento" }, { valor: "EN_CALIBRACION", texto: "En calibración" }];
  if (["EN_MANTENIMIENTO", "EN_CALIBRACION"].includes(pieza.estado) && !pieza.articulo.requiere_inspeccion) opciones.push({ valor: "APTO", texto: "Apta, volver a disponible" });
  if (["EN_MANTENIMIENTO", "EN_CALIBRACION"].includes(pieza.estado) && pieza.articulo.requiere_inspeccion) opciones.push({ valor: "NO_APTO", texto: "Regresar al servicio, pendiente de inspección" });
  return <Hoja abierta={abierta} alCambiar={(a) => !guardando && alCambiar(a)} titulo="Mantenimiento o calibración" descripcion={`${pieza.articulo.nombre} · ${pieza.codigo}`} pie={<Boton variante="normal" cargando={guardando} onClick={() => void guardar()}>Guardar estado</Boton>}>
    <div className="flex flex-col gap-4"><p>Las piezas en mantenimiento o calibración no están disponibles para entregar.</p><div className="flex flex-col gap-1.5"><label htmlFor="estado-pieza">Nuevo estado</label><ListaDesplegable id="estado-pieza" valor={estado} alCambiar={setEstado} deshabilitado={guardando} opciones={opciones} /></div>
      {pieza.articulo.requiere_inspeccion ? <p className="text-sm text-muted-foreground">Regresa la pieza al servicio como pendiente de inspección y luego registra una inspección nueva para declararla apta.</p> : null}
      <Campo etiqueta="Motivo" value={observacion} onChange={(e) => setObservacion(e.target.value)} required maxLength={1000} disabled={guardando} error={error} />
    </div>
  </Hoja>;
}
