import { cn } from "cn";
import { CameraIcon, ImageOffIcon, TrashIcon } from "lucide-react";
import { useRef, useState } from "react";

import { RenglonSemaforo } from "~/componentes/dominio/renglon-semaforo";
import type { Condicion, NivelSemaforo, RenglonEvaluado } from "~/componentes/dominio/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import type { RenglonDevolucionBorrador } from "./borrador";
import { ControlCondicion } from "./control-condicion";

interface PropiedadesRenglonDevolucion {
  local: RenglonDevolucionBorrador;
  /** Lo que respondió el servidor para este renglón; `null` mientras se revisa. */
  evaluado: RenglonEvaluado | null;
  /** Lo máximo que se puede devolver de este artículo (lo que el trabajador tiene en resguardo). */
  cantidadMaxima?: number;
  nota?: string;
  deshabilitado?: boolean;
  alCondicion: (condicion: Condicion) => void;
  alCantidad: (cantidad: number) => void;
  alQuitar: () => void;
  alObservacion: () => void;
  /** Recibe la foto elegida; la pantalla la reduce y la guarda. `null` la quita. */
  alFoto: (archivo: File | null) => Promise<void>;
}

/** Textos del semáforo propios de la devolución (el de la entrega dice "No se puede entregar"). */
function textosDe(evaluado: RenglonEvaluado): Partial<Record<NivelSemaforo, string>> {
  const reglas = new Set(evaluado.motivos.map((m) => m.regla));
  const rojo = reglas.has("V-12")
    ? "No es de la empresa"
    : reglas.has("V-04")
      ? "Falta elegir cómo regresa"
      : "No se puede recibir";
  return { VERDE: "Listo", AMARILLO: "Aviso", NARANJA: "Requiere autorización", ROJO: rojo };
}

/**
 * Un renglón de la devolución: el renglón con semáforo del servidor y, debajo, los tres botones de
 * condición (y, si es Dañado, la foto). Los renglones que no generan movimiento (código ajeno, pieza que
 * no está en resguardo) no llevan condición. No decide nada: pinta lo que evaluó el servidor.
 */
export function RenglonDevolucion({
  local,
  evaluado,
  cantidadMaxima,
  nota,
  deshabilitado = false,
  alCondicion,
  alCantidad,
  alQuitar,
  alObservacion,
  alFoto,
}: PropiedadesRenglonDevolucion) {
  const entradaFoto = useRef<HTMLInputElement>(null);
  const [procesando, setProcesando] = useState(false);
  const [falloFoto, setFalloFoto] = useState(false);

  if (!evaluado) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-dashed bg-muted p-3 text-base">
        <Cargando variante="en-linea" texto={`Revisando ${local.codigo}…`} className="justify-start p-0" />
        <Boton variante="texto" disabled={deshabilitado} onClick={alQuitar} aria-label={`Quitar ${local.codigo}`}>
          <TrashIcon aria-hidden="true" />
          Quitar
        </Boton>
      </div>
    );
  }

  const reglas = new Set(evaluado.motivos.map((m) => m.regla));
  const conMovimiento = evaluado.articulo !== null && !reglas.has("V-12") && !reglas.has("V-14") && !reglas.has("V-02");
  const danado = local.condicion === "DANADO";

  const elegirFoto = async (archivo: File | null) => {
    setFalloFoto(false);
    setProcesando(true);
    try {
      await alFoto(archivo);
    } catch {
      setFalloFoto(true);
    } finally {
      setProcesando(false);
      if (entradaFoto.current) entradaFoto.current.value = "";
    }
  };

  return (
    <div className="flex flex-col">
      <RenglonSemaforo
        // La lista de resguardo del trabajador ya dice cuánto tiene: aquí no se repite como "Hay N".
        renglon={{ ...evaluado, cantidad: local.cantidad, disponible: null }}
        textos={textosDe(evaluado)}
        observacion={local.observacion}
        nota={nota}
        deshabilitado={deshabilitado}
        cantidadMaxima={cantidadMaxima}
        onQuitar={alQuitar}
        onCantidad={evaluado.articulo?.control === "CANTIDAD" && conMovimiento ? alCantidad : undefined}
        onObservacion={evaluado.pide_observacion ? alObservacion : undefined}
        className={cn(conMovimiento && "rounded-b-none border-b-0")}
      />
      {conMovimiento ? (
        <div className="flex flex-col gap-3 rounded-b-xl border border-t-0 bg-card p-3">
          <ControlCondicion valor={local.condicion} alCambiar={alCondicion} deshabilitado={deshabilitado} />
          {danado ? (
            <div className="flex flex-col gap-2">
              {local.foto ? (
                <div className="flex items-center gap-3">
                  <img src={local.foto} alt="Foto del daño" className="size-20 rounded-lg border object-cover" />
                  <Boton variante="texto" disabled={deshabilitado || procesando} onClick={() => void elegirFoto(null)}>
                    <ImageOffIcon aria-hidden="true" />
                    Quitar foto
                  </Boton>
                </div>
              ) : null}
              <input
                ref={entradaFoto}
                type="file"
                accept="image/*"
                capture="environment"
                className="sr-only"
                tabIndex={-1}
                aria-label="Foto del daño"
                onChange={(e) => {
                  const archivo = e.target.files?.[0];
                  if (archivo) void elegirFoto(archivo);
                }}
              />
              <Boton
                variante="contorno"
                className="self-start"
                cargando={procesando}
                disabled={deshabilitado}
                onClick={() => entradaFoto.current?.click()}
              >
                <CameraIcon aria-hidden="true" />
                {local.foto ? "Cambiar foto" : "Agregar foto del daño"}
              </Boton>
              {!local.foto ? <p className="text-sm text-muted-foreground">La foto es opcional; ayuda a revisar el daño después.</p> : null}
              {falloFoto ? (
                <p role="alert" className="text-sm font-semibold text-destructive">
                  No pudimos usar esa imagen. Prueba con otra foto.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
