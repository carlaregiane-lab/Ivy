import { tool, type UIToolInvocation } from "ai";
import { z } from "zod";
import {
  ACCELERATION_UNITS,
  AREA_UNITS,
  FORCE_UNITS,
  LENGTH_UNITS,
  MASS_UNITS,
  POWER_UNITS,
  PRESSURE_UNITS,
  SPEED_UNITS,
  TIME_UNITS,
  TORQUE_UNITS,
  calculateEngineering,
} from "@/lib/engineering/calculations";

const positive = z.number().finite().positive();
const quantity = <T extends readonly [string, ...string[]]>(units: T) =>
  z.object({ value: positive, unit: z.enum(units) });

const calculationSchema = z.discriminatedUnion("calculation", [
  z.object({
    calculation: z.literal("forceFromMass"),
    mass: quantity(MASS_UNITS),
    acceleration: quantity(ACCELERATION_UNITS),
    outputUnit: z.enum(FORCE_UNITS).default("N"),
  }),
  z.object({
    calculation: z.literal("torqueFromForce"),
    force: quantity(FORCE_UNITS),
    leverArm: quantity(LENGTH_UNITS),
    outputUnit: z.enum(TORQUE_UNITS).default("N.m"),
  }),
  z.object({
    calculation: z.literal("pressureFromForce"),
    force: quantity(FORCE_UNITS),
    area: quantity(AREA_UNITS),
    outputUnit: z.enum(PRESSURE_UNITS).default("MPa"),
  }),
  z.object({
    calculation: z.literal("safetyFactor"),
    capacity: positive,
    demand: positive,
  }),
  z.object({
    calculation: z.literal("leadScrewLinearForce"),
    torque: quantity(TORQUE_UNITS),
    lead: quantity(LENGTH_UNITS),
    efficiency: z.number().finite().positive().max(1),
    outputUnit: z.enum(FORCE_UNITS).default("N"),
  }),
  z.object({
    calculation: z.literal("dcPower"),
    voltage: positive,
    current: positive,
    outputUnit: z.enum(POWER_UNITS).default("W"),
  }),
  z.object({
    calculation: z.literal("mechanicalPower"),
    force: quantity(FORCE_UNITS),
    speed: quantity(SPEED_UNITS),
    outputUnit: z.enum(POWER_UNITS).default("W"),
  }),
  z.object({
    calculation: z.literal("linearSpeed"),
    distance: quantity(LENGTH_UNITS),
    time: quantity(TIME_UNITS),
    outputUnit: z.enum(SPEED_UNITS).default("m/s"),
  }),
]);

export const engineeringCalculatorTool = tool({
  description:
    "Executa cálculos determinísticos de engenharia com conversão de unidades. Use sempre que a resposta depender de força, torque, pressão, fator de segurança, força de fuso, potência CC, potência mecânica ou velocidade linear. Não faça essas contas mentalmente.",
  inputSchema: calculationSchema,
  execute: async (input) => calculateEngineering(input),
});

export type EngineeringCalculatorInvocation = UIToolInvocation<typeof engineeringCalculatorTool>;
