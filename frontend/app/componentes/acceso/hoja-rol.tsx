import { useEffect, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { Label } from "~/components/ui/label";
import { Textarea } from "~/components/ui/textarea";
import { erroresDeAcceso } from "./errores";
import { textoPermisos, type RolAcceso } from "./tipos";

export type ModoHojaRol =
  | { tipo: "nuevo" }
  | { tipo: "duplicar"; rol: RolAcceso }
  | { tipo: "editar"; rol: RolAcceso };

interface Propiedades {
  /** `null` mantiene la hoja cerrada. */
  modo: ModoHojaRol | null;
  alCerrar: () => void;
  /** Recibe el rol que responde el servidor. */
  alGuardar: (rol: RolAcceso, modo: ModoHojaRol) => void;
}

/** Un rol nuevo, la copia de otro o el cambio de nombre y descripción. Los permisos se eligen en la matriz. */
export function HojaRol({ modo, alCerrar, alGuardar }: Propiedades) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!modo) return;
    if (modo.tipo === "nuevo") {
      setNombre("");
      setDescripcion("");
    } else if (modo.tipo === "duplicar") {
      setNombre(`Copia de ${modo.rol.nombre}`.slice(0, 80));
      setDescripcion(modo.rol.descripcion ?? "");
    } else {
      setNombre(modo.rol.nombre);
      setDescripcion(modo.rol.descripcion ?? "");
    }
    setError(null);
    setGeneral(null);
    setGuardando(false);
  }, [modo]);

  const renombreBloqueado = modo?.tipo === "editar" && modo.rol.inicial;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!modo) return;
    const limpio = nombre.trim();
    if (limpio === "") {
      setError("Escribe el nombre del rol.");
      return;
    }
    setGuardando(true);
    setError(null);
    setGeneral(null);
    try {
      let guardado: RolAcceso;
      if (modo.tipo === "editar") {
        const cambios: Record<string, unknown> = {};
        if (limpio !== modo.rol.nombre) cambios.nombre = limpio;
        if (descripcion.trim() !== (modo.rol.descripcion ?? "")) cambios.descripcion = descripcion.trim() || null;
        if (Object.keys(cambios).length === 0) {
          alCerrar();
          return;
        }
        guardado = await apiPatch<RolAcceso>(`/roles/${modo.rol.id}`, cambios);
      } else {
        guardado = await apiPost<RolAcceso>("/roles", {
          nombre: limpio,
          descripcion: descripcion.trim() || null,
          permisos: modo.tipo === "duplicar" ? modo.rol.permisos : [],
        });
      }
      aviso({
        titulo: modo.tipo === "editar" ? "El rol quedó actualizado" : `Se creó el rol ${guardado.nombre}`,
        tipo: "exito",
      });
      alGuardar(guardado, modo);
    } catch (causa) {
      const { campos, general: texto } = erroresDeAcceso(causa);
      if (campos.nombre) setError(campos.nombre);
      else setGeneral(texto);
      // Un nombre repetido llega como 409 sin campo.
      if (!campos.nombre && texto && /nombre/i.test(texto)) {
        setError(texto);
        setGeneral(null);
      }
      setGuardando(false);
    }
  }

  const titulo = modo?.tipo === "editar" ? "Editar rol" : modo?.tipo === "duplicar" ? "Duplicar rol" : "Nuevo rol";
  const textoBoton = modo?.tipo === "editar" ? "Guardar" : modo?.tipo === "duplicar" ? "Crear copia" : "Crear rol";

  return (
    <Hoja
      abierta={modo !== null}
      alCambiar={(a) => !a && !guardando && alCerrar()}
      titulo={titulo}
      descripcion={
        modo?.tipo === "duplicar"
          ? `Se copian los ${textoPermisos(modo.rol.permisos.length)} de ${modo.rol.nombre}. Después los puedes ajustar.`
          : modo?.tipo === "nuevo"
            ? "Nace sin permisos: quien lo tenga no verá ningún módulo hasta que se los actives."
            : undefined
      }
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-rol" cargando={guardando}>
            {textoBoton}
          </Boton>
        </>
      }
    >
      <form id="formulario-rol" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Campo
          etiqueta="Nombre del rol"
          value={nombre}
          maxLength={80}
          autoComplete="off"
          placeholder="Por ejemplo: Jefe de turno"
          disabled={renombreBloqueado}
          ayuda={renombreBloqueado ? "Los cinco roles iniciales conservan su nombre." : undefined}
          onChange={(e) => {
            setNombre(e.target.value);
            setError(null);
          }}
          error={error}
        />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="rol-descripcion" className="text-sm font-medium text-foreground">
            Para qué sirve (opcional)
          </Label>
          <Textarea
            id="rol-descripcion"
            value={descripcion}
            maxLength={500}
            rows={3}
            className="text-base md:text-base"
            onChange={(e) => setDescripcion(e.target.value)}
          />
        </div>
      </form>
    </Hoja>
  );
}
