import assert from "node:assert/strict";
import test from "node:test";
import {
  assessEngineeringReadiness,
  type EngineeringVerificationInput,
} from "../lib/engineering/verifications.ts";

const completeInput: EngineeringVerificationInput = {
  projectName: "Atuador de teste",
  verticalLoad: true,
  movingMechanism: true,
  electricalSystem: true,
  loadForceN: 100,
  actuatorForceN: 250,
  safetyFactor: 2,
  mechanicalRetention: true,
  limitSwitches: true,
  emergencyStop: true,
  guarding: true,
  electricalProtection: true,
  dutyCycleDefined: true,
  evidence: [{ kind: "test", description: "Teste funcional registrado." }],
};

test("libera somente um cenário preliminar totalmente atendido para revisão", () => {
  const output = assessEngineeringReadiness(completeInput);

  assert.equal(output.decision, "ready_for_review");
  assert.equal(output.readinessScore, 100);
  assert.equal(output.counts.blocked, 0);
  assert.equal(output.counts.evidence_required, 0);
});

test("bloqueia margem estrutural menor que um", () => {
  const output = assessEngineeringReadiness({ ...completeInput, safetyFactor: 0.8 });
  const margin = output.checks.find((item) => item.id === "safety-margin");

  assert.equal(output.decision, "blocked");
  assert.equal(margin?.status, "blocked");
  assert.equal(margin?.severity, "critical");
});

test("exige evidência para retenção vertical não informada", () => {
  const output = assessEngineeringReadiness({ ...completeInput, mechanicalRetention: null });
  const retention = output.checks.find((item) => item.id === "vertical-retention");

  assert.equal(output.decision, "conditional");
  assert.equal(retention?.status, "evidence_required");
  assert.match(retention?.requiredEvidence ?? "", /freio|trava/);
});

test("bloqueia projeto sem carga quantificada", () => {
  const output = assessEngineeringReadiness({ ...completeInput, loadForceN: null });

  assert.equal(output.decision, "blocked");
  assert.equal(output.checks.find((item) => item.id === "load-definition")?.status, "blocked");
});
