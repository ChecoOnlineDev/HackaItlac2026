import { useEffect, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { NotaBloqueo, Seleccion } from "./campos";
import { erroresPorCampo } from "./errores-campo";
import {
  estadoAReglas,
  FormularioReglas,
  REGLAS_VACIAS,
  reglasAEstado,
  validarReglas,
  type EstadoReglas,
} from "./formulario-reglas";
import type { Articulo, ArticuloFicha, Categoria, Control } from "./tipos";

interface Propiedades {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Artículo a editar; sin él, se da de alta uno nuevo. */
  articulo: ArticuloFicha | null;
  categorias: Categoria[];
  /** El costo solo se muestra y se captura con el permiso de costos. */
  puedeCostos: boolean;
  /** Categoría que se propone al dar de alta (la del filtro de la lista). */
  categoriaInicial?: string;
  alGuardar: (guardado: Articulo) => void;
}

const OPCIONES_CONTROL = [
  { valor: "CANTIDAD", texto: "Por cantidad (solo cuántas hay)" },
  { valor: "PIEZA", texto: "Por pieza (cada pieza tiene su código)" },
];
const OPCIONES_RETORNO = [
  { valor: "si", texto: "Retornable (se devuelve)" },
  { valor: "no", texto: "Consumible (no se devuelve)" },
];

const TIPO_CODIGO: Record<string, string> = {
  ARTICULO: "otro artículo",
  PIEZA: "una pieza",
  TRABAJADOR: "la credencial de un trabajador",
  VALE: "un vale",
};

function costoATexto(valor: Articulo["costo_unitario"]): string {
  return valor === null || valor === undefined ? "" : String(valor);
}

/** Alta y edición de un artículo: datos, control y retorno, y reglas de entrega. */
export function HojaArticulo({ abierta, alCambiar, articulo, categorias, puedeCostos, categoriaInicial, alGuardar }: Propiedades) {
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [marca, setMarca] = useState("");
  const [modelo, setModelo] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [control, setControl] = useState<Control>("CANTIDAD");
  const [retornable, setRetornable] = useState(true);
  const [talla, setTalla] = useState("");
  const [unidad, setUnidad] = useState("pieza");
  const [costo, setCosto] = useState("");
  const [reglas, setReglas] = useState<EstadoReglas>(REGLAS_VACIAS);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const bloqueado = articulo?.tiene_movimientos ?? false;
  const categoria = categorias.find((c) => c.id === categoriaId) ?? null;

  function tomarPlantilla(c: Categoria) {
    setControl(c.control);
    setRetornable(c.retornable);
    setReglas((actual) => ({ ...reglasAEstado(c), avisoInspeccion: articulo ? actual.avisoInspeccion : "" }));
  }

  useEffect(() => {
    if (!abierta) return;
    setErrores({});
    setGeneral(null);
    if (articulo) {
      setCodigo(articulo.codigo);
      setNombre(articulo.nombre);
      setMarca(articulo.marca ?? "");
      setModelo(articulo.modelo ?? "");
      setCategoriaId(articulo.categoria_id);
      setControl(articulo.control);
      setRetornable(articulo.retornable);
      setTalla(articulo.talla ?? "");
      setUnidad(articulo.unidad);
      setCosto(costoATexto(articulo.costo_unitario));
      setReglas(reglasAEstado(articulo));
    } else {
      setCodigo("");
      setNombre("");
      setMarca("");
      setModelo("");
      setTalla("");
      setUnidad("pieza");
      setCosto("");
      const inicial = categorias.find((c) => c.id === categoriaInicial) ?? null;
      setCategoriaId(inicial?.id ?? "");
      if (inicial) tomarPlantilla(inicial);
      else {
        setControl("CANTIDAD");
        setRetornable(true);
        setReglas(REGLAS_VACIAS);
      }
    }
    // Se reinicia solo al abrir o al cambiar de artículo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierta, articulo]);

  function elegirCategoria(id: string) {
    setCategoriaId(id);
    const elegida = categorias.find((c) => c.id === id);
    // Al dar de alta, la categoría trae su plantilla. Al editar, se ofrece con un botón.
    if (elegida && !articulo) tomarPlantilla(elegida);
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const locales = validarReglas(reglas, control);
    if (!articulo && codigo.trim() === "") locales.codigo = "Escribe el código del artículo.";
    if (nombre.trim() === "") locales.nombre = "Escribe el nombre del artículo.";
    if (categoriaId === "") locales.categoria_id = "Elige una categoría.";
    if (unidad.trim() === "") locales.unidad = "Escribe la unidad, por ejemplo “pieza” o “par”.";
    if (puedeCostos && costo.trim() !== "" && !(Number(costo) >= 0)) locales.costo_unitario = "Escribe un costo válido.";
    if (Object.keys(locales).length > 0) {
      setErrores(locales);
      return;
    }
    setGuardando(true);
    setErrores({});
    setGeneral(null);

    const comunes = {
      nombre: nombre.trim(),
      marca: marca.trim() || null,
      modelo: modelo.trim() || null,
      talla: talla.trim() || null,
      unidad: unidad.trim(),
      ...estadoAReglas(reglas),
      ...(puedeCostos ? { costo_unitario: costo.trim() === "" ? null : Number(costo).toFixed(2) } : {}),
    };

    try {
      let guardado: Articulo;
      if (articulo) {
        guardado = await apiPatch<Articulo>(`/articulos/${articulo.id}`, {
          ...comunes,
          ...(categoriaId !== articulo.categoria_id ? { categoria_id: categoriaId } : {}),
          // Con movimientos, control y retorno no se mandan: el servidor los rechazaría.
          ...(bloqueado ? {} : { control, retornable }),
        });
      } else {
        guardado = await apiPost<Articulo>("/articulos", {
          ...comunes,
          codigo: codigo.trim(),
          categoria_id: categoriaId,
          control,
          retornable,
        });
      }
      aviso({ titulo: "Cambio guardado. Aplica desde la siguiente entrega.", tipo: "exito" });
      alCambiar(false);
      alGuardar(guardado);
    } catch (causa) {
      if (esErrorApi(causa) && causa.codigo === "CODIGO_REPETIDO") {
        const tipo = TIPO_CODIGO[String(causa.detalles?.tipo ?? "")] ?? "otra cosa";
        setErrores({
          codigo: `Ese código ya lo usa ${tipo}. Cada código identifica una sola cosa: escribe uno distinto.`,
        });
      } else if (esErrorApi(causa) && causa.codigo === "CON_MOVIMIENTOS") {
        setGeneral(causa.message);
      } else {
        const { campos, general: texto } = erroresPorCampo(causa);
        setErrores(campos);
        setGeneral(texto);
      }
    } finally {
      setGuardando(false);
    }
  }

  const opcionesCategoria = categorias
    .filter((c) => c.activo || c.id === articulo?.categoria_id)
    .map((c) => ({ valor: c.id, texto: c.nombre }));

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo={articulo ? "Editar artículo" : "Nuevo artículo"}
      descripcion={articulo ? undefined : "Elige la categoría: el artículo toma sus reglas y puedes ajustarlas."}
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-articulo" cargando={guardando}>
            Guardar
          </Boton>
        </>
      }
    >
      <form id="formulario-articulo" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Seleccion
          etiqueta="Categoría"
          opciones={opcionesCategoria}
          vacio="Elige una categoría"
          value={categoriaId}
          alCambiar={(v) => elegirCategoria(v)}
          error={errores.categoria_id}
        />
        {articulo && categoria && categoriaId !== articulo.categoria_id ? (
          <div className="flex flex-col gap-2 rounded-2xl border p-3">
            <p>¿Quieres usar las reglas de “{categoria.nombre}” para este artículo?</p>
            <Boton variante="secundario" type="button" onClick={() => tomarPlantilla(categoria)} disabled={bloqueado}>
              Usar las reglas de la nueva categoría
            </Boton>
          </div>
        ) : null}
        <Campo
          etiqueta="Código"
          ayuda={articulo ? "El código no se puede cambiar." : "El que lleva la etiqueta del artículo."}
          value={codigo}
          maxLength={64}
          disabled={articulo !== null}
          onChange={(e) => setCodigo(e.target.value)}
          error={errores.codigo}
        />
        <Campo etiqueta="Nombre" value={nombre} maxLength={150} onChange={(e) => setNombre(e.target.value)} error={errores.nombre} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Marca (opcional)" value={marca} maxLength={80} onChange={(e) => setMarca(e.target.value)} error={errores.marca} />
          <Campo etiqueta="Modelo (opcional)" value={modelo} maxLength={80} onChange={(e) => setModelo(e.target.value)} error={errores.modelo} />
          <Campo etiqueta="Talla (opcional)" value={talla} maxLength={20} onChange={(e) => setTalla(e.target.value)} error={errores.talla} />
          <Campo etiqueta="Unidad" value={unidad} maxLength={20} onChange={(e) => setUnidad(e.target.value)} error={errores.unidad} />
        </div>
        {puedeCostos ? (
          <Campo
            etiqueta="Costo por unidad (opcional)"
            type="number"
            inputMode="decimal"
            min={0}
            step="0.01"
            value={costo}
            onChange={(e) => setCosto(e.target.value)}
            error={errores.costo_unitario}
            ayuda="Solo lo ven quienes tienen permiso. Nunca aparece en un vale."
          />
        ) : null}

        <Seleccion
          etiqueta="Cómo se controla"
          opciones={OPCIONES_CONTROL}
          value={control}
          disabled={bloqueado}
          alCambiar={(v) => setControl(v as Control)}
          error={errores.control}
        />
        <Seleccion
          etiqueta="Qué pasa con la entrega"
          opciones={OPCIONES_RETORNO}
          value={retornable ? "si" : "no"}
          disabled={bloqueado}
          alCambiar={(v) => setRetornable(v === "si")}
          error={errores.retornable}
        />
        {bloqueado ? (
          <NotaBloqueo>
            Este artículo ya tiene movimientos, así que su control y su entrega no se pueden cambiar. Si hace falta, crea un artículo nuevo e inactiva este.
          </NotaBloqueo>
        ) : null}

        <h3 className="mt-2 text-base font-semibold text-marino">Reglas de entrega</h3>
        {articulo?.dias_aviso_inspeccion_resuelto ? <p className="text-sm text-muted-foreground">Aviso actual: {articulo.dias_aviso_inspeccion_resuelto} días ({articulo.origen_aviso_inspeccion === "ARTICULO" ? "de este artículo" : articulo.origen_aviso_inspeccion === "CATEGORIA" ? "de la categoría" : "general"}). Deja el campo vacío para heredar.</p> : null}
        <FormularioReglas valor={reglas} alCambiar={setReglas} control={control} errores={errores} />
      </form>
    </Hoja>
  );
}
