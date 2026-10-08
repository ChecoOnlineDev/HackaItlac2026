import { Navigate } from "react-router";

/** Enlace anterior (`/entradas/nueva`): ahora la entrada manual vive en «Dar entrada» (EK-04). */
export default function EntradaNueva() {
  return <Navigate to="/entrada?metodo=mano" replace />;
}
