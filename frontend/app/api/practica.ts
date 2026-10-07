// Capa de práctica del tutorial guiado (FEAT-010, TU-02, TU-06, TU-07).
//
// Mientras la práctica está activa, el cliente de la API (`cliente.ts`, función `pedir`) NO llama a la red:
// responde desde aquí con un trabajador y unos artículos ficticios. Las pantallas reales no saben que están
// en práctica. Lo que no se contempla aquí (lectura o escritura) responde un error controlado y tampoco sale.
//
// Reglas de esta capa:
// - Estado a nivel de módulo, sin React.
// - Los datos van tipados con los mismos tipos del cliente para no desviarse de las respuestas reales.
// - La única excepción que deja pasar a la red NO existe: la sesión se responde con la última que el
//   cliente tuvo en memoria (`recordarSesionPractica`). Si nunca hubo una (no puede pasar con el tutorial
//   encendido desde una pantalla con sesión), `/sesion` responde un error controlado, no sale.
//
// Códigos de práctica (los que usan los guiones; también están en `CODIGOS_PRACTICA`):
//   Trabajador ........ EMP-0000  (Juan Práctica, vigente, con un arnés y unos guantes en resguardo)
//   Artículo verde .... PRA-CASCO (Casco de práctica, por cantidad)   · también PRA-GUANTES
//   Pieza ............. PRA-ARNES-01 (Arnés de práctica, en resguardo de Juan; sirve para devolver)
//   Traspaso .......... token PRACTICATRASPASO000001 · folio TR-PRACTICA-0001 (trae casco, guantes y PRA-ARNES-02)

import type { OpcionesApi } from "./cliente";
import type { Sesion } from "./tipos";
import type {
  AlmacenResumen,
  DotacionApi,
  EvaluacionApi,
  ValeConfirmadoApi,
  ValeDetalleApi,
} from "~/componentes/entrega/tipos";
import type { Busqueda, Escaneo, FichaArticulo, FichaPieza } from "~/componentes/consulta/tipos";
import type { MotivoRegla, NivelSemaforo, RenglonEvaluado } from "~/componentes/dominio/tipos";
import type { Ficha, Pendiente } from "~/componentes/personas/tipos";
import type { AlmacenRedApi, PorRecibirApi, TraspasoPorRecibirApi } from "~/componentes/traspasos/tipos";

// ------------------------------------------------------------------------------------------ interruptor

let activa = false;
let sesionEnMemoria: Sesion | null = null;
let contadorFolio = 0;
const valesDePractica = new Map<string, ValeDetalleApi>();
const valesPorCliente = new Map<string, ValeConfirmadoApi>();

export function activarPractica(): void {
  activa = true;
  contadorFolio = 0;
  valesDePractica.clear();
  valesPorCliente.clear();
}

export function desactivarPractica(): void {
  activa = false;
  contadorFolio = 0;
  valesDePractica.clear();
  valesPorCliente.clear();
}

export function practicaActiva(): boolean {
  return activa;
}

/** El cliente de la API avisa aquí de cada sesión que recibe, para poder responderla sin red en práctica. */
export function recordarSesionPractica(sesion: Sesion): void {
  if (!activa) sesionEnMemoria = sesion;
}

// ------------------------------------------------------------------------------------------ datos ficticios

export const CODIGOS_PRACTICA = {
  trabajador: "EMP-0000",
  articulo: "PRA-CASCO",
  articulo2: "PRA-GUANTES",
  pieza: "PRA-ARNES-01",
  piezaTraspaso: "PRA-ARNES-02",
  /** Token del vale de traspaso (22 caracteres, como el de un QR real). */
  traspaso: "PRACTICATRASPASO000001",
  traspasoFolio: "TR-PRACTICA-0001",
} as const;

const ID = {
  trabajador: "practica-trabajador",
  casco: "practica-articulo-casco",
  guantes: "practica-articulo-guantes",
  arnes: "practica-articulo-arnes",
  pieza1: "practica-pieza-arnes-01",
  pieza2: "practica-pieza-arnes-02",
  traspaso: "practica-traspaso",
  origen: "practica-almacen-origen",
  almacen: "practica-almacen",
} as const;

const ALMACEN_PRACTICA: AlmacenResumen = { id: ID.almacen, clave: "PRA", nombre: "Almacén de práctica" };
const ALMACEN_ORIGEN: AlmacenResumen = { id: ID.origen, clave: "ORI", nombre: "Almacén de origen (práctica)" };

interface ArticuloPractica {
  id: string;
  codigo: string;
  nombre: string;
  marca: string;
  control: "PIEZA" | "CANTIDAD";
  categoria: string;
  unidad: string;
}

const ARTICULOS: ArticuloPractica[] = [
  { id: ID.casco, codigo: CODIGOS_PRACTICA.articulo, nombre: "Casco de práctica", marca: "Ejemplo", control: "CANTIDAD", categoria: "EPP", unidad: "pieza" },
  { id: ID.guantes, codigo: CODIGOS_PRACTICA.articulo2, nombre: "Guantes de práctica", marca: "Ejemplo", control: "CANTIDAD", categoria: "EPP", unidad: "par" },
  { id: ID.arnes, codigo: "PRA-ARNES", nombre: "Arnés de práctica", marca: "Ejemplo", control: "PIEZA", categoria: "Equipo de altura", unidad: "pieza" },
];

interface PiezaPractica {
  id: string;
  codigo: string;
  articulo: ArticuloPractica;
  serie: string;
  /** `trabajador`: la tiene Juan. `transito`: viene en el traspaso. */
  donde: "trabajador" | "transito";
}

const PIEZAS: PiezaPractica[] = [
  { id: ID.pieza1, codigo: CODIGOS_PRACTICA.pieza, articulo: ARTICULOS[2], serie: "SER-PRA-001", donde: "trabajador" },
  { id: ID.pieza2, codigo: CODIGOS_PRACTICA.piezaTraspaso, articulo: ARTICULOS[2], serie: "SER-PRA-002", donde: "transito" },
];

const clave = (codigo: string) => codigo.trim().toUpperCase();
const sinAcentos = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
const articuloPorCodigo = (c: string) => ARTICULOS.find((a) => clave(a.codigo) === clave(c));
const piezaPorCodigo = (c: string) => PIEZAS.find((p) => clave(p.codigo) === clave(c));
const esTrabajador = (c: string) => [CODIGOS_PRACTICA.trabajador, "0000", ID.trabajador.toUpperCase()].includes(clave(c));

function diaIso(desplazamientoDias: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + desplazamientoDias);
  return d.toISOString().slice(0, 10);
}
const ahoraIso = () => new Date().toISOString();

function almacenActual(): AlmacenResumen {
  const a = sesionEnMemoria?.almacen;
  return a ? { id: a.id, clave: a.clave, nombre: a.nombre } : ALMACEN_PRACTICA;
}

function pendiente(articulo: ArticuloPractica, pieza: PiezaPractica | null, cantidad: number): Pendiente {
  return {
    articulo_id: articulo.id,
    articulo: articulo.nombre,
    control: articulo.control,
    pieza_id: pieza?.id ?? null,
    codigo: pieza?.codigo ?? articulo.codigo,
    numero_serie: pieza?.serie ?? null,
    cantidad,
    entregado_en: ahoraIso(),
    vale_id: null,
    folio: "PRACTICA-0000",
    almacen_id: almacenActual().id,
    almacen_clave: almacenActual().clave,
    almacen: almacenActual().nombre,
    de_periodo_anterior: false,
  };
}

function fichaTrabajador(): Ficha {
  return {
    id: ID.trabajador,
    numero_empleado: "EMP-0000",
    nombre: "Juan Práctica",
    estado: "ACTIVO",
    estado_texto: "Activo",
    puesto: "Soldador",
    puesto_id: null,
    area_obra: "Taller de práctica",
    vigencia: { vigente: true, motivo: null, regla: "E-02" },
    tiene_foto: false,
    foto_url: null,
    resguardo: [pendiente(ARTICULOS[2], PIEZAS[0], 1), pendiente(ARTICULOS[1], null, 2)],
    pendientes: { total: 2, de_periodos_anteriores: 0, regla: null },
    periodo: { id: "practica-periodo", puesto: "Soldador", area_obra: "Taller de práctica", referencia: null, inicio: diaIso(-180), fin: diaIso(180), creado_en: ahoraIso() },
    situacion: "CON_PENDIENTES",
    situacion_texto: "Con pendientes",
    tallas: null,
    codigos: ["EMP-0000"],
  };
}

function dotacion(): DotacionApi {
  return {
    puesto: { id: "practica-puesto", nombre: "Soldador" },
    renglones: [
      { articulo: { id: ID.casco, codigo: CODIGOS_PRACTICA.articulo, nombre: "Casco de práctica", unidad: "pieza", control: "CANTIDAD" }, recomendada: 1, entregada: 0, falta: 1 },
      { articulo: { id: ID.guantes, codigo: CODIGOS_PRACTICA.articulo2, nombre: "Guantes de práctica", unidad: "par", control: "CANTIDAD" }, recomendada: 2, entregada: 2, falta: 0 },
    ],
  };
}

function traspaso(): TraspasoPorRecibirApi {
  const destino = almacenActual();
  return {
    id: ID.traspaso,
    folio: CODIGOS_PRACTICA.traspasoFolio,
    token: CODIGOS_PRACTICA.traspaso,
    estado: "EN_TRANSITO",
    origen: ALMACEN_ORIGEN,
    destino,
    envio: { id: "practica-envia", nombre: "Ana Práctica" },
    creado_en: ahoraIso(),
    pendiente_total: 9,
    renglones: [
      { renglon: 1, articulo_id: ID.casco, articulo: "Casco de práctica", marca: "Ejemplo", modelo: null, talla: null, codigo: CODIGOS_PRACTICA.articulo, pieza_id: null, numero_serie: null, cantidad_enviada: 5, cantidad_recibida: 0, cantidad_pendiente: 5 },
      { renglon: 2, articulo_id: ID.guantes, articulo: "Guantes de práctica", marca: "Ejemplo", modelo: null, talla: null, codigo: CODIGOS_PRACTICA.articulo2, pieza_id: null, numero_serie: null, cantidad_enviada: 3, cantidad_recibida: 0, cantidad_pendiente: 3 },
      { renglon: 3, articulo_id: ID.arnes, articulo: "Arnés de práctica", marca: "Ejemplo", modelo: null, talla: null, codigo: CODIGOS_PRACTICA.piezaTraspaso, pieza_id: ID.pieza2, numero_serie: "SER-PRA-002", cantidad_enviada: 1, cantidad_recibida: 0, cantidad_pendiente: 1 },
    ],
    recepciones: [],
  };
}

function valeDelTraspaso(): ValeDetalleApi {
  const t = traspaso();
  return {
    id: t.id,
    folio: t.folio,
    token: t.token,
    tipo: "TRASPASO",
    estado: "EN_TRANSITO",
    almacen: t.origen,
    destino_almacen: t.destino,
    trabajador: null,
    responsable: t.envio,
    observacion: null,
    firma_modo: null,
    tiene_firma: false,
    valido: null,
    vale_origen_id: null,
    vale_origen_folio: null,
    dispositivo: null,
    creado_en: t.creado_en,
    renglones: t.renglones.map((r) => ({
      renglon: r.renglon,
      articulo_id: r.articulo_id,
      articulo: r.articulo,
      marca: r.marca,
      modelo: r.modelo,
      talla: r.talla,
      codigo_articulo: ARTICULOS.find((a) => a.id === r.articulo_id)?.codigo ?? r.codigo,
      pieza_id: r.pieza_id,
      codigo_pieza: r.pieza_id ? r.codigo : null,
      numero_serie: r.numero_serie,
      cantidad: r.cantidad_enviada,
      condicion: null,
      nivel: "VERDE",
      reglas: [],
      observacion: null,
    })),
  };
}

// ------------------------------------------------------------------------------------------ evaluación

const ORDEN: NivelSemaforo[] = ["VERDE", "AMARILLO", "NARANJA", "ROJO"];
const peor = (niveles: NivelSemaforo[]): NivelSemaforo => niveles.reduce((a, n) => (ORDEN.indexOf(n) > ORDEN.indexOf(a) ? n : a), "VERDE" as NivelSemaforo);

interface CuerpoPractica {
  tipo?: string;
  almacen_id?: string | null;
  trabajador_id?: string;
  id_cliente?: string;
  renglones?: { codigo: string; cantidad: number; condicion?: string; observacion?: string }[];
}

function renglonEvaluado(r: NonNullable<CuerpoPractica["renglones"]>[number], i: number, tipo: string): RenglonEvaluado {
  const base = { renglon: i + 1, codigo: r.codigo, cantidad: r.cantidad, pide_observacion: false, autorizable: false, requiere_confirmacion: false };
  const rojo = (regla: string, mensaje: string, extra: Partial<RenglonEvaluado> = {}): RenglonEvaluado => ({
    ...base, articulo: null, pieza: null, titular: null, disponible: null, nivel: "ROJO", motivos: [{ regla, nivel: "ROJO", mensaje }], ...extra,
  });
  const verde = (extra: Partial<RenglonEvaluado>): RenglonEvaluado => ({
    ...base, articulo: null, pieza: null, titular: null, disponible: null, nivel: "VERDE", motivos: [], ...extra,
  });
  const arte = (a: ArticuloPractica) => ({ id: a.id, nombre: a.nombre, marca: a.marca, talla: null, control: a.control, codigo: a.codigo, modelo: null, unidad: a.unidad, retornable: true, activo: true });

  const pieza = piezaPorCodigo(r.codigo);
  if (pieza) {
    const articulo = arte(pieza.articulo);
    const datosPieza = { id: pieza.id, estado: "DISPONIBLE", inspeccion_vigente_hasta: diaIso(90), numero_serie: pieza.serie, serie_pendiente: false };
    if (tipo === "DEVOLUCION" && pieza.donde === "trabajador") return verde({ articulo, pieza: datosPieza, titular: "Juan Práctica", cantidad: 1 });
    if (tipo === "RECEPCION" && pieza.donde === "transito") return verde({ articulo, pieza: datosPieza, titular: null, cantidad: 1 });
    if (tipo === "RECEPCION") return rojo("X-12", "Esta pieza no pertenece a este traspaso.", { articulo, pieza: datosPieza });
    const donde = pieza.donde === "trabajador" ? "la tiene Juan Práctica" : "viene en camino en un traspaso";
    return rojo("E-03", `Esta pieza no está en el almacén: ${donde}.`, { articulo, pieza: datosPieza, titular: pieza.donde === "trabajador" ? "Juan Práctica" : null });
  }
  const articulo = articuloPorCodigo(r.codigo);
  if (articulo && articulo.control === "CANTIDAD") {
    return verde({ articulo: arte(articulo), disponible: 50 });
  }
  if (tipo === "RECEPCION") return rojo("X-12", "Esto no pertenece a este traspaso.");
  return rojo("E-01", "Ese código no existe en el catálogo.");
}

function evaluar(cuerpo: CuerpoPractica): EvaluacionApi {
  const tipo = cuerpo.tipo ?? "ENTREGA";
  const renglones = (cuerpo.renglones ?? []).map((r, i) => renglonEvaluado(r, i, tipo));
  const nivel = peor(renglones.map((r) => r.nivel));
  const motivos: MotivoRegla[] = [];
  const quiereTrabajador = tipo === "ENTREGA" || tipo === "DEVOLUCION";
  const trabajador = quiereTrabajador && cuerpo.trabajador_id && esTrabajador(cuerpo.trabajador_id) ? fichaTrabajador() : null;
  return {
    nivel,
    puede_confirmar: renglones.length > 0 && nivel !== "ROJO",
    motivos,
    almacen: almacenActual(),
    trabajador,
    pide_observacion: false,
    autorizacion_error: null,
    renglones,
  };
}

// ------------------------------------------------------------------------------------------ confirmación

function confirmar(cuerpo: CuerpoPractica): { estado: number; cuerpo: unknown } {
  const previo = cuerpo.id_cliente ? valesPorCliente.get(cuerpo.id_cliente) : undefined;
  if (previo) return { estado: 200, cuerpo: previo };

  const ev = evaluar(cuerpo);
  if (!ev.puede_confirmar) {
    return {
      estado: 409,
      cuerpo: { codigo: "VALE_CAMBIO", mensaje: "La lista cambió. Revísala antes de confirmar.", detalles: ev },
    };
  }
  contadorFolio += 1;
  const n = String(contadorFolio).padStart(4, "0");
  const id = `practica-vale-${n}`;
  const creado = ahoraIso();
  const tipo = (cuerpo.tipo ?? "ENTREGA") as ValeDetalleApi["tipo"];
  const vale: ValeConfirmadoApi = {
    id,
    folio: `PRACTICA-${n}`,
    token: `PRACTICAVALE${n}`.padEnd(22, "0"),
    creado_en: creado,
    renglones: ev.renglones.map((r) => ({ renglon: r.renglon, codigo: r.codigo, articulo: r.articulo?.nombre ?? r.codigo, cantidad: r.cantidad, nivel: r.nivel, reglas: r.motivos.map((m) => m.regla) })),
  };
  valesPorCliente.set(cuerpo.id_cliente ?? id, vale);
  valesDePractica.set(id, {
    id,
    folio: vale.folio,
    token: vale.token,
    tipo,
    estado: "EMITIDO",
    almacen: ev.almacen,
    destino_almacen: null,
    trabajador: ev.trabajador ? { id: ev.trabajador.id, numero_empleado: ev.trabajador.numero_empleado, nombre: ev.trabajador.nombre, puesto: ev.trabajador.puesto, area_obra: ev.trabajador.area_obra } : null,
    responsable: { id: sesionEnMemoria?.usuario.id ?? "practica-usuario", nombre: sesionEnMemoria?.usuario.nombre ?? "Tú (práctica)" },
    observacion: null,
    firma_modo: tipo === "ENTREGA" ? "PANTALLA" : "SESION",
    tiene_firma: false,
    valido: null,
    vale_origen_id: tipo === "RECEPCION" ? ID.traspaso : null,
    vale_origen_folio: tipo === "RECEPCION" ? CODIGOS_PRACTICA.traspasoFolio : null,
    dispositivo: null,
    creado_en: creado,
    renglones: ev.renglones.map((r) => ({
      renglon: r.renglon,
      articulo_id: r.articulo?.id ?? "",
      articulo: r.articulo?.nombre ?? r.codigo,
      marca: r.articulo?.marca ?? null,
      modelo: null,
      talla: null,
      codigo_articulo: r.articulo?.codigo ?? r.codigo,
      pieza_id: r.pieza?.id ?? null,
      codigo_pieza: r.pieza?.id ? r.codigo : null,
      numero_serie: r.pieza?.numero_serie ?? null,
      cantidad: r.cantidad,
      condicion: cuerpo.renglones?.[r.renglon - 1]?.condicion ?? null,
      nivel: r.nivel,
      reglas: r.motivos.map((m) => m.regla),
      observacion: cuerpo.renglones?.[r.renglon - 1]?.observacion ?? null,
    })),
  });
  return { estado: 201, cuerpo: vale };
}

// ------------------------------------------------------------------------------------------ lecturas

function escanear(codigo: string): Escaneo {
  if (esTrabajador(codigo)) {
    const f = fichaTrabajador();
    return { tipo: "TRABAJADOR", id: f.id, resumen: { numero_empleado: f.numero_empleado, nombre: f.nombre, estado: f.estado, estado_texto: f.estado_texto, vigente: true, motivo_no_vigente: null, puesto: f.puesto, area_obra: f.area_obra, vigente_hasta: f.periodo?.fin ?? null, pendientes: f.resguardo.length } };
  }
  const pieza = piezaPorCodigo(codigo);
  if (pieza) {
    return { tipo: "PIEZA", id: pieza.id, resumen: { codigo: pieza.codigo, numero_serie: pieza.serie, articulo_id: pieza.articulo.id, articulo: pieza.articulo.nombre, estado: "DISPONIBLE", estado_texto: "Disponible", inspeccion_vigente_hasta: diaIso(90), inspeccion_vigente: true, ubicacion: ubicacionDe(pieza) } };
  }
  const articulo = articuloPorCodigo(codigo);
  if (articulo) {
    return { tipo: "ARTICULO", id: articulo.id, resumen: { codigo: articulo.codigo, nombre: articulo.nombre, marca: articulo.marca, categoria: articulo.categoria, control: articulo.control, retornable: true, unidad: articulo.unidad, activo: true, existencia_total: 50 } };
  }
  return { tipo: "DESCONOCIDO", id: null, resumen: { mensaje: "No reconocemos ese código." } };
}

function ubicacionDe(p: PiezaPractica) {
  return p.donde === "trabajador"
    ? { tipo: "TRABAJADOR", texto: "Juan Práctica", almacen_id: null, almacen_clave: null, trabajador_id: ID.trabajador, numero_empleado: "EMP-0000", virtual: null }
    : { tipo: "VIRTUAL", texto: "En camino", almacen_id: null, almacen_clave: null, trabajador_id: null, numero_empleado: null, virtual: "TRANSITO" };
}

function buscar(q: string): Busqueda {
  const t = sinAcentos(q);
  const f = fichaTrabajador();
  const articulos = ARTICULOS.filter((a) => sinAcentos(`${a.nombre} ${a.codigo}`).includes(t)).map((a) => ({ id: a.id, codigo: a.codigo, nombre: a.nombre, marca: a.marca, categoria: a.categoria, control: a.control, activo: true }));
  const piezas = PIEZAS.filter((p) => sinAcentos(`${p.articulo.nombre} ${p.codigo} ${p.serie}`).includes(t)).map((p) => ({ id: p.id, codigo: p.codigo, numero_serie: p.serie, articulo_id: p.articulo.id, articulo: p.articulo.nombre, estado: "DISPONIBLE", estado_texto: "Disponible", ubicacion: ubicacionDe(p).texto }));
  const trabajadores = sinAcentos(`${f.nombre} ${f.numero_empleado}`).includes(t) ? [{ id: f.id, numero_empleado: f.numero_empleado, nombre: f.nombre, estado: f.estado, estado_texto: f.estado_texto }] : [];
  const sin = articulos.length + piezas.length + trabajadores.length === 0;
  return {
    q,
    articulos: { elementos: articulos, total: articulos.length },
    piezas: { elementos: piezas, total: piezas.length },
    trabajadores: { elementos: trabajadores, total: trabajadores.length },
    sin_resultados: sin,
    mensaje: sin ? "No encontramos nada con ese texto." : null,
  };
}

function fichaPieza(p: PiezaPractica): FichaPieza {
  return {
    id: p.id, codigo: p.codigo, numero_serie: p.serie, serie_pendiente: false, estado: "DISPONIBLE", estado_texto: "Disponible",
    articulo: { id: p.articulo.id, codigo: p.articulo.codigo, nombre: p.articulo.nombre, marca: p.articulo.marca, modelo: null, talla: null, unidad: p.articulo.unidad, requiere_inspeccion: true, vigencia_inspeccion_dias: 180 },
    inspeccion_vigente_hasta: diaIso(90), inspeccion_vigente: true, ultima_inspeccion: null, ubicacion: ubicacionDe(p), historial: [],
  };
}

function fichaArticulo(a: ArticuloPractica): FichaArticulo {
  return {
    id: a.id, codigo: a.codigo, nombre: a.nombre, marca: a.marca, modelo: null, categoria_id: "practica-categoria", categoria_nombre: a.categoria,
    control: a.control, retornable: true, talla: null, unidad: a.unidad, requiere_inspeccion: false, requiere_autorizacion: false, activo: true,
    motivo_inactivacion: null, vigencia_inspeccion_dias: null, motivo_uso_especial: null, limite_cantidad: null, limite_periodo_dias: null,
    cantidad_aviso: null, tiene_movimientos: true,
    existencias: [{ almacen_id: almacenActual().id, clave: almacenActual().clave, nombre: almacenActual().nombre, cantidad: 50, disponible: 50 }],
    en_posesion: [],
  };
}

// ------------------------------------------------------------------------------------------ enrutador

type Resultado = { estado: number; cuerpo: unknown };

function noDisponible(metodo: string): Resultado {
  return {
    estado: 400,
    cuerpo: {
      codigo: "PRACTICA_NO_DISPONIBLE",
      mensaje: metodo === "GET" ? "Esto no está disponible mientras practicas." : "Esto no se puede hacer mientras practicas. Nada se guarda.",
      detalles: null,
    },
  };
}

const ok = (cuerpo: unknown): Resultado => ({ estado: 200, cuerpo });
const noExiste = (): Resultado => ({ estado: 404, cuerpo: { codigo: "NO_ENCONTRADO", mensaje: "No encontramos eso en la práctica.", detalles: null } });

function enrutar(ruta: string, metodo: string, cuerpo: unknown, parametros: OpcionesApi["parametros"]): Resultado {
  const sinConsulta = ruta.split("?")[0];
  const limpia = sinConsulta.replace(/^\/api(?=\/|$)/, "");
  const partes = limpia.split("/").filter(Boolean).map((p) => decodeURIComponent(p));
  const [a, b, c] = partes;

  if (metodo === "GET") {
    if (a === "sesion" && partes.length === 1) return sesionEnMemoria ? ok(sesionEnMemoria) : noDisponible(metodo);
    if (a === "escaneo" && b) return ok(escanear(b));
    if (a === "busqueda") return ok(buscar(String(parametros?.q ?? "")));
    if (a === "traspasos" && b === "por-recibir") {
      const lista: PorRecibirApi = { total: 1, elementos: [traspaso()] };
      return ok(lista);
    }
    if (a === "vales" && b === "por-token" && c) {
      if (c === CODIGOS_PRACTICA.traspaso) return ok(valeDelTraspaso());
      const v = [...valesDePractica.values()].find((x) => x.token === c);
      return v ? ok(v) : noExiste();
    }
    if (a === "vales" && b && partes.length === 2) {
      if (b === ID.traspaso) return ok(valeDelTraspaso());
      const v = valesDePractica.get(b);
      return v ? ok(v) : noExiste();
    }
    if (a === "trabajadores" && b && esTrabajador(b)) {
      if (c === "dotacion") return ok(dotacion());
      if (partes.length === 2) return ok(fichaTrabajador());
    }
    if (a === "piezas" && b && partes.length === 2) {
      const p = PIEZAS.find((x) => x.id === b);
      return p ? ok(fichaPieza(p)) : noExiste();
    }
    if (a === "articulos" && b && partes.length === 2) {
      const art = ARTICULOS.find((x) => x.id === b);
      return art ? ok(fichaArticulo(art)) : noExiste();
    }
    if (a === "almacenes") {
      const lista: AlmacenRedApi[] = [almacenActual(), ALMACEN_ORIGEN].map((x) => ({ ...x, tipo: "ALMACEN", estado: "ACTIVO", padre_id: null, padre_clave: null, hijos: [] }));
      return ok(lista);
    }
    return noDisponible(metodo);
  }

  if (metodo === "POST") {
    if (a === "sesion" && b === "refresh") return sesionEnMemoria ? ok(sesionEnMemoria) : noDisponible(metodo);
    if (a === "vales" && b === "evaluar") return ok(evaluar((cuerpo ?? {}) as CuerpoPractica));
    if (a === "vales" && partes.length === 1) return confirmar((cuerpo ?? {}) as CuerpoPractica);
  }
  // Cualquier otra escritura (y todo lo demás): error controlado. NUNCA sale a la red.
  return noDisponible(metodo);
}

/**
 * Responde una petición del cliente de la API sin red. Devuelve un `Response` real (con JSON) para que
 * `cliente.ts` lo procese igual que una respuesta del servidor, errores incluidos.
 */
export function responderPractica(ruta: string, opciones: OpcionesApi): Response {
  const metodo = opciones.metodo ?? "GET";
  const r = enrutar(ruta, metodo, opciones.cuerpo, opciones.parametros);
  return new Response(JSON.stringify(r.cuerpo), { status: r.estado, headers: { "Content-Type": "application/json" } });
}
