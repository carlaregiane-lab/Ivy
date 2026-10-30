"use client";

import { Tool, ToolContent, ToolHeader } from "@/components/ai-elements/tool";
import type { ActuatorSizingInvocation } from "@/lib/tools/actuator-sizing-tool";

const statusLabel = {
  preselected: "Pré-selecionado",
  resize_required: "Redimensionar",
  evidence_required: "Exige evidência",
} as const;

export function ActuatorSizing({
  invocation,
  onOpen,
}: {
  invocation: ActuatorSizingInvocation;
  onOpen: () => void;
}) {
  const completed = invocation.state === "output-available";
  const failed = invocation.state === "output-error";

  return (
    <Tool className="sizing-tool" defaultOpen={completed || failed}>
      <ToolHeader title="Dimensionamento do atuador" type="tool-sizeLinearActuator" state={invocation.state} />
      <ToolContent>
        {completed ? (
          <div className="sizing-tool-result">
            <div className="sizing-tool-heading">
              <span>PRÉ-DIMENSIONAMENTO · REVISÃO NECESSÁRIA</span>
              <strong>{invocation.output.metrics.proposedStructuralCapacityN} N mínimos propostos</strong>
              <p>Cálculo baseado em carga dinâmica e fator de segurança-alvo; componentes ainda dependem de catálogo e validação.</p>
            </div>
            <div className="sizing-metric-strip">
              <div><span>Carga dinâmica</span><strong>{invocation.output.metrics.designLoadN} N</strong></div>
              <div><span>FS proposto</span><strong>{invocation.output.metrics.proposedSafetyFactor}</strong></div>
              <div><span>Torque de pico</span><strong>{invocation.output.metrics.peakScrewTorqueNm} N·m</strong></div>
              <div><span>Motor</span><strong>{invocation.output.selections.motorNominalPowerW} W</strong></div>
            </div>
            <ul className="sizing-tool-components">
              {invocation.output.components.slice(0, 5).map((component) => (
                <li key={component.id} className={`status-${component.status}`}>
                  <span>{statusLabel[component.status]}</span>
                  <strong>{component.name}</strong>
                  <p>{component.selection}</p>
                </li>
              ))}
            </ul>
            <button className="open-sizing" type="button" onClick={onOpen}>Abrir dimensionamento completo</button>
          </div>
        ) : failed ? (
          <p className="engineering-tool-error">{invocation.errorText}</p>
        ) : (
          <p className="engineering-tool-running">Calculando carga dinâmica, transmissão e margens…</p>
        )}
      </ToolContent>
    </Tool>
  );
}
