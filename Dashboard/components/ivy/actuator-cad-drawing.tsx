import type { ActuatorCadResult } from "@/lib/cad/actuator-cad";

export function ActuatorCadDrawing({ model }: { model: ActuatorCadResult }) {
  const { overallWidthMm, overallHeightMm, travelMm } = model.parameters;
  return (
    <div
      className="actuator-drawing"
      role="img"
      aria-label={`Desenho técnico conceitual ${model.modelId}`}
    >
      <svg viewBox="0 0 760 520" role="img">
        <title>Vista frontal e lateral do atuador linear conceitual</title>
        <g className="drawing-lines">
          <rect x="115" y="420" width="260" height="28" rx="2" />
          <rect x="145" y="72" width="18" height="348" />
          <rect x="327" y="72" width="18" height="348" />
          <rect x="182" y="242" width="126" height="52" />
          <rect x="155" y="226" width="180" height="16" />
          <line x1="245" y1="72" x2="245" y2="420" className="screw-line" />
          <rect x="207" y="448" width="76" height="52" />
          <circle cx="245" cy="474" r="13" />
          <rect x="505" y="420" width="118" height="28" />
          <rect x="526" y="72" width="76" height="348" />
          <rect x="504" y="242" width="120" height="52" />
          <line x1="92" y1="72" x2="92" y2="448" className="dimension" />
          <line x1="84" y1="72" x2="100" y2="72" /><line x1="84" y1="448" x2="100" y2="448" />
          <line x1="115" y1="478" x2="375" y2="478" className="dimension" />
          <line x1="115" y1="470" x2="115" y2="486" /><line x1="375" y1="470" x2="375" y2="486" />
          <line x1="390" y1="104" x2="390" y2="404" className="dimension accent" />
        </g>
        <g className="drawing-copy">
          <text x="65" y="270" transform="rotate(-90 65 270)">{overallHeightMm} mm TOTAL</text>
          <text x="202" y="503">{overallWidthMm} mm</text>
          <text x="407" y="270" transform="rotate(-90 407 270)">CURSO {travelMm} mm</text>
          <text x="115" y="52">VISTA FRONTAL</text>
          <text x="505" y="52">VISTA LATERAL</text>
          <text x="505" y="486">{model.modelId} · {model.revision}</text>
        </g>
      </svg>
      <span>DESENHO CONCEITUAL · COTAS DE ENVOLTÓRIA</span>
    </div>
  );
}
