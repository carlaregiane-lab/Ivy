import { tool, type UIToolInvocation } from "ai";
import { z } from "zod";
import { assessEngineeringReadiness } from "@/lib/engineering/verifications";

const optionalBoolean = z.boolean().nullable();
const optionalPositive = z.number().finite().positive().nullable();

export const engineeringVerificationInputSchema = z.object({
  projectName: z.string().trim().min(1).max(80),
  verticalLoad: z.boolean(),
  movingMechanism: z.boolean(),
  electricalSystem: z.boolean(),
  loadForceN: optionalPositive,
  actuatorForceN: optionalPositive,
  safetyFactor: optionalPositive,
  mechanicalRetention: optionalBoolean,
  limitSwitches: optionalBoolean,
  emergencyStop: optionalBoolean,
  guarding: optionalBoolean,
  electricalProtection: optionalBoolean,
  dutyCycleDefined: optionalBoolean,
  evidence: z
    .array(
      z.object({
        kind: z.enum(["calculation", "drawing", "datasheet", "test", "inspection"]),
        description: z.string().trim().min(1).max(240),
      })
    )
    .max(30),
});

export const engineeringVerificationTool = tool({
  description:
    "Avalia prontidão, riscos e evidências de um projeto de engenharia. Use depois de atualizar o contexto e concluir os cálculos relevantes, antes de afirmar que o projeto pode avançar, ser validado ou fabricado.",
  inputSchema: engineeringVerificationInputSchema,
  execute: async (input) => assessEngineeringReadiness(input),
});

export type EngineeringVerificationInvocation = UIToolInvocation<
  typeof engineeringVerificationTool
>;
