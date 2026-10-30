import json
from pathlib import Path
import tempfile
import unittest

from ivy_lab.cad import generate_parametric_gripper_cad, render_cad_report
from ivy_lab.calculator import calculate_project
from ivy_lab.concepts import compare_gripper_concepts
from ivy_lab.interpreter import interpret_requirements


ADVANCED_REQUEST = (
    "Preciso desenvolver uma garra robótica elétrica de dois dedos para pegar "
    "caixas plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, "
    "elevá-las 30 cm em até 2 segundos e realizar 12 ciclos por minuto. "
    "A alimentação disponível é de 12 V, as peças estruturais serão impressas "
    "em PETG, o orçamento máximo é de R$ 600 e a garra trabalhará próxima a pessoas."
)

TEST_ANSWERS = {
    1: "Caixas rígidas, lisas e secas",
    2: "Os 2 segundos correspondem somente à elevação de 30 cm",
    3: "A fonte de 12 V fornece 10 A continuamente e 15 A de pico",
    4: "A garra operará 8 horas por dia, com vida útil de 1.000.000 de ciclos e manutenção a cada 100.000 ciclos",
    5: "Adotar provisoriamente coeficiente de atrito 0,4",
    6: "Usar provisoriamente fator de segurança 2,5",
    7: "Manter o limite de força bloqueado até análise formal e ensaios",
}


class ParametricCADTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.temporary.name) / "artifacts"
        self.brief = interpret_requirements(ADVANCED_REQUEST, mode="demo")
        self.calculation = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)
        self.concepts = compare_gripper_concepts(
            "PRJ-001",
            self.brief,
            self.calculation,
            source_calculation_revision=1,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _generate(self, *, revision: int = 1):
        return generate_parametric_gripper_cad(
            "PRJ-001",
            self.brief,
            self.calculation,
            self.concepts,
            source_calculation_revision=1,
            source_concept_revision=1,
            cad_revision=revision,
            artifact_root=self.artifact_root,
        )

    def test_generates_four_versioned_artifacts(self) -> None:
        report = self._generate()

        self.assertEqual("modelo_parametrico_preliminar", report.status)
        self.assertEqual(20, len(report.parameters))
        self.assertEqual(4, len(report.artifacts))
        self.assertEqual(
            {"openscad_model", "stl_preview", "svg_preview", "manifest"},
            {artifact.kind for artifact in report.artifacts},
        )
        self.assertTrue(all(Path(artifact.path).is_file() for artifact in report.artifacts))
        self.assertFalse(report.component_selected)
        self.assertFalse(report.safety_validated)
        self.assertFalse(report.fabrication_approved)

    def test_requirement_and_derived_parameters_are_correct(self) -> None:
        report = self._generate()
        values = {parameter.symbol: parameter for parameter in report.parameters}

        self.assertEqual(40.0, values["abertura_minima"].value)
        self.assertEqual("requisito", values["abertura_minima"].classification)
        self.assertEqual(90.0, values["abertura_maxima"].value)
        self.assertEqual(25.0, values["curso_por_dedo"].value)
        self.assertEqual("derivado", values["curso_por_dedo"].classification)
        self.assertEqual(8.0, values["avanco_fuso"].value)
        self.assertEqual("hipotese", values["avanco_fuso"].classification)

    def test_geometric_contract_has_ten_passes_and_two_alerts(self) -> None:
        report = self._generate()
        statuses = {check.id: check.status for check in report.checks}

        self.assertTrue(
            all(statuses[f"CAD-CHK-{number:03d}"] == "aprovado" for number in range(1, 11))
        )
        self.assertEqual("alerta", statuses["CAD-CHK-011"])
        self.assertEqual("alerta", statuses["CAD-CHK-012"])

    def test_files_are_parametric_visual_and_explicitly_block_fabrication(self) -> None:
        report = self._generate()
        by_kind = {artifact.kind: Path(artifact.path) for artifact in report.artifacts}
        scad = by_kind["openscad_model"].read_text(encoding="utf-8")
        stl = by_kind["stl_preview"].read_text(encoding="utf-8")
        svg = by_kind["svg_preview"].read_text(encoding="utf-8")

        self.assertIn("abertura_minima = 40", scad)
        self.assertIn("assembly();", scad)
        self.assertIn("NÃO APROVADO PARA FABRICAÇÃO", scad)
        self.assertTrue(stl.startswith("solid ivy_prj_001"))
        self.assertIn("facet normal", stl)
        self.assertIn("<svg", svg)
        self.assertIn("NÃO APROVADO PARA FABRICAÇÃO", svg)

    def test_manifest_repeats_lineage_and_safety_locks(self) -> None:
        report = self._generate()
        manifest_path = next(
            Path(artifact.path) for artifact in report.artifacts if artifact.kind == "manifest"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(report.parameter_signature, manifest["parameter_signature"])
        self.assertEqual(1, manifest["source_calculation_revision"])
        self.assertEqual(1, manifest["source_concept_revision"])
        self.assertFalse(manifest["fabrication_approved"])
        self.assertFalse(manifest["safety_validated"])

    def test_generation_is_deterministic_for_same_revision_and_inputs(self) -> None:
        first = self._generate()
        second_root = Path(self.temporary.name) / "second"
        second = generate_parametric_gripper_cad(
            "PRJ-001",
            self.brief,
            self.calculation,
            self.concepts,
            source_calculation_revision=1,
            source_concept_revision=1,
            cad_revision=1,
            artifact_root=second_root,
        )

        self.assertEqual(first.parameter_signature, second.parameter_signature)
        self.assertEqual(
            {item.kind: item.sha256 for item in first.artifacts},
            {item.kind: item.sha256 for item in second.artifacts},
        )

    def test_blocked_concept_does_not_create_files(self) -> None:
        incomplete_calculation = calculate_project("PRJ-001", self.brief, {})
        blocked_concepts = compare_gripper_concepts(
            "PRJ-001",
            self.brief,
            incomplete_calculation,
            source_calculation_revision=1,
        )

        report = generate_parametric_gripper_cad(
            "PRJ-001",
            self.brief,
            incomplete_calculation,
            blocked_concepts,
            source_calculation_revision=1,
            source_concept_revision=1,
            cad_revision=1,
            artifact_root=self.artifact_root,
        )

        self.assertEqual("bloqueado", report.status)
        self.assertEqual([], report.artifacts)
        self.assertFalse(self.artifact_root.exists())

    def test_rendered_report_names_files_and_limits(self) -> None:
        rendered = render_cad_report(self._generate())

        self.assertIn("MODELO CAD PARAMÉTRICO", rendered)
        self.assertIn("openscad_model", rendered)
        self.assertIn("Fabricação aprovada: não", rendered)
        self.assertIn("Segurança validada: não", rendered)


if __name__ == "__main__":
    unittest.main()
