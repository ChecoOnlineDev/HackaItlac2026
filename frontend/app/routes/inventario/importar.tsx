import { Navigate } from "react-router";

/** Enlace anterior (`/importar`): ahora la carga desde Excel vive en «Dar entrada» (EK-04). */
export default function Importar() {
  return <Navigate to="/entrada?metodo=excel" replace />;
}
