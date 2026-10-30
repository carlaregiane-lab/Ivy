import unittest

from ivy_lab.calculator import calculate_project
from ivy_lab.concepts import compare_gripper_concepts, render_concept_report
from ivy_lab.interpreter import interpret_requirements


ADVANCED_REQUEST = (
    "Preciso desenvolver uma garra robótica elétrica de dois dedos para pegar "
    "caixas plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, "
    "elevá-las 30 cm em até 2 segundos e realizar 12 ciclos por minuto. "
    "A alimentação disponível é de 12 V, as peças estruturais serão impressas "
    "em PETG, o orçamento máximo é de R$ 600 e a garra trabalhará próxima a pessoas."
)

TEST_ANSWERS = {
    1: "Caixas rígidas e secas, com baixa fragilidade",
    2: "Os 2 segundos correspondem somente à elevação de 30 cm",
    3: "A fonte de 12 V fornece 10 A continuamente e 15 A de pico",
    4: "A garra operará 8 horas por dia e fará manutenção a cada 100.000 ciclos",
    5: "Adotar provisoriamente coeficiente de atrito 0,4",
    6: "Usar provisoriamente fator de segurança 2,5 e deformação máxima de 1 mm",
    7: "Usar proteções e manter limites de força bloqueados até análise formal",
}


class ConceptComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = interpret_requirements(ADVANCED_REQUEST, mode="demo")
        calculation = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)
        self.report = compare_gripper_concepts("PRJ-001", self.brief, calculation)

    def test_three_concepts_produce_expected_estimates_and_ranking(self) -> None:
        concepts = {item.id: item for item in self.report.concepts}

        self.assertEqual("comparacao_preliminar", self.report.status)
        self.assertEqual(3, len(concepts))
        self.assertAlmostEqual(
            0.344684,
            concepts["CONCEPT-SCREW-001"].required_torque_nm,
            places=5,
        )
        self.assertAlmostEqual(
            1.114704,
            concepts["CONCEPT-RACK-001"].required_torque_nm,
            places=5,
        )
        self.assertAlmostEqual(
            1.263331,
            concepts["CONCEPT-BELT-001"].required_torque_nm,
            places=5,
        )
        self.assertAlmostEqual(
            187.5,
            concepts["CONCEPT-SCREW-001"].required_speed_rpm,
            places=5,
        )
        self.assertEqual("CONCEPT-SCREW-001", self.report.recommended_concept_id)
        self.assertTrue(self.report.ranking[0].startswith("1. CONCEPT-SCREW-001"))

    def test_every_concept_has_traceable_formula_and_hypotheses(self) -> None:
        self.assertTrue(any("REQ-GEOM-001" in item for item in self.report.traced_inputs))
        self.assertTrue(any("CALC-GRIP-001" in item for item in self.report.traced_inputs))
        for concept in self.report.concepts:
            self.assertTrue(concept.torque_formula)
            self.assertTrue(concept.torque_substitution)
            self.assertTrue(concept.geometry_assumptions)
            self.assertEqual("estimado_por_hipotese", concept.classification)

    def test_missing_width_and_grip_force_block_comparison(self) -> None:
        brief = interpret_requirements(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas.",
            mode="demo",
        )
        calculation = calculate_project("PRJ-002", brief, {})
        report = compare_gripper_concepts("PRJ-002", brief, calculation)

        self.assertEqual("bloqueado", report.status)
        self.assertEqual([], report.concepts)
        self.assertTrue(any("Curso dos dedos" in item for item in report.blocked_verifications))
        self.assertTrue(any("Força de fechamento" in item for item in report.blocked_verifications))

    def test_report_never_selects_motor_or_declares_safety(self) -> None:
        rendered = render_concept_report(self.report)

        self.assertFalse(self.report.motor_selected)
        self.assertFalse(self.report.safety_validated)
        self.assertIn("Nenhum motor", rendered)
        self.assertIn("não valida", rendered)
        self.assertIn("apenas para detalhamento", rendered)


if __name__ == "__main__":
    unittest.main()
