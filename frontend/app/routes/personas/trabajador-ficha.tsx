import { CameraIcon, IdCardIcon, LogOutIcon, QrCodeIcon, RotateCcwIcon, UndoIcon, UserXIcon, XCircleIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { api, apiDelete, apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { BotonNoAdeudo, useAccionNoAdeudo } from "~/componentes/devolucion/no-adeudo";
import { VistaCredencial } from "~/componentes/dominio/credencial";
import { BloqueDotacion } from "~/componentes/personas/bloque-dotacion";
import { ConsumoDelTrabajador } from "~/componentes/personas/consumo-trabajador";
import { SelectorFoto } from "~/componentes/personas/foto";
import { fechaCorta } from "~/componentes/personas/formato";
import { InsigniaSituacion, InsigniaVigencia } from "~/componentes/personas/insignias";
import { ListaPendientes } from "~/componentes/personas/pendientes";
import { cuerpoDePuesto, SelectorPuesto } from "~/componentes/puestos/selector-puesto";
import { etiquetaTalla } from "~/componentes/personas/tallas";
import type { CodigoLigado, Ficha, RespuestaBaja } from "~/componentes/personas/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Avatar } from "~/componentes/ui/avatar";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { hoyMx } from "~/componentes/personas/formato";
import { SelectorProyecto } from "~/componentes/proyectos/selector-proyecto";
import { ProyectosTrabajador } from "~/componentes/proyectos/proyectos-trabajador";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "trabajadores.ver" };

type Panel = null | "reingreso" | "baja" | "cancelar-baja" | "foto" | "credencial" | "imprimir";

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-bold text-marino">{titulo}</h2>
      {children}
    </section>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <dt className="text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className="text-base">{valor}</dd>
    </div>
  );
}

export default function FichaTrabajador() {
  const { id } = useParams();
  const { puede } = useSesion();
  const puedeAdministrar = puede("trabajadores.administrar");
  const puedeBaja = puede("trabajadores.iniciar_baja");
  const puedeNoAdeudo = puede("no_adeudo.emitir");
  const puedeImprimir = puede("etiquetas.imprimir");

  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cargando, setCargando] = useState(true);
  const [intento, setIntento] = useState(0);
  const [versionFoto, setVersionFoto] = useState(0);

  const [panel, setPanel] = useState<Panel>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [errorPanel, setErrorPanel] = useState<string | null>(null);
  const [errorFecha, setErrorFecha] = useState<string | null>(null);

  // Reingreso
  const [inicio, setInicio] = useState(hoyMx());
  const [fin, setFin] = useState("");
  const [puestoId, setPuestoId] = useState("");
  const [puesto, setPuesto] = useState("");
  const [proyectoId, setProyectoId] = useState("");
  // Foto y credencial
  const [foto, setFoto] = useState<File | null>(null);
  const [codigo, setCodigo] = useState("");
  const [generar, setGenerar] = useState(false);
  // Qué código se imprime en la credencial cuando la persona tiene varios ligados.
  const [codigoImpreso, setCodigoImpreso] = useState("");
  // Baja
  const [baja, setBaja] = useState<RespuestaBaja | null>(null);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const noAdeudo = useAccionNoAdeudo(ficha ? { id: ficha.id, nombre: ficha.nombre, estado: ficha.estado } : null, recargar);

  useEffect(() => {
    if (!id) return;
    const control = new AbortController();
    setCargando(true);
    setError(null);
    apiGet<Ficha>(`/trabajadores/${id}`, undefined, control.signal)
      .then((f) => {
        setFicha(f);
        setCargando(false);
      })
      .catch((causa: unknown) => {
        if (causa instanceof DOMException && causa.name === "AbortError") return;
        setError(causa);
        setCargando(false);
      });
    return () => control.abort();
  }, [id, intento]);

  function abrir(p: Exclude<Panel, null>) {
    setErrorPanel(null);
    setErrorFecha(null);
    if (p === "reingreso" && ficha) {
      setInicio(hoyMx());
      setFin("");
      setPuestoId("");
      setPuesto(ficha.puesto ?? "");
      setProyectoId(ficha.proyectos?.find((p) => p.principal)?.proyecto.id ?? ficha.proyectos?.[0]?.proyecto.id ?? "");
    }
    if (p === "foto") setFoto(null);
    if (p === "credencial") {
      setCodigo("");
      setGenerar(false);
    }
    setPanel(p);
  }

  async function ejecutar(accion: () => Promise<void>) {
    setTrabajando(true);
    setErrorPanel(null);
    try {
      await accion();
    } catch (causa) {
      if (esErrorApi(causa) && causa.campo === "fin") setErrorFecha(causa.message);
      else setErrorPanel(mensajeDeError(causa));
    } finally {
      setTrabajando(false);
    }
  }

  const reingresar = () =>
    ejecutar(async () => {
      if (!fin) {
        setErrorFecha("Elige la fecha de fin.");
        return;
      }
      if (fin < inicio) {
        setErrorFecha("La fecha de fin no puede ser anterior a la de inicio.");
        return;
      }
      const nueva = await apiPost<Ficha>(`/trabajadores/${id}/periodos`, {
        inicio,
        fin,
        ...cuerpoDePuesto(puestoId, puesto),
        proyecto_id: proyectoId || undefined,
      });
      setFicha(nueva);
      setPanel(null);
      aviso({ titulo: "Se registró el nuevo periodo", tipo: "exito" });
    });

  const iniciarBaja = () =>
    ejecutar(async () => {
      const respuesta = await apiPost<RespuestaBaja>(`/trabajadores/${id}/baja`);
      setBaja(respuesta);
      setPanel(null);
      recargar();
      aviso({ titulo: "La baja quedó en proceso", tipo: "info" });
    });

  const cancelarBaja = () =>
    ejecutar(async () => {
      const nueva = await apiDelete<Ficha>(`/trabajadores/${id}/baja`);
      setFicha(nueva);
      setBaja(null);
      setPanel(null);
      aviso({ titulo: "Se canceló la baja", tipo: "exito" });
    });

  const guardarFoto = () =>
    ejecutar(async () => {
      if (!foto) return;
      const cuerpo = new FormData();
      cuerpo.append("archivo", foto);
      await api(`/trabajadores/${id}/foto`, { metodo: "POST", cuerpo });
      setVersionFoto((v) => v + 1);
      setPanel(null);
      recargar();
      aviso({ titulo: "La foto quedó guardada", tipo: "exito" });
    });

  const ligarCodigo = () =>
    ejecutar(async () => {
      if (!codigo.trim() && !generar) {
        setErrorPanel("Escribe el código o elige generar uno propio.");
        return;
      }
      const ligado = await apiPost<CodigoLigado>(`/trabajadores/${id}/codigos`, codigo.trim() ? { codigo: codigo.trim() } : {});
      setPanel(null);
      recargar();
      aviso({ titulo: ligado.generado ? `Código propio generado: ${ligado.codigo}` : "La credencial quedó ligada", tipo: "exito" });
    });

  if (cargando && !ficha) {
    return (
      <Pantalla titulo="Ficha del trabajador">
        <Esqueleto tipo="lista" cantidad={3} />
      </Pantalla>
    );
  }

  if (error && !ficha) {
    const noExiste = esErrorApi(error) && error.status === 404;
    return (
      <Pantalla titulo="Ficha del trabajador">
        {noExiste ? (
          <EstadoVacio
            icono={UserXIcon}
            titulo="No encontramos a esa persona"
            descripcion="Puede que el enlace sea viejo. Búscala en la lista."
            accion={
              <Boton variante="normal" nativeButton={false} render={<Link to="/trabajadores" />}>
                Ir a la lista
              </Boton>
            }
          />
        ) : (
          <EstadoError error={error} alReintentar={recargar} />
        )}
      </Pantalla>
    );
  }

  if (!ficha) return null;

  const vigente = ficha.vigencia.vigente;
  const enBaja = ficha.estado === "BAJA_EN_PROCESO";
  const inactivo = ficha.estado === "INACTIVO";
  const tallas = Object.entries(ficha.tallas ?? {});
  const fotoUrl = ficha.foto_url ? `${ficha.foto_url}?v=${versionFoto}` : null;
  const codigoEnCredencial = ficha.codigos.includes(codigoImpreso) ? codigoImpreso : (ficha.codigos[0] ?? "");
  const pendientesBaja = baja?.pendientes ?? ficha.resguardo;

  return (
    <Pantalla titulo="Ficha del trabajador" descripcion="Datos, vigencia, lo que tiene en resguardo y sus pendientes.">
      <article
        aria-label={`Ficha de ${ficha.nombre}`}
        className={`flex flex-col gap-6 rounded-xl border p-4 md:p-6 ${vigente ? "" : "border-2 border-semaforo-rojo bg-semaforo-rojo/5"}`}
      >
        {!vigente ? (
          <div role="alert" className="flex items-start gap-3 rounded-lg border-2 border-semaforo-rojo bg-background p-4">
            <XCircleIcon aria-hidden="true" className="mt-0.5 size-6 shrink-0 text-semaforo-rojo" strokeWidth={3} />
            <div className="flex flex-col gap-1">
              <p className="text-lg font-bold text-foreground">No vigente: no se le puede entregar equipo</p>
              {ficha.vigencia.motivo ? <p className="text-base">{ficha.vigencia.motivo}</p> : null}
            </div>
          </div>
        ) : null}

        <header className="flex items-start gap-4">
          <Avatar nombre={ficha.nombre} fotoUrl={fotoUrl} tamano="lg" className="size-20 text-3xl sm:size-24" />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <h2 className="text-[20px] leading-tight font-bold text-marino">{ficha.nombre}</h2>
            <p className="text-base">Número {ficha.numero_empleado}</p>
            <p className="text-base">
              {ficha.puesto ?? "Sin puesto"}
              {ficha.area_obra ? ` · ${ficha.area_obra}` : ""}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <InsigniaVigencia vigencia={ficha.vigencia} />
              <InsigniaSituacion situacion={ficha.situacion} texto={ficha.situacion_texto} />
              <Insignia estado="neutra">{ficha.estado_texto}</Insignia>
            </div>
            {ficha.periodo ? (
              <p className="text-base">
                {vigente ? "Vigente" : "Contrato"} del {fechaCorta(ficha.periodo.inicio)} al {fechaCorta(ficha.periodo.fin)}
              </p>
            ) : (
              <p className="text-base">Sin periodo de contrato.</p>
            )}
          </div>
        </header>

        {/* Acciones, según permiso y estado */}
        {puedeAdministrar || puedeBaja || puedeImprimir || (puedeNoAdeudo && ficha.estado === "ACTIVO") ? (
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            {puedeAdministrar && !enBaja ? (
              <Boton variante={inactivo || !vigente ? "normal" : "contorno"} onClick={() => abrir("reingreso")}>
                <RotateCcwIcon aria-hidden="true" />
                Reingresar
              </Boton>
            ) : null}
            {puedeBaja && ficha.estado === "ACTIVO" ? (
              <Boton variante="contorno" onClick={() => abrir("baja")}>
                <LogOutIcon aria-hidden="true" />
                Iniciar baja
              </Boton>
            ) : null}
            {puedeNoAdeudo && ficha.estado === "ACTIVO" ? (
              <BotonNoAdeudo alAbrir={noAdeudo.abrir} />
            ) : null}
            {puedeAdministrar && enBaja ? (
              <Boton variante="contorno" onClick={() => abrir("cancelar-baja")}>
                <UndoIcon aria-hidden="true" />
                Cancelar baja
              </Boton>
            ) : null}
            {puedeImprimir && ficha.codigos.length > 0 ? (
              <Boton variante="contorno" onClick={() => abrir("imprimir")}>
                <IdCardIcon aria-hidden="true" />
                Credencial
              </Boton>
            ) : null}
            {puedeAdministrar ? (
              <>
                <Boton variante="contorno" onClick={() => abrir("foto")}>
                  <CameraIcon aria-hidden="true" />
                  {ficha.tiene_foto ? "Cambiar foto" : "Agregar foto"}
                </Boton>
                <Boton variante="contorno" onClick={() => abrir("credencial")}>
                  <QrCodeIcon aria-hidden="true" />
                  Ligar otra credencial
                </Boton>
              </>
            ) : null}
          </div>
        ) : null}

        {enBaja ? (
          <Seccion titulo="Baja en proceso">
            <p className="text-base">
              {pendientesBaja.length > 0
                ? `Todavía debe devolver ${pendientesBaja.length} ${pendientesBaja.length === 1 ? "pieza" : "piezas"}, de todos los almacenes. El vale de no adeudo se emite cuando no deba nada.`
                : "No debe nada: el almacén ya puede emitir su vale de no adeudo."}
            </p>
            {puedeNoAdeudo ? (
              <BotonNoAdeudo alAbrir={noAdeudo.abrir} className="self-start" />
            ) : (
              <p className="text-sm text-muted-foreground">El vale de no adeudo lo emite el almacén.</p>
            )}
            <p className="text-sm text-muted-foreground">Los consumibles (guantes, lentes, tapones…) no cuentan: solo lo que tiene que devolver.</p>
          </Seccion>
        ) : null}

        <ProyectosTrabajador key={`${ficha.id}|${ficha.periodo?.id ?? ""}`} trabajadorId={ficha.id} estado={ficha.estado} alCambiar={recargar} />
        <Seccion titulo="Resguardo y pendientes">
          {ficha.resguardo.length === 0 ? (
            <p className="text-base">No tiene equipo pendiente de devolver.</p>
          ) : (
            <>
              <p className="text-base font-semibold">
                {ficha.pendientes.total} {ficha.pendientes.total === 1 ? "pendiente" : "pendientes"}
                {ficha.pendientes.de_periodos_anteriores > 0 ? `, ${ficha.pendientes.de_periodos_anteriores} de un periodo anterior` : ""}
              </p>
              <ListaPendientes pendientes={ficha.resguardo} />
            </>
          )}
        </Seccion>

        <Seccion titulo="Dotación del puesto">
          <BloqueDotacion trabajadorId={ficha.id} version={`${ficha.periodo?.id ?? ""}|${intento}`} />
        </Seccion>

        <ConsumoDelTrabajador id={ficha.id} />
        {puede("deudores.ver") ? <Link className="self-start underline" to={`/deudores?trabajador_id=${ficha.id}`}>Ver sus adeudos por almacén</Link> : null}

        <Seccion titulo="Datos">
          <dl className="grid gap-4 sm:grid-cols-2">
            {ficha.periodo ? (
              <Dato etiqueta="Periodo actual" valor={`${fechaCorta(ficha.periodo.inicio)} al ${fechaCorta(ficha.periodo.fin)}`} />
            ) : null}
            {ficha.periodo?.referencia ? <Dato etiqueta="Referencia" valor={ficha.periodo.referencia} /> : null}
            <Dato
              etiqueta="Credenciales y códigos"
              valor={ficha.codigos.length > 0 ? ficha.codigos.join(", ") : "Todavía no tiene credencial ligada"}
            />
            {tallas.length > 0 ? (
              <Dato etiqueta="Tallas" valor={tallas.map(([k, v]) => `${etiquetaTalla(k)} ${v}`).join(" · ")} />
            ) : null}
            {"curp" in ficha ? <Dato etiqueta="CURP" valor={ficha.curp ?? "—"} /> : null}
            {"nss" in ficha ? <Dato etiqueta="NSS" valor={ficha.nss ?? "—"} /> : null}
          </dl>
        </Seccion>
      </article>

      {noAdeudo.ventanas}

      {/* Reingreso */}
      <Hoja
        abierta={panel === "reingreso"}
        alCambiar={(a) => !a && !trabajando && setPanel(null)}
        titulo="Reingresar"
        descripcion={`Registra un nuevo periodo para ${ficha.nombre}. Su historial y sus pendientes se conservan.`}
        pie={
          <Boton variante="normal" cargando={trabajando} onClick={() => void reingresar()}>
            Guardar nuevo periodo
          </Boton>
        }
      >
        <div className="flex flex-col gap-4">
          <CampoFecha etiqueta="Inicio" value={inicio} alCambiar={(v) => setInicio(v)} />
          <CampoFecha etiqueta="Fin" value={fin} alCambiar={(v) => { setFin(v); setErrorFecha(null); }} error={errorFecha} />
          <SelectorPuesto
            valorId={puestoId}
            valorTexto={puesto}
            alCambiar={(id, texto) => {
              setPuestoId(id);
              setPuesto(texto);
            }}
            vacio="Conservar el puesto actual"
            deshabilitado={trabajando}
          />
          <SelectorProyecto valor={proyectoId} alCambiar={setProyectoId} deshabilitado={trabajando} />
          {panel === "reingreso" && errorPanel ?<p role="alert" className="text-base font-semibold text-destructive">{errorPanel}</p> : null}
        </div>
      </Hoja>

      {/* Foto */}
      <Hoja
        abierta={panel === "foto"}
        alCambiar={(a) => !a && !trabajando && setPanel(null)}
        titulo={ficha.tiene_foto ? "Cambiar foto" : "Agregar foto"}
        descripcion="Toma una foto con la cámara o elige una imagen."
        pie={
          <Boton variante="normal" cargando={trabajando} disabled={!foto} onClick={() => void guardarFoto()}>
            Guardar foto
          </Boton>
        }
      >
        <div className="flex flex-col gap-4">
          <SelectorFoto
            nombre={ficha.nombre}
            fotoActualUrl={fotoUrl}
            archivo={foto}
            alElegir={(archivo, mensaje) => {
              setFoto(archivo);
              setErrorPanel(mensaje ?? null);
            }}
            deshabilitado={trabajando}
          />
          {panel === "foto" && errorPanel ? <p role="alert" className="text-base font-semibold text-destructive">{errorPanel}</p> : null}
        </div>
      </Hoja>

      {/* Imprimir o descargar la credencial (solo con `etiquetas.imprimir`) */}
      {puedeImprimir && ficha.codigos.length > 0 ? (
        <Hoja
          abierta={panel === "imprimir"}
          alCambiar={(a) => !a && setPanel(null)}
          titulo="Credencial"
          descripcion="Imprímela, guárdala como PDF o descarga la imagen."
        >
          {ficha.codigos.length > 1 ? (
            <div className="mb-4">
              <label htmlFor="codigo-credencial" className="mb-1.5 block text-sm font-medium">
                Código de la credencial
              </label>
              <ListaDesplegable
                id="codigo-credencial"
                valor={codigoEnCredencial}
                alCambiar={setCodigoImpreso}
                opciones={ficha.codigos.map((c) => ({ valor: c, texto: c }))}
              />
            </div>
          ) : null}
          <VistaCredencial
            key={codigoEnCredencial}
            datos={{ codigo: codigoEnCredencial, nombre: ficha.nombre, puesto: ficha.puesto, numero_empleado: ficha.numero_empleado }}
          />
        </Hoja>
      ) : null}

      {/* Credencial */}
      <Hoja
        abierta={panel === "credencial"}
        alCambiar={(a) => !a && !trabajando && setPanel(null)}
        titulo="Ligar otra credencial"
        descripcion="Teclea o pega el código de la credencial, o genera un código propio para imprimir."
        pie={
          <Boton variante="normal" cargando={trabajando} onClick={() => void ligarCodigo()}>
            Ligar credencial
          </Boton>
        }
      >
        <div className="flex flex-col gap-4">
          <Campo
            etiqueta="Código de la credencial"
            value={codigo}
            onChange={(e) => { setCodigo(e.target.value); setGenerar(false); setErrorPanel(null); }}
            autoComplete="off"
            autoCapitalize="characters"
            error={panel === "credencial" ? errorPanel : null}
          />
          <Boton
            variante={generar ? "normal" : "contorno"}
            aria-pressed={generar}
            className="self-start"
            onClick={() => { setGenerar((g) => !g); setCodigo(""); setErrorPanel(null); }}
          >
            <QrCodeIcon aria-hidden="true" />
            {generar ? "Se generará un código propio" : "Generar código propio"}
          </Boton>
        </div>
      </Hoja>

      {/* Baja */}
      <Confirmacion
        abierta={panel === "baja"}
        alCambiar={(a) => !a && !trabajando && setPanel(null)}
        mensaje={`¿Iniciar la baja de ${ficha.nombre}?`}
        detalle={
          errorPanel ??
          (ficha.resguardo.length > 0
            ? `Tiene ${ficha.resguardo.length} ${ficha.resguardo.length === 1 ? "pendiente" : "pendientes"} por devolver. Ya no se le podrá entregar equipo.`
            : "Ya no se le podrá entregar equipo. Puedes cancelar la baja mientras esté en proceso.")
        }
        etiquetaConfirmar="Sí, iniciar baja"
        etiquetaCancelar="No, volver"
        peligro
        cargando={trabajando}
        alConfirmar={() => void iniciarBaja()}
      />
      <Confirmacion
        abierta={panel === "cancelar-baja"}
        alCambiar={(a) => !a && !trabajando && setPanel(null)}
        mensaje={`¿Cancelar la baja de ${ficha.nombre}?`}
        detalle={errorPanel ?? "Volverá a estar activo y se le podrá entregar equipo."}
        etiquetaConfirmar="Sí, cancelar la baja"
        etiquetaCancelar="No, volver"
        cargando={trabajando}
        alConfirmar={() => void cancelarBaja()}
      />
    </Pantalla>
  );
}
