import unittest

from ivy_lab.calculator import calculate_project, render_calculation_report
from ivy_lab.interpreter import interpret_requirements


ADVANCED_REQUEST = (
    "Preciso desenvolver uma garra robótica elétrica de dois dedos para pegar "
    "caixas plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, "
    "elevá-las 30 cm em até 2 segundos e realizar 12 ciclos por minuto. "
    "A alimentação disponível é de 12 V, as peças estruturais serão impressas "
    "em PETG, o orçamento máximo é de R$ 600 e a garra trabalhará próxima a pessoas."
)

TEST_ANSWERS = {
    1: "Caixas de polipropileno rígido, com 120 mm de altura, 150 mm de profundidade, baixa fragilidade e superfície lisa e seca",
    2: "Os 2 segundos correspondem somente à elevação de 30 cm",
    3: "A fonte de 12 V fornece 10 A continuamente e 15 A de pico",
    4: "A garra operará 8 horas por dia, com vida útil desejada de 1.000.000 de ciclos e manutenção a cada 100.000 ciclos",
    5: "Adotar provisoriamente coeficiente de atrito 0,4 entre revestimento e caixa",
    6: "Usar provisoriamente fator de segurança 2,5 e deformação máxima de 1 mm",
    7: "Usar proteções, parada de emergência e manter o limite de força bloqueado até análise formal",
}


class EngineeringCalculatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = interpret_requirements(ADVANCED_REQUEST, mode="demo")

    def _value(self, report, identifier: str) -> float:
        return next(item.value for item in report.calculations if item.id == identifier)

    def test_complete_answers_produce_expected_traceable_results(self) -> None:
        report = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)

        self.assertEqual("parcial", report.status)
        self.assertAlmostEqual(14.709975, self._value(report, "CALC-MECH-001"), places=5)
        self.assertAlmostEqual(0.15, self._value(report, "CALC-KIN-001"), places=5)
        self.assertAlmostEqual(0.3, self._value(report, "CALC-KIN-002"), places=5)
        self.assertAlmostEqual(47.374921875, self._value(report, "CALC-GRIP-001"), places=5)
        self.assertAlmostEqual(2.20649625, self._value(report, "CALC-POWER-001"), places=5)
        self.assertAlmostEqual(4.5479925, self._value(report, "CALC-POWER-002"), places=5)
        self.assertAlmostEqual(120.0, self._value(report, "CALC-ENER-001"), places=5)
        self.assertAlmostEqual(180.0, self._value(report, "CALC-ENER-002"), places=5)
        self.assertAlmostEqual(5760.0, self._value(report, "CALC-DUTY-002"), places=5)
        self.assertAlmostEqual(17.361111, self._value(report, "CALC-LIFE-001"), places=5)
        self.assertAlmostEqual(173.611111, self._value(report, "CALC-LIFE-002"), places=5)

    def test_every_result_has_formula_substitution_and_sources(self) -> None:
        report = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)

        self.assertGreaterEqual(len(report.calculations), 12)
        for result in report.calculations:
            self.assertTrue(result.formula)
            self.assertTrue(result.substitution)
            self.assertTrue(result.unit)
            self.assertTrue(result.input_sources)

    def test_missing_answers_keep_dependent_calculations_blocked(self) -> None:
        report = calculate_project("PRJ-001", self.brief, {})
        ids = {item.id for item in report.calculations}

        self.assertNotIn("CALC-GRIP-001", ids)
        self.assertNotIn("CALC-ENER-001", ids)
        self.assertTrue(any("Força de aperto" in item for item in report.blocked_calculations))
        self.assertTrue(any("corrente contínua" in item for item in report.blocked_calculations))

    def test_report_never_selects_motor_or_declares_safety(self) -> None:
        report = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)
        rendered = render_calculation_report(report)

        self.assertIn("Nenhum motor ou mecanismo foi selecionado", rendered)
        self.assertIn("não foi declarado seguro", rendered)
        self.assertIn("Torque e rotação do atuador", rendered)


if __name__ == "__main__":
    unittest.main()
