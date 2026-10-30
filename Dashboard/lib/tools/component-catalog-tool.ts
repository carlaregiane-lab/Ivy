import { tool, type UIToolInvocation } from "ai";
import { z } from "zod";
import { selectCatalogComponents } from "@/lib/catalog/component-catalog";

export const componentCatalogInputSchema = z.object({
  projectName: z.string().trim().min(1).max(80),
  requiredScrewDiameterMm: z.number().finite().positive().max(100),
  requiredScrewLeadMm: z.number().finite().positive().max(50),
  requiredGuideSizeMm: z.number().finite().positive().max(100),
  requiredDynamicLoadN: z.number().finite().positive().max(1_000_000),
  requiredPeakTorqueNm: z.number().finite().positive().max(10_000),
  requiredScrewSpeedRpm: z.number().finite().positive().max(20_000),
  requiredMotorPowerW: z.number().finite().positive().max(100_000),
  supplyVoltageV: z.number().finite().positive().max(600),
});

export const componentCatalogTool = tool({
  description: "Compara o pré-dimensionamento do atuador com um catálogo local rastreável de componentes comerciais e fontes oficiais. Retorna candidatos, rejeições, lacunas de código e evidências necessárias; nunca equivale a uma autorização de compra ou fabricação.",
  inputSchema: componentCatalogInputSchema,
  execute: async (input) => selectCatalogComponents(input),
});

export type ComponentCatalogInvocation = UIToolInvocation<typeof componentCatalogTool>;
