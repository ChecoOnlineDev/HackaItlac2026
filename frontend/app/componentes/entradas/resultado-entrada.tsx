import { CircleCheckIcon, PackagePlusIcon } from "lucide-react";

import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { FolioQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { ValeImprimible, type ValeDetalle } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { ValeConfirmado } from "./tipos";

/** Forma de `GET /api/vales/{id}` (sin costos, F-12) que usa esta pantalla. */
interface ValeDelServidor {
  folio: string;
  token: string;
  tipo: ValeDetalle["tipo"];
  creado_en: string;
  almacen: { clave: string; nombre: string };
  responsable: { nombre: string };
  observacion: string | null;
  renglones: {
    renglon: number;
    articulo: string;
    marca: string | null;
    talla: string | null;
    codigo_articulo: string;
    codigo_pieza: string | null;
    numero_serie: string | null;
    cantidad: number;
  }[];
}

function aValeImprimible(v: ValeDelServidor): ValeDetalle {
  return {
    folio: v.folio,
    tipo: v.tipo,
    creado_en: v.creado_en,
    token: v.token,
    almacen: v.almacen,
    responsable: v.responsable,
    observacion: v.observacion,
    renglones: v.renglones.map((r) => ({
      renglon: r.renglon,
      articulo: { nombre: r.articulo, marca: r.marca, talla: r.talla },
      codigo: r.codigo_pieza ?? r.codigo_articulo,
      numero_serie: r.numero_serie,
      cantidad: r.cantidad,
    })),
  };
}

interface Propiedades {
  vale: ValeConfirmado;
  almacen: string;
  alNuevaEntrada: () => void;
}

/** Entrada registrada: folio en grande con su QR, "Nueva entrada" y el vale listo para imprimir. */
export function ResultadoEntrada({ vale, almacen, alNuevaEntrada }: Propiedades) {
  const detalle = useConsulta((signal) => apiGet<ValeDelServidor>(`/vales/${vale.id}`, undefined, signal), vale.id);

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="entrada-lista" className="flex flex-col items-center gap-4 rounded-2xl border border-semaforo-verde p-6 print:hidden">
        <h2 id="entrada-lista" className="flex items-center gap-2 text-lg font-semibold text-marino">
          <CircleCheckIcon aria-hidden="true" className="size-7 text-semaforo-verde" strokeWidth={3} />
          Entrada registrada
        </h2>
        <FolioQR
          folio={vale.folio}
          valor={urlDeVale(vale.token)}
          texto={`Entrada de inventario · ${almacen} · ${formatearFechaHora(vale.creado_en)}`}
        />
        <Boton variante="principal" onClick={alNuevaEntrada}>
          <PackagePlusIcon aria-hidden="true" />
          Nueva entrada
        </Boton>
      </section>

      {detalle.error ? (
        <EstadoError error={detalle.error} alReintentar={detalle.recargar} />
      ) : detalle.datos ? (
        <ValeImprimible vale={aValeImprimible(detalle.datos)} />
      ) : (
        <Esqueleto tipo="tarjeta" cantidad={1} />
      )}
    </div>
  );
}
