"""Histórico versionado e decisões persistentes dos projetos da Ivy."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


EventType = Literal[
    "project_created",
    "answers_updated",
    "calculation_saved",
    "concept_comparison_saved",
    "verification_saved",
    "cad_model_saved",
    "decision_recorded",
]


class ProjectHistoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_revision: int = Field(ge=1)
    created_at: str
    event_type: EventType
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ProjectDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_revision: int = Field(ge=1)
    created_at: str
    statement: str
    reason: str | None = None
    status: Literal["ativa"] = "ativa"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_project_history(project: dict, *, timestamp: str | None = None) -> None:
    """Adiciona o contrato v0.7 sem apagar ou reinterpretar dados antigos."""

    started_at = timestamp or now_iso()
    was_existing = "history_schema_version" not in project
    project.setdefault("history_schema_version", "0.1")
    project.setdefault("project_revision", 0)
    project.setdefault("history_started_at", started_at)
    project.setdefault(
        "history_origin",
        "ativado_em_projeto_existente" if was_existing else "desde_criacao",
    )
    project.setdefault("history", [])
    project.setdefault("decisions", [])

    if "calculation_history" not in project:
        project["calculation_history"] = []
        raw_report = project.get("calculation_report")
        if raw_report is not None:
            project["calculation_history"].append(
                {
                    "revision": int(project.get("calculation_revision", 0)),
                    "project_revision": None,
                    "created_at": str(project.get("updated_at") or started_at),
                    "legacy_snapshot": True,
                    "report": deepcopy(raw_report),
                }
            )

    if "concept_history" not in project:
        project["concept_history"] = []
        raw_report = project.get("concept_report")
        if raw_report is not None:
            project["concept_history"].append(
                {
                    "revision": int(project.get("concept_revision", 0)),
                    "project_revision": None,
                    "created_at": str(project.get("updated_at") or started_at),
                    "legacy_snapshot": True,
                    "report": deepcopy(raw_report),
                }
            )

    if "verification_history" not in project:
        project["verification_history"] = []
        raw_report = project.get("verification_report")
        if raw_report is not None:
            project["verification_history"].append(
                {
                    "revision": int(project.get("verification_revision", 0)),
                    "project_revision": None,
                    "created_at": str(project.get("updated_at") or started_at),
                    "legacy_snapshot": True,
                    "report": deepcopy(raw_report),
                }
            )

    if "cad_history" not in project:
        project["cad_history"] = []
        raw_report = project.get("cad_report")
        if raw_report is not None:
            project["cad_history"].append(
                {
                    "revision": int(project.get("cad_revision", 0)),
                    "project_revision": None,
                    "created_at": str(project.get("updated_at") or started_at),
                    "legacy_snapshot": True,
                    "report": deepcopy(raw_report),
                }
            )


def record_project_event(
    project: dict,
    event_type: EventType,
    summary: str,
    details: dict[str, Any] | None = None,
    *,
    timestamp: str | None = None,
) -> ProjectHistoryEvent:
    created_at = timestamp or now_iso()
    ensure_project_history(project, timestamp=created_at)
    revision = int(project.get("project_revision", 0)) + 1
    project["project_revision"] = revision
    event = ProjectHistoryEvent(
        id=f"EVT-{revision:04d}",
        project_revision=revision,
        created_at=created_at,
        event_type=event_type,
        summary=summary,
        details=details or {},
    )
    project.setdefault("history", []).append(event.model_dump(mode="json"))
    return event


def record_project_decision(
    project: dict,
    statement: str,
    reason: str | None = None,
    *,
    timestamp: str | None = None,
) -> tuple[ProjectDecision, ProjectHistoryEvent]:
    created_at = timestamp or now_iso()
    ensure_project_history(project, timestamp=created_at)
    decision_number = len(project.setdefault("decisions", [])) + 1
    decision_id = f"DEC-{decision_number:03d}"
    event = record_project_event(
        project,
        "decision_recorded",
        f"Decisão {decision_id} registrada.",
        {"decision_id": decision_id, "statement": statement, "reason": reason},
        timestamp=created_at,
    )
    decision = ProjectDecision(
        id=decision_id,
        project_revision=event.project_revision,
        created_at=created_at,
        statement=statement,
        reason=reason,
    )
    project["decisions"].append(decision.model_dump(mode="json"))
    return decision, event


def _event_label(event_type: EventType) -> str:
    return {
        "project_created": "Projeto criado",
        "answers_updated": "Respostas alteradas",
        "calculation_saved": "Cálculo guardado",
        "concept_comparison_saved": "Comparação guardada",
        "verification_saved": "Verificação guardada",
        "cad_model_saved": "Modelo CAD guardado",
        "decision_recorded": "Decisão registrada",
    }[event_type]


def _short(value: object, limit: int = 120) -> str:
    text = "não informado" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_project_history(project: dict) -> str:
    ensure_project_history(project)
    raw_events = project.get("history", [])
    events: list[ProjectHistoryEvent] = []
    invalid_count = 0
    for raw_event in raw_events:
        try:
            events.append(ProjectHistoryEvent.model_validate(raw_event))
        except (TypeError, ValueError):
            invalid_count += 1

    lines = [
        "IVY — HISTÓRICO DO PROJETO",
        "=" * 34,
        f"Código: {project.get('id')}",
        f"Projeto: {project.get('name')}",
        f"Revisão atual do projeto: {int(project.get('project_revision', 0))}",
        f"Histórico detalhado ativo desde: {project.get('history_started_at')}",
    ]
    if project.get("history_origin") == "ativado_em_projeto_existente":
        lines.append(
            "Escopo: os dados anteriores à versão 0.7 foram preservados, mas não foram "
            "reconstruídos como eventos retroativos."
        )

    lines.extend(["", "LINHA DO TEMPO"])
    if not events:
        lines.append("- Ainda não há mudanças registradas desde a ativação do histórico.")
    else:
        for event in events[-20:]:
            lines.append(
                f"- R{event.project_revision} | {event.created_at} | "
                f"{_event_label(event.event_type)} | {event.summary}"
            )
            if event.event_type == "answers_updated":
                for change in event.details.get("changes", []):
                    lines.append(
                        f"  Pergunta {change.get('question')}: "
                        f"{_short(change.get('before'))} -> {_short(change.get('after'))}"
                    )
            elif event.event_type == "calculation_saved":
                lines.append(
                    f"  Memória de cálculo: revisão {event.details.get('calculation_revision')}; "
                    f"estado {event.details.get('status')}."
                )
            elif event.event_type == "concept_comparison_saved":
                lines.append(
                    f"  Comparação: revisão {event.details.get('concept_revision')}; "
                    f"recomendação {event.details.get('recommended_concept_id') or 'bloqueada'}."
                )
            elif event.event_type == "verification_saved":
                lines.append(
                    f"  Verificação: revisão {event.details.get('verification_revision')}; "
                    f"estado {event.details.get('status')}; "
                    f"erros {event.details.get('error_count')}."
                )
            elif event.event_type == "cad_model_saved":
                lines.append(
                    f"  CAD: revisão {event.details.get('cad_revision')}; "
                    f"estado {event.details.get('status')}; "
                    f"conceito {event.details.get('concept_id') or 'bloqueado'}."
                )
            elif event.event_type == "decision_recorded":
                lines.append(
                    f"  {event.details.get('decision_id')}: "
                    f"{_short(event.details.get('statement'))}"
                )
        if len(events) > 20:
            lines.append(f"- {len(events) - 20} evento(s) anterior(es) foram ocultados nesta visão.")

    calculation_history = project.get("calculation_history", [])
    concept_history = project.get("concept_history", [])
    verification_history = project.get("verification_history", [])
    cad_history = project.get("cad_history", [])
    decisions = project.get("decisions", [])
    lines.extend(
        [
            "",
            "ARTEFATOS VERSIONADOS",
            f"- Memórias de cálculo preservadas: {len(calculation_history)}.",
            f"- Comparações de conceitos preservadas: {len(concept_history)}.",
            f"- Verificações independentes preservadas: {len(verification_history)}.",
            f"- Modelos CAD preservados: {len(cad_history)}.",
            f"- Decisões registradas: {len(decisions)}.",
        ]
    )
    if invalid_count:
        lines.extend(
            [
                "",
                "ALERTA",
                f"- {invalid_count} evento(s) inválido(s) não foram exibidos.",
            ]
        )
    return "\n".join(lines)


def render_project_decisions(project: dict) -> str:
    ensure_project_history(project)
    decisions: list[ProjectDecision] = []
    invalid_count = 0
    for raw_decision in project.get("decisions", []):
        try:
            decisions.append(ProjectDecision.model_validate(raw_decision))
        except (TypeError, ValueError):
            invalid_count += 1

    lines = [
        "IVY — DECISÕES DO PROJETO",
        "=" * 33,
        f"Código: {project.get('id')}",
        f"Projeto: {project.get('name')}",
        "",
        "DECISÕES ATIVAS",
    ]
    if not decisions:
        lines.append("- Ainda não há decisões registradas neste projeto.")
    for decision in decisions:
        lines.extend(
            [
                f"- {decision.id} | R{decision.project_revision} | {decision.created_at}",
                f"  Decisão: {decision.statement}",
                f"  Motivo: {decision.reason or 'não informado'}",
            ]
        )
    if invalid_count:
        lines.extend(
            [
                "",
                "ALERTA",
                f"- {invalid_count} decisão(ões) inválida(s) não foram exibidas.",
            ]
        )
    return "\n".join(lines)
