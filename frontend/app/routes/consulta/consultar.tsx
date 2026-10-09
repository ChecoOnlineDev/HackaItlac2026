import { HistoryIcon, SearchIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { apiGet } from "~/api/cliente";
import { ResultadoTrabajador } from "~/componentes/consulta/resultado-trabajador";
import { ResultadosBusqueda } from "~/componentes/consulta/resultados";
import type { Busqueda, Escaneo } from "~/componentes/consulta/tipos";
import { Escaner, type OrigenLectura } from "~/componentes/dominio/escaner";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";
import { useBusquedaDiferida } from "~/componentes/ui/busqueda-diferida";

export const handle: ManejadorRuta = { dispositivo: "celular" };

type Resultado =
  | { tipo: "trabajador"; id: string }
  | { tipo: "texto"; texto: string; busqueda: Busqueda }
  | { tipo: "aviso"; mensaje: string };

export default function Consultar() {
  const { puede } = useSesion();
  const navegar = useNavigate();
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const ultimo = useRef<string>("");
  const control = useRef<AbortController | null>(null);
  const [texto, setTexto] = useState("");
  const [pagina, setPagina] = useState(1);
  const busqueda = useBusquedaDiferida(texto, (q, signal) => apiGet<Busqueda>("/busqueda", { q, pagina, tamano: 10 }, signal), { vacio: (r) => r.sin_resultados });

  useEffect(() => () => control.current?.abort(), []);

  const consultar = useCallback(
    async (bruto: string, origen?: OrigenLectura) => {
      const texto = bruto.trim();
      ultimo.current = texto;
      setError(null);
      if (!texto) return;
      setTexto("");
      control.current?.abort();
      const actual = new AbortController();
      control.current = actual;
      setBuscando(true);
      try {
        const escaneo = await apiGet<Escaneo>(`/escaneo/${encodeURIComponent(texto)}`, undefined, actual.signal);
        if (actual.signal.aborted) return;
        switch (escaneo.tipo) {
          case "TRABAJADOR":
            setResultado({ tipo: "trabajador", id: escaneo.id });
            return;
          case "PIEZA":
            navegar(`/piezas/${escaneo.id}`);
            return;
          case "ARTICULO":
            navegar(`/articulos/${escaneo.id}`);
            return;
          case "VALE":
            navegar(`/vales/${escaneo.id}`);
            return;
          default: {
            if (origen === "teclado" && texto.length >= 2) {
              setPagina(1);
              setTexto(texto);
              busqueda.buscarYa();
            } else {
              setResultado({ tipo: "aviso", mensaje: "No se encontró ese código. Escribe al menos 2 letras o números para buscar." });
            }
          }
        }
      } catch (causa) {
        if (causa instanceof DOMException && causa.name === "AbortError") return;
        setError(causa);
        setResultado(null);
      } finally {
        if (control.current === actual) setBuscando(false);
      }
    },
    [navegar, busqueda.buscarYa],
  );

  const otraConsulta = () => {
    control.current?.abort();
    setBuscando(false);
    setResultado(null);
    setError(null);
    setTexto("");
    busqueda.limpiar();
  };

  const conResultado = resultado !== null && resultado.tipo !== "aviso";

  return (
    <Pantalla
      titulo="Consultar"
      descripcion="Escanea o escribe para saber quién tiene algo, o qué tiene un trabajador."
      ancho="formulario"
      acciones={
        puede("vales.ver") ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to="/mis-movimientos" />}>
            <HistoryIcon aria-hidden="true" />
            Mis movimientos de hoy
          </Boton>
        ) : null
      }
    >
      {!conResultado ? (
        <>
          <Escaner ancla="consultar-escaner" onCodigo={(c, o) => void consultar(c, o)} alCambiarTexto={(q) => { control.current?.abort(); setBuscando(false); setError(null); setResultado(null); setPagina(1); setTexto(q); }} activo={!buscando} />
          {busqueda.estado === "corto" ? <p role="status" className="text-sm text-muted-foreground">Escribe al menos 2 letras o números.</p> : null}
          {busqueda.estado === "buscando" ? <p role="status" className="text-sm text-muted-foreground">Buscando…</p> : null}
          {busqueda.estado === "sin_conexion" ? <p role="status">Sin conexión. Escanea el código o inténtalo cuando vuelva la señal.</p> : null}
          {busqueda.error ? <EstadoError error={busqueda.error} alReintentar={busqueda.buscarYa} /> : null}
          {busqueda.resultado ? <div inert={busqueda.estado === "buscando"} className={busqueda.estado === "buscando" ? "opacity-50" : undefined}>
            <ResultadosBusqueda busqueda={busqueda.resultado} texto={busqueda.textoDelResultado} />
            {[busqueda.resultado.articulos, busqueda.resultado.piezas, busqueda.resultado.trabajadores].some((g) => g.total > pagina * 10) ? <Boton variante="contorno" onClick={() => { setPagina((p) => p + 1); busqueda.buscarYa(); }}>Ver más</Boton> : null}
            {pagina > 1 ? <Boton variante="contorno" onClick={() => { setPagina(1); busqueda.buscarYa(); }}>Volver al inicio</Boton> : null}
          </div> : null}
          {resultado?.tipo === "aviso" ? (
            <p role="alert" className="rounded-2xl border bg-muted p-3 text-sm font-medium">
              {resultado.mensaje}
            </p>
          ) : null}
          {buscando ? <Esqueleto tipo="renglon" /> : null}
          {error ? <EstadoError error={error} alReintentar={() => void consultar(ultimo.current)} /> : null}
        </>
      ) : (
        <>
          <Boton variante="contorno" className="self-start" onClick={otraConsulta}>
            <SearchIcon aria-hidden="true" />
            Consultar otro
          </Boton>
          {resultado.tipo === "trabajador" ? <ResultadoTrabajador id={resultado.id} /> : null}
          {resultado.tipo === "texto" ? <ResultadosBusqueda busqueda={resultado.busqueda} texto={resultado.texto} /> : null}
        </>
      )}
    </Pantalla>
  );
}
