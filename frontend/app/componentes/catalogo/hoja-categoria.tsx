import { useEffect, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { FilaInterruptor, Seleccion } from "./campos";
import { erroresPorCampo } from "./errores-campo";
import {
  estadoAReglas,
  FormularioReglas,
  REGLAS_VACIAS,
  reglasAEstado,
  validarReglas,
  type EstadoReglas,
} from "./formulario-reglas";
import type { Categoria, Control, TipoCategoria } from "./tipos";

interface Propiedades {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Categoría a editar; sin ella, se crea una nueva. */
  categoria: Categoria | null;
  alGuardar: () => void;
}

const OPCIONES_TIPO = [
  { valor: "EPP", texto: "EPP (equipo de protección)" },
  { valor: "HERRAMIENTA", texto: "Herramienta" },
];
const OPCIONES_CONTROL = [
  { valor: "CANTIDAD", texto: "Por cantidad (solo cuántas hay)" },
  { valor: "PIEZA", texto: "Por pieza (cada pieza tiene su código)" },
];
const OPCIONES_RETORNO = [
  { valor: "si", texto: "Retornable (se devuelve)" },
  { valor: "no", texto: "Consumible (no se devuelve)" },
];

/** Alta y edición de una categoría con su plantilla de reglas. */
export function HojaCategoria({ abierta, alCambiar, categoria, alGuardar }: Propiedades) {
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<TipoCategoria>("EPP");
  const [control, setControl] = useState<Control>("CANTIDAD");
  const [retornable, setRetornable] = useState(true);
  const [altoValor, setAltoValor] = useState(false);
  const [reglas, setReglas] = useState<EstadoReglas>(REGLAS_VACIAS);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  // Cada vez que se abre, parte de la categoría elegida o de una vacía.
  useEffect(() => {
    if (!abierta) return;
    setNombre(categoria?.nombre ?? "");
    setTipo(categoria?.tipo ?? "EPP");
    setControl(categoria?.control ?? "CANTIDAD");
    setRetornable(categoria?.retornable ?? true);
    setAltoValor(categoria?.alto_valor ?? false);
    setReglas(categoria ? reglasAEstado(categoria) : REGLAS_VACIAS);
    setErrores({});
    setGeneral(null);
  }, [abierta, categoria]);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const locales = validarReglas(reglas, control);
    if (nombre.trim() === "") locales.nombre = "Escribe el nombre de la categoría.";
    if (Object.keys(locales).length > 0) {
      setErrores(locales);
      return;
    }
    setGuardando(true);
    setErrores({});
    setGeneral(null);
    const cuerpo = { nombre: nombre.trim(), tipo, control, retornable, alto_valor: altoValor, ...estadoAReglas(reglas) };
    try {
      if (categoria) await apiPatch(`/categorias/${categoria.id}`, cuerpo);
      else await apiPost("/categorias", cuerpo);
      aviso({ titulo: "Cambio guardado. Aplica desde la siguiente entrega.", tipo: "exito" });
      alCambiar(false);
      alGuardar();
    } catch (causa) {
      const { campos, general: texto } = erroresPorCampo(causa);
      setErrores(campos);
      setGeneral(texto);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo={categoria ? "Editar categoría" : "Nueva categoría"}
      descripcion="Las reglas se copian a los artículos nuevos de esta categoría. Los artículos que ya existen no cambian."
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-categoria" cargando={guardando}>
            Guardar
          </Boton>
        </>
      }
    >
      <form id="formulario-categoria" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Campo
          etiqueta="Nombre"
          value={nombre}
          maxLength={100}
          onChange={(e) => setNombre(e.target.value)}
          error={errores.nombre}
        />
        <Seleccion
          etiqueta="Tipo"
          opciones={OPCIONES_TIPO}
          value={tipo}
          alCambiar={(v) => setTipo(v as TipoCategoria)}
          error={errores.tipo}
        />
        <Seleccion
          etiqueta="Cómo se controla"
          opciones={OPCIONES_CONTROL}
          value={control}
          alCambiar={(v) => setControl(v as Control)}
          error={errores.control}
        />
        <Seleccion
          etiqueta="Qué pasa con la entrega"
          opciones={OPCIONES_RETORNO}
          value={retornable ? "si" : "no"}
          alCambiar={(v) => setRetornable(v === "si")}
          error={errores.retornable}
        />
        <h3 className="mt-2 text-base font-semibold text-marino">Reglas de entrega</h3>
        <FilaInterruptor titulo="Categoría de alto valor" ayuda="Sus artículos se destacan para dar seguimiento a su resguardo." activo={altoValor} alCambiar={setAltoValor} />
        {categoria?.articulos_con_aviso_propio ? <p className="text-sm text-muted-foreground">{categoria.articulos_con_aviso_propio} artículos tienen su propio aviso y no cambian.</p> : null}
        <FormularioReglas valor={reglas} alCambiar={setReglas} control={control} errores={errores} />
      </form>
    </Hoja>
  );
}
