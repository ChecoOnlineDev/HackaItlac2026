import { Link, useParams } from "react-router";
import { useState } from "react";
import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { CodigoQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { LEYENDA_RESPONSABILIDAD } from "~/componentes/dominio/vale-imprimible";
import { Button } from "~/components/ui/button";

interface Comprobante {
  folio: string;
  creado_en: string;
  integridad: "Íntegro" | "Alterado" | "Sin sello" | "Borrador";
  trabajador: { nombre: string; numero_empleado: string } | null;
  articulos: { renglon: number; codigo: string; nombre: string; marca: string | null;
    modelo: string | null; talla: string | null; numero_serie: string | null;
    cantidad: number; condicion: string | null }[];
}

function Copia({ datos, token, segunda = false }: { datos: Comprobante; token: string; segunda?: boolean }) {
  return <article className={`comprobante-copia rounded-xl border bg-white p-6 text-neutral-950 ${segunda ? "hidden print:block" : ""}`}>
    <header className="flex items-start justify-between gap-4">
      <div><p className="text-sm font-semibold tracking-wide">IMHOTEP · Comprobante</p>
        <h1 className="mt-1 text-2xl font-bold">{datos.folio}</h1>
        <p className="mt-1 text-sm">{new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Mexico_City" }).format(new Date(datos.creado_en))}</p>
      </div>
      <CodigoQR valor={urlDeVale(token)} tamano={88} titulo="Verificar este comprobante" />
    </header>
    <p className="mt-4 font-semibold">Estado: {datos.integridad}</p>
    {datos.integridad === "Alterado" && <p role="alert" className="mt-2 rounded-lg bg-red-50 p-3 text-red-900">El sello no coincide. Comunícalo al supervisor para que revise el registro.</p>}
    {datos.integridad === "Sin sello" && <p className="mt-2 text-sm">Este vale se emitió antes de activar los sellos de integridad.</p>}
    {datos.integridad === "Borrador" && <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">Ticket preparado. Falta recibir la foto del documento firmado para emitir el vale.</p>}
    {datos.trabajador && <p className="mt-4">{datos.trabajador.nombre} · {datos.trabajador.numero_empleado}</p>}
    <ul className="mt-4 divide-y">
      {datos.articulos.map(a => <li key={a.renglon} className="flex gap-3 py-3">
        <strong className="min-w-8">{a.cantidad}</strong>
        <div><p className="font-medium">{a.nombre}</p>
          <p className="text-sm">{[a.codigo, a.marca, a.modelo, a.talla, a.numero_serie].filter(Boolean).join(" · ")}</p>
          {a.condicion && <p className="text-sm">Condición: {a.condicion === "BUENO" ? "Buena" : a.condicion === "DESGASTE" ? "Desgaste" : "Dañado"}</p>}
        </div>
      </li>)}
    </ul>
    <p className="mt-5 text-sm leading-relaxed">{LEYENDA_RESPONSABILIDAD}</p>
    <div className="mt-10 border-t pt-2 text-center text-sm">Firma del trabajador · {segunda ? "Copia del almacén" : "Copia del trabajador"}</div>
  </article>;
}

export default function ComprobantePublico() {
  const [formato, setFormato] = useState<"carta" | "ticket">("carta");
  const { token = "" } = useParams();
  const consulta = useConsulta(signal => apiGet<Comprobante>(`/publico/vales/${encodeURIComponent(token)}`, undefined, signal), token);
  return <main className={`comprobante-${formato} mx-auto max-w-2xl space-y-4 px-4 py-6`}>
    <nav className="flex flex-wrap items-center justify-between gap-3 print:hidden">
      <p className="text-sm text-muted-foreground">Comprobante del trabajador</p>
      <Link to={`/vales/ver-qr/${encodeURIComponent(token)}`} className="text-sm text-primary underline underline-offset-4">Abrir en operación</Link>
    </nav>
    {consulta.cargando && !consulta.datos && <p role="status">Abriendo comprobante…</p>}
    {Boolean(consulta.error) && <div role="alert" className="rounded-xl border p-4"><p>No se pudo abrir este comprobante. Revisa el código e inténtalo de nuevo.</p><Button variant="outline" onClick={consulta.recargar} className="mt-3">Intentar de nuevo</Button></div>}
    {consulta.datos && <>
      <div className="flex flex-wrap items-end gap-3 print:hidden"><label className="flex flex-col gap-1 text-sm">Papel<select className="h-11 rounded-lg border bg-background px-3" value={formato} onChange={(e) => setFormato(e.target.value as "carta" | "ticket")}><option value="carta">Carta</option><option value="ticket">Ticket de 80 mm</option></select></label><Button onClick={() => window.print()}>Imprimir dos copias</Button></div>
      <Copia datos={consulta.datos} token={token} />
      <Copia datos={consulta.datos} token={token} segunda />
    </>}
    <style>{`@media print { @page { size: ${formato === "carta" ? "letter" : "80mm auto"}; margin: ${formato === "carta" ? "12mm" : "2mm"}; } .comprobante-copia { break-inside: avoid; border: 0; box-shadow: none; margin-bottom: 16mm; } .comprobante-ticket { width: 76mm; max-width: 76mm; padding: 0; } .comprobante-ticket .comprobante-copia { padding: 3mm; overflow-wrap: anywhere; } .comprobante-ticket header { flex-wrap: wrap; } .comprobante-ticket h1 { font-size: 16px; } }`}</style>
  </main>;
}
