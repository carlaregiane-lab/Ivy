import assert from "node:assert/strict";
import test from "node:test";
import { calculateEngineering } from "../lib/engineering/calculations.ts";

test("calcula força com conversão de massa", () => {
  const output = calculateEngineering({
    calculation: "forceFromMass",
    mass: { value: 1_500, unit: "g" },
    acceleration: { value: 9.81, unit: "m/s2" },
    outputUnit: "N",
  });

  assert.equal(output.result.value, 14.715);
  assert.equal(output.result.unit, "N");
});

test("calcula pressão convertendo milímetros quadrados para metros quadrados", () => {
  const output = calculateEngineering({
    calculation: "pressureFromForce",
    force: { value: 1_000, unit: "N" },
    area: { value: 100, unit: "mm2" },
    outputUnit: "MPa",
  });

  assert.equal(output.result.value, 10);
  assert.equal(output.result.unit, "MPa");
});

test("calcula força linear idealizada de um fuso", () => {
  const output = calculateEngineering({
    calculation: "leadScrewLinearForce",
    torque: { value: 2, unit: "N.m" },
    lead: { value: 5, unit: "mm" },
    efficiency: 0.8,
    outputUnit: "N",
  });

  assert.ok(Math.abs(output.result.value - 2_010.62) < 0.01);
  assert.equal(output.warnings.length, 1);
});

test("sinaliza fator de segurança abaixo da demanda", () => {
  const output = calculateEngineering({
    calculation: "safetyFactor",
    capacity: 800,
    demand: 1_000,
  });

  assert.equal(output.result.value, 0.8);
  assert.match(output.warnings[0], /menor que a demanda/i);
});

test("calcula velocidade linear em milímetros por segundo", () => {
  const output = calculateEngineering({
    calculation: "linearSpeed",
    distance: { value: 300, unit: "mm" },
    time: { value: 2, unit: "s" },
    outputUnit: "mm/s",
  });

  assert.equal(output.result.value, 150);
  assert.equal(output.result.unit, "mm/s");
});
