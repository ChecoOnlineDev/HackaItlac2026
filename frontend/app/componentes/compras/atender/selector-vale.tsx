import { CircleAlertIcon, SearchIcon } from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";

import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { instanteUtc } from "~/componentes/consulta/formato";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { ListaDesplegable, type OpcionLista } from "~/componentes/ui/lista-desplegable";
import type { ValeEntradaLista } from "./tipos";

interface ResultadoEscaneo {
  tipo: string;
  id: string | null;
  resumen?: { folio?: string; tipo?: string; tipo_texto?: string; estado?: string; almacen_clave?: string };
}

export interface ValeElegido {
  id: string;
  folio: string;
}

interface PropiedadesSelectorVale {
  /** Id del vale elegido, o "" si no se liga ninguno. */
  valor: string;
  alElegir: (id: string, folio: string) => void;
  /** Error del servidor sobre el vale (SC-06), junto al control. */
  error?: string | null;
}

/**
 * Elige el vale de ENTRADA con el que Compras metió lo comprado al almacén (SC-06). Es opcional: sin vale, la
 * solicitud se ingresa igual. Ofrece las últimas entradas que el usuario ve y, si la que busca no está, un campo
 * para escribir o pegar el folio. El servidor decide si el vale sirve.
 */
export function SelectorVale({ valor, alElegir, error }: PropiedadesSelectorVale) {
  const idFolio = useId();
  const [folio, setFolio] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  // Vales que el usuario trajo con el folio y que no están entre las últimas entradas.
  const [extra, setExtra] = useState<ValeElegido[]>([]);

  const lista = useConsulta(
    (signal) => apiGet<Pagina<ValeEntradaLista>>("/vales", { tipo: "ENTRADA", tamano: 30 }, signal),
    "vales-entrada",
  );

  const opciones = useMemo<OpcionLista[]>(() => {
    const deLista = (lista.datos?.elementos ?? [])
      .filter((v) => v.estado !== "CANCELADO")
      .map((v) => ({
        valor: v.id,
        texto: `${v.folio} · ${v.almacen.clave} · ${formatearFechaHora(instanteUtc(v.creado_en))}`,
      }));
    const ids = new Set(deLista.map((o) => o.valor));
    return [...extra.filter((e) => !ids.has(e.id)).map((e) => ({ valor: e.id, texto: e.folio })), ...deLista];
  }, [lista.datos, extra]);

  // Si el vale elegido ya no está en las opciones (por ejemplo, se recargó la lista), se suelta.
  useEffect(() => {
    if (valor && opciones.length > 0 && !opciones.some((o) => o.valor === valor)) alElegir("", "");
    // Solo importa cuando cambian las opciones.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opciones]);

  async function buscarFolio() {
    const codigo = folio.trim();
    if (!codigo) return;
    setBuscando(true);
    setAviso(null);
    try {
      const r = await apiGet<ResultadoEscaneo>(`/escaneo/${encodeURIComponent(codigo)}`);
      if (r.tipo !== "VALE" || !r.id) {
        setAviso("No encontramos un vale con ese folio. Revísalo o elige uno de la lista.");
      } else if (r.resumen?.tipo && r.resumen.tipo !== "ENTRADA") {
        setAviso(`Ese folio es de ${(r.resumen.tipo_texto ?? "otro tipo de vale").toLowerCase()}, no de una entrada.`);
      } else {
        const encontrado = { id: r.id, folio: r.resumen?.folio ?? codigo.toUpperCase() };
        setExtra((previos) => [encontrado, ...previos.filter((p) => p.id !== encontrado.id)]);
        alElegir(encontrado.id, encontrado.folio);
        setFolio("");
      }
    } catch (causa) {
      setAviso(mensajeDeError(causa));
    } finally {
      setBuscando(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${idFolio}-lista`} className="text-sm font-medium text-foreground">
          Vale de entrada (opcional)
        </label>
        <ListaDesplegable
          id={`${idFolio}-lista`}
          valor={valor}
          alCambiar={(id) => alElegir(id, opciones.find((o) => o.valor === id)?.texto.split(" · ")[0] ?? "")}
          opciones={opciones}
          vacio="Sin ligar un vale"
          deshabilitado={lista.cargando && !lista.datos}
          invalido={Boolean(error)}
          descritoPor={error ? `${idFolio}-error` : undefined}
        />
        {lista.error ? (
          <p className="text-sm text-muted-foreground">No pudimos cargar tus últimas entradas. Puedes escribir el folio abajo.</p>
        ) : (
          <p className="text-sm text-muted-foreground">Liga el vale con el que registraste lo comprado. Así queda a la vista de quien lo pidió.</p>
        )}
      </div>

      <div className="flex items-end gap-2">
        <Campo
          etiqueta="¿No está en la lista? Escribe el folio"
          claseContenedor="min-w-0 flex-1"
          value={folio}
          placeholder="Por ejemplo KEP-ING-000012"
          autoComplete="off"
          onChange={(e) => {
            setFolio(e.target.value);
            setAviso(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              void buscarFolio();
            }
          }}
        />
        <Boton variante="contorno" cargando={buscando} disabled={!folio.trim()} onClick={() => void buscarFolio()} className="h-11">
          {buscando ? null : <SearchIcon aria-hidden="true" />}
          Buscar
        </Boton>
      </div>
      {aviso ? (
        <p role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {aviso}
        </p>
      ) : null}
      {error ? (
        <p id={`${idFolio}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
