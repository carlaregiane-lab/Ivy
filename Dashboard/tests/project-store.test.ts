import assert from "node:assert/strict";
import test from "node:test";
import {
  activeProject,
  addProject,
  archiveProject,
  createProjectStore,
  createRevision,
  duplicateProject,
  renameProject,
  updateProjectMessages,
} from "../lib/projects/project-store.ts";

const now = "2026-08-11T15:00:00.000Z";

test("cria, renomeia e salva mensagens por projeto", () => {
  let store = createProjectStore<string>({ id: "one", now, name: "Novo projeto" });
  store = renameProject(store, "one", "Atuador Ivy", now);
  store = updateProjectMessages(store, "one", ["entrada", "resposta"], now);
  assert.equal(activeProject(store)?.name, "Atuador Ivy");
  assert.deepEqual(activeProject(store)?.messages, ["entrada", "resposta"]);
});

test("duplica, cria revisão e arquiva sem perder o projeto original", () => {
  let store = createProjectStore<string>({ id: "one", now, name: "Atuador", messages: ["projeto"] });
  store = createRevision(store, "one", { id: "rev-one", now, context: { phase: "cad" }, verification: null, cad: { id: "ACT" } });
  store = duplicateProject(store, "one", "two", now);
  assert.equal(activeProject(store)?.name, "Atuador — cópia");
  assert.equal(activeProject(store)?.revisions[0].label, "REV. 001");
  store = archiveProject(store, "two", now);
  assert.equal(activeProject(store)?.id, "one");
  assert.equal(store.projects.find((project) => project.id === "two")?.status, "archived");
});

test("não arquiva o único projeto ativo", () => {
  const store = createProjectStore({ id: "one", now });
  assert.equal(archiveProject(store, "one", now), store);
});

test("adiciona um projeto novo e o torna ativo", () => {
  const store = addProject(createProjectStore({ id: "one", now }), { id: "two", now, name: "Segundo" });
  assert.equal(activeProject(store)?.id, "two");
});
