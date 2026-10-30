"""Assistente conversacional de trabalho da Ivy."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Literal

from .calculator import (
    EngineeringCalculationReport,
    calculate_project,
    render_calculation_report,
)
from .cad import (
    ParametricCADReport,
    generate_parametric_gripper_cad,
    render_cad_report,
)
from .concepts import (
    ConceptComparisonReport,
    compare_gripper_concepts,
    render_concept_report,
)
from .interpreter import interpret_requirements
from .models import EngineeringBrief
from .project_memory import (
    ensure_project_history,
    now_iso,
    record_project_decision,
    record_project_event,
    render_project_decisions,
    render_project_history,
)
from .reporting import render_report
from .safety import assess_risk, normalize
from .verifier import (
    EngineeringVerificationReport,
    render_verification_report,
    render_verification_summary,
    verify_project,
)


AssistantMode = Literal["auto", "demo", "api"]

ASSISTANT_SYSTEM_PROMPT = """
Você é Ivy, uma assistente de trabalho e engenharia em desenvolvimento.
Converse em português do Brasil de forma natural, cordial, objetiva e colaborativa.
Ajude a organizar trabalho, esclarecer ideias, planejar projetos e aprender engenharia.
Quando faltar contexto, faça poucas perguntas úteis em vez de inventar informações.
Não diga que executou ações, cálculos, pesquisas ou testes que não executou.
Em engenharia, diferencie fatos, hipóteses e propostas. Não declare segurança sem evidência.
Recuse ajuda operacional para armas, explosivos ou outras aplicações perigosas e ofereça
alternativas seguras. Você é inspirada em assistentes de ficção, mas deve ser honesta
sobre seus limites reais e não fingir possuir voz, visão, acesso a arquivos ou controle
de máquinas quando essas ferramentas não estiverem conectadas.
""".strip()


@dataclass(frozen=True)
class AssistantReply:
    text: str
    should_exit: bool = False


class WorkMemory:
    """Memória local para identidade, notas, tarefas e projetos."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = {
            "creator_confirmed": False,
            "creator_name": None,
            "notes": [],
            "tasks": [],
            "projects": [],
            "active_project_id": None,
        }
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(loaded, dict):
            for key in self.data:
                if key in loaded:
                    self.data[key] = loaded[key]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def remember_creator(self, name: str | None = None) -> None:
        self.data["creator_confirmed"] = True
        if name:
            self.data["creator_name"] = name
        self.save()

    def add_note(self, note: str) -> int:
        notes = self.data.setdefault("notes", [])
        notes.append(note)
        self.save()
        return len(notes)

    def add_task(self, task: str) -> int:
        tasks = self.data.setdefault("tasks", [])
        tasks.append({"text": task, "done": False})
        self.save()
        return len(tasks)

    def complete_task(self, number: int) -> str | None:
        tasks = self.data.setdefault("tasks", [])
        if number < 1 or number > len(tasks):
            return None
        tasks[number - 1]["done"] = True
        self.save()
        return str(tasks[number - 1]["text"])

    def create_project(self, brief: EngineeringBrief) -> dict:
        projects = self.data.setdefault("projects", [])
        project_id = f"PRJ-{len(projects) + 1:03d}"
        timestamp = now_iso()
        project = {
            "id": project_id,
            "name": brief.project_name,
            "created_at": timestamp,
            "updated_at": timestamp,
            "brief": brief.model_dump(mode="json"),
            "answers": {},
            "calculation_revision": 0,
            "calculation_report": None,
            "calculations_stale": False,
            "concept_revision": 0,
            "concept_report": None,
            "concepts_stale": False,
            "verification_revision": 0,
            "verification_report": None,
            "verification_stale": False,
            "cad_revision": 0,
            "cad_report": None,
            "cad_stale": False,
            "history_schema_version": "0.1",
            "project_revision": 0,
            "history_started_at": timestamp,
            "history_origin": "desde_criacao",
            "history": [],
            "decisions": [],
            "calculation_history": [],
            "concept_history": [],
            "verification_history": [],
            "cad_history": [],
        }
        record_project_event(
            project,
            "project_created",
            f"Projeto {project_id} criado a partir do briefing inicial.",
            {"project_name": brief.project_name},
            timestamp=timestamp,
        )
        projects.append(project)
        self.data["active_project_id"] = project_id
        self.save()
        return project

    def active_project(self) -> dict | None:
        active_id = self.data.get("active_project_id")
        projects = self.data.setdefault("projects", [])
        for project in projects:
            if project.get("id") == active_id:
                return project
        return None

    def select_project(self, reference: str) -> dict | None:
        projects = self.data.setdefault("projects", [])
        normalized_reference = reference.strip().upper()
        selected: dict | None = None
        if normalized_reference.isdigit():
            index = int(normalized_reference)
            if 1 <= index <= len(projects):
                selected = projects[index - 1]
        else:
            for project in projects:
                if str(project.get("id", "")).upper() == normalized_reference:
                    selected = project
                    break
        if selected is None:
            return None
        self.data["active_project_id"] = selected.get("id")
        self.save()
        return selected

    def save_project_answers(self, answers: dict[int, str]) -> dict | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        ensure_project_history(project, timestamp=timestamp)
        stored_answers = project.setdefault("answers", {})
        changes: list[dict[str, object]] = []
        for number, answer in answers.items():
            previous = stored_answers.get(str(number))
            if previous == answer:
                continue
            changes.append(
                {
                    "question": number,
                    "before": previous,
                    "after": answer,
                }
            )
            stored_answers[str(number)] = answer
        if changes:
            if project.get("calculation_report") is not None:
                project["calculations_stale"] = True
            if project.get("concept_report") is not None:
                project["concepts_stale"] = True
            if project.get("verification_report") is not None:
                project["verification_stale"] = True
            if project.get("cad_report") is not None:
                project["cad_stale"] = True
            numbers = ", ".join(str(item["question"]) for item in changes)
            record_project_event(
                project,
                "answers_updated",
                f"Respostas {numbers} alteradas.",
                {"changes": changes},
                timestamp=timestamp,
            )
            project["updated_at"] = timestamp
        self.save()
        return project

    def save_project_calculation(
        self,
        report: EngineeringCalculationReport,
    ) -> tuple[dict, int] | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        ensure_project_history(project, timestamp=timestamp)
        revision = int(project.get("calculation_revision", 0)) + 1
        project["calculation_revision"] = revision
        serialized_report = report.model_dump(mode="json")
        project["calculation_report"] = serialized_report
        project["calculations_stale"] = False
        if project.get("concept_report") is not None:
            project["concepts_stale"] = True
        if project.get("verification_report") is not None:
            project["verification_stale"] = True
        if project.get("cad_report") is not None:
            project["cad_stale"] = True
        event = record_project_event(
            project,
            "calculation_saved",
            f"Memória de cálculo revisão {revision} guardada.",
            {"calculation_revision": revision, "status": report.status},
            timestamp=timestamp,
        )
        project.setdefault("calculation_history", []).append(
            {
                "revision": revision,
                "project_revision": event.project_revision,
                "created_at": timestamp,
                "legacy_snapshot": False,
                "report": deepcopy(serialized_report),
            }
        )
        project["updated_at"] = timestamp
        self.save()
        return project, revision

    def save_project_concepts(
        self,
        report: ConceptComparisonReport,
    ) -> tuple[dict, int] | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        ensure_project_history(project, timestamp=timestamp)
        revision = int(project.get("concept_revision", 0)) + 1
        project["concept_revision"] = revision
        serialized_report = report.model_dump(mode="json")
        project["concept_report"] = serialized_report
        project["concepts_stale"] = False
        if project.get("verification_report") is not None:
            project["verification_stale"] = True
        if project.get("cad_report") is not None:
            project["cad_stale"] = True
        event = record_project_event(
            project,
            "concept_comparison_saved",
            f"Comparação de conceitos revisão {revision} guardada.",
            {
                "concept_revision": revision,
                "status": report.status,
                "recommended_concept_id": report.recommended_concept_id,
            },
            timestamp=timestamp,
        )
        project.setdefault("concept_history", []).append(
            {
                "revision": revision,
                "project_revision": event.project_revision,
                "created_at": timestamp,
                "legacy_snapshot": False,
                "report": deepcopy(serialized_report),
            }
        )
        project["updated_at"] = timestamp
        self.save()
        return project, revision

    def save_project_cad(
        self,
        report: ParametricCADReport,
    ) -> tuple[dict, int] | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        ensure_project_history(project, timestamp=timestamp)
        revision = int(project.get("cad_revision", 0)) + 1
        project["cad_revision"] = revision
        serialized_report = report.model_dump(mode="json")
        project["cad_report"] = serialized_report
        project["cad_stale"] = False
        if project.get("verification_report") is not None:
            project["verification_stale"] = True
        event = record_project_event(
            project,
            "cad_model_saved",
            f"Modelo CAD paramétrico revisão {revision} guardado.",
            {
                "cad_revision": revision,
                "status": report.status,
                "concept_id": report.concept_id,
                "parameter_signature": report.parameter_signature,
            },
            timestamp=timestamp,
        )
        project.setdefault("cad_history", []).append(
            {
                "revision": revision,
                "project_revision": event.project_revision,
                "created_at": timestamp,
                "legacy_snapshot": False,
                "report": deepcopy(serialized_report),
            }
        )
        project["updated_at"] = timestamp
        self.save()
        return project, revision

    def save_project_verification(
        self,
        report: EngineeringVerificationReport,
    ) -> tuple[dict, int] | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        ensure_project_history(project, timestamp=timestamp)
        revision = int(project.get("verification_revision", 0)) + 1
        project["verification_revision"] = revision
        serialized_report = report.model_dump(mode="json")
        project["verification_report"] = serialized_report
        project["verification_stale"] = False
        event = record_project_event(
            project,
            "verification_saved",
            f"Verificação independente revisão {revision} guardada.",
            {
                "verification_revision": revision,
                "status": report.status,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
            },
            timestamp=timestamp,
        )
        project.setdefault("verification_history", []).append(
            {
                "revision": revision,
                "project_revision": event.project_revision,
                "created_at": timestamp,
                "legacy_snapshot": False,
                "report": deepcopy(serialized_report),
            }
        )
        project["updated_at"] = timestamp
        self.save()
        return project, revision

    def add_project_decision(
        self,
        statement: str,
        reason: str | None = None,
    ) -> tuple[dict, str, int] | None:
        project = self.active_project()
        if project is None:
            return None
        timestamp = now_iso()
        decision, event = record_project_decision(
            project,
            statement,
            reason,
            timestamp=timestamp,
        )
        project["updated_at"] = timestamp
        self.save()
        return project, decision.id, event.project_revision


def default_memory_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "ivy_memory.json"


def default_artifact_root(memory_path: Path) -> Path:
    if memory_path.parent.name.lower() == "data":
        return memory_path.parent.parent / "artifacts"
    return memory_path.parent / "artifacts"


def _extract_name(message: str) -> str | None:
    pattern = re.compile(
        r"(?:meu nome (?:é|e)|eu me chamo|pode me chamar de)\s+"
        r"([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{0,39})",
        re.IGNORECASE,
    )
    match = pattern.search(message)
    if not match:
        return None
    candidate = re.split(r"[,.;!?]|\s+(?:e|mas|porque)\s+", match.group(1), maxsplit=1)[0]
    candidate = " ".join(candidate.strip().split())
    return candidate[:40] or None


def _after_prefix(message: str, prefixes: tuple[str, ...]) -> str | None:
    normalized_message = normalize(message).strip()
    for prefix in prefixes:
        if normalized_message.startswith(prefix):
            return message.strip()[len(prefix) :].strip(" :,-")
    return None


def _brief_from_project(project: dict) -> EngineeringBrief | None:
    try:
        return EngineeringBrief.model_validate(project.get("brief", {}))
    except (TypeError, ValueError):
        return None


def _parse_numbered_answers(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    cleaned = re.sub(
        r"^\s*(?:minhas\s+)?respostas?\s*(?:s[aã]o)?\s*[:,-]?\s*",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    )
    for part in re.split(r"\s*;\s*|\r?\n+", cleaned):
        if not part.strip():
            continue
        match = re.fullmatch(
            r"\s*(?:(?:a\s+)?resposta\s+(?:da\s+pergunta\s+)?|pergunta\s+)?"
            r"(\d+)\s*(?::|[.)-]|\bé\b|\be\b)\s*(.+?)\s*",
            part,
            flags=re.IGNORECASE,
        )
        if match:
            answers[int(match.group(1))] = match.group(2).strip()
    return answers


def _split_decision(text: str) -> tuple[str, str | None]:
    parts = re.split(
        r"\s+(?:porque|pois)\s+|\s*;\s*motivo\s*:\s*",
        text.strip(),
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    statement = parts[0].strip(" .")
    reason = parts[1].strip(" .") if len(parts) > 1 else None
    return statement, reason or None


def _looks_like_new_project_request(normalized: str) -> bool:
    patterns = (
        r"^(?:eu\s+)?(?:quero|gostaria de|preciso)\s+(?:criar|desenvolver|projetar|construir|fazer|montar)\b",
        r"^(?:crie|comece|inicie)\s+(?:um\s+)?(?:novo\s+)?projeto\b",
        r"^(?:projete|desenvolva|construa)\b",
        r"^(?:novo projeto|tenho uma ideia de projeto)\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


class IvyAssistant:
    def __init__(
        self,
        mode: AssistantMode = "auto",
        memory_path: Path | None = None,
        artifact_root: Path | None = None,
    ) -> None:
        if mode not in {"auto", "demo", "api"}:
            raise ValueError(f"Modo desconhecido: {mode}")
        self.requested_mode = mode
        resolved_memory_path = memory_path or default_memory_path()
        self.memory = WorkMemory(resolved_memory_path)
        self.artifact_root = artifact_root or default_artifact_root(resolved_memory_path)
        self.history: list[dict[str, str]] = []
        api_ready = bool(os.getenv("OPENAI_API_KEY")) and importlib.util.find_spec("openai") is not None
        if mode == "api" and not api_ready:
            raise RuntimeError(
                "A conversa online exige OPENAI_API_KEY. A Ivy ainda pode funcionar no modo local."
            )
        self.online = mode == "api" or (mode == "auto" and api_ready)
        self.model = os.getenv("IVY_MODEL", "gpt-5.6")
        self.client = None
        if self.online:
            from openai import OpenAI

            self.client = OpenAI()

    def welcome(self) -> str:
        creator_name = self.memory.data.get("creator_name")
        if creator_name:
            greeting = f"Olá, {creator_name}. Eu sou Ivy, sua assistente de trabalho e engenharia."
        elif self.memory.data.get("creator_confirmed"):
            greeting = "Olá. Eu sou Ivy, sua assistente de trabalho e engenharia. É bom falar novamente com quem me criou."
        else:
            greeting = "Olá. Eu sou Ivy, sua assistente de trabalho e engenharia."
        mode_text = "conversa online" if self.online else "modo local"
        active_project = self.memory.active_project()
        project_text = ""
        if active_project:
            project_text = (
                f"\nProjeto ativo: {active_project.get('id')} — "
                f"{active_project.get('name', 'Projeto sem nome')}."
            )
        return (
            f"{greeting}\n"
            f"Estou em {mode_text}. Posso conversar, organizar tarefas e notas, "
            f"ou abrir um projeto de engenharia.{project_text}\n"
            "Pode falar normalmente comigo. Por exemplo: 'como está o projeto?', "
            "'faça os cálculos', 'compare os mecanismos', 'crie o modelo CAD', 'verifique o projeto' "
            "ou 'mostre o histórico'."
        )

    def _help(self) -> str:
        return (
            "Você não precisa memorizar comandos. Fale comigo normalmente, por exemplo:\n"
            "- 'crie um projeto para uma garra robótica';\n"
            "- 'como está o projeto?' ou 'mostre meus projetos';\n"
            "- 'a resposta 1 é ...; a resposta 2 é ...';\n"
            "- 'faça os cálculos' ou 'mostre o último cálculo';\n"
            "- 'compare os mecanismos' ou 'mostre os conceitos';\n"
            "- 'crie o modelo CAD' ou 'mostre o último CAD';\n"
            "- 'verifique o projeto' ou 'mostre a última verificação';\n"
            "- 'mostre o histórico' ou 'registre a decisão de ...';\n"
            "- 'anote que ...' ou 'crie uma tarefa para ...';\n"
            "- 'mostre minhas notas', 'mostre minhas tarefas' ou 'qual é seu status?';\n"
            "- 'encerre a conversa' quando quiser sair.\n"
            "Os atalhos iniciados por / continuam disponíveis, mas são opcionais."
        )

    def _status(self) -> str:
        tasks = self.memory.data.get("tasks", [])
        pending = sum(1 for item in tasks if not item.get("done"))
        notes = self.memory.data.get("notes", [])
        projects = self.memory.data.get("projects", [])
        active_project = self.memory.active_project()
        if active_project:
            ensure_project_history(active_project)
        project_status = (
            f" Projeto ativo: {active_project.get('id')} — {active_project.get('name')}, "
            f"revisão {active_project.get('project_revision', 0)}."
            if active_project
            else " Nenhum projeto ativo."
        )
        connection = f"online, modelo {self.model}" if self.online else "local, sem modelo online conectado"
        return (
            f"Estado: pronta para conversar. Conexão: {connection}. "
            f"Tarefas pendentes: {pending}. Notas guardadas: {len(notes)}. "
            f"Projetos guardados: {len(projects)}.{project_status}"
        )

    def _list_tasks(self) -> str:
        tasks = self.memory.data.get("tasks", [])
        if not tasks:
            return "Ainda não há tarefas. Você pode dizer: 'crie uma tarefa para revisar o projeto'."
        lines = ["Suas tarefas:"]
        for index, item in enumerate(tasks, 1):
            marker = "concluída" if item.get("done") else "pendente"
            lines.append(f"{index}. [{marker}] {item.get('text', '')}")
        return "\n".join(lines)

    def _list_notes(self) -> str:
        notes = self.memory.data.get("notes", [])
        if not notes:
            return "Ainda não há notas. Você pode dizer: 'anote que precisamos testar o atrito'."
        return "Notas guardadas:\n" + "\n".join(
            f"{index}. {note}" for index, note in enumerate(notes, 1)
        )

    def _project(self, request: str) -> str:
        if not request.strip():
            return "Descreva o que deseja desenvolver, por exemplo: 'crie um projeto de garra robótica para 500 g'."
        brief = interpret_requirements(request, mode="auto" if self.online else "demo")
        project = self.memory.create_project(brief)
        return (
            "Vou organizar isso como um projeto de engenharia.\n\n"
            + render_report(brief)
            + f"\n\nPROJETO GUARDADO\n{project['id']} foi definido como projeto ativo. "
            "Você pode responder naturalmente, por exemplo: 'a resposta 1 é ...; a resposta 2 é ...'."
        )

    def _project_summary(self, project: dict | None = None) -> str:
        project = project or self.memory.active_project()
        if project is None:
            return "Ainda não existe um projeto ativo. Diga o que deseja desenvolver para criarmos um."
        brief = _brief_from_project(project)
        if brief is None:
            return "O projeto ativo está corrompido e não pôde ser aberto. Podemos criar um novo projeto."
        ensure_project_history(project)
        answers = project.get("answers", {})
        valid_answers = {
            int(number): str(answer)
            for number, answer in answers.items()
            if str(number).isdigit() and 1 <= int(number) <= len(brief.questions)
        }
        lines = [
            "IVY — PROJETO ATIVO",
            "=" * 28,
            f"Código: {project.get('id')}",
            f"Projeto: {brief.project_name}",
            f"Objetivo: {brief.objective}",
            f"Revisão do projeto: {int(project.get('project_revision', 0))}.",
            f"Progresso das perguntas: {len(valid_answers)}/{len(brief.questions)} respondidas.",
        ]
        if project.get("calculation_report") is not None:
            revision = int(project.get("calculation_revision", 0))
            calculation_state = "desatualizada" if project.get("calculations_stale") else "atual"
            lines.append(f"Memória de cálculo: revisão {revision}, {calculation_state}.")
        else:
            lines.append("Memória de cálculo: ainda não criada.")
        if project.get("concept_report") is not None:
            revision = int(project.get("concept_revision", 0))
            concept_state = "desatualizada" if project.get("concepts_stale") else "atual"
            lines.append(f"Comparação de conceitos: revisão {revision}, {concept_state}.")
        else:
            lines.append("Comparação de conceitos: ainda não criada.")
        if project.get("verification_report") is not None:
            revision = int(project.get("verification_revision", 0))
            verification_state = (
                "desatualizada" if project.get("verification_stale") else "atual"
            )
            try:
                verification = EngineeringVerificationReport.model_validate(
                    project.get("verification_report")
                )
                verification_status = verification.status
            except (TypeError, ValueError):
                verification_status = "corrompida"
            lines.append(
                f"Verificação independente: revisão {revision}, {verification_state}, "
                f"estado {verification_status}."
            )
        else:
            lines.append("Verificação independente: ainda não criada.")
        if project.get("cad_report") is not None:
            revision = int(project.get("cad_revision", 0))
            cad_state = "desatualizado" if project.get("cad_stale") else "atual"
            try:
                cad_report = ParametricCADReport.model_validate(project.get("cad_report"))
                cad_status = cad_report.status
            except (TypeError, ValueError):
                cad_status = "corrompido"
            lines.append(
                f"Modelo CAD paramétrico: revisão {revision}, {cad_state}, "
                f"estado {cad_status}."
            )
        else:
            lines.append("Modelo CAD paramétrico: ainda não criado.")
        if valid_answers:
            lines.extend(["", "RESPOSTAS REGISTRADAS"])
            for number in sorted(valid_answers):
                lines.append(f"{number}. {brief.questions[number - 1]}")
                lines.append(f"   Resposta: {valid_answers[number]}")
        pending = [
            (index, question)
            for index, question in enumerate(brief.questions, 1)
            if index not in valid_answers
        ]
        if pending:
            lines.extend(["", "PERGUNTAS PENDENTES"])
            lines.extend(f"{number}. {question}" for number, question in pending)
            lines.extend(
                [
                    "",
                    "Próximo passo: responder naturalmente às perguntas pendentes. "
                    "As respostas ficam guardadas mesmo depois de fechar a Ivy.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "COLETA PRIORITÁRIA CONCLUÍDA",
                    "Todas as perguntas prioritárias foram respondidas. O projeto continua "
                    "dependendo de revisão das respostas e dos cálculos de engenharia antes "
                    "da seleção de componentes ou de qualquer conclusão de segurança.",
                ]
            )
        return "\n".join(lines)

    def _calculate_project(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        brief = _brief_from_project(project)
        if brief is None:
            return "O projeto ativo não pôde ser lido. Crie um novo projeto."
        answers = {
            int(number): str(answer)
            for number, answer in project.get("answers", {}).items()
            if str(number).isdigit()
        }
        report = calculate_project(str(project.get("id")), brief, answers)
        stored = self.memory.save_project_calculation(report)
        if stored is None:
            return "Não consegui guardar a memória de cálculo."
        _, revision = stored
        verified = self._create_verification()
        verification_text = ""
        if verified is not None:
            verification, verification_revision = verified
            verification_text = "\n\n" + render_verification_summary(
                verification, verification_revision
            )
        return (
            render_calculation_report(report)
            + f"\n\nCÁLCULO GUARDADO\nRevisão {revision} vinculada ao projeto {project.get('id')}."
            + verification_text
        )

    def _show_calculations(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        raw_report = project.get("calculation_report")
        if raw_report is None:
            return "Ainda não há cálculos guardados neste projeto. Diga 'faça os cálculos' para criá-los."
        try:
            report = EngineeringCalculationReport.model_validate(raw_report)
        except (TypeError, ValueError):
            return "A memória de cálculo deste projeto está corrompida. Peça para eu refazer os cálculos."
        revision = int(project.get("calculation_revision", 0))
        stale_warning = ""
        if project.get("calculations_stale"):
            stale_warning = (
                "\n\nATENÇÃO: esta revisão está desatualizada porque respostas do projeto "
                "mudaram. Peça para eu refazer os cálculos antes de usar os resultados."
            )
        return (
            render_calculation_report(report)
            + f"\n\nMEMÓRIA GUARDADA\nRevisão {revision} do projeto {project.get('id')}."
            + stale_warning
        )

    def _compare_concepts(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        brief = _brief_from_project(project)
        if brief is None:
            return "O projeto ativo não pôde ser lido. Crie um novo projeto."
        raw_calculation = project.get("calculation_report")
        if raw_calculation is None:
            return (
                "Ainda não há uma memória de cálculo para sustentar a comparação. "
                "Diga 'faça os cálculos' e depois peça para comparar os mecanismos."
            )
        if project.get("calculations_stale"):
            return (
                "A memória de cálculo está desatualizada porque as respostas mudaram. "
                "Diga 'refaça os cálculos' antes de comparar os mecanismos."
            )
        try:
            calculation = EngineeringCalculationReport.model_validate(raw_calculation)
        except (TypeError, ValueError):
            return (
                "A memória de cálculo deste projeto está corrompida. "
                "Peça para eu refazer os cálculos antes da comparação."
            )
        report = compare_gripper_concepts(
            str(project.get("id")),
            brief,
            calculation,
            source_calculation_revision=int(project.get("calculation_revision", 0)),
        )
        stored = self.memory.save_project_concepts(report)
        if stored is None:
            return "Não consegui guardar a comparação de conceitos."
        _, revision = stored
        verified = self._create_verification()
        verification_text = ""
        if verified is not None:
            verification, verification_revision = verified
            verification_text = "\n\n" + render_verification_summary(
                verification, verification_revision
            )
        return (
            render_concept_report(report)
            + f"\n\nCOMPARAÇÃO GUARDADA\nRevisão {revision} vinculada ao projeto "
            + f"{project.get('id')}."
            + verification_text
        )

    def _show_concepts(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        raw_report = project.get("concept_report")
        if raw_report is None:
            return (
                "Ainda não há uma comparação guardada neste projeto. "
                "Diga 'compare os mecanismos' para criá-la."
            )
        try:
            report = ConceptComparisonReport.model_validate(raw_report)
        except (TypeError, ValueError):
            return (
                "A comparação guardada está corrompida. "
                "Peça para eu comparar os mecanismos novamente."
            )
        revision = int(project.get("concept_revision", 0))
        stale_warning = ""
        if project.get("concepts_stale"):
            stale_warning = (
                "\n\nATENÇÃO: esta comparação está desatualizada porque respostas ou "
                "cálculos do projeto mudaram. Refaça os cálculos e a comparação."
            )
        return (
            render_concept_report(report)
            + f"\n\nCOMPARAÇÃO GUARDADA\nRevisão {revision} do projeto {project.get('id')}."
            + stale_warning
        )

    def _create_cad_model(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        brief = _brief_from_project(project)
        if brief is None:
            return "O projeto ativo não pôde ser lido. Crie um novo projeto."
        raw_calculation = project.get("calculation_report")
        if raw_calculation is None:
            return (
                "Ainda não há uma memória de cálculo para sustentar o CAD. "
                "Diga 'faça os cálculos' antes de pedir o modelo."
            )
        if project.get("calculations_stale"):
            return (
                "A memória de cálculo está desatualizada. Diga 'refaça os cálculos' "
                "antes de gerar uma nova geometria."
            )
        raw_concepts = project.get("concept_report")
        if raw_concepts is None:
            return (
                "Antes do CAD preciso comparar os mecanismos sob as mesmas condições. "
                "Diga 'compare os mecanismos' e depois 'crie o modelo CAD'."
            )
        if project.get("concepts_stale"):
            return (
                "A comparação de conceitos está desatualizada. Refaça os cálculos e a "
                "comparação antes de gerar o CAD."
            )
        try:
            calculation = EngineeringCalculationReport.model_validate(raw_calculation)
            concepts = ConceptComparisonReport.model_validate(raw_concepts)
        except (TypeError, ValueError):
            return (
                "Os artefatos que sustentam o CAD estão corrompidos. Refaça os cálculos "
                "e a comparação de conceitos."
            )
        next_revision = int(project.get("cad_revision", 0)) + 1
        report = generate_parametric_gripper_cad(
            str(project.get("id")),
            brief,
            calculation,
            concepts,
            source_calculation_revision=int(project.get("calculation_revision", 0)),
            source_concept_revision=int(project.get("concept_revision", 0)),
            cad_revision=next_revision,
            artifact_root=self.artifact_root,
        )
        if report.status != "modelo_parametrico_preliminar":
            return render_cad_report(report)
        stored = self.memory.save_project_cad(report)
        if stored is None:
            return "Não consegui guardar o modelo CAD no projeto ativo."
        _, revision = stored
        verified = self._create_verification()
        verification_text = ""
        if verified is not None:
            verification, verification_revision = verified
            verification_text = "\n\n" + render_verification_summary(
                verification, verification_revision
            )
        return (
            render_cad_report(report)
            + f"\n\nCAD GUARDADO\nRevisão {revision} vinculada ao projeto "
            + f"{project.get('id')}."
            + verification_text
        )

    def _show_cad(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        raw_report = project.get("cad_report")
        if raw_report is None:
            return (
                "Ainda não há um modelo CAD guardado neste projeto. "
                "Diga 'crie o modelo CAD' para iniciar o detalhamento virtual."
            )
        try:
            report = ParametricCADReport.model_validate(raw_report)
        except (TypeError, ValueError):
            return "O modelo CAD guardado está corrompido. Peça para eu gerar uma nova revisão."
        revision = int(project.get("cad_revision", 0))
        stale_warning = ""
        if project.get("cad_stale"):
            stale_warning = (
                "\n\nATENÇÃO: este CAD está desatualizado porque respostas, cálculos ou "
                "conceitos mudaram. Gere uma nova revisão antes de usá-lo."
            )
        return (
            render_cad_report(report)
            + f"\n\nCAD GUARDADO\nRevisão {revision} do projeto {project.get('id')}."
            + stale_warning
        )

    def _show_project_history(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        return render_project_history(project)

    def _create_verification(
        self,
    ) -> tuple[EngineeringVerificationReport, int] | None:
        project = self.memory.active_project()
        if project is None:
            return None
        ensure_project_history(project)
        report = verify_project(project)
        stored = self.memory.save_project_verification(report)
        if stored is None:
            return None
        _, revision = stored
        return report, revision

    def _verify_project(self) -> str:
        if self.memory.active_project() is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        verified = self._create_verification()
        if verified is None:
            return "Não consegui guardar a verificação independente."
        report, revision = verified
        return (
            render_verification_report(report)
            + f"\n\nVERIFICAÇÃO GUARDADA\nRevisão {revision} vinculada ao projeto "
            + f"{report.project_id}."
        )

    def _show_verification(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        raw_report = project.get("verification_report")
        if raw_report is None:
            return (
                "Ainda não há uma verificação independente guardada. "
                "Diga 'verifique o projeto' para criá-la."
            )
        try:
            report = EngineeringVerificationReport.model_validate(raw_report)
        except (TypeError, ValueError):
            return (
                "A verificação guardada está corrompida. "
                "Peça para eu verificar o projeto novamente."
            )
        revision = int(project.get("verification_revision", 0))
        stale_warning = ""
        if project.get("verification_stale"):
            stale_warning = (
                "\n\nATENÇÃO: esta verificação está desatualizada porque respostas, "
                "cálculos ou conceitos mudaram. Peça uma nova verificação."
            )
        return (
            render_verification_report(report)
            + f"\n\nVERIFICAÇÃO GUARDADA\nRevisão {revision} do projeto {project.get('id')}."
            + stale_warning
        )

    def _show_project_decisions(self) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        return render_project_decisions(project)

    def _record_project_decision(self, payload: str) -> str:
        if self.memory.active_project() is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        statement, reason = _split_decision(payload)
        if not statement:
            return (
                "Diga qual decisão deve ser registrada, por exemplo: "
                "'registre a decisão de detalhar o conceito de fuso porque obteve a maior pontuação'."
            )
        stored = self.memory.add_project_decision(statement, reason)
        if stored is None:
            return "Não consegui guardar a decisão no projeto ativo."
        project, decision_id, project_revision = stored
        reason_text = reason or "não informado"
        return (
            f"Decisão {decision_id} registrada no projeto {project.get('id')} "
            f"na revisão {project_revision}.\n"
            f"Decisão: {statement}.\nMotivo: {reason_text}."
        )

    def _list_projects(self) -> str:
        projects = self.memory.data.get("projects", [])
        if not projects:
            return "Ainda não há projetos guardados. Diga o que deseja desenvolver para criarmos um."
        active_id = self.memory.data.get("active_project_id")
        lines = ["PROJETOS GUARDADOS"]
        for index, project in enumerate(projects, 1):
            ensure_project_history(project)
            brief = _brief_from_project(project)
            question_count = len(brief.questions) if brief else 0
            answer_count = len(project.get("answers", {}))
            marker = "ativo" if project.get("id") == active_id else "guardado"
            lines.append(
                f"{index}. [{marker}] {project.get('id')} — {project.get('name')} "
                f"(R{project.get('project_revision', 0)}; "
                f"{answer_count}/{question_count} respostas)"
            )
        lines.append("Para trocar o projeto ativo, diga por exemplo: 'use o projeto 2'.")
        return "\n".join(lines)

    def _answer_project(self, payload: str) -> str:
        project = self.memory.active_project()
        if project is None:
            return "Não existe um projeto ativo. Primeiro me diga o que deseja desenvolver."
        brief = _brief_from_project(project)
        if brief is None:
            return "O projeto ativo não pôde ser lido. Crie um novo projeto."
        answers = _parse_numbered_answers(payload)
        if not answers:
            return "Diga, por exemplo: 'a resposta 1 é ...; a resposta 2 é ...'."
        invalid = sorted(number for number in answers if number < 1 or number > len(brief.questions))
        if invalid:
            return (
                "Não encontrei "
                + ", ".join(f"a pergunta {number}" for number in invalid)
                + f". Este projeto possui perguntas de 1 a {len(brief.questions)}."
            )
        updated = self.memory.save_project_answers(answers)
        if updated is None:
            return "Não consegui guardar as respostas do projeto ativo."
        total_answers = len(updated.get("answers", {}))
        remaining = len(brief.questions) - total_answers
        saved_numbers = ", ".join(str(number) for number in sorted(answers))
        if remaining > 0:
            return (
                f"Respostas {saved_numbers} guardadas no projeto {project.get('id')}. "
                f"Revisão do projeto: {updated.get('project_revision', 0)}. "
                f"Progresso: {total_answers}/{len(brief.questions)}; faltam {remaining}. "
                "Pergunte 'o que falta no projeto?' para ver o que continua pendente."
            )
        return (
            f"Respostas {saved_numbers} guardadas no projeto {project.get('id')}. "
            f"Revisão do projeto: {updated.get('project_revision', 0)}. "
            "Todas as perguntas prioritárias foram respondidas. Peça para revisar o projeto "
            "antes de iniciarmos os cálculos."
        )

    def _online_response(self, message: str) -> str:
        risk_level, _ = assess_risk(message)
        if risk_level.value == "critico":
            return (
                "Não posso ajudar a desenvolver uma aplicação perigosa. Posso ajudar com "
                "princípios de segurança, prevenção de riscos ou um projeto alternativo seguro."
            )
        self.history.append({"role": "user", "content": message})
        input_items = [
            {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
            *self.history[-16:],
        ]
        try:
            response = self.client.responses.create(model=self.model, input=input_items)
            reply = response.output_text.strip()
        except Exception as exc:
            if self.requested_mode == "api":
                return f"A conversa online não respondeu: {exc}"
            self.online = False
            return (
                "A conexão online não respondeu, então continuei no modo local. "
                + self._local_response(message)
            )
        if not reply:
            reply = "Não consegui formular uma resposta. Pode dizer isso de outra maneira?"
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _local_response(self, message: str) -> str:
        normalized = re.sub(r"\s+", " ", normalize(message)).strip(" \t\r\n!?.,;:")
        if any(phrase in normalized for phrase in ("quem e voce", "o que voce faz", "o que consegue fazer")):
            return (
                "Sou Ivy, sua assistente de trabalho e engenharia em desenvolvimento. "
                "Já consigo manter esta conversa, guardar notas e tarefas e transformar ideias "
                "de engenharia em requisitos. Respostas abertas mais avançadas exigem a conexão online."
            )
        if normalized.startswith(("oi", "ola", "bom dia", "boa tarde", "boa noite")):
            return "Olá! É um prazer conversar com você. Como posso ajudar no seu trabalho hoje?"
        if "obrigad" in normalized or "valeu" in normalized:
            return "Por nada. Estou pronta para continuar."
        if "como voce esta" in normalized or "tudo bem" in normalized:
            return "Estou funcionando normalmente e pronta para ajudar. E por onde começamos?"
        if _looks_like_new_project_request(normalized):
            return self._project(message)
        return (
            "Entendi. Nesta versão local eu trabalho melhor com tarefas, notas e projetos de engenharia. "
            "Pergunte o que eu consigo fazer para ver exemplos. Com a conexão online, poderei conversar e raciocinar "
            "de forma muito mais ampla."
        )

    def respond(self, message: str) -> AssistantReply:
        message = message.strip()
        if not message:
            return AssistantReply("Estou ouvindo. Pode escrever o que precisa.")
        normalized = re.sub(r"\s+", " ", normalize(message)).strip(" \t\r\n!?.,;:")

        if normalized in {"/sair", "sair", "encerrar", "tchau", "ate logo"}:
            return AssistantReply(
                "Até logo. Seus projetos, versões, modelos CAD, verificações, decisões, tarefas e notas locais ficaram guardados.",
                True,
            )
        if normalized in {
            "/ajuda",
            "ajuda",
            "comandos",
            "o que voce consegue fazer",
            "o que voce pode fazer",
            "como posso usar voce",
        }:
            return AssistantReply(self._help())
        if normalized in {"/status", "status", "qual e seu status", "como esta a ivy"}:
            return AssistantReply(self._status())
        if normalized in {
            "/projeto atual",
            "/projeto ativo",
            "projeto atual",
            "projeto ativo",
            "como esta o projeto",
            "como esta o projeto atual",
            "mostre o projeto atual",
            "qual e o projeto atual",
            "quero revisar o projeto",
            "revise o projeto",
            "o que falta no projeto",
            "resuma o projeto",
        }:
            return AssistantReply(self._project_summary())
        if normalized in {
            "/projetos",
            "projetos",
            "meus projetos",
            "mostre meus projetos",
            "mostre os projetos",
            "liste meus projetos",
            "quais projetos estao guardados",
        }:
            return AssistantReply(self._list_projects())
        if normalized in {
            "/historico",
            "/histórico",
            "historico",
            "historico do projeto",
            "mostre o historico",
            "mostre o historico do projeto",
            "o que mudou no projeto",
            "linha do tempo do projeto",
        }:
            return AssistantReply(self._show_project_history())
        if normalized in {
            "/decisoes",
            "/decisões",
            "decisoes",
            "decisoes do projeto",
            "mostre as decisoes",
            "mostre as decisoes do projeto",
            "quais decisoes foram registradas",
        }:
            return AssistantReply(self._show_project_decisions())
        show_cad_phrases = (
            "mostre o modelo cad",
            "mostre o cad",
            "mostre o ultimo cad",
            "quero ver o cad",
            "onde esta o cad",
            "onde estao os arquivos cad",
            "arquivos cad",
            "modelo 3d guardado",
        )
        if normalized in {"/cad", "cad guardado", "modelo cad guardado"} or any(
            phrase in normalized for phrase in show_cad_phrases
        ):
            return AssistantReply(self._show_cad())
        create_cad_phrases = (
            "crie o modelo cad",
            "gere o modelo cad",
            "faca o modelo cad",
            "gere o cad",
            "crie o cad",
            "modele a garra",
            "crie o modelo 3d",
            "gere o modelo 3d",
            "crie a geometria da garra",
        )
        if normalized in {"/gerar cad", "/criar cad", "gerar cad"} or any(
            phrase in normalized for phrase in create_cad_phrases
        ):
            return AssistantReply(self._create_cad_model())
        show_verification_phrases = (
            "mostre a verificacao",
            "mostre a ultima verificacao",
            "quero ver a verificacao",
            "ultima verificacao",
            "verificacao guardada",
            "relatorio de verificacao",
        )
        if normalized in {"/verificacao", "verificacao do projeto"} or any(
            phrase in normalized for phrase in show_verification_phrases
        ):
            return AssistantReply(self._show_verification())
        verify_phrases = (
            "verifique o projeto",
            "verifique os calculos",
            "confira os calculos",
            "audite o projeto",
            "audite os calculos",
            "faca uma revisao independente",
            "execute a verificacao",
            "rode a verificacao",
            "valide os calculos",
        )
        if normalized in {"/verificar", "verificar projeto", "verifique"} or any(
            phrase in normalized for phrase in verify_phrases
        ):
            return AssistantReply(self._verify_project())
        show_concept_phrases = (
            "mostre os conceitos",
            "mostre a comparacao",
            "quero ver os conceitos",
            "ultima comparacao",
            "comparacao guardada",
            "recupere a comparacao",
            "qual foi o conceito recomendado",
        )
        if normalized in {"/conceitos", "conceitos guardados"} or any(
            phrase in normalized for phrase in show_concept_phrases
        ):
            return AssistantReply(self._show_concepts())
        compare_concept_phrases = (
            "compare os mecanismos",
            "compare os conceitos",
            "crie conceitos",
            "avalie os mecanismos",
            "avalie os conceitos",
            "qual mecanismo e melhor",
            "qual conceito e melhor",
        )
        if normalized in {"/comparar conceitos", "/comparar mecanismos"} or any(
            phrase in normalized for phrase in compare_concept_phrases
        ):
            return AssistantReply(self._compare_concepts())
        show_calculation_phrases = (
            "mostre os calculos",
            "mostre o calculo",
            "quero ver os calculos",
            "quero ver o calculo",
            "ultimo calculo",
            "ultima memoria de calculo",
            "memoria de calculo guardada",
            "recupere os calculos",
            "quais foram os calculos",
        )
        if normalized in {"/calculos", "/cálculos", "calculos guardados"} or any(
            phrase in normalized for phrase in show_calculation_phrases
        ):
            return AssistantReply(self._show_calculations())
        calculate_phrases = (
            "calcule o projeto",
            "calcule esse projeto",
            "faca os calculos",
            "pode calcular",
            "vamos calcular",
            "inicie os calculos",
            "execute os calculos",
            "refaca os calculos",
            "recalcule",
            "atualize os calculos",
        )
        if normalized in {"/calcular", "calcular projeto", "calcule", "calcular"} or any(
            phrase in normalized for phrase in calculate_phrases
        ):
            return AssistantReply(self._calculate_project())
        if normalized in {
            "/tarefas",
            "tarefas",
            "minhas tarefas",
            "mostre minhas tarefas",
            "liste minhas tarefas",
            "o que tenho para fazer",
        }:
            return AssistantReply(self._list_tasks())
        if normalized in {
            "/notas",
            "notas",
            "minhas notas",
            "mostre minhas notas",
            "liste minhas notas",
            "o que voce anotou",
        }:
            return AssistantReply(self._list_notes())
        if normalized in {"/limpar", "limpe o historico", "apague o historico da conversa"}:
            self.history.clear()
            return AssistantReply(
                "Histórico da conversa atual limpo. Os projetos, tarefas e notas continuam guardados."
            )

        select_match = re.fullmatch(
            r"(?:/usar projeto|/usar|usar projeto|use o projeto|abra o projeto|"
            r"selecione o projeto|mude para o projeto)\s+(?:numero\s+)?([a-z0-9-]+)",
            normalized,
        )
        if select_match:
            project = self.memory.select_project(select_match.group(1))
            if project is None:
                return AssistantReply("Não encontrei esse projeto. Peça para eu mostrar seus projetos.")
            return AssistantReply(
                f"Projeto ativo alterado para {project.get('id')} — {project.get('name')}."
            )

        answer_payload = _after_prefix(
            message,
            ("/responder", "minhas respostas são", "minhas respostas sao", "respostas"),
        )
        if answer_payload is not None:
            return AssistantReply(self._answer_project(answer_payload))

        if self.memory.active_project() and _parse_numbered_answers(message):
            return AssistantReply(self._answer_project(message))

        project_request = _after_prefix(message, ("/projeto",))
        if project_request is not None:
            return AssistantReply(self._project(project_request))

        decision = _after_prefix(
            message,
            (
                "/decisao",
                "registre a decisao de",
                "registre a decisao",
                "guarde a decisao de",
                "guarde a decisao",
                "decidimos",
            ),
        )
        if decision is not None:
            return AssistantReply(self._record_project_decision(decision))

        note = _after_prefix(
            message,
            ("/nota", "anote que", "anote", "lembre que", "guarde uma nota", "salve uma nota"),
        )
        if note is not None:
            if not note:
                return AssistantReply("O que você quer que eu anote?")
            number = self.memory.add_note(note)
            return AssistantReply(f"Anotado localmente como nota {number}: {note}")

        task = _after_prefix(
            message,
            ("/tarefa", "adicione a tarefa", "adicione uma tarefa", "crie a tarefa", "crie uma tarefa", "nova tarefa"),
        )
        if task is not None:
            if not task:
                return AssistantReply("Qual tarefa você quer adicionar?")
            number = self.memory.add_task(task)
            return AssistantReply(f"Tarefa {number} adicionada: {task}")

        complete_match = re.fullmatch(
            r"(?:/concluir|concluir tarefa|conclua a tarefa|marque a tarefa)\s+(\d+)(?:\s+como concluida)?",
            normalized,
        )
        if complete_match:
            number = int(complete_match.group(1))
            completed = self.memory.complete_task(number)
            if completed is None:
                return AssistantReply("Não encontrei essa tarefa. Peça para eu mostrar suas tarefas.")
            return AssistantReply(f"Tarefa {number} concluída: {completed}")

        if _looks_like_new_project_request(normalized):
            return AssistantReply(self._project(message))

        name = _extract_name(message)
        creator_claim = any(
            phrase in normalized
            for phrase in ("sou seu criador", "sou sua criadora", "eu criei voce", "eu criei a ivy")
        )
        if creator_claim:
            self.memory.remember_creator(name)
            name_text = f", {name}" if name else ""
            return AssistantReply(
                f"Entendido{name_text}. Vou lembrar que você criou a Ivy. "
                "É um prazer conhecer você. Posso organizar uma tarefa, guardar uma ideia "
                "ou abrir um projeto de engenharia."
            )
        if name:
            self.memory.remember_creator(name)
            return AssistantReply(f"Prazer, {name}. Vou lembrar seu nome. Como posso ajudar?")

        reply = self._online_response(message) if self.online else self._local_response(message)
        return AssistantReply(reply)


def run_assistant(mode: AssistantMode = "auto", memory_path: Path | None = None) -> int:
    assistant = IvyAssistant(mode=mode, memory_path=memory_path)
    print("IVY — ASSISTENTE DE TRABALHO")
    print("=" * 34)
    print(assistant.welcome())

    while True:
        try:
            message = input("\nVocê > ")
        except (EOFError, KeyboardInterrupt):
            print("\n\nIvy > Até logo.")
            return 0
        reply = assistant.respond(message)
        print(f"\nIvy > {reply.text}")
        if reply.should_exit:
            return 0
