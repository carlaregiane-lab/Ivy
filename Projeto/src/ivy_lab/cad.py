"""Geração determinística de um modelo CAD paramétrico preliminar para a Ivy."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path
import re
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .calculator import EngineeringCalculationReport
from .concepts import ConceptComparisonReport, MechanismConcept
from .models import EngineeringBrief
from .safety import normalize


CADStatus = Literal[
    "modelo_parametrico_preliminar",
    "bloqueado",
    "inconsistente",
]


class CADParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    symbol: str
    description: str
    value: float = Field(gt=0)
    unit: Literal["mm"] = "mm"
    classification: Literal["requisito", "derivado", "hipotese"]
    source: str


class CADCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: Literal["aprovado", "alerta", "erro"]
    description: str
    expected: str | None = None
    actual: str | None = None


class CADArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["openscad_model", "stl_preview", "svg_preview", "manifest"]
    filename: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_size: int = Field(gt=0)


class ParametricCADReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"
    project_id: str
    project_name: str
    status: CADStatus
    concept_id: str | None
    concept_name: str | None
    source_calculation_revision: int | None
    source_concept_revision: int | None
    output_directory: str | None
    parameter_signature: str | None
    parameters: list[CADParameter]
    checks: list[CADCheck]
    artifacts: list[CADArtifact]
    assumptions: list[str]
    warnings: list[str]
    blocked_verifications: list[str]
    recommended_next_step: str
    component_selected: Literal[False] = False
    safety_validated: Literal[False] = False
    fabrication_approved: Literal[False] = False


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


def _find_concept(
    report: ConceptComparisonReport,
    identifier: str | None,
) -> MechanismConcept | None:
    if identifier is None:
        return None
    for concept in report.concepts:
        if concept.id == identifier:
            return concept
    return None


def _screw_lead_mm(concept: MechanismConcept) -> float | None:
    text = normalize(" ".join(concept.geometry_assumptions))
    match = re.search(r"avanco[^=]{0,32}=\s*(\d[\d\.,]*)\s*mm", text)
    if not match:
        return None
    try:
        value = _parse_pt_number(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


def _parameter_signature(
    project_id: str,
    concept_id: str,
    calculation_revision: int,
    concept_revision: int,
    parameters: Iterable[CADParameter],
) -> str:
    payload = {
        "project_id": project_id,
        "concept_id": concept_id,
        "source_calculation_revision": calculation_revision,
        "source_concept_revision": concept_revision,
        "parameters": [
            parameter.model_dump(mode="json")
            for parameter in sorted(parameters, key=lambda item: item.id)
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _p(
    identifier: str,
    symbol: str,
    description: str,
    value: float,
    classification: Literal["requisito", "derivado", "hipotese"],
    source: str,
) -> CADParameter:
    return CADParameter(
        id=identifier,
        symbol=symbol,
        description=description,
        value=float(value),
        classification=classification,
        source=source,
    )


def _parameters(
    minimum_opening_mm: float,
    maximum_opening_mm: float,
    screw_lead_mm: float,
) -> list[CADParameter]:
    travel_per_jaw_mm = (maximum_opening_mm - minimum_opening_mm) / 2.0
    base_length_mm = max(
        150.0,
        math.ceil((maximum_opening_mm + 60.0) / 10.0) * 10.0,
    )
    return [
        _p(
            "CAD-PARAM-001",
            "abertura_minima",
            "Abertura útil mínima entre as faces dos dedos",
            minimum_opening_mm,
            "requisito",
            "REQ-GEOM-001",
        ),
        _p(
            "CAD-PARAM-002",
            "abertura_maxima",
            "Abertura útil máxima entre as faces dos dedos",
            maximum_opening_mm,
            "requisito",
            "REQ-GEOM-001",
        ),
        _p(
            "CAD-PARAM-003",
            "curso_por_dedo",
            "Curso simétrico necessário para cada dedo",
            travel_per_jaw_mm,
            "derivado",
            "(CAD-PARAM-002 - CAD-PARAM-001) / 2",
        ),
        _p(
            "CAD-PARAM-004",
            "abertura_visualizada",
            "Abertura usada no arquivo STL de visualização",
            maximum_opening_mm,
            "derivado",
            "CAD-PARAM-002",
        ),
        _p(
            "CAD-PARAM-005",
            "comprimento_base",
            "Comprimento preliminar da base",
            base_length_mm,
            "hipotese",
            "Margem geométrica preliminar de 30 mm por lado",
        ),
        _p(
            "CAD-PARAM-006",
            "profundidade_base",
            "Profundidade preliminar da base",
            60.0,
            "hipotese",
            "Envelope ainda não informado pelo usuário",
        ),
        _p(
            "CAD-PARAM-007",
            "espessura_base",
            "Espessura preliminar da base",
            10.0,
            "hipotese",
            "A confirmar por análise estrutural do PETG",
        ),
        _p(
            "CAD-PARAM-008",
            "largura_carro",
            "Largura de cada carro móvel",
            24.0,
            "hipotese",
            "Geometria conceitual sem mancal selecionado",
        ),
        _p(
            "CAD-PARAM-009",
            "profundidade_carro",
            "Profundidade de cada carro móvel",
            44.0,
            "hipotese",
            "Geometria conceitual sem guia selecionada",
        ),
        _p(
            "CAD-PARAM-010",
            "altura_carro",
            "Altura de cada carro móvel",
            12.0,
            "hipotese",
            "Geometria conceitual sem porca selecionada",
        ),
        _p(
            "CAD-PARAM-011",
            "largura_dedo",
            "Largura estrutural de cada dedo",
            12.0,
            "hipotese",
            "Dimensão pendente de resistência e deformação",
        ),
        _p(
            "CAD-PARAM-012",
            "profundidade_dedo",
            "Profundidade de contato de cada dedo",
            20.0,
            "hipotese",
            "Profundidade e geometria da caixa ainda incompletas",
        ),
        _p(
            "CAD-PARAM-013",
            "altura_dedo",
            "Altura preliminar de cada dedo",
            50.0,
            "hipotese",
            "Altura da caixa ainda não confirmada",
        ),
        _p(
            "CAD-PARAM-014",
            "parede_minima",
            "Espessura mínima de referência nas regiões impressas",
            6.0,
            "hipotese",
            "Não validada para PETG, impressão ou carga real",
        ),
        _p(
            "CAD-PARAM-015",
            "diametro_fuso",
            "Diâmetro nominal meramente geométrico do fuso",
            8.0,
            "hipotese",
            "Nenhum fuso comercial foi selecionado",
        ),
        _p(
            "CAD-PARAM-016",
            "avanco_fuso",
            "Avanço usado no conceito de fuso",
            screw_lead_mm,
            "hipotese",
            "Hipótese registrada em CONCEPT-SCREW-001",
        ),
        _p(
            "CAD-PARAM-017",
            "comprimento_fuso",
            "Comprimento geométrico do fuso na visualização",
            base_length_mm - 10.0,
            "hipotese",
            "Derivado do envelope preliminar da base",
        ),
        _p(
            "CAD-PARAM-018",
            "diametro_guia",
            "Diâmetro geométrico das duas guias",
            8.0,
            "hipotese",
            "Nenhuma guia ou mancal foi selecionado",
        ),
        _p(
            "CAD-PARAM-019",
            "distancia_entre_guias",
            "Distância transversal entre os eixos das guias",
            32.0,
            "hipotese",
            "Envelope preliminar de 60 mm",
        ),
        _p(
            "CAD-PARAM-020",
            "folga_visual",
            "Folga geométrica mínima de referência",
            0.5,
            "hipotese",
            "A ajustar ao processo, material e precisão reais",
        ),
    ]


def _value(parameters: list[CADParameter], symbol: str) -> float:
    for parameter in parameters:
        if parameter.symbol == symbol:
            return float(parameter.value)
    raise KeyError(symbol)


def _check(
    identifier: str,
    condition: bool,
    description: str,
    expected: str,
    actual: str,
) -> CADCheck:
    return CADCheck(
        id=identifier,
        status="aprovado" if condition else "erro",
        description=description,
        expected=expected,
        actual=actual,
    )


def _geometric_checks(parameters: list[CADParameter]) -> list[CADCheck]:
    minimum = _value(parameters, "abertura_minima")
    maximum = _value(parameters, "abertura_maxima")
    travel = _value(parameters, "curso_por_dedo")
    base_length = _value(parameters, "comprimento_base")
    base_depth = _value(parameters, "profundidade_base")
    carriage_width = _value(parameters, "largura_carro")
    carriage_depth = _value(parameters, "profundidade_carro")
    carriage_height = _value(parameters, "altura_carro")
    finger_width = _value(parameters, "largura_dedo")
    finger_depth = _value(parameters, "profundidade_dedo")
    wall = _value(parameters, "parede_minima")
    screw_diameter = _value(parameters, "diametro_fuso")
    screw_length = _value(parameters, "comprimento_fuso")
    guide_diameter = _value(parameters, "diametro_guia")
    guide_spacing = _value(parameters, "distancia_entre_guias")
    clearance = _value(parameters, "folga_visual")
    outer_width = maximum + 2.0 * carriage_width
    available_guide_depth = base_depth - guide_spacing
    return [
        _check(
            "CAD-CHK-001",
            minimum > 0 and maximum > minimum,
            "A faixa de abertura deve ser positiva e crescente.",
            "0 < abertura mínima < abertura máxima",
            f"{minimum:g} mm < {maximum:g} mm",
        ),
        _check(
            "CAD-CHK-002",
            math.isclose(travel, (maximum - minimum) / 2.0, rel_tol=1e-9),
            "O curso por dedo deve representar metade da variação de abertura.",
            f"{(maximum - minimum) / 2.0:g} mm",
            f"{travel:g} mm",
        ),
        _check(
            "CAD-CHK-003",
            base_length >= outer_width + 10.0,
            "A base deve conter os carros na abertura máxima com margem lateral.",
            f">= {outer_width + 10.0:g} mm",
            f"{base_length:g} mm",
        ),
        _check(
            "CAD-CHK-004",
            screw_length >= outer_width,
            "O fuso geométrico deve cobrir o envelope dos carros na abertura máxima.",
            f">= {outer_width:g} mm",
            f"{screw_length:g} mm",
        ),
        _check(
            "CAD-CHK-005",
            carriage_width >= finger_width + 2.0 * clearance,
            "O carro deve acomodar o dedo e uma folga visual bilateral.",
            f">= {finger_width + 2.0 * clearance:g} mm",
            f"{carriage_width:g} mm",
        ),
        _check(
            "CAD-CHK-006",
            carriage_depth <= base_depth - 2.0 * clearance,
            "O carro deve permanecer dentro da profundidade da base.",
            f"<= {base_depth - 2.0 * clearance:g} mm",
            f"{carriage_depth:g} mm",
        ),
        _check(
            "CAD-CHK-007",
            finger_depth <= carriage_depth,
            "A profundidade do dedo não deve ultrapassar a do carro neste modelo.",
            f"<= {carriage_depth:g} mm",
            f"{finger_depth:g} mm",
        ),
        _check(
            "CAD-CHK-008",
            wall >= 4.0,
            "A hipótese de parede deve permanecer acima do mínimo conceitual de 4 mm.",
            ">= 4 mm",
            f"{wall:g} mm",
        ),
        _check(
            "CAD-CHK-009",
            screw_diameter + 2.0 * clearance <= carriage_height,
            "O volume do carro deve acomodar o fuso e a folga visual.",
            f"<= {carriage_height:g} mm",
            f"{screw_diameter + 2.0 * clearance:g} mm",
        ),
        _check(
            "CAD-CHK-010",
            available_guide_depth >= 2.0 * guide_diameter,
            "As guias devem caber na base com margem transversal.",
            f">= {2.0 * guide_diameter:g} mm disponíveis",
            f"{available_guide_depth:g} mm disponíveis",
        ),
        CADCheck(
            id="CAD-CHK-011",
            status="alerta",
            description=(
                "A verificação geométrica não comprova resistência, rigidez, desgaste, "
                "tolerâncias de impressão ou segurança perto de pessoas."
            ),
        ),
        CADCheck(
            id="CAD-CHK-012",
            status="alerta",
            description=(
                "O STL é uma visualização de volumes conceituais e não contém roscas, "
                "mancais, fixadores, sensores, proteções ou interfaces finais."
            ),
        ),
    ]


def _scad_text(
    project_id: str,
    concept: MechanismConcept,
    parameters: list[CADParameter],
    signature: str,
) -> str:
    values = {parameter.symbol: parameter.value for parameter in parameters}
    declarations = "\n".join(
        f"{parameter.symbol} = {parameter.value:.6g}; // mm | {parameter.classification} | {parameter.source}"
        for parameter in parameters
    )
    return f"""/*
Ivy CAD paramétrico preliminar
Projeto: {project_id}
Conceito: {concept.id} — {concept.name}
Assinatura dos parâmetros: {signature}
NÃO APROVADO PARA FABRICAÇÃO OU USO PRÓXIMO A PESSOAS.
*/

$fn = 64;
{declarations}

module base() {{
    color([0.18, 0.28, 0.38])
        translate([-comprimento_base/2, -profundidade_base/2, 0])
            cube([comprimento_base, profundidade_base, espessura_base]);
}}

module eixo_x(comprimento, diametro, y_pos, z_pos, cor) {{
    color(cor)
        translate([-comprimento/2, y_pos, z_pos])
            rotate([0, 90, 0]) cylinder(h=comprimento, d=diametro);
}}

module conjunto_dedo(lado, abertura) {{
    centro_x = lado * (abertura/2 + largura_dedo/2);
    color([0.86, 0.57, 0.12])
        translate([centro_x-largura_carro/2, -profundidade_carro/2, espessura_base])
            cube([largura_carro, profundidade_carro, altura_carro]);
    color([0.12, 0.48, 0.72])
        translate([centro_x-largura_dedo/2, -profundidade_dedo/2, espessura_base+altura_carro])
            cube([largura_dedo, profundidade_dedo, altura_dedo]);
}}

module assembly(abertura=abertura_visualizada) {{
    assert(abertura >= abertura_minima && abertura <= abertura_maxima,
           "A abertura deve permanecer dentro da faixa de requisitos.");
    base();
    eixo_x(comprimento_fuso, diametro_fuso, 0,
           espessura_base + altura_carro/2, [0.72, 0.72, 0.74]);
    eixo_x(comprimento_fuso, diametro_guia, -distancia_entre_guias/2,
           espessura_base + altura_carro/2, [0.45, 0.47, 0.50]);
    eixo_x(comprimento_fuso, diametro_guia, distancia_entre_guias/2,
           espessura_base + altura_carro/2, [0.45, 0.47, 0.50]);
    conjunto_dedo(-1, abertura);
    conjunto_dedo(1, abertura);
}}

assembly();
"""


@dataclass(frozen=True)
class _Triangle:
    a: tuple[float, float, float]
    b: tuple[float, float, float]
    c: tuple[float, float, float]


def _box_triangles(
    center: tuple[float, float, float],
    size: tuple[float, float, float],
) -> list[_Triangle]:
    cx, cy, cz = center
    sx, sy, sz = (value / 2.0 for value in size)
    vertices = [
        (cx - sx, cy - sy, cz - sz),
        (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz),
        (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz),
        (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz),
        (cx - sx, cy + sy, cz + sz),
    ]
    faces = (
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    )
    return [_Triangle(vertices[a], vertices[b], vertices[c]) for a, b, c in faces]


def _cylinder_x_triangles(
    center: tuple[float, float, float],
    length: float,
    diameter: float,
    segments: int = 24,
) -> list[_Triangle]:
    cx, cy, cz = center
    x0, x1 = cx - length / 2.0, cx + length / 2.0
    radius = diameter / 2.0
    triangles: list[_Triangle] = []
    for index in range(segments):
        a0 = 2.0 * math.pi * index / segments
        a1 = 2.0 * math.pi * (index + 1) / segments
        p00 = (x0, cy + radius * math.cos(a0), cz + radius * math.sin(a0))
        p01 = (x0, cy + radius * math.cos(a1), cz + radius * math.sin(a1))
        p10 = (x1, cy + radius * math.cos(a0), cz + radius * math.sin(a0))
        p11 = (x1, cy + radius * math.cos(a1), cz + radius * math.sin(a1))
        triangles.extend(
            [
                _Triangle(p00, p10, p11),
                _Triangle(p00, p11, p01),
                _Triangle((x0, cy, cz), p01, p00),
                _Triangle((x1, cy, cz), p10, p11),
            ]
        )
    return triangles


def _normal(triangle: _Triangle) -> tuple[float, float, float]:
    ux = triangle.b[0] - triangle.a[0]
    uy = triangle.b[1] - triangle.a[1]
    uz = triangle.b[2] - triangle.a[2]
    vx = triangle.c[0] - triangle.a[0]
    vy = triangle.c[1] - triangle.a[1]
    vz = triangle.c[2] - triangle.a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    magnitude = math.sqrt(nx * nx + ny * ny + nz * nz)
    if magnitude == 0:
        return 0.0, 0.0, 0.0
    return nx / magnitude, ny / magnitude, nz / magnitude


def _stl_text(project_id: str, parameters: list[CADParameter]) -> str:
    v = {parameter.symbol: parameter.value for parameter in parameters}
    opening = v["abertura_visualizada"]
    carriage_z = v["espessura_base"] + v["altura_carro"] / 2.0
    finger_z = v["espessura_base"] + v["altura_carro"] + v["altura_dedo"] / 2.0
    triangles: list[_Triangle] = []
    triangles.extend(
        _box_triangles(
            (0.0, 0.0, v["espessura_base"] / 2.0),
            (v["comprimento_base"], v["profundidade_base"], v["espessura_base"]),
        )
    )
    for side in (-1.0, 1.0):
        center_x = side * (opening / 2.0 + v["largura_dedo"] / 2.0)
        triangles.extend(
            _box_triangles(
                (center_x, 0.0, carriage_z),
                (v["largura_carro"], v["profundidade_carro"], v["altura_carro"]),
            )
        )
        triangles.extend(
            _box_triangles(
                (center_x, 0.0, finger_z),
                (v["largura_dedo"], v["profundidade_dedo"], v["altura_dedo"]),
            )
        )
    triangles.extend(
        _cylinder_x_triangles(
            (0.0, 0.0, carriage_z),
            v["comprimento_fuso"],
            v["diametro_fuso"],
        )
    )
    for guide_y in (-v["distancia_entre_guias"] / 2.0, v["distancia_entre_guias"] / 2.0):
        triangles.extend(
            _cylinder_x_triangles(
                (0.0, guide_y, carriage_z),
                v["comprimento_fuso"],
                v["diametro_guia"],
            )
        )
    lines = [f"solid ivy_{project_id.lower().replace('-', '_')}"]
    for triangle in triangles:
        nx, ny, nz = _normal(triangle)
        lines.append(f"  facet normal {nx:.8g} {ny:.8g} {nz:.8g}")
        lines.append("    outer loop")
        for vertex in (triangle.a, triangle.b, triangle.c):
            lines.append(
                f"      vertex {vertex[0]:.8g} {vertex[1]:.8g} {vertex[2]:.8g}"
            )
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid ivy_{project_id.lower().replace('-', '_')}")
    return "\n".join(lines) + "\n"


def _svg_text(project_id: str, parameters: list[CADParameter], signature: str) -> str:
    v = {parameter.symbol: parameter.value for parameter in parameters}
    width, height = 1200, 1020
    scale = 5.0
    origin_x = width / 2.0
    views = [
        ("Abertura mínima", v["abertura_minima"], 270.0),
        ("Abertura máxima", v["abertura_maxima"], 700.0),
    ]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<title>Prévia CAD paramétrica da garra {escape(project_id)}</title>",
        "<desc>Vista superior conceitual nas aberturas mínima e máxima. Não aprovada para fabricação.</desc>",
        '<rect width="100%" height="100%" fill="#f7f9fc"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#1c2d3f}.title{font-size:28px;font-weight:700}.label{font-size:20px;font-weight:600}.small{font-size:15px}.dim{stroke:#cf7a00;stroke-width:2}.part{stroke:#24384d;stroke-width:2}.base{fill:#dce6f0}.jaw{fill:#2f78b7}.car{fill:#e3a33a}.rail{stroke:#6d7782;stroke-width:5}.warn{fill:#9b2c2c;font-weight:700}</style>',
        f'<text x="60" y="55" class="title">Ivy — CAD paramétrico preliminar | {escape(project_id)}</text>',
        f'<text x="60" y="82" class="small">Assinatura: {signature[:20]}…</text>',
    ]
    for label, opening, y_center in views:
        base_w = v["comprimento_base"] * scale
        base_h = v["profundidade_base"] * scale
        base_x = origin_x - base_w / 2.0
        base_y = y_center - base_h / 2.0
        elements.append(f'<text x="60" y="{y_center-base_h/2-20:.1f}" class="label">{label}: {opening:g} mm</text>')
        elements.append(
            f'<rect x="{base_x:.1f}" y="{base_y:.1f}" width="{base_w:.1f}" height="{base_h:.1f}" rx="8" class="part base"/>'
        )
        for rail_offset in (-v["distancia_entre_guias"] / 2.0, v["distancia_entre_guias"] / 2.0):
            rail_y = y_center + rail_offset * scale
            elements.append(
                f'<line x1="{base_x+25:.1f}" y1="{rail_y:.1f}" x2="{base_x+base_w-25:.1f}" y2="{rail_y:.1f}" class="rail"/>'
            )
        for side in (-1.0, 1.0):
            center_mm = side * (opening / 2.0 + v["largura_dedo"] / 2.0)
            center_px = origin_x + center_mm * scale
            car_w = v["largura_carro"] * scale
            car_h = v["profundidade_carro"] * scale
            finger_w = v["largura_dedo"] * scale
            finger_h = v["profundidade_dedo"] * scale
            elements.append(
                f'<rect x="{center_px-car_w/2:.1f}" y="{y_center-car_h/2:.1f}" width="{car_w:.1f}" height="{car_h:.1f}" rx="5" class="part car"/>'
            )
            elements.append(
                f'<rect x="{center_px-finger_w/2:.1f}" y="{y_center-finger_h/2:.1f}" width="{finger_w:.1f}" height="{finger_h:.1f}" class="part jaw"/>'
            )
        x_left = origin_x - opening * scale / 2.0
        x_right = origin_x + opening * scale / 2.0
        dim_y = y_center + base_h / 2.0 + 35.0
        elements.extend(
            [
                f'<line x1="{x_left:.1f}" y1="{dim_y:.1f}" x2="{x_right:.1f}" y2="{dim_y:.1f}" class="dim"/>',
                f'<line x1="{x_left:.1f}" y1="{dim_y-10:.1f}" x2="{x_left:.1f}" y2="{dim_y+10:.1f}" class="dim"/>',
                f'<line x1="{x_right:.1f}" y1="{dim_y-10:.1f}" x2="{x_right:.1f}" y2="{dim_y+10:.1f}" class="dim"/>',
                f'<text x="{origin_x:.1f}" y="{dim_y+24:.1f}" text-anchor="middle" class="small">{opening:g} mm entre faces</text>',
            ]
        )
    elements.extend(
        [
            '<text x="60" y="960" class="warn">MODELO CONCEITUAL — NÃO APROVADO PARA FABRICAÇÃO</text>',
            '<text x="60" y="990" class="small">Faltam análise estrutural, tolerâncias, roscas, mancais, fixações, sensores, proteções e validação de segurança.</text>',
            "</svg>",
        ]
    )
    return "\n".join(elements) + "\n"


def _write_text(path: Path, content: str) -> CADArtifact:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    data = path.read_bytes()
    kind_by_suffix = {
        ".scad": "openscad_model",
        ".stl": "stl_preview",
        ".svg": "svg_preview",
        ".json": "manifest",
    }
    return CADArtifact(
        kind=kind_by_suffix[path.suffix],
        filename=path.name,
        path=str(path.resolve()),
        sha256=sha256(data).hexdigest(),
        byte_size=len(data),
    )


def _blocked_report(
    project_id: str,
    project_name: str,
    calculation_revision: int | None,
    concept_revision: int | None,
    reasons: list[str],
) -> ParametricCADReport:
    return ParametricCADReport(
        project_id=project_id,
        project_name=project_name,
        status="bloqueado",
        concept_id=None,
        concept_name=None,
        source_calculation_revision=calculation_revision,
        source_concept_revision=concept_revision,
        output_directory=None,
        parameter_signature=None,
        parameters=[],
        checks=[],
        artifacts=[],
        assumptions=[],
        warnings=[
            "Nenhuma geometria foi criada porque as dependências rastreáveis não estavam completas."
        ],
        blocked_verifications=reasons,
        recommended_next_step="Completar as dependências indicadas e solicitar novamente o modelo CAD.",
    )


def generate_parametric_gripper_cad(
    project_id: str,
    brief: EngineeringBrief,
    calculation_report: EngineeringCalculationReport,
    concept_report: ConceptComparisonReport,
    *,
    source_calculation_revision: int,
    source_concept_revision: int,
    cad_revision: int,
    artifact_root: Path,
) -> ParametricCADReport:
    """Gera um modelo de volumes rastreável, sem aprovar fabricação."""

    blocked: list[str] = []
    width_range = _width_range_mm(brief)
    if width_range is None:
        blocked.append("Faixa de abertura: REQ-GEOM-001 não pôde ser reproduzido.")
    if calculation_report.project_id != project_id:
        blocked.append("A memória de cálculo pertence a outro projeto.")
    if concept_report.project_id != project_id:
        blocked.append("A comparação de conceitos pertence a outro projeto.")
    if concept_report.status != "comparacao_preliminar":
        blocked.append("A comparação de conceitos ainda está bloqueada.")
    if concept_report.source_calculation_revision not in {
        None,
        source_calculation_revision,
    }:
        blocked.append("A comparação não usa a revisão atual da memória de cálculo.")
    concept = _find_concept(concept_report, concept_report.recommended_concept_id)
    if concept is None:
        blocked.append("Não existe um conceito recomendado e rastreável para detalhamento.")
    elif concept.id != "CONCEPT-SCREW-001":
        blocked.append(
            "A versão 0.9 modela apenas CONCEPT-SCREW-001; o conceito recomendado atual não é suportado."
        )
    lead = _screw_lead_mm(concept) if concept is not None else None
    if lead is None:
        blocked.append("O avanço hipotético do fuso não pôde ser recuperado da comparação.")
    grip_ids = {calculation.id for calculation in calculation_report.calculations}
    if "CALC-GRIP-001" not in grip_ids:
        blocked.append("CALC-GRIP-001 é necessário para manter a ligação com o dimensionamento.")
    if blocked:
        return _blocked_report(
            project_id,
            brief.project_name,
            source_calculation_revision,
            source_concept_revision,
            blocked,
        )

    assert width_range is not None
    assert concept is not None
    assert lead is not None
    minimum_opening_mm, maximum_opening_mm = width_range
    parameters = _parameters(minimum_opening_mm, maximum_opening_mm, lead)
    checks = _geometric_checks(parameters)
    errors = [check for check in checks if check.status == "erro"]
    signature = _parameter_signature(
        project_id,
        concept.id,
        source_calculation_revision,
        source_concept_revision,
        parameters,
    )
    output_directory = (
        artifact_root.resolve()
        / project_id
        / "cad"
        / f"rev-{cad_revision:03d}"
    )
    assumptions = [
        "A base, os carros e os dedos são volumes simplificados para inspeção de envelope.",
        "Os dois dedos se movem simetricamente em torno do centro da garra.",
        "O STL mostra a abertura máxima; a abertura pode ser alterada no arquivo OpenSCAD.",
        "As dimensões sem requisito explícito permanecem hipóteses editáveis, não fatos do projeto.",
    ]
    warnings = [
        "Nenhum motor, fuso, porca, guia, mancal, fixador ou sensor comercial foi selecionado.",
        "O arquivo não contém rosca real, tolerâncias, orientação de impressão ou detalhes de fabricação.",
        "O modelo não valida PETG, resistência, deformação, fluência, fadiga ou desgaste.",
        "Operação próxima a pessoas continua bloqueada até análise de risco, proteções e ensaios.",
        "Os arquivos servem somente para inspeção virtual e evolução do projeto.",
    ]
    blocked_verifications = [
        "Definir o envelope completo, interfaces de montagem e geometria real das caixas.",
        "Selecionar e dimensionar fuso, porca, guias, mancais, eixos e fixações.",
        "Executar análise estrutural e de deformação com propriedades do PETG e da impressão.",
        "Verificar interferências, tolerâncias, folgas, curso, fim de curso e montagem.",
        "Executar análise de risco para esmagamento, soltura de carga e falta de energia.",
        "Simular o mecanismo e revisar o modelo com profissional responsável antes de fabricar.",
    ]

    artifacts: list[CADArtifact] = []
    if not errors:
        prefix = f"ivy_{project_id.lower()}_cad_rev_{cad_revision:03d}"
        artifacts.append(
            _write_text(
                output_directory / f"{prefix}.scad",
                _scad_text(project_id, concept, parameters, signature),
            )
        )
        artifacts.append(
            _write_text(
                output_directory / f"{prefix}.stl",
                _stl_text(project_id, parameters),
            )
        )
        artifacts.append(
            _write_text(
                output_directory / f"{prefix}.svg",
                _svg_text(project_id, parameters, signature),
            )
        )
        manifest = {
            "schema_version": "0.1",
            "project_id": project_id,
            "project_name": brief.project_name,
            "cad_revision": cad_revision,
            "concept_id": concept.id,
            "source_calculation_revision": source_calculation_revision,
            "source_concept_revision": source_concept_revision,
            "parameter_signature": signature,
            "parameters": [parameter.model_dump(mode="json") for parameter in parameters],
            "checks": [check.model_dump(mode="json") for check in checks],
            "fabrication_approved": False,
            "safety_validated": False,
            "warnings": warnings,
        }
        artifacts.append(
            _write_text(
                output_directory / f"{prefix}.json",
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
        )

    status: CADStatus = "inconsistente" if errors else "modelo_parametrico_preliminar"
    next_step = (
        "Corrigir as verificações geométricas antes de usar ou exportar o modelo."
        if errors
        else (
            "Revisar visualmente o STL e o SVG, ajustar as hipóteses no OpenSCAD e então "
            "avançar para simulação estrutural e cinemática."
        )
    )
    return ParametricCADReport(
        project_id=project_id,
        project_name=brief.project_name,
        status=status,
        concept_id=concept.id,
        concept_name=concept.name,
        source_calculation_revision=source_calculation_revision,
        source_concept_revision=source_concept_revision,
        output_directory=str(output_directory),
        parameter_signature=signature,
        parameters=parameters,
        checks=checks,
        artifacts=artifacts,
        assumptions=assumptions,
        warnings=warnings,
        blocked_verifications=blocked_verifications,
        recommended_next_step=next_step,
    )


def _number_pt(value: float) -> str:
    rendered = f"{value:.3f}".rstrip("0").rstrip(".")
    return rendered.replace(".", ",")


def render_cad_report(report: ParametricCADReport) -> str:
    lines = [
        "IVY — MODELO CAD PARAMÉTRICO",
        "=" * 36,
        f"Projeto: {report.project_id} — {report.project_name}",
        f"Estado: {report.status}",
        f"Conceito: {report.concept_id or 'não disponível'} — {report.concept_name or 'não disponível'}",
        f"Memória de cálculo de origem: revisão {report.source_calculation_revision or 'não disponível'}",
        f"Comparação de origem: revisão {report.source_concept_revision or 'não disponível'}",
    ]
    if report.parameter_signature:
        lines.append(f"Assinatura dos parâmetros: {report.parameter_signature}")
    lines.extend(["", "PARÂMETROS"])
    if not report.parameters:
        lines.append("- Nenhum parâmetro foi gerado.")
    for parameter in report.parameters:
        lines.append(
            f"- {parameter.id}: {parameter.description} = "
            f"{_number_pt(parameter.value)} {parameter.unit} "
            f"[{parameter.classification}; fonte: {parameter.source}]."
        )
    lines.extend(["", "VERIFICAÇÕES GEOMÉTRICAS"])
    if not report.checks:
        lines.append("- Nenhuma verificação geométrica foi executada.")
    for check in report.checks:
        lines.append(f"- [{check.status.upper()}] {check.id}: {check.description}")
        if check.expected is not None or check.actual is not None:
            lines.append(
                f"  Esperado: {check.expected or 'não informado'} | "
                f"Encontrado: {check.actual or 'não informado'}"
            )
    lines.extend(["", "ARQUIVOS GERADOS"])
    if not report.artifacts:
        lines.append("- Nenhum arquivo foi criado.")
    for artifact in report.artifacts:
        lines.append(
            f"- {artifact.kind}: {artifact.path} "
            f"[{artifact.byte_size} bytes; SHA-256 {artifact.sha256}]"
        )
    lines.extend(["", "HIPÓTESES"])
    lines.extend(f"- {item}" for item in report.assumptions)
    lines.extend(["", "ALERTAS"])
    lines.extend(f"- {item}" for item in report.warnings)
    lines.extend(["", "VERIFICAÇÕES AINDA BLOQUEADAS"])
    lines.extend(f"- {item}" for item in report.blocked_verifications)
    lines.extend(
        [
            "",
            "LIMITES FORMAIS",
            "- Componente comercial selecionado: não.",
            "- Segurança validada: não.",
            "- Fabricação aprovada: não.",
            "",
            "PRÓXIMO PASSO",
            report.recommended_next_step,
        ]
    )
    return "\n".join(lines)
