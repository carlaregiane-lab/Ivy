export type ActuatorCadInput = {
  projectName: string;
  payloadKg: number;
  travelMm: number;
  screwLeadMm: number;
  motorVoltage: number;
  targetTimeS?: number | null;
  sizing?: {
    screwNominalDiameterMm: number;
    guideProfileSizeMm: number;
    guideCarriages: number;
    motorNominalPowerW: number;
    reductionRatio: number;
    proposedStructuralCapacityN: number;
  } | null;
};

export type ActuatorCadResult = {
  kind: "linear-actuator-concept";
  modelId: string;
  title: string;
  revision: "REV. 001";
  maturity: "concept";
  parameters: {
    payloadKg: number;
    travelMm: number;
    screwLeadMm: number;
    motorVoltage: number;
    targetTimeS: number | null;
    overallWidthMm: number;
    overallDepthMm: number;
    overallHeightMm: number;
    screwNominalDiameterMm: number;
    guideProfileSizeMm: number;
    guideCarriages: number;
    motorNominalPowerW: number | null;
    reductionRatio: number | null;
    proposedStructuralCapacityN: number | null;
  };
  parts: Array<{ name: string; detail: string }>;
  warnings: string[];
  downloadUrl: string;
};

function bounded(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

export function createActuatorCad(input: ActuatorCadInput): ActuatorCadResult {
  const payloadKg = bounded(input.payloadKg, 0.1, 500);
  const travelMm = bounded(input.travelMm, 20, 1500);
  const screwLeadMm = bounded(input.screwLeadMm, 1, 50);
  const motorVoltage = bounded(input.motorVoltage, 3, 600);
  const targetTimeS = input.targetTimeS ? bounded(input.targetTimeS, 0.2, 600) : null;
  const screwNominalDiameterMm = bounded(input.sizing?.screwNominalDiameterMm ?? 12, 8, 80);
  const guideProfileSizeMm = bounded(input.sizing?.guideProfileSizeMm ?? 16, 8, 55);
  const guideCarriages = bounded(input.sizing?.guideCarriages ?? 2, 2, 8);
  const overallWidthMm = bounded(100 + payloadKg * 2, 120, 260);
  const overallDepthMm = bounded(70 + payloadKg, 80, 180);
  const overallHeightMm = travelMm + 180;
  const modelId = `ACT-${Math.round(travelMm)}-${Math.round(payloadKg * 10)}`;
  const query = new URLSearchParams({
    payloadKg: String(payloadKg),
    travelMm: String(travelMm),
    screwLeadMm: String(screwLeadMm),
    motorVoltage: String(motorVoltage),
    screwDiameterMm: String(screwNominalDiameterMm),
    guideSizeMm: String(guideProfileSizeMm),
    motorPowerW: String(input.sizing?.motorNominalPowerW ?? 0),
    reductionRatio: String(input.sizing?.reductionRatio ?? 0),
    structuralCapacityN: String(input.sizing?.proposedStructuralCapacityN ?? 0),
    projectName: input.projectName.slice(0, 80),
  });

  return {
    kind: "linear-actuator-concept",
    modelId,
    title: `${input.projectName.trim() || "Atuador linear vertical"} — conceito paramétrico`,
    revision: "REV. 001",
    maturity: "concept",
    parameters: {
      payloadKg,
      travelMm,
      screwLeadMm,
      motorVoltage,
      targetTimeS,
      overallWidthMm,
      overallDepthMm,
      overallHeightMm,
      screwNominalDiameterMm,
      guideProfileSizeMm,
      guideCarriages,
      motorNominalPowerW: input.sizing?.motorNominalPowerW ?? null,
      reductionRatio: input.sizing?.reductionRatio ?? null,
      proposedStructuralCapacityN: input.sizing?.proposedStructuralCapacityN ?? null,
    },
    parts: [
      { name: "Base estrutural", detail: input.sizing ? `capacidade proposta ≥ ${input.sizing.proposedStructuralCapacityN.toFixed(0)} N` : `${overallWidthMm.toFixed(0)} × ${overallDepthMm.toFixed(0)} × 12 mm` },
      { name: "Guias verticais", detail: input.sizing ? `2 × perfil ${guideProfileSizeMm} · ${guideCarriages.toFixed(0)} carros` : `2 × Ø 16 · curso ${travelMm.toFixed(0)} mm` },
      { name: "Carro móvel", detail: `${(overallWidthMm * 0.72).toFixed(0)} × ${(overallDepthMm * 0.72).toFixed(0)} mm` },
      { name: "Plataforma de carga", detail: `carga nominal informada ${payloadKg.toFixed(1)} kg` },
      { name: "Fuso central", detail: `Ø ${screwNominalDiameterMm.toFixed(0)} · avanço ${screwLeadMm.toFixed(1)} mm/volta` },
      { name: input.sizing ? "Motor pré-selecionado" : "Motor provisório", detail: input.sizing ? `${input.sizing.motorNominalPowerW} W · ${motorVoltage.toFixed(0)} V · ${input.sizing.reductionRatio}:1 · freio` : `${motorVoltage.toFixed(0)} V · seleção pendente` },
    ],
    warnings: [
      input.sizing
        ? "Geometria atualizada com pré-seleções genéricas; interfaces e capacidades ainda precisam de catálogo e validação."
        : "Geometria conceitual: dimensões estruturais e interfaces ainda precisam de cálculo e seleção de componentes.",
      "O STL é uma malha de estudo e não deve ser usado diretamente para fabricação.",
      "Freio, retenção de carga, fins de curso, proteção e fixações ainda precisam ser definidos.",
    ],
    downloadUrl: `/api/cad/actuator?${query.toString()}`,
  };
}
