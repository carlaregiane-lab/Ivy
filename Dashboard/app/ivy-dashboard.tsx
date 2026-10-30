"use client";

import { useChat } from "@ai-sdk/react";
import { EngineeringCalculation } from "@/components/ai-elements/engineering-calculation";
import { EngineeringVerification } from "@/components/ai-elements/engineering-verification";
import { ConceptCad } from "@/components/ai-elements/concept-cad";
import { ActuatorSizing } from "@/components/ai-elements/actuator-sizing";
import { ComponentCatalog } from "@/components/ai-elements/component-catalog";
import { MessageResponse } from "@/components/ai-elements/message";
import { ActuatorCadDrawing } from "@/components/ivy/actuator-cad-drawing";
import { LinearActuatorPreview } from "@/components/ivy/linear-actuator-preview";
import { ProjectMenu } from "@/components/ivy/project-menu";
import { SizingDashboard } from "@/components/ivy/sizing-dashboard";
import { VerificationDashboard } from "@/components/ivy/verification-dashboard";
import type { IvyAgentUIMessage } from "@/lib/agents/ivy-agent";
import type { ActuatorCadResult } from "@/lib/cad/actuator-cad";
import type { EngineeringVerificationResult } from "@/lib/engineering/verifications";
import type { ActuatorSizingResult } from "@/lib/engineering/actuator-sizing";
import type { CatalogSelectionResult } from "@/lib/catalog/component-catalog";
import {
  activeProject,
  addProject,
  archiveProject,
  createProjectStore,
  createRevision,
  duplicateProject,
  loadProjectStore,
  renameProject,
  saveProjectStore,
  selectProject,
  updateProjectMessages,
  type IvyProjectStore,
} from "@/lib/projects/project-store";
import type { ProjectContext } from "@/lib/tools/project-context-tool";
import { DefaultChatTransport } from "ai";
import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";

const assemblySteps = [
  { name: "Estrutura-base", detail: "150 × 60 × 10 mm" },
  { name: "Guias lineares", detail: "Ø 8 · distância 32 mm" },
  { name: "Carros opostos", detail: "curso simétrico 25 mm" },
  { name: "Dedos de contato", detail: "abertura 40–90 mm" },
  { name: "Fuso central", detail: "avanço hipotético 8 mm" },
];

const parameters = [
  ["Carga", "1,5 kg"],
  ["Abertura", "40–90 mm"],
  ["Elevação", "300 mm / 2 s"],
  ["Alimentação", "12 V"],
];

const suggestions = [
  { icon: "⌁", label: "Iniciar projeto", prompt: "Quero iniciar um novo projeto de engenharia. Ajude-me a transformar minha ideia em requisitos claros e mensuráveis." },
  { icon: "◇", label: "Revisar uma ideia", prompt: "Quero descrever uma ideia de engenharia para você revisar. Diga quais dados precisa primeiro." },
  { icon: "∑", label: "Planejar cálculos", prompt: "Ajude-me a identificar os cálculos necessários para o projeto que vou descrever." },
  { icon: "✓", label: "Analisar riscos", prompt: "Quero analisar os riscos preliminares de um projeto de engenharia que vou descrever." },
];

const SESSION_KEY = "ivy:anonymous-session:v1";

function getSessionId() {
  try {
    const current = window.localStorage.getItem(SESSION_KEY);
    if (current) return current;
    const created = window.crypto.randomUUID();
    window.localStorage.setItem(SESSION_KEY, created);
    return created;
  } catch {
    return "ivy-browser-session";
  }
}

function messageText(message: IvyAgentUIMessage) {
  return message.parts
    .filter((part): part is Extract<IvyAgentUIMessage["parts"][number], { type: "text" }> => part.type === "text")
    .map((part) => part.text)
    .join("\n");
}

function latestCad(messages: IvyAgentUIMessage[]): ActuatorCadResult | null {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const parts = messages[messageIndex].parts;
    for (let partIndex = parts.length - 1; partIndex >= 0; partIndex -= 1) {
      const part = parts[partIndex];
      if (part.type === "tool-createConceptCad" && part.state === "output-available") return part.output;
    }
  }
  return null;
}

function latestSizing(messages: IvyAgentUIMessage[]): ActuatorSizingResult | null {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const parts = messages[messageIndex].parts;
    for (let partIndex = parts.length - 1; partIndex >= 0; partIndex -= 1) {
      const part = parts[partIndex];
      if (part.type === "tool-sizeLinearActuator" && part.state === "output-available") return part.output;
    }
  }
  return null;
}

function latestCatalog(messages: IvyAgentUIMessage[]): CatalogSelectionResult | null {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const parts = messages[messageIndex].parts;
    for (let partIndex = parts.length - 1; partIndex >= 0; partIndex -= 1) {
      const part = parts[partIndex];
      if (part.type === "tool-selectCatalogComponents" && part.state === "output-available") return part.output;
    }
  }
  return null;
}

function projectLabelFromMessages(messages: IvyAgentUIMessage[]) {
  const userMessages = messages.filter((message) => message.role === "user");
  if (!userMessages.length) return "Novo projeto";
  const projectMessage =
    userMessages.find(
      (message) => !suggestions.some((suggestion) => suggestion.prompt === messageText(message).trim())
    ) ?? null;
  if (!projectMessage) return "Projeto em definição";
  const text = messageText(projectMessage)
    .replace(/\s+/g, " ")
    .replace(/^(quero|preciso|gostaria de|ajude-me a|me ajude a|desenvolva|projete)\s+/i, "")
    .trim();
  if (!text) return "Projeto em definição";
  return text.length > 52 ? `${text.slice(0, 51).trim()}…` : text;
}

function latestProjectContext(messages: IvyAgentUIMessage[]): ProjectContext | null {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const parts = messages[messageIndex].parts;
    for (let partIndex = parts.length - 1; partIndex >= 0; partIndex -= 1) {
      const part = parts[partIndex];
      if (part.type === "tool-updateProjectContext" && part.state === "output-available") {
        return part.output;
      }
    }
  }
  return null;
}

function latestVerification(messages: IvyAgentUIMessage[]): EngineeringVerificationResult | null {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const parts = messages[messageIndex].parts;
    for (let partIndex = parts.length - 1; partIndex >= 0; partIndex -= 1) {
      const part = parts[partIndex];
      if (part.type === "tool-assessEngineeringReadiness" && part.state === "output-available") {
        return part.output;
      }
    }
  }
  return null;
}

function contextCompletion(context: ProjectContext | null) {
  if (!context) return 0;
  const completed = [
    Boolean(context.objective),
    context.requirements.length > 0,
    context.constraints.length > 0,
    context.calculations.length > 0,
    context.risks.length > 0,
  ].filter(Boolean).length;
  return Math.round((completed / 5) * 100);
}

const ivyTransport = new DefaultChatTransport<IvyAgentUIMessage>({
  api: "/api/chat",
  prepareSendMessagesRequest: ({ body, id, messages, trigger, messageId }) => ({
    body: {
      ...body,
      id,
      messages: messages.slice(-60),
      trigger,
      messageId,
      sessionId: getSessionId(),
    },
  }),
});

export function IvyDashboard() {
  const [mode, setMode] = useState<"chat" | "workspace" | "sizing" | "verifications">("chat");
  const [runtimeMode, setRuntimeMode] = useState<"checking" | "local" | "gateway">("checking");
  const [draft, setDraft] = useState("");
  const [stage, setStage] = useState(5);
  const [playing, setPlaying] = useState(false);
  const [view, setView] = useState<"assembly" | "cad">("assembly");
  const [angle, setAngle] = useState(-28);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const memoryLoadedRef = useRef(false);
  const [projectStore, setProjectStore] = useState<IvyProjectStore<IvyAgentUIMessage>>(() =>
    createProjectStore({ id: "loading-project", now: "1970-01-01T00:00:00.000Z", name: "Carregando projeto" })
  );
  const {
    messages,
    sendMessage,
    setMessages,
    status,
    error,
    clearError,
    regenerate,
    stop,
  } = useChat<IvyAgentUIMessage>({
    id: "ivy-engineering-workspace",
    transport: ivyTransport,
  });
  const thinking = status === "submitted" || status === "streaming";
  const currentProject = activeProject(projectStore);
  const currentProjectId = currentProject?.id;
  const projectContext = useMemo(() => latestProjectContext(messages), [messages]);
  const verification = useMemo(() => latestVerification(messages), [messages]);
  const sizing = useMemo(() => latestSizing(messages), [messages]);
  const catalog = useMemo(() => latestCatalog(messages), [messages]);
  const cadModel = useMemo(() => latestCad(messages), [messages]);
  const projectLabel = currentProject && currentProject.name !== "Novo projeto" && currentProject.name !== "Projeto importado"
    ? currentProject.name
    : projectContext?.projectName || projectLabelFromMessages(messages);
  const projectProgress = useMemo(() => contextCompletion(projectContext), [projectContext]);
  const blockedCalculations = projectContext?.calculations.filter((calculation) => calculation.status === "bloqueado").length ?? 0;
  const criticalRisks = projectContext?.risks.filter((risk) => risk.severity === "alta" || risk.severity === "critica").length ?? 0;

  useEffect(() => {
    queueMicrotask(() => {
      const stored = loadProjectStore<IvyAgentUIMessage>(window.localStorage, {
        id: window.crypto.randomUUID(),
        now: new Date().toISOString(),
      });
      const storedActive = activeProject(stored);
      setProjectStore(stored);
      setMessages(storedActive?.messages ?? []);
      memoryLoadedRef.current = true;
    });
  }, [setMessages]);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/chat", { signal: controller.signal })
      .then((response) => response.json() as Promise<{ mode?: unknown }>)
      .then((result) => {
        if (result.mode === "local" || result.mode === "gateway") setRuntimeMode(result.mode);
      })
      .catch(() => setRuntimeMode("local"));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!memoryLoadedRef.current || !currentProjectId) return;
    setProjectStore((store) => updateProjectMessages(store, currentProjectId, messages, new Date().toISOString()));
  }, [messages, currentProjectId]);

  useEffect(() => {
    if (!memoryLoadedRef.current) return;
    try {
      saveProjectStore(window.localStorage, projectStore);
    } catch {
      // A conversa continua disponível durante a sessão se o armazenamento estiver bloqueado.
    }
  }, [projectStore]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setStage((current) => {
        const maximum = cadModel ? cadModel.parts.length : assemblySteps.length;
        if (current >= maximum) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cadModel, playing]);

  const assemblyLabel = useMemo(() => {
    if (stage === 0) return "Vista explodida";
    const steps = cadModel?.parts ?? assemblySteps;
    if (stage === steps.length) return "Montagem completa";
    return `Montando ${steps[Math.max(0, stage - 1)].name}`;
  }, [cadModel, stage]);

  function sendPrompt(value: string) {
    const prompt = value.trim();
    if (!prompt || thinking) return;
    clearError();
    setDraft("");
    void sendMessage({ text: prompt });
  }

  function createNewProject() {
    void stop();
    const now = new Date().toISOString();
    setProjectStore((store) => addProject(store, { id: window.crypto.randomUUID(), now }));
    setMessages([]);
    clearError();
    setDraft("");
    setMode("chat");
    window.setTimeout(() => textareaRef.current?.focus(), 50);
  }

  function openProject(projectId: string) {
    void stop();
    const saved = currentProject
      ? updateProjectMessages(projectStore, currentProject.id, messages, new Date().toISOString())
      : projectStore;
    const selected = selectProject(saved, projectId);
    setProjectStore(selected);
    setMessages(activeProject(selected)?.messages ?? []);
    clearError();
    setMode("chat");
  }

  function renameCurrentProject(name: string) {
    if (!currentProject) return;
    setProjectStore((store) => renameProject(store, currentProject.id, name, new Date().toISOString()));
  }

  function duplicateCurrentProject() {
    if (!currentProject) return;
    const next = duplicateProject(projectStore, currentProject.id, window.crypto.randomUUID(), new Date().toISOString());
    setProjectStore(next);
    setMessages(activeProject(next)?.messages ?? []);
  }

  function archiveCurrentProject() {
    if (!currentProject) return;
    const next = archiveProject(projectStore, currentProject.id, new Date().toISOString());
    setProjectStore(next);
    setMessages(activeProject(next)?.messages ?? []);
  }

  function saveRevision() {
    if (!currentProject) return;
    setProjectStore((store) => createRevision(store, currentProject.id, {
      id: window.crypto.randomUUID(),
      now: new Date().toISOString(),
      context: projectContext,
      verification,
      cad: cadModel,
    }));
  }

  function replayAssembly() {
    setView("assembly");
    setStage(0);
    setPlaying(true);
  }

  return (
    <main className={`ivy-shell mode-${mode}`}>
      <header className="ivy-topbar">
        <button className="mobile-brand" type="button" onClick={() => setMode("chat")} aria-label="Ir para a conversa">
          <span className="ivy-symbol" aria-hidden="true">I</span>
          <span>Ivy</span>
        </button>
        {currentProject ? (
          <ProjectMenu
            store={projectStore}
            active={currentProject}
            onSelect={openProject}
            onCreate={createNewProject}
            onRename={renameCurrentProject}
            onDuplicate={duplicateCurrentProject}
            onArchive={archiveCurrentProject}
            onRevision={saveRevision}
          />
        ) : null}
        <div className="topbar-actions">
          <span className={`model-state ${error ? "needs-activation" : runtimeMode === "local" ? "local-mode" : ""}`}>
            <i /> {error ? "REVISE O AVISO" : runtimeMode === "local" ? "MODO TESTE LOCAL" : runtimeMode === "gateway" ? "IVY IA CONECTADA" : "VERIFICANDO MOTOR"}
          </span>
          <button type="button" aria-label="Abrir configurações">···</button>
        </div>
      </header>

      <aside className="primary-rail" aria-label="Navegação principal">
        <div className="brand">
          <span className="ivy-symbol" aria-hidden="true">I</span>
          <span><strong>Ivy</strong><small>Engineering AI</small></span>
        </div>

        <button className="new-chat" type="button" onClick={createNewProject}>
          <span aria-hidden="true">＋</span> Novo projeto
        </button>

        <nav className="main-nav">
          <button className={mode === "chat" ? "active" : ""} type="button" onClick={() => setMode("chat")}>
            <span aria-hidden="true">⌁</span> Conversa
          </button>
          <button className={mode === "workspace" ? "active" : ""} type="button" onClick={() => setMode("workspace")}>
            <span aria-hidden="true">◇</span> Workspace CAD
            <small>4</small>
          </button>
          <button className={mode === "sizing" ? "active" : ""} type="button" onClick={() => setMode("sizing")}>
            <span aria-hidden="true">∑</span> Dimensionamento
            {sizing ? <small>{sizing.components.filter((component) => component.status === "preselected").length}</small> : null}
          </button>
          <button className={mode === "verifications" ? "active" : ""} type="button" onClick={() => setMode("verifications")}>
            <span aria-hidden="true">✓</span> Verificações
            {verification?.counts.blocked ? <i /> : null}
          </button>
        </nav>

        <div className="history">
          <p>SESSÃO ATUAL</p>
          <button type="button" onClick={() => setMode("chat")}><strong>{projectLabel}</strong><small>Contexto definido pela conversa</small></button>
        </div>

        <div className="rail-footer">
          <span className="avatar">CD</span>
          <span><strong>Workspace da Carla</strong><small>Memória neste dispositivo</small></span>
          <i className="sync-light" role="img" aria-label="Sincronizado" />
        </div>
      </aside>

      {mode === "chat" ? (
        <section className={`chat-stage ${messages.length ? "has-messages" : "is-empty"}`} aria-label="Conversa com a Ivy">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="identity-line"><span className="signal" /> IVY · ASSISTENTE DE ENGENHARIA</div>
              <h1>O que vamos<br />projetar hoje?</h1>
              <p>Descreva qualquer projeto de engenharia. A Ivy usará somente os objetivos, requisitos e restrições informados nesta conversa.</p>

              <form className="composer hero-composer" onSubmit={(event) => { event.preventDefault(); sendPrompt(draft); }}>
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      sendPrompt(draft);
                    }
                  }}
                  rows={3}
                  placeholder="Pergunte à Ivy sobre seu projeto de engenharia..."
                  aria-label="Mensagem para a Ivy"
                />
                <div className="composer-footer">
                  <div>
                    <button type="button" aria-label="Anexar arquivo">＋</button>
                    <button type="button" aria-label="Escolher ferramenta"><span aria-hidden="true">⌘</span> Ferramentas</button>
                  </div>
                  <button className="send-button" type="submit" disabled={!draft.trim()} aria-label="Enviar mensagem">↑</button>
                </div>
              </form>

              <div className="suggestion-grid" aria-label="Sugestões de início">
                {suggestions.map((suggestion) => (
                  <button key={suggestion.label} type="button" onClick={() => sendPrompt(suggestion.prompt)}>
                    <span aria-hidden="true">{suggestion.icon}</span>{suggestion.label}
                  </button>
                ))}
              </div>

              <p className="demo-note">
                {runtimeMode === "local" ? "TESTE LOCAL SEM CUSTO" : "MOTOR DE IA CONECTADO"} · CONTEXTO DINÂMICO · MEMÓRIA NESTE DISPOSITIVO
              </p>
            </div>
          ) : (
            <div className="conversation-layout">
              <div className="conversation-heading">
                <span><i /> PROJETO ATUAL</span>
                <strong>{projectLabel}</strong>
                <button type="button" onClick={() => setMode("workspace")}>{cadModel ? "Abrir CAD do projeto" : "Ver exemplo CAD"} <span>↗</span></button>
              </div>

              <div className="message-stream" aria-live="polite">
                {messages.map((message, messageIndex) => (
                  <article key={message.id} className={`message ${message.role === "assistant" ? "ivy" : "user"}`}>
                    <div className="message-avatar">{message.role === "assistant" ? "I" : "CD"}</div>
                    <div className="message-content">
                      <p className="message-author">{message.role === "assistant" ? "Ivy" : "Você"}</p>
                      {message.parts.map((part, partIndex) => {
                        const partKey = `${message.id}-${partIndex}`;
                        if (part.type === "tool-calculateEngineering") {
                          return <EngineeringCalculation invocation={part} key={partKey} />;
                        }
                        if (part.type === "tool-assessEngineeringReadiness") {
                          return <EngineeringVerification invocation={part} key={partKey} />;
                        }
                        if (part.type === "tool-sizeLinearActuator") {
                          return <ActuatorSizing invocation={part} onOpen={() => setMode("sizing")} key={partKey} />;
                        }
                        if (part.type === "tool-selectCatalogComponents") {
                          return <ComponentCatalog invocation={part} onOpen={() => setMode("sizing")} key={partKey} />;
                        }
                        if (part.type === "tool-createConceptCad") {
                          return <ConceptCad invocation={part} onOpen={() => { setStage(part.state === "output-available" ? part.output.parts.length : 0); setView("assembly"); setMode("workspace"); }} key={partKey} />;
                        }
                        if (part.type !== "text") return null;
                        return message.role === "assistant" ? (
                          <MessageResponse className="ivy-markdown" isAnimating={thinking && messageIndex === messages.length - 1} key={partKey}>
                            {part.text}
                          </MessageResponse>
                        ) : (
                          <p key={partKey}>{part.text}</p>
                        );
                      })}
                      {message.role === "assistant" && messageText(message) && (
                        <div className="message-actions">
                          <button type="button" onClick={() => void navigator.clipboard.writeText(messageText(message))}>Copiar</button>
                          {messageIndex === messages.length - 1 && !thinking && (
                            <button type="button" onClick={() => void regenerate({ messageId: message.id })}>Gerar novamente</button>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                ))}
                {thinking && (
                  <article className="message ivy thinking">
                    <div className="message-avatar">I</div>
                    <div className="message-content"><p className="message-author">Ivy</p><div className="thinking-dots"><span /><span /><span /></div></div>
                  </article>
                )}
                {error && (
                  <article className="message ivy error-message" role="alert">
                    <div className="message-avatar">!</div>
                    <div className="message-content">
                      <p className="message-author">Conexão interrompida</p>
                      <p>{error.message || "Não consegui concluir esta resposta. Verifique a conexão e tente novamente em alguns instantes."}</p>
                      <div className="message-actions"><button type="button" onClick={clearError}>Fechar aviso</button></div>
                    </div>
                  </article>
                )}
              </div>

              <form className="composer docked-composer" onSubmit={(event) => { event.preventDefault(); sendPrompt(draft); }}>
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      sendPrompt(draft);
                    }
                  }}
                  rows={2}
                  placeholder="Continue a conversa..."
                  aria-label="Continuar conversa com a Ivy"
                />
                <div className="composer-footer">
                  <div>
                    <button type="button" aria-label="Anexar arquivo">＋</button>
                    <button type="button" onClick={() => sendPrompt("Pré-dimensione o atuador e selecione fuso, guias, rolamentos, motor e estrutura usando os dados já informados. Depois atualize o CAD conceitual.")}><span aria-hidden="true">∑</span> Dimensionar</button>
                    <button type="button" onClick={() => sendPrompt("Compare o pré-dimensionamento com componentes comerciais reais, fabricantes, códigos e fontes oficiais. Não aceite itens incompatíveis.")}><span aria-hidden="true">⌕</span> Catálogo</button>
                    <button type="button" onClick={() => sendPrompt("Crie o CAD conceitual e o modelo 3D deste projeto usando os parâmetros já informados.")}><span aria-hidden="true">◇</span> CAD</button>
                  </div>
                  <button className="send-button" type="submit" disabled={!draft.trim() || thinking} aria-label="Enviar mensagem">{thinking ? "…" : "↑"}</button>
                </div>
              </form>
            </div>
          )}
        </section>
      ) : mode === "verifications" ? (
        <VerificationDashboard assessment={verification} onBack={() => setMode("chat")} />
      ) : mode === "sizing" ? (
        <SizingDashboard
          sizing={sizing}
          catalog={catalog}
          onBack={() => setMode("chat")}
          onStart={() => {
            setMode("chat");
            sendPrompt("Pré-dimensione o atuador e selecione fuso, guias, rolamentos, motor e estrutura usando os dados já informados. Depois atualize o CAD conceitual.");
          }}
          onCatalog={() => {
            setMode("chat");
            sendPrompt("Compare o pré-dimensionamento com componentes comerciais reais, fabricantes, códigos e fontes oficiais. Não aceite itens incompatíveis.");
          }}
        />
      ) : (
        <section className="engineering-workspace" aria-label="Workspace de engenharia">
          <div className="workspace-title">
            <div>
              <button type="button" onClick={() => setMode("chat")}><span>←</span> Voltar à conversa</button>
              <p>{cadModel ? `${cadModel.modelId} · ${cadModel.revision} · CONCEITO` : "EXEMPLO CAD · PRJ-001 · REV. 001"}</p>
              <h1>{cadModel?.title ?? "Garra de fuso com roscas opostas — demonstração"}</h1>
            </div>
            <div className="view-switch" role="group" aria-label="Modo de visualização">
              <button className={view === "assembly" ? "selected" : ""} type="button" onClick={() => setView("assembly")}>Modelo 3D</button>
              <button className={view === "cad" ? "selected" : ""} type="button" onClick={() => setView("cad")}>Vista CAD</button>
            </div>
          </div>

          <div className="workspace-grid">
            <div className="viewer-card">
              <div className="viewer-readout left"><span>X</span> {cadModel?.parameters.overallWidthMm.toFixed(2) ?? "150.00"} <span>Y</span> {cadModel?.parameters.overallDepthMm.toFixed(2) ?? "60.00"} <span>Z</span> {cadModel?.parameters.overallHeightMm.toFixed(2) ?? "50.00"} mm</div>
              <div className="viewer-readout right"><span>REV</span> 001 · CONCEITO</div>

              {view === "assembly" ? (
                <div className="assembly-view" aria-label={`Modelo tridimensional: ${assemblyLabel}`}>
                  {cadModel ? (
                    <LinearActuatorPreview model={cadModel} angle={angle} stage={stage} />
                  ) : (
                    <>
                      <div className="axis axis-x" /><div className="axis axis-y" />
                      <div className="model-stage" style={{ transform: `rotateX(61deg) rotateZ(${angle}deg)` }}>
                        <div className={`model-part base-plate ${stage >= 1 ? "installed" : "exploded"}`} />
                        <div className={`model-part rail rail-one ${stage >= 2 ? "installed" : "exploded"}`} />
                        <div className={`model-part rail rail-two ${stage >= 2 ? "installed" : "exploded"}`} />
                        <div className={`model-part carriage carriage-left ${stage >= 3 ? "installed" : "exploded"}`} />
                        <div className={`model-part carriage carriage-right ${stage >= 3 ? "installed" : "exploded"}`} />
                        <div className={`model-part finger finger-left ${stage >= 4 ? "installed" : "exploded"}`} />
                        <div className={`model-part finger finger-right ${stage >= 4 ? "installed" : "exploded"}`} />
                        <div className={`model-part drive-screw ${stage >= 5 ? "installed" : "exploded"}`} />
                        <div className={`model-part motor-placeholder ${stage >= 5 ? "installed" : "exploded"}`}><span>ATUADOR<br />PENDENTE</span></div>
                      </div>
                    </>
                  )}
                  <div className="model-caption"><span className="project-pulse" />{assemblyLabel}</div>
                  <label className="rotation-control">ROTAÇÃO
                    <input aria-label="Rotação do modelo" type="range" min="-55" max="5" value={angle} onChange={(event) => setAngle(Number(event.target.value))} />
                  </label>
                </div>
              ) : (
                <div className="cad-view">
                  {cadModel ? <ActuatorCadDrawing model={cadModel} /> : <Image src="/ivy-cad.svg" alt="Vista CAD superior da garra nas aberturas de 40 e 90 milímetros" width={1536} height={1024} priority />}
                  <div className="cad-overlay"><span>{cadModel ? "VISTA TÉCNICA" : "PLANTA SUPERIOR"}</span><strong>{cadModel ? `${cadModel.parameters.travelMm} mm` : "40 / 90 mm"}</strong></div>
                </div>
              )}

              <div className="viewer-toolbar">
                <button type="button" onClick={replayAssembly}><span>▶</span> Montar</button>
                <button type="button" onClick={() => setPlaying((value) => !value)} disabled={stage === (cadModel?.parts.length ?? 5) && !playing}>{playing ? "Pausar" : "Continuar"}</button>
                <button type="button" onClick={() => { setPlaying(false); setStage(0); setView("assembly"); }}>Explodir</button>
                {cadModel ? <a className="download-stl" href={cadModel.downloadUrl} download>Baixar STL</a> : null}
              </div>
            </div>

            <aside className="workspace-inspector">
              <div className="mini-panel">
                <div className="mini-title"><span>PARÂMETROS</span><small>4 definidos</small></div>
                {(cadModel ? [
                  ["Carga", `${cadModel.parameters.payloadKg} kg`],
                  ["Curso", `${cadModel.parameters.travelMm} mm`],
                  ["Avanço", `${cadModel.parameters.screwLeadMm} mm/volta`],
                  ["Alimentação", `${cadModel.parameters.motorVoltage} V`],
                  ...(cadModel.parameters.motorNominalPowerW ? [["Motor", `${cadModel.parameters.motorNominalPowerW} W · ${cadModel.parameters.reductionRatio}:1`]] : []),
                ] : parameters).map(([name, value]) => <div className="parameter" key={name}><span>{name}</span><strong>{value}</strong></div>)}
              </div>
              <div className="mini-panel stages-panel">
                <div className="mini-title"><span>MONTAGEM</span><small>{stage}/{cadModel?.parts.length ?? 5}</small></div>
                {(cadModel?.parts ?? assemblySteps).map((step, index) => (
                  <button key={step.name} type="button" className={stage > index ? "complete" : ""} onClick={() => { setPlaying(false); setStage(index + 1); setView("assembly"); }}>
                    <span>{stage > index ? "✓" : `0${index + 1}`}</span><span><strong>{step.name}</strong><small>{step.detail}</small></span>
                  </button>
                ))}
              </div>
            </aside>
          </div>
        </section>
      )}

      <aside className="context-rail" aria-label="Contexto da conversa">
        <div className="context-heading">
          <span>CONTEXTO DA CONVERSA</span>
          <button type="button" aria-label="Fechar contexto">×</button>
        </div>

        <section className="project-card">
          <div className="project-card-top"><span>PROJETO ATUAL</span><i>DINÂMICO</i></div>
          <h2>{projectLabel}</h2>
          <p>{projectContext?.objective || "Objetivos e requisitos serão extraídos somente desta conversa."}</p>
          <div className="progress-label">
            <span>Contexto</span>
            <strong>{projectContext ? `${projectProgress}%` : messages.length ? "ANALISANDO" : "NOVO"}</strong>
          </div>
          <div className={`progress ${projectContext ? "has-context" : ""}`}>
            <span style={projectContext ? { width: `${projectProgress}%` } : undefined} />
          </div>
        </section>

        <section className="context-section">
          <div className="context-title"><span>ANÁLISE DO PROJETO</span><strong>IA</strong></div>
          <div className="metric-grid">
            <div>
              <small>OBJETIVO</small>
              <strong>{projectContext?.objective ? "definido" : <em>a definir</em>}</strong>
            </div>
            <div>
              <small>RESTRIÇÕES</small>
              <strong>{projectContext ? `${projectContext.constraints.length} registradas` : <em>a definir</em>}</strong>
            </div>
            <div>
              <small>CÁLCULOS</small>
              <strong>{projectContext ? `${projectContext.calculations.length} · ${blockedCalculations} bloqueados` : <em>sob demanda</em>}</strong>
            </div>
            <div>
              <small>SEGURANÇA</small>
              <strong>{projectContext ? (criticalRisks ? `${criticalRisks} alertas` : "preliminar") : <em>verificar</em>}</strong>
            </div>
          </div>
        </section>

        <section className="context-section compact-cad">
          <div className="context-title"><span>{cadModel ? "CAD DO PROJETO" : "EXEMPLO CAD"}</span><button type="button" onClick={() => setMode("workspace")}>ABRIR ↗</button></div>
          <button className="cad-preview" type="button" onClick={() => { setView("cad"); setMode("workspace"); }}>
            {cadModel ? <ActuatorCadDrawing model={cadModel} /> : <Image src="/ivy-cad.svg" alt="Prévia do modelo CAD da garra" width={1536} height={1024} />}
            <span>{cadModel ? `${cadModel.modelId} · ${cadModel.revision}` : "DEMONSTRAÇÃO · PRJ-001"}</span>
          </button>
        </section>

        {sizing ? (
          <section className="context-section compact-sizing">
            <div className="context-title"><span>DIMENSIONAMENTO</span><button type="button" onClick={() => setMode("sizing")}>ABRIR ↗</button></div>
            <div className="sizing-context-card">
              <span>CAPACIDADE PROPOSTA</span>
              <strong>{sizing.metrics.proposedStructuralCapacityN} N</strong>
              <p>FS {sizing.metrics.proposedSafetyFactor} · fuso Ø {sizing.selections.screwNominalDiameterMm} · motor {sizing.selections.motorNominalPowerW} W</p>
            </div>
          </section>
        ) : null}

        {catalog ? (
          <section className="context-section compact-catalog">
            <div className="context-title"><span>CATÁLOGO</span><button type="button" onClick={() => setMode("sizing")}>ABRIR ↗</button></div>
            <div className="catalog-context-card">
              <span>CANDIDATOS COMPATÍVEIS</span>
              <strong>{catalog.summary.candidates}</strong>
              <p>{catalog.summary.rejected} rejeitados · {catalog.summary.evidenceRequired} pendentes</p>
            </div>
          </section>
        ) : null}

        <section className="safety-card">
          <div><span>!</span><strong>VALIDAÇÃO NECESSÁRIA</strong></div>
          <p>A Ivy não declara nenhum projeto seguro ou pronto para fabricar sem evidências suficientes.</p>
          <button type="button" onClick={() => sendPrompt("Faça uma verificação preliminar de segurança do projeto descrito nesta conversa.")}>Analisar riscos</button>
        </section>

        <div className="context-footer"><span><i /> Memória do dispositivo ativa</span><small>agora</small></div>
      </aside>
    </main>
  );
}
