import { LockKeyholeIcon } from "lucide-react";
import { Link } from "react-router";

import { buttonVariants } from "~/components/ui/button";

/** Estado transversal "Sin permisos": regreso al inicio. */
export function SinPermiso() {
  return (
    <div role="alert" className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
      <LockKeyholeIcon aria-hidden="true" className="size-10 text-marino" />
      <h1>Tu rol no puede hacer esto</h1>
      <p className="text-muted-foreground">Si crees que debería poder, pídeselo a tu supervisor.</p>
      <Link to="/" className={buttonVariants({ size: "principal" })}>
        Ir al inicio
      </Link>
    </div>
  );
}
