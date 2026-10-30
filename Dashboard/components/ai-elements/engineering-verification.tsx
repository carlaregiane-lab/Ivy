"use client";

import { Tool, ToolContent, ToolHeader } from "@/components/ai-elements/tool";
import type { EngineeringVerificationInvocation } from "@/lib/tools/engineering-verification-tool";

const decisionLabel = {
  blocked: "Avanço bloqueado",
  conditional: "Avanço condicional",
  ready_for_review: "Pronto para revisão",
} as const;

const statusLabel = {
  approved: "Atendido",
  attention: "Atenção",
  blocked: "Bloqueio",
  evidence_required: "Exige evidência",
} as const;

export function EngineeringVerification({
  invocation,
}: {
  invocation: EngineeringVerificationInvocation;
}) {
  const completed = invocation.state === "output-available";
  const failed = invocation.state === "output-error";

  return (
    <Tool className="verification-tool" defaultOpen={completed || failed}>
      <ToolHeader
        title="Verificação de engenharia"
        type="tool-assessEngineeringReadiness"
        state={invocation.state}
      />
      <ToolContent>
        {completed ? (
          <div className={`verification-result decision-${invocation.output.decision}`}>
            <div className="verification-result-heading">
              <span>{decisionLabel[invocation.output.decision]}</span>
              <strong>{invocation.output.readinessScore}%</strong>
            </div>
            <p>{invocation.output.summary}</p>
            <div className="verification-counts" aria-label="Resumo das verificações">
              <span className="blocked">{invocation.output.counts.blocked} bloqueios</span>
              <span>{invocation.output.counts.evidence_required} pendências</span>
              <span className="approved">{invocation.output.counts.approved} atendidas</span>
            </div>
            <ul className="verification-checks-compact">
              {invocation.output.checks.map((item) => (
                <li className={`status-${item.status}`} key={item.id}>
                  <span>{statusLabel[item.status]}</span>
                  <strong>{item.title}</strong>
                  <p>{item.finding}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : failed ? (
          <p className="engineering-tool-error">{invocation.errorText}</p>
        ) : (
          <p className="engineering-tool-running">Comparando riscos, evidências e critérios…</p>
        )}
      </ToolContent>
    </Tool>
  );
}
