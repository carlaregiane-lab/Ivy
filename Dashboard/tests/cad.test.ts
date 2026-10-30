import assert from "node:assert/strict";
import test from "node:test";
import { createActuatorCad } from "../lib/cad/actuator-cad.ts";
import { generateActuatorStl } from "../lib/cad/stl.ts";

const model = createActuatorCad({
  projectName: "Atuador linear vertical",
  payloadKg: 12,
  travelMm: 300,
  screwLeadMm: 8,
  motorVoltage: 24,
  targetTimeS: 12,
});

test("gera um conceito paramétrico com os dados do atuador", () => {
  assert.equal(model.modelId, "ACT-300-120");
  assert.equal(model.parameters.travelMm, 300);
  assert.equal(model.parameters.overallHeightMm, 480);
  assert.equal(model.parts.length, 6);
  assert.match(model.downloadUrl, /^\/api\/cad\/actuator\?/);
  assert.equal(model.maturity, "concept");
});

test("exporta uma malha STL ASCII válida e não vazia", () => {
  const stl = generateActuatorStl(model);
  assert.match(stl, /^solid ACT-300-120/);
  assert.match(stl, /facet normal/);
  assert.match(stl, /endsolid ACT-300-120\n$/);
  assert.ok((stl.match(/facet normal/g) ?? []).length > 100);
});

test("reflete as pré-seleções no CAD paramétrico", () => {
  const sizedModel = createActuatorCad({
    projectName: "Atuador linear vertical",
    payloadKg: 12,
    travelMm: 300,
    screwLeadMm: 8,
    motorVoltage: 24,
    targetTimeS: 12,
    sizing: {
      screwNominalDiameterMm: 16,
      guideProfileSizeMm: 15,
      guideCarriages: 4,
      motorNominalPowerW: 100,
      reductionRatio: 5,
      proposedStructuralCapacityN: 400,
    },
  });
  assert.equal(sizedModel.parameters.screwNominalDiameterMm, 16);
  assert.equal(sizedModel.parameters.motorNominalPowerW, 100);
  assert.match(sizedModel.parts.find((part) => part.name === "Motor pré-selecionado")?.detail ?? "", /100 W/);
  assert.match(sizedModel.downloadUrl, /motorPowerW=100/);
});
