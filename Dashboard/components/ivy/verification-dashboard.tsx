import type {
  EngineeringVerificationResult,
  VerificationCheckStatus,
} from "@/lib/engineering/verifications";

const decisionLabel = {
  blocked: "AVANÇO BLOQUEADO",
  conditional: "AVANÇO CONDICIONAL",
  ready_for_review: "PRONTO PARA REVISÃO",
} as const;

const statusLabel: Record<VerificationCheckStatus, string> = {
  approved: "ATENDIDO",
  attention: "ATENÇÃO",
  blocked: "BLOQUEIO",
  evidence_required: "EXIGE EVIDÊNCIA",
};

const categoryLabel = {
  requirements: "Requisitos",
  mechanical: "Mecânica",
  electrical: "Elétrica",
  controls: "Controles",
  validation: "Validação",
} as const;

const severityLabel = {
  low: "BAIXA",
  medium: "MÉDIA",
  high: "ALTA",
  critical: "CRÍTICA",
} as const;

export function VerificationDashboard({
  assessment,
  onBack,
}: {
  assessment: EngineeringVerificationResult | null;
  onBack: () => void;
}) {
  if (!assessment) {
    return (
      <section className="verification-workspace verification-empty" aria-label="Verificações de engenharia">
        <div>
          <span className="verification-kicker">MOTOR DE VERIFICAÇÕES</span>
          <h1>Nenhuma análise registrada</h1>
          <p>Envie um projeto com dados e cálculos para a Ivy gerar a primeira verificação rastreável.</p>
          <button type="button" onClick={onBack}>Voltar à conversa</button>
        </div>
      </section>
    );
  }

  return (
    <section className="verification-workspace" aria-label="Verificações de engenharia">
      <header className="verification-header">
        <div>
          <button type="button" onClick={onBack}>← Voltar à conversa</button>
          <span className="verification-kicker">VERIFICAÇÃO PRELIMINAR · {assessment.projectName}</span>
          <h1>Prontidão e evidências</h1>
          <p>{assessment.summary}</p>
        </div>
        <div className={`verification-score decision-${assessment.decision}`}>
          <span>{decisionLabel[assessment.decision]}</span>
          <strong>{assessment.readinessScore}%</strong>
          <small>ÍNDICE DE PRONTIDÃO</small>
        </div>
      </header>

      <div className="verification-metrics" aria-label="Indicadores das verificações">
        <article className="blocked"><span>BLOQUEIOS</span><strong>{assessment.counts.blocked}</strong></article>
        <article><span>EXIGEM EVIDÊNCIA</span><strong>{assessment.counts.evidence_required}</strong></article>
        <article className="attention"><span>ATENÇÃO</span><strong>{assessment.counts.attention}</strong></article>
        <article className="approved"><span>ATENDIDAS</span><strong>{assessment.counts.approved}</strong></article>
      </div>

      <div className="verification-list">
        <div className="verification-list-heading">
          <span>VERIFICAÇÕES</span>
          <small>{assessment.checks.length} ITENS AVALIADOS</small>
        </div>
        {assessment.checks.map((item) => (
          <article className={`verification-row status-${item.status}`} key={item.id}>
            <div className="verification-row-status">
              <span>{statusLabel[item.status]}</span>
              <small>{severityLabel[item.severity]}</small>
            </div>
            <div className="verification-row-main">
              <small>{categoryLabel[item.category]}</small>
              <h2>{item.title}</h2>
              <p>{item.finding}</p>
            </div>
            <div className="verification-row-evidence">
              <span>EVIDÊNCIA NECESSÁRIA</span>
              <p>{item.requiredEvidence}</p>
              <strong>Próxima ação</strong>
              <p>{item.recommendation}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
