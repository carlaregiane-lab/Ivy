import assert from "node:assert/strict";
import test from "node:test";
import { selectCatalogComponents } from "../lib/catalog/component-catalog.ts";

const requirements = {
  projectName: "Atuador linear vertical",
  requiredScrewDiameterMm: 16,
  requiredScrewLeadMm: 8,
  requiredGuideSizeMm: 15,
  requiredDynamicLoadN: 176.52,
  requiredPeakTorqueNm: 0.963,
  requiredScrewSpeedRpm: 187.5,
  requiredMotorPowerW: 100,
  supplyVoltageV: 24,
};

test("seleciona a guia real e preserva a fonte oficial", () => {
  const result = selectCatalogComponents(requirements);
  const guide = result.evaluations.find((item) => item.entry.category === "guide");

  assert.equal(guide?.status, "candidate");
  assert.equal(guide?.entry.partNumber, "HGH15CAZ0H · artigo 5-001622");
  assert.equal(guide?.entry.specifications.dynamicLoadRatingN, 14_700);
  assert.match(guide?.entry.sourceUrl ?? "", /^https:\/\/www\.hiwin\.de\//);
});

test("rejeita fusos cujo avanço não atende os 8 mm por volta", () => {
  const result = selectCatalogComponents(requirements);
  const screws = result.evaluations.filter((item) => item.entry.category === "screw");

  assert.equal(result.decision, "blocked_by_catalog_mismatch");
  assert.equal(screws.every((item) => item.status === "rejected"), true);
  assert.match(result.blockers[0], /avanço exato de 8 mm/);
});

test("mantém motor e apoios como evidência pendente", () => {
  const result = selectCatalogComponents(requirements);
  const pending = result.evaluations.filter((item) => item.status === "evidence_required");

  assert.deepEqual(pending.map((item) => item.entry.category).sort(), ["drive", "support"]);
  assert.equal(result.summary.officialSources, 5);
});
