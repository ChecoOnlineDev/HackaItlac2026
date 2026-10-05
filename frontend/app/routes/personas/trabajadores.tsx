import { UserPlusIcon, UsersIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { formatearPeriodo } from "~/componentes/personas/formato";
import { InsigniaSituacion, InsigniaVigencia } from "~/componentes/personas/insignias";
import type { ElementoLista } from "~/componentes/personas/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { useRetraso } from "~/componentes/catalogo/usar-consulta";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "trabajadores.ver" };

const TAMANO = 20;

export default function Trabajadores() {
  const { puede } = useSesion();
  const puedeAdministrar = puede("trabajadores.administrar");

  const [texto, setTexto] = useState("");
  const busqueda = useRetraso(texto.trim());
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState<Pagina<ElementoLista> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cargando, setCargando] = useState(true);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const control = new AbortController();
    setCargando(true);
    setError(null);
    apiGet<Pagina<ElementoLista>>("/trabajadores", { q: busqueda, pagina, tamano: TAMANO }, control.signal)
      .then((respuesta) => {
        setDatos(respuesta);
        setCargando(false);
      })
      .catch((causa: unknown) => {
        if (causa instanceof DOMException && causa.name === "AbortError") return;
        setError(causa);
        setCargando(false);
      });
    return () => control.abort();
  }, [busqueda, pagina, intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  const totalPaginas = datos ? Math.max(1, Math.ceil(datos.total / TAMANO)) : 1;

  const botonAlta = puedeAdministrar ? (
    <Boton variante="normal" nativeButton={false} render={<Link to="/trabajadores/nuevo" />}>
      <UserPlusIcon aria-hidden="true" />
      Alta
    </Boton>
  ) : null;

  return (
    <Pantalla titulo="Trabajadores" descripcion="Busca por nombre o número y revisa su situación." acciones={botonAlta}>
      <div className="flex">
        <CampoBusqueda
          etiqueta="Buscar trabajador por nombre o número"
          placeholder="Buscar por nombre o número"
          value={texto}
          alCambiar={(v) => {
            setTexto(v);
            setPagina(1);
          }}
          claseContenedor="sm:max-w-md"
        />
      </div>

      {error && !datos ? (
        <EstadoError error={error} alReintentar={reintentar} />
      ) : cargando && !datos ? (
        <Esqueleto tipo="lista" cantidad={5} />
      ) : datos && datos.elementos.length === 0 ? (
        busqueda ? (
          <EstadoVacio
            icono={UsersIcon}
            titulo="No encontramos a nadie con esa búsqueda"
            descripcion="Revisa el nombre o el número, o borra la búsqueda."
            accion={
              <Boton variante="secundario" onClick={() => setTexto("")}>
                Borrar búsqueda
              </Boton>
            }
          />
        ) : (
          <EstadoVacio
            icono={UsersIcon}
            titulo="Todavía no hay trabajadores registrados"
            descripcion={puedeAdministrar ? "Da de alta a la primera persona." : "Cuando RH registre a alguien, aparecerá aquí."}
            accion={
              puedeAdministrar ? (
                <Boton variante="normal" nativeButton={false} render={<Link to="/trabajadores/nuevo" />}>
                  <UserPlusIcon aria-hidden="true" />
                  Alta de trabajador
                </Boton>
              ) : undefined
            }
          />
        )
      ) : datos ? (
        <div className="flex flex-col gap-4" aria-busy={cargando}>
          {error ? <EstadoError error={error} alReintentar={reintentar} /> : null}

          {/* Computadora: tabla */}
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Nombre</TableHead>
                  <TableHead scope="col">Puesto</TableHead>
                  <TableHead scope="col">Vigencia</TableHead>
                  <TableHead scope="col">Situación</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {datos.elementos.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="whitespace-normal">
                      <Link to={`/trabajadores/${t.id}`} className="flex min-h-12 items-center gap-3 font-semibold text-foreground hover:underline">
                        <Avatar nombre={t.nombre} fotoUrl={t.tiene_foto ? `/api/trabajadores/${t.id}/foto` : null} />
                        <span className="flex flex-col">
                          <span>{t.nombre}</span>
                          <span className="text-xs font-normal text-muted-foreground">{t.numero_empleado}</span>
                        </span>
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div>{t.puesto ?? "—"}</div>
                      <div className="text-xs text-muted-foreground">{t.area_obra ?? ""}</div>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="flex flex-col items-start gap-1">
                        <InsigniaVigencia vigencia={t.vigencia} />
                        <span className="text-xs text-muted-foreground">{formatearPeriodo(t.periodo_inicio, t.periodo_fin)}</span>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <InsigniaSituacion situacion={t.situacion} texto={t.situacion_texto} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Celular: tarjetas */}
          <ul className="flex flex-col gap-3 md:hidden">
            {datos.elementos.map((t) => (
              <li key={t.id}>
                <Link to={`/trabajadores/${t.id}`} className="flex flex-col gap-3 rounded-2xl border bg-card p-4 shadow-xs active:bg-accent/40">
                  <span className="flex items-center gap-3">
                    <Avatar nombre={t.nombre} fotoUrl={t.tiene_foto ? `/api/trabajadores/${t.id}/foto` : null} />
                    <span className="flex min-w-0 flex-col">
                      <span className="text-base font-semibold text-foreground">{t.nombre}</span>
                      <span className="text-sm text-muted-foreground">
                        {t.numero_empleado} · {t.puesto ?? "Sin puesto"}
                      </span>
                    </span>
                  </span>
                  <span className="flex flex-wrap items-center gap-2">
                    <InsigniaVigencia vigencia={t.vigencia} />
                    <InsigniaSituacion situacion={t.situacion} texto={t.situacion_texto} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          <nav aria-label="Páginas" className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {datos.total} {datos.total === 1 ? "trabajador" : "trabajadores"}
            </p>
            {totalPaginas > 1 ? (
              <div className="flex items-center gap-2">
                <Boton variante="contorno" disabled={pagina <= 1 || cargando} onClick={() => setPagina((p) => p - 1)}>
                  Anterior
                </Boton>
                <span className="text-sm">
                  Página {pagina} de {totalPaginas}
                </span>
                <Boton variante="contorno" disabled={pagina >= totalPaginas || cargando} onClick={() => setPagina((p) => p + 1)}>
                  Siguiente
                </Boton>
              </div>
            ) : null}
          </nav>
        </div>
      ) : null}
    </Pantalla>
  );
}
