import { useEffect, useMemo, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { erroresDeAcceso } from "~/componentes/acceso/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";
import { AYUDA_TIPO, TEXTO_TIPO, conDescendientes, type FichaAlmacen, type TipoAlmacen } from "./tipos";

export type ModoHojaAlmacen = { tipo: "nuevo" } | { tipo: "editar"; almacen: FichaAlmacen };

interface Propiedades {
  /** `null` mantiene la hoja cerrada. */
  modo: ModoHojaAlmacen | null;
  /** Todos los almacenes (activos y cerrados): de ahí salen los posibles «de quién depende». */
  almacenes: readonly FichaAlmacen[];
  alCerrar: () => void;
  /** Recibe la ficha que responde el servidor. */
  alGuardar: (ficha: FichaAlmacen, modo: ModoHojaAlmacen) => void;
}

type Errores = Partial<Record<"clave" | "nombre" | "tipo" | "padre", string>>;

/** Códigos del servidor que se escriben junto al campo que corrigen. */
const CAMPO_DE_CODIGO: Record<string, keyof Errores> = {
  CLAVE_REPETIDA: "clave",
  CLAVE_CON_FOLIOS: "clave",
  NOMBRE_REPETIDO: "nombre",
  YA_HAY_CENTRAL: "tipo",
  PADRE_INVALIDO: "padre",
};
const CAMPO_DE_API: Record<string, keyof Errores> = { clave: "clave", nombre: "nombre", tipo: "tipo", padre_id: "padre" };

/** Alta de un almacén o cambio de su nombre y de cuál depende (la clave, solo mientras no tenga folios). */
export function HojaAlmacen({ modo, almacenes, alCerrar, alGuardar }: Propiedades) {
  const [clave, setClave] = useState("");
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<TipoAlmacen | "">("");
  const [padreId, setPadreId] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!modo) return;
    if (modo.tipo === "nuevo") {
      setClave("");
      setNombre("");
      setTipo("");
      setPadreId("");
    } else {
      setClave(modo.almacen.clave);
      setNombre(modo.almacen.nombre);
      setTipo(modo.almacen.tipo);
      setPadreId(modo.almacen.padre_id ?? "");
    }
    setErrores({});
    setGeneral(null);
    setGuardando(false);
  }, [modo]);

  const editando = modo?.tipo === "editar" ? modo.almacen : null;
  const esCentral = tipo === "CENTRAL";
  // Con folios, la clave ya es parte de los vales emitidos y no se puede cambiar (AL-05).
  const claveBloqueada = editando?.resumen?.tiene_folios === true;

  /** Solo los almacenes activos; al editar, tampoco él mismo ni los que dependen de él (sin ciclos). */
  const posiblesPadres = useMemo(() => {
    const fuera = editando ? conDescendientes(editando.id, almacenes) : new Set<string>();
    return almacenes.filter((a) => a.estado === "ACTIVO" && !fuera.has(a.id));
  }, [almacenes, editando]);

  function quitarError(campo: keyof Errores) {
    setErrores((e) => {
      if (!(campo in e)) return e;
      const { [campo]: _quitado, ...resto } = e;
      return resto;
    });
    setGeneral(null);
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!modo || guardando) return;
    const limpios: Errores = {};
    const claveLimpia = clave.trim().toUpperCase();
    const nombreLimpio = nombre.trim();
    if (!/^[A-Z0-9]{2,10}$/.test(claveLimpia)) limpios.clave = "La clave lleva de 2 a 10 letras o números, sin acentos ni espacios.";
    if (!nombreLimpio) limpios.nombre = "Escribe el nombre del almacén.";
    if (modo.tipo === "nuevo") {
      if (!tipo) limpios.tipo = "Elige qué tipo de almacén es.";
      if (tipo && tipo !== "CENTRAL" && !padreId) limpios.padre = "Elige de qué almacén depende.";
    } else if (modo.almacen.tipo !== "CENTRAL" && !padreId) {
      limpios.padre = "Elige de qué almacén depende.";
    }
    if (Object.keys(limpios).length > 0) {
      setErrores(limpios);
      return;
    }
    setGuardando(true);
    setErrores({});
    setGeneral(null);
    try {
      let ficha: FichaAlmacen;
      if (modo.tipo === "nuevo") {
        ficha = await apiPost<FichaAlmacen>("/almacenes", {
          clave: claveLimpia,
          nombre: nombreLimpio,
          tipo,
          padre_id: tipo === "CENTRAL" ? null : padreId,
        });
      } else {
        const cambios: Record<string, unknown> = {};
        if (claveLimpia !== modo.almacen.clave) cambios.clave = claveLimpia;
        if (nombreLimpio !== modo.almacen.nombre) cambios.nombre = nombreLimpio;
        if (modo.almacen.tipo !== "CENTRAL" && padreId !== (modo.almacen.padre_id ?? "")) cambios.padre_id = padreId;
        if (Object.keys(cambios).length === 0) {
          alCerrar();
          return;
        }
        ficha = await apiPatch<FichaAlmacen>(`/almacenes/${modo.almacen.id}`, cambios);
      }
      aviso({
        titulo: modo.tipo === "nuevo" ? `Se creó el almacén ${ficha.nombre}` : "El almacén quedó actualizado",
        tipo: "exito",
      });
      alGuardar(ficha, modo);
    } catch (causa) {
      const campoDeCodigo = esErrorApi(causa) ? CAMPO_DE_CODIGO[causa.codigo] : undefined;
      if (campoDeCodigo && esErrorApi(causa)) {
        setErrores({ [campoDeCodigo]: causa.message });
      } else {
        const { campos, general: texto } = erroresDeAcceso(causa);
        const mapeados: Errores = {};
        for (const [campo, mensaje] of Object.entries(campos)) {
          const destino = CAMPO_DE_API[campo];
          if (destino) mapeados[destino] = mensaje;
        }
        if (Object.keys(mapeados).length > 0) setErrores(mapeados);
        else setGeneral(texto);
      }
      setGuardando(false);
    }
  }

  const titulo = editando ? `Editar ${editando.nombre}` : "Nuevo almacén";

  return (
    <Hoja
      abierta={modo !== null}
      alCambiar={(a) => !a && !guardando && alCerrar()}
      titulo={titulo}
      descripcion={
        editando
          ? "Cambia el nombre o de cuál depende. El tipo no se cambia."
          : "Al guardarlo ya puede recibir inventario y tener personal asignado."
      }
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-almacen" cargando={guardando}>
            {editando ? "Guardar cambios" : "Crear almacén"}
          </Boton>
        </>
      }
    >
      <form id="formulario-almacen" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Campo
          etiqueta="Clave"
          value={clave}
          maxLength={10}
          autoComplete="off"
          autoCapitalize="characters"
          placeholder="Por ejemplo: MID"
          disabled={claveBloqueada}
          ayuda={
            claveBloqueada
              ? "Ya tiene vales con esta clave, por eso no se puede cambiar."
              : "De 2 a 10 letras o números, sin acentos. Va al inicio de los folios (por ejemplo MID-ENT-000001)."
          }
          onChange={(e) => {
            setClave(e.target.value.toUpperCase());
            quitarError("clave");
          }}
          error={errores.clave}
        />
        <Campo
          etiqueta="Nombre"
          value={nombre}
          maxLength={100}
          autoComplete="off"
          placeholder="Por ejemplo: Midrex"
          onChange={(e) => {
            setNombre(e.target.value);
            quitarError("nombre");
          }}
          error={errores.nombre}
        />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="almacen-tipo" className="text-sm font-medium text-foreground">
            Tipo de almacén
          </Label>
          <ListaDesplegable
            id="almacen-tipo"
            valor={tipo}
            marcador="Elige el tipo"
            deshabilitado={editando !== null}
            invalido={Boolean(errores.tipo)}
            descritoPor="almacen-tipo-ayuda"
            alCambiar={(v) => {
              setTipo(v as TipoAlmacen | "");
              if (v === "CENTRAL") setPadreId("");
              quitarError("tipo");
              quitarError("padre");
            }}
            opciones={(["CENTRAL", "SUBALMACEN", "PROYECTO"] as const).map((t) => ({ valor: t, texto: TEXTO_TIPO[t] }))}
          />
          <p id="almacen-tipo-ayuda" className="text-sm text-muted-foreground">
            {tipo ? AYUDA_TIPO[tipo] : "Cada almacén es central, subalmacén o proyecto."}
          </p>
          {errores.tipo ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {errores.tipo}
            </p>
          ) : null}
        </div>
        {esCentral ? (
          <p className="rounded-xl border bg-muted p-3 text-sm">El almacén central no depende de otro.</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="almacen-padre" className="text-sm font-medium text-foreground">
              De qué almacén depende
            </Label>
            <ListaDesplegable
              id="almacen-padre"
              valor={padreId}
              marcador={tipo || editando ? "Elige el almacén" : "Primero elige el tipo"}
              deshabilitado={!tipo && !editando}
              invalido={Boolean(errores.padre)}
              alCambiar={(v) => {
                setPadreId(v);
                quitarError("padre");
              }}
              opciones={posiblesPadres.map((a) => ({ valor: a.id, texto: `${a.nombre} (${a.clave})` }))}
            />
            <p className="text-sm text-muted-foreground">Solo se ofrecen almacenes activos. Es de donde recibe su material.</p>
            {errores.padre ? (
              <p role="alert" className="text-sm font-medium text-destructive">
                {errores.padre}
              </p>
            ) : null}
          </div>
        )}
      </form>
    </Hoja>
  );
}
