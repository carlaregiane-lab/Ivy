"""Verificação independente dos artefatos de engenharia produzidos pela Ivy."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .calculator import EngineeringCalculationReport
from .cad import ParametricCADReport
from .concepts import ConceptComparisonReport
from .models import EngineeringBrief
from .safety import normalize


GRAVITY_M_S2 = 9.80665

VerificationSeverity = Literal["erro", "alerta", "informacao"]
VerificationStatus = Literal[
    "consistente_com_alertas",
    "inconsistente",
    "sem_artefatos",
]


class VerificationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: VerificationSeverity
    category: Literal[
        "integridade",
        "dependencia",
        "calculo",
        "unidade",
        "rastreabilidade",
        "hipotese",
        "seguranca",
        "conceito",
        "cad",
        "arquivo",
    ]
    title: str
    detail: str
    artifact_id: str | None = None
    expected: str | None = None
    actual: str | None = None


class EngineeringVerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"
    project_id: str
    project_name: str
    status: VerificationStatus
    calculation_revision: int | None
    concept_revision: int | None
    cad_revision: int | None = None
    checked_artifacts: list[str]
    checks_performed: int = Field(ge=0)
    passed_checks: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    findings: list[VerificationFinding]
    conclusions: list[str]
    recommended_next_step: str
    safety_validated: Literal[False] = False
    fabrication_approved: Literal[False] = False


@dataclass(frozen=True)
class _ExpectedCalculation:
    value: float
    unit: str
    classification: Literal["calculado", "estimado_por_hipotese"]


@dataclass(frozen=True)
class _ExpectedConcept:
    torque_nm: float
    revolutions: float
    speed_rpm: float
    power_w: float
    score: float


@dataclass(frozen=True)
class _ExpectedCADParameter:
    value: float
    unit: str
    classification: Literal["requisito", "derivado", "hipotese"]


class _Audit:
    def __init__(self) -> None:
        self.passed = 0
        self.findings: list[VerificationFinding] = []

    def check(
        self,
        condition: bool,
        *,
        identifier: str,
        severity: VerificationSeverity,
        category: str,
        title: str,
        detail: str,
        artifact_id: str | None = None,
        expected: str | None = None,
        actual: str | None = None,
    ) -> bool:
        if condition:
            self.passed += 1
            return True
        self.findings.append(
            VerificationFinding(
                id=identifier,
                severity=severity,
                category=category,
                title=title,
                detail=detail,
                artifact_id=artifact_id,
                expected=expected,
                actual=actual,
            )
        )
        return False

    def note(
        self,
        *,
        identifier: str,
        severity: VerificationSeverity,
        category: str,
        title: str,
        detail: str,
        artifact_id: str | None = None,
    ) -> None:
        self.findings.append(
            VerificationFinding(
                id=identifier,
                severity=severity,
                category=category,
                title=title,
                detail=detail,
                artifact_id=artifact_id,
            )
        )


def _parse_pt_number(text: str) -> float:
    cleaned = text.strip().replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")
    return float(cleaned)


def _find_number(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    try:
        return _parse_pt_number(match.group("value"))
    except ValueError:
        return None


def _answer_inputs(answers: dict[int, str]) -> dict[str, float | None]:
    text = normalize("\n".join(answers.values()))
    number = r"(?P<value>\d[\d\.,]*)"
    return {
        "continuous_current_a": _find_number(
            text, rf"{number}\s*a\b[^\n]{{0,24}}?(?:continu|nominal)"
        ),
        "peak_current_a": _find_number(
            text, rf"{number}\s*a\b[^\n]{{0,16}}?(?:de\s+)?pico"
        ),
        "hours_per_day": _find_number(text, rf"{number}\s*horas?\s+por\s+dia"),
        "life_cycles": _find_number(
            text, rf"vida\s+util[^\n]{{0,48}}?{number}\s*(?:de\s+)?ciclos"
        ),
        "maintenance_cycles": _find_number(
            text, rf"manutencao[^\n]{{0,48}}?{number}\s*(?:de\s+)?ciclos"
        ),
        "friction_coefficient": _find_number(
            text, rf"coeficiente\s+de\s+atrito\s*(?:de|=|:)?\s*{number}"
        ),
        "safety_factor": _find_number(
            text, rf"fator\s+de\s+seguranca\s*(?:de|=|:)?\s*{number}"
        ),
    }


def _requirement_value(
    brief: EngineeringBrief,
    identifier: str,
    *,
    normalized_value: bool = True,
) -> float | None:
    for requirement in brief.requirements:
        if requirement.id != identifier:
            continue
        value = requirement.normalized_value if normalized_value else requirement.original_value
        return float(value) if value is not None else None
    return None


def _expected_calculations(
    brief: EngineeringBrief,
    answers: dict[int, str],
) -> dict[str, _ExpectedCalculation]:
    expected: dict[str, _ExpectedCalculation] = {}
    mass = _requirement_value(brief, "REQ-PERF-001")
    distance = _requirement_value(brief, "REQ-PERF-002")
    time_s = _requirement_value(brief, "REQ-PERF-003")
    cadence = _requirement_value(brief, "REQ-PERF-004", normalized_value=False)
    voltage = _requirement_value(brief, "REQ-ENER-001", normalized_value=False)
    parsed = _answer_inputs(answers)

    if mass is not None:
        expected["CALC-MECH-001"] = _ExpectedCalculation(
            mass * GRAVITY_M_S2, "N", "calculado"
        )

    acceleration: float | None = None
    average_speed: float | None = None
    peak_speed: float | None = None
    if distance is not None and time_s is not None and time_s > 0:
        average_speed = distance / time_s
        acceleration = 4.0 * distance / (time_s**2)
        peak_speed = 2.0 * distance / time_s
        expected["CALC-KIN-001"] = _ExpectedCalculation(
            average_speed, "m/s", "calculado"
        )
        expected["CALC-KIN-002"] = _ExpectedCalculation(
            acceleration, "m/s²", "estimado_por_hipotese"
        )
        expected["CALC-KIN-003"] = _ExpectedCalculation(
            peak_speed, "m/s", "estimado_por_hipotese"
        )

    friction = parsed["friction_coefficient"]
    safety_factor = parsed["safety_factor"]
    if (
        mass is not None
        and acceleration is not None
        and friction is not None
        and friction > 0
        and safety_factor is not None
        and safety_factor > 0
    ):
        per_finger = safety_factor * mass * (GRAVITY_M_S2 + acceleration) / (friction * 2.0)
        expected["CALC-GRIP-001"] = _ExpectedCalculation(
            per_finger, "N por dedo", "estimado_por_hipotese"
        )
        expected["CALC-GRIP-002"] = _ExpectedCalculation(
            per_finger * 2.0, "N", "estimado_por_hipotese"
        )

    if mass is not None and average_speed is not None:
        expected["CALC-POWER-001"] = _ExpectedCalculation(
            mass * GRAVITY_M_S2 * average_speed, "W", "calculado"
        )
        if acceleration is not None and peak_speed is not None:
            expected["CALC-POWER-002"] = _ExpectedCalculation(
                mass * (GRAVITY_M_S2 + acceleration) * peak_speed,
                "W",
                "estimado_por_hipotese",
            )

    continuous_current = parsed["continuous_current_a"]
    peak_current = parsed["peak_current_a"]
    if voltage is not None and continuous_current is not None:
        expected["CALC-ENER-001"] = _ExpectedCalculation(
            voltage * continuous_current, "W", "calculado"
        )
    if voltage is not None and peak_current is not None:
        expected["CALC-ENER-002"] = _ExpectedCalculation(
            voltage * peak_current, "W", "calculado"
        )

    cycles_per_day: float | None = None
    if cadence is not None and cadence > 0:
        expected["CALC-DUTY-001"] = _ExpectedCalculation(
            60.0 / cadence, "s/ciclo", "calculado"
        )
    hours_per_day = parsed["hours_per_day"]
    if cadence is not None and hours_per_day is not None:
        cycles_per_day = cadence * 60.0 * hours_per_day
        expected["CALC-DUTY-002"] = _ExpectedCalculation(
            cycles_per_day, "ciclos/dia", "calculado"
        )
    maintenance_cycles = parsed["maintenance_cycles"]
    life_cycles = parsed["life_cycles"]
    if cycles_per_day and maintenance_cycles is not None:
        expected["CALC-LIFE-001"] = _ExpectedCalculation(
            maintenance_cycles / cycles_per_day, "dias de operação", "calculado"
        )
    if cycles_per_day and life_cycles is not None:
        expected["CALC-LIFE-002"] = _ExpectedCalculation(
            life_cycles / cycles_per_day, "dias de operação", "calculado"
        )
    return expected


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


def _expected_concepts(
    brief: EngineeringBrief,
    expected_calculations: dict[str, _ExpectedCalculation],
) -> dict[str, _ExpectedConcept]:
    width_range = _width_range_mm(brief)
    grip = expected_calculations.get("CALC-GRIP-001")
    if width_range is None or grip is None:
        return {}
    minimum_mm, maximum_mm = width_range
    travel_mm = (maximum_mm - minimum_mm) / 2.0
    travel_m = travel_mm / 1000.0
    force = grip.value
    closing_time_s = 1.0

    screw_lead_mm = 8.0
    screw_efficiency = 0.35
    screw_torque = 2.0 * force * (screw_lead_mm / 1000.0) / (
        2.0 * math.pi * screw_efficiency
    )
    screw_revolutions = travel_mm / screw_lead_mm
    screw_rpm = screw_revolutions * 60.0 / closing_time_s

    rack_radius_m = 10.0 / 1000.0
    rack_efficiency = 0.85
    rack_torque = 2.0 * force * rack_radius_m / rack_efficiency
    rack_rotation_rad = travel_m / rack_radius_m
    rack_revolutions = rack_rotation_rad / (2.0 * math.pi)
    rack_rpm = rack_revolutions * 60.0 / closing_time_s

    pulley_radius_m = 12.0 / 1000.0
    belt_efficiency = 0.90
    belt_torque = 2.0 * force * pulley_radius_m / belt_efficiency
    belt_rotation_rad = travel_m / pulley_radius_m
    belt_revolutions = belt_rotation_rad / (2.0 * math.pi)
    belt_rpm = belt_revolutions * 60.0 / closing_time_s

    return {
        "CONCEPT-SCREW-001": _ExpectedConcept(
            screw_torque,
            screw_revolutions,
            screw_rpm,
            screw_torque * (2.0 * math.pi * screw_rpm / 60.0),
            3.40,
        ),
        "CONCEPT-RACK-001": _ExpectedConcept(
            rack_torque,
            rack_revolutions,
            rack_rpm,
            rack_torque * rack_rotation_rad / closing_time_s,
            3.10,
        ),
        "CONCEPT-BELT-001": _ExpectedConcept(
            belt_torque,
            belt_revolutions,
            belt_rpm,
            belt_torque * belt_rotation_rad / closing_time_s,
            2.95,
        ),
    }


def _expected_cad_parameters(
    brief: EngineeringBrief,
) -> dict[str, _ExpectedCADParameter]:
    width_range = _width_range_mm(brief)
    if width_range is None:
        return {}
    minimum_mm, maximum_mm = width_range
    travel_mm = (maximum_mm - minimum_mm) / 2.0
    base_length_mm = max(
        150.0,
        math.ceil((maximum_mm + 60.0) / 10.0) * 10.0,
    )
    values: dict[str, tuple[float, Literal["requisito", "derivado", "hipotese"]]] = {
        "CAD-PARAM-001": (minimum_mm, "requisito"),
        "CAD-PARAM-002": (maximum_mm, "requisito"),
        "CAD-PARAM-003": (travel_mm, "derivado"),
        "CAD-PARAM-004": (maximum_mm, "derivado"),
        "CAD-PARAM-005": (base_length_mm, "hipotese"),
        "CAD-PARAM-006": (60.0, "hipotese"),
        "CAD-PARAM-007": (10.0, "hipotese"),
        "CAD-PARAM-008": (24.0, "hipotese"),
        "CAD-PARAM-009": (44.0, "hipotese"),
        "CAD-PARAM-010": (12.0, "hipotese"),
        "CAD-PARAM-011": (12.0, "hipotese"),
        "CAD-PARAM-012": (20.0, "hipotese"),
        "CAD-PARAM-013": (50.0, "hipotese"),
        "CAD-PARAM-014": (6.0, "hipotese"),
        "CAD-PARAM-015": (8.0, "hipotese"),
        "CAD-PARAM-016": (8.0, "hipotese"),
        "CAD-PARAM-017": (base_length_mm - 10.0, "hipotese"),
        "CAD-PARAM-018": (8.0, "hipotese"),
        "CAD-PARAM-019": (32.0, "hipotese"),
        "CAD-PARAM-020": (0.5, "hipotese"),
    }
    return {
        identifier: _ExpectedCADParameter(value, "mm", classification)
        for identifier, (value, classification) in values.items()
    }


def _cad_parameter_signature(report: ParametricCADReport) -> str | None:
    if (
        report.concept_id is None
        or report.source_calculation_revision is None
        or report.source_concept_revision is None
    ):
        return None
    payload = {
        "project_id": report.project_id,
        "concept_id": report.concept_id,
        "source_calculation_revision": report.source_calculation_revision,
        "source_concept_revision": report.source_concept_revision,
        "parameters": [
            parameter.model_dump(mode="json")
            for parameter in sorted(report.parameters, key=lambda item: item.id)
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and math.isclose(
        actual, expected, rel_tol=1e-7, abs_tol=1e-9
    )


def _number(value: float) -> str:
    return f"{value:.9g}"


def _check_history_snapshot(
    audit: _Audit,
    project: dict,
    *,
    artifact_name: str,
    revision_key: str,
    history_key: str,
    report_key: str,
) -> None:
    revision = int(project.get(revision_key, 0) or 0)
    history = project.get(history_key, [])
    current = project.get(report_key)
    matching = [item for item in history if int(item.get("revision", -1)) == revision]
    audit.check(
        revision > 0,
        identifier=f"VRF-HIST-{artifact_name.upper()}-001",
        severity="erro",
        category="integridade",
        title=f"Revisão de {artifact_name} inválida",
        detail="Um artefato atual deve possuir número de revisão positivo.",
        expected="revisão >= 1",
        actual=str(revision),
    )
    if audit.check(
        len(matching) == 1,
        identifier=f"VRF-HIST-{artifact_name.upper()}-002",
        severity="erro",
        category="integridade",
        title=f"Histórico de {artifact_name} inconsistente",
        detail="A revisão atual deve aparecer exatamente uma vez no histórico versionado.",
        expected="1 fotografia da revisão atual",
        actual=str(len(matching)),
    ):
        audit.check(
            matching[0].get("report") == current,
            identifier=f"VRF-HIST-{artifact_name.upper()}-003",
            severity="erro",
            category="integridade",
            title=f"Fotografia de {artifact_name} divergente",
            detail="O relatório atual difere da fotografia preservada para a mesma revisão.",
        )


def _verify_calculations(
    audit: _Audit,
    project: dict,
    brief: EngineeringBrief,
    answers: dict[int, str],
) -> tuple[EngineeringCalculationReport | None, dict[str, _ExpectedCalculation]]:
    raw_report = project.get("calculation_report")
    expected = _expected_calculations(brief, answers)
    if raw_report is None:
        audit.note(
            identifier="VRF-CALC-000",
            severity="informacao",
            category="dependencia",
            title="Memória de cálculo ausente",
            detail="Ainda não existe uma memória de cálculo para verificar.",
        )
        return None, expected
    try:
        report = EngineeringCalculationReport.model_validate(raw_report)
    except (TypeError, ValueError) as exc:
        audit.note(
            identifier="VRF-CALC-001",
            severity="erro",
            category="integridade",
            title="Memória de cálculo inválida",
            detail=f"O relatório não atende ao contrato de dados: {exc}",
        )
        return None, expected

    audit.check(
        not bool(project.get("calculations_stale")),
        identifier="VRF-CALC-002",
        severity="erro",
        category="dependencia",
        title="Memória de cálculo desatualizada",
        detail="As respostas mudaram depois desta revisão; os resultados devem ser recalculados.",
    )
    audit.check(
        report.project_id == str(project.get("id")),
        identifier="VRF-CALC-003",
        severity="erro",
        category="rastreabilidade",
        title="Projeto do cálculo divergente",
        detail="O identificador do relatório não corresponde ao projeto ativo.",
        expected=str(project.get("id")),
        actual=report.project_id,
    )
    _check_history_snapshot(
        audit,
        project,
        artifact_name="calculo",
        revision_key="calculation_revision",
        history_key="calculation_history",
        report_key="calculation_report",
    )

    identifiers = [item.id for item in report.calculations]
    audit.check(
        len(identifiers) == len(set(identifiers)),
        identifier="VRF-CALC-004",
        severity="erro",
        category="integridade",
        title="Identificadores de cálculo duplicados",
        detail="Cada resultado precisa ter um identificador único.",
    )
    actual_by_id = {item.id: item for item in report.calculations}
    for identifier, spec in expected.items():
        result = actual_by_id.get(identifier)
        if not audit.check(
            result is not None,
            identifier=f"VRF-{identifier}-PRESENCE",
            severity="erro",
            category="dependencia",
            title="Resultado esperado ausente",
            detail="Os dados atuais permitem o cálculo, mas o resultado não foi encontrado.",
            artifact_id=identifier,
        ):
            continue
        assert result is not None
        audit.check(
            _close(float(result.value), spec.value),
            identifier=f"VRF-{identifier}-VALUE",
            severity="erro",
            category="calculo",
            title="Valor numérico divergente",
            detail="O verificador recalculou o valor por uma rotina independente.",
            artifact_id=identifier,
            expected=_number(spec.value),
            actual=_number(float(result.value)),
        )
        audit.check(
            result.unit == spec.unit,
            identifier=f"VRF-{identifier}-UNIT",
            severity="erro",
            category="unidade",
            title="Unidade divergente",
            detail="A unidade declarada não corresponde à grandeza verificada.",
            artifact_id=identifier,
            expected=spec.unit,
            actual=result.unit,
        )
        audit.check(
            result.classification == spec.classification,
            identifier=f"VRF-{identifier}-CLASS",
            severity="erro",
            category="hipotese",
            title="Classificação do resultado divergente",
            detail="Valores dependentes de hipóteses devem permanecer identificados como estimativas.",
            artifact_id=identifier,
            expected=spec.classification,
            actual=result.classification,
        )
        audit.check(
            bool(result.formula.strip())
            and bool(result.substitution.strip())
            and bool(result.input_sources),
            identifier=f"VRF-{identifier}-TRACE",
            severity="erro",
            category="rastreabilidade",
            title="Rastreabilidade incompleta",
            detail="Fórmula, substituição e fontes são obrigatórias em cada resultado.",
            artifact_id=identifier,
        )

    for identifier in sorted(set(actual_by_id) - set(expected)):
        audit.note(
            identifier=f"VRF-{identifier}-UNEXPECTED",
            severity="erro",
            category="dependencia",
            title="Resultado sem entradas suficientes",
            detail="O relatório contém um resultado que o verificador não conseguiu derivar dos dados atuais.",
            artifact_id=identifier,
        )

    classifications = {item.id: item.classification for item in report.calculations}
    for result in report.calculations:
        if result.classification != "estimado_por_hipotese":
            continue
        normalized_sources = [normalize(source) for source in result.input_sources]
        has_hypothesis = any("hipotese" in source for source in normalized_sources)
        has_estimated_dependency = any(
            classifications.get(source) == "estimado_por_hipotese"
            for source in result.input_sources
        )
        audit.check(
            has_hypothesis or has_estimated_dependency,
            identifier=f"VRF-{result.id}-HYP",
            severity="alerta",
            category="hipotese",
            title="Hipótese não rastreada",
            detail="Uma estimativa deve apontar diretamente para a hipótese ou para outro resultado estimado.",
            artifact_id=result.id,
        )

    blocked_text = normalize(" ".join(report.blocked_calculations))
    for suffix, term, label in (
        ("TORQUE", "torque e rotacao", "torque e rotação do atuador"),
        ("PETG", "petg", "resistência e deformação do PETG"),
        ("PEOPLE", "perto de pessoas", "limite de força perto de pessoas"),
        ("COST", "custo total", "custo total"),
    ):
        audit.check(
            term in blocked_text,
            identifier=f"VRF-CALC-BLOCK-{suffix}",
            severity="erro",
            category="seguranca" if suffix == "PEOPLE" else "dependencia",
            title="Bloqueio obrigatório ausente",
            detail=f"O relatório deve manter bloqueado: {label}.",
        )
    return report, expected


def _verify_concepts(
    audit: _Audit,
    project: dict,
    brief: EngineeringBrief,
    expected_calculations: dict[str, _ExpectedCalculation],
) -> ConceptComparisonReport | None:
    raw_report = project.get("concept_report")
    if raw_report is None:
        audit.note(
            identifier="VRF-CONCEPT-000",
            severity="informacao",
            category="dependencia",
            title="Comparação de conceitos ausente",
            detail="A memória de cálculo pode ser verificada sem uma comparação mecânica.",
        )
        return None
    try:
        report = ConceptComparisonReport.model_validate(raw_report)
    except (TypeError, ValueError) as exc:
        audit.note(
            identifier="VRF-CONCEPT-001",
            severity="erro",
            category="integridade",
            title="Comparação de conceitos inválida",
            detail=f"O relatório não atende ao contrato de dados: {exc}",
        )
        return None

    audit.check(
        not bool(project.get("concepts_stale")),
        identifier="VRF-CONCEPT-002",
        severity="erro",
        category="dependencia",
        title="Comparação desatualizada",
        detail="Respostas ou cálculos mudaram depois desta comparação.",
    )
    audit.check(
        report.project_id == str(project.get("id")),
        identifier="VRF-CONCEPT-003",
        severity="erro",
        category="rastreabilidade",
        title="Projeto da comparação divergente",
        detail="O identificador da comparação não corresponde ao projeto ativo.",
        expected=str(project.get("id")),
        actual=report.project_id,
    )
    _check_history_snapshot(
        audit,
        project,
        artifact_name="conceito",
        revision_key="concept_revision",
        history_key="concept_history",
        report_key="concept_report",
    )

    source_revision = report.source_calculation_revision
    current_calculation_revision = int(project.get("calculation_revision", 0) or 0)
    if source_revision is None:
        audit.note(
            identifier="VRF-CONCEPT-004",
            severity="alerta",
            category="dependencia",
            title="Revisão de origem não registrada",
            detail="Comparações antigas são aceitas, mas não informam explicitamente qual revisão de cálculo utilizaram.",
        )
    else:
        audit.check(
            source_revision == current_calculation_revision,
            identifier="VRF-CONCEPT-005",
            severity="erro",
            category="dependencia",
            title="Revisão de cálculo incompatível",
            detail="A comparação deve apontar para a memória de cálculo atualmente ativa.",
            expected=str(current_calculation_revision),
            actual=str(source_revision),
        )

    expected = _expected_concepts(brief, expected_calculations)
    identifiers = [concept.id for concept in report.concepts]
    audit.check(
        len(identifiers) == len(set(identifiers)),
        identifier="VRF-CONCEPT-006",
        severity="erro",
        category="integridade",
        title="Identificadores de conceito duplicados",
        detail="Cada alternativa mecânica deve ter um identificador único.",
    )
    actual_by_id = {concept.id: concept for concept in report.concepts}
    numeric_fields = (
        ("required_torque_nm", "torque_nm", "torque"),
        ("rotation_revolutions", "revolutions", "rotações"),
        ("required_speed_rpm", "speed_rpm", "velocidade"),
        ("estimated_input_power_w", "power_w", "potência"),
        ("weighted_score", "score", "pontuação"),
    )
    for identifier, spec in expected.items():
        concept = actual_by_id.get(identifier)
        if not audit.check(
            concept is not None,
            identifier=f"VRF-{identifier}-PRESENCE",
            severity="erro",
            category="conceito",
            title="Conceito esperado ausente",
            detail="A comparação completa deve conter as três arquiteturas do benchmark.",
            artifact_id=identifier,
        ):
            continue
        assert concept is not None
        for actual_attr, expected_attr, label in numeric_fields:
            actual_value = float(getattr(concept, actual_attr))
            expected_value = float(getattr(spec, expected_attr))
            audit.check(
                _close(actual_value, expected_value),
                identifier=f"VRF-{identifier}-{actual_attr.upper()}",
                severity="erro",
                category="conceito",
                title=f"{label.capitalize()} do conceito divergente",
                detail="O valor foi recalculado a partir das mesmas entradas por uma rotina independente.",
                artifact_id=identifier,
                expected=_number(expected_value),
                actual=_number(actual_value),
            )

    for identifier in sorted(set(actual_by_id) - set(expected)):
        audit.note(
            identifier=f"VRF-{identifier}-UNEXPECTED",
            severity="erro",
            category="conceito",
            title="Conceito sem entradas suficientes",
            detail="A comparação apresenta uma alternativa que não pôde ser reproduzida.",
            artifact_id=identifier,
        )

    if expected:
        expected_ranking = [
            identifier
            for identifier, _ in sorted(
                expected.items(), key=lambda item: item[1].score, reverse=True
            )
        ]
        actual_ranking = []
        for item in report.ranking:
            match = re.search(r"CONCEPT-[A-Z]+-\d+", item)
            if match:
                actual_ranking.append(match.group(0))
        audit.check(
            actual_ranking == expected_ranking,
            identifier="VRF-CONCEPT-RANKING",
            severity="erro",
            category="conceito",
            title="Ranking divergente",
            detail="A ordem publicada não corresponde às pontuações recalculadas.",
            expected=", ".join(expected_ranking),
            actual=", ".join(actual_ranking),
        )
        audit.check(
            report.recommended_concept_id == expected_ranking[0],
            identifier="VRF-CONCEPT-RECOMMENDATION",
            severity="erro",
            category="conceito",
            title="Recomendação incompatível com o ranking",
            detail="A recomendação preliminar deve corresponder ao conceito de maior pontuação.",
            expected=expected_ranking[0],
            actual=str(report.recommended_concept_id),
        )
    return report


def _verify_cad(
    audit: _Audit,
    project: dict,
    brief: EngineeringBrief,
    concept_report: ConceptComparisonReport | None,
) -> ParametricCADReport | None:
    raw_report = project.get("cad_report")
    if raw_report is None:
        audit.note(
            identifier="VRF-CAD-000",
            severity="informacao",
            category="dependencia",
            title="Modelo CAD ausente",
            detail="Ainda não existe uma geometria paramétrica para verificar.",
        )
        return None
    try:
        report = ParametricCADReport.model_validate(raw_report)
    except (TypeError, ValueError) as exc:
        audit.note(
            identifier="VRF-CAD-001",
            severity="erro",
            category="integridade",
            title="Relatório CAD inválido",
            detail=f"O relatório não atende ao contrato de dados: {exc}",
        )
        return None

    audit.check(
        not bool(project.get("cad_stale")),
        identifier="VRF-CAD-002",
        severity="erro",
        category="dependencia",
        title="Modelo CAD desatualizado",
        detail="Respostas, cálculos ou conceitos mudaram depois desta geometria.",
    )
    audit.check(
        report.project_id == str(project.get("id")),
        identifier="VRF-CAD-003",
        severity="erro",
        category="rastreabilidade",
        title="Projeto do CAD divergente",
        detail="O identificador do relatório CAD não corresponde ao projeto ativo.",
        expected=str(project.get("id")),
        actual=report.project_id,
    )
    _check_history_snapshot(
        audit,
        project,
        artifact_name="cad",
        revision_key="cad_revision",
        history_key="cad_history",
        report_key="cad_report",
    )
    current_calculation_revision = int(project.get("calculation_revision", 0) or 0)
    current_concept_revision = int(project.get("concept_revision", 0) or 0)
    audit.check(
        report.source_calculation_revision == current_calculation_revision,
        identifier="VRF-CAD-004",
        severity="erro",
        category="dependencia",
        title="Origem de cálculo incompatível",
        detail="O CAD deve apontar para a memória de cálculo atualmente ativa.",
        expected=str(current_calculation_revision),
        actual=str(report.source_calculation_revision),
    )
    audit.check(
        report.source_concept_revision == current_concept_revision,
        identifier="VRF-CAD-005",
        severity="erro",
        category="dependencia",
        title="Origem de conceito incompatível",
        detail="O CAD deve apontar para a comparação de conceitos atualmente ativa.",
        expected=str(current_concept_revision),
        actual=str(report.source_concept_revision),
    )
    expected_concept_id = (
        concept_report.recommended_concept_id if concept_report is not None else None
    )
    audit.check(
        concept_report is not None,
        identifier="VRF-CAD-006",
        severity="erro",
        category="dependencia",
        title="Comparação de origem ausente",
        detail="Uma geometria CAD não pode existir sem uma comparação de conceitos rastreável.",
    )
    audit.check(
        report.concept_id == expected_concept_id == "CONCEPT-SCREW-001",
        identifier="VRF-CAD-007",
        severity="erro",
        category="cad",
        title="Conceito do CAD divergente",
        detail="A versão 0.9 deve modelar o conceito de fuso recomendado pela comparação ativa.",
        expected=str(expected_concept_id),
        actual=str(report.concept_id),
    )
    audit.check(
        report.status == "modelo_parametrico_preliminar",
        identifier="VRF-CAD-008",
        severity="erro",
        category="cad",
        title="Estado do CAD incompatível",
        detail="Um modelo guardado deve permanecer identificado como preliminar.",
        expected="modelo_parametrico_preliminar",
        actual=report.status,
    )

    expected_parameters = _expected_cad_parameters(brief)
    identifiers = [parameter.id for parameter in report.parameters]
    audit.check(
        len(identifiers) == len(set(identifiers)),
        identifier="VRF-CAD-009",
        severity="erro",
        category="integridade",
        title="Parâmetros CAD duplicados",
        detail="Cada dimensão deve possuir um identificador único.",
    )
    actual_by_id = {parameter.id: parameter for parameter in report.parameters}
    for identifier, spec in expected_parameters.items():
        parameter = actual_by_id.get(identifier)
        if not audit.check(
            parameter is not None,
            identifier=f"VRF-{identifier}-PRESENCE",
            severity="erro",
            category="cad",
            title="Parâmetro CAD esperado ausente",
            detail="A geometria completa da versão 0.9 deve conter este parâmetro.",
            artifact_id=identifier,
        ):
            continue
        assert parameter is not None
        audit.check(
            _close(float(parameter.value), spec.value),
            identifier=f"VRF-{identifier}-VALUE",
            severity="erro",
            category="cad",
            title="Valor do parâmetro CAD divergente",
            detail="O verificador refez a derivação dimensional por uma rotina independente.",
            artifact_id=identifier,
            expected=_number(spec.value),
            actual=_number(float(parameter.value)),
        )
        audit.check(
            parameter.unit == spec.unit,
            identifier=f"VRF-{identifier}-UNIT",
            severity="erro",
            category="unidade",
            title="Unidade do parâmetro CAD divergente",
            detail="Os parâmetros dimensionais da versão 0.9 devem permanecer em milímetros.",
            artifact_id=identifier,
            expected=spec.unit,
            actual=parameter.unit,
        )
        audit.check(
            parameter.classification == spec.classification,
            identifier=f"VRF-{identifier}-CLASS",
            severity="erro",
            category="hipotese",
            title="Classificação do parâmetro CAD divergente",
            detail="Requisitos, valores derivados e hipóteses devem continuar separados.",
            artifact_id=identifier,
            expected=spec.classification,
            actual=parameter.classification,
        )
        audit.check(
            bool(parameter.symbol.strip())
            and bool(parameter.description.strip())
            and bool(parameter.source.strip()),
            identifier=f"VRF-{identifier}-TRACE",
            severity="erro",
            category="rastreabilidade",
            title="Rastreabilidade do parâmetro incompleta",
            detail="Símbolo, descrição e fonte são obrigatórios para cada dimensão.",
            artifact_id=identifier,
        )
    for identifier in sorted(set(actual_by_id) - set(expected_parameters)):
        audit.note(
            identifier=f"VRF-{identifier}-UNEXPECTED",
            severity="erro",
            category="cad",
            title="Parâmetro CAD inesperado",
            detail="O relatório contém uma dimensão que o contrato v0.9 não reconhece.",
            artifact_id=identifier,
        )

    expected_signature = _cad_parameter_signature(report)
    audit.check(
        expected_signature is not None and report.parameter_signature == expected_signature,
        identifier="VRF-CAD-SIGNATURE",
        severity="erro",
        category="integridade",
        title="Assinatura dos parâmetros divergente",
        detail="A assinatura deve representar exatamente o projeto, as revisões e os parâmetros publicados.",
        expected=str(expected_signature),
        actual=str(report.parameter_signature),
    )

    check_ids = [check.id for check in report.checks]
    audit.check(
        len(check_ids) == len(set(check_ids)),
        identifier="VRF-CAD-CHECKS-001",
        severity="erro",
        category="integridade",
        title="Verificações geométricas duplicadas",
        detail="Cada regra geométrica deve possuir identificador único.",
    )
    checks_by_id = {check.id: check for check in report.checks}
    for number in range(1, 11):
        identifier = f"CAD-CHK-{number:03d}"
        check = checks_by_id.get(identifier)
        audit.check(
            check is not None and check.status == "aprovado",
            identifier=f"VRF-{identifier}",
            severity="erro",
            category="cad",
            title="Verificação geométrica ausente ou reprovada",
            detail="O conjunto de dez regras dimensionais deve estar presente e aprovado.",
            artifact_id=identifier,
            expected="aprovado",
            actual=check.status if check is not None else "ausente",
        )
    for number in (11, 12):
        identifier = f"CAD-CHK-{number:03d}"
        check = checks_by_id.get(identifier)
        audit.check(
            check is not None and check.status == "alerta",
            identifier=f"VRF-{identifier}",
            severity="erro",
            category="seguranca",
            title="Alerta obrigatório do CAD ausente",
            detail="O modelo deve manter visíveis os limites de validação e detalhamento.",
            artifact_id=identifier,
            expected="alerta",
            actual=check.status if check is not None else "ausente",
        )

    required_kinds = {
        "openscad_model",
        "stl_preview",
        "svg_preview",
        "manifest",
    }
    artifact_kinds = [artifact.kind for artifact in report.artifacts]
    audit.check(
        set(artifact_kinds) == required_kinds and len(artifact_kinds) == len(required_kinds),
        identifier="VRF-CAD-FILES-001",
        severity="erro",
        category="arquivo",
        title="Conjunto de arquivos CAD incompleto",
        detail="OpenSCAD, STL, SVG e manifesto devem existir exatamente uma vez.",
        expected=", ".join(sorted(required_kinds)),
        actual=", ".join(sorted(artifact_kinds)),
    )
    output_directory: Path | None = None
    if report.output_directory:
        try:
            output_directory = Path(report.output_directory).resolve()
        except OSError:
            output_directory = None
    audit.check(
        output_directory is not None,
        identifier="VRF-CAD-FILES-002",
        severity="erro",
        category="arquivo",
        title="Diretório CAD inválido",
        detail="O relatório deve registrar um diretório de saída válido.",
    )
    for artifact in report.artifacts:
        path = Path(artifact.path)
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        inside_directory = (
            output_directory is not None
            and resolved.parent == output_directory
            and resolved.name == artifact.filename
        )
        audit.check(
            inside_directory,
            identifier=f"VRF-CAD-FILE-{artifact.kind.upper()}-PATH",
            severity="erro",
            category="arquivo",
            title="Caminho de artefato divergente",
            detail="Cada arquivo deve permanecer no diretório da revisão CAD e coincidir com o nome registrado.",
            artifact_id=artifact.filename,
        )
        exists = resolved.is_file()
        if not audit.check(
            exists,
            identifier=f"VRF-CAD-FILE-{artifact.kind.upper()}-PRESENCE",
            severity="erro",
            category="arquivo",
            title="Arquivo CAD ausente",
            detail="O arquivo registrado não foi encontrado no disco.",
            artifact_id=artifact.filename,
        ):
            continue
        size = resolved.stat().st_size
        audit.check(
            size == artifact.byte_size,
            identifier=f"VRF-CAD-FILE-{artifact.kind.upper()}-SIZE",
            severity="erro",
            category="arquivo",
            title="Tamanho do arquivo divergente",
            detail="O tamanho atual não corresponde ao manifesto persistido.",
            artifact_id=artifact.filename,
            expected=str(artifact.byte_size),
            actual=str(size),
        )
        if size > 25_000_000:
            audit.note(
                identifier=f"VRF-CAD-FILE-{artifact.kind.upper()}-LIMIT",
                severity="erro",
                category="arquivo",
                title="Arquivo CAD excede o limite de verificação",
                detail="Arquivos acima de 25 MB não são lidos automaticamente pelo verificador local.",
                artifact_id=artifact.filename,
            )
            continue
        data = resolved.read_bytes()
        digest = sha256(data).hexdigest()
        audit.check(
            digest == artifact.sha256,
            identifier=f"VRF-CAD-FILE-{artifact.kind.upper()}-HASH",
            severity="erro",
            category="arquivo",
            title="Conteúdo do arquivo foi alterado",
            detail="O SHA-256 atual não corresponde ao valor guardado com a revisão CAD.",
            artifact_id=artifact.filename,
            expected=artifact.sha256,
            actual=digest,
        )
        text = data.decode("utf-8", errors="replace")
        if artifact.kind == "openscad_model":
            normalized_text = normalize(text)
            audit.check(
                "assembly();" in text
                and "assert(" in text
                and "include <" not in normalized_text
                and "use <" not in normalized_text
                and str(report.parameter_signature) in text,
                identifier="VRF-CAD-FILE-SCAD-CONTENT",
                severity="erro",
                category="arquivo",
                title="Contrato do arquivo OpenSCAD divergente",
                detail="O modelo deve ser autônomo, paramétrico e conter a assinatura da revisão.",
                artifact_id=artifact.filename,
            )
        elif artifact.kind == "stl_preview":
            audit.check(
                text.startswith("solid ivy_")
                and "facet normal" in text
                and "endsolid ivy_" in text,
                identifier="VRF-CAD-FILE-STL-CONTENT",
                severity="erro",
                category="arquivo",
                title="Prévia STL inválida",
                detail="A visualização deve possuir um sólido ASCII com facetas completas.",
                artifact_id=artifact.filename,
            )
        elif artifact.kind == "svg_preview":
            audit.check(
                "<svg" in text
                and "</svg>" in text
                and "nao aprovado para fabricacao" in normalize(text),
                identifier="VRF-CAD-FILE-SVG-CONTENT",
                severity="erro",
                category="arquivo",
                title="Prévia SVG inválida",
                detail="A prévia deve ser um SVG completo e exibir o bloqueio de fabricação.",
                artifact_id=artifact.filename,
            )
        elif artifact.kind == "manifest":
            try:
                manifest = json.loads(text)
            except json.JSONDecodeError:
                manifest = None
            audit.check(
                isinstance(manifest, dict)
                and manifest.get("parameter_signature") == report.parameter_signature
                and manifest.get("cad_revision") == int(project.get("cad_revision", 0) or 0)
                and manifest.get("fabrication_approved") is False
                and manifest.get("safety_validated") is False,
                identifier="VRF-CAD-FILE-MANIFEST-CONTENT",
                severity="erro",
                category="arquivo",
                title="Manifesto CAD inválido",
                detail="O manifesto deve repetir a assinatura, a revisão e os bloqueios formais.",
                artifact_id=artifact.filename,
            )

    blocked_text = normalize(" ".join(report.blocked_verifications))
    for suffix, term, label in (
        ("STRUCT", "analise estrutural", "análise estrutural"),
        ("INTERFERENCE", "interferencias", "verificação de interferências"),
        ("RISK", "analise de risco", "análise de risco"),
        ("SIMULATION", "simular", "simulação do mecanismo"),
    ):
        audit.check(
            term in blocked_text,
            identifier=f"VRF-CAD-BLOCK-{suffix}",
            severity="erro",
            category="seguranca" if suffix == "RISK" else "dependencia",
            title="Bloqueio obrigatório do CAD ausente",
            detail=f"O relatório deve manter bloqueado: {label}.",
        )
    return report


def verify_project(project: dict) -> EngineeringVerificationReport:
    """Audita um projeto sem alterar os cálculos nem os conceitos verificados."""

    audit = _Audit()
    project_id = str(project.get("id") or "desconhecido")
    project_name = str(project.get("name") or "Projeto sem nome")
    checked_artifacts: list[str] = []
    try:
        brief = EngineeringBrief.model_validate(project.get("brief", {}))
    except (TypeError, ValueError) as exc:
        audit.note(
            identifier="VRF-PROJECT-001",
            severity="erro",
            category="integridade",
            title="Briefing inválido",
            detail=f"O contrato de requisitos não pôde ser validado: {exc}",
        )
        brief = None
    else:
        checked_artifacts.append("briefing de requisitos")
        audit.check(
            brief.project_name == project_name,
            identifier="VRF-PROJECT-002",
            severity="alerta",
            category="rastreabilidade",
            title="Nome do projeto divergente",
            detail="O nome persistido e o nome do briefing deveriam coincidir.",
            expected=project_name,
            actual=brief.project_name,
        )

    answers = {
        int(number): str(answer)
        for number, answer in project.get("answers", {}).items()
        if str(number).isdigit()
    }
    calculation_report: EngineeringCalculationReport | None = None
    concept_report: ConceptComparisonReport | None = None
    cad_report: ParametricCADReport | None = None
    expected_calculations: dict[str, _ExpectedCalculation] = {}
    if brief is not None:
        calculation_report, expected_calculations = _verify_calculations(
            audit, project, brief, answers
        )
        if project.get("calculation_report") is not None:
            checked_artifacts.append("memória de cálculo")
        concept_report = _verify_concepts(audit, project, brief, expected_calculations)
        if project.get("concept_report") is not None:
            checked_artifacts.append("comparação de conceitos")
        cad_report = _verify_cad(audit, project, brief, concept_report)
        if project.get("cad_report") is not None:
            checked_artifacts.append("modelo CAD paramétrico")

    if calculation_report is not None:
        warnings_text = normalize(" ".join(calculation_report.warnings))
        audit.check(
            "nenhum motor" in warnings_text,
            identifier="VRF-SAFE-001",
            severity="erro",
            category="seguranca",
            title="Limite de seleção de motor ausente",
            detail="A memória de cálculo deve declarar que nenhum motor foi selecionado.",
        )
        audit.check(
            "nao foi declarado seguro" in warnings_text,
            identifier="VRF-SAFE-002",
            severity="erro",
            category="seguranca",
            title="Limite de segurança ausente",
            detail="A memória deve declarar que o projeto não foi considerado seguro ou pronto.",
        )
    if concept_report is not None:
        audit.check(
            concept_report.motor_selected is False,
            identifier="VRF-SAFE-003",
            severity="erro",
            category="seguranca",
            title="Seleção indevida de motor",
            detail="A comparação de conceitos não pode selecionar motor ou componente comercial.",
        )
        audit.check(
            concept_report.safety_validated is False,
            identifier="VRF-SAFE-004",
            severity="erro",
            category="seguranca",
            title="Validação indevida de segurança",
            detail="A comparação não pode declarar segurança física validada.",
        )
    if cad_report is not None:
        audit.check(
            cad_report.component_selected is False,
            identifier="VRF-SAFE-005",
            severity="erro",
            category="seguranca",
            title="Seleção indevida de componente no CAD",
            detail="O modelo preliminar não pode selecionar componentes comerciais.",
        )
        audit.check(
            cad_report.safety_validated is False,
            identifier="VRF-SAFE-006",
            severity="erro",
            category="seguranca",
            title="Validação indevida de segurança no CAD",
            detail="A geometria não pode declarar segurança física validada.",
        )
        audit.check(
            cad_report.fabrication_approved is False,
            identifier="VRF-SAFE-007",
            severity="erro",
            category="seguranca",
            title="Aprovação indevida de fabricação",
            detail="O CAD v0.9 deve permanecer bloqueado para fabricação.",
        )

    audit.note(
        identifier="VRF-SCOPE-001",
        severity="alerta",
        category="seguranca",
        title="Escopo limitado da verificação",
        detail=(
            "A coerência matemática e documental não substitui análise de risco, "
            "simulação física, ensaios, normas aplicáveis ou revisão profissional."
        ),
    )

    has_engineering_artifact = bool(
        project.get("calculation_report") is not None
        or project.get("concept_report") is not None
        or project.get("cad_report") is not None
    )
    error_count = sum(item.severity == "erro" for item in audit.findings)
    warning_count = sum(item.severity == "alerta" for item in audit.findings)
    if not has_engineering_artifact:
        status: VerificationStatus = "sem_artefatos"
    elif error_count:
        status = "inconsistente"
    else:
        status = "consistente_com_alertas"

    conclusions: list[str] = []
    if status == "sem_artefatos":
        conclusions.append("Ainda não existem cálculos ou conceitos para uma auditoria numérica.")
        next_step = "Criar a memória de cálculo e executar novamente a verificação independente."
    elif status == "inconsistente":
        conclusions.append(
            f"Foram encontradas {error_count} inconsistência(s) que impedem o uso técnico dos artefatos atuais."
        )
        next_step = (
            "Corrigir as inconsistências, refazer os artefatos afetados e repetir a verificação antes de usar a recomendação."
        )
    else:
        conclusions.append(
            "Os valores, unidades e dependências verificáveis estão coerentes com as entradas atuais."
        )
        if cad_report is not None:
            next_step = (
                "Revisar a geometria e avançar para simulação estrutural e cinemática; "
                "segurança e fabricação continuam bloqueadas."
            )
        else:
            next_step = (
                "Manter as hipóteses visíveis e avançar somente para detalhamento virtual; "
                "segurança e fabricação continuam bloqueadas."
            )
    conclusions.append(
        "Esta verificação não valida segurança, resistência física, conformidade normativa nem prontidão para fabricação."
    )

    return EngineeringVerificationReport(
        project_id=project_id,
        project_name=project_name,
        status=status,
        calculation_revision=(
            int(project.get("calculation_revision", 0) or 0)
            if project.get("calculation_report") is not None
            else None
        ),
        concept_revision=(
            int(project.get("concept_revision", 0) or 0)
            if project.get("concept_report") is not None
            else None
        ),
        cad_revision=(
            int(project.get("cad_revision", 0) or 0)
            if project.get("cad_report") is not None
            else None
        ),
        checked_artifacts=checked_artifacts,
        checks_performed=audit.passed + len(audit.findings),
        passed_checks=audit.passed,
        warning_count=warning_count,
        error_count=error_count,
        findings=audit.findings,
        conclusions=conclusions,
        recommended_next_step=next_step,
    )


def render_verification_report(report: EngineeringVerificationReport) -> str:
    lines = [
        "IVY — VERIFICAÇÃO INDEPENDENTE",
        "=" * 38,
        f"Projeto: {report.project_id} — {report.project_name}",
        f"Estado: {report.status}",
        f"Revisão de cálculo verificada: {report.calculation_revision or 'não disponível'}",
        f"Revisão de conceitos verificada: {report.concept_revision or 'não disponível'}",
        f"Revisão CAD verificada: {report.cad_revision or 'não disponível'}",
        "",
        "RESUMO",
        f"- Verificações executadas: {report.checks_performed}.",
        f"- Verificações aprovadas: {report.passed_checks}.",
        f"- Alertas: {report.warning_count}.",
        f"- Erros: {report.error_count}.",
        "- Artefatos: " + (", ".join(report.checked_artifacts) or "nenhum"),
        "",
        "ACHADOS",
    ]
    if not report.findings:
        lines.append("- Nenhuma divergência foi encontrada nas verificações executadas.")
    for finding in report.findings:
        lines.append(
            f"- [{finding.severity.upper()}] {finding.id} — {finding.title}"
        )
        lines.append(f"  {finding.detail}")
        if finding.artifact_id:
            lines.append(f"  Artefato: {finding.artifact_id}")
        if finding.expected is not None or finding.actual is not None:
            lines.append(
                f"  Esperado: {finding.expected or 'não informado'} | "
                f"Encontrado: {finding.actual or 'não informado'}"
            )
    lines.extend(["", "CONCLUSÕES"])
    lines.extend(f"- {item}" for item in report.conclusions)
    lines.extend(
        [
            "",
            "LIMITES FORMAIS",
            "- Segurança validada: não.",
            "- Fabricação aprovada: não.",
            "",
            "PRÓXIMO PASSO",
            report.recommended_next_step,
        ]
    )
    return "\n".join(lines)


def render_verification_summary(
    report: EngineeringVerificationReport,
    revision: int,
) -> str:
    gate = (
        "Uso técnico e recomendação bloqueados até a correção dos erros."
        if report.error_count
        else "Coerência interna confirmada; segurança e fabricação continuam bloqueadas."
    )
    return (
        "VERIFICAÇÃO AUTOMÁTICA\n"
        f"Revisão {revision}: {report.status}; {report.passed_checks} verificações aprovadas, "
        f"{report.warning_count} alerta(s) e {report.error_count} erro(s).\n"
        f"{gate} "
        "Diga 'mostre a verificação' para abrir o relatório completo."
    )
