import { Navigate, useSearchParams } from "react-router";
export { handle } from "./bitacora";
export default function RedireccionBitacora() { const [params] = useSearchParams(); const n = new URLSearchParams(params); n.set("vista", "renglones"); return <Navigate replace to={`/bitacora?${n}`} />; }
