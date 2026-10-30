"""Interpreta pedidos informais como requisitos rastreáveis de engenharia."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import importlib.util
from typing import Literal

from .models import (
    EngineeringBrief,
    EngineeringDomain,
    EngineeringRequirement,
    Readiness,
    RequirementCategory,
    RequirementSource,
    RiskLevel,
)
from .safety import assess_risk, normalize


SYSTEM_PROMPT = """
Você é o módulo Analista de Requisitos da Ivy Lab.

Sua tarefa nesta etapa é extrair e organizar requisitos de engenharia, fazer
apenas derivações matemáticas simples e listar os cálculos ainda necessários.
Não selecione componentes nem faça dimensionamentos com dados ausentes.

Regras obrigatórias:
- preserve valores e unidades fornecidos pelo usuário;
- extraia faixas, limites, distâncias, tempos, frequências, tensões, materiais e orçamento;
- nunca invente valores numéricos, dimensões, materiais ou normas;
- coloque inferências apenas em assumptions e deixe claro que exigem confirmação;
- liste informações essenciais ausentes em unknowns;
- formule perguntas curtas e prioritárias;
- nunca pergunte novamente por uma informação que já foi fornecida;
- inclua derived_values somente quando a fórmula e os dados forem explícitos;
- inclua em calculation_plan as fórmulas, dados faltantes e verificações necessárias;
- diferencie requisitos explícitos de propostas;
- não declare que algo é seguro, validado ou funcional;
- sinalize aplicações envolvendo armas, explosivos, alta energia, alta pressão,
  voo tripulado, dispositivos médicos ou equipamentos presos ao corpo;
- use português do Brasil;
- retorne apenas o objeto estruturado solicitado.
""".strip()


Mode = Literal["auto", "demo", "api"]


Measurement = tuple[float, str, float, str]
RangeMeasurement = tuple[float, float, str, float, float, str]


@dataclass(frozen=True)
class GripperFacts:
    mass: Measurement | None
    width_range: RangeMeasurement | None
    lift_distance: Measurement | None
    maximum_time: Measurement | None
    cycles_per_minute: Measurement | None
    voltage: Measurement | None
    budget: Measurement | None
    electric: bool
    two_finger: bool
    plastic_boxes: bool
    petg_structure: bool
    printed_structure: bool
    near_people: bool


def _to_float(value: str) -> float:
    value = value.strip()
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def _canonical_length_unit(unit: str) -> str:
    if unit.startswith("mm") or unit.startswith("mili"):
        return "mm"
    if unit.startswith("cm") or unit.startswith("centi"):
        return "cm"
    return "m"


def _length_to_m(value: float, unit: str) -> float:
    unit = _canonical_length_unit(unit)
    if unit == "mm":
        return value / 1000.0
    if unit == "cm":
        return value / 100.0
    return value


def _format_pt(value: float, decimals: int = 3) -> str:
    rendered = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return rendered.replace(".", ",")


def _extract_mass(text: str) -> Measurement | None:
    normalized = normalize(text)
    match = re.search(
        r"(?P<value>\d+(?:[\.,]\d+)?)\s*(?P<unit>kg|quilogramas?|g|gramas?)\b",
        normalized,
    )
    if not match:
        return None

    value = float(match.group("value").replace(",", "."))
    unit_text = match.group("unit")
    if unit_text.startswith("kg") or unit_text.startswith("quilo"):
        return value, "kg", value, "kg"
    return value, "g", value / 1000.0, "kg"


def _extract_gripper_facts(request: str) -> GripperFacts:
    normalized = normalize(request)
    number = r"\d+(?:[\.,]\d+)?"
    length_unit = r"mm|milimetros?|cm|centimetros?|m|metros?"

    width_range: RangeMeasurement | None = None
    width_match = re.search(
        rf"(?:entre\s+)?(?P<minimum>{number})\s*(?:e|a|ate|-)\s*"
        rf"(?P<maximum>{number})\s*(?P<unit>{length_unit})\s*(?:de\s+)?largura",
        normalized,
    )
    if width_match:
        minimum = _to_float(width_match.group("minimum"))
        maximum = _to_float(width_match.group("maximum"))
        unit = _canonical_length_unit(width_match.group("unit"))
        width_range = (
            minimum,
            maximum,
            unit,
            _length_to_m(minimum, unit),
            _length_to_m(maximum, unit),
            "m",
        )

    lift_distance: Measurement | None = None
    lift_match = re.search(
        rf"(?:eleva(?:-l[oa]s?)?|levantar|erguer)[^\d]{{0,30}}"
        rf"(?P<value>{number})\s*(?P<unit>{length_unit})\b",
        normalized,
    )
    if lift_match:
        value = _to_float(lift_match.group("value"))
        unit = _canonical_length_unit(lift_match.group("unit"))
        lift_distance = (value, unit, _length_to_m(value, unit), "m")

    maximum_time: Measurement | None = None
    time_match = re.search(
        rf"(?:em\s+)?ate\s+(?P<value>{number})\s*(?:s|segundos?)\b",
        normalized,
    )
    if time_match:
        value = _to_float(time_match.group("value"))
        maximum_time = (value, "s", value, "s")

    cycles_per_minute: Measurement | None = None
    cycle_match = re.search(
        rf"(?P<value>{number})\s*ciclos?\s*(?:por|/)\s*min(?:uto)?",
        normalized,
    )
    if cycle_match:
        value = _to_float(cycle_match.group("value"))
        cycles_per_minute = (value, "ciclos/min", value / 60.0, "Hz")

    voltage: Measurement | None = None
    voltage_match = re.search(rf"(?P<value>{number})\s*(?:v|volts?)\b", normalized)
    if voltage_match:
        value = _to_float(voltage_match.group("value"))
        voltage = (value, "V", value, "V")

    budget: Measurement | None = None
    budget_match = re.search(rf"r\$\s*(?P<value>{number})", normalized)
    if budget_match:
        value = _to_float(budget_match.group("value"))
        budget = (value, "BRL", value, "BRL")

    return GripperFacts(
        mass=_extract_mass(request),
        width_range=width_range,
        lift_distance=lift_distance,
        maximum_time=maximum_time,
        cycles_per_minute=cycles_per_minute,
        voltage=voltage,
        budget=budget,
        electric="eletric" in normalized,
        two_finger="dois dedos" in normalized or "2 dedos" in normalized,
        plastic_boxes="caixa" in normalized and "plastic" in normalized,
        petg_structure="petg" in normalized,
        printed_structure="impress" in normalized,
        near_people=any(
            phrase in normalized
            for phrase in ("proxima a pessoas", "proximo a pessoas", "perto de pessoas", "contato com pessoas")
        ),
    )


def _requirement(
    identifier: str,
    category: RequirementCategory,
    statement: str,
    verification_method: str,
    measurement: Measurement | None = None,
) -> EngineeringRequirement:
    original_value = original_unit = normalized_value = normalized_unit = None
    if measurement:
        original_value, original_unit, normalized_value, normalized_unit = measurement
    return EngineeringRequirement(
        id=identifier,
        category=category,
        statement=statement,
        source=RequirementSource.USER,
        original_value=original_value,
        original_unit=original_unit,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        verification_method=verification_method,
    )


def _demo_interpretation(request: str) -> EngineeringBrief:
    normalized = normalize(request)
    is_gripper = "garra" in normalized or "gripper" in normalized
    is_robotic = "robot" in normalized
    facts = _extract_gripper_facts(request) if is_gripper else None
    risk_level, safety_flags = assess_risk(request)

    domains: list[EngineeringDomain] = []
    if is_gripper:
        domains.append(EngineeringDomain.MECHANICAL)
    if is_robotic:
        domains.extend([EngineeringDomain.MECHATRONICS, EngineeringDomain.ELECTRONICS])
    if not domains:
        domains.append(EngineeringDomain.OTHER)
    domains = list(dict.fromkeys(domains))

    requirements: list[EngineeringRequirement] = []
    if is_gripper:
        requirements.append(
            _requirement(
                "REQ-FUNC-001",
                RequirementCategory.FUNCTIONAL,
                "A garra deve segurar e levantar o objeto definido pelo usuário.",
                "Teste funcional com objeto representativo após validação do protótipo.",
            )
        )

    if facts and facts.plastic_boxes:
        requirements.append(
            _requirement(
                "REQ-FUNC-002",
                RequirementCategory.FUNCTIONAL,
                "A garra deve manipular caixas plásticas.",
                "Teste com amostras representativas das caixas autorizadas.",
            )
        )

    if facts and (facts.electric or facts.two_finger):
        architecture = "elétrica de dois dedos" if facts.electric and facts.two_finger else (
            "elétrica" if facts.electric else "de dois dedos"
        )
        requirements.append(
            _requirement(
                "REQ-FUNC-003",
                RequirementCategory.FUNCTIONAL,
                f"A arquitetura solicitada é uma garra {architecture}.",
                "Inspeção do conceito e teste funcional do protótipo.",
            )
        )

    if facts and facts.mass:
        original_value, original_unit, _, _ = facts.mass
        requirements.append(
            _requirement(
                "REQ-PERF-001",
                RequirementCategory.PERFORMANCE,
                f"O sistema deve levantar uma carga máxima de {_format_pt(original_value)} {original_unit}.",
                "Ensaio de carga controlado, definido somente após o dimensionamento.",
                facts.mass,
            )
        )

    if facts and facts.width_range:
        minimum, maximum, unit, *_ = facts.width_range
        requirements.append(
            _requirement(
                "REQ-GEOM-001",
                RequirementCategory.GEOMETRY,
                f"A garra deve aceitar caixas com largura entre {_format_pt(minimum)} e {_format_pt(maximum)} {unit}.",
                "Medição da abertura útil e teste com gabaritos nos dois limites.",
            )
        )

    if facts and facts.lift_distance:
        value, unit, *_ = facts.lift_distance
        requirements.append(
            _requirement(
                "REQ-PERF-002",
                RequirementCategory.PERFORMANCE,
                f"A garra deve elevar a caixa por {_format_pt(value)} {unit}.",
                "Medição do deslocamento vertical durante um ciclo representativo.",
                facts.lift_distance,
            )
        )

    if facts and facts.maximum_time:
        value, unit, *_ = facts.maximum_time
        requirements.append(
            _requirement(
                "REQ-PERF-003",
                RequirementCategory.PERFORMANCE,
                f"A elevação deve ocorrer em no máximo {_format_pt(value)} {unit}.",
                "Cronometragem do movimento sob carga máxima.",
                facts.maximum_time,
            )
        )

    if facts and facts.cycles_per_minute:
        value, unit, *_ = facts.cycles_per_minute
        requirements.append(
            _requirement(
                "REQ-PERF-004",
                RequirementCategory.PERFORMANCE,
                f"O sistema deve realizar {_format_pt(value)} {unit}.",
                "Ensaio de cadência e temperatura durante a duração de trabalho especificada.",
                facts.cycles_per_minute,
            )
        )

    if facts and facts.voltage:
        value, unit, *_ = facts.voltage
        requirements.append(
            _requirement(
                "REQ-ENER-001",
                RequirementCategory.ENERGY,
                f"A alimentação disponível é de {_format_pt(value)} {unit}.",
                "Medição de tensão, corrente e queda de tensão sob carga.",
                facts.voltage,
            )
        )

    if facts and facts.petg_structure:
        requirements.append(
            _requirement(
                "REQ-MATL-001",
                RequirementCategory.MATERIAL,
                "As peças estruturais devem ser fabricadas em PETG.",
                "Inspeção do material e registro dos parâmetros de fabricação.",
            )
        )

    if facts and facts.printed_structure:
        requirements.append(
            _requirement(
                "REQ-MANU-001",
                RequirementCategory.MANUFACTURING,
                "As peças estruturais devem ser produzidas por impressão 3D.",
                "Registro do processo, orientação, preenchimento e lote de fabricação.",
            )
        )

    if facts and facts.budget:
        value, *_ = facts.budget
        requirements.append(
            _requirement(
                "REQ-BUDG-001",
                RequirementCategory.BUDGET,
                f"O orçamento máximo informado é de R$ {_format_pt(value)}.",
                "Planilha de custos com componentes, fabricação e margem de contingência.",
                facts.budget,
            )
        )

    if facts and facts.near_people:
        requirements.append(
            _requirement(
                "REQ-SAFE-001",
                RequirementCategory.SAFETY,
                "A garra trabalhará próxima a pessoas e exige medidas formais contra esmagamento e movimento inesperado.",
                "Análise de risco, teste de parada segura e validação dos limites de força.",
            )
        )

    if is_gripper:
        project_name = "Garra robótica para caixas plásticas" if facts and facts.plastic_boxes else "Garra robótica"
        objective = (
            "Desenvolver uma garra robótica elétrica de dois dedos para segurar e elevar caixas plásticas."
            if facts and facts.electric and facts.two_finger and facts.plastic_boxes
            else "Desenvolver uma garra robótica para segurar e levantar um objeto."
        )
        unknowns = []
        questions = []
        assumptions: list[str] = []

        if facts and facts.plastic_boxes:
            unknowns.append("Altura, profundidade, rigidez, fragilidade e condição superficial das caixas.")
            questions.append("Quais são a altura, profundidade, fragilidade e condição superficial das caixas?")
        else:
            unknowns.append("Forma, dimensões, material e fragilidade do objeto.")
            questions.append("Qual é a forma, o tamanho, o material e a fragilidade do objeto?")

        if not facts or not facts.width_range:
            unknowns.append("Abertura mínima e máxima e curso necessário da garra.")
            questions.append("Qual abertura mínima e máxima a garra precisa alcançar?")
        else:
            unknowns.append("Geometria, área de contato e material das superfícies dos dedos.")

        if not facts or not facts.electric:
            unknowns.append("Tipo de atuação pretendido.")
            questions.append("A atuação será elétrica, pneumática ou ainda não há preferência?")

        if facts and facts.lift_distance and facts.maximum_time:
            unknowns.append("Perfil de movimento, aceleração máxima e definição exata do intervalo de 2 s.")
            assumptions.append("O deslocamento informado foi interpretado como elevação vertical.")
            questions.append("Os 2 s incluem apenas a elevação ou também fechamento, estabilização e liberação?")
        else:
            unknowns.append("Orientação, distância, velocidade e aceleração do movimento.")
            questions.append("Qual é a distância, orientação e tempo máximo do movimento?")

        if facts and facts.voltage:
            unknowns.append("Corrente contínua e de pico disponível na fonte de 12 V.")
            questions.append("Qual corrente contínua e de pico a fonte de 12 V pode fornecer?")
        else:
            unknowns.append("Tensão, corrente e potência disponíveis.")
            questions.append("Qual fonte de alimentação está disponível?")

        if facts and facts.cycles_per_minute:
            unknowns.append("Horas de operação por dia, vida útil desejada e pausas entre lotes.")
            questions.append("Quantas horas por dia a garra operará e qual vida útil em ciclos é esperada?")
        else:
            unknowns.append("Frequência e duração esperadas de operação.")
            questions.append("Quantos ciclos por minuto e quantas horas por dia são esperados?")

        if facts and facts.petg_structure:
            unknowns.append("Orientação de impressão, preenchimento, espessuras, temperatura e propriedades do PETG utilizado.")
        else:
            unknowns.append("Material, processo de fabricação e ferramentas disponíveis.")

        unknowns.extend(
            [
                "Coeficiente de atrito entre os dedos e a caixa.",
                "Fator de segurança e deformação máxima aceitável.",
                "Geometria do mecanismo, braços de alavanca, eficiência e envelope disponível.",
            ]
        )
        questions.extend(
            [
                "Qual coeficiente de atrito pode ser adotado ou como ele será medido?",
                "Qual fator de segurança e deformação máxima devem ser usados?",
            ]
        )
        if facts and facts.near_people:
            unknowns.append("Limites de força, proteção de pontos de esmagamento e comportamento seguro em falha.")
            questions.append("Quais proteções, limites de força e reação a falhas serão exigidos perto de pessoas?")

        derived_values: list[str] = []
        if facts and facts.width_range:
            minimum, maximum, unit, normalized_minimum, normalized_maximum, _ = facts.width_range
            derived_values.append(
                f"Faixa de largura: {_format_pt(minimum)}-{_format_pt(maximum)} {unit} = "
                f"{_format_pt(normalized_minimum)}-{_format_pt(normalized_maximum)} m."
            )
        if facts and facts.mass:
            _, _, mass_kg, _ = facts.mass
            weight = mass_kg * 9.80665
            derived_values.append(
                f"Peso estático da carga: F = m * g = {_format_pt(mass_kg)} * 9,80665 = {_format_pt(weight, 2)} N."
            )
        if facts and facts.lift_distance and facts.maximum_time:
            _, _, distance_m, _ = facts.lift_distance
            _, _, time_s, _ = facts.maximum_time
            average_speed = distance_m / time_s
            derived_values.append(
                f"Velocidade média mínima de referência: v = {_format_pt(distance_m)} / {_format_pt(time_s)} = {_format_pt(average_speed)} m/s."
            )
        if facts and facts.cycles_per_minute:
            cycles, _, frequency_hz, _ = facts.cycles_per_minute
            period = 60.0 / cycles
            derived_values.append(
                f"Cadência: {_format_pt(cycles)} ciclos/min = {_format_pt(frequency_hz)} Hz, ou {_format_pt(period)} s por ciclo."
            )

        calculation_plan = [
            "Força de aperto: F_aperto >= FS * m * (g+a)/(mu * n); faltam atrito mu, aceleração a, fator de segurança FS e distribuição entre contatos n.",
            "Torque do atuador: relacionar a força de aperto aos braços de alavanca, transmissão e eficiência do mecanismo.",
            "Velocidade do atuador: converter o deslocamento e o tempo exigidos pela cinemática real da garra.",
            "Potência e corrente em 12 V: calcular a partir de torque, velocidade, eficiência e picos de partida.",
            "Resistência e deformação do PETG: verificar tensões, deflexão, anisotropia da impressão, fluência e fadiga.",
            "Regime térmico: verificar motor, eletrônica e estrutura durante 12 ciclos/min e a jornada diária ainda desconhecida.",
            "Segurança: analisar esmagamento, soltura da carga, falha de energia, parada segura e limites de força perto de pessoas.",
            "Custo: somar atuador, transmissão, sensores, fonte, estrutura, fixadores e contingência sem ultrapassar R$ 600.",
        ]
    else:
        project_name = "Novo projeto de engenharia"
        objective = request.strip()
        assumptions = []
        derived_values = []
        calculation_plan = []
        unknowns = [
            "Função principal mensurável.",
            "Dimensões e interfaces.",
            "Condições de operação.",
            "Restrições de energia, materiais, fabricação, prazo e orçamento.",
            "Critérios de segurança e verificação.",
        ]
        questions = [
            "Qual problema mensurável este projeto deve resolver?",
            "Quais são as dimensões e condições de operação?",
            "Quais limites de custo, prazo e fabricação existem?",
        ]

    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        readiness = Readiness.BLOCKED_BY_RISK
        next_step = "Realizar revisão humana especializada de risco antes de detalhar o projeto."
    elif risk_level is RiskLevel.MEDIUM:
        readiness = Readiness.NEEDS_CLARIFICATION
        next_step = "Responder às perguntas prioritárias e realizar análise preliminar de risco antes de selecionar componentes."
    else:
        readiness = Readiness.NEEDS_CLARIFICATION
        next_step = "Responder às perguntas prioritárias e aprovar o briefing de requisitos."

    return EngineeringBrief(
        schema_version="0.2",
        original_request=request.strip(),
        project_name=project_name,
        objective=objective,
        domains=domains,
        requirements=requirements,
        assumptions=assumptions,
        unknowns=unknowns,
        questions=questions,
        risk_level=risk_level,
        safety_flags=safety_flags,
        readiness=readiness,
        recommended_next_step=next_step,
        derived_values=derived_values,
        calculation_plan=calculation_plan,
    )


def _api_interpretation(request: str) -> EngineeringBrief:
    risk_level, safety_flags = assess_risk(request)
    if risk_level is RiskLevel.CRITICAL:
        brief = _demo_interpretation(request)
        return brief.model_copy(
            update={
                "readiness": Readiness.BLOCKED_BY_RISK,
                "recommended_next_step": (
                    "Realizar revisão humana especializada de risco antes de qualquer análise por IA."
                ),
            }
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "O modo API exige o pacote 'openai'. Instale o projeto com: python -m pip install -e ."
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY não está configurada no ambiente.")

    client = OpenAI()
    model = os.getenv("IVY_MODEL", "gpt-5.6")
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ],
        text_format=EngineeringBrief,
    )
    brief = response.output_parsed
    if brief is None:
        raise RuntimeError("O modelo não retornou um briefing estruturado.")

    combined_flags = list(dict.fromkeys([*brief.safety_flags, *safety_flags]))
    combined_risk = max(
        (brief.risk_level, risk_level),
        key=lambda level: list(RiskLevel).index(level),
    )
    return brief.model_copy(
        update={"risk_level": combined_risk, "safety_flags": combined_flags}
    )


def interpret_requirements(request: str, mode: Mode = "auto") -> EngineeringBrief:
    if not request or not request.strip():
        raise ValueError("O pedido de engenharia não pode estar vazio.")
    if mode not in {"auto", "demo", "api"}:
        raise ValueError(f"Modo desconhecido: {mode}")

    if mode == "demo":
        return _demo_interpretation(request)
    if mode == "api":
        return _api_interpretation(request)

    api_ready = bool(os.getenv("OPENAI_API_KEY")) and importlib.util.find_spec("openai") is not None
    if api_ready:
        return _api_interpretation(request)
    return _demo_interpretation(request)
