import { describe, expect, it } from "vitest";
import { validarOrigenServidor } from "./configuracion";

describe("OF-01 construcción por servidor", () => {
  it("acepta HTTPS y normaliza la barra final", () => {
    expect(validarOrigenServidor("https://imhotep.example/")).toBe("https://imhotep.example");
  });
  it.each([undefined, "http://example.com", "https://usuario:clave@example.com", "https://example.com/api", "https://example.com/?token=uno", "https://example.com/#uno"])(
    "rechaza un origen inseguro o ambiguo: %s", (valor) => expect(() => validarOrigenServidor(valor)).toThrow(),
  );
});
