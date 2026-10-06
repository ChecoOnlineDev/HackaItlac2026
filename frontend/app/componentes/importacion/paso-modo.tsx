import { cn } from "cn";
import { CircleAlertIcon, DownloadIcon } from "lucide-react";
import { useId, useState } from "react";

import { descargarArchivo } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import type { ModoImportacion } from "./tipos";

interface PropiedadesPasoModo {
  modo: ModoImportacion;
  alCambiar: (modo: ModoImportacion) => void;
  alContinuar: () => void;
}

const MODOS: { valor: ModoImportacion; titulo: string; texto: string; datos: string }[] = [
  {
    valor: "ALTA",
    titulo: "Alta y carga inicial",
    texto: "Da de alta los artículos que todavía no existen y suma la cantidad a los que ya están en el catálogo.",
    datos: "Trae código o nombre, marca, categoría, cantidad y almacén.",
  },
  {
    valor: "REPOSICION",
    titulo: "Reposición de stock",
    texto: "Solo suma lo que llegó a artículos que ya existen. Nunca crea artículos nuevos: si un código no existe, esa fila se queda fuera.",
    datos: "Trae solo código, cantidad y almacén.",
  },
];

/**
 * Paso 1: qué se quiere hacer. Cada modo tiene su plantilla de Excel de ejemplo. Lo que cada modo hace con
 * cada fila lo decide el servidor; aquí solo se elige y se explica con palabras sencillas.
 */
export function PasoModo({ modo, alCambiar, alContinuar }: PropiedadesPasoModo) {
  const nombre = useId();
  const [bajando, setBajando] = useState(false);
  const [errorPlantilla, setErrorPlantilla] = useState<string | null>(null);

  const bajarPlantilla = async () => {
    setBajando(true);
    setErrorPlantilla(null);
    try {
      await descargarArchivo("/importacion/plantilla", { modo }, modo === "ALTA" ? "plantilla-alta.xlsx" : "plantilla-reposicion.xlsx");
    } catch (causa) {
      setErrorPlantilla(mensajeDeError(causa));
    } finally {
      setBajando(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-lg font-semibold">¿Qué quieres hacer?</legend>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {MODOS.map((m) => {
            const elegido = modo === m.valor;
            return (
              <label
                key={m.valor}
                className={cn(
                  "flex min-h-12 cursor-pointer flex-col gap-1 rounded-2xl border p-4 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                  elegido ? "border-2 border-primary bg-accent" : "hover:bg-accent/50",
                )}
              >
                <span className="flex items-center gap-3">
                  <input type="radio" name={nombre} value={m.valor} checked={elegido} onChange={() => alCambiar(m.valor)} className="size-6 shrink-0 accent-primary" />
                  <span className="text-base font-semibold">{m.titulo}</span>
                </span>
                <span className="pl-9 text-base">{m.texto}</span>
                <span className="pl-9 text-sm text-muted-foreground">{m.datos}</span>
              </label>
            );
          })}
        </div>
        <p className="text-sm text-muted-foreground">En los dos casos verás todo en una tabla antes de guardar. No se guarda nada hasta que confirmes.</p>
      </fieldset>

      <section aria-labelledby="plantilla-titulo" className="flex flex-col gap-2 rounded-2xl border p-4">
        <h2 id="plantilla-titulo" className="text-base font-semibold">
          ¿No sabes cómo armar el archivo?
        </h2>
        <p className="text-sm text-muted-foreground">
          Baja la plantilla de {modo === "ALTA" ? "alta" : "reposición"}: trae las columnas que el sistema reconoce, una fila de ejemplo y las instrucciones.
        </p>
        <Boton variante="contorno" className="self-start" cargando={bajando} onClick={() => void bajarPlantilla()}>
          <DownloadIcon aria-hidden="true" className={bajando ? "hidden" : undefined} />
          Descargar plantilla de {modo === "ALTA" ? "alta" : "reposición"}
        </Boton>
        {errorPlantilla ? (
          <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            {errorPlantilla}
          </p>
        ) : null}
      </section>

      <AccionPrincipal>
        <Boton variante="principal" onClick={alContinuar}>
          Continuar
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
