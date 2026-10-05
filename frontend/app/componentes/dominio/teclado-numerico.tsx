import { DeleteIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";

interface PropiedadesTecladoNumerico {
  abierto: boolean;
  alCambiar: (abierto: boolean) => void;
  /** Cantidad con la que abre. El primer número que se teclea la reemplaza. */
  valorInicial: number;
  alAceptar: (cantidad: number) => void;
  titulo?: string;
  descripcion?: string;
  /** Mínimo permitido. Por omisión 1. */
  minimo?: number;
  /** Máximo permitido. Por omisión 9999. */
  maximo?: number;
}

/** Hoja con un teclado de números grandes para teclear una cantidad. También acepta el teclado físico. */
export function TecladoNumerico({
  abierto,
  alCambiar,
  valorInicial,
  alAceptar,
  titulo = "¿Cuántas piezas?",
  descripcion,
  minimo = 1,
  maximo = 9999,
}: PropiedadesTecladoNumerico) {
  // La fuente de verdad es una referencia: así dos teclas muy seguidas (como las de una pistola) no
  // se pisan aunque React todavía no haya vuelto a pintar.
  const origen = useRef({ texto: String(valorInicial), reemplazar: true });
  const [, repintar] = useState(0);
  const cambiar = (siguiente: { texto: string; reemplazar: boolean }) => {
    origen.current = siguiente;
    repintar((n) => n + 1);
  };

  useEffect(() => {
    if (abierto) cambiar({ texto: String(valorInicial), reemplazar: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, valorInicial]);

  const { texto } = origen.current;
  const valor = texto === "" ? 0 : Number(texto);
  const valido = valor >= minimo && valor <= maximo;

  const escribir = (digito: string) => {
    const { texto: actual, reemplazar } = origen.current;
    const base = reemplazar ? "" : actual === "0" ? "" : actual;
    const siguiente = base + digito;
    cambiar({ texto: siguiente.length > String(maximo).length ? actual : siguiente, reemplazar: false });
  };
  const borrar = () => {
    const { texto: actual, reemplazar } = origen.current;
    cambiar({ texto: reemplazar ? "" : actual.slice(0, -1), reemplazar: false });
  };
  const aceptar = () => {
    const n = origen.current.texto === "" ? 0 : Number(origen.current.texto);
    if (n < minimo || n > maximo) return;
    alAceptar(n);
    alCambiar(false);
  };

  useEffect(() => {
    if (!abierto) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (/^[0-9]$/.test(e.key)) {
        e.preventDefault();
        escribir(e.key);
      } else if (e.key === "Backspace") {
        e.preventDefault();
        borrar();
      } else if (e.key === "Enter") {
        e.preventDefault();
        aceptar();
      }
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  });

  return (
    <Hoja
      abierta={abierto}
      alCambiar={alCambiar}
      titulo={titulo}
      descripcion={descripcion}
      pie={
        <Boton variante="principal" disabled={!valido} onClick={aceptar}>
          Listo
        </Boton>
      }
    >
      <div className="mx-auto flex max-w-xs flex-col gap-4">
        <output
          aria-live="polite"
          aria-label="Cantidad"
          className="flex h-16 items-center justify-center rounded-xl border-2 border-primary bg-background text-4xl font-bold tabular-nums"
        >
          {texto === "" ? <span className="text-muted-foreground">0</span> : texto}
        </output>
        {!valido && texto !== "" ? (
          <p role="alert" className="text-center text-sm font-medium text-destructive">
            {valor < minimo ? `La cantidad mínima es ${minimo}.` : `La cantidad máxima es ${maximo}.`}
          </p>
        ) : null}
        <div className="grid grid-cols-3 gap-2">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
            <Boton key={d} variante="contorno" className="h-14 text-2xl font-semibold" onClick={() => escribir(d)}>
              {d}
            </Boton>
          ))}
          <Boton variante="contorno" className="h-14" aria-label="Borrar" onClick={borrar}>
            <DeleteIcon aria-hidden="true" className="size-6" />
          </Boton>
          <Boton variante="contorno" className="h-14 text-2xl font-semibold" onClick={() => escribir("0")}>
            0
          </Boton>
          <span aria-hidden="true" />
        </div>
      </div>
    </Hoja>
  );
}
