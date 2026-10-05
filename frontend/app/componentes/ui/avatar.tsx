import { cn } from "cn";
import { useState } from "react";

const TAMANOS = {
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-16 text-xl",
} as const;

interface PropiedadesAvatar {
  nombre: string;
  /** Dirección de la foto, por ejemplo `/api/trabajadores/{id}/foto`. Sin foto, se muestran las iniciales. */
  fotoUrl?: string | null;
  tamano?: keyof typeof TAMANOS;
  className?: string;
}

export function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  const primera = partes[0][0];
  const segunda = partes.length > 1 ? partes[1][0] : "";
  return (primera + segunda).toUpperCase();
}

/** Iniciales del nombre, o su foto si la hay. */
export function Avatar({ nombre, fotoUrl, tamano = "md", className }: PropiedadesAvatar) {
  const [fallo, setFallo] = useState(false);
  const mostrarFoto = Boolean(fotoUrl) && !fallo;
  return (
    <span
      role="img"
      aria-label={nombre}
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-accent font-bold text-marino select-none",
        TAMANOS[tamano],
        className,
      )}
    >
      {mostrarFoto ? (
        <img src={fotoUrl!} alt="" className="size-full object-cover" onError={() => setFallo(true)} />
      ) : (
        <span aria-hidden="true">{iniciales(nombre)}</span>
      )}
    </span>
  );
}
