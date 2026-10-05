import { InboxIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { ErrorApi } from "~/api/errores";
import { aviso } from "~/componentes/ui/aviso";
import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Cargando } from "~/componentes/ui/cargando";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { marcarConexion } from "~/api/red";

// Galería para revisar los componentes base. Solo existe fuera de producción (ver routes.ts).

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-b pb-8">
      <h2 className="text-xl">{titulo}</h2>
      {children}
    </section>
  );
}

export default function GaleriaComponentes() {
  const [hoja, setHoja] = useState(false);
  const [confirmacion, setConfirmacion] = useState(false);
  const [cargandoBoton, setCargandoBoton] = useState(false);
  const [pantalla, setPantalla] = useState(false);

  if (pantalla) {
    return (
      <div onClick={() => setPantalla(false)} className="cursor-pointer">
        <Cargando variante="pantalla" texto="Toca para cerrar" />
      </div>
    );
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-6">
      <header>
        <h1>Componentes base</h1>
        <p className="text-muted-foreground">Solo en desarrollo. Revisa cada uno en celular (375 px) y en computadora.</p>
      </header>

      <Seccion titulo="Cargando">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border">
            <Cargando variante="en-linea" texto="Cargando trabajadores" />
          </div>
          <div className="flex items-center justify-center rounded-xl border p-6">
            <Boton variante="normal" cargando>
              Guardando
            </Boton>
          </div>
        </div>
        <Boton variante="contorno" onClick={() => setPantalla(true)}>
          Ver variante pantalla completa
        </Boton>
      </Seccion>

      <Seccion titulo="Esqueleto">
        <Esqueleto tipo="lista" cantidad={2} />
        <Esqueleto tipo="tarjeta" cantidad={2} />
        <Esqueleto tipo="tabla" cantidad={3} />
      </Seccion>

      <Seccion titulo="Estado vacío y error">
        <EstadoVacio
          icono={InboxIcon}
          titulo="No hay traspasos por recibir"
          descripcion="Cuando otro almacén te envíe algo, aparecerá aquí."
          accion={<Boton variante="secundario">Consultar</Boton>}
        />
        <EstadoError error={new ErrorApi(500, { codigo: "ERROR", mensaje: "No pudimos cargar los trabajadores.", detalles: null })} alReintentar={() => aviso({ titulo: "Reintentando", tipo: "info" })} />
      </Seccion>

      <Seccion titulo="Botones">
        <Boton variante="principal">Confirmar entrega</Boton>
        <Boton variante="principal" cargando={cargandoBoton} onClick={() => { setCargandoBoton(true); window.setTimeout(() => setCargandoBoton(false), 2500); }}>
          Probar estado cargando
        </Boton>
        <Boton variante="principal" disabled>
          Continuar (deshabilitado)
        </Boton>
        <div className="flex flex-wrap gap-3">
          <Boton variante="normal">Normal</Boton>
          <Boton variante="secundario">Secundario</Boton>
          <Boton variante="contorno">Contorno</Boton>
          <Boton variante="texto">Texto</Boton>
          <Boton variante="peligro">Peligro</Boton>
        </div>
      </Seccion>

      <Seccion titulo="Campo">
        <Campo etiqueta="Número de empleado" placeholder="Ej. 10458" ayuda="Lo encuentras en la credencial." />
        <Campo etiqueta="Nombre" defaultValue="" error="Escribe el nombre completo." />
      </Seccion>

      <Seccion titulo="Avatar e insignias">
        <div className="flex items-center gap-4">
          <Avatar nombre="María Fernanda López" tamano="sm" />
          <Avatar nombre="María Fernanda López" />
          <Avatar nombre="Juan Pérez" tamano="lg" />
          <Avatar nombre="Con foto rota" fotoUrl="/no-existe.jpg" />
        </div>
        <div className="flex flex-wrap gap-2">
          <Insignia estado="verde" />
          <Insignia estado="amarillo" />
          <Insignia estado="naranja" />
          <Insignia estado="rojo" />
          <Insignia estado="neutra">En tránsito</Insignia>
          <Insignia estado="info">Activo</Insignia>
        </div>
      </Seccion>

      <Seccion titulo="Aviso, hoja, confirmación y conexión">
        <div className="flex flex-wrap gap-3">
          <Boton onClick={() => aviso({ titulo: "Se agregó Casco blanco", accion: { etiqueta: "Deshacer", alHacerClic: () => aviso({ titulo: "Renglón quitado", tipo: "info" }) } })}>
            Aviso con Deshacer
          </Boton>
          <Boton onClick={() => aviso({ titulo: "Cambio guardado", descripcion: "Aplica desde la siguiente entrega.", tipo: "exito" })}>Aviso de éxito</Boton>
          <Boton onClick={() => aviso({ titulo: "Falta una observación", tipo: "aviso" })}>Aviso de advertencia</Boton>
          <Boton onClick={() => setHoja(true)}>Abrir hoja</Boton>
          <Boton onClick={() => setConfirmacion(true)}>Abrir confirmación</Boton>
          <Boton onClick={() => marcarConexion(false)}>Simular sin conexión</Boton>
          <Boton onClick={() => marcarConexion(true)}>Restablecer conexión</Boton>
        </div>
      </Seccion>

      <Hoja
        abierta={hoja}
        alCambiar={setHoja}
        titulo="Observación"
        descripcion="Explica por qué se entrega más de lo habitual."
        pie={
          <Boton variante="principal" onClick={() => setHoja(false)}>
            Guardar observación
          </Boton>
        }
      >
        <Campo etiqueta="Motivo" placeholder="Escribe el motivo" />
      </Hoja>
      <Confirmacion
        abierta={confirmacion}
        alCambiar={setConfirmacion}
        mensaje="¿Entregar 10 pares de guantes?"
        alConfirmar={() => setConfirmacion(false)}
      />
    </main>
  );
}
