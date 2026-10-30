"use client";

import type { ActuatorSizingResult } from "@/lib/engineering/actuator-sizing";
import type { CatalogSelectionResult } from "@/lib/catalog/component-catalog";

const statusLabel = {
  preselected: "Pré-selecionado",
  resize_required: "Redimensionar",
  evidence_required: "Exige evidência",
} as const;

function formattedCatalogDate(value: string) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export function SizingDashboard({
  sizing,
  catalog,
  onBack,
  onStart,
  onCatalog,
}: {
  sizing: ActuatorSizingResult | null;
  catalog: CatalogSelectionResult | null;
  onBack: () => void;
  onStart: () => void;
  onCatalog: () => void;
}) {
  if (!sizing) {
    return (
      <section className="sizing-workspace sizing-empty" aria-label="Dimensionamento do atuador">
        <div>
          <span className="verification-kicker">DIMENSIONAMENTO</span>
          <h1>O atuador ainda não foi dimensionado</h1>
          <p>A Ivy precisa calcular carga dinâmica, torque, rotação, potência e capacidade estrutural antes de pré-selecionar os componentes.</p>
          <button type="button" onClick={onStart}>Dimensionar agora</button>
        </div>
      </section>
    );
  }

  const readyCount = sizing.components.filter((component) => component.status === "preselected").length;
  const pendingCount = sizing.components.length - readyCount;

  return (
    <section className="sizing-workspace" aria-label="Dimensionamento do atuador">
      <header className="sizing-header">
        <div>
          <button type="button" onClick={onBack}>← Voltar à conversa</button>
          <span>DIMENSIONAMENTO PRELIMINAR · {sizing.projectName}</span>
          <h1>Componentes e margens</h1>
          <p>Pré-seleções calculadas para orientar o próximo CAD. Nenhum item abaixo está liberado para compra ou fabricação sem as evidências indicadas.</p>
        </div>
        <div className="sizing-decision">
          <span>{sizing.decision === "resize_required" ? "REDIMENSIONAMENTO NECESSÁRIO" : "PRÉ-SELEÇÃO CONCLUÍDA"}</span>
          <strong>{readyCount}/{sizing.components.length}</strong>
          <small>{pendingCount} itens ainda exigem ação</small>
        </div>
      </header>

      <div className="sizing-metrics">
        <article><span>CARGA ESTÁTICA</span><strong>{sizing.metrics.staticLoadN} N</strong><small>massa × gravidade</small></article>
        <article><span>CARGA DINÂMICA</span><strong>{sizing.metrics.designLoadN} N</strong><small>fator {sizing.metrics.dynamicFactor}</small></article>
        <article className="accent"><span>CAPACIDADE PROPOSTA</span><strong>{sizing.metrics.proposedStructuralCapacityN} N</strong><small>FS {sizing.metrics.proposedSafetyFactor}</small></article>
        <article><span>FUSO</span><strong>{sizing.metrics.screwSpeedRpm} rpm</strong><small>{sizing.metrics.peakScrewTorqueNm} N·m pico</small></article>
        <article><span>VELOCIDADE</span><strong>{sizing.metrics.linearSpeedMmS} mm/s</strong><small>{sizing.metrics.mechanicalPowerW} W mecânicos</small></article>
        <article><span>MOTOR</span><strong>{sizing.selections.motorNominalPowerW} W</strong><small>redução {sizing.selections.reductionRatio}:1</small></article>
      </div>

      <div className="sizing-list-heading"><span>PRÉ-SELEÇÃO DOS COMPONENTES</span><small>{sizing.components.length} decisões rastreáveis</small></div>
      <div className="sizing-component-list">
        {sizing.components.map((component) => (
          <article key={component.id} className={`sizing-component status-${component.status}`}>
            <div className="sizing-component-status"><span>{statusLabel[component.status]}</span><small>{component.category}</small></div>
            <div><h2>{component.name}</h2><strong>{component.selection}</strong><p>{component.basis}</p></div>
            <div className="sizing-evidence"><span>EVIDÊNCIA NECESSÁRIA</span><p>{component.requiredEvidence}</p></div>
          </article>
        ))}
      </div>

      <aside className="sizing-blockers">
        <div><span>!</span><strong>ANTES DE COMPRAR OU FABRICAR</strong></div>
        <ul>{sizing.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
      </aside>

      <section className="catalog-section" aria-labelledby="catalog-title">
        <div className="catalog-section-heading">
          <div>
            <span>COMPONENTES COMERCIAIS</span>
            <h2 id="catalog-title">Comparação de catálogo</h2>
            <p>Os registros guardam fabricante, código, especificações, fonte oficial e data da consulta.</p>
          </div>
          {!catalog ? <button type="button" onClick={onCatalog}>Comparar agora</button> : null}
        </div>

        {catalog ? (
          <>
            <div className="catalog-summary">
              <article><span>CANDIDATOS</span><strong>{catalog.summary.candidates}</strong></article>
              <article><span>REJEITADOS</span><strong>{catalog.summary.rejected}</strong></article>
              <article><span>EVIDÊNCIA</span><strong>{catalog.summary.evidenceRequired}</strong></article>
              <article><span>FONTES OFICIAIS</span><strong>{catalog.summary.officialSources}</strong></article>
            </div>
            <div className="catalog-evaluations">
              {catalog.evaluations.map((evaluation) => (
                <article className={`catalog-evaluation catalog-status-${evaluation.status}`} key={evaluation.entry.id}>
                  <header>
                    <span>{evaluation.status === "candidate" ? "CANDIDATO" : evaluation.status === "rejected" ? "REJEITADO" : "EXIGE EVIDÊNCIA"}</span>
                    <small>{evaluation.entry.category}</small>
                  </header>
                  <h3>{evaluation.entry.manufacturer}</h3>
                  <strong>{evaluation.entry.partNumber}</strong>
                  <p>{evaluation.conclusion}</p>
                  <dl>
                    {evaluation.checks.map((check) => (
                      <div key={check.label}>
                        <dt>{check.label}</dt>
                        <dd className={check.passed === true ? "passed" : check.passed === false ? "failed" : "pending"}>
                          {check.catalog}
                          <small>exigido: {check.required}</small>
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <a href={evaluation.entry.sourceUrl} target="_blank" rel="noreferrer">Abrir fonte oficial ↗</a>
                  <small>Consultada em {formattedCatalogDate(evaluation.entry.checkedAt)}</small>
                </article>
              ))}
            </div>
            <aside className="catalog-blockers">
              <strong>DECISÃO: SELEÇÃO AINDA BLOQUEADA</strong>
              <ul>{catalog.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
            </aside>
          </>
        ) : (
          <div className="catalog-empty"><p>O pré-dimensionamento está pronto. Execute a comparação para procurar candidatos sem alterar silenciosamente os requisitos.</p></div>
        )}
      </section>
    </section>
  );
}
