import { Campo } from "~/componentes/ui/campo";
import { CampoEntero, FilaInterruptor } from "./campos";
import type { Control, Reglas } from "./tipos";

/** Las reglas tal como se editan en pantalla: textos para los números y interruptores para lo opcional. */
export interface EstadoReglas {
  inspeccion: boolean;
  vigencia: string;
  autorizacion: boolean;
  motivo: string;
  limite: boolean;
  limiteCantidad: string;
  /** Vacío significa "en posesión". */
  limitePeriodo: string;
  aviso: boolean;
  cantidadAviso: string;
}

export const REGLAS_VACIAS: EstadoReglas = {
  inspeccion: false,
  vigencia: "",
  autorizacion: false,
  motivo: "",
  limite: false,
  limiteCantidad: "",
  limitePeriodo: "",
  aviso: false,
  cantidadAviso: "",
};

const texto = (n: number | null) => (n === null || n === undefined ? "" : String(n));

export function reglasAEstado(r: Reglas): EstadoReglas {
  return {
    inspeccion: r.requiere_inspeccion,
    vigencia: texto(r.vigencia_inspeccion_dias),
    autorizacion: r.requiere_autorizacion,
    motivo: r.motivo_uso_especial ?? "",
    limite: r.limite_cantidad !== null,
    limiteCantidad: texto(r.limite_cantidad),
    limitePeriodo: texto(r.limite_periodo_dias),
    aviso: r.cantidad_aviso !== null,
    cantidadAviso: texto(r.cantidad_aviso),
  };
}

const entero = (valor: string): number | null => {
  const n = Number(valor);
  return valor.trim() !== "" && Number.isInteger(n) && n > 0 ? n : null;
};

/** Lo que se manda al servidor. Una regla apagada va en `null`. */
export function estadoAReglas(e: EstadoReglas): Reglas {
  return {
    requiere_inspeccion: e.inspeccion,
    vigencia_inspeccion_dias: e.inspeccion ? entero(e.vigencia) : null,
    requiere_autorizacion: e.autorizacion,
    motivo_uso_especial: e.autorizacion || e.inspeccion ? e.motivo.trim() || null : null,
    limite_cantidad: e.limite ? entero(e.limiteCantidad) : null,
    limite_periodo_dias: e.limite ? entero(e.limitePeriodo) : null,
    cantidad_aviso: e.aviso ? entero(e.cantidadAviso) : null,
  };
}

/** Revisa lo que se puede revisar sin preguntar al servidor. El servidor vuelve a validar todo. */
export function validarReglas(e: EstadoReglas, control: Control): Record<string, string> {
  const errores: Record<string, string> = {};
  if (e.inspeccion && control !== "PIEZA") {
    errores.requiere_inspeccion = "La inspección solo aplica a artículos que se controlan por pieza.";
  }
  if (e.inspeccion && e.vigencia.trim() !== "" && entero(e.vigencia) === null) {
    errores.vigencia_inspeccion_dias = "Escribe un número de días mayor que cero.";
  }
  if (e.limite) {
    if (entero(e.limiteCantidad) === null) errores.limite_cantidad = "Escribe cuántas piezas como máximo.";
    if (e.limitePeriodo.trim() !== "" && entero(e.limitePeriodo) === null) {
      errores.limite_periodo_dias = "Escribe un número de días mayor que cero, o déjalo vacío.";
    }
  }
  if (e.aviso && entero(e.cantidadAviso) === null) {
    errores.cantidad_aviso = "Escribe desde qué cantidad se avisa.";
  }
  return errores;
}

interface PropiedadesFormularioReglas {
  valor: EstadoReglas;
  alCambiar: (valor: EstadoReglas) => void;
  control: Control;
  errores: Record<string, string>;
  /** Introducción de la sección, por ejemplo "Estas reglas se copian a los artículos nuevos." */
  deshabilitado?: boolean;
}

/** Interruptores de las reglas de entrega: los usan la plantilla de la categoría y el artículo. */
export function FormularioReglas({ valor, alCambiar, control, errores, deshabilitado }: PropiedadesFormularioReglas) {
  const cambiar = (parcial: Partial<EstadoReglas>) => alCambiar({ ...valor, ...parcial });
  return (
    <div className="flex flex-col gap-3">
      <FilaInterruptor
        titulo="Inspección vigente"
        ayuda={
          control === "PIEZA"
            ? "No se entrega una pieza sin inspección al día."
            : "Solo aplica a artículos por pieza."
        }
        activo={valor.inspeccion}
        alCambiar={(inspeccion) => cambiar({ inspeccion })}
        disabled={deshabilitado}
      >
        <CampoEntero
          etiqueta="Días de vigencia"
          ayuda="Si lo dejas vacío, se usan 180 días."
          value={valor.vigencia}
          onChange={(e) => cambiar({ vigencia: e.target.value })}
          error={errores.vigencia_inspeccion_dias}
        />
      </FilaInterruptor>
      {errores.requiere_inspeccion ? (
        <p role="alert" className="-mt-1 text-sm font-medium text-destructive">
          {errores.requiere_inspeccion}
        </p>
      ) : null}

      <FilaInterruptor
        titulo="Autorización del supervisor"
        ayuda="Cada entrega espera el visto bueno del supervisor."
        activo={valor.autorizacion}
        alCambiar={(autorizacion) => cambiar({ autorizacion })}
        disabled={deshabilitado}
      />

      {valor.autorizacion || valor.inspeccion ? (
        <Campo
          etiqueta="Motivo corto"
          ayuda="Lo ve el almacenista al escanear, por ejemplo “Equipo de alturas”."
          maxLength={255}
          value={valor.motivo}
          onChange={(e) => cambiar({ motivo: e.target.value })}
          error={errores.motivo_uso_especial}
          disabled={deshabilitado}
        />
      ) : null}

      <FilaInterruptor
        titulo="Límite por trabajador"
        ayuda="Cuántas piezas puede tener o recibir cada trabajador."
        activo={valor.limite}
        alCambiar={(limite) => cambiar({ limite })}
        disabled={deshabilitado}
      >
        <CampoEntero
          etiqueta="Cantidad máxima"
          value={valor.limiteCantidad}
          onChange={(e) => cambiar({ limiteCantidad: e.target.value })}
          error={errores.limite_cantidad}
        />
        <CampoEntero
          etiqueta="Cada cuántos días"
          ayuda="Si lo dejas vacío, el límite cuenta lo que el trabajador tiene en su poder."
          value={valor.limitePeriodo}
          onChange={(e) => cambiar({ limitePeriodo: e.target.value })}
          error={errores.limite_periodo_dias}
        />
      </FilaInterruptor>

      <FilaInterruptor
        titulo="Aviso de cantidad inusual"
        ayuda="Pide confirmar cuando un renglón llega a esta cantidad."
        activo={valor.aviso}
        alCambiar={(aviso) => cambiar({ aviso })}
        disabled={deshabilitado}
      >
        <CampoEntero
          etiqueta="Avisar desde"
          value={valor.cantidadAviso}
          onChange={(e) => cambiar({ cantidadAviso: e.target.value })}
          error={errores.cantidad_aviso}
        />
      </FilaInterruptor>
    </div>
  );
}
