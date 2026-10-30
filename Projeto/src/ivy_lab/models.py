"""Modelos de dados do contrato de requisitos da Ivy Lab."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EngineeringDomain(str, Enum):
    MECHANICAL = "mecanica"
    MECHATRONICS = "mecatronica"
    ELECTRICAL = "eletrica"
    ELECTRONICS = "eletronica"
    SOFTWARE = "software"
    MATERIALS = "materiais"
    CIVIL = "civil"
    OTHER = "outra"


class RequirementCategory(str, Enum):
    FUNCTIONAL = "funcional"
    PERFORMANCE = "desempenho"
    GEOMETRY = "geometria"
    MATERIAL = "material"
    ENERGY = "energia"
    ENVIRONMENT = "ambiente"
    SAFETY = "seguranca"
    BUDGET = "orcamento"
    MANUFACTURING = "fabricacao"
    VERIFICATION = "verificacao"


class RequirementSource(str, Enum):
    USER = "informado_pelo_usuario"
    DERIVED = "derivado_deterministicamente"
    PROPOSED = "proposto_para_confirmacao"


class RiskLevel(str, Enum):
    LOW = "baixo"
    MEDIUM = "medio"
    HIGH = "alto"
    CRITICAL = "critico"


class Readiness(str, Enum):
    NEEDS_CLARIFICATION = "necessita_esclarecimentos"
    READY_FOR_CONCEPT = "pronto_para_conceito"
    BLOCKED_BY_RISK = "bloqueado_por_risco"


class EngineeringRequirement(StrictModel):
    id: str = Field(description="Identificador rastreável, por exemplo REQ-FUNC-001")
    category: RequirementCategory
    statement: str
    source: RequirementSource
    original_value: float | None
    original_unit: str | None
    normalized_value: float | None
    normalized_unit: str | None
    verification_method: str | None

    @model_validator(mode="after")
    def validate_value_pairs(self) -> "EngineeringRequirement":
        if (self.original_value is None) != (self.original_unit is None):
            raise ValueError("original_value e original_unit devem aparecer juntos")
        if (self.normalized_value is None) != (self.normalized_unit is None):
            raise ValueError("normalized_value e normalized_unit devem aparecer juntos")
        return self


class EngineeringBrief(StrictModel):
    schema_version: Literal["0.1", "0.2"]
    original_request: str
    project_name: str
    objective: str
    domains: list[EngineeringDomain]
    requirements: list[EngineeringRequirement]
    assumptions: list[str]
    unknowns: list[str]
    questions: list[str]
    risk_level: RiskLevel
    safety_flags: list[str]
    readiness: Readiness
    recommended_next_step: str
    derived_values: list[str] = Field(default_factory=list)
    calculation_plan: list[str] = Field(default_factory=list)
