"use client";

import { Tool, ToolContent, ToolHeader } from "@/components/ai-elements/tool";
import type { ComponentCatalogInvocation } from "@/lib/tools/component-catalog-tool";

const statusLabel = {
  candidate: "Candidato",
  rejected: "Rejeitado",
  evidence_required: "Exige evidência",
} as const;

export function ComponentCatalog({
  invocation,
  onOpen,
}: {
  invocation: ComponentCatalogInvocation;
  onOpen: () => void;
}) {
  const completed = invocation.state === "output-available";
  const failed = invocation.state === "output-error";

  return (
    <Tool className="catalog-tool" defaultOpen={completed || failed}>
      <ToolHeader title="Seleção de componentes comerciais" type="tool-selectCatalogComponents" state={invocation.state} />
      <ToolContent>
        {completed ? (
          <div className="catalog-tool-result">
            <div className="catalog-tool-heading">
              <span>CATÁLOGO RASTREÁVEL · FONTES OFICIAIS</span>
              <strong>{invocation.output.summary.candidates} candidato compatível</strong>
              <p>{invocation.output.summary.rejected} itens rejeitados e {invocation.output.summary.evidenceRequired} ainda dependentes de evidência.</p>
            </div>
            <ul className="catalog-tool-items">
              {invocation.output.evaluations.map((evaluation) => (
                <li className={`catalog-status-${evaluation.status}`} key={evaluation.entry.id}>
                  <span>{statusLabel[evaluation.status]}</span>
                  <strong>{evaluation.entry.manufacturer} · {evaluation.entry.partNumber}</strong>
                  <p>{evaluation.conclusion}</p>
                </li>
              ))}
            </ul>
            <button className="open-sizing" type="button" onClick={onOpen}>Abrir comparação de catálogo</button>
          </div>
        ) : failed ? (
          <p className="engineering-tool-error">{invocation.errorText}</p>
        ) : (
          <p className="engineering-tool-running">Comparando requisitos, códigos e fontes oficiais…</p>
        )}
      </ToolContent>
    </Tool>
  );
}
