export type VerificationEvidence = {
  kind: "calculation" | "drawing" | "datasheet" | "test" | "inspection";
  description: string;
};

export type EngineeringVerificationInput = {
  projectName: string;
  verticalLoad: boolean;
  movingMechanism: boolean;
  electricalSystem: boolean;
  loadForceN: number | null;
  actuatorForceN: number | null;
  safetyFactor: number | null;
  mechanicalRetention: boolean | null;
  limitSwitches: boolean | null;
  emergencyStop: boolean | null;
  guarding: boolean | null;
  electricalProtection: boolean | null;
  dutyCycleDefined: boolean | null;
  evidence: VerificationEvidence[];
};

export type VerificationCheckStatus = "approved" | "attention" | "blocked" | "evidence_required";
export type VerificationSeverity = "low" | "medium" | "high" | "critical";

export type VerificationCheck = {
  id: string;
  title: string;
  category: "requirements" | "mechanical" | "electrical" | "controls" | "validation";
  severity: VerificationSeverity;
  status: VerificationCheckStatus;
  finding: string;
  requiredEvidence: string;
  recommendation: string;
};

export type EngineeringVerificationResult = {
  projectName: string;
  decision: "blocked" | "conditional" | "ready_for_review";
  readinessScore: number;
  summary: string;
  counts: Record<VerificationCheckStatus, number>;
  checks: VerificationCheck[];
};

const severityWeight: Record<VerificationSeverity, number> = {
  low: 1,
  medium: 2,
  high: 4,
  critical: 6,
};

const statusCredit: Record<VerificationCheckStatus, number> = {
  approved: 1,
  attention: 0.5,
  evidence_required: 0.2,
  blocked: 0,
};

function check(value: VerificationCheck) {
  return value;
}

function booleanCheck(options: {
  id: string;
  title: string;
  category: VerificationCheck["category"];
  severity: VerificationSeverity;
  value: boolean | null;
  approvedFinding: string;
  missingFinding: string;
  requiredEvidence: string;
  recommendation: string;
  falseIsBlocked?: boolean;
}) {
  const status: VerificationCheckStatus =
    options.value === true
      ? "approved"
      : options.value === false && options.falseIsBlocked
        ? "blocked"
        : "evidence_required";
  return check({
    id: options.id,
    title: options.title,
    category: options.category,
    severity: options.severity,
    status,
    finding: options.value === true ? options.approvedFinding : options.missingFinding,
    requiredEvidence: options.requiredEvidence,
    recommendation: options.recommendation,
  });
}

function score(checks: VerificationCheck[]) {
  const totalWeight = checks.reduce((sum, item) => sum + severityWeight[item.severity], 0);
  const earnedWeight = checks.reduce(
    (sum, item) => sum + severityWeight[item.severity] * statusCredit[item.status],
    0
  );
  return totalWeight ? Math.round((earnedWeight / totalWeight) * 100) : 0;
}

export function assessEngineeringReadiness(
  input: EngineeringVerificationInput
): EngineeringVerificationResult {
  const checks: VerificationCheck[] = [];

  checks.push(
    input.loadForceN !== null
      ? check({
          id: "load-definition",
          title: "Carga de projeto definida",
          category: "requirements",
          severity: "high",
          status: "approved",
          finding: `Carga estática registrada: ${input.loadForceN.toLocaleString("pt-BR")} N.`,
          requiredEvidence: "Cálculo rastreável da carga e das combinações aplicáveis.",
          recommendation: "Acrescentar cargas dinâmicas, impactos e excentricidades quando aplicáveis.",
        })
      : check({
          id: "load-definition",
          title: "Carga de projeto definida",
          category: "requirements",
          severity: "high",
          status: "blocked",
          finding: "A carga de projeto ainda não foi quantificada.",
          requiredEvidence: "Cálculo rastreável da carga em newtons.",
          recommendation: "Definir massa, aceleração, orientação e casos críticos de carregamento.",
        })
  );

  if (input.safetyFactor === null) {
    checks.push(
      check({
        id: "safety-margin",
        title: "Margem estrutural",
        category: "mechanical",
        severity: "high",
        status: "evidence_required",
        finding: "O fator de segurança não foi demonstrado.",
        requiredEvidence: "Capacidade admissível, demanda e critério de aceitação aplicável.",
        recommendation: "Calcular a margem para todos os modos de falha relevantes.",
      })
    );
  } else if (input.safetyFactor < 1) {
    checks.push(
      check({
        id: "safety-margin",
        title: "Margem estrutural",
        category: "mechanical",
        severity: "critical",
        status: "blocked",
        finding: `Fator de segurança ${input.safetyFactor.toLocaleString("pt-BR")} menor que 1.`,
        requiredEvidence: "Novo dimensionamento com capacidade superior à demanda.",
        recommendation: "Interromper o avanço e redimensionar o conjunto.",
      })
    );
  } else if (input.safetyFactor < 1.5) {
    checks.push(
      check({
        id: "safety-margin",
        title: "Margem estrutural",
        category: "mechanical",
        severity: "high",
        status: "blocked",
        finding: `Fator de segurança ${input.safetyFactor.toLocaleString("pt-BR")} com margem estreita.`,
        requiredEvidence: "Critério de aceitação documentado e revisão das cargas reais.",
        recommendation: "Aumentar a capacidade ou reduzir a demanda antes de liberar o conceito.",
      })
    );
  } else {
    checks.push(
      check({
        id: "safety-margin",
        title: "Margem estrutural",
        category: "mechanical",
        severity: "high",
        status: "approved",
        finding: `Fator de segurança preliminar: ${input.safetyFactor.toLocaleString("pt-BR")}.`,
        requiredEvidence: "Memória de cálculo e critério de aceitação documentado.",
        recommendation: "Confirmar materiais, tolerâncias e casos dinâmicos.",
      })
    );
  }

  if (input.loadForceN !== null && input.actuatorForceN !== null) {
    const ratio = input.actuatorForceN / input.loadForceN;
    checks.push(
      check({
        id: "actuator-capacity",
        title: "Capacidade preliminar do atuador",
        category: "mechanical",
        severity: "high",
        status: ratio >= 1.5 ? "approved" : ratio >= 1 ? "attention" : "blocked",
        finding: `Relação entre força idealizada e carga: ${ratio.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}.`,
        requiredEvidence: "Curva real do atuador, rendimento, flambagem e limites do conjunto.",
        recommendation: "Validar a capacidade real com perdas, aceleração e pior condição de operação.",
      })
    );
  }

  if (input.verticalLoad) {
    checks.push(
      booleanCheck({
        id: "vertical-retention",
        title: "Retenção da carga vertical",
        category: "mechanical",
        severity: "critical",
        value: input.mechanicalRetention,
        approvedFinding: "Foi informado um meio de retenção da carga.",
        missingFinding: "Não há evidência de retenção da carga em perda de energia ou falha da transmissão.",
        requiredEvidence: "Desenho e teste do freio, trava, contrapeso ou solução equivalente.",
        recommendation: "Definir uma retenção independente e validar a falha segura.",
        falseIsBlocked: true,
      })
    );
  }

  if (input.movingMechanism) {
    checks.push(
      booleanCheck({
        id: "travel-limits",
        title: "Limites de curso",
        category: "controls",
        severity: "high",
        value: input.limitSwitches,
        approvedFinding: "Os limites de curso foram informados.",
        missingFinding: "Não há evidência de detecção e limitação segura do fim de curso.",
        requiredEvidence: "Diagrama, lista de componentes e teste funcional dos limites.",
        recommendation: "Prever limites funcionais e uma barreira independente contra sobrecurso.",
        falseIsBlocked: true,
      }),
      booleanCheck({
        id: "emergency-stop",
        title: "Parada de emergência",
        category: "controls",
        severity: "high",
        value: input.emergencyStop,
        approvedFinding: "A parada de emergência foi informada.",
        missingFinding: "A necessidade e a arquitetura da parada de emergência não foram demonstradas.",
        requiredEvidence: "Análise de risco, circuito e teste da função de parada.",
        recommendation: "Definir a estratégia de parada conforme os riscos e o modo de operação.",
      }),
      booleanCheck({
        id: "guarding",
        title: "Proteção contra partes móveis",
        category: "mechanical",
        severity: "high",
        value: input.guarding,
        approvedFinding: "Foi informada proteção contra acesso às partes móveis.",
        missingFinding: "Pontos de esmagamento, cisalhamento ou aprisionamento ainda não têm proteção demonstrada.",
        requiredEvidence: "Desenho das proteções e análise das zonas de acesso.",
        recommendation: "Mapear zonas perigosas e definir proteção física ou intertravada.",
      })
    );
  }

  if (input.electricalSystem) {
    checks.push(
      booleanCheck({
        id: "electrical-protection",
        title: "Proteção elétrica",
        category: "electrical",
        severity: "high",
        value: input.electricalProtection,
        approvedFinding: "Foram informadas proteções elétricas básicas.",
        missingFinding: "Não há evidência de proteção contra sobrecorrente, curto-circuito e falhas de alimentação.",
        requiredEvidence: "Diagrama elétrico, especificação das proteções e verificação de dimensionamento.",
        recommendation: "Definir proteção, seccionamento, aterramento e condutores aplicáveis.",
      })
    );
  }

  if (input.movingMechanism || input.electricalSystem) {
    checks.push(
      booleanCheck({
        id: "duty-cycle",
        title: "Ciclo de trabalho e aquecimento",
        category: "requirements",
        severity: "medium",
        value: input.dutyCycleDefined,
        approvedFinding: "O ciclo de trabalho foi informado.",
        missingFinding: "Frequência, duração e intervalo dos movimentos ainda não foram definidos.",
        requiredEvidence: "Perfil de missão e verificação térmica dos componentes.",
        recommendation: "Definir o ciclo de trabalho antes de selecionar motor, acionamento e transmissão.",
      })
    );
  }

  const hasValidationEvidence = input.evidence.some(
    (item) => item.kind === "test" || item.kind === "inspection"
  );
  checks.push(
    check({
      id: "validation-evidence",
      title: "Evidência de validação",
      category: "validation",
      severity: "medium",
      status: hasValidationEvidence ? "approved" : "evidence_required",
      finding: hasValidationEvidence
        ? "Há evidência registrada de teste ou inspeção."
        : "Ainda não há teste ou inspeção registrados para o conceito.",
      requiredEvidence: "Plano de teste, critérios de aceitação e resultados rastreáveis.",
      recommendation: "Criar um plano de validação antes da liberação para fabricação.",
    })
  );

  const counts: Record<VerificationCheckStatus, number> = {
    approved: 0,
    attention: 0,
    blocked: 0,
    evidence_required: 0,
  };
  checks.forEach((item) => {
    counts[item.status] += 1;
  });

  const decision = counts.blocked
    ? "blocked"
    : counts.attention || counts.evidence_required
      ? "conditional"
      : "ready_for_review";
  const summary =
    decision === "blocked"
      ? `Avanço bloqueado por ${counts.blocked} verificação${counts.blocked === 1 ? "" : "ões"}.`
      : decision === "conditional"
        ? "O conceito pode continuar em desenvolvimento, mas ainda exige evidências e decisões."
        : "As verificações preliminares estão atendidas; o projeto pode seguir para revisão técnica.";

  return {
    projectName: input.projectName,
    decision,
    readinessScore: score(checks),
    summary,
    counts,
    checks,
  };
}
