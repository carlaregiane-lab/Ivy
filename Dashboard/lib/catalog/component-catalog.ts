export type CatalogCategory = "screw" | "guide" | "support" | "drive";

export type CatalogEntry = {
  id: string;
  category: CatalogCategory;
  manufacturer: string;
  family: string;
  partNumber: string;
  identityLevel: "part_number" | "family_configuration";
  sourceUrl: string;
  sourceTitle: string;
  checkedAt: string;
  specifications: {
    nominalDiameterMm?: number;
    leadMm?: number;
    profileSizeMm?: number;
    dynamicLoadRatingN?: number;
    staticLoadRatingN?: number;
    ratedPowerW?: number;
    supplyVoltageV?: number;
    minimumRatedTorqueNm?: number;
    minimumSpeedRpm?: number;
    maximumSpeedRpm?: number;
  };
  notes: string;
};

export type CatalogSelectionInput = {
  projectName: string;
  requiredScrewDiameterMm: number;
  requiredScrewLeadMm: number;
  requiredGuideSizeMm: number;
  requiredDynamicLoadN: number;
  requiredPeakTorqueNm: number;
  requiredScrewSpeedRpm: number;
  requiredMotorPowerW: number;
  supplyVoltageV: number;
};

export type CatalogCheck = {
  label: string;
  required: string;
  catalog: string;
  passed: boolean | null;
};

export type CatalogEvaluation = {
  entry: CatalogEntry;
  status: "candidate" | "rejected" | "evidence_required";
  checks: CatalogCheck[];
  conclusion: string;
  requiredEvidence: string[];
};

export type CatalogSelectionResult = {
  kind: "commercial-component-selection";
  projectName: string;
  maturity: "catalog-candidate";
  decision: "blocked_by_catalog_mismatch" | "candidates_with_pending_evidence";
  summary: {
    candidates: number;
    rejected: number;
    evidenceRequired: number;
    officialSources: number;
  };
  requirements: CatalogSelectionInput;
  evaluations: CatalogEvaluation[];
  blockers: string[];
};

export const componentCatalog: readonly CatalogEntry[] = [
  {
    id: "hiwin-r16-5t3-rsi",
    category: "screw",
    manufacturer: "HIWIN",
    family: "RSI",
    partNumber: "R16-5T3-RSI",
    identityLevel: "part_number",
    sourceUrl: "https://www.hiwin.de/medias/sys_master/hiwinDocumentMedia/h4f/h3a/14745344311326/HIWIN%20CATALOGUE%20BALLSCREWS/HIWIN-CATALOGUE-BALLSCREWS.PDF?attachment=true",
    sourceTitle: "HIWIN — Ballscrews & Accessories",
    checkedAt: "2026-08-31",
    specifications: {
      nominalDiameterMm: 16,
      leadMm: 5,
      dynamicLoadRatingN: 7_310,
      staticLoadRatingN: 13_310,
    },
    notes: "Fuso de esferas com porca cilíndrica e recirculação simples.",
  },
  {
    id: "igus-ds16x10",
    category: "screw",
    manufacturer: "igus",
    family: "dryspin",
    partNumber: "DS16x10",
    identityLevel: "family_configuration",
    sourceUrl: "https://www.igus.com/lead-screws/news/2025-dryspin-news",
    sourceTitle: "igus — dryspin DS16x10",
    checkedAt: "2026-08-31",
    specifications: { nominalDiameterMm: 16, leadMm: 10 },
    notes: "Família de fuso trapezoidal sem lubrificação; a capacidade depende da porca e do ciclo escolhidos.",
  },
  {
    id: "hiwin-hgh15caz0h",
    category: "guide",
    manufacturer: "HIWIN",
    family: "HG",
    partNumber: "HGH15CAZ0H · artigo 5-001622",
    identityLevel: "part_number",
    sourceUrl: "https://www.hiwin.de/en/Products/Linear-guideways/Blocks/Ball-guides/Series-HG-QH/HGH-QHH/HGH15CAZ0H/p/5-001622",
    sourceTitle: "HIWIN — HGH15CAZ0H",
    checkedAt: "2026-08-31",
    specifications: {
      profileSizeMm: 15,
      dynamicLoadRatingN: 14_700,
      staticLoadRatingN: 23_470,
    },
    notes: "Carro estreito perfil 15; o trilho e o comprimento final ainda precisam ser configurados.",
  },
  {
    id: "hiwin-ek10-ef10",
    category: "support",
    manufacturer: "HIWIN",
    family: "Apoios C5",
    partNumber: "EK10-C5 18-000429 + EF10-C5 18-000434",
    identityLevel: "part_number",
    sourceUrl: "https://www.hiwin.de/en/Products/Ballscrews/Driven-nut-unit-AME/R16-05T3-AME/p/R16-05T3-AME",
    sourceTitle: "HIWIN — acessórios R16-05T3-AME",
    checkedAt: "2026-08-31",
    specifications: { nominalDiameterMm: 16 },
    notes: "Par fixo/flutuante listado pelo fabricante para a família R16-05T3-AME; compatibilidade com outra ponta de eixo não é automática.",
  },
  {
    id: "oriental-blh-100w-5",
    category: "drive",
    manufacturer: "Oriental Motor",
    family: "BLH Series",
    partNumber: "BLH · 100 W · 5:1 · freio (configuração pendente)",
    identityLevel: "family_configuration",
    sourceUrl: "https://www.orientalmotor.com/brushless-dc-motors-gear-motors/brushless-dc-motors-gear-motors-blh.html",
    sourceTitle: "Oriental Motor — BLH Series",
    checkedAt: "2026-08-31",
    specifications: {
      ratedPowerW: 100,
      supplyVoltageV: 24,
      minimumRatedTorqueNm: 1.8,
      minimumSpeedRpm: 100,
      maximumSpeedRpm: 3_000,
    },
    notes: "A página oficial confirma a família, potência, tensão, faixa, redutor 5:1 e opção de freio; falta fechar o código do conjunto motor/redutor/driver.",
  },
] as const;

function n(value: number, digits = 2) {
  return Number(value.toFixed(digits));
}

function screwEvaluation(entry: CatalogEntry, input: CatalogSelectionInput): CatalogEvaluation {
  const diameter = entry.specifications.nominalDiameterMm;
  const lead = entry.specifications.leadMm;
  const dynamic = entry.specifications.dynamicLoadRatingN;
  const checks: CatalogCheck[] = [
    { label: "Diâmetro", required: `${input.requiredScrewDiameterMm} mm`, catalog: diameter ? `${diameter} mm` : "não publicado", passed: diameter === input.requiredScrewDiameterMm },
    { label: "Avanço", required: `${input.requiredScrewLeadMm} mm/volta`, catalog: lead ? `${lead} mm/volta` : "não publicado", passed: lead === input.requiredScrewLeadMm },
    { label: "Carga dinâmica", required: `≥ ${input.requiredDynamicLoadN} N`, catalog: dynamic ? `${dynamic} N` : "não publicada nesta fonte", passed: dynamic ? dynamic >= input.requiredDynamicLoadN : null },
  ];
  const rejected = checks.some((check) => check.passed === false);
  return {
    entry,
    status: rejected ? "rejected" : checks.some((check) => check.passed === null) ? "evidence_required" : "candidate",
    checks,
    conclusion: rejected
      ? "Rejeitado para o conceito atual porque não mantém o avanço informado."
      : "Compatível com os requisitos numéricos disponíveis.",
    requiredEvidence: ["Comprimento usinado, condição de apoio, flambagem, velocidade crítica, vida e eficiência na montagem real."],
  };
}

function guideEvaluation(entry: CatalogEntry, input: CatalogSelectionInput): CatalogEvaluation {
  const profile = entry.specifications.profileSizeMm;
  const dynamic = entry.specifications.dynamicLoadRatingN;
  const checks: CatalogCheck[] = [
    { label: "Perfil", required: `${input.requiredGuideSizeMm}`, catalog: profile ? `${profile}` : "não publicado", passed: profile === input.requiredGuideSizeMm },
    { label: "Carga dinâmica por carro", required: `> ${input.requiredDynamicLoadN} N`, catalog: dynamic ? `${dynamic} N` : "não publicada", passed: dynamic ? dynamic > input.requiredDynamicLoadN : null },
  ];
  const rejected = checks.some((check) => check.passed === false);
  return {
    entry,
    status: rejected ? "rejected" : "candidate",
    checks,
    conclusion: rejected ? "Perfil incompatível com a pré-seleção." : "Candidato de catálogo; capacidade nominal supera a carga dinâmica informada.",
    requiredEvidence: ["Calcular momentos por excentricidade, distribuição entre quatro carros, vida, pré-carga e comprimento dos trilhos."],
  };
}

function supportEvaluation(entry: CatalogEntry, input: CatalogSelectionInput): CatalogEvaluation {
  return {
    entry,
    status: "evidence_required",
    checks: [
      { label: "Diâmetro nominal", required: `${input.requiredScrewDiameterMm} mm`, catalog: `${entry.specifications.nominalDiameterMm} mm`, passed: entry.specifications.nominalDiameterMm === input.requiredScrewDiameterMm },
      { label: "Ponta usinada", required: "geometria definida", catalog: "não definida no projeto", passed: null },
    ],
    conclusion: "Família de apoio localizada, mas a compatibilidade depende da ponta usinada e do fuso finalmente escolhido.",
    requiredEvidence: ["Desenho da ponta do eixo, cargas axial/radial, vida dos rolamentos e tolerâncias de montagem."],
  };
}

function driveEvaluation(entry: CatalogEntry, input: CatalogSelectionInput): CatalogEvaluation {
  const specs = entry.specifications;
  const checks: CatalogCheck[] = [
    { label: "Potência", required: `≥ ${input.requiredMotorPowerW} W`, catalog: `${specs.ratedPowerW} W`, passed: Boolean(specs.ratedPowerW && specs.ratedPowerW >= input.requiredMotorPowerW) },
    { label: "Tensão", required: `${input.supplyVoltageV} VDC`, catalog: `${specs.supplyVoltageV} VDC`, passed: specs.supplyVoltageV === input.supplyVoltageV },
    { label: "Torque nominal do redutor", required: `≥ ${input.requiredPeakTorqueNm} N·m`, catalog: `a partir de ${specs.minimumRatedTorqueNm} N·m`, passed: Boolean(specs.minimumRatedTorqueNm && specs.minimumRatedTorqueNm >= input.requiredPeakTorqueNm) },
    { label: "Rotação", required: `${input.requiredScrewSpeedRpm} rpm`, catalog: `${specs.minimumSpeedRpm}–${specs.maximumSpeedRpm} rpm`, passed: Boolean(specs.minimumSpeedRpm && specs.maximumSpeedRpm && input.requiredScrewSpeedRpm >= specs.minimumSpeedRpm && input.requiredScrewSpeedRpm <= specs.maximumSpeedRpm) },
  ];
  return {
    entry,
    status: checks.some((check) => check.passed === false) ? "rejected" : "evidence_required",
    checks,
    conclusion: "A família atende aos valores preliminares, mas ainda não existe um código completo de compra definido.",
    requiredEvidence: ["Código exato do motor, redutor, driver e cabo; curva torque × rotação, corrente, inércia, ciclo térmico e torque do freio."],
  };
}

export function selectCatalogComponents(input: CatalogSelectionInput): CatalogSelectionResult {
  const normalized: CatalogSelectionInput = {
    ...input,
    requiredDynamicLoadN: n(input.requiredDynamicLoadN),
    requiredPeakTorqueNm: n(input.requiredPeakTorqueNm, 3),
    requiredScrewSpeedRpm: n(input.requiredScrewSpeedRpm),
  };
  const evaluations = componentCatalog.map((entry) => {
    if (entry.category === "screw") return screwEvaluation(entry, normalized);
    if (entry.category === "guide") return guideEvaluation(entry, normalized);
    if (entry.category === "support") return supportEvaluation(entry, normalized);
    return driveEvaluation(entry, normalized);
  });
  const candidates = evaluations.filter((item) => item.status === "candidate").length;
  const rejected = evaluations.filter((item) => item.status === "rejected").length;
  const evidenceRequired = evaluations.filter((item) => item.status === "evidence_required").length;
  const hasCompatibleScrew = evaluations.some((item) => item.entry.category === "screw" && item.status === "candidate");

  return {
    kind: "commercial-component-selection",
    projectName: normalized.projectName,
    maturity: "catalog-candidate",
    decision: hasCompatibleScrew ? "candidates_with_pending_evidence" : "blocked_by_catalog_mismatch",
    summary: { candidates, rejected, evidenceRequired, officialSources: new Set(evaluations.map((item) => item.entry.sourceUrl)).size },
    requirements: normalized,
    evaluations,
    blockers: [
      ...(!hasCompatibleScrew ? [`O catálogo inicial não contém fuso Ø ${normalized.requiredScrewDiameterMm} com avanço exato de ${normalized.requiredScrewLeadMm} mm/volta.`] : []),
      "O código completo do conjunto motor, redutor, driver e freio ainda precisa ser fechado.",
      "Momentos das guias e vida dos rolamentos dependem da geometria e do ciclo de trabalho reais.",
      "Preço e disponibilidade não foram consultados e não influenciam esta seleção técnica inicial.",
    ],
  };
}
