import { EyeIcon, EyeOffIcon, LockKeyholeIcon } from "lucide-react";
import { useState, type ComponentProps } from "react";

import { Campo } from "./campo";

type PropiedadesCampoClave = Omit<ComponentProps<typeof Campo>, "type" | "icono" | "alFinal"> & {
  /** Sin icono de candado junto a la etiqueta. */
  sinIcono?: boolean;
};

/** Campo de contraseña con candado junto a la etiqueta y un botón para ver u ocultar lo escrito. */
export function CampoClave({ sinIcono = false, ...props }: PropiedadesCampoClave) {
  const [visible, setVisible] = useState(false);
  return (
    <Campo
      {...props}
      type={visible ? "text" : "password"}
      icono={sinIcono ? undefined : <LockKeyholeIcon />}
      alFinal={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          aria-pressed={visible}
          className="flex size-10 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {visible ? <EyeOffIcon aria-hidden="true" className="size-5" /> : <EyeIcon aria-hidden="true" className="size-5" />}
        </button>
      }
    />
  );
}
