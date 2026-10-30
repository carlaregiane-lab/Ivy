import { createActuatorCad } from "@/lib/cad/actuator-cad";
import { generateActuatorStl } from "@/lib/cad/stl";

function positive(search: URLSearchParams, key: string, fallback: number, maximum: number) {
  const value = Number(search.get(key));
  return Number.isFinite(value) && value > 0 ? Math.min(value, maximum) : fallback;
}

export function GET(request: Request) {
  const search = new URL(request.url).searchParams;
  const model = createActuatorCad({
    projectName: (search.get("projectName") || "Atuador linear vertical").slice(0, 80),
    payloadKg: positive(search, "payloadKg", 12, 500),
    travelMm: positive(search, "travelMm", 300, 1500),
    screwLeadMm: positive(search, "screwLeadMm", 8, 50),
    motorVoltage: positive(search, "motorVoltage", 24, 600),
    sizing: search.get("motorPowerW") && Number(search.get("motorPowerW")) > 0
      ? {
          screwNominalDiameterMm: positive(search, "screwDiameterMm", 16, 80),
          guideProfileSizeMm: positive(search, "guideSizeMm", 15, 55),
          guideCarriages: 4,
          motorNominalPowerW: positive(search, "motorPowerW", 100, 20_000),
          reductionRatio: positive(search, "reductionRatio", 5, 100),
          proposedStructuralCapacityN: positive(search, "structuralCapacityN", 400, 1_000_000),
        }
      : null,
  });
  const stl = generateActuatorStl(model);
  return new Response(stl, {
    headers: {
      "Content-Type": "model/stl; charset=utf-8",
      "Content-Disposition": `attachment; filename="${model.modelId.toLowerCase()}.stl"`,
      "Cache-Control": "private, max-age=0, must-revalidate",
    },
  });
}
