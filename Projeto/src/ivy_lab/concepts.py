"""Comparação determinística de conceitos mecânicos para projetos da Ivy."""

from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .calculator import EngineeringCalculationReport
from .models import EngineeringBrief
from .safety import normalize


class MechanismConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    principle: str
    geometry_assumptions: list[str]
    torque_formula: str
    torque_substitution: str
    required_torque_nm: float
    rotation_revolutions: float
    required_speed_rpm: float
    estimated_input_power_w: float
    weighted_score: float
    advantages: list[str]
    limitations: list[str]
    classification: Literal["estimado_por_hipotese"] = "estimado_por_hipotese"


class ConceptComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"
    project_id: str
    project_name: str
    source_calculation_revision: int | None = None
    status: Literal["comparacao_preliminar", "bloqueado"]
    traced_inputs: list[str]
    shared_assumptions: list[str]
    concepts: list[MechanismConcept]
    ranking: list[str]
    recommended_concept_id: str | None
    recommendation: str
    blocked_verifications: list[str]
    warnings: list[str]
    formula_sources: list[str]
    recommended_next_step: str
    motor_selected: Literal[False] = False
    safety_validated: Literal[False] = False


def _parse_pt_number(text: str) -> float:
    cleaned = text.strip().replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    return float(cleaned)


def _width_range_mm(brief: EngineeringBrief) -> tuple[float, float] | None:
    text = normalize(
        "\n".join(
            [brief.original_request]
            + [requirement.statement for requirement in brief.requirements]
        )
    )
    number = r"\d[\d\.,]*"
    match = re.search(
        rf"(?:entre|de)\s*(?P<minimum>{number})\s*(?:e|a|-)\s*"
        rf"(?P<maximum>{number})\s*(?P<unit>mm|cm|m)\s*(?:de\s+)?largura",
        text,
    )
    if not match:
        return None
    minimum = _parse_pt_number(match.group("minimum"))
    maximum = _parse_pt_number(match.group("maximum"))
    factor = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[match.group("unit")]
    minimum_mm, maximum_mm = minimum * factor, maximum * factor
    if minimum_mm <= 0 or maximum_mm <= minimum_mm:
        return None
    return minimum_mm, maximum_mm


def _calculation_value(
    report: EngineeringCalculationReport,
    identifier: str,
) -> float | None:
    for calculation in report.calculations:
        if calculation.id == identifier:
            return float(calculation.value)
    return None


def _score(values: dict[str, float]) -> float:
    weights = {
        "holding_control": 0.30,
        "efficiency": 0.20,
        "manufacturability": 0.20,
        "compactness": 0.15,
        "failure_behavior": 0.15,
    }
    return sum(values[key] * weight for key, weight in weights.items())


def compare_gripper_concepts(
    project_id: str,
    brief: EngineeringBrief,
    calculation_report: EngineeringCalculationReport,
    source_calculation_revision: int | None = None,
) -> ConceptComparisonReport:
    """Compara geometrias sem selecionar atuador ou declarar segurança."""

    width_range = _width_range_mm(brief)
    force_per_finger_n = _calculation_value(calculation_report, "CALC-GRIP-001")
    traced_inputs: list[str] = []
    blocked: list[str] = []

    if width_range is None:
        blocked.append("Curso dos dedos: falta uma faixa válida de largura ou abertura da garra.")
    else:
        minimum_mm, maximum_mm = width_range
        traced_inputs.append(
            f"Abertura útil = {minimum_mm:g}-{maximum_mm:g} mm [REQ-GEOM-001]."
        )

    if force_per_finger_n is None:
        blocked.append(
            "Força de fechamento: falta CALC-GRIP-001 em uma memória de cálculo atual."
        )
    else:
        traced_inputs.append(
            f"Força normal de referência = {force_per_finger_n:.6g} N por dedo [CALC-GRIP-001]."
        )

    formula_sources = [
        "Thomson Linear — torque de fuso: T = F * avanço / (2 * pi * eficiência).",
        "KHK Gears — o deslocamento da cremalheira por rotação corresponde à circunferência primitiva do pinhão.",
        "Gates — torque de correia: M = tensão efetiva * diâmetro primitivo / 2; eficiência deve ser considerada no acionamento.",
    ]
    warnings = [
        "Todos os resultados são estimativas de comparação baseadas em geometrias hipotéticas.",
        "Nenhum motor, redutor, driver, fuso, engrenagem, correia ou fornecedor foi selecionado.",
        "A comparação não valida resistência, desgaste, temperatura, folga, ruído ou segurança perto de pessoas.",
    ]
    shared_assumptions = [
        "Os dois dedos se movem simetricamente; cada dedo percorre metade da variação total de abertura.",
        "Foi adotado tempo comparativo de 1,0 s para fechar a garra; esse valor ainda deve ser confirmado no ciclo completo.",
        "A força de referência é aplicada durante todo o curso apenas para produzir uma comparação conservadora entre conceitos.",
        "A pontuação preliminar usa pesos: retenção/controle 30%, eficiência 20%, fabricação 20%, compacidade 15% e comportamento em falha 15%.",
    ]

    if width_range is None or force_per_finger_n is None:
        return ConceptComparisonReport(
            project_id=project_id,
            project_name=brief.project_name,
            source_calculation_revision=source_calculation_revision,
            status="bloqueado",
            traced_inputs=traced_inputs,
            shared_assumptions=shared_assumptions,
            concepts=[],
            ranking=[],
            recommended_concept_id=None,
            recommendation=(
                "A comparação não pode começar até existirem uma faixa de abertura e uma força "
                "de aperto rastreável."
            ),
            blocked_verifications=blocked,
            warnings=warnings,
            formula_sources=formula_sources,
            recommended_next_step="Completar os dados bloqueados e refazer os cálculos do projeto.",
        )

    minimum_mm, maximum_mm = width_range
    finger_travel_mm = (maximum_mm - minimum_mm) / 2.0
    finger_travel_m = finger_travel_mm / 1000.0
    closing_time_s = 1.0
    concepts: list[MechanismConcept] = []

    screw_lead_mm = 8.0
    screw_efficiency = 0.35
    screw_lead_m = screw_lead_mm / 1000.0
    screw_torque = (
        2.0 * force_per_finger_n * screw_lead_m / (2.0 * math.pi * screw_efficiency)
    )
    screw_revolutions = finger_travel_mm / screw_lead_mm
    screw_rpm = screw_revolutions * 60.0 / closing_time_s
    screw_power = screw_torque * (2.0 * math.pi * screw_rpm / 60.0)
    concepts.append(
        MechanismConcept(
            id="CONCEPT-SCREW-001",
            name="Fuso único com roscas opostas",
            principle="Um eixo com roscas direita e esquerda move os dois dedos de forma simétrica.",
            geometry_assumptions=[
                f"Avanço hipotético do fuso = {screw_lead_mm:g} mm/volta.",
                f"Eficiência comparativa = {screw_efficiency:.2f}.",
                f"Curso por dedo = {finger_travel_mm:g} mm.",
            ],
            torque_formula="T = 2 * F_dedo * avanço / (2 * pi * eficiência)",
            torque_substitution=(
                f"T = 2 * {force_per_finger_n:.6g} * {screw_lead_m:g} / "
                f"(2 * pi * {screw_efficiency:g})"
            ),
            required_torque_nm=screw_torque,
            rotation_revolutions=screw_revolutions,
            required_speed_rpm=screw_rpm,
            estimated_input_power_w=screw_power,
            weighted_score=_score(
                {
                    "holding_control": 5,
                    "efficiency": 2,
                    "manufacturability": 3,
                    "compactness": 3,
                    "failure_behavior": 3,
                }
            ),
            advantages=[
                "Boa resolução de posição e força por controle de rotação.",
                "Pode manter a posição com menor tendência a retorno, dependendo do avanço e do atrito reais.",
                "Torque estimado menor que nos conceitos de acionamento direto.",
            ],
            limitations=[
                "Exige maior rotação para cumprir o tempo de fechamento.",
                "Eficiência, folga, desgaste e aquecimento dependem do fuso e da porca reais.",
                "Autotravamento não pode ser presumido sem verificar geometria e atrito.",
            ],
        )
    )

    pinion_radius_mm = 10.0
    rack_efficiency = 0.85
    pinion_radius_m = pinion_radius_mm / 1000.0
    rack_torque = 2.0 * force_per_finger_n * pinion_radius_m / rack_efficiency
    rack_rotation_rad = finger_travel_m / pinion_radius_m
    rack_revolutions = rack_rotation_rad / (2.0 * math.pi)
    rack_rpm = rack_revolutions * 60.0 / closing_time_s
    rack_power = rack_torque * rack_rotation_rad / closing_time_s
    concepts.append(
        MechanismConcept(
            id="CONCEPT-RACK-001",
            name="Pinhão central com duas cremalheiras",
            principle="Um pinhão central desloca duas cremalheiras opostas ligadas aos dedos.",
            geometry_assumptions=[
                f"Raio primitivo hipotético = {pinion_radius_mm:g} mm.",
                f"Eficiência comparativa = {rack_efficiency:.2f}.",
                f"Curso por dedo = {finger_travel_mm:g} mm.",
            ],
            torque_formula="T = 2 * F_dedo * raio / eficiência",
            torque_substitution=(
                f"T = 2 * {force_per_finger_n:.6g} * {pinion_radius_m:g} / {rack_efficiency:g}"
            ),
            required_torque_nm=rack_torque,
            rotation_revolutions=rack_revolutions,
            required_speed_rpm=rack_rpm,
            estimated_input_power_w=rack_power,
            weighted_score=_score(
                {
                    "holding_control": 2,
                    "efficiency": 4,
                    "manufacturability": 4,
                    "compactness": 4,
                    "failure_behavior": 2,
                }
            ),
            advantages=[
                "Movimento simétrico simples e relação geométrica direta.",
                "Baixa rotação estimada para o curso requerido.",
                "Geometria adequada para protótipos e inspeção visual do movimento.",
            ],
            limitations=[
                "Torque direto mais alto e tendência a retorno sem freio ou transmissão adicional.",
                "Dentes impressos em PETG exigem verificação de desgaste, folga e resistência.",
                "O alinhamento das duas cremalheiras é crítico para evitar travamento.",
            ],
        )
    )

    pulley_radius_mm = 12.0
    belt_efficiency = 0.90
    pulley_radius_m = pulley_radius_mm / 1000.0
    belt_torque = 2.0 * force_per_finger_n * pulley_radius_m / belt_efficiency
    belt_rotation_rad = finger_travel_m / pulley_radius_m
    belt_revolutions = belt_rotation_rad / (2.0 * math.pi)
    belt_rpm = belt_revolutions * 60.0 / closing_time_s
    belt_power = belt_torque * belt_rotation_rad / closing_time_s
    concepts.append(
        MechanismConcept(
            id="CONCEPT-BELT-001",
            name="Correia sincronizadora com carros opostos",
            principle="Os dedos são ligados a trechos opostos de uma correia para se moverem simetricamente.",
            geometry_assumptions=[
                f"Raio primitivo hipotético da polia = {pulley_radius_mm:g} mm.",
                f"Eficiência comparativa do conjunto = {belt_efficiency:.2f}.",
                f"Curso por dedo = {finger_travel_mm:g} mm.",
            ],
            torque_formula="T = 2 * F_dedo * raio / eficiência",
            torque_substitution=(
                f"T = 2 * {force_per_finger_n:.6g} * {pulley_radius_m:g} / {belt_efficiency:g}"
            ),
            required_torque_nm=belt_torque,
            rotation_revolutions=belt_revolutions,
            required_speed_rpm=belt_rpm,
            estimated_input_power_w=belt_power,
            weighted_score=_score(
                {
                    "holding_control": 1,
                    "efficiency": 5,
                    "manufacturability": 3,
                    "compactness": 4,
                    "failure_behavior": 3,
                }
            ),
            advantages=[
                "Movimento suave, baixa rotação e eficiência comparativa alta.",
                "Pouca folga quando a correia está corretamente tensionada.",
                "Possibilidade de separar o atuador da região dos dedos.",
            ],
            limitations=[
                "Não mantém força sem atuação ou freio e depende de pré-tensão.",
                "Capacidade dos dentes, largura da correia e vida em fadiga ainda são desconhecidas.",
                "Perda de tensão ou salto de dentes pode liberar a carga.",
            ],
        )
    )

    ranked = sorted(concepts, key=lambda concept: concept.weighted_score, reverse=True)
    ranking = [
        f"{index}. {concept.id} — {concept.name}: {concept.weighted_score:.2f}/5"
        for index, concept in enumerate(ranked, 1)
    ]
    recommended = ranked[0]
    blocked.extend(
        [
            "Confirmar quanto do ciclo de 5 s está disponível para fechar e abrir os dedos.",
            "Definir envelope, dimensões reais, guias lineares, mancais, eixos e fixações.",
            "Verificar tensões, deformações, fluência, fadiga e anisotropia do PETG.",
            "Medir eficiência, folga, atrito, desgaste e regime térmico em protótipo de baixa energia.",
            "Executar análise formal de risco para esmagamento, soltura da carga e falta de energia.",
            "Selecionar componentes somente após curvas torque-velocidade, corrente, custo e disponibilidade.",
        ]
    )
    return ConceptComparisonReport(
        project_id=project_id,
        project_name=brief.project_name,
        source_calculation_revision=source_calculation_revision,
        status="comparacao_preliminar",
        traced_inputs=traced_inputs,
        shared_assumptions=shared_assumptions,
        concepts=concepts,
        ranking=ranking,
        recommended_concept_id=recommended.id,
        recommendation=(
            "O fuso com roscas opostas é o conceito recomendado apenas para detalhamento e teste virtual, "
            "por combinar controle de posição, retenção potencial e menor torque estimado. A recomendação "
            "não seleciona um componente e pode mudar após medir eficiência, tempo real do ciclo, folga, "
            "desgaste e comportamento em falha."
        ),
        blocked_verifications=blocked,
        warnings=warnings,
        formula_sources=formula_sources,
        recommended_next_step=(
            "Modelar parametricamente o conceito de fuso, confirmar o tempo de fechamento e definir "
            "diâmetro, avanço, guias e envelope antes de comparar curvas reais de atuadores."
        ),
    )


def _number_pt(value: float) -> str:
    rendered = f"{value:.3f}".rstrip("0").rstrip(".")
    return rendered.replace(".", ",")


def render_concept_report(report: ConceptComparisonReport) -> str:
    lines = [
        "IVY — COMPARAÇÃO DE CONCEITOS",
        "=" * 38,
        f"Projeto: {report.project_id} — {report.project_name}",
        f"Estado: {report.status}",
        f"Memória de cálculo de origem: revisão {report.source_calculation_revision or 'legada/não informada'}",
        "",
        "ENTRADAS RASTREADAS",
    ]
    lines.extend(f"- {item}" for item in report.traced_inputs)
    lines.extend(["", "HIPÓTESES COMUNS"])
    lines.extend(f"- {item}" for item in report.shared_assumptions)
    lines.extend(["", "CONCEITOS"])
    if not report.concepts:
        lines.append("- Nenhum conceito pôde ser calculado com os dados atuais.")
    for concept in report.concepts:
        lines.extend(
            [
                f"- {concept.id} — {concept.name} [estimado por hipótese]",
                f"  Princípio: {concept.principle}",
                "  Geometria: " + " ".join(concept.geometry_assumptions),
                f"  Fórmula de torque: {concept.torque_formula}",
                f"  Substituição: {concept.torque_substitution}",
                f"  Torque estimado: {_number_pt(concept.required_torque_nm)} N·m",
                f"  Rotação para fechar: {_number_pt(concept.rotation_revolutions)} volta(s)",
                f"  Velocidade estimada: {_number_pt(concept.required_speed_rpm)} rpm",
                f"  Potência mecânica de entrada estimada: {_number_pt(concept.estimated_input_power_w)} W",
                f"  Pontuação preliminar: {_number_pt(concept.weighted_score)}/5",
                "  Vantagens: " + "; ".join(concept.advantages),
                "  Limitações: " + "; ".join(concept.limitations),
            ]
        )
    lines.extend(["", "RANKING PRELIMINAR"])
    lines.extend(f"- {item}" for item in report.ranking)
    lines.extend(["", "RECOMENDAÇÃO PARA DETALHAMENTO", report.recommendation])
    lines.extend(["", "VERIFICAÇÕES AINDA BLOQUEADAS"])
    lines.extend(f"- {item}" for item in report.blocked_verifications)
    lines.extend(["", "ALERTAS"])
    lines.extend(f"- {item}" for item in report.warnings)
    lines.extend(["", "FONTES DAS FÓRMULAS"])
    lines.extend(f"- {item}" for item in report.formula_sources)
    lines.extend(["", "PRÓXIMO PASSO", report.recommended_next_step])
    return "\n".join(lines)
