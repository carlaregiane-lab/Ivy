import { tool } from "ai";
import { z } from "zod";

const shortText = z.string().trim().min(1).max(240);

export const projectContextSchema = z.object({
  projectName: z.string().trim().min(1).max(80),
  phase: z.enum(["descoberta", "definicao", "calculos", "conceito", "verificacao"]),
  objective: z.string().trim().max(500).nullable(),
  requirements: z.array(shortText).max(12),
  constraints: z.array(shortText).max(12),
  calculations: z
    .array(
      z.object({
        name: shortText,
        status: z.enum(["necessario", "pronto", "bloqueado"]),
        missingInputs: z.array(shortText).max(6),
      })
    )
    .max(10),
  risks: z
    .array(
      z.object({
        description: shortText,
        severity: z.enum(["baixa", "media", "alta", "critica"]),
        mitigation: z.string().trim().max(300).nullable(),
      })
    )
    .max(10),
  assumptions: z.array(shortText).max(10),
  openQuestions: z.array(shortText).max(8),
  confidence: z.enum(["baixa", "media", "alta"]),
});

export type ProjectContext = z.infer<typeof projectContextSchema>;

export const updateProjectContextTool = tool({
  description:
    "Atualiza a memória estruturada do projeto usando somente fatos da conversa. Preserve dados anteriores válidos, registre lacunas em openQuestions e nunca transforme suposições em requisitos confirmados.",
  inputSchema: projectContextSchema,
  execute: async (context) => context,
});
