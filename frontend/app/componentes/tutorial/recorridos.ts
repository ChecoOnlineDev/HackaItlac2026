import { CODIGOS_PRACTICA } from "~/api/practica";
import { EVENTO_ESCANEO_SIMULADO } from "~/componentes/dominio/escaner";
import type { Paso, Recorrido } from "./tipos";

/**
 * Guiones de los recorridos (FEAT-010, TU-04). Cada `ancla` es un `data-tutorial` que existe en el código de
 * la pantalla; si algún día falta, el motor omite el paso. El permiso es una clave `modulo.accion`, nunca un rol.
 */

/** «Escanear un ejemplo»: entrega el código ficticio al escáner que lleva esa ancla, como si se hubiera leído. */
function escanearEjemplo(ancla: string, codigo: string): NonNullable<Paso["accionSimulada"]> {
  return {
    etiqueta: "Escanear un ejemplo",
    ejecutar: () => {
      window.dispatchEvent(new CustomEvent(EVENTO_ESCANEO_SIMULADO, { detail: { ancla, codigo } }));
    },
  };
}

const rutaTraspaso = `/recibir/practica-traspaso`;

export const recorridos: Recorrido[] = [
  {
    id: "entregar",
    titulo: "Entregar",
    permiso: "entregas.crear",
    pasos: [
      {
        ancla: "entrega-escaner-trabajador",
        ruta: "/entregar",
        modo: "tocar",
        texto: "Primero identifica a quien recibe. Escanea su credencial o escribe su número.",
        accionSimulada: escanearEjemplo("entrega-escaner-trabajador", CODIGOS_PRACTICA.trabajador),
      },
      {
        ancla: "entrega-ficha-trabajador",
        modo: "leer",
        texto: "Aquí aparece la persona. En verde puede recibir; si saliera en rojo, no se le puede entregar.",
      },
      {
        ancla: "entrega-continuar",
        modo: "tocar",
        texto: "Cuando sea la persona correcta, toca «Continuar».",
      },
      {
        ancla: "entrega-escaner-articulos",
        modo: "tocar",
        texto: "Ahora escanea lo que se le entrega, una pieza o artículo a la vez.",
        accionSimulada: escanearEjemplo("entrega-escaner-articulos", CODIGOS_PRACTICA.articulo),
      },
      {
        ancla: "entrega-lista",
        modo: "leer",
        texto: "Cada renglón trae su color: verde se puede entregar, amarillo pide revisar y rojo no se puede entregar.",
      },
      {
        ancla: "entrega-continuar",
        modo: "tocar",
        texto: "Si la lista está bien, toca «Continuar».",
      },
      {
        ancla: "entrega-firma",
        modo: "tocar",
        texto: "Pide a la persona que firme en el recuadro con el dedo o el mouse. Al terminar el trazo, seguimos.",
        // Un toque sin trazo no firma: «Confirmar entrega» sigue deshabilitado hasta que haya firma.
        listo: () => document.querySelector('[data-tutorial="entrega-confirmar"]:not([disabled])') !== null,
      },
      {
        ancla: "entrega-confirmar",
        modo: "tocar",
        texto: "Toca «Confirmar entrega». En la práctica no se guarda nada de verdad.",
      },
      {
        ancla: "entrega-resultado",
        modo: "leer",
        texto: "Listo: este es el folio de práctica. En una entrega real, aquí queda el vale.",
      },
    ],
  },
  {
    id: "devolver",
    titulo: "Devolver",
    permiso: "devoluciones.crear",
    pasos: [
      {
        ancla: "devolver-escaner",
        ruta: "/devolver",
        modo: "tocar",
        texto: "Escanea la pieza que regresa. Se abona sola a quien la tenía.",
        accionSimulada: escanearEjemplo("devolver-escaner", CODIGOS_PRACTICA.pieza),
      },
      {
        ancla: "devolver-condicion",
        modo: "tocar",
        texto: "Elige cómo regresa: Bueno, Desgaste por uso o Dañado.",
      },
      {
        ancla: "devolver-confirmar",
        modo: "tocar",
        texto: "Toca «Confirmar devolución». En la práctica no se guarda nada de verdad.",
      },
      {
        ancla: "devolver-resultado",
        modo: "leer",
        texto: "Listo: este es el folio de práctica de la devolución.",
      },
    ],
  },
  {
    id: "consultar",
    titulo: "Consultar",
    pasos: [
      {
        ancla: "consultar-escaner",
        ruta: "/consultar",
        modo: "tocar",
        texto: "Escanea un código o escríbelo para saber quién tiene algo o qué tiene una persona.",
        accionSimulada: escanearEjemplo("consultar-escaner", CODIGOS_PRACTICA.trabajador),
      },
      {
        ancla: "consultar-ficha",
        modo: "leer",
        texto: "Aquí ves quién es, si está vigente y cuántas cosas tiene en resguardo.",
      },
      {
        ancla: "consultar-atajos",
        modo: "leer",
        texto: "Desde aquí pasas directo a la siguiente acción, por ejemplo entregarle o devolver lo que tiene.",
      },
    ],
  },
  {
    id: "recibir",
    titulo: "Recibir un traspaso",
    permiso: "traspasos.recibir",
    pasos: [
      {
        ancla: "recibir-lista",
        ruta: "/recibir",
        modo: "tocar",
        texto: "Aquí están los traspasos que vienen en camino. Toca uno para abrirlo.",
      },
      {
        ancla: "recibir-todo",
        ruta: rutaTraspaso,
        modo: "tocar",
        // El traspaso de práctica trae pocos renglones: «Recibir todo» no pide confirmación (solo la pide con más de 10).
        texto: "Si llegó todo, toca «Recibir todo». También puedes marcar cada renglón o escanear cada pieza.",
      },
      {
        ancla: "recibir-confirmar",
        modo: "tocar",
        texto: "Toca «Confirmar recepción». En la práctica no se guarda nada de verdad.",
      },
      {
        ancla: "recibir-resultado",
        modo: "leer",
        texto: "Listo: la recepción quedó registrada con su folio de práctica.",
      },
    ],
  },
];
