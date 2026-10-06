import { PackageIcon, Trash2Icon } from "lucide-react";
import { useEffect, useState } from "react";

import { api, apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { CampoEntero } from "~/componentes/catalogo/campos";
import { erroresPorCampo } from "~/componentes/catalogo/errores-campo";
import type { ArticuloFicha, ArticuloLista } from "~/componentes/catalogo/tipos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { textoLimiteDotacion, type Dotacion, type LimiteArticulo, type Puesto } from "./tipos";

interface Propiedades {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  puesto: Puesto | null;
  /** Solo quien administra el catálogo puede cambiarla; los demás la ven. */
  puedeEditar: boolean;
  alGuardar: () => void;
}

/** Un renglón en edición. `cantidad` es texto para poder borrar y reescribir sin que el campo salte. */
interface Renglon {
  articuloId: string;
  codigo: string;
  nombre: string;
  unidad: string;
  limite: LimiteArticulo | null;
  cantidad: string;
}

function aRenglones(dotacion: Dotacion): Renglon[] {
  return dotacion.renglones.map((r) => ({
    articuloId: r.articulo.id,
    codigo: r.articulo.codigo,
    nombre: r.articulo.nombre,
    unidad: r.articulo.unidad,
    limite: r.limite,
    cantidad: String(r.cantidad),
  }));
}

/** Qué cambia respecto de lo guardado, en una frase: "Se agregan 2 artículos y se quita 1". */
function resumenCambios(original: Renglon[], actual: Renglon[]): string | null {
  const antes = new Map(original.map((r) => [r.articuloId, r.cantidad]));
  const ahora = new Map(actual.map((r) => [r.articuloId, r.cantidad]));
  const agregados = actual.filter((r) => !antes.has(r.articuloId)).length;
  const quitados = original.filter((r) => !ahora.has(r.articuloId)).length;
  const cambiados = actual.filter((r) => antes.has(r.articuloId) && Number(antes.get(r.articuloId)) !== Number(r.cantidad)).length;
  const partes: string[] = [];
  if (agregados > 0) partes.push(agregados === 1 ? "se agrega 1 artículo" : `se agregan ${agregados} artículos`);
  if (quitados > 0) partes.push(quitados === 1 ? "se quita 1 artículo" : `se quitan ${quitados} artículos`);
  if (cambiados > 0) partes.push(cambiados === 1 ? "cambia la cantidad de 1 artículo" : `cambia la cantidad de ${cambiados} artículos`);
  if (partes.length === 0) return null;
  const frase = partes.length === 1 ? partes[0] : `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
  return frase.charAt(0).toUpperCase() + frase.slice(1) + ".";
}

/** Búsqueda de artículos activos para agregar a la dotación. */
function AgregarArticulo({ yaEstan, alElegir }: { yaEstan: Set<string>; alElegir: (articulo: ArticuloLista) => Promise<void> }) {
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const buscable = q.length >= 2;
  const [eligiendo, setEligiendo] = useState<string | null>(null);
  const consulta = useConsulta(
    (signal) => (buscable ? apiGet<Pagina<ArticuloLista>>("/articulos", { q, activo: true, tamano: 8 }, signal) : Promise.resolve(null)),
    buscable ? q : "",
  );
  const resultados = consulta.datos?.elementos ?? [];

  async function elegir(articulo: ArticuloLista) {
    setEligiendo(articulo.id);
    try {
      await alElegir(articulo);
      setTexto("");
    } finally {
      setEligiendo(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Campo
        etiqueta="Agregar un artículo"
        type="search"
        value={texto}
        autoComplete="off"
        placeholder="Busca por nombre o código"
        onChange={(e) => setTexto(e.target.value)}
      />
      {buscable && consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : null}
      {buscable && !consulta.error && !consulta.cargando && resultados.length === 0 ? (
        <p role="status" className="text-sm text-muted-foreground">
          No hay artículos activos con “{q}”.
        </p>
      ) : null}
      {buscable && resultados.length > 0 ? (
        <ul aria-label="Artículos encontrados" className="flex flex-col gap-2">
          {resultados.map((a) => {
            const repetido = yaEstan.has(a.id);
            return (
              <li key={a.id}>
                <button
                  type="button"
                  disabled={repetido || eligiendo !== null}
                  onClick={() => void elegir(a)}
                  className="flex min-h-12 w-full flex-col items-start gap-0.5 rounded-2xl border p-3 text-left hover:bg-muted disabled:opacity-60"
                >
                  <span className="flex flex-wrap items-center gap-2 text-base leading-tight font-semibold">
                    {a.nombre}
                    {repetido ? <Insignia estado="neutra">Ya está en la dotación</Insignia> : null}
                  </span>
                  <span className="text-sm text-muted-foreground">{[a.codigo, a.marca, a.categoria_nombre].filter(Boolean).join(" · ")}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

/**
 * Editor de la dotación recomendada de un puesto. El servidor reemplaza toda la lista al guardar
 * y valida (D-01: artículo repetido, inactivo o inexistente; D-04: cantidad mayor al límite).
 */
export function HojaDotacion({ abierta, alCambiar, puesto, puedeEditar, alGuardar }: Propiedades) {
  const consulta = useConsulta(
    (signal) => (abierta && puesto ? apiGet<Dotacion>(`/puestos/${puesto.id}/dotacion`, undefined, signal) : Promise.resolve(null)),
    abierta && puesto ? puesto.id : "",
  );
  const [original, setOriginal] = useState<Renglon[]>([]);
  const [renglones, setRenglones] = useState<Renglon[]>([]);
  const [errores, setErrores] = useState<Record<number, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  // Cada vez que se abre, parte de lo guardado en el servidor.
  useEffect(() => {
    if (!abierta) return;
    setErrores({});
    setGeneral(null);
    if (consulta.datos) {
      const lista = aRenglones(consulta.datos);
      setOriginal(lista);
      setRenglones(lista);
    }
  }, [abierta, consulta.datos]);

  const resumen = resumenCambios(original, renglones);

  async function agregar(articulo: ArticuloLista) {
    try {
      const ficha = await apiGet<ArticuloFicha>(`/articulos/${articulo.id}`);
      setRenglones((actual) => [
        ...actual,
        {
          articuloId: ficha.id,
          codigo: ficha.codigo,
          nombre: ficha.nombre,
          unidad: ficha.unidad,
          limite: ficha.limite_cantidad === null ? null : { cantidad: ficha.limite_cantidad, periodo_dias: ficha.limite_periodo_dias },
          cantidad: "1",
        },
      ]);
      setGeneral(null);
    } catch {
      setGeneral("No pudimos traer ese artículo. Inténtalo de nuevo.");
    }
  }

  function cambiarCantidad(indice: number, valor: string) {
    setRenglones((actual) => actual.map((r, i) => (i === indice ? { ...r, cantidad: valor } : r)));
    setErrores((e) => {
      if (!(indice in e)) return e;
      const { [indice]: _quitado, ...resto } = e;
      return resto;
    });
  }

  function quitar(indice: number) {
    setRenglones((actual) => actual.filter((_, i) => i !== indice));
    // Los errores van por posición: al quitar un renglón dejan de valer.
    setErrores({});
  }

  async function guardar() {
    if (!puesto) return;
    const locales: Record<number, string> = {};
    renglones.forEach((r, i) => {
      const n = Number(r.cantidad);
      if (!Number.isInteger(n) || n < 1 || n > 1000) locales[i] = "Escribe una cantidad entera de 1 a 1000.";
    });
    if (Object.keys(locales).length > 0) {
      setErrores(locales);
      return;
    }
    setGuardando(true);
    setErrores({});
    setGeneral(null);
    try {
      await api(`/puestos/${puesto.id}/dotacion`, {
        metodo: "PUT",
        cuerpo: { renglones: renglones.map((r) => ({ articulo_id: r.articuloId, cantidad: Number(r.cantidad) })) },
      });
      aviso({
        titulo: renglones.length === 0 ? "El puesto quedó sin dotación" : "La dotación quedó guardada",
        tipo: "exito",
      });
      alCambiar(false);
      alGuardar();
    } catch (causa) {
      const { campos, general: texto } = erroresPorCampo(causa);
      const porRenglon: Record<number, string> = {};
      const sueltos: string[] = [];
      for (const [campo, mensaje] of Object.entries(campos)) {
        const m = /^renglones\.(\d+)/.exec(campo);
        if (m) porRenglon[Number(m[1])] ??= mensaje;
        else sueltos.push(mensaje);
      }
      setErrores(porRenglon);
      setGeneral(texto ?? (sueltos.length > 0 ? sueltos.join(" ") : null));
    } finally {
      setGuardando(false);
    }
  }

  const yaEstan = new Set(renglones.map((r) => r.articuloId));
  const cargandoLista = abierta && consulta.datos === null && !consulta.error;

  let cuerpo;
  if (consulta.error && !consulta.datos) {
    cuerpo = <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  } else if (cargandoLista) {
    cuerpo = <Esqueleto tipo="lista" cantidad={3} />;
  } else {
    cuerpo = (
      <div className="flex flex-col gap-5">
        {renglones.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed p-6 text-center">
            <PackageIcon aria-hidden="true" className="size-6 text-muted-foreground" />
            <p className="text-base font-semibold text-marino">Este puesto no tiene dotación</p>
            <p className="text-sm text-muted-foreground">Sin dotación no se generan avisos al entregar.</p>
          </div>
        ) : (
          <ul aria-label="Artículos de la dotación" className="flex flex-col gap-3">
            {renglones.map((r, i) => (
              <li key={r.articuloId} className="flex flex-col gap-3 rounded-2xl border bg-card p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 flex-col">
                    <span className="text-base leading-tight font-semibold">{r.nombre}</span>
                    <span className="text-sm text-muted-foreground">{r.codigo}</span>
                  </div>
                  {puedeEditar ? (
                    <Boton variante="texto" aria-label={`Quitar ${r.nombre}`} onClick={() => quitar(i)} className="-mr-2 shrink-0">
                      <Trash2Icon aria-hidden="true" />
                      Quitar
                    </Boton>
                  ) : null}
                </div>
                {puedeEditar ? (
                  <CampoEntero
                    etiqueta={`Cantidad recomendada (${r.unidad})`}
                    value={r.cantidad}
                    max={1000}
                    onChange={(e) => cambiarCantidad(i, e.target.value)}
                    error={errores[i]}
                    ayuda={textoLimiteDotacion(r.limite)}
                    claseContenedor="max-w-48"
                  />
                ) : (
                  <p className="text-sm">
                    Cantidad recomendada: <strong>{r.cantidad}</strong> {r.unidad} · {textoLimiteDotacion(r.limite)}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
        {puedeEditar ? <AgregarArticulo yaEstan={yaEstan} alElegir={agregar} /> : null}
      </div>
    );
  }

  return (
    <Hoja
      abierta={abierta}
      alCambiar={(a) => !guardando && alCambiar(a)}
      titulo={puesto ? `Dotación de ${puesto.nombre}` : "Dotación"}
      descripcion="Lo que se recomienda entregar a quien ocupa este puesto. Al entregar algo fuera de esto, el sistema avisa pero no bloquea."
      pie={
        puedeEditar ? (
          <>
            {general ? (
              <p role="alert" className="text-sm font-medium text-destructive">
                {general}
              </p>
            ) : null}
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {resumen ?? "Sin cambios por guardar."}
            </p>
            <Boton variante="principal" onClick={() => void guardar()} cargando={guardando} disabled={resumen === null || cargandoLista}>
              Guardar dotación
            </Boton>
          </>
        ) : undefined
      }
    >
      {cuerpo}
    </Hoja>
  );
}
