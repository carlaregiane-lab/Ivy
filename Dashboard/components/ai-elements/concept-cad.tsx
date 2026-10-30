"use client";

import { Tool, ToolContent, ToolHeader } from "@/components/ai-elements/tool";
import type { ConceptCadInvocation } from "@/lib/tools/concept-cad-tool";

export function ConceptCad({
  invocation,
  onOpen,
}: {
  invocation: ConceptCadInvocation;
  onOpen: () => void;
}) {
  const completed = invocation.state === "output-available";
  const failed = invocation.state === "output-error";

  return (
    <Tool className="concept-cad-tool" defaultOpen={completed || failed}>
      <ToolHeader title="CAD conceitual paramétrico" type="tool-createConceptCad" state={invocation.state} />
      <ToolContent>
        {completed ? (
          <div className="concept-cad-result">
            <div>
              <span>{invocation.output.modelId} · {invocation.output.revision}</span>
              <strong>{invocation.output.title}</strong>
              <p>Modelo 3D conceitual e desenho técnico gerados a partir dos parâmetros informados.</p>
            </div>
            <dl>
              <div><dt>Carga</dt><dd>{invocation.output.parameters.payloadKg} kg</dd></div>
              <div><dt>Curso</dt><dd>{invocation.output.parameters.travelMm} mm</dd></div>
              <div><dt>Fuso</dt><dd>{invocation.output.parameters.screwLeadMm} mm/volta</dd></div>
              <div><dt>Motor</dt><dd>{invocation.output.parameters.motorVoltage} V</dd></div>
            </dl>
            <p className="concept-warning">Conceito para estudo — ainda não liberado para fabricação.</p>
            <div className="concept-cad-actions">
              <button type="button" onClick={onOpen}>Abrir modelo 3D</button>
              <a href={invocation.output.downloadUrl} download>Baixar STL</a>
            </div>
          </div>
        ) : failed ? (
          <p className="engineering-tool-error">{invocation.errorText}</p>
        ) : (
          <p className="engineering-tool-running">Construindo a geometria paramétrica…</p>
        )}
      </ToolContent>
    </Tool>
  );
}
