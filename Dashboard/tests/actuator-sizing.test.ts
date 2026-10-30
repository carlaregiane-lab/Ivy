import assert from "node:assert/strict";
import test from "node:test";
import { sizeLinearActuator } from "../lib/engineering/actuator-sizing.ts";

const sizing = sizeLinearActuator({
  projectName: "Atuador linear vertical",
  payloadKg: 12,
  travelMm: 300,
  targetTimeS: 12,
  screwLeadMm: 8,
  screwEfficiency: 0.35,
  supplyVoltage: 24,
  existingStructuralCapacityN: 150,
  targetSafetyFactor: 2,
  dynamicFactor: 1.5,
});

test("dimensiona a carga dinâmica e a capacidade estrutural proposta", () => {
  assert.equal(sizing.metrics.staticLoadN, 117.68);
  assert.equal(sizing.metrics.designLoadN, 176.52);
  assert.equal(sizing.metrics.requiredStructuralCapacityN, 353.04);
  assert.equal(sizing.metrics.proposedStructuralCapacityN, 400);
  assert.equal(sizing.metrics.proposedSafetyFactor, 2.27);
  assert.equal(sizing.metrics.existingDynamicSafetyFactor, 0.85);
  assert.equal(sizing.decision, "resize_required");
});

test("pré-seleciona transmissão, guias e motor rastreáveis", () => {
  assert.equal(sizing.selections.screwNominalDiameterMm, 16);
  assert.equal(sizing.selections.guideProfileSizeMm, 15);
  assert.equal(sizing.selections.guideCarriages, 4);
  assert.equal(sizing.selections.motorNominalPowerW, 100);
  assert.equal(sizing.selections.reductionRatio, 5);
  assert.equal(sizing.components.length, 7);
  assert.equal(sizing.components.find((component) => component.id === "structure")?.status, "resize_required");
  assert.match(sizing.components.find((component) => component.id === "retention")?.selection ?? "", /Freio/);
});

test("calcula rotação e torque do fuso com os parâmetros informados", () => {
  assert.equal(sizing.metrics.linearSpeedMmS, 25);
  assert.equal(sizing.metrics.screwSpeedRpm, 187.5);
  assert.equal(sizing.metrics.screwTorqueNm, 0.642);
  assert.equal(sizing.metrics.peakScrewTorqueNm, 0.963);
});
