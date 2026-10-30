"use client";

import type { ActuatorCadResult } from "@/lib/cad/actuator-cad";

export function LinearActuatorPreview({
  model,
  angle,
  stage,
}: {
  model: ActuatorCadResult;
  angle: number;
  stage: number;
}) {
  return (
    <div className="actuator-preview" aria-label={`Modelo tridimensional conceitual ${model.modelId}`}>
      <div className="axis axis-x" /><div className="axis axis-y" />
      <div className="actuator-model" style={{ transform: `rotateX(-7deg) rotateY(${angle}deg)` }}>
        <div className={`actuator-part actuator-base ${stage >= 1 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-column column-left ${stage >= 2 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-column column-right ${stage >= 2 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-screw ${stage >= 3 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-carriage ${stage >= 4 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-platform ${stage >= 5 ? "installed" : "exploded"}`} />
        <div className={`actuator-part actuator-motor ${stage >= 6 ? "installed" : "exploded"}`}><span>{model.parameters.motorVoltage} V</span></div>
      </div>
      <div className="concept-badge">CONCEITO · NÃO FABRICAR</div>
    </div>
  );
}
