"use client";

import type { IvyProject, IvyProjectStore } from "@/lib/projects/project-store";
import { useState } from "react";

export function ProjectMenu<TMessage>({
  store,
  active,
  onSelect,
  onCreate,
  onRename,
  onDuplicate,
  onArchive,
  onRevision,
}: {
  store: IvyProjectStore<TMessage>;
  active: IvyProject<TMessage>;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (name: string) => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onRevision: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(active.name);
  const projects = store.projects.filter((project) => project.status === "active");

  function close() {
    setOpen(false);
    setRenaming(false);
  }

  return (
    <div className="project-menu-wrap">
      <button className="project-selector" type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)} aria-label={`Projeto atual: ${active.name}`}>
        <span className="project-pulse" aria-hidden="true" />
        <span><small>PROJETO ATIVO</small><strong>{active.name}</strong></span>
        <span className="chevron" aria-hidden="true">⌄</span>
      </button>
      {open ? (
        <div className="project-menu" role="dialog" aria-label="Gerenciar projetos">
          <div className="project-menu-heading"><span>PROJETOS NESTE DISPOSITIVO</span><button type="button" onClick={close}>×</button></div>
          <div className="project-list">
            {projects.map((project) => (
              <button className={project.id === active.id ? "selected" : ""} type="button" key={project.id} onClick={() => { onSelect(project.id); close(); }}>
                <strong>{project.name}</strong><small>{project.revisions.length} revisões · salvo localmente</small>
              </button>
            ))}
          </div>
          {renaming ? (
            <form className="project-rename" onSubmit={(event) => { event.preventDefault(); onRename(name); close(); }}>
              <input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} aria-label="Novo nome do projeto" />
              <button type="submit">Salvar</button>
            </form>
          ) : null}
          <div className="project-menu-actions">
            <button type="button" onClick={() => { onCreate(); close(); }}>Novo</button>
            <button type="button" onClick={() => { setName(active.name); setRenaming(true); }}>Renomear</button>
            <button type="button" onClick={() => { onDuplicate(); close(); }}>Duplicar</button>
            <button type="button" onClick={() => { onRevision(); close(); }}>Criar revisão</button>
            <button type="button" disabled={projects.length <= 1} onClick={() => { onArchive(); close(); }}>Arquivar</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
