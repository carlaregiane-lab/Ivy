"""Ivy Lab: ferramentas verificáveis para engenharia assistida por IA."""

from .interpreter import interpret_requirements
from .models import EngineeringBrief

__all__ = ["EngineeringBrief", "interpret_requirements"]
__version__ = "0.9.0"
