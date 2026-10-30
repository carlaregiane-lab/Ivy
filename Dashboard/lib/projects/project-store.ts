export const PROJECT_STORE_KEY = "ivy:projects:workspace:v1";
export const LEGACY_MEMORY_KEY = "ivy:memory:workspace:v2";

export type IvyProjectStatus = "active" | "archived";

export type IvyProjectRevision<TMessage = unknown> = {
  id: string;
  label: string;
  createdAt: string;
  messages: TMessage[];
  context: unknown;
  verification: unknown;
  cad: unknown;
};

export type IvyProject<TMessage = unknown> = {
  id: string;
  name: string;
  status: IvyProjectStatus;
  createdAt: string;
  updatedAt: string;
  messages: TMessage[];
  revisions: IvyProjectRevision<TMessage>[];
  evidence: Array<{
    id: string;
    description: string;
    status: "pending" | "accepted" | "rejected";
    createdAt: string;
  }>;
  decisions: Array<{
    id: string;
    description: string;
    createdAt: string;
  }>;
};

export type IvyProjectStore<TMessage = unknown> = {
  version: 1;
  activeProjectId: string;
  projects: IvyProject<TMessage>[];
};

type ProjectSeed<TMessage> = {
  id: string;
  now: string;
  name?: string;
  messages?: TMessage[];
};

export function createProject<TMessage>({
  id,
  now,
  name = "Novo projeto",
  messages = [],
}: ProjectSeed<TMessage>): IvyProject<TMessage> {
  return {
    id,
    name,
    status: "active",
    createdAt: now,
    updatedAt: now,
    messages: messages.slice(-60),
    revisions: [],
    evidence: [],
    decisions: [],
  };
}

export function createProjectStore<TMessage>(seed: ProjectSeed<TMessage>): IvyProjectStore<TMessage> {
  const project = createProject(seed);
  return { version: 1, activeProjectId: project.id, projects: [project] };
}

export function activeProject<TMessage>(store: IvyProjectStore<TMessage>) {
  return store.projects.find((project) => project.id === store.activeProjectId) ?? store.projects[0];
}

export function addProject<TMessage>(store: IvyProjectStore<TMessage>, seed: ProjectSeed<TMessage>) {
  const project = createProject(seed);
  return { ...store, activeProjectId: project.id, projects: [...store.projects, project] };
}

export function selectProject<TMessage>(store: IvyProjectStore<TMessage>, projectId: string) {
  const project = store.projects.find((candidate) => candidate.id === projectId && candidate.status === "active");
  return project ? { ...store, activeProjectId: project.id } : store;
}

export function renameProject<TMessage>(store: IvyProjectStore<TMessage>, projectId: string, name: string, now: string) {
  const normalized = name.trim().slice(0, 80);
  if (!normalized) return store;
  return {
    ...store,
    projects: store.projects.map((project) =>
      project.id === projectId ? { ...project, name: normalized, updatedAt: now } : project
    ),
  };
}

export function updateProjectMessages<TMessage>(
  store: IvyProjectStore<TMessage>,
  projectId: string,
  messages: TMessage[],
  now: string
) {
  return {
    ...store,
    projects: store.projects.map((project) =>
      project.id === projectId
        ? { ...project, messages: messages.slice(-60), updatedAt: now }
        : project
    ),
  };
}

export function duplicateProject<TMessage>(
  store: IvyProjectStore<TMessage>,
  projectId: string,
  id: string,
  now: string
) {
  const source = store.projects.find((project) => project.id === projectId);
  if (!source) return store;
  const copy: IvyProject<TMessage> = {
    ...source,
    id,
    name: `${source.name} — cópia`.slice(0, 80),
    createdAt: now,
    updatedAt: now,
    messages: structuredClone(source.messages),
    revisions: structuredClone(source.revisions),
    evidence: structuredClone(source.evidence),
    decisions: structuredClone(source.decisions),
    status: "active",
  };
  return { ...store, activeProjectId: id, projects: [...store.projects, copy] };
}

export function archiveProject<TMessage>(store: IvyProjectStore<TMessage>, projectId: string, now: string) {
  const active = store.projects.filter((project) => project.status === "active");
  if (active.length <= 1) return store;
  const nextProjects = store.projects.map((project) =>
    project.id === projectId ? { ...project, status: "archived" as const, updatedAt: now } : project
  );
  const nextActive = nextProjects.find((project) => project.status === "active");
  return {
    ...store,
    activeProjectId: store.activeProjectId === projectId && nextActive ? nextActive.id : store.activeProjectId,
    projects: nextProjects,
  };
}

export function createRevision<TMessage>(
  store: IvyProjectStore<TMessage>,
  projectId: string,
  snapshot: { id: string; now: string; context: unknown; verification: unknown; cad: unknown }
) {
  return {
    ...store,
    projects: store.projects.map((project) => {
      if (project.id !== projectId) return project;
      const revision: IvyProjectRevision<TMessage> = {
        id: snapshot.id,
        label: `REV. ${String(project.revisions.length + 1).padStart(3, "0")}`,
        createdAt: snapshot.now,
        messages: structuredClone(project.messages),
        context: structuredClone(snapshot.context),
        verification: structuredClone(snapshot.verification),
        cad: structuredClone(snapshot.cad),
      };
      return { ...project, revisions: [...project.revisions, revision], updatedAt: snapshot.now };
    }),
  };
}

function isStoredProject(value: unknown): value is IvyProject<unknown> {
  if (!value || typeof value !== "object") return false;
  const project = value as Partial<IvyProject<unknown>>;
  return typeof project.id === "string" && typeof project.name === "string" && Array.isArray(project.messages);
}

export function loadProjectStore<TMessage>(
  storage: Pick<Storage, "getItem">,
  fallback: { id: string; now: string }
): IvyProjectStore<TMessage> {
  try {
    const raw = storage.getItem(PROJECT_STORE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<IvyProjectStore<TMessage>>;
      if (parsed.version === 1 && typeof parsed.activeProjectId === "string" && Array.isArray(parsed.projects)) {
        const projects = parsed.projects.filter(isStoredProject) as IvyProject<TMessage>[];
        if (projects.length) return { version: 1, activeProjectId: parsed.activeProjectId, projects };
      }
    }

    const legacyRaw = storage.getItem(LEGACY_MEMORY_KEY);
    const legacy = legacyRaw ? (JSON.parse(legacyRaw) as unknown) : [];
    return createProjectStore<TMessage>({
      ...fallback,
      name: Array.isArray(legacy) && legacy.length ? "Projeto importado" : "Novo projeto",
      messages: Array.isArray(legacy) ? (legacy as TMessage[]) : [],
    });
  } catch {
    return createProjectStore<TMessage>({ ...fallback, name: "Novo projeto", messages: [] });
  }
}

export function saveProjectStore<TMessage>(storage: Pick<Storage, "setItem">, store: IvyProjectStore<TMessage>) {
  storage.setItem(PROJECT_STORE_KEY, JSON.stringify(store));
}
