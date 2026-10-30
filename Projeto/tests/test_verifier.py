import copy
from pathlib import Path
import tempfile
import unittest

from ivy_lab.cad import generate_parametric_gripper_cad
from ivy_lab.calculator import calculate_project
from ivy_lab.concepts import compare_gripper_concepts
from ivy_lab.interpreter import interpret_requirements
from ivy_lab.project_memory import ensure_project_history
from ivy_lab.verifier import render_verification_report, verify_project


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


class EngineeringVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.brief = interpret_requirements(ADVANCED_REQUEST, mode="demo")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _project(self, *, with_concepts: bool = False, with_cad: bool = False) -> dict:
        calculation = calculate_project("PRJ-001", self.brief, TEST_ANSWERS)
        project = {
            "id": "PRJ-001",
            "name": self.brief.project_name,
            "brief": self.brief.model_dump(mode="json"),
            "answers": {str(key): value for key, value in TEST_ANSWERS.items()},
            "calculation_revision": 1,
            "calculation_report": calculation.model_dump(mode="json"),
            "calculations_stale": False,
            "concept_revision": 0,
            "concept_report": None,
            "concepts_stale": False,
            "cad_revision": 0,
            "cad_report": None,
            "cad_stale": False,
        }
        if with_concepts or with_cad:
            concepts = compare_gripper_concepts(
                "PRJ-001",
                self.brief,
                calculation,
                source_calculation_revision=1,
            )
            project["concept_revision"] = 1
            project["concept_report"] = concepts.model_dump(mode="json")
        if with_cad:
            cad = generate_parametric_gripper_cad(
                "PRJ-001",
                self.brief,
                calculation,
                concepts,
                source_calculation_revision=1,
                source_concept_revision=1,
                cad_revision=1,
                artifact_root=Path(self.temporary.name) / "artifacts",
            )
            project["cad_revision"] = 1
            project["cad_report"] = cad.model_dump(mode="json")
        ensure_project_history(project, timestamp="2026-08-09T12:00:00-03:00")
        return project

    def test_valid_calculation_is_recomputed_without_errors(self) -> None:
        report = verify_project(self._project())

        self.assertEqual("consistente_com_alertas", report.status)
        self.assertEqual(0, report.error_count)
        self.assertGreater(report.passed_checks, 40)
        self.assertFalse(report.safety_validated)
        self.assertFalse(report.fabrication_approved)

    def test_modified_numeric_value_is_detected(self) -> None:
        project = self._project()
        result = next(
            item
            for item in project["calculation_report"]["calculations"]
            if item["id"] == "CALC-MECH-001"
        )
        result["value"] = 999.0

        report = verify_project(project)

        self.assertEqual("inconsistente", report.status)
        self.assertTrue(any(item.id == "VRF-CALC-MECH-001-VALUE" for item in report.findings))
        self.assertTrue(any("fotografia" in item.title.lower() for item in report.findings))

    def test_modified_unit_is_detected(self) -> None:
        project = self._project()
        result = next(
            item
            for item in project["calculation_report"]["calculations"]
            if item["id"] == "CALC-KIN-001"
        )
        result["unit"] = "km/h"

        report = verify_project(project)

        self.assertTrue(any(item.id == "VRF-CALC-KIN-001-UNIT" for item in report.findings))
        self.assertEqual("inconsistente", report.status)

    def test_stale_calculation_blocks_verification(self) -> None:
        project = self._project()
        project["calculations_stale"] = True

        report = verify_project(project)

        self.assertTrue(any(item.id == "VRF-CALC-002" for item in report.findings))
        self.assertEqual("inconsistente", report.status)

    def test_concepts_and_ranking_are_recomputed(self) -> None:
        report = verify_project(self._project(with_concepts=True))

        self.assertEqual("consistente_com_alertas", report.status)
        self.assertEqual(0, report.error_count)
        self.assertIn("comparação de conceitos", report.checked_artifacts)
        self.assertGreater(report.passed_checks, 60)

    def test_modified_ranking_and_recommendation_are_detected(self) -> None:
        project = self._project(with_concepts=True)
        project["concept_report"]["ranking"] = list(
            reversed(project["concept_report"]["ranking"])
        )
        project["concept_report"]["recommended_concept_id"] = "CONCEPT-BELT-001"

        report = verify_project(project)
        identifiers = {item.id for item in report.findings}

        self.assertIn("VRF-CONCEPT-RANKING", identifiers)
        self.assertIn("VRF-CONCEPT-RECOMMENDATION", identifiers)
        self.assertEqual("inconsistente", report.status)

    def test_cad_parameters_and_files_are_independently_verified(self) -> None:
        report = verify_project(self._project(with_cad=True))

        self.assertEqual("consistente_com_alertas", report.status)
        self.assertEqual(0, report.error_count)
        self.assertEqual(1, report.cad_revision)
        self.assertIn("modelo CAD paramétrico", report.checked_artifacts)
        self.assertGreater(report.passed_checks, 120)

    def test_modified_cad_parameter_is_detected(self) -> None:
        project = self._project(with_cad=True)
        parameter = next(
            item
            for item in project["cad_report"]["parameters"]
            if item["id"] == "CAD-PARAM-002"
        )
        parameter["value"] = 95.0

        report = verify_project(project)
        identifiers = {item.id for item in report.findings}

        self.assertIn("VRF-CAD-PARAM-002-VALUE", identifiers)
        self.assertIn("VRF-CAD-SIGNATURE", identifiers)
        self.assertEqual("inconsistente", report.status)

    def test_modified_cad_file_is_detected_by_hash(self) -> None:
        project = self._project(with_cad=True)
        artifact = next(
            item
            for item in project["cad_report"]["artifacts"]
            if item["kind"] == "stl_preview"
        )
        Path(artifact["path"]).write_text("solid adulterado\nendsolid adulterado\n", encoding="utf-8")

        report = verify_project(project)
        identifiers = {item.id for item in report.findings}

        self.assertIn("VRF-CAD-FILE-STL_PREVIEW-HASH", identifiers)
        self.assertIn("VRF-CAD-FILE-STL-CONTENT", identifiers)
        self.assertEqual("inconsistente", report.status)

    def test_project_without_engineering_artifacts_is_reported(self) -> None:
        project = copy.deepcopy(self._project())
        project["calculation_revision"] = 0
        project["calculation_report"] = None
        project["calculation_history"] = []

        report = verify_project(project)
        rendered = render_verification_report(report)

        self.assertEqual("sem_artefatos", report.status)
        self.assertIn("Ainda não existe uma memória de cálculo", rendered)
        self.assertIn("Segurança validada: não", rendered)


if __name__ == "__main__":
    unittest.main()
