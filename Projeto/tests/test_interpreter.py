import unittest

from ivy_lab.interpreter import interpret_requirements
from ivy_lab.cli import render_report
from ivy_lab.models import EngineeringDomain, Readiness, RiskLevel


class RequirementsInterpreterTests(unittest.TestCase):
    def test_robotic_gripper_extracts_explicit_mass(self) -> None:
        brief = interpret_requirements(
            "Projete uma garra robótica capaz de levantar um objeto de 500 gramas.",
            mode="demo",
        )

        self.assertIn(EngineeringDomain.MECHANICAL, brief.domains)
        self.assertIn(EngineeringDomain.MECHATRONICS, brief.domains)
        load_requirement = next(item for item in brief.requirements if item.id == "REQ-PERF-001")
        self.assertEqual(load_requirement.original_value, 500)
        self.assertEqual(load_requirement.original_unit, "g")
        self.assertEqual(load_requirement.normalized_value, 0.5)
        self.assertEqual(load_requirement.normalized_unit, "kg")
        self.assertEqual(brief.readiness, Readiness.NEEDS_CLARIFICATION)
        self.assertGreaterEqual(len(brief.questions), 5)
        self.assertIn("normalizado: 0,5 kg", render_report(brief))

    def test_empty_request_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            interpret_requirements("   ", mode="demo")

    def test_high_risk_request_is_blocked_before_design(self) -> None:
        brief = interpret_requirements(
            "Projete uma arma com mecanismo robótico.",
            mode="demo",
        )

        self.assertEqual(brief.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(brief.readiness, Readiness.BLOCKED_BY_RISK)
        self.assertTrue(brief.safety_flags)

    def test_unknown_project_asks_for_measurable_goal(self) -> None:
        brief = interpret_requirements("Quero construir uma máquina inovadora.", mode="demo")

        self.assertFalse(brief.requirements)
        self.assertIn("Qual problema mensurável", brief.questions[0])

    def test_advanced_gripper_uses_all_supplied_constraints(self) -> None:
        request = (
            "Preciso desenvolver uma garra robótica elétrica de dois dedos para pegar "
            "caixas plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, "
            "elevá-las 30 cm em até 2 segundos e realizar 12 ciclos por minuto. "
            "A alimentação disponível é de 12 V, as peças estruturais serão impressas "
            "em PETG e o orçamento máximo é de R$ 600. A garra trabalhará próxima a pessoas. "
            "Organize os requisitos, identifique os dados que ainda faltam, indique os cálculos "
            "necessários e não escolha um motor nem declare o projeto seguro sem evidências suficientes."
        )

        brief = interpret_requirements(request, mode="demo")
        report = render_report(brief)
        statements = " ".join(item.statement for item in brief.requirements)

        for supplied_value in (
            "40 e 90 mm",
            "1,5 kg",
            "30 cm",
            "2 s",
            "12 ciclos/min",
            "12 V",
            "PETG",
            "R$ 600",
            "próxima a pessoas",
        ):
            self.assertIn(supplied_value, statements)

        repeated_questions = (
            "abertura mínima e máxima",
            "atuação será",
            "ciclos por minuto",
            "orçamento",
            "fonte de alimentação está disponível",
        )
        questions = " ".join(brief.questions).lower()
        for repeated in repeated_questions:
            self.assertNotIn(repeated, questions)

        self.assertEqual(brief.risk_level, RiskLevel.MEDIUM)
        self.assertIn("14,71 N", report)
        self.assertIn("0,15 m/s", report)
        self.assertIn("0,2 Hz", report)
        self.assertIn("Força de aperto", report)
        self.assertIn("Torque do atuador", report)
        self.assertIn("Potência e corrente", report)
        self.assertIn("Resistência e deformação do PETG", report)
        self.assertNotIn("motor selecionado", report.lower())


if __name__ == "__main__":
    unittest.main()
