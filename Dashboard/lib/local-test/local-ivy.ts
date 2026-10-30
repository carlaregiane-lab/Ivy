import {
  calculateEngineering,
  type EngineeringCalculationInput,
  type EngineeringCalculationResult,
} from "../engineering/calculations.ts";
import {
  assessEngineeringReadiness,
  type EngineeringVerificationInput,
  type EngineeringVerificationResult,
} from "../engineering/verifications.ts";
import type { ProjectContext } from "../tools/project-context-tool.ts";
import { createActuatorCad, type ActuatorCadInput, type ActuatorCadResult } from "../cad/actuator-cad.ts";
import {
  sizeLinearActuator,
  type ActuatorSizingInput,
  type ActuatorSizingResult,
} from "../engineering/actuator-sizing.ts";
import {
  selectCatalogComponents,
  type CatalogSelectionInput,
  type CatalogSelectionResult,
} from "../catalog/component-catalog.ts";

type LocalCalculation = {
  input: EngineeringCalculationInput;
  output: EngineeringCalculationResult;
};

type LocalVerification = {
  input: EngineeringVerificationInput;
  output: EngineeringVerificationResult;
};

type LocalCad = { input: ActuatorCadInput; output: ActuatorCadResult };
type LocalSizing = { input: ActuatorSizingInput; output: ActuatorSizingResult };
type LocalCatalog = { input: CatalogSelectionInput; output: CatalogSelectionResult };

export type LocalIvyScenario = {
  context: ProjectContext;
  calculations: LocalCalculation[];
  verification: LocalVerification;
  sizing: LocalSizing | null;
  catalog: LocalCatalog | null;
  cad: LocalCad | null;
  response: string;
};

type UnitValue = { value: number; unit: string };

function numberFrom(value: string) {
  return Number(value.replace(",", "."));
}

function findUnitValue(text: string, pattern: RegExp): UnitValue | null {
  const match = text.match(pattern);
  if (!match) return null;
  return { value: numberFrom(match[1]), unit: match[2] };
}

function findNumber(text: string, pattern: RegExp) {
  const match = text.match(pattern);
  return match ? numberFrom(match[1]) : null;
}

function normalizedLengthUnit(unit: string) {
  return unit.toLocaleLowerCase("pt-BR") as "m" | "cm" | "mm";
}

function normalizedForceUnit(unit: string) {
  return unit.toLocaleLowerCase("pt-BR") === "kn" ? "kN" : "N";
}

function normalizedAreaUnit(unit: string) {
  return unit.toLocaleLowerCase("pt-BR").replace("²", "2") as "m2" | "cm2" | "mm2";
}

function lengthToMillimeters(value: UnitValue) {
  const unit = normalizedLengthUnit(value.unit);
  if (unit === "m") return value.value * 1_000;
  if (unit === "cm") return value.value * 10;
  return value.value;
}

function addCalculation(calculations: LocalCalculation[], input: EngineeringCalculationInput) {
  calculations.push({ input, output: calculateEngineering(input) });
  return calculations.at(-1)!.output;
}

function formattedList(calculations: LocalCalculation[]) {
  return calculations.map(({ output }) => `- **${output.label}:** ${output.result.formatted}`).join("\n");
}

function warningsList(calculations: LocalCalculation[]) {
  const warnings = calculations.flatMap(({ output }) => output.warnings);
  if (!warnings.length) return "- Nenhum alerta automático foi produzido pelos cálculos disponíveis.";
  return [...new Set(warnings)].map((warning) => `- ${warning}`).join("\n");
}

function statedBoolean(text: string, positive: RegExp, negative: RegExp) {
  if (negative.test(text)) return false;
  if (positive.test(text)) return true;
  return null;
}

export function createLocalIvyScenario(prompt: string): LocalIvyScenario {
  const mass = findUnitValue(prompt, /(\d+(?:[.,]\d+)?)\s*(kg|g)\b/i);
  const travel = findUnitValue(
    prompt,
    /(?:distância(?:\s+de)?|percorrer|curso(?:\s+de)?)\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)\b/i
  );
  const timeSeconds = findNumber(prompt, /(?:em|durante|tempo(?:\s+de)?|por)\s*(\d+(?:[.,]\d+)?)\s*(?:s|segundos?)\b/i);
  const lever = findUnitValue(prompt, /braço[^\d]{0,45}(\d+(?:[.,]\d+)?)\s*(mm|cm|m)\b/i);
  const area = findUnitValue(prompt, /área[^\d]{0,45}(\d+(?:[.,]\d+)?)\s*(mm(?:²|2)|cm(?:²|2)|m(?:²|2))(?!\w)/i);
  const capacity = findUnitValue(prompt, /capacidade[^\d]{0,60}(\d+(?:[.,]\d+)?)\s*(kN|N)\b/i);
  const lead = findUnitValue(
    prompt,
    /(?:avanço(?:\s+do\s+fuso)?|passo(?:\s+do\s+fuso)?|fuso[^\d]{0,24}(?:avanço|passo))[^\d]{0,15}(\d+(?:[.,]\d+)?)\s*(mm|cm|m)\b/i
  );
  const torque = findUnitValue(prompt, /torque[^\d]{0,45}(\d+(?:[.,]\d+)?)\s*(N[·.]?m|N[·.]?mm)\b/i);
  const efficiencyPercent = findNumber(prompt, /eficiência[^\d]{0,45}(\d+(?:[.,]\d+)?)\s*%/i);
  const voltage = findNumber(prompt, /(\d+(?:[.,]\d+)?)\s*V\b/i);
  const current = findNumber(prompt, /(\d+(?:[.,]\d+)?)\s*A\b/i);
  const cadRequested = /\b(cad|modelo\s*3d|modelo\s+tridimensional|stl|desenho\s+técnico)\b/i.test(prompt);
  const sizingRequested = /\b(dimension(?:e|ar|amento)|pré-dimension|redimension|selecion(?:e|ar|amento)|componentes?)\b/i.test(prompt);
  const catalogRequested = /\b(catálogo|componente(?:s)?\s+(?:re(?:al|ais)|comercia(?:l|is))|peça(?:s)?\s+(?:re(?:al|ais)|comercia(?:l|is))|fabricante(?:s)?|código(?:s)?\s+(?:de\s+)?(?:compra|produto)|part\s*number)\b/i.test(prompt);

  const calculations: LocalCalculation[] = [];
  let loadForce: EngineeringCalculationResult | null = null;
  let linearSpeed: EngineeringCalculationResult | null = null;
  let screwForce: EngineeringCalculationResult | null = null;
  let safetyFactor: EngineeringCalculationResult | null = null;

  if (mass) {
    loadForce = addCalculation(calculations, {
      calculation: "forceFromMass",
      mass: { value: mass.value, unit: mass.unit.toLocaleLowerCase("pt-BR") as "kg" | "g" },
      acceleration: { value: 1, unit: "g0" },
      outputUnit: "N",
    });
  }

  if (loadForce && lever) {
    addCalculation(calculations, {
      calculation: "torqueFromForce",
      force: { value: loadForce.result.value, unit: "N" },
      leverArm: { value: lever.value, unit: normalizedLengthUnit(lever.unit) },
      outputUnit: "N.m",
    });
  }

  if (loadForce && area) {
    addCalculation(calculations, {
      calculation: "pressureFromForce",
      force: { value: loadForce.result.value, unit: "N" },
      area: { value: area.value, unit: normalizedAreaUnit(area.unit) },
      outputUnit: "MPa",
    });
  }

  if (loadForce && capacity) {
    const capacityInNewtons = capacity.value * (normalizedForceUnit(capacity.unit) === "kN" ? 1_000 : 1);
    safetyFactor = addCalculation(calculations, {
      calculation: "safetyFactor",
      capacity: capacityInNewtons,
      demand: loadForce.result.value,
    });
  }

  if (torque && lead && efficiencyPercent !== null) {
    screwForce = addCalculation(calculations, {
      calculation: "leadScrewLinearForce",
      torque: {
        value: torque.value,
        unit: torque.unit.toLocaleLowerCase("pt-BR").includes("mm") ? "N.mm" : "N.m",
      },
      lead: { value: lead.value, unit: normalizedLengthUnit(lead.unit) },
      efficiency: efficiencyPercent / 100,
      outputUnit: "N",
    });
  }

  if (voltage !== null && current !== null) {
    addCalculation(calculations, {
      calculation: "dcPower",
      voltage,
      current,
      outputUnit: "W",
    });
  }

  if (travel && timeSeconds !== null) {
    linearSpeed = addCalculation(calculations, {
      calculation: "linearSpeed",
      distance: { value: travel.value, unit: normalizedLengthUnit(travel.unit) },
      time: { value: timeSeconds, unit: "s" },
      outputUnit: "mm/s",
    });
  }

  if (loadForce && linearSpeed) {
    addCalculation(calculations, {
      calculation: "mechanicalPower",
      force: { value: loadForce.result.value, unit: "N" },
      speed: { value: linearSpeed.result.value, unit: "mm/s" },
      outputUnit: "W",
    });
  }

  const missingInputs = [
    !mass && "massa da carga",
    !travel && "distância ou curso",
    timeSeconds === null && "tempo do movimento",
    !lever && "comprimento do braço",
    !area && "área de contato",
    !capacity && "capacidade estrutural",
    !lead && "avanço do fuso",
    !torque && "torque aplicado",
    efficiencyPercent === null && "eficiência do fuso",
    voltage === null && "tensão",
    current === null && "corrente",
  ].filter((item): item is string => Boolean(item));

  const comparison =
    screwForce && loadForce
      ? screwForce.result.value >= loadForce.result.value
        ? `A força idealizada do fuso é ${(screwForce.result.value / loadForce.result.value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} vezes a força estática da carga.`
        : "A força idealizada do fuso é inferior à força estática da carga."
      : "A comparação entre fuso e carga depende dos dados ainda ausentes.";

  const projectName = mass ? "Atuador linear vertical" : "Projeto em teste local";
  const context: ProjectContext = {
    projectName,
    phase: calculations.length ? "calculos" : "descoberta",
    objective: mass
      ? `Projetar um atuador linear vertical para movimentar uma carga de ${mass.value.toLocaleString("pt-BR")} ${mass.unit}.`
      : prompt.trim().slice(0, 500) || null,
    requirements: [
      mass ? `Movimentar uma carga de ${mass.value.toLocaleString("pt-BR")} ${mass.unit}.` : null,
      travel ? `Percorrer ${travel.value.toLocaleString("pt-BR")} ${travel.unit}.` : null,
      timeSeconds !== null ? `Completar o movimento em ${timeSeconds.toLocaleString("pt-BR")} s.` : null,
      voltage !== null ? `Operar com alimentação de ${voltage.toLocaleString("pt-BR")} V.` : null,
    ].filter((item): item is string => Boolean(item)),
    constraints: ["Movimento vertical: considerar retenção da carga em perda de energia."],
    calculations: calculations.map(({ output }) => ({
      name: output.label,
      status: "pronto" as const,
      missingInputs: [],
    })),
    risks: [
      {
        description: "Queda da carga em falha de energia ou transmissão.",
        severity: "alta",
        mitigation: "Definir retenção mecânica, fim de curso e parada segura.",
      },
      ...(safetyFactor && safetyFactor.result.value < 1.5
        ? [
            {
              description: "Margem estrutural abaixo de 1,5 no cenário informado.",
              severity: "alta" as const,
              mitigation: "Rever a capacidade e definir o critério de aceitação antes da fabricação.",
            },
          ]
        : []),
    ],
    assumptions: ["A força da carga usa gravidade padrão de 1 g₀.", "Os cálculos do fuso são idealizados."],
    openQuestions: [
      ...missingInputs.slice(0, 5).map((item) => `Confirmar ${item}.`),
      "Qual é o ciclo de trabalho e a aceleração real do movimento?",
      "Qual mecanismo impedirá a queda da carga em uma falha?",
    ].slice(0, 8),
    confidence: calculations.length >= 6 ? "alta" : calculations.length >= 2 ? "media" : "baixa",
  };

  const verificationInput: EngineeringVerificationInput = {
    projectName,
    verticalLoad: /vertical/i.test(prompt),
    movingMechanism: Boolean(travel || lead || torque),
    electricalSystem: voltage !== null || current !== null,
    loadForceN: loadForce?.result.value ?? null,
    actuatorForceN: screwForce?.result.value ?? null,
    safetyFactor: safetyFactor?.result.value ?? null,
    mechanicalRetention: statedBoolean(
      prompt,
      /\b(freio|trava|contrapeso|retenção mecânica)\b/i,
      /\bsem\s+(freio|trava|contrapeso|retenção)\b/i
    ),
    limitSwitches: statedBoolean(
      prompt,
      /\b(fim de curso|sensor(?:es)? de limite)\b/i,
      /\bsem\s+(fim de curso|sensor(?:es)? de limite)\b/i
    ),
    emergencyStop: statedBoolean(
      prompt,
      /\b(parada de emergência|botão de emergência)\b/i,
      /\bsem\s+(parada de emergência|botão de emergência)\b/i
    ),
    guarding: statedBoolean(
      prompt,
      /\b(proteção física|carenagem|grade de proteção|intertravamento)\b/i,
      /\bsem\s+(proteção física|carenagem|grade de proteção|intertravamento)\b/i
    ),
    electricalProtection: statedBoolean(
      prompt,
      /\b(fusível|disjuntor|proteção contra sobrecorrente)\b/i,
      /\bsem\s+(fusível|disjuntor|proteção contra sobrecorrente)\b/i
    ),
    dutyCycleDefined: statedBoolean(
      prompt,
      /\b(ciclo de trabalho|duty cycle|movimentos por hora|ED\s*\d+\s*%)\b/i,
      /\b(ciclo de trabalho não definido|sem ciclo de trabalho)\b/i
    ),
    evidence: calculations.map(({ output }) => ({
      kind: "calculation" as const,
      description: `${output.label}: ${output.result.formatted}`,
    })),
  };
  const verification: LocalVerification = {
    input: verificationInput,
    output: assessEngineeringReadiness(verificationInput),
  };

  const existingStructuralCapacityN = capacity
    ? capacity.value * (normalizedForceUnit(capacity.unit) === "kN" ? 1_000 : 1)
    : null;
  const sizingInput = sizingRequested && mass && travel && timeSeconds !== null && lead && efficiencyPercent !== null && voltage !== null
    ? {
        projectName,
        payloadKg: mass.unit.toLocaleLowerCase("pt-BR") === "g" ? mass.value / 1_000 : mass.value,
        travelMm: lengthToMillimeters(travel),
        targetTimeS: timeSeconds,
        screwLeadMm: lengthToMillimeters(lead),
        screwEfficiency: efficiencyPercent / 100,
        supplyVoltage: voltage,
        existingStructuralCapacityN,
        targetSafetyFactor: findNumber(prompt, /fator(?:\s+de)?\s+segurança(?:\s+(?:alvo|mínimo))?[^\d]{0,20}(\d+(?:[.,]\d+)?)/i) ?? 2,
        dynamicFactor: findNumber(prompt, /fator\s+dinâmico[^\d]{0,20}(\d+(?:[.,]\d+)?)/i) ?? 1.5,
      }
    : null;
  const sizing = sizingInput ? { input: sizingInput, output: sizeLinearActuator(sizingInput) } : null;
  const catalogInput = catalogRequested && sizing
    ? {
        projectName,
        requiredScrewDiameterMm: sizing.output.selections.screwNominalDiameterMm,
        requiredScrewLeadMm: sizing.input.screwLeadMm,
        requiredGuideSizeMm: sizing.output.selections.guideProfileSizeMm,
        requiredDynamicLoadN: sizing.output.metrics.designLoadN,
        requiredPeakTorqueNm: sizing.output.metrics.peakScrewTorqueNm,
        requiredScrewSpeedRpm: sizing.output.metrics.screwSpeedRpm,
        requiredMotorPowerW: sizing.output.selections.motorNominalPowerW,
        supplyVoltageV: sizing.input.supplyVoltage,
      }
    : null;
  const catalog = catalogInput ? { input: catalogInput, output: selectCatalogComponents(catalogInput) } : null;

  const cadInput = cadRequested && mass && travel && lead && voltage !== null
    ? {
        projectName,
        payloadKg: mass.unit.toLocaleLowerCase("pt-BR") === "g" ? mass.value / 1_000 : mass.value,
        travelMm: lengthToMillimeters(travel),
        screwLeadMm: lengthToMillimeters(lead),
        motorVoltage: voltage,
        targetTimeS: timeSeconds,
        sizing: sizing
          ? {
              ...sizing.output.selections,
              proposedStructuralCapacityN: sizing.output.metrics.proposedStructuralCapacityN,
            }
          : null,
      }
    : null;
  const cad = cadInput ? { input: cadInput, output: createActuatorCad(cadInput) } : null;

  const baseResponse = calculations.length
    ? `**Modo Teste Local concluído.** Executei as ferramentas determinísticas da Ivy sem acessar um modelo externo.\n\n${formattedList(calculations)}\n\n**Comparação principal**\n\n${comparison}${sizing ? `\n\n**Pré-dimensionamento do atuador**\n\n- Carga dinâmica de projeto: ${sizing.output.metrics.designLoadN.toLocaleString("pt-BR")} N\n- Capacidade estrutural mínima proposta: ${sizing.output.metrics.proposedStructuralCapacityN.toLocaleString("pt-BR")} N\n- Fator de segurança proposto: ${sizing.output.metrics.proposedSafetyFactor.toLocaleString("pt-BR")}\n- Fuso: Ø ${sizing.output.selections.screwNominalDiameterMm} mm\n- Guias: perfil ${sizing.output.selections.guideProfileSizeMm}, 4 carros\n- Motor: ${sizing.output.selections.motorNominalPowerW} W, redução ${sizing.output.selections.reductionRatio}:1 e freio\n\nA pré-seleção corrige o alvo de capacidade no conceito, mas continua exigindo catálogos, análise estrutural e ensaios.` : ""}\n\n**Decisão de verificação**\n\n- **Prontidão:** ${verification.output.readinessScore}%\n- **Situação:** ${verification.output.summary}\n- **Bloqueios:** ${verification.output.counts.blocked}\n- **Evidências pendentes:** ${verification.output.counts.evidence_required}${cad ? `\n\n**CAD conceitual criado**\n\n- Modelo: ${cad.output.modelId}\n- Curso: ${cad.output.parameters.travelMm} mm\n- Exportação: STL disponível no Workspace CAD` : ""}\n\n**Alertas dos cálculos**\n\n${warningsList(calculations)}\n\nEsses resultados validam o fluxo local de contexto, ferramentas, unidades, riscos e interface. Eles não substituem revisão profissional, ensaios e validação antes da fabricação.`
    : `**Modo Teste Local ativo.** Não encontrei entradas numéricas suficientes para executar uma ferramenta. Informe valores e unidades para massa, distância, tempo, força, área, torque, avanço, eficiência, tensão ou corrente.`;
  const catalogSummary = catalog
    ? `\n\n**Seleção por catálogo**\n\n- Candidatos compatíveis: ${catalog.output.summary.candidates}\n- Rejeitados: ${catalog.output.summary.rejected}\n- Dependem de evidência: ${catalog.output.summary.evidenceRequired}\n- Fontes oficiais: ${catalog.output.summary.officialSources}\n\nA guia HIWIN perfil 15 passou pela comparação preliminar. O fuso segue bloqueado porque os candidatos disponíveis têm avanço diferente dos ${catalog.input.requiredScrewLeadMm} mm exigidos.`
    : "";
  const response = catalogSummary
    ? baseResponse.replace("\n\n**Decisão de verificação**", `${catalogSummary}\n\n**Decisão de verificação**`)
    : baseResponse;

  return { context, calculations, verification, sizing, catalog, cad, response };
}
