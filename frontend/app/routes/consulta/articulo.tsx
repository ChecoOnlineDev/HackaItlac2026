import { formatearMoneda } from "~/componentes/dominio/formato";
import { MapPinnedIcon, PackageCheckIcon, PencilIcon, UsersIcon, WarehouseIcon } from "lucide-react";
import { Link, useParams } from "react-router";

import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Dato, Seccion, VolverAConsultar } from "~/componentes/consulta/bloques";
import { textoControl } from "~/componentes/consulta/formato";
import type { FichaArticulo } from "~/componentes/consulta/tipos";
import { useCarga } from "~/componentes/consulta/use-carga";
import { TablaQuienLoTiene } from "~/componentes/seguimiento/quien-lo-tiene";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "catalogo.ver" };

function reglas(a: FichaArticulo): string[] {
  const lista: string[] = [];
  if (a.limite_cantidad) {
    lista.push(
      a.limite_periodo_dias
        ? `Máximo ${a.limite_cantidad} cada ${a.limite_periodo_dias} días por trabajador.`
        : `Máximo ${a.limite_cantidad} en resguardo por trabajador.`,
    );
  }
  if (a.cantidad_aviso) lista.push(`Avisa si piden ${a.cantidad_aviso} o más de una vez.`);
  if (a.requiere_inspeccion) {
    lista.push(
      a.vigencia_inspeccion_dias
        ? `Pide inspección vigente. Cada inspección dura ${a.vigencia_inspeccion_dias} días.`
        : "Pide inspección vigente.",
    );
  }
  if (a.requiere_autorizacion) lista.push(`Pide autorización del supervisor${a.motivo_uso_especial ? ` (${a.motivo_uso_especial})` : ""}.`);
  return lista;
}

export default function FichaArticulo() {
  const { id } = useParams();
  const { puede, puedeAlguno } = useSesion();
  const { datos: articulo, error, cargando, recargar } = useCarga<FichaArticulo>(id ? `/articulos/${id}` : null);

  if (cargando) {
    return (
      <Pantalla titulo="Ficha de artículo" ancho="formulario">
        <VolverAConsultar />

        <Esqueleto tipo="tarjeta" cantidad={2} />
        <Esqueleto tipo="lista" cantidad={3} />
      </Pantalla>
    );
  }

  if (error || !articulo) {
    return (
      <Pantalla titulo="Ficha de artículo" ancho="formulario">
        <VolverAConsultar />
        <EstadoError error={error ?? undefined} alReintentar={recargar} />
      </Pantalla>
    );
  }

  const listaReglas = reglas(articulo);
  const totalDisponible = articulo.existencias.reduce((s, e) => s + e.disponible, 0);
  const totalCantidad = articulo.existencias.reduce((s, e) => s + e.cantidad, 0);
  const costo = articulo.costo_unitario;

  return (
    <Pantalla
      titulo={articulo.nombre}
      descripcion={[`Código ${articulo.codigo}`, articulo.marca, articulo.modelo].filter(Boolean).join(" · ")}
      ancho="formulario"
    >
      <VolverAConsultar />
      {articulo.control === "PIEZA" && puede("etiquetas.imprimir") ? <Boton variante="contorno" className="self-start" nativeButton={false} render={<Link to={`/etiquetas?tipo=piezas&articulo_id=${articulo.id}`} />}>Etiquetas de sus piezas</Boton> : null}

      {articulo.alto_valor ? <Insignia estado="info">Alto valor{articulo.alto_valor_motivo ? ` · ${articulo.alto_valor_motivo}` : ""}</Insignia> : null}

      <div className="flex flex-wrap items-center gap-2">
        <Insignia estado={articulo.activo ? "info" : "neutra"}>{articulo.activo ? "Activo" : "Inactivo"}</Insignia>
        <Insignia estado="neutra">{articulo.categoria_nombre}</Insignia>
        <Insignia estado="neutra">{textoControl(articulo.control)}</Insignia>
      </div>
      {!articulo.activo && articulo.motivo_inactivacion ? (
        <p className="rounded-xl border bg-muted p-3 text-sm">No se entrega: {articulo.motivo_inactivacion}</p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {puede("entregas.crear") && articulo.activo ? (
          <Boton variante="normal" nativeButton={false} render={<Link to="/entregar" />}>
            <PackageCheckIcon aria-hidden="true" />
            Entregar
          </Boton>
        ) : null}
        {articulo.control === "PIEZA" && puedeAlguno(["reportes.existencias", "resguardo.ver"]) ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to={`/seguimiento?articulo=${articulo.id}`} />}>
            <MapPinnedIcon aria-hidden="true" />
            Ver todas sus piezas
          </Boton>
        ) : null}
        {puede("catalogo.administrar") ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to={`/catalogo/articulos?articulo=${articulo.id}`} />}>
            <PencilIcon aria-hidden="true" />
            Editar en el catálogo
          </Boton>
        ) : null}
      </div>

      <Seccion titulo={puede("almacenes.todos") ? "Dónde hay" : "Lo que hay en tu almacén"}>
        {articulo.existencias.length === 0 ? (
          <EstadoVacio icono={WarehouseIcon} titulo="No hay existencias" descripcion={puede("almacenes.todos") ? "Este artículo no está en ningún almacén." : "Este artículo no está en tu almacén."} />
        ) : (
          <>
            <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col" className="px-3 py-2 font-semibold">Almacén</TableHead>
                    <TableHead scope="col" className="px-3 py-2 text-right font-semibold">Hay</TableHead>
                    <TableHead scope="col" className="px-3 py-2 text-right font-semibold">Disponible</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y">
                  {articulo.existencias.map((e) => (
                    <TableRow key={e.almacen_id}>
                      <TableHead scope="row" className="px-3 py-3 font-semibold">{e.nombre}</TableHead>
                      <TableCell className="px-3 py-3 text-right tabular-nums">{e.cantidad}</TableCell>
                      <TableCell className="px-3 py-3 text-right font-semibold tabular-nums">{e.disponible}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                {articulo.existencias.length > 1 ? (
                  <TableFooter className="border-t-2 bg-muted/50">
                    <TableRow>
                      <TableHead scope="row" className="px-3 py-2 font-semibold">Total</TableHead>
                      <TableCell className="px-3 py-2 text-right font-semibold tabular-nums">{totalCantidad}</TableCell>
                      <TableCell className="px-3 py-2 text-right font-semibold tabular-nums">{totalDisponible}</TableCell>
                    </TableRow>
                  </TableFooter>
                ) : null}
              </Table>
            <p className="text-sm text-muted-foreground">
              {articulo.control === "PIEZA"
                ? "Disponible es lo que se puede entregar hoy: no cuenta las piezas no aptas, en mantenimiento ni en calibración."
                : "Disponible es lo que se puede entregar hoy."}
            </p>
          </>
        )}
      </Seccion>

      <Seccion titulo="Quién lo tiene">
        {articulo.en_posesion.length === 0 ? (
          <EstadoVacio icono={UsersIcon} titulo="Nadie lo tiene ahora" descripcion="Ningún trabajador lo tiene en resguardo." />
        ) : (
          <TablaQuienLoTiene
            poseedores={articulo.en_posesion}
            puedeVerTrabajador={puede("trabajadores.ver")}
            puedeVerVale={puede("vales.ver")}
            puedeVerPieza={puede("catalogo.ver")}
          />
        )}
      </Seccion>

      <Seccion titulo="Reglas de entrega">
        {listaReglas.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tiene reglas especiales.</p>
        ) : (
          <ul className="flex list-disc flex-col gap-1.5 rounded-2xl border p-4 pl-8 text-base">
            {listaReglas.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </Seccion>

      <Seccion titulo="Datos">
        <dl className="grid grid-cols-1 gap-3 rounded-2xl border bg-card p-4 shadow-xs sm:grid-cols-2">
          <Dato etiqueta="Unidad" valor={articulo.unidad} />
          <Dato etiqueta="Se devuelve" valor={articulo.retornable ? "Sí" : "No, se consume"} />
          {articulo.talla ? <Dato etiqueta="Talla" valor={articulo.talla} /> : null}
          {costo !== undefined && costo !== null ? (
            <Dato
              etiqueta="Costo por unidad"
              valor={formatearMoneda(costo)}
            />
          ) : null}
        </dl>
      </Seccion>
    </Pantalla>
  );
}
