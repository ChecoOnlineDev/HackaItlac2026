import { QrCodeIcon, RotateCcwIcon, TriangleAlertIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { api, apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { VistaCredencial } from "~/componentes/dominio/credencial";
import { SelectorFoto } from "~/componentes/personas/foto";
import { fechaCorta, hoyMx } from "~/componentes/personas/formato";
import { InsigniaSituacion, InsigniaVigencia } from "~/componentes/personas/insignias";
import { ListaPendientes } from "~/componentes/personas/pendientes";
import { TALLAS } from "~/componentes/personas/tallas";
import type { CodigoLigado, ElementoLista, Ficha } from "~/componentes/personas/tipos";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "trabajadores.administrar" };

type Errores = Record<string, string>;

/** Lleva un error de la API al campo que corresponde; si no hay campo, queda como mensaje general. */
function errorDeCampo(error: unknown, errores: Errores): { campo: string | null; mensaje: string } {
  const mensaje = mensajeDeError(error);
  return { campo: esErrorApi(error) ? error.campo : null, mensaje: errores[mensaje] ?? mensaje };
}

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-xl border p-4">
      <h2 className="text-lg font-bold text-marino">{titulo}</h2>
      {children}
    </section>
  );
}

export default function AltaTrabajador() {
  const { puede } = useSesion();
  const verDatosPersonales = puede("trabajadores.ver_datos_personales");
  const navegar = useNavigate();

  const [numero, setNumero] = useState("");
  const [nombre, setNombre] = useState("");
  const [puesto, setPuesto] = useState("");
  const [area, setArea] = useState("");
  const [inicio, setInicio] = useState(hoyMx());
  const [fin, setFin] = useState("");
  const [tallas, setTallas] = useState<Record<string, string>>({});
  const [curp, setCurp] = useState("");
  const [nss, setNss] = useState("");
  const [codigo, setCodigo] = useState("");
  const [generar, setGenerar] = useState(false);
  const [foto, setFoto] = useState<File | null>(null);

  const [errores, setErrores] = useState<Errores>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  // Avance del alta: si un paso falla, lo ya hecho no se repite.
  const [creadoId, setCreadoId] = useState<string | null>(null);
  const [credencialLista, setCredencialLista] = useState(false);
  const [codigoLigado, setCodigoLigado] = useState<string | null>(null);
  // Alta terminada: si quien la hizo puede imprimir etiquetas, se le ofrece la credencial antes de ir a la ficha.
  const [terminado, setTerminado] = useState<{ id: string; codigo: string } | null>(null);
  const [fotoLista, setFotoLista] = useState(false);

  // Número de empleado que ya existe: se ofrece el reingreso.
  const [existente, setExistente] = useState<Ficha | null>(null);
  const [porCurp, setPorCurp] = useState(false);
  const [revisandoNumero, setRevisandoNumero] = useState(false);
  const verificacion = useRef<AbortController | null>(null);

  // Datos del reingreso.
  const [reInicio, setReInicio] = useState(hoyMx());
  const [reFin, setReFin] = useState("");
  const [rePuesto, setRePuesto] = useState("");
  const [reArea, setReArea] = useState("");

  useEffect(() => () => verificacion.current?.abort(), []);

  function limpiar(campo: string) {
    setErrores((e) => {
      if (!(campo in e)) return e;
      const { [campo]: _quitado, ...resto } = e;
      return resto;
    });
    setErrorGeneral(null);
  }

  async function cargarExistente(id: string) {
    const ficha = await apiGet<Ficha>(`/trabajadores/${id}`);
    setExistente(ficha);
    setRePuesto(ficha.puesto ?? "");
    setReArea(ficha.area_obra ?? "");
    setReInicio(hoyMx());
    setReFin("");
    setErrores({});
  }

  /** Al salir del campo: ¿ya existe ese número? */
  async function revisarNumero() {
    const buscado = numero.trim();
    if (!buscado || creadoId) return;
    verificacion.current?.abort();
    const control = new AbortController();
    verificacion.current = control;
    setRevisandoNumero(true);
    try {
      const pagina = await apiGet<Pagina<ElementoLista>>("/trabajadores", { q: buscado, tamano: 50 }, control.signal);
      const coincide = pagina.elementos.find((t) => t.numero_empleado.toLowerCase() === buscado.toLowerCase());
      setPorCurp(false);
      if (coincide) await cargarExistente(coincide.id);
      else setExistente(null);
    } catch (causa) {
      if (causa instanceof DOMException && causa.name === "AbortError") return;
      // Si no se pudo revisar, el servidor lo vuelve a validar al guardar.
    } finally {
      if (verificacion.current === control) setRevisandoNumero(false);
    }
  }

  function cambiarNumero(valor: string) {
    setNumero(valor);
    limpiar("numero_empleado");
    if (existente) setExistente(null);
  }

  function validarLocal(): Errores {
    const e: Errores = {};
    if (!numero.trim()) e.numero_empleado = "Escribe el número de empleado.";
    if (!nombre.trim()) e.nombre = "Escribe el nombre completo.";
    if (!puesto.trim()) e.puesto = "Escribe el puesto.";
    if (!area.trim()) e.area_obra = "Escribe el área o la obra.";
    if (!inicio) e.inicio = "Elige la fecha de inicio.";
    if (!fin) e.fin = "Elige la fecha de fin.";
    else if (inicio && fin < inicio) e.fin = "La fecha de fin no puede ser anterior a la de inicio.";
    if (curp.trim() && !/^[A-Za-z0-9]{18}$/.test(curp.trim())) e.curp = "La CURP lleva 18 letras y números.";
    if (nss.trim() && !/^\d{11}$/.test(nss.trim())) e.nss = "El NSS lleva 11 números.";
    return e;
  }

  async function guardar(evento: FormEvent) {
    evento.preventDefault();
    if (guardando) return;
    const locales = creadoId ? {} : validarLocal();
    if (Object.keys(locales).length > 0) {
      setErrores(locales);
      return;
    }
    setErrores({});
    setErrorGeneral(null);
    setGuardando(true);

    let id = creadoId;
    let codigoFinal = codigoLigado; // el estado no se actualiza dentro de esta misma función
    try {
      // 1. Alta.
      if (!id) {
        const tallasLimpias = Object.fromEntries(Object.entries(tallas).filter(([, v]) => v.trim()));
        try {
          const ficha = await apiPost<Ficha>("/trabajadores", {
            nombre: nombre.trim(),
            numero_empleado: numero.trim(),
            puesto: puesto.trim(),
            area_obra: area.trim(),
            inicio,
            fin,
            tallas: Object.keys(tallasLimpias).length > 0 ? tallasLimpias : undefined,
            curp: verDatosPersonales && curp.trim() ? curp.trim() : undefined,
            nss: verDatosPersonales && nss.trim() ? nss.trim() : undefined,
          });
          id = ficha.id;
          setCreadoId(id);
        } catch (causa) {
          if (esErrorApi(causa) && causa.codigo === "TRABAJADOR_EXISTE") {
            const detalles = causa.detalles as { coincide_por?: string; trabajador?: { id?: string } } | null;
            const persona = detalles?.trabajador;
            setPorCurp(detalles?.coincide_por === "curp");
            if (persona?.id) await cargarExistente(persona.id);
            else setErrores({ numero_empleado: causa.message });
            return;
          }
          const { campo, mensaje } = errorDeCampo(causa, {});
          if (campo) setErrores({ [campo]: mensaje });
          else setErrorGeneral(mensaje);
          return;
        }
      }

      // 2. Credencial.
      if (!credencialLista && (codigo.trim() || generar)) {
        try {
          const ligado = await apiPost<CodigoLigado>(`/trabajadores/${id}/codigos`, codigo.trim() ? { codigo: codigo.trim() } : {});
          codigoFinal = ligado.codigo;
          setCodigoLigado(ligado.codigo);
          setCredencialLista(true);
        } catch (causa) {
          setErrores({ codigo: mensajeDeError(causa) });
          setErrorGeneral(
            "La persona ya quedó registrada, pero falta ligar su credencial. Corrige el código y vuelve a guardar, o termina después desde su ficha.",
          );
          return;
        }
      }

      // 3. Foto.
      if (!fotoLista && foto) {
        try {
          const cuerpo = new FormData();
          cuerpo.append("archivo", foto);
          await api(`/trabajadores/${id}/foto`, { metodo: "POST", cuerpo });
          setFotoLista(true);
        } catch (causa) {
          setErrores({ foto: mensajeDeError(causa) });
          setErrorGeneral(
            "La persona ya quedó registrada, pero no pudimos guardar su foto. Vuelve a guardar, o súbela después desde su ficha.",
          );
          return;
        }
      }

      aviso({ titulo: `Se registró a ${nombre.trim()}`, tipo: "exito" });
      if (codigoFinal && puede("etiquetas.imprimir")) setTerminado({ id, codigo: codigoFinal });
      else void navegar(`/trabajadores/${id}`);
    } finally {
      setGuardando(false);
    }
  }

  async function reingresar() {
    if (!existente || guardando) return;
    const e: Errores = {};
    if (!reInicio) e.re_inicio = "Elige la fecha de inicio.";
    if (!reFin) e.re_fin = "Elige la fecha de fin.";
    else if (reInicio && reFin < reInicio) e.re_fin = "La fecha de fin no puede ser anterior a la de inicio.";
    setErrores(e);
    if (Object.keys(e).length > 0) return;
    setGuardando(true);
    setErrorGeneral(null);
    try {
      await apiPost<Ficha>(`/trabajadores/${existente.id}/periodos`, {
        inicio: reInicio,
        fin: reFin,
        puesto: rePuesto.trim() || undefined,
        area_obra: reArea.trim() || undefined,
      });
      aviso({ titulo: `Se reingresó a ${existente.nombre}`, tipo: "exito" });
      void navegar(`/trabajadores/${existente.id}`);
    } catch (causa) {
      const { campo, mensaje } = errorDeCampo(causa, {});
      if (campo === "fin") setErrores({ re_fin: mensaje });
      else setErrorGeneral(mensaje);
    } finally {
      setGuardando(false);
    }
  }

  const yaRegistrado = creadoId !== null;

  if (terminado) {
    return (
      <Pantalla titulo="Trabajador registrado" descripcion={`${nombre.trim()} ya quedó en el sistema. Imprime su credencial o solo el código QR.`} ancho="formulario">
        <div className="flex flex-col gap-5">
          <VistaCredencial datos={{ codigo: terminado.codigo, nombre: nombre.trim(), puesto: puesto.trim(), numero_empleado: numero.trim() }} />
          <Boton variante="principal" onClick={() => navegar(`/trabajadores/${terminado.id}`)}>
            Ir a su ficha
          </Boton>
        </div>
      </Pantalla>
    );
  }

  return (
    <Pantalla titulo="Alta de trabajador" descripcion="Registra a una persona nueva o reingresa a una anterior." ancho="formulario">
      <form onSubmit={guardar} noValidate className="flex flex-col gap-5 pb-28 lg:pb-0">
        <Campo
          etiqueta="Número de empleado"
          value={numero}
          onChange={(e) => cambiarNumero(e.target.value)}
          onBlur={() => void revisarNumero()}
          error={errores.numero_empleado}
          ayuda={revisandoNumero ? "Revisando si ya existe…" : undefined}
          disabled={yaRegistrado || guardando}
          autoComplete="off"
          autoCapitalize="characters"
        />

        {existente ? (
          <section aria-live="polite" className="flex flex-col gap-4 rounded-xl border-2 border-primary p-4">
            <div className="flex items-start gap-3">
              <RotateCcwIcon aria-hidden="true" className="mt-1 size-5 shrink-0 text-primary" />
              <div className="flex flex-col gap-1">
                <h2 className="text-lg font-bold text-marino">{porCurp ? "Esa CURP" : "Ese número"} ya es de {existente.nombre}</h2>
                <p className="text-base">¿Quieres reingresarlo? Se le registra un nuevo periodo y conserva su historial.</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <InsigniaVigencia vigencia={existente.vigencia} />
              <InsigniaSituacion situacion={existente.situacion} texto={existente.situacion_texto} />
              <span className="text-base text-muted-foreground">{existente.estado_texto}</span>
            </div>
            {existente.vigencia.motivo ? <p className="text-base">{existente.vigencia.motivo}</p> : null}
            {existente.pendientes.total > 0 ? (
              <div className="flex flex-col gap-3">
                <p className="flex items-center gap-2 text-base font-semibold">
                  <TriangleAlertIcon aria-hidden="true" className="size-5 shrink-0" />
                  Tiene {existente.pendientes.total} {existente.pendientes.total === 1 ? "pendiente" : "pendientes"} por devolver
                  {existente.pendientes.de_periodos_anteriores > 0 ? " (algunos de un periodo anterior)" : ""}.
                </p>
                <ListaPendientes pendientes={existente.resguardo} />
              </div>
            ) : null}
            {existente.periodo ? (
              <p className="text-base text-muted-foreground">
                Último periodo: {fechaCorta(existente.periodo.inicio)} al {fechaCorta(existente.periodo.fin)}
              </p>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <CampoFecha etiqueta="Inicio del nuevo periodo" value={reInicio} alCambiar={(v) => setReInicio(v)} error={errores.re_inicio} />
              <CampoFecha etiqueta="Fin del nuevo periodo" value={reFin} alCambiar={(v) => setReFin(v)} error={errores.re_fin} />
              <Campo etiqueta="Puesto" value={rePuesto} onChange={(e) => setRePuesto(e.target.value)} />
              <Campo etiqueta="Área u obra" value={reArea} onChange={(e) => setReArea(e.target.value)} />
            </div>
            {errorGeneral ? (
              <p role="alert" className="text-base font-semibold text-destructive">
                {errorGeneral}
              </p>
            ) : null}
            <div className="flex flex-col gap-3 sm:flex-row">
              <Boton type="button" variante="normal" cargando={guardando} onClick={() => void reingresar()}>
                Reingresar a {existente.nombre.split(" ")[0]}
              </Boton>
              <Boton type="button" variante="contorno" disabled={guardando} onClick={() => navegar(`/trabajadores/${existente.id}`)}>
                Ver su ficha
              </Boton>
              <Boton type="button" variante="texto" disabled={guardando} onClick={() => (porCurp ? setExistente(null) : cambiarNumero(""))}>
                {porCurp ? "Corregir los datos" : "Usar otro número"}
              </Boton>
            </div>
          </section>
        ) : (
          <>
            <Seccion titulo="Datos del trabajador">
              <Campo etiqueta="Nombre completo" value={nombre} onChange={(e) => { setNombre(e.target.value); limpiar("nombre"); }} error={errores.nombre} disabled={yaRegistrado || guardando} autoComplete="off" />
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo etiqueta="Puesto" value={puesto} onChange={(e) => { setPuesto(e.target.value); limpiar("puesto"); }} error={errores.puesto} disabled={yaRegistrado || guardando} />
                <Campo etiqueta="Área u obra" value={area} onChange={(e) => { setArea(e.target.value); limpiar("area_obra"); }} error={errores.area_obra} disabled={yaRegistrado || guardando} />
                <CampoFecha etiqueta="Inicio del contrato" value={inicio} alCambiar={(v) => { setInicio(v); limpiar("inicio"); limpiar("fin"); }} error={errores.inicio} disabled={yaRegistrado || guardando} />
                <CampoFecha etiqueta="Fin del contrato" value={fin} alCambiar={(v) => { setFin(v); limpiar("fin"); }} error={errores.fin ?? (fin && inicio && fin < inicio ? "La fecha de fin no puede ser anterior a la de inicio." : undefined)} disabled={yaRegistrado || guardando} />
              </div>
            </Seccion>

            <Seccion titulo="Tallas (opcional)">
              <div className="grid grid-cols-2 gap-4">
                {TALLAS.map((t) => (
                  <Campo
                    key={t.clave}
                    etiqueta={t.etiqueta}
                    value={tallas[t.clave] ?? ""}
                    onChange={(e) => setTallas((actual) => ({ ...actual, [t.clave]: e.target.value }))}
                    disabled={yaRegistrado || guardando}
                    maxLength={20}
                  />
                ))}
              </div>
            </Seccion>

            {verDatosPersonales ? (
              <Seccion titulo="Datos personales (opcional)">
                <div className="grid gap-4 sm:grid-cols-2">
                  <Campo etiqueta="CURP" value={curp} onChange={(e) => { setCurp(e.target.value.toUpperCase()); limpiar("curp"); }} error={errores.curp} disabled={yaRegistrado || guardando} maxLength={18} autoComplete="off" />
                  <Campo etiqueta="NSS" value={nss} onChange={(e) => { setNss(e.target.value); limpiar("nss"); }} error={errores.nss} disabled={yaRegistrado || guardando} maxLength={11} inputMode="numeric" autoComplete="off" />
                </div>
              </Seccion>
            ) : null}

            <Seccion titulo="Credencial">
              <p className="text-base text-muted-foreground">
                Teclea o pega el código de su credencial, o genera un código propio para imprimir. También se puede ligar después, desde su ficha.
              </p>
              <Campo
                etiqueta="Código de la credencial"
                value={codigo}
                onChange={(e) => { setCodigo(e.target.value); setGenerar(false); limpiar("codigo"); }}
                error={errores.codigo}
                disabled={credencialLista || guardando}
                autoComplete="off"
                autoCapitalize="characters"
              />
              <Boton
                type="button"
                variante={generar ? "normal" : "contorno"}
                aria-pressed={generar}
                disabled={credencialLista || guardando}
                onClick={() => { setGenerar((g) => !g); setCodigo(""); limpiar("codigo"); }}
                className="self-start"
              >
                <QrCodeIcon aria-hidden="true" />
                {generar ? "Se generará un código propio" : "Generar código propio"}
              </Boton>
              {credencialLista ? <p className="text-base font-semibold">La credencial ya quedó ligada.</p> : null}
            </Seccion>

            <Seccion titulo="Foto (opcional)">
              <SelectorFoto
                nombre={nombre}
                archivo={foto}
                alElegir={(archivo, mensaje) => {
                  setFoto(archivo);
                  setFotoLista(false);
                  setErrores((e) => {
                    const { foto: _quitada, ...resto } = e;
                    return mensaje ? { ...resto, foto: mensaje } : resto;
                  });
                }}
                deshabilitado={fotoLista || guardando}
              />
              {errores.foto ? (
                <p role="alert" className="text-base font-semibold text-destructive">
                  {errores.foto}
                </p>
              ) : null}
              {fotoLista ? <p className="text-base font-semibold">La foto ya quedó guardada.</p> : null}
            </Seccion>

            {errorGeneral ? (
              <p role="alert" className="rounded-xl border-2 border-destructive p-4 text-base font-semibold text-destructive">
                {errorGeneral}
              </p>
            ) : null}

            <AccionPrincipal>
              <Boton type="submit" variante="principal" cargando={guardando}>
                {yaRegistrado ? "Terminar el registro" : "Guardar trabajador"}
              </Boton>
              {yaRegistrado ? (
                <Boton type="button" variante="texto" disabled={guardando} onClick={() => navegar(`/trabajadores/${creadoId}`)}>
                  Ir a su ficha
                </Boton>
              ) : null}
            </AccionPrincipal>
          </>
        )}
      </form>
    </Pantalla>
  );
}
