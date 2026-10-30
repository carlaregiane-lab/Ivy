"""Formatação dos resultados verificáveis produzidos pela Ivy."""

from __future__ import annotations

from .models import EngineeringBrief


DOMAIN_LABELS = {
    "mecanica": "mecânica",
    "mecatronica": "mecatrônica",
    "eletrica": "elétrica",
    "eletronica": "eletrônica",
    "software": "software",
    "materiais": "materiais",
    "civil": "civil",
    "outra": "outra",
}
RISK_LABELS = {
    "baixo": "baixo",
    "medio": "médio",
    "alto": "alto",
    "critico": "crítico",
}
READINESS_LABELS = {
    "necessita_esclarecimentos": "necessita de esclarecimentos",
    "pronto_para_conceito": "pronto para conceito",
    "bloqueado_por_risco": "bloqueado por risco",
}


def _number_pt(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def render_report(brief: EngineeringBrief) -> str:
    lines = [
        "IVY — BRIEFING DE REQUISITOS",
        "=" * 36,
        f"Projeto: {brief.project_name}",
        f"Objetivo: {brief.objective}",
        "Áreas: " + ", ".join(DOMAIN_LABELS[domain.value] for domain in brief.domains),
        f"Risco preliminar: {RISK_LABELS[brief.risk_level.value]}",
        f"Estado: {READINESS_LABELS[brief.readiness.value]}",
        "",
        "REQUISITOS CONFIRMADOS",
    ]

    if not brief.requirements:
        lines.append("- Nenhum requisito mensurável foi confirmado.")
    for requirement in brief.requirements:
        normalized = ""
        if (
            requirement.normalized_value is not None
            and requirement.original_value is not None
            and (
                requirement.normalized_value != requirement.original_value
                or requirement.normalized_unit != requirement.original_unit
            )
        ):
            normalized = (
                f" [normalizado: {_number_pt(requirement.normalized_value)} "
                f"{requirement.normalized_unit}]"
            )
        lines.append(f"- {requirement.id}: {requirement.statement}{normalized}")

    if brief.derived_values:
        lines.extend(["", "VALORES DERIVADOS POR CÁLCULO"])
        lines.extend(f"- {item}" for item in brief.derived_values)

    lines.extend(["", "INFORMAÇÕES AUSENTES"])
    lines.extend(f"- {item}" for item in brief.unknowns)

    if brief.calculation_plan:
        lines.extend(["", "CÁLCULOS E VERIFICAÇÕES NECESSÁRIOS"])
        lines.extend(f"- {item}" for item in brief.calculation_plan)

    lines.extend(["", "PERGUNTAS PRIORITÁRIAS"])
    lines.extend(f"{index}. {question}" for index, question in enumerate(brief.questions, 1))

    if brief.safety_flags:
        lines.extend(["", "ALERTAS DE SEGURANÇA"])
        lines.extend(f"- {item}" for item in brief.safety_flags)

    lines.extend(["", "PRÓXIMO PASSO", brief.recommended_next_step])
    return "\n".join(lines)
