import { useId, useState, type FormEvent } from "react";

import { crearArticulo, type ArticuloCreado } from "~/api/articulos";
import { apiGet } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";

interface CategoriaLista {
  id: string;
  nombre: string;
  control: "PIEZA" | "CANTIDAD";
}

interface Propiedades {
  /** Lo que se estaba buscando: se propone como nombre. */
  nombreInicial?: string;
  alCrear: (articulo: ArticuloCreado) => void;
  alCancelar: () => void;
}

/**
 * «Crear este artículo» (EK-07): formulario corto dentro de «Dar entrada». Pide nombre, categoría y unidad; la
 * categoría decide si se controla por cantidad o por pieza y el servidor genera el código.
 */
export function CrearArticulo({ nombreInicial = "", alCrear, alCancelar }: Propiedades) {
  const idCategoria = useId();
  const categorias = useConsulta(
    (signal) => apiGet<Pagina<CategoriaLista>>("/categorias", { activo: true, tamano: 200 }, signal),
    "entrada-crear-categorias",
  );
  const [nombre, setNombre] = useState(nombreInicial);
  const [categoriaId, setCategoriaId] = useState("");
  const [unidad, setUnidad] = useState("pieza");
  const [codigo, setCodigo] = useState("");
  const [pideCodigo, setPideCodigo] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const lista = categorias.datos?.elementos ?? [];
  const categoria = lista.find((c) => c.id === categoriaId) ?? null;

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (guardando) return;
    const locales: Record<string, string> = {};
    if (!nombre.trim()) locales.nombre = "Escribe el nombre del artículo.";
    if (!categoriaId) locales.categoria_id = "Elige una categoría.";
    if (!unidad.trim()) locales.unidad = "Escribe la unidad, por ejemplo “pieza” o “par”.";
    if (pideCodigo && !codigo.trim()) locales.codigo = "Escribe el código del artículo.";
    setErrores(locales);
    setErrorGeneral(null);
    if (Object.keys(locales).length > 0) return;

    setGuardando(true);
    try {
      const creado = await crearArticulo({
        nombre: nombre.trim(),
        categoria_id: categoriaId,
        unidad: unidad.trim(),
        ...(pideCodigo ? { codigo: codigo.trim() } : {}),
      });
      alCrear(creado);
    } catch (causa) {
      if (esErrorApi(causa) && causa.detalles?.motivo === "FALTA_CODIGO") {
        // La categoría no genera códigos (es una categoría de la empresa): se pide escribirlo.
        setPideCodigo(true);
        setErrores({ codigo: causa.message });
      } else if (esErrorApi(causa) && causa.campo && ["nombre", "categoria_id", "unidad", "codigo"].includes(causa.campo)) {
        setErrores({ [causa.campo]: causa.message });
      } else {
        setErrorGeneral(mensajeDeError(causa));
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form onSubmit={(e) => void guardar(e)} noValidate aria-labelledby="crear-articulo-titulo" className="flex flex-col gap-4 rounded-2xl border bg-card p-4">
      <div className="flex flex-col gap-1">
        <h2 id="crear-articulo-titulo" className="text-base font-semibold text-marino">
          Crear este artículo
        </h2>
        <p className="text-sm text-muted-foreground">Queda en el catálogo con un código que genera el sistema. Después captura cuánto entra.</p>
      </div>

      <Campo
        etiqueta="Nombre"
        value={nombre}
        maxLength={150}
        autoComplete="off"
        onChange={(e) => setNombre(e.target.value)}
        error={errores.nombre}
        disabled={guardando}
      />

      <div className="flex flex-col gap-1.5">
        <Label htmlFor={idCategoria} className="text-sm font-medium text-foreground">
          Categoría
        </Label>
        {categorias.error && !categorias.datos ? (
          <EstadoError error={categorias.error} alReintentar={categorias.recargar} className="p-3" />
        ) : (
          <ListaDesplegable
            id={idCategoria}
            valor={categoriaId}
            alCambiar={setCategoriaId}
            opciones={lista.map((c) => ({ valor: c.id, texto: c.nombre }))}
            marcador={categorias.cargando ? "Cargando categorías…" : "Elige una categoría"}
            deshabilitado={guardando || categorias.cargando}
            invalido={Boolean(errores.categoria_id)}
          />
        )}
        {errores.categoria_id ? (
          <p role="alert" className="text-sm font-medium">
            {errores.categoria_id}
          </p>
        ) : null}
        {categoria ? (
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground" role="status">
            Se controlará
            <Insignia estado="neutra">{categoria.control === "PIEZA" ? "Por pieza" : "Por cantidad"}</Insignia>
            {categoria.control === "PIEZA" ? "Cada pieza lleva su código y, si tiene, su número de serie." : "Solo importa cuántas hay."}
          </p>
        ) : null}
      </div>

      <Campo etiqueta="Unidad" value={unidad} maxLength={20} onChange={(e) => setUnidad(e.target.value)} error={errores.unidad} disabled={guardando} />

      {pideCodigo ? (
        <Campo
          etiqueta="Código del artículo"
          value={codigo}
          maxLength={64}
          autoComplete="off"
          ayuda="Esta categoría no genera códigos solos."
          onChange={(e) => setCodigo(e.target.value)}
          error={errores.codigo}
          disabled={guardando}
        />
      ) : null}

      {errorGeneral ? (
        <p role="alert" className="rounded-2xl border border-semaforo-rojo p-3 text-sm font-semibold">
          {errorGeneral}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Boton type="submit" variante="principal" cargando={guardando}>
          Crear y agregar a la entrada
        </Boton>
        <Boton type="button" variante="texto" disabled={guardando} onClick={alCancelar}>
          Cancelar
        </Boton>
      </div>
    </form>
  );
}
