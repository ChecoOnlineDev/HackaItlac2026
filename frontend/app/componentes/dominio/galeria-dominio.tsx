import { useRef, useState, type ReactNode } from "react";

import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { ConfirmarCantidad } from "./confirmar-cantidad";
import { Escaner, type ManejadorEscaner, type OrigenLectura } from "./escaner";
import { FichaTrabajador, type DatosFichaTrabajador } from "./ficha-trabajador";
import { FirmaPad } from "./firma-pad";
import { CodigoQR, FolioQR } from "./codigo-qr";
import { HojaEtiquetas } from "./hoja-etiquetas";
import { HojaObservacion } from "./hoja-observacion";
import { ListaRenglones } from "./lista-renglones";
import { RangoDeFechas, type RangoFechas } from "./rango-de-fechas";
import { RenglonSemaforo } from "./renglon-semaforo";
import { reproducir } from "./sonido";
import type { RenglonEvaluado } from "./tipos";
import { ValeImprimible, type ValeDetalle } from "./vale-imprimible";
import { hoyMexico } from "./fechas";

// Datos de ejemplo y secciones de la galería `/dev/componentes` para los componentes de dominio.

const base = {
  pieza: null,
  titular: null,
  disponible: null,
  pide_observacion: false,
  autorizable: false,
  requiere_confirmacion: false,
} satisfies Partial<RenglonEvaluado>;

export const RENGLONES_EJEMPLO: RenglonEvaluado[] = [
  {
    ...base,
    renglon: 1,
    codigo: "ALT-021",
    articulo: { id: "a1", nombre: "Arnés de seguridad", marca: "3M", talla: "M", control: "PIEZA" },
    pieza: { id: "p1", estado: "APTO", inspeccion_vigente_hasta: "2027-03-31", numero_serie: "AR-88231" },
    cantidad: 1,
    nivel: "VERDE",
    motivos: [],
  },
  {
    ...base,
    renglon: 2,
    codigo: "EPP-GUA-01",
    articulo: { id: "a2", nombre: "Guantes de carnaza", marca: "Truper", control: "CANTIDAD" },
    cantidad: 10,
    disponible: 140,
    nivel: "AMARILLO",
    requiere_confirmacion: true,
    pide_observacion: true,
    motivos: [
      { regla: "E-27", nivel: "AMARILLO", mensaje: "Es una cantidad mayor a la habitual." },
      { regla: "E-19", nivel: "AMARILLO", mensaje: "Pide una observación para entregarse." },
    ],
  },
  {
    ...base,
    renglon: 3,
    codigo: "EPP-CAS-02",
    articulo: { id: "a3", nombre: "Casco blanco", marca: "MSA", control: "CANTIDAD" },
    cantidad: 2,
    disponible: 30,
    nivel: "NARANJA",
    autorizable: true,
    motivos: [{ regla: "E-10", nivel: "NARANJA", mensaje: "Ya recibió un casco hace 12 días; el límite es uno cada 180." }],
  },
  {
    ...base,
    renglon: 4,
    codigo: "ALT-024",
    articulo: { id: "a4", nombre: "Arnés poliéster", marca: "Honeywell", talla: "L", control: "PIEZA" },
    pieza: { id: "p4", estado: "APTO", inspeccion_vigente_hasta: "2026-09-30", numero_serie: "AR-11902" },
    titular: "Juan Pérez Soto",
    cantidad: 1,
    nivel: "ROJO",
    motivos: [
      { regla: "E-06", nivel: "ROJO", mensaje: "Inspección vencida el 30/09/2026." },
      { regla: "E-03", nivel: "ROJO", mensaje: "La pieza la tiene otra persona." },
    ],
  },
  {
    ...base,
    renglon: 5,
    codigo: "XYZ-999",
    articulo: null,
    cantidad: 1,
    nivel: "ROJO",
    motivos: [{ regla: "E-01", nivel: "ROJO", mensaje: "No encontramos este código." }],
  },
];

const FICHA_VIGENTE: DatosFichaTrabajador = {
  id: "t1",
  numero_empleado: "TRB-1001",
  nombre: "María Fernanda López Hernández",
  puesto: "Soldadora",
  area_obra: "Patio 3",
  vigencia: { vigente: true, motivo: null, regla: "T-02" },
  tiene_foto: false,
  foto_url: null,
  periodo: { inicio: "2026-03-01", fin: "2026-12-31" },
  resguardo: [
    { articulo: "Arnés de seguridad", codigo: "ALT-021", numero_serie: "AR-88231", cantidad: 1, folio: "KEP-ENT-000123", de_periodo_anterior: false },
    { articulo: "Esmeriladora 4 1/2\"", codigo: "HER-007", cantidad: 1, folio: "KEP-ENT-000130", de_periodo_anterior: true },
  ],
};
const FICHA_NO_VIGENTE: DatosFichaTrabajador = {
  ...FICHA_VIGENTE,
  id: "t2",
  numero_empleado: "TRB-1015",
  nombre: "Juan Pérez Soto",
  puesto: "Ayudante general",
  vigencia: { vigente: false, motivo: "Su contrato terminó el 30/09/2026.", regla: "E-02" },
  tiene_foto: false,
  periodo: { inicio: "2026-01-01", fin: "2026-09-30" },
  resguardo: [],
};

const FIRMA_EJEMPLO =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 120"><path d="M20 90 C40 20 60 20 70 80 S100 30 120 70 S160 100 190 40 S230 30 280 60" fill="none" stroke="#0a0a0a" stroke-width="4" stroke-linecap="round"/></svg>',
  );

export const VALE_EJEMPLO: ValeDetalle = {
  folio: "KEP-ENT-000123",
  tipo: "ENTREGA",
  creado_en: "2026-10-05T20:32:00Z",
  token: "tok_ejemplo_0123456789abcdef",
  almacen: { clave: "KEP", nombre: "Almacén Kepler" },
  trabajador: { nombre: "María Fernanda López Hernández", numero_empleado: "TRB-1001", puesto: "Soldadora", area_obra: "Patio 3" },
  responsable: { nombre: "Carlos Almacenista" },
  autorizacion: { autorizado_por: { nombre: "Ana Supervisora" }, motivo: "Reposición por casco dañado" },
  observacion: null,
  firma: { imagen: FIRMA_EJEMPLO },
  renglones: [
    { renglon: 1, articulo: { nombre: "Arnés de seguridad", marca: "3M", talla: "M" }, codigo: "ALT-021", numero_serie: "AR-88231", cantidad: 1, condicion: "BUENO" },
    { renglon: 2, articulo: { nombre: "Guantes de carnaza", marca: "Truper" }, codigo: "EPP-GUA-01", cantidad: 10, condicion: "BUENO" },
    { renglon: 3, articulo: { nombre: "Casco blanco", marca: "MSA" }, codigo: "EPP-CAS-02", cantidad: 2, condicion: "BUENO" },
  ],
};

const ETIQUETAS_EJEMPLO = [
  { codigo: "TRB-1001", texto: "María Fernanda López Hernández" },
  { codigo: "TRB-1002", texto: "Juan Pérez Soto" },
  { codigo: "ALT-021", texto: "Arnés de seguridad 3M talla M" },
  { codigo: "ALT-022", texto: "Arnés de seguridad 3M talla L" },
  { codigo: "EPP-CAS-02", texto: "Casco blanco MSA (estante B-2)" },
  { codigo: "EPP-GUA-01", texto: "Guantes de carnaza Truper, par" },
];

/** Con `?solo=vale` (o escaner, renglon, lista, ficha, firma, qr, fechas, etiquetas) la galería muestra solo esa sección. */
function Seccion({ id, titulo, nota, children }: { id: string; titulo: string; nota?: string; children: ReactNode }) {
  const solo = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("solo");
  if (solo && solo !== id) return null;
  return (
    <section id={id} className="flex flex-col gap-3 border-b pb-8">
      <h2 className="text-xl">{titulo}</h2>
      {nota ? <p className="text-sm text-muted-foreground">{nota}</p> : null}
      {children}
    </section>
  );
}

/** Todas las secciones de la galería para los componentes de dominio. */
export function SeccionesDominio() {
  const [lecturas, setLecturas] = useState<{ codigo: string; origen: OrigenLectura }[]>([]);
  const [repetidos, setRepetidos] = useState(0);
  const [activo, setActivo] = useState(true);
  const manejador = useRef<ManejadorEscaner>(null);

  const [renglones, setRenglones] = useState<RenglonEvaluado[]>(RENGLONES_EJEMPLO.slice(0, 3));
  const [autorizado, setAutorizado] = useState(false);
  const [observacion, setObservacion] = useState<string | null>(null);
  const [hojaObs, setHojaObs] = useState(false);
  const [confirmar, setConfirmar] = useState(false);

  const [firma, setFirma] = useState<{ vacia: boolean; imagen: string | null; puntos: number }>({ vacia: true, imagen: null, puntos: 0 });
  const [rango, setRango] = useState<RangoFechas>({ desde: hoyMexico(), hasta: hoyMexico() });
  const [valeCancelado, setValeCancelado] = useState(false);

  const agregarSiguiente = () => {
    const usados = new Set(renglones.map((r) => r.codigo));
    const siguiente = RENGLONES_EJEMPLO.find((r) => !usados.has(r.codigo));
    if (siguiente) setRenglones((prev) => [...prev, siguiente]);
    else aviso({ titulo: "Ya están todos los renglones de ejemplo", tipo: "info" });
  };

  const vale: ValeDetalle = valeCancelado
    ? { ...VALE_EJEMPLO, cancelacion: { motivo: "Se entregó a la persona equivocada.", folio: "KEP-CAN-000007" } }
    : VALE_EJEMPLO;

  return (
    <>
      <Seccion
        id="escaner"
        titulo="Escáner"
        nota="Cámara (solo en navegadores con BarcodeDetector), pistola (teclea una ráfaga rápida terminada en Enter sin tener un campo con foco) y teclado."
      >
        <Escaner
          ref={manejador}
          activo={activo}
          onCodigo={(codigo, origen) => setLecturas((l) => [{ codigo, origen }, ...l].slice(0, 5))}
          onRepetido={() => {
            setRepetidos((n) => n + 1);
            reproducir("aviso");
          }}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Boton variante="contorno" onClick={() => setActivo((a) => !a)}>
            {activo ? "Apagar escáner" : "Encender escáner"}
          </Boton>
          <Boton variante="contorno" onClick={() => reproducir("ok")}>Sonido: correcto</Boton>
          <Boton variante="contorno" onClick={() => reproducir("aviso")}>Sonido: aviso</Boton>
          <Boton variante="contorno" onClick={() => reproducir("bloqueo")}>Sonido: bloqueo</Boton>
        </div>
        <div className="rounded-xl border p-3 text-sm" data-testid="lecturas">
          <p className="font-semibold">Últimas lecturas (repetidas ignoradas: {repetidos})</p>
          {lecturas.length === 0 ? (
            <p className="text-muted-foreground">Todavía no hay lecturas.</p>
          ) : (
            <ul>
              {lecturas.map((l, i) => (
                <li key={`${l.codigo}-${i}`}>
                  {l.codigo} <span className="text-muted-foreground">({l.origen})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Seccion>

      <Seccion id="renglon" titulo="Renglón con semáforo" nota="Los cuatro niveles, un código desconocido, un renglón autorizado y uno con la cantidad editable.">
        <div className="flex flex-col gap-3">
          {RENGLONES_EJEMPLO.map((r) => (
            <RenglonSemaforo
              key={r.codigo}
              renglon={r}
              onQuitar={() => aviso({ titulo: `Quitar ${r.codigo}`, tipo: "info" })}
              onPedirAutorizacion={() => aviso({ titulo: `Pedir autorización de ${r.codigo}`, tipo: "info" })}
              onCantidad={(n) => aviso({ titulo: `Cantidad de ${r.codigo}: ${n}`, tipo: "info" })}
            />
          ))}
          <RenglonSemaforo
            renglon={{ ...RENGLONES_EJEMPLO[2], cantidad: 1 }}
            estadoAutorizacion="autorizado"
            onCantidad={() => {}}
            onQuitar={() => {}}
          />
          <RenglonSemaforo
            renglon={{ ...RENGLONES_EJEMPLO[2], cantidad: 1 }}
            estadoAutorizacion="en_espera"
            onQuitar={() => {}}
          />
          <RenglonSemaforo renglon={RENGLONES_EJEMPLO[1]} resaltado nota="Cambió desde la última revisión; revísalo." onQuitar={() => {}} />
        </div>
      </Seccion>

      <Seccion id="lista" titulo="Lista de renglones" nota="Agrega renglones: entran con una transición corta, quedan resaltados y avisan «Se agregó…» con Deshacer 5 segundos.">
        <div className="flex flex-wrap gap-3">
          <Boton variante="normal" onClick={agregarSiguiente}>Agregar un renglón</Boton>
          <Boton variante="contorno" onClick={() => setRenglones([])}>Vaciar</Boton>
        </div>
        <ListaRenglones
          renglones={renglones}
          onQuitar={(r) => setRenglones((l) => l.filter((x) => x.codigo !== r.codigo))}
          onCantidad={(r, n) => setRenglones((l) => l.map((x) => (x.codigo === r.codigo ? { ...x, cantidad: n } : x)))}
          onPedirAutorizacion={() => setAutorizado(true)}
          onObservacion={() => setHojaObs(true)}
          estadoAutorizacion={(r) => (r.nivel === "NARANJA" && autorizado ? "autorizado" : null)}
          observacionDe={(r) => (r.pide_observacion ? observacion : null)}
          vacio={<p className="rounded-xl border p-6 text-center text-muted-foreground">Escanea un artículo para empezar.</p>}
        />
        <div className="flex flex-wrap gap-3">
          <Boton variante="contorno" onClick={() => setConfirmar(true)}>Probar «Confirmar cantidad»</Boton>
        </div>
        <HojaObservacion
          abierta={hojaObs}
          alCambiar={setHojaObs}
          motivo="Pide una observación para entregarse."
          regla="E-19"
          valorInicial={observacion ?? ""}
          respuestasRapidas={["Cuadrilla nueva", "Reposición por desgaste", "Obra con más personal"]}
          alGuardar={(t) => setObservacion(t)}
        />
        <ConfirmarCantidad
          abierta={confirmar}
          alCambiar={setConfirmar}
          cantidad={10}
          unidad="pares de"
          articulo="guantes"
          alConfirmar={() => {
            setConfirmar(false);
            aviso({ titulo: "Cantidad confirmada", tipo: "exito" });
          }}
          alCorregir={() => aviso({ titulo: "Corrige la cantidad", tipo: "info" })}
        />
      </Seccion>

      <Seccion id="ficha" titulo="Ficha del trabajador">
        <FichaTrabajador trabajador={FICHA_VIGENTE} />
        <FichaTrabajador trabajador={FICHA_NO_VIGENTE} />
        <FichaTrabajador trabajador={FICHA_VIGENTE} variante="reducida" />
        <FichaTrabajador trabajador={{ ...FICHA_VIGENTE, tiene_foto: true, foto_url: "/logo-imhotep.png", resguardo: [] }} variante="reducida" />
        <FichaTrabajador trabajador={FICHA_NO_VIGENTE} variante="reducida" />
      </Seccion>

      <Seccion id="firma" titulo="Firma">
        <FirmaPad onCambio={(vacia, imagen, trazo) => setFirma({ vacia, imagen, puntos: trazo.reduce((s, t) => s + t.length, 0) })} />
        <p className="text-sm" data-testid="estado-firma">
          {firma.vacia ? "Firma vacía." : `Firma lista (${firma.puntos} puntos).`}
        </p>
        {firma.imagen ? <img src={firma.imagen} alt="Vista de la firma exportada" className="max-w-xs rounded-lg border" /> : null}
      </Seccion>

      <Seccion id="qr" titulo="Código QR y folio">
        <div className="flex flex-wrap items-start gap-8">
          <CodigoQR valor="ALT-024" tamano={128} />
          <CodigoQR valor="TRB-1001" tamano={256} />
          <FolioQR folio="KEP-ENT-000123" valor="https://ejemplo.mx/v/tok_ejemplo" texto="Vale de entrega · 05/10/2026 14:32" />
        </div>
      </Seccion>

      <Seccion id="fechas" titulo="Rango de fechas">
        <div className="flex flex-wrap items-center gap-3">
          <RangoDeFechas valor={rango} onCambio={setRango} />
          <p className="text-sm" data-testid="rango">
            {rango.desde} a {rango.hasta}
          </p>
        </div>
      </Seccion>

      <Seccion id="vale" titulo="Vale imprimible" nota="Al imprimir (Ctrl+P) solo sale el documento, en hoja carta.">
        <Boton variante="contorno" className="w-fit" onClick={() => setValeCancelado((v) => !v)}>
          {valeCancelado ? "Ver vale vigente" : "Ver vale cancelado"}
        </Boton>
        <ValeImprimible vale={vale} />
      </Seccion>

      <Seccion id="etiquetas" titulo="Hoja de etiquetas">
        <HojaEtiquetas etiquetas={ETIQUETAS_EJEMPLO} />
      </Seccion>
    </>
  );
}
