import { useEffect, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { erroresPorCampo } from "~/componentes/catalogo/errores-campo";
import type { Puesto } from "./tipos";

interface Propiedades {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Puesto a renombrar; sin él se crea uno nuevo. */
  puesto: Puesto | null;
  /** Recibe el puesto guardado (el nuevo, para poder armarle la dotación enseguida). */
  alGuardar: (puesto: Puesto, esNuevo: boolean) => void;
}

/** Alta de un puesto o cambio de su nombre. */
export function HojaPuesto({ abierta, alCambiar, puesto, alGuardar }: Propiedades) {
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!abierta) return;
    setNombre(puesto?.nombre ?? "");
    setError(null);
    setGeneral(null);
  }, [abierta, puesto]);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const limpio = nombre.trim();
    if (limpio === "") {
      setError("Escribe el nombre del puesto.");
      return;
    }
    if (puesto && limpio === puesto.nombre) {
      alCambiar(false);
      return;
    }
    setGuardando(true);
    setError(null);
    setGeneral(null);
    try {
      const guardado = puesto
        ? await apiPatch<Puesto>(`/puestos/${puesto.id}`, { nombre: limpio })
        : await apiPost<Puesto>("/puestos", { nombre: limpio });
      aviso({ titulo: puesto ? "El puesto cambió de nombre" : "El puesto quedó creado", tipo: "exito" });
      alCambiar(false);
      alGuardar(guardado, puesto === null);
    } catch (causa) {
      if (esErrorApi(causa) && causa.status === 409) {
        setError(causa.message);
      } else {
        const { campos, general: texto } = erroresPorCampo(causa);
        setError(campos.nombre ?? null);
        setGeneral(texto ?? (campos.nombre ? null : "Revisa el nombre del puesto."));
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Hoja
      abierta={abierta}
      alCambiar={(a) => !guardando && alCambiar(a)}
      titulo={puesto ? "Cambiar el nombre del puesto" : "Nuevo puesto"}
      descripcion={
        puesto
          ? "Quienes ya tienen este puesto conservan su dotación. En su ficha puede seguir viéndose el nombre anterior."
          : "Después le armas su dotación: qué artículos y cuántos se recomiendan para quien lo ocupa."
      }
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-puesto" cargando={guardando}>
            {puesto ? "Guardar" : "Crear puesto"}
          </Boton>
        </>
      }
    >
      <form id="formulario-puesto" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Campo
          etiqueta="Nombre del puesto"
          value={nombre}
          maxLength={100}
          autoComplete="off"
          placeholder="Por ejemplo: Soldador"
          onChange={(e) => {
            setNombre(e.target.value);
            setError(null);
          }}
          error={error}
        />
      </form>
    </Hoja>
  );
}
