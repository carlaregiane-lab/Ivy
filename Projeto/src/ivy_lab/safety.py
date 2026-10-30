"""Triagem conservadora de riscos antes de qualquer chamada de modelo."""

import unicodedata

from .models import RiskLevel


HIGH_RISK_TERMS = {
    "arma",
    "explosivo",
    "bomba",
    "municao",
    "veneno",
    "agente biologico",
}

MEDIUM_RISK_TERMS = {
    "alta tensao",
    "alta pressao",
    "voo tripulado",
    "propulsor",
    "vestivel",
    "exoesqueleto",
    "dispositivo medico",
}

CAUTION_TERMS = {
    "proxima a pessoas",
    "proximo a pessoas",
    "perto de pessoas",
    "contato com pessoas",
    "acesso de pessoas",
}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def assess_risk(text: str) -> tuple[RiskLevel, list[str]]:
    normalized = normalize(text)
    high_matches = sorted(term for term in HIGH_RISK_TERMS if term in normalized)
    if high_matches:
        return (
            RiskLevel.CRITICAL,
            [
                "Aplicação potencialmente perigosa detectada: " + ", ".join(high_matches),
                "O projeto não pode avançar automaticamente sem revisão humana especializada.",
            ],
        )

    medium_matches = sorted(term for term in MEDIUM_RISK_TERMS if term in normalized)
    if medium_matches:
        return (
            RiskLevel.HIGH,
            [
                "Condição de engenharia de alto risco detectada: "
                + ", ".join(medium_matches),
                "São necessárias análise de risco formal e supervisão especializada.",
            ],
        )

    caution_matches = sorted(term for term in CAUTION_TERMS if term in normalized)
    if caution_matches:
        return (
            RiskLevel.MEDIUM,
            [
                "Operação próxima a pessoas detectada.",
                "Devem ser definidos limites de força, proteção contra esmagamento, parada segura e validação formal de risco.",
            ],
        )

    return RiskLevel.LOW, []
