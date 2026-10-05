import { ArrowLeftIcon, PencilIcon, PowerIcon, Trash2Icon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiDelete, apiGet, apiPatch, apiPost } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { Switch } from "~/components/ui/switch";
import { NotaBloqueo } from "./campos";
import { HojaArticulo } from "./hoja-articulo";
import {
  nombreConMarca,
  TEXTO_CONTROL,
  textoCosto,
  textoLimite,
  textoRetorno,
  type ArticuloFicha,
  type Categoria,
} from "./tipos";
import { useConsulta } from "./usar-consulta";

interface Propiedades {
  articuloId: string;
  categorias: Categoria[];
  puedeEditar: boolean;
  puedeCostos: boolean;
  alVolver: () => void;
  /** Avisa a la lista que algo cambió para que se actualice al regresar. */
  alCambiar: () => void;
}

function Seccion({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold text-marino">{titulo}</h2>
        {descripcion ? <p className="text-muted-foreground">{descripcion}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div className="flex flex-col">
      <dt className="text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className="text-base font-medium">{children}</dd>
    </div>
  );
}

interface PropiedadesRegla {
  titulo: string;
  activo: boolean;
  /** Lo que dice la regla cuando está activa, por ejemplo "Máximo 2 cada 30 días". */
  detalle?: string | null;
  motivo?: string | null;
  puedeEditar: boolean;
  ocupado: boolean;
  alCambiar: (activo: boolean) => void;
}

function ReglaEnDetalle({ titulo, activo, detalle, motivo, puedeEditar, ocupado, alCambiar }: PropiedadesRegla) {
  return (
    <li className="rounded-xl border p-4">
      <label className="flex min-h-12 cursor-pointer items-center justify-between gap-4">
        <span className="flex min-w-0 flex-col">
          <span className="text-base font-semibold">{titulo}</span>
          <span className="text-sm text-muted-foreground">{activo ? (detalle ?? "Activa") : "No aplica a este artículo"}</span>
          {activo && motivo ? <span className="text-sm">Motivo: {motivo}</span> : null}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <span className="w-6 text-right text-sm font-semibold" aria-hidden="true">
            {activo ? "Sí" : "No"}
          </span>
          <Switch
            checked={activo}
            onCheckedChange={alCambiar}
            disabled={!puedeEditar || ocupado}
            aria-label={titulo}
          />
        </span>
      </label>
    </li>
  );
}

/** Ficha de un artículo del catálogo: datos, reglas de entrega, existencias, quién lo tiene y estado. */
export function DetalleArticulo({ articuloId, categorias, puedeEditar, puedeCostos, alVolver, alCambiar }: Propiedades) {
  const consulta = useConsulta((signal) => apiGet<ArticuloFicha>(`/articulos/${articuloId}`, undefined, signal), articuloId);
  const [editando, setEditando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [inactivando, setInactivando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState<string | null>(null);
  const [confirmaInactivar, setConfirmaInactivar] = useState(false);
  const [confirmaInspeccion, setConfirmaInspeccion] = useState(false);
  const [confirmaEliminar, setConfirmaEliminar] = useState(false);

  const articulo = consulta.datos;

  if (consulta.error && !articulo) {
    return (
      <div className="flex flex-col gap-4">
        <Boton variante="texto" onClick={alVolver} className="self-start">
          <ArrowLeftIcon aria-hidden="true" />
          Volver a la lista
        </Boton>
        <EstadoError error={consulta.error} alReintentar={consulta.recargar} />
      </div>
    );
  }
  if (!articulo) return <Esqueleto tipo="tarjeta" cantidad={4} />;

  async function ejecutar(accion: () => Promise<unknown>, exito: string) {
    setOcupado(true);
    try {
      await accion();
      aviso({ titulo: exito, tipo: "exito" });
      alCambiar();
      consulta.recargar();
      return true;
    } catch (causa) {
      aviso({ titulo: mensajeDeError(causa), tipo: "error" });
      return false;
    } finally {
      setOcupado(false);
    }
  }

  const cambiarRegla = (cuerpo: Record<string, unknown>) =>
    ejecutar(() => apiPatch(`/articulos/${articuloId}`, cuerpo), "Cambio guardado. Aplica desde la siguiente entrega.");

  async function inactivar() {
    const hecho = await ejecutar(
      () => apiPost(`/articulos/${articuloId}/inactivacion`, { motivo: motivo.trim() }),
      "El artículo quedó inactivo.",
    );
    setConfirmaInactivar(false);
    if (hecho) {
      setInactivando(false);
      setMotivo("");
    }
  }

  const categoria = categorias.find((c) => c.id === articulo.categoria_id);
  const limite = textoLimite(articulo);
  const total = articulo.existencias.reduce((suma, e) => suma + e.cantidad, 0);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <Boton variante="texto" onClick={alVolver} className="-ml-4 self-start">
          <ArrowLeftIcon aria-hidden="true" />
          Volver a la lista
        </Boton>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h2 className="text-xl font-semibold text-marino">{articulo.nombre}</h2>
            <p className="text-muted-foreground">
              Código {articulo.codigo} · {articulo.categoria_nombre}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Insignia estado="neutra">{articulo.activo ? "Activo" : "Inactivo"}</Insignia>
            {puedeEditar ? (
              <Boton variante="contorno" onClick={() => setEditando(true)}>
                <PencilIcon aria-hidden="true" />
                Editar
              </Boton>
            ) : null}
          </div>
        </div>
        {!articulo.activo ? (
          <p role="status" className="rounded-xl border bg-muted p-3">
            <strong>Inactivo.</strong> Motivo: {articulo.motivo_inactivacion ?? "sin motivo registrado"}. Ya no se entrega ni se le registran entradas; su historial se conserva.
          </p>
        ) : null}
      </div>

      <Seccion titulo="Datos generales">
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Dato etiqueta="Nombre">{nombreConMarca(articulo)}</Dato>
          <Dato etiqueta="Categoría">{categoria ? categoria.nombre : articulo.categoria_nombre}</Dato>
          <Dato etiqueta="Cómo se controla">{TEXTO_CONTROL[articulo.control]}</Dato>
          <Dato etiqueta="Entrega">{textoRetorno(articulo.retornable)}</Dato>
          <Dato etiqueta="Unidad">{articulo.unidad}</Dato>
          <Dato etiqueta="Talla">{articulo.talla ?? "No aplica"}</Dato>
          {puedeCostos ? <Dato etiqueta="Costo por unidad">{textoCosto(articulo.costo_unitario)}</Dato> : null}
        </dl>
        {articulo.tiene_movimientos ? (
          <NotaBloqueo>
            Este artículo ya tiene movimientos: su control y su entrega quedan fijos. Para cambiarlos, crea un artículo nuevo e inactiva este.
          </NotaBloqueo>
        ) : null}
      </Seccion>

      <Seccion
        titulo="Reglas de entrega"
        descripcion="Cada cambio aplica desde la siguiente entrega. No cambia los vales ya emitidos."
      >
        <ul className="flex flex-col gap-3">
          <ReglaEnDetalle
            titulo="Inspección vigente"
            activo={articulo.requiere_inspeccion}
            detalle={articulo.vigencia_inspeccion_dias ? `La pieza debe estar inspeccionada; vale ${articulo.vigencia_inspeccion_dias} días.` : "La pieza debe estar inspeccionada."}
            puedeEditar={puedeEditar && articulo.control === "PIEZA"}
            ocupado={ocupado}
            alCambiar={(activo) => (activo ? setConfirmaInspeccion(true) : void cambiarRegla({ requiere_inspeccion: false }))}
          />
          <ReglaEnDetalle
            titulo="Autorización del supervisor"
            activo={articulo.requiere_autorizacion}
            detalle="Cada entrega espera el visto bueno del supervisor."
            motivo={articulo.motivo_uso_especial}
            puedeEditar={puedeEditar}
            ocupado={ocupado}
            alCambiar={(activo) => void cambiarRegla({ requiere_autorizacion: activo })}
          />
          <ReglaEnDetalle
            titulo="Límite por trabajador"
            activo={articulo.limite_cantidad !== null}
            detalle={limite}
            puedeEditar={puedeEditar}
            ocupado={ocupado}
            alCambiar={(activo) => {
              if (activo) setEditando(true);
              else void cambiarRegla({ limite_cantidad: null, limite_periodo_dias: null });
            }}
          />
          <ReglaEnDetalle
            titulo="Aviso de cantidad inusual"
            activo={articulo.cantidad_aviso !== null}
            detalle={articulo.cantidad_aviso ? `Pide confirmar desde ${articulo.cantidad_aviso} piezas en un renglón.` : null}
            puedeEditar={puedeEditar}
            ocupado={ocupado}
            alCambiar={(activo) => {
              if (activo) setEditando(true);
              else void cambiarRegla({ cantidad_aviso: null });
            }}
          />
        </ul>
        {puedeEditar ? (
          <Boton variante="contorno" onClick={() => setEditando(true)} className="self-start">
            <PencilIcon aria-hidden="true" />
            Editar cantidades y motivo
          </Boton>
        ) : null}
        {articulo.control === "CANTIDAD" ? (
          <p className="text-sm text-muted-foreground">La inspección solo aplica a artículos que se controlan por pieza.</p>
        ) : null}
      </Seccion>

      <Seccion titulo="Existencias" descripcion="“Disponible” no cuenta las piezas no aptas ni las que están en mantenimiento.">
        {articulo.existencias.length === 0 ? (
          <EstadoVacio titulo="Todavía no hay existencias" descripcion="Aparecen cuando se registra una entrada de este artículo." />
        ) : (
          <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Almacén</TableHead>
                  <TableHead scope="col" className="text-right">Existencia</TableHead>
                  <TableHead scope="col" className="text-right">Disponible</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {articulo.existencias.map((e) => (
                  <TableRow key={e.almacen_id}>
                    <TableHead scope="row">{e.nombre}</TableHead>
                    <TableCell className="text-right">{e.cantidad}</TableCell>
                    <TableCell className="text-right">{e.disponible}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow className="border-t bg-muted/50 font-semibold">
                  <TableHead scope="row">Total</TableHead>
                  <TableCell className="text-right">{total}</TableCell>
                  <TableCell className="text-right">{articulo.existencias.reduce((s, e) => s + e.disponible, 0)}</TableCell>
                </TableRow>
              </TableFooter>
            </Table>
        )}
      </Seccion>

      <Seccion titulo="Quién lo tiene">
        {articulo.en_posesion.length === 0 ? (
          <p className="text-muted-foreground">Nadie lo tiene en resguardo por ahora.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {articulo.en_posesion.map((p) => (
              <li key={p.trabajador_id} className="flex items-center justify-between gap-3 rounded-xl border p-3">
                <span className="min-w-0">
                  <span className="block font-semibold">{p.nombre}</span>
                  <span className="block text-sm text-muted-foreground">Empleado {p.numero_empleado}</span>
                </span>
                <span className="shrink-0 font-semibold">{p.cantidad} {p.cantidad === 1 ? "pieza" : "piezas"}</span>
              </li>
            ))}
          </ul>
        )}
      </Seccion>

      {puedeEditar ? (
        <Seccion titulo="Estado">
          {articulo.activo ? (
            <>
              <p>Al inactivarlo ya no se entrega ni se le registran entradas. Sus existencias se pueden trasladar y lo que está con trabajadores se puede devolver.</p>
              <Boton variante="contorno" onClick={() => setInactivando(true)} className="self-start">
                <PowerIcon aria-hidden="true" />
                Inactivar
              </Boton>
            </>
          ) : (
            <>
              <p>Al reactivarlo vuelve a operar con las reglas que tenía.</p>
              <Boton
                variante="normal"
                cargando={ocupado}
                className="self-start"
                onClick={() => void ejecutar(() => apiDelete(`/articulos/${articuloId}/inactivacion`), "El artículo se reactivó.")}
              >
                <PowerIcon aria-hidden="true" />
                Reactivar
              </Boton>
            </>
          )}
          {!articulo.tiene_movimientos ? (
            <div className="flex flex-col gap-2 border-t pt-3">
              <p className="text-muted-foreground">Como nunca tuvo movimientos, también se puede eliminar.</p>
              <Boton variante="peligro" onClick={() => setConfirmaEliminar(true)} className="self-start">
                <Trash2Icon aria-hidden="true" />
                Eliminar artículo
              </Boton>
            </div>
          ) : null}
        </Seccion>
      ) : null}

      <HojaArticulo
        abierta={editando}
        alCambiar={setEditando}
        articulo={articulo}
        categorias={categorias}
        puedeCostos={puedeCostos}
        alGuardar={() => {
          alCambiar();
          consulta.recargar();
        }}
      />

      <Hoja
        abierta={inactivando}
        alCambiar={(abierta) => {
          setInactivando(abierta);
          if (!abierta) setErrorMotivo(null);
        }}
        titulo="Inactivar artículo"
        descripcion="Escribe por qué se inactiva. Queda en el historial."
        pie={
          <Boton
            variante="principal"
            onClick={() => {
              if (motivo.trim() === "") {
                setErrorMotivo("Escribe el motivo.");
                return;
              }
              setErrorMotivo(null);
              setConfirmaInactivar(true);
            }}
          >
            Continuar
          </Boton>
        }
      >
        <Campo etiqueta="Motivo" value={motivo} maxLength={255} onChange={(e) => setMotivo(e.target.value)} error={errorMotivo} />
      </Hoja>

      <Confirmacion
        abierta={confirmaInactivar}
        alCambiar={setConfirmaInactivar}
        mensaje={`¿Inactivar “${articulo.nombre}”?`}
        detalle="Ya no se podrá entregar ni recibir. Su historial se conserva y se puede reactivar."
        etiquetaConfirmar="Sí, inactivar"
        etiquetaCancelar="Cancelar"
        cargando={ocupado}
        alConfirmar={() => void inactivar()}
      />

      <Confirmacion
        abierta={confirmaInspeccion}
        alCambiar={setConfirmaInspeccion}
        mensaje="¿Pedir inspección vigente?"
        detalle="Las piezas de este artículo quedan sin inspección vigente y no se entregan hasta que se inspeccionen."
        etiquetaConfirmar="Sí, pedirla"
        etiquetaCancelar="Cancelar"
        cargando={ocupado}
        alConfirmar={async () => {
          await cambiarRegla({ requiere_inspeccion: true });
          setConfirmaInspeccion(false);
        }}
      />

      <Confirmacion
        abierta={confirmaEliminar}
        alCambiar={setConfirmaEliminar}
        mensaje={`¿Eliminar “${articulo.nombre}”?`}
        detalle="Se borra del catálogo y no se puede deshacer."
        etiquetaConfirmar="Sí, eliminar"
        etiquetaCancelar="Cancelar"
        peligro
        cargando={ocupado}
        alConfirmar={async () => {
          const hecho = await ejecutar(() => apiDelete(`/articulos/${articuloId}`), "El artículo se eliminó.");
          setConfirmaEliminar(false);
          if (hecho) alVolver();
        }}
      />
    </div>
  );
}
