import { readFileSync } from "node:fs";
import { isValidElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { InsigniaEstadoCompra, InsigniaUrgencia } from "./insignias";

describe("insignias compartidas de Compras", () => {
  it.each(["solicitar/lista.tsx", "atender/lista.tsx"])("la vista %s importa la implementación común", (vista) => {
    const fuente = readFileSync(new URL(`./${vista}`, import.meta.url), "utf8");
    expect(fuente).toMatch(/import \{[^}]*InsigniaEstadoCompra[^}]*InsigniaUrgencia[^}]*\} from "~\/componentes\/compras\/insignias"/s);
  });

  it.each([
    ["PENDIENTE", "Pendiente", "neutra"],
    ["EN_COMPRA", "En compra", "info"],
    ["COMPRADA", "Comprada", "info"],
    ["INGRESADA", "Ingresada al almacén", "info"],
    ["RECHAZADA", "Rechazada", "neutra"],
    ["CANCELADA", "Cancelada", "neutra"],
  ] as const)("mantiene el texto, icono y estilo de estado %s", (estado, texto, nivel) => {
    const elemento = InsigniaEstadoCompra({ estado });
    expect(isValidElement(elemento)).toBe(true);
    expect(elemento.props.estado).toBe(nivel);
    const hijos = elemento.props.children as ReactNode[];
    expect(isValidElement(hijos[0])).toBe(true);
    expect(hijos[0]).toMatchObject({ props: { "aria-hidden": "true" } });
    expect(hijos[1]).toBe(texto);
  });

  it("muestra urgencia normal en gris y urgente en rojo con rayo", () => {
    const normal = InsigniaUrgencia({ urgencia: "NORMAL" });
    expect(normal.props).toMatchObject({ estado: "neutra", children: "Normal" });

    const urgente = InsigniaUrgencia({ urgencia: "URGENTE" });
    expect(urgente.props.className).toContain("text-destructive");
    const hijos = urgente.props.children as ReactNode[];
    expect(isValidElement(hijos[0])).toBe(true);
    expect(hijos[0]).toMatchObject({ props: { "aria-hidden": "true" } });
    expect(hijos[1]).toBe("Urgente");
  });
});
