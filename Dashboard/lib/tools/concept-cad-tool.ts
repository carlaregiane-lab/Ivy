import { tool, type UIToolInvocation } from "ai";
import { z } from "zod";
import { createActuatorCad } from "@/lib/cad/actuator-cad";

export const conceptCadInputSchema = z.object({
  projectName: z.string().trim().min(1).max(80),
  payloadKg: z.number().finite().positive().max(500),
  travelMm: z.number().finite().positive().max(1500),
  screwLeadMm: z.number().finite().positive().max(50),
  motorVoltage: z.number().finite().positive().max(600),
  targetTimeS: z.number().finite().positive().max(600).nullable().optional(),
  sizing: z.object({
    screwNominalDiameterMm: z.number().finite().positive().max(80),
    guideProfileSizeMm: z.number().finite().positive().max(55),
    guideCarriages: z.number().int().min(2).max(8),
    motorNominalPowerW: z.number().finite().positive().max(20_000),
    reductionRatio: z.number().finite().positive().max(100),
    proposedStructuralCapacityN: z.number().finite().positive().max(1_000_000),
  }).nullable().optional(),
});

export const conceptCadTool = tool({
  description:
    "Cria um CAD conceitual paramétrico de um atuador linear vertical, com modelo 3D, desenho técnico e STL. Use somente quando carga, curso, avanço do fuso e tensão forem conhecidos. Nunca apresente o resultado como pronto para fabricação.",
  inputSchema: conceptCadInputSchema,
  execute: async (input) => createActuatorCad(input),
});

export type ConceptCadInvocation = UIToolInvocation<typeof conceptCadTool>;
