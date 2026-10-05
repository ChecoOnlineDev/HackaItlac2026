import { HistoryIcon, SearchIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { apiGet } from "~/api/cliente";
import { ResultadoTrabajador } from "~/componentes/consulta/resultado-trabajador";
import { ResultadosBusqueda } from "~/componentes/consulta/resultados";
import type { Busqueda, Escaneo } from "~/componentes/consulta/tipos";
import { Escaner, type OrigenLectura } from "~/componentes/dominio/escaner";
import { reproducir } from "~/componentes/dominio/sonido";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = {};

type Resultado =
  | { tipo: "trabajador"; id: string }
  | { tipo: "texto"; texto: string; busqueda: Busqueda }
  | { tipo: "aviso"; mensaje: string };

const MINIMO_BUSQUEDA = 2;

export default function Consultar() {
  const { puede } = useSesion();
  const navegar = useNavigate();
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const ultimo = useRef<string>("");
  const control = useRef<AbortController | null>(null);

  useEffect(() => () => control.current?.abort(), []);

  const consultar = useCallback(
    async (bruto: string, _origen?: OrigenLectura) => {
      const texto = bruto.trim();
      ultimo.current = texto;
      setError(null);
      if (texto.length < MINIMO_BUSQUEDA) {
        setResultado({ tipo: "aviso", mensaje: "Escribe al menos dos caracteres para buscar." });
        return;
      }
      control.current?.abort();
      const actual = new AbortController();
      control.current = actual;
      setBuscando(true);
      try {
        const escaneo = await apiGet<Escaneo>(`/escaneo/${encodeURIComponent(texto)}`, undefined, actual.signal);
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
            // No es un código conocido: se busca como texto.
            const busqueda = await apiGet<Busqueda>("/busqueda", { q: texto }, actual.signal);
            if (busqueda.sin_resultados) reproducir("aviso");
            setResultado({ tipo: "texto", texto, busqueda });
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
    [navegar],
  );

  const otraConsulta = () => {
    control.current?.abort();
    setBuscando(false);
    setResultado(null);
    setError(null);
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
          <Escaner onCodigo={(c, o) => void consultar(c, o)} activo={!buscando} />
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
