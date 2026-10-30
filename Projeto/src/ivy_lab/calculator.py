"""Cálculos determinísticos e rastreáveis para projetos da Ivy."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import EngineeringBrief
from .safety import normalize


GRAVITY_M_S2 = 9.80665


class CalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    formula: str
    substitution: str
    value: float
    unit: str
    classification: Literal["calculado", "estimado_por_hipotese"]
    input_sources: list[str] = Field(default_factory=list)


class EngineeringCalculationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"
    project_id: str
    project_name: str
    status: Literal["parcial", "bloqueado"]
    inputs: list[str]
    assumptions: list[str]
    calculations: list[CalculationResult]
    blocked_calculations: list[str]
    warnings: list[str]
    recommended_next_step: str


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


def _answer_inputs(answers: dict[int, str]) -> dict[str, float | None]:
    text = normalize("\n".join(answers.values()))
    number = r"(?P<value>\d[\d\.,]*)"
    return {
        "continuous_current_a": _find_number(
            text,
            rf"{number}\s*a\b[^\n]{{0,24}}?(?:continu|nominal)",
        ),
        "peak_current_a": _find_number(
            text,
            rf"{number}\s*a\b[^\n]{{0,16}}?(?:de\s+)?pico",
        ),
        "hours_per_day": _find_number(
            text,
            rf"{number}\s*horas?\s+por\s+dia",
        ),
        "life_cycles": _find_number(
            text,
            rf"vida\s+util[^\n]{{0,48}}?{number}\s*(?:de\s+)?ciclos",
        ),
        "maintenance_cycles": _find_number(
            text,
            rf"manutencao[^\n]{{0,48}}?{number}\s*(?:de\s+)?ciclos",
        ),
        "friction_coefficient": _find_number(
            text,
            rf"coeficiente\s+de\s+atrito\s*(?:de|=|:)?\s*{number}",
        ),
        "safety_factor": _find_number(
            text,
            rf"fator\s+de\s+seguranca\s*(?:de|=|:)?\s*{number}",
        ),
    }


def _result(
    identifier: str,
    name: str,
    formula: str,
    substitution: str,
    value: float,
    unit: str,
    classification: Literal["calculado", "estimado_por_hipotese"],
    sources: list[str],
) -> CalculationResult:
    return CalculationResult(
        id=identifier,
        name=name,
        formula=formula,
        substitution=substitution,
        value=value,
        unit=unit,
        classification=classification,
        input_sources=sources,
    )


def calculate_project(
    project_id: str,
    brief: EngineeringBrief,
    answers: dict[int, str],
) -> EngineeringCalculationReport:
    """Calcula apenas o que pode ser rastreado até requisitos e respostas."""

    mass_kg = _requirement_value(brief, "REQ-PERF-001")
    distance_m = _requirement_value(brief, "REQ-PERF-002")
    time_s = _requirement_value(brief, "REQ-PERF-003")
    cycles_per_minute = _requirement_value(
        brief,
        "REQ-PERF-004",
        normalized_value=False,
    )
    voltage_v = _requirement_value(
        brief,
        "REQ-ENER-001",
        normalized_value=False,
    )
    parsed = _answer_inputs(answers)

    inputs: list[str] = []
    calculations: list[CalculationResult] = []
    assumptions = ["A aceleração da gravidade usada é g = 9,80665 m/s²."]
    blocked: list[str] = []
    warnings: list[str] = []

    if mass_kg is not None:
        inputs.append(f"Massa m = {mass_kg:g} kg [REQ-PERF-001].")
        weight_n = mass_kg * GRAVITY_M_S2
        calculations.append(
            _result(
                "CALC-MECH-001",
                "Peso estático da carga",
                "W = m * g",
                f"W = {mass_kg:g} * {GRAVITY_M_S2:g}",
                weight_n,
                "N",
                "calculado",
                ["REQ-PERF-001", "constante g"],
            )
        )
    else:
        blocked.append("Peso e forças: falta a massa confirmada da carga.")

    acceleration_m_s2: float | None = None
    average_speed_m_s: float | None = None
    peak_speed_m_s: float | None = None
    if distance_m is not None and time_s is not None and time_s > 0:
        inputs.extend(
            [
                f"Elevação s = {distance_m:g} m [REQ-PERF-002].",
                f"Tempo de elevação t = {time_s:g} s [REQ-PERF-003].",
            ]
        )
        average_speed_m_s = distance_m / time_s
        calculations.append(
            _result(
                "CALC-KIN-001",
                "Velocidade média de elevação",
                "v_media = s / t",
                f"v_media = {distance_m:g} / {time_s:g}",
                average_speed_m_s,
                "m/s",
                "calculado",
                ["REQ-PERF-002", "REQ-PERF-003"],
            )
        )
        assumptions.append(
            "Para a estimativa dinâmica, foi adotado perfil triangular simétrico: metade do tempo acelerando e metade desacelerando."
        )
        acceleration_m_s2 = 4.0 * distance_m / (time_s**2)
        peak_speed_m_s = 2.0 * distance_m / time_s
        calculations.extend(
            [
                _result(
                    "CALC-KIN-002",
                    "Aceleração do perfil triangular",
                    "a = 4 * s / t²",
                    f"a = 4 * {distance_m:g} / {time_s:g}²",
                    acceleration_m_s2,
                    "m/s²",
                    "estimado_por_hipotese",
                    ["REQ-PERF-002", "REQ-PERF-003", "hipótese de perfil triangular"],
                ),
                _result(
                    "CALC-KIN-003",
                    "Velocidade de pico do perfil triangular",
                    "v_pico = 2 * s / t",
                    f"v_pico = 2 * {distance_m:g} / {time_s:g}",
                    peak_speed_m_s,
                    "m/s",
                    "estimado_por_hipotese",
                    ["REQ-PERF-002", "REQ-PERF-003", "hipótese de perfil triangular"],
                ),
            ]
        )
    else:
        blocked.append("Cinemática: faltam distância e tempo de elevação confirmados.")

    friction = parsed["friction_coefficient"]
    safety_factor = parsed["safety_factor"]
    if friction is not None:
        inputs.append(f"Coeficiente de atrito provisório mu = {friction:g} [resposta do usuário].")
    if safety_factor is not None:
        inputs.append(f"Fator de segurança provisório FS = {safety_factor:g} [resposta do usuário].")
    if (
        mass_kg is not None
        and acceleration_m_s2 is not None
        and friction is not None
        and friction > 0
        and safety_factor is not None
        and safety_factor > 0
    ):
        assumptions.append("A carga normal é dividida igualmente entre dois dedos em contato.")
        per_finger_n = (
            safety_factor
            * mass_kg
            * (GRAVITY_M_S2 + acceleration_m_s2)
            / (friction * 2.0)
        )
        total_normal_n = per_finger_n * 2.0
        calculations.extend(
            [
                _result(
                    "CALC-GRIP-001",
                    "Força normal mínima estimada por dedo",
                    "N_dedo = FS * m * (g + a) / (mu * 2)",
                    (
                        f"N_dedo = {safety_factor:g} * {mass_kg:g} * "
                        f"({GRAVITY_M_S2:g} + {acceleration_m_s2:g}) / ({friction:g} * 2)"
                    ),
                    per_finger_n,
                    "N por dedo",
                    "estimado_por_hipotese",
                    [
                        "REQ-PERF-001",
                        "respostas: atrito e fator de segurança",
                        "CALC-KIN-002",
                        "hipótese de dois contatos iguais",
                    ],
                ),
                _result(
                    "CALC-GRIP-002",
                    "Força normal total estimada",
                    "N_total = 2 * N_dedo",
                    f"N_total = 2 * {per_finger_n:g}",
                    total_normal_n,
                    "N",
                    "estimado_por_hipotese",
                    ["CALC-GRIP-001"],
                ),
            ]
        )
        warnings.append(
            "A força de aperto depende de atrito e fator de segurança provisórios; confirme ambos por ensaio antes de dimensionar o atuador."
        )
    else:
        blocked.append(
            "Força de aperto: faltam massa, perfil de aceleração, coeficiente de atrito ou fator de segurança válidos."
        )

    if mass_kg is not None and average_speed_m_s is not None:
        average_lift_power_w = mass_kg * GRAVITY_M_S2 * average_speed_m_s
        calculations.append(
            _result(
                "CALC-POWER-001",
                "Potência mecânica ideal média de elevação",
                "P_media = m * g * v_media",
                f"P_media = {mass_kg:g} * {GRAVITY_M_S2:g} * {average_speed_m_s:g}",
                average_lift_power_w,
                "W",
                "calculado",
                ["REQ-PERF-001", "CALC-KIN-001", "constante g"],
            )
        )
        if acceleration_m_s2 is not None and peak_speed_m_s is not None:
            peak_lift_power_w = (
                mass_kg * (GRAVITY_M_S2 + acceleration_m_s2) * peak_speed_m_s
            )
            calculations.append(
                _result(
                    "CALC-POWER-002",
                    "Potência mecânica ideal de pico durante a aceleração",
                    "P_pico_ideal = m * (g + a) * v_pico",
                    (
                        f"P_pico_ideal = {mass_kg:g} * ({GRAVITY_M_S2:g} + "
                        f"{acceleration_m_s2:g}) * {peak_speed_m_s:g}"
                    ),
                    peak_lift_power_w,
                    "W",
                    "estimado_por_hipotese",
                    ["REQ-PERF-001", "CALC-KIN-002", "CALC-KIN-003"],
                )
            )
        warnings.append(
            "As potências mecânicas ideais não incluem perdas da transmissão, do motor, do driver nem margem térmica."
        )

    continuous_current_a = parsed["continuous_current_a"]
    peak_current_a = parsed["peak_current_a"]
    if voltage_v is not None:
        inputs.append(f"Tensão da fonte V = {voltage_v:g} V [REQ-ENER-001].")
    if voltage_v is not None and continuous_current_a is not None:
        inputs.append(
            f"Corrente contínua disponível I_cont = {continuous_current_a:g} A [resposta do usuário]."
        )
        calculations.append(
            _result(
                "CALC-ENER-001",
                "Potência elétrica contínua nominal da fonte",
                "P_cont = V * I_cont",
                f"P_cont = {voltage_v:g} * {continuous_current_a:g}",
                voltage_v * continuous_current_a,
                "W",
                "calculado",
                ["REQ-ENER-001", "resposta: corrente contínua"],
            )
        )
    else:
        blocked.append("Potência contínua da fonte: faltam tensão ou corrente contínua.")
    if voltage_v is not None and peak_current_a is not None:
        inputs.append(
            f"Corrente de pico disponível I_pico = {peak_current_a:g} A [resposta do usuário]."
        )
        calculations.append(
            _result(
                "CALC-ENER-002",
                "Potência elétrica de pico nominal da fonte",
                "P_pico = V * I_pico",
                f"P_pico = {voltage_v:g} * {peak_current_a:g}",
                voltage_v * peak_current_a,
                "W",
                "calculado",
                ["REQ-ENER-001", "resposta: corrente de pico"],
            )
        )
    else:
        blocked.append("Potência de pico da fonte: faltam tensão ou corrente de pico.")
    if voltage_v is not None and (continuous_current_a is not None or peak_current_a is not None):
        warnings.append(
            "A potência nominal da fonte não prova compatibilidade com um motor; ainda faltam eficiência, curva torque-velocidade, driver e regime térmico."
        )

    hours_per_day = parsed["hours_per_day"]
    life_cycles = parsed["life_cycles"]
    maintenance_cycles = parsed["maintenance_cycles"]
    cycles_per_day: float | None = None
    if cycles_per_minute is not None and cycles_per_minute > 0:
        inputs.append(
            f"Cadência f = {cycles_per_minute:g} ciclos/min [REQ-PERF-004]."
        )
        calculations.append(
            _result(
                "CALC-DUTY-001",
                "Período de um ciclo",
                "T = 60 / f",
                f"T = 60 / {cycles_per_minute:g}",
                60.0 / cycles_per_minute,
                "s/ciclo",
                "calculado",
                ["REQ-PERF-004"],
            )
        )
    if cycles_per_minute is not None and hours_per_day is not None:
        inputs.append(f"Jornada = {hours_per_day:g} h/dia [resposta do usuário].")
        cycles_per_day = cycles_per_minute * 60.0 * hours_per_day
        calculations.append(
            _result(
                "CALC-DUTY-002",
                "Ciclos por dia de operação",
                "ciclos_dia = f * 60 * horas_dia",
                f"ciclos_dia = {cycles_per_minute:g} * 60 * {hours_per_day:g}",
                cycles_per_day,
                "ciclos/dia",
                "calculado",
                ["REQ-PERF-004", "resposta: horas por dia"],
            )
        )
    else:
        blocked.append("Ciclos por dia: faltam cadência ou horas de operação diária.")

    if cycles_per_day and maintenance_cycles is not None:
        inputs.append(
            f"Intervalo de manutenção = {maintenance_cycles:g} ciclos [resposta do usuário]."
        )
        calculations.append(
            _result(
                "CALC-LIFE-001",
                "Intervalo entre manutenções em dias de operação",
                "dias_manut = ciclos_manut / ciclos_dia",
                f"dias_manut = {maintenance_cycles:g} / {cycles_per_day:g}",
                maintenance_cycles / cycles_per_day,
                "dias de operação",
                "calculado",
                ["CALC-DUTY-002", "resposta: intervalo de manutenção"],
            )
        )
    if cycles_per_day and life_cycles is not None:
        inputs.append(f"Vida útil desejada = {life_cycles:g} ciclos [resposta do usuário].")
        calculations.append(
            _result(
                "CALC-LIFE-002",
                "Vida útil em dias de operação",
                "dias_vida = ciclos_vida / ciclos_dia",
                f"dias_vida = {life_cycles:g} / {cycles_per_day:g}",
                life_cycles / cycles_per_day,
                "dias de operação",
                "calculado",
                ["CALC-DUTY-002", "resposta: vida útil em ciclos"],
            )
        )

    blocked.extend(
        [
            "Torque e rotação do atuador: faltam geometria do mecanismo, braços de alavanca, relação de transmissão e eficiência.",
            "Tensão e deformação do PETG: faltam geometria das peças, orientação de impressão e propriedades do lote fabricado.",
            "Limite de força para operação perto de pessoas: exige análise formal de risco e ensaios; nenhum valor seguro foi inferido.",
            "Custo total: faltam alternativas de mecanismo, componentes e cotações verificáveis.",
        ]
    )
    warnings.extend(
        [
            "Nenhum motor ou mecanismo foi selecionado por esta calculadora.",
            "O projeto não foi declarado seguro, validado ou pronto para fabricação.",
        ]
    )

    status: Literal["parcial", "bloqueado"] = "parcial" if calculations else "bloqueado"
    next_step = (
        "Validar coeficiente de atrito e perfil de movimento, definir a geometria do mecanismo "
        "e então calcular torque, rotação, eficiência e regime térmico antes de comparar atuadores."
        if calculations
        else "Completar os requisitos e respostas numéricas antes de iniciar o dimensionamento."
    )
    return EngineeringCalculationReport(
        project_id=project_id,
        project_name=brief.project_name,
        status=status,
        inputs=inputs,
        assumptions=assumptions,
        calculations=calculations,
        blocked_calculations=list(dict.fromkeys(blocked)),
        warnings=list(dict.fromkeys(warnings)),
        recommended_next_step=next_step,
    )


def _number_pt(value: float) -> str:
    if abs(value) >= 1000 and float(value).is_integer():
        return f"{value:,.0f}".replace(",", ".")
    rendered = f"{value:.3f}".rstrip("0").rstrip(".")
    return rendered.replace(".", ",")


def render_calculation_report(report: EngineeringCalculationReport) -> str:
    lines = [
        "IVY — MEMÓRIA DE CÁLCULO",
        "=" * 34,
        f"Projeto: {report.project_id} — {report.project_name}",
        f"Estado: {report.status}",
        "",
        "ENTRADAS RASTREADAS",
    ]
    lines.extend(f"- {item}" for item in report.inputs)
    lines.extend(["", "HIPÓTESES EXPLÍCITAS"])
    lines.extend(f"- {item}" for item in report.assumptions)
    lines.extend(["", "RESULTADOS"])
    if not report.calculations:
        lines.append("- Nenhum cálculo pôde ser concluído com os dados atuais.")
    for calculation in report.calculations:
        classification = (
            "calculado" if calculation.classification == "calculado" else "estimado por hipótese"
        )
        lines.extend(
            [
                f"- {calculation.id} — {calculation.name} [{classification}]",
                f"  Fórmula: {calculation.formula}",
                f"  Substituição: {calculation.substitution}",
                f"  Resultado: {_number_pt(calculation.value)} {calculation.unit}",
                "  Fontes: " + ", ".join(calculation.input_sources),
            ]
        )
    lines.extend(["", "CÁLCULOS AINDA BLOQUEADOS"])
    lines.extend(f"- {item}" for item in report.blocked_calculations)
    lines.extend(["", "ALERTAS"])
    lines.extend(f"- {item}" for item in report.warnings)
    lines.extend(["", "PRÓXIMO PASSO", report.recommended_next_step])
    return "\n".join(lines)
