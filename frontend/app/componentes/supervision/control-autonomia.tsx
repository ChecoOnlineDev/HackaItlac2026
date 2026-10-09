import { useEffect, useState } from "react";
import { apiPatch } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { aviso } from "~/componentes/ui/aviso";
import { useSesion } from "~/sesion/sesion";

/** DE-14: un cambio administrativo separado de los datos generales, con motivo auditable. */
export function ControlAutonomia({ ruta, campo, valor, etiqueta, alGuardar, bloqueado = false }: {
  ruta: string; campo: "despacho_autonomo" | "despacho_epp_con_aprobacion"; valor: boolean;
  etiqueta: string; alGuardar: (valor: boolean) => void; bloqueado?: boolean;
}) {
  const { puede } = useSesion();
  const [actual, setActual] = useState(valor);
  const [seleccionado, setSeleccionado] = useState(valor);
  const [motivo, setMotivo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { setActual(valor); setSeleccionado(valor); setMotivo(""); setError(null); }, [ruta, valor]);
  if (!puede("despacho.autonomia")) return null;
  const guardar = async () => {
    if (guardando || bloqueado || seleccionado === actual) return;
    if (!motivo.trim()) { setError("Escribe el motivo de este cambio."); return; }
    setGuardando(true); setError(null);
    try {
      const resultado = await apiPatch<Record<string, boolean>>(ruta, { [campo]: seleccionado, motivo: motivo.trim() });
      const nuevo = resultado[campo];
      setActual(nuevo); setSeleccionado(nuevo); setMotivo("");
      alGuardar(nuevo);
      aviso({ titulo: "Configuración del despacho guardada", descripcion: "La siguiente entrega se revisará con esta configuración.", tipo: "exito" });
    } catch (causa) { setError(mensajeDeError(causa)); }
    finally { setGuardando(false); }
  };
  return <section className="flex flex-col gap-3 rounded-xl border p-3">
    <h3 className="text-base font-semibold">Despacho de equipo de protección</h3>
    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium">
      <input type="checkbox" checked={seleccionado} disabled={guardando || bloqueado} onChange={(e) => { setSeleccionado(e.target.checked); setError(null); }} />{etiqueta}
    </label>
    {seleccionado !== actual ? <>
      <Campo etiqueta="Motivo del cambio" value={motivo} onChange={(e) => { setMotivo(e.target.value); setError(null); }} maxLength={1000} disabled={guardando || bloqueado} required error={error} />
      <Boton type="button" variante="contorno" cargando={guardando} disabled={bloqueado || guardando || !motivo.trim()} onClick={() => void guardar()}>Guardar configuración del despacho</Boton>
      <p className="text-xs text-muted-foreground">Este cambio se registra con tu usuario y motivo, y no modifica los datos generales del formulario.</p>
    </> : error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
  </section>;
}
