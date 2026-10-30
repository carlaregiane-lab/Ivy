import { tool, type UIToolInvocation } from "ai";
import { z } from "zod";
import { sizeLinearActuator } from "@/lib/engineering/actuator-sizing";

export const actuatorSizingInputSchema = z.object({
  projectName: z.string().trim().min(1).max(80),
  payloadKg: z.number().finite().positive().max(500),
  travelMm: z.number().finite().positive().max(1_500),
  targetTimeS: z.number().finite().positive().max(600),
  screwLeadMm: z.number().finite().positive().max(50),
  screwEfficiency: z.number().finite().min(0.1).max(0.95),
  supplyVoltage: z.number().finite().positive().max(600),
  existingStructuralCapacityN: z.number().finite().positive().nullable(),
  targetSafetyFactor: z.number().finite().min(1.5).max(4).default(2),
  dynamicFactor: z.number().finite().min(1).max(3).default(1.5),
});

export const actuatorSizingTool = tool({
  description:
    "Faz o pré-dimensionamento rastreável de um atuador linear vertical e pré-seleciona famílias genéricas de fuso, guias, apoios, motor, estrutura e funções de segurança. Use antes de atualizar o CAD ou sugerir componentes. O resultado não substitui catálogo, análise estrutural ou ensaio.",
  inputSchema: actuatorSizingInputSchema,
  execute: async (input) => sizeLinearActuator(input),
});

export type ActuatorSizingInvocation = UIToolInvocation<typeof actuatorSizingTool>;
