export type ActuatorSizingInput = {
  projectName: string;
  payloadKg: number;
  travelMm: number;
  targetTimeS: number;
  screwLeadMm: number;
  screwEfficiency: number;
  supplyVoltage: number;
  existingStructuralCapacityN: number | null;
  targetSafetyFactor?: number;
  dynamicFactor?: number;
};

export type SizingComponent = {
  id: "screw" | "guides" | "bearings" | "motor" | "structure" | "retention" | "limits";
  category: "transmission" | "guidance" | "support" | "drive" | "structure" | "safety";
  name: string;
  selection: string;
  basis: string;
  status: "preselected" | "resize_required" | "evidence_required";
  requiredEvidence: string;
};

export type ActuatorSizingResult = {
  kind: "actuator-preliminary-sizing";
  projectName: string;
  maturity: "preliminary";
  decision: "resize_required" | "preselected_with_pending_evidence";
  metrics: {
    staticLoadN: number;
    dynamicFactor: number;
    designLoadN: number;
    targetSafetyFactor: number;
    requiredStructuralCapacityN: number;
    proposedStructuralCapacityN: number;
    proposedSafetyFactor: number;
    existingDynamicSafetyFactor: number | null;
    linearSpeedMmS: number;
    screwSpeedRpm: number;
    screwTorqueNm: number;
    peakScrewTorqueNm: number;
    mechanicalPowerW: number;
    minimumMotorPowerW: number;
  };
  selections: {
    screwNominalDiameterMm: number;
    guideProfileSizeMm: number;
    guideCarriages: number;
    motorNominalPowerW: number;
    reductionRatio: number;
  };
  components: SizingComponent[];
  assumptions: string[];
  blockers: string[];
};

const GRAVITY = 9.80665;

function bounded(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function rounded(value: number, digits = 3) {
  return Number(value.toFixed(digits));
}

function roundUp(value: number, increment: number) {
  return Math.ceil(value / increment) * increment;
}

function standardMotorPower(minimumPowerW: number) {
  const ratings = [50, 100, 200, 400, 750, 1_000, 1_500];
  return ratings.find((rating) => rating >= minimumPowerW) ?? roundUp(minimumPowerW, 500);
}

export function sizeLinearActuator(input: ActuatorSizingInput): ActuatorSizingResult {
  const payloadKg = bounded(input.payloadKg, 0.1, 500);
  const travelMm = bounded(input.travelMm, 20, 1_500);
  const targetTimeS = bounded(input.targetTimeS, 0.2, 600);
  const screwLeadMm = bounded(input.screwLeadMm, 1, 50);
  const screwEfficiency = bounded(input.screwEfficiency, 0.1, 0.95);
  const supplyVoltage = bounded(input.supplyVoltage, 3, 600);
  const dynamicFactor = bounded(input.dynamicFactor ?? 1.5, 1, 3);
  const targetSafetyFactor = bounded(input.targetSafetyFactor ?? 2, 1.5, 4);

  const staticLoadN = payloadKg * GRAVITY;
  const designLoadN = staticLoadN * dynamicFactor;
  const requiredCapacity = designLoadN * targetSafetyFactor;
  const proposedStructuralCapacityN = roundUp(requiredCapacity, 50);
  const linearSpeedMmS = travelMm / targetTimeS;
  const screwSpeedRpm = (linearSpeedMmS * 60) / screwLeadMm;
  const screwTorqueNm = (designLoadN * (screwLeadMm / 1_000)) / (2 * Math.PI * screwEfficiency);
  const peakScrewTorqueNm = screwTorqueNm * 1.5;
  const mechanicalPowerW = designLoadN * (linearSpeedMmS / 1_000);
  const minimumMotorPowerW = Math.max(mechanicalPowerW / 0.7, 50);
  const motorNominalPowerW = standardMotorPower(minimumMotorPowerW * 1.5);
  const reductionRatio = screwSpeedRpm <= 250 ? 5 : screwSpeedRpm <= 500 ? 3 : 1;
  const screwNominalDiameterMm = designLoadN <= 1_000 && travelMm <= 500 ? 16 : designLoadN <= 2_500 && travelMm <= 1_000 ? 20 : 25;
  const guideProfileSizeMm = payloadKg <= 25 && travelMm <= 500 ? 15 : payloadKg <= 80 && travelMm <= 1_000 ? 20 : 25;
  const existingDynamicSafetyFactor = input.existingStructuralCapacityN
    ? input.existingStructuralCapacityN / designLoadN
    : null;
  const structureNeedsResize = existingDynamicSafetyFactor === null || existingDynamicSafetyFactor < targetSafetyFactor;

  const components: SizingComponent[] = [
    {
      id: "screw",
      category: "transmission",
      name: "Fuso linear",
      selection: `Diâmetro nominal preliminar ${screwNominalDiameterMm} mm · avanço ${screwLeadMm} mm/volta`,
      basis: `${rounded(peakScrewTorqueNm)} N·m de torque de pico e ${rounded(screwSpeedRpm, 1)} rpm no fuso.`,
      status: "preselected",
      requiredEvidence: "Catálogo do fuso, verificação de flambagem, velocidade crítica, vida, rendimento e condição de apoio.",
    },
    {
      id: "guides",
      category: "guidance",
      name: "Guias lineares",
      selection: `2 trilhos perfil ${guideProfileSizeMm} com 4 carros`,
      basis: `Carga dinâmica de projeto ${rounded(designLoadN, 1)} N e curso ${travelMm} mm.`,
      status: "preselected",
      requiredEvidence: "Catálogo, momentos por excentricidade, orientação, pré-carga, vida e rigidez.",
    },
    {
      id: "bearings",
      category: "support",
      name: "Apoios do fuso",
      selection: "Extremidade fixa com par axial/contato angular e extremidade livre radial",
      basis: "Arranjo preliminar para controlar carga axial e dilatação do fuso.",
      status: "evidence_required",
      requiredEvidence: "Geometria das pontas do fuso, carga axial admissível, rotação e vida dos rolamentos.",
    },
    {
      id: "motor",
      category: "drive",
      name: "Motor e redução",
      selection: `${motorNominalPowerW} W · ${supplyVoltage} V · redução ${reductionRatio}:1 · freio`,
      basis: `Mínimo calculado ${rounded(minimumMotorPowerW, 1)} W; rotação-alvo do fuso ${rounded(screwSpeedRpm, 1)} rpm.`,
      status: "preselected",
      requiredEvidence: "Curva torque × rotação, corrente, inércia, controle, ciclo de trabalho e capacidade real do freio.",
    },
    {
      id: "structure",
      category: "structure",
      name: "Estrutura e fixações",
      selection: `Capacidade admissível mínima proposta ${proposedStructuralCapacityN} N`,
      basis: `Carga dinâmica ${rounded(designLoadN, 1)} N × fator-alvo ${targetSafetyFactor}.`,
      status: structureNeedsResize ? "resize_required" : "preselected",
      requiredEvidence: "Material, geometria, soldas/parafusos, análise de tensões, flambagem e deformação.",
    },
    {
      id: "retention",
      category: "safety",
      name: "Retenção da carga",
      selection: "Freio normalmente fechado e retenção mecânica independente",
      basis: "Movimento vertical não pode depender apenas do torque do motor ou do atrito do fuso.",
      status: "evidence_required",
      requiredEvidence: "Análise de falha, desenho, capacidade nominal e teste de queda/perda de energia.",
    },
    {
      id: "limits",
      category: "safety",
      name: "Limites e sobrecurso",
      selection: "Limites funcionais superior/inferior e batentes mecânicos independentes",
      basis: `Curso nominal ${travelMm} mm com barreira física contra sobrecurso.`,
      status: "evidence_required",
      requiredEvidence: "Diagrama de controle, distância de parada, posição dos sensores e teste funcional.",
    },
  ];

  const blockers = [
    ...(structureNeedsResize
      ? [`A capacidade existente de ${input.existingStructuralCapacityN?.toLocaleString("pt-BR") ?? "valor não informado"} N não demonstra o fator-alvo contra a carga dinâmica.`]
      : []),
    "A retenção vertical ainda precisa ser definida e ensaiada.",
    "Faltam catálogos e condições reais de montagem para validar as pré-seleções.",
    "O ciclo de trabalho ainda precisa ser confirmado para a verificação térmica.",
  ];

  return {
    kind: "actuator-preliminary-sizing",
    projectName: input.projectName,
    maturity: "preliminary",
    decision: structureNeedsResize ? "resize_required" : "preselected_with_pending_evidence",
    metrics: {
      staticLoadN: rounded(staticLoadN, 2),
      dynamicFactor,
      designLoadN: rounded(designLoadN, 2),
      targetSafetyFactor,
      requiredStructuralCapacityN: rounded(requiredCapacity, 2),
      proposedStructuralCapacityN,
      proposedSafetyFactor: rounded(proposedStructuralCapacityN / designLoadN, 2),
      existingDynamicSafetyFactor: existingDynamicSafetyFactor === null ? null : rounded(existingDynamicSafetyFactor, 2),
      linearSpeedMmS: rounded(linearSpeedMmS, 2),
      screwSpeedRpm: rounded(screwSpeedRpm, 2),
      screwTorqueNm: rounded(screwTorqueNm),
      peakScrewTorqueNm: rounded(peakScrewTorqueNm),
      mechanicalPowerW: rounded(mechanicalPowerW, 2),
      minimumMotorPowerW: rounded(minimumMotorPowerW, 2),
    },
    selections: {
      screwNominalDiameterMm,
      guideProfileSizeMm,
      guideCarriages: 4,
      motorNominalPowerW,
      reductionRatio,
    },
    components,
    assumptions: [
      `Fator dinâmico preliminar ${dynamicFactor}.`,
      `Fator de segurança-alvo ${targetSafetyFactor}.`,
      `Rendimento informado do fuso ${(screwEfficiency * 100).toLocaleString("pt-BR")}% e rendimento global estimado de 70% somente para pré-dimensionamento do motor.`,
      "Carga centrada; impactos, excentricidade e atrito variável ainda não foram quantificados.",
    ],
    blockers,
  };
}
