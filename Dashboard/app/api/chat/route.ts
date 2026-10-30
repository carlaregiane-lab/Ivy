import {
  createAgentUIStreamResponse,
  createUIMessageStream,
  createUIMessageStreamResponse,
} from "ai";
import { ivyAgent, type IvyAgentUIMessage } from "@/lib/agents/ivy-agent";
import { createLocalIvyScenario } from "@/lib/local-test/local-ivy";
import { hasGatewayAuthentication } from "@/lib/ai/gateway-auth";

export const maxDuration = 60;

const MAX_RECEIVED_MESSAGES = 80;
const MAX_REQUEST_CHARACTERS = 120_000;
const MAX_CONTEXT_MESSAGES = 28;
const REQUESTS_PER_HOUR = 30;

type RateEntry = { count: number; resetAt: number };
type IvyRequest = {
  messages?: unknown;
  sessionId?: string;
};

const globalRateState = globalThis as typeof globalThis & {
  __ivyRateLimits?: Map<string, RateEntry>;
};
const rateLimits = globalRateState.__ivyRateLimits ?? new Map<string, RateEntry>();
globalRateState.__ivyRateLimits = rateLimits;

function normalizedSession(value: unknown) {
  if (typeof value !== "string") return "anonymous";
  return /^[a-zA-Z0-9-]{8,80}$/.test(value) ? value : "anonymous";
}

function requestKey(request: Request, sessionId: string) {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const ip = forwarded || request.headers.get("x-real-ip") || "unknown";
  return `${sessionId}:${ip}`;
}

function canContinue(key: string) {
  const now = Date.now();
  const current = rateLimits.get(key);
  if (!current || current.resetAt <= now) {
    rateLimits.set(key, { count: 1, resetAt: now + 60 * 60 * 1000 });
    return true;
  }
  if (current.count >= REQUESTS_PER_HOUR) return false;
  current.count += 1;
  return true;
}

function normalizeMessages(value: unknown) {
  if (!Array.isArray(value) || value.length === 0) {
    return { error: "Envie uma pergunta para a Ivy." } as const;
  }
  if (value.length > MAX_RECEIVED_MESSAGES) {
    return { error: "Esta conversa ficou grande demais. Inicie uma nova conversa para continuar." } as const;
  }

  let serialized: string;
  try {
    serialized = JSON.stringify(value);
  } catch {
    return { error: "A conversa contém dados inválidos." } as const;
  }
  if (serialized.length > MAX_REQUEST_CHARACTERS) {
    return { error: "O histórico completo ficou grande demais. Inicie uma nova conversa para continuar." } as const;
  }

  const messages = value.filter((item) => {
    if (!item || typeof item !== "object") return false;
    const candidate = item as { id?: unknown; role?: unknown; parts?: unknown };
    return (
      typeof candidate.id === "string" &&
      (candidate.role === "user" || candidate.role === "assistant") &&
      Array.isArray(candidate.parts)
    );
  });

  if (!messages.some((message) => (message as { role?: unknown }).role === "user")) {
    return { error: "Envie uma pergunta para a Ivy." } as const;
  }

  return { messages: messages.slice(-MAX_CONTEXT_MESSAGES) } as const;
}

function streamErrorMessage(error: unknown) {
  console.error("Ivy generation failed", error);
  const message = error instanceof Error ? error.message.toLocaleLowerCase("en-US") : "";
  if (message.includes("credit card") || message.includes("free credits")) {
    return "O cérebro da Ivy está pronto, mas a conta da Vercel ainda precisa ser ativada para liberar as respostas de IA.";
  }
  return "A Ivy não conseguiu concluir esta resposta. Tente novamente em alguns instantes.";
}

function textFromMessage(message: unknown) {
  if (!message || typeof message !== "object") return "";
  const parts = (message as { parts?: unknown }).parts;
  if (!Array.isArray(parts)) return "";
  return parts
    .filter(
      (part): part is { type: "text"; text: string } =>
        Boolean(
          part &&
            typeof part === "object" &&
            (part as { type?: unknown }).type === "text" &&
            typeof (part as { text?: unknown }).text === "string"
        )
    )
    .map((part) => part.text)
    .join("\n");
}

function localTestResponse(messages: IvyAgentUIMessage[]) {
  const projectConversation = messages
    .filter((message) => message.role === "user")
    .map(textFromMessage)
    .join("\n");
  const scenario = createLocalIvyScenario(projectConversation);
  const stream = createUIMessageStream<IvyAgentUIMessage>({
    originalMessages: messages,
    execute: ({ writer }) => {
      const contextCallId = `local-context-${crypto.randomUUID()}`;
      writer.write({
        type: "tool-input-available",
        toolCallId: contextCallId,
        toolName: "updateProjectContext",
        input: scenario.context,
      });
      writer.write({
        type: "tool-output-available",
        toolCallId: contextCallId,
        output: scenario.context,
      });

      scenario.calculations.forEach(({ input, output }, index) => {
        const toolCallId = `local-calculation-${index}-${crypto.randomUUID()}`;
        writer.write({
          type: "tool-input-available",
          toolCallId,
          toolName: "calculateEngineering",
          input,
        });
        writer.write({
          type: "tool-output-available",
          toolCallId,
          output,
        });
      });

      if (scenario.sizing) {
        const sizingCallId = `local-sizing-${crypto.randomUUID()}`;
        writer.write({
          type: "tool-input-available",
          toolCallId: sizingCallId,
          toolName: "sizeLinearActuator",
          input: scenario.sizing.input,
        });
        writer.write({
          type: "tool-output-available",
          toolCallId: sizingCallId,
          output: scenario.sizing.output,
        });
      }

      if (scenario.catalog) {
        const catalogCallId = `local-catalog-${crypto.randomUUID()}`;
        writer.write({
          type: "tool-input-available",
          toolCallId: catalogCallId,
          toolName: "selectCatalogComponents",
          input: scenario.catalog.input,
        });
        writer.write({
          type: "tool-output-available",
          toolCallId: catalogCallId,
          output: scenario.catalog.output,
        });
      }

      const verificationCallId = `local-verification-${crypto.randomUUID()}`;
      writer.write({
        type: "tool-input-available",
        toolCallId: verificationCallId,
        toolName: "assessEngineeringReadiness",
        input: scenario.verification.input,
      });
      writer.write({
        type: "tool-output-available",
        toolCallId: verificationCallId,
        output: scenario.verification.output,
      });

      if (scenario.cad) {
        const cadCallId = `local-cad-${crypto.randomUUID()}`;
        writer.write({
          type: "tool-input-available",
          toolCallId: cadCallId,
          toolName: "createConceptCad",
          input: scenario.cad.input,
        });
        writer.write({
          type: "tool-output-available",
          toolCallId: cadCallId,
          output: scenario.cad.output,
        });
      }

      const textId = `local-summary-${crypto.randomUUID()}`;
      writer.write({ type: "text-start", id: textId });
      writer.write({ type: "text-delta", id: textId, delta: scenario.response });
      writer.write({ type: "text-end", id: textId });
    },
    onError: (error) => {
      console.error("Ivy local test failed", error);
      return "O teste local da Ivy não pôde ser concluído.";
    },
  });

  return createUIMessageStreamResponse({ stream });
}

export function GET() {
  return Response.json({ mode: hasGatewayAuthentication() ? "gateway" : "local" });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as IvyRequest;
    const normalized = normalizeMessages(body.messages);
    if ("error" in normalized) {
      return Response.json({ error: normalized.error }, { status: 400 });
    }

    const sessionId = normalizedSession(body.sessionId);
    if (!canContinue(requestKey(request, sessionId))) {
      return Response.json(
        { error: "Limite temporário atingido. Aguarde antes de enviar outra pergunta." },
        { status: 429 }
      );
    }

    if (!hasGatewayAuthentication()) {
      return localTestResponse(normalized.messages as IvyAgentUIMessage[]);
    }

    return createAgentUIStreamResponse({
      agent: ivyAgent,
      uiMessages: normalized.messages,
      abortSignal: request.signal,
      timeout: { totalMs: 55_000 },
      onError: streamErrorMessage,
    });
  } catch (error) {
    console.error("Ivy chat request failed", error);
    return Response.json({ error: "Não foi possível processar a conversa." }, { status: 500 });
  }
}
