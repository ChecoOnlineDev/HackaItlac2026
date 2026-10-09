import { describe, expect, it } from "vitest";
import {
  DURACION_BLOQUEO_MS,
  ITERACIONES_PIN_LOCAL,
  crearDerivacionPinLocal,
  nuevoEstadoIntentosPin,
  pinLocalEstaBloqueado,
  registrarAciertoPinLocal,
  registrarFalloPinLocal,
  verificarPinLocal,
} from "./credencial-local";

const hoy = new Date("2026-10-09T12:00:00.000Z");

describe("credencial local FEAT-020", () => {
  it("OF-06 deriva el PIN con PBKDF2-SHA256 y una sal aleatoria", async () => {
    const primera = await crearDerivacionPinLocal("284739", { hoy });
    const segunda = await crearDerivacionPinLocal("284739", { hoy });

    expect(primera.algoritmo).toBe("PBKDF2-SHA256");
    expect(primera.iteraciones).toBe(ITERACIONES_PIN_LOCAL);
    expect(primera.iteraciones).toBeGreaterThanOrEqual(600_000);
    expect(primera.sal).not.toBe(segunda.sal);
    expect(primera.verificador).not.toContain("284739");
    await expect(verificarPinLocal("284739", primera)).resolves.toBe(true);
    await expect(verificarPinLocal("284738", primera)).resolves.toBe(false);
  });

  it("OF-06 rechaza PIN inválido, secuencias y fecha de hoy", async () => {
    for (const pin of ["12345", "1234567", "123456", "654321", "000000", "111111", "091026", "261009", "100926"]) {
      await expect(crearDerivacionPinLocal(pin, { hoy })).rejects.toThrow();
    }
  });

  it("OF-07 bloquea cinco errores durante cinco minutos y permite reintentar al vencer", () => {
    const inicio = nuevoEstadoIntentosPin();
    let estado = inicio;
    for (let intento = 1; intento <= 5; intento += 1) estado = registrarFalloPinLocal(estado, 10_000 * intento);

    expect(estado.fallosConsecutivos).toBe(5);
    expect(estado.bloqueadaHasta).toBe(50_000 + DURACION_BLOQUEO_MS);
    expect(pinLocalEstaBloqueado(estado, 50_000 + DURACION_BLOQUEO_MS - 1)).toBe(true);
    expect(pinLocalEstaBloqueado(estado, 50_000 + DURACION_BLOQUEO_MS)).toBe(false);
    expect(registrarFalloPinLocal(estado, 50_001).fallosConsecutivos).toBe(5);
    expect(registrarFalloPinLocal(estado, 50_000 + DURACION_BLOQUEO_MS).fallosConsecutivos).toBe(6);
  });

  it("OF-07 elimina la credencial al décimo error seguido y reinicia al acertar", () => {
    let estado = nuevoEstadoIntentosPin();
    for (let intento = 1; intento <= 5; intento += 1) estado = registrarFalloPinLocal(estado, intento);
    const vence = estado.bloqueadaHasta!;
    for (let intento = 6; intento <= 10; intento += 1) {
      estado = registrarFalloPinLocal(estado, vence + (intento - 5) * (DURACION_BLOQUEO_MS + 1));
    }

    expect(estado.debeBorrarCredencial).toBe(true);
    expect(pinLocalEstaBloqueado(estado, Number.MAX_SAFE_INTEGER)).toBe(true);
    expect(registrarAciertoPinLocal()).toEqual(nuevoEstadoIntentosPin());
  });
});
