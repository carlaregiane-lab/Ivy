import assert from "node:assert/strict";
import test from "node:test";
import { createLocalIvyScenario } from "../lib/local-test/local-ivy.ts";

const completePrompt = `
Quero projetar um atuador linear vertical para levantar uma carga de 12 kg por uma distância de 300 mm em 12 segundos.
Braço de alavanca para teste: 250 mm.
Área de contato: 600 mm².
Capacidade estrutural inicialmente considerada: 150 N.
Fuso com avanço de 8 mm por volta.
Torque aplicado ao fuso: 2,5 N·m.
Eficiência estimada do fuso: 35%.
Motor alimentado com 24 V e corrente de 8 A.
`;

test("modo local executa as oito funções do cenário completo", () => {
  const scenario = createLocalIvyScenario(completePrompt);

  assert.deepEqual(
    scenario.calculations.map(({ input }) => input.calculation),
    [
      "forceFromMass",
      "torqueFromForce",
      "pressureFromForce",
      "safetyFactor",
      "leadScrewLinearForce",
      "dcPower",
      "linearSpeed",
      "mechanicalPower",
    ]
  );
  assert.equal(scenario.context.projectName, "Atuador linear vertical");
  assert.equal(scenario.context.calculations.length, 8);
  assert.equal(scenario.context.confidence, "alta");
  assert.equal(scenario.verification.output.decision, "blocked");
  assert.equal(scenario.verification.output.counts.blocked, 1);
});

test("modo local conserva os resultados esperados do prompt de demonstração", () => {
  const scenario = createLocalIvyScenario(completePrompt);
  const values = new Map(
    scenario.calculations.map(({ input, output }) => [input.calculation, output.result.value])
  );

  assert.equal(values.get("forceFromMass"), 117.68);
  assert.equal(values.get("dcPower"), 192);
  assert.equal(values.get("linearSpeed"), 25);
  assert.equal(values.get("safetyFactor"), 1.27464);
});

test("modo local orienta a pessoa quando faltam dados numéricos", () => {
  const scenario = createLocalIvyScenario("Quero iniciar um projeto de engenharia.");

  assert.equal(scenario.calculations.length, 0);
  assert.match(scenario.response, /Não encontrei entradas numéricas suficientes/);
  assert.equal(scenario.context.confidence, "baixa");
});

test("modo local cria o CAD do atuador quando solicitado", () => {
  const scenario = createLocalIvyScenario(`${completePrompt}\nCrie o CAD, modelo 3D e STL deste projeto.`);
  assert.equal(scenario.cad?.output.modelId, "ACT-300-120");
  assert.equal(scenario.cad?.output.parameters.motorVoltage, 24);
  assert.match(scenario.response, /CAD conceitual criado/);
});

test("modo local dimensiona componentes e atualiza o CAD", () => {
  const scenario = createLocalIvyScenario(`${completePrompt}\nPré-dimensione os componentes e atualize o CAD.`);
  assert.equal(scenario.sizing?.output.metrics.proposedStructuralCapacityN, 400);
  assert.equal(scenario.sizing?.output.selections.screwNominalDiameterMm, 16);
  assert.equal(scenario.cad?.output.parameters.motorNominalPowerW, 100);
  assert.equal(scenario.cad?.output.parameters.guideCarriages, 4);
  assert.match(scenario.response, /Pré-dimensionamento do atuador/);
});

test("modo local entende passo do fuso como avanço por volta", () => {
  const promptWithScrewPitch = `${completePrompt.replace(
    "Fuso com avanço de 8 mm por volta.",
    "Fuso com passo de 8 mm por volta."
  )}\nDimensione os componentes e atualize o CAD.`;
  const scenario = createLocalIvyScenario(promptWithScrewPitch);

  assert.equal(scenario.sizing?.input.screwLeadMm, 8);
  assert.equal(scenario.cad?.output.parameters.screwLeadMm, 8);
});

test("modo local compara componentes comerciais depois do dimensionamento", () => {
  const scenario = createLocalIvyScenario(
    `${completePrompt}\nDimensione e compare com componentes comerciais reais, fabricante, código de compra e catálogo.`
  );

  assert.equal(scenario.catalog?.output.decision, "blocked_by_catalog_mismatch");
  assert.equal(scenario.catalog?.output.summary.candidates, 1);
  assert.equal(scenario.catalog?.output.evaluations.some((item) => item.entry.partNumber.includes("HGH15")), true);
});

test("modo local entende o pedido de catálogo no plural", () => {
  const scenario = createLocalIvyScenario(
    `${completePrompt}\nCompare o pré-dimensionamento com componentes comerciais reais, fabricantes, códigos e fontes oficiais.`
  );

  assert.equal(scenario.catalog?.output.summary.officialSources, 5);
});
