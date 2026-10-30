"use client";

import {
  Tool,
  ToolContent,
  ToolHeader,
} from "@/components/ai-elements/tool";
import type { EngineeringCalculatorInvocation } from "@/lib/tools/engineering-calculator-tool";

export function EngineeringCalculation({
  invocation,
}: {
  invocation: EngineeringCalculatorInvocation;
}) {
  const completed = invocation.state === "output-available";
  const failed = invocation.state === "output-error";

  return (
    <Tool className="engineering-calculation" defaultOpen={completed || failed}>
      <ToolHeader
        title="Cálculo de engenharia"
        type="tool-calculateEngineering"
        state={invocation.state}
      />
      <ToolContent>
        {completed ? (
          <div className="engineering-result">
            <div className="engineering-result-heading">
              <span>{invocation.output.label}</span>
              <strong>{invocation.output.result.formatted}</strong>
            </div>
            <dl>
              <div>
                <dt>Fórmula</dt>
                <dd>{invocation.output.formula}</dd>
              </div>
              <div>
                <dt>Substituição</dt>
                <dd>{invocation.output.substitution}</dd>
              </div>
            </dl>
            {invocation.output.warnings.length > 0 ? (
              <ul className="engineering-warnings">
                {invocation.output.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : failed ? (
          <p className="engineering-tool-error">{invocation.errorText}</p>
        ) : (
          <p className="engineering-tool-running">Validando dados e unidades…</p>
        )}
      </ToolContent>
    </Tool>
  );
}
